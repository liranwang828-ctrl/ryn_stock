# Key Price Anchors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable key-price-anchors block to reading-layer research reports and apply the first version to NBIS.

**Architecture:** Keep the methodology in docs first, then extend the reading-layer HTML with a dedicated key-price block. Use a manual first-pass NBIS example that explicitly labels the evidence basis for each price anchor instead of pretending to automate pricing before the data inputs are stable.

**Tech Stack:** Markdown specs, HTML, CSS, existing research reading template, existing company / industry markdown reports

---

## File Structure

- Verify: `investing-os/docs/superpowers/specs/2026-07-19-key-price-anchors-design.zh.md`
- Modify: `investing-os/dashboards/research-report-template.html`
- Modify: `investing-os/dashboards/reports/NBIS-verification-layer-report.html`
- Verify against:
  - `investing-os/wiki/companies/NBIS.zh.md`
  - `investing-os/wiki/industries/ai-commercialization-verification-layer.zh.md`

### Task 1: Extend the reusable reading template

**Files:**
- Modify: `investing-os/dashboards/research-report-template.html`

- [ ] **Step 1: Re-read the current template**

Run:

```powershell
Get-Content -Raw 'investing-os/dashboards/research-report-template.html'
```

Expected:

- The template currently contains hero, cards, timeline, coupling, and full-body sections.
- There is no dedicated key-price-anchors block yet.

- [ ] **Step 2: Add a “Key Price Anchors” section skeleton**

Insert a new section between the four-card block and the timeline block with:

- section title: `Key Price Anchors`
- one lead sentence
- a five-row table:
  - Current price context
  - Watch zone
  - Probe zone
  - Thesis-upgrade zone
  - Thesis-downgrade zone

Each row must contain these columns:

- Anchor
- Price
- Why it matters
- Main evidence layer
- Action meaning

- [ ] **Step 3: Style the anchor table**

Add CSS for:

- readable table layout on desktop
- stacked or scroll-friendly behavior on narrow screens
- visual distinction for upgrade and downgrade rows

- [ ] **Step 4: Verify the template**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\dashboards\research-report-template.html'
```

Expected:

- The new section is present.
- Chinese and English labels render correctly.

- [ ] **Step 5: Commit the template update**

Run:

```powershell
git add -- 'investing-os/dashboards/research-report-template.html'
git commit -m "docs: add key price anchors block to research report template"
```

Expected:

- One commit is created for the reusable template change.

### Task 2: Apply the first version to NBIS

**Files:**
- Modify: `investing-os/dashboards/reports/NBIS-verification-layer-report.html`

- [ ] **Step 1: Re-read the NBIS reading report**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\dashboards\reports\NBIS-verification-layer-report.html'
```

Expected:

- The report currently has no explicit investment price block.

- [ ] **Step 2: Add a first-pass NBIS key-price block**

Insert a new section with:

- title: `关键价格与操作锚点`
- short methodology note explaining the four-layer approach
- a five-row table with:
  - 当前价格背景
  - 观察区间
  - 试探仓区间
  - thesis 升级区间
  - thesis 降级区间

Each row must include:

- concrete price or price range
- why it matters
- which evidence layer dominates
- action meaning

Important:

- If exact live prices are not yet sourced in-system, explicitly label the block as `first-pass manual framework example`.
- Do not invent a false precision such as two decimal places without basis.

- [ ] **Step 3: Add a short methodology disclaimer**

Below the table add a short paragraph stating:

- these anchors come from structure + behavior + thesis translation
- derivatives / options reinforcement should be added only when current data is available
- this section is decision support, not execution automation

- [ ] **Step 4: Verify the NBIS report**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\dashboards\reports\NBIS-verification-layer-report.html'
```

Expected:

- The new key-price block renders correctly in UTF-8.
- The report now contains a practical bridge from research to action.

- [ ] **Step 5: Commit the NBIS update**

Run:

```powershell
git add -- 'investing-os/dashboards/reports/NBIS-verification-layer-report.html'
git commit -m "docs: add key price anchors to NBIS reading report"
```

Expected:

- One commit is created for the NBIS reading-report update.

### Task 3: Final verification and handoff

**Files:**
- Verify:
  - `investing-os/dashboards/research-report-template.html`
  - `investing-os/dashboards/reports/NBIS-verification-layer-report.html`

- [ ] **Step 1: Check final commit scope**

Run:

```powershell
git diff --stat HEAD~2..HEAD
```

Expected:

- The diff only includes the template and NBIS report changes for this implementation sequence.

- [ ] **Step 2: Confirm repository hygiene**

Run:

```powershell
git status --short
```

Expected:

- Existing unrelated user changes remain unstaged.
- Only intended files were part of this change sequence.

- [ ] **Step 3: Re-open the two HTML files**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\dashboards\research-report-template.html'
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\dashboards\reports\NBIS-verification-layer-report.html'
```

Expected:

- Both files render with the key-price block.
- The template remains reusable and the NBIS example remains readable.

## Self-Review

Spec coverage check:

- four-layer price methodology: covered in Task 2 note and table logic
- report output block: covered in Tasks 1 and 2
- reuse in template: covered in Task 1
- initial NBIS application: covered in Task 2
- repo hygiene: covered in Task 3

Placeholder scan:

- No `TODO`, `TBD`, or unresolved implementation markers remain.

Naming consistency:

- `Key Price Anchors` and `关键价格与操作锚点` are used consistently as the new report block name.

