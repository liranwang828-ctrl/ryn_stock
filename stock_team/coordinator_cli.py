from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from stock_team.orchestration.adapters import ExistingCliAdapter
from stock_team.orchestration.coordinator import WorkflowCoordinator
from stock_team.orchestration.store import SessionStore
from stock_team.utils.workspace_paths import investing_os_home


def default_runtime_dir() -> Path:
    return Path(investing_os_home()) / "system" / "runtime" / "sessions"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m stock_team.coordinator_cli")
    sub = parser.add_subparsers(dest="command", required=True)

    init_day = sub.add_parser("init-day")
    init_day.add_argument("--date", required=True)
    init_day.add_argument("--runtime-dir", default=str(default_runtime_dir()))

    show = sub.add_parser("show")
    show.add_argument("--session-id", required=True)
    show.add_argument("--runtime-dir", default=str(default_runtime_dir()))

    run = sub.add_parser("run")
    run.add_argument("--action", required=True)
    run.add_argument("--runtime-dir", default=str(default_runtime_dir()))

    return parser


def _coordinator(runtime_dir: str) -> WorkflowCoordinator:
    root = Path(__file__).resolve().parents[1]
    return WorkflowCoordinator(
        SessionStore(runtime_dir),
        ExistingCliAdapter(workspace_root=root, python_executable=sys.executable),
        now_fn=lambda: datetime.now().astimezone().isoformat(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init-day":
            coordinator = _coordinator(args.runtime_dir)
            state = coordinator.execute(
                {
                    "intent": "initialize_day",
                    "session_id": f"trading-{args.date}",
                    "expected_state": "IDLE",
                    "user_confirmation": False,
                    "parameters": {"market_date": args.date},
                    "idempotency_key": str(uuid.uuid4()),
                }
            )
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0
        if args.command == "show":
            state = SessionStore(args.runtime_dir).load(args.session_id)
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0
        if args.command == "run":
            payload = json.loads(Path(args.action).read_text(encoding="utf-8-sig"))
            state = _coordinator(args.runtime_dir).execute(payload)
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0
    except Exception as err:
        print(str(err), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
