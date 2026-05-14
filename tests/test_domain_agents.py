import sys, os
sys.path.insert(0, os.path.expanduser("~/stock_team"))

from agents.protocol import make_finding

def test_make_finding_backward_compatible():
    """旧版调用不传新参数，仍然正常工作"""
    msg = make_finding(
        "TechAgent", "AAPL", "bullish", 75,
        ["MACD金叉"],
        [{"field": "macd", "verified": True, "source": "yfinance"}]
    )
    assert msg["msg_type"] == "initial_finding"
    assert msg["signal"] == "bullish"
    assert msg["confidence"] == 75
    # 新字段有默认值
    assert "analysis" in msg
    assert isinstance(msg["analysis"], list)
    assert "conclusion" in msg
    assert "judgment" in msg["conclusion"]
    assert "boundary" in msg["conclusion"]
    assert "anticipated_challenge" in msg["conclusion"]

def test_make_finding_with_new_fields():
    """新版调用传入 analysis 和 conclusion"""
    msg = make_finding(
        "TechAgent", "AAPL", "bullish", 75,
        ["MACD金叉"],
        [{"field": "macd", "verified": True, "source": "yfinance"}],
        analysis=["MACD金叉通常预示3-5天延续性"],
        conclusion={
            "judgment": "技术结构偏多",
            "boundary": "若MACD柱收窄则看多减弱",
            "anticipated_challenge": "Minervini会质疑量能是否确认"
        }
    )
    assert msg["analysis"] == ["MACD金叉通常预示3-5天延续性"]
    assert msg["conclusion"]["judgment"] == "技术结构偏多"
    assert msg["conclusion"]["boundary"] == "若MACD柱收窄则看多减弱"
    assert msg["conclusion"]["anticipated_challenge"] == "Minervini会质疑量能是否确认"

def test_make_finding_default_conclusion_has_all_keys():
    """默认 conclusion 包含所有必需的 key"""
    msg = make_finding("FundAgent", "MSFT", "neutral", 50, [], [])
    c = msg["conclusion"]
    assert "judgment" in c
    assert "boundary" in c
    assert "anticipated_challenge" in c
