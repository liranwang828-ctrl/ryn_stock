# Operating Console Paged Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duplicate-summary/collapsed-legacy operating console with four mutually exclusive hash pages and a separate cognition Dashboard link.

**Architecture:** Keep one HTML and one API load. Add a hash router controlling four `data-page` panels, render each panel from the existing `daily_status` and manifest, and remove obsolete duplicate modules instead of hiding them.

**Tech Stack:** HTML/CSS/vanilla JavaScript, pytest source-contract tests, Playwright CLI.

---

### Task 1: Hash routes and page shells

**Files:** `operating-console.html`, `test_dashboard_refresh_prices.py`.

- [ ] Write failing tests for five stable navigation links and four mutually exclusive panels: today, evidence, review, diagnostics.
- [ ] Add `setPageFromHash()` and `hashchange` handling; default invalid/empty hash to `today`.
- [ ] Remove the four-summary grid and whole-page `diagnosticDetails` wrapper.
- [ ] Verify focused tests GREEN and commit.

### Task 2: Migrate or remove old modules

- [ ] Write failing source assertions that old `dailyStepSummary`, `factReadinessSummary`, `conversationPromptSummary`, `todayFocusSummary`, `Minimal Entry State`, and `Daily Routes` are absent.
- [ ] Today: create one task hero, DAILY timeline, confirmed focus/permission boundary, top warning.
- [ ] Evidence: render artifact readiness and current product task; move packet/evidence links here.
- [ ] Review: render review availability, pending events/lessons, explicit not-wired states.
- [ ] Diagnostics: move coordinator/state sync, artifact paths, snapshot fallback, logs/legacy links.
- [ ] Remove cognitive summary and keep only the growth Dashboard link.
- [ ] Verify focused tests GREEN and commit.

### Task 3: Browser verification and status ledger

- [ ] Run Dashboard tests excluding the known fixed-date freshness assertion.
- [ ] Use Playwright to open each hash route, verify one active page, and capture desktop plus narrow screenshots.
- [ ] Verify `/` and `/api/coordinator-summary` return 200.
- [ ] Record implementation, honest missing-data behavior, and visual verification in `WORKFLOW-STATUS.zh.md`.
- [ ] Run `git diff --check`, commit, push, and clean generated browser/runtime artifacts.

## Self-review

- No schema/API/coordinator/growth Dashboard changes.
- Old modules are evaluated and removed or migrated, not wholesale folded.
- Only confirmed decision-sheet data may be labelled today's focus.
