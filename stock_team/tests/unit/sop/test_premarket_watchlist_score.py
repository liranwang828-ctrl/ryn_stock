# tests/test_premarket_watchlist_score.py
import sys, os

from unittest.mock import patch, MagicMock
import pandas as pd

def _make_history(closes, highs=None, lows=None, volumes=None):
    n = len(closes)
    return pd.DataFrame({
        "Close":  closes,
        "High":   highs   or [c * 1.02 for c in closes],
        "Low":    lows    or [c * 0.98 for c in closes],
        "Volume": volumes or [1_000_000] * n,
    })

def test_score_stock_returns_required_keys():
    """score_stock 返回 sym / score / breakdown / summary / macro_note"""
    from stock_team.core.premarket_watchlist_score import score_stock
    macro  = {"yield_curve": "正常", "dxy": 100, "cpi_latest": "2.5%", "macro_score": 6}
    regime = {"overnight_signal": "太空 RKLB+6%", "regime": "trending_up"}

    closes_sym = [100.0] * 20 + [103.0]  # 3% 涨幅（5日RS高于SPY）
    closes_spy = [400.0] * 20 + [400.8]  # 0.2% 涨幅

    with patch("yfinance.Ticker") as MockTicker:
        def side_effect(sym):
            m = MagicMock()
            if sym == "SPY":
                m.history.return_value = _make_history(closes_spy)
            else:
                m.history.return_value = _make_history(closes_sym)
            return m
        MockTicker.side_effect = side_effect

        result = score_stock("RKLB", macro, regime)

    assert "sym"        in result
    assert "score"      in result
    assert "breakdown"  in result
    assert "summary"    in result
    assert "macro_note" in result
    assert result["sym"] == "RKLB"
    assert 0 <= result["score"] <= 100


def test_score_stock_overnight_narrative_hit():
    """当 overnight_signal 包含标的名时，叙事维度得满分"""
    from stock_team.core.premarket_watchlist_score import score_stock
    macro  = {"yield_curve": "正常", "dxy": 100, "cpi_latest": "2.5%", "macro_score": 6}
    regime = {"overnight_signal": "太空 RKLB+6.1% ASTS+4.5%", "regime": "trending_up"}

    closes = [100.0] * 21

    with patch("yfinance.Ticker") as MockTicker:
        m = MagicMock()
        m.history.return_value = _make_history(closes)
        MockTicker.return_value = m

        result = score_stock("RKLB", macro, regime)

    assert result["breakdown"]["narrative"] == 15, "叙事命中应得15分"


def test_score_stock_macro_penalty():
    """多重宏观逆风时宏观维度得0分"""
    from stock_team.core.premarket_watchlist_score import score_stock
    macro  = {
        "yield_curve": "倒挂", "dxy": 106, "cpi_latest": "4.5%",
        "macro_score": 2,  # 衰退风险
    }
    regime = {"overnight_signal": "", "regime": "trending_down"}

    pos_cfg = {
        "macro_sensitivity": {
            "rate_up": "负", "dollar_strong": "负",
            "inflation": "负", "recession": "负",
        }
    }
    closes = [100.0] * 21

    with patch("yfinance.Ticker") as MockTicker:
        m = MagicMock()
        m.history.return_value = _make_history(closes)
        MockTicker.return_value = m

        result = score_stock("LITE", macro, regime, pos_cfg=pos_cfg)

    assert result["breakdown"]["macro"] == 0, "4重逆风应得0分"


def test_rank_watchlist_sorted_by_score():
    """rank_watchlist 返回按 score 降序，前 n_top 标记 recommended=True"""
    from stock_team.core.premarket_watchlist_score import rank_watchlist
    macro  = {"yield_curve": "正常", "dxy": 100, "cpi_latest": "2.5%", "macro_score": 6}
    regime = {"overnight_signal": "RKLB+6%", "regime": "trending_up"}

    with patch("stock_team.core.premarket_watchlist_score.score_stock") as mock_score:
        mock_score.side_effect = lambda sym, *a, **kw: {
            "sym": sym, "score": {"RKLB": 82, "LITE": 74, "MRVL": 61}.get(sym, 50),
            "breakdown": {}, "summary": "", "macro_note": "",
            "rs5": 0, "ma20_dev": None, "upside": None,
            "vol_ratio": None, "narrative_hit": False,
        }
        results = rank_watchlist(["RKLB", "LITE", "MRVL"], macro, regime, n_top=2, positions={})

    assert results[0]["sym"] == "RKLB"
    assert results[0]["recommended"] is True
    assert results[1]["sym"] == "LITE"
    assert results[1]["recommended"] is True
    assert results[2]["recommended"] is False


def test_interactive_select_default(monkeypatch):
    """直接回车确认时返回推荐列表"""
    from stock_team.core.premarket_watchlist_score import interactive_select
    monkeypatch.setattr("builtins.input", lambda _: "")  # 模拟回车

    ranked = [
        {"sym": "RKLB", "score": 82, "recommended": True,  "summary": "", "macro_note": ""},
        {"sym": "LITE", "score": 74, "recommended": True,  "summary": "", "macro_note": ""},
        {"sym": "MRVL", "score": 61, "recommended": False, "summary": "", "macro_note": ""},
    ]
    selected = interactive_select(ranked)
    assert [r["sym"] for r in selected] == ["RKLB", "LITE"]


def test_interactive_select_override(monkeypatch):
    """输入代码时返回覆盖选择"""
    from stock_team.core.premarket_watchlist_score import interactive_select
    monkeypatch.setattr("builtins.input", lambda _: "LITE MRVL")

    ranked = [
        {"sym": "RKLB", "score": 82, "recommended": True,  "summary": "", "macro_note": ""},
        {"sym": "LITE", "score": 74, "recommended": True,  "summary": "", "macro_note": ""},
        {"sym": "MRVL", "score": 61, "recommended": False, "summary": "", "macro_note": ""},
    ]
    selected = interactive_select(ranked)
    assert [r["sym"] for r in selected] == ["LITE", "MRVL"]
