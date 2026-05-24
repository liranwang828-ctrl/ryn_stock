import sys, os, json, datetime
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _make_premarket(tmp_path, sym, date, action_dec="enter", exit_dec=None):
    path = str(tmp_path / "findings" / f"premarket_summary_{date}_{sym}.json")
    entry = {"decision": action_dec, "entry_base": 100.0, "stop_loss": 95.0,
             "target_price": 110.0}
    exit_ = {"decision": exit_dec, "hard_stop": 95.0, "target_price": 110.0,
              "flex_add_level": 93.0, "flex_reduce_level": 108.0} if exit_dec else None
    _write(path, {
        "date": date, "sym": sym,
        "market_context": {"env": "顺风", "vix_level": 18.5, "macro_events_today": []},
        "entry": entry,
        "exit": exit_,
        "thesis": {"status": "intact"} if exit_ else None,
        "strategic_context": {"source": "premarket_inferred"},
        "post_open_adj": None,
    })
    return path


def _make_positions(tmp_path, sym, gtc_placed=True):
    path = str(tmp_path / "config" / "positions.json")
    _write(path, {
        "positions": {sym: {
            "cost": 100.0, "shares": 10, "date": "2026-05-12",
            "thesis_status": "intact",
            "gtc_stop_placed": gtc_placed, "gtc_stop_date": "2026-05-12",
        }},
        "_excluded": [],
    })
    return path


# ── action_now 规则 ──────────────────────────────────────────────────────

def test_action_now_exit_beats_entry():
    """exit=exit 优先于 entry=enter"""
    from agents.daily_plan_writer import compute_action_now
    result = compute_action_now(
        entry_decision="enter", exit_decision="exit",
        thesis_status="intact", is_held=True,
    )
    assert result == "exit"


def test_action_now_reduce_beats_enter():
    """exit=reduce 优先于 entry=enter"""
    from agents.daily_plan_writer import compute_action_now
    result = compute_action_now(
        entry_decision="enter", exit_decision="reduce",
        thesis_status="intact", is_held=True,
    )
    assert result == "reduce"


def test_action_now_no_position_pass():
    """无仓位 + entry=pass → pass"""
    from agents.daily_plan_writer import compute_action_now
    result = compute_action_now(
        entry_decision="pass", exit_decision=None,
        thesis_status=None, is_held=False,
    )
    assert result == "pass"


def test_action_now_held_intact_hold():
    """有仓 + entry=pass + thesis=intact → hold"""
    from agents.daily_plan_writer import compute_action_now
    result = compute_action_now(
        entry_decision="pass", exit_decision=None,
        thesis_status="intact", is_held=True,
    )
    assert result == "hold"


# ── gtc_status 规则 ──────────────────────────────────────────────────────

def test_compute_gtc_status_missing(tmp_path):
    """gtc_stop_placed=False → 在 missing 列表中"""
    from agents.daily_plan_writer import compute_gtc_status
    _make_positions(tmp_path, "NVDA", gtc_placed=False)
    status = compute_gtc_status(base_dir=str(tmp_path))
    assert "NVDA" in status["missing"]
    assert "NVDA" not in status["placed"]


def test_compute_gtc_status_placed(tmp_path):
    """gtc_stop_placed=True → 在 placed 列表中"""
    from agents.daily_plan_writer import compute_gtc_status
    _make_positions(tmp_path, "NVDA", gtc_placed=True)
    status = compute_gtc_status(base_dir=str(tmp_path))
    assert "NVDA" in status["placed"]
    assert "NVDA" not in status["missing"]


# ── compute_next_action ──────────────────────────────────────────────────

def test_next_action_red_alert_is_immediate():
    """missed_alerts 有 red → immediate"""
    from agents.daily_plan_writer import compute_next_action
    session_state = {
        "missed_alerts": [{"level": "red", "sym": "NVDA", "event": "hard_stop_breach",
                           "detail": "破止损"}],
        "gtc_status": {"missing": [], "placed": ["NVDA"]},
    }
    daily_plan = {"pending_suggestions_total": 0, "per_symbol": {}}
    result = compute_next_action(session_state, daily_plan, session_min=40)
    assert result["priority"] == "immediate"


def test_next_action_gtc_missing_is_immediate(tmp_path):
    """gtc_status.missing 非空 → immediate"""
    from agents.daily_plan_writer import compute_next_action
    session_state = {
        "missed_alerts": [],
        "gtc_status": {"missing": ["NVDA"], "placed": []},
    }
    daily_plan = {"pending_suggestions_total": 0, "per_symbol": {}}
    result = compute_next_action(session_state, daily_plan, session_min=40)
    assert result["priority"] == "immediate"


def test_next_action_normal_fallback():
    """无紧急情况 → normal"""
    from agents.daily_plan_writer import compute_next_action
    session_state = {
        "missed_alerts": [],
        "gtc_status": {"missing": [], "placed": ["NVDA"]},
    }
    daily_plan = {"pending_suggestions_total": 0, "per_symbol": {}}
    result = compute_next_action(session_state, daily_plan, session_min=40)
    assert result["priority"] == "normal"


# ── build_daily_plan ─────────────────────────────────────────────────────

def test_build_daily_plan_schema(tmp_path):
    """build_daily_plan 返回所有顶层字段"""
    from agents.daily_plan_writer import build_daily_plan
    date = "2026-05-20"
    _make_premarket(tmp_path, "NVDA", date, action_dec="enter")
    _make_positions(tmp_path, "NVDA")

    plan = build_daily_plan(date, symbols=["NVDA"], base_dir=str(tmp_path))
    required = {"date", "generated_at", "market_context", "symbols_today",
                "per_symbol", "schedule", "gtc_required", "pending_suggestions_total"}
    assert required == set(plan.keys()), f"缺少: {required - set(plan.keys())}"
    assert "NVDA" in plan["per_symbol"]
    assert plan["per_symbol"]["NVDA"]["action_now"] == "enter"
