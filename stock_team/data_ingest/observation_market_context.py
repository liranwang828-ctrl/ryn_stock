"""Read-only yfinance market context for observation sessions."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


REQUIRED_MARKETS = ("QQQ", "SPY", "IWM", "VIXY")
ET = ZoneInfo("America/New_York")


def _prior_regular_close(ticker, observed_at: datetime) -> float:
    daily = ticker.history(period="5d", interval="1d", auto_adjust=False)
    if daily.empty:
        raise RuntimeError("daily history missing")
    candidates = daily
    try:
        dates = daily.index.tz_convert(ET).date if daily.index.tz is not None else daily.index.date
        candidates = daily[dates < observed_at.date()]
    except (AttributeError, TypeError):
        pass
    if candidates.empty:
        raise RuntimeError("prior regular close missing")
    return round(float(candidates["Close"].dropna().iloc[-1]), 4)


def _yfinance_history(symbol: str) -> dict:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    intraday = ticker.history(period="1d", interval="1m", prepost=True, auto_adjust=False)
    if intraday.empty:
        return {}
    close = intraday["Close"].dropna()
    if close.empty:
        return {}
    latest = float(close.iloc[-1])
    timestamp = close.index[-1]
    if getattr(timestamp, "tzinfo", None) is None:
        timestamp = timestamp.tz_localize(ET)
    else:
        timestamp = timestamp.tz_convert(ET)
    prev_close = _prior_regular_close(ticker, timestamp)
    return {
        "price": round(latest, 4),
        "prev_close": prev_close,
        "data_as_of": timestamp.isoformat(),
        "source": "yfinance_1m_prepost",
    }


def build_observation_context(
    *,
    trading_date: str,
    as_of_et: datetime,
    snapshot_path: Path,
    packet_path: Path,
    history_loader=None,
) -> list[str]:
    history_loader = history_loader or _yfinance_history
    as_of_et = as_of_et.astimezone(ET)
    if as_of_et.date().isoformat() != trading_date:
        raise ValueError("as_of_et date must match trading_date")

    markets = {}
    missing = []
    for symbol in REQUIRED_MARKETS:
        row = history_loader(symbol) or {}
        required = ("price", "prev_close", "source", "data_as_of")
        if any(row.get(field) in (None, "") for field in required):
            missing.append(symbol)
        else:
            markets[symbol] = {field: row[field] for field in required}
    if missing:
        raise RuntimeError("observation market data missing: " + ",".join(missing))

    payload = {
        "trading_date": trading_date,
        "date": trading_date,
        "as_of_et": as_of_et.isoformat(),
        "evidence_level": "observation_only",
        "permission": "no_trading_permission",
        "source_kind": "yfinance_observation_context",
        "markets": markets,
    }
    lines = [
        f"# Observation Market Context ({trading_date})",
        "",
        "- evidence_level: `observation_only`",
        "- permission: `no_trading_permission`",
        f"- as_of_et: `{as_of_et.isoformat()}`",
        "",
        "| Symbol | Latest Premarket Quote | Prior Regular Close | Data As Of | Source |",
        "|---|---:|---:|---|---|",
    ]
    for symbol in REQUIRED_MARKETS:
        row = markets[symbol]
        lines.append(
            f"| {symbol} | {row['price']} | {row['prev_close']} | {row['data_as_of']} | {row['source']} |"
        )
    lines.extend([
        "",
        "> This packet is factual observation context only. It is not a premarket quote, trading plan, or permission grant.",
        "",
    ])

    snapshot_path = Path(snapshot_path)
    packet_path = Path(packet_path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_tmp = snapshot_path.with_suffix(snapshot_path.suffix + ".tmp")
    packet_tmp = packet_path.with_suffix(packet_path.suffix + ".tmp")
    snapshot_tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    packet_tmp.write_text("\n".join(lines), encoding="utf-8")
    snapshot_tmp.replace(snapshot_path)
    packet_tmp.replace(packet_path)
    return [str(snapshot_path), str(packet_path)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build observation-only yfinance Stage 0 context")
    parser.add_argument("--date", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-out", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    build_observation_context(
        trading_date=args.date,
        as_of_et=datetime.fromisoformat(args.as_of),
        snapshot_path=Path(args.snapshot_out),
        packet_path=Path(args.out),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
