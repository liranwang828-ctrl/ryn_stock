# Data

This directory is reserved for data-source definitions, schemas, and local data notes.

Do not store secrets here.

Potential future sources:

- Financial statements
- Price data
- News feeds
- Filings
- Watchlists
- Portfolio snapshots

## Contracts

- `runtime-snapshot-contract.md`: boundary for exporting validated rules from `investing-os` to `stock_team` / `lianghua`.
- `runtime-parameter-map.md`: human-readable map from principles to candidate runtime parameters.
- `schemas/tactical-rules.schema.json`: JSON Schema for tactical rule snapshots.
- `schemas/risk-limits.schema.json`: JSON Schema for risk boundary snapshots.
- `schemas/watchlist-metadata.schema.json`: JSON Schema for symbol role and watchlist metadata snapshots.
- `schemas/signal-interpretation.schema.json`: JSON Schema for interpreting market signals as review inputs, not commands.
- `schemas/degraded-mode.schema.json`: JSON Schema for fail-closed runtime degradation behavior.
- `snapshots/examples/tactical-rules.example.json`: example draft snapshot, not approved for runtime use.
- `snapshots/examples/risk-limits.example.json`: example risk limits snapshot, not approved for runtime use.
- `snapshots/examples/watchlist-metadata.example.json`: example watchlist metadata snapshot, not approved for runtime use.
- `snapshots/examples/signal-interpretation.example.json`: example signal interpretation snapshot, not approved for runtime use.
- `snapshots/examples/degraded-mode.example.json`: example degraded-mode snapshot, not approved for runtime use.
- `snapshots/`: draft, active, retired, example, approval, and changelog structure for runtime snapshots.
- `packets/`: review-envelope contracts for incoming outputs from `stock_team`, ChatGPT, or manual research.
