# DAILY Stage 0 From Snapshot 最小设计

日期：2026-07-02  
范围：仅解决 `DAILY-1 / Stage 0` 在“已有正式 pre-market snapshot”前提下的显式复用入口  
状态：design-only，未授权实现

## 1. 问题定义

隔离试跑表明：

- `python -m stock_team.coordinator_cli init-day --date 2026-07-02` 可以成功创建当日会话。
- 随后 `start_stage0` 失败，进入 `FAILED_TOOL`。
- 根因不是 `market-context` 无法消费 snapshot，而是 `ExistingCliAdapter` 对 `start_stage0` 固定执行：
  1. `premarket-snapshot`
  2. `market-context`
- 当 paid premarket rows 缺失时，第一步直接报错：
  `missing_required_paid_premarket_rows:QQQ,SPY,IWM,VIXY`

这导致一个明确的 contract gap：

- Dashboard / coordinator 已能识别 `formal_provider_snapshot`
- 但 orchestration 主链没有一个“显式使用已有正式 snapshot”的独立动作
- 结果是“已有正式 snapshot”与“必须重新采集 snapshot”两种语义被混在同一个 `start_stage0` 里

## 2. 设计目标

本轮只实现一个最小目标：

- 保持 `start_stage0` 现有语义不变
- 新增一个显式 intent：`start_stage0_from_snapshot`
- 它只表示一件事：在已有正式 snapshot 已经存在且被判定为正式可用时，跳过重新采集，直接生成 Stage 0 market context

不在本轮目标内：

- 改写 `start_stage0` 现有行为
- 支持手工 snapshot、模拟 snapshot 或普通 cache snapshot 进入主链
- 扩展 observation / Stage 1 / intraday / review 的新语义
- 改动 paid provider 要求本身

## 3. 方案选择

已选方案：B

- 保持 adapter 现状
- 新增显式 intent `start_stage0_from_snapshot`

选择原因：

- 语义最干净：实时采集链与已有正式输入复用链分离
- 不会偷偷改变 `start_stage0` 的旧含义
- 以后审计、测试、Dashboard 文案、故障定位都更清楚

## 4. 语义定义

### 4.1 `start_stage0`

保留原语义，不修改：

- 输入：当日日期、as-of、universe、可选 snapshot 输出路径等
- 行为：先执行 `premarket-snapshot`，再执行 `market-context`
- 适用场景：需要实时生成正式 snapshot 的标准盘前链路

### 4.2 `start_stage0_from_snapshot`

新增语义：

- 输入：当日日期、as-of、universe、`pre_market_snapshot`、输出 packet 路径
- 行为：不执行 `premarket-snapshot`；只执行 `market-context --pre-market-snapshot <path>`
- 适用场景：正式 snapshot 已经存在，且 coordinator / Dashboard 已判定为可正式复用

### 4.3 允许前提

`start_stage0_from_snapshot` 只能在以下条件同时满足时出现：

- session 当前处于 `DAY_INITIALIZED`，或处于 `FAILED_TOOL` 且 `resume_from_state == DAY_INITIALIZED`
- `pre_market_snapshot` 文件存在
- snapshot 被判定为 `formal_provider_snapshot`
- snapshot 对应的 `as_of_et` 与 Stage 0 `as_of` 时间窗口一致

### 4.4 明确禁止

以下情况不得使用 `start_stage0_from_snapshot`：

- 手工编辑的 snapshot
- `offline_fixture`
- stale cache / simulated / unknown source snapshot
- 缺少 formal provenance 判定的 snapshot

## 5. Dashboard / Coordinator 边界

### 5.1 Dashboard 责任

Dashboard 只负责：

- 识别 snapshot 是否为 `formal_provider_snapshot`
- 在 `formal_ready == true` 时暴露“from snapshot”动作
- 在 `formal_ready == false` 时继续建议标准 `start_stage0`

Dashboard 不负责：

- 自行重写 snapshot 内容
- 把非正式 snapshot 冒充成正式输入
- 改变 coordinator 的状态机语义

### 5.2 Coordinator 责任

Coordinator 负责：

- 接受 `start_stage0_from_snapshot`
- 依据 intent 进入与 `start_stage0` 相同的 Stage 0 成功态
- 失败时像其他 action 一样进入 `FAILED_TOOL`

## 6. 代码影响面

本设计预期影响以下文件：

- `stock_team/orchestration/models.py`
  - 新增 canonical intent `start_stage0_from_snapshot`
- `stock_team/orchestration/transitions.py`
  - 允许 `DAY_INITIALIZED -> start_stage0_from_snapshot -> STAGE0_RUNNING/STAGE0_READY`
  - 必要时允许 `FAILED_TOOL` 通过 retry 复用该 intent 的错误恢复
- `stock_team/orchestration/adapters.py`
  - 为新 intent 建立仅执行 `market-context` 的命令构造
- `stock_team/server/dashboard_server.py`
  - 在 `formal_ready == true` 时生成该 action
  - `first_action` / `current_task` / action endpoint 文案和默认动作要能区分两条路径
- `stock_team/tests/unit/orchestration/test_adapters.py`
- `stock_team/tests/unit/orchestration/test_coordinator.py`
- `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`
- 视实际需要补一条 integration / E2E

## 7. 最小验收标准

满足以下几点即可视为本设计实现完成：

1. 现有 `start_stage0` 测试全部保持原行为不变
2. 新增测试证明 `start_stage0_from_snapshot` 不会调用 `premarket-snapshot`
3. 新增测试证明它会调用 `market-context --pre-market-snapshot <formal snapshot>`
4. Dashboard 在 `formal_ready == true` 时，推荐该新动作
5. 使用正式 snapshot 的隔离试跑可以从 `DAY_INITIALIZED` 推进到 `STAGE0_READY`
6. 非正式 snapshot 不能走这条动作

## 8. 风险与约束

主要风险不是实现复杂度，而是语义漂移：

- 如果 formal 判定过宽，会把不该进入主链的 snapshot 放进来
- 如果 Dashboard 与 adapter 对“formal”的判定不一致，会再次出现 UI 说能走、主链实际不能走

因此本轮应坚持：

- formal 判定单一来源
- 新 intent 只服务正式 snapshot
- 不顺手扩展其他 source_kind

## 9. 对低阶模型的任务边界

低阶模型只可在本设计边界内工作：

- 允许：新增 intent、接线、补测试、修 Dashboard 默认动作
- 不允许：改 `start_stage0` 语义、扩大 snapshot 来源、重构整个 Stage 0 数据链、顺手改 DAILY 其他阶段

## 10. 实施前结论

本设计的核心不是“让 Stage 0 更宽松”，而是“把两条本来不同的 Stage 0 路径显式拆开”：

- `start_stage0` = 采集 + 生成
- `start_stage0_from_snapshot` = 复用正式输入 + 生成

只有这样，后续 DAILY + Dashboard 联合流程才具备稳定、可审计、可恢复的动作语义。
