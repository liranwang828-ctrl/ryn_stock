import pytest

from stock_team.orchestration.models import new_trading_session
from stock_team.orchestration.store import SessionConflictError, SessionStore


def test_store_round_trip_and_atomic_temp_cleanup(tmp_path):
    store = SessionStore(tmp_path)
    state = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    store.create(state)
    assert store.load(state["session_id"]) == state
    assert not list(tmp_path.glob("*.tmp"))


def test_store_rejects_stale_state_version(tmp_path):
    store = SessionStore(tmp_path)
    state = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    store.create(state)
    newer = {**state, "state_version": 2, "state": "STAGE0_RUNNING"}
    with pytest.raises(SessionConflictError, match="expected version"):
        store.save(newer, expected_version=7)
