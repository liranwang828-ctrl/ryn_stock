import sys
import os

from stock_team.server.dashboard_experience_paths import (
    EXPERIENCE_PATHS,
    MAX_FIXES_PER_ROUND,
    MAX_HIGH_PRIORITY_ISSUES,
    PROTECTED_SCOPE_TOKENS,
    path_ids,
)


def test_experience_paths_freeze_v1_task_ids():
    assert path_ids() == [
        "path_a_premarket_orientation",
        "path_b_premarket_readiness",
        "path_c_symbol_action",
        "path_d_return_to_global",
    ]
    assert len(EXPERIENCE_PATHS) == 4


def test_experience_paths_enforce_controlled_round_limits():
    assert MAX_HIGH_PRIORITY_ISSUES == 3
    assert MAX_FIXES_PER_ROUND == 2


def test_protected_scope_explicitly_blocks_backtest_tokens():
    assert {"backtest", "joint_backtest", "sweep", "simulation"}.issubset(set(PROTECTED_SCOPE_TOKENS))
