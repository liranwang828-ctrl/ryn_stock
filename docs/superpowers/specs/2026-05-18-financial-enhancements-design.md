# 金融知识增强 — Design Spec

**Date**: 2026-05-18  
**Status**: Approved  
**Scope**: 8项金融知识增强，来源：ZhuLinsen/daily_stock_analysis (36k⭐) 萃取

---

## Goal

将 daily_stock_analysis 的核心金融分析方法论引入系统，包括：市场环境路由（5值regime）、乖离率追涨防护、预期重定价框架、情绪底部核查、大盘三段式复盘、催化剂分类、增收不增利检测。

---

## Architecture

```
子系统 A（基础层，先建）:
  config/market_regime.json    ← 新建（盘前写入，全天复用）
  agents/premarket.py          ← 修改（盘前运行 regime 检测，写 JSON）
  agents/quick_fundamentals.py ← 修改（新增 rev_fcf_gap + quality_warning）

子系统 B（入场&论点，依赖 A）:
  agents/poll.py               ← 修改（strategy_gate + evaluate_thesis_health）

子系统 C（盘前&盘后，独立）:
  agents/premarket_checklist.py ← 修改（情绪底部核查 + 催化剂分类显示）
  agents/postmarket_review.py   ← 修改（大盘三段式复盘）
  config/positions.json         ← 修改（加 catalyst_type + catalyst_persistence）
```

实施顺序：A → B → C（B 依赖 A 的 regime 文件）

---

## 子系统 A：基础层

### Part A1：Market Regime 检测

#### 输出文件：`config/market_regime.json`

```json
{
  "date": "2026-05-18",
  "regime": "trending_up",
  "confidence": "高",
  "signals": ["QQQ周涨+2.1%", "SPY MA20>MA50", "VIX=18.4降"],
  "updated_at": "2026-05-18T09:00:00"
}
```

`regime` 枚举（5值）：`trending_up / trending_down / sideways / volatile / sector_hot`

#### 检测逻辑（优先级从高到低，if-elif 链，第一个满足立即返回，不继续检测后续条件）

**volatile**（最高优先）：
- VIX > 25，OR
- 近5个交易日 SPY 任意两日日内振幅（(High-Low)/Open）> 1.5%

**sector_hot**：
- 任一板块 ETF（XLK/XLF/XLE/XLV/XLI/XLC/XLY/XLU）5日涨幅跑赢 SPY > 3%，同时 SPY 5日涨幅 < 1%（大盘平淡但板块轮动剧烈）

**trending_down**：
- SPY 或 QQQ 周线（5日）涨跌 < -2%，AND VIX 5日趋势向上（较5日前涨幅 > 10%）

**trending_up**：
- QQQ 5日涨幅 > 0%，AND SPY MA20 > MA50，AND VIX < 20

**sideways**（兜底）：
- 不满足以上任何条件（SPY 10日区间 < 3%，无明确趋势）

#### 触发时机

`premarket.py` 的 `run()` 函数在大盘数据获取后（现有 SPY/QQQ/VIX 数据处），调用新函数 `detect_market_regime()` 写入 `config/market_regime.json`。

同时将 regime 字符串注入 premarket_analysis 输出的 `macro.regime` 字段，供 poll.py 读取。

#### poll.py 读取方式

`run_poll()` 开头从 `config/market_regime.json` 读 regime（若文件不存在则默认 `"sideways"`），将其作为 `macro_state` 传入 `strategy_gate()`（现有接口兼容，字符串值扩展）。

---

### Part A2：增收不增利检测

在 `quick_fundamentals.py` 的 `fetch(sym)` 函数内新增检测。

**数据来源**：yfinance `freeCashflow` 返回 TTM 合计值（非季度值），无法直接算季度 YoY。改用**FCF/Revenue 比率变化**作为代理指标（更稳定，无需季度数据）：

```python
# FCF Margin = FCF / Revenue（比率越低=转化效率越差）
fcf_margin_now = fcf / rev if fcf and rev else None

# 已有: rev_growth_pct（营收增速）
# 用 fcf_margin 趋势判断增收不增利：
# 若营收增速 > 10% 且 FCF Margin < 15%（FCF 未同步增长）→ 质量预警

"fcf_margin":      round(fcf_margin_now * 100, 1) if fcf_margin_now else None
"rev_fcf_gap":     营收增速 - FCF Margin（比率，用于相对比较）
"quality_warning": rev_growth_pct > 10 and (fcf_margin_now or 1) < 0.15
```

注：`quality_warning=True` 表示"营收快速增长但 FCF 转化率偏低"，具体判断仍需结合行业基准。

`fmt_report()` 新增输出行：
```
盈利质量: FCF Margin 17.6% | ⚠️ 营收增速22%但FCF转化偏低，关注应收/存货
```

**同时**，`fetch()` 调用后将结果写入 `findings/fundamentals_{sym}.json`（供 evaluate_thesis_health 读取分析师目标价）：
```python
os.makedirs("findings", exist_ok=True)
json.dump(result, open(f"findings/fundamentals_{sym}.json", "w"), indent=2)
```

---

## 子系统 B：入场 & 论点增强

### Part B1：乖离率过滤器（strategy_gate）

**集成位置**：`strategy_gate()` 函数体的**最开头**（在任何评分计算之前），读取 `a["ma20"]` 和 `a["cur"]`，计算乖离率，设置 `_ma_ceiling`（局部变量），在函数末尾的 `consensus_code` 生成处应用 ceiling。

在 `strategy_gate()` 内，现有 `ma20` 字段已在 snap() 中计算，直接使用：

```python
ma_dev = (cur - ma20) / ma20 * 100 if ma20 else 0

if ma_dev > 10:
    score_penalty = 4
    warn_flag = f"⚠️ 乖离率{ma_dev:.1f}%严重超出，均值回归风险"
    consensus_code_ceiling = "no_buy"
elif ma_dev > 5:
    score_penalty = 2
    consensus_code_ceiling = "no_buy"  # 硬上限
elif ma_dev > 2:
    score_penalty = 1
    consensus_code_ceiling = None  # 不封顶，仅降分
else:
    score_penalty = 0
    consensus_code_ceiling = None
```

`consensus_code_ceiling` 为 `"no_buy"` 时，最终 `consensus_code` 不得高于 `no_buy`（即使加权评分 ≥ 7 也不输出 `buy`）。

输出格式新增一行（在技术信号区）：
```
│ 乖离率: +89.9% 🔴 严重超出 ⚠️ 不追（>5%禁追/>10%均值回归风险）
```

---

### Part B2：缩量回踩 T2 条件

**前提：snap() 需新增 `ma5` 和 `gain_10d` 字段**（与 B3 共用）：

在 `snap()` 的 MA 计算区域（现有 `ma20/ma50` 计算之后），新增：
```python
ma5     = float(h30["Close"].rolling(5).mean().iloc[-1])  if len(h30) >= 5  else None
gain_10d = (h30["Close"].iloc[-1] - h30["Close"].iloc[-11]) / h30["Close"].iloc[-11] * 100 if len(h30) >= 11 else None
```
并加入 snap() 的 return namedtuple。

在 `strategy_gate()` 的 T2 加仓判断区域（现有 `t2_conditions_met` 逻辑），新增一个前置条件函数 `_check_shrink_pullback(a)`：

```python
def _check_shrink_pullback(a):
    """缩量回踩验证：价格贴 MA5 + 成交量萎缩 + 乖离小"""
    cur    = a["cur"]
    ma5    = a.get("ma5")  # snap() 新增字段
    vr     = a.get("vol_ratio_5m", 1.0)

    if not ma5: return False, "MA5数据不可用"
    ma5_dev = abs(cur - ma5) / ma5 * 100
    vol_ok  = vr < 0.7
    dev_ok  = ma5_dev < 2.0
    price_ok = ma5_dev < 1.0  # 价格在 MA5 ± 1%

    met = price_ok and vol_ok and dev_ok
    reason = f"MA5偏离{ma5_dev:.1f}% 量比{vr:.2f}x" if not met else "缩量回踩条件满足"
    return met, reason
```

**注意**：`ma5` 字段需在 `snap()` 中新增（目前 snap 有 ma20/ma50，无 ma5）。

T2 加仓信号格式：
```
⚡ T2A条件满足（价格站稳+量比{vr}x+MACD正）
  ✅ 缩量回踩确认（MA5偏离0.3% 量比0.62x）
```

---

### Part B3：预期重定价框架（evaluate_thesis_health）

在 `evaluate_thesis_health()` 的信号检测区，新增一个判断块（在现有 T1/T2/RR 判断之后）：

**数据来源**：
- `catalyst_strength`：从 `position.get("catalyst_strength", 0)` 读取（或从 premarket_analysis 读）
- 10日涨幅：通过 yfinance history 计算（在 snap 时已有数据，用 `h30["Close"]` 计算）
- 分析师目标价：从 `quick_fundamentals` 输出文件读取（缓存，不每次拉取）

**三种状态检测**：

```python
# 状态1：利好不涨（预期转弱）
if position.get("catalyst_strength", 0) >= 3 and a.get("chg", 0) <= -0.5:
    signals.append("⚠️ 预期转弱：有强催化剂但今日下跌，市场已充分定价或论点被质疑")
    if status == "intact": status = "weakening"

# 状态2：预期兑现风险（连续大涨已定价）
gain_10d = a.get("gain_10d", 0)  # 需在 snap() 中新增10日涨跌幅
if gain_10d > 15:
    signals.append(f"⚠️ 预期兑现风险：10日涨{gain_10d:.1f}%，短期涨幅已充分定价，关注减速信号")

# 状态3：超越共识定价
target_price = _load_analyst_target(sym)  # 从缓存文件读
if target_price and cur > target_price * 1.0:
    over_pct = (cur - target_price) / target_price * 100
    signals.append(f"⚠️ 超越共识定价：现价${cur:.1f}超分析师目标${target_price:.1f}（+{over_pct:.1f}%），安全边际消失")
```

**`_load_analyst_target(sym)` 实现**：读取 `findings/fundamentals_{sym}.json`（由 `quick_fundamentals.fetch()` 调用时自动写入，详见 Part A2）。若文件不存在或无 `target_price` 字段，则跳过状态3检测，不影响其他逻辑。

**snap() 需新增字段**：`ma5` 和 `gain_10d`，详见 Part B2 说明。两者共用同一处 snap() 修改。

---

## 子系统 C：盘前 & 盘后

### Part C1：情绪底部五维核查（premarket_checklist）

新增函数 `_emotion_bottom_check(sym, pm_data, fundamentals)` → 返回 `(score, detail_lines)`

五个维度（每满足1项得1分，达到3分触发显示）：

| # | 维度 | 检测方法 | 数据来源 |
|---|------|---------|---------|
| 1 | 量能萎缩 | 近5日成交量均值 < 52周中位数×60% | yfinance history |
| 2 | 恐慌不高 | VIX 5日趋势向下 OR VIX < 18 | findings/macro.json |
| 3 | 新闻情绪 | premarket_analysis sentiment 为 neutral/negative | premarket_analysis JSON |
| 4 | 价格位置 | 现价在 MA20 ± 3% 以内且未跳空暴跌 | yfinance |
| 5 | 筹码稳定 | short_pct < 5% AND 内部人近期无大额净卖 | quick_fundamentals cache |

输出格式（在论点状态行之后）：

```
  情绪底部核查: 💡 强底部信号（4/5）— 量萎缩✅ 恐慌低✅ 情绪负面✅ 价格合理✅ 筹码稳定❌
```

score < 3 时不输出（保持输出干净）。

---

### Part C2：大盘三段式复盘（postmarket_review）

在 `postmarket_review.py` 的 `_master_response()` 之前，新增 `_market_3tier_review(date_str)` 函数，生成结构化大盘复盘块：

**第一段：趋势结构**
- SPY / QQQ / DJI 今日涨跌（yfinance，已在 postmarket 中拉取）
- 三指数同向/分化判断
- 成交量 vs 5日均量（扩量/缩量）

**第二段：资金情绪**
- VIX 方向（今日 vs 昨日）
- 上涨/下跌家数比（用 SPY 成分股近似，或用涨跌停标准）
- 成交额环比（今日 vs 近5日均值）

**第三段：主线板块**
- 11个板块 ETF（XLK/XLF/XLE/XLV/XLI/XLC/XLY/XLU/XLRE/XLB/XLP）今日涨跌
- 领涨前2个板块 + 简短催化判断（搜索 WebSearch 近期新闻）
- 板块扩散程度（上涨板块数 / 11）

输出格式：

```
【大盘三段式复盘】
━━━━━━━━━━━━━━━━━━━━━━━━
① 趋势: SPY -1.20% | QQQ -1.51% | DJI -0.85%  三指数同步下跌，弱势一致
   成交量: 1.2x 均量（放量下跌，偏空）

② 情绪: VIX 18.4 ↑（+5%）| 涨跌家比 2:8 | 成交额 1.1x 均量
   情绪方向: 偏空，恐慌轻度上升

③ 主线: 无明显领涨板块（最强 XLU +0.3% 防御）
   板块扩散: 2/11 板块上涨（广度极弱）
   判断: 防御轮动 + 整体回调，非主题行情日
━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Part C3：催化剂分类（positions.json + premarket_checklist）

**positions.json 新增两字段**（每个持仓）：

```json
"catalyst_type": "order",           // earnings/policy/order/capital/regulatory/null
"catalyst_persistence": "structural" // one_time/structural/null
```

字段语义：
- `earnings`：财报/业绩驱动（一次性/季度）
- `policy`：政策驱动（结构性，持续时间长）
- `order`：订单/客户合作（持续性取决于合作深度）
- `capital`：回购/增发/并购等资本运作（一次性）
- `regulatory`：监管/合规事件（通常一次性负面，或结构性利好）

**premarket_checklist.py** `_format_held()` 中，替换现有催化剂单行输出为分类展示：

```
【催化剂】类型: 订单(order) | 持续性: 结构性 | 强度: 4/5
  AWS Trainium2量产合作深化，多季度持续受益
```

---

## Validation

1. **Regime 写入**：运行 `python3.12 agents/premarket.py NVDA`，`config/market_regime.json` 生成且 `regime` 为五值之一。
2. **Regime poll 读取**：`poll.py` 读取 `market_regime.json`，`macro_state` 值正确传入 `strategy_gate()`。
3. **乖离率**：mock MRVL（距MA20 +90%），`strategy_gate` 输出 `consensus_code = no_buy` + 乖离率警示行。
4. **预期重定价**：mock catalyst_strength=3 且今日涨跌=-1%，`evaluate_thesis_health` 信号含"预期转弱"。
5. **增收不增利**：运行 `quick_fundamentals.py MRVL`，输出含 `rev_fcf_gap` 和 `quality_warning`。
6. **情绪底部核查**：mock 5维数据均满足，premarket_checklist 输出"强底部信号（5/5）"。
7. **三段式复盘**：运行 `postmarket_review.py`，输出含三段式结构。
8. **催化剂分类**：NVDA positions.json 加 `catalyst_type: earnings`，premarket_checklist 显示分类信息。

---

## Out of Scope

- 换手率 A 股原始数据接入（用量能百分位适配已足够）
- 板块扩散的机构级数据（用11个 ETF 近似）
- 月线乖离率计算（日线>5%已足够，月线可后续迭代）
- Regime 自动每轮 poll 更新（仅盘前更新一次，全天复用）
