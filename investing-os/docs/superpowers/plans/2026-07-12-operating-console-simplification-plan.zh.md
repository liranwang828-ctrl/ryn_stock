# Operating Console Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the operating console first screen to four daily-use summaries while preserving all engineering detail in one read-only collapsed diagnostic section.

**Architecture:** Reuse the existing `daily_status` payload and current page functions. Reorder existing markup rather than creating a second page, add one manifest-to-summary renderer, and move skill/snapshot/routes/cognition detail under `<details>` without changing APIs or the growth dashboard.

**Tech Stack:** Static HTML/CSS/JavaScript, pytest source-contract tests, existing local dashboard server.

---

### Task 1: Lock first-screen and diagnostic structure

**Files:**
- Modify: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`
- Modify: `investing-os/dashboards/operating-console.html`

- [ ] Add a failing source-contract test requiring the four IDs `dailyStepSummary`, `factReadinessSummary`, `conversationPromptSummary`, `todayFocusSummary` and a closed `diagnosticDetails` element.
- [ ] Assert diagnostic-only IDs occur inside `diagnosticDetails`, and workflow action buttons remain absent.
- [ ] Run the focused test and confirm RED.
- [ ] Add a compact four-card first-screen grid and wrap existing task, snapshot, cognitive detail, routes, and legacy sections in `<details id="diagnosticDetails">`.
- [ ] Keep one visible link to `growth-dashboard-draft.html`.
- [ ] Run the focused test and confirm GREEN.

### Task 2: Render four summaries from daily_status

**Files:** same two files.

- [ ] Add a failing test requiring `renderDailyFirstScreen(dailyStatus, manifest)` and its call from `renderCoordinator()`.
- [ ] Implement deterministic rendering:
  - current node/substep and status;
  - valid/total artifact count plus top missing item;
  - only `next_conversation_prompt`;
  - focus symbols from decision sheet/current task when available plus top warning and observation boundary.
- [ ] Use neutral fallback text when manifest is empty or missing.
- [ ] Run focused tests and the Dashboard test file excluding the known fixed-date freshness test.

### Task 3: Browser verification and status writeback

**Files:**
- Modify: `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`

- [ ] Restart or reuse the local server and request `/` plus `/api/coordinator-summary`.
- [ ] Verify the page returns 200 and contains the four first-screen IDs.
- [ ] Record exact automated and HTTP verification results.
- [ ] Run `git diff --check`, commit, push, and leave the growth dashboard unchanged.

## Self-review

- No API, manifest schema, coordinator state, or cognition Dashboard behavior changes.
- Diagnostic information is retained, not deleted.
- The page stays read-only and conversation-driven.
