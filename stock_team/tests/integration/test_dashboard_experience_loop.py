import sys
import os
import json

import pytest

from stock_team.server.dashboard_experience_loop import (
    _review_issues_from_manifest,
    auto_review_experience_round,
    bootstrap_experience_round,
    build_issue,
    build_recheck_result,
    propose_fix_batch,
    validate_round_payload,
    write_round_summary,
)


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_build_issue_requires_known_path_and_severity():
    issue = build_issue(
        page_module="Today Focus",
        task_path="path_b_premarket_readiness",
        problem="Next action is hidden behind multiple status chips.",
        why_it_hurts="User cannot tell which symbol is ready first.",
        severity="high",
        suggested_direction="Promote one primary action block.",
    )
    assert issue["severity"] == "high"
    assert issue["task_path"] == "path_b_premarket_readiness"


def test_validate_round_payload_rejects_too_many_high_priority_issues():
    with pytest.raises(ValueError, match="at most 3 high-priority issues"):
        validate_round_payload({
            "issues": [
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "high"},
            ],
            "implemented_fixes": [],
        })


def test_build_recheck_result_keeps_same_path_and_resolution_state():
    result = build_recheck_result(
        task_path="path_c_symbol_action",
        status="improved",
        before_problem="Action block was buried below dense metrics.",
        after_observation="Action block is visible in the first viewport.",
    )
    assert result["task_path"] == "path_c_symbol_action"
    assert result["status"] == "improved"


def test_bootstrap_experience_round_writes_manifest_from_dashboard_context(tmp_path):
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NOW", "NVDA"]})

    manifest_path = bootstrap_experience_round("2026-05-31", str(base))
    manifest = json.loads(open(manifest_path, encoding="utf-8").read())

    assert manifest["date"] == "2026-05-31"
    assert manifest["task_paths"][0]["id"] == "path_a_premarket_orientation"
    assert manifest["focus_symbols"] == ["NOW", "NVDA"]
    assert manifest["protected_scope"]["forbidden_tokens"][0] == "backtest"


def test_write_round_summary_persists_issue_fix_and_recheck_sections(tmp_path):
    summary_path = write_round_summary(
        base_dir=str(tmp_path),
        date_str="2026-05-31",
        issues=[{
            "page_module": "Today Focus",
            "task_path": "path_b_premarket_readiness",
            "problem": "Status chips dominate the ready signal.",
            "why_it_hurts": "Primary symbol is unclear.",
            "severity": "high",
            "suggested_direction": "Promote the primary ready action.",
        }],
        implemented_fixes=[{
            "title": "Promote ready action block",
            "files_touched": ["templates/daily_dashboard.html.j2"],
        }],
        recheck=[{
            "task_path": "path_b_premarket_readiness",
            "status": "improved",
            "before_problem": "Primary symbol was unclear.",
            "after_observation": "Primary symbol is visible without scanning secondary chips.",
        }],
    )
    payload = json.loads(open(summary_path, encoding="utf-8").read())
    assert payload["issue_count"] == 1
    assert payload["implemented_fix_count"] == 1
    assert payload["recheck"][0]["status"] == "improved"


def test_auto_review_experience_round_writes_issue_list_and_review_html(tmp_path):
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NOW"]})

    result = auto_review_experience_round("2026-05-31", str(base))

    assert os.path.exists(result["manifest_path"])
    assert os.path.exists(result["html_path"])
    assert os.path.exists(result["issues_path"])
    payload = json.loads(open(result["issues_path"], encoding="utf-8").read())
    assert payload["checked_path_count"] == 4
    assert isinstance(payload["issues"], list)


def test_auto_review_experience_round_flags_missing_focus_as_high_priority(tmp_path):
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": []})

    result = auto_review_experience_round("2026-05-31", str(base))
    payload = json.loads(open(result["issues_path"], encoding="utf-8").read())

    assert any(
        issue["task_path"] == "path_b_premarket_readiness" and issue["severity"] == "high"
        for issue in payload["issues"]
    )


def test_propose_fix_batch_limits_to_two_items_and_maps_targets():
    issues = [
        build_issue(
            page_module="Overview Action Center",
            task_path="path_a_premarket_orientation",
            problem="No explicit next action is available in the landing context snapshot.",
            why_it_hurts="User cannot immediately tell what to do next when opening the dashboard.",
            severity="high",
            suggested_direction="Surface a compact phase-aware next-action block in the first viewport.",
        ),
        build_issue(
            page_module="Today's Focus Table",
            task_path="path_b_premarket_readiness",
            problem="Focus symbols exist but none are marked ready for today's workflow.",
            why_it_hurts="User cannot distinguish which focus symbols can move directly into intraday execution.",
            severity="high",
            suggested_direction="Promote readiness state so at least one focus symbol is clearly actionable or clearly pending refresh.",
        ),
        build_issue(
            page_module="Global Navigation",
            task_path="path_d_return_to_global",
            problem="Overview and intraday tab switching hooks are incomplete.",
            why_it_hurts="Returning from a symbol detail to the global monitoring view is ambiguous.",
            severity="medium",
            suggested_direction="Keep explicit overview/intraday tab affordances stable.",
        ),
    ]

    batch = propose_fix_batch(issues)

    assert len(batch) == 2
    assert batch[0]["task_path"] == "path_a_premarket_orientation"
    assert "templates/daily_dashboard.html.j2" in batch[0]["files_touched"]


def test_review_issues_flags_missing_focus_drilldown_for_lead_symbol():
    manifest = {
        "focus_symbols": ["NOW"],
        "focus_status": {"NOW": {"today_state": "ready", "trade_plan_state": "today"}},
        "dashboard_route_snapshot": {"phase_label": "premarket", "has_next_action": True},
    }
    html = """
    <div id="tab-overview"></div>
    <span id="market-clock-phase">盘前</span>
    <input id="manual-focus-input" />
    <div id="tab-intraday"></div>
    <div class="intraday-card-body">NOW</div>
    <button onclick="showTab('overview')"></button>
    <button onclick="showTab('intraday')"></button>
    """

    issues = _review_issues_from_manifest(manifest, html)

    assert any(
        issue["task_path"] == "path_c_symbol_action" and issue["severity"] == "high"
        for issue in issues
    )


def test_review_issues_flags_missing_return_to_global_hook():
    manifest = {
        "focus_symbols": ["NOW"],
        "focus_status": {"NOW": {"today_state": "ready", "trade_plan_state": "today"}},
        "dashboard_route_snapshot": {"phase_label": "regular", "has_next_action": True},
    }
    html = """
    <div id="tab-overview"></div>
    <span id="market-clock-phase">盘中</span>
    <input id="manual-focus-input" />
    <div id="tab-intraday"></div>
    <div class="intraday-card-body">NOW</div>
    <button id="focus-drilldown-NOW" onclick="openIntradaySymbol('NOW')"></button>
    <div id="intraday-symbol-card-NOW"></div>
    <button onclick="showTab('overview')"></button>
    <button onclick="showTab('intraday')"></button>
    """

    issues = _review_issues_from_manifest(manifest, html)

    assert any(
        issue["task_path"] == "path_d_return_to_global" and issue["severity"] == "medium"
        for issue in issues
    )


def test_review_issues_flags_missing_focus_priority_summary():
    manifest = {
        "focus_symbols": ["NOW", "NVDA"],
        "focus_status": {
            "NOW": {"today_state": "ready", "trade_plan_state": "today"},
            "NVDA": {"today_state": "needs_refresh", "trade_plan_state": "historical"},
        },
        "dashboard_route_snapshot": {"phase_label": "premarket", "has_next_action": True},
    }
    html = """
    <div id="tab-overview"></div>
    <span id="market-clock-phase">盘前</span>
    <input id="manual-focus-input" />
    <div id="focus-readiness-panel"></div>
    <div id="tab-intraday"></div>
    <div id="intraday-symbol-card-NOW"></div>
    <button id="focus-drilldown-NOW" onclick="openIntradaySymbol('NOW')"></button>
    <button id="intraday-return-NOW" onclick="returnToOverviewFocus('NOW')"></button>
    <button onclick="showTab('overview')"></button>
    <button onclick="showTab('intraday')"></button>
    """

    issues = _review_issues_from_manifest(manifest, html)

    assert any(
        issue["task_path"] == "path_b_premarket_readiness"
        and "priority" in issue["problem"].lower()
        for issue in issues
    )


def test_bootstrap_experience_round_prefers_focus_list_over_broader_symbol_set(tmp_path):
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {
        "positions": {"COHR": {}, "NOW": {}, "VST": {}},
        "_excluded": [],
    })
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": ["COHR", "NOW", "VST"]})
    _write(str(base / "config" / "daily_focus.json"), {"focus_stocks": ["NOW", "VST"]})

    manifest_path = bootstrap_experience_round("2026-05-31", str(base))
    manifest = json.loads(open(manifest_path, encoding="utf-8").read())

    assert manifest["focus_symbols"] == ["NOW", "VST"]
