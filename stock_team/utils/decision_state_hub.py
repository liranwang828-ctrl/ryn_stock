import argparse
import glob
import json
import os
import re
from datetime import datetime, timezone
from typing import Any


_POSSIBLE_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = (
    _POSSIBLE_BASE
    if os.path.exists(os.path.join(_POSSIBLE_BASE, "templates"))
    else os.path.expanduser("~/stock_team")
)


def _load_json(path: str) -> dict[str, Any]:
    data, _status = _load_json_with_status(path)
    return data


def _load_json_with_status(path: str) -> tuple[dict[str, Any], str]:
    if not os.path.exists(path):
        return {}, "missing"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data, "ok"
        return {}, "invalid"
    except json.JSONDecodeError:
        return {}, "parse_error"
    except Exception:
        return {}, "invalid"


def _rel(path: str, base_dir: str) -> str:
    try:
        return os.path.relpath(path, base_dir).replace("\\", "/")
    except Exception:
        return path.replace("\\", "/")


def _source_status(
    path: str,
    base_dir: str,
    expected_date: str | None = None,
    load_status: str | None = None,
) -> dict[str, Any]:
    if not os.path.exists(path):
        return {"status": "missing", "path": _rel(path, base_dir)}
    if load_status in {"parse_error", "invalid"}:
        return {"status": load_status, "path": _rel(path, base_dir)}
    if expected_date and expected_date not in os.path.basename(path):
        status = "stale"
    else:
        status = "fresh" if expected_date else "available"
    return {"status": status, "path": _rel(path, base_dir)}


def _premarket_path(find_dir: str, date: str, sym: str) -> str:
    sym = sym.upper()
    capsule_path = os.path.join(
        find_dir, "symbols", sym, "plans", f"premarket_summary_{date}.json"
    )
    if os.path.exists(capsule_path):
        return capsule_path

    flat_path = os.path.join(find_dir, f"premarket_summary_{date}_{sym}.json")
    if os.path.exists(flat_path):
        return flat_path

    stale_candidates = _premarket_candidates(find_dir, sym)
    if stale_candidates:
        return stale_candidates[-1][1]
    return flat_path


def _premarket_candidates(find_dir: str, sym: str) -> list[tuple[str, str]]:
    sym = sym.upper()
    candidates: list[tuple[str, str]] = []
    patterns = [
        os.path.join(find_dir, "symbols", sym, "plans", "premarket_summary_*.json"),
        os.path.join(find_dir, f"premarket_summary_*_{sym}.json"),
    ]
    for pattern in patterns:
        for path in glob.glob(pattern):
            date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", os.path.basename(path))
            if date_match:
                candidates.append((date_match.group(1), path))
    return sorted(candidates, key=lambda item: item[0])


def _entry_decision_path(find_dir: str, date: str) -> str:
    return os.path.join(find_dir, f"entry_decision_{date}.json")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_thesis(premarket: dict[str, Any]) -> dict[str, Any]:
    thesis = premarket.get("thesis") if isinstance(premarket.get("thesis"), dict) else {}
    strategic = (
        premarket.get("strategic_context")
        if isinstance(premarket.get("strategic_context"), dict)
        else {}
    )
    base = (
        thesis.get("base_thesis")
        or thesis.get("summary")
        or strategic.get("base_thesis")
        or strategic.get("strategic_stance")
    )
    catalysts = thesis.get("key_catalysts") or strategic.get("key_catalysts")
    risks = thesis.get("main_risks") or strategic.get("main_risks")
    contradictions = []
    falsification = thesis.get("today_falsification") or strategic.get("falsification")
    if falsification:
        contradictions.extend(str(item) for item in _as_list(falsification))

    return {
        "base_thesis": base or "未找到可用 thesis 字段",
        "key_catalysts": [str(item) for item in _as_list(catalysts)],
        "main_risks": [str(item) for item in _as_list(risks)],
        "contradictions": contradictions,
        "llm_confidence": strategic.get("unified_confidence"),
        "llm_confidence_reason": (
            "来自 premarket_summary/strategic_context"
            if base
            else "未找到可用 thesis 字段"
        ),
        "verdict": "supportive" if base else "insufficient",
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _factor_quality(report: dict[str, Any]) -> tuple[dict[str, Any], str, str, list[str]]:
    factors = report.get("factors") if isinstance(report.get("factors"), dict) else {}
    if not factors:
        return {}, "neutral", "unavailable", ["未找到因子 IC 报告"]

    notes: list[str] = []
    usable_count = 0
    for name, data in factors.items():
        if not isinstance(data, dict):
            continue
        sample_weeks = _to_int(data.get("sample_weeks") or data.get("weeks"))
        mean_ic = _to_float(data.get("mean_ic"))
        if sample_weeks and sample_weeks < 8:
            notes.append(f"{name} 样本周数不足: {sample_weeks}")
        if abs(mean_ic) >= 0.03 and sample_weeks >= 8:
            usable_count += 1

    if usable_count:
        quality = "usable"
        direction = "supportive"
    else:
        quality = "weak"
        direction = "neutral"
    if not notes:
        notes.append("因子报告可用，未发现低样本提示")
    return factors, direction, quality, notes


def _extract_factor_evidence(
    find_dir: str, base_dir: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = os.path.join(find_dir, "factor_ic_report.json")
    report, load_status = _load_json_with_status(path)
    scores, direction, quality, notes = _factor_quality(report)
    return {
        "factor_scores": scores,
        "factor_direction": direction,
        "factor_quality": quality,
        "factor_notes": notes,
    }, _source_status(path, base_dir, load_status=load_status)


def _load_evidence_credibility(
    find_dir: str, base_dir: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = os.path.join(find_dir, "evidence_credibility_report.json")
    report, load_status = _load_json_with_status(path)
    return report, _source_status(path, base_dir, load_status=load_status)


def _factor_from_credibility(report: dict[str, Any]) -> dict[str, Any]:
    factor_cred = (
        report.get("factor_credibility")
        if isinstance(report.get("factor_credibility"), dict)
        else {}
    )
    overrides = (
        report.get("decision_state_overrides")
        if isinstance(report.get("decision_state_overrides"), dict)
        else {}
    )
    factor_quality = (
        overrides.get("factor_quality")
        or factor_cred.get("overall_verdict")
        or "unavailable"
    )
    factors = factor_cred.get("factors") if isinstance(factor_cred.get("factors"), dict) else {}
    warnings = overrides.get("required_warnings")
    return {
        "factor_scores": factors,
        "factor_direction": "supportive" if factor_quality in {"robust", "usable"} else "neutral",
        "factor_quality": factor_quality,
        "factor_notes": list(warnings) if isinstance(warnings, list) else [],
    }


def _backtest_from_credibility(report: dict[str, Any]) -> dict[str, Any]:
    backtest_cred = (
        report.get("backtest_credibility")
        if isinstance(report.get("backtest_credibility"), dict)
        else {}
    )
    overrides = (
        report.get("decision_state_overrides")
        if isinstance(report.get("decision_state_overrides"), dict)
        else {}
    )
    notes = backtest_cred.get("notes") if isinstance(backtest_cred.get("notes"), list) else []
    warnings = overrides.get("required_warnings") if isinstance(overrides.get("required_warnings"), list) else []
    full = backtest_cred.get("full_lifecycle") if isinstance(backtest_cred.get("full_lifecycle"), dict) else {}
    time_oos = backtest_cred.get("time_oos") if isinstance(backtest_cred.get("time_oos"), dict) else {}
    style_oos = backtest_cred.get("style_oos") if isinstance(backtest_cred.get("style_oos"), dict) else {}
    parameter_stability = (
        backtest_cred.get("parameter_stability")
        if isinstance(backtest_cred.get("parameter_stability"), dict)
        else {"tier": "unknown"}
    )
    return {
        "strategy_family": "weekly_rebalance",
        "matched_signal_set": "credibility_report",
        "in_sample_summary": full,
        "out_of_sample_summary": {
            "time_oos": time_oos,
            "style_oos": style_oos,
        },
        "drawdown_profile": {},
        "parameter_stability": parameter_stability,
        "backtest_verdict": (
            overrides.get("backtest_verdict")
            or backtest_cred.get("overall_verdict")
            or "unavailable"
        ),
        "backtest_notes": list(notes) + list(warnings),
    }


def _extract_backtest_evidence(
    find_dir: str, base_dir: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = os.path.join(find_dir, "weekly_oos_validation_results.json")
    report, load_status = _load_json_with_status(path)
    if not report:
        return {
            "strategy_family": "weekly_rebalance",
            "matched_signal_set": "default",
            "in_sample_summary": {},
            "out_of_sample_summary": {},
            "drawdown_profile": {},
            "parameter_stability": "unknown",
            "backtest_verdict": "unavailable",
            "backtest_notes": ["未找到周度样本外验证报告"],
        }, _source_status(path, base_dir, load_status=load_status)

    time_oos = report.get("time_oos") or report.get("time_oos_validation") or {}
    style_oos = report.get("style_oos") or report.get("style_oos_validation") or {}
    full = report.get("full_lifecycle") or report.get("full_period") or {}
    time_oos = time_oos if isinstance(time_oos, dict) else {}
    style_oos = style_oos if isinstance(style_oos, dict) else {}
    full = full if isinstance(full, dict) else {}
    alpha = _to_float(time_oos.get("alpha_pct"))
    style_alpha = _to_float(style_oos.get("alpha_pct"))
    verdict = "supportive" if alpha > 0 else "caution"
    notes = ["time-OOS alpha 为正"] if alpha > 0 else ["time-OOS alpha 不占优"]
    if style_alpha < 0:
        notes.append("style-OOS alpha 为负，需要在 dashboard 中保持可见")

    return {
        "strategy_family": "weekly_rebalance",
        "matched_signal_set": "default",
        "in_sample_summary": full,
        "out_of_sample_summary": {
            "time_oos": time_oos,
            "style_oos": style_oos,
        },
        "drawdown_profile": {
            "full_lifecycle_max_drawdown_pct": full.get("max_drawdown_pct"),
            "time_oos_max_drawdown_pct": time_oos.get("max_drawdown_pct"),
        },
        "parameter_stability": "unknown",
        "backtest_verdict": verdict,
        "backtest_notes": notes,
    }, _source_status(path, base_dir, load_status=load_status)


def _decision_for_symbol(entry_file: dict[str, Any], sym: str) -> dict[str, Any]:
    sym = sym.upper()
    decisions = entry_file.get("decisions")
    if isinstance(decisions, dict):
        value = decisions.get(sym)
        return value if isinstance(value, dict) else {}
    value = entry_file.get(sym)
    return value if isinstance(value, dict) else {}


def _extract_execution(
    sym: str, premarket: dict[str, Any], entry_file: dict[str, Any]
) -> dict[str, Any]:
    entry = premarket.get("entry") if isinstance(premarket.get("entry"), dict) else {}
    exit_data = premarket.get("exit") if isinstance(premarket.get("exit"), dict) else {}
    dec = _decision_for_symbol(entry_file, sym)
    decision_text = str(dec.get("decision") or "").strip()

    if decision_text == "可入场":
        action_state = "act"
        action_reason = "entry_decision 标记为可入场"
    elif decision_text == "不入场":
        action_state = "avoid"
        action_reason = "entry_decision 标记为不入场"
    elif decision_text:
        action_state = "wait"
        action_reason = f"entry_decision 标记为{decision_text}"
    else:
        action_state = "monitor"
        action_reason = "等待更多证据"

    return {
        "current_price": premarket.get("current_price"),
        "entry_zone": entry.get("entry_base") or entry.get("entry_base_adj"),
        "stop_level": exit_data.get("hard_stop") or entry.get("stop_loss"),
        "target_zone": exit_data.get("target_price") or entry.get("target_price"),
        "wait_conditions": dec.get("soft_vetoes") or [],
        "action_state": action_state,
        "action_reason": action_reason,
        "position_context": premarket.get("position_context") or "no_position",
    }


def _audit_item(source: str, status: str, detail: str) -> dict[str, str]:
    return {"source": source, "status": status, "detail": detail}


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def _allowed_actions(verdict: str, blocked_by: list[str], alignment: str) -> list[str]:
    if blocked_by:
        return ["wait", "monitor", "avoid"]
    if verdict == "act" and alignment == "aligned":
        return ["act", "wait", "monitor", "avoid"]
    if verdict == "avoid":
        return ["avoid", "monitor", "wait"]
    return ["wait", "monitor", "avoid"]


def _controller_audit(
    thesis: dict[str, Any],
    factor: dict[str, Any],
    backtest: dict[str, Any],
    execution: dict[str, Any],
    blocked_by: list[str],
    required: list[str],
    alignment: str,
    confidence: int,
    verdict: str,
) -> dict[str, Any]:
    evidence_for: list[dict[str, str]] = []
    evidence_against: list[dict[str, str]] = []
    downgrade_reasons: list[str] = []
    forbidden_claims: list[str] = []

    if thesis.get("verdict") == "supportive":
        evidence_for.append(_audit_item("thesis", "supportive", "个股 thesis 可用"))
    else:
        evidence_against.append(_audit_item("thesis", "insufficient", "缺少可用个股 thesis"))
        downgrade_reasons.append("缺少可用个股 thesis，不能提高主控置信度")

    factor_quality = str(factor.get("factor_quality") or "unavailable")
    if factor_quality in {"usable", "robust"}:
        evidence_for.append(_audit_item("factor", factor_quality, "存在可用因子证据"))
    else:
        evidence_against.append(_audit_item("factor", factor_quality, "因子证据不足或不可用"))
        downgrade_reasons.append("因子证据不足，不能声称强因子支持")
        forbidden_claims.append("不能把弱因子或样本不足因子说成强信号")

    backtest_verdict = str(backtest.get("backtest_verdict") or "unavailable")
    if backtest_verdict == "supportive":
        evidence_for.append(_audit_item("backtest", "supportive", "回测证据支持当前策略族"))
    else:
        evidence_against.append(_audit_item("backtest", backtest_verdict, "回测证据需要谨慎或不可用"))
        downgrade_reasons.append(f"回测证据为 {backtest_verdict}，不能声称完全验证")
        forbidden_claims.append("不能把 caution 回测称为 fully validated")

    for blocker in blocked_by:
        if blocker.startswith(("stale_", "invalid_")):
            evidence_against.append(
                _audit_item("source_freshness", blocker, "输入数据缺失、过期或格式无效")
            )

    if blocked_by:
        downgrade_reasons.append("存在阻断项，不能建议立即入场")
        forbidden_claims.append("不能建议立即入场")
        forbidden_claims.append("不能声称输入完整且新鲜")

    if alignment != "aligned":
        forbidden_claims.append("不能声称证据完全对齐")

    allowed = _allowed_actions(verdict, blocked_by, alignment)
    return {
        "evidence_for": evidence_for,
        "evidence_against": evidence_against,
        "downgrade_reasons": _dedupe(downgrade_reasons + list(required)),
        "allowed_actions": allowed,
        "forbidden_claims": _dedupe(forbidden_claims),
        "llm_output_contract": {
            "must_include": [
                "final_action",
                "confidence",
                "supporting_evidence",
                "opposing_evidence",
                "downgrade_reasons",
                "human_review_items",
            ],
            "final_action_must_be_one_of": allowed,
            "confidence_ceiling": confidence,
            "narrative_only_upgrade_allowed": False,
        },
    }


def _controller(
    thesis: dict[str, Any],
    factor: dict[str, Any],
    backtest: dict[str, Any],
    execution: dict[str, Any],
    invalid_sources: list[str] | None = None,
    stale_sources: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    blocked_by: list[str] = []
    required: list[str] = []
    for source in invalid_sources or []:
        blocked_by.append(f"invalid_{source}")
        required.append(f"检查 {source} 输入是否为有效 JSON")
    for source in stale_sources or []:
        blocked_by.append(f"stale_{source}")
        required.append(f"刷新 {source} 后再确认")
    if thesis.get("verdict") == "insufficient":
        blocked_by.append("missing_thesis")
        required.append("确认 thesis 是否已刷新")
    if factor.get("factor_quality") in {"unavailable", "weak"}:
        blocked_by.append("weak_or_missing_factor")
        required.append("确认因子证据是否足够")
    if backtest.get("backtest_verdict") in {"unavailable", "reject"}:
        blocked_by.append("missing_or_rejected_backtest")
        required.append("确认回测证据是否可用")
    for warning in warnings or []:
        if warning not in required:
            required.append(warning)

    if blocked_by:
        alignment = "insufficient"
        confidence = 35
    elif (
        thesis.get("verdict") == "supportive"
        and factor.get("factor_quality") == "usable"
        and backtest.get("backtest_verdict") == "supportive"
    ):
        alignment = "aligned"
        confidence = 70
    else:
        alignment = "mixed"
        confidence = 55

    verdict = execution.get("action_state") or "monitor"
    if blocked_by and verdict == "act":
        verdict = "wait"
    if alignment == "mixed":
        summary = "证据存在分歧，需带 caution 执行或人工复核"
    else:
        summary = {
            "act": "证据对齐，可按计划执行",
            "wait": "等待条件确认",
            "monitor": "证据不足，先观察",
            "avoid": "风险或门控不允许，避免交易",
        }.get(verdict, "等待人工确认")
    audit = _controller_audit(
        thesis,
        factor,
        backtest,
        execution,
        blocked_by,
        required,
        alignment,
        confidence,
        verdict,
    )
    return {
        "controller_verdict": verdict,
        "controller_confidence": confidence,
        "evidence_alignment": alignment,
        "required_human_check": required,
        "blocked_by": blocked_by,
        "summary_for_dashboard": summary,
        "audit": audit,
    }


def _visual_notes(
    controller: dict[str, Any], execution: dict[str, Any]
) -> dict[str, Any]:
    action_label = {
        "act": "可入场",
        "wait": "等待",
        "monitor": "观察",
        "avoid": "不入场",
    }.get(controller.get("controller_verdict"), "观察")
    risk_flag = (
        "blocked"
        if controller.get("blocked_by")
        else ("caution" if controller.get("evidence_alignment") != "aligned" else "none")
    )
    return {
        "primary_action": action_label,
        "why_now": [controller.get("summary_for_dashboard")],
        "risk_flag": risk_flag,
        "evidence_alignment": controller.get("evidence_alignment"),
        "missing_inputs": controller.get("blocked_by", []),
        "level_map": {
            "entry": execution.get("entry_zone"),
            "stop": execution.get("stop_level"),
            "target": execution.get("target_zone"),
            "wait": execution.get("wait_conditions", []),
        },
        "review_questions": controller.get("required_human_check", []),
    }


def build_symbol_state(date: str, sym: str, base_dir: str = BASE) -> dict[str, Any]:
    find_dir = os.path.join(base_dir, "findings")
    sym = sym.upper()
    pm_path = _premarket_path(find_dir, date, sym)
    entry_path = _entry_decision_path(find_dir, date)
    premarket, pm_status = _load_json_with_status(pm_path)
    entry_file, entry_status = _load_json_with_status(entry_path)
    credibility, credibility_src = _load_evidence_credibility(find_dir, base_dir)
    if credibility:
        factor = _factor_from_credibility(credibility)
        backtest = _backtest_from_credibility(credibility)
        factor_src = _source_status(
            os.path.join(find_dir, "factor_ic_report.json"), base_dir
        )
        backtest_src = _source_status(
            os.path.join(find_dir, "weekly_oos_validation_results.json"), base_dir
        )
    else:
        factor, factor_src = _extract_factor_evidence(find_dir, base_dir)
        backtest, backtest_src = _extract_backtest_evidence(find_dir, base_dir)
    pm_src = _source_status(pm_path, base_dir, date, load_status=pm_status)
    entry_src = _source_status(entry_path, base_dir, date, load_status=entry_status)
    thesis = _extract_thesis(premarket)
    execution = _extract_execution(sym, premarket, entry_file)
    invalid_sources = []
    if pm_status in {"parse_error", "invalid"}:
        invalid_sources.append("premarket_summary")
    if entry_status in {"parse_error", "invalid"}:
        invalid_sources.append("entry_decision")
    if factor_src.get("status") in {"parse_error", "invalid"}:
        invalid_sources.append("factor_ic_report")
    if backtest_src.get("status") in {"parse_error", "invalid"}:
        invalid_sources.append("weekly_oos")
    stale_sources = []
    if pm_src.get("status") == "stale":
        stale_sources.append("premarket_summary")
    if entry_src.get("status") == "stale":
        stale_sources.append("entry_decision")
    credibility_warnings = []
    if credibility:
        overrides = (
            credibility.get("decision_state_overrides")
            if isinstance(credibility.get("decision_state_overrides"), dict)
            else {}
        )
        warnings = overrides.get("required_warnings")
        if isinstance(warnings, list):
            credibility_warnings = [str(warning) for warning in warnings]
    controller = _controller(
        thesis,
        factor,
        backtest,
        execution,
        invalid_sources,
        stale_sources,
        credibility_warnings,
    )
    visual = _visual_notes(controller, execution)
    market_context = (
        premarket.get("market_context")
        if isinstance(premarket.get("market_context"), dict)
        else {}
    )
    return {
        "identity": {
            "symbol": sym,
            "date": date,
            "market_phase": market_context.get("phase")
            or premarket.get("market_phase")
            or "unknown",
            "track": premarket.get("track") or "swing",
            "source_freshness": {
                "premarket_summary": pm_src,
                "entry_decision": entry_src,
                "evidence_credibility_report": credibility_src,
                "factor_ic_report": factor_src,
                "weekly_oos": backtest_src,
            },
        },
        "thesis": thesis,
        "factor_evidence": factor,
        "backtest_evidence": backtest,
        "execution": execution,
        "controller": controller,
        "visual_notes": visual,
    }


def _discover_symbols(date: str, base_dir: str = BASE) -> list[str]:
    find_dir = os.path.join(base_dir, "findings")
    symbols: set[str] = set()
    for path in glob.glob(os.path.join(find_dir, f"premarket_summary_{date}_*.json")):
        name = os.path.basename(path)
        sym = name.removeprefix(f"premarket_summary_{date}_").removesuffix(".json")
        if sym:
            symbols.add(sym.upper())
    for path in glob.glob(
        os.path.join(find_dir, "symbols", "*", "plans", f"premarket_summary_{date}.json")
    ):
        sym = os.path.basename(os.path.dirname(os.path.dirname(path)))
        if sym:
            symbols.add(sym.upper())
    if not symbols:
        for path in glob.glob(os.path.join(find_dir, "premarket_summary_*_*.json")):
            name = os.path.basename(path).removesuffix(".json")
            sym = name.rsplit("_", 1)[-1]
            if sym:
                symbols.add(sym.upper())
        for path in glob.glob(
            os.path.join(find_dir, "symbols", "*", "plans", "premarket_summary_*.json")
        ):
            sym = os.path.basename(os.path.dirname(os.path.dirname(path)))
            if sym:
                symbols.add(sym.upper())
    entry = _load_json(_entry_decision_path(find_dir, date))
    decisions = entry.get("decisions")
    if isinstance(decisions, dict):
        symbols.update(str(sym).upper() for sym in decisions)
    else:
        symbols.update(
            str(sym).upper()
            for sym, value in entry.items()
            if sym != "date" and isinstance(value, dict)
        )
    return sorted(symbols)


def build_decision_state(
    date: str, symbols: list[str] | None = None, base_dir: str = BASE
) -> dict[str, Any]:
    chosen = [sym.upper() for sym in symbols] if symbols else _discover_symbols(date, base_dir)
    return {
        "date": date,
        "generated_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "symbols": {
            sym: build_symbol_state(date, sym, base_dir=base_dir) for sym in chosen
        },
    }


def write_decision_state(
    date: str, symbols: list[str] | None = None, base_dir: str = BASE
) -> str:
    payload = build_decision_state(date=date, symbols=symbols, base_dir=base_dir)
    out_dir = os.path.join(base_dir, "findings")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"decision_state_{date}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build daily per-symbol decision state.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--base-dir", default=BASE)
    parser.add_argument("symbols", nargs="*")
    args = parser.parse_args(argv)
    out_path = write_decision_state(args.date, args.symbols or None, base_dir=args.base_dir)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
