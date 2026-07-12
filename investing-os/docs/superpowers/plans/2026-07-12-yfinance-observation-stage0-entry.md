# Yfinance Observation Stage 0 Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 observation session 中用 yfinance 生成只读 Stage 0 事实包，并推进到 DAILY-1B 等待对话讨论，同时保持 trading 正式数据闸门不变。

**Architecture:** 新建独立、可测试的 observation producer，输出 session-scoped JSON snapshot 和 markdown packet；新增 `start_stage0_observation` intent 与 adapter 接线；`daily_status` 仅在 observation session 中接受该 evidence level。Dashboard 继续只读 manifest。

**Tech Stack:** Python、yfinance、现有 WorkflowCoordinator/ExistingCliAdapter、pytest

---

### Task 1: Observation producer

**Files:**
- Create: `stock_team/data_ingest/observation_market_context.py`
- Create: `stock_team/tests/unit/data_ingest/test_observation_market_context.py`

- [ ] 写失败测试：注入 fake history loader，要求 QQQ/SPY/IWM/VIXY 均输出 price、prev_close、source、data_as_of；JSON/markdown 包含 `observation_only` 和 `no_trading_permission`；缺少任一代理时不产生最终文件。
- [ ] Run: `python -m pytest stock_team/tests/unit/data_ingest/test_observation_market_context.py -q`；Expected: FAIL，模块不存在。
- [ ] 实现 `build_observation_context()`、原子写入和 `python -m stock_team.data_ingest.observation_market_context` CLI；默认 loader 使用 yfinance daily history。
- [ ] 重跑测试；Expected: PASS。
- [ ] Commit: `feat: add yfinance observation market context producer`。

### Task 2: Coordinator intent 与 adapter

**Files:**
- Modify: `stock_team/orchestration/models.py`
- Modify: `stock_team/orchestration/transitions.py`
- Modify: `stock_team/orchestration/coordinator.py`
- Modify: `stock_team/orchestration/adapters.py`
- Modify: `investing-os/system/data/schemas/coordinator-action.schema.json`
- Test: `stock_team/tests/unit/orchestration/test_models.py`
- Test: `stock_team/tests/unit/orchestration/test_transitions.py`
- Test: `stock_team/tests/unit/orchestration/test_coordinator.py`
- Test: `stock_team/tests/unit/orchestration/test_adapters.py`

- [ ] 写失败测试：canonical intent；DAY_INITIALIZED 到 STAGE0_READY；adapter 仅调用 observation producer；trading session 在写文件前拒绝。
- [ ] Run: `python -m pytest stock_team/tests/unit/orchestration -q -k "stage0_observation"`；Expected: FAIL。
- [ ] 最小实现 intent、transition、adapter command 和 session-type guard。
- [ ] 重跑测试及 orchestration suite；Expected: PASS。
- [ ] Commit: `feat: wire observation stage0 through coordinator`。

### Task 3: DAILY 状态模式判定

**Files:**
- Modify: `stock_team/orchestration/daily_status.py`
- Test: `stock_team/tests/unit/orchestration/test_daily_status.py`

- [ ] 写失败测试：完整 observation snapshot 在 observation session 中 valid/fresh 并推进到 DAILY-1B；同一 snapshot 在 trading session 中 invalid 且停在 DAILY-1A；artifact issues 保留 `observation_only_no_trading_permission`。
- [ ] Run: `python -m pytest stock_team/tests/unit/orchestration/test_daily_status.py -q`；Expected: FAIL。
- [ ] 新增 `_observation_snapshot()`，并将 session mode 传入 `_artifact()`；正式 `_formal_snapshot()` 不改变。
- [ ] 重跑测试；Expected: PASS。
- [ ] Commit: `feat: allow observation evidence without trading readiness`。

### Task 4: 隔离 E2E 与记录

**Files:**
- Modify: `stock_team/tests/integration/test_daily_e2e.py`
- Create: `investing-os/handoff/2026-07-12-yfinance-observation-stage0-rehearsal.zh.md`

- [ ] 写 E2E：临时 runtime 创建 observation session、DAILY-0 confirmation 和 universe；fake loader producer → coordinator intent → STAGE0_READY → DAILY-1B；验证 trading session 拒绝。
- [ ] Run: `python -m pytest stock_team/tests/integration/test_daily_e2e.py -q -k "observation_stage0"`；Expected: PASS after implementation。
- [ ] 使用真实 yfinance 和临时 runtime 运行固定已发生交易日 rehearsal；不得写真实 session。
- [ ] 运行限定回归：producer、orchestration、daily_status、DAILY E2E、Dashboard tests；Expected: 全部 PASS。
- [ ] 记录真实数据来源、状态、限制和下一步；清理派生 manifest。
- [ ] Commit: `test: verify yfinance observation stage0 rehearsal` 并 push 当前分支。
