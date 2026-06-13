import json


def test_updated_symbols_from_live_status_prefers_focus_symbols_with_detail(tmp_path):
    from stock_team.server.dashboard_server import updated_symbols_from_live_status

    path = tmp_path / "watchlist_live_status.json"
    path.write_text(json.dumps({
        "focus_symbols": ["NOW", "VST", "MISSING"],
        "symbols_detail": {
            "NOW": {"current_price": 99.92},
            "VST": {"current_price": 164.56},
            "CRM": {"current_price": 179.08},
        },
    }), encoding="utf-8")

    assert updated_symbols_from_live_status(str(path)) == ["NOW", "VST"]


def test_updated_symbols_from_live_status_falls_back_to_all_details(tmp_path):
    from stock_team.server.dashboard_server import updated_symbols_from_live_status

    path = tmp_path / "watchlist_live_status.json"
    path.write_text(json.dumps({
        "symbols_detail": {
            "COHR": {"current_price": 381.35},
            "GOOGL": {"current_price": 388.88},
        },
    }), encoding="utf-8")

    assert updated_symbols_from_live_status(str(path)) == ["COHR", "GOOGL"]


def test_price_refresh_state_sync_updates_positions_snapshot_and_nodes(tmp_path):
    from stock_team.server.dashboard_server import sync_price_refresh_state

    (tmp_path / "config").mkdir()
    (tmp_path / "findings" / "symbols" / "NOW").mkdir(parents=True)
    (tmp_path / "learning").mkdir()
    (tmp_path / "config" / "positions.json").write_text(json.dumps({
        "cash": 1000,
        "positions": {
            "NOW": {"shares": 2, "cost": 90},
            "VST": {"shares": 1, "cost": 150, "broker_last_price": 159},
        },
    }), encoding="utf-8")
    (tmp_path / "findings" / "watchlist_live_status.json").write_text(json.dumps({
        "refreshed_at": "2026-05-27 12:24:24",
        "focus_symbols": ["NOW", "VST"],
        "symbols_detail": {
            "NOW": {
                "current_price": 99.92,
                "buy_zone": {"min_price": 94, "max_price": 96},
                "hard_stop": 82,
                "target_price": 135,
                "status_cn": "接近黄金击球区",
            },
            "VST": {"current_price": 164.56},
        },
    }), encoding="utf-8")

    result = sync_price_refresh_state(str(tmp_path))

    assert result["updated"] == ["NOW", "VST"]
    positions = json.loads((tmp_path / "config" / "positions.json").read_text(encoding="utf-8"))
    assert positions["positions"]["NOW"]["broker_last_price"] == 99.92
    assert positions["positions"]["VST"]["broker_last_price"] == 164.56

    cache = json.loads((tmp_path / "learning" / "dashboard_cache.json").read_text(encoding="utf-8"))
    assert cache["intraday"]["NOW"]["price_now"]["price"] == 99.92
    assert cache["intraday"]["VST"]["price_now"]["price"] == 164.56

    snapshot = json.loads((tmp_path / "findings" / "portfolio_snapshot_current.json").read_text(encoding="utf-8"))
    assert [row["sym"] for row in snapshot["positions_detail"]] == ["NOW", "VST"]
    assert snapshot["positions_detail"][0]["cur_price"] == 99.92
    assert snapshot["totals"]["holdings_value"] == 364.4
    assert snapshot["totals"]["total_value"] == 1364.4

    nodes = json.loads((tmp_path / "findings" / "symbols" / "NOW" / "current_nodes.json").read_text(encoding="utf-8"))
    assert nodes["nodes"]["entry_base"]["price"] == 96
    assert nodes["nodes"]["hard_stop"]["price"] == 82
    assert nodes["nodes"]["target"]["price"] == 135
