# Stage Context Backtest Contract

This contract defines how investing-os asks stock_team to validate Stage 0 /
Stage 1 environment and plan context.

stock_team produces evidence only. It must not approve a tactic, change a
permission state, mutate dashboard config, or write trade instructions.

## Runtime Boundary

`stage-context-backtest` is research/review only.

It must not run during intraday trading runtime, dashboard refresh, or updater
loops. The intraday dashboard may display frozen Stage 0 / Stage 1 packet
readiness and runtime facts, but it must not call this command, optimize
contexts, change labels, or regenerate Stage 0 / Stage 1 anchors.

Historical intraday trigger events may appear in a request only as completed
research/review evidence. They are not live runtime inputs.

The packet is intended for investing-os validation records, post-market review,
weekend research, and explicit strategy-evolution work.

## Purpose

`stage-context-backtest` is not an intraday entry optimizer. It measures whether
pre-market context labels are associated with different tactic outcomes.

Examples of context labels:

- QQQ regime
- VIX regime
- market volume regime
- sector or theme regime
- catalyst bucket
- cognition state echo
- permission state echo

## Macro/Stage 0/1 Entry Boundary

When the research question is about Stage 0, Stage 1, macro context, broad
market permission, candidate-pool selection, or whether a strategy should be
allowed into the operating system, stock_team must use this macro/stage-context
research path first.

The default outcome model for macro/stage research is forward 3D / 5D / 10D / 20D returns, plus multi-day drawdown and adverse excursion evidence.

Macro/stage research guardrails:

- It must not use intraday-only exits.
- It must not use fixed 1%-2% take-profit or stop-loss assumptions.
- It must not force same-day exit unless the request explicitly says the study
  is an intraday tactic execution study.

Use `tactic-backtest` only after the macro/stage gate is already defined and
the question is explicitly about the intraday trigger, execution timing, or
microstructure of that accepted tactic.

## CLI

```powershell
python -m stock_team.cli stage-context-backtest `
  --request "C:\Users\rriww\Documents\investing-os\system\data\requests\YYYY-MM-DD-stage-context-backtest-request.json" `
  --out "C:\Users\rriww\Documents\investing-os\system\data\packets\stage-context-backtest-evidence-packet.md" `
  --json-out "C:\Users\rriww\Documents\investing-os\system\data\packets\stage-context-backtest-evidence-summary.json"
```

## Request Shape

Required fields:

- `artifact_type`: must be `stage_context_backtest_request`
- `study_id`: study identifier owned by investing-os
- `date_range`: historical window under review
- `context_fields`: ordered list of context labels to segment by
- `data.mode`: `fixture_events` or `joined_fixture_events`
- `data.events`: completed tactic or review events
- `data.events_source`: optional event source; when present, stock_team reads
  events from another evidence packet instead of inline `data.events`
- `data.stage_contexts`: required only for `joined_fixture_events`; daily Stage
  0 / Stage 1 labels keyed by `date`
- `data.stage_context_overlays`: optional investing-os owned daily context
  labels, also keyed by `date`
- `output_contract.allow_recommendations`: must be `false`
- `output_contract.allow_config_mutation`: must be `false`

## Output Shape

Markdown packet:

- YAML header with `packet_type: stage_context_backtest_evidence_packet`
- boundary statement: evidence only
- aggregate metrics
- data-quality metrics
- context-segment metrics
- embedded machine summary JSON

JSON summary:

- same data as the Markdown packet
- intended for investing-os ingestion and lineage tracking

## Boundary Rules

stock_team may calculate:

- event count
- win rate
- average return
- average win/loss
- average MAE/MFE
- context-segment metrics
- tactic-segment metrics
- symbol-segment metrics

stock_team may not calculate or emit:

- permission approval
- final tactic adoption
- position sizing
- account action
- dashboard config mutation
- psychological interpretation

## Relationship To Tactic Backtest

- `stage-context-backtest` answers: under which Stage 0 / Stage 1 contexts did
  tactic outcomes differ?
- `tactic-backtest` answers: within an allowed context, which trigger and risk
  parameters produced which historical outcomes?

The two evidence packets should be read together by investing-os. stock_team
does not combine them into a final action.

## Data Modes

### `fixture_events`

Each event already includes a `context` object. This is useful for contract
tests and downstream ingestion.

### `joined_fixture_events`

The request provides two fixture collections:

- `stage_contexts`: daily context labels from Stage 0 / Stage 1.
- `events`: completed tactic or review events with `date` or `entry_time`.

stock_team joins events to daily context labels by date. If an event has no
matching context, it remains in the evidence set with `unknown` context values
and increments `data_quality.missing_context_events`.

This mode is the bridge toward real historical adapters. It supports three
context sources:

- inline `stage_contexts`
- `stage_context_source.mode = daily_market_fixture`
- `stage_context_source.mode = daily_market_local_cache`

`daily_market_fixture` reads explicit `qqq_csv`, `vix_csv`, and `volume_csv`
paths. `daily_market_local_cache` reads:

- `daily_cache_QQQ.csv`
- `daily_cache_^VIX.csv`
- `daily_cache_SPY.csv`

from the requested `cache_dir`.

If `sector_symbol` is provided, `daily_market_local_cache` also reads
`daily_cache_<sector_symbol>.csv` and derives `sector_regime`. If the cache is
missing, the packet remains valid and records `sector_cache_missing:<symbol>` in
`data_quality.warnings`.

The first market-derived labels are:

- `qqq_regime`
- `vix_regime`
- `market_volume_regime`
- `sector_regime`

## Context Overlays

`stage_context_overlays` is the intended bridge for labels owned by
investing-os, including:

- `catalyst_bucket`
- `permission_state`
- `cognition_state`

stock_team may merge these labels into the same dated context table, but it
must treat them as echoes. It must not infer permission changes, cognitive
state, or catalyst meaning on its own.

Future adapters should add richer catalyst sources without changing the
downstream join and aggregation logic.

## Event Sources

`events_source.mode = tactic_backtest_json` reads events from a
`tactic_backtest_evidence_packet` JSON summary.

This is the preferred integration path:

```text
tactic-backtest JSON events
+ Stage context labels
-> stage-context-backtest evidence packet
```

If events lack `tactic_id`, stock_team copies the root `tactic_id` from the
tactic packet. The source packet remains evidence-only; Stage context backtest
does not reinterpret it as a recommendation.
