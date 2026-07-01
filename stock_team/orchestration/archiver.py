from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def archive_session(*, session_id: str, session_file: str, artifact_ledger: list[dict], archive_root: str) -> dict:
    archive_base = Path(archive_root) / session_id
    archive_base.mkdir(parents=True, exist_ok=True)

    session_path = Path(session_file)
    files = []
    missing_files = []
    rejected_files = []

    for entry in artifact_ledger:
        logical_name = entry.get("logical_name", "")
        source = Path(entry["path"])

        if not source.exists():
            missing_files.append(str(source))
            files.append({
                "logical_name": logical_name,
                "source_path": str(source),
                "archive_path": "",
                "sha256": "",
                "size_bytes": 0,
                "status": "missing",
            })
            continue

        try:
            source.resolve().relative_to(session_path.parent.resolve())
        except ValueError:
            rejected_files.append(str(source))
            files.append({
                "logical_name": logical_name,
                "source_path": str(source),
                "archive_path": "",
                "sha256": "",
                "size_bytes": 0,
                "status": "rejected",
            })
            continue

        content = source.read_bytes()
        sha256 = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)

        rel = source.resolve().relative_to(session_path.parent.resolve())
        dest = archive_base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            existing_hash = hashlib.sha256(dest.read_bytes()).hexdigest()
            if existing_hash != sha256:
                raise FileExistsError(f"archive conflict: {dest} (different content)")
        else:
            shutil.copy2(source, dest)

        files.append({
            "logical_name": logical_name,
            "source_path": str(source),
            "archive_path": str(dest),
            "sha256": sha256,
            "size_bytes": size_bytes,
            "status": "archived",
        })

    manifest = {
        "session_id": session_id,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "source_session_path": str(session_path),
        "files": files,
        "missing_files": missing_files,
        "rejected_files": rejected_files,
    }

    manifest_path = archive_base / "archive_manifest.json"
    if missing_files or rejected_files:
        manifest["status"] = "partial"
    else:
        manifest["status"] = "complete"

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if missing_files or rejected_files:
        raise RuntimeError(
            f"archive incomplete: {len(missing_files)} missing, {len(rejected_files)} rejected"
        )

    return manifest, str(manifest_path)
