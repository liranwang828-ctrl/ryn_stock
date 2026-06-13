# LLM Controller Discipline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic controller audit contract to `decision_state_{date}.json` so future LLM controller output is constrained by evidence, downgrade reasons, allowed actions, and forbidden claims.

**Architecture:** Extend the existing Decision State Hub controller output with an additive `controller.audit` object. Keep all current controller fields intact, derive audit fields from existing thesis/factor/backtest/execution/source status inputs, and cover behavior with focused unit tests before implementation.

**Tech Stack:** Python stdlib, pytest, existing `agents/decision_state_hub.py`, existing `tests/test_decision_state_hub.py`.

---

## 中文摘要

本计划实现 **LLM 主控纪律层** 的第一阶段：不接真实 LLM，不改交易规则，不改回测引擎，只在现有 `controller` 里新增 `audit` 字段。

实现后，每只股票的 `decision_state_{date}.json` 会保留原有字段，并新增：

- `controller.audit.evidence_for`
- `controller.audit.evidence_against`
- `controller.audit.downgrade_reasons`
- `controller.audit.allowed_actions`
- `controller.audit.forbidden_claims`
- `controller.audit.llm_output_contract`

这层字段用于约束未来真实 LLM 主控：它不能把 caution 回测说成 fully validated，不能把样本不足因子说成强信号，不能在 `allowed_actions` 不包含 `act` 时建议入场。

## File Structure

| File | Change | Responsibility |
| --- | --- | --- |
| `tests/test_decision_state_hub.py` | Modify | Add tests for controller audit behavior, allowed actions, forbidden claims, and LLM output contract. |
| `agents/decision_state_hub.py` | Modify | Add deterministic audit construction inside controller logic while preserving existing output fields. |
| `docs/superpowers/plans/2026-06-01-llm-controller-discipline.md` | Create | This implementation handoff plan. |

No new production module is needed. The first implementation should keep the audit builder close to `_controller()` because it depends on the same evidence inputs and should remain easy to inspect.

## Contract To Implement

`controller` keeps existing fields and gains:

```json
{
  "audit": {
    "evidence_for": [
      {"source": "thesis", "status": "supportive", "detail": "个股 thesis 可用"}
    ],
    "evidence_against": [
      {"source": "backtest", "status": "caution", "detail": "回测证据需要谨慎"}
    ],
    "downgrade_reasons": [
      "回测证据为 caution，不能声称完全验证"
    ],
    "allowed_actions": ["wait", "monitor", "avoid"],
    "forbidden_claims": [
      "不能声称证据完全对齐",
      "不能把 caution 回测称为 fully validated",
      "不能建议立即入场"
    ],
    "llm_output_contract": {
      "must_include": [
        "final_action",
        "confidence",
        "supporting_evidence",
        "opposing_evidence",
        "downgrade_reasons",
        "human_review_items"
      ],
      "final_action_must_be_one_of": ["wait", "monitor", "avoid"],
      "confidence_ceiling": 55,
      "narrative_only_upgrade_allowed": false
    }
  }
}
```

## Task 1: Add Audit Tests For Supportive Evidence

**Files:**
- Modify: `tests/test_decision_state_hub.py`

- [ ] **Step 1: Add the failing test**

Append this test to `tests/test_decision_state_hub.py`:

```python
def test_controller_audit_allows_act_when_evidence_aligned(tmp_path):
    from agents.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
            "entry": {"entry_base": 100.0},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )
    _write_json(
        findings / "evidence_credibility_report.json",
        {
            "factor_credibility": {
                "overall_verdict": "usable",
                "factors": {
                    "5. Volatility (20d)": {"tier": "robust", "weeks_count": 109}
                },
            },
            "backtest_credibility": {
                "overall_verdict": "supportive",
                "time_oos": {"verdict": "supportive", "alpha": 15.94},
                "style_oos": {"verdict": "supportive", "alpha": 4.2},
                "full_lifecycle": {"verdict": "supportive"},
                "parameter_stability": {"tier": "usable"},
                "notes": [],
            },
            "decision_state_overrides": {
                "factor_quality": "usable",
                "backtest_verdict": "supportive",
                "required_warnings": [],
            },
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    audit = state["symbols"]["NVDA"]["controller"]["audit"]

    assert "act" in audit["allowed_actions"]
    assert audit["llm_output_contract"]["final_action_must_be_one_of"] == audit["allowed_actions"]
    assert audit["llm_output_contract"]["confidence_ceiling"] == 70
    assert not any("不能建议立即入场" in claim for claim in audit["forbidden_claims"])
    assert any(item["source"] == "thesis" for item in audit["evidence_for"])
    assert any(item["source"] == "factor" for item in audit["evidence_for"])
    assert any(item["source"] == "backtest" for item in audit["evidence_for"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_controller_audit_allows_act_when_evidence_aligned -q
```

Expected: fails with `KeyError: 'audit'`.

- [ ] **Step 3: Commit the failing test is not committed yet**

Do not commit after the red step. Continue to Task 2.

## Task 2: Implement Minimal Audit Builder For Aligned Evidence

**Files:**
- Modify: `agents/decision_state_hub.py`
- Test: `tests/test_decision_state_hub.py`

- [ ] **Step 1: Add helper functions near `_controller()`**

In `agents/decision_state_hub.py`, add these helpers before `_controller()`:

```python
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
```

- [ ] **Step 2: Add a first audit builder**

Add this helper before `_controller()`:

```python
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
```

- [ ] **Step 3: Attach audit in `_controller()` return**

In `_controller()`, after `summary` is assigned and before `return`, add:

```python
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
```

Then add `"audit": audit` to the returned dictionary:

```python
        "audit": audit,
```

- [ ] **Step 4: Run the aligned audit test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_controller_audit_allows_act_when_evidence_aligned -q
```

Expected: passes.

- [ ] **Step 5: Run existing decision state tests**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py -q
```

Expected: all current tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add agents\decision_state_hub.py tests\test_decision_state_hub.py
git commit -m "feat: add controller audit contract"
```

## Task 3: Add Tests For Backtest Caution Discipline

**Files:**
- Modify: `tests/test_decision_state_hub.py`
- Modify: `agents/decision_state_hub.py`

- [ ] **Step 1: Add the failing caution test**

Append this test to `tests/test_decision_state_hub.py`:

```python
def test_controller_audit_blocks_act_when_backtest_is_caution(tmp_path):
    from agents.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )
    _write_json(
        findings / "evidence_credibility_report.json",
        {
            "factor_credibility": {
                "overall_verdict": "usable",
                "factors": {
                    "5. Volatility (20d)": {"tier": "robust", "weeks_count": 109}
                },
            },
            "backtest_credibility": {
                "overall_verdict": "caution",
                "time_oos": {"verdict": "supportive", "alpha": 15.94},
                "style_oos": {"verdict": "caution", "alpha": -23.64},
                "full_lifecycle": {"verdict": "supportive"},
                "parameter_stability": {"tier": "usable"},
                "notes": ["style-OOS alpha 为负，LLM 和 dashboard 必须显式提示"],
            },
            "decision_state_overrides": {
                "factor_quality": "usable",
                "backtest_verdict": "caution",
                "required_warnings": ["Style-OOS alpha 为负"],
            },
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    controller = state["symbols"]["NVDA"]["controller"]
    audit = controller["audit"]

    assert controller["evidence_alignment"] == "mixed"
    assert "act" not in audit["allowed_actions"]
    assert audit["llm_output_contract"]["final_action_must_be_one_of"] == audit["allowed_actions"]
    assert audit["llm_output_contract"]["confidence_ceiling"] == controller["controller_confidence"]
    assert any(item["source"] == "backtest" and item["status"] == "caution" for item in audit["evidence_against"])
    assert any("caution" in reason for reason in audit["downgrade_reasons"])
    assert any("fully validated" in claim for claim in audit["forbidden_claims"])
    assert any("证据完全对齐" in claim for claim in audit["forbidden_claims"])
```

- [ ] **Step 2: Run the caution test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_controller_audit_blocks_act_when_backtest_is_caution -q
```

Expected: passes if Task 2 already handles caution. If it fails because `controller_verdict` remains `act`, continue to Step 3.

- [ ] **Step 3: Tighten controller verdict for mixed evidence**

If needed, in `_controller()` after the existing downgrade for `blocked_by`, add:

```python
    if alignment == "mixed" and verdict == "act":
        verdict = "wait"
```

This makes the main controller verdict match the audit discipline: caution/mixed evidence cannot remain an immediate `act` verdict.

- [ ] **Step 4: Re-run the caution test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_controller_audit_blocks_act_when_backtest_is_caution -q
```

Expected: passes.

- [ ] **Step 5: Run existing backtest caution test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_backtest_caution_summary_does_not_claim_aligned_evidence -q
```

Expected: passes and still avoids the phrase `证据对齐`.

- [ ] **Step 6: Commit**

Run:

```powershell
git add agents\decision_state_hub.py tests\test_decision_state_hub.py
git commit -m "fix: block act when controller evidence is mixed"
```

## Task 4: Add Tests For Stale And Missing Input Discipline

**Files:**
- Modify: `tests/test_decision_state_hub.py`
- Modify: `agents/decision_state_hub.py`

- [ ] **Step 1: Add the failing stale test**

Append this test to `tests/test_decision_state_hub.py`:

```python
def test_controller_audit_records_stale_input_discipline(tmp_path):
    from agents.decision_state_hub import build_decision_state

    findings = tmp_path / "findings"
    _write_json(
        findings / "symbols" / "NVDA" / "plans" / "premarket_summary_2026-05-31.json",
        {
            "symbol": "NVDA",
            "date": "2026-05-31",
            "thesis": {"base_thesis": "Yesterday thesis should not look fresh"},
        },
    )
    _write_json(
        findings / "entry_decision_2026-06-01.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )

    state = build_decision_state(date="2026-06-01", symbols=["NVDA"], base_dir=str(tmp_path))
    controller = state["symbols"]["NVDA"]["controller"]
    audit = controller["audit"]

    assert "stale_premarket_summary" in controller["blocked_by"]
    assert "act" not in audit["allowed_actions"]
    assert any(item["source"] == "source_freshness" for item in audit["evidence_against"])
    assert any("刷新 premarket_summary" in reason for reason in audit["downgrade_reasons"])
    assert any("不能建议立即入场" in claim for claim in audit["forbidden_claims"])
    assert any("输入完整且新鲜" in claim for claim in audit["forbidden_claims"])
```

- [ ] **Step 2: Run the stale test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_controller_audit_records_stale_input_discipline -q
```

Expected: may fail because source freshness blockers are only in `downgrade_reasons`, not `evidence_against`.

- [ ] **Step 3: Add source freshness audit items**

In `_controller_audit()`, after evaluating backtest and before `if blocked_by:`, add:

```python
    for blocker in blocked_by:
        if blocker.startswith(("stale_", "invalid_")):
            evidence_against.append(
                _audit_item("source_freshness", blocker, "输入数据缺失、过期或格式无效")
            )
```

- [ ] **Step 4: Re-run stale test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_controller_audit_records_stale_input_discipline -q
```

Expected: passes.

- [ ] **Step 5: Run missing sources test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_missing_sources_emit_valid_monitor_state tests\test_decision_state_hub.py::test_controller_downgrades_action_when_evidence_missing -q
```

Expected: both pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add agents\decision_state_hub.py tests\test_decision_state_hub.py
git commit -m "test: cover stale controller audit discipline"
```

## Task 5: Add Tests For Sample-Insufficient Factor Discipline

**Files:**
- Modify: `tests/test_decision_state_hub.py`
- Modify: `agents/decision_state_hub.py`

- [ ] **Step 1: Add the failing insufficient factor test**

Append this test to `tests/test_decision_state_hub.py`:

```python
def test_controller_audit_records_insufficient_factor_samples(tmp_path):
    from agents.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )
    _write_json(
        findings / "evidence_credibility_report.json",
        {
            "factor_credibility": {
                "overall_verdict": "insufficient",
                "factors": {
                    "6. Sentiment Catalyst": {
                        "tier": "insufficient",
                        "weeks_count": 2,
                        "notes": ["样本只有 2 周，禁止作为强证据"],
                    }
                },
            },
            "backtest_credibility": {
                "overall_verdict": "supportive",
                "time_oos": {"verdict": "supportive", "alpha": 15.94},
                "style_oos": {"verdict": "supportive", "alpha": 4.2},
                "full_lifecycle": {"verdict": "supportive"},
                "parameter_stability": {"tier": "usable"},
                "notes": [],
            },
            "decision_state_overrides": {
                "factor_quality": "insufficient",
                "backtest_verdict": "supportive",
                "required_warnings": ["6. Sentiment Catalyst 样本不足"],
            },
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    audit = state["symbols"]["NVDA"]["controller"]["audit"]

    assert "act" not in audit["allowed_actions"]
    assert any(item["source"] == "factor" and item["status"] == "insufficient" for item in audit["evidence_against"])
    assert any("样本不足" in reason for reason in audit["downgrade_reasons"])
    assert any("样本不足因子" in claim for claim in audit["forbidden_claims"])
    assert audit["llm_output_contract"]["narrative_only_upgrade_allowed"] is False
```

- [ ] **Step 2: Run the insufficient factor test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_controller_audit_records_insufficient_factor_samples -q
```

Expected: passes if Task 2 already includes factor quality and required warnings. If it fails on exact wording, continue to Step 3.

- [ ] **Step 3: Tighten factor forbidden claim wording**

In `_controller_audit()`, ensure the factor failure branch includes this exact claim:

```python
        forbidden_claims.append("不能把弱因子或样本不足因子说成强信号")
```

The implementation in Task 2 already includes this line. If a wording drift occurred, restore it.

- [ ] **Step 4: Re-run the insufficient factor test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_controller_audit_records_insufficient_factor_samples -q
```

Expected: passes.

- [ ] **Step 5: Commit**

Run:

```powershell
git add agents\decision_state_hub.py tests\test_decision_state_hub.py
git commit -m "test: cover insufficient factor audit discipline"
```

## Task 6: Verify Dashboard-Safe Visual Notes Still Work

**Files:**
- Modify: `tests/test_decision_state_hub.py`
- Modify: `agents/decision_state_hub.py`

- [ ] **Step 1: Add a compatibility test for visual notes**

Append this test to `tests/test_decision_state_hub.py`:

```python
def test_visual_notes_remain_dashboard_safe_with_audit(tmp_path):
    from agents.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
            "entry": {"entry_base": 100.0},
            "exit": {"hard_stop": 94.0, "target_price": 112.0},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert "audit" in nvda["controller"]
    assert "primary_action" in nvda["visual_notes"]
    assert "risk_flag" in nvda["visual_notes"]
    assert "review_questions" in nvda["visual_notes"]
    assert isinstance(nvda["visual_notes"]["why_now"], list)
```

- [ ] **Step 2: Run dashboard-safe test**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_visual_notes_remain_dashboard_safe_with_audit -q
```

Expected: passes.

- [ ] **Step 3: Run dashboard context tests**

Run:

```powershell
python -m pytest tests\test_dashboard_writer.py -k "decision_state" -q
```

Expected: existing dashboard context tests pass because audit is additive and dashboard UI is unchanged.

- [ ] **Step 4: Commit if changes were needed**

If this task only added the compatibility test, commit it:

```powershell
git add tests\test_decision_state_hub.py
git commit -m "test: keep decision audit dashboard compatible"
```

## Task 7: Full Verification And Handoff

**Files:**
- Modify: `docs/superpowers/plans/2026-06-01-llm-controller-discipline.md`

- [ ] **Step 1: Run py_compile**

Run:

```powershell
python -m py_compile agents\decision_state_hub.py agents\dashboard_writer.py scripts\evidence_credibility_report.py
```

Expected: exits 0.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py tests\test_dashboard_writer.py -k "decision_state" -q
```

Expected: all selected tests pass.

- [ ] **Step 3: Run evidence tests**

Run:

```powershell
python -m pytest tests\test_evidence_credibility_report.py -q
```

Expected: all evidence credibility tests pass.

- [ ] **Step 4: Run CLI smoke in a temp directory**

Run:

```powershell
$tmp = New-Item -ItemType Directory -Path (Join-Path $env:TEMP ("decision_audit_" + [guid]::NewGuid()))
New-Item -ItemType Directory -Path (Join-Path $tmp.FullName "findings") | Out-Null
@'
{"symbol":"NVDA","date":"2026-06-01","thesis":{"base_thesis":"AI demand remains strong"}}
'@ | Set-Content -Path (Join-Path $tmp.FullName "findings\premarket_summary_2026-06-01_NVDA.json") -Encoding UTF8
@'
{"decisions":{"NVDA":{"decision":"可入场","confidence":"高"}}}
'@ | Set-Content -Path (Join-Path $tmp.FullName "findings\entry_decision_2026-06-01.json") -Encoding UTF8
python agents\decision_state_hub.py --date 2026-06-01 --base-dir $tmp.FullName NVDA
$out = Join-Path $tmp.FullName "findings\decision_state_2026-06-01.json"
$payload = Get-Content -Path $out -Encoding UTF8 | ConvertFrom-Json
$payload.symbols.NVDA.controller.audit.allowed_actions
$payload.symbols.NVDA.controller.audit.llm_output_contract.narrative_only_upgrade_allowed
Remove-Item -LiteralPath $tmp.FullName -Recurse -Force
```

Expected: output includes audit allowed actions and `False` for narrative-only upgrade.

- [ ] **Step 5: Run repository hygiene**

Run:

```powershell
python scripts\check_repo_hygiene.py
git status --short
```

Expected: hygiene passes and only intentional tracked files are modified before final commit.

- [ ] **Step 6: Append implementation notes to this plan**

Append a short section:

```markdown
## Implementation Notes

- `controller.audit` is additive and keeps existing controller fields stable.
- `allowed_actions` is derived from controller verdict, blockers, and evidence alignment.
- `llm_output_contract.final_action_must_be_one_of` always mirrors `allowed_actions`.
- No real LLM calls, trading rules, backtest engines, weekly scripts, or dashboard UI were changed.

## Verification

- `python -m py_compile agents\decision_state_hub.py agents\dashboard_writer.py scripts\evidence_credibility_report.py`
- `python -m pytest tests\test_decision_state_hub.py tests\test_dashboard_writer.py -k "decision_state" -q`
- `python -m pytest tests\test_evidence_credibility_report.py -q`
- `python scripts\check_repo_hygiene.py`
```

- [ ] **Step 7: Commit handoff notes**

Run:

```powershell
git add docs\superpowers\plans\2026-06-01-llm-controller-discipline.md
git commit -m "docs: record llm controller discipline handoff"
```

## Self-Review Checklist

- Spec coverage: The plan covers audit fields, allowed actions, forbidden claims, downgrade reasons, LLM output contract, stale input handling, caution backtest handling, insufficient factor handling, dashboard compatibility, and final verification.
- Placeholder scan: No step depends on unspecified code or future decisions.
- Type consistency: The plan consistently uses `controller.audit`, `evidence_for`, `evidence_against`, `downgrade_reasons`, `allowed_actions`, `forbidden_claims`, and `llm_output_contract`.
- Scope check: The plan does not modify trading rules, real LLM calls, backtest engines, weekly scripts, or dashboard UI.

## Implementation Notes

- `controller.audit` is additive and keeps existing controller fields stable.
- `allowed_actions` is derived from controller verdict, blockers, and evidence alignment.
- `llm_output_contract.final_action_must_be_one_of` always mirrors `allowed_actions`.
- `forbidden_claims` now blocks narrative-only upgrades such as calling caution backtests fully validated or calling weak/sample-insufficient factors strong signals.
- `evidence_against` now includes source freshness blockers for stale or invalid inputs.
- `visual_notes` remains dashboard-safe: audit stays under `controller`, and the dashboard-facing visual field surface remains intact.
- No real LLM calls, trading rules, backtest engines, weekly scripts, or dashboard UI were changed.
- An unrelated local change to `company_profile_current.json` was preserved in `stash@{0}` as `preserve unrelated company profile change before controller discipline verification`; it was not committed.

## Verification

- `python -m py_compile agents\decision_state_hub.py agents\dashboard_writer.py scripts\evidence_credibility_report.py` passed.
- `python -m pytest tests\test_decision_state_hub.py tests\test_dashboard_writer.py -k "decision_state" -q` passed with 16 tests.
- `python -m pytest tests\test_evidence_credibility_report.py -q` passed with 3 tests.
- CLI smoke wrote `decision_state_2026-06-01.json` in a temp findings directory and confirmed `controller.audit.allowed_actions` plus `narrative_only_upgrade_allowed = False`.
- `python scripts\check_repo_hygiene.py` passed after removing test-generated cache directories.
