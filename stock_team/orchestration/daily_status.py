from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ARTIFACT_PATHS = {
    "stage0_universe": ("inputs", "stage0-universe.json"),
    "premarket_snapshot": ("inputs", "pre-market-snapshot.json"),
    "stage0_market_context": ("packets", "stage0-market-context.md"),
    "stage0_discussion_notes": ("inputs", "stage0-discussion-notes.md"),
    "stage1_decision_sheet": ("inputs", "stage1-decision-sheet.json"),
    "stage1_plan_evidence": ("packets", "stage1-plan-evidence.md"),
    "trading_plan": ("inputs", "trading-plan.json"),
    "intraday_guidance": ("inputs", "intraday-guidance.json"),
}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"invalid_json:{type(exc).__name__}"]


def _formal_snapshot(payload) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("markets"), dict):
        return False
    for symbol in ("QQQ", "SPY", "IWM", "VIXY"):
        row = payload["markets"].get(symbol)
        if not isinstance(row, dict):
            return False
        if row.get("source") not in {"polygon_premarket_snapshot", "polygon_premarket_1m_aggregates"}:
            return False
        if row.get("price") in (None, "") or row.get("prev_close") in (None, ""):
            return False
        if row.get("source") == "polygon_premarket_1m_aggregates" and not row.get("latest_bar_time_et"):
            return False
    return True


def _observation_snapshot(payload) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("evidence_level") != "observation_only":
        return False
    if payload.get("permission") != "no_trading_permission":
        return False
    if payload.get("source_kind") != "yfinance_observation_context":
        return False
    markets = payload.get("markets")
    if not isinstance(markets, dict):
        return False
    for symbol in ("QQQ", "SPY", "IWM", "VIXY"):
        row = markets.get(symbol)
        if not isinstance(row, dict):
            return False
        if any(row.get(field) in (None, "") for field in ("price", "prev_close", "source", "data_as_of")):
            return False
    return True


def _artifact(
    role: str,
    path: Path,
    session_trading_date: str,
    active_trading_date: str | None,
    observation_mode: bool,
) -> tuple[dict, object]:
    present = path.exists()
    payload = None
    issues: list[str] = []
    valid = present
    confirmed = False
    if present and path.suffix == ".json":
        payload, issues = _read_json(path)
        valid = payload is not None
    if valid and role == "stage0_universe":
        required = (
            ("source_inputs", "positions"),
            ("source_inputs", "prior_review"),
            ("source_inputs", "cognition_state"),
            ("permission_state_before_open",),
            ("forbidden_actions",),
        )
        valid = isinstance(payload, dict)
        for keys in required:
            value = payload
            for key in keys:
                value = value.get(key) if isinstance(value, dict) else None
            if value is None:
                valid = False
                issues.append("missing:" + ".".join(keys))
    elif valid and role == "premarket_snapshot":
        formal = _formal_snapshot(payload)
        observation = observation_mode and _observation_snapshot(payload)
        valid = formal or observation
        if observation and not formal:
            issues.append("observation_only_no_trading_permission")
        elif not valid:
            issues.append("formal_premarket_snapshot_missing")
    elif valid and role == "stage1_decision_sheet":
        valid = (
            isinstance(payload, dict)
            and isinstance(payload.get("focus_symbols"), list)
        )
        confirmed = valid and payload.get("user_confirmed") is True
    elif valid and role in {"trading_plan", "intraday_guidance"}:
        required = {"risk_mode", "allowed_actions", "forbidden_actions"}
        valid = isinstance(payload, dict) and required.issubset(payload)
        if role == "trading_plan" and valid:
            confirmation = payload.get("user_confirmation") or {}
            confirmed = confirmation.get("confirmed") is True
    artifact_trading_date = (
        payload.get("trading_date") or payload.get("date")
        if isinstance(payload, dict)
        else session_trading_date
    )
    artifact_trading_date = artifact_trading_date or session_trading_date or None
    if not present:
        freshness = "missing"
    elif not valid or not artifact_trading_date or not active_trading_date:
        freshness = "unknown"
    elif artifact_trading_date == active_trading_date:
        freshness = "fresh"
    else:
        freshness = "stale"
        issues.append("trading_date_mismatch")
    updated_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if present else None
    return {
        "role": role,
        "path": str(path),
        "present": present,
        "valid": bool(valid),
        "confirmed": bool(confirmed),
        "freshness": freshness,
        "source": "investing-os" if role not in {"premarket_snapshot", "stage0_market_context", "stage1_plan_evidence"} else "stock_team",
        "updated_at": updated_at,
        "issues": issues,
    }, payload


def _missing(code: str, severity: str, role: str, message: str, prompt: str) -> dict:
    return {
        "code": code,
        "severity": severity,
        "artifact_role": role,
        "field": "",
        "message": message,
        "conversation_prompt": prompt,
    }


def _nodes(current_node: str, current_step: str, current_status: str) -> list[dict]:
    node_ids = ["DAILY-0", "DAILY-1", "DAILY-2", "DAILY-3", "DAILY-4"]
    labels = ["晨间准备", "盘前决策", "开盘观察", "盘中管理", "盘后复盘"]
    current_index = node_ids.index(current_node)
    nodes = []
    for index, (node_id, label) in enumerate(zip(node_ids, labels)):
        status = "complete" if index < current_index else "not_started"
        if index == current_index:
            status = current_status
        substeps = []
        if node_id == "DAILY-1":
            step_ids = ["DAILY-1A", "DAILY-1B", "DAILY-1C", "DAILY-1D"]
            step_labels = ["市场环境", "焦点确认", "标的证据", "计划确认"]
            current_step_index = step_ids.index(current_step) if current_step in step_ids else -1
            for step_index, (step_id, step_label) in enumerate(zip(step_ids, step_labels)):
                step_status = "complete" if current_index > 1 or (current_step_index >= 0 and step_index < current_step_index) else "not_started"
                if current_step_index == step_index:
                    step_status = current_status
                substeps.append({"step": step_id, "label": step_label, "status": step_status, "artifact_roles": []})
        nodes.append({"node": node_id, "label": label, "status": status, "current_substep": current_step if node_id == current_node else "", "substeps": substeps})
    return nodes


def build_daily_status(
    *,
    session: dict,
    runtime_root: Path,
    now: datetime | None = None,
    active_trading_date: str | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    session_id = session.get("session_id", "")
    trading_date = session.get("market_date", "")
    active_trading_date = active_trading_date or trading_date or None
    records = []
    payloads = {}
    for role, (folder, suffix) in ARTIFACT_PATHS.items():
        record, payload = _artifact(
            role,
            Path(runtime_root) / folder / f"{session_id}-{suffix}",
            trading_date,
            active_trading_date,
            session.get("session_type") == "observation",
        )
        records.append(record)
        payloads[role] = payload
    by_role = {item["role"]: item for item in records}

    if session.get("state") in {"PLAN_APPROVED", "INTRADAY_ACTIVE", "MARKET_CLOSED", "REVIEW_REQUIRED", "QUICK_REVIEWED", "CLOSED_UNREVIEWED", "DAY_ARCHIVED"}:
        trading_plan = by_role.get("trading_plan")
        intraday_guidance = by_role.get("intraday_guidance")
        if (
            trading_plan
            and trading_plan["valid"]
            and trading_plan["freshness"] == "fresh"
            and intraday_guidance
            and intraday_guidance["valid"]
            and intraday_guidance["freshness"] == "fresh"
        ):
            trading_plan["confirmed"] = True

    missing_items = []
    confirmation = session.get("daily0_confirmation")
    if not isinstance(confirmation, dict) or confirmation.get("user_confirmed") is not True:
        node, step, status = "DAILY-0", "DAILY-0", "waiting_user"
        prompt = "请在当前对话确认今天的活动模式、账户事实状态和分析范围。"
        missing_items.append(_missing("daily0_confirmation_missing", status, "session", "DAILY-0 尚未确认。", prompt))
    elif not all(
        by_role[r]["valid"] and by_role[r]["freshness"] == "fresh"
        for r in ("stage0_universe", "premarket_snapshot", "stage0_market_context")
    ):
        node, step, status = "DAILY-1", "DAILY-1A", "waiting_data"
        prompt = "请等待或刷新当日正式盘前数据。"
        missing_items.append(_missing("stage0_data_missing", status, "stage0_market_context", "正式 Stage 0 数据尚未齐全。", prompt))
    elif not (
        by_role["stage0_discussion_notes"]["valid"]
        and by_role["stage0_discussion_notes"]["freshness"] == "fresh"
        and by_role["stage1_decision_sheet"]["confirmed"]
        and by_role["stage1_decision_sheet"]["freshness"] == "fresh"
    ):
        node, step, status = "DAILY-1", "DAILY-1B", "waiting_user"
        prompt = "请在当前对话讨论市场环境并确认进入 Stage 1 的标的。"
        missing_items.append(_missing("focus_confirmation_missing", status, "stage1_decision_sheet", "焦点池尚未确认。", prompt))
    elif not (
        by_role["stage1_plan_evidence"]["valid"]
        and by_role["stage1_plan_evidence"]["freshness"] == "fresh"
    ):
        node, step, status = "DAILY-1", "DAILY-1C", "waiting_data"
        prompt = "请等待焦点标的证据生成。"
        missing_items.append(_missing("stage1_evidence_missing", status, "stage1_plan_evidence", "Stage 1 证据尚未生成。", prompt))
    elif not (
        by_role["trading_plan"]["confirmed"]
        and by_role["trading_plan"]["freshness"] == "fresh"
        and by_role["intraday_guidance"]["valid"]
        and by_role["intraday_guidance"]["freshness"] == "fresh"
    ):
        node, step, status = "DAILY-1", "DAILY-1D", "waiting_user"
        prompt = "请在当前对话确认今日计划、允许动作、禁止动作与失效条件。"
        missing_items.append(_missing("plan_confirmation_missing", status, "trading_plan", "交易计划尚未确认。", prompt))
    else:
        node, step, status = "DAILY-2", "DAILY-2", "active"
        prompt = "请观察开盘事实；仅在计划失效、风险触发或准备交易时回到当前对话。"

    observation_available = session.get("session_type") == "observation" or (
        isinstance(confirmation, dict) and confirmation.get("account_fact_status") != "verified"
    )
    state_step = {
        "DAY_INITIALIZED": "DAILY-1A", "STAGE0_READY": "DAILY-1B",
        "FOCUS_CONFIRMED": "DAILY-1C", "STAGE1_READY": "DAILY-1D",
        "PLAN_APPROVED": "DAILY-2",
    }.get(session.get("state"))
    return {
        "schema_version": "1.0",
        "trading_date": trading_date,
        "generated_at": now.isoformat(),
        "current_node": node,
        "current_step": step,
        "overall_status": status,
        "observation_available": observation_available,
        "next_conversation_prompt": prompt,
        "nodes": _nodes(node, step, status),
        "artifacts": records,
        "missing_items": missing_items,
        "warnings": [],
        "state_sync": {
            "needed": state_step is not None and state_step != step,
            "canonical_step": step,
            "coordinator_state": session.get("state"),
            "suggested_action": "review_state_sync_in_conversation",
        },
        "cognition_links": {"context_inputs": [], "cognition_updates": [], "promotion_queue": ""},
    }


def write_daily_status(manifest: dict, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output_path)
    return output_path
