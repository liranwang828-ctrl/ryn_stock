import sys, os
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from agents.question_router import classify_question, get_primary_masters

def test_classify_single_stock_intraday():
    result = classify_question("MRVL 今天还能买吗", symbols=["MRVL"])
    assert result["type"] == "日内/短线交易"
    assert result["symbols"] == ["MRVL"]

def test_classify_comparison():
    result = classify_question("LITE 和 AAOI 哪个更值得买", symbols=["LITE","AAOI"])
    assert result["type"] == "比较分析"
    assert len(result["symbols"]) == 2

def test_classify_risk():
    result = classify_question("MRVL T2 该不该加仓", symbols=["MRVL"])
    assert result["type"] in ["持仓加仓(T2/T3)", "风险评估", "日内/短线交易"]

def test_get_primary_masters_intraday():
    masters = get_primary_masters("日内/短线交易")
    assert "minervini" in masters
    assert "livermore" in masters

def test_get_primary_masters_comparison():
    masters = get_primary_masters("比较分析")
    assert len(masters) >= 3

def test_classify_sector():
    result = classify_question("光板块今天值得关注吗")
    assert result["type"] in ["板块轮动", "催化剂分析", "日内/短线交易"]
