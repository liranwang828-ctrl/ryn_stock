import json
from pathlib import Path

import pytest


def _write_request(tmp_path: Path, extra: dict | None = None) -> Path:
    request = {
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "tactic_id": "rs_pullback_rebound_intraday",
        "symbols": ["MU", "NVDA"],
        "date_range": {"start": "2026-01-01", "end": "2026-03-31"},
        "strategy": {
            "entry_model": {
                "type": "channel_reclaim",
                "indicator": "vwap"
            },
            "filters": [
                {
                    "type": "relative_volume",
                    "min_volume_ratio": 1.2
                }
            ],
            "exit_model": {
                "type": "fixed_pct"
            }
        },
        "hyperparameters": {
            "stop_loss_pct": 1.5,
            "take_profit_pct": 3.0,
            "min_volume_ratio": 1.2
        },
        "validation": {
            "windows": [
                {"name": "train", "start": "2026-01-01", "end": "2026-02-15"},
                {"name": "test", "start": "2026-02-16", "end": "2026-03-31"},
            ],
            "regime_fields": ["market_regime", "sector_regime"],
            "min_trades_per_window": 1,
        },
        "data": {
            "mode": "fixture_events",
            "events": [
                {
                    "symbol": "MU",
                    "entry_time": "2026-01-09T10:15:00-05:00",
                    "exit_time": "2026-01-09T15:45:00-05:00",
                    "return_pct": 2.5,
                    "mae_pct": -0.8,
                    "mfe_pct": 3.1,
                    "market_regime": "qqq_uptrend_low_vix",
                    "sector_regime": "semis_strong",
                    "outcome": "win",
                },
                {
                    "symbol": "NVDA",
                    "entry_time": "2026-02-20T10:05:00-05:00",
                    "exit_time": "2026-02-20T15:50:00-05:00",
                    "return_pct": -1.0,
                    "mae_pct": -1.4,
                    "mfe_pct": 0.6,
                    "market_regime": "high_volume_risk_off",
                    "sector_regime": "semis_weak",
                    "outcome": "loss",
                },
                {
                    "symbol": "MU",
                    "entry_time": "2026-03-03T10:20:00-05:00",
                    "exit_time": "2026-03-03T15:55:00-05:00",
                    "return_pct": 1.5,
                    "mae_pct": -0.6,
                    "mfe_pct": 1.9,
                    "market_regime": "qqq_uptrend_low_vix",
                    "sector_regime": "semis_strong",
                    "outcome": "win",
                },
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    if extra:
        request.update(extra)
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    return path


def test_request_rejects_config_mutation(tmp_path):
    from stock_team.backtest.tactic_backtest_system import load_request

    path = _write_request(
        tmp_path,
        {"output_contract": {"allow_recommendations": False, "allow_config_mutation": True}},
    )

    with pytest.raises(ValueError, match="allow_config_mutation"):
        load_request(path)


def test_runner_segments_metrics_by_window_and_regime(tmp_path):
    from stock_team.backtest.tactic_backtest_system import run_request

    request_path = _write_request(tmp_path)
    result = run_request(request_path)

    assert result["packet_type"] == "tactic_backtest_evidence_packet"
    assert result["tactic_id"] == "rs_pullback_rebound_intraday"
    assert result["summary"]["n_trades"] == 3
    assert result["summary"]["win_rate"] == pytest.approx(2 / 3)
    assert result["validation"]["windows"]["train"]["n_trades"] == 1
    assert result["validation"]["windows"]["test"]["n_trades"] == 2
    assert result["validation"]["regimes"]["market_regime:high_volume_risk_off"]["avg_return_pct"] == -1.0
    assert result["boundaries"]["contains_permission_decision"] is False


def test_report_writer_sanitizes_decision_language(tmp_path):
    from stock_team.backtest.tactic_backtest_system import run_request, write_outputs

    request_path = _write_request(tmp_path)
    result = run_request(request_path)
    md_path = tmp_path / "packet.md"
    json_path = tmp_path / "packet.json"

    write_outputs(result, md_path=md_path, json_path=json_path)

    md = md_path.read_text(encoding="utf-8")
    machine = json.loads(json_path.read_text(encoding="utf-8"))
    assert "No Permission Decision" in md
    assert "buy" not in md.lower()
    assert "sell" not in md.lower()
    assert "hold" not in md.lower()
    assert machine["summary"]["profit_factor"] == pytest.approx(4.0)


def test_intraday_ohlcv_fixture_generates_events_from_vwap_reclaim(tmp_path):
    from stock_team.backtest.tactic_backtest_system import run_request

    request = {
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
            "windows": [
                {"name": "test", "start": "2026-01-09", "end": "2026-01-09"},
            ],
            "regime_fields": ["market_regime", "sector_regime"],
            "min_trades_per_window": 1,
        },
        "data": {
            "mode": "intraday_ohlcv_fixture",
            "bar_interval": "5m",
            "bars": {
                "MU": [
                    {"timestamp": "2026-01-09T09:30:00-05:00", "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.0, "volume": 1000, "market_regime": "qqq_uptrend_low_vix", "sector_regime": "semis_strong"},
                    {"timestamp": "2026-01-09T09:35:00-05:00", "open": 100.0, "high": 100.2, "low": 98.0, "close": 98.5, "volume": 1200, "market_regime": "qqq_uptrend_low_vix", "sector_regime": "semis_strong"},
                    {"timestamp": "2026-01-09T09:40:00-05:00", "open": 98.5, "high": 99.0, "low": 98.1, "close": 98.6, "volume": 800, "market_regime": "qqq_uptrend_low_vix", "sector_regime": "semis_strong"},
                    {"timestamp": "2026-01-09T10:05:00-05:00", "open": 98.6, "high": 101.5, "low": 98.4, "close": 101.2, "volume": 5000, "market_regime": "qqq_uptrend_low_vix", "sector_regime": "semis_strong"},
                    {"timestamp": "2026-01-09T15:55:00-05:00", "open": 101.2, "high": 103.2, "low": 101.0, "close": 102.8, "volume": 1800, "market_regime": "qqq_uptrend_low_vix", "sector_regime": "semis_strong"}
                ]
            }
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "ohlcv_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["data_mode"] == "intraday_ohlcv_fixture"
    assert result["summary"]["n_trades"] == 1
    event = result["events"][0]
    assert event["symbol"] == "MU"
    assert event["entry_time"] == "2026-01-09T10:05:00-05:00"
    assert event["exit_reason"] == "end_of_day"
    assert event["return_pct"] == pytest.approx(1.041, abs=0.01)
    assert event["trigger"] == "channel_reclaim_vwap"


def test_tactic_backtest_local_cache_runs_and_calculates_metrics(tmp_path):
    from stock_team.backtest.tactic_backtest_system import run_request

    request = {
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "tactic_id": "rs_pullback_rebound_local",
        "symbols": ["MU"],
        "date_range": {"start": "2024-06-01", "end": "2024-06-15"},
        "strategy": {
            "entry_model": {
                "type": "channel_reclaim",
                "indicator": "vwap"
            },
            "filters": [
                {
                    "type": "relative_volume",
                    "min_volume_ratio": 0.5
                }
            ],
            "exit_model": {
                "type": "fixed_pct"
            }
        },
        "hyperparameters": {
            "action_window_start": "09:30",
            "action_window_end": "16:00",
            "min_volume_ratio": 0.5,
            "take_profit_pct": 2.0,
            "stop_loss_pct": 1.0,
            "leverage": 2
        },
        "validation": {
            "windows": [
                {"name": "train", "start": "2024-06-01", "end": "2024-06-08"},
                {"name": "test", "start": "2024-06-09", "end": "2024-06-15"},
            ],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 0,
        },
        "data": {
            "mode": "local_cache"
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    
    path = tmp_path / "local_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    
    result = run_request(path)
    assert result["packet_type"] == "tactic_backtest_evidence_packet"
    assert result["data_mode"] == "local_cache"
    assert result["summary"]["n_trades"] > 0
    assert "sharpe_ratio" in result["summary"]
    assert "sortino_ratio" in result["summary"]
    assert "calmar_ratio" in result["summary"]
    assert "max_drawdown_pct" in result["summary"]


def test_tactic_backtest_local_cache_builds_shared_context_once(monkeypatch, tmp_path):
    from stock_team.backtest import tactic_simulator
    from stock_team.backtest.tactic_backtest_system import run_request

    shared_context = {"market_regimes": {}, "benchmark_returns": {}}
    build_calls = []
    simulation_context_ids = []

    def fake_build_context(date_range):
        build_calls.append(date_range)
        return shared_context

    def fake_run_simulation_to_events(symbol, mode, date_range, params, bars_by_symbol=None, cache_context=None):
        simulation_context_ids.append(id(cache_context))
        return [
            {
                "symbol": symbol,
                "entry_time": f"{date_range['start']}T10:00:00-0500",
                "exit_time": f"{date_range['start']}T10:05:00-0500",
                "entry_price": 100.0,
                "exit_price": 101.0,
                "return_pct": 1.0,
                "mae_pct": -0.2,
                "mfe_pct": 1.2,
                "market_regime": "qqq_uptrend_low_vix",
                "sector_regime": "unknown",
                "trigger": "channel_reclaim_vwap",
                "exit_reason": "take_profit",
            }
        ]

    monkeypatch.setattr(tactic_simulator, "build_local_cache_context", fake_build_context)
    monkeypatch.setattr(tactic_simulator, "run_simulation_to_events", fake_run_simulation_to_events)

    request = {
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "tactic_id": "shared_cache_demo",
        "symbols": ["MU", "NVDA", "COHR"],
        "date_range": {"start": "2024-06-01", "end": "2024-06-15"},
        "strategy": {
            "entry_model": {"type": "channel_reclaim", "indicator": "vwap"},
            "filters": [{"type": "relative_volume", "min_volume_ratio": 0.5}],
            "exit_model": {"type": "fixed_pct"},
        },
        "hyperparameters": {
            "action_window_start": "09:30",
            "action_window_end": "16:00",
            "min_volume_ratio": 0.5,
            "take_profit_pct": 2.0,
            "stop_loss_pct": 1.0,
        },
        "validation": {
            "windows": [{"name": "test", "start": "2024-06-01", "end": "2024-06-15"}],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 0,
        },
        "data": {"mode": "local_cache"},
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "shared_cache_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["summary"]["n_trades"] == 3
    assert build_calls == [{"start": "2024-06-01", "end": "2024-06-15"}]
    assert simulation_context_ids == [id(shared_context)] * 3


def test_local_cache_loader_handles_mixed_timezone_offsets(tmp_path):
    from stock_team.backtest.tactic_simulator import _load_local_data_for_symbol

    learning = tmp_path / "learning"
    learning.mkdir()
    (learning / "intraday_cache_MIX.csv").write_text(
        "Datetime,Open,High,Low,Close,Volume\n"
        "2024-11-01 14:30:00-04:00,100,101,99,100.5,1000\n"
        "2024-11-04 14:30:00-05:00,101,102,100,101.5,1100\n",
        encoding="utf-8",
    )

    bars, daily_metrics = _load_local_data_for_symbol(
        "MIX",
        {"start": "2024-11-01", "end": "2024-11-04"},
        cache_context={"learning_dir": learning, "market_regimes": {}},
    )

    assert [bar["time"] for bar in bars] == ["14:30", "14:30"]
    assert [bar["timestamp"][:10] for bar in bars] == ["2024-11-01", "2024-11-04"]
    assert daily_metrics == {}


def test_local_cache_loader_filters_extended_hours_by_default(tmp_path):
    from stock_team.backtest.tactic_simulator import _load_local_data_for_symbol

    learning = tmp_path / "learning"
    learning.mkdir()
    (learning / "intraday_cache_REG.csv").write_text(
        "Datetime,Open,High,Low,Close,Volume\n"
        "2024-06-03 08:00:00+00:00,100,101,99,100,1000\n"
        "2024-06-03 13:30:00+00:00,101,102,100,101,1100\n"
        "2024-06-03 20:05:00+00:00,102,103,101,102,1200\n",
        encoding="utf-8",
    )

    bars, _ = _load_local_data_for_symbol(
        "REG",
        {"start": "2024-06-03", "end": "2024-06-03"},
        cache_context={"learning_dir": learning, "market_regimes": {}},
    )

    assert [bar["time"] for bar in bars] == ["09:30"]


def test_intraday_features_reset_vwap_volume_and_rs_by_session():
    from stock_team.backtest.tactic_simulator import _with_intraday_features

    bars = [
        {"timestamp": "2024-06-03T15:55:00-0400", "open": 100, "high": 100, "low": 100, "close": 100, "volume": 10000, "time": "15:55"},
        {"timestamp": "2024-06-04T09:30:00-0400", "open": 200, "high": 200, "low": 200, "close": 200, "volume": 100, "time": "09:30"},
        {"timestamp": "2024-06-04T09:35:00-0400", "open": 201, "high": 201, "low": 201, "close": 201, "volume": 200, "time": "09:35"},
    ]
    benchmark_returns = {
        "2024-06-03T15:55:00-0400": 0.05,
        "2024-06-04T09:30:00-0400": 0.10,
        "2024-06-04T09:35:00-0400": 0.20,
    }

    featured = _with_intraday_features(bars, benchmark_returns=benchmark_returns)

    assert featured[1]["vwap"] == 200
    assert featured[1]["volume_ratio"] == 1.0
    assert featured[1]["rs_diff"] == 0.0
    assert featured[2]["volume_ratio"] == 2.0


def test_dynamic_slippage_is_bounded_for_liquid_intraday_bars():
    from stock_team.backtest.tactic_simulator import compute_dynamic_slippage

    slip = compute_dynamic_slippage(close=100.0, atr14=2.0, gap_pct=0.0, leverage=1)

    assert 0.0002 <= slip <= 0.0015


def test_tactic_backtest_monte_carlo_and_censorship(tmp_path):
    from stock_team.backtest.tactic_backtest_system import run_request, write_outputs

    request = {
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "tactic_id": "rs_pullback_rebound_local",
        "symbols": ["MU"],
        "date_range": {"start": "2024-06-01", "end": "2024-06-15"},
        "strategy": {
            "entry_model": {
                "type": "channel_reclaim",
                "indicator": "vwap"
            },
            "filters": [
                {
                    "type": "relative_volume",
                    "min_volume_ratio": 0.5
                }
            ],
            "exit_model": {
                "type": "fixed_pct"
            }
        },
        "hyperparameters": {
            "action_window_start": "09:30",
            "action_window_end": "16:00",
            "min_volume_ratio": 0.5,
            "take_profit_pct": 2.0,
            "stop_loss_pct": 1.0,
            "leverage": 2
        },
        "validation": {
            "windows": [
                {"name": "train", "start": "2024-06-01", "end": "2024-06-08"},
                {"name": "test", "start": "2024-06-09", "end": "2024-06-15"},
            ],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 0,
            "monte_carlo": {
                "enabled": True,
                "simulations": 100
            }
        },
        "data": {
            "mode": "local_cache"
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    
    path = tmp_path / "local_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    
    result = run_request(path)
    assert "var_95_return_pct" in result["monte_carlo"]
    assert "cvar_95_return_pct" in result["monte_carlo"]
    assert "mdd_95_pct" in result["monte_carlo"]
    
    # Intentionally inject action-biased words to verify censorship
    result["events"].append({
        "symbol": "MU",
        "entry_time": "2024-06-03T10:00:00Z",
        "exit_time": "2024-06-03T15:00:00Z",
        "entry_price": 100.0,
        "exit_price": 102.0,
        "return_pct": 2.0,
        "mae_pct": -0.5,
        "mfe_pct": 2.5,
        "market_regime": "normal",
        "sector_regime": "normal",
        "trigger": "buy signal triggered", # "buy"
        "exit_reason": "sell stop hit",       # "sell"
        "entry_vwap": 100.0,
        "entry_volume_ratio": 1.5,
    })
    
    md_path = tmp_path / "packet.md"
    json_path = tmp_path / "packet.json"
    
    write_outputs(result, md_path=md_path, json_path=json_path)
    
    md_text = md_path.read_text(encoding="utf-8")
    json_text = json_path.read_text(encoding="utf-8")
    
    assert "buy" not in md_text.lower()
    assert "sell" not in md_text.lower()
    assert "hold" not in md_text.lower()
    
    assert "buy" not in json_text.lower()
    assert "sell" not in json_text.lower()
    assert "hold" not in json_text.lower()


def test_modular_strategy_registry_components(tmp_path):
    from stock_team.backtest.tactic_backtest_system import run_request
    
    # 1. channel_breakout + relative_strength + atr_trailing_stop
    request_breakout = {
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "tactic_id": "test_breakout",
        "symbols": ["MU"],
        "date_range": {"start": "2026-01-09", "end": "2026-01-09"},
        "strategy": {
            "entry_model": {
                "type": "channel_breakout",
                "indicator": "orb30_high"
            },
            "filters": [
                {
                    "type": "relative_strength",
                    "benchmark": "qqq",
                    "min_rs_diff": -100.0
                }
            ],
            "exit_model": {
                "type": "atr_trailing_stop"
            }
        },
        "hyperparameters": {
            "action_window_start": "10:00",
            "action_window_end": "11:00",
            "sl_atr_multiplier": 1.5,
            "tp_atr_multiplier": 2.5
        },
        "validation": {
            "windows": [{"name": "test", "start": "2026-01-09", "end": "2026-01-09"}],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 0
        },
        "data": {
            "mode": "intraday_ohlcv_fixture",
            "bars": {
                "MU": [
                    {"timestamp": "2026-01-09T09:30:00-05:00", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1000},
                    {"timestamp": "2026-01-09T09:45:00-05:00", "open": 100.0, "high": 102.0, "low": 100.0, "close": 102.0, "volume": 1000}, # ORB30 high is 102.0
                    {"timestamp": "2026-01-09T10:05:00-05:00", "open": 102.0, "high": 103.0, "low": 101.5, "close": 102.5, "volume": 1000}, # breaks out above 102.0
                    {"timestamp": "2026-01-09T15:55:00-05:00", "open": 102.5, "high": 105.0, "low": 102.0, "close": 104.0, "volume": 1000}
                ]
            }
        },
        "output_contract": {"allow_recommendations": False, "allow_config_mutation": False}
    }
    
    path = tmp_path / "breakout_request.json"
    path.write_text(json.dumps(request_breakout), encoding="utf-8")
    result = run_request(path)
    assert result["summary"]["n_trades"] == 1
    event = result["events"][0]
    assert event["trigger"] == "channel_breakout_orb30_high"
    assert event["entry_price"] == 102.5
    
    # 2. mean_reversion + rsi + partial_scaling
    request_reversion = {
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "tactic_id": "test_reversion",
        "symbols": ["MU"],
        "date_range": {"start": "2026-01-09", "end": "2026-01-09"},
        "strategy": {
            "entry_model": {
                "type": "mean_reversion",
                "indicator": "sma20"
            },
            "filters": [
                {
                    "type": "rsi",
                    "min_value": 0,
                    "max_value": 99
                }
            ],
            "exit_model": {
                "type": "partial_scaling"
            }
        },
        "hyperparameters": {
            "action_window_start": "09:30",
            "action_window_end": "16:00",
            "deviation_pct": 0.5,
            "sl_atr_multiplier": 1.0,
            "tp1_multiplier": 1.5,
            "tp2_multiplier": 3.0
        },
        "validation": {
            "windows": [{"name": "test", "start": "2026-01-09", "end": "2026-01-09"}],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 0
        },
        "data": {
            "mode": "intraday_ohlcv_fixture",
            "bars": {
                "MU": [
                    {"timestamp": "2026-01-09T09:30:00-05:00", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1000},
                    {"timestamp": "2026-01-09T09:35:00-05:00", "open": 100.0, "high": 100.0, "low": 98.0, "close": 98.5, "volume": 1000}, # sma20 is ~99.25, deviation is > 0.5%
                    {"timestamp": "2026-01-09T15:55:00-05:00", "open": 98.5, "high": 105.0, "low": 98.0, "close": 104.0, "volume": 1000}
                ]
            }
        },
        "output_contract": {"allow_recommendations": False, "allow_config_mutation": False}
    }
    
    path_rev = tmp_path / "reversion_request.json"
    path_rev.write_text(json.dumps(request_reversion), encoding="utf-8")
    result_rev = run_request(path_rev)
    assert result_rev["summary"]["n_trades"] == 1
