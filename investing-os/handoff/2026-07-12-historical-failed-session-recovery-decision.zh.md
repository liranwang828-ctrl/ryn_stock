# 2026-07-12 历史 FAILED_TOOL 会话恢复决策

## 当前事实

- 会话：`trading-2026-06-15`；
- 状态：`FAILED_TOOL`，有效恢复状态为 `DAY_INITIALIZED`；
- 失败动作：`start_stage0`；
- 最后错误：adapter return code 1；
- `retryable = false`；
- 已经在 2026-06-15 重试两次，均失败；
- 当前正式日历最近交易日为 2026-07-10，下一个交易日为 2026-07-13；
- 该会话的可解析产物均已被 Dashboard 降级为历史 `stale`。

## 判断

不得再次运行 2026-06-15 的盘前数据流程。它既不能成为当前交易日证据，也不应继续向用户显示 `retry_last_action`。

现有 H1 恢复契约要求 `FAILED_TOOL` 进入人工调查；当前状态机只允许 `retry_last_action`，没有“已确认过期后行政关闭”的显式动作。因此直接修改 JSON、删除 session 或伪装成正常复盘均不合适。

## 已完成修正

Dashboard/API 对历史失败会话现在返回：

- `session_kind = recovery_required`；
- `first_action = resolve_historical_session_in_conversation`；
- `next_step = resolve-historical-session`；
- readiness 保持 blocked；
- 页面明确提示不要重跑旧交易日盘前数据。

## 推荐方案

新增一个狭窄的显式动作 `abandon_failed_session`：

1. 只允许 `FAILED_TOOL` 且 `last_error.retryable == false`；
2. 必须有用户确认；
3. 写一份失败债务/保留产物清单；
4. 将会话转为可归档的终态并使用现有白名单 archiver；
5. 不将该动作解释为复盘完成，也不授予交易权限；
6. 完成后才能在正式交易日创建新 session。

这比手工改 JSON 更可追溯，也不会把旧失败伪装成成功。

## 尚需用户确认

是否采用上述方案，并在实现通过测试后，用它关闭 `trading-2026-06-15`。
