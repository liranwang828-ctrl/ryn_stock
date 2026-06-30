# DAILY 契约代码实施计划

> 依据：DAILY-CONTRACT v4 approved (`e0d4338`)
> 范围：C1–C14 候选修正 → 可独立派发的 TDD 任务
> 规则：每个任务独立 commit，先写测试再做最小实现，不越权修改

---

## 0. 执行规则

### 0.1 任务分类

- `verified_bug`：行为与已确认契约相反，需修复 + 回归测试
- `missing_capability`：契约要求但代码不存在，需 TDD 实现
- `design_decision`：高阶已定案，按决定方向实施
- `boundary_conflict`：违反脑-肌边界，需拆开归属

### 0.2 低阶模型共同限制

**可以：**
- 读取任务列出的文件和相关测试
- 写测试 → 最小实现 → 运行测试 → 独立 commit push
- 创建任务唯一的新文件

**不得：**
- 修改脑-肌边界（下单权限、IBKR 地位、investing-os 认知域）
- 重新解释已批准的 DAILY 契约条款
- 顺手修复发现的其他问题
- 使用真实账户或真实交易运行

### 0.3 验收标准

每个任务完成后：局部测试通过 + 相关审计测试不退化 + 产物路径符合 7.6 规范

---

## 第一批：独立并行（无共享文件冲突）

### Task I-1: Session Router — C1

**分类：** `missing_capability`
**文件：** `coordinator_cli.py`、`models.py`、`orchestration/store.py`
**测试：** `tests/unit/orchestration/test_coordinator_cli.py`、`tests/unit/orchestration/test_models.py`

**需求（契约 1.DAILY-0）：**
- `init-day` 添加 `--session-type` 参数，支持全部 6 种 SESSION_TYPES
- trading/observation → 进入 DAILY-1
- research/review/maintenance → 旁路到对应工作流
- 默认值保持 `trading`（向后兼容）

**TDD 步骤：**
1. 写测试：test_init_day_with_session_type、test_init_day_rejects_invalid_session_type
2. 实现：在 coordinator_cli.py init-day 添加 --session-type 参数
3. 回归：现有 11 tests 不退化

**产物：** 修改 coordinator_cli.py、models.py，更新测试文件

---

### Task I-2: Focus Pool Gate — C8

**分类：** `verified_bug`
**文件：** `cli.py`（`handle_premarket()` L1159 附近）
**测试：** `tests/unit/core/test_cli.py`

**需求（契约 2.DAILY-1 失败与恢复）：**
- decision sheet 缺失时阻止 Step 4 执行，不得静默回退到 watchlist 全量
- 输出明确错误信息：缺少焦点池确认，请先完成 DAILY-1 Step 3

**TDD 步骤：**
1. 写测试：test_premarket_rejects_missing_decision_sheet
2. 实现：在 handle_premarket() 中 decision sheet 缺失时 raise/return 错误
3. 回归：现有 premarket 测试不退化

---

### Task I-3: Remove post_open_adj — C9

**分类：** `design_decision`（契约 7.7：选项 A — 移除）
**文件：** `data_ingest/intraday_snapshot.py`（`get_effective_nodes()`）
**测试：** `tests/unit/sop/test_intraday_snapshot.py`

**需求（契约 7.7）：**
- 从 `get_effective_nodes()` 移除 `post_open_adj` 优先逻辑
- 盘中锚点调整必须回到计划变更与用户确认流程

**TDD 步骤：**
1. 写测试：test_get_effective_nodes_ignores_post_open_adj、test_get_effective_nodes_uses_original_nodes
2. 实现：移除 post_open_adj 分支
3. 回归：现有 30 tests 不退化（调整受影响的 test_get_effective_nodes_prefers_adj）

---

### Task I-4: Confirm Artifact Validation — C7

**分类：** `missing_capability`
**文件：** `orchestration/adapters.py`（L141-144）
**测试：** `tests/unit/orchestration/test_adapters.py`

**需求（契约 7.4）：**
- `record_focus_confirmation`：校验 decision sheet 文件存在 + 必填字段（focus_symbols, user_confirmed）
- `record_plan_approval`：校验 trading plan + intraday guidance 文件存在 + 必填字段
- coordinator 只做 schema/引用/版本/一致性校验，不生成内容

**TDD 步骤：**
1. 写测试：test_record_focus_confirmation_validates_decision_sheet、test_record_plan_approval_validates_plan_files
2. 实现：在 adapter 对应分支添加文件存在性和必填字段校验
3. 回归：现有 adapter 测试不退化

---

### Task I-5: Canonical Runtime Paths — C14

**分类：** `design_decision`（契约 7.6）
**文件：** `orchestration/store.py`、`orchestration/adapters.py`、`cli.py`（路径常量）
**测试：** 相关测试文件

**需求（契约 7.6）：**
- 创建 `investing-os/system/runtime/{sessions,inputs,packets}` 目录结构
- sessions/：协调器状态 JSON
- inputs/：investing-os 确认后的输入（decision sheet、trading plan、guidance）
- packets/：stock_team 生成并经协调器登记的证据包
- 旧路径保留但不作为新 DAILY canonical 路径

**TDD 步骤：**
1. 写测试：test_runtime_paths_resolve_correctly、test_session_store_uses_runtime_dir
2. 实现：定义 RUNTIME_ROOT 常量，更新 store.py 和 adapters.py 的路径引用
3. 回归：全部 89 tests 不退化

---

## 第二批：依赖第一批完成后再执行

### Task I-6: OBSERVATION_ACTIVE State — C5

**分类：** `design_decision`（契约 7.2）
**依赖：** I-1（session router 已支持 observation 模式）
**文件：** `orchestration/transitions.py`、`orchestration/models.py`
**测试：** `tests/unit/orchestration/test_transitions.py`、`tests/unit/orchestration/test_models.py`

**需求（契约 7.2）：**
- 在 TRADING_STATES 中注册 `OBSERVATION_ACTIVE`
- 在 transitions.py 添加从 `FOCUS_CONFIRMED` → `start_observation` → `OBSERVATION_ACTIVE` 的转换
- `OBSERVATION_ACTIVE` 的 allowed_actions 不含任何交易权限动作

**TDD 步骤：**
1. 写测试：test_observation_active_state_exists、test_focus_confirmed_to_observation_active、test_observation_active_forbids_trading_actions
2. 实现：注册状态 + 添加转换
3. 回归：现有 transition 测试不退化

---

### Task I-7: Intraday Snapshot Adapter + Time Window Soft Prompt — C11 + 7.9

**分类：** `design_decision`
**依赖：** I-6（OBSERVATION_ACTIVE 状态就位）
**文件：** `orchestration/adapters.py`、`cli.py`
**测试：** `tests/unit/orchestration/test_adapters.py`、`tests/unit/core/test_cli.py`

**需求（契约 7.5 + 7.9）：**
- adapters.py 添加 `intraday-snapshot` intent 映射
- `handle_intraday_snapshot()` 添加时间窗口软提示（警告但允许）
- 循环模式：对同一 `intraday-snapshot` 动作的重复调度，不创建第二套业务逻辑

**TDD 步骤：**
1. 写测试：test_adapter_supports_intraday_snapshot、test_intraday_snapshot_soft_warns_outside_window
2. 实现：添加 adapter 映射 + 时间窗口警告
3. 回归：现有 21 intraday snapshot tests + 16 orchestration tests 不退化

---

### Task I-8: Review States + Archive Logic — C3, C4, C6

**分类：** `missing_capability`
**依赖：** I-1（session router 已就位）
**文件：** `orchestration/transitions.py`、`orchestration/models.py`、新 `orchestration/archiver.py`
**测试：** 新测试文件 + 现有 transition/model tests

**需求（契约 5.DAILY-4 + 7.1）：**
- C3：添加 `REVIEW_REQUIRED` 到 BEGIN_TRANSITIONS
- C4：注册 `QUICK_REVIEWED`、`CLOSED_UNREVIEWED` 到 TRADING_STATES
- C6：实现 archive_day 最小逻辑：文件汇总 + 产物清单 JSON（manifest）
- 三种复盘路径：freeze → CLOSED_UNREVIEWED、quick → QUICK_REVIEWED、full → 完整 DAILY-4

**TDD 步骤：**
1. 写测试：每个状态注册 + 转换 + archive_day 产物写入
2. 实现：models.py 注册 → transitions.py 添加转换 → archiver.py 最小归档
3. 回归：现有 11 postmarket tests + transition tests 不退化

---

### Task I-9: Intraday Exception Confirmation — C10

**分类：** `missing_capability`
**依赖：** I-6（OBSERVATION_ACTIVE 状态就位）
**文件：** `orchestration/coordinator.py`、`orchestration/transitions.py`
**测试：** `tests/unit/orchestration/test_coordinator.py`

**需求（契约 4.DAILY-3 必须由用户确认）：**
- INTRADAY_ACTIVE 状态添加例外确认动作（`request_exception`）
- 用户确认后 coordinator 记录例外和用户确认时间

**TDD 步骤：**
1. 写测试：test_intraday_exception_requires_user_confirmation
2. 实现：添加 intent + confirmation flow
3. 回归：现有 coordinator tests 不退化

---

## 第三批：边界修正 + 端到端

### Task I-10: generate_suggestions Boundary — C13

**分类：** `boundary_conflict`（契约 7.10）
**文件：** `data_ingest/postmarket_data_collector.py`
**测试：** `tests/unit/sop/test_postmarket_summary.py`

**需求（契约 7.10）：**
- stock_team 只保留复盘事实输出（成交匹配、价格对比、执行偏差、信号准确性统计）
- lesson_record / thesis_status 等认知类型标记为 deprecated in stock_team
- investing-os 侧接收事实包并生成认知候选（本次只做 stock_team 侧拆分）

**TDD 步骤：**
1. 写测试：test_generate_suggestions_returns_facts_only、test_generate_suggestions_no_lesson_types
2. 实现：重构 generate_suggestions() 只输出事实类型
3. 回归：11 postmarket tests 不退化

---

### Task I-11: Dashboard Runtime Manifest — C12

**分类：** `missing_capability`（契约 7.11）
**依赖：** I-5（runtime paths 就位）、I-7（intraday-snapshot adapter 就位）
**文件：** `server/dashboard_server.py`、`dashboards/intraday-dashboard.html`
**测试：** `tests/unit/core/test_dashboard_refresh_prices.py`

**需求（契约 7.11）：**
- CLI 生产路径和 Dashboard 消费路径统一到 coordinator 登记的 runtime manifest
- dashboard_server 启动时不创建可能陈旧的文件；读取 coordinator manifest 获取最新 snapshot 路径
- 添加新鲜度时间戳验证

**TDD 步骤：**
1. 写测试：test_dashboard_reads_from_runtime_manifest、test_dashboard_rejects_stale_manifest
2. 实现：修改 dashboard_server.py 从 manifest 读路径
3. 回归：5 dashboard tests 不退化

---

### Task I-12: DAILY End-to-End Tests (非交易模拟)

**分类：** `missing_capability`
**依赖：** I-1 至 I-11 全部完成
**文件：** 新 `tests/integration/test_daily_e2e.py`
**测试 fixture：** 模拟 IBKR 数据、模拟行情数据

**需求：**
- DAILY-0 → DAILY-1 → DAILY-2 → DAILY-3 → DAILY-4 完整 trading 路径
- DAILY-0 → DAILY-1 → DAILY-2 → DAILY-3 → DAILY-4 完整 observation 路径
- 跨日恢复：freeze/quick_review/full_review 三种路径
- 无交易日：DAILY-0 → 直接 DAY_ARCHIVED

**TDD 步骤：**
1. 创建模拟 fixture（yfinance mock + positions mock）
2. 写测试：每个端到端路径一个 test
3. 运行：验证全部路径可执行

---

## 分发建议

| 批次 | 任务 | 可并行 | 预估文件冲突 |
|------|------|--------|------------|
| 1 | I-1, I-2, I-3, I-4, I-5 | ✅ 5 个任务互不修改共享文件 | 无 |
| 2 | I-6, I-7, I-8, I-9 | I-6→I-7 依赖，I-6→I-9 依赖，I-8 独立 | transitions.py 共享 |
| 3 | I-10, I-11, I-12 | I-10 独立，I-11 依赖 I-5/I-7，I-12 依赖全部 | I-12 只新增 |

**推荐执行顺序：** 第一批 5 个全部并行 → 第二批 I-8 独立 + I-6 → I-7 → I-9 串行 → 第三批
