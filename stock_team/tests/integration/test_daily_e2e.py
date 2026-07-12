from __future__ import annotations

import json
from pathlib import Path

import pytest

from stock_team.orchestration.adapters import AdapterError, AdapterResult
from stock_team.orchestration.archiver import archive_session
from stock_team.orchestration.coordinator import WorkflowCoordinator
from stock_team.orchestration.models import new_trading_session
from stock_team.orchestration.store import SessionStore
from stock_team.orchestration.transitions import (
    TransitionError,
    allowed_actions,
    begin_transition,
    complete_transition,
    requires_confirmation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeAdapter:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def run(self, intent, parameters):
        self.calls.append((intent, parameters))
        if self.error:
            raise self.error
        return self.result


def _make_result(tmp_path, name="artifact.txt"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / name
    path.write_text("artifact content", encoding="utf-8")
    return AdapterResult(command=["python"], stdout="ok", stderr="", artifact_paths=[str(path)])


def _walk_stage0():
    """DAY_INITIALIZED -> STAGE0_RUNNING -> STAGE0_READY -> FOCUS_CONFIRMED"""
    assert "start_stage0" in allowed_actions("DAY_INITIALIZED")
    state = begin_transition("DAY_INITIALIZED", "start_stage0")
    assert state == "STAGE0_RUNNING"
    state = complete_transition(state, "start_stage0", success=True)
    assert state == "STAGE0_READY"

    assert "record_focus_confirmation" in allowed_actions(state)
    assert requires_confirmation("record_focus_confirmation")
    state = begin_transition(state, "record_focus_confirmation")
    assert state == "FOCUS_CONFIRMED"
    return state


def _walk_stage1(state):
    """FOCUS_CONFIRMED -> STAGE1_RUNNING -> STAGE1_READY -> PLAN_APPROVED"""
    assert "start_stage1" in allowed_actions(state)
    state = begin_transition(state, "start_stage1")
    assert state == "STAGE1_RUNNING"
    state = complete_transition(state, "start_stage1", success=True)
    assert state == "STAGE1_READY"

    assert "record_plan_approval" in allowed_actions(state)
    assert requires_confirmation("record_plan_approval")
    state = begin_transition(state, "record_plan_approval")
    assert state == "PLAN_APPROVED"
    return state


def _walk_to_intraday():
    """Full walk: DAY_INITIALIZED -> ... -> INTRADAY_ACTIVE"""
    state = _walk_stage0()
    state = _walk_stage1(state)
    assert "start_intraday" in allowed_actions(state)
    state = begin_transition(state, "start_intraday")
    assert state == "INTRADAY_ACTIVE"
    return state


def _walk_to_market_closed():
    """Full walk: DAY_INITIALIZED -> ... -> MARKET_CLOSED"""
    state = _walk_to_intraday()
    assert "close_market" in allowed_actions(state)
    state = begin_transition(state, "close_market")
    assert state == "MARKET_CLOSED"
    return state


def _walk_observation_to_active():
    """Observation path: DAY_INITIALIZED -> ... -> FOCUS_CONFIRMED -> OBSERVATION_ACTIVE"""
    state = _walk_stage0()
    assert "start_observation" in allowed_actions(state)
    state = begin_transition(state, "start_observation")
    assert state == "OBSERVATION_ACTIVE"
    return state


# ---------------------------------------------------------------------------
# Trading path tests
# ---------------------------------------------------------------------------

def test_trading_full_path(tmp_path):
    """Full trading path from DAY_INITIALIZED to DAY_ARCHIVED via review_day."""
    state = _walk_to_market_closed()

    # MARKET_CLOSED -> REVIEW_REQUIRED -> DAY_ARCHIVED
    assert "review_day" in allowed_actions(state)
    state = begin_transition(state, "review_day")
    assert state == "REVIEW_REQUIRED"

    assert "archive_day" in allowed_actions(state)
    state = begin_transition(state, "archive_day")
    assert state == "DAY_ARCHIVED"

    # Verify archive via new API (L2: artifact_ledger whitelist)
    _verify_archive_manifest(tmp_path, "s1", "2026-07-01", [("report.json", '{"status":"done"}')])


def test_trading_quick_review_path(tmp_path):
    """Trading path ending with quick_review instead of full review."""
    state = _walk_to_market_closed()

    # MARKET_CLOSED -> QUICK_REVIEWED -> DAY_ARCHIVED
    assert "quick_review" in allowed_actions(state)
    state = begin_transition(state, "quick_review")
    assert state == "QUICK_REVIEWED"

    assert "archive_day" in allowed_actions(state)
    state = begin_transition(state, "archive_day")
    assert state == "DAY_ARCHIVED"

    _verify_archive_manifest(tmp_path, "s2", "2026-07-01", [("quick_report.json", '{"status":"done"}')])


def test_trading_freeze_path():
    """Trading path ending with freeze — session goes to CLOSED_UNREVIEWED, can be archived later."""
    state = _walk_to_market_closed()

    # MARKET_CLOSED -> CLOSED_UNREVIEWED
    assert "freeze" in allowed_actions(state)
    state = begin_transition(state, "freeze")
    assert state == "CLOSED_UNREVIEWED"

    # CLOSED_UNREVIEWED can be archived (L3: enables freeze+archive recovery)
    assert allowed_actions("CLOSED_UNREVIEWED") == ["archive_day"]
    assert "archive_day" in allowed_actions("CLOSED_UNREVIEWED")

    # archive_day from CLOSED_UNREVIEWED -> DAY_ARCHIVED
    state = begin_transition("CLOSED_UNREVIEWED", "archive_day")
    assert state == "DAY_ARCHIVED"


# ---------------------------------------------------------------------------
# Observation path tests
# ---------------------------------------------------------------------------

def test_observation_path(tmp_path):
    """Observation path through MARKET_CLOSED to DAY_ARCHIVED."""
    state = _walk_observation_to_active()

    # OBSERVATION_ACTIVE -> MARKET_CLOSED -> DAY_ARCHIVED
    assert "close_market" in allowed_actions(state)
    state = begin_transition(state, "close_market")
    assert state == "MARKET_CLOSED"

    # MARKET_CLOSED -> archive_day (skip review for observation)
    # Note: archive_day is NOT directly reachable from MARKET_CLOSED;
    # observation path goes through archive_day from OBSERVATION_ACTIVE or
    # via one of the MARKET_CLOSED exits. We use quick_review as a fast path.
    assert "quick_review" in allowed_actions(state)
    state = begin_transition(state, "quick_review")
    assert state == "QUICK_REVIEWED"

    assert "archive_day" in allowed_actions(state)
    state = begin_transition(state, "archive_day")
    assert state == "DAY_ARCHIVED"

    # Verify no trading actions are available in OBSERVATION_ACTIVE
    obs_actions = allowed_actions("OBSERVATION_ACTIVE")
    for trading_intent in ("start_intraday", "record_plan_approval", "start_stage1"):
        assert trading_intent not in obs_actions
    assert "close_market" in obs_actions
    assert "archive_day" in obs_actions
    assert "refresh_market_observation" in obs_actions

    _verify_archive_manifest(tmp_path, "obs1", "2026-07-01", [("obs_report.json", '{"status":"observed"}')])


def test_observation_direct_archive(tmp_path):
    """Observation direct archive: OBSERVATION_ACTIVE -> archive_day -> DAY_ARCHIVED."""
    state = _walk_observation_to_active()

    # Direct archive from OBSERVATION_ACTIVE (skip MARKET_CLOSED)
    assert "archive_day" in allowed_actions("OBSERVATION_ACTIVE")
    state = begin_transition(state, "archive_day")
    assert state == "DAY_ARCHIVED"

    _verify_archive_manifest(tmp_path, "obs2", "2026-07-01", [("direct_obs.json", '{"status":"observed_direct"}')])


# ---------------------------------------------------------------------------
# Intraday exception flow
# ---------------------------------------------------------------------------

def test_intraday_exception_flow(tmp_path):
    """Exception during intraday: self-loop with user_confirmation, stay INTRADAY_ACTIVE."""
    state = _walk_to_intraday()

    # request_exception is allowed and is a self-loop
    assert "request_exception" in allowed_actions(state)
    assert requires_confirmation("request_exception")

    # The self-loop: request_exception returns to INTRADAY_ACTIVE
    next_state = begin_transition(state, "request_exception")
    assert next_state == "INTRADAY_ACTIVE"

    # request_exception fails WITHOUT user_confirmation at the Coordinator level
    store = SessionStore(tmp_path / "sessions")
    session = new_trading_session("exc-session", "2026-07-01", "2026-07-01T09:00:00+00:00")
    session["state"] = "INTRADAY_ACTIVE"
    session["state_version"] = 5
    session["allowed_actions"] = ["close_market", "request_exception"]
    store.create(session)

    adapter = FakeAdapter(result=_make_result(tmp_path / "artifacts"))
    coordinator = WorkflowCoordinator(
        store, adapter, now_fn=lambda: "2026-07-01T14:30:00+00:00"
    )

    # Without user_confirmation -> error
    with pytest.raises(ValueError, match="requires user_confirmation"):
        coordinator.execute({
            "intent": "request_exception",
            "session_id": "exc-session",
            "expected_state": "INTRADAY_ACTIVE",
            "user_confirmation": False,
            "parameters": {"reason": "unexpected drop", "detail": "SPX -2% in 5min"},
            "idempotency_key": "exc-no-confirm",
        })

    # With user_confirmation -> succeeds, stays INTRADAY_ACTIVE
    state = coordinator.execute({
        "intent": "request_exception",
        "session_id": "exc-session",
        "expected_state": "INTRADAY_ACTIVE",
        "user_confirmation": True,
        "parameters": {"reason": "unexpected drop", "detail": "SPX -2% in 5min"},
        "idempotency_key": "exc-yes-confirm",
    })
    assert state["state"] == "INTRADAY_ACTIVE"
    assert len(state["intraday_exceptions"]) == 1
    assert state["intraday_exceptions"][0]["reason"] == "unexpected drop"
    assert state["intraday_exceptions"][0]["confirmed_by_user"] is True

    # After exception, can still close_market
    assert "close_market" in allowed_actions(state["state"])
    close_state = coordinator.execute({
        "intent": "close_market",
        "session_id": "exc-session",
        "expected_state": "INTRADAY_ACTIVE",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "exc-close",
    })
    assert close_state["state"] == "MARKET_CLOSED"


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------

def test_invalid_transitions_rejected():
    """Verify invalid state jumps are rejected with TransitionError."""
    # DAY_INITIALIZED -> start_intraday is not legal
    assert "start_intraday" not in allowed_actions("DAY_INITIALIZED")
    with pytest.raises(TransitionError, match="start_intraday"):
        begin_transition("DAY_INITIALIZED", "start_intraday")

    # FOCUS_CONFIRMED -> close_market is not legal
    assert "close_market" not in allowed_actions("FOCUS_CONFIRMED")
    with pytest.raises(TransitionError, match="close_market"):
        begin_transition("FOCUS_CONFIRMED", "close_market")

    # STAGE0_READY -> start_intraday is not legal
    assert "start_intraday" not in allowed_actions("STAGE0_READY")
    with pytest.raises(TransitionError, match="start_intraday"):
        begin_transition("STAGE0_READY", "start_intraday")

    # INTRADAY_ACTIVE -> record_focus_confirmation is not legal
    assert "record_focus_confirmation" not in allowed_actions("INTRADAY_ACTIVE")
    with pytest.raises(TransitionError, match="record_focus_confirmation"):
        begin_transition("INTRADAY_ACTIVE", "record_focus_confirmation")

    # PLAN_APPROVED -> archive_day is not legal
    assert "archive_day" not in allowed_actions("PLAN_APPROVED")
    with pytest.raises(TransitionError, match="archive_day"):
        begin_transition("PLAN_APPROVED", "archive_day")

    # Verify all expected terminal states do not accept random intents
    for terminal in ("DAY_ARCHIVED",):
        assert allowed_actions(terminal) == []
        with pytest.raises(TransitionError):
            begin_transition(terminal, "start_stage0")
    # CLOSED_UNREVIEWED is not fully terminal in L3: allows archive_day
    assert allowed_actions("CLOSED_UNREVIEWED") == ["archive_day"]
    with pytest.raises(TransitionError):
        begin_transition("CLOSED_UNREVIEWED", "start_stage0")


# ---------------------------------------------------------------------------
# Confirmation actions
# ---------------------------------------------------------------------------

def test_confirmation_actions():
    """Verify that the three confirmation-requiring intents are correctly identified."""
    confirm_actions = {"record_focus_confirmation", "record_plan_approval", "request_exception"}
    for intent in confirm_actions:
        assert requires_confirmation(intent), f"{intent} should require confirmation"

    non_confirm = {"start_stage0", "start_stage1", "start_intraday", "close_market",
                   "review_day", "quick_review", "freeze", "archive_day",
                   "start_observation", "retry_last_action"}
    for intent in non_confirm:
        assert not requires_confirmation(intent), f"{intent} should NOT require confirmation"


# ---------------------------------------------------------------------------
# Session store integration
# ---------------------------------------------------------------------------

def test_session_store_persistence_across_path(tmp_path):
    """SessionStore correctly persists and loads state through the full trading path."""
    store = SessionStore(tmp_path / "sessions")
    adapter = FakeAdapter(result=_make_result(tmp_path / "artifacts"))

    now = "2026-07-01T09:00:00+00:00"
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: now)

    state = coordinator.execute({
        "intent": "initialize_day",
        "session_id": "e2e-persist",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-07-01"},
        "idempotency_key": "persist-init",
    })
    assert state["state"] == "DAY_INITIALIZED"

    # Reload from store and verify
    loaded = store.load("e2e-persist")
    assert loaded["state"] == "DAY_INITIALIZED"
    assert loaded["session_id"] == "e2e-persist"
    assert loaded["session_type"] == "trading"


def test_new_trading_session_defaults():
    """new_trading_session produces a valid session with correct initial state."""
    session = new_trading_session("test-session", "2026-07-01", "2026-07-01T09:00:00+00:00")
    assert session["state"] == "DAY_INITIALIZED"
    assert session["state_version"] == 1
    assert session["allowed_actions"] == ["start_stage0", "start_stage0_from_snapshot"]
    assert session["session_type"] == "trading"
    assert session["data_quality"]["status"] == "unknown"
    assert session["pending_confirmations"] == []
    assert session["processed_actions"] == []
    assert session["intraday_exceptions"] == []


def test_new_trading_session_observation_type():
    """new_trading_session supports observation session type."""
    session = new_trading_session("obs-session", "2026-07-01", "2026-07-01T09:00:00+00:00",
                                  session_type="observation")
    assert session["session_type"] == "observation"
    assert session["state"] == "DAY_INITIALIZED"


# ---------------------------------------------------------------------------
# Archive helper (L2: artifact_ledger whitelist API)
# ---------------------------------------------------------------------------

def _verify_archive_manifest(tmp_path, session_id, market_date, artifact_specs):
    """Create artifacts, call archiver with L2 API, verify manifest."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True)
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True)
    artifact_ledger = []
    for name, content in artifact_specs:
        path = artifacts_dir / name
        path.write_text(content, encoding="utf-8")
        artifact_ledger.append({"logical_name": name, "path": str(path)})

    session_file = sessions_dir / f"{session_id}.json"
    session_data = {
        "session_id": session_id,
        "session_type": "trading",
        "state": "DAY_ARCHIVED",
        "state_version": 10,
        "market_date": market_date,
        "artifacts": artifact_ledger,
        "data_quality": {"status": "unknown", "warnings": []},
        "pending_confirmations": [],
        "allowed_actions": [],
        "processed_actions": [],
        "updated_at": "2026-07-01T16:00:00+00:00",
    }
    session_file.write_text(json.dumps(session_data), encoding="utf-8")

    archive_root = tmp_path / "archive"
    manifest, manifest_path = archive_session(
        session_id=session_id,
        trading_date=market_date,
        session_file=str(session_file),
        artifact_ledger=artifact_ledger,
        archive_root=str(archive_root),
    )

    assert Path(manifest_path).exists()
    assert manifest["session_id"] == session_id
    assert manifest["trading_date"] == market_date
    assert "archived_at" in manifest
    assert manifest["status"] == "complete"
    assert isinstance(manifest["files"], list)
    assert len(manifest["files"]) == len(artifact_specs)
    for f in manifest["files"]:
        assert f["status"] == "archived"
        assert f["sha256"]
        assert f["size_bytes"] > 0


# ---------------------------------------------------------------------------
# L3: start_stage0_from_snapshot E2E
# ---------------------------------------------------------------------------


def test_e2e_start_stage0_from_snapshot_reaches_stage0_ready(tmp_path):
    """E2E: init-day -> start_stage0_from_snapshot with formal snapshot -> STAGE0_READY."""
    store = SessionStore(tmp_path)
    snapshot = tmp_path / "formal_snapshot.json"
    snapshot.write_text(
        '{"source_kind":"formal_provider_snapshot","markets":{"QQQ":{"price":736.7}}}',
        encoding="utf-8",
    )
    out = tmp_path / "packet.md"
    out.write_text("", encoding="utf-8")

    result = AdapterResult(
        command=["python", "-m", "stock_team.cli", "market-context", "--pre-market-snapshot", str(snapshot)],
        stdout="ok",
        stderr="",
        artifact_paths=[str(out)],
    )
    adapter = FakeAdapter(result=result)
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-07-02T12:00:00+00:00")

    init = coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-07-02",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-07-02"},
        "idempotency_key": "init-1",
    })
    assert init["state"] == "DAY_INITIALIZED"

    state = coordinator.execute({
        "intent": "start_stage0_from_snapshot",
        "session_id": "trading-2026-07-02",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {
            "date": "2026-07-02",
            "as_of": "2026-07-02T09:20:00-04:00",
            "universe": "u.json",
            "pre_market_snapshot": str(snapshot),
            "out": str(out),
        },
        "idempotency_key": "snap-1",
    })
    assert state["state"] == "STAGE0_READY"
    assert len(state["artifacts"]) >= 1
    assert state["artifacts"][0]["role"] == "start_stage0_from_snapshot"


def test_e2e_original_start_stage0_still_reaches_stage0_ready(tmp_path):
    """E2E regression: init-day -> start_stage0 (original) still works."""
    store = SessionStore(tmp_path)
    out = tmp_path / "packet.md"
    out.write_text("", encoding="utf-8")

    result = AdapterResult(command=["python"], stdout="ok", stderr="", artifact_paths=[str(out)])
    adapter = FakeAdapter(result=result)
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-07-02T12:00:00+00:00")

    state = coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-07-02",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-07-02"},
        "idempotency_key": "init-1",
    })
    assert state["state"] == "DAY_INITIALIZED"

    state = coordinator.execute({
        "intent": "start_stage0",
        "session_id": "trading-2026-07-02",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {
            "date": "2026-07-02",
            "as_of": "2026-07-02T09:20:00-04:00",
            "universe": "u.json",
            "pre_market_snapshot": "s.json",
            "out": str(out),
        },
        "idempotency_key": "stage0-1",
    })
    assert state["state"] == "STAGE0_READY"
    assert adapter.calls[0][0] == "start_stage0"


def test_e2e_start_stage0_from_snapshot_adapter_called_with_correct_intent(tmp_path):
    """E2E: start_stage0_from_snapshot sends correct intent to adapter, not start_stage0."""
    store = SessionStore(tmp_path)
    snapshot = tmp_path / "formal_snapshot.json"
    snapshot.write_text('{"source_kind":"formal_provider_snapshot"}', encoding="utf-8")
    out = tmp_path / "packet.md"
    out.write_text("", encoding="utf-8")

    result = AdapterResult(command=["python"], stdout="ok", stderr="", artifact_paths=[str(out)])
    adapter = FakeAdapter(result=result)
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-07-02T12:00:00+00:00")

    coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-07-02",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-07-02"},
        "idempotency_key": "init-1",
    })

    coordinator.execute({
        "intent": "start_stage0_from_snapshot",
        "session_id": "trading-2026-07-02",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {
            "date": "2026-07-02",
            "as_of": "2026-07-02T09:20:00-04:00",
            "universe": "u.json",
            "pre_market_snapshot": str(snapshot),
            "out": str(out),
        },
        "idempotency_key": "snap-1",
    })
    assert adapter.calls[0][0] == "start_stage0_from_snapshot"


def test_e2e_current_daily_status_never_reuses_old_session_artifacts(tmp_path):
    from stock_team.orchestration.daily_status import build_daily_status
    from stock_team.server.dashboard_server import _select_dashboard_session

    runtime_root = tmp_path / "runtime"
    inputs = runtime_root / "inputs"
    packets = runtime_root / "packets"
    inputs.mkdir(parents=True)
    packets.mkdir()

    old = new_trading_session(
        "trading-2026-07-10",
        "2026-07-10",
        "2026-07-10T08:00:00-04:00",
        session_type="observation",
    )
    old["state"] = "DAY_ARCHIVED"
    current = new_trading_session(
        "trading-2026-07-13",
        "2026-07-13",
        "2026-07-13T08:00:00-04:00",
        session_type="observation",
    )
    current["daily0_confirmation"] = {
        "confirmed_at": "2026-07-13T08:01:00-04:00",
        "activity_mode": "observation",
        "account_fact_status": "stale_unverified",
        "account_snapshot_ref": "runtime/inputs/account.json",
        "analysis_scope_ref": "runtime/inputs/universe.json",
        "user_confirmed": True,
    }
    (inputs / "trading-2026-07-10-stage0-universe.json").write_text(json.dumps({
        "date": "2026-07-10",
        "source_inputs": {"positions": [], "prior_review": {}, "cognition_state": {}},
        "permission_state_before_open": "Yellow",
        "forbidden_actions": [],
    }), encoding="utf-8")
    (packets / "trading-2026-07-10-stage0-market-context.md").write_text("# old context\n", encoding="utf-8")

    selection = _select_dashboard_session(
        [old, current],
        {"trading_date": "2026-07-13", "calendar_status": "verified"},
    )
    manifest = build_daily_status(
        session=selection["session"],
        runtime_root=runtime_root,
        active_trading_date="2026-07-13",
    )

    assert selection["session_kind"] == "current"
    assert selection["session"]["session_id"] == "trading-2026-07-13"
    assert manifest["current_step"] == "DAILY-1A"
    assert manifest["overall_status"] == "waiting_data"
    assert all(item["present"] is False for item in manifest["artifacts"])


def test_e2e_abandon_failed_session_archives_debt_and_retained_artifacts(tmp_path):
    runtime = tmp_path / "runtime"
    store = SessionStore(runtime / "sessions")
    session = new_trading_session(
        "trading-2026-06-15",
        "2026-06-15",
        "2026-06-15T12:00:00+00:00",
    )
    session["state"] = "FAILED_TOOL"
    session["state_version"] = 3
    session["allowed_actions"] = ["retry_last_action", "abandon_failed_session"]
    session["last_error"] = {
        "error_class": "AdapterError",
        "message": "historical failure",
        "retryable": False,
        "intent": "start_stage0",
        "parameters": {},
        "resume_from_state": "DAY_INITIALIZED",
        "occurred_at": "2026-06-15T12:00:00+00:00",
    }
    store.create(session)
    inputs = runtime / "inputs"
    packets = runtime / "packets"
    inputs.mkdir()
    packets.mkdir()
    retained = inputs / "trading-2026-06-15-stage0-universe.json"
    retained.write_text('{"date":"2026-06-15"}', encoding="utf-8")
    other = packets / "trading-2026-07-13-stage0-market-context.md"
    other.write_text("# other session", encoding="utf-8")
    coordinator = WorkflowCoordinator(store, FakeAdapter(), now_fn=lambda: "2026-07-12T14:00:00+08:00")

    closed = coordinator.execute({
        "intent": "abandon_failed_session",
        "session_id": "trading-2026-06-15",
        "expected_state": "FAILED_TOOL",
        "user_confirmation": True,
        "parameters": {"reason": "historical non-retryable stage0 failure"},
        "idempotency_key": "abandon-1",
    })
    archived = coordinator.execute({
        "intent": "archive_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "CLOSED_UNREVIEWED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "archive-1",
    })

    assert closed["state"] == "CLOSED_UNREVIEWED"
    assert archived["state"] == "DAY_ARCHIVED"
    archive_manifest = json.loads(Path(archived["archive_manifest_path"]).read_text(encoding="utf-8"))
    assert archive_manifest["status"] == "complete"
    archived_sources = {item["source_path"] for item in archive_manifest["files"]}
    assert str(retained) in archived_sources
    assert str(inputs / "trading-2026-06-15-daily4-review.json") in archived_sources
    assert str(other) not in archived_sources
