# Tactic Backtest Contract

This contract defines how investing-os asks stock_team to validate a tactic.

stock_team produces evidence only. It must not approve a tactic, change a rule,
change a portfolio state, or write trade instructions.

## Runtime Boundary

`tactic-backtest` is research/review only.

It must not run during intraday trading runtime, dashboard refresh, or updater
loops. The intraday dashboard may monitor whether frozen, accepted conditions
pass or fail, but it must not call this command, run parameter sweeps, optimize
entries, or alter rules while the trading day is active.

Historical intraday bars and trigger events may appear in a request only as
completed research/review evidence. They are not live runtime inputs.

The packet is intended for investing-os validation records, post-market review,
weekend research, and explicit strategy-evolution work before any rule is
accepted by the brain.

## CLI

```powershell
python -m stock_team.cli tactic-backtest `
  --request "C:\Users\rriww\Documents\investing-os\system\data\requests\YYYY-MM-DD-tactic-backtest-request.json" `
  --out "C:\Users\rriww\Documents\investing-os\system\data\packets\tactic-backtest-evidence-packet.md" `
  --json-out "C:\Users\rriww\Documents\investing-os\system\data\packets\tactic-backtest-evidence-summary.json"
```

## Request Shape

Required fields:

- `artifact_type`: must be `tactic_backtest_request`
- `tactic_id`: tactic identifier owned by investing-os
- `symbols`: symbols to validate
- `date_range`: requested historical window
- `validation.windows`: train/test or walk-forward segments
- `validation.regime_fields`: fields used for regime segmentation
- `data.mode`: first supported mode is `fixture_events`
- `output_contract.allow_recommendations`: must be `false`
- `output_contract.allow_config_mutation`: must be `false`

## Output Shape

Markdown packet:

- YAML header with `packet_type: tactic_backtest_evidence_packet`
- boundary statement: evidence only
- aggregate metrics
- validation window metrics
- regime segment metrics
- embedded machine summary JSON

JSON summary:

- same data as the Markdown packet
- intended for investing-os ingestion and lineage tracking

## Boundary Rules

stock_team may calculate:

- sample count
- win rate
- average return
- average win/loss
- profit factor
- MAE/MFE
- validation-window metrics
- regime-segment metrics

stock_team may not calculate or emit:

- tactic approval
- portfolio permission
- final rule adoption
- position sizing
- account action
- config mutation

## Data Modes

### `fixture_events`

Use this mode to validate packet shape and downstream ingestion. The request
provides completed trade events directly.

### `intraday_ohlcv_fixture`

Use this mode to validate event generation from intraday OHLCV bars without
network access. "Intraday" here means historical intraday-style bars used for
research/review only, not live intraday execution. The first implemented event
adapter is intentionally narrow:

- tactic: `rs_pullback_rebound_intraday`
- trigger: previous bar below VWAP, current bar reclaims VWAP
- confirmation: current volume ratio above `min_volume_ratio`
- action window: bounded by `action_window_start` and `action_window_end`
- exit: first stop / take-profit touch, otherwise end of day

This mode is for reproducible tests and contract hardening. It is not a data
source for production validation.

### Next Adapter

The next adapter should be Polygon-first:

- read `POLYGON_API_KEY` via existing stock_team data access conventions
- fetch 1m or 5m aggregate bars
- cache raw bars with source and freshness metadata
- convert bars into the same normalized OHLCV shape used by
  `intraday_ohlcv_fixture`
- preserve the same output contract
