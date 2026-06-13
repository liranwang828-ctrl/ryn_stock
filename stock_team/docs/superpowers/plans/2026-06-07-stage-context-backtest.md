# Stage Context Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evidence-only Stage 0 / Stage 1 context backtest command.

**Architecture:** Create a focused `backtest/stage_context_backtest.py` module that reads a brain-authored request, aggregates event outcomes by context labels, and writes Markdown/JSON evidence packets. Wire it into `stock_team.cli` as `stage-context-backtest`.

**Tech Stack:** Python standard library, pytest, existing stock_team CLI patterns.

---

### Task 1: Stage Context Evidence Runner

**Files:**
- Create: `backtest/stage_context_backtest.py`
- Test: `tests/unit/core/test_stage_context_backtest.py`

- [x] **Step 1: Write failing tests for grouped Stage context metrics**

Tests assert `run_request()` groups events by ordered `context_fields`, calculates event count, win rate, average return, MAE, and MFE, and emits boundary flags showing no permission decision or config mutation.

- [x] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests\unit\core\test_stage_context_backtest.py -q`

Expected: fail with `ModuleNotFoundError: No module named 'stock_team.backtest.stage_context_backtest'`.

- [x] **Step 3: Implement minimal evidence runner**

Implemented `load_request()`, `run_request()`, `write_outputs()`, `render_markdown()`, request-key validation, and simple metric helpers.

- [x] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests\unit\core\test_stage_context_backtest.py -q`

Observed: `3 passed`.

### Task 2: CLI Integration

**Files:**
- Modify: `cli.py`
- Modify: `tests/unit/core/test_cli.py`

- [x] **Step 1: Write failing CLI tests**

Tests assert root help lists `stage-context-backtest` and the command writes Markdown/JSON evidence packets.

- [x] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests\unit\core\test_cli.py::test_cli_stage_context_backtest_generation tests\unit\core\test_cli.py::test_cli_help -q`

Expected: fail because the subcommand is not registered.

- [x] **Step 3: Add CLI handler and parser**

Added `handle_stage_context_backtest()` and the `stage-context-backtest` parser.

- [x] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests\unit\core\test_cli.py::test_cli_stage_context_backtest_generation tests\unit\core\test_cli.py::test_cli_help -q`

Observed: `2 passed`.

### Task 3: Contract And Handoff

**Files:**
- Create: `docs/stage-context-backtest-contract.md`
- Create: `docs/superpowers/specs/2026-06-07-stage-context-backtest-design.md`
- Create: `docs/superpowers/plans/2026-06-07-stage-context-backtest.md`
- Modify: `docs/ACTIVE_WORKSPACE.md`
- Modify: `C:\Users\rriww\Documents\investing-os\handoff\requests\antigravity-current-tasks.md`

- [x] **Step 1: Document the Stage context contract**

Documented request shape, output shape, metrics, boundary rules, and relationship to `tactic-backtest`.

- [x] **Step 2: Record dashboard follow-up**

Recorded that the intraday HTML dashboard exists and is usable, while future work should return to investing-os dashboard integration and experience polish.
