# Growth Dashboard Brain-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the growth dashboard as an investing-os-only cognition dashboard with no direct stock_team runtime dependency.

**Architecture:** Use a static local HTML file for layout and a small local JavaScript data file for current nodes, lessons, tasks, and radar scores. The dashboard displays evidence already absorbed by investing-os; it does not call stock_team APIs or show live IBKR state.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, local `file://` usage.

---

### Task 1: Remove Muscle Direct Access

**Files:**
- Modify: `C:\Users\rriww\Documents\investing-os\dashboards\growth-dashboard-draft.html`
- Create: `C:\Users\rriww\Documents\investing-os\dashboards\assets\growth-dashboard-data.js`

- [ ] Replace corrupted dashboard content with a clean bilingual static dashboard.
- [ ] Remove `fetchSystemStatus`, `localhost:8080`, `localhost:8000`, IBKR connection status, and evidence packet polling.
- [ ] Add an explicit Brain-Muscle boundary note: all user entry starts from investing-os; stock_team evidence is displayed only after absorption.

### Task 2: Implement Structure Map And Lesson Landing

**Files:**
- Modify: `C:\Users\rriww\Documents\investing-os\dashboards\growth-dashboard-draft.html`
- Modify: `C:\Users\rriww\Documents\investing-os\dashboards\assets\growth-dashboard-data.js`

- [ ] Render a radial/tree map with cognition, decision, execution, evolution, wiki, system, and integrations branches.
- [ ] Render candidate lesson nodes around the map.
- [ ] On lesson click, show recommended landing files and draw lines to targets.
- [ ] Keep decisions manual in chat, not inside the webpage.

### Task 3: Implement Capability Radar

**Files:**
- Modify: `C:\Users\rriww\Documents\investing-os\dashboards\growth-dashboard-draft.html`
- Modify: `C:\Users\rriww\Documents\investing-os\dashboards\assets\growth-dashboard-data.js`

- [ ] Render six radar dimensions: Research, Risk, Discipline, Execution, Emotion, Review.
- [ ] Show score, delta, source report, and reason on click.
- [ ] Ensure scores are cognition/process scores, not P/L scores.

### Task 4: Verify

**Files:**
- Verify: `C:\Users\rriww\Documents\investing-os\dashboards\growth-dashboard-draft.html`

- [ ] Run file growth check.
- [ ] Open the local HTML in the in-app browser.
- [ ] Verify no garbled Chinese.
- [ ] Verify no direct stock_team network calls remain.
