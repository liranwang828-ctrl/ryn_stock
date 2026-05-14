import json, sys
sys.path.insert(0, '/home/lirawang/stock_team')
from agents.protocol import (
    make_finding, make_challenge, make_endorsement, make_data_challenge,
    EXIT_OK, EXIT_FAIL, EXIT_SKIP,
    BOARD_PATH, VERIFIED_PATH, STRATEGY_PATH, FINDINGS_DIR
)

def test_make_finding_has_required_fields():
    msg = make_finding("TechAgent", "AMD", "bullish", 75,
                       ["MACD金叉"], [{"field": "close", "verified": True, "source": "yfinance"}])
    assert msg["msg_type"] == "initial_finding"
    assert msg["from"] == "TechAgent"
    assert msg["signal"] in ("bullish", "bearish", "neutral")
    assert 0 <= msg["confidence"] <= 100
    assert msg["data_refs"]
    assert "timestamp" in msg
    assert msg["revision"] == 0

def test_make_challenge_has_target():
    msg = make_challenge("TechAgent", "SentimentAgent", "RSI超买与机构乐观分歧",
                         [{"field": "rsi14", "verified": True, "source": "yfinance"}])
    assert msg["msg_type"] == "challenge"
    assert msg["target"] == "SentimentAgent"

def test_exit_codes_distinct():
    assert EXIT_OK != EXIT_FAIL != EXIT_SKIP
