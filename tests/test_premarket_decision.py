# tests/test_premarket_decision.py
import sys, os, json
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
from unittest.mock import patch

def test_load_thresholds_returns_defaults_when_no_file():
    """无配置文件时返回内置默认值"""
    from agents.premarket_decision import load_thresholds
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent/path.json"):
        t = load_thresholds()
    assert t["hard_vetoes"]["rr_min"] == 2.0
    assert t["hard_vetoes"]["macro_score_min"] == 4
    assert t["hard_vetoes"]["watchlist_score_min"] == 50
    assert t["soft_vetoes"]["ma20_dev_max"] == 0.05


def test_load_thresholds_reads_file(tmp_path):
    """存在配置文件时从文件读取"""
    from agents.premarket_decision import load_thresholds
    cfg = {
        "hard_vetoes": {"rr_min": 2.5, "qqq_premarket_min": -0.02,
                        "macro_score_min": 5, "watchlist_score_min": 55},
        "soft_vetoes": {"ma20_dev_max": 0.03, "rs5_min": 0.01, "max_headwinds": 2},
        "macro_type_overrides": {},
    }
    p = tmp_path / "decision_thresholds.json"
    p.write_text(json.dumps(cfg))
    with patch("agents.premarket_decision._THRESHOLDS_PATH", str(p)):
        t = load_thresholds()
    assert t["hard_vetoes"]["rr_min"] == 2.5
    assert t["soft_vetoes"]["ma20_dev_max"] == 0.03


def test_load_thresholds_applies_macro_type_override(tmp_path):
    """macro_type 分组覆盖正确应用"""
    from agents.premarket_decision import load_thresholds
    cfg = {
        "hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                        "macro_score_min": 4, "watchlist_score_min": 50},
        "soft_vetoes": {"ma20_dev_max": 0.05, "rs5_min": 0.0, "max_headwinds": 2},
        "macro_type_overrides": {"防御型": {"macro_score_min": 3}},
    }
    p = tmp_path / "decision_thresholds.json"
    p.write_text(json.dumps(cfg))
    with patch("agents.premarket_decision._THRESHOLDS_PATH", str(p)):
        t_growth    = load_thresholds(macro_type="成长型")
        t_defensive = load_thresholds(macro_type="防御型")
    assert t_growth["hard_vetoes"]["macro_score_min"] == 4
    assert t_defensive["hard_vetoes"]["macro_score_min"] == 3


def _make_inputs(
    thesis_status="intact", rr_ratio=3.5, qqq_chg=-0.005,
    macro_score=6, score=75, overnight_note="已在目标区间",
):
    order_sheet = {"rr_ratio": rr_ratio, "overnight_note": overnight_note}
    macro       = {"macro_score": macro_score}
    pos_cfg     = {"thesis_status": thesis_status}
    return order_sheet, macro, pos_cfg, qqq_chg, score


def test_hard_veto_thesis_broken():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    osh, macro, pos, qqq, score = _make_inputs(thesis_status="broken")
    vetoes = _check_hard_vetoes(osh, macro, pos, qqq, score, t)
    assert any("thesis_status" in v for v in vetoes)


def test_hard_veto_thesis_weakening():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    osh, macro, pos, qqq, score = _make_inputs(thesis_status="weakening")
    vetoes = _check_hard_vetoes(osh, macro, pos, qqq, score, t)
    assert any("thesis_status" in v for v in vetoes)


def test_hard_veto_rr_low():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    osh, macro, pos, qqq, score = _make_inputs(rr_ratio=0.6)
    vetoes = _check_hard_vetoes(osh, macro, pos, qqq, score, t)
    assert any("RR" in v for v in vetoes)


def test_hard_veto_qqq_down():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    osh, macro, pos, qqq, score = _make_inputs(qqq_chg=-0.02)
    vetoes = _check_hard_vetoes(osh, macro, pos, qqq, score, t)
    assert any("QQQ" in v for v in vetoes)


def test_hard_veto_macro_score_low():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    osh, macro, pos, qqq, score = _make_inputs(macro_score=3)
    vetoes = _check_hard_vetoes(osh, macro, pos, qqq, score, t)
    assert any("macro_score" in v for v in vetoes)


def test_hard_veto_score_low():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    osh, macro, pos, qqq, score = _make_inputs(score=40)
    vetoes = _check_hard_vetoes(osh, macro, pos, qqq, score, t)
    assert any("watchlist_score" in v for v in vetoes)


def test_hard_veto_overnight_invalid():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    osh, macro, pos, qqq, score = _make_inputs(overnight_note="区间失效（盘前$980 大幅高出）")
    vetoes = _check_hard_vetoes(osh, macro, pos, qqq, score, t)
    assert any("区间失效" in v for v in vetoes)


def test_no_hard_vetoes_with_clean_inputs():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    osh, macro, pos, qqq, score = _make_inputs()
    vetoes = _check_hard_vetoes(osh, macro, pos, qqq, score, t)
    assert vetoes == []


def _default_soft_thresholds():
    return {"soft_vetoes": {"ma20_dev_max": 0.05, "rs5_min": 0.0, "max_headwinds": 2}}


def test_soft_veto_ma20_high():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.08, "rs5": 2.0, "narrative_hit": True},
        macro={"yield_curve": "正常", "dxy": 100, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "光模块"},
        regime={"regime": "trending_up", "overnight_signal": ""},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert any("MA20" in v for v in result)


def test_soft_veto_rs5_negative():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.01, "rs5": -1.5, "narrative_hit": True},
        macro={"yield_curve": "正常", "dxy": 100, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "光模块"},
        regime={"regime": "trending_up", "overnight_signal": ""},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert any("RS5" in v for v in result)


def test_soft_veto_headwinds():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.01, "rs5": 1.0, "narrative_hit": True},
        macro={"yield_curve": "倒挂", "dxy": 106, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {"rate_up": "负", "dollar_strong": "负"},
                 "macro_type": "光模块"},
        regime={"regime": "trending_up", "overnight_signal": ""},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert any("逆风" in v for v in result)


def test_soft_veto_regime_mismatch():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.01, "rs5": 1.0, "narrative_hit": False},
        macro={"yield_curve": "正常", "dxy": 100, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "光模块"},
        regime={"regime": "sector_hot", "overnight_signal": "能源 XLE+5%"},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert any("Regime" in v for v in result)


def test_no_soft_vetoes_clean():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="RKLB",
        watchlist_result={"ma20_dev": -0.02, "rs5": 3.0, "narrative_hit": True},
        macro={"yield_curve": "正常", "dxy": 99, "macro_score": 7},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "太空"},
        regime={"regime": "sector_hot", "overnight_signal": "太空 RKLB+6%"},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert result == []


def test_soft_veto_master_confidence_low():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.01, "rs5": 1.0, "narrative_hit": True},
        macro={"yield_curve": "正常", "dxy": 99, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "光模块"},
        regime={"regime": "trending_up", "overnight_signal": ""},
        master_confidence_all_low=True,   # 触发 veto 4
        thresholds=t,
    )
    assert any("置信度" in v for v in result)


def test_soft_veto_stage2_insufficient():
    from agents.premarket_decision import _check_soft_vetoes
    from unittest.mock import patch
    import pandas as pd
    t = _default_soft_thresholds()
    # RS5=-1 且 mock MA20 下降 → 触发 veto 6
    fake_closes = pd.Series([110.0]*5 + [108.0]*5 + [106.0])  # 下降趋势
    with patch("agents.premarket_decision._is_stage2_insufficient", return_value=True):
        result = _check_soft_vetoes(
            sym="LITE",
            watchlist_result={"ma20_dev": 0.01, "rs5": -1.0, "narrative_hit": True},
            macro={"yield_curve": "正常", "dxy": 99, "macro_score": 6},
            pos_cfg={"macro_sensitivity": {}, "macro_type": "光模块"},
            regime={"regime": "trending_up", "overnight_signal": ""},
            master_confidence_all_low=False,
            thresholds=t,
        )
    assert any("Stage 2" in v for v in result)


# ── Task 4: evaluate_entry 集成测试 ──────────────────────────────────────────

def _clean_watchlist_result(score=75, ma20_dev=0.01, rs5=2.0, narrative_hit=True):
    return {"score": score, "ma20_dev": ma20_dev, "rs5": rs5,
            "narrative_hit": narrative_hit}

def _clean_order_sheet(rr_ratio=3.5, overnight_note="已在目标区间"):
    return {"rr_ratio": rr_ratio, "overnight_note": overnight_note}

_CLEAN_MACRO   = {"macro_score": 6, "yield_curve": "正常", "dxy": 99}
_CLEAN_POS_CFG = {"thesis_status": "intact", "macro_sensitivity": {}, "macro_type": "光模块"}
_CLEAN_REGIME  = {"regime": "trending_up", "overnight_signal": "LITE+3%"}


def test_evaluate_entry_ke_ruchang():
    """0个硬否决 + 0个软否决 → 可入场"""
    from agents.premarket_decision import evaluate_entry
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent"), \
         patch("agents.premarket_decision._is_stage2_insufficient", return_value=False):
        result = evaluate_entry(
            sym="LITE",
            order_sheet=_clean_order_sheet(),
            watchlist_result=_clean_watchlist_result(),
            macro=_CLEAN_MACRO,
            pos_cfg=_CLEAN_POS_CFG,
            regime=_CLEAN_REGIME,
            qqq_premarket_chg=-0.003,
        )
    assert result["decision"] == "可入场"
    assert result["hard_vetoes"] == []


def test_evaluate_entry_bu_ruchang_hard_veto():
    """RR=0.6x → 不入场（硬否决）"""
    from agents.premarket_decision import evaluate_entry
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent"), \
         patch("agents.premarket_decision._is_stage2_insufficient", return_value=False):
        result = evaluate_entry(
            sym="MRVU",
            order_sheet=_clean_order_sheet(rr_ratio=0.6),
            watchlist_result=_clean_watchlist_result(),
            macro=_CLEAN_MACRO,
            pos_cfg=_CLEAN_POS_CFG,
            regime=_CLEAN_REGIME,
            qqq_premarket_chg=-0.003,
        )
    assert result["decision"] == "不入场"
    assert len(result["hard_vetoes"]) >= 1


def test_evaluate_entry_guancha_two_soft():
    """0个硬否决 + 2个软否决 → 观察"""
    from agents.premarket_decision import evaluate_entry
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent"), \
         patch("agents.premarket_decision._is_stage2_insufficient", return_value=False):
        result = evaluate_entry(
            sym="LITE",
            order_sheet=_clean_order_sheet(),
            watchlist_result=_clean_watchlist_result(
                ma20_dev=0.08,   # 软否决1: MA20乖离>5%
                rs5=-1.5,        # 软否决2: RS5<0
                narrative_hit=True,
            ),
            macro=_CLEAN_MACRO,
            pos_cfg=_CLEAN_POS_CFG,
            regime=_CLEAN_REGIME,
            qqq_premarket_chg=-0.003,
        )
    assert result["decision"] == "观察"
    assert len(result["soft_vetoes"]) >= 2


def test_evaluate_entry_one_soft_is_ke_ruchang():
    """0个硬否决 + 1个软否决 → 可入场（边界）"""
    from agents.premarket_decision import evaluate_entry
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent"), \
         patch("agents.premarket_decision._is_stage2_insufficient", return_value=False):
        result = evaluate_entry(
            sym="LITE",
            order_sheet=_clean_order_sheet(),
            watchlist_result=_clean_watchlist_result(ma20_dev=0.08),  # 仅1个软否决
            macro=_CLEAN_MACRO,
            pos_cfg=_CLEAN_POS_CFG,
            regime=_CLEAN_REGIME,
            qqq_premarket_chg=-0.003,
        )
    assert result["decision"] == "可入场"
    assert len(result["soft_vetoes"]) == 1
