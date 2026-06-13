"""Unified tactic backtest evidence runner.

This module is the boundary layer between investing-os and stock_team.
It turns a brain-authored tactic backtest request into factual evidence.
It does not approve tactics, mutate config, or emit trade instructions.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

FORBIDDEN_OUTPUT_KEYS = {
    "recommendation",
    "recommended_action",
    "permission",
    "decision",
    "approved",
    "sizing",
}


def _get_default_symbols() -> list[str]:
    learning_dir = Path("D:/gemini/lianghua/stock_team/learning")
    if not learning_dir.exists():
        learning_dir = Path.cwd() / "learning"
    if not learning_dir.exists():
        return ["MU", "NVDA", "COHR"]
    symbols = []
    for f in learning_dir.glob("intraday_cache_*.csv"):
        symbol = f.name.replace("intraday_cache_", "").replace(".csv", "")
        if symbol not in ("QQQ", "SPY", "IWM", "VIX", "^VIX"):
            symbols.append(symbol)
    return sorted(symbols) if symbols else ["MU", "NVDA", "COHR"]


def load_request(path: str | Path) -> dict[str, Any]:
    request_path = Path(path)
    data = json.loads(request_path.read_text(encoding="utf-8"))
    if data.get("artifact_type") != "tactic_backtest_request":
        raise ValueError("artifact_type must be tactic_backtest_request")
    if not data.get("tactic_id"):
        raise ValueError("tactic_id is required")
        
    # Standard schema validation for the Tactic Schema Registry
    strat = data.get("strategy")
    if not strat:
        raise ValueError("strategy definition is required")
        
    entry = strat.get("entry_model")
    if not entry or "type" not in entry:
        raise ValueError("strategy.entry_model with type is required")
    allowed_entries = {"channel_reclaim", "channel_breakout", "mean_reversion", "trend_pullback"}
    if entry["type"] not in allowed_entries:
        raise ValueError(f"strategy.entry_model.type must be one of {allowed_entries}")
        
    exit_mod = strat.get("exit_model")
    if not exit_mod or "type" not in exit_mod:
        raise ValueError("strategy.exit_model with type is required")
    allowed_exits = {"fixed_pct", "atr_static", "atr_trailing_stop", "partial_scaling", "time_exit"}
    if exit_mod["type"] not in allowed_exits:
        raise ValueError(f"strategy.exit_model.type must be one of {allowed_exits}")
        
    filters = strat.get("filters", [])
    allowed_filters = {"relative_volume", "relative_strength", "macd", "rsi"}
    for f in filters:
        if "type" not in f:
            raise ValueError("each strategy filter must have a type")
        if f["type"] not in allowed_filters:
            raise ValueError(f"strategy filter type must be one of {allowed_filters}")
        # Parameter validation for each filter type
        if f["type"] == "relative_volume":
            if "min_volume_ratio" not in f:
                raise ValueError("relative_volume filter requires min_volume_ratio")
        elif f["type"] == "relative_strength":
            if "benchmark" not in f or "min_rs_diff" not in f:
                raise ValueError("relative_strength filter requires benchmark and min_rs_diff")
        elif f["type"] == "macd":
            if "signal" not in f or f["signal"] not in {"bullish_crossover", "histogram_rising"}:
                raise ValueError("macd filter requires signal ('bullish_crossover' or 'histogram_rising')")
        elif f["type"] == "rsi":
            if "min_value" not in f or "max_value" not in f:
                raise ValueError("rsi filter requires min_value and max_value")

    # Fill defaults if missing
    if "symbols" not in data or not data["symbols"]:
        # Limit to first 50 default symbols to prevent slow runs by default
        data["symbols"] = _get_default_symbols()[:50]
        
    if "date_range" not in data or not data["date_range"]:
        from datetime import date, timedelta
        today = date.today()
        yesterday = today - timedelta(days=1)
        five_years_ago = today - timedelta(days=5 * 365)
        data["date_range"] = {
            "start": five_years_ago.strftime("%Y-%m-%d"),
            "end": yesterday.strftime("%Y-%m-%d")
        }
        
    start_str = data["date_range"]["start"]
    end_str = data["date_range"]["end"]
    
    # Generate dynamic train/test OOS split based on date range
    from datetime import datetime, timedelta
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()
    except Exception as e:
        # Fallback to default parsing
        start_dt = date(2024, 6, 1)
        end_dt = date(2024, 8, 30)
        
    days = (end_dt - start_dt).days
    train_days = int(days * 0.7)
    train_end_dt = start_dt + timedelta(days=train_days)
    test_start_dt = train_end_dt + timedelta(days=1)
    
    train_end_str = train_end_dt.strftime("%Y-%m-%d")
    test_start_str = test_start_dt.strftime("%Y-%m-%d")
        
    if "validation" not in data or not data["validation"]:
        data["validation"] = {
            "windows": [
                {"name": "train", "start": start_str, "end": train_end_str},
                {"name": "test", "start": test_start_str, "end": end_str}
            ],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 0,
            "monte_carlo": {
                "enabled": True,
                "simulations": 1000
            }
        }
    else:
        val = data["validation"]
        if "windows" not in val or not val["windows"]:
            val["windows"] = [
                {"name": "train", "start": start_str, "end": train_end_str},
                {"name": "test", "start": test_start_str, "end": end_str}
            ]
        if "regime_fields" not in val:
            val["regime_fields"] = ["market_regime"]
        if "monte_carlo" not in val:
            val["monte_carlo"] = {"enabled": True, "simulations": 1000}

    contract = data.get("output_contract", {})
    if contract.get("allow_config_mutation") is not False:
        raise ValueError("output_contract.allow_config_mutation must be false")
    if contract.get("allow_recommendations") is not False:
        raise ValueError("output_contract.allow_recommendations must be false")
    _scan_for_forbidden_keys(data)
    return data


def run_request(path: str | Path) -> dict[str, Any]:
    request = load_request(path)
    data = request.get("data", {})
    if not data:
        data = {"mode": "local_cache"}
        request["data"] = data
    mode = data.get("mode", "local_cache")
    if "mode" not in data:
        data["mode"] = mode

    validation = request.get("validation", {})
    regime_fields = validation.get("regime_fields", [])
    windows = validation.get("windows", [])
    
    # Merge strategy and hyperparameters for simulator
    params = dict(request.get("hyperparameters", {}))
    params["strategy"] = request.get("strategy", {})
    data["tactic_params"] = params

    # Check if we run on local cache or inline ohlcv
    if mode == "fixture_events":
        events = [_normalize_event(e) for e in data.get("events", [])]
    elif mode in ("intraday_ohlcv_fixture", "local_cache"):
        events = []
        symbols = request.get("symbols", [])
        bars_by_symbol = data.get("bars", {})
        
        # Delegate K-line loading and rules to the decoupled tactic simulator
        from stock_team.backtest import tactic_simulator

        cache_context = None
        if mode == "local_cache":
            cache_context = tactic_simulator.build_local_cache_context(request.get("date_range", {}))
        
        for symbol in symbols:
            symbol_events = tactic_simulator.run_simulation_to_events(
                symbol=symbol,
                mode=mode,
                date_range=request.get("date_range", {}),
                params=params,
                bars_by_symbol=bars_by_symbol,
                cache_context=cache_context,
            )
            for e in symbol_events:
                events.append(_normalize_event(e))
    else:
        raise ValueError(f"Unsupported data.mode: {mode}")

    # Monte Carlo Bootstrapping
    mc_results = {}
    mc_config = validation.get("monte_carlo", {})
    if mc_config.get("enabled", False) and events:
        sims = int(mc_config.get("simulations", 1000))
        mc_results = _run_monte_carlo_bootstrap(events, simulations=sims)

    # Sharpe/Sortino/Calmar summary
    summary_metrics = _metrics(events)

    result = {
        "packet_type": "tactic_backtest_evidence_packet",
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "tactic_id": request["tactic_id"],
        "symbols": request["symbols"],
        "date_range": request.get("date_range", {}),
        "data_mode": mode,
        "summary": summary_metrics,
        "validation": {
            "windows": _window_metrics(events, windows),
            "regimes": _regime_metrics(events, regime_fields),
            "min_trades_per_window": validation.get("min_trades_per_window"),
        },
        "monte_carlo": mc_results,
        "boundaries": {
            "contains_permission_decision": False,
            "config_mutation": False,
            "final_tactic_status_change": False,
            "notes": [
                "Evidence only. Tactic approval remains in investing-os.",
                "No config, position, or permission state was changed.",
            ],
        },
        "events": events,
    }
    return result


def write_outputs(
    result: dict[str, Any],
    md_path: str | Path,
    json_path: str | Path | None = None,
) -> None:
    md_target = Path(md_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    
    md_content = render_markdown(result)
    censored_md = _censor_text(md_content)
    md_target.write_text(censored_md, encoding="utf-8")
    
    if json_path:
        json_target = Path(json_path)
        json_target.parent.mkdir(parents=True, exist_ok=True)
        json_content = json.dumps(result, indent=2, ensure_ascii=False)
        censored_json = _censor_text(json_content)
        json_target.write_text(censored_json, encoding="utf-8")


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "---",
        "packet_type: tactic_backtest_evidence_packet",
        f"tactic_id: {result['tactic_id']}",
        f"generated_at: {result['generated_at']}",
        "authority: evidence_only",
        "---",
        "",
        f"# Tactic Backtest Evidence Packet: {result['tactic_id']}",
        "",
        "## Boundary",
        "",
        "**No Permission Decision.** This packet contains factual validation evidence only.",
        "Tactic approval, portfolio action, and rule adoption remain outside stock_team.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| :--- | ---: |",
    ]
    for key, value in result["summary"].items():
        lines.append(f"| {key} | {_fmt(value)} |")
        
    # Walk-forward / Monte Carlo Bootstrap rendering if present
    if result.get("monte_carlo"):
        lines.extend([
            "",
            "## Monte Carlo Stress Test & VaR Analysis (1,000+ Re-samples)",
            "",
            "| Downside Metric | Value |",
            "| :--- | ---: |",
        ])
        for key, value in result["monte_carlo"].items():
            lines.append(f"| {key} | {_fmt(value)} |")

    lines.extend(["", "## Validation Windows", "", "| Window | Trades | Win Rate | Avg Return % | Profit Factor | Sharpe | Max DD % |", "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for name, metrics in result["validation"]["windows"].items():
        lines.append(
            f"| {name} | {metrics['n_trades']} | {_fmt_pct(metrics['win_rate'])} | "
            f"{_fmt(metrics['avg_return_pct'])} | {_fmt(metrics['profit_factor'])} | "
            f"{_fmt(metrics['sharpe_ratio'])} | {_fmt(metrics['max_drawdown_pct'])} |"
        )
    lines.extend(["", "## Regime Segments", "", "| Segment | Trades | Win Rate | Avg Return % | MAE % | MFE % | Sharpe |", "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for name, metrics in result["validation"]["regimes"].items():
        lines.append(
            f"| {name} | {metrics['n_trades']} | {_fmt_pct(metrics['win_rate'])} | "
            f"{_fmt(metrics['avg_return_pct'])} | {_fmt(metrics['avg_mae_pct'])} | "
            f"{_fmt(metrics['avg_mfe_pct'])} | {_fmt(metrics['sharpe_ratio'])} |"
        )
    lines.extend(["", "## Machine Summary", "", "```json", json.dumps(result, indent=2, ensure_ascii=False), "```", ""])
    return "\n".join(lines)


def _scan_for_forbidden_keys(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"Forbidden request key: {path + key}")
            _scan_for_forbidden_keys(child, f"{path}{key}.")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_for_forbidden_keys(child, f"{path}{index}.")


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        **event,
        "return_pct": float(event.get("return_pct", 0.0)),
        "mae_pct": float(event.get("mae_pct", 0.0)),
        "mfe_pct": float(event.get("mfe_pct", 0.0)),
        "entry_date": _date_part(event.get("entry_time", "")),
    }


def _normalize_bar(bar: dict[str, Any]) -> dict[str, Any]:
    return {
        **bar,
        "open": float(bar["open"]),
        "high": float(bar["high"]),
        "low": float(bar["low"]),
        "close": float(bar["close"]),
        "volume": float(bar["volume"]),
        "time": bar.get("time") or _time_part(bar["timestamp"]),
    }


def _date_part(value: str) -> str:
    return value[:10]


def _time_part(value: str) -> str:
    return value[11:16]


def _metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "n_trades": 0,
            "win_rate": None,
            "avg_return_pct": None,
            "avg_win_pct": None,
            "avg_loss_pct": None,
            "profit_factor": None,
            "avg_mae_pct": None,
            "avg_mfe_pct": None,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "calmar_ratio": None,
            "max_drawdown_pct": None,
        }

    returns = [e["return_pct"] for e in events]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    # Daily resampled calculation
    dates = [e["exit_time"][:10] for e in events]
    daily_rets = {}
    for e in events:
        dt = e["exit_time"][:10]
        daily_rets[dt] = daily_rets.get(dt, 0.0) + (e["return_pct"] / 100.0)

    start_date = min(dates)
    end_date = max(dates)
    all_dates = pd.date_range(start=start_date, end=end_date, freq="B")

    series_rets = pd.Series(0.0, index=all_dates)
    for dt, ret in daily_rets.items():
        dt_parsed = pd.to_datetime(dt)
        if dt_parsed in series_rets.index:
            series_rets[dt_parsed] = ret

    rf_daily = 0.04 / 252
    excess = series_rets - rf_daily

    std_ret = series_rets.std()
    sharpe = (np.sqrt(252) * (excess.mean() / std_ret)) if std_ret > 0 else 0.0

    downside_rets = excess[excess < 0]
    downside_std = downside_rets.std()
    sortino = (excess.mean() * 252) / (downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

    cum_equity = (1.0 + series_rets).cumprod()
    peak = cum_equity.cummax()
    dd = (cum_equity - peak) / peak
    max_dd_pct = float(dd.min()) * 100.0 if not dd.empty else 0.0

    annualized_return = series_rets.mean() * 252 * 100.0
    calmar = (annualized_return / abs(max_dd_pct)) if max_dd_pct != 0 else 0.0

    return {
        "n_trades": len(events),
        "win_rate": (len(wins) / len(events)) if events else None,
        "avg_return_pct": (sum(returns) / len(returns)) if returns else None,
        "avg_win_pct": (sum(wins) / len(wins)) if wins else None,
        "avg_loss_pct": (sum(losses) / len(losses)) if losses else None,
        "profit_factor": (gross_win / gross_loss) if gross_loss else None,
        "avg_mae_pct": _avg([e["mae_pct"] for e in events]),
        "avg_mfe_pct": _avg([e["mfe_pct"] for e in events]),
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "max_drawdown_pct": max_dd_pct,
    }


def _window_metrics(
    events: list[dict[str, Any]],
    windows: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    segmented = {}
    for window in windows:
        start = date.fromisoformat(window["start"])
        end = date.fromisoformat(window["end"])
        members = [
            e for e in events
            if start <= date.fromisoformat(e["entry_date"]) <= end
        ]
        segmented[window["name"]] = _metrics(members)
    return segmented


def _regime_metrics(
    events: list[dict[str, Any]],
    regime_fields: list[str],
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        for field in regime_fields:
            groups[f"{field}:{event.get(field, 'unknown')}"].append(event)
    return {name: _metrics(members) for name, members in sorted(groups.items())}


def _avg(values: list[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


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


def _run_monte_carlo_bootstrap(events: list[dict[str, Any]], simulations: int = 1000) -> dict[str, Any]:
    if not events:
        return {}
        
    returns = np.array([e["return_pct"] / 100.0 for e in events])
    num_trades = len(returns)
    
    simulated_final_returns = []
    simulated_max_drawdowns = []
    
    np.random.seed(42)
    
    for _ in range(simulations):
        boot_returns = np.random.choice(returns, size=num_trades, replace=True)
        equity = [1.0]
        for r in boot_returns:
            equity.append(equity[-1] * (1.0 + r))
            
        equity = np.array(equity)
        final_ret = (equity[-1] - 1.0) * 100.0
        simulated_final_returns.append(final_ret)
        
        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / peak * 100.0
        simulated_max_drawdowns.append(dd.min())
        
    simulated_final_returns = np.array(simulated_final_returns)
    simulated_max_drawdowns = np.array(simulated_max_drawdowns)
    
    var_95_ret = np.percentile(simulated_final_returns, 5)
    cvar_95_ret = simulated_final_returns[simulated_final_returns <= var_95_ret].mean()
    mdd_95 = np.percentile(simulated_max_drawdowns, 5)
    
    var_99_ret = np.percentile(simulated_final_returns, 1)
    cvar_99_ret = simulated_final_returns[simulated_final_returns <= var_99_ret].mean()
    mdd_99 = np.percentile(simulated_max_drawdowns, 1)
    
    return {
        "var_95_return_pct": float(var_95_ret),
        "cvar_95_return_pct": float(cvar_95_ret) if not np.isnan(cvar_95_ret) else 0.0,
        "mdd_95_pct": float(mdd_95),
        "var_99_return_pct": float(var_99_ret),
        "cvar_99_return_pct": float(cvar_99_ret) if not np.isnan(cvar_99_ret) else 0.0,
        "mdd_99_pct": float(mdd_99),
    }


def _censor_text(text: str) -> str:
    replacements = {
        r"\bbuying\b": "entering",
        r"\bBuying\b": "Entering",
        r"\bBUYING\b": "ENTERING",
        r"\bselling\b": "exiting",
        r"\bSelling\b": "Exiting",
        r"\bSELLING\b": "EXITING",
        r"\bholding\b": "exposure",
        r"\bHolding\b": "Exposure",
        r"\bHOLDING\b": "EXPOSURE",
        r"\bholdings\b": "exposures",
        r"\bHoldings\b": "Exposures",
        r"\bHOLDINGS\b": "EXPOSURES",
        r"\bbuys\b": "entries",
        r"\bBuys\b": "Entries",
        r"\bBUYS\b": "ENTRIES",
        r"\bsells\b": "exits",
        r"\bSells\b": "Exits",
        r"\bSELLS\b": "EXITS",
        r"\bholds\b": "exposures",
        r"\bHolds\b": "Exposures",
        r"\bHOLDS\b": "EXPOSURES",
        r"\bbuy\b": "entry",
        r"\bBuy\b": "Entry",
        r"\bBUY\b": "ENTRY",
        r"\bsell\b": "exit",
        r"\bSell\b": "Exit",
        r"\bSELL\b": "EXIT",
        r"\bhold\b": "exposure",
        r"\bHold\b": "Exposure",
        r"\bHOLD\b": "EXPOSURE",
    }
    censored = text
    for pattern, repl in replacements.items():
        censored = re.sub(pattern, repl, censored)
    return censored
