# 2026-07-12 yfinance Observation Stage 0 隔离演练

## 结论

独立 observation Stage 0 路径已跑通：真实 yfinance → observation producer → adapter → coordinator → DAILY manifest，最终停在 `DAILY-1B / waiting_user`，等待用户与高阶模型讨论市场环境。

该结论只表示只读 observation 流程可用，不表示正式盘前 snapshot 已取得，不授予交易权限。

## 隔离条件

- 临时 runtime，退出后自动删除；
- 固定已发生交易日：2026-07-10 ET；
- session：`observation-2026-07-10`；
- DAILY-0：observation、账户事实 `stale_unverified`；
- 没有写入真实 `investing-os/system/runtime/sessions/`；
- 没有创建 2026-07-13 session。

## 真实 yfinance 结果

| Symbol | Latest daily close | Previous daily close | Source | Data as of |
|---|---:|---:|---|---|
| QQQ | 725.51 | 723.28 | yfinance_daily_history | 2026-07-10 ET |
| SPY | 754.95 | 751.71 | yfinance_daily_history | 2026-07-10 ET |
| IWM | 295.99 | 297.24 | yfinance_daily_history | 2026-07-10 ET |
| VIXY | 20.34 | 20.81 | yfinance_daily_history | 2026-07-10 ET |

这些值是 daily history，不是 timestamp-proven premarket quotes。

## 流程结果

- coordinator state：`STAGE0_READY`；
- DAILY current step：`DAILY-1B`；
- overall status：`waiting_user`；
- observation available：`true`；
- snapshot issue：`observation_only_no_trading_permission`；
- trading session 使用相同 evidence level 时仍判为非正式并停在 DAILY-1A。

## 新增边界

- intent：`start_stage0_observation`；
- 只允许 observation session；
- trading session 在 producer 写文件前拒绝；
- producer 仅写事实 snapshot 和只读 market-context markdown；
- Dashboard 不增加 POST 或流程按钮；
- 正式 `start_stage0` / `start_stage0_from_snapshot` 规则未改变。

## 下一次正式使用

在真实交易日由当前对话：

1. 确认 DAILY-0 observation 模式、账户事实和分析范围；
2. 创建当日 ET observation session；
3. 执行 `start_stage0_observation`；
4. Dashboard 显示 DAILY-1B；
5. 用户与高阶模型讨论市场环境后再确认焦点池。

正式 trading 模式仍必须等待 provider-backed premarket snapshot。
