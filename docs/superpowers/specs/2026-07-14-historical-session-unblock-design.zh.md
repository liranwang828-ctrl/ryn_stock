# 历史会话阻塞今日会话解除设计（2026-07-14）

## 背景

当前 `operating-console` 的 today 入口仍被上一交易日会话 `observation-2026-07-13` 阻塞。`/api/coordinator-summary` 返回：

- `session_kind = recovery_required`
- `first_action = resolve_historical_session_in_conversation`
- `entry_state.missing_items = historical session must be resolved before a new formal trading session`

与此同时，today 页面又投影了上一交易日的 stale artifacts，造成“今天似乎已有产物，但又无法开始正式流程”的混乱体验。

本次只做一个最小修复：严格遵守既有 DAILY 契约，在不伪造 2026-07-14 盘前产物的前提下，先解除“昨日历史会话阻塞今日正式会话”这一条主链阻塞。

## 目标

1. 正确识别历史会话不能被当作今日会话继续执行。
2. 为历史会话提供正式的处理完成判定，使其不再永久阻塞今日会话。
3. 历史会话处理完成后，today 入口自动回到今日 `DAILY-0` / `init-day`。
4. Dashboard/API 不再把上一交易日产物误投影为“今天已就绪”。

## 非目标

1. 不补造 2026-07-14 的盘前快照、市场环境包或 Stage 1 计划。
2. 不修改 DAILY 契约语义，不引入“强制跳过昨天”的旁路按钮。
3. 不顺手重构整个 coordinator/session 模型。
4. 不处理价格源准确性问题；该问题后续在正式今日会话中单独处理。

## 现状与根因

### 现象

- today 页面当前时间上下文已是 2026-07-14 regular session。
- session 仍指向 2026-07-13 的 `observation-2026-07-13`。
- `daily_status.artifacts` 列出了 2026-07-13 的 stage0/stage1/trading plan/intraday guidance，并统一带有 `trading_date_mismatch`。
- `entry_state` 与 `daily_status` 同时存在，但表达不统一：前者强调“必须先解决历史会话”，后者仍在展示 stale artifact 细节。

### 根因判断

根因不是单一数据错误，而是“跨日恢复判定”和“today 投影逻辑”没有彻底对齐：

1. coordinator 已能识别历史会话需要恢复；
2. 但 today summary 仍继续携带上一交易日 artifact 投影；
3. 历史会话处理完成后的“今日可重新开始”解锁路径不够清晰或未贯通到公开入口。

因此本次修复应同时覆盖：

- 历史会话处理完成判定；
- summary/entry_state 的解锁逻辑；
- daily status 对 stale 历史 artifact 的 today 投影抑制。

## 方案比较

### 方案 A（推荐）：严格路由修复 + today 投影收敛

保留既有“历史会话必须先处理”的契约；补齐处理完成后的解锁逻辑，并在 today 页只显示阻塞而不把历史 artifact 伪装成今日 readiness。

优点：

- 与既有 DAILY 契约一致；
- 改动面最小；
- 能在今天先恢复系统可用性。

缺点：

- 不主动简化现有会话模型；
- 仍保留历史会话处理这一显式步骤。

### 方案 B：跨日自动切断

只要 `trading_date != today` 就让旧会话不再阻塞。

优点：

- 用户表面体验最顺。

缺点：

- 破坏既有跨日恢复/复盘语义；
- 容易隐藏未完成收尾。

### 方案 C：新增强制开始今日会话 override

增加一个新 intent 或按钮显式跳过历史阻塞。

优点：

- 实现很快。

缺点：

- 最容易污染契约；
- 未来会被滥用，削弱正式主链。

结论：采用方案 A。

## 设计

### 1. 会话层语义

当活跃会话的 `trading_date` 早于当前交易日时，该会话被视为“历史会话”，不能直接作为 today formal session 的继续。

历史会话在公开入口只允许两类结果：

1. 被正式关闭/归档，使其不再阻塞今日；
2. 被导向既有 review/freeze/repair 路径，直到满足“不再阻塞今日”的完成条件。

本次不新增新的业务状态名；优先复用现有 terminal / archived / reviewed 语义，只补齐 today 是否继续阻塞的判断条件。

### 2. 协调器/summary 解锁逻辑

`coordinator-summary` 在存在历史会话且未处理完成时：

- `session_kind = recovery_required`
- `first_action = resolve_historical_session_in_conversation`
- `entry_state.readiness = blocked`

一旦历史会话处理完成：

- 不再返回 `recovery_required`
- today 的首动作恢复为新交易日初始化（`init-day` / `start daily-0` 一类既有入口）
- summary 中的 `session.session_id` 应对应今日新会话，或在尚未初始化时显式为空而不是继续指向昨天

### 3. daily status / dashboard 投影

today 页在“历史会话阻塞”期间，只显示阻塞本身，不把上一交易日 artifacts 视为 today readiness 的一部分。

具体要求：

1. 历史 artifact 可以作为 diagnostics / recovery context 保留；
2. 但 `today` 视图下不应继续出现“present=true, valid=true”给用户造成“今天已生成”的误解；
3. 如果 artifact 的 `trading_date != today trading_date`，则 today readiness 计算应忽略它，只保留一条明确 blocker。

### 4. 运行时边界

修复只解除阻塞，不补做任何 today 盘前产物。

也就是说，历史会话关闭后：

- today 会回到 `DAILY-0` / `DAY_INITIALIZED` 之前的正式起点；
- 后续是否进入 `trading` / `observation`，以及如何获取 today 数据，仍按正式会话重新执行。

## 受影响组件

### 核心代码

- `stock_team/orchestration/coordinator.py`
- `stock_team/orchestration/daily_status.py`
- `stock_team/server/dashboard_server.py`

### 可能涉及

- `stock_team/orchestration/models.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/tests/unit/orchestration/test_coordinator.py`
- `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`
- `stock_team/tests/unit/orchestration/test_coordinator_cli.py`
- `stock_team/tests/integration/test_daily_e2e.py`

## 测试策略

采用 TDD，只为以下 4 个行为补测试：

1. 有历史会话时，today summary 返回阻塞且首动作为 `resolve_historical_session_in_conversation`。
2. 历史会话被正式处理完成后，today summary 不再阻塞，并回到今日初始化入口。
3. today daily status 不再把 `trading_date_mismatch` 的历史 artifacts 当作 today 已就绪产物。
4. dashboard today 页/API 对 blocker 与 readiness 的表达一致。

## 验收标准

1. 历史会话存在且未完成时，today 被阻塞，提示正确。
2. 历史会话处理完成后，today 阻塞消失。
3. 新启动的今天会话为 `2026-07-14`，不复用 `2026-07-13`。
4. Dashboard today 页与 `/api/coordinator-summary` 表达一致。
5. 不产生任何伪造的 2026-07-14 盘前 artifact。

## 风险与控制

### 风险 1：误放开 today，绕过历史会话处理

控制：只接受已有 terminal/reviewed/archived 语义作为“处理完成”，不新增宽松旁路。

### 风险 2：today 页信息骤减，影响诊断

控制：历史 artifact 保留在 diagnostics / recovery context，不在 today readiness 主视图使用。

### 风险 3：修复 summary 后，dashboard 仍依赖旧字段

控制：用 focused unit test 同时覆盖 summary payload 与 today entry projection。

## 实施顺序

1. 先查明当前“处理完成判定”到底落在哪个函数/字段。
2. 先写 failing tests，锁定 blocker 清除与 today 投影抑制。
3. 最小实现解锁逻辑。
4. 跑 unit + integration 验证。
5. 最后再手动刷新本地 dashboard 验证 today 页面。
