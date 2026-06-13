# Repository Hygiene Rules

Last updated: 2026-05-31

This repo mixes trading source code, local market data, generated reports, and daily operating state. Keep those categories separate. A clean repo should let any teammate answer two questions quickly:

1. What code/config/docs changed?
2. What runtime artifacts were produced locally but should not be committed?

## Commit These

- Source code under `agents/`, `scripts/`, `tools/`, and `templates/`.
- Tests under `tests/`.
- Durable configuration under `config/` when it represents team-agreed behavior.
- Durable methodology or operating docs under `docs/` and `knowledge/`.
- Small curated examples that are intentionally used by tests or documentation.

## Do Not Commit These

- Secrets and local environment files: `.env`, `.env.*`.
- Python and test caches: `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`.
- Generated dashboards and transient reports: most `reports/*.html` outputs.
- Generated findings and learning logs: `findings/`, `learning/`.
- Daily operating snapshots: `daily_plan_*.json`, `daily_checklist_*.json`, `premarket_analysis_*.json`, `session_state_*.json`.
- Large downloaded market data, scratch files, and research package exports.

## Before Commit

Run:

```powershell
python scripts/check_repo_hygiene.py
git status --short
```

Then run focused tests for the files you touched. For dashboard and backtest work, the current smoke set is:

```powershell
python -m pytest tests\test_dashboard_cache.py tests\test_dashboard_experience_loop.py tests\test_dashboard_experience_paths.py tests\test_dashboard_refresh_prices.py tests\test_dashboard_writer.py tests\test_portfolio_health.py tests\test_premarket_consensus_lock.py tests\test_refresh_prices_focus.py tests\test_backtest_engine.py tests\test_backtest_macro.py tests\test_backtest_micro.py tests\test_backtest_result.py -q
```

If full `pytest` hangs or times out, report that fact plainly and include the focused verification command that did pass.

## Cleanup Policy

Safe to delete any time:

- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.coverage`
- `htmlcov/`

Do not delete without explicit human confirmation:

- `.env`
- `findings/`
- `learning/`
- `archive/`
- `research_package/`
- any `portfolio`, `positions`, or trading history file

## Naming Discipline

- New reusable tools go in `scripts/` only when they are command-line workflows.
- New agent modules go in `agents/` only when they are called by the trading workflow or dashboard.
- New long-lived rules go in `docs/` or `knowledge/`.
- New generated outputs should land in an ignored directory or match an ignored pattern before the generating script is committed.

## Documentation Language

- For new design specs, plans, and durable methodology notes, include a Chinese version or Chinese summary when saving the document.
- Prefer Chinese-first explanations for user-facing trading workflow docs. English can remain for code-facing names, schemas, and implementation details.
- If a document is bilingual, keep the Chinese section near the top so it is easy to review before implementation.

## If The Repo Gets Messy

1. Run `git status --short`.
2. Run `python scripts/check_repo_hygiene.py`.
3. Add missing ignore rules for generated artifacts.
4. Commit source/config/docs/test changes together with the rule that prevents future pollution.
5. Only remove ignored local files when they are clearly cache files or the human explicitly asked to purge them.
