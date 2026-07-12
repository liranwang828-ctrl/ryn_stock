# yfinance Observation Stage 0 启动入口设计

## 目标

让用户在当前对话说“开始今日会话”后，可以在 observation 模式下复用 yfinance 完成只读市场准备，并停在 DAILY-1B 等待用户与高阶模型讨论。

该路径不得伪装成正式盘前 snapshot，不授予交易权限，也不得放松 trading 模式的 provider 闸门。

## 已验证现状

隔离试跑成功取得 QQQ、SPY、IWM、VIXY 的 yfinance 价格和前收盘价。现有系统正确将其判为 `formal_premarket_snapshot_missing`，状态停在 `DAILY-1A / waiting_data`。

缺口是：R3 已确认 observation 应有完整只读 DAILY 路径，但当前没有独立的 observation Stage 0 producer 和 coordinator intent。

## 采用方案

新增显式的 `start_stage0_observation`，不改变 `start_stage0` 和 `start_stage0_from_snapshot`：

1. 仅允许 `session_type = observation`；
2. 通过 yfinance 获取四个必需市场代理的历史/当前可用事实；
3. 写入 session-scoped observation snapshot 和 market-context packet；
4. 所有产物明确标注 `observation_only`、`no_trading_permission` 和数据时间；
5. coordinator 成功后进入 `STAGE0_READY`；
6. DAILY 状态进入 `DAILY-1B / waiting_user`，等待当前对话讨论和焦点确认；
7. Dashboard 只展示 manifest，不自行判断或推进。

## 未采用方案

- 让 yfinance 通过正式 snapshot 校验：会削弱 trading 数据门槛。
- 继续复用 `start_stage0_from_snapshot`：其语义是已存在正式 snapshot，混入 observation 会重新制造歧义。
- 让 Dashboard 直接调用 yfinance：会把事实生产和流程逻辑塞进展示层。

## 组件边界

### stock_team producer

新增小型 observation context producer，负责：

- 获取 QQQ、SPY、IWM、VIXY；
- 保存 `price`、`prev_close`、source、数据时间和缺口；
- 生成只读市场环境 markdown；
- 网络或任一必需代理缺失时失败，不写“已完成”状态。

producer 不生成焦点池、交易结论、心理解释或权限变化。

### coordinator

新增 `start_stage0_observation` 状态转换和 adapter 接线。仅 observation session 可执行；trading session 必须拒绝。

### investing-os / DAILY status

observation session 可将完整 yfinance observation snapshot 视为“本模式有效”，但 artifact issues 必须包含 `observation_only_no_trading_permission`。trading session 对同一文件仍判为非正式、不可推进。

## 数据与时间语义

- session 和文件名继续使用 ET `trading_date`；
- snapshot 必须记录 `as_of_et`；
- yfinance 行情不是 timestamp-proven premarket quote；
- 交易日盘前、盘中或非交易日演练必须分别标注 phase；
- 非交易日只能运行隔离 rehearsal，不在真实 runtime 创建未来 session。

## 用户交互

正式交易日的预期流程：

```text
用户：开始今日会话
→ 当前对话确认 observation 模式和 DAILY-0 事实
→ 系统创建当日 ET session
→ start_stage0_observation 获取 yfinance 事实并生成只读产物
→ Dashboard 显示 DAILY-1B / 等待讨论
→ 用户与高阶模型讨论市场环境并确认焦点
```

## 失败处理

- yfinance 网络失败或必需代理缺失：状态进入 `FAILED_TOOL`，保留具体缺口；
- 产物部分写入：使用临时文件后原子替换，避免假完成；
- trading session 调用该 intent：在任何 producer 写入前拒绝；
- 日期与 session 不匹配：拒绝；
- observation 产物不能用于 trading readiness。

## 验收标准

1. observation session 可从 DAY_INITIALIZED 到 STAGE0_READY；
2. 四个市场代理均有 price、prev_close、source 和数据时间；
3. DAILY 状态进入 DAILY-1B，且显示 observation-only 警告；
4. trading session 使用同类数据仍停在 DAILY-1A；
5. Dashboard 不新增 POST 或流程按钮；
6. 隔离 runtime E2E 通过，真实非交易日 runtime 不创建未来 session；
7. 试跑结果写入 handoff 并推送 Git。
