# DAILY Phase 2 实施计划

> 依据：DAILY-CONTRACT v4 approved + WORKFLOW-STATUS Phase 1 完成
> Phase 1 成果：C1–C14 全部实现，164 tests passed
> Phase 2 范围：跨日恢复、非交易日、复盘交互

---

## 剩余缺口（从 WORKFLOW-STATUS）

| 缺口 | 来源 | 优先级 | 依赖用户决定 |
|------|------|--------|------------|
| 跨日恢复路由器 | DAILY-0 | P0 | 否（Q1 已批准） |
| 非交易日路径 | DAILY-0 | P1 | 部分（需定义触发条件） |
| 复盘交互对话流 | DAILY-4 | P1 | 是（Q2 对话方式） |
| E2E 握手链集成 | DAILY-1 | P2 | 否 |
| IBKR streaming 对接 | DAILY-3 | P3 | 否 |

---

## 第一批：跨日恢复路由器（无需用户决定）

### Task P2-1: SessionStore.list_sessions()

**文件：** `orchestration/store.py`
**测试：** `tests/unit/orchestration/test_store.py`

**需求：**
- 添加 `list_sessions()` 方法，返回所有 session 的 (session_id, state) 列表
- 支持按日期过滤
- 支持只返回未关闭的 session（state != DAY_ARCHIVED 且 state != CLOSED_UNREVIEWED）

### Task P2-2: Cross-Day Recovery Router

**文件：** `coordinator_cli.py`、`coordinator.py`
**测试：** `tests/unit/orchestration/test_coordinator_cli.py`

**需求（契约 Q1）：**
- `init-day` 检查前一个交易日是否有未关闭 session
- 如果有：提示用户选择 freeze/quick_review/full_review 恢复路径
- 自动执行所选恢复 → 关闭旧 session → 创建新 session

### Task P2-3: Non-Trading Day Path

**文件：** `orchestration/transitions.py`、`models.py`、`coordinator.py`
**测试：** `tests/unit/orchestration/test_transitions.py`

**需求：**
- 添加 `NON_TRADING` 状态或直接 DAY_INITIALIZED → DAY_ARCHIVED 转换
- `init-day` 添加 `--market-status non-trading` 选项

---

## 第二批：复盘交互（需用户确认后实施）

### Task P2-4: DAILY-4 Step 3-6 复盘交互

**保留占位，待用户确认 Q2 复盘交互方式后展开。**

---

## 执行规则

- TDD：先写测试，最小实现
- 独立 commit，不越权修改
- 从项目根目录运行测试
