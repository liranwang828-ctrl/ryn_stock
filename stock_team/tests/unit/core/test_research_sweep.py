import json
from pathlib import Path


def _request(tmp_path: Path, tactic_id: str) -> Path:
    request = {
        "artifact_type": "tactic_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os-research",
        "tactic_id": tactic_id,
        "symbols": ["MU", "NVDA"],
        "date_range": {"start": "2024-06-01", "end": "2024-06-15"},
        "strategy": {
            "entry_model": {"type": "channel_reclaim", "indicator": "vwap"},
            "filters": [{"type": "relative_volume", "min_volume_ratio": 1.0}],
            "exit_model": {"type": "fixed_pct"},
        },
        "hyperparameters": {
            "action_window_start": "10:00",
            "action_window_end": "11:30",
            "min_volume_ratio": 1.0,
            "take_profit_pct": 2.0,
            "stop_loss_pct": 1.0,
        },
        "validation": {
            "windows": [{"name": "test", "start": "2024-06-01", "end": "2024-06-15"}],
            "regime_fields": ["market_regime"],
            "min_trades_per_window": 0,
            "monte_carlo": {"enabled": False},
        },
        "data": {"mode": "local_cache"},
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / f"{tactic_id}.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    return path


def test_research_sweep_reuses_featured_symbol_bars(monkeypatch, tmp_path):
    from stock_team.backtest import research_sweep

    load_calls = []
    feature_calls = []

    def fake_build_context(date_range):
        return {"benchmark_returns": {}, "market_regimes": {}}

    def fake_load_symbol(symbol, date_range, cache_context=None):
        load_calls.append(symbol)
        return [
            {
                "timestamp": "2024-06-03T10:00:00-0400",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1000.0,
                "time": "10:00",
                "market_regime": "qqq_uptrend_low_vix",
                "sector_regime": "unknown",
            }
        ], {}

    def fake_features(bars, benchmark_returns=None):
        feature_calls.append(bars[0]["timestamp"])
        return bars

    def fake_simulate(symbol, bars, params, daily_metrics):
        return [
            {
                "symbol": symbol,
                "entry_time": "2024-06-03T10:00:00-0400",
                "exit_time": "2024-06-03T10:05:00-0400",
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

    monkeypatch.setattr(research_sweep.tactic_simulator, "build_local_cache_context", fake_build_context)
    monkeypatch.setattr(research_sweep.tactic_simulator, "_load_local_data_for_symbol", fake_load_symbol)
    monkeypatch.setattr(research_sweep.tactic_simulator, "_with_intraday_features", fake_features)
    monkeypatch.setattr(research_sweep.tactic_simulator, "_simulate_all_trades", fake_simulate)

    result = research_sweep.run_local_cache_sweep([
        _request(tmp_path, "candidate_a"),
        _request(tmp_path, "candidate_b"),
    ])

    assert [item["tactic_id"] for item in result["candidates"]] == ["candidate_a", "candidate_b"]
    assert load_calls == ["MU", "NVDA"]
    assert feature_calls == ["2024-06-03T10:00:00-0400", "2024-06-03T10:00:00-0400"]
    assert result["candidates"][0]["summary"]["n_trades"] == 2
