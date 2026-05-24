# tests/test_backtest_engine.py
import sys, os
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


def _make_ohlcv(n=300, start_price=100.0, trend=0.0002):
    """生成模拟日线 OHLCV 数据"""
    np.random.seed(42)
    closes = [start_price]
    for i in range(n - 1):
        closes.append(closes[-1] * (1 + trend + np.random.normal(0, 0.015)))
    closes = [round(c, 2) for c in closes]
    return pd.DataFrame({
        "Open":   [c * 0.995 for c in closes],
        "High":   [c * 1.015 for c in closes],
        "Low":    [c * 0.985 for c in closes],
        "Close":  closes,
        "Volume": [1_000_000 + int(np.random.normal(0, 200_000)) for _ in closes],
    })


def test_compute_daily_signals_has_required_columns():
    """_compute_daily_signals 返回含 ma20_dev / rs5 / vol_ratio 的 DataFrame"""
    from agents.backtest_engine import _compute_daily_signals
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start_price=400.0)
    result = _compute_daily_signals(sym_df, spy_df)
    assert "ma20_dev"  in result.columns
    assert "rs5"       in result.columns
    assert "vol_ratio" in result.columns
    assert len(result) == len(sym_df)


def test_compute_daily_signals_ma20_dev_correct():
    """MA20乖离率计算正确：(close - MA20) / MA20"""
    from agents.backtest_engine import _compute_daily_signals
    df = pd.DataFrame({
        "Close":  [100.0] * 250,
        "High":   [101.0] * 250,
        "Low":    [99.0]  * 250,
        "Open":   [100.0] * 250,
        "Volume": [1_000_000] * 250,
    })
    spy_df = _make_ohlcv(250, start_price=400.0)
    result = _compute_daily_signals(df, spy_df)
    # 第20行之后 ma20_dev 应接近0（close=MA20=100）
    assert abs(result["ma20_dev"].iloc[30]) < 0.001


def test_forward_return_5d():
    """_add_forward_returns 添加 5日后涨跌幅列"""
    from agents.backtest_engine import _add_forward_returns
    df = pd.DataFrame({"Close": [100, 102, 104, 103, 105, 107, 106, 108, 110, 112]})
    result = _add_forward_returns(df, days=5)
    assert "fwd_5d" in result.columns
    # 第0行 5日后是第5行(107)：(107-100)/100 = 7%
    assert abs(result["fwd_5d"].iloc[0] - 0.07) < 0.001
    # 最后5行 fwd_5d 应为 NaN
    assert pd.isna(result["fwd_5d"].iloc[-1])


def test_scan_signal_returns_scan_result():
    """_scan_signal 对 ma20_dev 扫描，返回含 optimal / win_rate / n_samples 的 dict"""
    from agents.backtest_engine import _scan_signal
    # 构造：ma20_dev <= 0.03 时 5日后上涨；否则下跌
    ma20_devs = [0.02] * 50 + [0.08] * 50
    fwd_5d    = [0.02] * 50 + [-0.01] * 50
    df = pd.DataFrame({"ma20_dev": ma20_devs, "fwd_5d": fwd_5d})

    result = _scan_signal(
        df, signal_col="ma20_dev", thresholds=[0.01, 0.03, 0.05, 0.10],
        direction="below",
        fwd_col="fwd_5d",
    )
    assert "optimal"   in result
    assert "win_rate"  in result
    assert "scan"      in result
    # threshold=0.03 捕获前50行（全涨），win_rate=1.0，应为最优
    assert result["optimal"] == 0.03


def test_run_signal_scan_structure():
    """run_signal_scan 对单个标的返回含全部信号键的 dict"""
    from agents.backtest_engine import run_signal_scan
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start_price=400.0)

    with patch("agents.backtest_engine._fetch_ohlcv") as mock_ohlcv, \
         patch("agents.backtest_engine._fetch_spy") as mock_spy:
        mock_ohlcv.return_value = sym_df
        mock_spy.return_value   = spy_df
        result = run_signal_scan("MRVL", years=1)

    assert "ma20_dev_max"  in result
    assert "rs5_min"       in result
    assert "vol_ratio_max" in result
    for key in result:
        assert "optimal"  in result[key]
        assert "win_rate" in result[key]


def test_run_portfolio_scan_aggregates_symbols():
    """run_portfolio_scan 对多个标的聚合结果，返回统一最优阈值"""
    from agents.backtest_engine import run_portfolio_scan
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start_price=400.0)

    with patch("agents.backtest_engine._fetch_ohlcv") as mock_ohlcv, \
         patch("agents.backtest_engine._fetch_spy") as mock_spy:
        mock_ohlcv.return_value = sym_df
        mock_spy.return_value   = spy_df
        result = run_portfolio_scan(["MRVL", "RKLB"], years=1, write_output=False)

    assert "ma20_dev_max"     in result
    assert "rs5_min"          in result
    assert "symbols_scanned"  in result
    assert len(result["symbols_scanned"]) == 2


def test_simulate_decision_framework_returns_summary():
    """simulate_decision_framework 只使用 soft_vetoes 中的技术信号"""
    from agents.backtest_engine import simulate_decision_framework
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start_price=400.0)
    # 只传 soft_vetoes：hard_vetoes 不可历史重建
    thresholds = {
        "soft_vetoes": {"ma20_dev_max": 0.05, "rs5_min": 0.0, "max_headwinds": 2},
    }
    with patch("agents.backtest_engine._fetch_ohlcv") as mock_ohlcv, \
         patch("agents.backtest_engine._fetch_spy") as mock_spy:
        mock_ohlcv.return_value = sym_df
        mock_spy.return_value   = spy_df
        result = simulate_decision_framework(["MRVL"], thresholds, years=1,
                                              write_output=False)

    assert "win_rate"     in result
    assert "n_entries"    in result
    assert "mean_ret_pct" in result
    assert "note"         in result
    assert "hard" not in result.get("thresholds_used", {})
    assert result["n_entries"] > 0
