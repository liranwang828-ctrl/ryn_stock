# AI 过热阶段波段估值温度计

## 状态

```yaml
status: methodology_candidate_pending_user_review
created_at: 2026-06-05
use_case: AI theme swing valuation
trade_permission: no
```

## 为什么需要这套方法

在 AI 主题过热阶段，传统估值经常会失效：

- DCF 对短期情绪和资金流不敏感。
- 静态 P/E 可能长期看贵，但股价仍继续上涨。
- 只看便宜会错过主线。
- 完全不看估值又容易在情绪末端接盘。

所以这里不用“估值 = 买卖开关”。

而是：

```text
估值 = 风险温度计
```

它的作用不是告诉我“应该买还是卖”，而是告诉我：

- 是否允许追高
- 是否只能等回调
- 仓位能不能打满
- 止损必须多紧
- 是否需要分批
- 赔率是否还够

## 核心问题

每次研究 AI 波段仓，都问六个问题：

```text
1. Narrative Temperature
2. Growth Confirmation
3. Peer Valuation And Quality
4. Price Location
5. Downside If Narrative Cools
6. Swing Risk / Reward
```

## 1. Narrative Temperature

问题：

市场是否正在奖励这条 AI 主线？

观察：

- 板块是否持续相对强于 QQQ / SOXX
- 同主题标的是否集体走强
- 新闻、财报、订单、capex 是否都指向同一方向
- 是否已经进入人人都在讨论的过热状态

分级：

| 温度 | 含义 | 行动含义 |
|---|---|---|
| 冷 | 市场不关心 | 只研究，不交易 |
| 温 | 主题开始发酵 | 可观察，可小仓试探 |
| 热 | 主题被持续奖励 | 可做波段，但必须有买点 |
| 过热 | 情绪拥挤，涨幅大 | 不追高，只等回调或极强确认 |

## 2. Growth Confirmation

问题：

基本面是否正在兑现叙事？

观察：

- 收入增长是否加速
- 毛利率是否改善
- 指引是否上修
- 管理层是否持续确认需求
- 订单、backlog、capex、产能是否支持增长

分级：

| 等级 | 含义 |
|---|---|
| Weak | 只有故事，没有财务确认 |
| Mixed | 有增长，但利润率或指引不足 |
| Strong | 收入、利润率、指引同时支持 |
| Excellent | 增长、利润率、订单、产能全部共振 |

## 3. Peer Valuation And Quality

问题：

为什么是这家公司，而不是同行？

观察：

- 是否比同行更纯
- 是否比同行更高质量
- 是否比同行更抗波动
- 是否比同行更便宜
- 是否比同行更强

同行对比不要只看价格强弱，也要看质量：

```text
高 beta 强，不一定更适合重仓。
财务质量强，不一定短线更快。
平台更宽，不一定市场马上奖励。
```

## 4. Price Location

问题：

当前位置是在合理买点，还是情绪末端？

观察：

- 是否刚突破
- 是否回踩承接
- 是否远离均线 / VWAP / 成本区
- 是否接近前高压力
- 是否连续多日加速
- 是否有成交量确认

分级：

| 位置 | 含义 | 行动 |
|---|---|---|
| Base / Pullback | 回调承接 | 最适合计划买点 |
| Early Breakout | 初段突破 | 可小仓，等确认加 |
| Mid Trend | 趋势中段 | 只做计划内回踩 |
| Extension | 情绪加速 | 不追高 |
| Blowoff Risk | 末端拥挤 | 减仓 / 不开新仓 |

## 5. Downside If Narrative Cools

问题：

如果 AI 情绪降温，这只票会回到哪里？

观察：

- 最近突破起点
- 20 日线 / 50 日线
- 前高平台
- 财报 gap 区
- 板块回撤时历史 beta
- 同行是否已经先跌

这一步的目的：

```text
不是预测会跌到哪里，
而是判断如果错了，亏损是否还能接受。
```

## 6. Swing Risk / Reward

问题：

当前位置还值得承担波段风险吗？

简化公式：

```text
expected_upside / acceptable_downside >= 2
```

如果做不到 2:1：

- 不追高
- 等回调
- 降低仓位
- 或只观察

## 温度计输出

最后输出四个结果：

```yaml
valuation_temperature:
entry_permission:
max_position:
required_invalidation:
```

## 行动映射

| 估值温度 | 条件 | 行动 |
|---|---|---|
| Green | 主题热、增长确认、价格在回调/初段、赔率好 | 可写 swing plan |
| Yellow | 主题热但价格偏高，或同行信号混合 | 只允许小仓或等回调 |
| Orange | 主题过热，价格扩展，赔率一般 | 不追高，只等强承接 |
| Red | 主题退潮或基本面不确认 | 不交易 / 降风险 |

## 仓位规则

仓位不是固定值，而是估值温度的结果。

| 状态 | 允许仓位 |
|---|---|
| Green | 可接近计划上限 |
| Yellow | 计划上限的 1/3 到 1/2 |
| Orange | 观察或极小仓 |
| Red | 不开仓 |

## 注意

这套方法不替代交易计划。

它只回答：

```text
这个位置是否值得写计划？
最多允许多大仓位？
是否只能等回调？
```

真正交易仍需要：

- trigger
- invalidation
- size
- add rule
- partial profit rule
- exit rule
