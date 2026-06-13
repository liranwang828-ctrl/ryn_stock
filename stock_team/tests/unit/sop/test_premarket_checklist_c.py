# tests/test_premarket_checklist_c.py
import sys, os, json, tempfile

def test_prepare_master_brief_context_keys():
    """prepare_master_brief_context 返回包含三大师所需数据的 dict"""
    from stock_team.core.premarket_checklist import prepare_master_brief_context

    tech = {
        "cur": 870.0, "ma20": 922.0, "atr14": 89.0,
        "ma20_dev": -5.7, "lo5": 857.0, "lo10": 840.0, "hi20": 960.0,
    }
    macro = {
        "yield_curve": "倒挂", "dxy": 102.5, "vix": 18.5,
        "macro_tone": "中性", "macro_score": 5,
    }
    pos_cfg = {
        "thesis": "光模块AI数据中心需求",
        "thesis_status": "intact",
        "catalyst_type": "order",
        "macro_type": "光模块",
        "macro_sensitivity": {"rate_up": "负"},
        "node1": 855.0,
    }
    order_sheet = {
        "entry_range": (860.0, 920.0),
        "entry_base": 870.0,
        "stop_loss": 855.0,
        "target_price": 922.0,
        "rr_ratio": 3.5,
        "cancel_conditions": ["QQQ 开跌 > -1.5%"],
    }

    result = prepare_master_brief_context("LITE", tech, macro, pos_cfg, order_sheet)

    # 必须包含三大师各自需要的数据
    assert "minervini" in result
    assert "druckenmiller" in result
    assert "marks" in result

    # Minervini 需要技术位置
    m = result["minervini"]
    assert "current_price" in m
    assert "ma20_dev_pct" in m

    # Druckenmiller 需要宏观+sizing建议
    d = result["druckenmiller"]
    assert "sizing_note" in d

    # Marks 需要 RR 比
    mk = result["marks"]
    assert "rr_ratio" in mk
    assert "entry" in mk
    assert "stop" in mk
    assert "target" in mk


def test_prepare_master_brief_context_writes_json(tmp_path, monkeypatch):
    """结果写入 findings/premarket_masters_{date}.json"""
    from stock_team.core.premarket_checklist import prepare_master_brief_context
    import stock_team.core.premarket_checklist as mod

    # 重定向 BASE 到临时目录
    monkeypatch.setattr(mod, "BASE", str(tmp_path))
    (tmp_path / "findings").mkdir(exist_ok=True)

    result = prepare_master_brief_context(
        "LITE",
        tech={"cur": 870.0, "ma20": 922.0, "atr14": 89.0, "ma20_dev": -5.7,
              "lo5": 857.0, "lo10": 840.0, "hi20": 960.0},
        macro={"yield_curve": "正常", "dxy": 100.0, "vix": 15.0,
               "macro_tone": "中性", "macro_score": 6},
        pos_cfg={"thesis": "test", "thesis_status": "intact",
                 "catalyst_type": "order", "macro_type": "光模块",
                 "macro_sensitivity": {}, "node1": 855.0},
        order_sheet={"entry_range": (860.0, 920.0), "entry_base": 870.0,
                     "stop_loss": 855.0, "target_price": 922.0,
                     "rr_ratio": 3.5, "cancel_conditions": []},
    )

    from datetime import datetime
    date = datetime.now().strftime("%Y-%m-%d")
    out_file = tmp_path / "findings" / f"premarket_masters_{date}.json"
    assert out_file.exists(), f"JSON 未生成: {out_file}"
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "LITE" in data
