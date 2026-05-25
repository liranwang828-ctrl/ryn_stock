"""Append-only journal helpers for shared knowledge records."""

from __future__ import annotations

import json
import os
from typing import Any


def _journal_path(base_dir: str) -> str:
    return os.path.join(base_dir, "learning", "knowledge_journal.jsonl")


def append_knowledge_event(base_dir: str, event: dict[str, Any]) -> str:
    path = _journal_path(base_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    try:
        from agents.knowledge_index import update_knowledge_index_from_event

        update_knowledge_index_from_event(base_dir, event)
    except Exception:
        pass
    return path


def load_recent_events(base_dir: str, limit: int = 50) -> list[dict[str, Any]]:
    path = _journal_path(base_dir)
    if limit <= 0 or not os.path.exists(path):
        return []

    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(value, dict):
                continue
            rows.append(value)
    return rows[-limit:]
