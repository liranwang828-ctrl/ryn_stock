# 回测系统设计规格

**日期**: 2026-05-21  
**状态**: 待实施  
**作者**: lirawang + Claude（含7位大师讨论）

---

## 一、背景与目标

### 问题
宏观策略和微观策略的所有参数（k1/k2/RSI阈值/VWAP偏离等）目前依赖直觉设定，缺乏历史数据验证。无法回答"这套参数的历史胜率是多少"。

### 目标
构建一套**纯脚本、按需运行**的历史回测系统，对两个策略参数文件进行数据驱动的优化，找到在历史上期望值最高、风险最小的参数组合。

### 设计约束
- 只用免费数据（yfinance）
- 一次运行 10-30 分钟，不常驻进程
- 结果需人工确认后才写回参数文件（防止过拟合自动覆盖）

---

## 二、整体架构

```
agents/
  backtest_macro.py      ← 宏观策略回测：5年日线，验证"何时进场"
  backtest_micro.py      ← 微观策略回测：结构位(5年) + 盘中信号(60天)
  backtest_runner.py     ← 统一入口，调用以上两个，生成对比报告

config/
  macro_strategy_params.json     ← 全局宏观参数（扫描后更新）
  micro_strategy_params.json     ← 全局微观参数（扫描后更新）
  macro_strategy_{sym}.json      ← 个股参数 evolution 字段（扫描后更新）

findings/
  backtest_report_{date}.json    ← 机器可读结果
  backtest_report_{date}.html    ← 人类可读对比报告（确认后才写回参数）
```

**用法：**
```bash
# 全量回测（宏观 + 微观结构位，约 15-25 分钟）
python3.12 agents/backtest_runner.py --years 5

# 仅盘中信号回测（60天滚动窗口，约 3-5 分钟，每2-4周重跑）
python3.12 agents/backtest_runner.py --intraday-only --window-days 60

# 确认并写回参数
python3.12 agents/backtest_runner.py --apply findings/backtest_report_{date}.json
```

---

## 三、评估指标体系（大师讨论确认）

每个参数组合计算以下6个指标（3.1-3.5 参与优化，3.6 Alpha 作为必要条件）：

### 3.1 期望值（EV）— 主优化目标
```
EV = 胜率 × 平均盈利 − 败率 × 平均亏损
```
- 正值说明策略有 edge
- 所有参数扫描以 EV 最大化为主目标

### 3.2 Sortino 比率（替代 Sharpe）
```
Sortino = (年化策略收益 − 无风险利率) / 下行标准差
无风险利率：使用3月期美债收益率近似（约4-5%，用固定值4.5%）
```
- 只惩罚下行波动，不惩罚上行
- 用于过滤"EV 为正但下行波动极大"的不稳定参数

### 3.3 最大回撤
```
Max Drawdown = max((peak - trough) / peak) 在所有持仓期间
```
- 设定上限阈值（第一版建议 -25%）
- 超过阈值的参数组合直接淘汰，不参与竞争

### 3.4 双重门槛（最低可接受标准）
```
胜率 ≥ 55%  AND  盈亏比（平均盈利/平均亏损） ≥ 1.5
```
- 不满足任一条件的参数组合直接淘汰

### 3.5 尾部风险（Taleb 检验）
```
最大单笔亏损 / 平均盈利 ≤ 3.0
```
- 防止策略在极端情况下单笔亏损摧毁整个期望值

### 3.6 Alpha（Druckenmiller 要求）
```
Alpha = 策略年化收益 − SPY 同期年化收益
```
- 必须为正，否则直接买 SPY 更好

### 3.7 附加诊断（不参与优化，作为参考）
- **MAE（最大不利偏移）**：入场后最大回撤幅度 → 反映止损设置是否合理
- **MFE（最大有利偏移）**：入场后最大涨幅 → 反映是否"卖早了"
- **Kelly 仓位建议**：`Kelly% = EV / 方差` → 理论最优仓位比例
- **连续亏损概率**：连续亏损5笔的概率（>20% 则心理上难以执行）

---

## 四、股票宇宙（约55只）

覆盖多板块多波动率，用于全局参数训练：

```python
BACKTEST_UNIVERSE = {
    "半导体/AI":    ["NVDA","AMD","AVGO","QCOM","MRVL","LITE","INTC","AMAT","KLAC"],
    "大型科技":     ["MSFT","AAPL","GOOGL","META","AMZN","NFLX","CRM","ORCL"],
    "消费/零售":    ["NIKE","SBUX","MCD","HD","COST","WMT","TGT"],
    "金融":         ["JPM","GS","V","MA","BAC"],
    "医疗":         ["JNJ","ABBV","UNH","LLY","PFE"],
    "工业/国防":    ["CAT","HON","RTX","BA"],
    "能源":         ["XOM","CVX","OXY"],
    "中概":         ["BABA","BIDU","JD"],
    "避险/大宗":    ["IAU","GLD","GDX"],
    "高波动成长":   ["TSLA","COIN","ROKU","SNOW"],
    "ETF/基准":     ["QQQ","SPY","TQQQ","SOXX","XLK","XLF"],
}
```

**分组输出**：高波动（半导体+成长）vs 低波动（消费+金融+医疗）vs 避险，检测参数是否存在系统性板块偏差。

---

## 五、宏观策略回测（backtest_macro.py）

### 5.1 数据
- 个股日线 OHLCV（5年，约1255根）
- SPY、QQQ 日线（相对强度 + 宏观背景）
- ^VIX、^VIX3M 日线（VIX 水平 + 期限结构）
- 财报日历（yfinance calendar，黑窗期过滤）

### 5.2 信号计算（每日滚动）
```python
ma20_dev    = (close - MA20) / MA20          # MA20 乖离率
ma200_up    = MA200.slope > 0                 # MA200 趋势方向（Stage 2 过滤）
dist_hi52w  = (close - hi52w) / hi52w        # 距52周高点（< -0.25 = 健康区间）
rs5         = stock_5d_ret - spy_5d_ret       # RS5日超额
vol_ratio   = volume / volume.rolling(20).mean()
vix_level   = vix_close                       # VIX 绝对值
vix_ts      = vix_close / vix3m_close         # VIX 期限结构（>1 = 短期恐慌）
rs_rank     = stock 在宇宙50只中的RS排名百分位
```

### 5.3 扫描参数
| 参数 | 范围 | 步长 | 写回位置 |
|------|------|------|---------|
| vix_panic_threshold | 20-30 | 2 | macro_strategy_params |
| ma20_dev_veto_pct | 5-15 | 2 | macro_strategy_params |
| qqq5m_veto | -1.0~-0.3 | 0.1 | macro_strategy_params |
| obs_minutes | 15-45 | 5 | macro_strategy_params |
| vix_ts_threshold | 0.9-1.2 | 0.05 | macro_strategy_params（新增）|
| rs_rank_min | 50-80 | 10 | macro_strategy_params（新增）|

### 5.4 硬规则（所有组合必须遵守）
- 财报黑窗期：距财报 < 10 个交易日跳过该信号
- 滑点：每笔 0.1%
- MA200 方向过滤：MA200 斜率 ≤ 0 时，跳过该信号（可选择性开关）

---

## 六、微观策略回测（backtest_micro.py）

### 6.1 结构位回测（5年日线）

#### 交易定义
```
入场：当日 Low ≤ Add1_d（当日计算的 Add1 价位）
  Add1_d = MA50_d + k2 × ATR14_d

持有：直到以下之一触发
  止盈：当日 High ≥ TP1_d = swing_high_90d × 0.995
  止损：当日 Low ≤ DynamicStop_d
    初始：MA50_d − k1 × ATR14_d
    浮盈≥breakeven_pct → 止损上移至成本
    浮盈≥trail_pct → 止损跟随 MA20

注：所有价位每日用截至 t−1 的历史数据滚动计算（防数据泄露）
```

#### 扫描参数（P1 优先网格搜索）
| 参数 | 范围 | 步长 | 写回位置 |
|------|------|------|---------|
| k1（止损ATR倍数）| 0.5-2.0 | 0.25 | `~/stock_team/macro_strategy_{sym}.json` evolution |
| k4（TP2折扣）| 0.80-1.0 | 0.05 | `~/stock_team/macro_strategy_{sym}.json` evolution |
| k5（情景降级）| 0.3-1.0 | 0.1 | `~/stock_team/macro_strategy_{sym}.json` evolution |
| breakeven_pct | 5-12 | 1 | `config/micro_strategy_params.json` |
| trail_pct | 10-20 | 2 | `config/micro_strategy_params.json` |

注：`macro_strategy_{sym}.json` 文件位于 `~/stock_team/`（BASE 目录），不在 `config/` 子目录。

#### 敏感性分析（P2，固定其他只扰动单个参数±20%）
- k2（Add1 ATR偏移）— 降为 P2 原因：k2 影响 Add1 价位，但 Add1 触及频率对整体 EV 影响相对 k1/k4 小，且 k1>k2 的逻辑约束已隐含控制；首版先用 k2=0.2 固定，验证后再加入 P1
- k6（base→bear 降级倍数）
- add1_tolerance_pct（Add1 价位容差）

### 6.2 盘中信号回测（60天5分钟）

#### 数据
- 个股5分钟 OHLCV（yfinance period="60d" interval="5m"）
- 仅使用持仓标的（NVDA/BABA/MSFT/IAU/MRVL/LITE），不跑全宇宙50只

#### 操作窗口
```
有效时间：10:00-10:30 ET（开盘后30-60分钟）
10:30后无新节点触发 → 当日不操作
操作延续到次日（持仓不强制当日平）
```

#### 交易定义（盘中）
```
入场价：触发信号的那根5分钟K线收盘价（加 0.1% 滑点）
止损价：当时 macro_strategy_{sym}.json 的 dynamic_stop.price
止盈价：当时 macro_strategy_{sym}.json 的 tp1.price
最大持有时间：当日收盘（16:00 ET）若未触发，次日延续
出场逻辑：High ≥ TP1 → 止盈；Low ≤ dynamic_stop → 止损；
          收盘时两者均未触发 → 持仓延续到次日，次日再判断
```

#### 信号检测（在10:00-10:30的5分钟K线上）
```python
rsi14_5m   = 5分钟K线的 RSI14
vwap_dev   = (price - VWAP) / VWAP × 100
vol_ratio  = 当前5分钟量 / 前20根5分钟均量
macd_cross = MACD 底背离（fast-slow 由负转正）
```

#### 扫描参数
| 参数 | 范围 | 步长 | 写回位置 |
|------|------|------|---------|
| rsi14_5m_oversold | 25-45 | 5 | micro_strategy_params |
| vwap_add_threshold | -3.0~-0.5 | 0.5 | micro_strategy_params |
| vol_ratio_shrink | 0.5-0.9 | 0.1 | micro_strategy_params |
| min_signals_required | 2-4 | 1（整数）| micro_strategy_params |

---

## 七、参数扫描流程

**扫描顺序：串行分阶段，不联合优化**
```
Step 1: 宏观策略扫描（backtest_macro.py）→ 更新 macro_strategy_params.json
Step 2: 微观结构位扫描（backtest_micro.py --structural）→ 更新各标的 evolution 字段
Step 3: 盘中信号扫描（backtest_micro.py --intraday）→ 更新 micro_strategy_params.json
```
各 Step 独立运行，Step 2 使用 Step 1 产出的最优宏观参数作为固定背景。

### 阶段1：大师约束剪枝
在扫描前，淘汰违反以下逻辑约束的参数组合：
```
k1 ≥ k2（止损宽度 > Add1 偏移，确保止损在Add1下方）
k4 ≤ 1.0（不能高于分析师目标价）
k5 < k6（bull→base 警戒比 base→bear 宽松）
max_drawdown ≤ 25%（任何参数组合的历史最大回撤上限）
```

### 阶段2：网格搜索
- P1 参数（k1/k4/k5）网格：7×5×8 = 280 组
- 每组计算5个指标
- 总耗时估计：10-20分钟

### 阶段3：样本外验证
- 训练集：data[:80%]（约4年）
- 验证集：data[80%:]（约1年）
- 淘汰条件：验证集胜率比训练集低 > 15个百分点 → 过拟合警告

### 阶段4：分时期分析
输出每个市场环境下的指标：
- 2021（牛市）/ 2022（熊市）/ 2023（复苏）/ 2024（AI牛市）
- 若某参数只在特定环境下优秀 → 标注为"环境依赖"，不推荐使用

---

## 八、输出与报告

### 机器可读（findings/backtest_report_{date}.json）
```json
{
  "run_date": "2026-05-21",
  "years": 5,
  "universe_size": 55,
  "total_simulated_trades": 2300,
  "macro_params": {
    "current": {...},
    "recommended": {...},
    "improvement": {"ev_pct": +12, "sortino": +0.3, "max_dd": -5}
  },
  "micro_structural_params": {
    "per_sym": {
      "NVDA": {"current_k1": 1.0, "recommended_k1": 1.25, ...},
      ...
    },
    "_write_back": "每个 sym 单独写回 ~/stock_team/macro_strategy_{sym}.json 的 evolution 字段，不合并到单一文件"
  },
  "micro_intraday_params": {...},
  "by_period": {...},
  "by_sector": {...},
  "master_notes": {...}
}
```

### 人类可读报告（findings/backtest_report_{date}.html）
- 参数变更前后对比表
- 分时期胜率图
- 分板块胜率图
- MAE/MFE 分布图
- Alpha vs SPY 对比
- 大师约束检查结果
- **人工确认**：HTML 末尾打印确认命令，用户查看报告后在终端手动执行 `--apply`（不实现 HTTP server）

### 写回机制
```bash
# 查看报告后，人工确认再写回
# --apply 执行前自动备份当前参数到 findings/params_backup_{date}.json
python3.12 agents/backtest_runner.py --apply findings/backtest_report_2026-05-21.json

# 若新参数表现变差，快速恢复
python3.12 agents/backtest_runner.py --restore findings/params_backup_2026-05-21.json

# 写回内容
config/macro_strategy_params.json    ← 全局宏观参数
config/micro_strategy_params.json   ← 全局微观参数
macro_strategy_{sym}.json evolution ← 各标的 k 值
```

---

## 九、重跑周期

| 回测类型 | 周期 | 触发条件 |
|---------|------|---------|
| 宏观 + 微观结构位 | 每季度 | 定期或新增标的后 |
| 盘中信号 | 每2-4周 | 60天窗口滚动 |
| 紧急重跑 | 随时 | 连续亏损3笔以上 |

---

## 十、文件依赖关系

```
backtest_runner.py
  ├─ backtest_macro.py
  │    reads: config/macro_strategy_params.json
  │    reads: yfinance [universe + VIX + VIX3M + SPY + QQQ]
  │    writes: findings/backtest_report_{date}.json (macro section)
  │
  ├─ backtest_micro.py
  │    reads: config/micro_strategy_params.json
  │    reads: macro_strategy_{sym}.json (当前 k 值作为基准)
  │    reads: yfinance [holdings 日线 + 5分钟]
  │    writes: findings/backtest_report_{date}.json (micro section)
  │
  └─ (--apply) writes:
       config/macro_strategy_params.json
       config/micro_strategy_params.json
       macro_strategy_{sym}.json (evolution 字段)
```
