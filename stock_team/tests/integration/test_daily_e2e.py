from __future__ import annotations

import json

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

    # Verify archive manifest
    session = new_trading_session("s1", "2026-07-01", "2026-07-01T09:00:00+00:00")
    session["state"] = "DAY_ARCHIVED"
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "report.json").write_text('{"status":"done"}', encoding="utf-8")

    archive_dir = tmp_path / "archive"
    manifest_path = archive_session(session, str(artifacts_dir), archive_dir=str(archive_dir))

    manifest = json.loads(open(manifest_path, encoding="utf-8").read())
    assert manifest["session_id"] == "s1"
    assert manifest["date"] == "2026-07-01"
    assert "archived_at" in manifest
    assert isinstance(manifest["artifacts"], list)
    assert len(manifest["artifacts"]) == 1
    assert manifest["artifacts"][0]["name"] == "report.json"


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

    # Verify archive manifest
    session = new_trading_session("s2", "2026-07-01", "2026-07-01T09:00:00+00:00")
    session["state"] = "DAY_ARCHIVED"
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "quick_report.json").write_text('{"status":"done"}', encoding="utf-8")

    archive_dir = tmp_path / "archive"
    manifest_path = archive_session(session, str(artifacts_dir), archive_dir=str(archive_dir))

    manifest = json.loads(open(manifest_path, encoding="utf-8").read())
    assert manifest["session_id"] == "s2"
    assert "archived_at" in manifest
    assert len(manifest["artifacts"]) == 1
    assert manifest["artifacts"][0]["name"] == "quick_report.json"


def test_trading_freeze_path():
    """Trading path ending with freeze — session stays CLOSED_UNREVIEWED, never archived."""
    state = _walk_to_market_closed()

    # MARKET_CLOSED -> CLOSED_UNREVIEWED (no archive)
    assert "freeze" in allowed_actions(state)
    state = begin_transition(state, "freeze")
    assert state == "CLOSED_UNREVIEWED"

    # Verify CLOSED_UNREVIEWED has no further transitions
    assert allowed_actions("CLOSED_UNREVIEWED") == []
    assert "archive_day" not in allowed_actions("CLOSED_UNREVIEWED")

    # Verify archive_day is NOT legal from CLOSED_UNREVIEWED
    with pytest.raises(TransitionError, match="archive_day"):
        begin_transition("CLOSED_UNREVIEWED", "archive_day")


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

    # Verify archive manifest
    session = new_trading_session("obs1", "2026-07-01", "2026-07-01T09:00:00+00:00", session_type="observation")
    session["state"] = "DAY_ARCHIVED"
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "obs_report.json").write_text('{"status":"observed"}', encoding="utf-8")

    archive_dir = tmp_path / "archive"
    manifest_path = archive_session(session, str(artifacts_dir), archive_dir=str(archive_dir))

    manifest = json.loads(open(manifest_path, encoding="utf-8").read())
    assert manifest["session_id"] == "obs1"
    assert manifest["date"] == "2026-07-01"
    assert "archived_at" in manifest


def test_observation_direct_archive(tmp_path):
    """Observation direct archive: OBSERVATION_ACTIVE -> archive_day -> DAY_ARCHIVED."""
    state = _walk_observation_to_active()

    # Direct archive from OBSERVATION_ACTIVE (skip MARKET_CLOSED)
    assert "archive_day" in allowed_actions("OBSERVATION_ACTIVE")
    state = begin_transition(state, "archive_day")
    assert state == "DAY_ARCHIVED"

    # Verify archive manifest
    session = new_trading_session("obs2", "2026-07-01", "2026-07-01T09:00:00+00:00", session_type="observation")
    session["state"] = "DAY_ARCHIVED"
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "direct_obs.json").write_text('{"status":"observed_direct"}', encoding="utf-8")

    archive_dir = tmp_path / "archive"
    manifest_path = archive_session(session, str(artifacts_dir), archive_dir=str(archive_dir))

    manifest = json.loads(open(manifest_path, encoding="utf-8").read())
    assert manifest["session_id"] == "obs2"
    assert len(manifest["artifacts"]) == 1
    assert manifest["artifacts"][0]["name"] == "direct_obs.json"


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
    for terminal in ("DAY_ARCHIVED", "CLOSED_UNREVIEWED"):
        assert allowed_actions(terminal) == []
        with pytest.raises(TransitionError):
            begin_transition(terminal, "start_stage0")


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
    assert session["allowed_actions"] == ["start_stage0"]
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
