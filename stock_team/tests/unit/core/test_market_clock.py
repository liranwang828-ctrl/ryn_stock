from datetime import datetime
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")


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
