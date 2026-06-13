# Phase 1 Coordinator Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a thin, tested workflow coordinator that stores validated session state, enforces legal transitions and idempotency, and invokes existing `stock_team` CLI commands without changing their business logic.

**Architecture:** Create a focused `stock_team.orchestration` package containing models, a state store, transition rules, command adapters, and the coordinator service. Expose it through a separate `python -m stock_team.coordinator_cli` entry point. Store schemas and runtime state under `investing-os`, while keeping existing Evidence Packets and Stock Team commands as independent authorities for evidence.

**Tech Stack:** Python 3 standard library, JSON Schema documents, argparse, subprocess, pathlib, hashlib, pytest.

---

## Scope And Boundaries

This plan implements only architecture Phase 1:

- session and action schemas
- state model and transition validation
- atomic state storage
- idempotent action handling
- adapters around existing Stock Team CLI commands
- coordinator CLI
- targeted tests and documentation

Do not implement:

- Dashboard manifest or UI changes
- Daily Workspace
- cross-day recovery choices
- production Stage 0 collector
- research candidate adoption
- background scheduling
- broker order placement

Do not rewrite handlers inside `stock_team/cli.py`. The coordinator calls those commands as subprocesses.

## File Map

Create:

- `investing-os/system/data/schemas/session-state.schema.json`: persisted session-state contract.
- `investing-os/system/data/schemas/coordinator-action.schema.json`: coordinator action contract.
- `investing-os/system/runtime/README.md`: runtime storage rules; generated session files remain untracked.
- `stock_team/orchestration/__init__.py`: public orchestration exports.
- `stock_team/orchestration/models.py`: typed constants and dependency-free validation.
- `stock_team/orchestration/store.py`: atomic JSON state storage and write locking.
- `stock_team/orchestration/transitions.py`: legal state/action transition table.
- `stock_team/orchestration/adapters.py`: bounded subprocess adapters to existing CLI commands.
- `stock_team/orchestration/coordinator.py`: action orchestration, idempotency, artifacts, and failure recording.
- `stock_team/coordinator_cli.py`: user/machine coordinator command entry point.
- `stock_team/tests/unit/orchestration/__init__.py`: test package marker.
- `stock_team/tests/unit/orchestration/test_models.py`
- `stock_team/tests/unit/orchestration/test_store.py`
- `stock_team/tests/unit/orchestration/test_transitions.py`
- `stock_team/tests/unit/orchestration/test_adapters.py`
- `stock_team/tests/unit/orchestration/test_coordinator.py`
- `stock_team/tests/unit/orchestration/test_coordinator_cli.py`

Modify:

- `.gitignore`: ignore generated `investing-os/system/runtime/sessions/*.json`, lock files, and temporary files while retaining the README.
- `README.md`: document the coordinator entry point and boundary.
- `stock_team/docs/ACTIVE_WORKSPACE.md`: add the coordinator as the workflow entry point while preserving `stock_team.cli` as the evidence command surface.

## Canonical State And Action Values

Use these exact session types:

```python
SESSION_TYPES = {"trading", "observation", "research", "review", "maintenance"}
```

Use these exact trading states in Phase 1:

```python
TRADING_STATES = {
    "IDLE",
    "DAY_INITIALIZED",
    "STAGE0_RUNNING",
    "STAGE0_READY",
    "DISCUSSION_REQUIRED",
    "FOCUS_CONFIRMED",
    "STAGE1_RUNNING",
    "STAGE1_READY",
    "PLAN_CONFIRMATION",
    "PLAN_APPROVED",
    "INTRADAY_ACTIVE",
    "MARKET_CLOSED",
    "REVIEW_REQUIRED",
    "DAY_ARCHIVED",
    "BLOCKED_DATA",
    "WAITING_USER",
    "DEGRADED_OBSERVE",
    "FAILED_TOOL"
}
```

Phase 1 supports these actions:

```python
ACTION_INTENTS = {
    "initialize_day",
    "start_stage0",
    "record_focus_confirmation",
    "start_stage1",
    "record_plan_approval",
    "start_intraday",
    "close_market",
    "archive_day",
    "retry_last_action"
}
```

Cross-day actions such as `quick_review` and `freeze_unreviewed` belong to Phase 2.

### Task 1: Add Session And Action Schemas

**Files:**
- Create: `investing-os/system/data/schemas/session-state.schema.json`
- Create: `investing-os/system/data/schemas/coordinator-action.schema.json`
- Create: `stock_team/tests/unit/orchestration/__init__.py`
- Create: `stock_team/tests/unit/orchestration/test_models.py`

- [ ] **Step 1: Write failing schema-presence and contract tests**

```python
import json
from pathlib import Path

from stock_team.utils.workspace_paths import investing_os_home


SCHEMA_DIR = Path(investing_os_home()) / "system" / "data" / "schemas"


def test_session_schema_declares_required_state_fields():
    schema = json.loads((SCHEMA_DIR / "session-state.schema.json").read_text(encoding="utf-8"))
    assert set(schema["required"]) >= {
        "session_id", "session_type", "state", "state_version",
        "artifacts", "data_quality", "pending_confirmations",
        "allowed_actions", "processed_actions", "updated_at",
    }
    assert schema["properties"]["session_type"]["enum"] == [
        "trading", "observation", "research", "review", "maintenance"
    ]


def test_action_schema_requires_optimistic_state_and_idempotency():
    schema = json.loads((SCHEMA_DIR / "coordinator-action.schema.json").read_text(encoding="utf-8"))
    assert set(schema["required"]) >= {
        "intent", "session_id", "expected_state", "user_confirmation",
        "parameters", "idempotency_key",
    }
```

- [ ] **Step 2: Run the tests and verify they fail because schemas are missing**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_models.py -q
```

Expected: two failures with `FileNotFoundError` for the schema files.

- [ ] **Step 3: Add the complete JSON schemas**

The session schema must:

- use JSON Schema draft 2020-12
- set `additionalProperties` to `false`
- allow `market_date` to be a date string or `null`
- define `artifacts` with `role`, `path`, `sha256`, `created_at`
- define data quality statuses `production_ready`, `degraded`, `stale`, `missing`, `unknown`
- define `processed_actions` with `idempotency_key`, `intent`, `result_state`, `processed_at`
- define nullable `last_error` with `error_class`, `message`, `retryable`, `intent`, `occurred_at`

The action schema must:

- set `additionalProperties` to `false`
- use the exact Phase 1 `ACTION_INTENTS`
- require a non-empty `idempotency_key`
- allow arbitrary object content only inside `parameters`

- [ ] **Step 4: Run schema contract tests**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_models.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit the schema contracts**

```powershell
git add investing-os/system/data/schemas stock_team/tests/unit/orchestration
git commit -m "feat: define coordinator session contracts"
```

### Task 2: Implement Dependency-Free Model Validation

**Files:**
- Create: `stock_team/orchestration/__init__.py`
- Create: `stock_team/orchestration/models.py`
- Modify: `stock_team/tests/unit/orchestration/test_models.py`

- [ ] **Step 1: Add failing validation tests**

Append tests covering:

```python
import pytest

from stock_team.orchestration.models import ValidationError, validate_action, validate_session


def valid_session():
    return {
        "session_id": "trading-2026-06-15",
        "session_type": "trading",
        "market_date": "2026-06-15",
        "state": "DAY_INITIALIZED",
        "state_version": 1,
        "artifacts": [],
        "data_quality": {"status": "unknown", "warnings": []},
        "pending_confirmations": [],
        "allowed_actions": ["start_stage0"],
        "processed_actions": [],
        "backlog_links": [],
        "last_error": None,
        "updated_at": "2026-06-15T12:00:00+00:00",
    }


def test_validate_session_accepts_canonical_shape():
    assert validate_session(valid_session())["state"] == "DAY_INITIALIZED"


def test_validate_session_rejects_unknown_state():
    state = valid_session()
    state["state"] = "MADE_UP"
    with pytest.raises(ValidationError, match="state"):
        validate_session(state)


def test_validate_action_rejects_empty_idempotency_key():
    with pytest.raises(ValidationError, match="idempotency_key"):
        validate_action({
            "intent": "start_stage0",
            "session_id": "trading-2026-06-15",
            "expected_state": "DAY_INITIALIZED",
            "user_confirmation": False,
            "parameters": {},
            "idempotency_key": "",
        })
```

- [ ] **Step 2: Run the tests and verify import failure**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_models.py -q
```

Expected: collection fails because `stock_team.orchestration.models` does not exist.

- [ ] **Step 3: Implement focused validators**

`models.py` must provide:

```python
class ValidationError(ValueError):
    pass


def validate_session(data: dict) -> dict:
    """Return data after validating required keys, enums, types, and ISO dates."""


def validate_action(data: dict) -> dict:
    """Return data after validating the coordinator action contract."""


def new_trading_session(session_id: str, market_date: str, now: str) -> dict:
    """Build a validated DAY_INITIALIZED state with start_stage0 allowed."""
```

Use standard-library checks rather than adding `jsonschema`. Reject unknown top-level keys so runtime validation matches `additionalProperties: false`.

- [ ] **Step 4: Run model tests**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_models.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit model validation**

```powershell
git add stock_team/orchestration stock_team/tests/unit/orchestration/test_models.py
git commit -m "feat: validate coordinator state models"
```

### Task 3: Add Atomic Session Storage

**Files:**
- Create: `stock_team/orchestration/store.py`
- Create: `stock_team/tests/unit/orchestration/test_store.py`
- Create: `investing-os/system/runtime/README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing store tests**

```python
import json

import pytest

from stock_team.orchestration.models import new_trading_session
from stock_team.orchestration.store import SessionConflictError, SessionStore


def test_store_round_trip_and_atomic_temp_cleanup(tmp_path):
    store = SessionStore(tmp_path)
    state = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    store.create(state)
    assert store.load(state["session_id"]) == state
    assert not list(tmp_path.glob("*.tmp"))


def test_store_rejects_stale_state_version(tmp_path):
    store = SessionStore(tmp_path)
    state = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    store.create(state)
    newer = {**state, "state_version": 2, "state": "STAGE0_RUNNING"}
    with pytest.raises(SessionConflictError, match="expected version"):
        store.save(newer, expected_version=7)
```

- [ ] **Step 2: Run store tests and verify import failure**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_store.py -q
```

Expected: collection fails because `store.py` does not exist.

- [ ] **Step 3: Implement `SessionStore`**

Provide:

```python
class SessionNotFoundError(FileNotFoundError):
    pass


class SessionConflictError(RuntimeError):
    pass


class SessionBusyError(RuntimeError):
    pass


class SessionStore:
    def __init__(self, root): ...
    def create(self, state: dict) -> dict: ...
    def load(self, session_id: str) -> dict: ...
    def save(self, state: dict, expected_version: int) -> dict: ...
    def lock(self, session_id: str): ...
```

Requirements:

- reject session IDs containing path separators or `..`
- create the root directory on demand
- lock with exclusive creation of `<session_id>.lock`
- remove the lock in `finally`
- write UTF-8 JSON to `<session_id>.json.tmp`, flush and `os.fsync`, then use `os.replace`
- validate state before writing and after reading
- reject create when the session file already exists
- reject save when stored `state_version` differs from `expected_version`

- [ ] **Step 4: Add runtime documentation and ignore rules**

`investing-os/system/runtime/README.md` must state that session JSON, locks, and temp files are generated local state, while approved rules remain under existing snapshot contracts.

Add to `.gitignore`:

```gitignore
investing-os/system/runtime/sessions/*
!investing-os/system/runtime/sessions/.gitkeep
investing-os/system/runtime/*.lock
investing-os/system/runtime/*.tmp
```

Create `investing-os/system/runtime/sessions/.gitkeep` if the implementation expects the directory to exist in a fresh checkout.

- [ ] **Step 5: Run store and model tests**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_models.py stock_team\tests\unit\orchestration\test_store.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit atomic storage**

```powershell
git add .gitignore investing-os/system/runtime stock_team/orchestration/store.py stock_team/tests/unit/orchestration/test_store.py
git commit -m "feat: persist coordinator sessions atomically"
```

### Task 4: Encode Legal Transitions And Allowed Actions

**Files:**
- Create: `stock_team/orchestration/transitions.py`
- Create: `stock_team/tests/unit/orchestration/test_transitions.py`

- [ ] **Step 1: Write failing transition tests**

```python
import pytest

from stock_team.orchestration.transitions import TransitionError, begin_transition, complete_transition


def test_stage0_moves_through_running_to_ready():
    running = begin_transition("DAY_INITIALIZED", "start_stage0")
    assert running == "STAGE0_RUNNING"
    assert complete_transition(running, "start_stage0", success=True) == "STAGE0_READY"


def test_stage1_requires_focus_confirmation():
    with pytest.raises(TransitionError, match="start_stage1"):
        begin_transition("DISCUSSION_REQUIRED", "start_stage1")


def test_failed_tool_preserves_resume_state():
    result = complete_transition("STAGE1_RUNNING", "start_stage1", success=False)
    assert result == "FAILED_TOOL"


def test_allowed_actions_for_stage0_ready_requires_discussion_confirmation():
    from stock_team.orchestration.transitions import allowed_actions
    assert allowed_actions("STAGE0_READY") == ["record_focus_confirmation"]
```

- [ ] **Step 2: Run tests and verify import failure**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_transitions.py -q
```

Expected: collection fails because `transitions.py` does not exist.

- [ ] **Step 3: Implement explicit transition tables**

Use data tables, not nested condition chains:

```python
BEGIN_TRANSITIONS = {
    ("DAY_INITIALIZED", "start_stage0"): "STAGE0_RUNNING",
    ("STAGE0_READY", "record_focus_confirmation"): "FOCUS_CONFIRMED",
    ("FOCUS_CONFIRMED", "start_stage1"): "STAGE1_RUNNING",
    ("STAGE1_READY", "record_plan_approval"): "PLAN_APPROVED",
    ("PLAN_APPROVED", "start_intraday"): "INTRADAY_ACTIVE",
    ("INTRADAY_ACTIVE", "close_market"): "MARKET_CLOSED",
    ("MARKET_CLOSED", "archive_day"): "DAY_ARCHIVED",
}

SUCCESS_TRANSITIONS = {
    ("STAGE0_RUNNING", "start_stage0"): "STAGE0_READY",
    ("STAGE1_RUNNING", "start_stage1"): "STAGE1_READY",
}
```

`record_focus_confirmation` and `record_plan_approval` require `user_confirmation=True`; expose `requires_confirmation(intent)` for the coordinator.

`retry_last_action` is legal only from `FAILED_TOOL`; it resolves to the original intent stored in `last_error` and is handled by the coordinator, not directly in the table.

- [ ] **Step 4: Run transition tests**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_transitions.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit transitions**

```powershell
git add stock_team/orchestration/transitions.py stock_team/tests/unit/orchestration/test_transitions.py
git commit -m "feat: enforce coordinator state transitions"
```

### Task 5: Add Bounded Existing-CLI Adapters

**Files:**
- Create: `stock_team/orchestration/adapters.py`
- Create: `stock_team/tests/unit/orchestration/test_adapters.py`

- [ ] **Step 1: Write failing adapter tests**

```python
import subprocess

import pytest

from stock_team.orchestration.adapters import AdapterError, ExistingCliAdapter


def test_market_context_adapter_builds_existing_cli_command(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append((command, kwargs)) or subprocess.CompletedProcess(command, 0, "ok", ""))
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    adapter.run("start_stage0", {
        "date": "2026-06-15",
        "as_of": "2026-06-15T09:20:00-04:00",
        "universe": "universe.json",
        "pre_market_snapshot": "snapshot.json",
        "out": "stage0.md",
    })
    assert calls[0][0][:4] == ["python", "-m", "stock_team.cli", "market-context"]
    assert calls[0][1]["timeout"] == 30


def test_adapter_timeout_is_retryable(tmp_path, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(subprocess, "run", timeout)
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    with pytest.raises(AdapterError) as caught:
        adapter.run("start_stage0", {"date": "2026-06-15", "as_of": "x", "universe": "u", "out": "o"})
    assert caught.value.retryable is True
```

- [ ] **Step 2: Run tests and verify import failure**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_adapters.py -q
```

Expected: collection fails because `adapters.py` does not exist.

- [ ] **Step 3: Implement the adapter**

Provide:

```python
@dataclass(frozen=True)
class AdapterResult:
    command: list[str]
    stdout: str
    stderr: str
    artifact_paths: list[str]


class AdapterError(RuntimeError):
    def __init__(self, message, *, retryable, command=None, stderr=""): ...


class ExistingCliAdapter:
    def run(self, intent: str, parameters: dict) -> AdapterResult: ...
```

Phase 1 adapters:

- `start_stage0` -> `stock_team.cli market-context`
- `start_stage1` -> `stock_team.cli premarket`
- `start_intraday` -> `stock_team.cli intraday-dashboard` without `--loop`

Requirements:

- use argument arrays, never `shell=True`
- default timeout: Stage 0 `30s`, Stage 1 `60s`, intraday one-shot `30s`
- run from unified workspace root
- pass UTF-8 text capture
- classify timeout and return code `>= 2` as retryable only when stderr contains timeout/network/provider language
- classify missing arguments, invalid contract, and return code `1` validation failures as non-retryable
- verify every declared output path exists before reporting success
- return output artifact paths without reading or interpreting their business content

- [ ] **Step 4: Run adapter tests**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_adapters.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit adapters**

```powershell
git add stock_team/orchestration/adapters.py stock_team/tests/unit/orchestration/test_adapters.py
git commit -m "feat: adapt coordinator to evidence CLI"
```

### Task 6: Implement Idempotent Coordinator Actions

**Files:**
- Create: `stock_team/orchestration/coordinator.py`
- Create: `stock_team/tests/unit/orchestration/test_coordinator.py`
- Modify: `stock_team/orchestration/__init__.py`

- [ ] **Step 1: Write failing coordinator tests**

Cover these behaviors with a `FakeAdapter`:

```python
def test_initialize_day_creates_session(tmp_path): ...
def test_repeated_idempotency_key_returns_existing_result_without_second_adapter_call(tmp_path): ...
def test_stale_expected_state_is_rejected(tmp_path): ...
def test_confirmation_action_requires_user_confirmation(tmp_path): ...
def test_successful_stage0_registers_sha256_artifact_and_advances_state(tmp_path): ...
def test_adapter_failure_records_failed_tool_and_retry_metadata(tmp_path): ...
def test_retry_last_action_replays_original_intent_once(tmp_path): ...
```

The artifact assertion must calculate the expected digest from a real temporary output file:

```python
import hashlib

expected = hashlib.sha256(output_path.read_bytes()).hexdigest()
assert state["artifacts"][0]["sha256"] == expected
```

- [ ] **Step 2: Run tests and verify import failure**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_coordinator.py -q
```

Expected: collection fails because `coordinator.py` does not exist.

- [ ] **Step 3: Implement `WorkflowCoordinator`**

Public interface:

```python
class WorkflowCoordinator:
    def __init__(self, store, adapter, now_fn=None): ...
    def execute(self, action: dict) -> dict: ...
```

Execution order:

1. Validate action.
2. Handle `initialize_day` by creating a canonical session.
3. Load and lock existing session for all other actions.
4. Return the stored state immediately when `idempotency_key` is already processed.
5. Reject when `expected_state != state["state"]`.
6. Enforce `requires_confirmation`.
7. Resolve `retry_last_action` from `last_error.intent` and preserve the new idempotency key.
8. Move tool actions to their running state and save before invoking the adapter.
9. Invoke the adapter outside no more than one session lock scope; Phase 1 may hold the lock for simplicity, but document that long-running background jobs are Phase 2.
10. On success, register each artifact with role, normalized path, SHA-256, and timestamp.
11. Set success state, clear `last_error`, refresh `allowed_actions`, append processed action, increment `state_version`, and save.
12. On `AdapterError`, set `FAILED_TOOL`, preserve resume details in `last_error`, append processed action, increment version, and save.

Do not parse Packets for trading conclusions. Phase 1 records adapter success and artifacts only.

- [ ] **Step 4: Run coordinator tests**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_coordinator.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Run all orchestration unit tests**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit the coordinator service**

```powershell
git add stock_team/orchestration stock_team/tests/unit/orchestration/test_coordinator.py
git commit -m "feat: coordinate workflow actions idempotently"
```

### Task 7: Add Coordinator CLI

**Files:**
- Create: `stock_team/coordinator_cli.py`
- Create: `stock_team/tests/unit/orchestration/test_coordinator_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Use subprocess tests following `test_cli.py` conventions:

```python
def test_coordinator_cli_help(): ...
def test_coordinator_cli_initialize_and_show(tmp_path): ...
def test_coordinator_cli_run_action_from_json(tmp_path): ...
def test_coordinator_cli_returns_nonzero_for_stale_state(tmp_path): ...
```

Expected CLI:

```text
python -m stock_team.coordinator_cli init-day --date 2026-06-15 --runtime-dir <dir>
python -m stock_team.coordinator_cli run --action <action.json> --runtime-dir <dir>
python -m stock_team.coordinator_cli show --session-id trading-2026-06-15 --runtime-dir <dir>
```

- [ ] **Step 2: Run CLI tests and verify module failure**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_coordinator_cli.py -q
```

Expected: failures because `stock_team.coordinator_cli` does not exist.

- [ ] **Step 3: Implement argparse CLI**

Requirements:

- default runtime directory is `<investing_os_home>/system/runtime/sessions`
- `init-day` creates `trading-YYYY-MM-DD` with a generated UUID idempotency key
- `run` reads UTF-8 or UTF-8 BOM JSON and prints final state JSON to stdout
- `show` prints the stored state without mutation
- validation/conflict errors exit `2`
- tool failures exit `3` after printing the persisted `FAILED_TOOL` state
- unexpected errors exit `1`
- never print credentials or environment contents

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration\test_coordinator_cli.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Verify help manually**

Run:

```powershell
python -m stock_team.coordinator_cli --help
```

Expected: lists `init-day`, `run`, and `show`.

- [ ] **Step 6: Commit the CLI**

```powershell
git add stock_team/coordinator_cli.py stock_team/tests/unit/orchestration/test_coordinator_cli.py
git commit -m "feat: expose workflow coordinator CLI"
```

### Task 8: Document Boundaries And Run Regression Verification

**Files:**
- Modify: `README.md`
- Modify: `stock_team/docs/ACTIVE_WORKSPACE.md`

- [ ] **Step 1: Document the two CLI surfaces**

Add concise examples explaining:

- `python -m stock_team.coordinator_cli`: workflow state and action entry point
- `python -m stock_team.cli`: existing evidence and calculation commands
- the coordinator invokes existing commands and does not replace their logic
- generated runtime state location and Git exclusion
- Dashboard integration is Phase 2

- [ ] **Step 2: Run the complete Phase 1 suite**

Run:

```powershell
python -m pytest stock_team\tests\unit\orchestration stock_team\tests\unit\core\test_cli.py -q
```

Expected: all orchestration tests and the existing CLI contract suite pass.

- [ ] **Step 3: Run repository checks**

Run:

```powershell
git diff --check
& .\investing-os\tools\check-file-growth.ps1
```

Expected:

- `git diff --check` exits successfully.
- File growth reports no new hard-limit violation. The pre-existing soft-limit warning for `system/closed-loop-operating-architecture.md` may remain.

- [ ] **Step 4: Exercise a local state-only smoke flow**

Run:

```powershell
$runtime = Join-Path $env:TEMP 'stock-coordinator-smoke'
Remove-Item -Recurse -Force $runtime -ErrorAction SilentlyContinue
python -m stock_team.coordinator_cli init-day --date 2026-06-15 --runtime-dir $runtime
python -m stock_team.coordinator_cli show --session-id trading-2026-06-15 --runtime-dir $runtime
```

Expected:

- both commands exit `0`
- shown state is `DAY_INITIALIZED`
- `allowed_actions` contains only `start_stage0`
- state version is `1`

- [ ] **Step 5: Review the implementation against Phase 1 boundaries**

Confirm from `git diff --name-only`:

- no existing `stock_team.cli` handlers were rewritten
- no Dashboard files changed
- no order-placement code was added
- no cognition or decision files are written by Stock Team
- all generated runtime JSON remains untracked

- [ ] **Step 6: Commit documentation and verification updates**

```powershell
git add README.md stock_team/docs/ACTIVE_WORKSPACE.md
git commit -m "docs: describe coordinator workflow boundary"
```

## Phase 1 Completion Criteria

Phase 1 is complete only when:

- schemas exist and match runtime validators
- state writes are validated, atomic, versioned, and locked
- illegal and stale transitions fail without mutation
- repeated idempotency keys do not rerun tools
- Stage 0, Stage 1, and one-shot intraday adapters call existing CLI commands
- tool failure persists a recoverable `FAILED_TOOL` state
- coordinator CLI can initialize, run, and show sessions
- existing CLI contract tests still pass
- no Dashboard, production collector, adoption, or order logic has entered scope

Phase 2 must not begin until these criteria have fresh verification evidence.
