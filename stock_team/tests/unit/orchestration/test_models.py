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
    assert session["allowed_actions"] == ["start_stage0"]


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
    for readonly in ("intraday-snapshot", "close_market", "archive_day"):
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
