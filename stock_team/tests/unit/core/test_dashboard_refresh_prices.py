import json
from datetime import datetime


def test_updated_symbols_from_live_status_prefers_focus_symbols_with_detail(tmp_path):
    from stock_team.server.dashboard_server import updated_symbols_from_live_status

    path = tmp_path / "watchlist_live_status.json"
    path.write_text(json.dumps({
        "focus_symbols": ["NOW", "VST", "MISSING"],
        "symbols_detail": {
            "NOW": {"current_price": 99.92},
            "VST": {"current_price": 164.56},
            "CRM": {"current_price": 179.08},
        },
    }), encoding="utf-8")

    assert updated_symbols_from_live_status(str(path)) == ["NOW", "VST"]


def test_updated_symbols_from_live_status_falls_back_to_all_details(tmp_path):
    from stock_team.server.dashboard_server import updated_symbols_from_live_status

    path = tmp_path / "watchlist_live_status.json"
    path.write_text(json.dumps({
        "symbols_detail": {
            "COHR": {"current_price": 381.35},
            "GOOGL": {"current_price": 388.88},
        },
    }), encoding="utf-8")

    assert updated_symbols_from_live_status(str(path)) == ["COHR", "GOOGL"]


def test_price_refresh_state_sync_updates_positions_snapshot_and_nodes(tmp_path):
    from stock_team.server.dashboard_server import sync_price_refresh_state

    (tmp_path / "config").mkdir()
    (tmp_path / "findings" / "symbols" / "NOW").mkdir(parents=True)
    (tmp_path / "learning").mkdir()
    (tmp_path / "config" / "positions.json").write_text(json.dumps({
        "cash": 1000,
        "positions": {
            "NOW": {"shares": 2, "cost": 90},
            "VST": {"shares": 1, "cost": 150, "broker_last_price": 159},
        },
    }), encoding="utf-8")
    (tmp_path / "findings" / "watchlist_live_status.json").write_text(json.dumps({
        "refreshed_at": "2026-05-27 12:24:24",
        "focus_symbols": ["NOW", "VST"],
        "symbols_detail": {
            "NOW": {
                "current_price": 99.92,
                "buy_zone": {"min_price": 94, "max_price": 96},
                "hard_stop": 82,
                "target_price": 135,
                "status_cn": "接近黄金击球区",
            },
            "VST": {"current_price": 164.56},
        },
    }), encoding="utf-8")

    result = sync_price_refresh_state(str(tmp_path))

    assert result["updated"] == ["NOW", "VST"]
    positions = json.loads((tmp_path / "config" / "positions.json").read_text(encoding="utf-8"))
    assert positions["positions"]["NOW"]["broker_last_price"] == 99.92
    assert positions["positions"]["VST"]["broker_last_price"] == 164.56

    cache = json.loads((tmp_path / "learning" / "dashboard_cache.json").read_text(encoding="utf-8"))
    assert cache["intraday"]["NOW"]["price_now"]["price"] == 99.92
    assert cache["intraday"]["VST"]["price_now"]["price"] == 164.56

    snapshot = json.loads((tmp_path / "findings" / "portfolio_snapshot_current.json").read_text(encoding="utf-8"))
    assert [row["sym"] for row in snapshot["positions_detail"]] == ["NOW", "VST"]
    assert snapshot["positions_detail"][0]["cur_price"] == 99.92
    assert snapshot["totals"]["holdings_value"] == 364.4
    assert snapshot["totals"]["total_value"] == 1364.4

    nodes = json.loads((tmp_path / "findings" / "symbols" / "NOW" / "current_nodes.json").read_text(encoding="utf-8"))
    assert nodes["nodes"]["entry_base"]["price"] == 96
    assert nodes["nodes"]["hard_stop"]["price"] == 82
    assert nodes["nodes"]["target"]["price"] == 135


def test_build_stage0_universe_document_uses_snapshot_focus_symbols_and_positions(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _build_stage0_universe_document

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    (stock_team_home / "config").mkdir(parents=True)
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    (investing_os_home / "wiki" / "journals").mkdir(parents=True)

    (stock_team_home / "config" / "positions.json").write_text(json.dumps({
        "positions": {
            "NVDA": {"shares": 30, "tranche": "core", "thesis_status": "intact"},
            "MRVU": {"shares": 10, "tranche": "tactical", "thesis_status": "needs_review"},
        }
    }), encoding="utf-8")
    (investing_os_home / "system" / "runtime" / "inputs" / "trading-2026-06-15-pre-market-snapshot.json").write_text(
        json.dumps({
            "focus_symbols": "MRVU, GOOGL, ORCL",
            "themes": "ai_infrastructure, cloud",
        }),
        encoding="utf-8",
    )
    (investing_os_home / "wiki" / "journals" / "2026-06-14-review.md").write_text(
        "# review",
        encoding="utf-8",
    )

    universe_path, journal_path = _build_stage0_universe_document(
        str(stock_team_home),
        "2026-06-15",
        "trading-2026-06-15",
    )

    data = json.loads(open(universe_path, encoding="utf-8").read())
    symbols = {row["symbol"]: row for row in data["universe"]}

    assert journal_path.endswith("2026-06-14-review.md")
    assert set(symbols) == {"MRVU", "GOOGL", "ORCL", "NVDA"}
    assert symbols["NVDA"]["role"] == "current_position"
    assert symbols["MRVU"]["role"] == "current_position"
    assert symbols["GOOGL"]["role"] == "watchlist"
    assert symbols["ORCL"]["source"] == "snapshot_focus_symbols"


def test_stage0_snapshot_form_marks_manual_draft_not_ready(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _load_stage0_snapshot_form

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    snapshot_path = investing_os_home / "system" / "runtime" / "inputs" / "trading-2026-06-16-pre-market-snapshot.json"
    snapshot_path.write_text(json.dumps({
        "as_of_et": "2026-06-16T09:20:00-04:00",
        "window": "pre_market_before_09_30_ET",
        "markets": [
            {"symbol": "QQQ", "last": "736.7", "premarket_change_pct": "2.13", "note": "manual"},
        ],
        "themes": "ai_infrastructure",
        "focus_symbols": "AAOX, MUU",
    }), encoding="utf-8")

    data = _load_stage0_snapshot_form(str(stock_team_home), {"market_date": "2026-06-16", "session_id": "trading-2026-06-16"})

    assert data["exists"] is True
    assert data["formal_ready"] is False
    assert data["source_kind"] == "manual_draft"


def test_stage0_snapshot_form_marks_formal_provider_snapshot_ready(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _load_stage0_snapshot_form

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    snapshot_path = investing_os_home / "system" / "runtime" / "inputs" / "trading-2026-06-16-pre-market-snapshot.json"
    snapshot_path.write_text(json.dumps({
        "as_of_et": "2026-06-16T09:20:00-04:00",
        "window": "pre_market_before_09_30_ET",
        "markets": {
            "QQQ": {"price": 736.7, "prev_close": 721.34, "source": "polygon_premarket_snapshot"},
            "SPY": {"price": 751.15, "prev_close": 741.75, "source": "polygon_premarket_snapshot"},
            "IWM": {"price": 297.4, "prev_close": 292.25, "source": "polygon_premarket_snapshot"},
            "VIXY": {"price": 22.47, "prev_close": 23.29, "source": "polygon_premarket_snapshot"},
        },
        "themes": {
            "ai_infrastructure": {"proxy": "SMH", "return_5d": 8.18, "return_20d": 16.31, "source": "polygon_premarket_snapshot"}
        },
        "focus_symbols": "AAOX, MUU",
    }), encoding="utf-8")

    data = _load_stage0_snapshot_form(str(stock_team_home), {"market_date": "2026-06-16", "session_id": "trading-2026-06-16"})

    assert data["exists"] is True
    assert data["formal_ready"] is True
    assert data["source_kind"] == "formal_provider_snapshot"


def test_stage0_snapshot_form_marks_premarket_minute_snapshot_ready(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _load_stage0_snapshot_form

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    snapshot_path = investing_os_home / "system" / "runtime" / "inputs" / "trading-2026-06-16-pre-market-snapshot.json"
    snapshot_path.write_text(json.dumps({
        "as_of_et": "2026-06-16T09:20:00-04:00",
        "window": "pre_market_before_09_30_ET",
        "markets": {
            "QQQ": {"price": 742.92, "prev_close": 744.0, "source": "polygon_premarket_1m_aggregates", "latest_bar_time_et": "2026-06-16T09:20:00-04:00"},
            "SPY": {"price": 754.48, "prev_close": 754.83, "source": "polygon_premarket_1m_aggregates", "latest_bar_time_et": "2026-06-16T09:20:00-04:00"},
            "IWM": {"price": 295.07, "prev_close": 294.64, "source": "polygon_premarket_1m_aggregates", "latest_bar_time_et": "2026-06-16T09:20:00-04:00"},
            "VIXY": {"price": 21.8, "prev_close": 21.7, "source": "polygon_premarket_1m_aggregates", "latest_bar_time_et": "2026-06-16T09:14:00-04:00"},
        },
        "themes": {
            "ai_infrastructure": {"proxy": "SMH", "return_5d": 8.27, "return_20d": 16.86, "source": "polygon_premarket_1m_aggregates"}
        },
        "focus_symbols": "AAOX, MUU",
    }), encoding="utf-8")

    data = _load_stage0_snapshot_form(str(stock_team_home), {"market_date": "2026-06-16", "session_id": "trading-2026-06-16"})

    assert data["exists"] is True
    assert data["formal_ready"] is True
    assert data["source_kind"] == "formal_provider_snapshot"


def test_coordinator_summary_exposes_skill_guided_stage0_discussion(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "packets").mkdir(parents=True)
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    stage0_packet = investing_os_home / "system" / "runtime" / "packets" / "trading-2026-06-16-stage0-market-context.md"
    stage0_packet.write_text("# Stage 0", encoding="utf-8")

    session = {
        "session_id": "trading-2026-06-16",
        "state": "STAGE0_READY",
        "market_date": "2026-06-16",
    }

    payload = _coordinator_summary_payload(session, None, base_dir=str(stock_team_home))
    task = payload["current_task"]

    assert task["id"] == "stage0_discussion"
    assert task["recommended_skill"] == "pre-market-planning"
    assert task["skill_path"].endswith("agents{}pre-market-planning-agent.md".format("\\" if "\\" in task["skill_path"] else "/"))
    assert task["agent_role"] == "investing-os planning agent"
    assert task["inputs"][0]["exists"] is True
    assert task["outputs"][0]["path"].endswith("trading-2026-06-16-stage0-discussion-notes.md")
    assert task["outputs"][1]["path"].endswith("trading-2026-06-16-stage1-decision-sheet.json")
    assert payload["first_action"] == "record_focus_confirmation"


def test_bootstrap_current_task_outputs_creates_stage0_discussion_templates(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _bootstrap_current_task_outputs

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "packets").mkdir(parents=True)
    stage0_packet = investing_os_home / "system" / "runtime" / "packets" / "trading-2026-06-16-stage0-market-context.md"
    stage0_packet.write_text("# Stage 0", encoding="utf-8")

    session = {
        "session_id": "trading-2026-06-16",
        "state": "STAGE0_READY",
        "market_date": "2026-06-16",
    }

    result = _bootstrap_current_task_outputs(session, None, str(stock_team_home))

    assert result["created_paths"][0].endswith("trading-2026-06-16-stage0-discussion-notes.md")
    assert result["created_paths"][1].endswith("trading-2026-06-16-stage1-decision-sheet.json")
    assert "Stage 0 Discussion Notes" in open(result["created_paths"][0], encoding="utf-8").read()
    decision_sheet = json.loads(open(result["created_paths"][1], encoding="utf-8").read())
    assert decision_sheet["risk_mode"] == "observe_only"
    assert decision_sheet["user_confirmed"] is False


def test_bootstrap_current_task_outputs_creates_plan_approval_templates(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _bootstrap_current_task_outputs

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "packets").mkdir(parents=True)
    stage1_packet = investing_os_home / "system" / "runtime" / "packets" / "trading-2026-06-16-stage1-plan-evidence.md"
    stage1_packet.write_text("# Stage 1", encoding="utf-8")

    session = {
        "session_id": "trading-2026-06-16",
        "state": "STAGE1_READY",
        "market_date": "2026-06-16",
    }

    result = _bootstrap_current_task_outputs(session, None, str(stock_team_home))

    assert result["created_paths"][0].endswith("trading-2026-06-16-trading-plan.json")
    assert result["created_paths"][1].endswith("trading-2026-06-16-intraday-guidance.json")
    trading_plan = json.loads(open(result["created_paths"][0], encoding="utf-8").read())
    intraday_guidance = json.loads(open(result["created_paths"][1], encoding="utf-8").read())
    assert trading_plan["risk_mode"] == "observe_only"
    assert intraday_guidance["default_action"] == "observe_only"


def test_default_stage1_action_passes_market_date_to_cli_adapter(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _default_stage1_action

    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    session = {
        "session_id": "observation-2026-07-13",
        "state": "FOCUS_CONFIRMED",
        "market_date": "2026-07-13",
    }
    task = {
        "inputs": [
            {"role": "stock_team_packet", "path": "context.md"},
            {"role": "decision_sheet", "path": "decision.json"},
        ]
    }

    action = _default_stage1_action(str(tmp_path / "stock_team"), session, task)

    assert action["parameters"]["date"] == "2026-07-13"


def test_dashboard_reads_from_runtime_manifest(tmp_path, monkeypatch):
    """Dashboard reads snapshot paths from a coordinator manifest instead of constructing its own path."""
    from stock_team.server.dashboard_server import _get_latest_manifest

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    archive_dir = investing_os_home / "system" / "runtime" / "sessions" / "archive"
    archive_dir.mkdir(parents=True)

    manifest = {
        "date": "2026-07-01",
        "session_id": "trading-2026-07-01",
        "archived_at": "2026-07-01T09:30:00+00:00",
        "artifacts": [
            {
                "name": "pre-market-snapshot.json",
                "path": str(archive_dir / "trading-2026-07-01" / "pre-market-snapshot.json"),
                "hash": "abc123",
            },
            {
                "name": "stage0-market-context.md",
                "path": str(archive_dir / "trading-2026-07-01" / "stage0-market-context.md"),
                "hash": "def456",
            },
        ],
    }

    manifest_file = archive_dir / "trading-2026-07-01_manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    result = _get_latest_manifest(
        str(stock_team_home),
        now=datetime.fromisoformat("2026-07-01T10:00:00+00:00"),
    )

    assert result["status"] == "ok"
    assert result["manifest"]["session_id"] == "trading-2026-07-01"
    assert len(result["manifest"]["artifacts"]) == 2
    assert result["manifest"]["artifacts"][0]["name"] == "pre-market-snapshot.json"
    assert result["freshness"] == "fresh"
    assert result["manifest_path"] is not None


def test_dashboard_rejects_stale_manifest(tmp_path, monkeypatch):
    """Dashboard validates freshness timestamps and rejects stale data."""
    from datetime import datetime, timezone, timedelta
    from stock_team.server.dashboard_server import _get_latest_manifest

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    archive_dir = investing_os_home / "system" / "runtime" / "sessions" / "archive"
    archive_dir.mkdir(parents=True)

    old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    manifest = {
        "date": "2026-06-29",
        "session_id": "trading-2026-06-29",
        "archived_at": old_timestamp,
        "artifacts": [
            {
                "name": "pre-market-snapshot.json",
                "path": str(archive_dir / "trading-2026-06-29" / "pre-market-snapshot.json"),
                "hash": "abc123",
            },
        ],
    }

    manifest_file = archive_dir / "trading-2026-06-29_manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    result = _get_latest_manifest(str(stock_team_home))

    assert result["status"] == "ok"
    assert result["freshness"] == "stale"
    assert "manifest" in result


def test_get_latest_manifest_returns_missing_when_no_manifests(tmp_path, monkeypatch):
    """Dashboard handles missing manifests gracefully."""
    from stock_team.server.dashboard_server import _get_latest_manifest

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    (investing_os_home / "system" / "runtime").mkdir(parents=True)

    result = _get_latest_manifest(str(stock_team_home))

    assert result["status"] == "missing"
    assert result["manifest"] is None
    assert result["freshness"] == "no_manifest"


def test_get_latest_manifest_picks_newest_by_mtime(tmp_path, monkeypatch):
    """When multiple manifests exist, the newest (by file mtime) is returned."""
    import time as _time
    from stock_team.server.dashboard_server import _get_latest_manifest

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    archive_dir = investing_os_home / "system" / "runtime" / "sessions" / "archive"
    archive_dir.mkdir(parents=True)

    older = {
        "date": "2026-06-28",
        "session_id": "trading-2026-06-28",
        "archived_at": "2026-06-28T16:00:00+00:00",
        "artifacts": [],
    }
    newer = {
        "date": "2026-07-01",
        "session_id": "trading-2026-07-01",
        "archived_at": "2026-07-01T09:30:00+00:00",
        "artifacts": [{"name": "snapshot.json", "path": "/tmp/snapshot.json", "hash": "xyz"}],
    }

    older_file = archive_dir / "trading-2026-06-28_manifest.json"
    newer_file = archive_dir / "trading-2026-07-01_manifest.json"
    older_file.write_text(json.dumps(older), encoding="utf-8")
    _time.sleep(0.05)
    newer_file.write_text(json.dumps(newer), encoding="utf-8")

    result = _get_latest_manifest(str(stock_team_home))

    assert result["manifest"]["session_id"] == "trading-2026-07-01"
    assert len(result["manifest"]["artifacts"]) == 1


def test_default_stage0_action_uses_from_snapshot_when_formal_ready(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _default_stage0_action

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    (stock_team_home / "config").mkdir(parents=True)
    (stock_team_home / "config" / "positions.json").write_text(json.dumps({}), encoding="utf-8")
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    (investing_os_home / "system" / "runtime" / "packets").mkdir(parents=True)
    (investing_os_home / "wiki" / "journals").mkdir(parents=True)

    snapshot_path = investing_os_home / "system" / "runtime" / "inputs" / "trading-2026-07-01-pre-market-snapshot.json"
    snapshot_path.write_text(json.dumps({
        "markets": {
            "QQQ": {"price": 736.7, "prev_close": 721.34, "source": "polygon_premarket_snapshot"},
            "SPY": {"price": 751.15, "prev_close": 741.75, "source": "polygon_premarket_snapshot"},
            "IWM": {"price": 297.4, "prev_close": 292.25, "source": "polygon_premarket_snapshot"},
            "VIXY": {"price": 22.47, "prev_close": 23.29, "source": "polygon_premarket_snapshot"},
        },
    }), encoding="utf-8")

    session = {"session_id": "trading-2026-07-01", "market_date": "2026-07-01", "state": "DAY_INITIALIZED"}
    result = _default_stage0_action(str(stock_team_home), session)

    assert result["action"]["intent"] == "start_stage0_from_snapshot"
    assert "pre_market_snapshot" in result["action"]["parameters"]


def test_default_stage0_action_uses_start_stage0_when_not_formal_ready(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _default_stage0_action

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    (stock_team_home / "config").mkdir(parents=True)
    (stock_team_home / "config" / "positions.json").write_text(json.dumps({}), encoding="utf-8")
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    (investing_os_home / "system" / "runtime" / "packets").mkdir(parents=True)
    (investing_os_home / "wiki" / "journals").mkdir(parents=True)

    snapshot_path = investing_os_home / "system" / "runtime" / "inputs" / "trading-2026-07-01-pre-market-snapshot.json"
    snapshot_path.write_text(json.dumps({
        "markets": [
            {"symbol": "QQQ", "last": "736.7", "premarket_change_pct": "2.13", "note": "manual"},
        ],
    }), encoding="utf-8")

    session = {"session_id": "trading-2026-07-01", "market_date": "2026-07-01", "state": "DAY_INITIALIZED"}
    result = _default_stage0_action(str(stock_team_home), session)

    assert result["action"]["intent"] == "start_stage0"
    assert "pre_market_snapshot" not in result["action"]["parameters"]


def test_coordinator_first_action_returns_from_snapshot_when_formal_ready():
    from stock_team.server.dashboard_server import _coordinator_first_action

    assert _coordinator_first_action("pre_market", "DAY_INITIALIZED", None, formal_ready=True) == "start_stage0_from_snapshot"
    assert _coordinator_first_action("pre_market", "STAGE0_RUNNING", None, formal_ready=True) == "start_stage0_from_snapshot"


def test_coordinator_first_action_returns_start_stage0_when_not_formal_ready():
    from stock_team.server.dashboard_server import _coordinator_first_action

    assert _coordinator_first_action("pre_market", "DAY_INITIALIZED", None, formal_ready=False) == "start_stage0"
    assert _coordinator_first_action("pre_market", "STAGE0_RUNNING", None, formal_ready=False) == "start_stage0"


def test_coordinator_first_action_does_not_change_other_states():
    from stock_team.server.dashboard_server import _coordinator_first_action

    assert _coordinator_first_action("pre_market", "STAGE0_READY", None, formal_ready=True) == "record_focus_confirmation"
    assert _coordinator_first_action("pre_market", "FOCUS_CONFIRMED", None, formal_ready=True) == "start_stage1"
    assert _coordinator_first_action("pre_market", "STAGE1_READY", None, formal_ready=True) == "record_plan_approval"


def test_entry_state_payload_contains_five_core_fields():
    from stock_team.server.dashboard_server import _build_minimal_entry_state

    payload = _build_minimal_entry_state(
        {"mode": "trading", "state": "DAY_INITIALIZED", "next_action": "start_stage0"},
        [],
    )

    assert set(payload.keys()) == {
        "today_mode",
        "current_step",
        "readiness",
        "missing_items",
        "next_action",
    }


def test_coordinator_summary_payload_exposes_blocker_missing_items(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)

    session = {
        "session_id": "trading-2026-07-08",
        "state": "FAILED_TOOL",
        "market_date": "2026-07-08",
        "mode": "trading",
    }

    payload = _coordinator_summary_payload(session, None, base_dir=str(stock_team_home))

    assert payload["entry_state"]["missing_items"] == ["tool execution failed; inspect runtime inputs"]
    assert payload["entry_state"]["readiness"] == "blocked"


def test_coordinator_summary_payload_exposes_read_only_daily_status(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    session = {
        "session_id": "trading-2026-07-11",
        "session_type": "observation",
        "state": "DAY_INITIALIZED",
        "market_date": "2026-07-11",
        "mode": "observation",
    }

    payload = _coordinator_summary_payload(session, None, base_dir=str(stock_team_home))

    assert payload["daily_status"]["current_node"] == "DAILY-0"
    assert payload["daily_status"]["overall_status"] == "waiting_user"
    assert session.get("daily0_confirmation") is None


def test_coordinator_summary_payload_exposes_read_only_premarket_tape(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    inputs = investing_os_home / "system" / "runtime" / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "observation-2026-07-13-premarket-tape.json").write_text(json.dumps({
        "status": "partial",
        "generated_at_et": "2026-07-13T08:25:00-04:00",
        "records": {
            "NQ=F": {"symbol": "NQ=F", "asset_class": "index_future", "last": 29728.5, "change_pct": 0.1, "freshness": "fresh", "quality": "usable_observation"},
            "QQQ": {"symbol": "QQQ", "asset_class": "etf_premarket", "last": 717.62, "change_pct": -1.09, "freshness": "fresh", "quality": "degraded"},
        },
        "cross_asset_checks": {"QQQ_NQ": {"status": "conflicted"}},
        "missing_symbols": ["BTC-USD"],
        "warnings": ["BTC-USD:missing"],
    }), encoding="utf-8")
    session = {
        "session_id": "observation-2026-07-13",
        "session_type": "observation",
        "state": "STAGE0_READY",
        "market_date": "2026-07-13",
        "mode": "observation",
    }

    payload = _coordinator_summary_payload(session, None, base_dir=str(stock_team_home))

    assert payload["premarket_tape"]["status"] == "partial"
    assert payload["premarket_tape"]["groups"]["index_futures"][0]["symbol"] == "NQ=F"
    assert payload["premarket_tape"]["cross_asset_checks"]["QQQ_NQ"]["status"] == "conflicted"


def test_coordinator_summary_payload_handles_missing_premarket_tape(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    session = {
        "session_id": "observation-2026-07-13",
        "session_type": "observation",
        "state": "DAY_INITIALIZED",
        "market_date": "2026-07-13",
        "mode": "observation",
    }

    payload = _coordinator_summary_payload(session, None, base_dir=str(stock_team_home))

    assert payload["premarket_tape"] == {
        "status": "missing",
        "groups": {},
        "cross_asset_checks": {},
    }


def test_non_trading_day_recovery_compares_artifacts_with_last_trading_date(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    inputs = investing_os_home / "system" / "runtime" / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "trading-2026-06-15-stage0-universe.json").write_text(json.dumps({
        "date": "2026-06-15",
        "source_inputs": {"positions": [], "prior_review": {}, "cognition_state": {}},
        "permission_state_before_open": "Yellow",
        "forbidden_actions": [],
    }), encoding="utf-8")
    session = {
        "session_id": "trading-2026-06-15",
        "session_type": "observation",
        "state": "FAILED_TOOL",
        "market_date": "2026-06-15",
        "mode": "observation",
    }

    payload = _coordinator_summary_payload(
        session,
        None,
        base_dir=str(stock_team_home),
        trading_date_context={
            "trading_date": None,
            "last_trading_date": "2026-07-10",
            "calendar_status": "verified",
        },
        session_kind="recovery_required",
    )

    universe = next(item for item in payload["daily_status"]["artifacts"] if item["role"] == "stage0_universe")
    assert universe["valid"] is True
    assert universe["freshness"] == "stale"


def test_historical_failed_session_requires_conversation_resolution_not_retry(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    session = {
        "session_id": "trading-2026-06-15",
        "session_type": "trading",
        "state": "FAILED_TOOL",
        "market_date": "2026-06-15",
        "mode": "trading",
        "last_error": {"retryable": False, "intent": "start_stage0"},
    }

    payload = _coordinator_summary_payload(
        session,
        None,
        base_dir=str(stock_team_home),
        trading_date_context={"trading_date": "2026-07-13", "calendar_status": "verified"},
        session_kind="recovery_required",
    )

    assert payload["first_action"] == "resolve_historical_session_in_conversation"
    assert payload["next_step"] == "resolve-historical-session"
    assert payload["entry_state"]["readiness"] == "blocked"
    assert payload["entry_state"]["next_action"] == "resolve_historical_session_in_conversation"
    assert "retry" not in payload["current_task"]["summary"].lower()


def test_historical_failed_session_entry_state_reuses_daily_status_blocker(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "inputs").mkdir(parents=True)
    session = {
        "session_id": "trading-2026-06-15",
        "session_type": "trading",
        "state": "FAILED_TOOL",
        "market_date": "2026-06-15",
        "mode": "trading",
        "last_error": {"retryable": False, "intent": "start_stage0"},
    }

    payload = _coordinator_summary_payload(
        session,
        None,
        base_dir=str(stock_team_home),
        trading_date_context={"trading_date": "2026-07-13", "calendar_status": "verified"},
        session_kind="recovery_required",
    )

    assert payload["entry_state"]["readiness"] == "blocked"
    assert payload["entry_state"]["next_action"] == "resolve_historical_session_in_conversation"
    assert payload["entry_state"]["missing_items"] == [
        item["message"] for item in payload["daily_status"]["missing_items"]
    ]
    assert any(
        item["code"] == "historical_session_blocking"
        for item in payload["daily_status"]["missing_items"]
    )


def test_operating_console_uses_daily_status_as_read_only_workflow_view():
    from pathlib import Path

    page = (Path(__file__).parents[4] / "investing-os" / "dashboards" / "operating-console.html").read_text(encoding="utf-8")

    assert "manifest.daily_status" in page
    assert 'id="todayPrompt"' in page
    assert 'fetch("/api/coordinator-summary")' in page
    assert 'method: "POST"' not in page
    assert 'data-choice="init_day"' not in page
    assert 'data-choice="record_focus_confirmation"' not in page
    assert 'data-choice="start_stage1"' not in page
    assert "manifest.trading_date_context" in page
    assert "manifest.session_kind" in page
    assert 'id="tradingDateEt"' in page
    assert 'id="beijingTime"' in page
    assert 'id="sessionKind"' in page
    assert "resolve_historical_session_in_conversation" in page
    assert 'id="premarketTape"' in page
    assert "manifest.premarket_tape" in page


def test_dashboard_session_selection_prefers_current_open_session_over_terminal_history():
    from stock_team.server.dashboard_server import _select_dashboard_session

    sessions = [
        {"session_id": "trading-2026-07-10", "market_date": "2026-07-10", "state": "DAY_ARCHIVED"},
        {"session_id": "trading-2026-07-13", "market_date": "2026-07-13", "state": "DAY_INITIALIZED"},
    ]

    selected = _select_dashboard_session(sessions, {"trading_date": "2026-07-13", "calendar_status": "verified"})

    assert selected["session"]["session_id"] == "trading-2026-07-13"
    assert selected["session_kind"] == "current"


def test_dashboard_session_selection_marks_single_old_open_session_for_recovery():
    from stock_team.server.dashboard_server import _select_dashboard_session

    sessions = [
        {"session_id": "trading-2026-07-10", "market_date": "2026-07-10", "state": "STAGE0_READY"},
    ]

    selected = _select_dashboard_session(sessions, {"trading_date": "2026-07-13", "calendar_status": "verified"})

    assert selected["session_kind"] == "recovery_required"
    assert selected["session"]["session_id"] == "trading-2026-07-10"


def test_dashboard_session_selection_blocks_multiple_open_sessions():
    from stock_team.server.dashboard_server import _select_dashboard_session

    sessions = [
        {"session_id": "trading-2026-07-09", "market_date": "2026-07-09", "state": "STAGE0_READY"},
        {"session_id": "trading-2026-07-10", "market_date": "2026-07-10", "state": "PLAN_APPROVED"},
    ]

    selected = _select_dashboard_session(sessions, {"trading_date": "2026-07-13", "calendar_status": "verified"})

    assert selected["session"] is None
    assert selected["session_kind"] == "blocked"
    assert selected["diagnostics"]


def test_dashboard_session_selection_treats_same_day_archived_session_as_history():
    from stock_team.server.dashboard_server import _select_dashboard_session

    sessions = [
        {"session_id": "trading-2026-07-14", "market_date": "2026-07-14", "state": "DAY_ARCHIVED"},
    ]

    selected = _select_dashboard_session(sessions, {"trading_date": "2026-07-14", "calendar_status": "verified"})

    assert selected["session"]["session_id"] == "trading-2026-07-14"
    assert selected["session_kind"] == "history"


def test_dashboard_session_selection_ignores_same_day_archived_when_older_session_needs_recovery():
    from stock_team.server.dashboard_server import _select_dashboard_session

    sessions = [
        {"session_id": "trading-2026-07-14", "market_date": "2026-07-14", "state": "DAY_ARCHIVED"},
        {"session_id": "trading-2026-07-13", "market_date": "2026-07-13", "state": "PLAN_APPROVED"},
    ]

    selected = _select_dashboard_session(sessions, {"trading_date": "2026-07-14", "calendar_status": "verified"})

    assert selected["session"]["session_id"] == "trading-2026-07-13"
    assert selected["session_kind"] == "recovery_required"


def test_dashboard_session_selection_does_not_create_session_on_non_trading_day():
    from stock_team.server.dashboard_server import _select_dashboard_session

    selected = _select_dashboard_session([], {
        "trading_date": None,
        "calendar_status": "verified",
        "session_kind": "non_trading_day",
    })

    assert selected["session"] is None
    assert selected["session_kind"] == "not_started"


def test_dashboard_today_ignores_historical_artifacts_for_readiness(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    runtime_root = investing_os_home / "system" / "runtime"
    inputs_dir = runtime_root / "inputs"
    packets_dir = runtime_root / "packets"
    inputs_dir.mkdir(parents=True)
    packets_dir.mkdir(parents=True)

    (inputs_dir / "observation-2026-07-13-stage0-universe.json").write_text(
        json.dumps({
            "date": "2026-07-13",
            "source_inputs": {"positions": [], "prior_review": {}, "cognition_state": {}},
            "permission_state_before_open": "Yellow",
            "forbidden_actions": [],
        }),
        encoding="utf-8",
    )
    (packets_dir / "observation-2026-07-13-stage0-market-context.md").write_text("# stale", encoding="utf-8")

    session = {
        "session_id": "observation-2026-07-13",
        "market_date": "2026-07-13",
        "trading_date": "2026-07-13",
        "state": "PLAN_APPROVED",
        "mode": "observation",
        "session_type": "observation",
        "daily0_confirmation": {"user_confirmed": True},
        "allowed_actions": [],
        "completed": {"artifacts": []},
    }

    payload = _coordinator_summary_payload(
        session,
        None,
        base_dir=str(stock_team_home),
        trading_date_context={"trading_date": "2026-07-14", "calendar_status": "verified"},
        session_kind="recovery_required",
    )

    assert payload["entry_state"]["readiness"] == "blocked"
    assert payload["daily_status"]["overall_status"] == "blocked"
    assert "historical_session_blocking" in {
        item["code"] for item in payload["daily_status"]["missing_items"]
    }
    historical_artifacts = [
        artifact
        for artifact in payload["daily_status"]["artifacts"]
        if artifact["path"].endswith("2026-07-13-stage0-universe.json")
        or artifact["path"].endswith("2026-07-13-stage0-market-context.md")
    ]
    assert historical_artifacts
    assert all(artifact["freshness"] == "stale" for artifact in historical_artifacts)
    assert all("trading_date_mismatch" in artifact["issues"] for artifact in historical_artifacts)


def test_dashboard_summary_uses_same_historical_session_blocker_as_daily_status(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    runtime_root = investing_os_home / "system" / "runtime"
    inputs_dir = runtime_root / "inputs"
    packets_dir = runtime_root / "packets"
    inputs_dir.mkdir(parents=True)
    packets_dir.mkdir(parents=True)

    (inputs_dir / "observation-2026-07-13-stage0-universe.json").write_text(
        json.dumps({
            "date": "2026-07-13",
            "source_inputs": {"positions": [], "prior_review": {}, "cognition_state": {}},
            "permission_state_before_open": "Yellow",
            "forbidden_actions": [],
        }),
        encoding="utf-8",
    )
    (packets_dir / "observation-2026-07-13-stage0-market-context.md").write_text("# stale", encoding="utf-8")

    session = {
        "session_id": "observation-2026-07-13",
        "market_date": "2026-07-13",
        "trading_date": "2026-07-13",
        "state": "PLAN_APPROVED",
        "mode": "observation",
        "session_type": "observation",
        "daily0_confirmation": {"user_confirmed": True},
        "allowed_actions": [],
        "completed": {"artifacts": []},
    }

    payload = _coordinator_summary_payload(
        session,
        None,
        base_dir=str(stock_team_home),
        trading_date_context={"trading_date": "2026-07-14", "calendar_status": "verified"},
        session_kind="recovery_required",
    )

    assert payload["entry_state"]["readiness"] == "blocked"
    assert payload["entry_state"]["next_action"] == "resolve_historical_session_in_conversation"
    assert payload["entry_state"]["missing_items"] == [
        item["message"] for item in payload["daily_status"]["missing_items"]
    ]
    assert payload["daily_status"]["overall_status"] == "blocked"
    assert any(
        item["code"] == "historical_session_blocking"
        for item in payload["daily_status"]["missing_items"]
    )


def test_daily_status_does_not_block_resolved_historical_sessions(tmp_path):
    from stock_team.orchestration.daily_status import build_daily_status

    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir(parents=True)

    status = build_daily_status(
        session={
            "session_id": "trading-2026-07-13",
            "market_date": "2026-07-13",
            "state": "IDLE",
            "mode": "trading",
            "session_type": "trading",
        },
        runtime_root=runtime_root,
        active_trading_date="2026-07-14",
    )

    assert status["overall_status"] != "blocked"
    assert "historical_session_blocking" not in {
        item["code"] for item in status["missing_items"]
    }


def test_operating_console_has_four_hash_pages_without_duplicate_legacy_summaries():
    from pathlib import Path

    page = (Path(__file__).parents[4] / "investing-os" / "dashboards" / "operating-console.html").read_text(encoding="utf-8")

    for element_id in ("pageToday", "pageEvidence", "pageReview", "pageDiagnostics"):
        assert f'id="{element_id}"' in page
    for route in ("#today", "#evidence", "#review", "#diagnostics"):
        assert f'href="{route}"' in page
    assert "setPageFromHash" in page
    assert "window.addEventListener(\"hashchange\"" in page
    for removed in (
        "dailyStepSummary", "factReadinessSummary",
        "conversationPromptSummary", "todayFocusSummary",
        "Minimal Entry State", "Daily Routes",
    ):
        assert removed not in page
