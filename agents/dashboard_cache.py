"""Helpers for the dashboard's last-successful operational cache."""

from __future__ import annotations

import json
import os
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
