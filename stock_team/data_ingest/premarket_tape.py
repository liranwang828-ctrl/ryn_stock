"""Observation-only cross-asset premarket tape."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")
FRESH_MINUTES = 10
AGING_MINUTES = 30
FUTURE_TOLERANCE_MINUTES = 2
KNOWN_COMPARISON_KINDS = {
    "prior_regular_close",
    "prior_futures_settlement_or_provider_previous_close",
    "prior_24h_reference",
}
ASSETS = {
    "NQ=F": "index_future",
    "ES=F": "index_future",
    "YM=F": "index_future",
    "RTY=F": "index_future",
    "QQQ": "etf_premarket",
    "SPY": "etf_premarket",
    "IWM": "etf_premarket",
    "SMH": "etf_premarket",
    "SOXX": "etf_premarket",
    "BTC-USD": "crypto",
    "CL=F": "commodity_future",
    "GC=F": "commodity_future",
    "DX-Y.NYB": "currency_index",
    "ZN=F": "rates_future",
    "^VIX": "volatility",
}
CORE_SYMBOLS = {"NQ=F", "ES=F", "QQQ", "SPY", "^VIX"}


def _as_et(value: str | datetime) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(ET)


def classify_freshness(as_of_et: str, now_et: datetime) -> str:
    age = (_as_et(now_et) - _as_et(as_of_et)).total_seconds() / 60
    if age <= FRESH_MINUTES:
        return "fresh"
    if age <= AGING_MINUTES:
        return "aging"
    return "stale"


def normalize_record(
    *,
    symbol: str,
    asset_class: str,
    last: float,
    comparison_value: float | None,
    comparison_kind: str,
    as_of_et: str,
    source: str,
    now_et: datetime,
    reported_volume: int | None = None,
) -> dict:
    now = _as_et(now_et)
    observed = _as_et(as_of_et)
    freshness = classify_freshness(observed.isoformat(), now)
    issues: list[str] = []
    if observed - now > timedelta(minutes=FUTURE_TOLERANCE_MINUTES):
        issues.append("timestamp_in_future")
    if comparison_kind not in KNOWN_COMPARISON_KINDS:
        issues.append("comparison_semantics_unknown")
    if asset_class in {"etf_premarket", "focus_equity_premarket"} and reported_volume == 0:
        issues.append("zero_reported_volume")
    change_pct = None
    if comparison_value not in (None, 0):
        change_pct = round((float(last) / float(comparison_value) - 1) * 100, 2)
    if freshness == "stale":
        quality = "stale_unverified"
    elif issues:
        quality = "degraded"
    else:
        quality = "usable_observation"
    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "last": round(float(last), 4),
        "comparison_value": round(float(comparison_value), 4) if comparison_value is not None else None,
        "comparison_kind": comparison_kind,
        "change_pct": change_pct,
        "as_of_et": observed.isoformat(),
        "source": source,
        "freshness": freshness,
        "quality": quality,
        "reported_volume": reported_volume,
        "issues": issues,
    }


def compare_pair(name: str, left: dict | None, right: dict | None) -> dict:
    if not left or not right:
        return {"name": name, "status": "insufficient_quality", "difference_pct_points": None}
    if left.get("freshness") == "stale" or right.get("freshness") == "stale":
        return {"name": name, "status": "insufficient_quality", "difference_pct_points": None}
    if left.get("change_pct") is None or right.get("change_pct") is None:
        return {"name": name, "status": "insufficient_quality", "difference_pct_points": None}
    left_change = float(left["change_pct"])
    right_change = float(right["change_pct"])
    difference = round(abs(left_change - right_change), 2)
    opposite_material = left_change * right_change < 0 and min(abs(left_change), abs(right_change)) > 0.20
    status = "conflicted" if difference > 0.50 or opposite_material else "aligned"
    return {"name": name, "status": status, "difference_pct_points": difference}


def build_cross_asset_checks(records: dict[str, dict]) -> dict:
    checks = {
        "QQQ_NQ": compare_pair("QQQ_NQ", records.get("QQQ"), records.get("NQ=F")),
        "SPY_ES": compare_pair("SPY_ES", records.get("SPY"), records.get("ES=F")),
        "IWM_RTY": compare_pair("IWM_RTY", records.get("IWM"), records.get("RTY=F")),
    }
    vix = records.get("^VIX", {})
    futures = [records.get(symbol, {}).get("change_pct") for symbol in ("NQ=F", "ES=F")]
    usable_futures = [value for value in futures if value is not None]
    if vix.get("change_pct") is not None and vix["change_pct"] > 2 and usable_futures and max(map(abs, usable_futures)) < 0.5:
        macro_state = "volatility_up_with_equity_futures_flat"
    else:
        macro_state = "mixed_macro_tape"
    checks["macro_state"] = {"status": macro_state}
    return checks


def _last_valid_bar(frame):
    close = frame["Close"].dropna()
    if close.empty:
        raise RuntimeError("no valid intraday close")
    position = close.index[-1]
    timestamp = position.tz_localize(ET) if position.tzinfo is None else position.tz_convert(ET)
    volume = int(frame.loc[:position, "Volume"].fillna(0).sum()) if "Volume" in frame else None
    return float(close.iloc[-1]), timestamp.isoformat(), volume


def _prior_regular_close(ticker, now_et: datetime) -> float:
    daily = ticker.history(period="5d", interval="1d", auto_adjust=False)
    if daily.empty:
        raise RuntimeError("daily history missing")
    candidates = daily
    try:
        dates = daily.index.tz_convert(ET).date if daily.index.tz is not None else daily.index.date
        candidates = daily[dates < now_et.date()]
    except (AttributeError, TypeError):
        pass
    if candidates.empty:
        candidates = daily
    return float(candidates["Close"].dropna().iloc[-1])


def _load_yfinance_record(symbol: str, asset_class: str, now_et: datetime) -> dict:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    intraday = ticker.history(period="2d" if asset_class == "crypto" else "1d", interval="1m", prepost=True, auto_adjust=False)
    if intraday.empty:
        raise RuntimeError("intraday history missing")
    last, timestamp, volume = _last_valid_bar(intraday)
    if asset_class == "crypto":
        close = intraday["Close"].dropna()
        target = _as_et(timestamp) - timedelta(hours=24)
        index = close.index.tz_localize(ET) if close.index.tz is None else close.index.tz_convert(ET)
        nearest_position = min(range(len(index)), key=lambda i: abs((index[i] - target).total_seconds()))
        comparison = float(close.iloc[nearest_position])
        comparison_kind = "prior_24h_reference"
        source = "yfinance_1m_24h"
    elif asset_class in {"etf_premarket", "focus_equity_premarket", "volatility"}:
        comparison = _prior_regular_close(ticker, now_et)
        comparison_kind = "prior_regular_close"
        source = "yfinance_1m_prepost"
    else:
        fast_info = ticker.fast_info
        comparison = float(fast_info["previous_close"])
        comparison_kind = "prior_futures_settlement_or_provider_previous_close"
        source = "yfinance_1m_futures"
    return {
        "last": last,
        "comparison_value": comparison,
        "comparison_kind": comparison_kind,
        "as_of_et": timestamp,
        "source": source,
        "reported_volume": volume,
    }


def build_premarket_tape(
    *,
    trading_date: str,
    session_id: str,
    now_et: datetime,
    output_path: Path,
    focus_symbols: list[str] | None = None,
    record_loader=None,
) -> dict:
    now = _as_et(now_et)
    if now.date().isoformat() != trading_date:
        raise ValueError("now_et date must match trading_date")
    loader = record_loader or _load_yfinance_record
    asset_map = dict(ASSETS)
    for symbol in focus_symbols or []:
        if symbol and symbol not in asset_map:
            asset_map[symbol] = "focus_equity_premarket"
    records: dict[str, dict] = {}
    missing_symbols: list[str] = []
    warnings: list[str] = []
    for symbol, asset_class in asset_map.items():
        try:
            raw = loader(symbol, asset_class, now)
            records[symbol] = normalize_record(
                symbol=symbol,
                asset_class=asset_class,
                now_et=now,
                **raw,
            )
        except Exception as exc:
            missing_symbols.append(symbol)
            warnings.append(f"{symbol}:{type(exc).__name__}:{exc}")
    if CORE_SYMBOLS.isdisjoint(records):
        raise RuntimeError("all core premarket symbols missing")
    payload = {
        "schema_version": "1.0",
        "session_id": session_id,
        "trading_date": trading_date,
        "generated_at_et": now.isoformat(),
        "evidence_level": "observation_only",
        "permission": "no_trading_permission",
        "status": "partial" if missing_symbols else "ready",
        "records": records,
        "cross_asset_checks": build_cross_asset_checks(records),
        "missing_symbols": missing_symbols,
        "warnings": warnings,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output_path)
    return payload


def _focus_symbols(universe_path: str | None) -> list[str]:
    if not universe_path:
        return []
    payload = json.loads(Path(universe_path).read_text(encoding="utf-8-sig"))
    symbols = payload.get("primary_focus", []) + payload.get("cognition_watchlist", [])
    return list(dict.fromkeys(str(symbol) for symbol in symbols if symbol))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build observation-only premarket tape")
    parser.add_argument("--date", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--universe")
    args = parser.parse_args(argv)
    build_premarket_tape(
        trading_date=args.date,
        session_id=args.session_id,
        now_et=datetime.fromisoformat(args.as_of),
        output_path=Path(args.out),
        focus_symbols=_focus_symbols(args.universe),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
