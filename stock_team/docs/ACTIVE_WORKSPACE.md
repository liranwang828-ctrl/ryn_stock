# Active Workspace Guide

Date: 2026-06-07

This file defines the active working surface for the investing-os / stock_team
brain-muscle architecture.

## Active Entry Points

- `cli.py`
  - Main contract surface called by investing-os.
  - Current commands include `market-context`, `premarket`, `trade-evidence`,
    `intraday-snapshot`, `company-packet`, `industry-packet`, and
    `tactic-backtest`.

- `backtest/tactic_backtest_system.py`
  - Unified tactic backtest evidence runner.
  - Evidence only. No tactic approval or config mutation.
  - Research/review only. It is not an intraday dashboard producer.

- `docs/tactic-backtest-contract.md`
  - Contract for future tactic backtest extensions.

- `docs/stage-context-backtest-contract.md`
  - Contract for Stage 0 / Stage 1 gate-quality backtest evidence.
  - Research/review only. It must not run during intraday dashboard refresh.

## Runtime Split

- Trading runtime: Stage 0 packet, Stage 1 packet, intraday dashboard, runtime
  price/level/condition/account facts, and latest manifest/HTML output.
- Research/review runtime: `tactic-backtest`, `stage-context-backtest`,
  parameter studies, context quality studies, and validation records.
- The intraday dashboard must not call backtest commands, run optimization, or
  mutate Stage 0 / Stage 1 anchors. It only checks packet readiness and refreshes
  runtime facts.

## Research Entry Rule

- If the question is about macro conditions, Stage 0 / Stage 1, candidate-pool
  selection, or whether a factor/tactic should enter the system, start with
  `stage-context-backtest` style daily/multi-day evidence.
- Macro/stage studies use forward 3D / 5D / 10D / 20D returns and multi-day
  drawdown/adverse excursion evidence.
- Do not model macro/stage questions with intraday ORB/VWAP triggers, fixed
  1%-2% stop/take-profit assumptions, or forced same-day exits.
- Use `tactic-backtest` only when the question explicitly asks about intraday
  trigger execution after the macro/stage gate is already defined.

## Active Directories

- `backtest/`: backtest engines, adapters, and evidence runners.
- `core/`: operational evidence utilities such as trade evidence export,
  IBKR checks, polling, and premarket helpers.
- `data_ingest/`: Polygon, fundamentals, postmarket, and data acquisition code.
- `config/`: runtime configuration and example request contracts.
- `docs/`: active contracts, architecture notes, and implementation guidance.
- `templates/`: active render templates.
- `tests/unit/core/`: current unit tests for CLI and core contracts.
- `reports/dashboard.html`: current stock_team dashboard surface.
- `reports/index.html`: report index.
- `reports/latest_evidence_dashboard.json`: current dashboard data bridge.

## Quarantined Generated Artifacts

Generated outputs and old runtime state were moved to:

```text
archive/cleanup_2026-06-07/
```

Subfolders:

- `root_runtime_state/`
- `findings_generated/`
- `reports_generated/`

Do not move these files back unless there is a specific reason and the reason is
documented in the relevant task or handoff.

## Not Active For New Work

Do not build new workflows around the old agent script paths shown as deleted by
git status, such as `agents/cio.py`, `agents/data_agent.py`, or old root-level
test paths. Those belong to a previous structure and are the source of many
current full-suite failures.

New work should use the active import paths:

- `stock_team.core.*`
- `stock_team.data_ingest.*`
- `stock_team.backtest.*`
- `stock_team.utils.*`
- `stock_team.server.*`

## Verification Baseline

For the current tactic-backtest surface:

```powershell
python -m pytest tests\unit\core\test_tactic_backtest_system.py `
  tests\unit\core\test_cli.py::test_cli_tactic_backtest_generation `
  tests\unit\core\test_cli.py::test_cli_tactic_backtest_ohlcv_fixture_generation `
  tests\unit\core\test_cli.py::test_cli_help -q
```

Expected: `7 passed`.

Full-suite failures currently include old agent-path and legacy import issues.
Do not treat those as regressions from the tactic-backtest work unless the
failing test touches an active file listed above.
