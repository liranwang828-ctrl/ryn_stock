import json
import subprocess
import sys


def test_coordinator_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "stock_team.coordinator_cli", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    assert "init-day" in result.stdout
    assert "run" in result.stdout
    assert "show" in result.stdout


def test_coordinator_cli_initialize_and_show(tmp_path):
    init = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_team.coordinator_cli",
            "init-day",
            "--date",
            "2026-06-15",
            "--runtime-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert init.returncode == 0
    payload = json.loads(init.stdout)
    assert payload["state"] == "DAY_INITIALIZED"

    show = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_team.coordinator_cli",
            "show",
            "--session-id",
            "trading-2026-06-15",
            "--runtime-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert show.returncode == 0
    shown = json.loads(show.stdout)
    assert shown["session_id"] == "trading-2026-06-15"
