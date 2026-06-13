# Review: Integration Refactoring Plan

Date: 2026-06-05  
Reviewer: Codex  
Reviewed file: `handoff/2026-06-05-integration-refactoring-plan.md`

## Summary

The proposal has the right strategic direction:

- Move cognition, principles, research memory, and reflection assets into `investing-os`.
- Keep `stock_team` / `lianghua` as the quantitative lab and execution/tooling layer.
- Separate qualitative discipline from quantitative parameters.
- Prevent AI agents from bypassing human judgment or mutating account state directly.

However, the current plan is too aggressive to execute as written.

The main risks are:

- It proposes deleting or physically moving source assets too early.
- It may create tight runtime coupling from `stock_team` into `investing-os`.
- It risks turning discipline principles into backtest-optimized parameters.
- It needs stronger fail-safe rules for missing plans and degraded operation.
- It relies too much on Markdown policy for AI isolation instead of enforceable code boundaries.

Recommendation:

Treat the current document as a proposal, not an execution plan.

Before implementation, revise it into a slower migration plan with inventory, copy/import, verification, archive, and explicit user approval before deletion.

## Key Findings

### P0: Do Not Delete `stock_team` Assets During Initial Migration

The plan uses `[DELETE]` for existing principles, cases, findings, reflections, and scripts.

This is unsafe.

Migration should be:

```text
inventory
|
copy/import
|
verify
|
archive
|
user approval
|
delete only if still necessary
```

Source assets are cognitive history. They should not be physically deleted until imported content has been reviewed and validated.

Recommended change:

Replace all early `[DELETE]` actions with `[COPY]`, `[IMPORT]`, or `[ARCHIVE AFTER APPROVAL]`.

### P1: Avoid Runtime Coupling From `stock_team` Directly Into `investing-os`

The plan says `stock_team` will load configuration and rules from `investing-os` on each run.

This creates tight coupling between a knowledge repository and a runtime system.

Better model:

```text
investing-os
|
validated rule snapshot export
|
stock_team / lianghua runtime
```

`investing-os` should remain the cognition and governance source. Runtime code should consume a validated export or snapshot, not directly depend on wiki files.

Recommended change:

Add an explicit export boundary:

- `investing-os` owns principles, templates, reviews, and rule intent.
- `stock_team` consumes generated, schema-validated runtime snapshots.
- Runtime snapshots should be versioned and auditable.

### P1: Do Not Reduce Discipline Principles To Backtest Parameters

The plan proposes extracting all threshold numbers into `config/tactical_rules.json` and optimizing them through backtesting.

This is partially correct for quantitative thresholds, but not for discipline rules.

Some numbers are not merely performance parameters. They are behavioral constraints.

Example:

```text
Principle:
Do not immediately reverse action after taking profit because of regret.

Parameter:
cooling_minutes = 15 / 30 / 60
```

The principle belongs in `investing-os`.

The parameter may be tested, reviewed, and exported.

Recommended change:

Split every numeric rule into:

- `discipline intent`
- `runtime parameter`
- `source of evidence`
- `review cadence`
- `falsification or adjustment condition`

### P1: Degraded Operation Must Be Fail-Safe, Not Fail-Open

The plan correctly wants to avoid hard crashes when daily plans or snapshots are missing.

But degraded mode must not become an excuse for unplanned action.

If `daily_plan.json` or pre-market planning is missing, allowed behavior should be limited to:

- read-only monitoring
- alerts
- risk warnings
- journal/review tasks
- no new trade generation

Recommended change:

Define degraded mode explicitly:

```text
No plan = no new discretionary execution.
```

### P2: AI Isolation Needs Code-Level Enforcement

The proposed Brainstorm Mode / Execution Mode separation is good.

But `AGENTS.md` and discipline docs are not enough.

Enforcement should include:

- read-only mode by default
- all writes through CLI commands
- schema validation before writes
- state transition guards
- audit logs
- tests for unauthorized writes

Recommended change:

Document the policy in `AGENTS.md`, but implement enforcement in `stock_team` / `lianghua` code.

### P2: Use `wiki/inbox/` Before Importing Reports Into Permanent Wiki

The plan suggests moving all research reports directly into `wiki/companies/` and `wiki/industries/`.

This risks turning `investing-os` into a document dump.

Better model:

```text
wiki/inbox/
|
WHY alignment
|
deduplication
|
source labeling
|
structure rewrite
|
permanent wiki
```

Recommended change:

Create `wiki/inbox/` for imported material that has not yet been converted into durable knowledge.

## Recommended Revised Plan

### Phase 0: Inventory Only

Goal: understand source assets without moving or deleting anything.

Actions:

- Locate the real active `stock_team` / `lianghua` repository.
- Generate an inventory of principles, cases, findings, reflections, scripts, tests, configs, and runtime state files.
- Classify each item as cognition, research, reflection, runtime config, code, raw data, generated output, or legacy artifact.

No file deletion.

No physical migration yet.

### Phase 1: Define Import Contracts

Goal: define what may enter `investing-os`.

Actions:

- Add templates for principles and cases.
- Add `wiki/inbox/`.
- Add import rules.
- Add source metadata requirements.
- Add WHY alignment checks for imported material.

### Phase 2: Copy Into Inbox

Goal: preserve original assets while preparing migration.

Actions:

- Copy candidate cognition/research/reflection assets into `wiki/inbox/`.
- Keep source paths and timestamps.
- Do not rewrite content destructively.
- Do not delete source files.

### Phase 3: Structure And Absorb

Goal: convert imported assets into durable knowledge.

Actions:

- Convert principles into `PRIN-*` files.
- Convert cases into `CASE-*` files.
- Convert research into company or industry notes.
- Convert reflections into journals.
- Add links between principles, cases, companies, and journals.

### Phase 4: Export Runtime Snapshots

Goal: connect `investing-os` to `stock_team` without tight coupling.

Actions:

- Define exported runtime snapshot schema.
- Separate discipline intent from runtime parameters.
- Generate or manually maintain a validated snapshot.
- Let `stock_team` read only the snapshot, not the full wiki.

### Phase 5: Refactor `stock_team`

Goal: make `stock_team` a safer quantitative/tooling layer.

Actions:

- Remove hardcoded thresholds.
- Load validated runtime config.
- Add degraded read-only monitoring mode.
- Add state transition guards.
- Route all writes through CLI commands.
- Add unit and integration tests.

### Phase 6: Archive Or Delete Only After Approval

Goal: clean old files safely.

Actions:

- Archive migrated source files first.
- Verify imported knowledge and runtime tests.
- Ask user approval before any deletion.
- Keep a migration log.

## Suggested Wording Changes

Replace:

```text
[DELETE] stock_team/...
```

With:

```text
[COPY] stock_team/... -> investing-os/wiki/inbox/
[ARCHIVE AFTER VERIFICATION]
[DELETE ONLY AFTER USER APPROVAL]
```

Replace:

```text
stock_team 每次运行只读装载 investing-os 中的配置与规则
```

With:

```text
stock_team reads a schema-validated runtime snapshot exported from investing-os.
```

Replace:

```text
原则文件中的所有阈值数字必须通过回测优化
```

With:

```text
Discipline principles stay in investing-os. Runtime parameters are separated, versioned, and may be evaluated by backtests where appropriate.
```

## Decision

Do not execute the original plan as written.

Approve the direction, but require a revised execution plan using the safer phased migration above.

