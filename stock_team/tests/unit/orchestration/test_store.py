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


def test_list_sessions_returns_all(tmp_path):
    store = SessionStore(tmp_path)
    s1 = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    s2 = new_trading_session("trading-2026-06-16", "2026-06-16", "2026-06-16T12:00:00+00:00")
    store.create(s1)
    store.create(s2)
    sessions = store.list_sessions()
    ids = {s["session_id"] for s in sessions}
    assert ids == {"trading-2026-06-15", "trading-2026-06-16"}


def test_list_sessions_filter_by_date(tmp_path):
    store = SessionStore(tmp_path)
    s1 = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    s2 = new_trading_session("trading-2026-06-16", "2026-06-16", "2026-06-16T12:00:00+00:00")
    store.create(s1)
    store.create(s2)
    sessions = store.list_sessions(market_date="2026-06-15")
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "trading-2026-06-15"


def test_list_sessions_exclude_terminal(tmp_path):
    store = SessionStore(tmp_path)
    s1 = new_trading_session("trading-2026-06-15", "2026-06-15", "2026-06-15T12:00:00+00:00")
    s1["state"] = "DAY_ARCHIVED"
    s2 = new_trading_session("trading-2026-06-16", "2026-06-16", "2026-06-16T12:00:00+00:00")
    s2["state"] = "INTRADAY_ACTIVE"
    s3 = new_trading_session("trading-2026-06-17", "2026-06-17", "2026-06-17T12:00:00+00:00")
    s3["state"] = "CLOSED_UNREVIEWED"
    store.create(s1)
    store.create(s2)
    store.create(s3)
    active = store.list_sessions(only_open=True)
    ids = {s["session_id"] for s in active}
    assert ids == {"trading-2026-06-16"}


def test_list_sessions_empty(tmp_path):
    store = SessionStore(tmp_path)
    assert store.list_sessions() == []
