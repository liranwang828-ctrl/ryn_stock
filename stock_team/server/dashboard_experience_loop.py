from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from jinja2 import Environment, FileSystemLoader

from stock_team.server.dashboard_experience_paths import (
    EXPERIENCE_PATHS,
    MAX_FIXES_PER_ROUND,
    MAX_HIGH_PRIORITY_ISSUES,
    PROTECTED_SCOPE_TOKENS,
    path_ids,
)
from stock_team.server.dashboard_writer import build_dashboard_context, build_dashboard_route_snapshot


KNOWN_PATH_IDS = set(path_ids())
KNOWN_SEVERITIES = {"high", "medium", "low"}
KNOWN_RECHECK_STATUS = {"improved", "unchanged", "regressed"}
REPO_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX_TARGETS = {
    "path_a_premarket_orientation": {
        "files_touched": [
            "agents/dashboard_writer.py",
            "templates/daily_dashboard.html.j2",
        ],
        "strategy": "derive_or_render_next_action",
    },
    "path_b_premarket_readiness": {
        "files_touched": [
            "agents/dashboard_writer.py",
            "templates/daily_dashboard.html.j2",
        ],
        "strategy": "promote_focus_readiness",
    },
    "path_c_symbol_action": {
        "files_touched": [
            "templates/daily_dashboard.html.j2",
        ],
        "strategy": "tighten_intraday_action_visibility",
    },
    "path_d_return_to_global": {
        "files_touched": [
            "templates/daily_dashboard.html.j2",
        ],
        "strategy": "stabilize_global_navigation",
    },
}


@dataclass(frozen=True)
class ExperienceIssue:
    page_module: str
    task_path: str
    problem: str
    why_it_hurts: str
    severity: str
    suggested_direction: str


def build_issue(**kwargs: Any) -> dict[str, Any]:
    issue = ExperienceIssue(**kwargs)
    if issue.task_path not in KNOWN_PATH_IDS:
        raise ValueError(f"unknown task path: {issue.task_path}")
    if issue.severity not in KNOWN_SEVERITIES:
        raise ValueError(f"unknown severity: {issue.severity}")
    return asdict(issue)


def build_recheck_result(task_path: str, status: str, before_problem: str, after_observation: str) -> dict[str, str]:
    if task_path not in KNOWN_PATH_IDS:
        raise ValueError(f"unknown task path: {task_path}")
    if status not in KNOWN_RECHECK_STATUS:
        raise ValueError(f"unknown recheck status: {status}")
    return {
        "task_path": task_path,
        "status": status,
        "before_problem": before_problem,
        "after_observation": after_observation,
    }


def validate_round_payload(payload: dict[str, Any]) -> dict[str, Any]:
    issues = payload.get("issues") or []
    implemented_fixes = payload.get("implemented_fixes") or []
    high_count = sum(1 for issue in issues if issue.get("severity") == "high")
    if high_count > MAX_HIGH_PRIORITY_ISSUES:
        raise ValueError("at most 3 high-priority issues are allowed per round")
    if len(implemented_fixes) > MAX_FIXES_PER_ROUND:
        raise ValueError("at most 2 implemented fixes are allowed per round")
    return payload


def bootstrap_experience_round(date_str: str, base_dir: str) -> str:
    ctx = build_dashboard_context(date_str, base_dir=base_dir)
    route_snapshot = build_dashboard_route_snapshot(ctx)
    focus_symbols = list(ctx.get("focus_list") or ctx.get("symbols") or [])
    report_status = ctx.get("report_status") or {}
    payload = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dashboard_route_snapshot": route_snapshot,
        "focus_symbols": focus_symbols,
        "focus_status": {
            sym: report_status.get(sym, {})
            for sym in focus_symbols
        },
        "task_paths": [
            {
                "id": path.id,
                "title": path.title,
                "goal": path.goal,
                "entry_hint": path.entry_hint,
                "success_signal": path.success_signal,
            }
            for path in EXPERIENCE_PATHS
        ],
        "protected_scope": {
            "forbidden_tokens": list(PROTECTED_SCOPE_TOKENS),
        },
    }
    out_dir = os.path.join(base_dir, "findings", "dashboard_experience", date_str)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "round_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


def write_round_summary(
    *,
    base_dir: str,
    date_str: str,
    issues: list[dict],
    implemented_fixes: list[dict],
    recheck: list[dict],
) -> str:
    payload = validate_round_payload({
        "issues": issues,
        "implemented_fixes": implemented_fixes,
        "recheck": recheck,
    })
    payload["issue_count"] = len(issues)
    payload["implemented_fix_count"] = len(implemented_fixes)
    payload["recheck_count"] = len(recheck)
    out_dir = os.path.join(base_dir, "findings", "dashboard_experience", date_str)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "round_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


def _render_review_html(date_str: str, base_dir: str) -> str:
    ctx = build_dashboard_context(date_str, base_dir=base_dir)
    env = Environment(
        loader=FileSystemLoader(os.path.join(REPO_BASE, "templates")),
        autoescape=False,
    )
    html = env.get_template("daily_dashboard.html.j2").render(**ctx)
    out_dir = os.path.join(base_dir, "findings", "dashboard_experience", date_str)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "review_dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def _issue_payload_path(base_dir: str, date_str: str) -> str:
    out_dir = os.path.join(base_dir, "findings", "dashboard_experience", date_str)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, "auto_issues.json")


def _review_issues_from_manifest(manifest: dict[str, Any], html: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    focus_symbols = manifest.get("focus_symbols") or []
    route_snapshot = manifest.get("dashboard_route_snapshot") or {}
    focus_status = manifest.get("focus_status") or {}

    if 'id="tab-overview"' not in html or 'id="market-clock-phase"' not in html:
        issues.append(build_issue(
            page_module="Overview Header",
            task_path="path_a_premarket_orientation",
            problem="Landing view does not clearly expose market phase anchors.",
            why_it_hurts="Premarket orientation becomes guesswork at the first screen.",
            severity="high",
            suggested_direction="Keep the market phase badge and overview entry visible in the first viewport.",
        ))
    elif route_snapshot.get("phase_label") in (None, "", "unknown"):
        issues.append(build_issue(
            page_module="Overview Header",
            task_path="path_a_premarket_orientation",
            problem="Route snapshot cannot determine the current phase.",
            why_it_hurts="The experience loop cannot judge the right next action.",
            severity="medium",
            suggested_direction="Backfill a stable phase label from session state or market clock.",
        ))
    if not route_snapshot.get("has_next_action"):
        issues.append(build_issue(
            page_module="Overview Action Center",
            task_path="path_a_premarket_orientation",
            problem="No explicit next action is available in the landing context snapshot.",
            why_it_hurts="User cannot immediately tell what to do next when opening the dashboard.",
            severity="high",
            suggested_direction="Surface a compact phase-aware next-action block in the first viewport.",
        ))

    if not focus_symbols:
        issues.append(build_issue(
            page_module="Today's Focus Table",
            task_path="path_b_premarket_readiness",
            problem="No focus symbols are available for readiness review.",
            why_it_hurts="The premarket-to-intraday flow has no primary symbol to inspect.",
            severity="high",
            suggested_direction="Promote at least one focus source before the workflow continues.",
        ))
    elif 'id="manual-focus-input"' not in html:
        issues.append(build_issue(
            page_module="Today's Focus Table",
            task_path="path_b_premarket_readiness",
            problem="Focus readiness panel is missing its direct input control.",
            why_it_hurts="User cannot quickly reconcile focus changes from agent chat or manual edits.",
            severity="medium",
            suggested_direction="Keep a visible direct-add control in the focus area.",
        ))
    if focus_symbols and 'id="focus-priority-strip"' not in html:
        issues.append(build_issue(
            page_module="Today's Focus Table",
            task_path="path_b_premarket_readiness",
            problem="Focus readiness view is missing a clear priority summary for who to monitor first.",
            why_it_hurts="User still has to scan the whole focus table before knowing the first symbol to watch.",
            severity="high",
            suggested_direction="Promote one lead focus cue with a direct drilldown action into intraday review.",
        ))
    if focus_symbols and not any(
        (status or {}).get("today_state") == "ready" or (status or {}).get("trade_plan_state") == "today"
        for status in focus_status.values()
    ) and "今日待刷新" not in html and "今日已就绪" not in html:
        issues.append(build_issue(
            page_module="Today's Focus Table",
            task_path="path_b_premarket_readiness",
            problem="Focus symbols exist but none are marked ready for today's workflow.",
            why_it_hurts="User cannot distinguish which focus symbols can move directly into intraday execution.",
            severity="high",
            suggested_direction="Promote readiness state so at least one focus symbol is clearly actionable or clearly pending refresh.",
        ))

    if focus_symbols:
        lead = str(focus_symbols[0]).upper()
        has_intraday_tab = 'id="tab-intraday"' in html
        has_intraday_card = f'id="intraday-symbol-card-{lead}"' in html
        has_drilldown = f'id="focus-drilldown-{lead}"' in html and f"openIntradaySymbol('{lead}')" in html
        if (not has_intraday_tab) or (not has_intraday_card) or (not has_drilldown):
            issues.append(build_issue(
                page_module="Intraday Detail",
                task_path="path_c_symbol_action",
                problem="Lead focus symbol is missing a direct drilldown path into the intraday action card.",
                why_it_hurts="The flow breaks when moving from premarket focus into intraday execution context.",
                severity="high",
                suggested_direction="Expose a one-click jump from the focus row into the matching intraday symbol card.",
            ))

        has_return_hook = f'id="intraday-return-{lead}"' in html and f"returnToOverviewFocus('{lead}')" in html
        has_overview_target = f'id="focus-row-{lead}"' in html or 'id="focus-readiness-panel"' in html
        if not has_return_hook or not has_overview_target:
            issues.append(build_issue(
                page_module="Global Navigation",
                task_path="path_d_return_to_global",
                problem="Symbol detail is missing a clear path back to the overview monitoring context.",
                why_it_hurts="Returning from a symbol detail to the global monitoring view is ambiguous.",
                severity="medium",
                suggested_direction="Provide an explicit return-to-overview control that lands near the focus queue.",
            ))

    elif "showTab('overview'" not in html or "showTab('intraday'" not in html:
        issues.append(build_issue(
            page_module="Global Navigation",
            task_path="path_d_return_to_global",
            problem="Overview and intraday tab switching hooks are incomplete.",
            why_it_hurts="Returning from a symbol detail to the global monitoring view is ambiguous.",
            severity="medium",
            suggested_direction="Keep explicit overview/intraday tab affordances stable.",
        ))

    return issues


def auto_review_experience_round(date_str: str, base_dir: str) -> dict[str, str]:
    manifest_path = bootstrap_experience_round(date_str, base_dir)
    html_path = _render_review_html(date_str, base_dir)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    issues = _review_issues_from_manifest(manifest, html)
    payload = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checked_path_count": len(manifest.get("task_paths") or []),
        "issues": issues,
    }
    issues_path = _issue_payload_path(base_dir, date_str)
    with open(issues_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return {
        "manifest_path": manifest_path,
        "html_path": html_path,
        "issues_path": issues_path,
    }


def propose_fix_batch(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    ranked = sorted(
        issues,
        key=lambda issue: (
            severity_rank.get(issue.get("severity", "low"), 99),
            issue.get("task_path", ""),
        ),
    )
    batch: list[dict[str, Any]] = []
    for issue in ranked:
        target = FIX_TARGETS.get(issue.get("task_path"))
        if not target:
            continue
        batch.append({
            "task_path": issue.get("task_path"),
            "problem": issue.get("problem"),
            "strategy": target["strategy"],
            "files_touched": list(target["files_touched"]),
        })
        if len(batch) >= MAX_FIXES_PER_ROUND:
            break
    return batch
