from __future__ import annotations

import hashlib
from pathlib import Path

from .adapters import AdapterError, AdapterResult
from .models import new_trading_session, validate_action
from .transitions import allowed_actions, begin_transition, complete_transition, requires_confirmation


class WorkflowCoordinator:
    def __init__(self, store, adapter, now_fn=None):
        self.store = store
        self.adapter = adapter
        self.now_fn = now_fn or (lambda: "")

    def execute(self, action: dict) -> dict:
        action = validate_action(action)
        now = self.now_fn()
        if action["intent"] == "initialize_day":
            state = new_trading_session(
                session_id=action["session_id"],
                market_date=action["parameters"]["market_date"],
                now=now,
                session_type=action["parameters"].get("session_type", "trading"),
            )
            processed = {
                "idempotency_key": action["idempotency_key"],
                "intent": action["intent"],
                "result_state": state["state"],
                "processed_at": now,
            }
            state["processed_actions"].append(processed)
            return self.store.create(state)

        state = self.store.load(action["session_id"])
        for processed in state["processed_actions"]:
            if processed["idempotency_key"] == action["idempotency_key"]:
                return state
        if action["expected_state"] != state["state"]:
            raise ValueError(f"expected_state mismatch: {action['expected_state']} != {state['state']}")
        original_action = action
        if action["intent"] == "retry_last_action":
            last_error = state.get("last_error") or {}
            retry_intent = last_error.get("intent")
            retry_parameters = last_error.get("parameters") or {}
            retry_state = last_error.get("resume_from_state")
            if not retry_intent:
                raise ValueError("retry_last_action requires last_error.intent")
            action = {
                **action,
                "intent": retry_intent,
                "parameters": retry_parameters,
            }
            state["state"] = retry_state or state["state"]
        if requires_confirmation(action["intent"]) and not action["user_confirmation"]:
            raise ValueError(f"{action['intent']} requires user_confirmation")

        previous_version = state["state_version"]
        source_state = state["state"]
        running_state = begin_transition(state["state"], action["intent"])
        state["state"] = running_state
        state["state_version"] = previous_version + 1
        state["updated_at"] = now
        self.store.save(state, expected_version=previous_version)

        try:
            if action["intent"] == "request_exception":
                result = AdapterResult(command=[], stdout="", stderr="", artifact_paths=[])
            else:
                result = self.adapter.run(action["intent"], action["parameters"])
        except AdapterError as err:
            failed = self.store.load(action["session_id"])
            prev = failed["state_version"]
            failed["state"] = "FAILED_TOOL"
            failed["state_version"] = prev + 1
            failed["last_error"] = {
                "error_class": err.__class__.__name__,
                "message": str(err),
                "retryable": err.retryable,
                "intent": action["intent"],
                "parameters": action["parameters"],
                "resume_from_state": source_state,
                "occurred_at": now,
            }
            failed["processed_actions"].append(
                {
                    "idempotency_key": original_action["idempotency_key"],
                    "intent": original_action["intent"],
                    "result_state": "FAILED_TOOL",
                    "processed_at": now,
                }
            )
            failed["allowed_actions"] = allowed_actions("FAILED_TOOL")
            failed["updated_at"] = now
            self.store.save(failed, expected_version=prev)
            return failed

        completed = self.store.load(action["session_id"])
        prev = completed["state_version"]
        completed["state"] = complete_transition(completed["state"], action["intent"], success=True)
        completed["state_version"] = prev + 1
        completed["last_error"] = None
        completed["allowed_actions"] = allowed_actions(completed["state"])
        completed["updated_at"] = now
        if action["intent"] == "request_exception":
            completed.setdefault("intraday_exceptions", []).append(
                {
                    "reason": action["parameters"].get("reason", ""),
                    "detail": action["parameters"].get("detail", ""),
                    "confirmed_by_user": True,
                    "confirmed_at": now,
                }
            )
        for artifact_path in result.artifact_paths:
            path = Path(artifact_path)
            completed["artifacts"].append(
                {
                    "role": action["intent"],
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "created_at": now,
                }
            )
        completed["processed_actions"].append(
            {
                "idempotency_key": original_action["idempotency_key"],
                "intent": original_action["intent"],
                "result_state": completed["state"],
                "processed_at": now,
            }
        )
        self.store.save(completed, expected_version=prev)
        return completed
