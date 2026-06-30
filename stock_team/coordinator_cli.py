from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from stock_team.orchestration.adapters import ExistingCliAdapter
from stock_team.orchestration.coordinator import WorkflowCoordinator
from stock_team.orchestration.models import SESSION_TYPES
from stock_team.orchestration.store import SessionStore
from stock_team.utils.workspace_paths import investing_os_home


def default_runtime_dir() -> Path:
    return Path(investing_os_home()) / "system" / "runtime" / "sessions"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m stock_team.coordinator_cli")
    sub = parser.add_subparsers(dest="command", required=True)

    init_day = sub.add_parser("init-day")
    init_day.add_argument("--date", required=True)
    init_day.add_argument("--session-type", choices=sorted(SESSION_TYPES), default="trading")
    init_day.add_argument("--runtime-dir", default=str(default_runtime_dir()))
    init_day.add_argument("--recovery", choices=["freeze", "quick_review", "full_review"], default=None)

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
            store = SessionStore(args.runtime_dir)
            open_sessions = store.list_sessions(only_open=True)

            previous_open = [
                s for s in open_sessions
                if s["market_date"] < args.date
            ]

            if previous_open and not args.recovery:
                prev = previous_open[0]
                print(
                    f"发现未关闭会话: {prev['session_id']} (状态: {prev['state']}, "
                    f"日期: {prev['market_date']})",
                    file=sys.stderr,
                )
                print(
                    "请使用 --recovery {freeze|quick_review|full_review} 选择恢复路径后重试。",
                    file=sys.stderr,
                )
                return 1

            coordinator = _coordinator(args.runtime_dir)

            if previous_open and args.recovery:
                prev = previous_open[0]
                recovery_map = {
                    "freeze": "freeze",
                    "quick_review": "quick_review",
                    "full_review": "review_day",
                }
                recovery_intent = recovery_map[args.recovery]

                # If old session is in an active state, close market first
                if prev["state"] in ("INTRADAY_ACTIVE", "OBSERVATION_ACTIVE"):
                    close_action = {
                        "intent": "close_market",
                        "session_id": prev["session_id"],
                        "expected_state": prev["state"],
                        "user_confirmation": False,
                        "parameters": {},
                        "idempotency_key": str(uuid.uuid4()),
                    }
                    coordinator.execute(close_action)
                    prev = store.load(prev["session_id"])

                recovery_action = {
                    "intent": recovery_intent,
                    "session_id": prev["session_id"],
                    "expected_state": prev["state"],
                    "user_confirmation": False,
                    "parameters": {},
                    "idempotency_key": str(uuid.uuid4()),
                }
                recovered = coordinator.execute(recovery_action)
                print(
                    f"已恢复: {prev['session_id']} -> {recovered['state']}",
                    file=sys.stderr,
                )

                # If quick_review, also archive
                if args.recovery == "quick_review":
                    archive_action = {
                        "intent": "archive_day",
                        "session_id": prev["session_id"],
                        "expected_state": "QUICK_REVIEWED",
                        "user_confirmation": False,
                        "parameters": {},
                        "idempotency_key": str(uuid.uuid4()),
                    }
                    coordinator.execute(archive_action)

            state = coordinator.execute(
                {
                    "intent": "initialize_day",
                    "session_id": f"{args.session_type}-{args.date}",
                    "expected_state": "IDLE",
                    "user_confirmation": False,
                    "parameters": {"market_date": args.date, "session_type": args.session_type},
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
