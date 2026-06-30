import pytest

from stock_team.orchestration.transitions import TransitionError, allowed_actions, begin_transition, complete_transition


def test_stage0_moves_through_running_to_ready():
    running = begin_transition("DAY_INITIALIZED", "start_stage0")
    assert running == "STAGE0_RUNNING"
    assert complete_transition(running, "start_stage0", success=True) == "STAGE0_READY"


def test_stage1_requires_focus_confirmation():
    with pytest.raises(TransitionError, match="start_stage1"):
        begin_transition("DISCUSSION_REQUIRED", "start_stage1")


def test_failed_tool_preserves_resume_state():
    result = complete_transition("STAGE1_RUNNING", "start_stage1", success=False)
    assert result == "FAILED_TOOL"


def test_allowed_actions_for_stage0_ready_requires_discussion_confirmation():
    assert allowed_actions("STAGE0_READY") == ["record_focus_confirmation"]


def test_focus_confirmed_to_observation_active():
    result = begin_transition("FOCUS_CONFIRMED", "start_observation")
    assert result == "OBSERVATION_ACTIVE"


def test_observation_active_rejects_trading_intents():
    for trading_intent in ("start_intraday", "record_plan_approval"):
        with pytest.raises(TransitionError, match=trading_intent):
            begin_transition("OBSERVATION_ACTIVE", trading_intent)


def test_market_closed_to_review_required():
    result = begin_transition("MARKET_CLOSED", "review_day")
    assert result == "REVIEW_REQUIRED"


def test_review_required_to_day_archived():
    result = begin_transition("REVIEW_REQUIRED", "archive_day")
    assert result == "DAY_ARCHIVED"


def test_quick_reviewed_transition():
    result = begin_transition("MARKET_CLOSED", "quick_review")
    assert result == "QUICK_REVIEWED"


def test_closed_unreviewed_transition():
    result = begin_transition("MARKET_CLOSED", "freeze")
    assert result == "CLOSED_UNREVIEWED"


def test_archive_day_action_exists():
    assert "archive_day" in allowed_actions("REVIEW_REQUIRED")


def test_intraday_active_allows_request_exception():
    actions = allowed_actions("INTRADAY_ACTIVE")
    assert "request_exception" in actions
    assert "close_market" in actions


def test_request_exception_transition():
    result = begin_transition("INTRADAY_ACTIVE", "request_exception")
    assert result == "INTRADAY_ACTIVE"
