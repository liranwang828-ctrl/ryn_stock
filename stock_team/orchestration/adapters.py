from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AdapterResult:
    command: list[str]
    stdout: str
    stderr: str
    artifact_paths: list[str]


class AdapterError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool, command: list[str] | None = None, stderr: str = ""):
        super().__init__(message)
        self.retryable = retryable
        self.command = command or []
        self.stderr = stderr


class ExistingCliAdapter:
    def __init__(self, workspace_root: Path | str, python_executable: str = "python"):
        self.workspace_root = Path(workspace_root)
        self.python_executable = python_executable

    def run(self, intent: str, parameters: dict[str, Any]) -> AdapterResult:
        command, timeout, artifact_paths = self._build_command(intent, parameters)
        try:
            completed = subprocess.run(
                command,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AdapterError(
                f"{intent} timed out after {timeout}s",
                retryable=True,
                command=command,
            ) from exc

        if completed.returncode != 0:
            retryable = completed.returncode >= 2 or "timeout" in completed.stderr.lower()
            raise AdapterError(
                f"{intent} failed with return code {completed.returncode}",
                retryable=retryable,
                command=command,
                stderr=completed.stderr,
            )

        for artifact in artifact_paths:
            if not (self.workspace_root / artifact).exists():
                raise AdapterError(
                    f"{intent} succeeded but missing artifact {artifact}",
                    retryable=False,
                    command=command,
                    stderr=completed.stderr,
                )

        return AdapterResult(
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            artifact_paths=artifact_paths,
        )

    def _build_command(self, intent: str, parameters: dict[str, Any]) -> tuple[list[str], int, list[str]]:
        if intent == "start_stage0":
            command = [
                self.python_executable,
                "-m",
                "stock_team.cli",
                "market-context",
                "--date",
                parameters["date"],
                "--as-of",
                parameters["as_of"],
                "--themes",
                parameters.get("themes", "semiconductors,ai_infrastructure,memory,cloud"),
                "--universe",
                parameters["universe"],
                "--out",
                parameters["out"],
            ]
            if snapshot := parameters.get("pre_market_snapshot"):
                command.extend(["--pre-market-snapshot", snapshot])
            return command, 30, [parameters["out"]]

        if intent == "start_stage1":
            command = [
                self.python_executable,
                "-m",
                "stock_team.cli",
                "premarket",
                "--date",
                parameters["date"],
                "--decision-sheet",
                parameters["decision_sheet"],
                "--out",
                parameters["out"],
            ]
            if watchlist := parameters.get("watchlist"):
                command.extend(["--watchlist", watchlist])
            if parameters.get("refresh"):
                command.append("--refresh")
            return command, 60, [parameters["out"]]

        if intent == "start_intraday":
            command = [
                self.python_executable,
                "-m",
                "stock_team.cli",
                "intraday-dashboard",
                "--guidance",
                parameters["guidance"],
                "--out",
                parameters["out"],
            ]
            if html_out := parameters.get("html_out"):
                command.extend(["--html-out", html_out])
            if parameters.get("refresh"):
                command.append("--refresh")
            return command, 30, [p for p in [parameters["out"], parameters.get("html_out")] if p]

        raise AdapterError(f"unsupported intent {intent!r}", retryable=False)
