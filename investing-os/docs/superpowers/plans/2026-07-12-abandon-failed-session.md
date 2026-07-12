# Abandon Failed Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为不可重试的历史 `FAILED_TOOL` 会话提供用户确认、债务留痕、保留产物归档和终态关闭路径。

**Architecture:** 新动作 `abandon_failed_session` 只从 `FAILED_TOOL` 进入 `CLOSED_UNREVIEWED`，复用现有 freeze 型 DAILY-4 债务记录和 `archive_day` 白名单 archiver。协调器在关闭前登记 runtime `inputs/`、`packets/` 中属于该 session 的现存产物；不修改旧产物内容，也不将关闭解释为复盘完成。

**Tech Stack:** Python、现有 orchestration state machine、SessionStore、archive_session、pytest

---

### Task 1: 状态机契约

**Files:**
- Modify: `stock_team/orchestration/models.py`
- Modify: `stock_team/orchestration/transitions.py`
- Test: `stock_team/tests/unit/orchestration/test_models.py`
- Test: `stock_team/tests/unit/orchestration/test_transitions.py`

- [ ] 写失败测试：动作属于 canonical intent；`FAILED_TOOL` 暴露该动作；动作要求确认；begin transition 进入 `CLOSED_UNREVIEWED`。
- [ ] Run: `python -m pytest stock_team/tests/unit/orchestration/test_models.py stock_team/tests/unit/orchestration/test_transitions.py -q`；Expected: FAIL。
- [ ] 最小实现：加入 ACTION_INTENTS、BEGIN_TRANSITIONS、ALLOWED_ACTIONS 和 CONFIRMATION_ACTIONS。
- [ ] 重跑相同测试；Expected: PASS。
- [ ] Commit: `feat: add abandoned failed-session transition`。

### Task 2: 债务记录与保留产物登记

**Files:**
- Modify: `stock_team/orchestration/coordinator.py`
- Test: `stock_team/tests/unit/orchestration/test_coordinator.py`

- [ ] 写失败测试：未确认被拒绝；`last_error.retryable != false` 被拒绝；合法动作生成 freeze 型 debt review；登记 session 前缀的 inputs/packets 文件；不登记其他 session 文件。
- [ ] Run: `python -m pytest stock_team/tests/unit/orchestration/test_coordinator.py -q -k "abandon_failed"`；Expected: FAIL。
- [ ] 最小实现：在 begin transition 前验证不可重试；把动作列入 meta intents；复用 `new_daily4_review(..., "freeze")`；扫描范围严格限制为 `Path(store.root).parent/{inputs,packets}` 和文件名前缀 `{session_id}-`。
- [ ] 重跑测试；Expected: PASS。
- [ ] Commit: `feat: record debt when abandoning failed session`。

### Task 3: 归档链集成测试

**Files:**
- Modify: `stock_team/tests/integration/test_daily_e2e.py`

- [ ] 写集成测试：`FAILED_TOOL -> abandon_failed_session -> CLOSED_UNREVIEWED -> archive_day -> DAY_ARCHIVED`；manifest 包含 debt review 和保留产物；不包含其他 session 文件。
- [ ] Run: `python -m pytest stock_team/tests/integration/test_daily_e2e.py -q -k "abandon_failed"`；Expected: 在实现后 PASS，并通过临时移除新 transition 验证测试会失败。
- [ ] 跑限定回归：orchestration unit + DAILY E2E；Expected: 全部 PASS。
- [ ] Commit: `test: verify abandoned session archive chain`。

### Task 4: 真实历史会话关闭

**Files:**
- Runtime mutation: `investing-os/system/runtime/sessions/trading-2026-06-15.json`
- Create runtime archive: `investing-os/system/runtime/archive/2026-06-15/trading-2026-06-15/`
- Modify: `investing-os/handoff/2026-07-12-historical-failed-session-recovery-decision.zh.md`

- [ ] 关闭前核对 session id、state、`retryable=false` 和目标 archive 根目录。
- [ ] 通过 WorkflowCoordinator 执行带 `user_confirmation=true` 的 `abandon_failed_session`。
- [ ] 重新读取 session，确认 `CLOSED_UNREVIEWED`、债务记录存在且 artifact ledger 仅包含同 session 文件。
- [ ] 执行 `archive_day`，确认 `DAY_ARCHIVED`、manifest complete、原文件 hash 与归档 hash 一致。
- [ ] 调用 Dashboard API，确认不再返回 `recovery_required`，且非交易日不创建未来 session。
- [ ] 将事实、manifest 路径和测试结果写回决策记录；不提交 runtime 派生文件。
- [ ] 清理 runtime manifests，提交文档并推送当前分支。
