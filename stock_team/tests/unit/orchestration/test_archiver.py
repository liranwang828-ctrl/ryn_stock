import json
from pathlib import Path

import pytest


def _make_session_file(tmp_path, session_id, artifacts=None):
    session_file = tmp_path / f"{session_id}.json"
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

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report_path = artifacts_dir / "report.json"
    report_path.write_text('{"key": "value"}', encoding="utf-8")

    session_file = _make_session_file(
        tmp_path, "trading-2026-06-15",
        artifacts=[{"logical_name": "report", "path": str(report_path)}],
    )

    archive_root = tmp_path / "archive"
    manifest, manifest_path = archive_session(
        session_id="trading-2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "report", "path": str(report_path)}],
        archive_root=str(archive_root),
    )
    assert Path(manifest_path).exists()
    assert manifest["session_id"] == "trading-2026-06-15"
    assert manifest["status"] == "complete"


def test_archive_manifest_contains_required_fields(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report_path = artifacts_dir / "report.json"
    report_path.write_text('{"key": "value"}', encoding="utf-8")

    session_file = _make_session_file(
        tmp_path, "trading-2026-06-15",
        artifacts=[{"logical_name": "report", "path": str(report_path)}],
    )

    archive_root = tmp_path / "archive"
    manifest, _ = archive_session(
        session_id="trading-2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "report", "path": str(report_path)}],
        archive_root=str(archive_root),
    )

    for field in ("session_id", "archived_at", "source_session_path", "files", "missing_files", "rejected_files", "status"):
        assert field in manifest, f"manifest missing {field}"
    assert isinstance(manifest["files"], list)
    assert manifest["files"][0]["logical_name"] == "report"
    assert manifest["files"][0]["status"] == "archived"
    assert "sha256" in manifest["files"][0]
    assert "size_bytes" in manifest["files"][0]


def test_archive_copies_files_to_archive_dir(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report_path = artifacts_dir / "report.json"
    report_content = '{"key": "value"}'
    report_path.write_text(report_content, encoding="utf-8")

    session_file = _make_session_file(
        tmp_path, "trading-2026-06-15",
        artifacts=[{"logical_name": "report", "path": str(report_path)}],
    )

    archive_root = tmp_path / "archive"
    archive_session(
        session_id="trading-2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "report", "path": str(report_path)}],
        archive_root=str(archive_root),
    )

    assert report_path.exists()
    copied = archive_root / "trading-2026-06-15" / "artifacts" / "report.json"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == report_content


def test_archive_preserves_relative_directory_structure(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    sub = tmp_path / "inputs"
    sub.mkdir(parents=True)
    file_path = sub / "data.json"
    file_path.write_text("data", encoding="utf-8")

    session_file = _make_session_file(
        tmp_path, "trading-2026-06-16",
        artifacts=[{"logical_name": "input_data", "path": str(file_path)}],
    )

    archive_root = tmp_path / "archive"
    archive_session(
        session_id="trading-2026-06-16",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "input_data", "path": str(file_path)}],
        archive_root=str(archive_root),
    )

    copied = archive_root / "trading-2026-06-16" / "inputs" / "data.json"
    assert copied.exists()


def test_archive_fails_on_missing_file(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    missing_path = tmp_path / "nonexistent.json"
    session_file = _make_session_file(
        tmp_path, "trading-2026-06-15",
        artifacts=[{"logical_name": "missing_report", "path": str(missing_path)}],
    )

    archive_root = tmp_path / "archive"
    with pytest.raises(RuntimeError, match="archive incomplete"):
        archive_session(
            session_id="trading-2026-06-15",
            session_file=str(session_file),
            artifact_ledger=[{"logical_name": "missing_report", "path": str(missing_path)}],
            archive_root=str(archive_root),
        )


def test_archive_rejects_path_outside_session_scope(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    outside = tmp_path.parent / "outside.json"
    outside.write_text("secret", encoding="utf-8")

    session_file = _make_session_file(
        tmp_path, "trading-2026-06-15",
        artifacts=[{"logical_name": "outside", "path": str(outside)}],
    )

    archive_root = tmp_path / "archive"
    with pytest.raises(RuntimeError, match="archive incomplete"):
        archive_session(
            session_id="trading-2026-06-15",
            session_file=str(session_file),
            artifact_ledger=[{"logical_name": "outside", "path": str(outside)}],
            archive_root=str(archive_root),
        )


def test_archive_only_copies_ledger_listed_files(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    listed = artifacts_dir / "listed.json"
    unlisted = artifacts_dir / "unlisted.json"
    listed.write_text("listed", encoding="utf-8")
    unlisted.write_text("unlisted", encoding="utf-8")

    session_file = _make_session_file(
        tmp_path, "trading-2026-06-15",
        artifacts=[{"logical_name": "listed", "path": str(listed)}],
    )

    archive_root = tmp_path / "archive"
    archive_session(
        session_id="trading-2026-06-15",
        session_file=str(session_file),
        artifact_ledger=[{"logical_name": "listed", "path": str(listed)}],
        archive_root=str(archive_root),
    )

    session_archive = archive_root / "trading-2026-06-15"
    copied_files = list(session_archive.rglob("*"))
    assert any("listed.json" in str(f) for f in copied_files)
    assert not any("unlisted.json" in str(f) for f in copied_files)
