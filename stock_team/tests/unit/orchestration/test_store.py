from __future__ import annotations

import json
from pathlib import Path

import pytest

from stock_team.orchestration.models import new_trading_session


def test_store_round_trip_and_atomic_temp_cleanup(tmp_path):
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    state = new_trading_session(
        "trading-2026-06-15",
        "2026-06-15",
        "2026-06-15T12:00:00+00:00",
    )

    store.create(state)

    assert store.load(state["session_id"]) == state
    assert not list(tmp_path.glob("*.tmp"))


def test_store_rejects_stale_state_version(tmp_path):
    from stock_team.orchestration.store import SessionConflictError, SessionStore

    store = SessionStore(tmp_path)
    state = new_trading_session(
        "trading-2026-06-15",
        "2026-06-15",
        "2026-06-15T12:00:00+00:00",
    )

    store.create(state)
    newer = {**state, "state_version": 2, "state": "STAGE0_RUNNING"}

    with pytest.raises(SessionConflictError, match="expected version"):
        store.save(newer, expected_version=7)


def test_store_rejects_invalid_session_id(tmp_path):
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)

    with pytest.raises(ValueError, match="session_id"):
        store.load("../oops")


def test_store_lock_context_releases_lock(tmp_path):
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    state = new_trading_session(
        "trading-2026-06-15",
        "2026-06-15",
        "2026-06-15T12:00:00+00:00",
    )
    store.create(state)

    with store.lock(state["session_id"]):
        assert (tmp_path / f'{state["session_id"]}.lock').exists()

    assert not (tmp_path / f'{state["session_id"]}.lock').exists()
