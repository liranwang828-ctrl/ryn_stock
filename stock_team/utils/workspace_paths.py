"""Resolve paths shared by stock_team and the sibling investing-os repository."""

import os
from pathlib import Path


def workspace_home(stock_team_home=None):
    """Return the unified workspace root containing both repositories."""
    package_home = Path(stock_team_home or Path(__file__).resolve().parents[1])
    return str(package_home.resolve().parent)


def investing_os_home(stock_team_home=None):
    """Return the configured brain repository, defaulting to a workspace sibling."""
    configured = os.environ.get("INVESTING_OS_HOME")
    if configured:
        return str(Path(configured).expanduser().resolve())
    return str((Path(workspace_home(stock_team_home)) / "investing-os").resolve())
