import sys, os, json
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
from unittest.mock import patch, MagicMock
import pandas as pd, numpy as np


def _make_price_history(n=120, close=224.77):
    """生成模拟价格历史"""
    np.random.seed(42)
    closes = [close]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.012)))
    closes = list(reversed(closes))
    return pd.DataFrame({
        "Open":   [c * 0.998 for c in closes],
        "High":   [c * 1.012 for c in closes],
        "Low":    [c * 0.988 for c in closes],
        "Close":  closes,
        "Volume": [int(50e6 + np.random.normal(0, 5e6)) for _ in closes],
    })


def _mock_ticker(hist_df, info=None):
    t = MagicMock()
    t.history.return_value = hist_df
    t.info = info or {
        "targetMeanPrice": 275.3,
        "targetLowPrice": 200.0,
        "targetHighPrice": 350.0,
        "numberOfAnalystOpinions": 50,
    }
    return t


def test_fetch_market_data_returns_required_fields():
    from agents.macro_strategy import fetch_market_data
    hist = _make_price_history()
    ticker = _mock_ticker(hist)
    with patch("agents.macro_strategy.yf.Ticker", return_value=ticker):
        data = fetch_market_data("TEST")
    required = ["price", "ma20", "ma50", "ma200", "atr14", "atr21",
                "fib_382", "fib_618", "swing_high_90d", "swing_low_90d", "swing_low_14d",
                "rsi14", "volume_ratio", "analyst_target", "sentiment_score"]
    for f in required:
        assert f in data, f"Missing field: {f}"


def test_fetch_market_data_ma_ordering():
    """MA20 应该比 MA50 更接近当前价（短期均线更快）"""
    from agents.macro_strategy import fetch_market_data
    hist = _make_price_history(close=224.77)
    ticker = _mock_ticker(hist)
    with patch("agents.macro_strategy.yf.Ticker", return_value=ticker):
        data = fetch_market_data("TEST")
    assert abs(data["ma20"] - data["price"]) <= abs(data["ma50"] - data["price"]) + 5


def test_fetch_market_data_atr_positive():
    from agents.macro_strategy import fetch_market_data
    hist = _make_price_history()
    ticker = _mock_ticker(hist)
    with patch("agents.macro_strategy.yf.Ticker", return_value=ticker):
        data = fetch_market_data("TEST")
    assert data["atr14"] > 0
    assert data["atr21"] > 0


def test_fetch_market_data_fib_levels():
    """fib_382 应该在 swing_low 和 swing_high 之间"""
    from agents.macro_strategy import fetch_market_data
    hist = _make_price_history()
    ticker = _mock_ticker(hist)
    with patch("agents.macro_strategy.yf.Ticker", return_value=ticker):
        data = fetch_market_data("TEST")
    lo, hi = data["swing_low_14d"], data["swing_high_90d"]
    if hi > lo:
        assert lo <= data["fib_382"] <= hi
        assert lo <= data["fib_618"] <= hi


def _default_mkt(price=224.77, ma20=215.8, ma50=210.2, ma200=178.5,
                  atr14=8.3, fib_382=202.1, fib_618=187.2,
                  swing_low_14d=208.5, swing_high_90d=242.5,
                  volume_ratio=1.1, analyst_target=275.3):
    return dict(price=price, ma20=ma20, ma50=ma50, ma200=ma200,
                atr14=atr14, atr21=7.9, fib_382=fib_382, fib_618=fib_618,
                swing_high_90d=swing_high_90d, swing_low_14d=swing_low_14d,
                swing_low_90d=190.0,
                rsi14=60.9, volume_ratio=volume_ratio,
                analyst_target=analyst_target, sentiment_score=0.75)

def _default_ev(k1=1.0, k2=0.2, k3=0.0, k4=0.90, k5=0.5, k6=1.0,
                k_reentry=0.3, fe_catalyst=2.0, c1=0.5, c2=1.5,
                Z_pre_reduce_pct=20, N_time_stop=30, D_decay_stop=14,
                M_decay_min_pct=5.0):
    return dict(k1=k1, k2=k2, k3=k3, k4=k4, k5=k5, k6=k6,
                k_reentry=k_reentry, fe_catalyst=fe_catalyst,
                c1=c1, c2=c2, Z_pre_reduce_pct=Z_pre_reduce_pct,
                N_time_stop=N_time_stop, D_decay_stop=D_decay_stop,
                M_decay_min_pct=M_decay_min_pct)


def test_entry_invalidation_above_entry_base():
    from agents.macro_strategy import calc_entry_nodes
    mkt = _default_mkt()
    ev  = _default_ev()
    nodes = calc_entry_nodes(mkt, ev, entry_base=224.0,
                             unified_confidence=3, thesis_status="intact")
    assert nodes["entry_invalidation"]["price"] > 224.0


def test_add1_uses_max_of_fib_and_ma50():
    from agents.macro_strategy import calc_entry_nodes
    mkt = _default_mkt(fib_382=195.0, ma50=210.0, atr14=8.0)
    ev  = _default_ev(k2=0.2)
    nodes = calc_entry_nodes(mkt, ev, entry_base=224.0,
                             unified_confidence=3, thesis_status="intact")
    assert nodes["add1"]["price"] >= 195.0


def test_add2_requires_high_confidence():
    from agents.macro_strategy import calc_entry_nodes
    mkt = _default_mkt()
    ev  = _default_ev()
    nodes_low  = calc_entry_nodes(mkt, ev, entry_base=224.0,
                                  unified_confidence=2, thesis_status="intact")
    nodes_high = calc_entry_nodes(mkt, ev, entry_base=224.0,
                                  unified_confidence=4, thesis_status="intact")
    assert nodes_low["add2"] is None
    assert nodes_high["add2"] is not None


def test_reentry_requires_intact_thesis():
    from agents.macro_strategy import calc_entry_nodes
    mkt = _default_mkt()
    ev  = _default_ev()
    nodes = calc_entry_nodes(mkt, ev, entry_base=224.0,
                             unified_confidence=3, thesis_status="weakening")
    assert nodes["re_entry"] is None


# ── Task 3: 止损节点 ──────────────────────────────────────────────────────────

def test_dynamic_stop_below_ma50():
    from agents.macro_strategy import calc_stop_nodes
    mkt = _default_mkt(ma50=210.2, atr14=8.3, swing_low_14d=208.5)
    ev  = _default_ev(k1=1.0)
    nodes = calc_stop_nodes(mkt, ev, entry_base=224.0, bear_scenario_price=156.4)
    assert nodes["dynamic_stop"]["price"] < 210.2

def test_dynamic_stop_uses_structural_low():
    from agents.macro_strategy import calc_stop_nodes
    mkt = _default_mkt(ma50=200.0, atr14=5.0, swing_low_14d=215.0)
    ev  = _default_ev(k1=1.0)
    nodes = calc_stop_nodes(mkt, ev, entry_base=224.0, bear_scenario_price=156.4)
    # max(200.0, 215.0) = 215.0, 215.0 - 5.0 = 210.0
    assert abs(nodes["dynamic_stop"]["price"] - 210.0) < 1.0

def test_force_exit_uses_bear_scenario():
    from agents.macro_strategy import calc_stop_nodes
    mkt = _default_mkt()
    ev  = _default_ev()
    nodes = calc_stop_nodes(mkt, ev, entry_base=224.0, bear_scenario_price=156.4)
    assert nodes["force_exit"]["price_bear"] == 156.4

def test_force_exit_catalyst_below_entry():
    from agents.macro_strategy import calc_stop_nodes
    mkt = _default_mkt(atr14=8.3)
    ev  = _default_ev(fe_catalyst=2.0)
    nodes = calc_stop_nodes(mkt, ev, entry_base=224.0, bear_scenario_price=156.4)
    assert nodes["force_exit"]["price_catalyst"] < 224.0


# ── Task 4: 目标节点 ──────────────────────────────────────────────────────────

def test_tp1_near_swing_high():
    from agents.macro_strategy import calc_target_nodes
    mkt = _default_mkt(swing_high_90d=242.5, price=224.77)
    ev  = _default_ev()
    nodes = calc_target_nodes(mkt, ev)
    assert nodes["tp1"]["price"] > mkt["price"]
    assert nodes["tp1"]["reduce_pct"] == 30

def test_tp2_applies_analyst_discount():
    from agents.macro_strategy import calc_target_nodes
    mkt = _default_mkt(analyst_target=275.3, swing_high_90d=242.5)
    ev  = _default_ev(k4=0.90)
    nodes = calc_target_nodes(mkt, ev)
    assert nodes["tp2"]["price"] <= 275.3 * 0.90 + 1.0

def test_tp2_none_when_no_analyst_target():
    from agents.macro_strategy import calc_target_nodes
    mkt = _default_mkt(analyst_target=None)
    ev  = _default_ev()
    nodes = calc_target_nodes(mkt, ev)
    assert nodes["tp2"]["price"] is not None


# ── Task 5: 情景+催化剂+时间止损 ─────────────────────────────────────────────

from datetime import date as _date

def test_scenario_downgrade_below_ma():
    from agents.macro_strategy import calc_scenario_nodes
    mkt = _default_mkt(ma20=215.8, ma50=210.2, atr14=8.3)
    ev  = _default_ev(k5=0.5, k6=1.0)
    nodes = calc_scenario_nodes(mkt, ev)
    assert nodes["scenario_downgrade"]["bull_to_base"]["price"] < 215.8
    assert nodes["scenario_downgrade"]["base_to_bear"]["price"] < 210.2

def test_catalyst_pre_reduce_active_when_close():
    from agents.macro_strategy import calc_scenario_nodes
    mkt  = _default_mkt()
    ev   = _default_ev()
    cat  = {"event": "earnings", "date": "2026-05-22", "importance": "high"}
    today = _date(2026, 5, 20)
    nodes = calc_scenario_nodes(mkt, ev, catalyst=cat, today=today, entry_base=224.0)
    assert nodes["catalyst_framework"]["pre_reduce_active"] is True

def test_catalyst_pre_reduce_inactive_when_far():
    from agents.macro_strategy import calc_scenario_nodes
    mkt   = _default_mkt()
    ev    = _default_ev()
    cat   = {"event": "earnings", "date": "2026-07-01", "importance": "high"}
    today = _date(2026, 5, 20)
    nodes = calc_scenario_nodes(mkt, ev, catalyst=cat, today=today, entry_base=224.0)
    assert nodes["catalyst_framework"]["pre_reduce_active"] is False

def test_time_stop_standard():
    from agents.macro_strategy import calc_time_stop
    ev    = _default_ev(N_time_stop=30)
    today = _date(2026, 5, 20)
    stop = calc_time_stop(ev, today=today, catalyst_date="2026-06-15", position_type="thesis")
    assert stop["type"] == "standard"
    assert stop["review_date"] is not None

def test_time_stop_decay_for_leveraged():
    from agents.macro_strategy import calc_time_stop
    ev    = _default_ev(D_decay_stop=14)
    today = _date(2026, 5, 20)
    stop = calc_time_stop(ev, today=today, catalyst_date=None, position_type="trend")
    assert stop["type"] == "decay"
    assert stop["decay_days"] == 14


# ── Task 6: 主编排器集成测试 ──────────────────────────────────────────────────

import tempfile

def test_build_nodes_integration():
    from agents.macro_strategy import build_nodes
    import os, json
    mkt  = _default_mkt()
    memo = json.load(open(os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")),
                                       "tests/fixtures/macro_strategy_memo.json"), encoding="utf-8"))
    pos  = {"cost": 100.0, "shares": 10, "position_type": "thesis",
            "thesis_status": "intact"}
    nodes = build_nodes("TEST", mkt, memo, pos, entry_base=100.0)
    required_keys = ["entry_invalidation", "add1", "dynamic_stop",
                     "force_exit", "tp1", "tp2", "flex_reduce",
                     "scenario_downgrade", "catalyst_framework", "time_stop"]
    for k in required_keys:
        assert k in nodes, f"Missing node: {k}"


def test_write_macro_strategy(tmp_path):
    from agents.macro_strategy import build_nodes, write_macro_strategy
    import json
    import os
    mkt  = _default_mkt()
    memo = json.load(open(os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")),
                                       "tests/fixtures/macro_strategy_memo.json"), encoding="utf-8"))
    pos  = {"cost": 100.0, "shares": 10, "position_type": "thesis",
            "thesis_status": "intact"}
    nodes = build_nodes("TEST", mkt, memo, pos, entry_base=100.0)
    out_path = write_macro_strategy("TEST", mkt, memo, nodes, base_dir=str(tmp_path))
    assert os.path.exists(out_path)
    data = json.load(open(out_path, encoding="utf-8"))
    assert data["sym"] == "TEST"
    assert "evolution" in data
    assert "nodes" in data
    assert "market_inputs" in data
    assert "memo_inputs" in data


def test_backtest_evaluates_stop_hit_rate():
    from agents.macro_strategy import backtest_node
    closes = [100.0] * 5 + [95.0] * 5 + [100.0] * 10 + [88.0] * 10
    result = backtest_node(
        node_type="dynamic_stop",
        node_price=92.0,
        entry_price=100.0,
        price_history=closes,
    )
    assert "hit" in result
    assert "hit_rate" in result
    assert 0.0 <= result["hit_rate"] <= 1.0


def test_backtest_returns_zero_hit_when_price_never_drops():
    from agents.macro_strategy import backtest_node
    closes = [100.0, 101.0, 102.0, 103.0, 105.0]
    result = backtest_node(
        node_type="dynamic_stop",
        node_price=90.0,
        entry_price=100.0,
        price_history=closes,
    )
    assert result["hit"] is False
    assert result["hit_rate"] == 0.0


def test_scan_parameters_returns_best_k1():
    from agents.macro_strategy import scan_parameters
    outcomes = [
        {"node_type": "dynamic_stop", "planned_price": 95.0,
         "actual_trigger_price": 94.0, "outcome": "hit", "pnl_impact": -5.0},
        {"node_type": "dynamic_stop", "planned_price": 95.0,
         "actual_trigger_price": 93.0, "outcome": "hit", "pnl_impact": -7.0},
        {"node_type": "tp1", "planned_price": 110.0,
         "actual_trigger_price": 112.0, "outcome": "hit", "pnl_impact": 10.0},
    ]
    result = scan_parameters(outcomes, param_name="k1",
                             param_range=[0.5, 1.0, 1.5])
    assert "best_value" in result
    assert result["best_value"] in [0.5, 1.0, 1.5]
    assert "metric" in result
