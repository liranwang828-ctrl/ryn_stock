# tests/test_intraday_snapshot.py
import sys, os, json
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))


def _nodes(entry_base=100.0, hard_stop=95.0, target=110.0,
           flex_add=93.0, flex_reduce=108.0):
    return {
        "entry_base": entry_base, "hard_stop": hard_stop,
        "target": target, "flex_add": flex_add, "flex_reduce": flex_reduce,
    }


def test_plan_vs_now_dist_formulas():
    """距离字段分母统一用 price"""
    from agents.intraday_snapshot import compute_dist_fields
    price = 102.0
    nodes = _nodes(entry_base=100.0, hard_stop=95.0, target=110.0,
                   flex_add=93.0, flex_reduce=108.0)
    d = compute_dist_fields(price, nodes)
    assert abs(d["dist_to_entry_pct"]       - (102.0 - 100.0) / 102.0 * 100) < 0.01
    assert abs(d["dist_to_stop_pct"]        - (102.0 -  95.0) / 102.0 * 100) < 0.01
    assert abs(d["dist_to_target_pct"]      - (110.0 - 102.0) / 102.0 * 100) < 0.01
    assert abs(d["dist_to_flex_add_pct"]    - (102.0 -  93.0) / 102.0 * 100) < 0.01
    assert abs(d["dist_to_flex_reduce_pct"] - (108.0 - 102.0) / 102.0 * 100) < 0.01


def test_plan_vs_now_null_when_no_nodes():
    """节点为 None 时距离字段为 None"""
    from agents.intraday_snapshot import compute_dist_fields
    d = compute_dist_fields(100.0, {"entry_base": None, "hard_stop": None,
                                    "target": None, "flex_add": None, "flex_reduce": None})
    assert d["dist_to_entry_pct"] is None
    assert d["dist_to_stop_pct"] is None


def test_thesis_signal_breach_on_stop():
    """price ≤ hard_stop → breach"""
    from agents.intraday_snapshot import compute_thesis_signal
    sig = compute_thesis_signal(
        price=94.0, hard_stop=95.0, dist_to_stop_pct=-1.1,
        thesis_status="intact", falsification_count=0,
    )
    assert sig == "breach"


def test_thesis_signal_warning_weakening():
    """weakening + 止损尚远（dist > 3%）→ warning"""
    from agents.intraday_snapshot import compute_thesis_signal
    sig = compute_thesis_signal(
        price=99.0, hard_stop=95.0, dist_to_stop_pct=4.0,   # dist=4% > 3%，不触发规则3
        thesis_status="weakening", falsification_count=0,
    )
    assert sig == "warning"


def test_thesis_signal_breach_weakening_near_stop():
    """weakening + 接近止损（dist < 3%）→ breach（spec 规则 3）"""
    from agents.intraday_snapshot import compute_thesis_signal
    sig = compute_thesis_signal(
        price=96.5, hard_stop=95.0, dist_to_stop_pct=1.6,   # dist=1.6% < 3%，触发规则3
        thesis_status="weakening", falsification_count=0,
    )
    assert sig == "breach"


def test_thesis_signal_intact_normal():
    """正常情况 → intact"""
    from agents.intraday_snapshot import compute_thesis_signal
    sig = compute_thesis_signal(
        price=102.0, hard_stop=95.0, dist_to_stop_pct=6.9,
        thesis_status="intact", falsification_count=0,
    )
    assert sig == "intact"


def test_entry_go_expired_after_10_30():
    """session_min ≥ 60 → expired（优先于其他规则）"""
    from agents.intraday_snapshot import compute_entry_go_status
    status = compute_entry_go_status(
        session_min=65,
        post_open_calibrated=True,
        entry_go=False,
    )
    assert status == "expired"


def test_entry_go_go():
    """entry_go=True → go"""
    from agents.intraday_snapshot import compute_entry_go_status
    status = compute_entry_go_status(
        session_min=35,
        post_open_calibrated=True,
        entry_go=True,
    )
    assert status == "go"


def test_entry_go_pending_not_calibrated():
    """post_open_calibrated=False → pending"""
    from agents.intraday_snapshot import compute_entry_go_status
    status = compute_entry_go_status(
        session_min=20,
        post_open_calibrated=False,
        entry_go=None,
    )
    assert status == "pending"


def test_get_effective_nodes_prefers_adj():
    """post_open_adj 值优先于原始值"""
    from agents.intraday_snapshot import get_effective_nodes
    summary = {
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0},
        "exit": {"hard_stop": 94.0, "target_price": 109.0,
                 "flex_add_level": 92.0, "flex_reduce_level": 107.0},
        "post_open_adj": {
            "entry_base_adj": 101.0,
            "hard_stop_adj": None,
            "target_adj": None,
            "flex_add_adj": 91.0,
            "flex_reduce_adj": None,
        },
    }
    nodes = get_effective_nodes(summary)
    assert nodes["entry_base"] == 101.0
    assert nodes["hard_stop"]  == 94.0
    assert nodes["flex_add"]   == 91.0


def test_get_effective_nodes_no_adj():
    """post_open_adj=None → 全用原始值"""
    from agents.intraday_snapshot import get_effective_nodes
    summary = {
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0},
        "exit": {"hard_stop": 95.0, "target_price": 110.0,
                 "flex_add_level": 93.0, "flex_reduce_level": 108.0},
        "post_open_adj": None,
    }
    nodes = get_effective_nodes(summary)
    assert nodes["entry_base"] == 100.0
    assert nodes["hard_stop"]  == 95.0


def test_build_plan_vs_now_fields():
    """build_plan_vs_now 返回所有必要字段"""
    from agents.intraday_snapshot import build_plan_vs_now
    summary = {
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0,
                  "entry_conditions": ["A", "B"], "cancel_conditions": []},
        "exit": {"hard_stop": 95.0, "target_price": 110.0,
                 "flex_add_level": 93.0, "flex_reduce_level": 108.0},
        "thesis": {"status": "intact", "today_falsification": []},
        "post_open_adj": None,
    }
    pvn = build_plan_vs_now(
        price=102.0, summary=summary,
        session_min=20, post_open_calibrated=False,
    )
    required = {"dist_to_entry_pct", "dist_to_stop_pct", "dist_to_target_pct",
                "dist_to_flex_add_pct", "dist_to_flex_reduce_pct",
                "entry_conditions_met", "entry_conditions_total",
                "scene_match", "thesis_signal", "entry_go_status"}
    assert required == set(pvn.keys()), f"缺少字段: {required - set(pvn.keys())}"
    assert pvn["thesis_signal"] == "intact"
    assert pvn["entry_go_status"] == "pending"


def test_detect_event_hard_stop_breach():
    """price ≤ hard_stop → hard_stop_breach"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=94.0, hard_stop=95.0,
        thesis_signal="breach", prev_thesis_signal="intact",
        gate_status="未通过", prev_gate_status="通过",
        master_consensus="no_buy", prev_master_consensus="neutral",
        session_min=40, entry_go_status="go", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event == "hard_stop_breach"


def test_detect_event_entry_go():
    """entry_go_status 从 pending 变 go → entry_go"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=102.0, hard_stop=95.0,
        thesis_signal="intact", prev_thesis_signal="intact",
        gate_status="通过", prev_gate_status="通过",
        master_consensus="buy", prev_master_consensus="buy",
        session_min=30, entry_go_status="go", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event == "entry_go"


def test_detect_event_thesis_breach():
    """thesis_signal 从 intact 变 breach → thesis_breach"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=100.0, hard_stop=95.0,
        thesis_signal="breach", prev_thesis_signal="intact",
        gate_status="通过", prev_gate_status="通过",
        master_consensus="neutral", prev_master_consensus="neutral",
        session_min=50, entry_go_status="pending", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event == "thesis_breach"


def test_detect_event_gate_flip():
    """gate_status 翻转 → gate_flip"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=100.0, hard_stop=95.0,
        thesis_signal="intact", prev_thesis_signal="intact",
        gate_status="通过", prev_gate_status="未通过",
        master_consensus="neutral", prev_master_consensus="neutral",
        session_min=50, entry_go_status="pending", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event == "gate_flip"


def test_detect_event_no_event():
    """无变化 → None"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=100.0, hard_stop=95.0,
        thesis_signal="intact", prev_thesis_signal="intact",
        gate_status="通过", prev_gate_status="通过",
        master_consensus="neutral", prev_master_consensus="neutral",
        session_min=50, entry_go_status="pending", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event is None


def test_append_and_read_snapshot(tmp_path):
    """append_snapshot 写 JSONL，read_latest_snapshot 读最新一条"""
    from agents.intraday_snapshot import append_snapshot, read_latest_snapshot
    date = "2026-05-20"
    r1 = {"ts": "09:30:00", "meta": {"sym": "TEST", "date": date, "session_min": 0,
          "llm_triggered": False, "llm_trigger": None, "cooldown_until": None,
          "post_open_calibrated": False},
          "price_now": {"price": 100.0}, "plan_vs_now": {},
          "node_snapshot": {}, "action_now": None}
    r2 = {**r1, "ts": "09:32:00", "price_now": {"price": 101.0}}

    append_snapshot("TEST", date, r1, find_dir=str(tmp_path))
    append_snapshot("TEST", date, r2, find_dir=str(tmp_path))

    latest = read_latest_snapshot("TEST", date, find_dir=str(tmp_path))
    assert latest["price_now"]["price"] == 101.0
    assert latest["ts"] == "09:32:00"


def test_update_poll_state_merges_new_keys(tmp_path):
    """update_poll_state 只追加新字段，不覆盖已有字段"""
    from agents.intraday_snapshot import update_poll_state
    state_file = tmp_path / "poll_state_2026-05-20.json"
    state_file.write_text(json.dumps({
        "date": "2026-05-20",
        "symbols": {"TEST": {"last_price": 100.0, "gate_status": "未通过"}}
    }), encoding="utf-8")

    plan_vs_now = {
        "entry_conditions_met": 1, "entry_conditions_total": 3,
        "dist_to_stop_pct": 5.2, "dist_to_target_pct": 7.8,
        "thesis_signal": "intact", "entry_go_status": "pending",
    }
    update_poll_state("TEST", plan_vs_now, last_action_now=None,
                      last_event=None, last_event_at=None,
                      cooldown_until=None, master_consensus="neutral",
                      poll_state_path=str(state_file))

    state = json.loads(state_file.read_text(encoding="utf-8"))
    sym = state["symbols"]["TEST"]
    assert sym["last_price"] == 100.0           # 原有字段未被覆盖
    assert "plan_vs_now" in sym
    assert sym["plan_vs_now"]["thesis_signal"] == "intact"
    assert "last_action_now" in sym
    assert "master_consensus" in sym
    assert sym["master_consensus"] == "neutral"


def test_write_snapshot_entry_creates_file(tmp_path):
    """write_snapshot_entry 追加 JSONL 文件且结构完整"""
    from agents.intraday_snapshot import write_snapshot_entry
    import pathlib
    state_file = tmp_path / "poll_state_2026-05-20.json"
    state_file.write_text(json.dumps({"date": "2026-05-20", "symbols": {}}))

    summary = {
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0,
                  "entry_conditions": ["A"], "cancel_conditions": []},
        "exit": {"hard_stop": 95.0, "target_price": 110.0,
                 "flex_add_level": 93.0, "flex_reduce_level": 108.0},
        "thesis": {"status": "intact", "today_falsification": []},
        "post_open_adj": None,
    }

    write_snapshot_entry(
        sym="TEST", date="2026-05-20",
        price_now={
            "price": 102.0, "chg_pct": 0.5, "vwap_dist_pct": 0.2,
            "rs_vs_spy": 1.0, "rs_vs_sector": 0.5, "rsi14_5m": 55.0,
            "vol_ratio": 1.1, "gate_status": "通过", "gate_pass": ["RS"],
            "gate_block": [], "master_avg": 6.0, "master_consensus": "neutral",
        },
        premarket_summary=summary,
        session_min=20,
        post_open_calibrated=False,
        prev_poll_state={},
        vix_spike=False,
        find_dir=str(tmp_path),
        poll_state_path=str(state_file),
    )

    files = list(pathlib.Path(tmp_path).glob("intraday_snapshot_2026-05-20_TEST.jsonl"))
    assert files, "JSONL 文件未生成"
    record = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert set(record.keys()) == {"ts", "meta", "price_now", "plan_vs_now",
                                  "node_snapshot", "action_now"}
    assert record["action_now"] is None
    assert record["meta"]["sym"] == "TEST"
