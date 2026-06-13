# tests/test_position_builder.py
import sys, os, json, tempfile, datetime

def _minimal_pos():
    """最小合法持仓记录"""
    return {
        "cost": 100.0, "shares": 10, "date": "2026-05-20",
        "note": "test", "tranche": "T1",
        "t1_cost": 100.0, "t1_shares": 10, "t1_date": "2026-05-20",
        "t2_cost": None, "t2_shares": 0,
        "t2_conditions": {"note": "", "underlying_price_floor": None,
                          "etf_price_floor": None, "vol_ratio_min": None},
        "t3_cost": None, "t3_shares": 0,
        "position_type": "thesis",
        "thesis": "测试论点",
        "thesis_status": "intact", "thesis_updated": "2026-05-20",
        "falsification_conditions": ["价格跌破$90"],
        "falsification_updated": "2026-05-20",
        "catalyst_type": None, "catalyst_deadline": None,
        "catalyst_persistence": None,
        "daily_action": "B", "action_updated": "2026-05-20",
        "t1_stop_snapshot": 90.0,
        "stop_note": "GTC已挂", "gtc_stop_placed": True, "gtc_stop_date": "2026-05-20",
        "macro_type": "成长型",
        "macro_sensitivity": {"rate_up": "负", "inflation": "中",
                               "recession": "负", "dollar_strong": "负",
                               "credit_tight": "负"},
        "target_pct": 10.0, "min_pct": 5.0, "max_pct": 15.0,
        "_pending": False, "_pending_fields": [],
    }

def test_validate_valid_position():
    from stock_team.core.position_builder import validate_position
    pos = _minimal_pos()
    errors = validate_position(pos)
    assert errors == [], f"Valid position should have no errors, got: {errors}"

def test_validate_missing_required():
    from stock_team.core.position_builder import validate_position
    pos = _minimal_pos()
    del pos["thesis"]
    del pos["falsification_conditions"]
    errors = validate_position(pos)
    assert any("thesis" in e for e in errors)
    assert any("falsification_conditions" in e for e in errors)

def test_validate_pending_position():
    from stock_team.core.position_builder import validate_position
    pos = _minimal_pos()
    pos["_pending"] = True
    pos["falsification_conditions"] = []
    pos["t1_stop_snapshot"] = None
    errors = validate_position(pos)
    # _pending=True 时允许必填字段为空，validate 只报 warning 不报 error
    assert errors == []

def test_write_position_new(tmp_path):
    """write_position 新建持仓写入 positions.json"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")

    from stock_team.core.position_builder import write_position
    pos = _minimal_pos()
    write_position("TEST", pos, pos_path=str(pos_file))

    data = json.loads(pos_file.read_text(encoding="utf-8"))
    assert "TEST" in data["positions"]
    assert data["positions"]["TEST"]["thesis"] == "测试论点"

def test_write_position_excluded_preserved(tmp_path):
    """write_position 不覆盖 _excluded 列表"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": ["BABA"]}), encoding="utf-8")

    from stock_team.core.position_builder import write_position
    write_position("TEST", _minimal_pos(), pos_path=str(pos_file))

    data = json.loads(pos_file.read_text(encoding="utf-8"))
    assert "BABA" in data["_excluded"]

def test_write_entry_audit(tmp_path):
    """write_entry_audit 生成 position_entry_{date}_{sym}.json"""
    from stock_team.core.position_builder import write_entry_audit
    date = "2026-05-20"
    audit = write_entry_audit(
        sym="TEST", date=date, mode="planning",
        fields_written=["cost", "thesis"],
        fields_pending=[],
        user_inputs={"thesis": "测试论点"},
        auto_filled={},
        find_dir=str(tmp_path),
    )
    # 文件应存在
    fname = f"position_entry_{date}_TEST.json"
    assert (tmp_path / fname).exists()
    d = json.loads((tmp_path / fname).read_text(encoding="utf-8"))
    assert d["mode"] == "planning"
    assert d["pending_count"] == 0

def test_quick_mode_creates_pending_position(tmp_path):
    """quick_mode 写入 positions.json，_pending=True，缺失字段在 _pending_fields"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")

    from stock_team.core.position_builder import quick_mode
    result = quick_mode(
        sym="TEST",
        cost=100.0, shares=10, date="2026-05-20",
        position_type="thesis",
        thesis="AI算力垄断",
        pos_path=str(pos_file),
        find_dir=str(tmp_path),
    )

    data = json.loads(pos_file.read_text(encoding="utf-8"))
    pos = data["positions"]["TEST"]
    assert pos["_pending"] is True
    assert "falsification_conditions" in pos["_pending_fields"]
    assert pos["cost"] == 100.0
    assert pos["thesis"] == "AI算力垄断"
    assert result["mode"] == "quick"

def test_quick_mode_position_type_enum(tmp_path):
    """quick_mode 拒绝无效的 position_type，且不污染真实 positions.json"""
    import pytest
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="position_type"):
        from stock_team.core.position_builder import quick_mode
        quick_mode("X", 100.0, 1, "2026-05-20", "invalid_type", "test",
                   pos_path=str(pos_file), find_dir=str(tmp_path))

def test_planning_mode_no_memo(tmp_path):
    """无 strategic_memo 时，planning_mode 返回引导问题列表"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")

    from stock_team.core.position_builder import planning_mode
    result = planning_mode(
        sym="NVDA", memo_dir=str(tmp_path),  # 无 memo 文件
        pos_path=str(pos_file), find_dir=str(tmp_path),
    )
    assert result["source"] == "manual"
    assert "prefilled" in result
    # 无 memo 时 prefilled 为空
    assert result["prefilled"].get("thesis") is None

def test_planning_mode_with_memo(tmp_path):
    """有 strategic_memo 时，prefilled 包含 thesis 和 macro_sensitivity"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")

    # 写入 mock strategic_memo
    memo = {
        "sym": "NVDA", "analysis_date": "2026-05-20",
        "synthesis": {"key_condition": "Blackwell出货节奏", "strategic_stance": "hold"},
        "support_and_risk": {
            "macro_fit": {"assessment": "favorable", "active_headwinds": [], "headwind_count": 0},
            "main_risks": ["竞争对手AMD追赶"],
        },
        "judgment": {"thesis_lifecycle_stage": {"stage": "mid"}},
        "outlook": {"valid_until": "2026-06-30"},
    }
    (tmp_path / "strategic_memo_NVDA.json").write_text(
        json.dumps(memo, ensure_ascii=False), encoding="utf-8")

    from stock_team.core.position_builder import planning_mode
    result = planning_mode(
        sym="NVDA", memo_dir=str(tmp_path),
        pos_path=str(pos_file), find_dir=str(tmp_path),
    )
    assert result["source"] == "strategic_memo"
    assert result["prefilled"]["thesis"] == "Blackwell出货节奏"
    assert result["prefilled"]["macro_sensitivity"]["rate_up"] is not None

def test_planning_mode_write(tmp_path):
    """planning_mode write=True 时将记录写入 positions.json"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")

    from stock_team.core.position_builder import planning_mode
    user_answers = {
        "thesis": "AI算力垄断",
        "falsification_conditions": ["跌破$200且跑输SOXX"],
        "t1_stop_snapshot": 195.0,
        "gtc_stop_placed": True,
        "position_type": "thesis",
        "cost": 220.0, "shares": 10, "date": "2026-05-20",
    }
    planning_mode(
        sym="NVDA", memo_dir=str(tmp_path),
        pos_path=str(pos_file), find_dir=str(tmp_path),
        write=True, user_answers=user_answers,
    )
    data = json.loads(pos_file.read_text(encoding="utf-8"))
    assert "NVDA" in data["positions"]
    pos = data["positions"]["NVDA"]
    assert pos["_pending"] is False
    assert pos["falsification_conditions"] == ["跌破$200且跑输SOXX"]

def test_catch_up_mode_fills_pending(tmp_path):
    """catch_up_mode 填写 _pending=True 的持仓字段"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")

    from stock_team.core.position_builder import quick_mode, catch_up_mode
    quick_mode("TEST", 100.0, 10, "2026-05-20", "thesis", "AI论点",
               pos_path=str(pos_file), find_dir=str(tmp_path))

    catch_up_mode(
        sym="TEST",
        updates={
            "falsification_conditions": ["跌破$90且跑输SPY"],
            "t1_stop_snapshot": 88.0,
            "gtc_stop_placed": True,
        },
        pos_path=str(pos_file), find_dir=str(tmp_path),
    )

    data = json.loads(pos_file.read_text(encoding="utf-8"))
    pos = data["positions"]["TEST"]
    assert pos["falsification_conditions"] == ["跌破$90且跑输SPY"]
    assert pos["t1_stop_snapshot"] == 88.0
    assert "t1_stop_snapshot" not in pos["_pending_fields"]

def test_catch_up_sym_not_in_positions(tmp_path):
    """catch_up_mode 对不存在的 sym 抛 KeyError"""
    import pytest
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}), encoding="utf-8")
    from stock_team.core.position_builder import catch_up_mode
    with pytest.raises(KeyError):
        catch_up_mode("NONEXISTENT", {"thesis": "x"},
                      pos_path=str(pos_file), find_dir=str(tmp_path))

def test_catch_up_clears_pending_when_complete(tmp_path):
    """所有 _pending_fields 都填完后，_pending 变为 False"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))

    from stock_team.core.position_builder import quick_mode, catch_up_mode, PENDING_FIELDS_DEFAULT
    quick_mode("TEST", 100.0, 10, "2026-05-20", "thesis", "AI论点",
               pos_path=str(pos_file), find_dir=str(tmp_path))

    updates = {f: "dummy" for f in PENDING_FIELDS_DEFAULT}
    updates["falsification_conditions"] = ["条件1"]
    updates["t1_stop_snapshot"] = 88.0
    updates["gtc_stop_placed"] = True
    updates["t2_conditions"] = {"note": "test"}
    updates["macro_sensitivity"] = {"rate_up": "负", "inflation": "中",
                                    "recession": "负", "dollar_strong": "负",
                                    "credit_tight": "负"}

    catch_up_mode("TEST", updates, pos_path=str(pos_file), find_dir=str(tmp_path))

    data = json.loads(pos_file.read_text(encoding="utf-8"))
    pos = data["positions"]["TEST"]
    assert pos["_pending"] is False
    assert pos["_pending_fields"] == []

def test_translator_detects_buy_intent():
    """translator 识别'买了NVDA'等买入意图（只测正则匹配，不执行子进程）"""
    from stock_team.archive.deprecated_data.translator import _COMPILED
    text = "刚买了NVDA"
    matched = [intent for pat, intent, fn in _COMPILED if pat.search(text)]
    assert "buy_quick" in matched, f"buy_quick 未匹配，命中: {matched}"

def test_translator_detects_new_position_intent():
    """translator 识别'建仓NVDA'等新建仓意图（只测正则匹配）"""
    from stock_team.archive.deprecated_data.translator import _COMPILED
    text = "新建仓位NVDA"
    matched = [intent for pat, intent, fn in _COMPILED if pat.search(text)]
    assert "new_position" in matched, f"new_position 未匹配，命中: {matched}"
