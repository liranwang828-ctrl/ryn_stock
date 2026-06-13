# Operating Console Entrypoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `operating-console.html` as the daily investing-os entrypoint while keeping `growth-dashboard-draft.html` as the cognition-growth view.

**Architecture:** The console is a static local HTML page backed by `dashboards/assets/operating-console-data.js`. It does not execute trades or call `stock_team` directly; it displays route state, permission state, evidence gaps, available packets, and next actions. `command-router.md` remains the textual workflow contract.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, local JSON-like JavaScript data files, PowerShell static verification.

---

### Task 1: Repair Command Router

**Files:**
- Modify: `system/workflows/command-router.md`

- [ ] Replace mojibake Chinese route labels with readable Chinese.
- [ ] Make the route table daily-use oriented: 盘前, 盘中检查, 交易复盘, 盘后总结, 公司研究, 行业研究, 周末复盘.
- [ ] Keep the stock_team boundary unchanged.

### Task 2: Add Console Data

**Files:**
- Create: `dashboards/assets/operating-console-data.js`

- [ ] Define `window.OPERATING_CONSOLE_DATA`.
- [ ] Include permission state, next action, evidence gaps, route cards, packet availability, pending lessons, and links to the growth dashboard/report archive.
- [ ] Use static sample data from the current system state only.

### Task 3: Add Operating Console Page

**Files:**
- Create: `dashboards/operating-console.html`

- [ ] Build a quiet operational layout, not a marketing page.
- [ ] Show current permission state, next action, evidence gaps, stock_team packet readiness, pending lessons, and route cards.
- [ ] Link to `growth-dashboard-draft.html` and the latest HTML report.
- [ ] Avoid buy / sell / hold buttons and live execution controls.

### Task 4: Connect Dashboard Direction

**Files:**
- Modify: `dashboards/growth-dashboard-draft.html`

- [ ] Add a small link back to `operating-console.html`.
- [ ] Do not merge console behavior into the growth dashboard.

### Task 5: Verify

**Files:**
- Read: `tools/check-file-growth.ps1`
- Read: generated HTML files

- [ ] Run `tools/check-file-growth.ps1`.
- [ ] Check that `operating-console.html` references the data script.
- [ ] Check that the console contains no buy / sell / hold recommendation language.
- [ ] Check that route labels render as Chinese text in source.
