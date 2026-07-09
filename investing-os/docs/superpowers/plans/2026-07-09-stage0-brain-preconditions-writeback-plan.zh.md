# Stage0 Brain Preconditions Writeback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write the confirmed Stage0 brain-side preconditions back into `investing-os` canonical template, workflow, and packet contract files without expanding scope into runtime or bridge code.

**Architecture:** Keep the change set limited to three canonical files: the Stage0 structure source (`pre-market-universe.json`), the Stage0 workflow source (`pre-market.md`), and the Stage0 brain→muscle exchange contract (`pre-market-context-packet.md`). Do not edit dashboard, coordinator, or bridge logic in this batch.

**Tech Stack:** Existing `investing-os` JSON template files, Markdown workflow/contract files, Git-tracked handoff/spec artifacts, manual verification with ripgrep and file inspection.

---

## File Structure

### Files to modify

- `investing-os/templates/pre-market-universe.json`
  - Canonical Stage0 structure source; must explicitly contain the five confirmed brain-side preconditions.
- `investing-os/system/workflows/pre-market.md`
  - Canonical Stage0 workflow rationale; must explain that Stage0 is not a pure market-data action and must load brain-owned state first.
- `investing-os/system/data/packets/pre-market-context-packet.md`
  - Canonical brain→muscle exchange contract; must clarify ownership and boundary of the five preconditions.

### Files to inspect but not modify in this batch

- `investing-os/docs/superpowers/specs/2026-07-08-stage0-brain-preconditions-canonical-writeback-design.zh.md`
- `investing-os/handoff/2026-07-06-stage0-brain-precondition-blocker.zh.md`
- `investing-os/templates/pre-market-decision-sheet.json`
- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`

### Verification files

- `investing-os/templates/pre-market-universe.json`
- `investing-os/system/workflows/pre-market.md`
- `investing-os/system/data/packets/pre-market-context-packet.md`

---

### Task 1: Lock the exact five-field structure in `pre-market-universe.json`

**Files:**
- Modify: `investing-os/templates/pre-market-universe.json`

- [ ] **Step 1: Write the failing structure checklist**

```json
{
  "source_inputs": {
    "positions": [],
    "prior_review": {},
    "cognition_state": {}
  },
  "permission_state_before_open": "",
  "forbidden_actions": []
}
```

- [ ] **Step 2: Verify the current file shape and find the exact target section**

Run: `rg -n "source_inputs|positions|prior_review|cognition_state|permission_state_before_open|forbidden_actions" investing-os/templates/pre-market-universe.json`

Expected: field names are present, and the exact structure section to tighten is visible before editing

- [ ] **Step 3: Edit the template to keep the five preconditions explicitly inside the canonical Stage0 structure**

Required result:

```json
"source_inputs": {
  "positions": [
    {
      "source": "IBKR | cached_ibkr | manual_snapshot",
      "as_of_et": "YYYY-MM-DDTHH:MM:SS-04:00",
      "symbols": []
    }
  ],
  "prior_review": {
    "path": "wiki/journals/YYYY-MM-DD-review.md",
    "status": "reviewed_for_stage0_input",
    "key_risks": []
  },
  "cognition_state": {
    "permission_basis": "normal | yellow | red | recovery_boundary",
    "active_risks": []
  }
},
"permission_state_before_open": "Red | Yellow | Normal | Recovery",
"forbidden_actions": [
  "new_short_term_trade_without_plan",
  "new_leveraged_product_trade_without_explicit_brain_approval",
  "loss_repair_reentry"
]
```

- [ ] **Step 4: Re-run the structure search to confirm the five fields remain explicit**

Run: `rg -n "source_inputs|positions|prior_review|cognition_state|permission_state_before_open|forbidden_actions" investing-os/templates/pre-market-universe.json`

Expected: all five field groups are still present in the canonical template

- [ ] **Step 5: Commit**

```bash
git add investing-os/templates/pre-market-universe.json
git commit -m "docs: lock stage0 brain preconditions in pre-market universe template"
```

---

### Task 2: Write the canonical workflow reason into `pre-market.md`

**Files:**
- Modify: `investing-os/system/workflows/pre-market.md`

- [ ] **Step 1: Write the failing prose checklist**

```md
Required workflow rules:
- Stage 0 is not a pure market-data action
- Brain-owned state must load before Stage 0
- Missing brain preconditions block formal continuation
```

- [ ] **Step 2: Locate the existing Stage0/brain-side rule section**

Run: `rg -n "Stage 0|source_inputs.positions|prior_review|cognition_state|permission_state_before_open|forbidden_actions" investing-os/system/workflows/pre-market.md`

Expected: existing lines show where the rationale should be tightened rather than duplicated elsewhere

- [ ] **Step 3: Add or tighten the workflow language so the rule is explicit**

Required content direction:

```md
Stage 0 is not a pure market-data action.

Before requesting market context, the system must load the current positions context, prior review state, cognition state, permission state before open, and forbidden actions.

If these inputs are missing, Stage 0 may collect or display partial facts, but it must not be treated as formally ready to continue the pre-market workflow.
```

- [ ] **Step 4: Re-open the file and verify the wording exists in the canonical workflow**

Run: `rg -n "not a pure market-data action|must load|must not be treated as formally ready" investing-os/system/workflows/pre-market.md`

Expected: the new rule text is present

- [ ] **Step 5: Commit**

```bash
git add investing-os/system/workflows/pre-market.md
git commit -m "docs: define stage0 brain preconditions in pre-market workflow"
```

---

### Task 3: Write the ownership boundary into `pre-market-context-packet.md`

**Files:**
- Modify: `investing-os/system/data/packets/pre-market-context-packet.md`

- [ ] **Step 1: Write the failing contract checklist**

```md
Required packet rules:
- the five preconditions are brain-owned
- stock_team consumes them as boundaries
- stock_team must not rewrite permission / forbidden / cognition judgment
```

- [ ] **Step 2: Inspect the current packet contract for the right insertion point**

Run: `rg -n "Purpose|Boundary|source_system|review_owner|forbidden|permission|cognition" investing-os/system/data/packets/pre-market-context-packet.md`

Expected: there is a clear existing contract section to extend

- [ ] **Step 3: Add the minimal ownership language without expanding the packet scope**

Required content direction:

```md
The Stage 0 pre-market context packet is requested under brain-owned preconditions:
- positions
- prior_review
- cognition_state
- permission_state_before_open
- forbidden_actions

These fields are provided by investing-os as input boundaries.
stock_team may consume them to scope facts and evidence.
stock_team must not overwrite or reinterpret the final cognition, permission, or forbidden-action judgment.
```

- [ ] **Step 4: Re-run a search to verify the ownership wording exists**

Run: `rg -n "brain-owned preconditions|stock_team may consume|must not overwrite|forbidden_actions" investing-os/system/data/packets/pre-market-context-packet.md`

Expected: the new boundary text is present

- [ ] **Step 5: Commit**

```bash
git add investing-os/system/data/packets/pre-market-context-packet.md
git commit -m "docs: define stage0 brain precondition ownership in packet contract"
```

---

### Task 4: Cross-check the three canonical files for consistency

**Files:**
- Modify: `investing-os/docs/superpowers/specs/2026-07-08-stage0-brain-preconditions-canonical-writeback-design.zh.md` only if a contradiction is found

- [ ] **Step 1: Run a consistency grep across the three canonical files**

Run:

```bash
rg -n "positions|prior_review|cognition_state|permission_state_before_open|forbidden_actions" investing-os/templates/pre-market-universe.json investing-os/system/workflows/pre-market.md investing-os/system/data/packets/pre-market-context-packet.md
```

Expected: all five field names appear across the three files in their intended roles

- [ ] **Step 2: Manually verify role separation**

Checklist:
- template defines structure
- workflow defines why/when it blocks
- packet contract defines ownership boundary

- [ ] **Step 3: If contradiction exists, patch only the contradictory wording**

Example contradiction to fix:

```md
Bad: stock_team owns permission state
Good: investing-os owns permission state; stock_team only consumes it as input boundary
```

- [ ] **Step 4: Commit if any consistency fix was needed**

```bash
git add investing-os/templates/pre-market-universe.json investing-os/system/workflows/pre-market.md investing-os/system/data/packets/pre-market-context-packet.md investing-os/docs/superpowers/specs/2026-07-08-stage0-brain-preconditions-canonical-writeback-design.zh.md
git commit -m "docs: align stage0 brain precondition writeback wording"
```

---

### Task 5: Record the completion in workflow status

**Files:**
- Modify: `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`

- [ ] **Step 1: Add a brief note under current DAILY / minimal-entry follow-up work**

Required note direction:

```md
Stage0 brain preconditions have been written back into canonical template/workflow/packet files:
- pre-market-universe.json
- pre-market.md
- pre-market-context-packet.md
```

- [ ] **Step 2: Verify the note is searchable**

Run: `rg -n "Stage0 brain preconditions|pre-market-universe.json|pre-market-context-packet.md" investing-os/system/workflows/WORKFLOW-STATUS.zh.md`

Expected: the new note is present

- [ ] **Step 3: Commit**

```bash
git add investing-os/system/workflows/WORKFLOW-STATUS.zh.md
git commit -m "docs: record stage0 brain preconditions writeback status"
```

---

## Self-Review

### Spec coverage

This plan covers:

- writing back the five confirmed Stage0 brain preconditions
- touching only the three canonical files named in the approved spec
- preserving separation of concerns between structure, workflow rationale, and packet ownership boundary
- recording completion in workflow status

### Placeholder scan

No `TBD`, `TODO`, “implement later”, or unspecified “write tests later” placeholders remain.

### Type consistency

The same five field names remain consistent across the plan:

- `positions`
- `prior_review`
- `cognition_state`
- `permission_state_before_open`
- `forbidden_actions`

---

Plan complete and saved to `investing-os/docs/superpowers/plans/2026-07-09-stage0-brain-preconditions-writeback-plan.zh.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

