import sys, os, json, datetime
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _make_agent_file(tmp_path, agent, sym, date, signal="bullish", analysis=None, key_points=None):
    path = tmp_path / "findings" / f"{agent}_{sym}_{date}.json"
    _write(str(path), {
        "from": agent, "symbol": sym, "signal": signal,
        "confidence": 70,
        "analysis": analysis or ["分析段落1", "分析段落2"],
        "key_points": key_points or ["关键点A", "关键点B"],
        "conclusion": {"judgment": "测试结论", "boundary": "测试边界"},
    })


def _make_debate_file(tmp_path, sym, date):
    path = tmp_path / "findings" / f"debate_{sym}_{date}.jsonl"
    os.makedirs(str(tmp_path / "findings"), exist_ok=True)
    msgs = [
        {"from": "TechAgent", "msg_type": "challenge", "content": "我质疑基本面论断", "symbol": sym},
        {"from": "FundAgent", "msg_type": "response", "content": "基本面数据支持论断", "symbol": sym},
    ]
    with open(str(path), "w", encoding="utf-8") as f:
        for m in msgs:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")


def _make_positions(tmp_path, sym):
    _write(str(tmp_path / "config" / "positions.json"), {
        "positions": {sym: {
            "cost": 184.0, "shares": 30, "date": "2026-05-12",
            "thesis": "NVIDIA GPU数据中心AI算力垄断",
            "thesis_status": "intact",
            "falsification_conditions": ["跌破$200且跑输SOX", "Blackwell出货延迟超3个月"],
            "t2_conditions": {"note": "NVDA>$240回踩买", "underlying_price_floor": 240.0},
            "target_pct": 25.0,
            "position_type": "thesis",
            "gtc_stop_placed": False,
            "t1_stop_snapshot": 215.0,
        }},
        "_excluded": [],
    })


def test_build_position_context(tmp_path):
    """position_context 包含论点/证伪/加减仓策略"""
    from agents.strategic_memo_writer import build_position_context
    _make_positions(tmp_path, "NVDA")
    ctx = build_position_context("NVDA", base_dir=str(tmp_path))
    assert ctx["thesis_full"] == "NVIDIA GPU数据中心AI算力垄断"
    assert len(ctx["falsification_conditions"]) == 2
    assert ctx["reduce_strategy"]["target_pct"] == 25.0
    assert ctx["position_snapshot"]["cost"] == 184.0


def test_load_agent_analysis(tmp_path):
    """从 per-sym agent 文件读取完整分析"""
    from agents.strategic_memo_writer import load_agent_analysis_per_sym
    date = "2026-05-20"
    _make_agent_file(tmp_path, "TechAgent", "NVDA", date,
                     analysis=["MACD金叉", "RSI健康"], key_points=["Stage 2"])
    result = load_agent_analysis_per_sym("NVDA", date, find_dir=str(tmp_path / "findings"))
    assert "tech" in result
    assert result["tech"]["analysis"] == ["MACD金叉", "RSI健康"]
    assert result["tech"]["key_points"] == ["Stage 2"]


def test_load_debate_highlights(tmp_path):
    """从 per-sym debate 文件提取辩论摘要"""
    from agents.strategic_memo_writer import load_debate_highlights
    date = "2026-05-20"
    _make_debate_file(tmp_path, "NVDA", date)
    result = load_debate_highlights("NVDA", date, find_dir=str(tmp_path / "findings"))
    assert result["rounds"] >= 1
    assert len(result["key_challenges"]) > 0


def test_build_scenarios(tmp_path):
    """三情景分析基于 target_pct 和 hard_stop 构建"""
    from agents.strategic_memo_writer import build_scenarios
    _make_positions(tmp_path, "NVDA")
    scenarios = build_scenarios("NVDA", cur_price=224.0, base_dir=str(tmp_path))
    assert "bull" in scenarios and "base" in scenarios and "bear" in scenarios
    assert scenarios["base"]["price_target"] > 224.0
    assert scenarios["bear"]["price_target"] < 224.0
