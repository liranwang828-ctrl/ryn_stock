"""
组合层外部环境止损模块 — portfolio_macro_guard.py
大盘层（VIX/SPY）和板块层（ETF）的触发检查。
被 macro_strategy.py 调用，不写入个股 JSON。
"""
import json, os

CFG_PATH = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")),
                        "config/portfolio_macro_guard.json")


def get_thresholds(cfg_path: str = CFG_PATH) -> dict:
    try:
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "vix_spike_threshold": 5.0,
            "spy_drop_threshold": -2.5,
            "portfolio_reduce_pct": 20,
            "sector_reduce_pct": 30,
        }


def check_market_stress(vix_change: float, spy_change: float,
                        vix_threshold: float = 5.0,
                        spy_threshold: float = -2.5) -> dict:
    triggered = vix_change >= vix_threshold or spy_change <= spy_threshold
    reason = []
    if vix_change >= vix_threshold:
        reason.append(f"VIX +{vix_change:.1f}")
    if spy_change <= spy_threshold:
        reason.append(f"SPY {spy_change:.2f}%")
    return {
        "triggered": triggered,
        "layer":     "market" if triggered else None,
        "reason":    " + ".join(reason) if reason else None,
    }


def check_sector_stress(sector_etf_below_ma50: bool,
                        stock_rs_negative: bool) -> dict:
    triggered = sector_etf_below_ma50 and stock_rs_negative
    return {
        "triggered": triggered,
        "layer":     "sector" if triggered else None,
        "reason":    "板块ETF跌破MA50 + 个股RS转负" if triggered else None,
    }
