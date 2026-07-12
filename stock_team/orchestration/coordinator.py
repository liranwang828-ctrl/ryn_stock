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
        if action["intent"] == "start_stage0_observation":
            if state.get("session_type") != "observation":
                raise ValueError("start_stage0_observation requires an observation session")
            if action["parameters"].get("date") != state.get("market_date"):
                raise ValueError("observation Stage 0 date must match session market_date")
        if action["intent"] == "abandon_failed_session":
            last_error = state.get("last_error") or {}
            if last_error.get("retryable") is not False:
                raise ValueError("abandon_failed_session requires a non-retryable last_error")
            if not str(action["parameters"].get("reason", "")).strip():
                raise ValueError("abandon_failed_session requires a reason")
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

        if action["intent"] == "archive_day":
            from .archiver import archive_session

            review_path = Path(self.store.root).parent / "inputs" / f"{state['session_id']}-daily4-review.json"
            if state["state"] == "REVIEW_REQUIRED":
                if not review_path.exists():
                    failed = self.store.load(action["session_id"])
                    prev = failed["state_version"]
                    failed["state"] = "FAILED_TOOL"
                    failed["state_version"] = prev + 1
                    failed["last_error"] = {
                        "error_class": "RuntimeError",
                        "message": "full_review blocked: daily4 review file not found",
                        "retryable": False,
                        "intent": action["intent"],
                        "parameters": action["parameters"],
                        "resume_from_state": state["state"],
                        "occurred_at": now,
                    }
                    failed["processed_actions"].append({
                        "idempotency_key": original_action["idempotency_key"],
                        "intent": original_action["intent"],
                        "result_state": "FAILED_TOOL",
                        "processed_at": now,
                    })
                    failed["allowed_actions"] = allowed_actions("FAILED_TOOL")
                    failed["updated_at"] = now
                    self.store.save(failed, expected_version=prev)
                    return failed
                import json as _json
                review = _json.loads(review_path.read_text(encoding="utf-8"))
                if review.get("review_mode") == "full_review":
                    confirmations = review.get("user_confirmations", {})
                    missing = [k for k, v in confirmations.items() if not v]
                    if missing:
                        failed = self.store.load(action["session_id"])
                        prev = failed["state_version"]
                        failed["state"] = "FAILED_TOOL"
                        failed["state_version"] = prev + 1
                        failed["last_error"] = {
                            "error_class": "RuntimeError",
                            "message": f"full_review blocked: unconfirmed gates — {', '.join(missing)}",
                            "retryable": False,
                            "intent": action["intent"],
                            "parameters": action["parameters"],
                            "resume_from_state": state["state"],
                            "occurred_at": now,
                        }
                        failed["processed_actions"].append({
                            "idempotency_key": original_action["idempotency_key"],
                            "intent": original_action["intent"],
                            "result_state": "FAILED_TOOL",
                            "processed_at": now,
                        })
                        failed["allowed_actions"] = allowed_actions("FAILED_TOOL")
                        failed["updated_at"] = now
                        self.store.save(failed, expected_version=prev)
                        return failed
                    if review.get("ibkr_fact_status") != "verified":
                        failed = self.store.load(action["session_id"])
                        prev = failed["state_version"]
                        failed["state"] = "FAILED_TOOL"
                        failed["state_version"] = prev + 1
                        failed["last_error"] = {
                            "error_class": "RuntimeError",
                            "message": "full_review blocked: ibkr_fact_status not verified",
                            "retryable": False,
                            "intent": action["intent"],
                            "parameters": action["parameters"],
                            "resume_from_state": state["state"],
                            "occurred_at": now,
                        }
                        failed["processed_actions"].append({
                            "idempotency_key": original_action["idempotency_key"],
                            "intent": original_action["intent"],
                            "result_state": "FAILED_TOOL",
                            "processed_at": now,
                        })
                        failed["allowed_actions"] = allowed_actions("FAILED_TOOL")
                        failed["updated_at"] = now
                        self.store.save(failed, expected_version=prev)
                        return failed

            try:
                _, manifest_path = archive_session(
                    session_id=state["session_id"],
                    trading_date=state["market_date"],
                    session_file=str(self.store._session_path(state["session_id"])),
                    artifact_ledger=state["artifacts"],
                    archive_root=str(Path(self.store.root).parent / "archive"),
                )
            except RuntimeError as err:
                failed = self.store.load(action["session_id"])
                prev = failed["state_version"]
                failed["state"] = "FAILED_TOOL"
                failed["state_version"] = prev + 1
                failed["last_error"] = {
                    "error_class": err.__class__.__name__,
                    "message": str(err),
                    "retryable": False,
                    "intent": action["intent"],
                    "parameters": action["parameters"],
                    "resume_from_state": state["state"],
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
            state["archive_manifest_path"] = manifest_path

        previous_version = state["state_version"]
        source_state = state["state"]
        running_state = begin_transition(state["state"], action["intent"])
        state["state"] = running_state
        state["state_version"] = previous_version + 1
        state["updated_at"] = now
        self.store.save(state, expected_version=previous_version)

        try:
            _meta_intents = {"request_exception", "close_market", "close_observation_day", "freeze", "quick_review", "review_day", "record_observation_exception", "archive_day", "abandon_failed_session"}
            if action["intent"] in _meta_intents:
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
            failed["allowed_actions"] = (
                ["retry_last_action"]
                if err.retryable
                else allowed_actions("FAILED_TOOL")
            )
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
        if action["intent"] == "record_observation_exception":
            completed.setdefault("observation_exceptions", []).append(
                {
                    "reason": action["parameters"].get("reason", ""),
                    "detail": action["parameters"].get("detail", ""),
                    "confirmed_by_user": True,
                    "confirmed_at": now,
                }
            )
        if action["intent"] in ("freeze", "quick_review", "review_day", "abandon_failed_session"):
            import json as _json

            from .models import new_daily4_review

            if action["intent"] in ("freeze", "abandon_failed_session"):
                review_mode = "freeze"
            elif action["intent"] == "quick_review":
                review_mode = "quick_review"
            else:
                review_mode = "full_review"
            review = new_daily4_review(
                completed["session_id"],
                completed.get("market_date", ""),
                review_mode,
                ibkr_fact_status=action["parameters"].get("ibkr_fact_status", "stale_unverified"),
            )
            if action["intent"] == "abandon_failed_session":
                review["review_judgments"].append({
                    "judgment_type": "data_quality",
                    "summary": f"Abandoned historical failure: {action['parameters']['reason']}",
                    "evidence_refs": [],
                    "confidence": "high",
                    "source": "user_confirmed",
                })
                review["archive_closure"]["user_confirmed_at"] = now
            if action["intent"] == "quick_review":
                for anomaly in action["parameters"].get("position_anomalies", []):
                    review["review_judgments"].append({
                        "judgment_type": "execution",
                        "summary": anomaly,
                        "evidence_refs": [],
                        "confidence": "low",
                        "source": "assistant_inferred",
                    })
                for deviation in action["parameters"].get("risk_deviations", []):
                    review["review_judgments"].append({
                        "judgment_type": "sizing",
                        "summary": deviation,
                        "evidence_refs": [],
                        "confidence": "low",
                        "source": "assistant_inferred",
                    })
                for warning in action["parameters"].get("pending_warnings", []):
                    review["review_judgments"].append({
                        "judgment_type": "data_quality",
                        "summary": warning,
                        "evidence_refs": [],
                        "confidence": "low",
                        "source": "assistant_inferred",
                    })
                if action["parameters"].get("user_accepted"):
                    review["user_confirmations"]["bias_classification_confirmed"] = True
                    review["archive_closure"]["user_confirmed_at"] = now
            review_suffix = (
                "failed-session-debt.json"
                if action["intent"] == "abandon_failed_session"
                else "daily4-review.json"
            )
            review_path = Path(self.store.root).parent / "inputs" / f"{completed['session_id']}-{review_suffix}"
            review_path.parent.mkdir(parents=True, exist_ok=True)
            review_path.write_text(_json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
            if action["intent"] != "abandon_failed_session":
                completed["daily4_review_path"] = str(review_path)
            completed["artifacts"].append({
                "logical_name": (
                    "failed_session_debt"
                    if action["intent"] == "abandon_failed_session"
                    else "daily4_review"
                ),
                "role": action["intent"],
                "path": str(review_path),
                "sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
                "created_at": now,
            })
            if action["intent"] == "abandon_failed_session":
                known_paths = {str(Path(item["path"])) for item in completed["artifacts"] if item.get("path")}
                runtime_root = Path(self.store.root).parent
                prefix = f"{completed['session_id']}-"
                for folder in ("inputs", "packets"):
                    artifact_dir = runtime_root / folder
                    if not artifact_dir.exists():
                        continue
                    for path in sorted(artifact_dir.glob(f"{prefix}*")):
                        if not path.is_file() or str(path) in known_paths:
                            continue
                        completed["artifacts"].append({
                            "logical_name": path.name[len(prefix):],
                            "role": "retained_historical_artifact",
                            "path": str(path),
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "created_at": now,
                        })
                        known_paths.add(str(path))
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
