"""Research sweep runner for tactic candidates.

This module keeps research-only candidate scans fast by precomputing local-cache
bars and intraday features once per symbol, then reusing them across candidate
parameter sets.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from stock_team.backtest import tactic_simulator
from stock_team.backtest.tactic_backtest_system import (
    _metrics,
    _normalize_event,
    _regime_metrics,
    _window_metrics,
    load_request,
)


def run_local_cache_sweep(request_paths: list[str | Path]) -> dict[str, Any]:
    requests = [load_request(path) for path in request_paths]
    if not requests:
        raise ValueError("at least one tactic backtest request is required")

    for request in requests:
        mode = request.get("data", {}).get("mode", "local_cache")
        if mode != "local_cache":
            raise ValueError("research sweep currently supports local_cache requests only")

    shared_date_range = requests[0].get("date_range", {})
    cache_context = tactic_simulator.build_local_cache_context(shared_date_range)
    symbols = sorted({symbol for request in requests for symbol in request.get("symbols", [])})
    symbol_cache = _precompute_symbol_cache(symbols, shared_date_range, cache_context)

    candidates = []
    for request in requests:
        validation = request.get("validation", {})
        windows = validation.get("windows", [])
        regime_fields = validation.get("regime_fields", [])
        params = dict(request.get("hyperparameters", {}))
        params["strategy"] = request.get("strategy", {})

        events = []
        for symbol in request.get("symbols", []):
            cached = symbol_cache.get(symbol)
            if not cached:
                continue
            symbol_events = tactic_simulator._simulate_all_trades(
                symbol=symbol,
                bars=cached["bars"],
                params=params,
                daily_metrics=cached["daily_metrics"],
            )
            events.extend(_normalize_event(event) for event in symbol_events)

        candidates.append({
            "tactic_id": request["tactic_id"],
            "symbols": request.get("symbols", []),
            "date_range": request.get("date_range", {}),
            "summary": _metrics(events),
            "validation": {
                "windows": _window_metrics(events, windows),
                "regimes": _regime_metrics(events, regime_fields),
                "min_trades_per_window": validation.get("min_trades_per_window"),
            },
            "events": events,
            "boundaries": {
                "contains_permission_decision": False,
                "config_mutation": False,
                "final_tactic_status_change": False,
            },
        })

    return {
        "packet_type": "research_sweep_evidence_packet",
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "data_mode": "local_cache_precomputed_sweep",
        "symbols": symbols,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "boundaries": {
            "contains_permission_decision": False,
            "config_mutation": False,
            "final_tactic_status_change": False,
            "notes": [
                "Evidence only. Strategy adoption remains in investing-os.",
                "No dashboard, config, position, or permission state was changed.",
            ],
        },
    }


def _precompute_symbol_cache(
    symbols: list[str],
    date_range: dict[str, str],
    cache_context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    symbol_cache = {}
    benchmark_returns = cache_context.get("benchmark_returns", {})
    for symbol in symbols:
        bars, daily_metrics = tactic_simulator._load_local_data_for_symbol(
            symbol,
            date_range,
            cache_context=cache_context,
        )
        if not bars:
            continue
        featured_bars = tactic_simulator._with_intraday_features(
            bars,
            benchmark_returns=benchmark_returns,
        )
        symbol_cache[symbol] = {
            "bars": featured_bars,
            "daily_metrics": daily_metrics,
        }
    return symbol_cache
