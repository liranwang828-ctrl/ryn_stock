import json
from pathlib import Path


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_lock_consensus_writes_poll_dashboard_contract(tmp_path):
    from stock_team.core.premarket_consensus_lock import lock_consensus

    (tmp_path / "config").mkdir()
    (tmp_path / "findings").mkdir()
    (tmp_path / "learning").mkdir()
    (tmp_path / "templates").mkdir()
    _ = tmp_path / "templates" / "daily_dashboard.html.j2"
    _.write_text("{{ session_lock.locked }} {{ symbols|join(',') }}", encoding="utf-8")
    (tmp_path / "config" / "daily_focus.json").write_text(
        json.dumps({"focus_stocks": ["OLD"]}),
        encoding="utf-8",
    )
    (tmp_path / "config" / "today_focus.json").write_text(
        json.dumps(["OLD"]),
        encoding="utf-8",
    )
    (tmp_path / "config" / "poll_config.json").write_text(
        json.dumps({"default_symbols": ["OLD"], "portfolio_symbols": ["OLD"], "watchlist": []}),
        encoding="utf-8",
    )
    (tmp_path / "config" / "positions.json").write_text(
        json.dumps({"positions": {"COHR": {"shares": 10}, "NOW": {"shares": 15}}}),
        encoding="utf-8",
    )

    result = lock_consensus(
        date="2026-05-26",
        decisions={
            "COHR": {
                "action": "wait",
                "entry_base": 375,
                "entry_low": 370,
                "entry_high": 385,
                "hard_stop": 340,
                "soft_stop": 355,
                "target": 420,
                "flex_add": 355,
                "flex_reduce": 450,
                "target_2": 450,
                "reasoning": "RR too weak; wait for pullback.",
                "rr_ratio": 1.3,
            }
        },
        base_dir=str(tmp_path),
        session_name="lite_cohr",
        rebuild_dashboard=False,
    )

    assert result["ok"] is True
    confirmation = result["confirmation"]
    assert "今日盘前共识已锁定" in confirmation["text"]
    assert "COHR: wait" in confirmation["text"]
    assert "entry_base=375.0" in confirmation["text"]
    assert "findings/premarket_summary_2026-05-26_COHR.json" in confirmation["updated_files"]
    pm = _read(tmp_path / "findings" / "premarket_summary_2026-05-26_COHR.json")
    assert pm["source"] == "human_agent_consensus"
    assert pm["entry"]["entry_base"] == 375.0
    assert pm["entry"]["entry_zone"] == [370.0, 385.0]
    assert pm["exit"]["hard_stop"] == 340.0
    assert pm["exit"]["flex_reduce_level"] == 450.0

    capsule_pm = _read(tmp_path / "findings" / "symbols" / "COHR" / "plans" / "premarket_summary_2026-05-26.json")
    assert capsule_pm["entry"]["target_price"] == 420.0
    latest_pm = _read(tmp_path / "findings" / "symbols" / "COHR" / "latest_premarket_plan.json")
    assert latest_pm["date"] == "2026-05-26"
    assert latest_pm["source_archive"] == "plans/premarket_summary_2026-05-26.json"
    assert latest_pm["entry"]["entry_base"] == 375.0
    current_nodes = _read(tmp_path / "findings" / "symbols" / "COHR" / "current_nodes.json")
    assert current_nodes["source"] == "human_agent_consensus"
    assert current_nodes["source_plan"] == "latest_premarket_plan.json"
    assert current_nodes["nodes"]["entry_base"]["price"] == 375.0
    assert current_nodes["nodes"]["hard_stop"]["price"] == 340.0
    assert "findings/symbols/COHR/latest_premarket_plan.json" in confirmation["updated_files"]
    assert "findings/symbols/COHR/current_nodes.json" in confirmation["updated_files"]

    macro = _read(tmp_path / "macro_strategy_COHR.json")
    assert macro["source"] == "human_agent_consensus"
    assert macro["nodes"]["entry_base"]["price"] == 375.0
    assert macro["nodes"]["hard_stop"]["price"] == 340.0
    assert macro["nodes"]["flex_reduce"]["price"] == 450.0

    daily_plan = _read(tmp_path / "daily_plan_2026-05-26.json")
    assert daily_plan["symbols_today"] == ["COHR"]
    assert daily_plan["per_symbol"]["COHR"]["key_levels"]["entry_base"] == 375.0
    assert daily_plan["per_symbol"]["COHR"]["action_now"] == "wait"

    lock = _read(tmp_path / "findings" / "session_lock.json")
    assert lock["locked"] is True
    assert lock["symbols"] == ["COHR"]
    assert lock["session_name"] == "lite_cohr"

    focus = _read(tmp_path / "config" / "daily_focus.json")
    today_focus = _read(tmp_path / "config" / "today_focus.json")
    poll_cfg = _read(tmp_path / "config" / "poll_config.json")
    assert focus["focus_stocks"] == ["COHR"]
    assert today_focus == ["COHR"]
    assert poll_cfg["default_symbols"] == ["COHR"]
    assert poll_cfg["portfolio_symbols"] == ["COHR", "NOW"]


def test_lock_decision_package_keeps_rejected_out_of_focus_and_poll(tmp_path):
    from stock_team.core.premarket_consensus_lock import lock_decision_package

    (tmp_path / "config").mkdir()
    (tmp_path / "findings").mkdir()
    (tmp_path / "learning").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "daily_dashboard.html.j2").write_text(
        "{{ session_lock.locked }} {{ symbols|join(',') }}",
        encoding="utf-8",
    )
    (tmp_path / "config" / "daily_focus.json").write_text(
        json.dumps({"focus_stocks": ["OLD"]}),
        encoding="utf-8",
    )
    (tmp_path / "config" / "today_focus.json").write_text(
        json.dumps(["OLD"]),
        encoding="utf-8",
    )
    (tmp_path / "config" / "poll_config.json").write_text(
        json.dumps({"default_symbols": ["OLD"], "portfolio_symbols": ["OLD"], "watchlist": []}),
        encoding="utf-8",
    )
    (tmp_path / "config" / "positions.json").write_text(
        json.dumps({"positions": {"COHR": {"shares": 10}, "VST": {"shares": 5}, "NOW": {"shares": 15}}}),
        encoding="utf-8",
    )

    package = {
        "session_name": "multi_compare",
        "selected_symbols": ["COHR", "VST"],
        "rejected_symbols": {
            "GOOGL": "Relative strength is weak; keep as research-only.",
            "LITE": "Discussed as peer, not today's focus.",
        },
        "portfolio_context": {"max_new_exposure_pct": 5},
        "decisions": {
            "COHR": {
                "action": "watch",
                "entry_low": 370,
                "entry_high": 385,
                "entry_base": 375,
                "hard_stop": 340,
                "target": 420,
                "allocation_pct": 0,
                "reasoning": "Wait for pullback.",
            },
            "VST": {
                "action": "starter",
                "entry_base": 156,
                "hard_stop": 128,
                "target": 185,
                "flex_add": 148,
                "flex_reduce": 205,
                "allocation_pct": 2,
                "reasoning": "Starter allowed.",
            },
            "GOOGL": {
                "action": "reject",
                "entry_base": 380,
                "hard_stop": 360,
                "target": 420,
            },
        },
    }

    result = lock_decision_package(
        date="2026-05-26",
        package=package,
        base_dir=str(tmp_path),
        rebuild_dashboard=False,
    )

    assert result["ok"] is True
    assert result["symbols"] == ["COHR", "VST"]
    assert result["rejected_symbols"] == {"GOOGL": "Relative strength is weak; keep as research-only.", "LITE": "Discussed as peer, not today's focus."}
    confirmation = result["confirmation"]
    assert "今日关注: COHR / VST" in confirmation["text"]
    assert "未纳入今日关注" in confirmation["text"]
    assert "GOOGL: Relative strength is weak; keep as research-only." in confirmation["text"]
    assert "LITE: Discussed as peer, not today's focus." in confirmation["text"]
    assert "GOOGL" not in confirmation["selected_symbols"]
    assert (tmp_path / "findings" / "premarket_summary_2026-05-26_COHR.json").exists()
    assert (tmp_path / "findings" / "premarket_summary_2026-05-26_VST.json").exists()
    assert not (tmp_path / "findings" / "premarket_summary_2026-05-26_GOOGL.json").exists()

    focus = _read(tmp_path / "config" / "daily_focus.json")
    today_focus = _read(tmp_path / "config" / "today_focus.json")
    poll_cfg = _read(tmp_path / "config" / "poll_config.json")
    assert focus["focus_stocks"] == ["COHR", "VST"]
    assert today_focus == ["COHR", "VST"]
    assert poll_cfg["default_symbols"] == ["COHR", "VST"]
    assert "GOOGL" not in poll_cfg["default_symbols"]
    assert poll_cfg["portfolio_symbols"] == ["COHR", "VST", "NOW"]

    lock = _read(tmp_path / "findings" / "session_lock.json")
    assert lock["symbols"] == ["COHR", "VST"]
    assert lock["rejected_symbols"]["GOOGL"].startswith("Relative strength")

    record = _read(tmp_path / "findings" / "premarket_consensus_2026-05-26_multi_compare.json")
    assert record["selected_symbols"] == ["COHR", "VST"]
    assert "GOOGL" in record["rejected_symbols"]
    assert record["portfolio_context"]["max_new_exposure_pct"] == 5
