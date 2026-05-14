import sys, os
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from agents.strategy_council import parse_strategy, evaluate_strategy, format_review_output

def test_parse_strategy_detects_add_tranche():
    result = parse_strategy("我想把T2的加仓条件设为：价格回踩0.3-2.5% + 量缩<0.75x")
    assert result["strategy_type"] in ["加仓策略", "入场条件", "持仓管理"]
    assert len(result["core_conditions"]) > 0

def test_parse_strategy_detects_stop_loss():
    result = parse_strategy("止损设在ATR×1.5，加反拥挤噪声")
    assert result["strategy_type"] in ["止损原则", "风险管理"]

def test_evaluate_strategy_returns_structure():
    strategy = {
        "raw_text": "T2加仓条件：价格回踩0.5-2% + 量缩",
        "strategy_type": "加仓策略",
        "core_conditions": ["价格回踩0.5-2%", "量缩"],
        "parsed_at": "2026-05-14T00:00:00+00:00"
    }
    result = evaluate_strategy(strategy)
    assert "kept" in result
    assert "improved" in result
    assert "pending" in result
    assert "master_reviews" in result
    assert len(result["master_reviews"]) > 0

def test_format_review_output_has_sections():
    review = {
        "strategy": {"raw_text": "T2加仓", "strategy_type": "加仓策略"},
        "kept": ["量缩条件正确"],
        "improved": [{"suggestion": "上限改为1.5%", "by": "minervini", "concern": ""}],
        "pending": [],
        "master_reviews": {},
    }
    output = format_review_output(review, "T2加仓策略")
    assert "保留" in output
    assert "改进" in output
