# 2026-06-04 Daily Review

## Date

2026-06-04

## Source

User-provided ChatGPT structured review, absorbed into `investing-os`.

## Market Context

盘前已经意识到市场环境偏弱，因此对整体市场风险有心理准备。

长期核心持仓：

- MSFT
- NVDA
- GOOGL

波段持仓：

- COHR
- ORCL
- INTC

开盘阶段，主要持仓没有造成明显情绪压力。长期持仓和 AI 基础设施趋势持仓的 thesis 没有因为单日市场偏弱而被证伪。

## Decisions

### Long-Term Holdings

MSFT、NVDA、GOOGL 按长期配置逻辑继续持有。

执行质量：

- 符合计划
- 无明显情绪偏离
- 能接受正常波动

### SNXX

实际过程：

```text
VWAP 突破
|
追高买入
|
被套
|
加仓
|
再次下跌
|
持续盯盘
|
止损离场
```

交易性质发生漂移：

```text
机会交易
|
成本管理
|
解套交易
```

SNXX 在账户资金占比不算特别大，但占据了过高注意力，并持续影响到收盘。

### COHR / ORCL / INTC

尾盘卖出并锁定部分利润。

需要继续复查：

- 这是理性风险管理，还是 SNXX 情绪外溢后的联动决策？
- 卖出是否意味着 thesis 变化？
- 是否只是降低夜盘和次日回撤风险？

## Emotions

### 开盘前

- 接受波动
- 接受市场风险
- 无明显 FOMO

### SNXX 阶段

- FOMO：担心错过 VWAP 突破机会
- Loss aversion：不愿接受初始损失
- Attention capture：SNXX 占据过多注意力
- Emotional spillover：SNXX 情绪可能影响其他持仓决策

## Errors

- 没有明确短线 thesis 就交易
- VWAP 突破被误当成完整 thesis
- 被套后加仓依据来自价格下跌，而不是 thesis 强化
- 没有预设加仓规则
- 单一低确信度短线交易占用了过多认知资源
- 持续盯盘影响睡眠

## Cognitive Update

本次复盘最大的发现不是 SNXX 的亏损。

关键发现：

长期投资体系能够帮助用户在市场下跌时保持稳定。

但短线交易会迅速消耗认知资源，并可能将情绪扩散到其他本来不需要处理的仓位。

未来需要管理的不只是资金仓位。

还要管理认知仓位。

## Discipline Check

通过：

- 长期核心持仓未因单日波动被情绪化处理
- 尾盘 SNXX 最终止损，符合风险控制优先原则

违反或部分违反：

- 无计划不交易
- 信号不是命令
- 不做情绪化交易
- 不让单一标的绑架情绪
- 短线交易前未定义 thesis、risk、falsification、add rule

## Risk

### Position Risk

SNXX 加仓扩大了风险。

### Emotional Risk

单一交易影响整体账户状态。

### Attention Risk

认知资源被短线交易大量消耗。

### Sleep Risk

熬夜影响次日判断质量。

## Falsification

### SNXX

没有明确 thesis，因此没有明确证伪条件。

未来短线交易必须提前定义：

- thesis
- trigger
- risk
- falsification
- add rule

### COHR / ORCL / INTC

暂无证据证明长期或波段逻辑被破坏。

卖出不等于 thesis 被证伪。

## System Update

新增原则：

- `wiki/principles/PRIN-006-cognitive-attention-budget.md`

新增检查表：

- `system/checks/short-term-trade-checklist.md`

短线交易前必须回答：

1. Thesis 是什么？
2. Trigger 是什么？
3. 最大亏损是多少？
4. 失效条件是什么？
5. 加仓条件是什么？
6. 如果被套，是否仍允许加仓？

Agent / AI 提醒规则：

如果持续盯单超过 30 分钟，必须暂停并重新记录：

- Fact
- Thesis
- Risk

## Follow-Up

- 回看 SNXX 全部成交记录。
- 统计最近 20 笔短线交易中的计划外加仓行为。
- 评估 SNXX 是否影响 COHR、ORCL、INTC 的卖出决策。
- 在未来复盘中区分 thesis 证伪、风险管理和情绪外溢。

## One Sentence Lesson

低确信度短线交易不得获得高于核心仓位的注意力。

