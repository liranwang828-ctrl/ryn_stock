import sys, os, json

def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_dashboard_cache_round_trip(tmp_path):
    """dashboard cache should persist and reload the same JSON payload."""
    from stock_team.server.dashboard_cache import load_dashboard_cache, write_dashboard_cache

    payload = {
        "date": "2026-05-24",
        "generated_at": "2026-05-24T09:30:00-04:00",
        "market_clock": {"phase": "盘中", "next_open": "2026-05-25T09:30:00-04:00"},
        "intraday": {
            "NVDA": {
                "price_now": {"price": 220.0, "gate_status": "通过"},
                "plan_vs_now": {"entry_go_status": "go"},
            }
        },
    }

    write_dashboard_cache(str(tmp_path), payload)

    assert load_dashboard_cache(str(tmp_path)) == payload


def test_build_dashboard_context_uses_dashboard_cache_when_findings_missing(tmp_path):
    """dashboard context should fall back to cached operational state when findings are absent."""
    from stock_team.server.dashboard_cache import write_dashboard_cache
    from stock_team.server.dashboard_writer import build_dashboard_context

    date = "2026-05-24"
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})

    write_dashboard_cache(str(base), {
        "date": date,
        "generated_at": "2026-05-24T09:45:00-04:00",
        "market_clock": {"phase": "盘中", "next_open": None},
        "intraday": {
            "NVDA": {
                "price_now": {
                    "price": 220.0,
                    "chg_pct": 1.5,
                    "gate_status": "通过",
                    "master_avg": 6.0,
                    "master_consensus": "buy",
                },
                "plan_vs_now": {"entry_go_status": "go"},
            }
        },
        "daily_plan": {
            "date": date,
            "per_symbol": {
                "NVDA": {"entry_go_status": "go"},
            },
        },
    })

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))

    assert ctx["intraday"]["NVDA"]["price_now"]["price"] == 220.0
    assert ctx["intraday"]["NVDA"]["price_now"]["master_consensus"] == "buy"
    assert ctx["intraday"]["NVDA"]["plan_vs_now"]["entry_go_status"] == "go"
    assert ctx["daily_plan"]["per_symbol"]["NVDA"]["entry_go_status"] == "go"


def test_update_latest_prices_merges_intraday_cache(tmp_path):
    """manual price refresh should persist latest prices without dropping cached fields."""
    from stock_team.server.dashboard_cache import load_dashboard_cache, update_latest_prices, write_dashboard_cache

    write_dashboard_cache(str(tmp_path), {
        "intraday": {
            "MRVL": {
                "price_now": {"gate_status": "pending", "master_avg": 5.0},
                "plan_vs_now": {"entry_go_status": "pending"},
            }
        }
    })

    update_latest_prices(str(tmp_path), {
        "MRVL": {"price": 196.51, "chg_pct": 3.05, "source": "manual_yfinance"},
        "AMD": {"price": 164.20, "chg_pct": -0.5, "source": "manual_yfinance"},
    }, asof="2026-05-26T09:00:00+08:00")

    cache = load_dashboard_cache(str(tmp_path))

    assert cache["intraday"]["MRVL"]["price_now"]["price"] == 196.51
    assert cache["intraday"]["MRVL"]["price_now"]["gate_status"] == "pending"
    assert cache["intraday"]["MRVL"]["price_now"]["price_source"] == "manual_yfinance"
    assert cache["intraday"]["MRVL"]["meta"]["price_asof"] == "2026-05-26T09:00:00+08:00"
    assert cache["intraday"]["AMD"]["price_now"]["price"] == 164.20
