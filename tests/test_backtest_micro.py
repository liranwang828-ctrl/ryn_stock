# tests/test_backtest_micro.py
import sys, os
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
import pandas as pd
import numpy as np


def _make_ohlcv(n=300, start=100.0):
    np.random.seed(42)
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.012)))
    closes = [max(1.0, c) for c in closes]
    return pd.DataFrame({
        "Open":  [c * 0.998 for c in closes],
        "High":  [c * 1.015 for c in closes],
        "Low":   [c * 0.985 for c in closes],
        "Close": closes,
        "Volume":[int(1e7) for _ in closes],
    })


def test_compute_structural_nodes_has_required_columns():
    from agents.backtest_micro import compute_structural_nodes
    df = _make_ohlcv(300)
    params = {"k1": 1.0, "k2": 0.2, "k4": 0.9, "k5": 0.5}
    result = compute_structural_nodes(df, params)
    required = ["add1", "dynamic_stop", "tp1", "scenario_b2b"]
    for col in required:
        assert col in result.columns, f"Missing: {col}"


def test_structural_nodes_stop_below_add1():
    from agents.backtest_micro import compute_structural_nodes
    df = _make_ohlcv(300)
    params = {"k1": 1.0, "k2": 0.2, "k4": 0.9, "k5": 0.5}
    result = compute_structural_nodes(df, params).dropna()
    assert (result["dynamic_stop"] < result["add1"]).all()


def test_simulate_structural_trades_returns_list():
    from agents.backtest_micro import compute_structural_nodes, simulate_structural_trades
    df = _make_ohlcv(300)
    nodes = compute_structural_nodes(df, {"k1": 1.0, "k2": 0.2, "k4": 0.9, "k5": 0.5})
    trades = simulate_structural_trades(df, nodes, slippage=0.001)
    assert isinstance(trades, list)
    assert all("return" in t and "outcome" in t for t in trades)


def _make_5min_df(n=500, start=200.0):
    np.random.seed(7)
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.003)))
    closes = [max(1.0, c) for c in closes]
    times = pd.date_range("2026-01-02 09:30", periods=n, freq="5min", tz="America/New_York")
    return pd.DataFrame({
        "Open":  [c * 0.999 for c in closes],
        "High":  [c * 1.005 for c in closes],
        "Low":   [c * 0.995 for c in closes],
        "Close": closes,
        "Volume":[int(1e5) for _ in closes],
    }, index=times)


def test_compute_intraday_signals_has_required():
    from agents.backtest_micro import compute_intraday_signals
    df = _make_5min_df()
    result = compute_intraday_signals(df)
    for col in ["rsi14_5m", "vwap_dev", "vol_ratio_5m"]:
        assert col in result.columns


def test_scan_intraday_params_returns_results():
    from agents.backtest_micro import compute_intraday_signals, scan_intraday_params
    df = _make_5min_df(600)
    signals = compute_intraday_signals(df)
    param_grid = {"rsi14_5m_oversold": [30, 35, 40],
                  "vwap_add_threshold": [-2.0, -1.5, -1.0]}
    results = scan_intraday_params(signals, param_grid,
                                   add1_price=195.0, stop_price=185.0, tp1_price=210.0)
    assert len(results) == 9
    assert all("metrics" in r for r in results)


def test_scan_structural_params_finds_best():
    from agents.backtest_micro import scan_structural_params
    df = _make_ohlcv(400)
    param_grid = {"k1": [0.75, 1.0, 1.25], "k4": [0.85, 0.90, 0.95]}
    results = scan_structural_params(df, param_grid)
    assert len(results) == 9
    assert all("metrics" in r for r in results)
