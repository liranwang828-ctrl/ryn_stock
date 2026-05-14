import sys, os, math
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from agents.daily_plan import calc_stop

def test_calc_stop_basic():
    stop = calc_stop(vwap=177.3, atr14=9.5, seed=42)
    base_stop = 177.3 - 9.5 * 0.3  # = 174.45
    assert stop < base_stop, "actual_stop 应低于 base_stop"
    assert stop > base_stop - base_stop * 0.01, "噪声最大0.8%，不应偏移过大"

def test_calc_stop_avoids_integer():
    stop = calc_stop(vwap=174.75, atr14=1.5, seed=0)
    assert stop < 174.0 - 0.1 - 0.3 + 0.01, "整数位检测：应额外偏移-0.3"

def test_calc_stop_no_integer_adjustment():
    stop = calc_stop(vwap=181.0, atr14=12.0, seed=99)
    base_stop = 181.0 - 12.0 * 0.3  # = 177.4
    assert stop > 175.5, "无额外整数偏移，stop不应过低"
    assert stop < base_stop, "仍有噪声，stop应低于base_stop"

def test_infer_scene_A():
    from agents.daily_plan import infer_scene
    scene = infer_scene(vol_ratio=1.5, above_prev_high=True, rs=3.2, macd_positive=True,
        range_pct=2.0, near_vwap=False, high_pullback_pct=1.0, below_vwap=False,
        rebound_pct=1.5, etf_up=False, rs_vs_sector=4.0)
    assert scene == "A"

def test_infer_scene_B():
    from agents.daily_plan import infer_scene
    scene = infer_scene(vol_ratio=0.75, above_prev_high=False, rs=1.0, macd_positive=True,
        range_pct=1.8, near_vwap=True, high_pullback_pct=1.5, below_vwap=False,
        rebound_pct=0.5, etf_up=False, rs_vs_sector=1.0)
    assert scene == "B"

def test_infer_scene_C():
    from agents.daily_plan import infer_scene
    scene = infer_scene(vol_ratio=0.6, above_prev_high=False, rs=0.5, macd_positive=False,
        range_pct=1.2, near_vwap=False, high_pullback_pct=1.0, below_vwap=False,
        rebound_pct=0.5, etf_up=False, rs_vs_sector=0.5)
    assert scene == "C"

def test_infer_scene_D():
    from agents.daily_plan import infer_scene
    scene = infer_scene(vol_ratio=1.0, above_prev_high=False, rs=-1.0, macd_positive=False,
        range_pct=3.5, near_vwap=False, high_pullback_pct=3.5, below_vwap=True,
        rebound_pct=0.0, etf_up=False, rs_vs_sector=-1.0)
    assert scene == "D"

def test_infer_scene_F():
    from agents.daily_plan import infer_scene
    scene = infer_scene(vol_ratio=1.8, above_prev_high=False, rs=-5.0, macd_positive=False,
        range_pct=4.0, near_vwap=False, high_pullback_pct=4.0, below_vwap=True,
        rebound_pct=-2.0, etf_up=False, rs_vs_sector=-4.0)
    assert scene == "F"

def test_infer_scene_H():
    from agents.daily_plan import infer_scene
    scene = infer_scene(vol_ratio=1.4, above_prev_high=False, rs=5.0, macd_positive=True,
        range_pct=2.0, near_vwap=False, high_pullback_pct=0.5, below_vwap=False,
        rebound_pct=2.0, etf_up=True, rs_vs_sector=4.0)
    assert scene == "H"

def test_build_stock_plan_basic_fields():
    from agents.daily_plan import _build_stock_plan
    pre_data = {"symbol":"MRVL","pred_scene":"B","top_headline":"AMD持股★★★",
                "catalyst_strength":3,"vwap_current":177.3,"atr":9.5,"pre_price":178.0}
    plan = _build_stock_plan(pre_data, date_str="2026-05-14", seed=42)
    required = ["predicted_scene","catalyst","catalyst_strength","watch_zone_lo","watch_zone_hi",
                "t1_entry_hint","t1_stop","t1_target1","t1_target2","t2_condition_a",
                "t2_condition_b","t2_stop_mode","plan_status","actual_scene","actual_vwap",
                "entered","added_at"]
    for field in required:
        assert field in plan, f"缺少字段：{field}"

def test_build_stock_plan_stop_is_below_vwap():
    from agents.daily_plan import _build_stock_plan
    pre_data = {"symbol":"MRVL","pred_scene":"B","top_headline":"x","catalyst_strength":2,
                "vwap_current":177.3,"atr":9.5,"pre_price":178.0}
    plan = _build_stock_plan(pre_data, date_str="2026-05-14", seed=42)
    assert plan["t1_stop"] < 177.3

def test_build_stock_plan_watch_zone():
    from agents.daily_plan import _build_stock_plan
    pre_data = {"symbol":"MRVL","pred_scene":"B","top_headline":"x","catalyst_strength":2,
                "vwap_current":177.3,"atr":9.5,"pre_price":178.0}
    plan = _build_stock_plan(pre_data, date_str="2026-05-14", seed=42)
    assert abs(plan["watch_zone_lo"] - 177.3*0.99) < 0.01
    assert abs(plan["watch_zone_hi"] - 177.3*1.01) < 0.01

def test_build_stock_plan_targets():
    from agents.daily_plan import _build_stock_plan
    pre_data = {"symbol":"MRVL","pred_scene":"B","top_headline":"x","catalyst_strength":2,
                "vwap_current":177.3,"atr":9.5,"pre_price":178.0}
    plan = _build_stock_plan(pre_data, date_str="2026-05-14", seed=42)
    assert plan["t1_target1"] > plan["watch_zone_hi"]
    assert plan["t1_target2"] > plan["t1_target1"]

def test_build_stock_plan_defaults():
    from agents.daily_plan import _build_stock_plan
    pre_data = {"symbol":"MRVL","pred_scene":"A","top_headline":"x","catalyst_strength":3,
                "vwap_current":100.0,"atr":5.0,"pre_price":102.0}
    plan = _build_stock_plan(pre_data, date_str="2026-05-14", seed=1)
    assert plan["actual_scene"] is None
    assert plan["actual_vwap"] is None
    assert plan["entered"] is False
    assert plan["plan_status"] == "active"


# ── Task 4: generate_plan ────────────────────────────────────────────────────
import json, tempfile, shutil
from unittest.mock import patch
from agents.daily_plan import generate_plan, get_all, get_plan

FAKE_PREMARKET = {
    "date": "2026-05-14",
    "generated_at": "2026-05-14T09:20:00Z",
    "stocks": {
        "MRVL": {"symbol":"MRVL","pred_scene":"B","top_headline":"AMD持股★★★",
                 "catalyst_strength":3,"vwap_current":177.3,"atr":9.5,"pre_price":178.0},
        "AAOI": {"symbol":"AAOI","pred_scene":"A","top_headline":"400G订单",
                 "catalyst_strength":3,"vwap_current":195.0,"atr":12.0,"pre_price":196.0},
    }
}

def _make_temp_base(premarket_data=None):
    tmpdir = tempfile.mkdtemp()
    date_str = "2026-05-14"
    pre_path = os.path.join(tmpdir, f"premarket_analysis_{date_str}.json")
    with open(pre_path, "w") as f:
        json.dump(premarket_data or FAKE_PREMARKET, f)
    return tmpdir, date_str

def test_generate_plan_creates_json():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL","AAOI"], date_str=date_str, seed=42)
        plan_path = os.path.join(tmpdir, f"daily_plan_{date_str}.json")
        assert os.path.exists(plan_path)
        with open(plan_path) as f:
            data = json.load(f)
        assert data["date"] == date_str
        assert "MRVL" in data["stocks"] and "AAOI" in data["stocks"]
    finally:
        shutil.rmtree(tmpdir)

def test_generate_plan_filters_by_symbols():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
        with open(os.path.join(tmpdir, f"daily_plan_{date_str}.json")) as f:
            data = json.load(f)
        assert "MRVL" in data["stocks"] and "AAOI" not in data["stocks"]
    finally:
        shutil.rmtree(tmpdir)

def test_generate_plan_all_symbols():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(None, date_str=date_str, seed=42)
        with open(os.path.join(tmpdir, f"daily_plan_{date_str}.json")) as f:
            data = json.load(f)
        assert "MRVL" in data["stocks"] and "AAOI" in data["stocks"]
    finally:
        shutil.rmtree(tmpdir)

def test_generate_plan_raises_if_no_premarket():
    import pytest
    tmpdir = tempfile.mkdtemp()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            with pytest.raises(FileNotFoundError):
                generate_plan(["MRVL"], date_str="2099-01-01")
    finally:
        shutil.rmtree(tmpdir)


# ── Task 5: get_plan / get_all ───────────────────────────────────────────────
def test_get_plan_returns_stock():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            plan = get_plan("MRVL", date_str=date_str)
        assert plan["predicted_scene"] == "B" and "t1_stop" in plan
    finally:
        shutil.rmtree(tmpdir)

def test_get_plan_missing_symbol_returns_none():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            result = get_plan("XXXX", date_str=date_str)
        assert result is None
    finally:
        shutil.rmtree(tmpdir)

def test_get_all_returns_all_stocks():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(None, date_str=date_str, seed=42)
            all_plans = get_all(date_str=date_str)
        assert "MRVL" in all_plans and "AAOI" in all_plans
    finally:
        shutil.rmtree(tmpdir)

def test_get_all_empty_if_no_file():
    tmpdir = tempfile.mkdtemp()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            all_plans = get_all(date_str="2099-01-01")
        assert all_plans == {}
    finally:
        shutil.rmtree(tmpdir)


# ── Task 6: add_symbol ───────────────────────────────────────────────────────
from agents.daily_plan import add_symbol

def test_add_symbol_writes_to_plan():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            add_symbol("AAOI", date_str=date_str, seed=99)
            all_plans = get_all(date_str=date_str)
        assert "AAOI" in all_plans and "MRVL" in all_plans
    finally:
        shutil.rmtree(tmpdir)

def test_add_symbol_not_in_premarket_raises():
    import pytest
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            with pytest.raises(KeyError):
                add_symbol("NONEXISTENT", date_str=date_str)
    finally:
        shutil.rmtree(tmpdir)

def test_add_symbol_idempotent():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            add_symbol("AAOI", date_str=date_str, seed=1)
            add_symbol("AAOI", date_str=date_str, seed=2)
            all_plans = get_all(date_str=date_str)
        assert "AAOI" in all_plans
    finally:
        shutil.rmtree(tmpdir)


# ── Task 7: update_scene ─────────────────────────────────────────────────────
from agents.daily_plan import update_scene

def test_update_scene_sets_actual_scene():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            update_scene("MRVL", actual_scene="D", actual_vwap=175.5, date_str=date_str)
            plan = get_plan("MRVL", date_str=date_str)
        assert plan["actual_scene"] == "D" and plan["actual_vwap"] == 175.5
    finally:
        shutil.rmtree(tmpdir)

def test_update_scene_auto_infer_when_no_scene():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            update_scene("MRVL", actual_scene=None, actual_vwap=170.0, date_str=date_str,
                infer_kwargs={"vol_ratio":1.8,"above_prev_high":False,"rs":-5.0,
                    "macd_positive":False,"range_pct":4.0,"near_vwap":False,
                    "high_pullback_pct":4.0,"below_vwap":True,"rebound_pct":-2.0,
                    "etf_up":False,"rs_vs_sector":-4.0})
            plan = get_plan("MRVL", date_str=date_str)
        assert plan["actual_scene"] == "F"
    finally:
        shutil.rmtree(tmpdir)

def test_update_scene_missing_symbol_raises():
    import pytest
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            with pytest.raises(KeyError):
                update_scene("XXXX", actual_scene="B", date_str=date_str)
    finally:
        shutil.rmtree(tmpdir)

def test_update_scene_updates_watch_zone_with_actual_vwap():
    tmpdir, date_str = _make_temp_base()
    try:
        with patch("agents.daily_plan.BASE", tmpdir):
            generate_plan(["MRVL"], date_str=date_str, seed=42)
            update_scene("MRVL", actual_scene="B", actual_vwap=180.0, date_str=date_str)
            plan = get_plan("MRVL", date_str=date_str)
        assert abs(plan["watch_zone_lo"] - 180.0*0.99) < 0.01
        assert abs(plan["watch_zone_hi"] - 180.0*1.01) < 0.01
    finally:
        shutil.rmtree(tmpdir)
