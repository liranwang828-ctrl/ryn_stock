from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from .adapters import AdapterError, ExistingCliAdapter
from .models import (
    ValidationError,
    new_trading_session,
    validate_action,
    validate_session,
)
from .store import SessionStore
from .transitions import allowed_actions, begin_transition, complete_transition, requires_confirmation


class WorkflowCoordinator:
    def __init__(
        self,
        store: SessionStore,
        adapter: ExistingCliAdapter,
        now_fn: Callable[[], str] | None = None,
    ):
        self.store = store
        self.adapter = adapter
        self.now_fn = now_fn or (lambda: "1970-01-01T00:00:00+00:00")

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        action = validate_action(action)
        intent = action["intent"]
        session_id = action["session_id"]

        if intent == "initialize_day":
            state = new_trading_session(
                session_id=session_id,
                market_date=action["parameters"]["market_date"],
                now=self.now_fn(),
            )
            state["processed_actions"].append(
                {
                    "idempotency_key": action["idempotency_key"],
                    "intent": intent,
                    "result_state": state["state"],
                    "processed_at": self.now_fn(),
                }
            )
            state["state_version"] = 1
            self.store.create(validate_session(state))
            return state

        state = self.store.load(session_id)
        starting_version = state["state_version"]

        for processed in state["processed_actions"]:
            if processed["idempotency_key"] == action["idempotency_key"]:
                return state

        if action["expected_state"] != state["state"]:
            raise ValidationError(
                f"expected_state: expected {action['expected_state']!r}, found {state['state']!r}"
            )

        if requires_confirmation(intent) and not action["user_confirmation"]:
            raise ValidationError(f"{intent}: user_confirmation is required")

        if intent == "retry_last_action":
            if state["state"] != "FAILED_TOOL" or not state.get("last_error"):
                raise ValidationError("retry_last_action: no retryable failure is recorded")
            original_intent = state["last_error"]["intent"]
            try:
                result = self._run_tool(state, original_intent, action)
            except AdapterError as exc:
                state["state"] = "FAILED_TOOL"
                state["state_version"] = starting_version + 1
                state["last_error"] = {
                    "error_class": exc.__class__.__name__,
                    "message": str(exc),
                    "retryable": exc.retryable,
                    "intent": original_intent,
                    "occurred_at": self.now_fn(),
                }
            else:
                state["processed_actions"].append(
                    {
                        "idempotency_key": action["idempotency_key"],
                        "intent": intent,
                        "result_state": result["state"],
                        "processed_at": self.now_fn(),
                    }
                )
                state["state"] = result["state"]
                state["state_version"] = starting_version + 1
                state["allowed_actions"] = allowed_actions(state["state"])
                state["last_error"] = None
            self.store.save(validate_session(state), expected_version=starting_version)
            return state

        if intent not in {"record_focus_confirmation", "record_plan_approval"}:
            state["state"] = begin_transition(state["state"], intent)

        if intent in {"start_stage0", "start_stage1", "start_intraday"}:
            try:
                result = self._run_tool(state, intent, action)
            except AdapterError as exc:
                state["state"] = "FAILED_TOOL"
                state["state_version"] = starting_version + 1
                state["last_error"] = {
                    "error_class": exc.__class__.__name__,
                    "message": str(exc),
                    "retryable": exc.retryable,
                    "intent": intent,
                    "occurred_at": self.now_fn(),
                }
            else:
                state["artifacts"].extend(result["artifacts"])
                state["state"] = result["state"]
                state["state_version"] = starting_version + 1
                state["last_error"] = None
        elif intent == "record_focus_confirmation":
            state["state"] = "FOCUS_CONFIRMED"
            state["state_version"] = starting_version + 1
        elif intent == "record_plan_approval":
            state["state"] = "PLAN_APPROVED"
            state["state_version"] = starting_version + 1
        elif intent == "close_market":
            state["state"] = "MARKET_CLOSED"
            state["state_version"] = starting_version + 1
        elif intent == "archive_day":
            state["state"] = "DAY_ARCHIVED"
            state["state_version"] = starting_version + 1

        state["processed_actions"].append(
            {
                "idempotency_key": action["idempotency_key"],
                "intent": intent,
                "result_state": state["state"],
                "processed_at": self.now_fn(),
            }
        )
        state["allowed_actions"] = allowed_actions(state["state"])
        self.store.save(validate_session(state), expected_version=starting_version)
        return state

    def _run_tool(self, state: dict[str, Any], intent: str, action: dict[str, Any]) -> dict[str, Any]:
        result = self.adapter.run(intent, action["parameters"])
        artifacts = []
        for artifact_path in result.artifact_paths:
            path = Path(self.store.root) / artifact_path
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            artifacts.append(
                {
                    "role": intent,
                    "path": str(Path(artifact_path)),
                    "sha256": digest,
                    "created_at": self.now_fn(),
                }
            )
        if intent == "start_stage0":
            return {"state": "STAGE0_READY", "artifacts": artifacts}
        if intent == "start_stage1":
            return {"state": "STAGE1_READY", "artifacts": artifacts}
        if intent == "start_intraday":
            return {"state": "INTRADAY_ACTIVE", "artifacts": artifacts}
        raise ValidationError(f"{intent}: unsupported tool transition")
