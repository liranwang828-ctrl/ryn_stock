# yfinance 隔离 DAILY 数据试跑

日期：2026-07-11（周六）  
模式：observation / fallback 验证  
结论：yfinance 可获取事实数据，但不得据此完成正式 Stage 0 或正式盘中确认。

## 1. 直接 yfinance 连通性

单标的 `COHR`、`period=5d`、`interval=1d` 成功返回 5 行。

最近两日：

| 日期 | 收盘 | 最高 | 最低 | 开盘 | 成交量 |
|---|---:|---:|---:|---:|---:|
| 2026-07-09 | 327.24 | 340.73 | 326.27 | 335.14 | 4,158,600 |
| 2026-07-10 | 324.50 | 330.15 | 315.19 | 321.40 | 4,025,800 |

## 2. 现有 `premarket --refresh` 试跑

输入：canonical `pre-market-decision-sheet.json` 中的单一示例标的 COHR。

结果：

- `core/premarket.py` 已成功生成 `premarket_analysis_2026-07-11.json`；
- 数据包含 COHR 价格、新闻、ATR、月度上下文和 options indicators；
- 外层 `stock_team.cli premarket` 在 124 秒超时，没有生成最终 Stage 1 evidence packet；
- 命令执行过程会改写 `config/market_regime.json` 和 `config/positions_mode.json`，不满足本轮“隔离试跑”要求；这些副作用已清理，不提交。

这证明旧 premarket producer 能取得 yfinance 数据，但完整命令仍有长耗时/阻塞点和正式配置写入副作用，不能直接接入对话驱动 DAILY。

## 3. 正式 Stage 0 闸门

命令：

```text
python -m stock_team.cli market-context --date 2026-07-11 --as-of 2026-07-11T09:20:00-04:00 --universe investing-os/templates/pre-market-universe.json ...
```

结果：立即拒绝，错误为：

```text
missing_pre_market_data: live Stage 0 requires an explicit --pre-market-snapshot captured before 09:30 ET
```

判断：符合已批准契约。yfinance 日线/当前报价不得伪装为 timestamp-proven premarket snapshot。

## 4. `intraday-snapshot` fallback 试跑

`COHR` 数据获取成功：

- current price：324.50
- VWAP：323.28
- VWAP deviation：+0.38%
- volume ratio：0.7x
- data sources：yfinance + local cache
- 边界：factual monitoring only，无 buy/sell、心理解释、最终 thesis 或权限变更

但输出在周六仍写出：

- `target_window: 09:30-16:00 ET`
- `in_window: true`
- packet `status: verified`

因此发现一个 verified gap：旧 intraday window 只依据 ET 时钟，未校验交易日/周末。该结果只能用于 observation 数据链试跑，不能完成正式 DAILY-2/3 事实确认。

## 5. 对当前 DAILY 的含义

- yfinance fallback 连通，可用于只读观察和分析准备；
- manifest 应保持 `waiting_data` + `observation_available=true`；
- 正式 Stage 0 仍等待 provider-backed premarket snapshot；
- 在真实交易日试跑前，需要先让 intraday producer 校验交易日，并隔离 `premarket --refresh` 对正式配置的写入；
- 本轮不修改上述旧 producer 逻辑，只记录真实试跑结果。
