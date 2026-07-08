# Minimal Usable Entry And Stage0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the existing `investing-os + stock_team` assets to restore a minimal usable operating entry that shows today mode, current step, readiness, missing items, and next action without sacrificing `investing-os` growth potential.

**Architecture:** Keep `investing-os/dashboards/operating-console.html` as the user-facing canonical entry shell, add a thin status-aggregation layer that reads existing runtime/evidence/blocker sources, and surface only five core fields in the entry view. Preserve bridge logic and large legacy runtime files as upstream sources rather than deep-refactoring them in this batch.

**Tech Stack:** Existing `investing-os` static HTML/JS assets, existing `stock_team` runtime/session outputs, Python server/runtime code already present in `stock_team`, Markdown handoff docs, Git-based audit flow.

---

## File Structure

### Existing files to modify

- `investing-os/dashboards/operating-console.html`
  - Existing canonical entry shell to be restored as the minimal usable user entry.
- `investing-os/dashboards/assets/operating-console-data.js`
  - Existing console data model to be extended with first-batch entry state fields and file-role tags.
- `stock_team/server/dashboard_server.py`
  - Existing runtime access point; only minimal read-only exposure should be added for entry state aggregation if required.
- `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`
  - Update implementation status after the first batch is actually delivered.

### New files to create

- `investing-os/handoff/2026-07-08-entry-source-map.zh.md`
  - Source-of-truth map for the five displayed fields and file-role tags.
- `investing-os/handoff/2026-07-08-entry-file-tag-ledger.zh.md`
  - First-batch file tagging ledger for useful/useless-file screening preparation.

### Existing files to inspect but not restructure in this batch

- `stock_team/server/dashboard_writer.py`
- `stock_team/server/dashboard_cache.py`
- `stock_team/templates/daily_dashboard.html.j2`
- `investing-os/handoff/2026-07-06-stage0-brain-precondition-blocker.zh.md`
- `investing-os/handoff/2026-07-06-recent-work-disposition-ledger.zh.md`
- `investing-os/docs/superpowers/specs/2026-07-08-minimal-usable-entry-and-stage0-design.zh.md`

### Test targets

- Existing dashboard/coordinator unit tests already near `stock_team/tests/unit/...`
- Add or update focused tests only around new aggregation/output behavior
- Manual verification of entry page rendering and field presence

---

### Task 1: Freeze first-batch source mapping and file-role tags

**Files:**
- Create: `investing-os/handoff/2026-07-08-entry-source-map.zh.md`
- Create: `investing-os/handoff/2026-07-08-entry-file-tag-ledger.zh.md`
- Modify: `investing-os/docs/superpowers/specs/2026-07-08-minimal-usable-entry-and-stage0-design.zh.md` only if a contradiction is discovered during source mapping

- [ ] **Step 1: Write the source-map document content**

```md
# 最小入口数据来源映射

目标字段：
- today_mode
- current_step
- readiness
- missing_items
- next_action

每个字段必须记录：
- primary_source
- fallback_source
- owner (`investing-os` / `stock_team`)
- display_rule
- unresolved_risk
```

- [ ] **Step 2: Write the file-tag ledger content**

```md
# 第一批入口接线文件标签台账

| file | tag | disposition | reason |
|---|---|---|---|
| investing-os/dashboards/operating-console.html | canonical-entry | keep | 用户正式入口壳 |
| investing-os/dashboards/assets/operating-console-data.js | canonical-entry | keep | 入口 view-model |
| stock_team/server/dashboard_server.py | runtime-source | transitional | 当前只读状态来源 |
| stock_team/server/dashboard_writer.py | legacy-runtime | reference-only | 本批不深改 |
```
```

- [ ] **Step 3: Save the two docs and verify they exist**

Run: `Get-ChildItem investing-os/handoff/2026-07-08-entry-*`

Expected: both files are listed

- [ ] **Step 4: Commit**

```bash
git add investing-os/handoff/2026-07-08-entry-source-map.zh.md investing-os/handoff/2026-07-08-entry-file-tag-ledger.zh.md
git commit -m "docs: add minimal entry source and file-tag ledgers"
```

---

### Task 2: Add a thin entry-state data shape in operating-console data

**Files:**
- Modify: `investing-os/dashboards/assets/operating-console-data.js`
- Test: manual inspection in browser or file preview

- [ ] **Step 1: Write the failing expectation as a data-shape checklist**

```js
// Expected new shape
window.OPERATING_CONSOLE_DATA = {
  ...existingFields,
  entryState: {
    todayMode: "",
    currentStep: "",
    readiness: "",
    missingItems: [],
    nextAction: "",
    tags: []
  }
}
```

- [ ] **Step 2: Verify the current file lacks the final agreed shape**

Run: `rg "entryState|todayMode|currentStep|readiness|missingItems|nextAction" investing-os/dashboards/assets/operating-console-data.js`

Expected: partial match or missing fields, confirming the new shape still needs to be added

- [ ] **Step 3: Add the minimal entry-state block without breaking existing fields**

```js
entryState: {
  todayMode: "unknown",
  currentStep: "unknown",
  readiness: "blocked",
  missingItems: [],
  nextAction: "inspect_runtime_state",
  tags: ["canonical-entry"]
}
```

- [ ] **Step 4: Re-open the file and verify the new keys are present**

Run: `rg "entryState|todayMode|currentStep|readiness|missingItems|nextAction" investing-os/dashboards/assets/operating-console-data.js`

Expected: all six keys are found

- [ ] **Step 5: Commit**

```bash
git add investing-os/dashboards/assets/operating-console-data.js
git commit -m "feat: add minimal entry-state shape to operating console data"
```

---

### Task 3: Define the entry-state aggregation contract in server/runtime terms

**Files:**
- Modify: `stock_team/server/dashboard_server.py`
- Test: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py` or the nearest dashboard/coordinator server tests

- [ ] **Step 1: Write the failing test for a minimal aggregated entry-state payload**

```python
def test_entry_state_payload_contains_five_core_fields():
    payload = _build_minimal_entry_state(...)
    assert set(payload.keys()) == {
        "today_mode",
        "current_step",
        "readiness",
        "missing_items",
        "next_action",
    }
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest stock_team/tests/unit -k "entry_state_payload_contains_five_core_fields" -v`

Expected: FAIL because the helper or payload shape does not exist yet

- [ ] **Step 3: Implement the thinnest possible read-only aggregation helper**

```python
def _build_minimal_entry_state(session_summary: dict | None, blockers: list[str] | None) -> dict:
    session_summary = session_summary or {}
    blockers = [item for item in (blockers or []) if item]
    return {
        "today_mode": session_summary.get("mode", "unknown"),
        "current_step": session_summary.get("state", "unknown"),
        "readiness": "blocked" if blockers else session_summary.get("readiness", "partial"),
        "missing_items": blockers[:5],
        "next_action": session_summary.get("next_action", "inspect_runtime_state"),
    }
```

- [ ] **Step 4: Re-run the focused test to verify it passes**

Run: `python -m pytest stock_team/tests/unit -k "entry_state_payload_contains_five_core_fields" -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_team/server/dashboard_server.py stock_team/tests/unit
git commit -m "feat: add minimal entry-state aggregation helper"
```

---

### Task 4: Surface the five core fields in operating-console UI

**Files:**
- Modify: `investing-os/dashboards/operating-console.html`
- Modify: `investing-os/dashboards/assets/operating-console-data.js`
- Test: manual browser/file rendering

- [ ] **Step 1: Write the failing UI checklist**

```md
Required visible fields:
- Today Mode
- Current Step
- Readiness
- Missing Items
- Next Action
```

- [ ] **Step 2: Confirm the current page does not visibly render all five fields together**

Run: `rg "Today Mode|Current Step|Readiness|Missing Items|Next Action" investing-os/dashboards/operating-console.html`

Expected: one or more labels missing

- [ ] **Step 3: Add one compact entry-state panel to the existing console**

```html
<section id="entry-state-panel">
  <h2>Today Status</h2>
  <div data-entry-field="today-mode"></div>
  <div data-entry-field="current-step"></div>
  <div data-entry-field="readiness"></div>
  <ul data-entry-field="missing-items"></ul>
  <div data-entry-field="next-action"></div>
</section>
```

- [ ] **Step 4: Wire the existing page script/data binding to fill the panel from `entryState`**

```js
const entry = data.entryState || {};
setText("today-mode", entry.todayMode || "unknown");
setText("current-step", entry.currentStep || "unknown");
setText("readiness", entry.readiness || "blocked");
renderList("missing-items", entry.missingItems || []);
setText("next-action", entry.nextAction || "inspect_runtime_state");
```

- [ ] **Step 5: Open the page and visually verify all five fields appear**

Run: manual local preview of `investing-os/dashboards/operating-console.html`

Expected: all five fields are visible without opening secondary views

- [ ] **Step 6: Commit**

```bash
git add investing-os/dashboards/operating-console.html investing-os/dashboards/assets/operating-console-data.js
git commit -m "feat: surface minimal entry-state panel in operating console"
```

---

### Task 5: Make missing items come from active blockers, not static filler

**Files:**
- Modify: `stock_team/server/dashboard_server.py`
- Modify: `investing-os/handoff/2026-07-08-entry-source-map.zh.md`
- Test: focused unit test around blocker translation

- [ ] **Step 1: Write the failing test for blocker-to-missing-items translation**

```python
def test_entry_state_missing_items_prefers_known_blockers():
    payload = _build_minimal_entry_state(
        {"mode": "trading", "state": "DAY_INITIALIZED"},
        ["missing prior_review", "missing permission_state_before_open"],
    )
    assert payload["missing_items"] == [
        "missing prior_review",
        "missing permission_state_before_open",
    ]
```

- [ ] **Step 2: Run the test to verify it fails or is not yet enforced**

Run: `python -m pytest stock_team/tests/unit -k "missing_items_prefers_known_blockers" -v`

Expected: FAIL

- [ ] **Step 3: Tighten the helper so blocker-derived items win over generic placeholders**

```python
if blockers:
    missing_items = blockers[:5]
else:
    missing_items = session_summary.get("missing_items", [])[:5]
```

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python -m pytest stock_team/tests/unit -k "missing_items_prefers_known_blockers" -v`

Expected: PASS

- [ ] **Step 5: Update the source-map doc with the final source priority**

```md
missing_items:
  primary_source: active blockers
  fallback_source: runtime session summary missing_items
  owner: investing-os interpretation over stock_team runtime facts
```

- [ ] **Step 6: Commit**

```bash
git add stock_team/server/dashboard_server.py investing-os/handoff/2026-07-08-entry-source-map.zh.md stock_team/tests/unit
git commit -m "feat: derive entry missing items from active blockers"
```

---

### Task 6: Preserve growth potential in the entry panel

**Files:**
- Modify: `investing-os/dashboards/operating-console.html`
- Modify: `investing-os/handoff/2026-07-08-entry-file-tag-ledger.zh.md`
- Test: manual UI inspection

- [ ] **Step 1: Write the UI requirement checklist**

```md
The entry panel must leave visible room or links for:
- review
- growth dashboard
- cognition/principles
```

- [ ] **Step 2: Confirm the current entry panel lacks explicit growth-facing links or placeholders**

Run: `rg "growth|review|principle|cognition" investing-os/dashboards/operating-console.html`

Expected: missing or insufficient references in the new panel section

- [ ] **Step 3: Add compact forward links/placeholders without expanding into a full dashboard**

```html
<nav class="entry-growth-links">
  <a href="./growth-dashboard-draft.html">Growth</a>
  <a href="../wiki/principles/README.md">Principles</a>
  <span data-entry-link="review">Review</span>
</nav>
```

- [ ] **Step 4: Update the file-tag ledger to mark the entry shell as growth-preserving**

```md
| investing-os/dashboards/operating-console.html | canonical-entry | keep | 最小入口且保留 growth/review/cognition 接回空间 |
```

- [ ] **Step 5: Visually verify the panel still stays compact**

Run: manual local preview of `investing-os/dashboards/operating-console.html`

Expected: the page still reads like a minimal entry, not a large dashboard

- [ ] **Step 6: Commit**

```bash
git add investing-os/dashboards/operating-console.html investing-os/handoff/2026-07-08-entry-file-tag-ledger.zh.md
git commit -m "feat: preserve growth-facing links in minimal operating entry"
```

---

### Task 7: Verify the first batch and update status ledger

**Files:**
- Modify: `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`
- Modify: `investing-os/handoff/2026-07-06-recent-work-disposition-ledger.zh.md` only if the transitional status of entry-related bridge logic changes

- [ ] **Step 1: Run focused tests**

Run: `python -m pytest stock_team/tests/unit -k "entry_state or dashboard or coordinator" -q`

Expected: relevant focused tests pass

- [ ] **Step 2: Run broader regression checks if focused tests pass**

Run: `python -m pytest stock_team/tests/unit/orchestration/ -q`

Expected: existing orchestration tests still pass

- [ ] **Step 3: Manually verify the operating-console page**

Checklist:
- shows all five core fields
- shows no more than five missing items
- shows one primary next action
- still exposes growth-facing space

- [ ] **Step 4: Update workflow status ledger with evidence**

```md
Minimal entry status:
- operating-console restored as active minimal entry shell
- five core fields visible
- current runtime/evidence/blocker sources mapped
- growth-preserving links retained
```

- [ ] **Step 5: Commit**

```bash
git add investing-os/system/workflows/WORKFLOW-STATUS.zh.md
git commit -m "docs: record minimal entry batch verification status"
```

---

## Self-Review

### Spec coverage

This plan covers:

- restoring a minimal entry through `operating-console`
- using existing `stock_team` runtime/evidence sources
- surfacing five core fields
- exposing blockers as missing items
- preserving `investing-os` growth potential
- adding file-role tags for later useful/useless-file screening

### Placeholder scan

No task uses `TBD`, `TODO`, “implement later”, or “add tests” without concrete commands or example content.

### Type consistency

The repeated five-field payload shape stays consistent:

- `today_mode`
- `current_step`
- `readiness`
- `missing_items`
- `next_action`

The UI-facing names remain aligned with the same logical fields in `entryState`.

---

Plan complete and saved to `investing-os/docs/superpowers/plans/2026-07-08-minimal-usable-entry-and-stage0-plan.zh.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

