"""Deterministic synthesis helpers for learning lessons and knowledge nodes."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from agents.knowledge_schema import normalize_knowledge_node, normalize_lesson

_POSITIVE_MARKERS = (
    "confirmed",
    "confirmation",
    "patient",
    "patience",
    "worked",
    "win",
    "won",
    "held",
    "support",
)
_NEGATIVE_MARKERS = (
    "impulsive",
    "impulsively",
    "chase",
    "chasing",
    "early",
    "late",
    "failed",
    "loss",
    "missed",
    "weak",
)


def _as_items(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, dict):
        return [value]
    items: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            items.append(item)
        else:
            items.append({"text": str(item)})
    return items


def _text_from_item(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "summary", "text", "body", "notes", "note", "result", "rule_change"):
        value = item.get(key)
        if value:
            parts.append(str(value).strip())
    return " ".join(part for part in parts if part)


def _first_excerpt(items: list[dict[str, Any]]) -> str:
    for item in items:
        text = _text_from_item(item)
        if text:
            return text
    return ""


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _collect_texts(*groups: list[dict[str, Any]]) -> str:
    return " ".join(
        text
        for group in groups
        for text in (_text_from_item(item) for item in group)
        if text
    )


def _stable_last_updated(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    seconds = int(digest[:8], 16) % (50 * 365 * 24 * 60 * 60)
    stamp = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    return stamp.isoformat().replace("+00:00", "Z")


def _normalize_tags(*values: Any) -> list[str]:
    tags: list[str] = []
    for value in values:
        if not value:
            continue
        pieces = re.split(r"[^A-Za-z0-9]+", str(value))
        for piece in pieces:
            cleaned = piece.strip().lower()
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
    return tags


def synthesize_lesson(
    docs: list[dict[str, Any]] | tuple[dict[str, Any], ...] | dict[str, Any],
    outcomes: list[dict[str, Any]] | tuple[dict[str, Any], ...] | dict[str, Any],
    observations: list[dict[str, Any]] | tuple[dict[str, Any], ...] | dict[str, Any],
) -> dict[str, Any]:
    docs_list = _as_items(docs)
    outcomes_list = _as_items(outcomes)
    observations_list = _as_items(observations)

    combined_text = _collect_texts(docs_list, outcomes_list, observations_list)
    first_doc = _first_excerpt(docs_list)
    first_outcome = _first_excerpt(outcomes_list)
    first_observation = _first_excerpt(observations_list)

    positive_hits = 0
    negative_hits = 0
    for text in (combined_text,):
        if _contains_any(text, _POSITIVE_MARKERS):
            positive_hits += 1
        if _contains_any(text, _NEGATIVE_MARKERS):
            negative_hits += 1

    outcome_text = _collect_texts(outcomes_list)
    if _contains_any(outcome_text, ("win", "won", "positive", "profit", "gain", "worked")):
        positive_hits += 1
    if _contains_any(outcome_text, ("loss", "lost", "negative", "failed", "missed")):
        negative_hits += 1

    what_worked: list[str] = []
    if positive_hits:
        what_worked.append("Confirmation and patience improved the result.")
    elif first_doc:
        what_worked.append(first_doc)

    what_failed: list[str] = []
    if negative_hits:
        what_failed.append("Impulsive or unconfirmed execution weakened the setup.")
    elif first_observation and _contains_any(first_observation, _NEGATIVE_MARKERS):
        what_failed.append(first_observation)

    if negative_hits:
        bias = "impulsiveness"
        rule_change = "Tighten the entry rule and avoid unconfirmed or rushed setups."
    elif positive_hits:
        bias = "confirmation_bias"
        rule_change = "Keep requiring confirmation before committing."
    else:
        bias = "neutral"
        rule_change = "Capture the clearest repeatable trigger before acting."

    summary_bits = [bit for bit in (first_doc, first_outcome, first_observation) if bit]
    summary = " | ".join(summary_bits) if summary_bits else "No evidence provided."

    lesson = {
        "summary": summary,
        "what_worked": what_worked,
        "what_failed": what_failed,
        "bias": bias,
        "rule_change": rule_change,
    }
    return normalize_lesson(lesson)


def build_knowledge_node(
    theme: str,
    lesson: dict[str, Any],
    supporting_cases: list[Any] | tuple[Any, ...] | Any,
) -> dict[str, Any]:
    support_list = list(supporting_cases) if isinstance(supporting_cases, (list, tuple)) else [supporting_cases]

    lesson_text = _collect_texts([lesson] if isinstance(lesson, dict) else [], [])
    statement = lesson.get("rule_change") if isinstance(lesson, dict) else ""
    if not statement:
        statement = lesson.get("summary") if isinstance(lesson, dict) else ""
        if not statement:
            statement = f"{theme} learning node"

    if isinstance(lesson, dict) and lesson.get("what_worked") and support_list:
        validity = "supported"
    elif isinstance(lesson, dict) and lesson.get("what_worked"):
        validity = "tentative"
    else:
        validity = "weak"

    tags = _normalize_tags(theme, lesson.get("bias") if isinstance(lesson, dict) else None, lesson_text)
    payload = {
        "theme": theme,
        "statement": statement,
        "tags": tags,
        "validity": validity,
        "supporting_cases": support_list,
    }
    payload["last_updated"] = _stable_last_updated(payload)
    return normalize_knowledge_node(payload)
