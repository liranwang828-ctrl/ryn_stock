import json
from datetime import datetime

import pytest


def test_etf_record_uses_prior_regular_close_and_intraday_last_bar():
    from stock_team.data_ingest.premarket_tape import normalize_record

    record = normalize_record(
        symbol="QQQ",
        asset_class="etf_premarket",
        last=717.62,
        comparison_value=725.51,
        comparison_kind="prior_regular_close",
        as_of_et="2026-07-13T08:21:46-04:00",
        source="yfinance_1m_prepost",
        now_et=datetime.fromisoformat("2026-07-13T08:25:00-04:00"),
        reported_volume=0,
    )

    assert record["change_pct"] == -1.09
    assert record["freshness"] == "fresh"
    assert record["quality"] == "degraded"
    assert record["issues"] == ["zero_reported_volume"]


def test_unknown_comparison_kind_is_not_usable():
    from stock_team.data_ingest.premarket_tape import normalize_record

    record = normalize_record(
        symbol="NQ=F",
        asset_class="index_future",
        last=29728.5,
        comparison_value=29695.25,
        comparison_kind="provider_defined_unknown",
        as_of_et="2026-07-13T08:11:00-04:00",
        source="yfinance_fast_info",
        now_et=datetime.fromisoformat("2026-07-13T08:12:00-04:00"),
    )

    assert record["quality"] == "degraded"
    assert "comparison_semantics_unknown" in record["issues"]


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        ("2026-07-13T08:15:00-04:00", "fresh"),
        ("2026-07-13T08:14:59-04:00", "aging"),
        ("2026-07-13T07:55:00-04:00", "aging"),
        ("2026-07-13T07:54:59-04:00", "stale"),
    ],
)
def test_freshness_boundaries(as_of, expected):
    from stock_team.data_ingest.premarket_tape import classify_freshness

    now = datetime.fromisoformat("2026-07-13T08:25:00-04:00")
    assert classify_freshness(as_of, now) == expected


def test_future_timestamp_is_degraded():
    from stock_team.data_ingest.premarket_tape import normalize_record

    record = normalize_record(
        symbol="ES=F",
        asset_class="index_future",
        last=100,
        comparison_value=99,
        comparison_kind="prior_futures_settlement_or_provider_previous_close",
        as_of_et="2026-07-13T08:28:00-04:00",
        source="fake",
        now_et=datetime.fromisoformat("2026-07-13T08:25:00-04:00"),
    )
    assert record["quality"] == "degraded"
    assert "timestamp_in_future" in record["issues"]


def test_small_future_offset_during_sequential_fetch_is_tolerated():
    from stock_team.data_ingest.premarket_tape import normalize_record

    record = normalize_record(
        symbol="QQQ",
        asset_class="etf_premarket",
        last=100,
        comparison_value=99,
        comparison_kind="prior_regular_close",
        as_of_et="2026-07-13T08:26:00-04:00",
        source="fake",
        now_et=datetime.fromisoformat("2026-07-13T08:25:00-04:00"),
        reported_volume=1,
    )
    assert "timestamp_in_future" not in record["issues"]
    assert record["quality"] == "usable_observation"


def test_qqq_nq_opposite_directions_are_conflicted():
    from stock_team.data_ingest.premarket_tape import compare_pair

    result = compare_pair(
        "QQQ_NQ",
        {"change_pct": -1.09, "quality": "degraded", "freshness": "fresh"},
        {"change_pct": 0.30, "quality": "usable_observation", "freshness": "fresh"},
    )
    assert result["status"] == "conflicted"


def test_stale_member_makes_pair_insufficient_quality():
    from stock_team.data_ingest.premarket_tape import compare_pair

    result = compare_pair(
        "QQQ_NQ",
        {"change_pct": -0.2, "quality": "stale_unverified", "freshness": "stale"},
        {"change_pct": -0.1, "quality": "usable_observation", "freshness": "fresh"},
    )
    assert result["status"] == "insufficient_quality"


def _fake_loader(symbol, asset_class, now_et):
    changes = {
        "QQQ": -1.0,
        "NQ=F": 0.2,
        "SPY": -0.1,
        "ES=F": -0.1,
        "IWM": 0.1,
        "RTY=F": 0.1,
    }
    comparison = 100.0
    last = comparison * (1 + changes.get(symbol, 0.0) / 100)
    kind = (
        "prior_regular_close"
        if asset_class in {"etf_premarket", "focus_equity_premarket", "volatility"}
        else "prior_24h_reference"
        if asset_class == "crypto"
        else "prior_futures_settlement_or_provider_previous_close"
    )
    return {
        "last": last,
        "comparison_value": comparison,
        "comparison_kind": kind,
        "as_of_et": now_et.isoformat(),
        "source": "fake_loader",
        "reported_volume": 1,
    }


def test_build_premarket_tape_writes_observation_payload(tmp_path):
    from stock_team.data_ingest.premarket_tape import build_premarket_tape

    out = tmp_path / "tape.json"
    payload = build_premarket_tape(
        trading_date="2026-07-13",
        session_id="observation-2026-07-13",
        now_et=datetime.fromisoformat("2026-07-13T08:25:00-04:00"),
        output_path=out,
        focus_symbols=["AMAT", "TSM"],
        record_loader=_fake_loader,
    )

    assert payload["evidence_level"] == "observation_only"
    assert payload["permission"] == "no_trading_permission"
    assert payload["cross_asset_checks"]["QQQ_NQ"]["status"] == "conflicted"
    assert json.loads(out.read_text(encoding="utf-8"))["session_id"] == "observation-2026-07-13"


def test_non_core_failure_publishes_partial_payload(tmp_path):
    from stock_team.data_ingest.premarket_tape import build_premarket_tape

    def loader(symbol, asset_class, now_et):
        if symbol == "AMAT":
            raise RuntimeError("missing")
        return _fake_loader(symbol, asset_class, now_et)

    payload = build_premarket_tape(
        trading_date="2026-07-13",
        session_id="observation-2026-07-13",
        now_et=datetime.fromisoformat("2026-07-13T08:25:00-04:00"),
        output_path=tmp_path / "tape.json",
        focus_symbols=["AMAT"],
        record_loader=loader,
    )
    assert payload["status"] == "partial"
    assert payload["missing_symbols"] == ["AMAT"]


def test_all_core_failures_do_not_publish_output(tmp_path):
    from stock_team.data_ingest.premarket_tape import CORE_SYMBOLS, build_premarket_tape

    def loader(symbol, asset_class, now_et):
        if symbol in CORE_SYMBOLS:
            raise RuntimeError("core missing")
        return _fake_loader(symbol, asset_class, now_et)

    out = tmp_path / "tape.json"
    with pytest.raises(RuntimeError, match="all core premarket symbols missing"):
        build_premarket_tape(
            trading_date="2026-07-13",
            session_id="observation-2026-07-13",
            now_et=datetime.fromisoformat("2026-07-13T08:25:00-04:00"),
            output_path=out,
            record_loader=loader,
        )
    assert not out.exists()
