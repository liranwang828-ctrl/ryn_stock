# tests/test_premarket_exit_sheet.py
import sys, os

from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import date, timedelta


def test_parse_time_deadline_finds_date():
    """_parse_time_deadline 从中文文本解析截止日期"""
    from stock_team.core.premarket_exit_sheet import _parse_time_deadline
    text = "【路径/时间成本】MRVL 两周内（截止 2099-12-31）无法收复"
    days, date_str = _parse_time_deadline(text)
    assert date_str == "2099-12-31"
    assert days > 0


def test_parse_time_deadline_no_date():
    """无日期文本返回 (None, None)"""
    from stock_team.core.premarket_exit_sheet import _parse_time_deadline
    days, ds = _parse_time_deadline("【基本面/论点失效】大客户减单")
    assert days is None
    assert ds is None


def test_compute_stop_levels_uses_manual_gtc():
    """t1_stop_snapshot 非空时 stop_source=manual_gtc"""
    from stock_team.core.premarket_exit_sheet import _compute_stop_levels
    pos_cfg = {"t1_stop_snapshot": 76.0, "t1_cost": 102.5}
    with patch("stock_team.core.premarket_exit_sheet._fetch_price_and_atr",
               return_value={"cur": 88.4, "atr14": 5.0, "lo5": 80.0}):
        hs, ss, src, tech = _compute_stop_levels("MRVU", pos_cfg)
    assert hs == 76.0
    assert src == "manual_gtc"
    assert ss == 102.5  # soft_stop = cost


def test_compute_stop_levels_uses_auto_atr():
    """无手工止损时 stop_source=auto_atr，值为 lo5 - atr*0.3"""
    from stock_team.core.premarket_exit_sheet import _compute_stop_levels
    pos_cfg = {"t1_stop_snapshot": None, "node1": None, "t1_cost": 141.0}
    with patch("stock_team.core.premarket_exit_sheet._fetch_price_and_atr",
               return_value={"cur": 141.0, "atr14": 10.0, "lo5": 130.0}):
        hs, ss, src, tech = _compute_stop_levels("BABA", pos_cfg)
    assert src == "auto_atr"
    assert abs(hs - (130.0 - 10.0 * 0.3)) < 0.01  # lo5 - atr*0.3 = 127.0


def _make_pos(thesis_status="intact", t1_stop=None, node1=None, cost=100.0,
              falsification_conditions=None):
    return {
        "thesis_status": thesis_status,
        "t1_stop_snapshot": t1_stop,
        "node1": node1,
        "t1_cost": cost,
        "falsification_conditions": falsification_conditions or [],
    }

def _mock_tech(cur=120.0, atr14=5.0, lo5=110.0):
    return {"cur": cur, "atr14": atr14, "lo5": lo5}


def test_evaluate_exit_price_below_hard_stop():
    """价格 < 硬止损 → 应出场"""
    from stock_team.core.premarket_exit_sheet import evaluate_exit
    pos = _make_pos(t1_stop=100.0, cost=120.0)
    with patch("stock_team.core.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=95.0, lo5=90.0)):
        r = evaluate_exit("LITE", pos, {})
    assert r["decision"] == "应出场"
    assert "price < hard_stop" in r["hard_triggers"]
    assert r["hard_dist_pct"] < 0  # negative = below stop


def test_evaluate_exit_thesis_broken():
    """thesis_status=broken → 应出场"""
    from stock_team.core.premarket_exit_sheet import evaluate_exit
    pos = _make_pos(thesis_status="broken", t1_stop=80.0, cost=100.0)
    with patch("stock_team.core.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=85.0)):
        r = evaluate_exit("BABA", pos, {})
    assert r["decision"] == "应出场"
    assert "thesis_status=broken" in r["hard_triggers"]


def test_evaluate_exit_time_expired():
    """过期时间证伪条件 → 应出场"""
    from stock_team.core.premarket_exit_sheet import evaluate_exit
    past = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    cond = f"【路径/时间成本】截止 {past} 未完成"
    pos = _make_pos(t1_stop=80.0, cost=100.0, falsification_conditions=[cond])
    with patch("stock_team.core.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=90.0)):
        r = evaluate_exit("TEST", pos, {})
    assert r["decision"] == "应出场"
    assert any("expired" in t for t in r["hard_triggers"])


def test_evaluate_exit_weakening():
    """thesis=weakening → 考虑减仓"""
    from stock_team.core.premarket_exit_sheet import evaluate_exit
    pos = _make_pos(thesis_status="weakening", t1_stop=80.0, cost=100.0)
    with patch("stock_team.core.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=110.0)):
        r = evaluate_exit("NVDA", pos, {})
    assert r["decision"] == "考虑减仓"
    assert "thesis_status=weakening" in r["soft_triggers"]


def test_evaluate_exit_time_soft_trigger():
    """时间证伪条件 ≤3天 → 考虑减仓"""
    from stock_team.core.premarket_exit_sheet import evaluate_exit
    soon = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
    cond = f"【路径/时间成本】截止 {soon} 条件"
    pos = _make_pos(t1_stop=80.0, cost=100.0, falsification_conditions=[cond])
    with patch("stock_team.core.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=110.0)):
        r = evaluate_exit("TEST", pos, {})
    assert r["decision"] == "考虑减仓"
    assert any("time_condition_expiring" in t for t in r["soft_triggers"])


def test_evaluate_exit_hold():
    """无触发条件 → 继续持有"""
    from stock_team.core.premarket_exit_sheet import evaluate_exit
    pos = _make_pos(t1_stop=80.0, cost=100.0)
    with patch("stock_team.core.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=120.0)):
        r = evaluate_exit("IAU", pos, {})
    assert r["decision"] == "继续持有"
    assert r["hard_triggers"] == []
    assert r["soft_triggers"] == []


def test_write_exit_decision_creates_json(tmp_path, monkeypatch):
    """write_exit_decision 生成 exit_decision_{date}.json"""
    from stock_team.core.premarket_exit_sheet import write_exit_decision
    import stock_team.core.premarket_exit_sheet as mod
    monkeypatch.setattr(mod, "_FINDINGS", str(tmp_path))

    decisions = {
        "MRVU": {
            "decision": "考虑减仓", "hard_stop": 76.0, "soft_stop": 102.5,
            "stop_source": "manual_gtc", "cur": 88.4, "hard_dist_pct": 14.0,
            "hard_triggers": [], "soft_triggers": ["price_in_loss_zone"],
            "falsification_check": [], "rr_remaining": None, "reason": "浮亏区",
        }
    }
    write_exit_decision(decisions, findings_dir=str(tmp_path))

    import json
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    out = tmp_path / f"exit_decision_{date_str}.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "date" in data
    assert "positions" in data
    assert "MRVU" in data["positions"]
    assert data["positions"]["MRVU"]["decision"] == "考虑减仓"
