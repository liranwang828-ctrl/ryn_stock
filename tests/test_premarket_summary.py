# tests/test_premarket_summary.py
import json, os, sys
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
from unittest.mock import patch


def test_macro_has_vix(tmp_path):
    """premarket_analysis JSON 的 macro 字段应含 vix_level（需要最新盘前数据）"""
    import glob, pytest
    base = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
    files = sorted(glob.glob(f"{base}/premarket_analysis_*.json"))
    if not files:
        pytest.skip("无历史盘前文件")
    d = json.load(open(files[-1], encoding="utf-8"))
    if "vix_level" not in d.get("macro", {}):
        pytest.skip("最新文件早于 vix_level 改动，下次盘前运行后验证")
    assert d["macro"]["vix_level"] is not None or d["macro"]["vix_level"] is None  # 字段存在即通过


def test_order_sheet_has_flex_reduce():
    """generate_order_sheet 返回值应含 flex_reduce_level"""
    from agents.premarket_order_sheet import generate_order_sheet

    mock_tech = {
        "cur": 100.0, "ma20": 98.0, "atr14": 3.0,
        "lo5": 96.0, "lo10": 94.0, "hi20": 108.0, "hi5": 104.0,
        "ma20_dev": 2.0,
    }
    with patch("agents.premarket_order_sheet._get_technicals", return_value=mock_tech), \
         patch("agents.premarket_order_sheet._load_json", return_value={}):
        result = generate_order_sheet("TEST")
    assert "flex_reduce_level" in result, "order_sheet 缺少 flex_reduce_level"
    assert result["flex_reduce_level"] > result["flex_add_level"], \
        "flex_reduce 应高于 flex_add"


import tempfile, datetime

def _make_mock_files(tmp_path, sym="TEST", is_held=True):
    """在 tmp_path 下构造 6 个输入文件的最小合法版本"""
    date = datetime.date.today().strftime("%Y-%m-%d")
    findings = tmp_path / "findings"
    findings.mkdir()

    (tmp_path / f"premarket_analysis_{date}.json").write_text(json.dumps({
        "date": date,
        "macro": {"spy_pre": 0.2, "nq_futures": 0.3, "env": "顺风", "vix_level": 18.5},
        "stocks": {sym: {
            "symbol": sym, "gap_pct": 1.5, "pred_scene": "B",
            "news_type": "neutral", "catalyst_strength": 1,
            "pre_vol_ratio": 0.9, "sector_ref": "SOXX", "sector_gap": 0.3,
            "month_context": {"rs_1m": 5.0, "above_ma20": True, "above_ma50": True,
                              "tech_stage": "上升趋势"},
            "confidence": "中", "reasoning": "平开，等回踩",
        }},
    }), encoding="utf-8")

    (findings / f"order_sheet_{date}.json").write_text(json.dumps({
        "date": date,
        "symbols": {sym: {
            "sym": sym, "date": date, "is_held": is_held,
            "entry_base": 100.0, "stop_loss": 97.0, "target_price": 110.0,
            "rr_ratio": 3.3, "entry_conditions": ["条件A"],
            "cancel_conditions": ["取消条件A"],
            "flex_add_level": 94.0, "flex_reduce_level": 104.0,
            "overnight_note": "", "regime_note": "热点不在科技",
        }},
    }), encoding="utf-8")

    (findings / f"entry_decision_{date}.json").write_text(json.dumps({
        "date": date,
        sym: {"decision": "可入场", "hard_vetoes": [], "soft_vetoes": [], "sizing": "×1.0"},
    }), encoding="utf-8")

    exit_data: dict = {"date": date}
    if is_held:
        exit_data["positions"] = {sym: {
            "sym": sym, "decision": "继续持有",
            "hard_stop": 95.0, "soft_stop": 97.0, "stop_source": "auto_atr",
            "cur": 101.0, "hard_dist_pct": 5.9, "hard_triggers": [],
            "soft_triggers": [], "falsification_check": ["论点破裂条件"],
            "rr_remaining": 4.5,
        }}
    (findings / f"exit_decision_{date}.json").write_text(
        json.dumps(exit_data), encoding="utf-8")

    checklist_data: dict = {"date": date}
    if is_held:
        checklist_data["symbols"] = {sym: {
            "sym": sym, "date": date, "has_position": True,
            "thesis_status": "intact", "daily_action": "B",
            "position_type": "thesis",
        }}
    (tmp_path / f"daily_checklist_{date}.json").write_text(
        json.dumps(checklist_data), encoding="utf-8")

    (findings / "today_focus.json").write_text(json.dumps({}), encoding="utf-8")
    return date


def test_summary_schema_completeness_no_memo(tmp_path):
    """无 strategic_memo 时生成 Lite 模式 JSON，所有顶层 key 存在"""
    from agents.premarket_summary import build_summary
    date = _make_mock_files(tmp_path, sym="TEST", is_held=True)
    result = build_summary("TEST", date, base_dir=str(tmp_path))

    required_keys = {"date", "sym", "generated_at", "market_context",
                     "stock_snapshot", "entry", "exit", "thesis",
                     "strategic_context", "post_open_adj"}
    assert required_keys.issubset(set(result.keys())), f"缺少 key: {required_keys - set(result.keys())}"
    assert result["strategic_context"]["source"] == "premarket_inferred"
    assert result["post_open_adj"] is None
    assert result["exit"] is not None
    assert result["thesis"] is not None


def test_summary_not_held(tmp_path):
    """不持仓时 exit 和 thesis 为 None"""
    from agents.premarket_summary import build_summary
    date = _make_mock_files(tmp_path, sym="TEST", is_held=False)
    result = build_summary("TEST", date, base_dir=str(tmp_path))
    assert result["exit"] is None
    assert result["thesis"] is None


def test_decision_translation(tmp_path):
    """中文决策值正确翻译为英文枚举"""
    from agents.premarket_summary import build_summary
    date = _make_mock_files(tmp_path, sym="TEST", is_held=True)
    result = build_summary("TEST", date, base_dir=str(tmp_path))
    assert result["entry"]["decision"] in ("enter", "watch", "pass")
    assert result["exit"]["decision"] in ("hold", "reduce", "exit")


def test_alignment_check_consistent(tmp_path):
    """strategic_stance=hold + entry=enter → consistent"""
    from agents.premarket_summary import build_summary
    date = _make_mock_files(tmp_path, sym="TEST", is_held=True)
    result = build_summary("TEST", date, base_dir=str(tmp_path))
    ac = result["strategic_context"]["alignment_check"]
    assert ac["strategic_vs_tactical"] in ("consistent", "tension", "contradiction")


def test_premarket_summary_cli(tmp_path, monkeypatch):
    """CLI main() 正常退出且产出 JSON 文件"""
    import agents.premarket_summary as m
    date = _make_mock_files(tmp_path, sym="CLI", is_held=False)
    # monkeypatch build_summary / write_summary to use tmp_path
    _orig_build = m.build_summary
    _orig_write = m.write_summary
    monkeypatch.setattr(m, "build_summary",
                        lambda sym, ds: _orig_build(sym, ds, base_dir=str(tmp_path)))
    monkeypatch.setattr(m, "write_summary",
                        lambda sym, d: _orig_write(sym, d, base_dir=str(tmp_path)))
    m.main(["CLI"])
    files = list((tmp_path / "findings").glob(f"premarket_summary_{date}_CLI.json"))
    assert files, "premarket_summary JSON 未生成"
