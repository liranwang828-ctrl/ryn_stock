# 宏观策略（Macro Strategy）设计规格

**日期**: 2026-05-20  
**状态**: 待实施  
**作者**: lirawang + Claude

---

## 一、背景与目标

### 问题

当前 `strategic_memo_{sym}.json` 的所有交易数字（止损位、加仓位、目标价）基于成本价加固定百分比生成，与市场结构完全脱节：

- `hard_stop = cost × 0.87`（任意 -13%）
- `target_price = cost × (1 + target_pct%)`（基于成本，无 TA 依据）
- `t2_price_floor = cost × 0.92`（任意 -8%）

### 目标

设计独立的**宏观策略模块**，综合 memo 定性分析 + 实时市场数据，系统性制定所有交易节点。节点有章法、可解释、可回测、参数可自主进化。

### 命名约定

- **宏观策略**：本模块，负责制定所有价格节点
- **具体策略**：盘中执行逻辑（poll.py 等，不在本模块范围内）
- **节点命名**：Entry/Add1/Add2（买入方向）、TP1/TP2（卖出方向），避免 T1/T2 歧义

---

## 二、架构

### 定位

独立脚本 `agents/macro_strategy.py`，在以下两个流程中被调用：

```
stock-deep-research:
  cio.py → strategic_memo_writer.py → macro_strategy.py → report_viewer.py

stock-premarket:
  premarket.py → ... → macro_strategy.py --refresh → premarket_summary.py
```

`--refresh` 模式只重新抓取市场数据，更新以下动态节点，不重跑全量计算：Flex Reduce（盘中价位）、Time Stop（days_away 更新）、Catalyst Framework（pre_reduce_active 状态、post 触发价）。静态结构节点（Dynamic Stop、Add1/2、TP1/2）保持不变。

### 输入

| 来源 | 内容 |
|------|------|
| `strategic_memo_{sym}.json` | strategic_stance, scenarios, next_catalyst, unified_confidence, falsification_conditions, agent_analysis |
| 实时市场数据（yfinance） | OHLCV 历史, MA20/50/200, ATR14/ATR21, 近期摆动高低点(swing_high_90d/swing_low_14d), RSI14, 成交量比, 分析师目标价 |
| `memo.agent_analysis.sentiment` | sentiment_score（情绪得分）= SentimentAgent.confidence / 100，范围 [0,1]；TP1 阻力区参考 swing_high_90d 及其附近高点聚集区 |
| `config/positions.json` | cost, shares, position_type, catalyst_deadline |
| `findings/order_sheet_{date}.json` | entry_base（计划入场价，优先使用）；缺失时 fallback 到 positions.cost |

### 输出

`macro_strategy_{sym}.json`（示例结构见第五节）

被以下模块读取：
- `premarket_summary.py`：替换 exit_sect 中的 hard_stop / target_price
- `report_viewer.py`：在研究报告中渲染节点详情
- `backtest_engine.py`（扩展）：历史回测节点有效性

---

## 三、13个主节点

### 3.1 建仓类

#### Entry Invalidation（追涨上限）
- **用途**：防止在计划入场价之上追高
- **计算**：`entry_base + i1 × ATR14`，默认 `i1 = 0.5`；entry_base 来自 order_sheet_{date}.json.entry_base，缺失时用 positions.cost
- **失效条件**：N/A（纯上限，无失效）

#### Entry / Add1 / Add2（三批买入）
- **Entry**：初始建仓价，来自 order_sheet 或用户手动设定
- **Add1**：`max(Fib38.2%, MA50 + k2×ATR14)`；若近14日结构低点低于 max() 结果且差距 > 0.5×ATR14，则以结构低点作为更保守的覆盖值（结构优先规则）
  - 触发条件：论点 intact + vol_ratio < 0.8 + 催化剂窗口外
  - 失效条件：放量跌破 MA50 → 取消 Add1 计划
- **Add2**：`max(Fib61.8%, MA200 + k3×ATR14)`
  - 触发条件：unified_confidence ≥ 4（高置信度才允许第三批）
  - 失效条件：论点转 weakening → 取消 Add2
- **催化剂窗口冻结**：催化剂前3天/后1天内，自动冻结 Add1/Add2 价格触发

#### Re-entry（重建仓位价）
- **用途**：Dynamic Stop 触发出场后，论点仍 intact 时的重新入场价
- **计算**：`MA50 + k_reentry×ATR14`，通常为 Add1 附近
- **条件**：thesis_status = intact + 距止损出场 ≥ 3 天

### 3.2 止损类

#### Dynamic Stop（动态止损）

**状态机：**

```
初始状态（T1 锚定）:
  price = max(MA50, 近14日结构低点) − k1×ATR14
  默认 k1 = 1.0

激活条件 → 转移动止损:
  浮盈 ≥ +8%  → 止损上移至成本价（保本线）
  浮盈 ≥ +15% → 止损跟随 MA20（每日更新）

跳空执行规则:
  开盘价直接低于 stop_price → 市价出场，不等盘中确认
```

- **失效条件**：当日收盘反回 stop_price + 0.5×ATR14 以上且缩量 → 视为假突破，记录但不自动恢复

**与 Scenario Downgrade 的关系**：Dynamic Stop 是**执行触发器**（当天市价出场），Scenario Downgrade base→bear 是**论点状态分类器**（更新 thesis_status）。两者价格接近属于设计意图——论点破裂时价格也应在止损附近。同时触发时：Dynamic Stop 优先执行出场，Scenario Downgrade 更新状态标签。

#### Force Exit（强制清仓）

两个触发版本，任一满足即执行全仓清出：

| 版本 | 触发价 | 来源 |
|------|--------|------|
| Bear 情景版 | `memo.scenarios.bear.price_target` | 论点完全破裂兜底线 |
| 催化剂暴雷版 | `Entry − fe_catalyst×ATR14` | 催化剂期间重大负面事件 |

- **跳空规则**：开盘直接低于 Force Exit 价 → 市价执行，无等待

#### Market Context Stop（外部环境止损）
独立模块 `portfolio_macro_guard`，被宏观策略调用，不写入个股节点：

| 层次 | 触发条件 | 动作 |
|------|---------|------|
| 大盘层 | VIX 单日 +5 以上 或 SPY 单日 < −2.5% | 所有持仓按比例缩仓 X% |
| 板块层 | 对应板块 ETF 跌破 MA50 + 个股相对强度转负 | 该板块持仓缩仓 Y% |

X、Y 系数通过回测优化，存放于 `config/portfolio_macro_guard.json`；`macro_strategy.py` 在生成节点时调用 `portfolio_macro_guard.get_thresholds()` 获取当前值，不写入个股 JSON。

### 3.3 目标类

#### TP1（第一批减仓目标）
- **计算**：近90日内最近阻力位（近期高点聚集区）
- **减仓量**：30% 持仓
- **跳空规则**：开盘跳空高于 TP1 → 直接按开盘价执行 TP1

#### TP2（第二批减仓目标/清仓）
- **计算**：`min(分析师目标价 × k4, 历史前高)`，默认 `k4 = 0.90`
- **减仓量**：剩余全部
- **失效条件**：分析师目标价下调超 10% → 重新计算 TP2

#### Flex Reduce（盘中动态减仓）
- **计算**：盘中动态（VWAP + RSI > 70 警戒，近期短期阻力）
- **约束**：单次减量 ≤ 该批次计划减仓量的 50%，剩余留给 TP1/TP2 执行
- **备注**：`--refresh` 模式每日盘前更新

### 3.4 情景类

#### Scenario Downgrade（情景降级价位）

| 降级方向 | 触发价 | 含义 |
|---------|--------|------|
| bull → base | `MA20 − k5×ATR14` | 论点转 weakening，发出预警 |
| base → bear | `MA50 − k6×ATR14` | 论点转 broken，触发 Dynamic Stop 或 Force Exit 评估 |

两个价位同时也是论点损伤预警的量化锚点（合并，无独立节点）。

#### Catalyst Framework（催化剂节点）
- **前缩仓价**：催化剂重要性 = high + days_away ≤ 3 → 建议缩至安全仓位（减 Z%）
- **后加仓触发**：催化剂结果超预期 + 股价站上 `entry_base + c1×ATR14` → 触发 Add1
- **后强制清仓**：催化剂结果暴雷 + 股价跌破 `entry_base − c2×ATR14` → 触发 Force Exit（催化剂版）

Z、c1、c2 为可回测系数。

### 3.5 时间类

#### Time Stop（时间止损框架）

| 子类型 | 适用场景 | 触发条件 |
|--------|---------|---------|
| 普通时间止损 | 所有持仓 | 持仓超过 N 天，价格未向 TP1 移动 5% 以上 → 强制重新评估 |
| 衰减止损 | 杠杆 ETF（MRVU/LITX） | 持有 > D 天且底层标的涨幅 < M% → 复利损耗超阈值，强制清仓 |

默认值：N=30天，D=14天，M=5%

---

## 四、自主进化机制

### 层1：历史数据回测（参数优化）

```
输入：
  历史 OHLCV（yfinance 拉取）
  历史 memo 快照（cio runs/ 目录的存档）

扫描参数空间：
  k1 ∈ [0.5, 2.0]  (Dynamic Stop ATR 倍数)
  k4 ∈ [0.80, 1.0] (TP2 分析师目标折扣)
  k5 ∈ [0.3, 0.8]  (Scenario Downgrade bull→base)
  k6 ∈ [0.8, 1.5]  (Scenario Downgrade base→bear)
  N  ∈ [20, 45]    (时间止损天数)
  D  ∈ [7, 21]     (杠杆衰减天数)

评估指标：
  Dynamic Stop 被扫频率（越低越好）
  TP1/TP2 命中率（越高越好）
  平均盈亏比（越高越好）
  最大回撤（越低越好）

输出：
  最优系数写入 macro_strategy_{sym}.json evolution 字段
  同时写入 learning/macro_strategy_backtest_{date}.json
```

### 层2：交易反馈（前向学习）

```
每次交易结束：
  对比 "计划节点 vs 实际价格行为"
  追加到 learning/macro_strategy_outcomes.jsonl

字段：{sym, date, node_type, planned_price, actual_trigger_price,
       outcome: hit|missed|skipped, pnl_impact}

达到 30 条记录后：
  引入 ML 特征回归
  特征：ATR距离, MA距离, 情绪得分, 催化剂类型, unified_confidence
  目标：预测各节点命中概率
```

### 后期优化（方案 C，关键扩展点）

盘前校正层：读取当日开盘数据（gap%、VIX 变化、期货）→ 对节点做 ±校正量微调，不改变结构层节点，只在 premarket_summary 中写入当日校正版本。

---

## 五、输出 JSON 结构

```json
{
  "sym": "NVDA",
  "generated_at": "2026-05-20T17:00:00Z",
  "market_data_date": "2026-05-20",
  "nodes": {
    "entry_invalidation": {
      "price": 229.5,
      "basis": "entry_base(224.0) + 0.5×ATR14(8.3) = 228.2，取整229.5"
    },
    "add1": {
      "price": 212.0,
      "basis": "max(Fib38.2%=202.1, MA50(210.2)+0.2×ATR14(8.3)=211.9) = 211.9，近14日结构低点208.5差距<0.5×ATR不触发结构覆盖，取 212.0",
      "conditions": ["论点 intact", "vol_ratio < 0.8", "催化剂窗口外"],
      "invalidation": "放量跌破 MA50 → 取消 Add1"
    },
    "add2": {
      "price": 187.0,
      "basis": "Fib61.8%=187.2",
      "conditions": ["unified_confidence ≥ 4"],
      "invalidation": "论点转 weakening → 取消"
    },
    "re_entry": {
      "price": 213.0,
      "basis": "MA50(210.2) + 0.3×ATR14 = 212.7",
      "conditions": ["thesis_status = intact", "距止损出场 ≥ 3天"],
      "invalidation": "距止损出场不足3天 或 论点已转 weakening/broken → 取消重建"
    },
    "dynamic_stop": {
      "price": 201.9,
      "basis": "max(MA50=210.2, 近14日结构低点=208.5) − 1.0×ATR14(8.3) = 201.9",
      "trail_activation": {
        "breakeven_trigger_pct": 8,
        "ma20_trail_trigger_pct": 15
      },
      "invalidation": "收盘反回 stop+0.5×ATR 且缩量 → 假突破",
      "gap_rule": "开盘直接低于此价 → 市价出场"
    },
    "force_exit": {
      "price_bear": 156.4,
      "price_catalyst": 195.2,
      "basis_bear": "memo.scenarios.bear.price_target",
      "basis_catalyst": "entry(224.0) − 2.0×ATR14 = 207.4，取催化剂缓冲修正",
      "gap_rule": "开盘低于此价 → 市价执行"
    },
    "tp1": {
      "price": 238.0,
      "basis": "近90日阻力区 235-240，取中值 238",
      "reduce_pct": 30,
      "gap_rule": "开盘高于 TP1 → 按开盘价执行"
    },
    "tp2": {
      "price": 247.8,
      "basis": "分析师目标$275.3 × 0.90 = 247.8",
      "reduce_pct": 100,
      "invalidation": "分析师目标下调超10% → 重算"
    },
    "flex_reduce": {
      "note": "盘中动态，--refresh 每日更新",
      "max_reduce_pct": 15,
      "basis": "VWAP 偏离 + RSI > 70"
    },
    "scenario_downgrade": {
      "bull_to_base": {
        "price": 206.1,
        "basis": "MA20(215.8) − 0.5×ATR14(8.3) = 215.8 - 4.15 = 211.65，取近期支撑修正 206.1"
      },
      "base_to_bear": {
        "price": 200.0,
        "basis": "MA50(210.2) − 1.0×ATR14 = 201.9，与 dynamic_stop 相近"
      }
    },
    "catalyst_framework": {
      "pre_reduce_active": true,
      "pre_reduce_days": 3,
      "pre_reduce_pct": 20,
      "post_add_trigger": 231.0,
      "post_force_exit": 210.0,
      "next_catalyst": {"event": "earnings", "date": "2026-05-28", "importance": "high"}
    },
    "time_stop": {
      "type": "standard",
      "review_date": "2026-06-18",
      "condition": "持仓超30天且未向TP1移动5%",
      "decay_stop": null
    }
  },
  "market_inputs": {
    "price": 224.77,
    "ma20": 215.8,
    "ma50": 210.2,
    "ma200": 178.5,
    "atr14": 8.3,
    "atr21": 7.9,
    "fib_382": 202.1,
    "fib_618": 187.2,
    "analyst_target": 275.3,
    "rsi14": 60.9,
    "swing_high_90d": 242.5,
    "swing_low_14d": 208.5,
    "volume_ratio": 1.1,
    "sentiment_score": 0.85
  },
  "memo_inputs": {
    "strategic_stance": "hold",
    "unified_confidence": 3,
    "next_catalyst": {"event": "earnings", "date": "2026-05-28", "importance": "high"},
    "scenario_bear_price": 156.4,
    "scenario_base_price": 211.6,
    "scenario_bull_price": 275.3
  },
  "evolution": {
    "rule_version": "1.0",
    "k1": 1.0,
    "k2": 0.2,
    "k3": 0.0,
    "k4": 0.90,
    "k5": 0.5,
    "k6": 1.0,
    "k_reentry": 0.3,
    "fe_catalyst": 2.0,
    "c1": 0.5,
    "c2": 1.5,
    "Z_pre_reduce_pct": 20,
    "N_time_stop": 30,
    "D_decay_stop": 14,
    "M_decay_min_pct": 5.0,
    "last_backtest_date": null,
    "backtest_score": null,
    "outcomes_count": 0
  }
}
```

---

## 六、集成点变更

### premarket_summary.py
读取 `macro_strategy_{sym}.json`，替换当前草率计算：
- `exit_sect.hard_stop` ← `nodes.dynamic_stop.price`
- `exit_sect.target_price` ← `nodes.tp1.price`（主目标改为 TP1）
- `exit_sect.flex_add_level` ← `nodes.add1.price`
- `exit_sect.flex_reduce_level` ← `nodes.flex_reduce`

### strategic_memo_writer.py
`position_context` 中的 add_strategy / reduce_strategy 字段改为从 macro_strategy 读取，memo 只保留定性描述，数字来自宏观策略。

### report_viewer.py
新增"交易节点"Section，渲染 macro_strategy_{sym}.json 的所有节点，含计算依据和失效条件。

### backtest_engine.py（新增扩展）
新增 `backtest_macro_strategy` 模式，扫描参数空间，输出最优系数。

---

## 七、新增 Skill 触发规则

在 `stock-deep-research` skill 中，`macro_strategy.py` 作为第6步（report_agent 之前）自动调用。在 `stock-premarket` skill 中，`macro_strategy.py --refresh` 作为第7步（premarket_summary 之前）调用。

---

## 八、未来扩展（方案 C）

**盘前校正层（关键优化点）**：
在 `macro_strategy.py --refresh` 中增加盘前校正逻辑：读取当日开盘数据（gap%、VIX 变化、期货走势）→ 对结构层节点做 ±校正，结果写入 `premarket_summary` 的 `macro_adj` 字段。结构层节点不变，仅盘前报告中展示校正版本。

**ML 层**：
交易反馈数据达到 30 条后，引入特征回归模型预测各节点命中概率，高概率节点自动提高权重。
