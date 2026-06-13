"""
市场时间感知 — 告诉系统今天是什么特殊日期
影响: 策略门控阈值、风险偏好、操作建议

用法:
  from stock_team.utils.market_calendar import get_context, get_time_factor
  ctx = get_context()  # 返回今日时间特征
"""
import os, json
from datetime import datetime, timezone, timedelta, date
import yfinance as yf

ET = timezone(timedelta(hours=-4))

# 美联储 2026 年议息日历（FOMC）
FOMC_DATES_2026 = {
    "2026-01-29", "2026-03-19", "2026-05-07", "2026-06-18",
    "2026-07-30", "2026-09-17", "2026-11-05", "2026-12-17",
}

# 美国市场假日 2026
US_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
}

def get_context(today: date = None) -> dict:
    """返回今日市场时间特征"""
    if today is None:
        today = datetime.now(ET).date()
    today_str = today.strftime("%Y-%m-%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    ctx = {
        "date": today_str,
        "weekday": today.strftime("%A"),
        "is_holiday": today_str in US_HOLIDAYS_2026,
        "is_fomc_day": today_str in FOMC_DATES_2026,
        "is_fomc_eve": tomorrow_str in FOMC_DATES_2026,
        "is_month_end": (today + timedelta(days=1)).month != today.month,
        "is_quarter_end": today.month in (3, 6, 9, 12) and (today + timedelta(days=1)).month != today.month,
        "is_friday": today.weekday() == 4,
        "is_monday": today.weekday() == 0,
        "warnings": [],
        "suggestions": [],
    }

    # 生成警告和建议
    if ctx["is_holiday"]:
        ctx["warnings"].append("⚠️  今日美国市场休市")
    if ctx["is_fomc_day"]:
        ctx["warnings"].append("⚠️  美联储议息日：下午2点发布决议，波动率显著放大")
        ctx["suggestions"].append("议息日前减少新建仓，等待决议后方向确认")
    if ctx["is_fomc_eve"]:
        ctx["warnings"].append("🔔 明日美联储议息，今日市场可能提前蓄力或避险")
    if ctx["is_month_end"]:
        ctx["warnings"].append("📅 月末：机构可能调仓再平衡，流动性变化")
    if ctx["is_quarter_end"]:
        ctx["warnings"].append("📊 季末：机构大规模再平衡，窗口装扮效应")
    if ctx["is_friday"]:
        ctx["suggestions"].append("周五下午：避免建立需要过夜的高风险仓位")

    return ctx

def get_time_factor() -> float:
    """返回0-100的时间因子（用于统一置信度计算）"""
    ctx = get_context()
    score = 60.0  # 默认

    if ctx["is_holiday"]:      return 0.0   # 休市
    if ctx["is_fomc_day"]:     score -= 20  # 议息日大幅降低
    if ctx["is_fomc_eve"]:     score -= 10
    if ctx["is_month_end"]:    score -= 5
    if ctx["is_quarter_end"]:  score -= 10
    if ctx["is_friday"]:       score -= 5

    return max(0, min(100, score))

def format_context(ctx: dict) -> str:
    lines = []
    if ctx["warnings"]:
        for w in ctx["warnings"]:
            lines.append(f"  {w}")
    if ctx["suggestions"]:
        for s in ctx["suggestions"]:
            lines.append(f"  💡 {s}")
    if not lines:
        lines.append(f"  普通交易日（{ctx['weekday']}）")
    return "\n".join(lines)

if __name__ == "__main__":
    ctx = get_context()
    print(f"=== 市场日历 {ctx['date']} ===")
    print(format_context(ctx))
    print(f"\n时间因子: {get_time_factor():.0f}/100")
