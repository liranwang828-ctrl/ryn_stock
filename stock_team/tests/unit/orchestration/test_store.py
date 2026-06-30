import pytest

from stock_team.orchestration.models import new_trading_session
from stock_team.orchestration.protocol import INPUTS_DIR, PACKETS_DIR, RUNTIME_ROOT, SESSIONS_DIR
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


def test_session_store_uses_canonical_runtime_dir():
    store = SessionStore()
    resolved = store.root.resolve()
    expected = RUNTIME_ROOT.resolve() / "sessions"
    assert resolved == expected


def test_canonical_runtime_dirs_exist():
    assert RUNTIME_ROOT.exists()
    assert SESSIONS_DIR.exists()
    assert INPUTS_DIR.exists()
    assert PACKETS_DIR.exists()
