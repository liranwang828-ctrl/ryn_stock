"""
Backtest framework — historical replay using paper_trader and compute_indicators.
Walks forward through historical data, generates signals, and simulates trades.
"""
import os, sys, json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from indicators.compute_indicators import compute_all_indicators
from indicators.data_fetcher import DataFetcher
from agents.paper_trader import (
    calc_stop, calc_targets, decide_mode, try_enter,
    try_add_tranche, check_exits, load_portfolio,
    _load_acct_cfg, ACCOUNTS,
)

WARMUP_BARS = 50


def run_backtest(symbols: List[str], period: str = "6mo",
                 interval: str = "1d") -> dict:
    """
    Walk-forward backtest for a list of symbols.

    Returns dict with per-account metrics: return, sharpe, max_dd, win_rate, profit_factor.
    """
    print(f"\n{'='*60}")
    print(f"  Backtest: {', '.join(symbols)}  |  {period}  |  {interval}")
    print(f"{'='*60}")

    fetcher = DataFetcher()
    data = {}
    for sym in symbols:
        try:
            df = fetcher.get_ohlcv(sym, period=period, interval=interval)
            if df is not None and not df.empty:
                data[sym] = df
                print(f"  {sym}: {len(df)} bars")
        except Exception as e:
            print(f"  {sym}: FETCH FAILED — {e}")

    if not data:
        print("[Backtest] No data available.")
        return {}

    # Align to common date range
    common_idx = sorted(set.intersection(*(set(df.index) for df in data.values())))
    if len(common_idx) < WARMUP_BARS + 10:
        print(f"[Backtest] Insufficient data: {len(common_idx)} bars.")
        return {}

    for sym in data:
        data[sym] = data[sym].loc[data[sym].index.isin(common_idx)]

    # Track positions per account (simple in-memory simulation)
    trades = {acct: [] for acct in ACCOUNTS}
    equity_curves = {acct: [100000] for acct in ACCOUNTS}

    for i in range(WARMUP_BARS, len(common_idx)):
        current_date = common_idx[i]

        for sym, df in data.items():
            window = df.iloc[max(0, i - 100):i + 1].copy()
            if len(window) < 20:
                continue

            try:
                ind = compute_all_indicators(window)
            except Exception:
                continue

            bar = df.iloc[i]
            cur = float(bar["close"])
            hi = float(bar.get("high", cur))
            lo = float(bar.get("low", cur))
            vwap = ind.get("VWAP", cur)
            atr = ind.get("ATR_14", cur * 0.02) or cur * 0.02
            rsi = ind.get("RSI_14", 50) or 50
            macd_hist = ind.get("MACD_hist", 0) or 0

            # Simple signal: bullish if MACD histogram positive and RSI > 50
            signal = "neutral"
            if macd_hist > 0 and rsi > 55:
                signal = "bullish"
            elif macd_hist < 0 and rsi < 45:
                signal = "bearish"
            confidence = min(90, 50 + abs(rsi - 50))

            persona_score = confidence / 10  # 0-10 scale
            rs = rsi / 10  # simplified RS

            for acct in ACCOUNTS:
                port = {"account": acct, "cash": equity_curves[acct][-1],
                        "initial_cash": 100000, "positions": {}}
                entry = try_enter(sym, cur, vwap, atr, rs, persona_score,
                                  {}, 0, {sym: cur}, catalyst_strength=1, acct=acct)
                if entry:
                    trades[acct].append({"date": current_date, "sym": sym,
                                         "action": "entry", "price": cur})

                # Check exits
                exit_msg = check_exits(sym, cur, hi, lo, acct=acct)

        # Track equity
        for acct in ACCOUNTS:
            port = load_portfolio(acct)
            eq = port["cash"]
            for sym, pos in port.get("positions", {}).items():
                idx = None
                for j, dt in enumerate(common_idx):
                    if dt >= current_date:
                        idx = max(0, j - 1) if dt > current_date else j
                        break
                if idx is not None and sym in data:
                    price = float(data[sym].iloc[idx]["close"])
                    eq += pos["shares"] * price
            equity_curves[acct].append(eq)

    # Compute metrics
    results = {}
    for acct in ACCOUNTS:
        curve = equity_curves[acct]
        returns = np.diff(curve) / curve[:-1]
        if len(returns) > 0:
            mean_ret = np.mean(returns)
            std_ret = np.std(returns) or 1e-9
            sharpe = mean_ret / std_ret * np.sqrt(252)
            peak = np.maximum.accumulate(curve)
            dd = (curve - peak) / peak
            max_dd = float(np.min(dd)) * 100

            acct_trades = trades[acct]
            wins = [t for t in acct_trades if t.get("pnl_pct", 0) > 0]
            win_rate = len(wins) / len(acct_trades) * 100 if acct_trades else 0

            results[acct] = {
                "total_return_pct": float((curve[-1] - curve[0]) / curve[0] * 100),
                "sharpe": float(sharpe),
                "max_drawdown_pct": float(max_dd),
                "win_rate_pct": float(win_rate),
                "trades": len(acct_trades),
                "final_equity": float(curve[-1]),
            }

    return results


def report(results: dict):
    """Print formatted backtest report."""
    print(f"\n{'='*60}")
    print("  BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"  {'Account':<12s} {'Return':>8s} {'Sharpe':>7s} {'MaxDD':>7s} "
          f"{'Win%':>6s} {'Trades':>7s}")
    for acct in ACCOUNTS:
        r = results.get(acct, {})
        if r:
            print(f"  {acct:<12s} {r['total_return_pct']:+7.2f}% "
                  f"{r['sharpe']:6.2f}  {r['max_drawdown_pct']:-6.2f}% "
                  f"{r['win_rate_pct']:5.1f}% {r['trades']:7d}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backtest runner")
    parser.add_argument("symbols", nargs="+")
    parser.add_argument("--period", default="3mo")
    parser.add_argument("--interval", default="1d")
    args = parser.parse_args()

    results = run_backtest(args.symbols, period=args.period, interval=args.interval)
    report(results)
