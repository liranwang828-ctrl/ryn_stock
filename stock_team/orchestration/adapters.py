from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


RETRYABLE_TERMS = ("timeout", "timed out", "network", "provider", "temporar", "connection")


@dataclass(frozen=True)
class AdapterResult:
    command: list[str]
    stdout: str
    stderr: str
    artifact_paths: list[str]


class AdapterError(RuntimeError):
    def __init__(self, message, *, retryable, command=None, stderr=""):
        super().__init__(message)
        self.retryable = retryable
        self.command = command or []
        self.stderr = stderr


class ExistingCliAdapter:
    def __init__(self, workspace_root, python_executable="python"):
        self.workspace_root = Path(workspace_root)
        self.python_executable = python_executable

    def run(self, intent: str, parameters: dict) -> AdapterResult:
        commands, artifact_paths = self._build(intent, parameters)
        last_completed = None
        last_command = None
        for command, timeout in commands:
            last_command = command
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(self.workspace_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise AdapterError(
                    f"{intent} timed out",
                    retryable=True,
                    command=command,
                    stderr=str(exc),
                ) from exc
            stderr = completed.stderr or ""
            if completed.returncode != 0:
                raise AdapterError(
                    f"{intent} failed with return code {completed.returncode}",
                    retryable=self._is_retryable(completed.returncode, stderr),
                    command=command,
                    stderr=stderr,
                )
            last_completed = completed

        stderr = (last_completed.stderr or "") if last_completed else ""
        for path in artifact_paths:
            if not Path(path).exists():
                raise AdapterError(
                    f"expected artifact missing: {path}",
                    retryable=False,
                    command=last_command or [],
                    stderr=stderr,
                )
        return AdapterResult(
            command=last_command or [],
            stdout=(last_completed.stdout or "") if last_completed else "",
            stderr=stderr,
            artifact_paths=artifact_paths,
        )

    def _build(self, intent: str, parameters: dict) -> tuple[list[tuple[list[str], int]], list[str]]:
        if intent == "start_stage0":
            out = str(parameters["out"])
            snapshot_path = str(
                parameters.get("pre_market_snapshot")
                or (Path(out).with_name("pre_market_snapshot.json"))
            )
            snapshot_command = [
                self.python_executable,
                "-m",
                "stock_team.cli",
                "premarket-snapshot",
                "--date",
                str(parameters["date"]),
                "--as-of",
                str(parameters["as_of"]),
                "--focus-symbols",
                str(parameters.get("focus_symbols", "")),
                "--themes",
                str(parameters.get("themes", "")),
                "--catalysts",
                str(parameters.get("catalysts", "")),
                "--notes",
                str(parameters.get("notes", "")),
                "--out",
                snapshot_path,
            ]
            market_context_command = [
                self.python_executable,
                "-m",
                "stock_team.cli",
                "market-context",
                "--date",
                str(parameters["date"]),
                "--as-of",
                str(parameters["as_of"]),
                "--universe",
                str(parameters["universe"]),
                "--pre-market-snapshot",
                snapshot_path,
                "--out",
                out,
            ]
            return [(snapshot_command, 120), (market_context_command, 90)], [snapshot_path, out]
        if intent == "start_stage1":
            out = str(parameters["out"])
            command = [
                self.python_executable,
                "-m",
                "stock_team.cli",
                "premarket",
                "--context-packet",
                str(parameters["context_packet"]),
                "--decision-sheet",
                str(parameters["decision_sheet"]),
                "--out",
                out,
            ]
            return [(command, 60)], [out]
        if intent == "record_focus_confirmation":
            return [], [
                str(parameters["discussion_notes"]),
                str(parameters["decision_sheet"]),
            ]
        if intent == "record_plan_approval":
            return [], [
                str(parameters["trading_plan"]),
                str(parameters["intraday_guidance"]),
            ]
        if intent == "start_intraday":
            out = str(parameters["out"])
            command = [
                self.python_executable,
                "-m",
                "stock_team.cli",
                "intraday-dashboard",
                "--snapshot",
                str(parameters["snapshot"]),
                "--out",
                out,
            ]
            return [(command, 30)], [out]
        raise AdapterError(f"unsupported intent: {intent}", retryable=False)

    def _is_retryable(self, returncode: int, stderr: str) -> bool:
        text = stderr.lower()
        if returncode >= 2:
            return any(term in text for term in RETRYABLE_TERMS)
        if returncode == 1:
            return False
        return False
