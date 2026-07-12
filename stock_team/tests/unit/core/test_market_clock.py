from datetime import date, datetime
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")


class FakeCalendar:
    def __init__(self, sessions):
        self.sessions = sorted(date.fromisoformat(item) for item in sessions)

    def is_session(self, day):
        value = day.date() if hasattr(day, "date") else day
        return value in self.sessions

    def previous_session(self, day):
        value = day.date() if hasattr(day, "date") else day
        return max(item for item in self.sessions if item < value)

    def next_session(self, day):
        value = day.date() if hasattr(day, "date") else day
        return min(item for item in self.sessions if item > value)


def test_market_clock_skips_weekend_and_memorial_day():
    from stock_team.utils.market_clock import get_market_clock

    now = datetime(2026, 5, 24, 1, 51, tzinfo=ET)

    clock = get_market_clock(now)

    assert clock["phase"] == "rest_day"
    assert clock["phase_label"] == "休息日"
    assert clock["next_open_et"].startswith("2026-05-26T09:30:00")
    assert clock["countdown_target"] == "open"


def test_market_clock_regular_session_counts_to_close():
    from stock_team.utils.market_clock import get_market_clock

    now = datetime(2026, 5, 26, 10, 15, tzinfo=ET)

    clock = get_market_clock(now)

    assert clock["phase"] == "regular"
    assert clock["phase_label"] == "盘中"
    assert clock["countdown_target"] == "close"
    assert clock["next_close_et"].startswith("2026-05-26T16:00:00")


def test_market_clock_premarket_counts_to_open():
    from stock_team.utils.market_clock import get_market_clock

    now = datetime(2026, 5, 26, 8, 45, tzinfo=ET)

    clock = get_market_clock(now)

    assert clock["phase"] == "premarket"
    assert clock["phase_label"] == "盘前"
    assert clock["countdown_target"] == "open"
    assert clock["next_open_et"].startswith("2026-05-26T09:30:00")


def test_trading_date_stays_on_et_date_after_beijing_midnight():
    from stock_team.utils.market_clock import get_market_clock

    calendar = FakeCalendar(["2026-07-09", "2026-07-10", "2026-07-13"])
    now = datetime(2026, 7, 10, 15, 0, tzinfo=ET)

    context = get_market_clock(now, calendar=calendar)

    assert context["trading_date"] == "2026-07-10"
    assert context["now_cn"].startswith("2026-07-11T03:00:00")
    assert context["session_kind"] == "current"
    assert context["calendar_status"] == "verified"
    assert context["formal_session_allowed"] is True


def test_non_trading_day_exposes_previous_and_next_without_formal_session():
    from stock_team.utils.market_clock import get_market_clock

    calendar = FakeCalendar(["2026-07-02", "2026-07-06"])
    now = datetime(2026, 7, 3, 10, 0, tzinfo=ET)

    context = get_market_clock(now, calendar=calendar)

    assert context["trading_date"] is None
    assert context["last_trading_date"] == "2026-07-02"
    assert context["next_trading_date"] == "2026-07-06"
    assert context["session_kind"] == "non_trading_day"
    assert context["formal_session_allowed"] is False


def test_calendar_failure_is_unverified_and_never_allows_formal_session():
    from stock_team.utils.market_clock import get_market_clock

    class BrokenCalendar:
        def is_session(self, day):
            raise RuntimeError("calendar unavailable")

    context = get_market_clock(datetime(2026, 7, 10, 9, 0, tzinfo=ET), calendar=BrokenCalendar())

    assert context["calendar_status"] == "unverified"
    assert context["formal_session_allowed"] is False
    assert context["trading_date"] is None
