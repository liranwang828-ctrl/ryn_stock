# tests/test_harvest_has_catalyst.py
import sys, os, json

from unittest.mock import patch, MagicMock
import pandas as pd


def _fake_obs_record(catalyst_strength=0):
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "date": today, "time": "10:00", "session": "morning",
        "sym": "LITE", "is_position": True, "price": 870.0,
        "rsi3": 45, "macd": 0.5, "rs_pct": 2.3,
        "gate_pass": True, "gate_block": "",
        "gate_detail": {}, "key_obs": "", "key_levels": {},
        "spy_chg": 0.005, "qqq5m": 0.003, "vix": 18.5,
        "vix_dir": "下降", "macro": "normal",
        "catalyst_strength": catalyst_strength,
        "vol_ratio": 0.75,
    }


def test_outcome_has_catalyst_true_when_strength_positive(tmp_path, monkeypatch):
    """catalyst_strength > 0 时 has_catalyst=True"""
    import stock_team.archive.deprecated_agents.harvest_agent as ha
    monkeypatch.setattr(ha, "OBS_LOG",  str(tmp_path / "obs.jsonl"))
    monkeypatch.setattr(ha, "OBS_OUT",  str(tmp_path / "outcomes.jsonl"))

    obs = _fake_obs_record(catalyst_strength=3)
    with open(ha.OBS_LOG, "w", encoding="utf-8") as f:
        f.write(json.dumps(obs) + "\n")

    fake_hist = pd.DataFrame({
        "Open":  [868.0, 875.0],
        "High":  [880.0, 882.0],
        "Low":   [860.0, 865.0],
        "Close": [870.0, 878.0],
    })
    with patch("yfinance.Ticker") as MockTicker:
        m = MagicMock()
        m.history.return_value = fake_hist
        MockTicker.return_value = m
        ha.process_observation_log()

    outcomes = [json.loads(l) for l in open(ha.OBS_OUT, encoding="utf-8")]
    assert len(outcomes) == 1
    assert outcomes[0]["has_catalyst"] is True


def test_outcome_has_catalyst_false_when_strength_zero(tmp_path, monkeypatch):
    """catalyst_strength == 0 时 has_catalyst=False"""
    import stock_team.archive.deprecated_agents.harvest_agent as ha
    monkeypatch.setattr(ha, "OBS_LOG",  str(tmp_path / "obs.jsonl"))
    monkeypatch.setattr(ha, "OBS_OUT",  str(tmp_path / "outcomes.jsonl"))

    obs = _fake_obs_record(catalyst_strength=0)
    with open(ha.OBS_LOG, "w", encoding="utf-8") as f:
        f.write(json.dumps(obs) + "\n")

    fake_hist = pd.DataFrame({
        "Open":  [868.0, 875.0], "High":  [880.0, 882.0],
        "Low":   [860.0, 865.0], "Close": [870.0, 878.0],
    })
    with patch("yfinance.Ticker") as MockTicker:
        m = MagicMock()
        m.history.return_value = fake_hist
        MockTicker.return_value = m
        ha.process_observation_log()

    outcomes = [json.loads(l) for l in open(ha.OBS_OUT, encoding="utf-8")]
    assert len(outcomes) == 1
    assert outcomes[0]["has_catalyst"] is False
