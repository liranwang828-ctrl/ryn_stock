from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from stock_team.orchestration.adapters import ExistingCliAdapter
from stock_team.orchestration.coordinator import WorkflowCoordinator
from stock_team.orchestration.models import IBKR_FACT_STATUSES, SESSION_TYPES
from stock_team.orchestration.stage0_universe import build_stage0_universe_document
from stock_team.orchestration.store import SessionConflictError, SessionStore
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

    confirm_daily0 = sub.add_parser("confirm-daily0")
    confirm_daily0.add_argument("--session-id", required=True)
    confirm_daily0.add_argument("--activity-mode", choices=sorted(SESSION_TYPES), required=True)
    confirm_daily0.add_argument("--account-fact-status", choices=sorted(IBKR_FACT_STATUSES), required=True)
    confirm_daily0.add_argument("--account-snapshot-ref", default="")
    confirm_daily0.add_argument("--analysis-scope-ref", default="")
    confirm_daily0.add_argument("--runtime-dir", default=str(default_runtime_dir()))

    invalidate_daily0 = sub.add_parser("invalidate-daily0")
    invalidate_daily0.add_argument("--session-id", required=True)
    invalidate_daily0.add_argument("--reason", required=True)
    invalidate_daily0.add_argument("--runtime-dir", default=str(default_runtime_dir()))

    prepare_universe = sub.add_parser("prepare-stage0-universe")
    prepare_universe.add_argument("--session-id", required=True)
    prepare_universe.add_argument("--runtime-dir", default=str(default_runtime_dir()))

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

            # H1 §3.2: check for damaged sessions first
            try:
                open_sessions = store.list_sessions(only_open=True, raise_on_damaged=True)
            except SessionConflictError as exc:
                print(str(exc), file=sys.stderr)
                return 1

            previous_open = [
                s for s in open_sessions
                if s["market_date"] < args.date
            ]

            # H1 §3.3: block on multiple old sessions
            if len(previous_open) > 1:
                ids = ", ".join(s["session_id"] for s in previous_open)
                print(
                    f"存在多个未关闭旧会话: {ids}。请先手动处理多余旧会话后再重试。",
                    file=sys.stderr,
                )
                return 1

            prev = previous_open[0] if previous_open else None

            # H1 §3.3: FAILED_TOOL requires investigation
            if prev and prev["state"] == "FAILED_TOOL":
                print(
                    f"旧会话 {prev['session_id']} 处于 FAILED_TOOL 状态，"
                    "需要手动判断是否为损坏会话后再重试。",
                    file=sys.stderr,
                )
                return 1

            # H1 §3.3: REVIEW_REQUIRED only allows full_review
            if prev and prev["state"] == "REVIEW_REQUIRED":
                if args.recovery != "full_review":
                    print(
                        f"旧会话 {prev['session_id']} 处于 REVIEW_REQUIRED 状态，"
                        "只能使用 --recovery full_review 继续完整复盘。",
                        file=sys.stderr,
                    )
                    return 1

            if prev and not args.recovery:
                print(
                    f"发现未关闭会话: {prev['session_id']} (状态: {prev['state']}, "
                    f"日期: {prev['market_date']})",
                    file=sys.stderr,
                )
                if prev["state"] == "REVIEW_REQUIRED":
                    print(
                        "请使用 --recovery full_review 继续完整复盘。",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "请使用 --recovery {freeze|quick_review|full_review} 选择恢复路径后重试。",
                        file=sys.stderr,
                    )
                return 1

            coordinator = _coordinator(args.runtime_dir)

            if prev and args.recovery:
                # H1 §3.5: close market for active states first
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

                if args.recovery == "freeze":
                    freeze_action = {
                        "intent": "freeze",
                        "session_id": prev["session_id"],
                        "expected_state": prev["state"],
                        "user_confirmation": False,
                        "parameters": {},
                        "idempotency_key": str(uuid.uuid4()),
                    }
                    coordinator.execute(freeze_action)

                    archive_action = {
                        "intent": "archive_day",
                        "session_id": prev["session_id"],
                        "expected_state": "CLOSED_UNREVIEWED",
                        "user_confirmation": False,
                        "parameters": {},
                        "idempotency_key": str(uuid.uuid4()),
                    }
                    coordinator.execute(archive_action)
                    print(
                        f"已冻结并归档: {prev['session_id']} (欠账记录已保留)",
                        file=sys.stderr,
                    )

                elif args.recovery == "quick_review":
                    qr_action = {
                        "intent": "quick_review",
                        "session_id": prev["session_id"],
                        "expected_state": prev["state"],
                        "user_confirmation": False,
                        "parameters": {},
                        "idempotency_key": str(uuid.uuid4()),
                    }
                    coordinator.execute(qr_action)

                    archive_action = {
                        "intent": "archive_day",
                        "session_id": prev["session_id"],
                        "expected_state": "QUICK_REVIEWED",
                        "user_confirmation": False,
                        "parameters": {},
                        "idempotency_key": str(uuid.uuid4()),
                    }
                    coordinator.execute(archive_action)
                    print(
                        f"已快速复盘并归档: {prev['session_id']}",
                        file=sys.stderr,
                    )

                elif args.recovery == "full_review":
                    if prev["state"] != "REVIEW_REQUIRED":
                        review_action = {
                            "intent": "review_day",
                            "session_id": prev["session_id"],
                            "expected_state": prev["state"],
                            "user_confirmation": False,
                            "parameters": {},
                            "idempotency_key": str(uuid.uuid4()),
                        }
                        coordinator.execute(review_action)
                    print(
                        f"已进入完整复盘: {prev['session_id']}。"
                        "请在完成 DAILY-4 归档后重新 init-day。",
                        file=sys.stderr,
                    )
                    # H1 §3.4: full_review does NOT create today's session
                    return 0

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
        if args.command == "confirm-daily0":
            store = SessionStore(args.runtime_dir)
            state = store.load(args.session_id)
            if args.activity_mode != state["session_type"]:
                raise ValueError("activity_mode must match session_type")
            previous_version = state["state_version"]
            now = datetime.now().astimezone().isoformat()
            state["daily0_confirmation"] = {
                "confirmed_at": now,
                "activity_mode": args.activity_mode,
                "account_fact_status": args.account_fact_status,
                "account_snapshot_ref": args.account_snapshot_ref,
                "analysis_scope_ref": args.analysis_scope_ref,
                "user_confirmed": True,
            }
            state["state_version"] = previous_version + 1
            state["updated_at"] = now
            store.save(state, expected_version=previous_version)
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0
        if args.command == "invalidate-daily0":
            store = SessionStore(args.runtime_dir)
            state = store.load(args.session_id)
            reason = args.reason.strip()
            if not reason:
                raise ValueError("reason must not be empty")
            previous_confirmation = state.get("daily0_confirmation")
            if not isinstance(previous_confirmation, dict):
                raise ValueError("daily0_confirmation is not present")
            previous_version = state["state_version"]
            now = datetime.now().astimezone().isoformat()
            state.setdefault("daily0_confirmation_history", []).append({
                "invalidated_at": now,
                "invalidated_reason": reason,
                "previous_confirmation": previous_confirmation,
            })
            state.pop("daily0_confirmation", None)
            state["state_version"] = previous_version + 1
            state["updated_at"] = now
            store.save(state, expected_version=previous_version)
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0
        if args.command == "prepare-stage0-universe":
            store = SessionStore(args.runtime_dir)
            state = store.load(args.session_id)
            runtime_root = Path(args.runtime_dir).resolve().parent
            universe_path, journal_path = build_stage0_universe_document(
                base_dir=Path(__file__).resolve().parent,
                runtime_root=runtime_root,
                market_date=state["market_date"],
                session_id=state["session_id"],
            )
            print(json.dumps({
                "session_id": state["session_id"],
                "market_date": state["market_date"],
                "universe_path": str(universe_path.resolve()),
                "journal_path": journal_path,
            }, ensure_ascii=False, indent=2))
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
