# tests/test_dashboard_writer.py
import sys, os, json, shutil
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_load_premarket_summaries_returns_dict(tmp_path):
    """load_premarket_summaries 杩斿洖 {sym: summary} 瀛楀吀"""
    from agents.dashboard_writer import load_premarket_summaries
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    _write(str(findings / f"premarket_summary_{date}_NVDA.json"), {
        "date": date, "sym": "NVDA",
        "stock_snapshot": {"gap_pct": 1.5, "pred_scene": "B"},
        "entry": {"decision": "enter", "sizing": "脳1.0"},
        "exit": None, "thesis": None,
        "market_context": {"env": "椤洪", "vix_level": 18.5},
        "strategic_context": {"source": "premarket_inferred", "strategic_stance": "hold"},
        "post_open_adj": None,
    })
    result = load_premarket_summaries(date, symbols=["NVDA"], find_dir=str(findings))
    assert "NVDA" in result
    assert result["NVDA"]["entry"]["decision"] == "enter"


def test_load_intraday_latest_returns_dict(tmp_path):
    """load_intraday_latest 杩斿洖 {sym: latest_record} 瀛楀吀"""
    from agents.dashboard_writer import load_intraday_latest
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    record = {"ts": "10:30:00", "meta": {"sym": "NVDA", "date": date,
              "session_min": 60, "llm_triggered": False, "llm_trigger": None,
              "cooldown_until": None, "post_open_calibrated": True},
              "price_now": {"price": 220.0, "chg_pct": 1.5, "gate_status": "閫氳繃",
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
    """load_intraday_events returns only llm-triggered rows."""
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
          "node_snapshot": {}, "action_now": {"conclusion": "enter", "note": "entry_go 瑙﹀彂"}}

    with open(str(findings / f"intraday_snapshot_{date}_NVDA.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps(r1) + "\n")
        f.write(json.dumps(r2) + "\n")

    events = load_intraday_events(date, symbols=["NVDA"], find_dir=str(findings))
    assert len(events) == 1
    assert events[0]["meta"]["llm_trigger"] == "entry_go"


def test_build_dashboard_context_schema(tmp_path):
    """build_dashboard_context returns required top-level keys."""
    from agents.dashboard_writer import build_dashboard_context
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()

    ctx = build_dashboard_context(date, symbols=["NVDA"],
                                  base_dir=str(tmp_path))
    required = {"date", "generated_at", "symbols", "premarket",
                "intraday", "events", "portfolio", "postmarket_day",
                "session_state", "daily_plan"}
    assert required.issubset(set(ctx.keys())), f"缂哄皯: {required - set(ctx.keys())}"


def test_build_dashboard_context_includes_learning_state(tmp_path):
    """dashboard context should surface compact learning state from the cached index."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-24"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})
    _write(str(base / "learning" / "knowledge_index.json"), {
        "scope": "all_time",
        "source_coverage": {"observation": 1, "lesson": 1, "decision": 0, "outcome": 0, "knowledge_node": 0},
        "latest_lessons": [{
            "summary": "Keep requiring confirmation before committing.",
            "ts": "2026-05-24T18:05:00-04:00",
        }],
        "latest_observations": [{
            "summary": "NVDA held above the opening shelf.",
            "ts": "2026-05-24T09:35:00-04:00",
        }],
        "open_questions": ["Does confirmation still help in high-VIX sessions?"],
    })

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    learning = ctx["learning"]

    assert learning["scope"] == "all_time"
    assert learning["source_coverage"]["lesson"] == 1
    assert learning["source_coverage"]["observation"] == 1
    assert learning["latest_lessons"][0]["summary"] == "Keep requiring confirmation before committing."
    assert learning["latest_observations"][0]["summary"] == "NVDA held above the opening shelf."
    assert learning["open_questions"][0] == "Does confirmation still help in high-VIX sessions?"


def test_load_portfolio_snapshot_is_read_only_when_missing(tmp_path):
    """load_portfolio_snapshot should not create runtime artifacts on dashboard render."""
    from unittest.mock import patch
    from agents.dashboard_writer import load_portfolio_snapshot

    findings = tmp_path / "findings"
    findings.mkdir()

    with patch("agents.portfolio_snapshot.build_portfolio_snapshot") as build, \
         patch("agents.portfolio_snapshot.write_portfolio_snapshot") as write:
        build.return_value = {"totals": {"total_value": 1000.0}}

        result = load_portfolio_snapshot("2026-05-24", find_dir=str(findings))

    assert result == {}
    build.assert_not_called()
    write.assert_not_called()


def test_load_intraday_latest_fills_missing_defaults(tmp_path):
    """load_intraday_latest should backfill missing intraday defaults."""
    from agents.dashboard_writer import load_intraday_latest
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    record = {
        "ts": "10:30:00",
        "meta": {"sym": "NVDA", "date": date, "session_min": 60,
                 "llm_triggered": False, "llm_trigger": None,
                 "cooldown_until": None, "post_open_calibrated": True},
        "price_now": {"price": 220.0, "gate_status": "閫氳繃"},
        "plan_vs_now": {},
        "node_snapshot": {},
        "action_now": None,
    }
    with open(str(findings / f"intraday_snapshot_{date}_NVDA.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    result = load_intraday_latest(date, symbols=["NVDA"], find_dir=str(findings))
    assert result["NVDA"]["price_now"]["master_avg"] == 5.0
    assert result["NVDA"]["price_now"]["master_consensus"] == "neutral"
    assert result["NVDA"]["plan_vs_now"]["entry_go_status"] == "pending"


def test_build_dashboard_context_normalizes_summary_fields(tmp_path):
    """dashboard context should normalize missing summary fields."""
    from agents.dashboard_writer import build_dashboard_context
    date = "2026-05-20"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {"NVDA": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "daily_plan_2026-05-20.json"), {
        "date": date,
        "symbols_today": ["NVDA"],
        "per_symbol": {
            "NVDA": {
                "premarket_summary_path": f"findings/premarket_summary_{date}_NVDA.json",
                "action_now": "watch",
                "key_levels": {"entry_base": 100.0, "hard_stop": 95.0, "flex_add": None, "flex_reduce": None, "target": 110.0},
                "entry_go_status": None,
                "pending_suggestions": 0,
                "memo_valid": True,
            }
        },
        "stocks": {}
    })
    _write(str(base / "findings" / f"premarket_summary_{date}_NVDA.json"), {
        "date": date,
        "sym": "NVDA",
        "entry": {"decision": "enter", "entry_base": 100.0},
        "exit": {"decision": None, "hard_stop": 95.0, "flex_reduce_level": 108.0},
        "thesis": {"status": "intact", "today_falsification": []},
        "strategic_context": {"source": "premarket_inferred", "strategic_stance": "hold", "thesis_lifecycle": "mid"},
        "post_open_adj": None,
        "market_context": {"env": "normal"},
    })
    _write(str(base / "macro_strategy_NVDA.json"), {
        "sym": "NVDA",
        "nodes": {
            "flex_reduce": {"note": "test only"},
            "scenario_downgrade": {
                "bull_to_base": {"price": 98.0, "basis": "test"},
                "base_to_bear": {"price": 90.0, "basis": "test"}
            }
        }
    })
    _write(str(base / "reports" / f"{date}_NVDA.html"), "<html></html>")
    _write(str(base / "findings" / f"intraday_snapshot_{date}_NVDA.jsonl"), {
        "ts": "10:30:00",
        "meta": {"sym": "NVDA", "date": date, "session_min": 60, "llm_triggered": False,
                 "llm_trigger": None, "cooldown_until": None, "post_open_calibrated": True},
        "price_now": {"price": 220.0, "gate_status": "閫氳繃"},
        "plan_vs_now": {},
        "node_snapshot": {},
        "action_now": None
    })

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    assert ctx["daily_plan"]["per_symbol"]["NVDA"]["entry_go_status"] == "pending"
    assert ctx["intraday"]["NVDA"]["price_now"]["master_consensus"] == "neutral"
    assert ctx["intraday"]["NVDA"]["plan_vs_now"]["entry_go_status"] == "pending"
    assert ctx["macro_nodes"]["NVDA"]["flex_reduce"]["price"] == 108.0
    assert ctx["macro_nodes"]["NVDA"]["scenario_downgrade"]["price"] == 98.0


def test_build_dashboard_context_backfills_sector_relative_strength(tmp_path):
    """dashboard context should copy cached sector-relative fields without live fetches."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-20"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()

    _write(str(base / "config" / "positions.json"), {"positions": {"NVDA": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {
        "default_symbols": ["NVDA"],
        "sector_map": {"NVDA": {"ref": "SOXX", "ref_name": "鍗婂浣揝OXX"}},
    })
    _write(str(base / "findings" / f"premarket_summary_{date}_NVDA.json"), {
        "date": date,
        "sym": "NVDA",
        "stock_snapshot": {
            "gap_pct": 4.0,
            "sector_ref": "SOXX",
            "sector_gap_pct": 3.0,
            "rs_vs_sector": 1.0,
        },
        "entry": {"decision": "enter", "entry_base": 100.0},
        "exit": {"decision": None, "hard_stop": 95.0, "flex_reduce_level": 108.0},
        "thesis": {"status": "intact", "today_falsification": []},
        "strategic_context": {"source": "premarket_inferred", "strategic_stance": "hold", "thesis_lifecycle": "mid"},
        "post_open_adj": None,
        "market_context": {"env": "normal"},
    })
    _write(str(base / "findings" / f"intraday_snapshot_{date}_NVDA.jsonl"), {
        "ts": "10:30:00",
        "meta": {"sym": "NVDA", "date": date, "session_min": 60, "llm_triggered": False,
                 "llm_trigger": None, "cooldown_until": None, "post_open_calibrated": True},
        "price_now": {"price": 220.0, "chg_pct": 2.0, "gate_status": "閫氳繃", "rs_vs_sector": 0.0},
        "plan_vs_now": {},
        "node_snapshot": {},
        "action_now": None
    })
    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))

    assert ctx["premarket"]["NVDA"]["stock_snapshot"]["sector_ref"] == "SOXX"
    assert ctx["premarket"]["NVDA"]["stock_snapshot"]["sector_gap_pct"] == 3.0
    assert ctx["premarket"]["NVDA"]["stock_snapshot"]["rs_vs_sector"] == 1.0
    assert ctx["intraday"]["NVDA"]["price_now"]["sector_ref"] == "SOXX"
    assert ctx["intraday"]["NVDA"]["price_now"]["rs_vs_sector"] == 0.0


def test_build_dashboard_context_backfills_missing_symbol_from_cache(tmp_path):
    """dashboard cache should backfill a missing symbol without requiring whole-collection fallback."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-20"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()

    _write(str(base / "config" / "positions.json"), {"positions": {"AMD": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["AMD"]})
    _write(str(base / "findings" / f"premarket_summary_{date}_AMD.json"), {
        "date": date,
        "sym": "AMD",
        "stock_snapshot": {"gap_pct": 2.0},
        "entry": {"decision": "watch", "entry_base": 100.0},
        "exit": {"hard_stop": 95.0},
        "thesis": {"status": "intact"},
        "strategic_context": {"source": "premarket_inferred", "strategic_stance": "hold"},
        "market_context": {"env": "normal"},
    })
    _write(str(base / "findings" / f"intraday_snapshot_{date}_AMD.jsonl"), {
        "ts": "10:00:00",
        "meta": {"sym": "AMD", "date": date, "session_min": 30, "llm_triggered": False,
                 "llm_trigger": None, "cooldown_until": None, "post_open_calibrated": True},
        "price_now": {"price": 150.0, "chg_pct": 1.2, "gate_status": "閫氳繃"},
        "plan_vs_now": {"entry_go_status": "go"},
        "node_snapshot": {},
        "action_now": None
    })
    _write(str(base / "learning" / "dashboard_cache.json"), {
        "date": date,
        "generated_at": "2026-05-20T10:00:00Z",
        "premarket": {
            "NVDA": {
                "stock_snapshot": {"sector_ref": "SOXX", "sector_gap_pct": 3.0, "rs_vs_sector": 1.0}
            }
        },
        "intraday": {
            "NVDA": {
                "price_now": {"sector_ref": "SOXX", "sector_gap_pct": 3.0, "rs_vs_sector": 1.0}
            }
        },
        "daily_plan": {
            "per_symbol": {
                "NVDA": {"entry_go_status": "pending", "key_levels": {"entry_base": 101.0}}
            }
        },
        "learning": {
            "scope": "all_time",
            "source_coverage": {"observation": 0, "lesson": 0, "decision": 0, "outcome": 0, "knowledge_node": 0},
            "latest_lessons": [],
            "latest_observations": [],
            "open_questions": []
        }
    })

    ctx = build_dashboard_context(date, symbols=["NVDA", "AMD"], base_dir=str(base))

    assert ctx["premarket"]["NVDA"]["stock_snapshot"]["sector_ref"] == "SOXX"
    assert ctx["intraday"]["NVDA"]["price_now"]["sector_ref"] == "SOXX"
    assert ctx["daily_plan"]["per_symbol"]["NVDA"]["entry_go_status"] == "pending"
    assert "AMD" in ctx["premarket"]
    assert "AMD" in ctx["intraday"]
    assert ctx["daily_plan"]["per_symbol"]["AMD"]["entry_go_status"] == "go"


def test_build_dashboard_context_preserves_zero_sector_values(tmp_path):
    """zero sector values should be preserved and not overwritten as missing."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-20"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()

    _write(str(base / "config" / "positions.json"), {"positions": {"NVDA": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "findings" / f"premarket_summary_{date}_NVDA.json"), {
        "date": date,
        "sym": "NVDA",
        "stock_snapshot": {"sector_ref": "SOXX", "sector_gap_pct": 0.0, "rs_vs_sector": 0.0},
        "entry": {"decision": "enter", "entry_base": 100.0},
        "exit": {"decision": None, "hard_stop": 95.0},
        "thesis": {"status": "intact"},
        "strategic_context": {"source": "premarket_inferred", "strategic_stance": "hold"},
        "market_context": {"env": "normal"},
    })
    _write(str(base / "findings" / f"intraday_snapshot_{date}_NVDA.jsonl"), {
        "ts": "10:00:00",
        "meta": {"sym": "NVDA", "date": date, "session_min": 30, "llm_triggered": False,
                 "llm_trigger": None, "cooldown_until": None, "post_open_calibrated": True},
        "price_now": {"price": 150.0, "chg_pct": 1.2, "sector_ref": "SOXX", "sector_gap_pct": 0.0, "rs_vs_sector": 0.0},
        "plan_vs_now": {"entry_go_status": "go"},
        "node_snapshot": {},
        "action_now": None
    })
    _write(str(base / "learning" / "dashboard_cache.json"), {
        "premarket": {
            "NVDA": {
                "stock_snapshot": {"sector_ref": "SOXX", "sector_gap_pct": 3.0, "rs_vs_sector": 1.0}
            }
        },
        "intraday": {
            "NVDA": {
                "price_now": {"sector_ref": "SOXX", "sector_gap_pct": 3.0, "rs_vs_sector": 1.0}
            }
        },
        "learning": {
            "scope": "all_time",
            "source_coverage": {"observation": 0, "lesson": 0, "decision": 0, "outcome": 0, "knowledge_node": 0},
            "latest_lessons": [],
            "latest_observations": [],
            "open_questions": []
        }
    })

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))

    assert ctx["premarket"]["NVDA"]["stock_snapshot"]["sector_gap_pct"] == 0.0
    assert ctx["premarket"]["NVDA"]["stock_snapshot"]["rs_vs_sector"] == 0.0
    assert ctx["intraday"]["NVDA"]["price_now"]["sector_gap_pct"] == 0.0
    assert ctx["intraday"]["NVDA"]["price_now"]["rs_vs_sector"] == 0.0


def test_build_dashboard_context_uses_cached_learning_without_rebuild(tmp_path, monkeypatch):
    """dashboard render should use cached learning or empty payload, not rebuild the journal."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-24"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()

    _write(str(base / "config" / "positions.json"), {"positions": {"NVDA": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    with open(base / "learning" / "knowledge_journal.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "lesson", "id": "les-x", "date": date, "summary": "should not rebuild"}) + "\n")
    _write(str(base / "learning" / "dashboard_cache.json"), {
        "learning": {
            "scope": "all_time",
            "source_coverage": {"observation": 2, "lesson": 1, "decision": 0, "outcome": 0, "knowledge_node": 0},
            "latest_lessons": [{"summary": "cached lesson"}],
            "latest_observations": [{"summary": "cached obs"}],
            "open_questions": ["cached q"]
        }
    })

    import agents.knowledge_index as knowledge_index

    monkeypatch.setattr(knowledge_index, "rebuild_knowledge_index", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("rebuild should not run")))
    monkeypatch.setattr(knowledge_index, "load_knowledge_index", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("load_knowledge_index should not run")))

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    learning = ctx["learning"]

    assert learning["scope"] == "all_time"
    assert learning["source_coverage"]["lesson"] == 1
    assert learning["latest_lessons"][0]["summary"] == "cached lesson"
    assert learning["latest_observations"][0]["summary"] == "cached obs"


def test_build_dashboard_context_attaches_mini_chart_from_intraday_rows(tmp_path):
    """dashboard context should attach a compact mini_chart derived from existing intraday rows."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-24"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {"NVDA": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})

    node_snapshot = {
        "entry_base": 101.0,
        "hard_stop": 96.0,
        "target": 112.0,
        "flex_add": 99.0,
        "flex_reduce": 108.0,
    }
    prices = [100.0 + i for i in range(10)]
    with open(base / "findings" / f"intraday_snapshot_{date}_NVDA.jsonl", "w", encoding="utf-8") as f:
        for idx, price in enumerate(prices):
            f.write(json.dumps({
                "ts": f"09:{30 + idx:02d}:00",
                "meta": {"sym": "NVDA", "date": date, "session_min": idx, "llm_triggered": False,
                         "llm_trigger": None, "cooldown_until": None, "post_open_calibrated": True},
                "price_now": {"price": price, "chg_pct": 1.0, "gate_status": "閫氳繃"},
                "plan_vs_now": {"entry_go_status": "go"},
                "node_snapshot": node_snapshot if idx == len(prices) - 1 else {},
                "action_now": None,
            }, ensure_ascii=False) + "\n")

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    mini_chart = ctx["intraday"]["NVDA"]["mini_chart"]

    assert mini_chart["kind"] == "candles"
    assert mini_chart["count"] == 10
    assert len(mini_chart["candles"]) == 10
    assert mini_chart["candles"][0]["open"] == 100.0
    assert mini_chart["candles"][0]["slot"] == 0
    assert mini_chart["candles"][0]["close"] == 100.0
    assert mini_chart["candles"][0]["high"] == 100.05
    assert mini_chart["candles"][0]["low"] == 99.95
    assert mini_chart["candles"][-1]["close"] == 109.0
    assert mini_chart["nodes"] == [
        {"name": "entry_base", "price": 101.0},
        {"name": "hard_stop", "price": 96.0},
        {"name": "target", "price": 112.0},
        {"name": "flex_add", "price": 99.0},
        {"name": "flex_reduce", "price": 108.0},
    ]


def test_build_dashboard_context_right_aligns_sparse_mini_chart_slots(tmp_path):
    """sparse intraday mini charts should use fixed 10-slot positions."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {"MRVL": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["MRVL"]})

    with open(base / "findings" / f"intraday_snapshot_{date}_MRVL.jsonl", "w", encoding="utf-8") as f:
        for idx, price in enumerate([196.1, 196.4, 196.2, 196.5]):
            f.write(json.dumps({
                "ts": f"09:{30 + idx:02d}:00",
                "meta": {"sym": "MRVL", "date": date, "session_min": idx, "llm_triggered": False,
                         "llm_trigger": None, "cooldown_until": None, "post_open_calibrated": True},
                "price_now": {"price": price, "chg_pct": 3.0, "gate_status": "ok"},
                "plan_vs_now": {"entry_go_status": "go"},
                "node_snapshot": {},
                "action_now": None,
            }, ensure_ascii=False) + "\n")

    ctx = build_dashboard_context(date, symbols=["MRVL"], base_dir=str(base))
    candles = ctx["intraday"]["MRVL"]["mini_chart"]["candles"]

    assert [candle["slot"] for candle in candles] == [6, 7, 8, 9]


def test_build_dashboard_context_uses_previous_intraday_tail_when_today_missing(tmp_path):
    """when today has no intraday rows, mini_chart should fall back to the latest prior tail."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    prev_date = "2026-05-24"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {"MRVL": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["MRVL"]})

    with open(base / "findings" / f"intraday_snapshot_{prev_date}_MRVL.jsonl", "w", encoding="utf-8") as f:
        for idx, price in enumerate([193.0 + i for i in range(12)]):
            f.write(json.dumps({
                "ts": f"15:{48 + idx:02d}:00",
                "meta": {"sym": "MRVL", "date": prev_date, "session_min": 300 + idx,
                         "llm_triggered": False, "llm_trigger": None,
                         "cooldown_until": None, "post_open_calibrated": True},
                "price_now": {"price": price, "chg_pct": 1.0, "gate_status": "ok"},
                "plan_vs_now": {"entry_go_status": "expired"},
                "node_snapshot": {"hard_stop": 190.0},
                "action_now": None,
            }, ensure_ascii=False) + "\n")

    ctx = build_dashboard_context(date, symbols=["MRVL"], base_dir=str(base))
    rec = ctx["intraday"]["MRVL"]
    chart = rec["mini_chart"]

    assert rec["meta"]["chart_source"] == "previous_close"
    assert rec["price_now"] == {}
    assert chart["source"] == "previous_close"
    assert chart["source_date"] == prev_date
    assert chart["count"] == 10
    assert chart["candles"][0]["close"] == 195.0
    assert chart["candles"][-1]["close"] == 204.0


def test_build_dashboard_context_uses_previous_tail_for_sparse_today_chart(tmp_path):
    """sparse today rows should keep current price but chart from previous close."""
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    prev_date = "2026-05-24"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {"MRVL": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["MRVL"]})

    with open(base / "findings" / f"intraday_snapshot_{date}_MRVL.jsonl", "w", encoding="utf-8") as f:
        for idx, price in enumerate([196.1, 196.4, 196.2, 196.5]):
            f.write(json.dumps({
                "ts": f"09:{30 + idx:02d}:00",
                "meta": {"sym": "MRVL", "date": date},
                "price_now": {"price": price, "chg_pct": 3.0},
                "plan_vs_now": {"entry_go_status": "expired"},
                "node_snapshot": {},
                "action_now": None,
            }, ensure_ascii=False) + "\n")
    with open(base / "findings" / f"intraday_snapshot_{prev_date}_MRVL.jsonl", "w", encoding="utf-8") as f:
        for idx, price in enumerate([190.0 + i for i in range(10)]):
            f.write(json.dumps({
                "ts": f"15:{40 + idx:02d}:00",
                "meta": {"sym": "MRVL", "date": prev_date},
                "price_now": {"price": price, "chg_pct": 1.0},
                "plan_vs_now": {},
                "node_snapshot": {"hard_stop": 188.0},
                "action_now": None,
            }, ensure_ascii=False) + "\n")

    ctx = build_dashboard_context(date, symbols=["MRVL"], base_dir=str(base))
    rec = ctx["intraday"]["MRVL"]

    assert rec["price_now"]["price"] == 196.5
    assert rec["meta"]["chart_source"] == "previous_close"
    assert rec["mini_chart"]["source"] == "previous_close"
    assert rec["mini_chart"]["count"] == 10
    assert rec["mini_chart"]["candles"][0]["close"] == 190.0


def test_write_dashboard_renders_mini_candle_card_markup(tmp_path):
    """rendered dashboard should include the compact candle strip scaffold."""
    from agents.dashboard_writer import write_dashboard

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = tmp_path
    shutil.copytree(os.path.join(repo_root, "templates"), base / "templates")
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()

    date = "2026-05-24"
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})

    node_snapshot = {
        "entry_base": 101.0,
        "hard_stop": 96.0,
        "target": 112.0,
        "flex_add": 99.0,
        "flex_reduce": 108.0,
    }
    with open(base / "findings" / f"intraday_snapshot_{date}_NVDA.jsonl", "w", encoding="utf-8") as f:
        for idx, price in enumerate([100.0, 101.5, 100.7, 102.0]):
            f.write(json.dumps({
                "ts": f"09:{30 + idx:02d}:00",
                "meta": {"sym": "NVDA", "date": date, "session_min": idx, "llm_triggered": False,
                         "llm_trigger": None, "cooldown_until": None, "post_open_calibrated": True},
                "price_now": {"price": price, "chg_pct": 1.0, "gate_status": "ok"},
                "plan_vs_now": {"entry_go_status": "go"},
                "node_snapshot": node_snapshot,
                "action_now": None,
            }, ensure_ascii=False) + "\n")

    out = write_dashboard(date, symbols=["NVDA"], base_dir=str(base))
    html = (base / "reports" / f"daily_dashboard_{date}.html").read_text(encoding="utf-8")

    assert out.endswith(f"daily_dashboard_{date}.html")
    assert "intraday-mini-chart" in html
    assert "mini-candle-strip" in html
    assert "mini-node-line mini-node-hard_stop" in html
    assert "mini-candle-body" in html


def test_write_dashboard_renders_intraday_card_nodes_from_macro_nodes(tmp_path):
    """intraday detail cards should fall back to macro strategy nodes for key levels."""
    from agents.dashboard_writer import write_dashboard

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = tmp_path
    shutil.copytree(os.path.join(repo_root, "templates"), base / "templates")
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()

    date = "2026-05-25"
    _write(str(base / "config" / "positions.json"), {"positions": {"MRVL": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["MRVL"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["MRVL"]})
    _write(str(base / f"macro_strategy_MRVL.json"), {
        "nodes": {
            "dynamic_stop": {"price": 145.14},
            "add1": {"price": 157.96},
            "tp1": {"price": 197.18},
            "scenario_downgrade": {"bull_to_base": {"price": 164.82}},
        }
    })
    with open(base / "findings" / f"intraday_snapshot_{date}_MRVL.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": "09:30:00",
            "meta": {"sym": "MRVL", "date": date},
            "price_now": {"price": 196.51, "chg_pct": 3.05},
            "plan_vs_now": {"entry_go_status": "expired", "thesis_signal": "intact"},
            "node_snapshot": {},
            "action_now": None,
        }, ensure_ascii=False) + "\n")

    write_dashboard(date, symbols=["MRVL"], base_dir=str(base))
    html = (base / "reports" / f"daily_dashboard_{date}.html").read_text(encoding="utf-8")

    assert "$145.14" in html
    assert "$157.96" in html
    assert "$197.18" in html


def test_write_dashboard_renders_intraday_mini_candle_strip(tmp_path):
    """dashboard HTML should include the compact intraday candlestick strip."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from agents.dashboard_writer import build_dashboard_context

    date = "2026-05-24"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {"NVDA": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})
    with open(base / "findings" / f"intraday_snapshot_{date}_NVDA.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": "09:30:00",
            "meta": {"sym": "NVDA", "date": date, "session_min": 0, "llm_triggered": False,
                     "llm_trigger": None, "cooldown_until": None, "post_open_calibrated": True},
            "price_now": {"price": 100.0, "chg_pct": 1.0, "gate_status": "ok"},
            "plan_vs_now": {"entry_go_status": "go"},
            "node_snapshot": {
                "entry_base": 101.0,
                "hard_stop": 96.0,
                "target": 112.0,
                "flex_add": 99.0,
                "flex_reduce": 108.0,
            },
            "action_now": None,
        }, ensure_ascii=False) + "\n")

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    assert "mini-candle-strip" in html
    assert "mini-node-line" in html
    assert "mini-candle-body" in html


