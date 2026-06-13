import sys, os

import pandas as pd
import numpy as np
from learning.features import extract_intraday_features, extract_swing_features

def make_fake_ohlcv(n=30):
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    prices = 100 + np.cumsum(np.random.randn(n))
    df = pd.DataFrame({
        "Open": prices * 0.99,
        "High": prices * 1.02,
        "Low":  prices * 0.98,
        "Close": prices,
        "Volume": np.random.randint(1000000, 10000000, n),
    }, index=dates)
    return df

def test_intraday_features_keys():
    h = make_fake_ohlcv()
    feat = extract_intraday_features(h, peer_chg=1.5)
    for key in ["gap_pct", "rsi14", "macd_hist", "vol_ratio", "peer_chg",
                "pct_from_52w_high", "amplitude"]:
        assert key in feat, f"Missing key: {key}"

def test_swing_features_keys():
    h = make_fake_ohlcv()
    feat = extract_swing_features(h, short_pct=12.0, catalyst_strength=2)
    for key in ["ma20_dist", "ma50_dist", "short_pct", "catalyst_strength",
                "rsi14", "trend_5d", "trend_10d"]:
        assert key in feat, f"Missing key: {key}"

def test_gap_pct_calculation():
    h = make_fake_ohlcv()
    h.iloc[-2, h.columns.get_loc("Close")] = 100.0
    h.iloc[-1, h.columns.get_loc("Open")] = 105.0
    feat = extract_intraday_features(h, peer_chg=0)
    assert abs(feat["gap_pct"] - 5.0) < 0.5
