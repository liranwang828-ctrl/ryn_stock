"""Deterministic adapters that normalize early research inputs.

The functions in this module stay intentionally small and side-effect free:
they copy the raw payload, add canonical fields, and derive a stable ``id``
from the normalized content.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _copy_raw(raw: dict[str, Any] | None) -> dict[str, Any]:
    return dict(raw or {})


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return text.strip()


def _upper_symbol(value: Any) -> str:
    return _clean_text(value).upper()


def _normalize_symbols(raw: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    if "symbols" in raw and raw["symbols"] is not None:
        symbols = raw["symbols"]
        if isinstance(symbols, (list, tuple, set)):
            values.extend(symbols)
        else:
            values.append(symbols)
    elif "symbol" in raw and raw["symbol"] is not None:
        values.append(raw["symbol"])

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        symbol = _upper_symbol(value)
        if symbol and symbol not in seen:
            seen.add(symbol)
            result.append(symbol)
    if not result and raw.get("symbol") is not None:
        fallback = _upper_symbol(raw.get("symbol"))
        if fallback:
            result.append(fallback)
    return result


def _normalize_citations(raw: dict[str, Any]) -> list[str]:
    citations: list[Any] = []
    if "citations" in raw and raw["citations"] is not None:
        raw_citations = raw["citations"]
        if isinstance(raw_citations, (list, tuple, set)):
            citations.extend(raw_citations)
        else:
            citations.append(raw_citations)
    elif "citation" in raw and raw["citation"] is not None:
        citations.append(raw["citation"])

    result: list[str] = []
    seen: set[str] = set()
    for value in citations:
        citation = _clean_text(value)
        if citation and citation not in seen:
            seen.add(citation)
            result.append(citation)
    if not result and raw.get("citation") is not None:
        fallback = _clean_text(raw.get("citation"))
        if fallback:
            result.append(fallback)
            seen.add(fallback)
    if raw.get("url"):
        url = _clean_text(raw.get("url"))
        if url and url not in seen:
            result.append(url)
            seen.add(url)
    return result


def _preferred_text(*values: Any) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


def _canonicalize_for_hash(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    for key in ("symbols", "citations"):
        value = data.get(key)
        if isinstance(value, list):
            data[key] = sorted(value)
    return data


def _stable_id(source_type: str, payload: dict[str, Any]) -> str:
    canonical_payload = _canonicalize_for_hash(payload)
    canonical = json.dumps(
        {"source_type": source_type, **canonical_payload},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{source_type}-{digest}"


def _finalize(raw: dict[str, Any], source_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    doc = _copy_raw(raw)
    doc.update(payload)
    doc["source_type"] = source_type
    doc["id"] = _stable_id(source_type, payload)
    return doc


def ingest_news_item(raw: dict[str, Any]) -> dict[str, Any]:
    symbols = _normalize_symbols(raw)
    title = _clean_text(raw.get("title"))
    source = _clean_text(raw.get("source"))
    url = _clean_text(raw.get("url"))
    published_at = _clean_text(raw.get("published_at"))
    text = _preferred_text(raw.get("text"), raw.get("body"))
    citations = _normalize_citations(raw)
    payload = {
        "symbols": symbols,
        "title": title,
        "source": source,
        "url": url,
        "published_at": published_at,
        "text": text,
        "citations": citations,
    }
    return _finalize(raw, "news", payload)


def ingest_sec_filing(raw: dict[str, Any]) -> dict[str, Any]:
    symbol = _upper_symbol(raw.get("symbol"))
    form_type = _clean_text(raw.get("form_type"))
    source = _clean_text(raw.get("source"))
    url = _clean_text(raw.get("url"))
    published_at = _clean_text(raw.get("published_at"))
    text = _preferred_text(raw.get("text"), raw.get("body"))
    citations = _normalize_citations(raw)
    payload = {
        "symbol": symbol,
        "form_type": form_type,
        "source": source,
        "url": url,
        "published_at": published_at,
        "text": text,
        "citations": citations,
    }
    return _finalize(raw, "sec_filing", payload)


def ingest_public_holding(raw: dict[str, Any]) -> dict[str, Any]:
    person = _clean_text(raw.get("person"))
    symbol = _upper_symbol(raw.get("symbol"))
    action = _clean_text(raw.get("action"))
    source = _clean_text(raw.get("source"))
    published_at = _clean_text(raw.get("published_at"))
    rationale = _preferred_text(raw.get("rationale"), raw.get("text"))
    citations = _normalize_citations(raw)
    payload = {
        "person": person,
        "symbol": symbol,
        "action": action,
        "source": source,
        "published_at": published_at,
        "rationale": rationale,
        "text": rationale,
        "citations": citations,
    }
    return _finalize(raw, "public_holding", payload)


def ingest_manual_note(raw: dict[str, Any]) -> dict[str, Any]:
    source = _clean_text(raw.get("source"))
    published_at = _clean_text(raw.get("published_at"))
    title = _clean_text(raw.get("title"))
    text = _preferred_text(raw.get("text"), raw.get("body"))
    symbols = _normalize_symbols(raw)
    citations = _normalize_citations(raw)
    payload = {
        "source": source,
        "published_at": published_at,
        "title": title,
        "text": text,
        "symbols": symbols,
        "citations": citations,
    }
    return _finalize(raw, "manual_note", payload)
