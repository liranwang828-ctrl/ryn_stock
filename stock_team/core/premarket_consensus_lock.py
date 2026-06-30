"""Lock a human-agent premarket consensus into the dashboard/poll contracts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, date as _date
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from stock_team.utils.capsule_utils import get_capsule_dir, get_current_nodes_path, get_latest_premarket_plan_path


def _load(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            value = json.load(f)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _save(path: str, payload: dict[str, Any]) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def _node(price: float | None, label: str, source: str) -> dict[str, Any]:
    return {"price": price, "label": label, "source": source}


def _normalize_decision(raw: dict[str, Any]) -> dict[str, Any]:
    entry_base = _float_or_none(raw.get("entry_base") or raw.get("entry_low"))
    target = _float_or_none(raw.get("target") or raw.get("target_price"))
    return {
        "action": raw.get("action") or raw.get("decision") or "watch",
        "entry_base": entry_base,
        "entry_low": _float_or_none(raw.get("entry_low")),
        "entry_high": _float_or_none(raw.get("entry_high")),
        "hard_stop": _float_or_none(raw.get("hard_stop") or raw.get("stop_loss")),
        "soft_stop": _float_or_none(raw.get("soft_stop")),
        "target": target,
        "flex_add": _float_or_none(raw.get("flex_add") or raw.get("flex_add_level") or entry_base),
        "flex_reduce": _float_or_none(raw.get("flex_reduce") or raw.get("flex_reduce_level") or target),
        "target_2": _float_or_none(raw.get("target_2") or raw.get("tp2")),
        "target_3": _float_or_none(raw.get("target_3") or raw.get("tp3")),
        "rr_ratio": _float_or_none(raw.get("rr_ratio")),
        "reasoning": raw.get("reasoning") or raw.get("thesis") or "",
        "allocation_pct": _float_or_none(raw.get("allocation_pct")),
        "thesis_status": raw.get("thesis_status") or "intact",
        "falsification": raw.get("falsification") or raw.get("today_falsification") or [],
    }


def _build_premarket_summary(sym: str, date: str, decision: dict[str, Any], generated_at: str) -> dict[str, Any]:
    entry_zone = [v for v in (decision.get("entry_low"), decision.get("entry_high")) if v is not None]
    return {
        "sym": sym,
        "date": date,
        "generated_at": generated_at,
        "source": "human_agent_consensus",
        "entry": {
            "entry_base": decision.get("entry_base"),
            "entry_base_adj": decision.get("entry_base"),
            "decision": decision.get("action"),
            "action": decision.get("action"),
            "reasoning": decision.get("reasoning"),
            "target_price": decision.get("target"),
            "stop_loss": decision.get("hard_stop"),
            "rr_ratio": decision.get("rr_ratio"),
            "entry_zone": entry_zone,
        },
        "exit": {
            "hard_stop": decision.get("hard_stop"),
            "soft_stop": decision.get("soft_stop"),
            "target_price": decision.get("target"),
            "flex_add_level": decision.get("flex_add"),
            "flex_reduce_level": decision.get("flex_reduce"),
        },
        "thesis": {
            "status": decision.get("thesis_status"),
            "today_falsification": decision.get("falsification") or [],
        },
        "strategic_context": {
            "strategic_stance": decision.get("action"),
            "summary": decision.get("reasoning"),
            "source": "human_agent_consensus",
        },
    }


def _build_macro_strategy(sym: str, date: str, decision: dict[str, Any], generated_at: str) -> dict[str, Any]:
    nodes = {
        "entry_base": _node(decision.get("entry_base"), "Entry base", "human_agent_consensus"),
        "hard_stop": _node(decision.get("hard_stop"), "Hard stop", "human_agent_consensus"),
        "soft_stop": _node(decision.get("soft_stop"), "Soft warning", "human_agent_consensus"),
        "target": _node(decision.get("target"), "Target", "human_agent_consensus"),
        "flex_add": _node(decision.get("flex_add"), "Flex add", "human_agent_consensus"),
        "flex_reduce": _node(decision.get("flex_reduce"), "Flex reduce", "human_agent_consensus"),
        "target_2": _node(decision.get("target_2") or decision.get("flex_reduce"), "Target 2", "human_agent_consensus"),
    }
    if decision.get("target_3") is not None:
        nodes["target_3"] = _node(decision.get("target_3"), "Target 3", "human_agent_consensus")
    return {
        "sym": sym,
        "date": date,
        "generated_at": generated_at,
        "source": "human_agent_consensus",
        "nodes": {k: v for k, v in nodes.items() if v.get("price") is not None},
        "strategy": {
            "action": decision.get("action"),
            "decision": decision.get("action"),
            "reasoning": decision.get("reasoning"),
            "rr_ratio": decision.get("rr_ratio"),
        },
        "position_plan": {"target_pct": decision.get("allocation_pct")},
    }


def _build_current_nodes(sym: str, date: str, macro: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "sym": sym,
        "date": date,
        "generated_at": generated_at,
        "source": macro.get("source") or "human_agent_consensus",
        "source_plan": "latest_premarket_plan.json",
        "nodes": macro.get("nodes", {}),
        "strategy": macro.get("strategy", {}),
    }


def _daily_plan_row(sym: str, date: str, decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "premarket_summary_path": f"findings/premarket_summary_{date}_{sym}.json",
        "action_now": decision.get("action"),
        "key_levels": {
            "entry_base": decision.get("entry_base"),
            "hard_stop": decision.get("hard_stop"),
            "flex_add": decision.get("flex_add"),
            "flex_reduce": decision.get("flex_reduce"),
            "target": decision.get("target"),
        },
        "entry_go_status": "decided",
        "pending_suggestions": 0,
        "memo_valid": True,
        "is_lite_inferred": False,
        "reasoning": decision.get("reasoning"),
        "rr_ratio": decision.get("rr_ratio"),
    }


def _merge_config_symbols(base_dir: str, symbols: list[str]) -> None:
    cfg_dir = os.path.join(base_dir, "config")
    daily_focus_path = os.path.join(cfg_dir, "daily_focus.json")
    focus = _load(daily_focus_path)
    focus["focus_stocks"] = symbols
    _save(daily_focus_path, focus)

    _save(os.path.join(cfg_dir, "today_focus.json"), symbols)

    poll_path = os.path.join(cfg_dir, "poll_config.json")
    poll = _load(poll_path)
    poll["default_symbols"] = symbols
    positions = _load(os.path.join(cfg_dir, "positions.json")).get("positions", {})
    if isinstance(positions, dict):
        poll["portfolio_symbols"] = [str(sym).upper() for sym in positions if str(sym).strip()]
    _save(poll_path, poll)


def _normalize_rejected(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k).upper(): str(v) for k, v in value.items() if str(k).strip()}
    if isinstance(value, list):
        result: dict[str, str] = {}
        for item in value:
            if isinstance(item, dict):
                sym = str(item.get("sym") or item.get("symbol") or "").upper().strip()
                reason = item.get("reason") or item.get("note") or ""
                if sym:
                    result[sym] = str(reason)
            else:
                sym = str(item).upper().strip()
                if sym:
                    result[sym] = ""
        return result
    return {}


def _consensus_record_path(date: str, session_name: str | None, base_dir: str) -> str:
    safe_session = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (session_name or "manual")).strip("_")
    return os.path.join(base_dir, "findings", f"premarket_consensus_{date}_{safe_session or 'manual'}.json")


def _display_path(path: str | None, base_dir: str) -> str | None:
    if not path:
        return None
    try:
        return os.path.relpath(path, base_dir).replace("\\", "/")
    except Exception:
        return path.replace("\\", "/")


def _build_confirmation(
    date: str,
    symbols: list[str],
    decisions: dict[str, dict[str, Any]],
    rejected_symbols: dict[str, str],
    written: list[str],
    dashboard_path: str | None,
    base_dir: str,
) -> dict[str, Any]:
    updated_files = [_display_path(path, base_dir) for path in written]
    if dashboard_path:
        updated_files.append(_display_path(dashboard_path, base_dir))
    updated_files = [path for path in updated_files if path]

    lines = [
        f"✅ 今日盘前共识已锁定 ({date})",
        f"今日关注: {' / '.join(symbols) if symbols else '无'}",
        "",
        "行动与价格节点:",
    ]
    for sym in symbols:
        decision = decisions.get(sym, {})
        parts = [
            f"{sym}: {decision.get('action') or 'watch'}",
            f"entry_base={decision.get('entry_base')}",
            f"hard_stop={decision.get('hard_stop')}",
            f"target={decision.get('target')}",
        ]
        if decision.get("flex_add") is not None:
            parts.append(f"flex_add={decision.get('flex_add')}")
        if decision.get("flex_reduce") is not None:
            parts.append(f"flex_reduce={decision.get('flex_reduce')}")
        if decision.get("allocation_pct") is not None:
            parts.append(f"allocation_pct={decision.get('allocation_pct')}")
        lines.append("- " + ", ".join(parts))

    if rejected_symbols:
        lines.extend(["", "未纳入今日关注:"])
        for sym, reason in rejected_symbols.items():
            lines.append(f"- {sym}: {reason or '仅作为研究/对比，不进入今日盘中关注'}")

    lines.extend(["", "已更新所需文件和数据:"])
    for path in updated_files:
        lines.append(f"- {path}")

    return {
        "text": "\n".join(lines),
        "selected_symbols": symbols,
        "rejected_symbols": rejected_symbols,
        "actions": {
            sym: {
                "action": decisions.get(sym, {}).get("action"),
                "entry_base": decisions.get(sym, {}).get("entry_base"),
                "hard_stop": decisions.get(sym, {}).get("hard_stop"),
                "target": decisions.get(sym, {}).get("target"),
                "flex_add": decisions.get(sym, {}).get("flex_add"),
                "flex_reduce": decisions.get(sym, {}).get("flex_reduce"),
                "allocation_pct": decisions.get(sym, {}).get("allocation_pct"),
            }
            for sym in symbols
        },
        "updated_files": updated_files,
    }


def lock_consensus(
    date: str,
    decisions: dict[str, dict[str, Any]],
    base_dir: str = BASE,
    session_name: str | None = None,
    rebuild_dashboard: bool = True,
    rejected_symbols: dict[str, str] | None = None,
    portfolio_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the fixed premarket consensus files consumed by poll and dashboard."""
    generated_at = datetime.now(timezone.utc).isoformat()
    symbols = [str(sym).upper().strip() for sym in decisions if str(sym).strip()]
    normalized = {sym: _normalize_decision(decisions[sym]) for sym in symbols}
    written: list[str] = []

    for sym, decision in normalized.items():
        pm = _build_premarket_summary(sym, date, decision, generated_at)
        flat_pm_path = os.path.join(base_dir, "findings", f"premarket_summary_{date}_{sym}.json")
        written.append(_save(flat_pm_path, pm))

        capsule_pm_path = os.path.join(get_capsule_dir(sym, base_dir), "plans", f"premarket_summary_{date}.json")
        written.append(_save(capsule_pm_path, pm))
        latest_pm = dict(pm)
        latest_pm["source_archive"] = f"plans/premarket_summary_{date}.json"
        written.append(_save(get_latest_premarket_plan_path(sym, base_dir), latest_pm))

        macro = _build_macro_strategy(sym, date, decision, generated_at)
        written.append(_save(os.path.join(base_dir, f"macro_strategy_{sym}.json"), macro))
        written.append(_save(get_current_nodes_path(sym, base_dir), _build_current_nodes(sym, date, macro, generated_at)))

        capsule_strategy_path = os.path.join(get_capsule_dir(sym, base_dir), "strategy.json")
        capsule_strategy = _load(capsule_strategy_path)
        capsule_strategy.update({
            "symbol": sym,
            "updated_at": generated_at,
            "key_levels": {
                "entry_low": decision.get("entry_low"),
                "entry_high": decision.get("entry_high"),
                "entry_base": decision.get("entry_base"),
                "stop_loss": decision.get("hard_stop"),
                "target_price": decision.get("target"),
            },
            "exit_plan": {
                "flex_add_level": decision.get("flex_add"),
                "flex_reduce_level": decision.get("flex_reduce"),
            },
            "thesis": {
                "status": decision.get("thesis_status"),
                "today_falsification": decision.get("falsification") or [],
            },
        })
        written.append(_save(capsule_strategy_path, capsule_strategy))

    daily_plan = _load(os.path.join(base_dir, f"daily_plan_{date}.json"))
    daily_plan.update({
        "date": date,
        "generated_at": generated_at,
        "source": "human_agent_consensus",
        "symbols_today": symbols,
    })
    per_symbol = daily_plan.setdefault("per_symbol", {})
    stocks = daily_plan.setdefault("stocks", {})
    for sym, decision in normalized.items():
        row = _daily_plan_row(sym, date, decision)
        per_symbol[sym] = row
        stocks[sym] = {
            "stop": decision.get("hard_stop"),
            "t1_target": decision.get("target"),
            "t2_target": decision.get("flex_reduce"),
            "action_now": decision.get("action"),
            "key_levels": row["key_levels"],
        }
    written.append(_save(os.path.join(base_dir, f"daily_plan_{date}.json"), daily_plan))

    lock_payload = {
        "date": date,
        "locked": True,
        "locked_at": generated_at,
        "session_name": session_name,
        "symbols": symbols,
        "rejected_symbols": rejected_symbols or {},
        "message": "Human-agent premarket consensus is locked. Do not rerun automated CIO/strategy agents before market close.",
        "source": "premarket_consensus_lock",
    }
    written.append(_save(os.path.join(base_dir, "findings", "session_lock.json"), lock_payload))
    _merge_config_symbols(base_dir, symbols)

    consensus_record = {
        "date": date,
        "generated_at": generated_at,
        "session_name": session_name,
        "selected_symbols": symbols,
        "rejected_symbols": rejected_symbols or {},
        "portfolio_context": portfolio_context or {},
        "decisions": normalized,
        "source": "premarket_consensus_lock",
    }
    written.append(_save(_consensus_record_path(date, session_name, base_dir), consensus_record))

    dashboard_path = None
    if rebuild_dashboard:
        from stock_team.server.dashboard_writer import write_dashboard
        dashboard_path = write_dashboard(date, symbols=symbols, base_dir=base_dir)
    confirmation = _build_confirmation(
        date=date,
        symbols=symbols,
        decisions=normalized,
        rejected_symbols=rejected_symbols or {},
        written=written,
        dashboard_path=dashboard_path,
        base_dir=base_dir,
    )

    return {
        "ok": True,
        "date": date,
        "symbols": symbols,
        "rejected_symbols": rejected_symbols or {},
        "written": written,
        "dashboard_path": dashboard_path,
        "confirmation": confirmation,
    }


def lock_decision_package(
    date: str,
    package: dict[str, Any],
    base_dir: str = BASE,
    rebuild_dashboard: bool = True,
) -> dict[str, Any]:
    """Lock the standard multi-symbol discussion result package."""
    if not isinstance(package, dict):
        raise ValueError("decision package must be a dict")
    all_decisions = package.get("decisions") or package.get("per_symbol_decisions") or {}
    if not isinstance(all_decisions, dict):
        raise ValueError("decision package decisions must be a dict keyed by symbol")

    selected = [str(sym).upper().strip() for sym in package.get("selected_symbols", []) if str(sym).strip()]
    if not selected:
        selected = [str(sym).upper().strip() for sym in all_decisions if str(sym).strip()]
    rejected = _normalize_rejected(package.get("rejected_symbols"))
    selected = [sym for sym in dict.fromkeys(selected) if sym not in rejected]
    selected_decisions = {
        sym: all_decisions[sym] if sym in all_decisions else all_decisions.get(sym.lower(), {})
        for sym in selected
    }
    return lock_consensus(
        date=date,
        decisions=selected_decisions,
        base_dir=base_dir,
        session_name=package.get("session_name"),
        rebuild_dashboard=rebuild_dashboard,
        rejected_symbols=rejected,
        portfolio_context=package.get("portfolio_context") or {},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lock human-agent premarket consensus into dashboard/poll files.")
    parser.add_argument("--date", default=_date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--session", default=None)
    parser.add_argument("--decisions-json", required=True, help="Path to a JSON object keyed by symbol.")
    parser.add_argument("--no-rebuild", action="store_true")
    args = parser.parse_args(argv)

    payload = _load(args.decisions_json)
    if not payload:
        print(f"No decisions found in {args.decisions_json}", file=sys.stderr)
        return 1
    if "decisions" in payload or "selected_symbols" in payload:
        if args.session and not payload.get("session_name"):
            payload["session_name"] = args.session
        result = lock_decision_package(
            date=args.date,
            package=payload,
            base_dir=BASE,
            rebuild_dashboard=not args.no_rebuild,
        )
    else:
        result = lock_consensus(
            date=args.date,
            decisions=payload,
            base_dir=BASE,
            session_name=args.session,
            rebuild_dashboard=not args.no_rebuild,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
