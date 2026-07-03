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
    "start_stage0_from_snapshot",
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
SESSION_OPTIONAL = {"market_date", "backlog_links", "last_error", "intraday_exceptions", "observation_exceptions", "archive_manifest_path", "daily4_review_path"}
REVIEW_MODES = {"full_review", "quick_review", "freeze"}
JUDGMENT_TYPES = {"thesis", "execution", "sizing", "emotion", "data_quality"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
SOURCE_TYPES = {"user_confirmed", "assistant_inferred"}
USER_DECISIONS = {"noise", "observe", "learning_candidate"}
IBKR_FACT_STATUSES = {"verified", "stale_unverified", "missing"}
REVIEW_JUDGMENT_REQUIRED = {"judgment_type", "summary", "evidence_refs", "confidence", "source"}
CANDIDATE_LESSON_REQUIRED = {"candidate_id", "theme", "statement", "supporting_evidence_refs", "requires_followup", "user_decision"}
USER_CONFIRMATIONS_REQUIRED = {"bias_classification_confirmed", "emotion_notes_confirmed", "noise_vs_candidate_confirmed", "learning_candidates_confirmed"}
ARCHIVE_CLOSURE_REQUIRED = {"archive_manifest_path", "user_confirmed_at"}
DAILY4_REVIEW_REQUIRED = {"session_id", "trading_date", "review_mode", "ibkr_fact_status", "fact_packet_refs", "review_judgments", "candidate_lessons", "user_confirmations", "archive_closure"}
DAILY4_REVIEW_OPTIONAL = set()
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
        "allowed_actions": ["start_stage0", "start_stage0_from_snapshot"],
        "processed_actions": [],
        "backlog_links": [],
        "intraday_exceptions": [],
        "observation_exceptions": [],
        "last_error": None,
        "updated_at": now,
    }
    return validate_session(session)


def validate_daily4_review(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("daily4 review must be an object")
    _require_keys(data, DAILY4_REVIEW_REQUIRED, DAILY4_REVIEW_OPTIONAL, "daily4 review")
    _require_non_empty_string(data["session_id"], "session_id")
    _require_iso_date(data["trading_date"], "trading_date")
    if data["review_mode"] not in REVIEW_MODES:
        raise ValidationError(f"review_mode must be one of {sorted(REVIEW_MODES)}")
    if data["ibkr_fact_status"] not in IBKR_FACT_STATUSES:
        raise ValidationError(f"ibkr_fact_status must be one of {sorted(IBKR_FACT_STATUSES)}")
    if not isinstance(data["fact_packet_refs"], list):
        raise ValidationError("fact_packet_refs must be a list")
    if not isinstance(data["review_judgments"], list):
        raise ValidationError("review_judgments must be a list")
    for j in data["review_judgments"]:
        _require_keys(j, REVIEW_JUDGMENT_REQUIRED, set(), "review_judgment")
        if j["judgment_type"] not in JUDGMENT_TYPES:
            raise ValidationError(f"judgment_type must be one of {sorted(JUDGMENT_TYPES)}")
        if j["confidence"] not in CONFIDENCE_LEVELS:
            raise ValidationError(f"confidence must be one of {sorted(CONFIDENCE_LEVELS)}")
        if j["source"] not in SOURCE_TYPES:
            raise ValidationError(f"source must be one of {sorted(SOURCE_TYPES)}")
        if not isinstance(j["evidence_refs"], list):
            raise ValidationError("evidence_refs must be a list")
    if not isinstance(data["candidate_lessons"], list):
        raise ValidationError("candidate_lessons must be a list")
    for c in data["candidate_lessons"]:
        _require_keys(c, CANDIDATE_LESSON_REQUIRED, set(), "candidate_lesson")
        if c["user_decision"] not in USER_DECISIONS:
            raise ValidationError(f"user_decision must be one of {sorted(USER_DECISIONS)}")
        if not isinstance(c["requires_followup"], bool):
            raise ValidationError("requires_followup must be a boolean")
        if not isinstance(c["supporting_evidence_refs"], list):
            raise ValidationError("supporting_evidence_refs must be a list")
    uq = data["user_confirmations"]
    if not isinstance(uq, dict):
        raise ValidationError("user_confirmations must be an object")
    _require_keys(uq, USER_CONFIRMATIONS_REQUIRED, set(), "user_confirmations")
    for k in USER_CONFIRMATIONS_REQUIRED:
        if not isinstance(uq[k], bool):
            raise ValidationError(f"user_confirmations.{k} must be a boolean")
    ac = data["archive_closure"]
    if not isinstance(ac, dict):
        raise ValidationError("archive_closure must be an object")
    _require_keys(ac, ARCHIVE_CLOSURE_REQUIRED, set(), "archive_closure")
    if not isinstance(ac["archive_manifest_path"], str):
        raise ValidationError("archive_manifest_path must be a string")
    if ac["user_confirmed_at"]:
        _require_iso_datetime(ac["user_confirmed_at"], "user_confirmed_at")
    return data


def new_daily4_review(session_id: str, trading_date: str, review_mode: str, ibkr_fact_status: str = "stale_unverified") -> dict:
    review = {
        "session_id": session_id,
        "trading_date": trading_date,
        "review_mode": review_mode,
        "ibkr_fact_status": ibkr_fact_status,
        "fact_packet_refs": [],
        "review_judgments": [],
        "candidate_lessons": [],
        "user_confirmations": {
            "bias_classification_confirmed": False,
            "emotion_notes_confirmed": False,
            "noise_vs_candidate_confirmed": False,
            "learning_candidates_confirmed": False,
        },
        "archive_closure": {
            "archive_manifest_path": "",
            "user_confirmed_at": "",
        },
    }
    return validate_daily4_review(review)
