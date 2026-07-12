"""Market session clock for the local dashboard."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")
CN = ZoneInfo("Asia/Shanghai")

US_MARKET_HOLIDAYS_2026 = {
    "2026-01-01",
    "2026-01-19",
    "2026-02-16",
    "2026-04-03",
    "2026-05-25",
    "2026-07-03",
    "2026-09-07",
    "2026-11-26",
    "2026-12-25",
}

PREMARKET_START = time(4, 0)
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
AFTER_HOURS_END = time(20, 0)


def _is_market_holiday(day) -> bool:
    return day.isoformat() in US_MARKET_HOLIDAYS_2026


def _is_trading_day(day) -> bool:
    return day.weekday() < 5 and not _is_market_holiday(day)


def _session_dt(day, session_time: time) -> datetime:
    return datetime.combine(day, session_time, tzinfo=ET)


def _next_trading_day(day):
    cursor = day
    while not _is_trading_day(cursor):
        cursor += timedelta(days=1)
    return cursor


def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}天")
    if hours or days:
        parts.append(f"{hours}小时")
    parts.append(f"{minutes}分钟")
    return "".join(parts)


def _load_exchange_calendar():
    import exchange_calendars as xcals

    return xcals.get_calendar("XNYS")


def _calendar_day(value):
    return value.date() if hasattr(value, "date") else value


def _trading_date_context(now_et: datetime, calendar=None) -> dict:
    try:
        calendar = calendar or _load_exchange_calendar()
        today = now_et.date()
        if calendar.is_session(today):
            trading_date = today
            last_trading_date = _calendar_day(calendar.previous_session(today))
            next_trading_date = _calendar_day(calendar.next_session(today))
            session_kind = "current"
            formal_session_allowed = True
        else:
            trading_date = None
            last_trading_date = _calendar_day(calendar.previous_session(today))
            next_trading_date = _calendar_day(calendar.next_session(today))
            session_kind = "non_trading_day"
            formal_session_allowed = False
        return {
            "trading_date": trading_date.isoformat() if trading_date else None,
            "last_trading_date": last_trading_date.isoformat(),
            "next_trading_date": next_trading_date.isoformat(),
            "session_kind": session_kind,
            "calendar_status": "verified",
            "formal_session_allowed": formal_session_allowed,
        }
    except Exception as exc:
        return {
            "trading_date": None,
            "last_trading_date": None,
            "next_trading_date": None,
            "session_kind": "calendar_unverified",
            "calendar_status": "unverified",
            "formal_session_allowed": False,
            "calendar_error": f"{type(exc).__name__}: {exc}",
        }


def get_market_clock(now: datetime | None = None, *, calendar=None) -> dict:
    """Return current US equity-market session state for dashboard display."""
    now_et = (now or datetime.now(ET)).astimezone(ET)
    today = now_et.date()
    is_trading_day = _is_trading_day(today)

    open_dt = _session_dt(today, REGULAR_OPEN)
    close_dt = _session_dt(today, REGULAR_CLOSE)
    premarket_dt = _session_dt(today, PREMARKET_START)
    after_hours_end_dt = _session_dt(today, AFTER_HOURS_END)

    if not is_trading_day:
        phase = "rest_day"
        phase_label = "休息日"
        target = "open"
        next_open_day = _next_trading_day(today + timedelta(days=1))
        target_dt = _session_dt(next_open_day, REGULAR_OPEN)
        next_close_dt = _session_dt(next_open_day, REGULAR_CLOSE)
    elif premarket_dt <= now_et < open_dt:
        phase = "premarket"
        phase_label = "盘前"
        target = "open"
        target_dt = open_dt
        next_close_dt = close_dt
    elif open_dt <= now_et < close_dt:
        phase = "regular"
        phase_label = "盘中"
        target = "close"
        target_dt = close_dt
        next_close_dt = close_dt
    elif close_dt <= now_et < after_hours_end_dt:
        phase = "postmarket"
        phase_label = "盘后"
        target = "open"
        next_open_day = _next_trading_day(today + timedelta(days=1))
        target_dt = _session_dt(next_open_day, REGULAR_OPEN)
        next_close_dt = _session_dt(next_open_day, REGULAR_CLOSE)
    else:
        phase = "overnight"
        phase_label = "夜盘"
        target = "open"
        next_day = today if now_et < premarket_dt else today + timedelta(days=1)
        next_open_day = _next_trading_day(next_day)
        target_dt = _session_dt(next_open_day, REGULAR_OPEN)
        next_close_dt = _session_dt(next_open_day, REGULAR_CLOSE)

    countdown_seconds = int((target_dt - now_et).total_seconds())
    payload = {
        "phase": phase,
        "phase_label": phase_label,
        "countdown_target": target,
        "countdown_seconds": max(0, countdown_seconds),
        "countdown_human": _format_duration(countdown_seconds),
        "now_et": now_et.isoformat(timespec="seconds"),
        "now_cn": now_et.astimezone(CN).isoformat(timespec="seconds"),
        "is_trading_day": is_trading_day,
        "is_holiday": _is_market_holiday(today),
        "next_open_et": target_dt.isoformat(timespec="seconds") if target == "open" else open_dt.isoformat(timespec="seconds"),
        "next_close_et": next_close_dt.isoformat(timespec="seconds"),
    }
    payload.update(_trading_date_context(now_et, calendar=calendar))
    return payload
