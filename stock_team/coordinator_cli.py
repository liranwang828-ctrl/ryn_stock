from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stock_team.orchestration import ExistingCliAdapter, SessionStore, WorkflowCoordinator


def _runtime_dir(default_root: Path | None = None) -> Path:
    if default_root is not None:
        return default_root
    workspace = Path(__file__).resolve().parents[1]
    return workspace.parent / "investing-os" / "system" / "runtime" / "sessions"


def _coordinator(runtime_dir: Path) -> WorkflowCoordinator:
    return WorkflowCoordinator(
        SessionStore(runtime_dir),
        ExistingCliAdapter(workspace_root=Path(__file__).resolve().parents[1].parent),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workflow coordinator CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    init_day = sub.add_parser("init-day")
    init_day.add_argument("--date", required=True)
    init_day.add_argument("--runtime-dir")

    run = sub.add_parser("run")
    run.add_argument("--action", required=True)
    run.add_argument("--runtime-dir")

    show = sub.add_parser("show")
    show.add_argument("--session-id", required=True)
    show.add_argument("--runtime-dir")

    return parser


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir) if getattr(args, "runtime_dir", None) else _runtime_dir()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.command == "init-day":
            coordinator = _coordinator(runtime_dir)
            state = coordinator.execute(
                {
                    "intent": "initialize_day",
                    "session_id": f"trading-{args.date}",
                    "expected_state": "IDLE",
                    "user_confirmation": False,
                    "parameters": {"market_date": args.date},
                    "idempotency_key": f"init-{args.date}",
                }
            )
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0

        if args.command == "run":
            coordinator = _coordinator(runtime_dir)
            action = _load_json(Path(args.action))
            state = coordinator.execute(action)
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0

        if args.command == "show":
            state = SessionStore(runtime_dir).load(args.session_id)
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0

    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
