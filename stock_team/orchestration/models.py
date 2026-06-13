from __future__ import annotations

from datetime import date, datetime
from typing import Any


SESSION_TYPES = (
    "trading",
    "observation",
    "research",
    "review",
    "maintenance",
)

TRADING_STATES = (
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
    "FAILED_TOOL",
)

ACTION_INTENTS = (
    "initialize_day",
    "start_stage0",
    "record_focus_confirmation",
    "start_stage1",
    "record_plan_approval",
    "start_intraday",
    "close_market",
    "archive_day",
    "retry_last_action",
)

DATA_QUALITY = (
    "production_ready",
    "degraded",
    "stale",
    "missing",
    "unknown",
)

_SESSION_REQUIRED_KEYS = {
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
_SESSION_OPTIONAL_KEYS = {"market_date", "backlog_links", "last_error"}
_SESSION_ALLOWED_KEYS = _SESSION_REQUIRED_KEYS | _SESSION_OPTIONAL_KEYS

_ACTION_REQUIRED_KEYS = {
    "intent",
    "session_id",
    "expected_state",
    "user_confirmation",
    "parameters",
    "idempotency_key",
}
_ACTION_ALLOWED_KEYS = _ACTION_REQUIRED_KEYS


class ValidationError(ValueError):
    pass


def _fail(field: str, message: str) -> None:
    raise ValidationError(f"{field}: {message}")


def _ensure_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(field, "must be an object")
    return value


def _ensure_exact_keys(data: dict[str, Any], *, required: set[str], allowed: set[str], context: str) -> None:
    missing = [key for key in required if key not in data]
    if missing:
        _fail(context, f"missing required key {missing[0]!r}")
    unknown = [key for key in data if key not in allowed]
    if unknown:
        _fail(context, f"unexpected top-level key {unknown[0]!r}")


def _ensure_string(value: Any, field: str, *, nonempty: bool = False) -> str:
    if not isinstance(value, str):
        _fail(field, "must be a string")
    if nonempty and value == "":
        _fail(field, "must not be empty")
    return value


def _ensure_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        _fail(field, "must be a boolean")
    return value


def _ensure_int(value: Any, field: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        _fail(field, "must be an integer")
    if minimum is not None and value < minimum:
        _fail(field, f"must be >= {minimum}")
    return value


def _ensure_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(field, "must be an array")
    return value


def _ensure_date(value: Any, field: str) -> str:
    text = _ensure_string(value, field)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        _fail(field, f"must be ISO date: {exc}")
    return text


def _ensure_datetime(value: Any, field: str) -> str:
    text = _ensure_string(value, field)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        _fail(field, f"must be ISO datetime: {exc}")
    return text


def _validate_artifact(item: Any, index: int) -> None:
    artifact = _ensure_dict(item, f"artifacts[{index}]")
    _ensure_exact_keys(
        artifact,
        required={"role", "path", "sha256", "created_at"},
        allowed={"role", "path", "sha256", "created_at"},
        context=f"artifacts[{index}]",
    )
    _ensure_string(artifact["role"], f"artifacts[{index}].role")
    _ensure_string(artifact["path"], f"artifacts[{index}].path")
    sha256 = _ensure_string(artifact["sha256"], f"artifacts[{index}].sha256")
    if len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
        _fail(f"artifacts[{index}].sha256", "must be 64 lowercase hex characters")
    _ensure_datetime(artifact["created_at"], f"artifacts[{index}].created_at")


def _validate_confirmation(item: Any, index: int) -> None:
    confirmation = _ensure_dict(item, f"pending_confirmations[{index}]")
    _ensure_exact_keys(
        confirmation,
        required={"intent", "requested_at"},
        allowed={"intent", "requested_at", "reason"},
        context=f"pending_confirmations[{index}]",
    )
    _ensure_string(confirmation["intent"], f"pending_confirmations[{index}].intent")
    _ensure_datetime(
        confirmation["requested_at"], f"pending_confirmations[{index}].requested_at"
    )
    if "reason" in confirmation:
        _ensure_string(confirmation["reason"], f"pending_confirmations[{index}].reason")


def _validate_processed_action(item: Any, index: int) -> None:
    processed = _ensure_dict(item, f"processed_actions[{index}]")
    _ensure_exact_keys(
        processed,
        required={"idempotency_key", "intent", "result_state", "processed_at"},
        allowed={"idempotency_key", "intent", "result_state", "processed_at"},
        context=f"processed_actions[{index}]",
    )
    _ensure_string(processed["idempotency_key"], f"processed_actions[{index}].idempotency_key")
    _ensure_string(processed["intent"], f"processed_actions[{index}].intent")
    _ensure_string(processed["result_state"], f"processed_actions[{index}].result_state")
    _ensure_datetime(processed["processed_at"], f"processed_actions[{index}].processed_at")


def _validate_backlog_link(item: Any, index: int) -> None:
    link = _ensure_dict(item, f"backlog_links[{index}]")
    _ensure_exact_keys(
        link,
        required={"label", "href"},
        allowed={"label", "href", "note"},
        context=f"backlog_links[{index}]",
    )
    _ensure_string(link["label"], f"backlog_links[{index}].label")
    _ensure_string(link["href"], f"backlog_links[{index}].href")
    if "note" in link:
        _ensure_string(link["note"], f"backlog_links[{index}].note")


def _validate_last_error(value: Any) -> None:
    if value is None:
        return
    error = _ensure_dict(value, "last_error")
    _ensure_exact_keys(
        error,
        required={"error_class", "message", "retryable", "intent", "occurred_at"},
        allowed={"error_class", "message", "retryable", "intent", "occurred_at"},
        context="last_error",
    )
    _ensure_string(error["error_class"], "last_error.error_class")
    _ensure_string(error["message"], "last_error.message")
    _ensure_bool(error["retryable"], "last_error.retryable")
    _ensure_string(error["intent"], "last_error.intent")
    _ensure_datetime(error["occurred_at"], "last_error.occurred_at")


def validate_session(data: dict[str, Any]) -> dict[str, Any]:
    session = _ensure_dict(data, "session")
    _ensure_exact_keys(
        session,
        required=_SESSION_REQUIRED_KEYS,
        allowed=_SESSION_ALLOWED_KEYS,
        context="session",
    )

    _ensure_string(session["session_id"], "session.session_id")
    if session["session_type"] not in SESSION_TYPES:
        _fail("session.session_type", f"must be one of {SESSION_TYPES}")
    if session["state"] not in TRADING_STATES:
        _fail("session.state", f"must be one of {TRADING_STATES}")
    _ensure_int(session["state_version"], "session.state_version", minimum=1)

    if "market_date" in session and session["market_date"] is not None:
        _ensure_date(session["market_date"], "session.market_date")

    artifacts = _ensure_list(session["artifacts"], "session.artifacts")
    for index, item in enumerate(artifacts):
        _validate_artifact(item, index)

    data_quality = _ensure_dict(session["data_quality"], "session.data_quality")
    _ensure_exact_keys(
        data_quality,
        required={"status", "warnings"},
        allowed={"status", "warnings"},
        context="session.data_quality",
    )
    if data_quality["status"] not in DATA_QUALITY:
        _fail("session.data_quality.status", f"must be one of {DATA_QUALITY}")
    warnings = _ensure_list(data_quality["warnings"], "session.data_quality.warnings")
    for index, warning in enumerate(warnings):
        _ensure_string(warning, f"session.data_quality.warnings[{index}]")

    confirmations = _ensure_list(
        session["pending_confirmations"], "session.pending_confirmations"
    )
    for index, item in enumerate(confirmations):
        _validate_confirmation(item, index)

    allowed_actions = _ensure_list(session["allowed_actions"], "session.allowed_actions")
    for index, action in enumerate(allowed_actions):
        _ensure_string(action, f"session.allowed_actions[{index}]")

    processed_actions = _ensure_list(session["processed_actions"], "session.processed_actions")
    for index, item in enumerate(processed_actions):
        _validate_processed_action(item, index)

    if "backlog_links" in session:
        backlog_links = _ensure_list(session["backlog_links"], "session.backlog_links")
        for index, item in enumerate(backlog_links):
            _validate_backlog_link(item, index)

    if "last_error" in session:
        _validate_last_error(session["last_error"])

    _ensure_datetime(session["updated_at"], "session.updated_at")
    return session


def validate_action(data: dict[str, Any]) -> dict[str, Any]:
    action = _ensure_dict(data, "action")
    _ensure_exact_keys(
        action,
        required=_ACTION_REQUIRED_KEYS,
        allowed=_ACTION_ALLOWED_KEYS,
        context="action",
    )

    if action["intent"] not in ACTION_INTENTS:
        _fail("action.intent", f"must be one of {ACTION_INTENTS}")
    _ensure_string(action["session_id"], "action.session_id")
    _ensure_string(action["expected_state"], "action.expected_state")
    _ensure_bool(action["user_confirmation"], "action.user_confirmation")
    _ensure_dict(action["parameters"], "action.parameters")
    _ensure_string(action["idempotency_key"], "action.idempotency_key", nonempty=True)
    return action


def new_trading_session(session_id: str, market_date: str, now: str) -> dict[str, Any]:
    session = {
        "session_id": _ensure_string(session_id, "session_id", nonempty=True),
        "session_type": "trading",
        "market_date": _ensure_date(market_date, "market_date"),
        "state": "DAY_INITIALIZED",
        "state_version": 1,
        "artifacts": [],
        "data_quality": {"status": "unknown", "warnings": []},
        "pending_confirmations": [],
        "allowed_actions": ["start_stage0"],
        "processed_actions": [],
        "backlog_links": [],
        "last_error": None,
        "updated_at": _ensure_datetime(now, "now"),
    }
    return validate_session(session)
