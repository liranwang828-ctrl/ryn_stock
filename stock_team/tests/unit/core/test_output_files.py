import sys, os, json

from unittest.mock import patch, MagicMock
from datetime import datetime


def _mock_technicals():
    return {
        "cur": 870.0, "ma20": 920.0, "atr14": 50.0,
        "lo5": 857.0, "lo10": 840.0, "hi20": 960.0, "ma20_dev": -5.4,
    }


def test_order_sheet_writes_json_files(tmp_path, monkeypatch):
    """generate_order_sheet + write_order_sheet_files 生成两个 JSON 文件"""
    import stock_team.core.premarket_order_sheet as mod
    monkeypatch.setattr(mod, "_FUND_DIR",    str(tmp_path))
    monkeypatch.setattr(mod, "_REGIME_PATH", str(tmp_path / "regime.json"))
    monkeypatch.setattr(mod, "_POS_PATH",    str(tmp_path / "pos.json"))
    monkeypatch.setattr(mod, "_MACRO_PATH",  str(tmp_path / "macro.json"))

    (tmp_path / "regime.json").write_text('{"regime":"trending_up","overnight_signal":""}', encoding="utf-8")
    (tmp_path / "pos.json").write_text('{"positions":{}}', encoding="utf-8")
    (tmp_path / "macro.json").write_text('{"macro_tone":"中性"}', encoding="utf-8")

    with patch("stock_team.core.premarket_order_sheet._get_technicals") as mock_tech, \
         patch("stock_team.core.premarket_order_sheet._get_overnight_data") as mock_ov, \
         patch("stock_team.core.premarket_order_sheet._load_json") as mock_load:

        mock_tech.return_value = _mock_technicals()
        mock_ov.return_value = {"overnight_price": None, "overnight_chg": None, "already_in_zone": None}

        def _load_side(path, default=None):
            p = str(path)
            if "regime" in p: return {"regime": "trending_up", "overnight_signal": ""}
            if "pos"    in p: return {"positions": {}}
            if "macro"  in p: return {"macro_tone": "中性"}
            return default or {}
        mock_load.side_effect = _load_side

        date_str = datetime.now().strftime("%Y-%m-%d")
        d = mod.generate_order_sheet("LITE")
        mod.write_order_sheet_files({"LITE": d}, findings_dir=str(tmp_path), base_dir=str(tmp_path))

    # Verify order_sheet_{date}.json — must have "date" and "symbols" wrapper
    order_file = tmp_path / f"order_sheet_{date_str}.json"
    assert order_file.exists(), f"order_sheet 文件未生成: {order_file}"
    order_data = json.loads(order_file.read_text(encoding="utf-8"))
    assert "date"    in order_data, "order_sheet 缺少 date 字段"
    assert "symbols" in order_data, "order_sheet 缺少 symbols 包装"
    assert "LITE"    in order_data["symbols"]
    assert "stop_loss" in order_data["symbols"]["LITE"]

    # Verify daily_plan_{date}.json — poll.py reads plan.get("stocks",{}).get(sym)
    plan_file = tmp_path / f"daily_plan_{date_str}.json"
    assert plan_file.exists(), f"daily_plan compat 文件未生成: {plan_file}"
    plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
    assert "stocks" in plan_data, "daily_plan 缺少 stocks key（poll.py 需要这个结构）"
    lite = plan_data["stocks"].get("LITE", {})
    assert "stop"      in lite, "daily_plan.stocks.LITE 缺少 stop"
    assert "t1_target" in lite, "daily_plan.stocks.LITE 缺少 t1_target"
    assert "t2_target" in lite, "daily_plan.stocks.LITE 缺少 t2_target"


def test_entry_decision_writes_json(tmp_path, monkeypatch):
    """write_entry_decision 生成 entry_decision_{date}.json"""
    import stock_team.core.premarket_decision as mod
    monkeypatch.setattr(mod, "_THRESHOLDS_PATH", "/nonexistent")
    monkeypatch.setattr(mod, "_FINDINGS",        str(tmp_path))

    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")

    with patch("stock_team.core.premarket_decision._is_stage2_insufficient", return_value=False):
        decisions = {
            "LITE": {"decision": "可入场", "hard_vetoes": [], "soft_vetoes": [],
                     "reason": "通过", "score": 75, "rr_ratio": 3.5},
            "MRVU": {"decision": "不入场", "hard_vetoes": ["thesis=weakening"],
                     "soft_vetoes": [], "reason": "硬否决", "score": 45, "rr_ratio": 1.2},
        }
        pos_syms = ["BABA", "NVDA"]
        mod.write_entry_decision(decisions, pos_syms, findings_dir=str(tmp_path))

    out_file = tmp_path / f"entry_decision_{date_str}.json"
    assert out_file.exists(), f"entry_decision 文件未生成"
    data = json.loads(out_file.read_text(encoding="utf-8"))

    assert "decisions"    in data
    assert "LITE"         in data["decisions"]
    assert "MRVU"         in data["decisions"]
    assert "poll_needed"  in data
    assert "poll_symbols" in data
    # LITE (可入场) should be in poll_symbols
    assert "LITE"  in data["poll_symbols"]
    # MRVU (不入场) should NOT be in poll_symbols
    assert "MRVU" not in data["poll_symbols"]
    # Positions should always be in poll_symbols
    assert "BABA"  in data["poll_symbols"]
    assert "NVDA"  in data["poll_symbols"]
    # poll_needed = True because LITE (可入场) exists
    assert data["poll_needed"] is True
