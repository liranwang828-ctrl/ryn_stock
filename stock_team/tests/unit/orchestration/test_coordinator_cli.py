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


def test_init_day_detects_unclosed_previous_session(tmp_path):
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    prev = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    prev["state"] = "INTRADAY_ACTIVE"
    store.create(prev)

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
    )
    assert result.returncode == 1
    stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    assert "trading-2026-06-14" in stderr_text


def test_init_day_recovery_freeze_closes_previous(tmp_path):
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    prev = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    prev["state"] = "INTRADAY_ACTIVE"
    store.create(prev)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_team.coordinator_cli",
            "init-day",
            "--date",
            "2026-06-15",
            "--recovery",
            "freeze",
            "--runtime-dir",
            str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    closed = store.load("trading-2026-06-14")
    assert closed["state"] == "DAY_ARCHIVED"
    new_session = json.loads(result.stdout.decode("utf-8", errors="replace"))
    assert new_session["session_id"] == "trading-2026-06-15"


def test_init_day_no_recovery_needed_when_previous_is_archived(tmp_path):
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    prev = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    prev["state"] = "DAY_ARCHIVED"
    store.create(prev)

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
    )
    assert result.returncode == 0
    new_session = json.loads(result.stdout.decode("utf-8", errors="replace"))
    assert new_session["session_id"] == "trading-2026-06-15"


# ---------------------------------------------------------------------------
# L3: H1 cross-day recovery tests
# ---------------------------------------------------------------------------


def test_init_day_blocks_on_damaged_session_file(tmp_path):
    """H1 §3.2: damaged session files are detected and block init-day."""
    (tmp_path / "corrupt.json").write_text("{not valid json", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 1
    stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    assert "damaged" in stderr_text.lower()


def test_init_day_blocks_on_multiple_old_unclosed_sessions(tmp_path):
    """H1 §3.3: more than one unclosed old session blocks init-day."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    for date_str in ("2026-06-13", "2026-06-14"):
        s = new_trading_session(f"trading-{date_str}", date_str, f"{date_str}T12:00:00+00:00")
        s["state"] = "INTRADAY_ACTIVE"
        store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 1
    stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    assert "trading-2026-06-14" in stderr_text


def test_init_day_blocks_on_failed_tool_session(tmp_path):
    """H1 §3.3: FAILED_TOOL state blocks init-day, requires manual investigation."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "FAILED_TOOL"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 1
    stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    assert "FAILED_TOOL" in stderr_text


def test_init_day_review_required_rejects_freeze_and_quick_review(tmp_path):
    """H1 §3.3: REVIEW_REQUIRED state only allows --recovery full_review."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "REVIEW_REQUIRED"
    store.create(s)

    for recovery in ("freeze", "quick_review"):
        result = subprocess.run(
            [
                sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
                "--date", "2026-06-15", "--recovery", recovery,
                "--runtime-dir", str(tmp_path),
            ],
            capture_output=True,
        )
        assert result.returncode == 1, f"{recovery} should be rejected for REVIEW_REQUIRED"
        stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        assert "REVIEW_REQUIRED" in stderr_text


def test_init_day_full_review_from_market_closed(tmp_path):
    """H1 §3.4: full_review from MARKET_CLOSED transitions to REVIEW_REQUIRED, no today session."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "MARKET_CLOSED"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--recovery", "full_review",
            "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    old = store.load("trading-2026-06-14")
    assert old["state"] == "REVIEW_REQUIRED"
    assert not (tmp_path / "trading-2026-06-15.json").exists()


def test_init_day_full_review_from_review_required_no_transition(tmp_path):
    """H1 §3.4: full_review from REVIEW_REQUIRED does not re-transition, just prints message."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "REVIEW_REQUIRED"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--recovery", "full_review",
            "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    old = store.load("trading-2026-06-14")
    assert old["state"] == "REVIEW_REQUIRED"
    assert not (tmp_path / "trading-2026-06-15.json").exists()


def test_init_day_recovery_quick_review_from_intraday_active(tmp_path):
    """H1 §3.5: quick_review closes market if active, quick reviews, archives, creates today."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "INTRADAY_ACTIVE"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--recovery", "quick_review",
            "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    old = store.load("trading-2026-06-14")
    assert old["state"] == "DAY_ARCHIVED"
    new_session = json.loads(result.stdout.decode("utf-8", errors="replace"))
    assert new_session["session_id"] == "trading-2026-06-15"


def test_init_day_recovery_freeze_from_observation_active(tmp_path):
    """H1 §3.5: freeze closes observation, freezes, archives, creates today."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("observation-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00",
                            session_type="observation")
    s["state"] = "OBSERVATION_ACTIVE"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--recovery", "freeze",
            "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    old = store.load("observation-2026-06-14")
    assert old["state"] == "DAY_ARCHIVED"
    new_session = json.loads(result.stdout.decode("utf-8", errors="replace"))
    assert new_session["session_id"] == "trading-2026-06-15"


def test_init_day_recovery_freeze_from_market_closed_skips_close(tmp_path):
    """H1 §3.5: freeze from MARKET_CLOSED skips close_market, freezes directly."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "MARKET_CLOSED"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--recovery", "freeze",
            "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    old = store.load("trading-2026-06-14")
    assert old["state"] == "DAY_ARCHIVED"


def test_init_day_quick_review_from_market_closed(tmp_path):
    """H1 §3.5: quick_review from MARKET_CLOSED skips close_market, quick reviews directly."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "MARKET_CLOSED"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--recovery", "quick_review",
            "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    old = store.load("trading-2026-06-14")
    assert old["state"] == "DAY_ARCHIVED"


def test_init_day_full_review_from_intraday_active(tmp_path):
    """H1 §3.4-3.5: full_review from INTRADAY_ACTIVE closes market first, then reviews."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "INTRADAY_ACTIVE"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--recovery", "full_review",
            "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    old = store.load("trading-2026-06-14")
    assert old["state"] == "REVIEW_REQUIRED"
    assert not (tmp_path / "trading-2026-06-15.json").exists()


def test_init_day_full_review_from_observation_active(tmp_path):
    """H1 §3.5: full_review from OBSERVATION_ACTIVE closes market first, then reviews."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("observation-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00",
                            session_type="observation")
    s["state"] = "OBSERVATION_ACTIVE"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--recovery", "full_review",
            "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    old = store.load("observation-2026-06-14")
    assert old["state"] == "REVIEW_REQUIRED"
    assert not (tmp_path / "trading-2026-06-15.json").exists()


def test_init_day_recovery_preserves_stderr_message(tmp_path):
    """H1 §3.3: when no --recovery given, stderr explains available recovery options."""
    from stock_team.orchestration.models import new_trading_session
    from stock_team.orchestration.store import SessionStore

    store = SessionStore(tmp_path)
    s = new_trading_session("trading-2026-06-14", "2026-06-14", "2026-06-14T12:00:00+00:00")
    s["state"] = "INTRADAY_ACTIVE"
    store.create(s)

    result = subprocess.run(
        [
            sys.executable, "-m", "stock_team.coordinator_cli", "init-day",
            "--date", "2026-06-15", "--runtime-dir", str(tmp_path),
        ],
        capture_output=True,
    )
    assert result.returncode == 1
    stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    assert "trading-2026-06-14" in stderr_text
    assert "freeze" in stderr_text
    assert "quick_review" in stderr_text
    assert "full_review" in stderr_text
