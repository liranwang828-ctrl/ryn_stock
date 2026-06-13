# 盘后复盘流程待办（2026-06-01）

## P0：卖出/清仓动作需要独立评分语义

当前 `postmarket_trade_review.py` 的执行质量评分主要按买入/入场视角设计，导致 `SELL_CLEAR`、`SELL_PARTIAL` 等卖出动作也可能显示为“次优入场”“追涨/点位过差”等措辞。数值仍可辅助判断成交价相对日内区间的位置，但语言会误导复盘结论。

后续优化方向：

- 为 `BUY`、`BUY_ADD`、`SELL_CLEAR`、`SELL_PARTIAL` 分开定义评分语义。
- 卖出动作应输出“止盈质量 / 止损纪律 / 风险释放质量 / 是否卖飞”一类结论。
- 交易复盘 JSON 建议增加 `trade_intent` 字段，例如 `entry`、`add`、`take_profit`、`stop_loss`、`risk_reduce`、`cash_raise`。
- HTML 报告中买入和卖出分开展示，避免把卖出复盘混进入场质量排名。

## P1：盘后沙盒必须优先使用真实成交记录

已修正 `postmarket_data_collector.py`：当 `knowledge/trading_history.jsonl` 中存在当日 `manual_user_report` 记录时，盘后沙盒优先使用用户口述/确认的真实成交，不再从持仓快照差异反推。

后续需要补充测试：

- 当存在真实成交记录时，不应混入快照反推交易。
- 当没有真实成交记录时，才允许回退到快照差异推断。
- 对 `price_approximate`、`price_inferred` 的成交，报告中需要显式标注数据置信度。

## P1：高质量行情源默认优先级

已修正 `postmarket_trade_review.py`：日内交易点评默认先使用 Polygon/Massive 1-minute aggregates，失败后再回退到 yfinance。

后续优化方向：

- 统一抽象 `market_data_provider`，让盘前、盘中、盘后三套流程都遵循同一优先级。
- 在报告中写入 `data_source`，方便复盘时知道每笔交易来自 Polygon 还是 yfinance fallback。
- 为外部 API 超时增加更短的单请求 timeout 和清晰错误提示。

## P0：盘后复盘必须先拉行情再评价交易

盘后复盘不能只根据成交记录、主观叙述或大师输出直接下结论。每次评价买点/卖点前，必须先拉取或加载：

- 交易标的当日 1-minute K 线。
- 当日 open/high/low/close/VWAP。
- 最近 5 日、10 日 K 线表现。
- QQQ 同日和近期表现。
- 相关板块 ETF 或同业对照，例如 IGV/HACK/SOXX/SMH/XLC，或 AAOI/LITE/COHR 这类 peer basket。

自由交易日没有盘前计划时，改用以下标准评价：

- 成交价相对日内高低点的位置。
- 成交价相对 VWAP 的位置。
- 成交价相对收盘价的结果。
- 标的相对 QQQ/板块/同业是否强势。
- 若缺少精确成交时间，必须说明只能做价格位置评价，不能做分钟级时点评价。

这条是 P0 流程纪律：**先行情，后复盘；先数据，后大师。**
