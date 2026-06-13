from __future__ import annotations

import subprocess

import pytest


def test_market_context_adapter_builds_existing_cli_command(tmp_path, monkeypatch):
    from stock_team.orchestration.adapters import ExistingCliAdapter

    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        (tmp_path / "stage0.md").write_text("packet", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    adapter.run(
        "start_stage0",
        {
            "date": "2026-06-15",
            "as_of": "2026-06-15T09:20:00-04:00",
            "universe": "universe.json",
            "pre_market_snapshot": "snapshot.json",
            "out": "stage0.md",
        },
    )

    assert calls[0][0][:4] == ["python", "-m", "stock_team.cli", "market-context"]
    assert calls[0][1]["timeout"] == 30


def test_adapter_timeout_is_retryable(tmp_path, monkeypatch):
    from stock_team.orchestration.adapters import AdapterError, ExistingCliAdapter

    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    with pytest.raises(AdapterError) as caught:
        adapter.run(
            "start_stage0",
            {
                "date": "2026-06-15",
                "as_of": "2026-06-15T09:20:00-04:00",
                "universe": "universe.json",
                "out": "stage0.md",
            },
        )

    assert caught.value.retryable is True
