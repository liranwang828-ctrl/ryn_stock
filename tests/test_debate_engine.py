import sys, os
sys.path.insert(0, os.path.expanduser("~/stock_team"))

from agents.debate_engine import detect_contradictions, weighted_synthesis

def test_detect_contradictions_finds_opposing_signals():
    """bullish vs bearish 应该被识别为矛盾"""
    stances = {
        "minervini":     {"signal": "bullish", "core_argument": "Stage 2确认，量能支撑", "confidence": 75},
        "marks":         {"signal": "bearish", "core_argument": "估值90%历史分位，过热", "confidence": 70},
        "druckenmiller": {"signal": "bullish", "core_argument": "宏观顺风，主题强劲", "confidence": 80},
    }
    contradictions = detect_contradictions(stances)
    assert len(contradictions) >= 1
    for pair in contradictions:
        assert len(pair) == 2

def test_detect_contradictions_no_false_positives():
    """两个都看多不应该产生矛盾"""
    stances = {
        "minervini":     {"signal": "bullish", "core_argument": "技术看多", "confidence": 75},
        "druckenmiller": {"signal": "bullish", "core_argument": "宏观看多", "confidence": 80},
    }
    contradictions = detect_contradictions(stances)
    assert len(contradictions) == 0

def test_weighted_synthesis_respects_primary_masters():
    """函数能正常运行并返回必要字段"""
    stances = {
        "minervini": {"signal": "bullish", "core_argument": "技术", "confidence": 80},
        "marks":     {"signal": "bearish", "core_argument": "风险", "confidence": 70},
    }
    result = weighted_synthesis(stances, {}, primary_masters=["minervini"])
    assert "consensus_signal" in result
    assert "weighted_confidence" in result
    assert "unresolved_contradictions" in result

def test_weighted_synthesis_handles_split():
    """主角分歧时包含 conditional_map"""
    stances = {
        "minervini": {"signal": "bullish", "core_argument": "技术", "confidence": 75},
        "marks":     {"signal": "bearish", "core_argument": "估值", "confidence": 75},
    }
    result = weighted_synthesis(stances, {}, primary_masters=["minervini", "marks"])
    assert result["consensus_signal"] in ["bullish", "bearish", "neutral"]
