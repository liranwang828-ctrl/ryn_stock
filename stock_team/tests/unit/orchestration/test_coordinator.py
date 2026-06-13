from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


class FakeAdapter:
    def __init__(self, outputs=None, *, error=None):
        self.outputs = outputs or {}
        self.error = error
        self.calls = []

    def run(self, intent, parameters):
        self.calls.append((intent, parameters))
        if self.error is not None:
            raise self.error
        result = self.outputs[intent]
        if callable(result):
            return result(intent, parameters)
        return result


def _write_packet(path: Path, content: str = "packet") -> None:
    path.write_text(content, encoding="utf-8")


def test_initialize_day_creates_session(tmp_path):
    from stock_team.orchestration.coordinator import WorkflowCoordinator
    from stock_team.orchestration.store import SessionStore

    coordinator = WorkflowCoordinator(SessionStore(tmp_path), FakeAdapter(), now_fn=lambda: "2026-06-15T12:00:00+00:00")
    state = coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-06-15"},
        "idempotency_key": "init-1",
    })

    assert state["state"] == "DAY_INITIALIZED"
    assert state["allowed_actions"] == ["start_stage0"]
    assert state["state_version"] == 1
    assert (tmp_path / "trading-2026-06-15.json").exists()


def test_repeated_idempotency_key_returns_existing_result_without_second_adapter_call(tmp_path):
    from stock_team.orchestration.coordinator import WorkflowCoordinator
    from stock_team.orchestration.store import SessionStore

    out = tmp_path / "stage0.md"
    adapter = FakeAdapter(
        outputs={
            "start_stage0": lambda intent, params: type("R", (), {
                "command": ["python"],
                "stdout": "ok",
                "stderr": "",
                "artifact_paths": [str(out)],
            })()
        }
    )
    coordinator = WorkflowCoordinator(SessionStore(tmp_path), adapter, now_fn=lambda: "2026-06-15T12:00:00+00:00")
    coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-06-15"},
        "idempotency_key": "init-1",
    })
    _write_packet(out)
    first = coordinator.execute({
        "intent": "start_stage0",
        "session_id": "trading-2026-06-15",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {
            "date": "2026-06-15",
            "as_of": "2026-06-15T09:20:00-04:00",
            "universe": "universe.json",
            "out": str(out),
        },
        "idempotency_key": "stage0-1",
    })
    second = coordinator.execute({
        "intent": "start_stage0",
        "session_id": "trading-2026-06-15",
        "expected_state": "STAGE0_READY",
        "user_confirmation": False,
        "parameters": {
            "date": "2026-06-15",
            "as_of": "2026-06-15T09:20:00-04:00",
            "universe": "universe.json",
            "out": str(out),
        },
        "idempotency_key": "stage0-1",
    })

    assert first == second
    assert len(adapter.calls) == 1


def test_stale_expected_state_is_rejected(tmp_path):
    from stock_team.orchestration.coordinator import WorkflowCoordinator
    from stock_team.orchestration.store import SessionStore

    out = tmp_path / "stage0.md"
    def run_stage0(intent, parameters):
        _write_packet(out, "stage0 packet")
        return type("R", (), {"command": ["python"], "stdout": "ok", "stderr": "", "artifact_paths": [str(out)]})()

    coordinator = WorkflowCoordinator(SessionStore(tmp_path), FakeAdapter(), now_fn=lambda: "2026-06-15T12:00:00+00:00")
    coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-06-15"},
        "idempotency_key": "init-1",
    })
    coordinator = WorkflowCoordinator(SessionStore(tmp_path), FakeAdapter(outputs={"start_stage0": run_stage0}), now_fn=lambda: "2026-06-15T12:00:00+00:00")
    coordinator.execute({
        "intent": "start_stage0",
        "session_id": "trading-2026-06-15",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {"date": "2026-06-15", "as_of": "2026-06-15T09:20:00-04:00", "universe": "u", "out": str(out)},
        "idempotency_key": "stage0-1",
    })

    with pytest.raises(ValueError, match="expected_state"):
        coordinator.execute({
            "intent": "start_stage0",
            "session_id": "trading-2026-06-15",
            "expected_state": "DAY_INITIALIZED",
            "user_confirmation": False,
            "parameters": {"date": "2026-06-15", "as_of": "2026-06-15T09:20:00-04:00", "universe": "u", "out": "s.md"},
            "idempotency_key": "stage0-2",
        })


def test_confirmation_action_requires_user_confirmation(tmp_path):
    from stock_team.orchestration.coordinator import WorkflowCoordinator
    from stock_team.orchestration.store import SessionStore

    out = tmp_path / "stage0.md"

    def run_stage0(intent, parameters):
        _write_packet(out, "stage0 packet")
        return type("R", (), {"command": ["python"], "stdout": "ok", "stderr": "", "artifact_paths": [str(out)]})()

    coordinator = WorkflowCoordinator(
        SessionStore(tmp_path),
        FakeAdapter(outputs={"start_stage0": run_stage0}),
        now_fn=lambda: "2026-06-15T12:00:00+00:00",
    )
    coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-06-15"},
        "idempotency_key": "init-1",
    })
    coordinator.execute({
        "intent": "start_stage0",
        "session_id": "trading-2026-06-15",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {"date": "2026-06-15", "as_of": "2026-06-15T09:20:00-04:00", "universe": "u", "out": str(out)},
        "idempotency_key": "stage0-1",
    })

    with pytest.raises(ValueError, match="user_confirmation"):
        coordinator.execute({
            "intent": "record_focus_confirmation",
            "session_id": "trading-2026-06-15",
            "expected_state": "STAGE0_READY",
            "user_confirmation": False,
            "parameters": {},
            "idempotency_key": "focus-1",
        })


def test_successful_stage0_registers_sha256_artifact_and_advances_state(tmp_path):
    from stock_team.orchestration.coordinator import WorkflowCoordinator
    from stock_team.orchestration.store import SessionStore

    out = tmp_path / "stage0.md"

    def run_stage0(intent, parameters):
        _write_packet(out, "stage0 packet")
        return type("R", (), {"command": ["python"], "stdout": "ok", "stderr": "", "artifact_paths": [str(out)]})()

    coordinator = WorkflowCoordinator(
        SessionStore(tmp_path),
        FakeAdapter(outputs={"start_stage0": run_stage0}),
        now_fn=lambda: "2026-06-15T12:00:00+00:00",
    )
    coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-06-15"},
        "idempotency_key": "init-1",
    })
    state = coordinator.execute({
        "intent": "start_stage0",
        "session_id": "trading-2026-06-15",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {"date": "2026-06-15", "as_of": "2026-06-15T09:20:00-04:00", "universe": "u", "out": str(out)},
        "idempotency_key": "stage0-1",
    })

    assert state["state"] == "STAGE0_READY"
    assert state["artifacts"][0]["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert state["processed_actions"][-1]["result_state"] == "STAGE0_READY"


def test_adapter_failure_records_failed_tool_and_retry_metadata(tmp_path):
    from stock_team.orchestration.adapters import AdapterError
    from stock_team.orchestration.coordinator import WorkflowCoordinator
    from stock_team.orchestration.store import SessionStore

    coordinator = WorkflowCoordinator(
        SessionStore(tmp_path),
        FakeAdapter(error=AdapterError("boom", retryable=True, command=["python"], stderr="timeout")),
        now_fn=lambda: "2026-06-15T12:00:00+00:00",
    )
    coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-06-15"},
        "idempotency_key": "init-1",
    })
    state = coordinator.execute({
        "intent": "start_stage0",
        "session_id": "trading-2026-06-15",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {"date": "2026-06-15", "as_of": "2026-06-15T09:20:00-04:00", "universe": "u", "out": "stage0.md"},
        "idempotency_key": "stage0-1",
    })

    assert state["state"] == "FAILED_TOOL"
    assert state["last_error"]["retryable"] is True
    assert state["last_error"]["intent"] == "start_stage0"


def test_retry_last_action_replays_original_intent_once(tmp_path):
    from stock_team.orchestration.adapters import AdapterError
    from stock_team.orchestration.coordinator import WorkflowCoordinator
    from stock_team.orchestration.store import SessionStore

    out = tmp_path / "stage0.md"
    attempts = {"count": 0}

    def run_stage0(intent, parameters):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise AdapterError("boom", retryable=True, command=["python"], stderr="timeout")
        _write_packet(out, "stage0 packet")
        return type("R", (), {"command": ["python"], "stdout": "ok", "stderr": "", "artifact_paths": [str(out)]})()

    coordinator = WorkflowCoordinator(
        SessionStore(tmp_path),
        FakeAdapter(outputs={"start_stage0": run_stage0}),
        now_fn=lambda: "2026-06-15T12:00:00+00:00",
    )
    coordinator.execute({
        "intent": "initialize_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "IDLE",
        "user_confirmation": False,
        "parameters": {"market_date": "2026-06-15"},
        "idempotency_key": "init-1",
    })
    failed = coordinator.execute({
        "intent": "start_stage0",
        "session_id": "trading-2026-06-15",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {"date": "2026-06-15", "as_of": "2026-06-15T09:20:00-04:00", "universe": "u", "out": str(out)},
        "idempotency_key": "stage0-1",
    })
    retried = coordinator.execute({
        "intent": "retry_last_action",
        "session_id": "trading-2026-06-15",
        "expected_state": "FAILED_TOOL",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "retry-1",
    })

    assert failed["state"] == "FAILED_TOOL"
    assert retried["state"] == "STAGE0_READY"
    assert attempts["count"] == 2
