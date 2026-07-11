# DAILY Status Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only DAILY-0/1 manifest from existing canonical runtime files and make the operating console render that manifest without using Dashboard buttons to advance the workflow.

**Architecture:** Add an isolated `stock_team.orchestration.daily_status` module that reads session/runtime artifacts, applies deterministic structural/confirmation checks, and writes one derived `daily-status.json`. Extend the existing session schema for DAILY-0 confirmation, expose the builder through the current dashboard server, and keep the cognition Dashboard unchanged.

**Tech Stack:** Python 3, JSON Schema draft 2020-12, pytest, existing coordinator runtime paths, vanilla HTML/JavaScript operating console.

---

## File structure

### Create

- `investing-os/system/data/schemas/daily-status.schema.json` — external manifest contract.
- `stock_team/orchestration/daily_status.py` — artifact validation and manifest derivation only.
- `stock_team/tests/unit/orchestration/test_daily_status.py` — focused DAILY-0/1 red-green tests.

### Modify

- `investing-os/system/data/schemas/session-state.schema.json` — optional `daily0_confirmation` object.
- `stock_team/orchestration/models.py` — validate optional confirmation and initialize it as absent.
- `stock_team/tests/unit/orchestration/test_models.py` — schema/model coverage.
- `stock_team/server/dashboard_server.py` — call manifest builder and return it from coordinator summary.
- `stock_team/tests/unit/core/test_dashboard_refresh_prices.py` — server integration coverage.
- `investing-os/dashboards/operating-console.html` — render manifest fields and remove workflow-advancing controls from the primary flow.
- `investing-os/system/workflows/WORKFLOW-STATUS.zh.md` — implementation and verification result.

## Task 1: Session DAILY-0 confirmation contract

**Files:** session schema, models, model tests.

- [ ] Write failing tests asserting `daily0_confirmation` is declared and a valid session accepts:

```python
session["daily0_confirmation"] = {
    "confirmed_at": "2026-07-11T08:00:00-04:00",
    "activity_mode": "observation",
    "account_fact_status": "stale_unverified",
    "account_snapshot_ref": "runtime/inputs/account.json",
    "analysis_scope_ref": "runtime/inputs/universe.json",
    "user_confirmed": True,
}
assert validate_session(session) == session
```

- [ ] Run focused tests and verify RED because the optional key is rejected.

```powershell
python -m pytest stock_team/tests/unit/orchestration/test_models.py -k "daily0_confirmation" -q
```

- [ ] Add `daily0_confirmation` to `SESSION_OPTIONAL`, validate its exact keys/types/enums, and add the equivalent JSON Schema object with `additionalProperties: false`.
- [ ] Add rejection tests for invalid activity mode, invalid fact status, false/non-boolean confirmation, and malformed timestamp.
- [ ] Run the full model tests and verify GREEN.
- [ ] Commit:

```powershell
git add -- investing-os/system/data/schemas/session-state.schema.json stock_team/orchestration/models.py stock_team/tests/unit/orchestration/test_models.py
git commit -m "feat: add DAILY-0 confirmation to session contract"
```

## Task 2: DAILY status schema and pure builder

**Files:** create schema, builder, focused tests.

- [ ] Write a failing test for a minimal observation session with valid DAILY-0 confirmation and no Stage 0 artifacts. Expected result:

```python
assert manifest["current_node"] == "DAILY-1"
assert manifest["current_step"] == "DAILY-1A"
assert manifest["overall_status"] == "waiting_data"
assert manifest["observation_available"] is True
assert manifest["next_conversation_prompt"] == "请等待或刷新当日正式盘前数据。"
```

- [ ] Verify RED because `build_daily_status()` does not exist.
- [ ] Implement the public API:

```python
def build_daily_status(*, session: dict, runtime_root: Path, now: datetime | None = None) -> dict:
    """Derive DAILY-0/1 status without mutating canonical artifacts or session."""
```

- [ ] Add deterministic artifact records for these exact roles and paths:
  - `stage0_universe` → `inputs/{session_id}-stage0-universe.json`
  - `premarket_snapshot` → `inputs/{session_id}-pre-market-snapshot.json`
  - `stage0_market_context` → `packets/{session_id}-stage0-market-context.md`
  - `stage0_discussion_notes` → `inputs/{session_id}-stage0-discussion-notes.md`
  - `stage1_decision_sheet` → `inputs/{session_id}-stage1-decision-sheet.json`
  - `stage1_plan_evidence` → `packets/{session_id}-stage1-plan-evidence.md`
  - `trading_plan` → `inputs/{session_id}-trading-plan.json`
  - `intraday_guidance` → `inputs/{session_id}-intraday-guidance.json`
- [ ] Add tests and minimal validators for missing, malformed JSON, date mismatch, five Stage 0 preconditions, formal snapshot source, decision `user_confirmed`, Stage 1 focus scope, plan required fields, guidance required fields, and plan confirmation version.
- [ ] Add artifact fields `role/path/present/valid/confirmed/freshness/source/updated_at/issues`; path remains in manifest but UI hides it by default.
- [ ] Implement node/substep derivation and fixed missing-item prompt mapping. Do not perform investment-quality judgments.
- [ ] Implement state-sync reporting using a fixed coordinator-state-to-step map; never mutate session.
- [ ] Write `write_daily_status(manifest, output_path)` using atomic replace so only the derived manifest is written.
- [ ] Validate builder output against `daily-status.schema.json` in tests using the repository's available JSON Schema test dependency; if no validator library exists, test the declared schema shape and exact required keys without adding a new dependency.
- [ ] Run:

```powershell
python -m pytest stock_team/tests/unit/orchestration/test_daily_status.py -q
```

- [ ] Commit:

```powershell
git add -- investing-os/system/data/schemas/daily-status.schema.json stock_team/orchestration/daily_status.py stock_team/tests/unit/orchestration/test_daily_status.py
git commit -m "feat: derive DAILY-0 and DAILY-1 status manifest"
```

## Task 3: Dashboard server read-only integration

**Files:** dashboard server and focused dashboard tests.

- [ ] Write failing tests proving `_coordinator_summary_payload()` exposes `daily_status`, uses canonical file progress when session lags, and reports `state_sync.needed` without saving the session.
- [ ] Verify RED with:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "daily_status" -q
```

- [ ] Add one helper that loads the active session, calls `build_daily_status()`, and writes:

```text
investing-os/system/runtime/manifests/{session_id}-daily-status.json
```

- [ ] Return the manifest as `daily_status` from `/api/coordinator-summary`; retain legacy `entry_state` as a compatibility projection derived from the manifest, not a second decision path.
- [ ] Ensure GET/refresh never calls coordinator actions and never changes the session file.
- [ ] Add corrupt/missing artifact integration tests and verify the endpoint still returns a structured manifest.
- [ ] Run focused dashboard and orchestration tests.
- [ ] Commit:

```powershell
git add -- stock_team/server/dashboard_server.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "feat: expose read-only DAILY status through dashboard server"
```

## Task 4: Operating console manifest rendering

**Files:** operating console and focused static tests in the existing dashboard test file.

- [ ] Write failing assertions that the page reads `manifest.daily_status`, renders DAILY-0..4 and current substeps, shows one `next_conversation_prompt`, and does not render primary workflow buttons for `init_day`, `record_focus_confirmation`, or `start_stage1`.
- [ ] Verify RED using the focused dashboard test module.
- [ ] Update the page so `renderCoordinatorSummary()` delegates workflow display to `daily_status`; retain artifact detail expansion with paths hidden until expanded.
- [ ] Replace workflow-advancing buttons with a static “在当前对话继续” notice. Preserve non-workflow navigation links and read-only refresh.
- [ ] Keep `growth-dashboard-draft.html` and its data assets unchanged.
- [ ] Run focused tests and manually inspect the rendered HTML source for duplicate readiness logic.
- [ ] Commit:

```powershell
git add -- investing-os/dashboards/operating-console.html stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "feat: render DAILY manifest in operating console"
```

## Task 5: Offline isolated DAILY-0/1 pass

**Files:** extend focused unit/integration fixtures; status ledger.

- [ ] Add a fixture-driven integration test that progresses files without network:
  1. session + DAILY-0 confirmation;
  2. Stage 0 universe/snapshot/packet;
  3. discussion notes + confirmed decision sheet;
  4. Stage 1 packet;
  5. confirmed trading plan + guidance.
- [ ] After each artifact group, rebuild manifest and assert the exact current step/status/prompt.
- [ ] Assert the final manifest marks DAILY-1 complete and DAILY-2 active or ready-to-enter according to the session mode, without coordinator mutation.
- [ ] Run:

```powershell
python -m pytest stock_team/tests/unit/orchestration/test_daily_status.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py stock_team/tests/integration/test_daily_e2e.py -q
```

- [ ] Run the full orchestration suite:

```powershell
python -m pytest stock_team/tests/unit/orchestration stock_team/tests/integration/test_daily_e2e.py -q
```

- [ ] Record exact results and remaining real-data limitation in `WORKFLOW-STATUS.zh.md`. Do not claim real premarket readiness from fixtures.
- [ ] Commit:

```powershell
git add -- stock_team/tests/unit/orchestration/test_daily_status.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py stock_team/tests/integration/test_daily_e2e.py investing-os/system/workflows/WORKFLOW-STATUS.zh.md
git commit -m "test: verify isolated DAILY-0 and DAILY-1 manifest flow"
```

## Final verification

- [ ] Run `git diff --check` and confirm worktree scope.
- [ ] Confirm no cognition Dashboard files changed.
- [ ] Confirm every production behavior was preceded by a failing test.
- [ ] Confirm fresh test output has zero unexpected failures; report any pre-existing freshness test separately with evidence.
- [ ] Push the current branch only after all required verification passes.

## Self-review

- The plan implements only DAILY-0/1 and the operating console projection.
- Intraday event runtime and cognition Dashboard changes are explicitly excluded.
- The builder is separate from `dashboard_server.py` and read-only toward canonical artifacts.
- Existing artifact filenames and validators are reused; no parallel DAILY file family is created.
- Real market-data success is not inferred from offline fixtures.
