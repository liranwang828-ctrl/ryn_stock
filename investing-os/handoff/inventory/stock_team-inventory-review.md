# Review: Phase 0 Stock Team Inventory

Date: 2026-06-05  
Reviewed files:

- `handoff/inventory/stock_team-inventory-manifest.json`
- `handoff/inventory/stock_team-inventory-summary.md`

## Verdict

Phase 0 is accepted as an inventory pass.

The output follows the key safety rule: it produced inventory artifacts inside `investing-os/handoff/inventory/` and did not require movement, deletion, renaming, or refactoring of `stock_team` assets.

Do not start Phase 2 yet.

Before Phase 1 / Phase 2, fix the classification and destination issues listed below.

## Verified

- Manifest exists.
- Summary exists.
- Total files counted: 1965.
- Required fields exist on all manifest entries:
  - `path`
  - `relative_path`
  - `size`
  - `last_modified`
  - `extension`
  - `category`
  - `suggested_destination`
  - `migration_action`
  - `sha256`
  - `notes`
- Outer `STOCK` repository remains clean.

## Manifest Breakdown

Categories:

- `legacy_artifact`: 1142
- `generated_output`: 583
- `code`: 200
- `runtime_config`: 20
- `cognition`: 15
- `reflection`: 3
- `research`: 2

Migration actions:

- `candidate_archive_later`: 1137
- `ignore_generated`: 583
- `candidate_code_refactor`: 200
- `candidate_runtime_config`: 20
- `candidate_copy_to_inbox`: 20
- `keep`: 5

## Required Fixes Before Next Phase

### P1: Do Not Map Broad System Docs To `wiki/principles/README.md`

Several files are classified as cognition but point to `wiki/principles/README.md`.

Examples:

- `docs/wiki/00_system_overview_zh.md`
- `docs/wiki/01_ai_usage_protocol_zh.md`
- `docs/wiki/02_portfolio_framework_zh.md`
- `docs/wiki/03_daily_workflow_zh.md`
- `docs/wiki/04_company_research_method_zh.md`
- `docs/wiki/05_market_sector_map_zh.md`
- `docs/wiki/ai/answer_checklist_zh.md`
- `docs/wiki/ai/llm_controller_discipline_zh.md`
- `docs/wiki/ai/low_model_boundary_zh.md`

These should not all become `wiki/principles/README.md`.

Suggested mapping:

- system overview -> `wiki/inbox/system/` or `system/architecture` candidate
- AI usage protocol -> `agents/` or `system/checks/`
- portfolio framework -> `framework.md` or `wiki/principles/`
- daily workflow -> `system/workflows/`
- company research method -> `wiki/methodologies/`
- market sector map -> `wiki/industries/`
- AI answer checklist / LLM discipline / low model boundary -> `agents/` and `system/checks/`

### P1: Treat `.env` And Secret-Like Files As Sensitive

The manifest includes:

- `.env`
- `.env.template`
- files with `KEY` / `KEYS` in the name

They are currently marked `candidate_archive_later`.

This is too loose.

Suggested action:

- `.env` -> `sensitive_do_not_copy`
- `.env.template` -> `candidate_runtime_config_template`
- `*KEY*.csv` cache files -> likely `ignore_generated` unless proven otherwise

No secret-bearing file should be copied into `investing-os`.

### P1: Fill Or Normalize Empty `suggested_destination`

There are many entries where `suggested_destination` exists as a field but is empty.

That may be acceptable for generated files, but the manifest should make that explicit.

Suggested convention:

- generated output -> `null`
- ignored cache -> `null`
- code refactor candidates -> `stock_team/<target-area>`
- archive candidates -> `stock_team/archive/<category>/`
- sensitive files -> `null`

### P2: `candidate_archive_later` Is Too Broad

1137 files are marked `candidate_archive_later`.

That bucket is too large for later decision-making.

Suggested split:

- `candidate_archive_generated`
- `candidate_archive_legacy_script`
- `candidate_archive_old_report`
- `candidate_archive_runtime_snapshot`
- `sensitive_do_not_copy`
- `unknown_review_required`

### P2: Runtime Config Needs Subclassification

20 files are marked `candidate_runtime_config`.

Before Phase 4, split them into:

- portfolio state
- watchlist
- tactical parameters
- market regime
- server/app config
- generated or historical config

`positions.json` and `target_orders_rebalance.json` require extra care because they may represent account state or intended action.

## Approval

Approved for Phase 1 only, with constraints.

Phase 1 may:

- create `wiki/inbox/README.md`
- define import templates
- update classification rules
- produce a corrected inventory manifest if needed

Phase 1 must not:

- copy source assets yet
- delete anything
- modify `stock_team`
- import `.env` or secret-like files
- move directly into Phase 2

## Stop Condition

After Phase 1, stop and submit:

- revised import contract
- corrected destination mapping
- sensitive-file handling rule
- updated manifest if classification logic changed

