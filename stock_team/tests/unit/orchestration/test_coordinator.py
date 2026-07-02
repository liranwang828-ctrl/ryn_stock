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


def test_archive_day_failure_does_not_leave_day_archived(tmp_path):
    """archive failure must keep the session in its previous state, not DAY_ARCHIVED."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "CLOSED_UNREVIEWED"
    session["state_version"] = 5
    session["allowed_actions"] = ["archive_day"]
    session["artifacts"] = [{"logical_name": "missing", "path": str(tmp_path / "nonexistent.json")}]
    store.create(session)

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "archive_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "CLOSED_UNREVIEWED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "archive-fail",
    })
    assert state["state"] == "FAILED_TOOL"
    assert state["last_error"]["intent"] == "archive_day"

    loaded = store.load("trading-2026-06-15")
    assert loaded["state"] == "FAILED_TOOL"
    assert loaded["state"] != "DAY_ARCHIVED"


def test_archive_day_success_with_empty_artifacts(tmp_path):
    """Successful archive with no artifacts produces manifest."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "CLOSED_UNREVIEWED"
    session["state_version"] = 5
    session["allowed_actions"] = ["archive_day"]
    store.create(session)

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "archive_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "CLOSED_UNREVIEWED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "archive-ok",
    })
    assert state["state"] == "DAY_ARCHIVED"
    assert "archive_manifest_path" in state
    assert "2026-06-15" in state["archive_manifest_path"]


# ---------------------------------------------------------------------------
# H4-L2: freeze / quick_review daily4 review file generation
# ---------------------------------------------------------------------------


def test_freeze_generates_debt_record_review_file(tmp_path):
    """freeze writes a debt-record review file (empty judgments, empty lessons)."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "MARKET_CLOSED"
    session["state_version"] = 5
    session["allowed_actions"] = ["freeze"]
    store.create(session)

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "freeze",
        "session_id": "trading-2026-06-15",
        "expected_state": "MARKET_CLOSED",
        "user_confirmation": False,
        "parameters": {"ibkr_fact_status": "missing"},
        "idempotency_key": "freeze-1",
    })
    assert state["state"] == "CLOSED_UNREVIEWED"

    import json

    review_path = tmp_path.parent / "inputs" / "trading-2026-06-15-daily4-review.json"
    assert review_path.exists()
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["review_mode"] == "freeze"
    assert review["ibkr_fact_status"] == "missing"
    assert review["review_judgments"] == []
    assert review["candidate_lessons"] == []

    artifact = next(a for a in state["artifacts"] if a.get("logical_name") == "daily4_review")
    assert artifact["role"] == "freeze"
    assert artifact["path"] == str(review_path)


def test_quick_review_generates_minimal_review_file(tmp_path):
    """quick_review writes a review file with risk check judgments from parameters."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "MARKET_CLOSED"
    session["state_version"] = 5
    session["allowed_actions"] = ["quick_review"]
    store.create(session)

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "quick_review",
        "session_id": "trading-2026-06-15",
        "expected_state": "MARKET_CLOSED",
        "user_confirmation": False,
        "parameters": {
            "position_anomalies": ["position XYZ overweight"],
            "risk_deviations": ["risk limit exceeded by 2%"],
            "pending_warnings": ["IBKR fact status unverified"],
            "user_accepted": True,
        },
        "idempotency_key": "qr-1",
    })
    assert state["state"] == "QUICK_REVIEWED"

    import json

    review_path = tmp_path.parent / "inputs" / "trading-2026-06-15-daily4-review.json"
    assert review_path.exists()
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["review_mode"] == "quick_review"
    assert review["candidate_lessons"] == []
    assert len(review["review_judgments"]) == 3
    assert review["review_judgments"][0]["judgment_type"] == "execution"
    assert review["review_judgments"][0]["summary"] == "position XYZ overweight"
    assert review["review_judgments"][1]["judgment_type"] == "sizing"
    assert review["review_judgments"][2]["judgment_type"] == "data_quality"
    assert review["user_confirmations"]["bias_classification_confirmed"] is True
    assert review["archive_closure"]["user_confirmed_at"] == "2026-06-15T16:00:00+00:00"

    artifact = next(a for a in state["artifacts"] if a.get("logical_name") == "daily4_review")
    assert artifact["role"] == "quick_review"


def test_quick_review_without_user_acceptance_still_writes_file(tmp_path):
    """quick_review generates a review file even without user_accepted flag."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "MARKET_CLOSED"
    session["state_version"] = 5
    session["allowed_actions"] = ["quick_review"]
    store.create(session)

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "quick_review",
        "session_id": "trading-2026-06-15",
        "expected_state": "MARKET_CLOSED",
        "user_confirmation": False,
        "parameters": {"position_anomalies": ["unexpected position"]},
        "idempotency_key": "qr-2",
    })
    assert state["state"] == "QUICK_REVIEWED"

    import json

    review = json.loads((tmp_path.parent / "inputs" / "trading-2026-06-15-daily4-review.json").read_text(encoding="utf-8"))
    assert review["review_mode"] == "quick_review"
    assert review["user_confirmations"]["bias_classification_confirmed"] is False
    assert review["archive_closure"]["user_confirmed_at"] == ""


# ---------------------------------------------------------------------------
# H4-L3: full_review wiring and archive gates
# ---------------------------------------------------------------------------


def test_review_day_generates_full_review_skeleton(tmp_path):
    """review_day writes a full_review skeleton to the daily4 review file."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "MARKET_CLOSED"
    session["state_version"] = 5
    session["allowed_actions"] = ["review_day"]
    store.create(session)

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "review_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "MARKET_CLOSED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "review-1",
    })
    assert state["state"] == "REVIEW_REQUIRED"

    import json

    review_path = tmp_path.parent / "inputs" / "trading-2026-06-15-daily4-review.json"
    assert review_path.exists()
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["review_mode"] == "full_review"
    assert review["review_judgments"] == []
    assert review["candidate_lessons"] == []
    assert review["user_confirmations"]["bias_classification_confirmed"] is False

    artifact = next(a for a in state["artifacts"] if a.get("logical_name") == "daily4_review")
    assert artifact["role"] == "review_day"


def test_archive_day_blocks_full_review_with_unconfirmed_gates(tmp_path):
    """archive_day from REVIEW_REQUIRED blocks if user_confirmations are not all True."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "REVIEW_REQUIRED"
    session["state_version"] = 5
    session["allowed_actions"] = ["archive_day"]
    store.create(session)

    import json as _json
    from stock_team.orchestration.models import new_daily4_review

    review = new_daily4_review("trading-2026-06-15", "2026-06-15", "full_review", ibkr_fact_status="verified")
    review["user_confirmations"]["bias_classification_confirmed"] = True
    review["user_confirmations"]["emotion_notes_confirmed"] = True
    review["user_confirmations"]["noise_vs_candidate_confirmed"] = False
    review["user_confirmations"]["learning_candidates_confirmed"] = False
    review_path = tmp_path.parent / "inputs" / "trading-2026-06-15-daily4-review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(_json.dumps(review), encoding="utf-8")

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "archive_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "REVIEW_REQUIRED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "archive-blocked",
    })
    assert state["state"] == "FAILED_TOOL"
    assert "unconfirmed gates" in state["last_error"]["message"]

    loaded = store.load("trading-2026-06-15")
    assert loaded["state"] == "FAILED_TOOL"


def test_archive_day_blocks_full_review_with_unverified_ibkr(tmp_path):
    """archive_day blocks full_review if ibkr_fact_status is not verified."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "REVIEW_REQUIRED"
    session["state_version"] = 5
    session["allowed_actions"] = ["archive_day"]
    store.create(session)

    import json as _json
    from stock_team.orchestration.models import new_daily4_review

    review = new_daily4_review("trading-2026-06-15", "2026-06-15", "full_review", ibkr_fact_status="stale_unverified")
    review["user_confirmations"] = {
        "bias_classification_confirmed": True,
        "emotion_notes_confirmed": True,
        "noise_vs_candidate_confirmed": True,
        "learning_candidates_confirmed": True,
    }
    review_path = tmp_path.parent / "inputs" / "trading-2026-06-15-daily4-review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(_json.dumps(review), encoding="utf-8")

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "archive_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "REVIEW_REQUIRED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "archive-no-ibkr",
    })
    assert state["state"] == "FAILED_TOOL"
    assert "ibkr_fact_status not verified" in state["last_error"]["message"]


def test_archive_day_allows_full_review_with_all_gates_passed(tmp_path):
    """archive_day succeeds for full_review when all confirmations are True and ibkr is verified."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "REVIEW_REQUIRED"
    session["state_version"] = 5
    session["allowed_actions"] = ["archive_day"]
    store.create(session)

    import json as _json
    from stock_team.orchestration.models import new_daily4_review

    review = new_daily4_review("trading-2026-06-15", "2026-06-15", "full_review", ibkr_fact_status="verified")
    review["user_confirmations"] = {
        "bias_classification_confirmed": True,
        "emotion_notes_confirmed": True,
        "noise_vs_candidate_confirmed": True,
        "learning_candidates_confirmed": True,
    }
    review_path = tmp_path.parent / "inputs" / "trading-2026-06-15-daily4-review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(_json.dumps(review), encoding="utf-8")

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "archive_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "REVIEW_REQUIRED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "archive-ok-full",
    })
    assert state["state"] == "DAY_ARCHIVED"
    assert "archive_manifest_path" in state


def test_archive_day_allows_freeze_without_gates(tmp_path):
    """archive_day does NOT block freeze mode — gates only apply to full_review."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    session["state"] = "CLOSED_UNREVIEWED"
    session["state_version"] = 5
    session["allowed_actions"] = ["archive_day"]
    store.create(session)

    import json as _json
    from stock_team.orchestration.models import new_daily4_review

    review = new_daily4_review("trading-2026-06-15", "2026-06-15", "freeze", ibkr_fact_status="missing")
    review_path = tmp_path.parent / "inputs" / "trading-2026-06-15-daily4-review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(_json.dumps(review), encoding="utf-8")

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-15T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "archive_day",
        "session_id": "trading-2026-06-15",
        "expected_state": "CLOSED_UNREVIEWED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "archive-freeze-ok",
    })
    assert state["state"] == "DAY_ARCHIVED"


def test_archive_day_blocks_when_review_file_missing_for_full_review(tmp_path):
    """archive_day from REVIEW_REQUIRED must block if daily4 review file does not exist."""
    store = SessionStore(tmp_path)
    session = new_trading_session("trading-2026-06-16", "2026-06-16", "2026-06-16T12:00:00+00:00")
    session["state"] = "REVIEW_REQUIRED"
    session["state_version"] = 5
    session["allowed_actions"] = ["archive_day"]
    store.create(session)

    adapter = FakeAdapter()
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-06-16T16:00:00+00:00")

    state = coordinator.execute({
        "intent": "archive_day",
        "session_id": "trading-2026-06-16",
        "expected_state": "REVIEW_REQUIRED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "archive-no-file",
    })
    assert state["state"] == "FAILED_TOOL"
    assert "daily4 review file not found" in state["last_error"]["message"]

    loaded = store.load("trading-2026-06-16")
    assert loaded["state"] == "FAILED_TOOL"


# ---------------------------------------------------------------------------
# L3: start_stage0_from_snapshot coordinator isolation verification
# ---------------------------------------------------------------------------


def test_start_stage0_from_snapshot_advances_to_stage0_ready_with_artifact(tmp_path):
    """start_stage0_from_snapshot from DAY_INITIALIZED reaches STAGE0_READY with a packet artifact."""
    store = SessionStore(tmp_path)
    store.create(new_trading_session("trading-2026-07-02", "2026-07-02", "2026-07-02T12:00:00+00:00"))

    out = tmp_path / "stage0.md"
    snapshot = tmp_path / "formal_snapshot.json"
    snapshot.write_text('{"source_kind":"formal_provider_snapshot","markets":{"QQQ":{"price":736.7}}}', encoding="utf-8")

    result = make_result(tmp_path, name="stage0.md")
    adapter = FakeAdapter(result=result)
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-07-02T12:00:00+00:00")

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
        "idempotency_key": "stage0-snap-1",
    })
    assert state["state"] == "STAGE0_READY"
    assert len(state["artifacts"]) == 1
    assert state["artifacts"][0]["role"] == "start_stage0_from_snapshot"


def test_start_stage0_from_snapshot_adapter_call_has_correct_intent(tmp_path):
    """start_stage0_from_snapshot passes the correct intent to the adapter, not start_stage0."""
    store = SessionStore(tmp_path)
    store.create(new_trading_session("trading-2026-07-02", "2026-07-02", "2026-07-02T12:00:00+00:00"))

    snapshot = tmp_path / "formal_snapshot.json"
    snapshot.write_text('{"source_kind":"formal_provider_snapshot"}', encoding="utf-8")
    out = tmp_path / "stage0.md"

    result = make_result(tmp_path, name="stage0.md")
    adapter = FakeAdapter(result=result)
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-07-02T12:00:00+00:00")

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
        "idempotency_key": "stage0-snap-2",
    })
    assert len(adapter.calls) == 1
    assert adapter.calls[0][0] == "start_stage0_from_snapshot"


def test_original_start_stage0_unchanged_by_new_intent(tmp_path):
    """Existing start_stage0 path still works and passes the correct intent."""
    store = SessionStore(tmp_path)
    store.create(new_trading_session("trading-2026-07-02", "2026-07-02", "2026-07-02T12:00:00+00:00"))

    result = make_result(tmp_path, name="stage0.md")
    adapter = FakeAdapter(result=result)
    coordinator = WorkflowCoordinator(store, adapter, now_fn=lambda: "2026-07-02T12:00:00+00:00")

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
            "out": str(tmp_path / "stage0.md"),
        },
        "idempotency_key": "stage0-orig-1",
    })
    assert state["state"] == "STAGE0_READY"
    assert adapter.calls[0][0] == "start_stage0"
