# Dashboard Premarket To Intraday Experience Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a controlled two-agent dashboard optimization loop that reviews the premarket-to-intraday workflow, records structured usability issues, applies small-batch fixes, and re-checks the same workflow without increasing intraday load.

**Architecture:** Add a dashboard-local experience loop package that defines fixed task paths, validates issue/recheck artifacts, and boots a single review round from the existing dashboard context. Keep the first version artifact-driven and dashboard-scoped so it can support real browser-based review later without touching backtest infrastructure or introducing background polling.

**Tech Stack:** Python 3.12, stdlib `json`/`dataclasses`/`pathlib`, existing dashboard context builders, pytest

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `D:/gemini/lianghua/stock_team/agents/dashboard_experience_paths.py` | Create | Define the fixed Path A-D review tasks, protected scopes, and per-path expectations for v1. |
| `D:/gemini/lianghua/stock_team/agents/dashboard_experience_loop.py` | Create | Validate issue/recheck artifacts, enforce per-round limits, and bootstrap a single review round manifest from existing dashboard state. |
| `D:/gemini/lianghua/stock_team/agents/dashboard_writer.py` | Modify | Expose minimal route/state fields needed by the loop manifest without changing polling behavior. |
| `D:/gemini/lianghua/stock_team/tests/test_dashboard_experience_paths.py` | Create | Verify path definitions, protected scope rules, and review limits stay stable. |
| `D:/gemini/lianghua/stock_team/tests/test_dashboard_experience_loop.py` | Create | Verify manifest bootstrap, artifact validation, and round summaries. |
| `D:/gemini/lianghua/stock_team/docs/superpowers/specs/2026-05-31-dashboard-premarket-intraday-experience-loop-design.md` | Reference only | Source-of-truth scope; no edits expected during implementation. |

## Scope Guardrails

- Only touch dashboard-scoped code and tests.
- Do **not** edit files whose primary responsibility is backtesting, parameter sweeps, simulation, or result analysis.
- Do **not** add hidden refresh behavior, broader symbol polling, or timer-based background work.
- Keep v1 artifact-driven: one round, max three high-priority issues, max two fixes, one re-check.

---

### Task 1: Freeze review paths and limits in code

**Files:**
- Create: `D:/gemini/lianghua/stock_team/agents/dashboard_experience_paths.py`
- Test: `D:/gemini/lianghua/stock_team/tests/test_dashboard_experience_paths.py`

- [ ] **Step 1: Write the failing path-definition tests**

```python
from agents.dashboard_experience_paths import (
    EXPERIENCE_PATHS,
    MAX_FIXES_PER_ROUND,
    MAX_HIGH_PRIORITY_ISSUES,
    PROTECTED_SCOPE_TOKENS,
    path_ids,
)


def test_experience_paths_freeze_v1_task_ids():
    assert path_ids() == ["path_a_premarket_orientation", "path_b_premarket_readiness", "path_c_symbol_action", "path_d_return_to_global"]


def test_experience_paths_enforce_controlled_round_limits():
    assert MAX_HIGH_PRIORITY_ISSUES == 3
    assert MAX_FIXES_PER_ROUND == 2


def test_protected_scope_explicitly_blocks_backtest_tokens():
    assert {"backtest", "joint_backtest", "sweep", "simulation"}.issubset(set(PROTECTED_SCOPE_TOKENS))
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_paths.py -v
```

Expected: FAIL with `ModuleNotFoundError` or import errors because the new module does not exist yet.

- [ ] **Step 3: Implement the path registry**

```python
from __future__ import annotations

from dataclasses import dataclass


MAX_HIGH_PRIORITY_ISSUES = 3
MAX_FIXES_PER_ROUND = 2
PROTECTED_SCOPE_TOKENS = (
    "backtest",
    "joint_backtest",
    "parameter_sweep",
    "simulation",
)


@dataclass(frozen=True)
class ExperiencePath:
    id: str
    title: str
    goal: str
    entry_hint: str
    success_signal: str


EXPERIENCE_PATHS = (
    ExperiencePath(
        id="path_a_premarket_orientation",
        title="Premarket Orientation",
        goal="Identify market phase and current top action from the landing view.",
        entry_hint="Open the dashboard landing page.",
        success_signal="Current phase and top action are obvious within one screen.",
    ),
    ExperiencePath(
        id="path_b_premarket_readiness",
        title="Premarket Readiness",
        goal="Confirm today focus and determine which symbols deserve attention first.",
        entry_hint="Start from the landing overview and inspect today's focus area.",
        success_signal="Ready vs not-ready symbols can be differentiated without cross-reading multiple modules.",
    ),
    ExperiencePath(
        id="path_c_symbol_action",
        title="Move Into Symbol-Level Action",
        goal="Enter a focus symbol and find price, node, and action-relevant data quickly.",
        entry_hint="Open a symbol detail view from the overview.",
        success_signal="Price, node, and action context are visible without hunting across sections.",
    ),
    ExperiencePath(
        id="path_d_return_to_global",
        title="Return To Global Monitoring",
        goal="Return from symbol detail and recover the next global monitoring priority.",
        entry_hint="Navigate back from a symbol detail view.",
        success_signal="The next monitoring target is obvious after returning to the global view.",
    ),
)


def path_ids() -> list[str]:
    return [path.id for path in EXPERIENCE_PATHS]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_paths.py -v
```

Expected: PASS for all three tests.

- [ ] **Step 5: Commit**

```powershell
git -C D:\gemini\lianghua\stock_team add agents/dashboard_experience_paths.py tests/test_dashboard_experience_paths.py
git -C D:\gemini\lianghua\stock_team commit -m "feat: add dashboard experience path registry"
```

---

### Task 2: Add artifact validation for issue, fix, and re-check reports

**Files:**
- Create: `D:/gemini/lianghua/stock_team/agents/dashboard_experience_loop.py`
- Test: `D:/gemini/lianghua/stock_team/tests/test_dashboard_experience_loop.py`

- [ ] **Step 1: Write the failing artifact-validation tests**

```python
import pytest

from agents.dashboard_experience_loop import (
    build_issue,
    build_recheck_result,
    validate_round_payload,
)


def test_build_issue_requires_known_path_and_severity():
    issue = build_issue(
        page_module="Today Focus",
        task_path="path_b_premarket_readiness",
        problem="Next action is hidden behind multiple status chips.",
        why_it_hurts="User cannot tell which symbol is ready first.",
        severity="high",
        suggested_direction="Promote one primary action block.",
    )
    assert issue["severity"] == "high"
    assert issue["task_path"] == "path_b_premarket_readiness"


def test_validate_round_payload_rejects_too_many_high_priority_issues():
    with pytest.raises(ValueError, match="at most 3 high-priority issues"):
        validate_round_payload({
            "issues": [
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "high"},
            ],
            "implemented_fixes": [],
        })


def test_build_recheck_result_keeps_same_path_and_resolution_state():
    result = build_recheck_result(
        task_path="path_c_symbol_action",
        status="improved",
        before_problem="Action block was buried below dense metrics.",
        after_observation="Action block is visible in the first viewport.",
    )
    assert result["task_path"] == "path_c_symbol_action"
    assert result["status"] == "improved"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_loop.py -v
```

Expected: FAIL with missing functions or import errors.

- [ ] **Step 3: Implement the artifact helpers**

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agents.dashboard_experience_paths import (
    MAX_FIXES_PER_ROUND,
    MAX_HIGH_PRIORITY_ISSUES,
    path_ids,
)

KNOWN_PATH_IDS = set(path_ids())
KNOWN_SEVERITIES = {"high", "medium", "low"}
KNOWN_RECHECK_STATUS = {"improved", "unchanged", "regressed"}


@dataclass(frozen=True)
class ExperienceIssue:
    page_module: str
    task_path: str
    problem: str
    why_it_hurts: str
    severity: str
    suggested_direction: str


def build_issue(**kwargs: Any) -> dict[str, Any]:
    issue = ExperienceIssue(**kwargs)
    if issue.task_path not in KNOWN_PATH_IDS:
        raise ValueError(f"unknown task path: {issue.task_path}")
    if issue.severity not in KNOWN_SEVERITIES:
        raise ValueError(f"unknown severity: {issue.severity}")
    return asdict(issue)


def build_recheck_result(task_path: str, status: str, before_problem: str, after_observation: str) -> dict[str, str]:
    if task_path not in KNOWN_PATH_IDS:
        raise ValueError(f"unknown task path: {task_path}")
    if status not in KNOWN_RECHECK_STATUS:
        raise ValueError(f"unknown recheck status: {status}")
    return {
        "task_path": task_path,
        "status": status,
        "before_problem": before_problem,
        "after_observation": after_observation,
    }


def validate_round_payload(payload: dict[str, Any]) -> dict[str, Any]:
    issues = payload.get("issues") or []
    implemented_fixes = payload.get("implemented_fixes") or []
    high_count = sum(1 for issue in issues if issue.get("severity") == "high")
    if high_count > MAX_HIGH_PRIORITY_ISSUES:
        raise ValueError("at most 3 high-priority issues are allowed per round")
    if len(implemented_fixes) > MAX_FIXES_PER_ROUND:
        raise ValueError("at most 2 implemented fixes are allowed per round")
    return payload
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_loop.py -v
```

Expected: PASS for all three tests.

- [ ] **Step 5: Commit**

```powershell
git -C D:\gemini\lianghua\stock_team add agents/dashboard_experience_loop.py tests/test_dashboard_experience_loop.py
git -C D:\gemini\lianghua\stock_team commit -m "feat: add dashboard experience artifact validation"
```

---

### Task 3: Bootstrap a single dashboard experience round from live dashboard context

**Files:**
- Modify: `D:/gemini/lianghua/stock_team/agents/dashboard_experience_loop.py`
- Modify: `D:/gemini/lianghua/stock_team/agents/dashboard_writer.py`
- Test: `D:/gemini/lianghua/stock_team/tests/test_dashboard_experience_loop.py`

- [ ] **Step 1: Write the failing manifest bootstrap test**

```python
import json

from agents.dashboard_experience_loop import bootstrap_experience_round


def test_bootstrap_experience_round_writes_manifest_from_dashboard_context(tmp_path):
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    (base / "config" / "positions.json").write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")
    (base / "config" / "poll_config.json").write_text(json.dumps({"default_symbols": []}), encoding="utf-8")
    (base / "config" / "daily_focus.json").write_text(json.dumps({"focus_stocks": ["NOW", "NVDA"]}), encoding="utf-8")

    manifest_path = bootstrap_experience_round("2026-05-31", str(base))
    manifest = json.loads(open(manifest_path, encoding="utf-8").read())

    assert manifest["date"] == "2026-05-31"
    assert manifest["task_paths"][0]["id"] == "path_a_premarket_orientation"
    assert manifest["focus_symbols"] == ["NOW", "NVDA"]
    assert manifest["protected_scope"]["forbidden_tokens"][0] == "backtest"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_loop.py::test_bootstrap_experience_round_writes_manifest_from_dashboard_context -v
```

Expected: FAIL because `bootstrap_experience_round` does not exist yet.

- [ ] **Step 3: Add a tiny dashboard route snapshot helper in `dashboard_writer.py`**

```python
def build_dashboard_route_snapshot(ctx: dict) -> dict:
    session_state = ctx.get("session_state") or {}
    market_clock = ctx.get("market_clock") or {}
    symbols = ctx.get("symbols") or []
    return {
        "phase_label": session_state.get("market_phase") or market_clock.get("phase") or "unknown",
        "top_symbols": list(symbols[:5]),
        "has_focus": bool(symbols),
        "daily_plan_date": (ctx.get("daily_plan") or {}).get("date"),
    }
```

- [ ] **Step 4: Implement manifest bootstrap in `dashboard_experience_loop.py`**

```python
import json
import os
from datetime import datetime, timezone

from agents.dashboard_experience_paths import EXPERIENCE_PATHS, PROTECTED_SCOPE_TOKENS
from agents.dashboard_writer import build_dashboard_context, build_dashboard_route_snapshot


def bootstrap_experience_round(date_str: str, base_dir: str) -> str:
    ctx = build_dashboard_context(date_str, base_dir=base_dir)
    route_snapshot = build_dashboard_route_snapshot(ctx)
    focus_symbols = list(ctx.get("symbols") or [])
    payload = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dashboard_route_snapshot": route_snapshot,
        "focus_symbols": focus_symbols,
        "task_paths": [
            {
                "id": path.id,
                "title": path.title,
                "goal": path.goal,
                "entry_hint": path.entry_hint,
                "success_signal": path.success_signal,
            }
            for path in EXPERIENCE_PATHS
        ],
        "protected_scope": {
            "forbidden_tokens": list(PROTECTED_SCOPE_TOKENS),
        },
    }
    out_dir = os.path.join(base_dir, "findings", "dashboard_experience", date_str)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "round_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path
```

- [ ] **Step 5: Run targeted tests**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_loop.py -v
```

Expected: PASS for the new bootstrap test plus prior validation tests.

- [ ] **Step 6: Commit**

```powershell
git -C D:\gemini\lianghua\stock_team add agents/dashboard_experience_loop.py agents/dashboard_writer.py tests/test_dashboard_experience_loop.py
git -C D:\gemini\lianghua\stock_team commit -m "feat: bootstrap dashboard experience review rounds"
```

---

### Task 4: Add round summary generation for experience -> implementation -> re-check

**Files:**
- Modify: `D:/gemini/lianghua/stock_team/agents/dashboard_experience_loop.py`
- Test: `D:/gemini/lianghua/stock_team/tests/test_dashboard_experience_loop.py`

- [ ] **Step 1: Write the failing round-summary test**

```python
import json

from agents.dashboard_experience_loop import write_round_summary


def test_write_round_summary_persists_issue_fix_and_recheck_sections(tmp_path):
    summary_path = write_round_summary(
        base_dir=str(tmp_path),
        date_str="2026-05-31",
        issues=[{
            "page_module": "Today Focus",
            "task_path": "path_b_premarket_readiness",
            "problem": "Status chips dominate the ready signal.",
            "why_it_hurts": "Primary symbol is unclear.",
            "severity": "high",
            "suggested_direction": "Promote the primary ready action.",
        }],
        implemented_fixes=[{
            "title": "Promote ready action block",
            "files_touched": ["templates/daily_dashboard.html.j2"],
        }],
        recheck=[{
            "task_path": "path_b_premarket_readiness",
            "status": "improved",
            "before_problem": "Primary symbol was unclear.",
            "after_observation": "Primary symbol is visible without scanning secondary chips.",
        }],
    )
    payload = json.loads(open(summary_path, encoding="utf-8").read())
    assert payload["issue_count"] == 1
    assert payload["implemented_fix_count"] == 1
    assert payload["recheck"][0]["status"] == "improved"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_loop.py::test_write_round_summary_persists_issue_fix_and_recheck_sections -v
```

Expected: FAIL because `write_round_summary` does not exist yet.

- [ ] **Step 3: Implement round summary writer**

```python
def write_round_summary(
    *,
    base_dir: str,
    date_str: str,
    issues: list[dict],
    implemented_fixes: list[dict],
    recheck: list[dict],
) -> str:
    payload = validate_round_payload({
        "issues": issues,
        "implemented_fixes": implemented_fixes,
        "recheck": recheck,
    })
    payload["issue_count"] = len(issues)
    payload["implemented_fix_count"] = len(implemented_fixes)
    payload["recheck_count"] = len(recheck)
    out_dir = os.path.join(base_dir, "findings", "dashboard_experience", date_str)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "round_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path
```

- [ ] **Step 4: Run the loop test file again**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_loop.py -v
```

Expected: PASS for all loop tests.

- [ ] **Step 5: Commit**

```powershell
git -C D:\gemini\lianghua\stock_team add agents/dashboard_experience_loop.py tests/test_dashboard_experience_loop.py
git -C D:\gemini\lianghua\stock_team commit -m "feat: persist dashboard experience round summaries"
```

---

### Task 5: Verify no dashboard regressions and document operator entrypoints

**Files:**
- Modify: `D:/gemini/lianghua/stock_team/tests/test_dashboard_writer.py`
- Modify: `D:/gemini/lianghua/stock_team/docs/superpowers/plans/2026-05-31-dashboard-premarket-intraday-experience-loop.md`

- [ ] **Step 1: Add a regression test for the new route snapshot helper**

```python
def test_build_dashboard_route_snapshot_uses_existing_context_fields(tmp_path):
    from agents.dashboard_writer import build_dashboard_context, build_dashboard_route_snapshot

    date = "2026-05-31"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NOW"]})

    ctx = build_dashboard_context(date, symbols=["NOW"], base_dir=str(base))
    snapshot = build_dashboard_route_snapshot(ctx)

    assert snapshot["top_symbols"] == ["NOW"]
    assert snapshot["has_focus"] is True
```

- [ ] **Step 2: Run the targeted dashboard writer tests**

Run:

```powershell
pytest D:\gemini\lianghua\stock_team\tests\test_dashboard_writer.py -k "route_snapshot or build_dashboard_context" -v
```

Expected: PASS and no failures in the touched dashboard context helpers.

- [ ] **Step 3: Run the complete focused verification set**

Run:

```powershell
pytest `
  D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_paths.py `
  D:\gemini\lianghua\stock_team\tests\test_dashboard_experience_loop.py `
  D:\gemini\lianghua\stock_team\tests\test_dashboard_writer.py -v
```

Expected: PASS for all new loop tests and touched dashboard writer coverage.

- [ ] **Step 4: Add a short operator note to the plan footer for future implementers**

```markdown
## Operator Entry Points

- Bootstrap one review round: call `bootstrap_experience_round(date_str, base_dir)`
- Save validated issue/fix/recheck artifacts: call `write_round_summary(...)`
- Keep browser-based experience review outside repo runtime for v1; feed its structured results back through the validated artifact helpers.
```

- [ ] **Step 5: Commit**

```powershell
git -C D:\gemini\lianghua\stock_team add tests/test_dashboard_writer.py agents/dashboard_writer.py docs/superpowers/plans/2026-05-31-dashboard-premarket-intraday-experience-loop.md
git -C D:\gemini\lianghua\stock_team commit -m "test: cover dashboard experience loop integration"
```

---

## Self-Review

### Spec coverage

- Controlled mode-2 loop: covered by Task 2 artifact limits and Task 4 round summary.
- Fixed review paths A-D: covered by Task 1 path registry and Task 3 manifest bootstrap.
- No backtest interference: covered by Task 1 protected tokens and scope guardrails.
- No intraday load increase: preserved by keeping all new code artifact-driven and read-only against existing dashboard context.
- Future bridge to mode 3: supported by reusable manifest and summary artifacts.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Every code-changing step includes concrete code.
- Every verification step includes an exact command and expected outcome.

### Type consistency

- `task_path` IDs are defined once in Task 1 and reused consistently in Tasks 2-4.
- Issue severity values are normalized to `high|medium|low`.
- Recheck status values are normalized to `improved|unchanged|regressed`.

## Operator Entry Points

- Bootstrap one review round: call `bootstrap_experience_round(date_str, base_dir)`
- Save validated issue/fix/recheck artifacts: call `write_round_summary(...)`
- Keep browser-based experience review outside repo runtime for v1; feed its structured results back through the validated artifact helpers.

