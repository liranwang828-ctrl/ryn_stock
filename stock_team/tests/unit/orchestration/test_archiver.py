import json
from pathlib import Path


def test_archive_creates_manifest(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    session_state = {
        "session_id": "trading-2026-06-15",
        "market_date": "2026-06-15",
        "state": "REVIEW_REQUIRED",
    }
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "report.json").write_text('{"key": "value"}', encoding="utf-8")

    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()

    manifest_path = archive_session(session_state, str(artifacts_dir), archive_dir=str(archive_dir))
    assert Path(manifest_path).exists()
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    assert manifest["session_id"] == "trading-2026-06-15"


def test_archive_manifest_contains_required_fields(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    session_state = {
        "session_id": "trading-2026-06-15",
        "market_date": "2026-06-15",
        "state": "REVIEW_REQUIRED",
    }
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "report.json").write_text('{"key": "value"}', encoding="utf-8")

    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()

    manifest_path = archive_session(session_state, str(artifacts_dir), archive_dir=str(archive_dir))
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    assert "date" in manifest
    assert "session_id" in manifest
    assert "artifacts" in manifest
    assert "archived_at" in manifest
    assert isinstance(manifest["artifacts"], list)


def test_archive_copies_files_to_archive_dir(tmp_path):
    from stock_team.orchestration.archiver import archive_session

    session_state = {
        "session_id": "trading-2026-06-15",
        "market_date": "2026-06-15",
        "state": "REVIEW_REQUIRED",
    }
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report_content = '{"key": "value"}'
    (artifacts_dir / "report.json").write_text(report_content, encoding="utf-8")

    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()

    archive_session(session_state, str(artifacts_dir), archive_dir=str(archive_dir))

    # Original files still exist (not moved)
    assert (artifacts_dir / "report.json").exists()
    assert (artifacts_dir / "report.json").read_text(encoding="utf-8") == report_content
    # File was copied to archive
    copied = archive_dir / "trading-2026-06-15" / "report.json"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == report_content
