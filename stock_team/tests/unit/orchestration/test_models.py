import json
from pathlib import Path

import pytest

from stock_team.orchestration.models import ValidationError, new_trading_session, validate_action, validate_session
from stock_team.utils.workspace_paths import investing_os_home


SCHEMA_DIR = Path(investing_os_home()) / "system" / "data" / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_session_schema_declares_required_state_fields():
    schema = load_schema("session-state.schema.json")

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "session_id",
        "session_type",
        "state",
        "state_version",
        "artifacts",
        "data_quality",
        "pending_confirmations",
        "allowed_actions",
        "processed_actions",
        "updated_at",
    }
    assert schema["properties"]["session_type"]["enum"] == [
        "trading",
        "observation",
        "research",
        "review",
        "maintenance",
    ]
    assert schema["properties"]["state"]["enum"] == [
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
        "QUICK_REVIEWED",
        "CLOSED_UNREVIEWED",
        "DAY_ARCHIVED",
        "BLOCKED_DATA",
        "WAITING_USER",
        "DEGRADED_OBSERVE",
        "FAILED_TOOL",
        "OBSERVATION_ACTIVE",
    ]
    assert schema["properties"]["market_date"] == {
        "anyOf": [
            {"type": "string", "format": "date"},
            {"type": "null"},
        ]
    }
    assert schema["properties"]["artifacts"]["items"]["required"] == [
        "role",
        "path",
        "sha256",
        "created_at",
    ]
    assert schema["properties"]["data_quality"]["properties"]["status"]["enum"] == [
        "production_ready",
        "degraded",
        "stale",
        "missing",
        "unknown",
    ]
    assert schema["properties"]["data_quality"]["required"] == ["status", "warnings"]
    assert schema["properties"]["processed_actions"]["items"]["required"] == [
        "idempotency_key",
        "intent",
        "result_state",
        "processed_at",
    ]
    assert "backlog_links" in schema["properties"]
    assert "intraday_exceptions" in schema["properties"]
    assert schema["properties"]["last_error"] == {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "error_class",
                    "message",
                    "retryable",
                    "intent",
                    "occurred_at",
                ],
                "properties": {
                    "error_class": {"type": "string"},
                    "message": {"type": "string"},
                    "retryable": {"type": "boolean"},
                    "intent": {"type": "string"},
                    "occurred_at": {"type": "string", "format": "date-time"},
                },
            },
            {"type": "null"},
        ]
    }
    assert schema["properties"]["updated_at"] == {"type": "string", "format": "date-time"}


def test_action_schema_requires_optimistic_state_and_idempotency():
    schema = load_schema("coordinator-action.schema.json")

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "intent",
        "session_id",
        "expected_state",
        "user_confirmation",
        "parameters",
        "idempotency_key",
    }
    assert schema["properties"]["intent"]["enum"] == [
        "initialize_day",
        "start_stage0",
        "record_focus_confirmation",
        "start_stage1",
        "record_plan_approval",
        "start_intraday",
        "close_market",
        "review_day",
        "quick_review",
        "freeze",
        "archive_day",
        "retry_last_action",
        "start_observation",
        "request_exception",
    ]
    assert schema["properties"]["session_id"] == {"type": "string"}
    assert schema["properties"]["expected_state"] == {"type": "string"}
    assert schema["properties"]["user_confirmation"] == {"type": "boolean"}
    assert schema["properties"]["parameters"] == {"type": "object"}
    assert schema["properties"]["idempotency_key"] == {
        "type": "string",
        "minLength": 1,
    }


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
        "allowed_actions": ["start_stage0", "start_stage0_from_snapshot"],
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


def test_new_session_supports_all_session_types():
    from stock_team.orchestration.models import SESSION_TYPES

    for stype in sorted(SESSION_TYPES):
        session = new_trading_session(
            session_id=f"{stype}-2026-06-15",
            market_date="2026-06-15",
            now="2026-06-15T12:00:00+00:00",
            session_type=stype,
        )
        assert session["session_type"] == stype
        assert session["state"] == "DAY_INITIALIZED"


def test_new_trading_session_builds_valid_initial_state():
    session = new_trading_session(
        session_id="trading-2026-06-15",
        market_date="2026-06-15",
        now="2026-06-15T12:00:00+00:00",
    )
    assert session["state"] == "DAY_INITIALIZED"
    assert session["allowed_actions"] == ["start_stage0", "start_stage0_from_snapshot"]


def test_observation_active_state_exists():
    from stock_team.orchestration.models import TRADING_STATES

    assert "OBSERVATION_ACTIVE" in TRADING_STATES


def test_observation_active_forbids_trading_actions():
    from stock_team.orchestration.transitions import allowed_actions

    actions = allowed_actions("OBSERVATION_ACTIVE")
    for trading_intent in ("start_stage0", "start_stage1", "record_plan_approval", "start_intraday"):
        assert trading_intent not in actions, f"OBSERVATION_ACTIVE must not allow {trading_intent}"


def test_observation_active_allows_readonly_actions():
    from stock_team.orchestration.transitions import allowed_actions

    actions = allowed_actions("OBSERVATION_ACTIVE")
    for readonly in ("refresh_market_observation", "close_market", "close_observation_day", "archive_day"):
        assert readonly in actions, f"OBSERVATION_ACTIVE must allow {readonly}"


def test_review_required_in_trading_states():
    from stock_team.orchestration.models import TRADING_STATES

    assert "REVIEW_REQUIRED" in TRADING_STATES


def test_quick_reviewed_in_trading_states():
    from stock_team.orchestration.models import TRADING_STATES

    assert "QUICK_REVIEWED" in TRADING_STATES


def test_closed_unreviewed_in_trading_states():
    from stock_team.orchestration.models import TRADING_STATES

    assert "CLOSED_UNREVIEWED" in TRADING_STATES


# ---------------------------------------------------------------------------
# H4-L1: daily4 review schema validation
# ---------------------------------------------------------------------------


def _valid_review(**overrides):
    review = {
        "session_id": "trading-2026-07-01",
        "trading_date": "2026-07-01",
        "review_mode": "full_review",
        "ibkr_fact_status": "verified",
        "fact_packet_refs": [],
        "review_judgments": [],
        "candidate_lessons": [],
        "user_confirmations": {
            "bias_classification_confirmed": True,
            "emotion_notes_confirmed": True,
            "noise_vs_candidate_confirmed": True,
            "learning_candidates_confirmed": True,
        },
        "archive_closure": {
            "archive_manifest_path": "/path/to/manifest.json",
            "user_confirmed_at": "2026-07-01T16:00:00+00:00",
        },
    }
    review.update(overrides)
    return review


def test_validate_daily4_review_accepts_full_review():
    from stock_team.orchestration.models import validate_daily4_review

    result = validate_daily4_review(_valid_review())
    assert result["session_id"] == "trading-2026-07-01"
    assert result["review_mode"] == "full_review"


def test_validate_daily4_review_rejects_invalid_review_mode():
    from stock_team.orchestration.models import ValidationError, validate_daily4_review

    with pytest.raises(ValidationError, match="review_mode"):
        validate_daily4_review(_valid_review(review_mode="made_up_mode"))


def test_validate_daily4_review_rejects_invalid_ibkr_fact_status():
    from stock_team.orchestration.models import ValidationError, validate_daily4_review

    with pytest.raises(ValidationError, match="ibkr_fact_status"):
        validate_daily4_review(_valid_review(ibkr_fact_status="garbage"))


def test_validate_daily4_review_rejects_invalid_judgment_type():
    from stock_team.orchestration.models import ValidationError, validate_daily4_review

    review = _valid_review(review_judgments=[{
        "judgment_type": "invalid_type",
        "summary": "test",
        "evidence_refs": [],
        "confidence": "low",
        "source": "assistant_inferred",
    }])
    with pytest.raises(ValidationError, match="judgment_type"):
        validate_daily4_review(review)


def test_validate_daily4_review_rejects_invalid_confidence():
    from stock_team.orchestration.models import ValidationError, validate_daily4_review

    review = _valid_review(review_judgments=[{
        "judgment_type": "execution",
        "summary": "test",
        "evidence_refs": [],
        "confidence": "extreme",
        "source": "user_confirmed",
    }])
    with pytest.raises(ValidationError, match="confidence"):
        validate_daily4_review(review)


def test_validate_daily4_review_rejects_invalid_source():
    from stock_team.orchestration.models import ValidationError, validate_daily4_review

    review = _valid_review(review_judgments=[{
        "judgment_type": "thesis",
        "summary": "test",
        "evidence_refs": [],
        "confidence": "medium",
        "source": "made_up_source",
    }])
    with pytest.raises(ValidationError, match="source"):
        validate_daily4_review(review)


def test_validate_daily4_review_rejects_invalid_user_decision():
    from stock_team.orchestration.models import ValidationError, validate_daily4_review

    review = _valid_review(candidate_lessons=[{
        "candidate_id": "c1",
        "theme": "test",
        "statement": "test",
        "supporting_evidence_refs": [],
        "requires_followup": False,
        "user_decision": "definitely_adopt",
    }])
    with pytest.raises(ValidationError, match="user_decision"):
        validate_daily4_review(review)


def test_validate_daily4_review_rejects_non_bool_confirmation():
    from stock_team.orchestration.models import ValidationError, validate_daily4_review

    review = _valid_review()
    review["user_confirmations"]["bias_classification_confirmed"] = "yes"
    with pytest.raises(ValidationError, match="must be a boolean"):
        validate_daily4_review(review)


def test_validate_daily4_review_rejects_missing_archive_closure_field():
    from stock_team.orchestration.models import ValidationError, validate_daily4_review

    review = _valid_review()
    review["archive_closure"] = {"archive_manifest_path": "/p"}
    with pytest.raises(ValidationError, match="user_confirmed_at"):
        validate_daily4_review(review)


def test_validate_daily4_review_accepts_all_review_modes():
    from stock_team.orchestration.models import validate_daily4_review

    for mode in ("full_review", "quick_review", "freeze"):
        result = validate_daily4_review(_valid_review(review_mode=mode))
        assert result["review_mode"] == mode


def test_validate_daily4_review_accepts_all_ibkr_statuses():
    from stock_team.orchestration.models import validate_daily4_review

    for status in ("verified", "stale_unverified", "missing"):
        result = validate_daily4_review(_valid_review(ibkr_fact_status=status))
        assert result["ibkr_fact_status"] == status


def test_new_daily4_review_creates_valid_full_review():
    from stock_team.orchestration.models import new_daily4_review

    review = new_daily4_review("trading-2026-07-01", "2026-07-01", "full_review")
    assert review["session_id"] == "trading-2026-07-01"
    assert review["trading_date"] == "2026-07-01"
    assert review["review_mode"] == "full_review"
    assert review["ibkr_fact_status"] == "stale_unverified"
    assert review["fact_packet_refs"] == []
    assert review["review_judgments"] == []
    assert review["candidate_lessons"] == []
    assert review["user_confirmations"]["bias_classification_confirmed"] is False
    assert review["archive_closure"]["archive_manifest_path"] == ""


def test_new_daily4_review_supports_explicit_ibkr_status():
    from stock_team.orchestration.models import new_daily4_review

    review = new_daily4_review("trading-2026-07-01", "2026-07-01", "freeze", ibkr_fact_status="missing")
    assert review["review_mode"] == "freeze"
    assert review["ibkr_fact_status"] == "missing"


def test_daily4_review_path_returns_inputs_dir():
    from stock_team.orchestration.protocol import daily4_review_path

    path = daily4_review_path("trading-2026-07-01")
    assert path.name == "trading-2026-07-01-daily4-review.json"
    assert "inputs" in str(path).lower()


# ---------------------------------------------------------------------------
# L1: start_stage0_from_snapshot canonical intent
# ---------------------------------------------------------------------------


def test_validate_action_accepts_start_stage0_from_snapshot():
    result = validate_action({
        "intent": "start_stage0_from_snapshot",
        "session_id": "trading-2026-07-01",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "key-1",
    })
    assert result["intent"] == "start_stage0_from_snapshot"


def test_start_stage0_still_validates():
    """Existing start_stage0 must still be accepted by validate_action."""
    result = validate_action({
        "intent": "start_stage0",
        "session_id": "trading-2026-07-01",
        "expected_state": "DAY_INITIALIZED",
        "user_confirmation": False,
        "parameters": {},
        "idempotency_key": "key-2",
    })
    assert result["intent"] == "start_stage0"


# ---------------------------------------------------------------------------
# R1: new_trading_session allowed_actions includes start_stage0_from_snapshot
# ---------------------------------------------------------------------------


def test_new_trading_session_allowed_actions_includes_both_stage0_intents():
    """R1: new_trading_session() must expose both start_stage0
    and start_stage0_from_snapshot as allowed actions at DAY_INITIALIZED."""
    session = new_trading_session(
        session_id="trading-2026-07-03",
        market_date="2026-07-03",
        now="2026-07-03T09:00:00-04:00",
    )
    assert "start_stage0" in session["allowed_actions"]
    assert "start_stage0_from_snapshot" in session["allowed_actions"]
    assert len(session["allowed_actions"]) == 2
