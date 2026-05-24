# tests/test_premarket_order_sheet_b.py
import sys, os
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
from unittest.mock import patch, MagicMock
import json


def _make_regime(overnight_signal="", regime="trending_up"):
    return {"overnight_signal": overnight_signal, "regime": regime}


def test_overnight_data_below_range():
    """隔夜价低于入场区间下限时，输出包含'已跌入目标区间'提示"""
    from agents.premarket_order_sheet import generate_order_sheet

    with patch("agents.premarket_order_sheet._get_technicals") as mock_tech, \
         patch("agents.premarket_order_sheet._get_overnight_data") as mock_ov, \
         patch("agents.premarket_order_sheet._load_json") as mock_load:

        mock_tech.return_value = {
            "cur": 900.0, "ma20": 920.0, "atr14": 50.0,
            "lo5": 870.0, "lo10": 855.0, "hi20": 950.0, "ma20_dev": -2.2,
        }
        # entry_low = max(870*0.99, 920-25) = max(860.3, 895) = 895
        # overnight 855 < entry_low 895
        mock_ov.return_value = {
            "overnight_price": 855.0,
            "overnight_chg": -0.05,
            "already_in_zone": None,
        }
        mock_load.return_value = {}

        result = generate_order_sheet("LITE")

    assert "overnight_note" in result
    assert "已跌入目标区间" in result["overnight_note"]


def test_overnight_data_above_range():
    """隔夜价高于入场区间上限+0.5ATR时，输出'区间失效'"""
    from agents.premarket_order_sheet import generate_order_sheet

    with patch("agents.premarket_order_sheet._get_technicals") as mock_tech, \
         patch("agents.premarket_order_sheet._get_overnight_data") as mock_ov, \
         patch("agents.premarket_order_sheet._load_json") as mock_load:

        mock_tech.return_value = {
            "cur": 900.0, "ma20": 920.0, "atr14": 50.0,
            "lo5": 870.0, "lo10": 855.0, "hi20": 950.0, "ma20_dev": -2.2,
        }
        # entry_high = 920+25 = 945; threshold = 945+25 = 970
        # overnight 980 > 970 → 区间失效
        mock_ov.return_value = {
            "overnight_price": 980.0,
            "overnight_chg": 0.09,
            "already_in_zone": None,
        }
        mock_load.return_value = {}

        result = generate_order_sheet("LITE")

    assert "overnight_note" in result
    assert "区间失效" in result["overnight_note"]


def test_overnight_data_within_range():
    """隔夜价在入场区间内时，输出'已在目标区间'"""
    from agents.premarket_order_sheet import generate_order_sheet

    with patch("agents.premarket_order_sheet._get_technicals") as mock_tech, \
         patch("agents.premarket_order_sheet._get_overnight_data") as mock_ov, \
         patch("agents.premarket_order_sheet._load_json") as mock_load:

        mock_tech.return_value = {
            "cur": 900.0, "ma20": 920.0, "atr14": 50.0,
            "lo5": 870.0, "lo10": 855.0, "hi20": 950.0, "ma20_dev": -2.2,
        }
        # entry_low=895, entry_high=945; overnight 910 is within range
        mock_ov.return_value = {
            "overnight_price": 910.0,
            "overnight_chg": 0.01,
            "already_in_zone": None,
        }
        mock_load.return_value = {}

        result = generate_order_sheet("LITE")

    assert "overnight_note" in result
    assert "已在目标区间" in result["overnight_note"]


def test_narrative_hit_added_to_result():
    """当 overnight_signal 包含标的时，结果含 narrative_hit=True"""
    from agents.premarket_order_sheet import generate_order_sheet

    regime_data = {"overnight_signal": "太空 RKLB+6.1% ASTS+4.5%", "regime": "trending_up"}

    with patch("agents.premarket_order_sheet._get_technicals") as mock_tech, \
         patch("agents.premarket_order_sheet._get_overnight_data") as mock_ov, \
         patch("agents.premarket_order_sheet._load_json") as mock_load:

        mock_tech.return_value = {
            "cur": 25.0, "ma20": 26.0, "atr14": 1.0,
            "lo5": 24.0, "lo10": 23.0, "hi20": 28.0, "ma20_dev": -3.8,
        }
        mock_ov.return_value = {"overnight_price": 25.5, "overnight_chg": 0.02, "already_in_zone": None}

        def load_side_effect(path, default=None):
            if "market_regime" in str(path):
                return regime_data
            return default or {}
        mock_load.side_effect = load_side_effect

        result = generate_order_sheet("RKLB")

    assert result.get("narrative_hit") is True


def test_personalized_cancel_lite_has_xar():
    """LITE（光模块）的取消条件包含 XAR ETF"""
    from agents.premarket_order_sheet import _personalized_cancel_conditions

    pos_cfg = {
        "macro_sensitivity": {"rate_up": "负"},
        "macro_type": "光模块",
        "catalyst_type": "order",
        "node1": 855.0,
    }
    tech  = {"lo5": 860.0}
    macro = {"yield_curve": "倒挂", "dxy": 100, "yield_10y": 4.45}

    conds = _personalized_cancel_conditions("LITE", pos_cfg, tech, macro)

    assert any("XAR" in c for c in conds), f"取消条件中应包含XAR，实际: {conds}"
    assert any("855" in c for c in conds), \
        f"取消条件应包含node1价格855，实际: {conds}"


def test_personalized_cancel_qqq_always_present():
    """QQQ 基础条件必须存在"""
    from agents.premarket_order_sheet import _personalized_cancel_conditions

    conds = _personalized_cancel_conditions("RKLB", {}, {}, {})
    assert any("QQQ" in c for c in conds)


def test_personalized_cancel_macro_rate_specific():
    """倒挂时，利率取消条件包含具体10Y收益率数字"""
    from agents.premarket_order_sheet import _personalized_cancel_conditions

    pos_cfg = {"macro_sensitivity": {"rate_up": "负"}}
    macro   = {"yield_curve": "倒挂", "dxy": 100, "yield_10y": 4.55}

    conds = _personalized_cancel_conditions("LITE", pos_cfg, {}, macro)
    assert any("4.55" in c or "4.6" in c for c in conds), \
        f"应含具体10Y数值，实际: {conds}"
