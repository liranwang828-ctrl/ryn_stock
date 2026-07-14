# Historical Session Unblock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复“昨日历史会话阻塞今日正式会话”的主链问题，使 today 入口在历史会话处理完成后自动回到今日 `DAILY-0` 初始化，而不是继续投影昨日 stale 会话。

**Architecture:** 这次只改三层：coordinator 负责判断历史会话是否仍阻塞 today，daily status 负责过滤 `trading_date_mismatch` 的历史 artifacts，dashboard summary 负责把统一 blocker/readiness 投影给 today 页面。实现顺序遵循 TDD：先补 failing tests，再做最小修复，最后用 integration 和本地 API 验证 today 路由切换。

**Tech Stack:** Python, pytest, stock_team orchestration/session models, dashboard server, local runtime session JSON

---

## File Structure

- Modify: `stock_team/orchestration/coordinator.py`
  - 明确“历史会话已处理完成”的判定，并在完成后解除 today 阻塞
- Modify: `stock_team/orchestration/daily_status.py`
  - today readiness 计算时忽略 `trading_date != today` 的历史 artifacts
- Modify: `stock_team/server/dashboard_server.py`
  - summary payload 与 today entry projection 保持一致
- Test: `stock_team/tests/unit/orchestration/test_coordinator.py`
  - 覆盖 blocker 存在 / blocker 解除
- Test: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`
  - 覆盖 today summary / entry_state / daily_status 对齐
- Test: `stock_team/tests/integration/test_daily_e2e.py`
  - 覆盖跨日修复后的公开入口行为

---

### Task 1: 锁定当前跨日阻塞根因

**Files:**
- Modify: `stock_team/tests/unit/orchestration/test_coordinator.py`
- Modify: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`

- [ ] **Step 1: 写 coordinator failing test，锁定“历史会话未处理时 today 必须阻塞”**

```python
def test_historical_session_blocks_today_until_resolved(tmp_path):
    runtime_root = tmp_path / "runtime"
    sessions_dir = runtime_root / "sessions"
    sessions_dir.mkdir(parents=True)

    historical_session = {
        "session_id": "observation-2026-07-13",
        "trading_date": "2026-07-13",
        "state": "PLAN_APPROVED",
        "mode": "observation",
        "allowed_actions": [],
        "completed": {"artifacts": []},
    }
    (sessions_dir / "observation-2026-07-13.json").write_text(
        json.dumps(historical_session),
        encoding="utf-8",
    )

    summary = build_coordinator_summary(
        runtime_root=runtime_root,
        now_et="2026-07-14T09:36:36-04:00",
    )

    assert summary["session_kind"] == "recovery_required"
    assert summary["first_action"] == "resolve_historical_session_in_conversation"
    assert summary["entry_state"]["readiness"] == "blocked"
```

- [ ] **Step 2: 跑单测，确认它以正确原因失败**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_coordinator.py -k historical_session_blocks_today_until_resolved -v`

Expected: FAIL，当前实现无法稳定表达“历史会话未处理时 today 阻塞”的完整契约，或测试辅助函数/断言与实际不一致。

- [ ] **Step 3: 写 dashboard failing test，锁定“today 不应把历史 artifact 当成今日 readiness”**

```python
def test_dashboard_today_ignores_historical_artifacts_for_readiness(tmp_path):
    runtime_root = tmp_path / "runtime"
    inputs_dir = runtime_root / "inputs"
    packets_dir = runtime_root / "packets"
    sessions_dir = runtime_root / "sessions"
    inputs_dir.mkdir(parents=True)
    packets_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    (inputs_dir / "observation-2026-07-13-stage0-universe.json").write_text("{}", encoding="utf-8")
    (packets_dir / "observation-2026-07-13-stage0-market-context.md").write_text("# stale", encoding="utf-8")

    session = {
        "session_id": "observation-2026-07-13",
        "trading_date": "2026-07-13",
        "state": "PLAN_APPROVED",
        "mode": "observation",
        "allowed_actions": [],
        "completed": {"artifacts": []},
    }
    (sessions_dir / "observation-2026-07-13.json").write_text(json.dumps(session), encoding="utf-8")

    payload = build_dashboard_summary_payload(
        runtime_root=runtime_root,
        now_et="2026-07-14T09:36:36-04:00",
    )

    assert payload["entry_state"]["readiness"] == "blocked"
    assert payload["daily_status"]["missing_items"][0]["code"] == "historical_session_blocking"
    assert all(
        artifact["freshness"] != "fresh"
        for artifact in payload["daily_status"]["artifacts"]
        if artifact["path"].endswith("2026-07-13-stage0-market-context.md")
    )
```

- [ ] **Step 4: 跑 dashboard 单测，确认它先失败**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k historical_artifacts_for_readiness -v`

Expected: FAIL，当前 today payload 仍把历史 artifact 投影到 today readiness。

- [ ] **Step 5: Commit**

```bash
git add stock_team/tests/unit/orchestration/test_coordinator.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "test: lock historical session blocking behavior"
```

---

### Task 2: 最小实现 coordinator 解锁逻辑

**Files:**
- Modify: `stock_team/orchestration/coordinator.py`
- Test: `stock_team/tests/unit/orchestration/test_coordinator.py`

- [ ] **Step 1: 写 failing test，锁定“历史会话处理完成后 today 不再阻塞”**

```python
def test_historical_session_no_longer_blocks_after_archive(tmp_path):
    runtime_root = tmp_path / "runtime"
    sessions_dir = runtime_root / "sessions"
    sessions_dir.mkdir(parents=True)

    historical_session = {
        "session_id": "observation-2026-07-13",
        "trading_date": "2026-07-13",
        "state": "DAY_ARCHIVED",
        "mode": "observation",
        "allowed_actions": [],
        "completed": {"artifacts": []},
    }
    (sessions_dir / "observation-2026-07-13.json").write_text(
        json.dumps(historical_session),
        encoding="utf-8",
    )

    summary = build_coordinator_summary(
        runtime_root=runtime_root,
        now_et="2026-07-14T09:36:36-04:00",
    )

    assert summary["session_kind"] != "recovery_required"
    assert summary["first_action"] != "resolve_historical_session_in_conversation"
```

- [ ] **Step 2: 跑单测，确认失败**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_coordinator.py -k historical_session_no_longer_blocks_after_archive -v`

Expected: FAIL，当前 archived/reviewed terminal 条件还没有完整解除 today 阻塞。

- [ ] **Step 3: 在 coordinator 中实现“历史会话是否仍阻塞 today”的单一判定**

```python
def _historical_session_still_blocks(session: dict[str, Any], today: str) -> bool:
    session_date = session.get("trading_date")
    if not session_date or session_date >= today:
        return False

    terminal_states = {
        "DAY_ARCHIVED",
        "IDLE",
    }
    review_cleared_states = {
        "QUICK_REVIEWED",
        "FULL_REVIEWED",
        "CLOSED_UNREVIEWED",
    }

    state = session.get("state")
    return state not in terminal_states and state not in review_cleared_states
```

- [ ] **Step 4: 在 summary 生成路径中只对“仍阻塞”的历史会话返回 recovery_required**

```python
if historical_session and _historical_session_still_blocks(historical_session, trading_date):
    return {
        "session_kind": "recovery_required",
        "first_action": "resolve_historical_session_in_conversation",
        "entry_state": {
            "readiness": "blocked",
            "missing_items": [
                "historical session must be resolved before a new formal trading session"
            ],
            "next_action": "resolve_historical_session_in_conversation",
        },
    }
```

- [ ] **Step 5: 跑 coordinator 相关测试，确认由红转绿**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_coordinator.py -q`

Expected: PASS，包括新加的历史会话 blocker / unblock 测试。

- [ ] **Step 6: Commit**

```bash
git add stock_team/orchestration/coordinator.py stock_team/tests/unit/orchestration/test_coordinator.py
git commit -m "fix: unblock today after historical session is formally resolved"
```

---

### Task 3: 最小实现 daily status 对历史 artifact 的 today 过滤

**Files:**
- Modify: `stock_team/orchestration/daily_status.py`
- Modify: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`

- [ ] **Step 1: 写 failing test，锁定“trading_date_mismatch artifact 不进入 today readiness”**

```python
def test_daily_status_uses_historical_artifacts_only_as_diagnostics(tmp_path):
    runtime_root = tmp_path / "runtime"
    inputs_dir = runtime_root / "inputs"
    packets_dir = runtime_root / "packets"
    sessions_dir = runtime_root / "sessions"
    inputs_dir.mkdir(parents=True)
    packets_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    (inputs_dir / "observation-2026-07-13-stage0-universe.json").write_text("{}", encoding="utf-8")
    (packets_dir / "observation-2026-07-13-stage0-market-context.md").write_text("# stale", encoding="utf-8")

    session = {
        "session_id": "observation-2026-07-13",
        "trading_date": "2026-07-13",
        "state": "PLAN_APPROVED",
        "mode": "observation",
        "allowed_actions": [],
        "completed": {"artifacts": []},
    }
    (sessions_dir / "observation-2026-07-13.json").write_text(json.dumps(session), encoding="utf-8")

    status = build_daily_status(
        runtime_root=runtime_root,
        trading_date="2026-07-14",
        now_et="2026-07-14T09:36:36-04:00",
    )

    assert status["overall_status"] == "blocked"
    assert status["missing_items"][0]["code"] == "historical_session_blocking"
```

- [ ] **Step 2: 跑单测，确认失败**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k historical_session_blocking -v`

Expected: FAIL，当前 build_daily_status 仍把 mismatch artifacts 当作 today 的 stale inputs 来展示。

- [ ] **Step 3: 在 daily_status 中区分“today artifacts”和“historical diagnostics artifacts”**

```python
def _is_today_artifact(artifact: dict[str, Any], trading_date: str) -> bool:
    issues = set(artifact.get("issues") or [])
    if "trading_date_mismatch" in issues:
        return False
    path = artifact.get("path", "")
    return trading_date in path
```

- [ ] **Step 4: 仅用 today artifacts 计算 readiness；历史 artifact 保留给 diagnostics**

```python
today_artifacts = [a for a in artifacts if _is_today_artifact(a, trading_date)]
historical_artifacts = [a for a in artifacts if not _is_today_artifact(a, trading_date)]

if historical_session_blocking:
    overall_status = "blocked"
    missing_items = [{
        "code": "historical_session_blocking",
        "severity": "blocked",
        "artifact_role": "",
        "field": "",
        "message": "上一交易日会话尚未处理完成，今日正式会话仍被阻塞。",
        "conversation_prompt": "请先完成历史会话处理，再开始今日会话。",
    }]

status["artifacts"] = historical_artifacts + today_artifacts
```

- [ ] **Step 5: 跑 dashboard/daily_status 相关测试**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q`

Expected: PASS，today readiness 与历史 artifact 诊断分层生效。

- [ ] **Step 6: Commit**

```bash
git add stock_team/orchestration/daily_status.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "fix: keep historical artifacts out of today readiness"
```

---

### Task 4: 对齐 dashboard summary 与 today 页面入口

**Files:**
- Modify: `stock_team/server/dashboard_server.py`
- Modify: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`

- [ ] **Step 1: 写 failing test，锁定 summary payload 与 daily status blocker 一致**

```python
def test_dashboard_summary_uses_same_historical_session_blocker_as_daily_status(tmp_path):
    payload = build_dashboard_summary_payload(
        runtime_root=tmp_path / "runtime",
        now_et="2026-07-14T09:36:36-04:00",
    )

    assert payload["entry_state"]["readiness"] == "blocked"
    assert payload["entry_state"]["next_action"] == "resolve_historical_session_in_conversation"
    assert payload["daily_status"]["overall_status"] == "blocked"
```

- [ ] **Step 2: 跑单测，确认失败**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k same_historical_session_blocker -v`

Expected: FAIL，当前 summary payload 可能仍用旧投影逻辑。

- [ ] **Step 3: 在 dashboard summary 组装层复用统一 blocker 结果，而不是重复推断**

```python
daily_status = build_daily_status(...)
entry_state = build_entry_state_from_daily_status(daily_status, coordinator_summary)

payload["entry_state"] = entry_state
payload["daily_status"] = daily_status
```

- [ ] **Step 4: 跑 dashboard tests，确认 today API 表达一致**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_team/server/dashboard_server.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "fix: align dashboard today blocker with daily status"
```

---

### Task 5: 端到端验证公开入口恢复今天会话

**Files:**
- Modify: `stock_team/tests/integration/test_daily_e2e.py`

- [ ] **Step 1: 写 failing integration test，锁定“处理昨天后 today 回到 init-day”**

```python
def test_today_entry_returns_to_init_day_after_historical_session_is_archived(tmp_path):
    runtime_root = tmp_path / "runtime"
    sessions_dir = runtime_root / "sessions"
    sessions_dir.mkdir(parents=True)

    historical_session = {
        "session_id": "observation-2026-07-13",
        "trading_date": "2026-07-13",
        "state": "DAY_ARCHIVED",
        "mode": "observation",
        "allowed_actions": [],
        "completed": {"artifacts": []},
    }
    (sessions_dir / "observation-2026-07-13.json").write_text(json.dumps(historical_session), encoding="utf-8")

    summary = build_coordinator_summary(
        runtime_root=runtime_root,
        now_et="2026-07-14T09:36:36-04:00",
    )

    assert summary["session"]["market_date"] == "2026-07-14" or summary["session"] is None
    assert summary["first_action"] in {"init_day", "start_day", "start_daily_0"}
```

- [ ] **Step 2: 跑 integration test，确认先失败**

Run: `python -m pytest stock_team/tests/integration/test_daily_e2e.py -k historical_session_is_archived -v`

Expected: FAIL，当前公开入口还未完全切回 today 初始化。

- [ ] **Step 3: 修正 coordinator / dashboard 上残余的 today fallback 路径（如果前四个任务未完全覆盖）**

```python
if not blocking_historical_session:
    first_action = _default_today_start_action(...)
    session_payload = _today_session_payload_or_none(...)
```

- [ ] **Step 4: 跑全量相关测试**

Run: `python -m pytest stock_team/tests/unit/orchestration stock_team/tests/unit/core/test_dashboard_refresh_prices.py stock_team/tests/integration/test_daily_e2e.py -q`

Expected: PASS

- [ ] **Step 5: 手动验证本地 API**

Run: `python -c "import json,urllib.request;print(urllib.request.urlopen('http://localhost:8080/api/coordinator-summary').read().decode('utf-8'))"`

Expected:
- 历史会话未处理时：`session_kind = recovery_required`
- 历史会话处理完成后：today 不再 blocked，首动作回到 today 初始化

- [ ] **Step 6: Commit**

```bash
git add stock_team/tests/integration/test_daily_e2e.py stock_team/orchestration/coordinator.py stock_team/server/dashboard_server.py stock_team/orchestration/daily_status.py
git commit -m "test: verify today entry recovers after historical session resolution"
```

---

## Self-Review

- Spec coverage:
  - 历史会话阻塞 today：Task 1 / Task 2
  - 处理完成后 today 解锁：Task 2 / Task 5
  - 历史 artifact 不再伪装 today readiness：Task 3
  - Dashboard/API 一致：Task 4 / Task 5
- Placeholder scan:
  - 无 `TODO` / `TBD`
  - 每个任务都给了测试、命令、期望结果与 commit
- Type consistency:
  - 统一使用 `recovery_required`、`resolve_historical_session_in_conversation`、`historical_session_blocking`
  - today 初始化动作名在 Task 5 中明确限制为现有入口之一，实施时需要对照现有常量命名

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-14-historical-session-unblock-plan.zh.md`.

Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints
