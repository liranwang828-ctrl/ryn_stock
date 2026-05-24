# tests/test_postmarket_summary.py
import sys, os, json, datetime
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _make_premarket(tmp_path, sym, date, entry_go=True, scene="B"):
    """构造最小合法 premarket_summary"""
    path = str(tmp_path / "findings" / f"premarket_summary_{date}_{sym}.json")
    _write_json(path, {
        "date": date, "sym": sym,
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0,
                  "entry_conditions": ["A"], "cancel_conditions": []},
        "exit": {"hard_stop": 95.0, "target_price": 110.0,
                 "flex_add_level": 93.0, "flex_reduce_level": 108.0},
        "thesis": {"status": "intact", "today_falsification": []},
        "stock_snapshot": {"pred_scene": scene, "catalyst_strength": 1},
        "post_open_adj": {"entry_go": entry_go, "scene_confirmed": scene,
                          "entry_base_adj": None, "hard_stop_adj": None},
        "strategic_context": {"source": "premarket_inferred",
                              "strategic_stance": "hold", "unified_confidence": 3},
    })
    return path


def _make_intraday(tmp_path, sym, date, thesis_signal="intact"):
    """构造最小合法 intraday_snapshot（最后一条 JSONL）"""
    path = str(tmp_path / "findings" / f"intraday_snapshot_{date}_{sym}.jsonl")
    record = {
        "ts": "15:58:00",
        "meta": {"date": date, "sym": sym, "session_min": 388,
                 "llm_triggered": False, "llm_trigger": None,
                 "cooldown_until": None, "post_open_calibrated": True},
        "price_now": {"price": 105.0, "gate_status": "通过",
                      "master_avg": 6.5, "master_consensus": "buy"},
        "plan_vs_now": {"thesis_signal": thesis_signal, "entry_go_status": "go"},
        "node_snapshot": {}, "action_now": None,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _make_positions(tmp_path, sym, shares=10, cost=100.0, date="2026-05-12"):
    path = str(tmp_path / "config" / "positions.json")
    _write_json(path, {
        "positions": {sym: {
            "cost": cost, "shares": shares, "date": date,
            "thesis_status": "intact", "thesis_updated": date,
        }},
        "_excluded": [],
    })
    return path


# ── 测试 build_execution ──────────────────────────────────────────────────

def test_build_execution_entry_triggered(tmp_path):
    """entry_go=True → plan_entry_triggered=True"""
    from agents.postmarket_data_collector import build_execution
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date, entry_go=True)
    _make_intraday(tmp_path, "TEST", date)
    result = build_execution("TEST", date, base_dir=str(tmp_path))
    assert result["plan_entry_triggered"] is True


def test_build_execution_no_intraday(tmp_path):
    """无 intraday 文件 → plan_exit_triggered=None"""
    from agents.postmarket_data_collector import build_execution
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date)
    # 不创建 intraday 文件
    result = build_execution("TEST", date, base_dir=str(tmp_path))
    assert result["plan_exit_triggered"] is None


# ── 测试 build_signal_accuracy ─────────────────────────────────────────────

def test_signal_accuracy_consensus_correct(tmp_path):
    """master_consensus=buy + day_ret > 0 → master_consensus_correct=True"""
    from agents.postmarket_data_collector import build_signal_accuracy
    date = "2026-05-20"
    pm_path = _make_premarket(tmp_path, "TEST", date, scene="B")
    it_path = _make_intraday(tmp_path, "TEST", date)
    result = build_signal_accuracy(
        sym="TEST", date=date,
        day_ret_pct=1.5,
        base_dir=str(tmp_path),
    )
    assert result["master_consensus_correct"] is True  # consensus=buy, ret>0


def test_signal_accuracy_pred_scene_match(tmp_path):
    """pred_scene == actual_scene → pred_scene_correct=True"""
    from agents.postmarket_data_collector import build_signal_accuracy
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date, scene="B")
    _make_intraday(tmp_path, "TEST", date)
    result = build_signal_accuracy("TEST", date, day_ret_pct=0.5,
                                   base_dir=str(tmp_path))
    assert result["pred_scene_correct"] is True
    assert result["actual_scene"] == "B"


# ── 测试 generate_suggestions ──────────────────────────────────────────────

def test_generate_suggestions_lesson_always_present():
    """lesson_record 每日必有"""
    from agents.postmarket_data_collector import generate_suggestions
    suggs = generate_suggestions(
        sym="TEST", date="2026-05-20",
        execution={"followed_plan": "yes"},
        performance={"day_ret_pct": 0.5, "thesis_days": 5, "vs_stop_pct": 5.0},
        signal_accuracy={},
    )
    types = [s["type"] for s in suggs]
    assert "lesson_record" in types


def test_generate_suggestions_thesis_status_on_breach():
    """thesis_signal=breach 终盘 → thesis_status 建议"""
    from agents.postmarket_data_collector import generate_suggestions
    suggs = generate_suggestions(
        sym="TEST", date="2026-05-20",
        execution={"followed_plan": "no"},
        performance={"day_ret_pct": -3.5, "thesis_days": 5, "vs_stop_pct": -1.0},
        signal_accuracy={"thesis_signal_correct": True},
    )
    types = [s["type"] for s in suggs]
    assert "thesis_status" in types


# ── Task 2 测试：build_per_stock_summary / write_per_stock_summary ──────────

def test_build_per_stock_summary_schema(tmp_path):
    """build_per_stock_summary 返回所有顶层字段"""
    from agents.postmarket_summary import build_per_stock_summary
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date)
    _make_intraday(tmp_path, "TEST", date)
    _make_positions(tmp_path, "TEST", shares=10, cost=100.0)

    result = build_per_stock_summary("TEST", date, base_dir=str(tmp_path),
                                      day_ret_pct=1.5)
    required = {"date", "sym", "generated_at", "execution", "performance",
                "signal_accuracy", "snapshot_thesis_status",
                "learning_notes", "next_day"}
    assert required == set(result.keys()), f"缺少: {required - set(result.keys())}"
    assert result["sym"] == "TEST"
    assert isinstance(result["next_day"]["suggestions"], list)
    assert result["snapshot_thesis_status"] == "intact"


def test_write_per_stock_summary_creates_file(tmp_path):
    """write_per_stock_summary 生成 JSON 文件"""
    from agents.postmarket_summary import build_per_stock_summary, write_per_stock_summary
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date)
    _make_intraday(tmp_path, "TEST", date)
    _make_positions(tmp_path, "TEST")

    data = build_per_stock_summary("TEST", date, base_dir=str(tmp_path), day_ret_pct=1.5)
    path = write_per_stock_summary("TEST", date, data, base_dir=str(tmp_path))

    import pathlib
    assert pathlib.Path(path).exists()
    d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    assert d["sym"] == "TEST"


# ── Task 3 测试：suggestion_applier ──────────────────────────────────────────

def test_apply_suggestion_thesis_status(tmp_path):
    """apply_suggestion 写回 positions.json 的 thesis_status"""
    from agents.suggestion_applier import apply_suggestion
    pos_file = tmp_path / "config" / "positions.json"
    pos_file.parent.mkdir(parents=True)
    pos_file.write_text(json.dumps({
        "positions": {"NVDA": {"thesis_status": "intact", "cost": 100.0}},
        "_excluded": [],
    }), encoding="utf-8")

    suggestion = {
        "type": "thesis_status",
        "priority": "high",
        "description": "论点动摇",
        "proposed_value": {"new_status": "weakening"},
        "confirmed": True,
        "applied_at": None, "applied_to": None,
    }
    result = apply_suggestion("NVDA", suggestion, base_dir=str(tmp_path))

    pos_data = json.loads(pos_file.read_text(encoding="utf-8"))
    assert pos_data["positions"]["NVDA"]["thesis_status"] == "weakening"
    assert result["applied_to"]["old_value"]["thesis_status"] == "intact"


def test_apply_suggestion_lesson_record(tmp_path):
    """lesson_record 追加到 trading_lessons.json"""
    from agents.suggestion_applier import apply_suggestion
    lessons_file = tmp_path / "trading_lessons.json"
    lessons_file.write_text(json.dumps([]), encoding="utf-8")

    suggestion = {
        "type": "lesson_record",
        "proposed_value": {"lesson": "测试教训"},
        "confirmed": True, "applied_at": None, "applied_to": None,
    }
    apply_suggestion("TEST", suggestion, base_dir=str(tmp_path))

    data = json.loads(lessons_file.read_text(encoding="utf-8"))
    assert any("测试教训" in str(item) for item in data)


def test_apply_suggestion_display_only(tmp_path):
    """展示型建议（correlation_warning）applied_to 为 null，不写文件"""
    from agents.suggestion_applier import apply_suggestion
    suggestion = {
        "type": "correlation_warning",
        "proposed_value": {"pair": ["NVDA", "NBIL"], "corr": 0.91},
        "confirmed": True, "applied_at": None, "applied_to": None,
    }
    result = apply_suggestion("TEST", suggestion, base_dir=str(tmp_path))
    assert result["applied_to"] is None
