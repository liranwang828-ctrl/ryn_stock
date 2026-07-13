from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .protocol import INPUTS_DIR, PACKETS_DIR, RUNTIME_ROOT


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
        if intent == "start_stage0_from_snapshot":
            out = str(parameters["out"])
            snapshot_path = str(parameters["pre_market_snapshot"])
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
            return [(market_context_command, 90)], [out]
        if intent == "start_stage0_observation":
            snapshot_path = str(parameters["snapshot_out"])
            out = str(parameters["out"])
            command = [
                self.python_executable,
                "-m",
                "stock_team.data_ingest.observation_market_context",
                "--date",
                str(parameters["date"]),
                "--as-of",
                str(parameters["as_of"]),
                "--snapshot-out",
                snapshot_path,
                "--out",
                out,
            ]
            commands = [(command, 120)]
            artifacts = [snapshot_path, out]
            tape_out = parameters.get("tape_out")
            if tape_out:
                tape_command = [
                    self.python_executable,
                    "-m",
                    "stock_team.data_ingest.premarket_tape",
                    "--date",
                    str(parameters["date"]),
                    "--session-id",
                    str(parameters.get("session_id") or f"observation-{parameters['date']}"),
                    "--as-of",
                    str(parameters["as_of"]),
                    "--out",
                    str(tape_out),
                ]
                if parameters.get("universe"):
                    tape_command.extend(["--universe", str(parameters["universe"])])
                commands.append((tape_command, 180))
                artifacts.append(str(tape_out))
            return commands, artifacts
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
            decision_sheet_path = Path(str(parameters["decision_sheet"]))
            if not decision_sheet_path.exists():
                raise AdapterError(
                    f"decision sheet not found: {decision_sheet_path}",
                    retryable=False,
                )
            try:
                content = json.loads(decision_sheet_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise AdapterError(
                    f"decision sheet is not valid JSON: {exc}",
                    retryable=False,
                )
            if "focus_symbols" not in content:
                raise AdapterError(
                    "decision sheet missing required field 'focus_symbols'",
                    retryable=False,
                )
            if content.get("user_confirmed") is not True:
                raise AdapterError(
                    "decision sheet must have user_confirmed set to true",
                    retryable=False,
                )
            return [], [
                str(parameters["discussion_notes"]),
                str(parameters["decision_sheet"]),
            ]
        if intent == "record_plan_approval":
            trading_plan_path = Path(str(parameters["trading_plan"]))
            intraday_guidance_path = Path(str(parameters["intraday_guidance"]))

            errors = []
            for label, path in [
                ("trading plan", trading_plan_path),
                ("intraday guidance", intraday_guidance_path),
            ]:
                if not path.exists():
                    errors.append(f"{label} not found: {path}")
                    continue
                try:
                    content = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise AdapterError(
                        f"{label} is not valid JSON: {exc}",
                        retryable=False,
                    )
                for field in ("risk_mode", "allowed_actions", "forbidden_actions"):
                    if field not in content:
                        errors.append(
                            f"{label} missing required field '{field}'"
                        )

            if errors:
                raise AdapterError(
                    "plan approval validation failed: " + "; ".join(errors),
                    retryable=False,
                )

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
        if intent == "refresh_market_observation":
            out = str(parameters["out"])
            command = [
                self.python_executable,
                "-m",
                "stock_team.cli",
                "intraday-snapshot",
                "--symbols",
                str(parameters["symbols"]),
                "--out",
                out,
            ]
            if parameters.get("refresh"):
                command.append("--refresh")
            return [(command, 60)], [out]
        raise AdapterError(f"unsupported intent: {intent}", retryable=False)

    def _is_retryable(self, returncode: int, stderr: str) -> bool:
        text = stderr.lower()
        if returncode >= 2:
            return any(term in text for term in RETRYABLE_TERMS)
        if returncode == 1:
            return False
        return False
