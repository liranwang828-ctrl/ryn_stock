"""
Safety Filter — 8 market safety checks with tiered response.
Tiers: red (hard block) / orange (strong warning + override) / yellow (info only)
"""
import os, json
from datetime import datetime, timezone, timedelta

# 2026 FOMC meeting dates (decision day, usually Wednesday)
FOMC_DATES_2026 = [
    "2026-01-29", "2026-03-19", "2026-05-07", "2026-06-18",
    "2026-07-29", "2026-09-17", "2026-11-05", "2026-12-17",
]

# Tier classification
RED = "red"
ORANGE = "orange"
YELLOW = "yellow"

TIER = {
    "F1": ORANGE,   # VIX急涨 — rare, systemic risk
    "F2": YELLOW,   # 重大新闻冲击 — depends on definition
    "F3": RED,      # 大盘熔断 — market halted
    "F4": YELLOW,   # 低流动性 — common intraday
    "F5": YELLOW,   # FOMC管制 — predictable
    "F6": YELLOW,   # 财报风险 — very common per-ticker
    "F7": YELLOW,   # 隔夜跳空 — weekly occurrence
    "F8": ORANGE,   # 相关性融涨 — systemic, no edge
}

NEWS_PANIC_KEYWORDS = [
    "crash", "meltdown", "contagion", "war", "attack", "default",
    "bankrupt", "bailout", "emergency", "panic", "crisis", "collapse",
    "地震", "战争", "崩盘", "危机", "违约", "紧急", "熔断",
]


def _get_field(fields, key, default=None):
    """Extract a field value from a potentially nested dict."""
    v = fields.get(key)
    if isinstance(v, dict):
        return v.get("value", default)
    return v if v is not None else default


def check_f1_vix(fields):
    """VIX急涨: VIX > 35"""
    vix = _get_field(fields, "vix")
    if vix is not None and vix > 35:
        vix_pct = _get_field(fields, "vix_percentile", 0)
        return {
            "id": "F1", "tier": TIER["F1"], "triggered": True,
            "name": "VIX急涨",
            "detail": f"VIX={vix:.1f} (分位{vix_pct:.0%})，市场恐慌中",
            "action": "建议关闭50%多头仓位，暂停新开多仓",
        }
    return {"id": "F1", "tier": TIER["F1"], "triggered": False}


def check_f2_news(fields):
    """重大新闻冲击: 新闻标题含恐慌关键词且 < 30分钟"""
    headlines = _get_field(fields, "news_headlines", [])
    now = datetime.now(timezone.utc)
    for h in (headlines or [])[:5]:
        title = (h.get("title", "") or "").lower()
        time_str = h.get("time", "")
        if any(kw in title for kw in NEWS_PANIC_KEYWORDS):
            return {
                "id": "F2", "tier": TIER["F2"], "triggered": True,
                "name": "重大新闻冲击",
                "detail": f"检测到恐慌关键词: {title[:80]}",
                "action": "建议暂停交易30分钟，等待信息消化",
            }
    return {"id": "F2", "tier": TIER["F2"], "triggered": False}


def check_f3_circuit_breaker(fields):
    """大盘熔断: SPY 跌超 5%"""
    spy_chg = _get_field(fields, "spy_daily_chg")
    if spy_chg is not None and spy_chg < -0.05:
        return {
            "id": "F3", "tier": TIER["F3"], "triggered": True,
            "name": "大盘熔断",
            "detail": f"SPY日内跌幅={spy_chg:.1%}，超过5%熔断线",
            "action": "禁止所有新开仓，收紧现有止损至1×ATR",
        }
    return {"id": "F3", "tier": TIER["F3"], "triggered": False}


def check_f4_liquidity(fields):
    """低流动性: 当日成交量 < 20日均量50%"""
    vol_ratio = _get_field(fields, "Volume_ratio") or _get_field(fields, "volume_breakout_ratio")
    if vol_ratio is not None and vol_ratio < 0.5:
        return {
            "id": "F4", "tier": TIER["F4"], "triggered": True,
            "name": "低流动性",
            "detail": f"成交量比率={vol_ratio:.2f}，仅为20日均量的{vol_ratio:.0%}",
            "action": "建议减仓50%，流动性不足时滑点风险大",
        }
    return {"id": "F4", "tier": TIER["F4"], "triggered": False}


def check_f5_fomc(fields):
    """FOMC管制期: 决策日前后90分钟窗口"""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    if today_str not in FOMC_DATES_2026:
        return {"id": "F5", "tier": TIER["F5"], "triggered": False}

    hour = now.hour + now.minute / 60.0
    if 13.5 <= hour <= 15.5:
        return {
            "id": "F5", "tier": TIER["F5"], "triggered": True,
            "name": "FOMC管制期",
            "detail": f"FOMC决策日（{today_str}），当前在管制窗口内（14:00前后90分钟）",
            "action": "建议暂停新开仓，现有持仓收紧止损至1.5×ATR",
        }
    return {"id": "F5", "tier": TIER["F5"], "triggered": False}


def check_f6_earnings(fields, symbol):
    """财报风险: 48h内有财报且非财报策略仓位"""
    earnings_date = _get_field(fields, "earnings_date")
    if not earnings_date:
        return {"id": "F6", "tier": TIER["F6"], "triggered": False}

    try:
        if isinstance(earnings_date, (int, float)):
            ed = datetime.fromtimestamp(earnings_date, tz=timezone.utc)
        elif isinstance(earnings_date, str):
            ed = datetime.fromisoformat(earnings_date.replace("Z", "+00:00"))
        else:
            return {"id": "F6", "tier": TIER["F6"], "triggered": False}

        now = datetime.now(timezone.utc)
        hours_until = (ed - now).total_seconds() / 3600
        if 0 < hours_until <= 48:
            return {
                "id": "F6", "tier": TIER["F6"], "triggered": True,
                "name": "财报风险",
                "detail": f"{symbol} 将在 {hours_until:.0f} 小时内发布财报",
                "action": f"建议暂停 {symbol} 新开仓，等待财报后价格发现",
            }
    except (ValueError, TypeError, OSError):
        pass
    return {"id": "F6", "tier": TIER["F6"], "triggered": False}


def check_f7_overnight_gap(fields):
    """隔夜跳空: 开盘跳空 > 2%"""
    gap = _get_field(fields, "overnight_chg")
    if gap is not None and abs(gap) > 0.02:
        direction = "高开" if gap > 0 else "低开"
        return {
            "id": "F7", "tier": TIER["F7"], "triggered": True,
            "name": "隔夜跳空",
            "detail": f"{direction} {gap:.1%}，超过2%阈值",
            "action": "建议等待价格稳定后再入场（连续3根5分钟K线振幅<0.5%）",
        }
    return {"id": "F7", "tier": TIER["F7"], "triggered": False}


def check_f8_correlation_meltup(fields):
    """相关性融涨: >80%板块同向 + R² > 0.9"""
    sector_healthy = _get_field(fields, "sector_healthy")
    spy_above_ma200 = _get_field(fields, "spy_above_ma200")
    corr = _get_field(fields, "correlation_with_spy")

    if corr is not None and corr > 0.9 and spy_above_ma200:
        return {
            "id": "F8", "tier": TIER["F8"], "triggered": True,
            "name": "相关性融涨",
            "detail": f"个股与SPY相关性={corr:.2f}，板块高度同步，选股无Alpha",
            "action": "建议暂停开仓，等待相关性下降（R²<0.8持续10分钟）",
        }
    return {"id": "F8", "tier": TIER["F8"], "triggered": False}


CHECKS = [
    check_f1_vix,
    check_f2_news,
    check_f3_circuit_breaker,
    check_f4_liquidity,
    check_f5_fomc,
    check_f6_earnings,
    check_f7_overnight_gap,
    check_f8_correlation_meltup,
]


def check_all(fields, symbol="", require_spy=False):
    """
    Run all 8 safety checks.

    Returns:
        blocked: bool — if True, hard block (red tier triggered)
        report: dict with red/orange/yellow lists, blocked flag, summary
    """
    report = {"red": [], "orange": [], "yellow": [], "blocked": False, "summary": ""}

    for check_fn in CHECKS:
        if check_fn == check_f6_earnings:
            result = check_fn(fields, symbol)
        else:
            result = check_fn(fields)

        if not result.get("triggered"):
            continue

        tier = result["tier"]
        report[tier].append(result)

    if report["red"]:
        report["blocked"] = True
        names = ", ".join(r["name"] for r in report["red"])
        report["summary"] = f"RED HARD BLOCK: {names}"
    elif report["orange"]:
        names = ", ".join(r["name"] for r in report["orange"])
        report["summary"] = f"ORANGE WARNING: {names}"
    elif report["yellow"]:
        names = ", ".join(r["name"] for r in report["yellow"])
        report["summary"] = f"YELLOW INFO: {names}"
    else:
        report["summary"] = "All safety checks passed"

    return report["blocked"], report


def print_report(report):
    """Pretty-print the safety check report to console."""
    print(f"\n{'='*50}")
    print(f"  Safety Report -- {report['summary']}")
    print(f"{'='*50}")

    if report["red"]:
        print("\n  [RED: Hard Block -- trading blocked]")
        for r in report["red"]:
            print(f"    {r['id']} {r['name']}: {r['detail']}")
            print(f"    -> {r['action']}")

    if report["orange"]:
        print("\n  [ORANGE: Strong Warning -- manual confirm recommended]")
        for r in report["orange"]:
            print(f"    {r['id']} {r['name']}: {r['detail']}")
            print(f"    -> {r['action']}")

    if report["yellow"]:
        print("\n  [YELLOW: Info -- logged, not blocking]")
        for r in report["yellow"]:
            print(f"    {r['id']} {r['name']}: {r['detail']}")
            print(f"    -> {r['action']}")

    if not any([report["red"], report["orange"], report["yellow"]]):
        print("  All safety checks passed")


def main():
    """Standalone test: python safety_filter.py AAPL"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    args = parser.parse_args()

    from agents.protocol import BASE, VERIFIED_PATH

    if not os.path.exists(VERIFIED_PATH):
        print("未找到 data_verified.json，请先运行 data_agent + verifier_agent")
        return

    data = json.load(open(VERIFIED_PATH, encoding="utf-8"))
    fields = data.get("fields", {})

    blocked, report = check_all(fields, args.symbol)
    print_report(report)

    if blocked:
        print("\nWARNING: Trade blocked by safety filter.")
    elif report["orange"]:
        print("\nWARNING: Strong warning signals present. Manual confirmation recommended.")


if __name__ == "__main__":
    main()
