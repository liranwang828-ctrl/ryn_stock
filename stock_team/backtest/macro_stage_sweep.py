"""Daily macro / Stage 0+1 factor sweep.

This is the correct entry point for macro context and candidate-pool research.
It uses daily bars and multi-day forward outcomes only. It does not model
intraday triggers, fixed take-profit/stop-loss exits, or same-day exits.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from stock_team.backtest.backtest_macro import compute_metrics as _legacy_compute_metrics

OUTCOME_HORIZONS = ["fwd_3d", "fwd_5d", "fwd_10d", "fwd_20d"]


def load_candidate_pool(
    cache_dir: str | Path,
    watchlist_path: str | Path | None = None,
    limit: int = 50,
) -> list[str]:
    cache = Path(cache_dir)
    pool: list[str] = []
    if watchlist_path and Path(watchlist_path).exists():
        payload = json.loads(Path(watchlist_path).read_text(encoding="utf-8"))
        for symbol in _extract_watchlist_symbols(payload):
            if _daily_cache_exists(cache, symbol) and symbol not in pool:
                pool.append(symbol)
                if len(pool) >= limit:
                    return pool

    cache_symbols = []
    for path in cache.glob("daily_cache_*.csv"):
        symbol = path.stem.replace("daily_cache_", "")
        if symbol in {"QQQ", "SPY", "^VIX", "IWM", "VIX"}:
            continue
        cache_symbols.append((symbol, path.stat().st_size))
    cache_symbols.sort(key=lambda item: (-item[1], item[0]))
    for symbol, _size in cache_symbols:
        if symbol not in pool:
            pool.append(symbol)
            if len(pool) >= limit:
                break
    return pool


def run_daily_macro_stage_sweep(
    cache_dir: str | Path,
    symbols: list[str],
    date_range: dict[str, str],
    gates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cache = Path(cache_dir)
    gates = gates or _default_gates()
    qqq = _read_daily(cache / "daily_cache_QQQ.csv", date_range)
    vix = _read_daily(cache / "daily_cache_^VIX.csv", date_range)
    data_warnings: list[str] = []
    volume_proxy_path = cache / "daily_cache_SPY.csv"
    if volume_proxy_path.exists():
        volume_proxy = _read_daily(volume_proxy_path, date_range)
    else:
        volume_proxy = qqq
        data_warnings.append("volume_proxy_fallback_to_qqq")
    market = _build_market_context(qqq, vix, volume_proxy)

    symbol_frames = []
    for symbol in symbols:
        path = cache / f"daily_cache_{symbol}.csv"
        if not path.exists():
            continue
        frame = _build_symbol_context(symbol, _read_daily(path, date_range), qqq, market)
        if not frame.empty:
            symbol_frames.append(frame)

    combined = pd.concat(symbol_frames, ignore_index=True) if symbol_frames else pd.DataFrame()
    gate_results = []
    for gate in gates:
        matched = _apply_gate(combined, gate.get("conditions", {})) if not combined.empty else combined
        gate_results.append({
            "gate_id": gate["gate_id"],
            "conditions": gate.get("conditions", {}),
            "metrics": {horizon: _forward_metrics(matched, horizon) for horizon in OUTCOME_HORIZONS},
            "diagnostics": _gate_diagnostics(matched),
            "symbol_segments": _symbol_segments(matched),
            "boundaries": _boundaries(),
        })

    return {
        "packet_type": "macro_stage_sweep_evidence_packet",
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "date_range": date_range,
        "symbols": symbols,
        "symbols_loaded": sorted(combined["symbol"].unique().tolist()) if not combined.empty else [],
        "n_daily_rows": int(len(combined)),
        "data_warnings": data_warnings,
        "outcome_horizons": OUTCOME_HORIZONS,
        "gates": gate_results,
        "boundaries": _boundaries(),
    }


def run_cycle_factor_search(
    cache_dir: str | Path,
    symbols: list[str],
    date_range: dict[str, str],
    max_candidates: int = 20,
) -> dict[str, Any]:
    gates = _cycle_factor_candidate_gates()
    sweep = run_daily_macro_stage_sweep(cache_dir=cache_dir, symbols=symbols, date_range=date_range, gates=gates)
    ranked = []
    for gate in sweep["gates"]:
        score = _score_cycle_candidate(gate)
        candidate = {
            "gate_id": gate["gate_id"],
            "conditions": gate["conditions"],
            "score": score,
            "grade": _grade_cycle_candidate(score, gate),
            "primary_metrics": gate["metrics"]["fwd_10d"],
            "diagnostics": gate["diagnostics"],
            "boundaries": gate["boundaries"],
        }
        ranked.append(candidate)
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return {
        "packet_type": "cycle_factor_search_evidence_packet",
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "date_range": date_range,
        "symbols": symbols,
        "symbols_loaded": sweep["symbols_loaded"],
        "n_daily_rows": sweep["n_daily_rows"],
        "data_warnings": sweep["data_warnings"],
        "ranked_candidates": ranked[:max_candidates],
        "boundaries": _boundaries(),
    }


def write_outputs(result: dict[str, Any], md_path: str | Path, json_path: str | Path | None = None) -> None:
    md_target = Path(md_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(render_markdown(result), encoding="utf-8")
    if json_path:
        json_target = Path(json_path)
        json_target.parent.mkdir(parents=True, exist_ok=True)
        json_target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Macro Stage Sweep Evidence",
        "",
        "Evidence only. Daily/multi-day macro-stage research, not intraday execution.",
        "",
        f"symbols_loaded: {len(result.get('symbols_loaded', []))}",
        f"n_daily_rows: {result.get('n_daily_rows', 0)}",
        f"data_warnings: {', '.join(result.get('data_warnings') or []) or 'none'}",
        "",
        "| gate | horizon | n | win_rate | avg_return_pct | alpha_vs_qqq_pct | sharpe_proxy | sortino | max_drawdown | avg_mae_pct | avg_mfe_pct |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for gate in result["gates"]:
        for horizon, metrics in gate["metrics"].items():
            lines.append(
                f"| {gate['gate_id']} | {horizon} | {metrics['n_events']} | "
                f"{_fmt(metrics['win_rate'])} | {_fmt(metrics['avg_return_pct'])} | "
                f"{_fmt(metrics.get('alpha_vs_qqq_pct'))} | {_fmt(metrics.get('sharpe_proxy'))} | "
                f"{_fmt(metrics.get('sortino'))} | "
                f"{_fmt(metrics.get('max_drawdown'))} | "
                f"{_fmt(metrics['avg_mae_pct'])} | {_fmt(metrics['avg_mfe_pct'])} |"
            )
        diagnostics = gate.get("diagnostics", {})
        oos = diagnostics.get("walk_forward_oos", {})
        overfit = diagnostics.get("overfit_risk", {})
        test_metrics = oos.get("test", {})
        lines.extend([
            "",
            f"## {gate['gate_id']} diagnostics",
            "",
            f"walk_forward_oos: method={oos.get('method', '-')} test_n={test_metrics.get('n_events', '-')} "
            f"test_avg_return_pct={_fmt(test_metrics.get('avg_return_pct'))} "
            f"test_alpha_vs_qqq_pct={_fmt(test_metrics.get('alpha_vs_qqq_pct'))}",
        f"overfit_risk: risk_level={overfit.get('risk_level', '-')} "
        f"sample_size_ok={overfit.get('sample_size_ok', '-')} "
        f"stability_rate={_fmt(overfit.get('stability_rate'))} "
        f"oos_degradation_pct={_fmt(overfit.get('oos_degradation_pct'))}",
            "market_cycle_windows: "
            + ", ".join(
                f"{name}(n={metrics.get('n_events', '-')}, alpha={_fmt(metrics.get('alpha_vs_qqq_pct'))})"
                for name, metrics in diagnostics.get("market_cycle_windows", {}).items()
            ),
            "max_drawdown_basis: legacy_event_sequence_not_portfolio_equity",
            "",
        ])
    return "\n".join(lines) + "\n"


def _daily_cache_exists(cache: Path, symbol: str) -> bool:
    return (cache / f"daily_cache_{symbol}.csv").exists()


def _extract_watchlist_symbols(payload: dict[str, Any]) -> list[str]:
    symbols: list[str] = []

    def add_symbol(value: str) -> None:
        symbol = value.strip().upper()
        if symbol and symbol.startswith("_") is False and symbol not in symbols:
            symbols.append(symbol)

    explicit_watchlist = payload.get("watchlist")
    if isinstance(explicit_watchlist, dict):
        for symbol in explicit_watchlist.keys():
            add_symbol(symbol)

    for section_value in payload.values():
        if not isinstance(section_value, dict):
            continue
        for symbol, detail in section_value.items():
            if symbol.startswith("_"):
                continue
            if isinstance(detail, dict):
                add_symbol(symbol)
    return symbols


def _read_daily(path: str | Path, date_range: dict[str, str]) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["Date"], utc=True).dt.strftime("%Y-%m-%d")
    start = date_range.get("start")
    end = date_range.get("end")
    if start:
        df = df[df["date"] >= start]
    if end:
        df = df[df["date"] <= end]
    return df.sort_values("date").reset_index(drop=True)


def _build_market_context(qqq: pd.DataFrame, vix: pd.DataFrame, volume_proxy: pd.DataFrame) -> pd.DataFrame:
    market = qqq[["date", "Close", "Volume"]].rename(columns={"Close": "qqq_close", "Volume": "qqq_volume"})
    market["qqq_ma20"] = market["qqq_close"].rolling(20, min_periods=5).mean()
    market["qqq_ma50"] = market["qqq_close"].rolling(50, min_periods=10).mean()
    market["qqq_ma100"] = market["qqq_close"].rolling(100, min_periods=30).mean()
    market["qqq_ret5"] = market["qqq_close"].pct_change(5, fill_method=None)
    market["qqq_ret60"] = market["qqq_close"].pct_change(60, fill_method=None)
    market["qqq_regime"] = "qqq_unknown"
    market.loc[(market["qqq_close"] >= market["qqq_ma20"]) & (market["qqq_ret5"] >= -0.01), "qqq_regime"] = "qqq_uptrend"
    market.loc[(market["qqq_close"] < market["qqq_ma20"]) | (market["qqq_ret5"] <= -0.02), "qqq_regime"] = "qqq_downtrend"
    market["qqq_cycle_regime"] = "transition_market"
    market.loc[
        (market["qqq_close"] >= market["qqq_ma100"]) & (market["qqq_ret60"] >= 0),
        "qqq_cycle_regime",
    ] = "bull_market"
    market.loc[
        (market["qqq_close"] < market["qqq_ma100"]) & (market["qqq_ret60"] <= 0),
        "qqq_cycle_regime",
    ] = "bear_market"

    vix_small = vix[["date", "Close"]].rename(columns={"Close": "vix_close"})
    vix_small["vix_direction"] = vix_small["vix_close"].diff().map(lambda value: "rising" if value > 0 else "falling")
    vix_small["vix_level"] = vix_small["vix_close"].map(lambda value: "high" if value >= 20 else "low")
    vix_small["vix_regime"] = "vix_" + vix_small["vix_level"] + "_" + vix_small["vix_direction"]
    market = market.merge(vix_small[["date", "vix_close", "vix_regime"]], on="date", how="left")

    vol = volume_proxy[["date", "Volume"]].rename(columns={"Volume": "market_volume"})
    vol["market_volume_ma20"] = vol["market_volume"].rolling(20, min_periods=5).mean()
    vol["market_volume_ratio"] = vol["market_volume"] / vol["market_volume_ma20"]
    market = market.merge(vol[["date", "market_volume_ratio"]], on="date", how="left")
    market["market_volume_regime"] = "normal_volume"
    market.loc[market["market_volume_ratio"] >= 1.5, "market_volume_regime"] = "high_volume_expansion"
    market.loc[
        (market["market_volume_ratio"] >= 1.5) & (market["qqq_close"].pct_change(fill_method=None) < 0),
        "market_volume_regime",
    ] = "high_volume_risk_off"
    return market


def _build_symbol_context(symbol: str, symbol_df: pd.DataFrame, qqq: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    frame = symbol_df[["date", "Close", "High", "Low", "Volume"]].rename(
        columns={"Close": "close", "High": "high", "Low": "low", "Volume": "volume"}
    )
    qqq_ref = _benchmark_forward_frame(qqq)
    frame = frame.merge(qqq_ref, on="date", how="left").merge(market, on="date", how="left")
    frame["symbol"] = symbol
    for days in [5, 10, 20, 50]:
        frame[f"symbol_ret{days}"] = frame["close"].pct_change(days, fill_method=None)
        frame[f"qqq_ret{days}"] = frame["qqq_close_ref"].pct_change(days, fill_method=None)
        frame[f"symbol_rs{days}"] = (frame[f"symbol_ret{days}"] - frame[f"qqq_ret{days}"]) * 100.0
    frame["symbol_ma20"] = frame["close"].rolling(20, min_periods=5).mean()
    frame["symbol_ma50"] = frame["close"].rolling(50, min_periods=10).mean()
    frame["symbol_above_ma20"] = frame["close"] >= frame["symbol_ma20"]
    frame["symbol_above_ma50"] = frame["close"] >= frame["symbol_ma50"]
    frame["symbol_ma20_dist_pct"] = (frame["close"] / frame["symbol_ma20"] - 1.0) * 100.0
    frame["symbol_ma50_dist_pct"] = (frame["close"] / frame["symbol_ma50"] - 1.0) * 100.0
    frame["symbol_pullback_5d_pct"] = frame["close"].pct_change(5, fill_method=None) * 100.0
    for days in [3, 5, 10, 20]:
        frame[f"fwd_{days}d"] = frame["close"].pct_change(days, fill_method=None).shift(-days) * 100.0
        frame[f"mae_{days}d"] = (frame["low"].rolling(days, min_periods=1).min().shift(-days + 1) / frame["close"] - 1.0) * 100.0
        frame[f"mfe_{days}d"] = (frame["high"].rolling(days, min_periods=1).max().shift(-days + 1) / frame["close"] - 1.0) * 100.0
    return frame


def _benchmark_forward_frame(qqq: pd.DataFrame) -> pd.DataFrame:
    qqq_ref = qqq[["date", "Close"]].rename(columns={"Close": "qqq_close_ref"}).copy()
    for days in [3, 5, 10, 20]:
        qqq_ref[f"qqq_fwd_{days}d"] = qqq_ref["qqq_close_ref"].pct_change(days, fill_method=None).shift(-days) * 100.0
    return qqq_ref


def _apply_gate(df: pd.DataFrame, conditions: dict[str, Any]) -> pd.DataFrame:
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    for key, allowed in conditions.items():
        if key == "min_symbol_rs20":
            mask &= df["symbol_rs20"] >= float(allowed)
        elif key.startswith("min_symbol_rs"):
            window = key.replace("min_symbol_rs", "")
            mask &= df[f"symbol_rs{window}"] >= float(allowed)
        elif key.startswith("max_symbol_rs"):
            window = key.replace("max_symbol_rs", "")
            mask &= df[f"symbol_rs{window}"] <= float(allowed)
        elif key == "max_symbol_ma20_dist_pct":
            mask &= df["symbol_ma20_dist_pct"] <= float(allowed)
        elif key == "min_symbol_ma20_dist_pct":
            mask &= df["symbol_ma20_dist_pct"] >= float(allowed)
        elif key == "max_symbol_pullback_5d_pct":
            mask &= df["symbol_pullback_5d_pct"] <= float(allowed)
        elif key == "min_symbol_pullback_5d_pct":
            mask &= df["symbol_pullback_5d_pct"] >= float(allowed)
        elif key == "symbol_above_ma20":
            mask &= df["symbol_above_ma20"] == bool(allowed)
        elif key == "symbol_above_ma50":
            mask &= df["symbol_above_ma50"] == bool(allowed)
        elif key in df.columns:
            values = allowed if isinstance(allowed, list) else [allowed]
            mask &= df[key].isin(values)
    return df[mask]


def _forward_metrics(df: pd.DataFrame, horizon: str) -> dict[str, Any]:
    days = horizon.replace("fwd_", "").replace("d", "")
    cols = [horizon, f"qqq_fwd_{days}d", f"mae_{days}d", f"mfe_{days}d"]
    rows = df[[col for col in cols if col in df.columns]].dropna(subset=[horizon]) if not df.empty else df
    clean = [float(value) for value in rows[horizon].tolist()] if not rows.empty else []
    if not clean:
        return {
            "metric_source": "backtest_macro.compute_metrics",
            "n_events": 0,
            "win_rate": None,
            "avg_return_pct": None,
            "avg_mae_pct": None,
            "avg_mfe_pct": None,
            "alpha_vs_qqq_pct": None,
            "sharpe_proxy": None,
            "sortino": None,
            "max_drawdown": None,
            "max_drawdown_basis": "legacy_event_sequence_not_portfolio_equity",
            "legacy_metrics": _legacy_compute_metrics([]),
        }
    wins = [value for value in clean if value > 0]
    mae_values = [float(value) for value in rows[f"mae_{days}d"].dropna().tolist()]
    mfe_values = [float(value) for value in rows[f"mfe_{days}d"].dropna().tolist()]
    qqq_values = [float(value) for value in rows[f"qqq_fwd_{days}d"].dropna().tolist()] if f"qqq_fwd_{days}d" in rows else []
    legacy = _legacy_compute_metrics([value / 100.0 for value in clean])
    sharpe_proxy = _sharpe_proxy(clean)
    return {
        "metric_source": "backtest_macro.compute_metrics",
        "n_events": len(clean),
        "win_rate": len(wins) / len(clean),
        "avg_return_pct": sum(clean) / len(clean),
        "avg_mae_pct": sum(mae_values) / len(mae_values) if mae_values else None,
        "avg_mfe_pct": sum(mfe_values) / len(mfe_values) if mfe_values else None,
        "avg_qqq_return_pct": sum(qqq_values) / len(qqq_values) if qqq_values else None,
        "alpha_vs_qqq_pct": (sum(clean) / len(clean)) - (sum(qqq_values) / len(qqq_values)) if qqq_values else None,
        "sharpe_proxy": sharpe_proxy,
        "sortino": legacy.get("sortino"),
        "max_drawdown": legacy.get("max_drawdown"),
        "max_drawdown_basis": "legacy_event_sequence_not_portfolio_equity",
        "rr_ratio": legacy.get("rr_ratio"),
        "ev": legacy.get("ev"),
        "legacy_metrics": legacy,
    }


def _sharpe_proxy(values_pct: list[float]) -> float | None:
    if len(values_pct) < 2:
        return None
    series = pd.Series([value / 100.0 for value in values_pct])
    std = series.std()
    if std == 0 or pd.isna(std):
        return None
    ann_factor = min(len(series), 50) ** 0.5
    return round(float(series.mean() / std * ann_factor), 3)


def _gate_diagnostics(df: pd.DataFrame) -> dict[str, Any]:
    horizon = "fwd_10d"
    if df.empty or horizon not in df.columns:
        return {
            "primary_horizon": horizon,
            "yearly_windows": {},
            "market_cycle_windows": {},
            "walk_forward_oos": {"method": "anchored_time_split", "train": _forward_metrics(df, horizon), "test": _forward_metrics(df, horizon)},
            "overfit_risk": {"sample_size_ok": False, "oos_degradation_pct": None, "risk_level": "insufficient_data"},
        }

    yearly_windows = {}
    dated = df.dropna(subset=[horizon]).copy()
    dated["year"] = dated["date"].str.slice(0, 4)
    for year, group in dated.groupby("year"):
        yearly_windows[year] = _forward_metrics(group, horizon)
    market_cycle_windows = {}
    if "qqq_cycle_regime" in dated.columns:
        for regime, group in dated.groupby("qqq_cycle_regime"):
            market_cycle_windows[regime] = _forward_metrics(group, horizon)

    sorted_rows = dated.sort_values("date")
    split_at = max(1, int(len(sorted_rows) * 0.6))
    train = sorted_rows.iloc[:split_at]
    test = sorted_rows.iloc[split_at:]
    train_metrics = _forward_metrics(train, horizon)
    test_metrics = _forward_metrics(test, horizon)
    train_avg = train_metrics.get("avg_return_pct")
    test_avg = test_metrics.get("avg_return_pct")
    degradation = (test_avg - train_avg) if train_avg is not None and test_avg is not None else None
    yearly_positive = [
        metrics.get("avg_return_pct", 0) > 0
        for metrics in yearly_windows.values()
        if metrics.get("avg_return_pct") is not None
    ]
    stability_rate = (sum(yearly_positive) / len(yearly_positive)) if yearly_positive else None
    sample_size_ok = bool(test_metrics.get("n_events", 0) >= 30 and train_metrics.get("n_events", 0) >= 50)
    risk_level = "low"
    if not sample_size_ok:
        risk_level = "high"
    elif degradation is not None and degradation < -1.0:
        risk_level = "medium"
    if stability_rate is not None and stability_rate < 0.5:
        risk_level = "high"

    return {
        "primary_horizon": horizon,
        "yearly_windows": yearly_windows,
        "market_cycle_windows": market_cycle_windows,
        "walk_forward_oos": {
            "method": "anchored_time_split",
            "train": train_metrics,
            "test": test_metrics,
        },
        "overfit_risk": {
            "sample_size_ok": sample_size_ok,
            "stability_rate": stability_rate,
            "oos_degradation_pct": degradation,
            "risk_level": risk_level,
        },
    }


def _symbol_segments(df: pd.DataFrame) -> dict[str, Any]:
    segments = {}
    if df.empty:
        return segments
    for symbol, group in df.groupby("symbol"):
        segments[symbol] = {horizon: _forward_metrics(group, horizon) for horizon in OUTCOME_HORIZONS}
    return segments


def _cycle_factor_candidate_gates() -> list[dict[str, Any]]:
    gates = [
        {"gate_id": "baseline_all_candidates_v1", "conditions": {}},
        {
            "gate_id": "bull_rs20_above_ma50_v1",
            "conditions": {"qqq_cycle_regime": ["bull_market"], "min_symbol_rs20": 0.0, "symbol_above_ma50": True},
        },
        {
            "gate_id": "bull_rs50_above_ma50_v1",
            "conditions": {"qqq_cycle_regime": ["bull_market"], "min_symbol_rs50": 0.0, "symbol_above_ma50": True},
        },
        {
            "gate_id": "bull_rs20_ma20_pullback_v1",
            "conditions": {
                "qqq_cycle_regime": ["bull_market"],
                "min_symbol_rs20": 0.0,
                "symbol_above_ma50": True,
                "max_symbol_ma20_dist_pct": 5.0,
                "min_symbol_ma20_dist_pct": -3.0,
            },
        },
        {
            "gate_id": "bull_rs50_short_pullback_v1",
            "conditions": {
                "qqq_cycle_regime": ["bull_market"],
                "min_symbol_rs50": 0.0,
                "symbol_above_ma50": True,
                "max_symbol_pullback_5d_pct": 0.0,
                "min_symbol_pullback_5d_pct": -8.0,
            },
        },
        {
            "gate_id": "bear_relative_strength_defense_v1",
            "conditions": {"qqq_cycle_regime": ["bear_market"], "min_symbol_rs20": 0.0, "symbol_above_ma20": True},
        },
        {
            "gate_id": "bear_rs50_above_ma50_defense_v1",
            "conditions": {"qqq_cycle_regime": ["bear_market"], "min_symbol_rs50": 0.0, "symbol_above_ma50": True},
        },
        {
            "gate_id": "transition_strict_rs50_v1",
            "conditions": {
                "qqq_cycle_regime": ["transition_market"],
                "min_symbol_rs50": 5.0,
                "symbol_above_ma50": True,
                "symbol_above_ma20": True,
            },
        },
        {
            "gate_id": "cycle_aware_rs50_no_transition_v1",
            "conditions": {
                "qqq_cycle_regime": ["bull_market", "bear_market"],
                "min_symbol_rs50": 0.0,
                "symbol_above_ma50": True,
            },
        },
        {
            "gate_id": "cycle_aware_rs20_no_transition_v1",
            "conditions": {
                "qqq_cycle_regime": ["bull_market", "bear_market"],
                "min_symbol_rs20": 0.0,
                "symbol_above_ma50": True,
            },
        },
    ]
    return gates


def _score_cycle_candidate(gate: dict[str, Any]) -> float:
    metrics = gate["metrics"]["fwd_10d"]
    diagnostics = gate["diagnostics"]
    cycles = diagnostics.get("market_cycle_windows", {})
    bull = cycles.get("bull_market", {})
    bear = cycles.get("bear_market", {})
    transition = cycles.get("transition_market", {})
    overfit = diagnostics.get("overfit_risk", {})

    score = 0.0
    score += 2.0 * _num(bull.get("alpha_vs_qqq_pct"))
    score += 1.5 * _num(bear.get("alpha_vs_qqq_pct"))
    score += 0.75 * min(_num(transition.get("alpha_vs_qqq_pct")), 0.0)
    score += 0.5 * _num(metrics.get("sharpe_proxy"))
    score += 0.5 * _num(metrics.get("avg_return_pct"))
    if metrics.get("n_events", 0) < 100:
        score -= 2.0
    if bull and bull.get("n_events", 0) < 50:
        score -= 1.0
    if overfit.get("risk_level") == "high":
        score -= 1.5
    elif overfit.get("risk_level") == "medium":
        score -= 0.5
    degradation = overfit.get("oos_degradation_pct")
    if degradation is not None and degradation < -1.0:
        score += degradation
    return round(score, 3)


def _grade_cycle_candidate(score: float, gate: dict[str, Any]) -> str:
    metrics = gate["metrics"]["fwd_10d"]
    if metrics.get("n_events", 0) < 80:
        return "Reject"
    if score >= 2.5:
        return "A"
    if score >= 0.75:
        return "B"
    if score >= 0:
        return "C"
    return "Reject"


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _boundaries() -> dict[str, Any]:
    return {
        "contains_permission_decision": False,
        "config_mutation": False,
        "uses_intraday_exit": False,
        "uses_fixed_take_profit_stop_loss": False,
        "forces_same_day_exit": False,
    }


def _default_gates() -> list[dict[str, Any]]:
    return [
        {
            "gate_id": "macro_uptrend_low_vix_rs20_v1",
            "conditions": {
                "qqq_regime": ["qqq_uptrend"],
                "vix_regime": ["vix_low_falling", "vix_low_rising"],
                "min_symbol_rs20": 0.0,
                "symbol_above_ma20": True,
            },
        },
        {
            "gate_id": "macro_uptrend_any_vix_rs20_v1",
            "conditions": {
                "qqq_regime": ["qqq_uptrend"],
                "min_symbol_rs20": 0.0,
                "symbol_above_ma20": True,
            },
        },
        {
            "gate_id": "macro_pullback_uptrend_rs20_v1",
            "conditions": {
                "qqq_regime": ["qqq_uptrend"],
                "min_symbol_rs20": 0.0,
                "symbol_above_ma50": True,
            },
        },
    ]


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)
