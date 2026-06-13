# Market Mode Action Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a phase-aware dashboard action center that shows useful work during closed, overnight, premarket, regular, and postmarket sessions.

**Architecture:** Reuse the existing `/api/market-clock` response and front-end `syncMarketClock()` loop. Add static action-center markup to the overview tab and a small JavaScript phase mapping that updates titles, descriptions, and primary/secondary action groups without adding any new polling workload.

**Tech Stack:** Jinja2 dashboard template, vanilla JavaScript, existing dashboard CSS, pytest render assertions.

---

### Task 1: Render Action Center Shell

**Files:**
- Modify: `templates/daily_dashboard.html.j2`
- Test: `tests/test_dashboard_writer.py`

- [x] Add a failing dashboard render test that expects `market-mode-action-center`, `market-mode-primary-actions`, `market-mode-secondary-actions`, and the text `现在可以做什么`.
- [x] Add the Action Center shell near the top of the overview tab, before the existing top command board.
- [x] Run the focused dashboard writer test.

### Task 2: Phase-Aware Front-End Mapping

**Files:**
- Modify: `templates/scripts.js.j2`
- Test: `tests/test_dashboard_writer.py`

- [x] Extend the render test to assert the generated HTML contains `updateMarketModeActionCenter`, `marketModePhaseConfig`, `runTask('scan')`, `runTask('premarket')`, `runTask('poll')`, `runTask('postmarket')`, and `generateAllFocusReports()`.
- [x] Add a JavaScript phase mapping inside `syncMarketClock()` flow.
- [x] Ensure the Action Center updates from `/api/market-clock` and falls back to `closed` if the API is unavailable.

### Task 3: Styling

**Files:**
- Modify: `templates/styles.css.j2`
- Test: `tests/test_dashboard_writer.py`

- [x] Extend the render test to assert CSS class names `market-mode-action-center`, `market-mode-action-grid`, and `market-mode-action-btn`.
- [x] Add responsive styling with compact, low-noise buttons and no nested cards.
- [x] Run focused tests and `py_compile` for dashboard modules.

### Task 4: Verification

**Files:**
- Read-only verification of generated dashboard.

- [x] Run `py -3.12 -m pytest tests/test_dashboard_writer.py -q`.
- [x] Run `py -3.12 -m py_compile agents/dashboard_writer.py agents/dashboard_server.py`.
- [x] Generate dashboard HTML only if needed for inspection, and do not commit generated `reports/*.html`.

