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
