import json
from pathlib import Path

import pytest


def _make_session_file(sessions_dir, session_id, artifacts=None):
    """Create session file at sessions_dir/{session_id}.json (mimics runtime/sessions/)."""
    session_file = sessions_dir / f"{session_id}.json"
    session_data = {
        "session_id": session_id,
        "session_type": "trading",
        "state": "REVIEW_REQUIRED",
        "state_version": 5,
        "market_date": "2026-06-15",
        "artifacts": artifacts or [],
        "data_quality": {"status": "unknown", "warnings": []},
        "pending_confirmations": [],
        "allowed_actions": [],
        "processed_actions": [],
        "updated_at": "2026-06-15T16:00:00+00:00",
    }
    session_file.write_text(json.dumps(session_data), encoding="utf-8")
    return session_file


def test_archive_creates_manifest(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    sessions_dir = tmp_path / "runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    artifacts_dir = tmp_path / "runtime" / "inputs"
    artifacts_dir.mkdir(parents=True)
    report_path = artifacts_dir / "report.json"
    report_path.write_text('{"key": "value"}', encoding="utf-8")

    session_file = _make_session_file(
        sessions_dir, "trading-2026-06-15",
        artifacts=[{"logical_name": "report", "path": str(report_path)}],
    )

    archive_root = tmp_path / "archive"
    manifest, manifest_path = archive_session(
        session_id="trading-2026-06-15",
        trading_date="2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "report", "path": str(report_path)}],
        archive_root=str(archive_root),
    )
    assert Path(manifest_path).exists()
    assert manifest["session_id"] == "trading-2026-06-15"
    assert manifest["trading_date"] == "2026-06-15"
    assert manifest["status"] == "complete"


def test_archive_manifest_contains_required_fields(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    sessions_dir = tmp_path / "runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    artifacts_dir = tmp_path / "runtime" / "inputs"
    artifacts_dir.mkdir(parents=True)
    report_path = artifacts_dir / "report.json"
    report_path.write_text('{"key": "value"}', encoding="utf-8")

    session_file = _make_session_file(
        sessions_dir, "trading-2026-06-15",
        artifacts=[{"logical_name": "report", "path": str(report_path)}],
    )

    archive_root = tmp_path / "archive"
    manifest, _ = archive_session(
        session_id="trading-2026-06-15",
        trading_date="2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "report", "path": str(report_path)}],
        archive_root=str(archive_root),
    )

    for field in ("session_id", "trading_date", "archived_at", "source_session_path", "files", "missing_files", "rejected_files", "status"):
        assert field in manifest, f"manifest missing {field}"
    assert isinstance(manifest["files"], list)
    assert manifest["files"][0]["logical_name"] == "report"
    assert manifest["files"][0]["status"] == "archived"
    assert "sha256" in manifest["files"][0]
    assert "size_bytes" in manifest["files"][0]


def test_archive_copies_files_to_archive_dir(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    sessions_dir = tmp_path / "runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    artifacts_dir = tmp_path / "runtime" / "inputs"
    artifacts_dir.mkdir(parents=True)
    report_path = artifacts_dir / "report.json"
    report_content = '{"key": "value"}'
    report_path.write_text(report_content, encoding="utf-8")

    session_file = _make_session_file(
        sessions_dir, "trading-2026-06-15",
        artifacts=[{"logical_name": "report", "path": str(report_path)}],
    )

    archive_root = tmp_path / "archive"
    archive_session(
        session_id="trading-2026-06-15",
        trading_date="2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "report", "path": str(report_path)}],
        archive_root=str(archive_root),
    )

    assert report_path.exists()
    copied = archive_root / "2026-06-15" / "trading-2026-06-15" / "inputs" / "report.json"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == report_content


def test_archive_preserves_relative_directory_structure(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    sessions_dir = tmp_path / "runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    sub = tmp_path / "runtime" / "packets"
    sub.mkdir(parents=True)
    file_path = sub / "data.json"
    file_path.write_text("data", encoding="utf-8")

    session_file = _make_session_file(
        sessions_dir, "trading-2026-06-16",
        artifacts=[{"logical_name": "input_data", "path": str(file_path)}],
    )

    archive_root = tmp_path / "archive"
    archive_session(
        session_id="trading-2026-06-16",
        trading_date="2026-06-16",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "input_data", "path": str(file_path)}],
        archive_root=str(archive_root),
    )

    copied = archive_root / "2026-06-16" / "trading-2026-06-16" / "packets" / "data.json"
    assert copied.exists()


def test_archive_fails_on_missing_file(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    sessions_dir = tmp_path / "runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    missing_path = tmp_path / "runtime" / "inputs" / "nonexistent.json"

    session_file = _make_session_file(
        sessions_dir, "trading-2026-06-15",
        artifacts=[{"logical_name": "missing_report", "path": str(missing_path)}],
    )

    archive_root = tmp_path / "archive"
    with pytest.raises(RuntimeError, match="archive incomplete"):
        archive_session(
            session_id="trading-2026-06-15",
            trading_date="2026-06-15",
            session_file=str(session_file),
            artifact_ledger=[{"logical_name": "missing_report", "path": str(missing_path)}],
            archive_root=str(archive_root),
        )


def test_archive_rejects_path_outside_runtime_scope(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    sessions_dir = tmp_path / "runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("secret", encoding="utf-8")

    session_file = _make_session_file(
        sessions_dir, "trading-2026-06-15",
        artifacts=[{"logical_name": "outside", "path": str(outside)}],
    )

    archive_root = tmp_path / "archive"
    with pytest.raises(RuntimeError, match="archive incomplete"):
        archive_session(
            session_id="trading-2026-06-15",
            trading_date="2026-06-15",
            session_file=str(session_file),
            artifact_ledger=[{"logical_name": "outside", "path": str(outside)}],
            archive_root=str(archive_root),
        )


def test_archive_only_copies_ledger_listed_files(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    sessions_dir = tmp_path / "runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    artifacts_dir = tmp_path / "runtime" / "inputs"
    artifacts_dir.mkdir(parents=True)
    listed = artifacts_dir / "listed.json"
    unlisted = artifacts_dir / "unlisted.json"
    listed.write_text("listed", encoding="utf-8")
    unlisted.write_text("unlisted", encoding="utf-8")

    session_file = _make_session_file(
        sessions_dir, "trading-2026-06-15",
        artifacts=[{"logical_name": "listed", "path": str(listed)}],
    )

    archive_root = tmp_path / "archive"
    archive_session(
        session_id="trading-2026-06-15",
        trading_date="2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "listed", "path": str(listed)}],
        archive_root=str(archive_root),
    )

    session_archive = archive_root / "2026-06-15" / "trading-2026-06-15"
    copied_files = list(session_archive.rglob("*"))
    assert any("listed.json" in str(f) for f in copied_files)
    assert not any("unlisted.json" in str(f) for f in copied_files)


def test_archive_accepts_sibling_runtime_dirs(tmp_path):
    """Canonical artifacts in runtime/inputs/ and runtime/packets/ are accepted."""
    from stock_team.orchestration.archiver import archive_session

    sessions_dir = tmp_path / "runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    inputs_dir = tmp_path / "runtime" / "inputs"
    inputs_dir.mkdir(parents=True)
    packets_dir = tmp_path / "runtime" / "packets"
    packets_dir.mkdir(parents=True)

    input_file = inputs_dir / "snapshot.json"
    input_file.write_text('{"data": "input"}', encoding="utf-8")
    packet_file = packets_dir / "plan.json"
    packet_file.write_text('{"data": "packet"}', encoding="utf-8")

    session_file = _make_session_file(
        sessions_dir, "trading-2026-06-15",
        artifacts=[
            {"logical_name": "snapshot", "path": str(input_file)},
            {"logical_name": "plan", "path": str(packet_file)},
        ],
    )

    archive_root = tmp_path / "archive"
    manifest, _ = archive_session(
        session_id="trading-2026-06-15",
        trading_date="2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[
            {"logical_name": "snapshot", "path": str(input_file)},
            {"logical_name": "plan", "path": str(packet_file)},
        ],
        archive_root=str(archive_root),
    )
    assert manifest["status"] == "complete"
    assert len(manifest["files"]) == 2
    assert all(f["status"] == "archived" for f in manifest["files"])
