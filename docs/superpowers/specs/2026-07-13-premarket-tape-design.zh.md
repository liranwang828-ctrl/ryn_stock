# Premarket Tape 设计

日期：2026-07-13  
状态：待用户书面设计复核  
适用范围：`stock_team` 盘前事实获取、`investing-os` DAILY 盘前分析、只读 Dashboard 展示

## 1. 问题

现有 observation Stage 0 的标准产物主要使用最近一个交易日的日线收盘。它适合做历史基准，却不足以代表当前盘前环境。

本次盘前试跑又暴露两个问题：

1. ETF盘前报价与期货方向可能冲突，例如QQQ盘前约-1.09%，同时NQ期货约+0.11%；
2. yfinance可能返回零成交量、延迟时间戳或不同含义的`previous_close`，系统不能把所有数值当成同等级事实。

因此需要新增独立的盘前市场磁带，而不是覆盖或重新解释原Stage 0日线基准。

## 2. 目标

每天美股盘前生成一份带时间戳、来源、基准语义和数据质量的跨资产快照，至少回答：

- 指数期货当前方向；
- QQQ/SPY等ETF盘前报价；
- BTC等24小时风险资产状态；
- 原油、黄金、美元、利率和VIX状态；
- 期货与ETF是否给出一致解释；
- 哪些数据可用于环境讨论，哪些必须降级或忽略。

本功能只提供事实与数据质量，不生成交易方向、仓位、订单或交易许可。

## 3. 不做的内容

- 不替换正式券商账户事实；
- 不把yfinance升级为正式交易级行情；
- 不在Dashboard内计算交易结论；
- 不自动推进焦点池确认或Stage 1；
- 不在本轮接入完整IBKR streaming；
- 不扩展到期权链、新闻情绪或复杂技术指标。

## 4. 方案选择

采用独立产物方案：

```text
Stage 0 日线基准
+
Premarket Tape 当前盘前层
```

未采用直接扩展Stage 0 snapshot的原因：会混淆最近收盘、盘前ETF、24小时资产与期货结算基准，并增加现有契约回归风险。

未采用完整多供应商实时总线的原因：当前目标是先让每日流程可用；IBKR/Polygon多源仲裁可作为后续增强。

## 5. 标准资产集合

### 指数期货

- `NQ=F`：Nasdaq 100 futures
- `ES=F`：S&P 500 futures
- `YM=F`：Dow futures
- `RTY=F`：Russell 2000 futures

### ETF盘前

- `QQQ`
- `SPY`
- `IWM`
- `SMH`
- `SOXX`

### 24小时与宏观代理

- `BTC-USD`
- `CL=F`：WTI
- `GC=F`：Gold
- `DX-Y.NYB`：美元指数
- `ZN=F`：10年期国债期货代理
- `^VIX`

### 当日焦点池

从Stage 0 universe读取，不在producer中硬编码。例如当前池：AMAT、TSM、AMD、MU、COHR，以及SNPS、MSFT、CIEN、LITE、ORCL观察池。

## 6. 数据模型

产物路径：

`investing-os/system/runtime/inputs/{session_id}-premarket-tape.json`

每条记录至少包含：

```json
{
  "symbol": "QQQ",
  "asset_class": "etf_premarket",
  "last": 717.62,
  "comparison_value": 725.51,
  "comparison_kind": "prior_regular_close",
  "change_pct": -1.09,
  "as_of_et": "2026-07-13T08:21:46-04:00",
  "source": "yfinance_1m_prepost",
  "freshness": "fresh",
  "quality": "degraded",
  "issues": ["zero_reported_volume"]
}
```

顶层至少包含：

- `session_id`
- `trading_date`
- `generated_at_et`
- `evidence_level: observation_only`
- `permission: no_trading_permission`
- `records`
- `cross_asset_checks`
- `missing_symbols`
- `warnings`

## 7. 基准语义

不同资产不能共用模糊的`previous_close`：

- ETF：`prior_regular_close`
- 期货：`prior_futures_settlement_or_provider_previous_close`
- BTC：`prior_24h_reference`或明确的`provider_previous_close`
- VIX：`prior_regular_close`

任何不能确认语义的值必须：

- 保留原始字段；
- 标记`comparison_kind: provider_defined_unknown`；
- 不参与跨资产一致性结论。

## 8. Freshness与质量

以美东时间计算：

- `fresh`：盘前连续市场数据不超过10分钟；
- `aging`：超过10分钟且不超过30分钟；
- `stale`：超过30分钟；
- `missing`：无时间戳或无有效值。

质量规则：

- 有有效值、时间戳新鲜且基准明确：`usable_observation`；
- 零成交量但存在盘前价格：`degraded`；
- 时间戳陈旧、基准不明或跨日：`stale_unverified`；
- 不得用`fast_info.last_price`冒充ETF盘前价格；ETF盘前必须取pre/post intraday最后有效bar；
- BTC时间戳陈旧时不得用于风险偏好结论。

## 9. 跨资产一致性检查

系统只产生解释状态，不产生交易结论。

### QQQ与NQ

- 同方向且差异在容忍范围：`aligned`
- 方向相反或差异明显：`conflicted`
- 任一数据降级：`insufficient_quality`

### SPY与ES、IWM与RTY

使用相同规则。

### 油价、美元、债券与VIX

只生成组合描述，例如：

- `volatility_up_with_equity_futures_flat`
- `oil_up_rates_pressure`
- `mixed_macro_tape`

不得输出“买入/卖出”或直接把价格变化推断为Reality变化。

初始容忍范围采用配置常量，不写入Dashboard。第一版建议ETF与对应期货变化差的绝对值超过0.50个百分点，或方向相反且双方变化绝对值均超过0.20个百分点时标记冲突。

## 10. 数据流

```text
DAILY-0确认
-> Stage 0 universe
-> 既有observation market context（日线基准）
-> Premarket Tape producer（当前盘前层）
-> 数据质量与跨资产检查
-> Stage 0讨论
-> Dashboard只读展示
```

Premarket Tape失败不应伪造Stage 0完成，也不应删除已有日线基准。Manifest显示独立缺失或降级状态，由当前对话决定是否继续观察。

## 11. Dashboard展示

Dashboard只展示：

- 最后更新时间；
- 期货、ETF、BTC、宏观四组精简卡片；
- freshness和数据源；
- 跨资产状态：一致、冲突或证据不足；
- 一句固定提示：结论在当前对话生成。

Dashboard不计算交易权限、不决定焦点池、不触发流程动作。

## 12. 错误处理

- 单个symbol失败不阻止其他记录落盘；
- 必需核心集合为NQ、ES、QQQ、SPY、VIX；缺少任一核心项时整体标记`partial`；
- 所有核心项均缺失时producer失败且不发布部分正式文件；
- 非核心资产缺失写入`missing_symbols`；
- 使用临时文件后原子替换，防止Dashboard读取半文件；
- provider异常、时间戳异常和比较基准异常分别记录，不能合并成通用错误。

## 13. 测试要求

至少覆盖：

1. ETF使用pre/post最后bar而不是fast_info last；
2. 期货、ETF和BTC基准语义不同；
3. fresh/aging/stale边界；
4. 零成交量降级但不丢弃价格；
5. QQQ与NQ方向冲突；
6. BTC陈旧不参与风险偏好结论；
7. 单个非核心symbol失败仍生成partial产物；
8. 核心集合全部失败时不发布部分文件；
9. Dashboard只读解析，不新增POST或流程判断；
10. 现有observation Stage 0和trading Stage 0行为保持不变。

## 14. 验收标准

在真实美股盘前运行后：

- 用户能同时看到QQQ盘前与NQ期货；
- 每个值都有美东时间戳、来源、基准语义和freshness；
- QQQ/NQ冲突会被显式标记，而不是任取一个解释市场；
- 陈旧BTC不会显示为有效风险信号；
- 原Stage 0日线基准继续存在；
- DAILY仍停在对话确认节点，不因Tape生成自动获得交易权限。

