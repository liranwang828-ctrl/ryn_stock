import json
from pathlib import Path

import pytest


def test_backtest_contracts_declare_research_only_intraday_boundary():
    docs_dir = Path(__file__).resolve().parents[3] / "docs"

    for contract_name in [
        "stage-context-backtest-contract.md",
        "tactic-backtest-contract.md",
    ]:
        text = (docs_dir / contract_name).read_text(encoding="utf-8").lower()

        assert "research/review only" in text
        assert "must not run during intraday" in text
        assert "dashboard" in text


def test_stage_context_contract_declares_macro_entry_boundary():
    text = (Path(__file__).resolve().parents[3] / "docs" / "stage-context-backtest-contract.md").read_text(
        encoding="utf-8"
    ).lower()

    assert "macro/stage 0/1 entry boundary" in text
    assert "forward 3d / 5d / 10d / 20d returns" in text
    assert "must not use intraday-only exits" in text
    assert "must not use fixed 1%-2% take-profit or stop-loss assumptions" in text
    assert "must not force same-day exit" in text


def _write_stage_request(tmp_path: Path) -> Path:
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": [
            "qqq_regime",
            "vix_regime",
            "market_volume_regime",
            "catalyst_bucket",
            "cognition_state",
            "permission_state",
        ],
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
                        "market_volume_regime": "normal_volume",
                        "catalyst_bucket": "positive_company_catalyst",
                        "cognition_state": "normal",
                        "permission_state": "Yellow",
                    },
                },
                {
                    "date": "2026-01-06",
                    "symbol": "NVDA",
                    "tactic_id": "vwap_reclaim",
                    "return_pct": 1.0,
                    "mae_pct": -0.6,
                    "mfe_pct": 1.5,
                    "context": {
                        "qqq_regime": "qqq_uptrend",
                        "vix_regime": "vix_low_falling",
                        "market_volume_regime": "normal_volume",
                        "catalyst_bucket": "positive_company_catalyst",
                        "cognition_state": "normal",
                        "permission_state": "Yellow",
                    },
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
                        "market_volume_regime": "high_volume_risk_off",
                        "catalyst_bucket": "no_clear_catalyst",
                        "cognition_state": "loss_repair_watch",
                        "permission_state": "Red",
                    },
                },
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "stage_context_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    return path


def test_stage_context_backtest_groups_environment_and_plan_quality(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    result = run_request(_write_stage_request(tmp_path))

    assert result["packet_type"] == "stage_context_backtest_evidence_packet"
    assert result["study_id"] == "stage_gate_demo"
    assert result["summary"]["n_events"] == 3
    assert result["summary"]["win_rate"] == pytest.approx(2 / 3)
    assert result["boundaries"]["contains_permission_decision"] is False
    assert result["boundaries"]["config_mutation"] is False

    good_key = (
        "qqq_regime=qqq_uptrend|vix_regime=vix_low_falling|"
        "market_volume_regime=normal_volume|"
        "catalyst_bucket=positive_company_catalyst|"
        "cognition_state=normal|permission_state=Yellow"
    )
    weak_key = (
        "qqq_regime=qqq_downtrend|vix_regime=vix_high_rising|"
        "market_volume_regime=high_volume_risk_off|"
        "catalyst_bucket=no_clear_catalyst|"
        "cognition_state=loss_repair_watch|permission_state=Red"
    )
    assert result["context_segments"][good_key]["n_events"] == 2
    assert result["context_segments"][good_key]["avg_return_pct"] == pytest.approx(1.5)
    assert result["context_segments"][weak_key]["win_rate"] == 0.0


def test_stage_context_backtest_rejects_decision_keys(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    path = _write_stage_request(tmp_path)
    request = json.loads(path.read_text(encoding="utf-8"))
    request["approved"] = True
    path.write_text(json.dumps(request), encoding="utf-8")

    with pytest.raises(ValueError, match="Forbidden request key"):
        run_request(path)


def test_stage_context_backtest_joins_stage_labels_to_tactic_events(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_join_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["qqq_regime", "vix_regime", "permission_state"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_contexts": [
                {
                    "date": "2026-01-05",
                    "context": {
                        "qqq_regime": "qqq_uptrend",
                        "vix_regime": "vix_low_falling",
                        "permission_state": "Yellow",
                    },
                },
                {
                    "date": "2026-01-08",
                    "context": {
                        "qqq_regime": "qqq_downtrend",
                        "vix_regime": "vix_high_rising",
                        "permission_state": "Red",
                    },
                },
            ],
            "events": [
                {
                    "date": "2026-01-05",
                    "symbol": "MU",
                    "tactic_id": "vwap_reclaim",
                    "return_pct": 2.0,
                    "mae_pct": -0.4,
                    "mfe_pct": 2.7,
                },
                {
                    "entry_time": "2026-01-08T10:05:00-05:00",
                    "symbol": "COHR",
                    "tactic_id": "vwap_reclaim",
                    "return_pct": -1.5,
                    "mae_pct": -2.1,
                    "mfe_pct": 0.4,
                },
                {
                    "date": "2026-01-09",
                    "symbol": "NVDA",
                    "tactic_id": "breakout",
                    "return_pct": 0.5,
                    "mae_pct": -0.2,
                    "mfe_pct": 1.0,
                },
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "joined_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    yellow_key = "qqq_regime=qqq_uptrend|vix_regime=vix_low_falling|permission_state=Yellow"
    red_key = "qqq_regime=qqq_downtrend|vix_regime=vix_high_rising|permission_state=Red"
    unknown_key = "qqq_regime=unknown|vix_regime=unknown|permission_state=unknown"

    assert result["data_mode"] == "joined_fixture_events"
    assert result["summary"]["n_events"] == 3
    assert result["data_quality"]["stage_context_count"] == 2
    assert result["data_quality"]["missing_context_events"] == 1
    assert result["context_segments"][yellow_key]["avg_return_pct"] == 2.0
    assert result["context_segments"][red_key]["avg_return_pct"] == -1.5
    assert result["context_segments"][unknown_key]["n_events"] == 1
    assert result["events"][0]["context_source"] == "stage_context_by_date"


def test_stage_context_backtest_writes_evidence_only_packets(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request, write_outputs

    result = run_request(_write_stage_request(tmp_path))
    md_path = tmp_path / "stage_context_packet.md"
    json_path = tmp_path / "stage_context_packet.json"

    write_outputs(result, md_path=md_path, json_path=json_path)

    md = md_path.read_text(encoding="utf-8")
    machine = json.loads(json_path.read_text(encoding="utf-8"))
    assert "packet_type: stage_context_backtest_evidence_packet" in md
    assert "Evidence Only" in md
    assert "qqq_regime=qqq_downtrend\\|vix_regime=vix_high_rising" in md
    assert "recommendation" not in md.lower()
    assert machine["summary"]["n_events"] == 3


def test_stage_context_backtest_markdown_shows_join_data_quality(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request, write_outputs

    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_join_quality_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["qqq_regime"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_contexts": [
                {"date": "2026-01-05", "context": {"qqq_regime": "qqq_uptrend"}}
            ],
            "events": [
                {"date": "2026-01-05", "symbol": "MU", "return_pct": 2, "mae_pct": -0.4, "mfe_pct": 2.7},
                {"date": "2026-01-06", "symbol": "NVDA", "return_pct": -1, "mae_pct": -1.2, "mfe_pct": 0.3},
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "joined_quality_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    md_path = tmp_path / "joined_quality_packet.md"

    write_outputs(run_request(path), md_path=md_path)

    md = md_path.read_text(encoding="utf-8")
    assert "## Data Quality" in md
    assert "| stage_context_count | 1 |" in md
    assert "| missing_context_events | 1 |" in md


def test_stage_context_backtest_derives_stage_contexts_from_daily_market_fixture(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    qqq = tmp_path / "QQQ.csv"
    vix = tmp_path / "VIX.csv"
    spy = tmp_path / "SPY.csv"
    qqq.write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,100,101,99,100,1000",
            "2026-01-03,100,103,99,102,1100",
            "2026-01-04,102,104,101,103,1200",
            "2026-01-05,103,107,102,106,1300",
            "2026-01-06,106,107,99,100,4000",
        ]),
        encoding="utf-8",
    )
    vix.write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,14,15,13,14,0",
            "2026-01-03,14,15,13,14,0",
            "2026-01-04,14,15,13,15,0",
            "2026-01-05,15,16,14,16,0",
            "2026-01-06,16,26,15,25,0",
        ]),
        encoding="utf-8",
    )
    spy.write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,200,201,199,200,1000",
            "2026-01-03,200,201,199,200,1000",
            "2026-01-04,200,201,199,200,1000",
            "2026-01-05,200,201,199,200,1000",
            "2026-01-06,200,201,199,200,3000",
        ]),
        encoding="utf-8",
    )
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_market_fixture_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["qqq_regime", "vix_regime", "market_volume_regime"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_context_source": {
                "mode": "daily_market_fixture",
                "qqq_csv": str(qqq),
                "vix_csv": str(vix),
                "volume_csv": str(spy),
            },
            "events": [
                {"date": "2026-01-05", "symbol": "MU", "return_pct": 2, "mae_pct": -0.4, "mfe_pct": 2.7},
                {"date": "2026-01-06", "symbol": "COHR", "return_pct": -1.5, "mae_pct": -2.1, "mfe_pct": 0.4},
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "market_fixture_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    risk_on = "qqq_regime=qqq_uptrend|vix_regime=vix_low_rising|market_volume_regime=normal_volume"
    risk_off = "qqq_regime=qqq_downtrend|vix_regime=vix_high_rising|market_volume_regime=high_volume_risk_off"
    assert result["data_quality"]["stage_context_source"] == "daily_market_fixture"
    assert result["data_quality"]["stage_context_count"] == 5
    assert result["context_segments"][risk_on]["avg_return_pct"] == 2.0
    assert result["context_segments"][risk_off]["avg_return_pct"] == -1.5


def test_stage_context_backtest_derives_stage_contexts_from_local_cache_dir(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    cache_dir = tmp_path / "learning"
    cache_dir.mkdir()
    (cache_dir / "daily_cache_QQQ.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,100,101,99,100,1000",
            "2026-01-03,100,103,99,102,1100",
            "2026-01-04,102,104,101,103,1200",
            "2026-01-05,103,107,102,106,1300",
        ]),
        encoding="utf-8",
    )
    (cache_dir / "daily_cache_^VIX.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,14,15,13,14,0",
            "2026-01-03,14,15,13,14,0",
            "2026-01-04,14,15,13,15,0",
            "2026-01-05,15,16,14,16,0",
        ]),
        encoding="utf-8",
    )
    (cache_dir / "daily_cache_SPY.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,200,201,199,200,1000",
            "2026-01-03,200,201,199,200,1000",
            "2026-01-04,200,201,199,200,1000",
            "2026-01-05,200,201,199,200,1000",
        ]),
        encoding="utf-8",
    )
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_local_cache_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["qqq_regime", "vix_regime", "market_volume_regime"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_context_source": {
                "mode": "daily_market_local_cache",
                "cache_dir": str(cache_dir),
            },
            "events": [
                {"date": "2026-01-05", "symbol": "MU", "return_pct": 2, "mae_pct": -0.4, "mfe_pct": 2.7}
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "local_cache_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["data_quality"]["stage_context_source"] == "daily_market_local_cache"
    assert result["data_quality"]["stage_context_count"] == 4
    assert result["events"][0]["context"]["qqq_regime"] == "qqq_uptrend"


def test_stage_context_backtest_local_cache_uses_sector_symbol_when_available(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    cache_dir = tmp_path / "learning"
    cache_dir.mkdir()
    (cache_dir / "daily_cache_QQQ.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,100,101,99,100,1000",
            "2026-01-05,100,101,99,101,1000",
        ]),
        encoding="utf-8",
    )
    (cache_dir / "daily_cache_^VIX.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,14,15,13,14,0",
            "2026-01-05,14,15,13,14,0",
        ]),
        encoding="utf-8",
    )
    (cache_dir / "daily_cache_SECTOR.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,200,201,199,200,1000",
            "2026-01-05,200,211,199,210,1000",
        ]),
        encoding="utf-8",
    )
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_local_sector_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["sector_regime"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_context_source": {
                "mode": "daily_market_local_cache",
                "cache_dir": str(cache_dir),
                "sector_symbol": "SECTOR",
            },
            "events": [
                {"date": "2026-01-05", "symbol": "MU", "return_pct": 2, "mae_pct": -0.4, "mfe_pct": 2.7}
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "local_sector_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["events"][0]["context"]["sector_regime"] == "sector_strong"


def test_stage_context_backtest_local_cache_warns_when_sector_symbol_missing(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    cache_dir = tmp_path / "learning"
    cache_dir.mkdir()
    (cache_dir / "daily_cache_QQQ.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,100,101,99,100,1000",
            "2026-01-05,100,101,99,101,1000",
        ]),
        encoding="utf-8",
    )
    (cache_dir / "daily_cache_^VIX.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,14,15,13,14,0",
            "2026-01-05,14,15,13,14,0",
        ]),
        encoding="utf-8",
    )
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_missing_sector_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["sector_regime"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_context_source": {
                "mode": "daily_market_local_cache",
                "cache_dir": str(cache_dir),
                "sector_symbol": "MISSING",
            },
            "events": [
                {"date": "2026-01-05", "symbol": "MU", "return_pct": 2, "mae_pct": -0.4, "mfe_pct": 2.7}
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "missing_sector_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["events"][0]["context"].get("sector_regime") is None
    assert "sector_cache_missing:MISSING" in result["data_quality"]["warnings"]


def test_stage_context_backtest_local_cache_falls_back_to_qqq_volume_when_spy_missing(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    cache_dir = tmp_path / "learning"
    cache_dir.mkdir()
    (cache_dir / "daily_cache_QQQ.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,100,101,99,100,1000",
            "2026-01-03,100,103,99,102,1100",
            "2026-01-04,102,104,101,103,1200",
        ]),
        encoding="utf-8",
    )
    (cache_dir / "daily_cache_^VIX.csv").write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,14,15,13,14,0",
            "2026-01-03,14,15,13,14,0",
            "2026-01-04,14,15,13,15,0",
        ]),
        encoding="utf-8",
    )
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_missing_spy_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["market_volume_regime"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_context_source": {
                "mode": "daily_market_local_cache",
                "cache_dir": str(cache_dir),
            },
            "events": [
                {"date": "2026-01-04", "symbol": "MU", "return_pct": 1, "mae_pct": -0.2, "mfe_pct": 1.3}
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "missing_spy_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["data_quality"]["stage_context_count"] == 3
    assert "volume_cache_missing_used_qqq_volume" in result["data_quality"]["warnings"]


def test_stage_context_backtest_derives_sector_regime_from_daily_market_fixture(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    qqq = tmp_path / "QQQ.csv"
    vix = tmp_path / "VIX.csv"
    sector = tmp_path / "SOXX.csv"
    qqq.write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,100,101,99,100,1000",
            "2026-01-05,100,101,99,101,1000",
            "2026-01-06,101,102,100,102,1000",
        ]),
        encoding="utf-8",
    )
    vix.write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,14,15,13,14,0",
            "2026-01-05,14,15,13,14,0",
            "2026-01-06,14,15,13,14,0",
        ]),
        encoding="utf-8",
    )
    sector.write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,200,201,199,200,1000",
            "2026-01-05,200,211,199,210,1000",
            "2026-01-06,210,211,190,195,1000",
        ]),
        encoding="utf-8",
    )
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_sector_fixture_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["sector_regime"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_context_source": {
                "mode": "daily_market_fixture",
                "qqq_csv": str(qqq),
                "vix_csv": str(vix),
                "volume_csv": str(qqq),
                "sector_csv": str(sector),
            },
            "events": [
                {"date": "2026-01-05", "symbol": "MU", "return_pct": 2, "mae_pct": -0.4, "mfe_pct": 2.7},
                {"date": "2026-01-06", "symbol": "COHR", "return_pct": -1, "mae_pct": -1.2, "mfe_pct": 0.3},
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "sector_fixture_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["events"][0]["context"]["sector_regime"] == "sector_strong"
    assert result["events"][1]["context"]["sector_regime"] == "sector_weak"
    assert result["context_segments"]["sector_regime=sector_strong"]["avg_return_pct"] == 2.0
    assert result["context_segments"]["sector_regime=sector_weak"]["avg_return_pct"] == -1.0


def test_stage_context_backtest_merges_brain_context_overlays_by_date(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    qqq = tmp_path / "QQQ.csv"
    vix = tmp_path / "VIX.csv"
    qqq.write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,100,101,99,100,1000",
            "2026-01-05,100,101,99,101,1000",
        ]),
        encoding="utf-8",
    )
    vix.write_text(
        "\n".join([
            "Date,Open,High,Low,Close,Volume",
            "2026-01-02,14,15,13,14,0",
            "2026-01-05,14,15,13,14,0",
        ]),
        encoding="utf-8",
    )
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_overlay_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": [
            "qqq_regime",
            "catalyst_bucket",
            "permission_state",
            "cognition_state",
        ],
        "data": {
            "mode": "joined_fixture_events",
            "stage_context_source": {
                "mode": "daily_market_fixture",
                "qqq_csv": str(qqq),
                "vix_csv": str(vix),
                "volume_csv": str(qqq),
            },
            "stage_context_overlays": [
                {
                    "date": "2026-01-05",
                    "context": {
                        "catalyst_bucket": "positive_company_catalyst",
                        "permission_state": "Yellow",
                        "cognition_state": "normal",
                    },
                    "source": "investing-os_fixture",
                }
            ],
            "events": [
                {"date": "2026-01-05", "symbol": "MU", "return_pct": 2, "mae_pct": -0.4, "mfe_pct": 2.7}
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "overlay_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    event_context = result["events"][0]["context"]
    assert event_context["qqq_regime"] == "qqq_uptrend"
    assert event_context["catalyst_bucket"] == "positive_company_catalyst"
    assert event_context["permission_state"] == "Yellow"
    assert event_context["cognition_state"] == "normal"
    assert result["data_quality"]["stage_context_overlay_count"] == 1
    assert result["events"][0]["context_source"] == "stage_context_by_date"


def test_stage_context_backtest_overlay_fields_do_not_create_permission_decision(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_overlay_boundary_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["permission_state"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_contexts": [
                {
                    "date": "2026-01-05",
                    "context": {"permission_state": "Yellow"},
                }
            ],
            "stage_context_overlays": [
                {
                    "date": "2026-01-05",
                    "context": {"catalyst_bucket": "positive_company_catalyst"},
                }
            ],
            "events": [
                {"date": "2026-01-05", "symbol": "MU", "return_pct": 2, "mae_pct": -0.4, "mfe_pct": 2.7}
            ],
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "overlay_boundary_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["boundaries"]["contains_permission_decision"] is False
    assert result["boundaries"]["config_mutation"] is False


def test_stage_context_backtest_reads_events_from_tactic_backtest_json(tmp_path):
    from stock_team.backtest.stage_context_backtest import run_request

    tactic_json = tmp_path / "tactic_backtest.json"
    tactic_json.write_text(json.dumps({
        "packet_type": "tactic_backtest_evidence_packet",
        "tactic_id": "vwap_reclaim",
        "events": [
            {
                "symbol": "MU",
                "entry_time": "2026-01-05T10:05:00-05:00",
                "return_pct": 2.0,
                "mae_pct": -0.4,
                "mfe_pct": 2.7,
            },
            {
                "symbol": "COHR",
                "entry_time": "2026-01-08T10:05:00-05:00",
                "return_pct": -1.5,
                "mae_pct": -2.1,
                "mfe_pct": 0.4,
            },
        ],
    }), encoding="utf-8")
    request = {
        "artifact_type": "stage_context_backtest_request",
        "version": "1.0",
        "requested_by": "investing-os",
        "study_id": "stage_gate_tactic_source_demo",
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "context_fields": ["qqq_regime"],
        "data": {
            "mode": "joined_fixture_events",
            "stage_contexts": [
                {"date": "2026-01-05", "context": {"qqq_regime": "qqq_uptrend"}},
                {"date": "2026-01-08", "context": {"qqq_regime": "qqq_downtrend"}},
            ],
            "events_source": {
                "mode": "tactic_backtest_json",
                "path": str(tactic_json),
            },
        },
        "output_contract": {
            "allow_recommendations": False,
            "allow_config_mutation": False,
        },
    }
    path = tmp_path / "stage_request.json"
    path.write_text(json.dumps(request), encoding="utf-8")

    result = run_request(path)

    assert result["summary"]["n_events"] == 2
    assert result["data_quality"]["event_source"] == "tactic_backtest_json"
    assert result["data_quality"]["event_source_count"] == 2
    assert result["events"][0]["tactic_id"] == "vwap_reclaim"
    assert result["events"][0]["date"] == "2026-01-05"
    assert result["context_segments"]["qqq_regime=qqq_uptrend"]["avg_return_pct"] == 2.0
