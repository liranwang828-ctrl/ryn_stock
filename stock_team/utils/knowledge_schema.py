"""Shared normalized knowledge record helpers.

The helpers stay intentionally small and deterministic: they return a copy of
the caller-provided mapping with a canonical ``kind`` field added or replaced.
"""

from __future__ import annotations

from typing import Any


def _normalize(raw: dict[str, Any], kind: str) -> dict[str, Any]:
    data = dict(raw or {})
    data["kind"] = kind
    return data


def normalize_observation(raw: dict[str, Any]) -> dict[str, Any]:
    return _normalize(raw, "observation")


def normalize_decision(raw: dict[str, Any]) -> dict[str, Any]:
    return _normalize(raw, "decision")


def normalize_outcome(raw: dict[str, Any]) -> dict[str, Any]:
    return _normalize(raw, "outcome")


def normalize_lesson(raw: dict[str, Any]) -> dict[str, Any]:
    return _normalize(raw, "lesson")


def normalize_knowledge_node(raw: dict[str, Any]) -> dict[str, Any]:
    return _normalize(raw, "knowledge_node")
