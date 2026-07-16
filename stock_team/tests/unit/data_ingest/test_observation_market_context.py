import json
import sys
import types
from datetime import datetime

import pytest


def _history(symbol):
    return {
        "price": {"QQQ": 725.51, "SPY": 754.95, "IWM": 295.99, "VIXY": 20.34}[symbol],
        "prev_close": {"QQQ": 723.28, "SPY": 751.71, "IWM": 297.24, "VIXY": 20.81}[symbol],
        "data_as_of": "2026-07-10T16:00:00-04:00",
        "source": "fake_history",
    }


def test_build_observation_context_writes_labeled_snapshot_and_packet(tmp_path):
    from stock_team.data_ingest.observation_market_context import build_observation_context

    snapshot_path = tmp_path / "snapshot.json"
    packet_path = tmp_path / "context.md"
    result = build_observation_context(
        trading_date="2026-07-10",
        as_of_et=datetime.fromisoformat("2026-07-10T08:30:00-04:00"),
        snapshot_path=snapshot_path,
        packet_path=packet_path,
        history_loader=_history,
    )

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert result == [str(snapshot_path), str(packet_path)]
    assert snapshot["evidence_level"] == "observation_only"
    assert snapshot["permission"] == "no_trading_permission"
    assert set(snapshot["markets"]) == {"QQQ", "SPY", "IWM", "VIXY"}
    assert all(row["price"] and row["prev_close"] and row["data_as_of"] for row in snapshot["markets"].values())
    packet = packet_path.read_text(encoding="utf-8")
    assert "observation_only" in packet
    assert "no_trading_permission" in packet


def test_build_observation_context_does_not_publish_partial_outputs(tmp_path):
    from stock_team.data_ingest.observation_market_context import build_observation_context

    def incomplete(symbol):
        return {} if symbol == "IWM" else _history(symbol)

    snapshot_path = tmp_path / "snapshot.json"
    packet_path = tmp_path / "context.md"
    with pytest.raises(RuntimeError, match="IWM"):
        build_observation_context(
            trading_date="2026-07-10",
            as_of_et=datetime.fromisoformat("2026-07-10T08:30:00-04:00"),
            snapshot_path=snapshot_path,
            packet_path=packet_path,
            history_loader=incomplete,
        )

    assert not snapshot_path.exists()
    assert not packet_path.exists()


def test_build_observation_context_labels_snapshot_as_premarket_not_daily_close(tmp_path):
    from stock_team.data_ingest.observation_market_context import build_observation_context

    snapshot_path = tmp_path / "snapshot.json"
    packet_path = tmp_path / "context.md"
    build_observation_context(
        trading_date="2026-07-10",
        as_of_et=datetime.fromisoformat("2026-07-10T08:30:00-04:00"),
        snapshot_path=snapshot_path,
        packet_path=packet_path,
        history_loader=_history,
    )

    packet = packet_path.read_text(encoding="utf-8")
    assert "Latest Premarket Quote" in packet
    assert "Latest Daily Close" not in packet


def test_yfinance_history_uses_intraday_premarket_series_not_daily_close(monkeypatch):
    import pandas as pd

    from stock_team.data_ingest.observation_market_context import _yfinance_history

    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **kwargs):
            calls.append(kwargs)
            if kwargs.get("interval") == "1m":
                idx = pd.DatetimeIndex([
                    "2026-07-10T08:28:00-04:00",
                    "2026-07-10T08:29:00-04:00",
                ])
                return pd.DataFrame({
                    "Close": [724.12, 725.51],
                    "Volume": [100, 150],
                }, index=idx)
            idx = pd.DatetimeIndex([
                "2026-07-09T16:00:00-04:00",
                "2026-07-10T16:00:00-04:00",
            ])
            return pd.DataFrame({
                "Close": [723.28, 726.00],
            }, index=idx)

    fake_module = types.SimpleNamespace(Ticker=FakeTicker)
    monkeypatch.setitem(sys.modules, "yfinance", fake_module)

    row = _yfinance_history("QQQ")

    assert any(call.get("interval") == "1m" and call.get("prepost") is True for call in calls)
    assert row["price"] == 725.51
    assert row["prev_close"] == 723.28
    assert row["data_as_of"] == "2026-07-10T08:29:00-04:00"
    assert row["source"] == "yfinance_1m_prepost"
