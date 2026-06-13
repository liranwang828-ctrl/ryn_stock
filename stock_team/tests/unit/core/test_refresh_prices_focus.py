import json


def test_refresh_prices_prefers_daily_focus_over_legacy_today_focus(tmp_path):
    from stock_team.data_ingest.refresh_prices import _load_focus_symbols

    config = tmp_path / "config"
    config.mkdir()
    (config / "daily_focus.json").write_text(
        json.dumps({"focus_stocks": ["COHR", "VST"]}),
        encoding="utf-8",
    )
    (config / "today_focus.json").write_text(
        json.dumps(["OLD"]),
        encoding="utf-8",
    )

    assert _load_focus_symbols(str(tmp_path)) == ["COHR", "VST"]


def test_refresh_prices_falls_back_to_today_focus_when_daily_focus_missing(tmp_path):
    from stock_team.data_ingest.refresh_prices import _load_focus_symbols

    config = tmp_path / "config"
    config.mkdir()
    (config / "today_focus.json").write_text(
        json.dumps(["NOW", "GOOGL"]),
        encoding="utf-8",
    )

    assert _load_focus_symbols(str(tmp_path)) == ["NOW", "GOOGL"]
