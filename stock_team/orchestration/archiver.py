from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def archive_session(session_state: dict, artifacts_dir: str, *, archive_dir: str | None = None) -> str:
    if archive_dir is None:
        from stock_team.utils.workspace_paths import investing_os_home

        archive_dir = str(Path(investing_os_home()) / "system" / "runtime" / "sessions" / "archive")

    archive_path = Path(archive_dir)
    archive_path.mkdir(parents=True, exist_ok=True)

    session_id = session_state["session_id"]
    artifacts_base = Path(artifacts_dir)

    artifacts = []
    session_archive_dir = archive_path / session_id
    session_archive_dir.mkdir(parents=True, exist_ok=True)

    if artifacts_base.is_dir():
        for file_path in sorted(artifacts_base.rglob("*")):
            if file_path.is_file():
                content = file_path.read_bytes()
                sha256 = hashlib.sha256(content).hexdigest()
                dest = session_archive_dir / file_path.name
                shutil.copy2(file_path, dest)
                artifacts.append({
                    "name": file_path.name,
                    "path": str(dest),
                    "hash": sha256,
                })

    manifest = {
        "date": session_state.get("market_date", ""),
        "session_id": session_id,
        "artifacts": artifacts,
        "archived_at": datetime.now(timezone.utc).isoformat(),
    }

    manifest_path = archive_path / f"{session_id}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return str(manifest_path)
