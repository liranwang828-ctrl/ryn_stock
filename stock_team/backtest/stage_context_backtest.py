"""Stage 0 / Stage 1 context evidence runner.

This module validates whether pre-market environment and plan context labels
are associated with different tactic outcomes. It produces evidence only; it
does not approve tactics, change permissions, or mutate live configuration.
"""

from __future__ import annotations

import json
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

FORBIDDEN_REQUEST_KEYS = {
    "recommendation",
    "recommended_action",
    "permission_approval",
    "approved",
    "decision",
    "sizing",
    "config_mutation",
}


def load_request(path: str | Path) -> dict[str, Any]:
    request_path = Path(path)
    data = json.loads(request_path.read_text(encoding="utf-8"))
    if data.get("artifact_type") != "stage_context_backtest_request":
        raise ValueError("artifact_type must be stage_context_backtest_request")
    if not data.get("study_id"):
        raise ValueError("study_id is required")
    if not data.get("context_fields"):
        raise ValueError("context_fields is required")

    contract = data.get("output_contract", {})
    if contract.get("allow_config_mutation") is not False:
        raise ValueError("output_contract.allow_config_mutation must be false")
    if contract.get("allow_recommendations") is not False:
        raise ValueError("output_contract.allow_recommendations must be false")

    mode = data.get("data", {}).get("mode")
    if mode not in {"fixture_events", "joined_fixture_events"}:
        raise ValueError("supported data.mode values: fixture_events, joined_fixture_events")

    _scan_for_forbidden_keys(data)
    return data


def run_request(path: str | Path) -> dict[str, Any]:
    request = load_request(path)
    data = request.get("data", {})
    context_fields = list(request["context_fields"])
    events, data_quality = _load_events(data, context_fields)

    context_segments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tactic_segments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    symbol_segments: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for event in events:
        context_segments[_context_key(event, context_fields)].append(event)
        tactic_segments[event.get("tactic_id", "unknown")].append(event)
        symbol_segments[event.get("symbol", "unknown")].append(event)

    return {
        "packet_type": "stage_context_backtest_evidence_packet",
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "study_id": request["study_id"],
        "date_range": request.get("date_range", {}),
        "context_fields": context_fields,
        "data_mode": data.get("mode"),
        "data_quality": data_quality,
        "summary": _metrics(events),
        "context_segments": {
            key: _metrics(members) for key, members in sorted(context_segments.items())
        },
        "tactic_segments": {
            key: _metrics(members) for key, members in sorted(tactic_segments.items())
        },
        "symbol_segments": {
            key: _metrics(members) for key, members in sorted(symbol_segments.items())
        },
        "boundaries": {
            "contains_permission_decision": False,
            "config_mutation": False,
            "final_tactic_status_change": False,
            "notes": [
                "Evidence only. Stage gate interpretation remains in investing-os.",
                "No permission, tactic status, portfolio, or dashboard config was changed.",
            ],
        },
        "events": events,
    }


def write_outputs(
    result: dict[str, Any],
    md_path: str | Path,
    json_path: str | Path | None = None,
) -> None:
    md_target = Path(md_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(render_markdown(result), encoding="utf-8")

    if json_path:
        json_target = Path(json_path)
        json_target.parent.mkdir(parents=True, exist_ok=True)
        json_target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "---",
        "packet_type: stage_context_backtest_evidence_packet",
        f"study_id: {result['study_id']}",
        f"generated_at: {result['generated_at']}",
        "authority: evidence_only",
        "---",
        "",
        f"# Stage Context Backtest Evidence Packet: {result['study_id']}",
        "",
        "## Boundary",
        "",
        "**Evidence Only.** This packet measures Stage 0 / Stage 1 context outcomes.",
        "Stage gate interpretation, permission state, and tactic adoption remain outside stock_team.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| :--- | ---: |",
    ]
    for key, value in result["summary"].items():
        lines.append(f"| {key} | {_fmt(value)} |")

    lines.extend([
        "",
        "## Data Quality",
        "",
        "| Field | Value |",
        "| :--- | ---: |",
    ])
    for key, value in result.get("data_quality", {}).items():
        lines.append(f"| {key} | {_fmt(value)} |")

    lines.extend([
        "",
        "## Context Segments",
        "",
        "| Context | Events | Win Rate | Avg Return % | Avg MAE % | Avg MFE % |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for key, metrics in result["context_segments"].items():
        lines.append(
            f"| {_escape_md_cell(key)} | {metrics['n_events']} | {_fmt_pct(metrics['win_rate'])} | "
            f"{_fmt(metrics['avg_return_pct'])} | {_fmt(metrics['avg_mae_pct'])} | "
            f"{_fmt(metrics['avg_mfe_pct'])} |"
        )

    lines.extend(["", "## Machine Summary", "", "```json"])
    lines.append(json.dumps(result, indent=2, ensure_ascii=False))
    lines.extend(["```", ""])
    return "\n".join(lines)


def _scan_for_forbidden_keys(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_REQUEST_KEYS:
                raise ValueError(f"Forbidden request key: {path + key}")
            _scan_for_forbidden_keys(child, f"{path}{key}.")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_for_forbidden_keys(child, f"{path}{index}.")


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    context = event.get("context")
    if not isinstance(context, dict):
        raise ValueError("each event requires a context object")
    return {
        **event,
        "return_pct": float(event.get("return_pct", 0.0)),
        "mae_pct": float(event.get("mae_pct", 0.0)),
        "mfe_pct": float(event.get("mfe_pct", 0.0)),
    }


def _load_events(data: dict[str, Any], context_fields: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mode = data.get("mode")
    if mode == "fixture_events":
        raw_events, event_quality = _resolve_event_rows(data)
        events = [_normalize_event(e) for e in raw_events]
        return events, {
            "stage_context_count": None,
            **event_quality,
            "missing_context_events": 0,
            "warnings": [],
        }

    stage_context_rows, context_source, source_warnings = _resolve_stage_context_rows(data)
    overlay_count = _merge_stage_context_overlays(stage_context_rows, data.get("stage_context_overlays", []))
    stage_contexts = _stage_contexts_by_date(stage_context_rows)
    raw_events, event_quality = _resolve_event_rows(data)
    events = []
    missing = 0
    for raw_event in raw_events:
        event = dict(raw_event)
        event_date = _event_date(event)
        context = stage_contexts.get(event_date)
        if context is None:
            missing += 1
            context = {field: "unknown" for field in context_fields}
            event["context_source"] = "missing_stage_context"
        else:
            event["context_source"] = "stage_context_by_date"
        event["date"] = event_date
        event["context"] = context
        events.append(_normalize_event(event))

    warnings = []
    if missing:
        warnings.append(f"{missing}_events_missing_stage_context")
    warnings.extend(source_warnings)
    return events, {
        "stage_context_count": len(stage_contexts),
        "stage_context_source": context_source,
        "stage_context_overlay_count": overlay_count,
        **event_quality,
        "missing_context_events": missing,
        "warnings": warnings,
    }


def _resolve_event_rows(data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = data.get("events_source")
    if not isinstance(source, dict):
        events = list(data.get("events", []))
        return events, {
            "event_source": "inline_events",
            "event_source_count": len(events),
        }
    mode = source.get("mode")
    if mode == "tactic_backtest_json":
        payload = json.loads(Path(source["path"]).read_text(encoding="utf-8"))
        if payload.get("packet_type") != "tactic_backtest_evidence_packet":
            raise ValueError("events_source tactic_backtest_json must point to tactic_backtest_evidence_packet")
        tactic_id = payload.get("tactic_id", "unknown")
        events = []
        for event in payload.get("events", []):
            event_copy = dict(event)
            event_copy.setdefault("tactic_id", tactic_id)
            events.append(event_copy)
        return events, {
            "event_source": "tactic_backtest_json",
            "event_source_count": len(events),
        }
    raise ValueError(f"Unsupported events_source.mode: {mode}")


def _resolve_stage_context_rows(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    source = data.get("stage_context_source")
    if isinstance(source, dict):
        mode = source.get("mode")
        if mode == "daily_market_fixture":
            rows, _warnings = _derive_market_stage_contexts(source)
            return rows, "daily_market_fixture", _warnings
        if mode == "daily_market_local_cache":
            rows, _warnings = _derive_market_stage_contexts(_local_cache_market_source(source))
            return rows, "daily_market_local_cache", _warnings
        raise ValueError(f"Unsupported stage_context_source.mode: {mode}")
    return list(data.get("stage_contexts", [])), "inline_stage_contexts", []


def _local_cache_market_source(source: dict[str, Any]) -> dict[str, Any]:
    cache_dir = Path(source.get("cache_dir") or Path.cwd() / "learning")
    mapped = {
        "qqq_csv": str(cache_dir / "daily_cache_QQQ.csv"),
        "vix_csv": str(cache_dir / "daily_cache_^VIX.csv"),
        "volume_csv": str(cache_dir / "daily_cache_SPY.csv"),
    }
    sector_symbol = source.get("sector_symbol")
    if sector_symbol:
        mapped["sector_symbol"] = str(sector_symbol).upper()
        mapped["sector_csv"] = str(cache_dir / f"daily_cache_{str(sector_symbol).upper()}.csv")
    return mapped


def _derive_market_stage_contexts(source: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    qqq_rows = _read_daily_csv(source["qqq_csv"])
    vix_rows = _read_daily_csv(source["vix_csv"])
    warnings = []
    volume_path = source.get("volume_csv") or source["qqq_csv"]
    if not Path(volume_path).exists():
        volume_path = source["qqq_csv"]
        warnings.append("volume_cache_missing_used_qqq_volume")
    volume_rows = _read_daily_csv(volume_path)
    vix_by_date = {row["date"]: row for row in vix_rows}
    volume_by_date = {row["date"]: row for row in volume_rows}
    sector_rows = []
    sector_csv = source.get("sector_csv")
    if sector_csv and Path(sector_csv).exists():
        sector_rows = _read_daily_csv(sector_csv)
    elif sector_csv:
        warnings.append(f"sector_cache_missing:{source.get('sector_symbol', 'unknown')}")
    sector_by_date = {row["date"]: row for row in sector_rows}

    contexts = []
    qqq_closes: list[float] = []
    volume_values: list[float] = []
    prior_vix_close: float | None = None
    prior_sector_close: float | None = None

    for row in qqq_rows:
        date_key = row["date"]
        qqq_close = row["close"]
        prior_qqq_close = qqq_closes[-1] if qqq_closes else None
        qqq_closes.append(qqq_close)

        vol_row = volume_by_date.get(date_key)
        volume = vol_row["volume"] if vol_row else row["volume"]
        volume_values.append(volume)

        vix_row = vix_by_date.get(date_key)
        vix_close = vix_row["close"] if vix_row else None
        context = {
            "qqq_regime": _qqq_regime(qqq_closes),
            "vix_regime": _vix_regime(vix_close, prior_vix_close),
            "market_volume_regime": _market_volume_regime(volume_values, qqq_closes),
        }
        sector_row = sector_by_date.get(date_key)
        if sector_row:
            context["sector_regime"] = _sector_regime(
                sector_close=sector_row["close"],
                prior_sector_close=prior_sector_close,
                qqq_close=qqq_close,
                prior_qqq_close=prior_qqq_close,
            )
        contexts.append({"date": date_key, "context": context})
        if vix_close is not None:
            prior_vix_close = vix_close
        if sector_row:
            prior_sector_close = sector_row["close"]

    return contexts, warnings


def _read_daily_csv(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append({
                "date": str(raw["Date"])[:10],
                "open": float(raw.get("Open") or 0.0),
                "close": float(raw.get("Close") or 0.0),
                "volume": float(raw.get("Volume") or 0.0),
            })
    return rows


def _qqq_regime(closes: list[float]) -> str:
    if len(closes) < 2:
        return "qqq_unknown"
    close = closes[-1]
    ma = sum(closes[-min(len(closes), 20):]) / min(len(closes), 20)
    one_day_ret = close / closes[-2] - 1.0
    if close >= ma and one_day_ret >= -0.01:
        return "qqq_uptrend"
    if close < ma or one_day_ret <= -0.015:
        return "qqq_downtrend"
    return "qqq_flat"


def _vix_regime(vix_close: float | None, prior_vix_close: float | None) -> str:
    if vix_close is None:
        return "vix_unknown"
    direction = "rising" if prior_vix_close is not None and vix_close > prior_vix_close else "falling"
    level = "high" if vix_close >= 20 else "low"
    return f"vix_{level}_{direction}"


def _market_volume_regime(volumes: list[float], closes: list[float]) -> str:
    if len(volumes) < 2:
        return "unknown_volume"
    current = volumes[-1]
    lookback = volumes[:-1][-20:]
    avg_volume = sum(lookback) / len(lookback) if lookback else 0.0
    volume_ratio = current / avg_volume if avg_volume else 0.0
    down_day = len(closes) >= 2 and closes[-1] < closes[-2]
    if volume_ratio >= 1.5 and down_day:
        return "high_volume_risk_off"
    if volume_ratio >= 1.5:
        return "high_volume_expansion"
    return "normal_volume"


def _sector_regime(
    sector_close: float,
    prior_sector_close: float | None,
    qqq_close: float,
    prior_qqq_close: float | None,
) -> str:
    if prior_sector_close is None or prior_qqq_close is None:
        return "sector_unknown"
    sector_ret = sector_close / prior_sector_close - 1.0
    qqq_ret = qqq_close / prior_qqq_close - 1.0
    spread = sector_ret - qqq_ret
    if spread >= 0.005:
        return "sector_strong"
    if spread <= -0.005:
        return "sector_weak"
    return "sector_neutral"


def _stage_contexts_by_date(stage_contexts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_date = {}
    for item in stage_contexts:
        date_key = item.get("date")
        context = item.get("context")
        if date_key and isinstance(context, dict):
            by_date[str(date_key)] = dict(context)
    return by_date


def _merge_stage_context_overlays(
    stage_context_rows: list[dict[str, Any]],
    overlays: list[dict[str, Any]],
) -> int:
    if not overlays:
        return 0
    rows_by_date = {str(item.get("date"))[:10]: item for item in stage_context_rows if item.get("date")}
    applied = 0
    for overlay in overlays:
        date_key = str(overlay.get("date", ""))[:10]
        context = overlay.get("context")
        if not date_key or not isinstance(context, dict):
            continue
        row = rows_by_date.get(date_key)
        if row is None:
            row = {"date": date_key, "context": {}}
            rows_by_date[date_key] = row
            stage_context_rows.append(row)
        row_context = row.setdefault("context", {})
        if isinstance(row_context, dict):
            row_context.update(context)
            applied += 1
    return applied


def _event_date(event: dict[str, Any]) -> str:
    if event.get("date"):
        return str(event["date"])[:10]
    if event.get("entry_time"):
        return str(event["entry_time"])[:10]
    raise ValueError("each joined event requires date or entry_time")


def _context_key(event: dict[str, Any], context_fields: list[str]) -> str:
    context = event.get("context", {})
    return "|".join(f"{field}={context.get(field, 'unknown')}" for field in context_fields)


def _metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "n_events": 0,
            "win_rate": None,
            "avg_return_pct": None,
            "avg_win_pct": None,
            "avg_loss_pct": None,
            "avg_mae_pct": None,
            "avg_mfe_pct": None,
        }
    returns = [float(e["return_pct"]) for e in events]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    return {
        "n_events": len(events),
        "win_rate": len(wins) / len(events),
        "avg_return_pct": _avg(returns),
        "avg_win_pct": _avg(wins),
        "avg_loss_pct": _avg(losses),
        "avg_mae_pct": _avg([float(e["mae_pct"]) for e in events]),
        "avg_mfe_pct": _avg([float(e["mfe_pct"]) for e in events]),
    }


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def _escape_md_cell(value: str) -> str:
    return str(value).replace("|", "\\|")
