def test_cleanup_legacy_position_metadata_prefers_ibkr_live_api():
    from stock_team.core.ibkr_monitor import _cleanup_legacy_position_metadata

    payload = {
        "cash": 10960.0,
        "cash_note": "manual value",
        "broker_snapshot": {"source": "user_manual_update"},
        "positions_update_note": "from screenshots",
        "market_trade_date": "2026-06-02",
        "positions": {
            "GOOGL": {
                "shares": 8,
                "cost": 384.305,
                "broker_price_source": "manual_watchlist_refresh",
            },
            "VST": {
                "shares": 10,
                "cost": 159.71,
                "note": "Auto-added by IBKR Monitor",
                "broker_price_source": "ibkr_screenshot_user_report",
            },
        },
    }

    cleaned = _cleanup_legacy_position_metadata(payload)

    assert "cash_note" not in cleaned
    assert "broker_snapshot" not in cleaned
    assert "positions_update_note" not in cleaned
    assert "market_trade_date" not in cleaned
    assert cleaned["account_sync_source"] == "ibkr_live_api"
    assert cleaned["positions_source"] == "ibkr_live_api"
    assert cleaned["trade_history_source"] == "ibkr_tws_api_reqExecutions"
    assert cleaned["positions"]["GOOGL"]["position_source"] == "ibkr_live_api"
    assert "broker_price_source" not in cleaned["positions"]["GOOGL"]
    assert cleaned["positions"]["VST"]["note"] == "Auto-added from IBKR live sync"
