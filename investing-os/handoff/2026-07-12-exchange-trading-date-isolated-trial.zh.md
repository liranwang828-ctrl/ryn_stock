# 2026-07-12 美股交易日与 Dashboard 隔离验收

## 结论

交易日归属、旧会话识别和旧产物降级已在隔离测试与本地只读 API 中验证。当前为美东周日，系统没有创建周一正式会话；旧的 `trading-2026-06-15` 被标为 `recovery_required`，其结构有效产物显示为 `stale`，不再显示为当日 fresh。

本记录不代表真实 DAILY-0/1 已执行，也不授予交易权限。

## 固定验收场景

集成测试建立：

- 已归档旧 session：`trading-2026-07-10`，包含旧 Stage 0 产物；
- 当前 open session：`trading-2026-07-13`，不包含任何产物；
- 当前交易日上下文：`2026-07-13 ET`。

结果：Dashboard 会话选择器选择当前 session；DAILY 状态停在 `DAILY-1A / waiting_data`；旧 session 产物没有进入当前 artifact ledger。

## 实际本地 API 检查

检查时间：2026-07-12 北京时间（美东周日）。

返回事实：

- `calendar_status = verified`；
- `trading_date = null`；
- `last_trading_date = 2026-07-10`；
- `next_trading_date = 2026-07-13`；
- `session_kind = recovery_required`；
- selected session 为 `trading-2026-06-15`；
- `stage0_universe`、`stage0_market_context`、`stage1_plan_evidence` 均为 `valid + stale`。

因此，旧产物仍可供恢复和借鉴，但不能计入当前交易日 readiness。

## 验证命令

```powershell
python -m pytest stock_team/tests/unit/core/test_market_clock.py stock_team/tests/unit/orchestration/test_daily_status.py stock_team/tests/unit/orchestration/test_store.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py stock_team/tests/integration/test_daily_e2e.py -q
```

最终测试数以本轮最终核验输出为准。

## 运行环境修正

- 已安装并写入依赖：`exchange-calendars>=4.5`；
- 修正了该库在非交易日必须使用 `date_to_session(direction=...)` 的接口差异；
- 清理了多个残留 Dashboard server，只保留一个监听 8080 的当前代码进程。

## 未完成项

- in-app browser 自动控制受用户级 Node ESM 配置冲突阻断，未完成自动截图或 DOM 视觉检查；
- 页面服务和 `/api/coordinator-summary` 已返回 200，用户刷新页面即可进行人工视觉确认；
- 当前是非交易日，因此尚未进行真实盘前数据获取；下一次正式试跑应在交易日以当前 ET `trading_date` 初始化 DAILY-0/1。
