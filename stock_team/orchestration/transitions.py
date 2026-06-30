from __future__ import annotations


BEGIN_TRANSITIONS = {
    ("DAY_INITIALIZED", "start_stage0"): "STAGE0_RUNNING",
    ("STAGE0_READY", "record_focus_confirmation"): "FOCUS_CONFIRMED",
    ("FOCUS_CONFIRMED", "start_stage1"): "STAGE1_RUNNING",
    ("FOCUS_CONFIRMED", "start_observation"): "OBSERVATION_ACTIVE",
    ("STAGE1_READY", "record_plan_approval"): "PLAN_APPROVED",
    ("PLAN_APPROVED", "start_intraday"): "INTRADAY_ACTIVE",
    ("INTRADAY_ACTIVE", "close_market"): "MARKET_CLOSED",
    ("INTRADAY_ACTIVE", "request_exception"): "INTRADAY_ACTIVE",
    ("OBSERVATION_ACTIVE", "close_market"): "MARKET_CLOSED",
    ("MARKET_CLOSED", "review_day"): "REVIEW_REQUIRED",
    ("REVIEW_REQUIRED", "archive_day"): "DAY_ARCHIVED",
    ("MARKET_CLOSED", "quick_review"): "QUICK_REVIEWED",
    ("MARKET_CLOSED", "freeze"): "CLOSED_UNREVIEWED",
    ("QUICK_REVIEWED", "archive_day"): "DAY_ARCHIVED",
    ("OBSERVATION_ACTIVE", "archive_day"): "DAY_ARCHIVED",
}

SUCCESS_TRANSITIONS = {
    ("STAGE0_RUNNING", "start_stage0"): "STAGE0_READY",
    ("STAGE1_RUNNING", "start_stage1"): "STAGE1_READY",
}

ALLOWED_ACTIONS = {
    "DAY_INITIALIZED": ["start_stage0"],
    "STAGE0_READY": ["record_focus_confirmation"],
    "FOCUS_CONFIRMED": ["start_stage1", "start_observation"],
    "STAGE1_READY": ["record_plan_approval"],
    "PLAN_APPROVED": ["start_intraday"],
    "INTRADAY_ACTIVE": ["close_market", "request_exception"],
    "OBSERVATION_ACTIVE": ["intraday-snapshot", "close_market", "archive_day"],
    "MARKET_CLOSED": ["review_day", "quick_review", "freeze"],
    "REVIEW_REQUIRED": ["archive_day"],
    "QUICK_REVIEWED": ["archive_day"],
    "FAILED_TOOL": ["retry_last_action"],
}

CONFIRMATION_ACTIONS = {"record_focus_confirmation", "record_plan_approval", "request_exception"}


class TransitionError(RuntimeError):
    pass


def begin_transition(state: str, intent: str) -> str:
    try:
        return BEGIN_TRANSITIONS[(state, intent)]
    except KeyError as exc:
        raise TransitionError(f"{intent} is not legal from {state}") from exc


def complete_transition(state: str, intent: str, *, success: bool) -> str:
    if not success:
        return "FAILED_TOOL"
    try:
        return SUCCESS_TRANSITIONS[(state, intent)]
    except KeyError:
        return state


def allowed_actions(state: str) -> list[str]:
    return ALLOWED_ACTIONS.get(state, [])


def requires_confirmation(intent: str) -> bool:
    return intent in CONFIRMATION_ACTIONS
