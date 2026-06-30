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


def test_init_day_defaults_to_trading(tmp_path):
    result = subprocess.run(
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
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["session_type"] == "trading"
    assert payload["session_id"] == "trading-2026-06-15"


def test_init_day_with_session_type_trading(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_team.coordinator_cli",
            "init-day",
            "--date",
            "2026-06-15",
            "--session-type",
            "trading",
            "--runtime-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["session_type"] == "trading"
    assert payload["session_id"] == "trading-2026-06-15"


def test_init_day_with_session_type_observation(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_team.coordinator_cli",
            "init-day",
            "--date",
            "2026-06-15",
            "--session-type",
            "observation",
            "--runtime-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["session_type"] == "observation"
    assert payload["session_id"] == "observation-2026-06-15"


def test_init_day_with_session_type_research(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_team.coordinator_cli",
            "init-day",
            "--date",
            "2026-06-15",
            "--session-type",
            "research",
            "--runtime-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["session_type"] == "research"
    assert payload["session_id"] == "research-2026-06-15"


def test_init_day_rejects_invalid_session_type(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_team.coordinator_cli",
            "init-day",
            "--date",
            "2026-06-15",
            "--session-type",
            "garbage_not_a_type",
            "--runtime-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode != 0
