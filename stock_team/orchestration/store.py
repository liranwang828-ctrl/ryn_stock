from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

from .models import validate_session


class SessionNotFoundError(FileNotFoundError):
    pass


class SessionConflictError(RuntimeError):
    pass


class SessionBusyError(RuntimeError):
    pass


class SessionStore:
    def __init__(self, root=None):
        if root is None:
            from .protocol import SESSIONS_DIR

            root = SESSIONS_DIR
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, state: dict) -> dict:
        state = validate_session(state)
        session_id = state["session_id"]
        path = self._session_path(session_id)
        if path.exists():
            raise SessionConflictError(f"session already exists: {session_id}")
        with self.lock(session_id):
            if path.exists():
                raise SessionConflictError(f"session already exists: {session_id}")
            self._write_state(path, state)
        return state

    def load(self, session_id: str) -> dict:
        path = self._session_path(session_id)
        if not path.exists():
            raise SessionNotFoundError(session_id)
        with path.open("r", encoding="utf-8") as fh:
            state = json.load(fh)
        return validate_session(state)

    def save(self, state: dict, expected_version: int) -> dict:
        state = validate_session(state)
        session_id = state["session_id"]
        path = self._session_path(session_id)
        if not path.exists():
            raise SessionNotFoundError(session_id)
        with self.lock(session_id):
            current = self.load(session_id)
            if current["state_version"] != expected_version:
                raise SessionConflictError(
                    f"expected version {expected_version}, found {current['state_version']}"
                )
            self._write_state(path, state)
        return state

    @contextmanager
    def lock(self, session_id: str):
        lock_path = self._lock_path(session_id)
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SessionBusyError(session_id) from exc
        try:
            os.close(fd)
            yield
        finally:
            try:
                os.remove(lock_path)
            except FileNotFoundError:
                pass

    TERMINAL_STATES = {"DAY_ARCHIVED", "CLOSED_UNREVIEWED"}

    def list_sessions(self, *, market_date: str | None = None, only_open: bool = False) -> list[dict]:
        sessions = []
        for path in sorted(self.root.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    state = json.load(fh)
                state = validate_session(state)
            except Exception:
                continue
            if market_date is not None and state.get("market_date") != market_date:
                continue
            if only_open and state.get("state") in self.TERMINAL_STATES:
                continue
            sessions.append(state)
        return sessions

    def _validate_session_id(self, session_id: str) -> str:
        if not isinstance(session_id, str) or not session_id or ".." in session_id or "/" in session_id or "\\" in session_id:
            raise SessionConflictError(f"invalid session id: {session_id!r}")
        return session_id

    def _session_path(self, session_id: str) -> Path:
        session_id = self._validate_session_id(session_id)
        return self.root / f"{session_id}.json"

    def _lock_path(self, session_id: str) -> str:
        session_id = self._validate_session_id(session_id)
        return str(self.root / f"{session_id}.lock")

    def _write_state(self, path: Path, state: dict) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        payload = json.dumps(state, ensure_ascii=False, indent=2)
        with tmp_path.open("w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
