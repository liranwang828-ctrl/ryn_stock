import json


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

    result = _get_latest_manifest(str(stock_team_home))

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
