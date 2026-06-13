# tests/test_dashboard_writer.py
import sys, os, json, shutil

def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_load_premarket_summaries_returns_dict(tmp_path):
    """load_premarket_summaries 杩斿洖 {sym: summary} 瀛楀吀"""
    from stock_team.server.dashboard_writer import load_premarket_summaries
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
    from stock_team.server.dashboard_writer import load_intraday_latest
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
    from stock_team.server.dashboard_writer import load_intraday_events
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
    from stock_team.server.dashboard_writer import build_dashboard_context
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()

    ctx = build_dashboard_context(date, symbols=["NVDA"],
                                  base_dir=str(tmp_path))
    required = {"date", "generated_at", "symbols", "premarket",
                "intraday", "events", "portfolio", "postmarket_day",
                "session_state", "daily_plan"}
    assert required.issubset(set(ctx.keys())), f"缂哄皯: {required - set(ctx.keys())}"


def test_dashboard_context_loads_decision_state_when_present(tmp_path):
    """dashboard context should expose decision_state from findings."""
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    _write(str(base / "findings" / f"decision_state_{date}.json"), {
        "date": date,
        "symbols": {
            "NVDA": {
                "state": "watch",
                "confidence": 0.72,
                "reasons": ["holding above trigger"],
            }
        },
    })

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))

    assert ctx["decision_state"]["date"] == date
    assert ctx["decision_state"]["symbols"]["NVDA"]["state"] == "watch"
    assert ctx["decision_state"]["symbols"]["NVDA"]["confidence"] == 0.72


def test_dashboard_context_uses_empty_decision_state_when_missing(tmp_path):
    """dashboard context should include an empty decision_state fallback."""
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))

    assert ctx["decision_state"] == {"date": date, "symbols": {}}


def test_build_dashboard_context_includes_learning_state(tmp_path):
    """dashboard context should surface compact learning state from the cached index."""
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import load_portfolio_snapshot

    findings = tmp_path / "findings"
    findings.mkdir()

    with patch("stock_team.core.portfolio_snapshot.build_portfolio_snapshot") as build, \
         patch("stock_team.core.portfolio_snapshot.write_portfolio_snapshot") as write:
        build.return_value = {"totals": {"total_value": 1000.0}}

        result = load_portfolio_snapshot("2026-05-24", find_dir=str(findings))

    assert result == {}
    build.assert_not_called()
    write.assert_not_called()


def test_load_portfolio_snapshot_prefers_current_over_dated(tmp_path):
    """Dashboard current-state portfolio should not be pinned to a stale dated archive."""
    from stock_team.server.dashboard_writer import load_portfolio_snapshot

    findings = tmp_path / "findings"
    findings.mkdir()
    (findings / "portfolio_snapshot_2026-05-26.json").write_text(
        json.dumps({"source": "dated", "positions_detail": [{"sym": "OLD"}]}),
        encoding="utf-8",
    )
    (findings / "portfolio_snapshot_current.json").write_text(
        json.dumps({"source": "current", "positions_detail": [{"sym": "NEW"}]}),
        encoding="utf-8",
    )

    result = load_portfolio_snapshot("2026-05-26", find_dir=str(findings))

    assert result["source"] == "current"
    assert result["positions_detail"][0]["sym"] == "NEW"


def test_load_portfolio_snapshot_can_read_dated_archive_for_history(tmp_path):
    """Historical charts should keep reading dated archives, not the current-state file."""
    from stock_team.server.dashboard_writer import load_portfolio_snapshot

    findings = tmp_path / "findings"
    findings.mkdir()
    (findings / "portfolio_snapshot_2026-05-25.json").write_text(
        json.dumps({"source": "dated", "totals": {"total_value": 25000}}),
        encoding="utf-8",
    )
    (findings / "portfolio_snapshot_current.json").write_text(
        json.dumps({"source": "current", "totals": {"total_value": 40000}}),
        encoding="utf-8",
    )

    result = load_portfolio_snapshot("2026-05-25", find_dir=str(findings), prefer_current=False)

    assert result["source"] == "dated"
    assert result["totals"]["total_value"] == 25000


def test_load_intraday_latest_fills_missing_defaults(tmp_path):
    """load_intraday_latest should backfill missing intraday defaults."""
    from stock_team.server.dashboard_writer import load_intraday_latest
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


def test_dashboard_portfolio_uses_broker_last_price_over_snapshot(tmp_path):
    """Asset allocation should prefer local broker price snapshots over stale risk snapshots."""
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-26"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})
    _write(str(base / "config" / "positions.json"), {
        "cash": 1000.0,
        "positions": {
            "MRVU": {
                "shares": 25,
                "cost": 123.75,
                "broker_last_price": 142.2,
            }
        },
    })
    _write(str(base / "findings" / "portfolio_snapshot_current.json"), {
        "positions_detail": [{
            "sym": "MRVU",
            "shares": 25,
            "cost": 123.75,
            "cur_price": 122.48,
            "market_value": 3062.0,
            "net_exposure": 6124.0,
            "leverage": 2,
            "beta": 2.0,
            "var_5pct_loss": 612.4,
        }],
        "totals": {
            "total_value": 4062.0,
            "total_exposure": 6124.0,
            "var_5pct_loss": 612.4,
            "total_unrealized_pnl_pct": -1.0,
        },
    })

    ctx = build_dashboard_context(date, symbols=[], base_dir=str(base))
    row = ctx["portfolio"]["positions_detail"][0]
    assert row["cur_price"] == 142.2
    assert row["market_value"] == 3555.0
    assert row["net_exposure"] == 7110.0
    assert row["price_source"] == "broker_last_price"
    assert ctx["nav"] == 4555.0


def test_build_dashboard_route_snapshot_uses_existing_context_fields(tmp_path):
    from stock_team.server.dashboard_writer import build_dashboard_context, build_dashboard_route_snapshot

    date = "2026-05-31"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NOW"]})

    ctx = build_dashboard_context(date, symbols=["NOW"], base_dir=str(base))
    snapshot = build_dashboard_route_snapshot(ctx)

    assert snapshot["top_symbols"] == ["NOW"]
    assert snapshot["has_focus"] is True


def test_build_dashboard_context_normalizes_summary_fields(tmp_path):
    """dashboard context should normalize missing summary fields."""
    from stock_team.server.dashboard_writer import build_dashboard_context
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
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    from stock_team.server.dashboard_writer import write_dashboard

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    html = (base / "reports" / "dashboard.html").read_text(encoding="utf-8")

    assert out.endswith("dashboard.html")
    assert "intraday-mini-chart" in html
    assert "mini-candle-strip" in html
    assert "mini-node-line mini-node-hard_stop" in html
    assert "mini-candle-body" in html


def test_write_dashboard_renders_intraday_card_nodes_from_macro_nodes(tmp_path):
    """intraday detail cards should fall back to macro strategy nodes for key levels."""
    from stock_team.server.dashboard_writer import write_dashboard

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    html = (base / "reports" / "dashboard.html").read_text(encoding="utf-8")

    assert "$145.14" in html
    assert "$157.96" in html
    assert "$197.18" in html


def test_write_dashboard_renders_intraday_mini_candle_strip(tmp_path):
    """dashboard HTML should include the compact intraday candlestick strip."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

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
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    assert "mini-candle-strip" in html
    assert "mini-node-line" in html
    assert "mini-candle-body" in html


def test_write_dashboard_renders_focus_research_status_panel(tmp_path):
    """dashboard should frame today's focus as research status, not a task launcher."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    assert "focus-readiness-panel" in html
    assert "今日关注可以来自 agent 对话、候选池、持仓或手动输入" in html
    assert "research-status-chip" in html
    assert "缺口补全" in html
    assert "generateAllFocusReports()" in html
    assert "refreshLatestPrices()" in html
    assert "generateReportForFocus('NVDA')" in html
    assert "removeFromFocus('NVDA')" in html


def test_research_portal_iframe_points_to_reports_index(tmp_path):
    """research tab should embed the reports portal, not recursively load dashboard /index.html."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})

    ctx = build_dashboard_context(date, symbols=[], base_dir=str(base))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    assert 'iframe src="/reports/index.html"' in html
    assert 'iframe src="index.html"' not in html


def test_dashboard_context_uses_historical_research_and_nodes(tmp_path):
    """focus status should use historical research and premarket nodes as fallback."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-26"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["MRVL"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["MRVL"]})
    (base / "reports" / "research_MRVL.html").write_text("<html>research</html>", encoding="utf-8")
    (base / "reports" / "2026-05-22_MRVL.html").write_text("<html>cio</html>", encoding="utf-8")
    _write(str(base / "findings" / "premarket_summary_2026-05-24_MRVL.json"), {
        "date": "2026-05-24",
        "sym": "MRVL",
        "entry": {"entry_base": 196.0, "target_price": 210.0},
        "exit": {"hard_stop": 188.0, "flex_add_level": 192.0, "flex_reduce_level": 205.0},
        "thesis": {"status": "intact"},
    })

    ctx = build_dashboard_context(date, symbols=["MRVL"], base_dir=str(base))
    status = ctx["report_status"]["MRVL"]
    nodes = ctx["macro_nodes"]["MRVL"]

    assert status["research_base_state"] == "ready"
    assert status["trade_plan_state"] == "historical"
    assert status["today_state"] == "needs_refresh"
    assert status["latest_cio_date"] == "2026-05-22"
    assert status["latest_premarket_date"] == "2026-05-24"
    assert nodes["dynamic_stop"]["price"] == 188.0
    assert nodes["add1"]["price"] == 192.0
    assert nodes["flex_reduce"]["price"] == 205.0
    assert nodes["tp1"]["price"] == 210.0

    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)
    assert "研究已建" in html
    assert "历史计划" in html
    assert "今日待刷新" in html
    assert "历史CIO" in html
    assert "✅节点" in html


def test_dashboard_context_keeps_daily_focus_symbol_with_cache_and_current_nodes(tmp_path):
    """daily focus symbols should render even when they only have manual refresh cache."""
    from stock_team.server.dashboard_cache import update_latest_prices
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-27"
    base = tmp_path
    (base / "findings" / "symbols" / "NOW").mkdir(parents=True)
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NOW"]})
    _write(str(base / "findings" / "symbols" / "NOW" / "current_nodes.json"), {
        "date": date,
        "source": "manual_watchlist_refresh",
        "nodes": {
            "entry_base": {"price": 96},
            "hard_stop": {"price": 82},
            "target": {"price": 135},
        },
    })
    update_latest_prices(str(base), {"NOW": {"price": 99.92, "source": "manual_watchlist_refresh"}}, asof="2026-05-27 12:29:02")

    ctx = build_dashboard_context(date, base_dir=str(base))

    assert "NOW" in ctx["focus_list"]
    assert ctx["intraday"]["NOW"]["price_now"]["price"] == 99.92
    assert ctx["intraday"]["NOW"]["mini_chart"]["candles"]
    assert ctx["macro_nodes"]["NOW"]["dynamic_stop"]["price"] == 82
    assert ctx["macro_nodes"]["NOW"]["tp1"]["price"] == 135


def test_dashboard_prefers_symbol_current_plan_and_nodes(tmp_path):
    """Current capsule plan/nodes should be the dashboard source even when dated archives exist."""
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-26"
    base = tmp_path
    (base / "findings" / "symbols" / "NVDA" / "plans").mkdir(parents=True)
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"cash": 0, "positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})
    _write(str(base / "findings" / "symbols" / "NVDA" / "plans" / "premarket_summary_2026-05-25.json"), {
        "date": "2026-05-25",
        "sym": "NVDA",
        "entry": {"entry_base": 100.0},
        "exit": {"hard_stop": 90.0},
    })
    _write(str(base / "findings" / "symbols" / "NVDA" / "latest_premarket_plan.json"), {
        "date": date,
        "sym": "NVDA",
        "entry": {"entry_base": 120.0},
        "exit": {"hard_stop": 110.0},
    })
    _write(str(base / "findings" / "symbols" / "NVDA" / "current_nodes.json"), {
        "date": date,
        "sym": "NVDA",
        "nodes": {
            "entry_base": {"price": 120.0, "label": "Entry base"},
            "hard_stop": {"price": 110.0, "label": "Hard stop"},
        },
    })

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    status = ctx["report_status"]["NVDA"]

    assert status["trade_plan_state"] == "today"
    assert status["today_state"] == "ready"
    assert status["latest_premarket_date"] == date
    assert ctx["premarket_details"]["NVDA"]["entry"]["entry_base"] == 120.0
    assert ctx["macro_nodes"]["NVDA"]["entry_base"]["price"] == 120.0


def test_dashboard_context_derives_flex_from_entry_when_exit_missing(tmp_path):
    """historical plans without exit section should still provide usable flex references."""
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-26"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["MRVL"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["MRVL"]})
    _write(str(base / "findings" / "premarket_summary_2026-05-24_MRVL.json"), {
        "date": "2026-05-24",
        "sym": "MRVL",
        "entry": {"entry_base": 171.23, "stop_loss": 159.44, "target_price": 188.30},
        "exit": None,
    })

    ctx = build_dashboard_context(date, symbols=["MRVL"], base_dir=str(base))
    nodes = ctx["macro_nodes"]["MRVL"]

    assert nodes["add1"]["price"] == 171.23
    assert nodes["flex_reduce"]["price"] == 188.30


def test_dashboard_renders_market_mode_action_center(tmp_path):
    """dashboard should render a phase-aware action center in the overview tab."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    # Task 1 Shell assertions
    assert "market-mode-action-center" in html
    assert "market-mode-primary-actions" in html
    assert "market-mode-secondary-actions" in html
    assert "现在可以做什么" in html

    # Task 2 JS assertions
    assert "updateMarketModeActionCenter" in html
    assert "marketModePhaseConfig" in html
    assert "runTask('scan')" in html
    assert "runTask('premarket')" in html
    assert "runTask('poll')" in html
    assert "runTask('postmarket')" in html
    assert "generateAllFocusReports()" in html

    # Task 3 CSS class assertions
    assert "market-mode-action-center" in html
    assert "market-mode-action-grid" in html
    assert "market-mode-action-btn" in html




def test_dashboard_renders_focus_to_intraday_navigation_hooks(tmp_path):
    """focus rows should offer a direct jump into symbol-level intraday review."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    assert 'id="focus-row-NVDA"' in html
    assert "focus-drilldown-link" in html
    assert "openIntradaySymbol('NVDA')" in html
    assert "function openIntradaySymbol(symbol)" in html
    assert 'id="intraday-symbol-card-NVDA"' in html


def test_dashboard_renders_intraday_return_to_global_hooks(tmp_path):
    """symbol detail cards should offer an explicit way back to the overview focus list."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    assert "intraday-return-link" in html
    assert "returnToOverviewFocus('NVDA')" in html
    assert "function returnToOverviewFocus(symbol)" in html
    assert 'id="focus-readiness-panel"' in html


def test_dashboard_renders_focus_priority_summary(tmp_path):
    """overview should surface a clear first-monitor cue instead of forcing a full table scan."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NOW", "NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NOW", "NVDA"]})
    _write(str(base / "findings" / "symbols" / "NOW" / "latest_premarket_plan.json"), {
        "date": date,
        "sym": "NOW",
        "entry": {"entry_base": 96.0},
        "exit": {"hard_stop": 90.0},
    })

    ctx = build_dashboard_context(date, symbols=["NOW", "NVDA"], base_dir=str(base))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    assert "focus-priority-strip" in html
    assert "focus-priority-lead" in html
    assert "先盯" in html
    assert "NOW" in html
    assert "openIntradaySymbol('NOW')" in html


def test_dashboard_renders_interactive_skills_directory(tmp_path):
    """dashboard should render the interactive skills directory card and JS config updates."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)

    # 1. HTML Card Assertions
    assert "skills-directory-card" in html
    assert "skills-directory-header" in html
    assert "skills-directory-content" in html
    assert "智能体交互技能名录" in html
    assert "Skill 1: 深度个股调研" in html
    assert "Skill 2: 行业板块筛选" in html
    assert "Skill 9: 回测参数优化" in html
    assert "Skill 5: 策略锚点规划" in html
    assert "Skill 6: 新建/调整持仓" in html
    assert "Skill 3: 大师辩论探讨" in html
    assert "Skill 4: 逻辑证伪与研判" in html
    assert "Skill 7: 心智纠偏与修正" in html
    assert "Skill 8: 心智复盘与日志" in html

    # 2. CSS Styles Assertions
    assert ".skills-directory-card" in html
    assert ".skill-group" in html
    assert ".skill-item" in html
    assert ".skill-copy-btn" in html

    # 3. JS Handlers & Copy Config Assertions
    assert "copySkillText" in html
    assert "Skill 2 个股行业调查" in html
    assert "Skill 9 回测参数设计" in html
    assert "Skill 5 策略锚点规划" in html
    assert "Skill 6 盘中异动监测" in html
    assert "Skill 7 心智纠偏" in html
    assert "Skill 8 心智复盘与日志" in html


def test_dashboard_context_resolves_capsule_paths(tmp_path):
    """dashboard context should successfully resolve and load paths from the stock capsule directory."""
    from pathlib import Path
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "config").mkdir()
    (base / "learning").mkdir()
    
    # Create Capsule plans & snapshots folders
    plans_dir = base / "findings" / "symbols" / "NVDA" / "plans"
    snaps_dir = base / "findings" / "symbols" / "NVDA" / "snapshots"
    plans_dir.mkdir(parents=True)
    snaps_dir.mkdir(parents=True)

    _write(str(base / "config" / "positions.json"), {"positions": {"NVDA": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})

    # Write capsule premarket summary & intraday snapshot
    _write(str(plans_dir / f"premarket_summary_{date}.json"), {
        "entry": {"entry_base": 150.0, "decision": "buy"},
        "exit": {"hard_stop": 145.0, "target_price": 170.0},
        "thesis": {"status": "intact", "today_falsification": ["f1"]}
    })
    with open(str(snaps_dir / f"intraday_snapshot_{date}.jsonl"), "w", encoding="utf-8") as sf:
        sf.write('{"price": 152.0, "time": "10:00:00"}\n')

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    
    # Assertions
    assert "NVDA" in ctx.get("premarket", {})
    assert ctx["premarket"]["NVDA"]["entry"]["entry_base"] == 150.0
    assert ctx["premarket"]["NVDA"]["entry"]["decision"] == "buy"


def test_dashboard_writer_falls_back_to_capsule_strategy(tmp_path):
    """dashboard context loading should successfully fallback to strategy.json if today's summary is missing."""
    from pathlib import Path
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-25"
    base = tmp_path
    (base / "config").mkdir()
    (base / "learning").mkdir()
    
    # Create Capsule dir
    capsule_dir = base / "findings" / "symbols" / "NVDA"
    capsule_dir.mkdir(parents=True)

    _write(str(base / "config" / "positions.json"), {"positions": {"NVDA": {}}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["NVDA"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NVDA"]})

    # Write fallback strategy.json
    _write(str(capsule_dir / "strategy.json"), {
        "symbol": "NVDA",
        "key_levels": {
            "entry_low": 148.0,
            "entry_high": 152.0,
            "stop_loss": 140.0,
            "target_price": 168.0
        },
        "exit_plan": {
            "flex_add_level": 146.0,
            "flex_reduce_level": 160.0
        },
        "thesis": {
            "status": "weakening",
            "today_falsification": ["falsification fallback"]
        }
    })

    # Call context loader without daily premarket summary (should fallback to strategy.json)
    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    
    # Assertions
    assert "NVDA" in ctx.get("premarket", {})
    pm_nvda = ctx["premarket"]["NVDA"]
    assert pm_nvda.get("_fallback_mode") is True
    assert pm_nvda["entry"]["entry_base"] == 148.0
    assert pm_nvda["entry"]["stop_loss"] == 140.0
    assert pm_nvda["thesis"]["status"] == "weakening"
    assert "falsification fallback" in pm_nvda["thesis"]["today_falsification"]


def test_dashboard_renders_session_lock_from_json(tmp_path):
    """dashboard should render lock state from session_lock.json, not post-process HTML."""
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-26"
    base = tmp_path
    (base / "config").mkdir()
    (base / "findings").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["COHR"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["COHR"]})
    _write(str(base / "findings" / "session_lock.json"), {
        "date": date,
        "locked": True,
        "symbols": ["COHR"],
        "session_name": "lite_cohr",
        "message": "Locked by human-agent consensus.",
    })

    ctx = build_dashboard_context(date, symbols=["COHR"], base_dir=str(base))
    assert ctx["session_lock"]["locked"] is True

    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[2] / "templates")),
                      autoescape=False)
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)
    assert "session-lock-banner" in html
    assert "Session Lock Active" in html
    assert "Locked by human-agent consensus." in html
    assert 'onclick="generateAllFocusReports()"' not in html
