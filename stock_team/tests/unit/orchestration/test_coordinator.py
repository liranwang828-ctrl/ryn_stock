import hashlib

import pytest

from stock_team.orchestration.coordinator import WorkflowCoordinator
from stock_team.orchestration.adapters import AdapterError
from stock_team.orchestration.models import new_trading_session
from stock_team.orchestration.store import SessionStore


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


def make_result(tmp_path, name="stage0.md"):
    from stock_team.orchestration.adapters import AdapterResult

    output_path = tmp_path / name
    output_path.write_text("artifact", encoding="utf-8")
    return AdapterResult(
        command=["python"],
        stdout="ok",
        stderr="",
        artifact_paths=[str(output_path)],
    )


def test_initialize_day_creates_session(tmp_path):
    store = SessionStore(tmp_path)
    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T12:00:00+00:00")
    state = coordinator.execute(
        {
            "intent": "initialize_day",
            "session_id": "trading-2026-06-15",
            "expected_state": "IDLE",
            "user_confirmation": False,
            "parameters": {"market_date": "2026-06-15"},
            "idempotency_key": "init-1",
        }
    )
    assert state["state"] == "DAY_INITIALIZED"


def test_repeated_idempotency_key_returns_existing_result_without_second_adapter_call(tmp_path):
    store = SessionStore(tmp_path)
    base = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    store.create(base)
    adapter = FakeAdapter(result=make_result(tmp_path))
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T12:00:00+00:00")
    action = {
        "intent": "start_stage0",
        "session_id": "trading-2026-06-15",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {
            "date": "2026-06-15",
            "as_of": "2026-06-15T09:20:00-04:00",
            "universe": "u.json",
            "pre_market_snapshot": "s.json",
            "out": str(tmp_path / "stage0.md"),
        },
        "idempotency_key": "stage0-1",
    }
    first = coordinator.execute(action)
    second = coordinator.execute(action)
    assert first == second
    assert len(adapter.calls) == 1


def test_stale_expected_state_is_rejected(tmp_path):
    store = SessionStore(tmp_path)
    store.create(new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00"))
    coordinator = WorkflowCoordinator(store, FakeAdapter(), now_fn=lambda: "2026-06-15T12:00:00+00:00")
    with pytest.raises(ValueError, match="expected_state"):
        coordinator.execute(
            {
                "intent": "start_stage0",
                "session_id": "trading-2026-06-15",
                "expected_state": "STAGE0_READY",
                "user_confirmation": False,
                "parameters": {
                    "date": "2026-06-15",
                    "as_of": "2026-06-15T09:20:00-04:00",
                    "universe": "u.json",
                    "pre_market_snapshot": "s.json",
                    "out": str(tmp_path / "stage0.md"),
                },
                "idempotency_key": "stage0-1",
            }
        )


def test_successful_stage0_registers_sha256_artifact_and_advances_state(tmp_path):
    store = SessionStore(tmp_path)
    store.create(new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00"))
    result = make_result(tmp_path)
    coordinator = WorkflowCoordinator(store, FakeAdapter(result=result), now_fn=lambda: "2026-06-15T12:00:00+00:00")
    state = coordinator.execute(
        {
            "intent": "start_stage0",
            "session_id": "trading-2026-06-15",
            "expected_state": "DAY_INITIALIZED",
            "user_confirmation": False,
            "parameters": {
                "date": "2026-06-15",
                "as_of": "2026-06-15T09:20:00-04:00",
                "universe": "u.json",
                "pre_market_snapshot": "s.json",
                "out": str(tmp_path / "stage0.md"),
            },
            "idempotency_key": "stage0-1",
        }
    )
    expected = hashlib.sha256((tmp_path / "stage0.md").read_bytes()).hexdigest()
    assert state["state"] == "STAGE0_READY"
    assert state["artifacts"][0]["sha256"] == expected


def test_adapter_failure_records_failed_tool_and_retry_metadata(tmp_path):
    store = SessionStore(tmp_path)
    store.create(new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00"))
    adapter = FakeAdapter(error=AdapterError("network timeout", retryable=True, command=["python"], stderr="timeout"))
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T12:00:00+00:00")
    state = coordinator.execute(
        {
            "intent": "start_stage0",
            "session_id": "trading-2026-06-15",
            "expected_state": "DAY_INITIALIZED",
            "user_confirmation": False,
            "parameters": {
                "date": "2026-06-15",
                "as_of": "2026-06-15T09:20:00-04:00",
                "universe": "u.json",
                "pre_market_snapshot": "s.json",
                "out": str(tmp_path / "stage0.md"),
            },
            "idempotency_key": "stage0-fail-1",
        }
    )
    assert state["state"] == "FAILED_TOOL"
    assert state["last_error"]["retryable"] is True
    assert state["last_error"]["intent"] == "start_stage0"
    assert state["allowed_actions"] == ["retry_last_action"]


def test_retry_last_action_replays_original_intent_once(tmp_path):
    store = SessionStore(tmp_path)
    store.create(new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00"))
    failing = FakeAdapter(error=AdapterError("network timeout", retryable=True, command=["python"], stderr="timeout"))
    coordinator = WorkflowCoordinator(store, failing, now_fn=lambda: "2026-06-15T12:00:00+00:00")
    coordinator.execute(
        {
            "intent": "start_stage0",
            "session_id": "trading-2026-06-15",
            "expected_state": "DAY_INITIALIZED",
            "user_confirmation": False,
            "parameters": {
                "date": "2026-06-15",
                "as_of": "2026-06-15T09:20:00-04:00",
                "universe": "u.json",
                "pre_market_snapshot": "s.json",
                "out": str(tmp_path / "stage0.md"),
            },
            "idempotency_key": "stage0-fail-1",
        }
    )
    succeeding = FakeAdapter(result=make_result(tmp_path))
    retry_coordinator = WorkflowCoordinator(store, succeeding, now_fn=lambda: "2026-06-15T12:00:01+00:00")
    state = retry_coordinator.execute(
        {
            "intent": "retry_last_action",
            "session_id": "trading-2026-06-15",
            "expected_state": "FAILED_TOOL",
            "user_confirmation": False,
            "parameters": {},
            "idempotency_key": "retry-1",
        }
    )
    assert state["state"] == "STAGE0_READY"
    assert len(succeeding.calls) == 1
    assert succeeding.calls[0][0] == "start_stage0"


def test_intraday_exception_requires_user_confirmation(tmp_path):
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "INTRADAY_ACTIVE"
    session["state_version"] = 5
    session["allowed_actions"] = ["close_market", "request_exception"]
    store.create(session)

    adapter = FakeAdapter(result=make_result(tmp_path))
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T14:30:00+00:00")

    with pytest.raises(ValueError, match="requires user_confirmation"):
        coordinator.execute(
            {
                "intent": "request_exception",
                "session_id": "trading-2026-06-15",
                "expected_state": "INTRADAY_ACTIVE",
                "user_confirmation": False,
                "parameters": {"reason": "unexpected volatility", "detail": "SPX dropped 2% in 5 min"},
                "idempotency_key": "exc-1",
            }
        )

    state = coordinator.execute(
        {
            "intent": "request_exception",
            "session_id": "trading-2026-06-15",
            "expected_state": "INTRADAY_ACTIVE",
            "user_confirmation": True,
            "parameters": {"reason": "unexpected volatility", "detail": "SPX dropped 2% in 5 min"},
            "idempotency_key": "exc-2",
        }
    )
    assert state["state"] == "INTRADAY_ACTIVE"
    assert len(state["intraday_exceptions"]) == 1
    assert state["intraday_exceptions"][0]["reason"] == "unexpected volatility"
    assert state["intraday_exceptions"][0]["confirmed_at"] == "2026-06-15T14:30:00+00:00"
