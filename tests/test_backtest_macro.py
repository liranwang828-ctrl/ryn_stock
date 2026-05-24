# tests/test_backtest_macro.py
import sys, os
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock


def _make_ohlcv(n=300, start=100.0, vol_scale=1.0):
    """生成模拟日线 OHLCV"""
    np.random.seed(42)
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.012 * vol_scale)))
    closes = [max(1.0, c) for c in closes]
    return pd.DataFrame({
        "Open":   [c * 0.998 for c in closes],
        "High":   [c * 1.015 for c in closes],
        "Low":    [c * 0.985 for c in closes],
        "Close":  closes,
        "Volume": [int(1e7 + np.random.normal(0, 1e6)) for _ in closes],
    })


def test_compute_macro_signals_has_required_columns():
    from agents.backtest_macro import compute_macro_signals
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start=450.0)
    vix_df = _make_ohlcv(300, start=18.0, vol_scale=0.3)
    result = compute_macro_signals(sym_df, spy_df, vix_df)
    required = ["ma20_dev", "ma200_up", "rs5", "vol_ratio",
                "dist_hi52w", "vix_level", "vix_ts"]
    for col in required:
        assert col in result.columns, f"Missing column: {col}"


def test_compute_macro_signals_ma200_up_boolean():
    from agents.backtest_macro import compute_macro_signals
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start=450.0)
    vix_df = _make_ohlcv(300, start=18.0, vol_scale=0.3)
    result = compute_macro_signals(sym_df, spy_df, vix_df)
    assert result["ma200_up"].dtype == bool


def test_compute_metrics_ev_positive_when_mostly_wins():
    from agents.backtest_macro import compute_metrics
    returns = [0.05] * 7 + [-0.02] * 3
    metrics = compute_metrics(returns, risk_free_rate=0.045)
    assert metrics["ev"] > 0
    assert metrics["win_rate"] == 0.7
    assert metrics["max_drawdown"] <= 0


def test_compute_metrics_returns_all_keys():
    from agents.backtest_macro import compute_metrics
    returns = [0.03, -0.01, 0.02, 0.04, -0.015]
    metrics = compute_metrics(returns, risk_free_rate=0.045)
    required = ["ev", "win_rate", "rr_ratio", "sortino", "max_drawdown",
                "max_single_loss", "n_trades", "alpha_vs_spy"]
    for k in required:
        assert k in metrics, f"Missing metric: {k}"


def _make_macro_df():
    n = 300
    np.random.seed(42)
    dates = pd.date_range("2021-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "ma20_dev":  np.random.normal(0.02, 0.03, n),
        "ma200_up":  np.random.choice([True, False], n),
        "rs5":       np.random.normal(0.5, 2.0, n),
        "vol_ratio": np.random.uniform(0.5, 1.5, n),
        "dist_hi52w": np.random.uniform(-0.5, 0.05, n),
        "vix_level": np.random.uniform(15, 30, n),
        "vix_ts":    np.random.uniform(0.85, 1.2, n),
        "fwd_10d":   np.random.normal(0.01, 0.04, n),
        "Close":     np.cumsum(np.random.normal(0, 1, n)) + 200,
    }, index=dates)


def test_apply_macro_filter_reduces_rows():
    from agents.backtest_macro import apply_macro_filter
    df = _make_macro_df()
    params = {"vix_panic_threshold": 25, "ma20_dev_veto_pct": 8.0, "ma200_filter": True}
    filtered = apply_macro_filter(df, params)
    assert len(filtered) < len(df)


def test_scan_macro_params_returns_results():
    from agents.backtest_macro import scan_macro_params
    df = _make_macro_df()
    param_grid = {
        "vix_panic_threshold": [22, 25, 28],
        "ma20_dev_veto_pct":   [6.0, 8.0, 10.0],
    }
    results = scan_macro_params(df, param_grid)
    assert len(results) == 9
    assert all("ev" in r["metrics"] for r in results)
    assert all("params" in r for r in results)
