"""Helpers for the dashboard's last-successful operational cache."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


def _cache_path(base_dir: str) -> str:
    return os.path.join(base_dir, "learning", "dashboard_cache.json")


def write_dashboard_cache(base_dir: str, payload: dict[str, Any]) -> str:
    path = _cache_path(base_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def load_dashboard_cache(base_dir: str) -> dict[str, Any]:
    path = _cache_path(base_dir)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            value = json.load(f)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def update_latest_prices(base_dir: str, prices: dict[str, dict[str, Any]], asof: str | None = None) -> str:
    cache = load_dashboard_cache(base_dir)
    if not isinstance(cache, dict):
        cache = {}
    intraday = cache.setdefault("intraday", {})
    asof_value = asof or datetime.now(timezone.utc).isoformat()

    for raw_sym, price_data in (prices or {}).items():
        if not isinstance(price_data, dict):
            continue
        sym = str(raw_sym).upper()
        rec = intraday.setdefault(sym, {})
        if not isinstance(rec, dict):
            rec = {}
            intraday[sym] = rec
        price_now = rec.setdefault("price_now", {})
        if not isinstance(price_now, dict):
            price_now = {}
            rec["price_now"] = price_now
        if price_data.get("price") is not None:
            price_now["price"] = price_data.get("price")
        if price_data.get("chg_pct") is not None:
            price_now["chg_pct"] = price_data.get("chg_pct")
        price_now["price_source"] = price_data.get("source") or "manual_refresh"
        price_now["price_asof"] = asof_value
        meta = rec.setdefault("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            rec["meta"] = meta
        meta["sym"] = sym
        meta["price_asof"] = asof_value

    cache["latest_price_refresh_at"] = asof_value
    return write_dashboard_cache(base_dir, cache)
