# tests/unit/core/test_cli.py
import os
import sys
import subprocess
import json
import pytest
import time
from datetime import datetime, timezone
from types import SimpleNamespace

# Base is stock_team folder
STOCK_TEAM_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Parent is the workspace root where stock_team can be imported
WORKSPACE_DIR = os.path.dirname(STOCK_TEAM_DIR)
PYTHON = sys.executable

def get_env():
    env = os.environ.copy()
    # Add workspace directory to python path for the subprocess
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = WORKSPACE_DIR + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = WORKSPACE_DIR
    return env


def _brain_universe(items, **overrides):
    payload = {
        "source_inputs": {
            "positions": [],
            "prior_review": {
                "path": "wiki/journals/2026-06-05-major-drawdown-review.md",
                "status": "reviewed_for_stage0_input",
            },
            "cognition_state": {
                "permission_basis": "major_drawdown_recovery_boundary",
                "active_risks": ["trapped_leveraged_position_review_required"],
            },
        },
        "permission_state_before_open": "Red",
        "forbidden_actions": [
            "new_short_term_trade",
            "new_leveraged_product_trade",
            "loss_repair_reentry",
        ],
        "positions": items,
    }
    payload.update(overrides)
    return payload


def test_investing_os_home_prefers_environment_override(monkeypatch, tmp_path):
    """Unified workspace callers may explicitly select the brain repository."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    expected = tmp_path / "custom-investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(expected))

    assert cli._investing_os_home() == str(expected.resolve())


def test_investing_os_home_defaults_to_workspace_sibling(monkeypatch, tmp_path):
    """A copied stock_team should discover investing-os beside its package directory."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    stock_team_dir = tmp_path / "stock_team"
    stock_team_dir.mkdir()
    monkeypatch.delenv("INVESTING_OS_HOME", raising=False)
    monkeypatch.setattr(cli, "BASE", str(stock_team_dir))

    assert cli._investing_os_home() == str((tmp_path / "investing-os").resolve())


def test_intraday_refresh_subprocess_timeout_is_reported(monkeypatch):
    """Runtime refresh subprocess must time out instead of blocking a dashboard iteration forever."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout"))

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    warnings = cli._refresh_intraday_runtime_data(SimpleNamespace(refresh_timeout_seconds=3))

    assert warnings == ["runtime_refresh_timeout_after_3s"]


def test_intraday_data_source_health_reflects_ibkr_and_warnings(monkeypatch):
    """Dashboard health should not report IBKR active or verified status when probes/warnings say otherwise."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    monkeypatch.setattr(cli, "_probe_ibkr_active", lambda: False)
    monkeypatch.setattr(cli, "_probe_polygon_active", lambda: True)
    health = cli._build_intraday_data_source_health(
        uses_fallback=False,
        warnings=["runtime_refresh_timeout_after_1s"],
    )

    assert health["ibkr_active"] is False
    assert health["polygon_active"] is True
    assert health["status"] == "warning_runtime_refresh_timeout"
    assert health["warnings"] == ["runtime_refresh_timeout_after_1s"]


def test_intraday_data_source_health_reports_polygon_runtime_gaps(monkeypatch):
    """Missing Polygon runtime bars should produce a degraded health state, not verified."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    monkeypatch.setattr(cli, "_probe_ibkr_active", lambda: True)
    monkeypatch.setattr(cli, "_probe_polygon_active", lambda: True)
    health = cli._build_intraday_data_source_health(
        uses_fallback=True,
        warnings=["MU_polygon_runtime_bars_unavailable"],
    )

    assert health["polygon_active"] is True
    assert health["yfinance_fallback_active"] is True
    assert health["status"] == "warning_yfinance_fallback_used"


def test_load_premarket_snapshot_adapter_accepts_dashboard_list_shape(tmp_path):
    """Stage 0 should accept the dashboard snapshot form without requiring manual JSON reshaping."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({
        "as_of_et": "2026-06-15T09:20:00-04:00",
        "window": "pre_market_before_09_30_ET",
        "markets": [
            {"symbol": "QQQ", "last": "736.7", "premarket_change_pct": "2.13", "note": "strong"},
            {"symbol": "SPY", "last": "751.15", "premarket_change_pct": "1.27", "note": "firm"},
        ],
        "themes": "ai_infrastructure, cloud",
        "catalysts": "Focus on opening trend.",
        "notes": "dashboard shape",
    }), encoding="utf-8")

    as_of_et = cli._parse_stage0_as_of("2026-06-15T09:20:00-04:00")
    markets, themes, catalysts, missing = cli._load_premarket_snapshot_adapter(str(snapshot), as_of_et)

    assert missing == []
    assert markets[0]["symbol"] == "QQQ"
    assert markets[0]["price"] == 736.7
    assert markets[0]["yesterday_change_pct"] == 2.13
    assert themes[0]["theme"] == "ai_infrastructure"
    assert themes[0]["proxy"] == "SMH"
    assert catalysts[0]["type"] == "dashboard_note"
    assert catalysts[0]["title"] == "Focus on opening trend."


def test_enrich_premarket_snapshot_with_history_backfills_missing_context():
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    markets = [
        {
            "symbol": "QQQ",
            "label": "Nasdaq 100 proxy",
            "price": 736.7,
            "yesterday_change_pct": 2.13,
            "return_5d": None,
            "return_20d": None,
            "volume_ratio": None,
            "source": "pre_market_snapshot_adapter",
        }
    ]
    themes = [
        {
            "theme": "semiconductors",
            "proxy": "SOXX",
            "return_5d": None,
            "return_20d": None,
            "source": "pre_market_snapshot_adapter",
        }
    ]
    history_context = {
        "QQQ": ({"return_5d": 4.2, "return_20d": 8.5, "volume_ratio": 1.3, "source": "polygon_cache"}, []),
        "SOXX": ({"return_5d": 6.1, "return_20d": 11.4, "source": "polygon_cache"}, []),
    }

    enriched_markets, enriched_themes, missing = cli._enrich_premarket_snapshot_with_history(
        markets,
        themes,
        history_context,
    )

    assert missing == []
    assert enriched_markets[0]["yesterday_change_pct"] == 2.13
    assert enriched_markets[0]["return_5d"] == 4.2
    assert enriched_markets[0]["return_20d"] == 8.5
    assert enriched_markets[0]["volume_ratio"] == 1.3
    assert enriched_markets[0]["source"] == "pre_market_snapshot_adapter+polygon_cache"
    assert enriched_themes[0]["return_5d"] == 6.1
    assert enriched_themes[0]["return_20d"] == 11.4
    assert enriched_themes[0]["source"] == "pre_market_snapshot_adapter+polygon_cache"


def test_requested_theme_proxies_maps_power_theme():
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    requested_themes, theme_proxies, missing = cli._requested_theme_proxies("power,memory")

    assert requested_themes == ["power", "memory"]
    assert theme_proxies["power"] == "XLU"
    assert theme_proxies["memory"] == "MU"
    assert missing == []


def test_runtime_price_fallback_warning_distinguishes_bar_gaps(monkeypatch):
    """Unavailable minute bars should not be reported as a Polygon API key failure."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    monkeypatch.setattr(cli, "_probe_polygon_active", lambda: True)
    warning = cli._runtime_price_fallback_warning(["MU_polygon_runtime_bars_unavailable"])

    assert "polygon_runtime_bars_unavailable_for_requested_date_or_symbols" in warning
    assert "api_key_missing" not in warning


def test_polygon_probe_uses_requests_session_and_cache(monkeypatch):
    """Polygon health probe should use a reusable requests session and short TTL cache."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    calls = []

    class FakeResponse:
        ok = True

        def json(self):
            return {"status": "OK"}

    class FakeSession:
        def get(self, url, params=None, timeout=None):
            calls.append({"url": url, "params": params, "timeout": timeout})
            return FakeResponse()

    monkeypatch.setattr(cli, "get_api_key", lambda: "fake-key")
    monkeypatch.setattr(cli, "_POLYGON_HEALTH_CACHE", {"checked_at": 0, "active": False})

    assert cli._probe_polygon_active(session=FakeSession(), now=100.0) is True
    assert cli._probe_polygon_active(session=FakeSession(), now=101.0) is True
    assert len(calls) == 1
    assert calls[0]["timeout"] <= 3


def test_polygon_runtime_snapshot_uses_minute_bars_and_cache(monkeypatch):
    """Polygon runtime snapshots should derive price/VWAP/volume context from minute aggregates."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    calls = []

    class FakeResponse:
        ok = True

        def json(self):
            return {
                "status": "OK",
                "results": [
                    {"t": 1000, "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "v": 1000, "vw": 100.0},
                    {"t": 2000, "o": 100.0, "h": 104.0, "l": 99.0, "c": 103.0, "v": 3000, "vw": 102.0},
                ],
            }

    class FakeSession:
        def get(self, url, params=None, timeout=None):
            calls.append({"url": url, "params": params, "timeout": timeout})
            return FakeResponse()

    monkeypatch.setattr(cli, "get_api_key", lambda: "fake-key")
    monkeypatch.setattr(cli, "_POLYGON_RUNTIME_CACHE", {})

    snapshots, warnings = cli._fetch_polygon_runtime_snapshots(
        ["MU"], "2026-06-05", session=FakeSession(), now=100.0
    )
    cached, cached_warnings = cli._fetch_polygon_runtime_snapshots(
        ["MU"], "2026-06-05", session=FakeSession(), now=101.0
    )

    assert warnings == []
    assert cached_warnings == []
    assert len(calls) == 1
    assert calls[0]["timeout"] <= 3
    assert snapshots["MU"]["current_price"] == 103.0
    assert snapshots["MU"]["vwap"] == 101.5
    assert snapshots["MU"]["volume_ratio"] == 1.5
    assert snapshots["MU"]["source"] == "polygon_1m_aggregates"
    assert cached == snapshots


def test_polygon_runtime_snapshot_fetches_symbols_concurrently(monkeypatch):
    """Runtime bar fetches should not wait for each ticker sequentially."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    class FakeResponse:
        ok = True

        def json(self):
            return {
                "status": "OK",
                "results": [
                    {"t": 1000, "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "v": 1000, "vw": 100.0}
                ],
            }

    class SlowSession:
        def get(self, url, params=None, timeout=None):
            time.sleep(0.2)
            return FakeResponse()

    monkeypatch.setattr(cli, "get_api_key", lambda: "fake-key")
    monkeypatch.setattr(cli, "_POLYGON_RUNTIME_CACHE", {})

    started = time.monotonic()
    snapshots, warnings = cli._fetch_polygon_runtime_snapshots(
        ["MU", "COHR"], "2026-06-05", session=SlowSession(), now=100.0
    )
    elapsed = time.monotonic() - started

    assert warnings == []
    assert set(snapshots) == {"MU", "COHR"}
    assert elapsed < 0.35


def test_fetch_polygon_premarket_bars_filters_to_stage0_window(monkeypatch):
    """Stage0 premarket bars must be timestamp-proven before the regular open."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    def ts_ms(hour, minute):
        return int(datetime(2026, 6, 16, hour, minute, tzinfo=timezone.utc).timestamp() * 1000)

    class FakeResponse:
        ok = True

        def json(self):
            return {
                "status": "OK",
                "results": [
                    {"t": ts_ms(8, 0), "c": 100.0, "v": 100},    # 04:00 ET
                    {"t": ts_ms(13, 20), "c": 106.0, "v": 300},  # 09:20 ET
                    {"t": ts_ms(13, 31), "c": 109.0, "v": 900},  # 09:31 ET, reject
                ],
            }

    class FakeSession:
        def get(self, url, params=None, timeout=None):
            return FakeResponse()

    as_of = cli._parse_stage0_as_of("2026-06-16T09:20:00-04:00")
    bars, warning = cli._fetch_polygon_premarket_bars(
        "QQQ", "2026-06-16", as_of, "test-key", session=FakeSession()
    )

    assert warning is None
    assert [bar["close"] for bar in bars] == [100.0, 106.0]
    assert bars[-1]["time_et"].isoformat().startswith("2026-06-16T09:20:00")


def test_fetch_paid_premarket_row_uses_timestamp_proven_minute_bars(monkeypatch):
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    as_of = cli._parse_stage0_as_of("2026-06-16T09:20:00-04:00")

    monkeypatch.setattr(
        "stock_team.agents.macro_strategy.fetch_polygon_daily_aggs",
        lambda symbol, api_key, days=40: [
            {"t": int(datetime(2026, 6, 12, tzinfo=timezone.utc).timestamp() * 1000), "c": 100.0, "v": 1000},
            {"t": int(datetime(2026, 6, 13, tzinfo=timezone.utc).timestamp() * 1000), "c": 101.0, "v": 1100},
            {"t": int(datetime(2026, 6, 14, tzinfo=timezone.utc).timestamp() * 1000), "c": 102.0, "v": 1200},
            {"t": int(datetime(2026, 6, 15, tzinfo=timezone.utc).timestamp() * 1000), "c": 105.0, "v": 1500},
        ],
    )
    monkeypatch.setattr(
        cli,
        "_fetch_polygon_premarket_bars",
        lambda symbol, date_str, stage0_as_of_et, api_key: (
            [
                {"time_et": as_of.replace(hour=8, minute=0), "close": 104.0, "volume": 100},
                {"time_et": as_of.replace(hour=9, minute=20), "close": 106.25, "volume": 300},
            ],
            None,
        ),
    )

    row, missing = cli._fetch_paid_premarket_row("QQQ", as_of, "test-key")

    assert missing == []
    assert row["price"] == 106.25
    assert row["prev_close"] == 105.0
    assert row["source"] == "polygon_premarket_1m_aggregates"
    assert row["latest_bar_time_et"].startswith("2026-06-16T09:20:00")


def test_intraday_dashboard_uses_polygon_runtime_snapshot(monkeypatch, tmp_path):
    """Dashboard manifest should expose Polygon runtime source for price/VWAP when available."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    stage0 = tmp_path / "stage0.md"
    stage1 = tmp_path / "stage1.md"
    guidance = tmp_path / "guidance.json"
    manifest = tmp_path / "manifest.json"
    out_md = tmp_path / "dashboard.md"
    html_out = tmp_path / "dashboard.html"
    stage0.write_text("stage0", encoding="utf-8")
    stage1.write_text("stage1", encoding="utf-8")
    guidance.write_text(json.dumps({
        "date": "2026-06-05",
        "derived_from": {
            "stage0_market_context_packet": str(stage0),
            "stage1_plan_evidence_packet": str(stage1),
        },
        "symbols": [
            {
                "symbol": "MU",
                "role": "mid_term_swing_candidate",
                "intraday_mode": "conditional_action_allowed",
                "brain_permission": {"status": "conditional", "scope": "test"},
                "evidence_conditions_to_monitor": [
                    {"condition_id": "volume_confirms", "description": "rebound attempt has volume confirmation."}
                ],
                "levels_to_monitor": [
                    {"level_id": "vwap_anchor", "meaning": "trigger_review", "formula_or_value": "VWAP"}
                ],
            }
        ],
        "stock_team_dashboard_request": {"latest_manifest_path": str(manifest)},
    }), encoding="utf-8")

    monkeypatch.setattr(cli, "_fetch_polygon_runtime_snapshots", lambda symbols, date_str: ({
        "MU": {
            "current_price": 103.0,
            "vwap": 101.5,
            "volume_ratio": 1.5,
            "source": "polygon_1m_aggregates",
            "source_timestamp": "2026-06-05T14:30:00Z",
            "latest_bar_timestamp": 123456,
        }
    }, []))
    monkeypatch.setattr(cli, "_probe_polygon_active", lambda: True)
    monkeypatch.setattr(cli, "_probe_ibkr_active", lambda: True)

    cli.handle_intraday_dashboard(SimpleNamespace(
        guidance=str(guidance),
        out=str(out_md),
        html_out=str(html_out),
        refresh=False,
        loop=False,
    ))

    data = json.loads(manifest.read_text(encoding="utf-8"))
    runtime_data = data["symbol_condition_status"]["MU"]["runtime_data"]
    assert runtime_data["current_price_source"] == "polygon_1m_aggregates"
    assert runtime_data["vwap_source"] == "polygon_1m_aggregates"
    assert runtime_data["volume_ratio"] == 1.5
    assert data["symbol_condition_status"]["MU"]["conditions"][0]["status"] == "pass"
    assert data["symbol_condition_status"]["MU"]["monitored_levels"][0]["computed_value"] == 101.5

def test_cli_help():
    """Verify that python -m stock_team.cli --help prints usage and exits cleanly."""
    res = subprocess.run([PYTHON, "-m", "stock_team.cli", "--help"], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "premarket" in res.stdout
    assert "premarket-snapshot" in res.stdout
    assert "trade-evidence" in res.stdout
    assert "intraday-snapshot" in res.stdout
    assert "company-packet" in res.stdout
    assert "industry-packet" in res.stdout
    assert "backtest-rs-rebound" in res.stdout
    assert "tactic-backtest" in res.stdout
    assert "stage-context-backtest" in res.stdout
    assert "market-context" in res.stdout


def test_cli_stage_context_backtest_generation(tmp_path):
    """Stage context backtest should write evidence-only Markdown and JSON packets."""
    request = tmp_path / "stage_context_request.json"
    request.write_text(json.dumps({
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_cli_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["qqq_regime", "vix_regime", "permission_state"],
        "data": {
            "mode": "fixture_events",
            "events": [
                {
                    "date": "2026-01-05",
                    "symbol": "MU",
                    "tactic_id": "vwap_reclaim",
                    "return_pct": 2.0,
                    "mae_pct": -0.4,
                    "mfe_pct": 2.7,
                    "context": {
                        "qqq_regime": "qqq_uptrend",
                        "vix_regime": "vix_low_falling",
                        "permission_state": "Yellow"
                    }
                },
                {
                    "date": "2026-01-08",
                    "symbol": "COHR",
                    "tactic_id": "vwap_reclaim",
                    "return_pct": -1.5,
                    "mae_pct": -2.1,
                    "mfe_pct": 0.4,
                    "context": {
                        "qqq_regime": "qqq_downtrend",
                        "vix_regime": "vix_high_rising",
                        "permission_state": "Red"
                    }
                }
            ]
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False
        }
    }), encoding="utf-8")
    out_md = tmp_path / "stage_context_packet.md"
    out_json = tmp_path / "stage_context_packet.json"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "stage-context-backtest",
        "--request", str(request),
        "--out", str(out_md),
        "--json-out", str(out_json),
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    assert out_md.exists()
    assert out_json.exists()
    content = out_md.read_text(encoding="utf-8")
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "packet_type: stage_context_backtest_evidence_packet" in content
    assert "Evidence Only" in content
    assert data["summary"]["n_events"] == 2

def test_cli_premarket_help():
    """Verify premarket subcommand help works."""
    res = subprocess.run([PYTHON, "-m", "stock_team.cli", "premarket", "--help"], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "--watchlist" in res.stdout
    assert "--out" in res.stdout

def test_cli_tactic_backtest_generation(tmp_path):
    """Unified tactic-backtest should write evidence-only markdown and JSON packets."""
    request = tmp_path / "tactic_request.json"
    request.write_text(json.dumps({
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "tactic_id": "rs_pullback_rebound_intraday",
        "symbols": ["MU"],
        "date_range": {"start": "2026-01-01", "end": "2026-02-28"},
        "strategy": {
            "entry_model": {"type": "channel_reclaim", "indicator": "vwap"},
            "filters": [{"type": "relative_volume", "min_volume_ratio": 1.2}],
            "exit_model": {"type": "fixed_pct"}
        },
        "hyperparameters": {
            "min_volume_ratio": 1.2,
            "stop_loss_pct": 1.5,
            "take_profit_pct": 3.0
        },
        "validation": {
            "windows": [
                {"name": "train", "start": "2026-01-01", "end": "2026-01-31"},
                {"name": "test", "start": "2026-02-01", "end": "2026-02-28"}
            ],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 1
        },
        "data": {
            "mode": "fixture_events",
            "events": [
                {
                    "symbol": "MU",
                    "entry_time": "2026-01-09T10:15:00-05:00",
                    "exit_time": "2026-01-09T15:45:00-05:00",
                    "return_pct": 2.0,
                    "mae_pct": -0.5,
                    "mfe_pct": 2.4,
                    "market_regime": "qqq_uptrend_low_vix"
                },
                {
                    "symbol": "MU",
                    "entry_time": "2026-02-09T10:15:00-05:00",
                    "exit_time": "2026-02-09T15:45:00-05:00",
                    "return_pct": -1.0,
                    "mae_pct": -1.3,
                    "mfe_pct": 0.6,
                    "market_regime": "high_volume_risk_off"
                }
            ]
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False
        }
    }), encoding="utf-8")
    out_md = tmp_path / "tactic_packet.md"
    out_json = tmp_path / "tactic_packet.json"

    started = time.monotonic()
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "tactic-backtest",
        "--request", str(request),
        "--out", str(out_md),
        "--json-out", str(out_json),
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    assert out_md.exists()
    assert out_json.exists()
    content = out_md.read_text(encoding="utf-8")
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "packet_type: tactic_backtest_evidence_packet" in content
    assert "No Permission Decision" in content
    assert data["summary"]["n_trades"] == 2

def test_cli_tactic_backtest_ohlcv_fixture_generation(tmp_path):
    """Unified tactic-backtest should generate events from intraday OHLCV fixtures."""
    request = tmp_path / "tactic_ohlcv_request.json"
    request.write_text(json.dumps({
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "tactic_id": "rs_pullback_rebound_intraday",
        "symbols": ["MU"],
        "date_range": {"start": "2026-01-09", "end": "2026-01-09"},
        "strategy": {
            "entry_model": {
                "type": "channel_reclaim",
                "indicator": "vwap"
            },
            "filters": [
                {
                    "type": "relative_volume",
                    "min_volume_ratio": 2.0
                }
            ],
            "exit_model": {
                "type": "fixed_pct"
            }
        },
        "hyperparameters": {
            "action_window_start": "10:00",
            "action_window_end": "11:00",
            "min_volume_ratio": 2.0,
            "take_profit_pct": 3.0,
            "stop_loss_pct": 1.5
        },
        "validation": {
            "windows": [{"name": "test", "start": "2026-01-09", "end": "2026-01-09"}],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 1
        },
        "data": {
            "mode": "intraday_ohlcv_fixture",
            "bars": {
                "MU": [
                    {"timestamp": "2026-01-09T09:30:00-05:00", "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.0, "volume": 1000, "market_regime": "qqq_uptrend_low_vix"},
                    {"timestamp": "2026-01-09T09:35:00-05:00", "open": 100.0, "high": 100.2, "low": 98.0, "close": 98.5, "volume": 1200, "market_regime": "qqq_uptrend_low_vix"},
                    {"timestamp": "2026-01-09T09:40:00-05:00", "open": 98.5, "high": 99.0, "low": 98.1, "close": 98.6, "volume": 800, "market_regime": "qqq_uptrend_low_vix"},
                    {"timestamp": "2026-01-09T10:05:00-05:00", "open": 98.6, "high": 101.5, "low": 98.4, "close": 101.2, "volume": 5000, "market_regime": "qqq_uptrend_low_vix"},
                    {"timestamp": "2026-01-09T15:55:00-05:00", "open": 101.2, "high": 103.2, "low": 101.0, "close": 102.8, "volume": 1800, "market_regime": "qqq_uptrend_low_vix"}
                ]
            }
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False
        }
    }), encoding="utf-8")
    out_md = tmp_path / "tactic_ohlcv_packet.md"
    out_json = tmp_path / "tactic_ohlcv_packet.json"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "tactic-backtest",
        "--request", str(request),
        "--out", str(out_md),
        "--json-out", str(out_json),
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["data_mode"] == "intraday_ohlcv_fixture"
    assert data["events"][0]["trigger"] == "channel_reclaim_vwap"

def test_cli_market_context_requires_brain_universe(tmp_path):
    """Stage 0 must be anchored to a brain-provided universe."""
    out_file = tmp_path / "market_context.md"
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-06",
        "--offline-fixture", str(tmp_path / "missing_fixture.json"),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode != 0
    assert "--universe" in res.stderr

def test_cli_market_context_requires_brain_precondition_state(tmp_path):
    """Stage 0 must not start from a naked ticker universe without brain-side state."""
    fixture = tmp_path / "market_fixture.json"
    fixture.write_text(json.dumps({
        "markets": {
            "QQQ": {"price": 500.0, "prev_close": 490.0, "source": "fixture"}
        },
        "themes": {
            "memory": {"proxy": "MU", "return_5d": -2.0, "return_20d": 12.0, "source": "fixture"}
        }
    }), encoding="utf-8")
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps({
        "positions": [
            {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "candidate_only"}
        ]
    }), encoding="utf-8")
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-06",
        "--themes", "memory",
        "--offline-fixture", str(fixture),
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode != 0
    assert "missing_brain_precondition_state" in res.stderr
    assert "source_inputs.positions" in res.stderr
    assert not out_file.exists()

def test_cli_market_context_live_requires_premarket_as_of(tmp_path):
    """Live Stage 0 must declare the pre-market as-of time before data collection."""
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps(_brain_universe([
            {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "candidate_only"}
    ])), encoding="utf-8")
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-08",
        "--themes", "memory",
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode != 0
    assert "--as-of is required" in res.stderr
    assert not out_file.exists()

def test_cli_market_context_rejects_post_open_as_of(tmp_path):
    """Stage 0 must not be reconstructed from post-open or post-close data."""
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps(_brain_universe([
            {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "candidate_only"}
    ])), encoding="utf-8")
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-08",
        "--as-of", "2026-06-08T09:30:00-04:00",
        "--themes", "memory",
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode != 0
    assert "Stage 0 as-of must be before 09:30 ET" in res.stderr
    assert not out_file.exists()

def test_cli_market_context_live_fails_without_premarket_snapshot(tmp_path):
    """A valid Stage 0 cannot be backfilled from live daily data after the fact."""
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps(_brain_universe([
            {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "candidate_only"}
    ])), encoding="utf-8")
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-08",
        "--as-of", "2026-06-08T09:20:00-04:00",
        "--themes", "memory",
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode != 0
    assert "missing_pre_market_data" in res.stderr
    assert not out_file.exists()

def test_cli_market_context_live_uses_premarket_snapshot_adapter(tmp_path):
    """Live Stage 0 may write a packet only from an explicit pre-market snapshot adapter."""
    as_of = "2026-06-08T09:20:00-04:00"
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps(_brain_universe([
            {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "candidate_only"},
            {"symbol": "COHR", "role": "swing", "theme": "optical", "research_status": "researched_draft"}
    ])), encoding="utf-8")
    snapshot = tmp_path / "premarket_snapshot.json"
    snapshot.write_text(json.dumps({
        "as_of_et": as_of,
        "window": "pre_market_before_09_30_ET",
        "markets": {
            "QQQ": {"price": 719.2, "prev_close": 705.06, "return_5d": -1.2, "return_20d": 1.4, "volume_ratio": 0.3, "source": "polygon_premarket_snapshot"},
            "SPY": {"price": 742.1, "prev_close": 737.55, "return_5d": -0.7, "return_20d": 0.8, "volume_ratio": 0.2, "source": "polygon_premarket_snapshot"},
            "IWM": {"price": 285.8, "prev_close": 281.65, "return_5d": -0.4, "return_20d": 0.6, "volume_ratio": 0.2, "source": "polygon_premarket_snapshot"},
            "VIXY": {"price": 23.8, "prev_close": 24.31, "return_5d": -0.9, "return_20d": -12.5, "volume_ratio": 0.4, "source": "polygon_premarket_snapshot"}
        },
        "themes": {
            "memory": {"proxy": "MU", "return_5d": -2.5, "return_20d": 12.0, "source": "polygon_premarket_snapshot"},
            "optical": {"proxy": "LITE", "return_5d": 1.1, "return_20d": 5.2, "source": "polygon_premarket_snapshot"}
        },
        "catalysts": [
            {"type": "macro", "title": "pre-market futures stabilizing", "source": "polygon_premarket_snapshot"}
        ]
    }), encoding="utf-8")
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-08",
        "--as-of", as_of,
        "--pre-market-snapshot", str(snapshot),
        "--themes", "memory,optical",
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    content = out_file.read_text(encoding="utf-8")
    assert "as_of_et: 2026-06-08T09:20:00-04:00" in content
    assert "stage0_window: pre_market_before_09_30_ET" in content
    assert "polygon_premarket_snapshot" in content
    assert "| QQQ | Nasdaq 100 proxy | 719.2 | +2.01%" in content
    assert "| MU | watchlist | memory | candidate_only | -2.50% | +12.00% | evidence mapping only |" in content
    assert "| COHR | swing | optical | researched_draft | +1.10% | +5.20% | evidence mapping only |" in content

def test_cli_market_context_rejects_snapshot_as_of_mismatch(tmp_path):
    """Stage 0 must reject pre-market snapshots from a different as-of time."""
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps(_brain_universe([
            {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "candidate_only"}
    ])), encoding="utf-8")
    snapshot = tmp_path / "premarket_snapshot.json"
    snapshot.write_text(json.dumps({
        "as_of_et": "2026-06-08T09:10:00-04:00",
        "window": "pre_market_before_09_30_ET",
        "markets": {
            "QQQ": {"price": 719.2, "prev_close": 705.06, "source": "polygon_premarket_snapshot"}
        }
    }), encoding="utf-8")
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-08",
        "--as-of", "2026-06-08T09:20:00-04:00",
        "--pre-market-snapshot", str(snapshot),
        "--themes", "memory",
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode != 0
    assert "pre-market snapshot as_of_et must match --as-of" in res.stderr
    assert not out_file.exists()

def test_cli_market_context_accepts_snapshot_with_utf8_bom(tmp_path):
    """Windows-created adapter JSON may include a UTF-8 BOM and should still parse."""
    as_of = "2026-06-08T09:20:00-04:00"
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps(_brain_universe([
            {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "candidate_only"}
    ])), encoding="utf-8")
    snapshot = tmp_path / "premarket_snapshot_bom.json"
    payload = json.dumps({
        "as_of_et": as_of,
        "window": "pre_market_before_09_30_ET",
        "markets": {
            "QQQ": {"price": 719.2, "prev_close": 705.06, "source": "polygon_premarket_snapshot"},
            "SPY": {"price": 742.1, "prev_close": 737.55, "source": "polygon_premarket_snapshot"},
            "IWM": {"price": 285.8, "prev_close": 281.65, "source": "polygon_premarket_snapshot"},
            "VIXY": {"price": 23.8, "prev_close": 24.31, "source": "polygon_premarket_snapshot"}
        },
        "themes": {
            "memory": {"proxy": "MU", "return_5d": -2.5, "return_20d": 12.0, "source": "polygon_premarket_snapshot"}
        }
    })
    snapshot.write_bytes(("\ufeff" + payload).encode("utf-8"))
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-08",
        "--as-of", as_of,
        "--pre-market-snapshot", str(snapshot),
        "--themes", "memory",
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    assert "polygon_premarket_snapshot" in out_file.read_text(encoding="utf-8")

def test_generate_premarket_snapshot_payload_uses_paid_provider_rows(monkeypatch):
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    as_of = cli._parse_stage0_as_of("2026-06-16T09:20:00-04:00")

    monkeypatch.setattr(cli, "get_api_key", lambda: "test-key")

    def fake_fetch(symbol, stage0_as_of_et, api_key):
        assert api_key == "test-key"
        rows = {
            "QQQ": {"price": 736.7, "prev_close": 721.34, "source": "polygon_premarket_snapshot"},
            "SPY": {"price": 751.15, "prev_close": 741.75, "source": "polygon_premarket_snapshot"},
            "IWM": {"price": 297.4, "prev_close": 292.25, "source": "polygon_premarket_snapshot"},
            "VIXY": {"price": 22.47, "prev_close": 23.29, "source": "polygon_premarket_snapshot"},
            "SMH": {"price": 0, "prev_close": 0, "return_5d": 8.18, "return_20d": 16.31, "source": "polygon_premarket_snapshot"},
            "SOXX": {"price": 0, "prev_close": 0, "return_5d": 5.0, "return_20d": 10.0, "source": "polygon_premarket_snapshot"},
            "IGV": {"price": 0, "prev_close": 0, "return_5d": -3.09, "return_20d": 1.0, "source": "polygon_premarket_snapshot"},
            "LITE": {"price": 0, "prev_close": 0, "return_5d": 2.1, "return_20d": 4.3, "source": "polygon_premarket_snapshot"},
            "MU": {"price": 0, "prev_close": 0, "return_5d": 6.2, "return_20d": 12.5, "source": "polygon_premarket_snapshot"},
            "XLU": {"price": 0, "prev_close": 0, "return_5d": 1.1, "return_20d": 3.3, "source": "polygon_premarket_snapshot"},
        }
        return rows[symbol], []

    monkeypatch.setattr(cli, "_fetch_paid_premarket_row", fake_fetch)

    payload = cli._generate_premarket_snapshot_payload(
        "2026-06-16",
        as_of,
        focus_symbols=["AAOX", "MUU", "COHR"],
        themes_text="ai_infrastructure,semiconductors,cloud,optical,memory,power",
        catalysts_text="Manage AAOX and MUU exit timing.",
        notes_text="IBKR positions already synced.",
    )

    assert payload["markets"]["QQQ"]["source"] == "polygon_premarket_snapshot"
    assert payload["markets"]["QQQ"]["price"] == 736.7
    assert payload["themes"]["memory"]["proxy"] == "MU"
    assert payload["themes"]["memory"]["return_20d"] == 12.5
    assert payload["focus_symbols"] == "AAOX, MUU, COHR"

def test_fetch_paid_premarket_row_rejects_generic_snapshot_without_true_premarket_marker(monkeypatch):
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    as_of = cli._parse_stage0_as_of("2026-06-16T09:20:00-04:00")

    monkeypatch.setattr(
        "stock_team.agents.macro_strategy.fetch_polygon_daily_aggs",
        lambda symbol, api_key, days=40: [
            {"c": 100.0, "v": 1000},
            {"c": 101.0, "v": 1100},
            {"c": 102.0, "v": 1200},
            {"c": 103.0, "v": 1300},
            {"c": 104.0, "v": 1400},
            {"c": 105.0, "v": 1500},
        ],
    )
    monkeypatch.setattr(
        "stock_team.agents.macro_strategy.fetch_polygon_snapshot",
        lambda symbol, api_key: {"price": 106.0, "prev_close": 105.0},
    )

    row, missing = cli._fetch_paid_premarket_row("QQQ", as_of, "test-key")

    assert row == {}
    assert "QQQ_snapshot_not_true_premarket" in missing

def test_fetch_paid_premarket_row_accepts_explicit_true_premarket_snapshot(monkeypatch):
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    as_of = cli._parse_stage0_as_of("2026-06-16T09:20:00-04:00")

    monkeypatch.setattr(
        "stock_team.agents.macro_strategy.fetch_polygon_daily_aggs",
        lambda symbol, api_key, days=40: [
            {"c": float(i), "v": float(1000 + i)} for i in range(100, 130)
        ],
    )
    monkeypatch.setattr(
        "stock_team.agents.macro_strategy.fetch_polygon_snapshot",
        lambda symbol, api_key: {
            "price": 131.25,
            "prev_close": 129.0,
            "session": "premarket",
        },
    )

    row, missing = cli._fetch_paid_premarket_row("QQQ", as_of, "test-key")

    assert missing == []
    assert row["price"] == 131.25
    assert row["prev_close"] == 129.0
    assert row["source"] == "polygon_premarket_snapshot"

def test_generate_premarket_snapshot_payload_fails_closed_when_core_market_missing(monkeypatch):
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    as_of = cli._parse_stage0_as_of("2026-06-16T09:20:00-04:00")

    monkeypatch.setattr(cli, "get_api_key", lambda: "test-key")

    def fake_fetch(symbol, stage0_as_of_et, api_key):
        if symbol == "QQQ":
            return {}, ["QQQ_missing"]
        return {"price": 1.0, "prev_close": 1.0, "source": "polygon_premarket_snapshot"}, []

    monkeypatch.setattr(cli, "_fetch_paid_premarket_row", fake_fetch)

    with pytest.raises(ValueError, match="missing_required_paid_premarket_rows"):
        cli._generate_premarket_snapshot_payload(
            "2026-06-16",
            as_of,
            focus_symbols=["AAOX"],
            themes_text="ai_infrastructure",
            catalysts_text="",
            notes_text="",
        )

def test_generate_premarket_snapshot_payload_fetches_rows_concurrently(monkeypatch):
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli

    as_of = cli._parse_stage0_as_of("2026-06-16T09:20:00-04:00")
    monkeypatch.setattr(cli, "get_api_key", lambda: "test-key")

    def fake_fetch(symbol, stage0_as_of_et, api_key):
        time.sleep(0.2)
        return {
            "price": 1.0,
            "prev_close": 1.0,
            "return_5d": 0.0,
            "return_20d": 0.0,
            "source": "polygon_premarket_snapshot",
        }, []

    monkeypatch.setattr(cli, "_fetch_paid_premarket_row", fake_fetch)

    started = time.monotonic()
    payload = cli._generate_premarket_snapshot_payload(
        "2026-06-16",
        as_of,
        focus_symbols=["AAOX", "MUU"],
        themes_text="ai_infrastructure,semiconductors,cloud,optical,memory,power",
        catalysts_text="",
        notes_text="",
    )
    elapsed = time.monotonic() - started

    assert "QQQ" in payload["markets"]
    assert elapsed < 1.5

def test_cli_market_context_generation_from_fixture(tmp_path):
    """Smoke test market-context without network by using an offline fixture."""
    fixture = tmp_path / "market_fixture.json"
    fixture.write_text(json.dumps({
        "markets": {
            "QQQ": {"price": 500.0, "prev_close": 490.0, "return_5d": 2.5, "return_20d": 6.0, "volume_ratio": 1.2, "source": "fixture"},
            "SPY": {"price": 600.0, "prev_close": 594.0, "return_5d": 1.5, "return_20d": 4.0, "volume_ratio": 0.9, "source": "fixture"},
            "VIXY": {"price": 12.0, "prev_close": 12.6, "return_5d": -4.0, "return_20d": -8.0, "volume_ratio": 1.1, "source": "fixture"}
        },
        "themes": {
            "semiconductors": {"proxy": "SOXX", "return_5d": 3.0, "return_20d": 8.0, "source": "fixture"},
            "memory": {"proxy": "MU", "return_5d": 5.0, "return_20d": 12.0, "source": "fixture"}
        },
        "catalysts": [
            {"type": "macro", "title": "FOMC speaker window", "source": "fixture"}
        ]
    }), encoding="utf-8")
    out_file = tmp_path / "market_context.md"
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps(_brain_universe([
            {"symbol": "NVDA", "role": "core", "theme": "semiconductors", "research_status": "researched"},
            {"symbol": "COHR", "role": "swing", "theme": "semiconductors", "research_status": "researched"},
            {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "researched"}
    ])), encoding="utf-8")
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-06",
        "--themes", "semiconductors,memory",
        "--offline-fixture", str(fixture),
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    assert os.path.exists(out_file)
    content = out_file.read_text(encoding="utf-8")
    assert "packet_type: pre_market_environment_packet" in content
    assert "## 1. Yesterday / Recent Market Context" in content
    assert "## 2. Sector / Theme Heat" in content
    assert "## 3. Universe Input Quality" in content
    assert "- universe_count: 3" in content
    assert "- universe_required_fields_complete: true" in content
    assert "## 4. Universe Relevance Map" in content
    assert "NVDA" in content
    assert "COHR" in content
    assert "## 5. Catalysts To Notice" in content
    assert "symbol_selection_recommendation" in content
    assert "buy_sell_hold_recommendation" in content

def test_cli_market_context_reads_symbol_keyed_brain_sheet(tmp_path):
    """Stage 0 must support brain sheets keyed by symbol."""
    fixture = tmp_path / "market_fixture.json"
    fixture.write_text(json.dumps({
        "markets": {
            "QQQ": {"price": 500.0, "prev_close": 490.0, "return_5d": 2.5, "return_20d": 6.0, "volume_ratio": 1.2, "source": "fixture"}
        },
        "themes": {
            "semiconductors": {"proxy": "SOXX", "return_5d": 3.0, "return_20d": 8.0, "source": "fixture"},
            "memory": {"proxy": "MU", "return_5d": -2.0, "return_20d": 12.0, "source": "fixture"}
        }
    }), encoding="utf-8")
    brain_sheet = tmp_path / "brain_sheet.json"
    brain_sheet.write_text(json.dumps(_brain_universe([], **{
        "MU": {"symbol": "MU", "role": "watchlist", "theme": "memory", "research_status": "researched"},
        "NVDA": {"symbol": "NVDA", "role": "core", "theme": "semiconductors", "research_status": "researched"}
    })), encoding="utf-8")
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-06",
        "--themes", "semiconductors,memory",
        "--offline-fixture", str(fixture),
        "--universe", str(brain_sheet),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    content = out_file.read_text(encoding="utf-8")
    assert "| MU | watchlist | memory | researched | -2.00% | +12.00% | evidence mapping only |" in content
    assert "| NVDA | core | semiconductors | researched | +3.00% | +8.00% | evidence mapping only |" in content

def test_cli_market_context_reports_universe_field_gaps(tmp_path):
    """Stage 0 should report incomplete brain universe metadata without guessing it."""
    fixture = tmp_path / "market_fixture.json"
    fixture.write_text(json.dumps({
        "markets": {
            "QQQ": {"price": 500.0, "prev_close": 490.0, "return_5d": 2.5, "return_20d": 6.0, "volume_ratio": 1.2, "source": "fixture"}
        },
        "themes": {
            "memory": {"proxy": "MU", "return_5d": -2.0, "return_20d": 12.0, "source": "fixture"}
        }
    }), encoding="utf-8")
    universe = tmp_path / "universe.json"
    universe.write_text(json.dumps(_brain_universe([
            {"symbol": "MU", "role": "watchlist"}
    ])), encoding="utf-8")
    out_file = tmp_path / "market_context.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "market-context",
        "--date", "2026-06-06",
        "--themes", "memory",
        "--offline-fixture", str(fixture),
        "--universe", str(universe),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    content = out_file.read_text(encoding="utf-8")
    assert "- universe_required_fields_complete: false" in content
    assert "- MU_missing_theme" in content
    assert "- MU_missing_research_status" in content
    assert "| MU | watchlist | — | — | — | — | evidence mapping only |" in content

def test_cli_company_packet_generation(tmp_path):
    """Smoke test company-packet subcommand to verify it generates a valid markdown packet."""
    out_file = tmp_path / "test_company.md"
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "company-packet",
        "--symbol", "NVDA",
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")
    
    assert res.returncode == 0
    assert os.path.exists(out_file)
    
    # Verify packet YAML content
    content = out_file.read_text(encoding="utf-8")
    assert "packet_type: company_research_packet" in content
    assert "status: verified" in content
    assert "forbidden_sections_absent:" in content
    assert "buy_sell_hold_recommendation" in content

def test_cli_intraday_snapshot_generation(tmp_path):
    """Smoke test intraday-snapshot subcommand."""
    out_file = tmp_path / "test_snapshot.md"
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "intraday-snapshot",
        "--symbols", "MSFT,NVDA",
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")
    
    assert res.returncode == 0
    assert os.path.exists(out_file)
    content = out_file.read_text(encoding="utf-8")
    assert "packet_type: runtime_monitor_packet" in content


def test_cli_premarket_generation(tmp_path):
    """Verify premarket command generates plan-evidence-packet.md with correct calculations and rule collisions."""
    watchlist = tmp_path / "watchlist.json"
    watchlist.write_text(json.dumps({
        "default_symbols": ["MU", "NVDA"]
    }), encoding="utf-8")
    
    decision_sheet = tmp_path / "decision_sheet.json"
    decision_sheet.write_text(json.dumps({
        "sheet_type": "pre_market_decision_sheet",
        "stage": "stage_1_symbol_plan_evidence_request",
        "date": "2026-06-06",
        "user_confirmed_focus_pool": ["MU", "NVDA"],
        "permission_state_before_open": "Yellow",
        "symbols": [
            {
                "symbol": "MU",
                "role": "mid_term_swing_candidate",
                "theme": "memory",
                "research_status": "partially_researched",
                "plan_mode": "conditional_action_allowed",
                "key_levels": [
                    {
                        "meaning": "observe_support",
                        "formula_request": "calculate MA20, MA50, previous day high/low"
                    }
                ],
                "rule_collision_contract": [
                    {
                        "rule_id": "yellow_state_conditional_only",
                        "if": "permission_state_before_open == Yellow",
                        "then": "return condition pass/fail only; no automatic action"
                    },
                    {
                        "rule_id": "loss_repair_guard",
                        "if": "symbol interest is connected to trapped leveraged exposure",
                        "then": "flag as risk_context_for_brain_review"
                    }
                ]
            }
        ]
    }), encoding="utf-8")
    
    out_file = tmp_path / "plan_evidence.md"
    
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "premarket",
        "--date", "2026-06-06",
        "--watchlist", str(watchlist),
        "--decision-sheet", str(decision_sheet),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")
    
    assert res.returncode == 0
    assert os.path.exists(out_file)
    
    content = out_file.read_text(encoding="utf-8")
    
    # Verify packet YAML content
    assert "packet_type: plan_evidence_packet" in content
    assert "stage: pre_market_stage_1" in content
    assert "status: fallback_data" in content
    
    # Verify section headers
    assert "## Input Summary" in content
    assert "## Stage 0 Market Context Echo" in content
    assert "## Brain Decision Echo" in content
    assert "## Symbol Factor Calculations" in content
    assert "## Rule Collision Results" in content
    assert "## Forbidden Content Check" in content
    assert "## Machine-Readable Summary" in content
    
    # Verify MU calculations and rule collisions are present
    assert "MU" in content
    assert "yellow_state_conditional_only" in content
    assert "linked_leveraged_exposure_check" in content
    assert "linked_leveraged_exposure_detected" in content
    assert "MUU" in content
    
    # Verify no forbidden sections
    assert "buy / sell / hold recommendation | false" in content


def test_cli_premarket_generation_no_watchlist(tmp_path):
    """Verify premarket command runs successfully without --watchlist if decision-sheet is provided."""
    decision_sheet = tmp_path / "decision_sheet.json"
    decision_sheet.write_text(json.dumps({
        "sheet_type": "pre_market_decision_sheet",
        "stage": "stage_1_symbol_plan_evidence_request",
        "date": "2026-06-06",
        "user_confirmed_focus_pool": ["MU"],
        "permission_state_before_open": "Yellow",
        "symbols": [
            {
                "symbol": "MU",
                "role": "mid_term_swing_candidate",
                "theme": "memory",
                "research_status": "partially_researched",
                "plan_mode": "conditional_action_allowed",
                "key_levels": [],
                "rule_collision_contract": []
            }
        ]
    }), encoding="utf-8")
    
    out_file = tmp_path / "plan_evidence_no_wl.md"
    
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "premarket",
        "--date", "2026-06-06",
        "--decision-sheet", str(decision_sheet),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")
    
    assert res.returncode == 0
    assert os.path.exists(out_file)
    content = out_file.read_text(encoding="utf-8")
    assert "packet_type: plan_evidence_packet" in content
    assert "MU" in content


def test_cli_premarket_accepts_decision_sheet_with_utf8_bom(tmp_path):
    """PowerShell-authored brain artifacts may include a UTF-8 BOM."""
    decision_sheet = tmp_path / "decision_sheet.json"
    decision_sheet.write_text(json.dumps({
        "sheet_type": "pre_market_decision_sheet",
        "date": "2026-06-06",
        "user_confirmed_focus_pool": ["MU"],
        "permission_state_before_open": "Yellow",
        "symbols": [{
            "symbol": "MU",
            "role": "watchlist",
            "theme": "memory",
            "research_status": "candidate_only",
            "plan_mode": "observe_only",
        }],
    }), encoding="utf-8-sig")
    out_file = tmp_path / "plan_evidence.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "premarket",
        "--date", "2026-06-06",
        "--decision-sheet", str(decision_sheet),
        "--out", str(out_file),
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    assert "packet_type: plan_evidence_packet" in out_file.read_text(encoding="utf-8")


def test_cli_premarket_sanitizes_stage1_boundary_language(tmp_path):
    """Stage 1 must normalize brain rule language into evidence-only terms."""
    stage0 = tmp_path / "pre-market-context-packet.md"
    stage0.write_text(
        """---
packet_type: pre_market_environment_packet
status: fallback_data
---

## 1. Yesterday / Recent Market Context

| Symbol | Market | Price | 1D % | 5D % | 20D % | Volume Ratio | Source |
|---|---|---:|---:|---:|---:|---:|---|
| QQQ | Nasdaq 100 proxy | 500.00 | -1.00% | -4.50% | +1.46% | 2.40x | fixture |

## 3. Universe Input Quality

- universe_count: 2
- universe_required_fields_complete: true
""",
        encoding="utf-8",
    )
    decision_sheet = tmp_path / "decision_sheet.json"
    decision_sheet.write_text(json.dumps({
        "sheet_type": "pre_market_decision_sheet",
        "stage": "stage_1_symbol_plan_evidence_request",
        "date": "2026-06-06",
        "derived_from_stage0_packet": str(stage0),
        "user_confirmed_focus_pool": ["MU", "NVDA"],
        "permission_state_before_open": "Yellow",
        "symbols": [
            {
                "symbol": "MU",
                "role": "mid_term_swing_candidate",
                "theme": "memory",
                "research_status": "partially_researched",
                "plan_mode": "conditional_action_allowed",
                "rule_collision_contract": [
                    {
                        "rule_id": "loss_repair_guard",
                        "if": "symbol interest is connected to trapped leveraged exposure",
                        "then": "flag as risk_context_for_brain_review"
                    }
                ]
            },
            {
                "symbol": "NVDA",
                "role": "short_term_candidate",
                "theme": "ai_infrastructure",
                "research_status": "core_position_research_pending",
                "plan_mode": "conditional_action_allowed",
                "pre_authorized_actions": [
                    {"action_id": "NVDA_one_preplanned_entry_demo", "conditions": ["QQQ is not high-volume risk-off"]}
                ],
                "rule_collision_contract": [
                    {
                        "rule_id": "preauthorized_action_fast_check",
                        "if": "all pre_authorized_action conditions are true and fast_consistency_check passes",
                        "then": "return preauthorized_conditions_met; do not output buy/sell/hold"
                    }
                ]
            }
        ]
    }), encoding="utf-8")
    out_file = tmp_path / "plan_evidence.md"

    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "premarket",
        "--date", "2026-06-06",
        "--decision-sheet", str(decision_sheet),
        "--out", str(out_file)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")

    assert res.returncode == 0
    content = out_file.read_text(encoding="utf-8")
    assert "preauthorized_conditions_met" not in content
    assert "loss_repair_guard" not in content
    assert "risk_context_for_brain_review" not in content
    assert "linked_leveraged_exposure_detected" in content
    assert "related_position: MUU" in content
    assert "preauthorized_definition_complete" in content
    assert "required_data_available" in content or "required_data_missing" in content
    assert "status: fallback_data" in content
    assert "polygon_api_key_missing_or_failed" in content

def test_intraday_snapshot_soft_warns_outside_window(monkeypatch, tmp_path):
    """When called outside 9:30-16:00 ET, handle_intraday_snapshot prints warning but still executes."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import types

    eastern = ZoneInfo("America/New_York")
    fake_now = datetime(2026, 6, 30, 17, 30, 0, tzinfo=eastern)
    monkeypatch.setattr(cli, "_et_now", lambda: fake_now)

    class FakeHistory:
        empty = True

    class FakeTicker:
        def history(self, period=None):
            return FakeHistory()

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda sym: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    out_file = tmp_path / "snapshot.md"
    args = SimpleNamespace(symbols="MSFT", refresh=False, out=str(out_file))

    import io
    captured = io.StringIO()
    old_stdout = cli.sys.stdout
    cli.sys.stdout = captured
    try:
        cli.handle_intraday_snapshot(args)
    finally:
        cli.sys.stdout = old_stdout

    output = captured.getvalue()
    assert "[提示]" in output
    assert "不在目标盘中窗口" in output
    assert "17:30" in output
    assert out_file.exists()


def test_intraday_snapshot_no_warning_inside_window(monkeypatch, tmp_path):
    """When called inside 9:30-16:00 ET, handle_intraday_snapshot prints no time window warning."""
    sys.path.insert(0, WORKSPACE_DIR)
    import stock_team.cli as cli
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import types

    eastern = ZoneInfo("America/New_York")
    fake_now = datetime(2026, 6, 30, 11, 0, 0, tzinfo=eastern)
    monkeypatch.setattr(cli, "_et_now", lambda: fake_now)

    class FakeHistory:
        empty = True

    class FakeTicker:
        def history(self, period=None):
            return FakeHistory()

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda sym: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    out_file = tmp_path / "snapshot.md"
    args = SimpleNamespace(symbols="MSFT", refresh=False, out=str(out_file))

    import io
    captured = io.StringIO()
    old_stdout = cli.sys.stdout
    cli.sys.stdout = captured
    try:
        cli.handle_intraday_snapshot(args)
    finally:
        cli.sys.stdout = old_stdout

    output = captured.getvalue()
    assert "[提示]" not in output
    assert out_file.exists()


def test_cli_intraday_dashboard_generation(tmp_path):
    """Verify that intraday-dashboard subcommand executes cleanly and generates compliant manifest, HTML, and Markdown outputs."""
    guidance = tmp_path / "guidance.json"
    manifest = tmp_path / "manifest.json"
    out_md = tmp_path / "report.md"
    html_out = tmp_path / "dashboard.html"
    
    stage0 = tmp_path / "stage0.md"
    stage1 = tmp_path / "stage1.md"
    stage0.write_text("mock stage0 context packet content", encoding="utf-8")
    stage1.write_text("mock stage1 plan evidence packet content", encoding="utf-8")
    
    guidance.write_text(json.dumps({
        "artifact_type": "intraday_guidance_to_stock_team",
        "version": "1.0",
        "date": "2026-06-06",
        "derived_from": {
            "stage0_market_context_packet": str(stage0),
            "stage1_plan_evidence_packet": str(stage1)
        },
        "permission_state": {
            "state": "Yellow",
            "reason": ["Test reason"]
        },
        "global_controls": {
            "allowed_actions": ["observe"],
            "forbidden_actions": ["trade"],
            "attention_budget_minutes": 10,
            "new_risk_requires_user_confirmation": True
        },
        "symbols": [
            {
                "symbol": "MU",
                "role": "mid_term_swing_candidate",
                "intraday_mode": "conditional_action_allowed",
                "brain_permission": {
                    "status": "conditional",
                    "scope": "staged_swing_entry"
                },
                "evidence_conditions_to_monitor": [
                    {
                        "condition_id": "no_muu_loss_repair_context",
                        "description": "MU setup must remain separate from MUU trapped-position repair motive."
                    }
                ],
                "levels_to_monitor": [
                    {
                        "level_id": "ma20_swing_anchor",
                        "meaning": "trigger_review",
                        "formula_or_value": "MA20"
                    }
                ]
            }
        ],
        "stock_team_dashboard_request": {
            "output_kind": "evidence_dashboard",
            "show": ["packet_readiness", "symbol_condition_status"],
            "forbidden_ui_labels": ["buy", "sell", "hold"],
            "latest_manifest_path": str(manifest)
        }
    }), encoding="utf-8")
    
    started = time.monotonic()
    started = time.monotonic()
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "intraday-dashboard",
        "--guidance", str(guidance),
        "--out", str(out_md),
        "--html-out", str(html_out)
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8")
    
    assert res.returncode == 0
    
    # 1. Verify Manifest JSON exists and contains normalised keys and correct data
    assert manifest.exists()
    m_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert m_data["artifact_type"] == "evidence_dashboard"
    mu_data = m_data["symbol_condition_status"]["MU"]
    # Check normalization
    cond = mu_data["conditions"][0]
    assert cond["condition_id"] == "no_linked_leveraged_exposure_exception"
    assert "核对持仓中是否存在关联杠杆" in cond["description"]
    # Verify no un-censored forbidden words
    manifest_txt = manifest.read_text(encoding="utf-8").lower()
    for word in ["buy", "sell", "hold"]:
        assert word not in manifest_txt or "[censored" in manifest_txt
        
    # 2. Verify Markdown report exists and is formatted
    assert out_md.exists()
    md_content = out_md.read_text(encoding="utf-8")
    assert "Intraday Evidence Dashboard (2026-06-06)" in md_content
    assert "no_linked_leveraged_exposure_exception" in md_content
    
    # 3. Verify HTML dashboard was generated at the target html-out path
    assert html_out.exists()
    html_content = html_out.read_text(encoding="utf-8")
    assert "STOCK TEAM 盘中证据监控看板" in html_content
    assert "Outfit" in html_content
    assert "rgba(15, 23, 42, 0.45)" in html_content
def test_cli_intraday_dashboard_loop_refreshes_runtime_only(tmp_path):
    """Updater loop should refresh dashboard outputs without rewriting Stage 0/1 anchors."""
    guidance = tmp_path / "guidance.json"
    manifest = tmp_path / "manifest.json"
    out_md = tmp_path / "report.md"
    html_out = tmp_path / "dashboard.html"
    stage0 = tmp_path / "stage0.md"
    stage1 = tmp_path / "stage1.md"
    stage0_text = "stage0 anchor packet"
    stage1_text = "stage1 anchor packet"
    stage0.write_text(stage0_text, encoding="utf-8")
    stage1.write_text(stage1_text, encoding="utf-8")

    guidance.write_text(json.dumps({
        "artifact_type": "intraday_guidance_to_stock_team",
        "version": "1.0",
        "date": "2026-06-06",
        "derived_from": {
            "stage0_market_context_packet": str(stage0),
            "stage1_plan_evidence_packet": str(stage1)
        },
        "symbols": [
            {
                "symbol": "MU",
                "role": "mid_term_swing_candidate",
                "intraday_mode": "conditional_action_allowed",
                "brain_permission": {"status": "conditional", "scope": "staged_swing_entry"},
                "evidence_conditions_to_monitor": [
                    {"condition_id": "market_stabilization", "description": "QQQ and SOXX stop expanding downside risk."}
                ],
                "levels_to_monitor": [
                    {"level_id": "ma20_swing_anchor", "meaning": "trigger_review", "formula_or_value": "MA20"}
                ]
            }
        ],
        "stock_team_dashboard_request": {
            "latest_manifest_path": str(manifest)
        }
    }), encoding="utf-8")

    started = time.monotonic()
    res = subprocess.run([
        PYTHON, "-m", "stock_team.cli", "intraday-dashboard",
        "--guidance", str(guidance),
        "--out", str(out_md),
        "--html-out", str(html_out),
        "--loop",
        "--iterations", "2",
        "--interval-seconds", "0",
    ], cwd=WORKSPACE_DIR, env=get_env(), capture_output=True, text=True, encoding="utf-8", timeout=20)
    elapsed = time.monotonic() - started

    assert res.returncode == 0
    assert elapsed < 20
    assert stage0.read_text(encoding="utf-8") == stage0_text
    assert stage1.read_text(encoding="utf-8") == stage1_text
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["updater_loop"]["enabled"] is True
    assert data["updater_loop"]["iteration"] == 2
    assert data["updater_loop"]["iterations_requested"] == 2
    assert out_md.exists()
    assert html_out.exists()
