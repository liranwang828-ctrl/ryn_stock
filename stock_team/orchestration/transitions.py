from __future__ import annotations


class TransitionError(RuntimeError):
    pass


BEGIN_TRANSITIONS = {
    ("DAY_INITIALIZED", "start_stage0"): "STAGE0_RUNNING",
    ("STAGE0_READY", "record_focus_confirmation"): "FOCUS_CONFIRMED",
    ("FOCUS_CONFIRMED", "start_stage1"): "STAGE1_RUNNING",
    ("STAGE1_READY", "record_plan_approval"): "PLAN_APPROVED",
    ("PLAN_APPROVED", "start_intraday"): "INTRADAY_ACTIVE",
    ("INTRADAY_ACTIVE", "close_market"): "MARKET_CLOSED",
    ("MARKET_CLOSED", "archive_day"): "DAY_ARCHIVED",
}

SUCCESS_TRANSITIONS = {
    ("STAGE0_RUNNING", "start_stage0"): "STAGE0_READY",
    ("STAGE1_RUNNING", "start_stage1"): "STAGE1_READY",
}

FAILURE_TRANSITIONS = {
    "STAGE0_RUNNING": "FAILED_TOOL",
    "STAGE1_RUNNING": "FAILED_TOOL",
}

ALLOWED_ACTIONS = {
    "IDLE": ["initialize_day"],
    "DAY_INITIALIZED": ["start_stage0"],
    "STAGE0_READY": ["record_focus_confirmation"],
    "DISCUSSION_REQUIRED": ["record_focus_confirmation"],
    "FOCUS_CONFIRMED": ["start_stage1"],
    "STAGE1_READY": ["record_plan_approval"],
    "PLAN_APPROVED": ["start_intraday"],
    "INTRADAY_ACTIVE": ["close_market"],
    "MARKET_CLOSED": ["archive_day"],
    "FAILED_TOOL": ["retry_last_action"],
}

CONFIRMATION_REQUIRED = {
    "record_focus_confirmation",
    "record_plan_approval",
}


def allowed_actions(state: str) -> list[str]:
    return list(ALLOWED_ACTIONS.get(state, []))


def requires_confirmation(intent: str) -> bool:
    return intent in CONFIRMATION_REQUIRED


def begin_transition(state: str, intent: str) -> str:
    try:
        return BEGIN_TRANSITIONS[(state, intent)]
    except KeyError as exc:
        raise TransitionError(f"{intent} is not allowed from {state}") from exc


def complete_transition(state: str, intent: str, *, success: bool) -> str:
    if success:
        if (state, intent) in SUCCESS_TRANSITIONS:
            return SUCCESS_TRANSITIONS[(state, intent)]
        raise TransitionError(f"{intent} cannot complete from {state}")
    if state in FAILURE_TRANSITIONS:
        return FAILURE_TRANSITIONS[state]
    raise TransitionError(f"{intent} cannot fail from {state}")
