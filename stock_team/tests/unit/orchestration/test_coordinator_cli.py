from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


WORKSPACE_DIR = Path(__file__).resolve().parents[4]
PYTHON = sys.executable


def test_coordinator_cli_help():
    res = subprocess.run(
        [PYTHON, "-m", "stock_team.coordinator_cli", "--help"],
        cwd=WORKSPACE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert res.returncode == 0
    assert "init-day" in res.stdout
    assert "run" in res.stdout
    assert "show" in res.stdout


def test_coordinator_cli_initialize_and_show(tmp_path):
    runtime_dir = tmp_path / "runtime"
    res = subprocess.run(
        [
            PYTHON,
            "-m",
            "stock_team.coordinator_cli",
            "init-day",
            "--date",
            "2026-06-15",
            "--runtime-dir",
            str(runtime_dir),
        ],
        cwd=WORKSPACE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert res.returncode == 0
    assert "DAY_INITIALIZED" in res.stdout

    show = subprocess.run(
        [
            PYTHON,
            "-m",
            "stock_team.coordinator_cli",
            "show",
            "--session-id",
            "trading-2026-06-15",
            "--runtime-dir",
            str(runtime_dir),
        ],
        cwd=WORKSPACE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert show.returncode == 0
    payload = json.loads(show.stdout)
    assert payload["state"] == "DAY_INITIALIZED"


def test_coordinator_cli_run_dispatches_action(tmp_path, monkeypatch):
    from stock_team import coordinator_cli

    action_path = tmp_path / "action.json"
    runtime_dir = tmp_path / "runtime"
    action_path.write_text(
        json.dumps(
            {
                "intent": "initialize_day",
                "session_id": "trading-2026-06-15",
                "expected_state": "IDLE",
                "user_confirmation": False,
                "parameters": {"market_date": "2026-06-15"},
                "idempotency_key": "init-1",
            }
        ),
        encoding="utf-8",
    )

    calls = []

    class FakeCoordinator:
        def __init__(self, store, adapter, now_fn=None):
            self.store = store
            self.adapter = adapter

        def execute(self, action):
            calls.append(action)
            return {"state": "DAY_INITIALIZED"}

    monkeypatch.setattr(coordinator_cli, "WorkflowCoordinator", FakeCoordinator)

    code = coordinator_cli.main(
        [
            "run",
            "--action",
            str(action_path),
            "--runtime-dir",
            str(runtime_dir),
        ]
    )

    assert code == 0
    assert calls[0]["intent"] == "initialize_day"

