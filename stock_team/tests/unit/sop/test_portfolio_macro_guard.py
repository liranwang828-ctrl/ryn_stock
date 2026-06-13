import sys, os

def test_get_thresholds_returns_required_keys():
    from stock_team.core.portfolio_macro_guard import get_thresholds
    cfg_path = os.path.join(next(p for p in [os.path.abspath(__file__)] + [os.path.dirname(os.path.abspath(__file__))] + [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))] + [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))] + [os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))] if os.path.exists(os.path.join(p, "templates"))),
                            "config/portfolio_macro_guard.json")
    thresholds = get_thresholds(cfg_path=cfg_path)
    assert "vix_spike_threshold" in thresholds
    assert "portfolio_reduce_pct" in thresholds


def test_check_market_stress_triggers_on_vix_spike():
    from stock_team.core.portfolio_macro_guard import check_market_stress
    result = check_market_stress(vix_change=6.0, spy_change=-1.0,
                                 vix_threshold=5.0, spy_threshold=-2.5)
    assert result["triggered"] is True
    assert result["layer"] == "market"


def test_check_market_stress_triggers_on_spy_drop():
    from stock_team.core.portfolio_macro_guard import check_market_stress
    result = check_market_stress(vix_change=2.0, spy_change=-3.0,
                                 vix_threshold=5.0, spy_threshold=-2.5)
    assert result["triggered"] is True


def test_check_market_stress_no_trigger():
    from stock_team.core.portfolio_macro_guard import check_market_stress
    result = check_market_stress(vix_change=1.0, spy_change=-0.5,
                                 vix_threshold=5.0, spy_threshold=-2.5)
    assert result["triggered"] is False
