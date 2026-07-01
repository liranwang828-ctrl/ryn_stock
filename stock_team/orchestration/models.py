from __future__ import annotations

from datetime import date, datetime


SESSION_TYPES = {"trading", "observation", "research", "review", "maintenance"}
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
    "QUICK_REVIEWED",
    "CLOSED_UNREVIEWED",
    "DAY_ARCHIVED",
    "BLOCKED_DATA",
    "WAITING_USER",
    "DEGRADED_OBSERVE",
    "FAILED_TOOL",
    "OBSERVATION_ACTIVE",
}
ACTION_INTENTS = {
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
    "refresh_market_observation",
    "record_observation_exception",
    "close_observation_day",
}
SESSION_REQUIRED = {
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
SESSION_OPTIONAL = {"market_date", "backlog_links", "last_error", "intraday_exceptions", "observation_exceptions"}
ACTION_REQUIRED = {
    "intent",
    "session_id",
    "expected_state",
    "user_confirmation",
    "parameters",
    "idempotency_key",
}


class ValidationError(ValueError):
    pass


def _require_keys(data: dict, required: set[str], optional: set[str], label: str) -> None:
    missing = required - data.keys()
    if missing:
        raise ValidationError(f"{label} missing required keys: {sorted(missing)}")
    unknown = data.keys() - required - optional
    if unknown:
        raise ValidationError(f"{label} contains unknown keys: {sorted(unknown)}")


def _require_non_empty_string(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    return value


def _require_iso_datetime(value, field: str) -> str:
    _require_non_empty_string(value, field)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO datetime") from exc
    return value


def _require_iso_date(value, field: str) -> str:
    _require_non_empty_string(value, field)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO date") from exc
    return value


def validate_session(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("session must be an object")
    _require_keys(data, SESSION_REQUIRED, SESSION_OPTIONAL, "session")
    _require_non_empty_string(data["session_id"], "session_id")
    session_type = _require_non_empty_string(data["session_type"], "session_type")
    if session_type not in SESSION_TYPES:
        raise ValidationError("session_type must be a canonical value")
    state = _require_non_empty_string(data["state"], "state")
    if state not in TRADING_STATES:
        raise ValidationError("state must be a canonical value")
    if not isinstance(data["state_version"], int) or data["state_version"] < 1:
        raise ValidationError("state_version must be an integer >= 1")
    if data.get("market_date") is not None:
        _require_iso_date(data["market_date"], "market_date")
    if not isinstance(data["artifacts"], list):
        raise ValidationError("artifacts must be a list")
    if not isinstance(data["pending_confirmations"], list):
        raise ValidationError("pending_confirmations must be a list")
    if not isinstance(data["allowed_actions"], list):
        raise ValidationError("allowed_actions must be a list")
    if not isinstance(data["processed_actions"], list):
        raise ValidationError("processed_actions must be a list")
    if "backlog_links" in data and not isinstance(data["backlog_links"], list):
        raise ValidationError("backlog_links must be a list")
    dq = data["data_quality"]
    if not isinstance(dq, dict):
        raise ValidationError("data_quality must be an object")
    if dq.keys() != {"status", "warnings"}:
        raise ValidationError("data_quality must contain status and warnings")
    if dq["status"] not in {"production_ready", "degraded", "stale", "missing", "unknown"}:
        raise ValidationError("data_quality.status must be canonical")
    if not isinstance(dq["warnings"], list):
        raise ValidationError("data_quality.warnings must be a list")
    if data.get("last_error") is not None and not isinstance(data["last_error"], dict):
        raise ValidationError("last_error must be an object or null")
    if data.get("intraday_exceptions") is not None and not isinstance(data["intraday_exceptions"], list):
        raise ValidationError("intraday_exceptions must be a list")
    if data.get("observation_exceptions") is not None and not isinstance(data["observation_exceptions"], list):
        raise ValidationError("observation_exceptions must be a list")
    _require_iso_datetime(data["updated_at"], "updated_at")
    return data


def validate_action(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("action must be an object")
    _require_keys(data, ACTION_REQUIRED, set(), "action")
    intent = _require_non_empty_string(data["intent"], "intent")
    if intent not in ACTION_INTENTS:
        raise ValidationError("intent must be a canonical value")
    _require_non_empty_string(data["session_id"], "session_id")
    _require_non_empty_string(data["expected_state"], "expected_state")
    if not isinstance(data["user_confirmation"], bool):
        raise ValidationError("user_confirmation must be a boolean")
    if not isinstance(data["parameters"], dict):
        raise ValidationError("parameters must be an object")
    _require_non_empty_string(data["idempotency_key"], "idempotency_key")
    return data


def new_trading_session(session_id: str, market_date: str, now: str, session_type: str = "trading") -> dict:
    session = {
        "session_id": session_id,
        "session_type": session_type,
        "market_date": market_date,
        "state": "DAY_INITIALIZED",
        "state_version": 1,
        "artifacts": [],
        "data_quality": {"status": "unknown", "warnings": []},
        "pending_confirmations": [],
        "allowed_actions": ["start_stage0"],
        "processed_actions": [],
        "backlog_links": [],
        "intraday_exceptions": [],
        "observation_exceptions": [],
        "last_error": None,
        "updated_at": now,
    }
    return validate_session(session)
