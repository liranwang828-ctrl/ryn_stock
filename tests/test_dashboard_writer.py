# tests/test_dashboard_writer.py
import sys, os, json
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_load_premarket_summaries_returns_dict(tmp_path):
    """load_premarket_summaries 返回 {sym: summary} 字典"""
    from agents.dashboard_writer import load_premarket_summaries
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    _write(str(findings / f"premarket_summary_{date}_NVDA.json"), {
        "date": date, "sym": "NVDA",
        "stock_snapshot": {"gap_pct": 1.5, "pred_scene": "B"},
        "entry": {"decision": "enter", "sizing": "×1.0"},
        "exit": None, "thesis": None,
        "market_context": {"env": "顺风", "vix_level": 18.5},
        "strategic_context": {"source": "premarket_inferred", "strategic_stance": "hold"},
        "post_open_adj": None,
    })
    result = load_premarket_summaries(date, symbols=["NVDA"], find_dir=str(findings))
    assert "NVDA" in result
    assert result["NVDA"]["entry"]["decision"] == "enter"


def test_load_intraday_latest_returns_dict(tmp_path):
    """load_intraday_latest 返回 {sym: latest_record} 字典"""
    from agents.dashboard_writer import load_intraday_latest
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    record = {"ts": "10:30:00", "meta": {"sym": "NVDA", "date": date,
              "session_min": 60, "llm_triggered": False, "llm_trigger": None,
              "cooldown_until": None, "post_open_calibrated": True},
              "price_now": {"price": 220.0, "chg_pct": 1.5, "gate_status": "通过",
                            "master_avg": 6.5, "master_consensus": "buy"},
              "plan_vs_now": {"thesis_signal": "intact", "entry_go_status": "go",
                              "dist_to_stop_pct": 5.2},
              "node_snapshot": {}, "action_now": None}
    with open(str(findings / f"intraday_snapshot_{date}_NVDA.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    result = load_intraday_latest(date, symbols=["NVDA"], find_dir=str(findings))
    assert "NVDA" in result
    assert result["NVDA"]["price_now"]["price"] == 220.0


def test_load_intraday_events_filters_llm(tmp_path):
    """load_intraday_events 只返回 llm_triggered=True 的条目"""
    from agents.dashboard_writer import load_intraday_events
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    r1 = {"ts": "09:30:00", "meta": {"sym": "NVDA", "date": date, "session_min": 0,
          "llm_triggered": False, "llm_trigger": None, "cooldown_until": None,
          "post_open_calibrated": False},
          "price_now": {}, "plan_vs_now": {}, "node_snapshot": {}, "action_now": None}
    r2 = {"ts": "10:00:00", "meta": {"sym": "NVDA", "date": date, "session_min": 30,
          "llm_triggered": True, "llm_trigger": "entry_go", "cooldown_until": None,
          "post_open_calibrated": True},
          "price_now": {"price": 218.0}, "plan_vs_now": {"entry_go_status": "go"},
          "node_snapshot": {}, "action_now": {"conclusion": "enter", "note": "entry_go 触发"}}

    with open(str(findings / f"intraday_snapshot_{date}_NVDA.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps(r1) + "\n")
        f.write(json.dumps(r2) + "\n")

    events = load_intraday_events(date, symbols=["NVDA"], find_dir=str(findings))
    assert len(events) == 1
    assert events[0]["meta"]["llm_trigger"] == "entry_go"


def test_build_dashboard_context_schema(tmp_path):
    """build_dashboard_context 返回必要的顶层 key"""
    from agents.dashboard_writer import build_dashboard_context
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()

    ctx = build_dashboard_context(date, symbols=["NVDA"],
                                  base_dir=str(tmp_path))
    required = {"date", "generated_at", "symbols", "premarket",
                "intraday", "events", "portfolio", "postmarket_day",
                "session_state", "daily_plan"}
    assert required.issubset(set(ctx.keys())), f"缺少: {required - set(ctx.keys())}"
