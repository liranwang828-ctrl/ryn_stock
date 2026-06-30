from __future__ import annotations

from pathlib import Path

from stock_team.utils.workspace_paths import workspace_home

RUNTIME_ROOT = Path(workspace_home()) / "investing-os" / "system" / "runtime"
SESSIONS_DIR = RUNTIME_ROOT / "sessions"
INPUTS_DIR = RUNTIME_ROOT / "inputs"
PACKETS_DIR = RUNTIME_ROOT / "packets"
