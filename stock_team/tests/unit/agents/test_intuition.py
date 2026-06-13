import sys, os

import numpy as np

def test_score_returns_both_tracks_or_none():
    from agents.intuition_agent import score_symbol
    result = score_symbol("FAKE", {})
    assert result is None or ("intraday" in result and "swing" in result)

def test_find_similar_cases_empty():
    from agents.intuition_agent import find_similar_cases
    assert find_similar_cases({}, [], top_k=3) == []

def test_format_intuition_line_contains_pct():
    from agents.intuition_agent import format_intuition_line
    result = format_intuition_line(
        intra_score=0.68, swing_score=0.71,
        similar=[{"sym": "NBIS", "date": "2026-05-14", "ret": 12.0, "track": "intraday"}]
    )
    assert "68%" in result and "日内" in result
