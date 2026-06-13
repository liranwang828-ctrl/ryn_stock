# Stage Context Backtest Design

## Goal

Build the first evidence-only backtest layer for Stage 0 / Stage 1 gate quality.
This layer validates whether pre-market environment and plan labels are
associated with different tactic outcomes. It does not optimize a live entry
point or approve trading permission.

## Architecture

The system has two distinct backtest layers:

- `stage-context-backtest`: validates environment, catalyst, cognition, and
  permission-state context labels.
- `tactic-backtest`: validates concrete intraday triggers such as VWAP reclaim,
  breakout, volume confirmation, and exit models.

The first implementation accepts `fixture_events` and `joined_fixture_events`.
In `fixture_events`, each event contains a completed tactic outcome plus a
`context` object. In `joined_fixture_events`, daily Stage 0 / Stage 1 labels are
provided separately and joined to tactic events by date.

## Data Flow

```text
investing-os stage context study request
-> stock_team stage-context-backtest
-> aggregate metrics
-> context segment metrics
-> evidence-only Markdown and JSON packet
-> investing-os interpretation and possible rule review
```

## Boundary

stock_team may calculate event metrics and context segment statistics. It may
not approve tactics, change permission state, mutate dashboard config, or write
trade instructions.

## First Slice

The first slice supports:

- fixture event ingestion
- joined fixture ingestion by date
- forbidden request-key validation
- aggregate event metrics
- context segment metrics
- data-quality metrics for missing Stage context
- tactic and symbol segment metrics
- CLI output to Markdown and JSON

The next slice should derive context labels from historical Stage 0 / Stage 1
packets and pair them with real tactic backtest events.
