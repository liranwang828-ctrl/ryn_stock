# Research Report Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the current AMAT reading report logic and add a reusable reliability gate for future company reports.

**Architecture:** Keep the methodology lightweight and document-first. Add a canonical checklist, tighten template wording, then repair the AMAT report as the first concrete example.

**Tech Stack:** Markdown docs, HTML reading reports, existing research-report template

---

## File Structure

- Verify: `investing-os/docs/superpowers/specs/2026-07-19-research-report-reliability-design.zh.md`
- Create: `investing-os/system/checks/research-report-reliability-checklist.zh.md`
- Modify: `investing-os/dashboards/research-report-template.html`
- Modify: `investing-os/dashboards/reports/AMAT-reality-layer-report.html`

### Task 1: Add the canonical reliability checklist

**Files:**
- Create: `investing-os/system/checks/research-report-reliability-checklist.zh.md`

- [ ] Re-read `investing-os/system/checks/README.md` and keep the new checklist short, operational, and reusable.
- [ ] Write a checklist that forces separation of Reality / Price / Behavior / Odds.
- [ ] Include pass/fail questions for high-point language, pullback language, timeline interpretation, and trigger consistency.
- [ ] Verify UTF-8 rendering with:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\system\checks\research-report-reliability-checklist.zh.md'
```

### Task 2: Tighten the reusable reading template

**Files:**
- Modify: `investing-os/dashboards/research-report-template.html`

- [ ] Re-read the current timeline and key-price wording in the template.
- [ ] Add guidance that interpretation must name the dimension that changed instead of merging Reality and Price.
- [ ] Add guidance that pullback may improve odds without implying the company became stronger.
- [ ] Verify UTF-8 rendering with:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\dashboards\research-report-template.html'
```

### Task 3: Repair the AMAT report

**Files:**
- Modify: `investing-os/dashboards/reports/AMAT-reality-layer-report.html`

- [ ] Re-read the current hero summary, key-price callout, timeline, and “current investment view” block.
- [ ] Rewrite the prose so that:
  - high-point language maps to Price stretch, not weaker Reality
  - pullback language maps to repricing / odds reassessment, not automatic strengthening
  - the current view explicitly separates Reality / Price / Behavior / Odds
- [ ] Verify UTF-8 rendering with:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\dashboards\reports\AMAT-reality-layer-report.html'
```

### Task 4: Final verification and commit

**Files:**
- Verify:
  - `investing-os/docs/superpowers/specs/2026-07-19-research-report-reliability-design.zh.md`
  - `investing-os/docs/superpowers/plans/2026-07-19-research-report-reliability-implementation-plan.zh.md`
  - `investing-os/system/checks/research-report-reliability-checklist.zh.md`
  - `investing-os/dashboards/research-report-template.html`
  - `investing-os/dashboards/reports/AMAT-reality-layer-report.html`

- [ ] Check the exact changed files with:

```powershell
git diff --name-only
```

- [ ] Re-read the changed files in UTF-8 and confirm the repaired wording is explicit.
- [ ] Stage only the files from this plan.
- [ ] Commit with a docs-focused message that mentions report reliability and the AMAT fix.
