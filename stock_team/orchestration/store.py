from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
from typing import Iterator

from .models import ValidationError, validate_session


class SessionNotFoundError(FileNotFoundError):
    pass


class SessionConflictError(RuntimeError):
    pass


class SessionBusyError(RuntimeError):
    pass


def _sanitize_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session_id must be a non-empty string")
    if session_id != Path(session_id).name or any(sep in session_id for sep in ("/", "\\", "..")):
        raise ValueError("session_id must be a flat filename-safe identifier")
    return session_id


class SessionStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.root / f"{_sanitize_session_id(session_id)}.json"

    def _lock_path(self, session_id: str) -> Path:
        return self.root / f"{_sanitize_session_id(session_id)}.lock"

    def _tmp_path(self, session_id: str) -> Path:
        return self.root / f"{_sanitize_session_id(session_id)}.json.tmp"

    def load(self, session_id: str) -> dict:
        path = self._path(session_id)
        if not path.exists():
            raise SessionNotFoundError(path)
        with path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
        return validate_session(state)

    def create(self, state: dict) -> dict:
        validated = validate_session(state)
        path = self._path(validated["session_id"])
        if path.exists():
            raise SessionConflictError(f"session already exists: {path}")
        self._write_atomic(validated)
        return validated

    def save(self, state: dict, expected_version: int) -> dict:
        validated = validate_session(state)
        path = self._path(validated["session_id"])
        current = self.load(validated["session_id"])
        if current["state_version"] != expected_version:
            raise SessionConflictError(
                f"expected version {expected_version}, found {current['state_version']}"
            )
        self._write_atomic(validated)
        return validated

    @contextlib.contextmanager
    def lock(self, session_id: str) -> Iterator[Path]:
        lock_path = self._lock_path(session_id)
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SessionBusyError(f"session locked: {lock_path}") from exc
        try:
            os.close(fd)
            yield lock_path
        finally:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _write_atomic(self, state: dict) -> None:
        session_id = state["session_id"]
        tmp_path = self._tmp_path(session_id)
        final_path = self._path(session_id)
        payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
        with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, final_path)

