"""Derived all-time knowledge index helpers."""

from __future__ import annotations

import json
import os
from typing import Any

_INDEX_FILE = "knowledge_index.json"
_JOURNAL_FILE = "knowledge_journal.jsonl"
_KIND_ORDER = ("observation", "decision", "outcome", "lesson", "knowledge_node")
_LATEST_LIMIT = 3
_OPEN_QUESTION_LIMIT = 5


def _learning_dir(base_dir: str) -> str:
    return os.path.join(base_dir, "learning")


def _journal_path(base_dir: str) -> str:
    return os.path.join(_learning_dir(base_dir), _JOURNAL_FILE)


def _index_path(base_dir: str) -> str:
    return os.path.join(_learning_dir(base_dir), _INDEX_FILE)


def _blank_index() -> dict[str, Any]:
    return {
        "scope": "all_time",
        "generated_at": None,
        "source_coverage": {kind: 0 for kind in _KIND_ORDER},
        "latest_lessons": [],
        "latest_observations": [],
        "open_questions": [],
    }


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "id": row.get("id"),
        "ts": row.get("ts"),
        "date": row.get("date"),
        "kind": row.get("kind"),
        "summary": row.get("summary") or row.get("statement") or row.get("rule_change") or row.get("text") or row.get("body") or "",
    }
    if row.get("source") is not None:
        compact["source"] = row.get("source")
    if row.get("source_id") is not None:
        compact["source_id"] = row.get("source_id")
    return compact


def _normalize_question(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _apply_row(index: dict[str, Any], row: dict[str, Any]) -> None:
    kind = str(row.get("kind") or "").strip()
    if kind in index["source_coverage"]:
        index["source_coverage"][kind] += 1

    if kind == "lesson":
        index["latest_lessons"].insert(0, _compact_row(row))
        for question in row.get("open_questions") or []:
            q = _normalize_question(question)
            if q and q not in index["open_questions"]:
                index["open_questions"].insert(0, q)
    elif kind == "observation":
        index["latest_observations"].insert(0, _compact_row(row))
        q = _normalize_question(row.get("question"))
        if q and q not in index["open_questions"]:
            index["open_questions"].insert(0, q)


def _finalize(index: dict[str, Any]) -> dict[str, Any]:
    index["latest_lessons"] = index["latest_lessons"][:_LATEST_LIMIT]
    index["latest_observations"] = index["latest_observations"][:_LATEST_LIMIT]
    index["open_questions"] = index["open_questions"][:_OPEN_QUESTION_LIMIT]
    index["scope"] = "all_time"
    return index


def _read_journal_rows(base_dir: str) -> list[dict[str, Any]]:
    path = _journal_path(base_dir)
    if not os.path.exists(path):
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
            if isinstance(value, dict):
                rows.append(value)
    return rows


def save_knowledge_index(base_dir: str, index: dict[str, Any]) -> str:
    path = _index_path(base_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    return path


def rebuild_knowledge_index(base_dir: str) -> dict[str, Any]:
    index = _blank_index()
    for row in _read_journal_rows(base_dir):
        _apply_row(index, row)
    index = _finalize(index)
    save_knowledge_index(base_dir, index)
    return index


def load_knowledge_index(base_dir: str) -> dict[str, Any]:
    path = _index_path(base_dir)
    if not os.path.exists(path):
        return rebuild_knowledge_index(base_dir)
    try:
        with open(path, encoding="utf-8") as f:
            value = json.load(f)
    except Exception:
        return rebuild_knowledge_index(base_dir)
    if not isinstance(value, dict):
        return rebuild_knowledge_index(base_dir)
    value.setdefault("scope", "all_time")
    value.setdefault("generated_at", None)
    value.setdefault("source_coverage", {kind: 0 for kind in _KIND_ORDER})
    value.setdefault("latest_lessons", [])
    value.setdefault("latest_observations", [])
    value.setdefault("open_questions", [])
    return value


def update_knowledge_index_from_event(base_dir: str, event: dict[str, Any]) -> dict[str, Any]:
    path = _index_path(base_dir)
    if not os.path.exists(path):
        return rebuild_knowledge_index(base_dir)

    index = load_knowledge_index(base_dir)
    if not isinstance(index, dict):
        index = _blank_index()
    _apply_row(index, event if isinstance(event, dict) else {})
    index = _finalize(index)
    save_knowledge_index(base_dir, index)
    return index
