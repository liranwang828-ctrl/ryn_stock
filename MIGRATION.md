# Unified Workspace Migration

Date: 2026-06-13

## Method

The two systems were copied into `C:\Users\rriww\Documents\STOCK`; the source
directories were not moved or modified. This permits verification and rollback
without data loss.

## Included

- investing-os documents, workflows, templates, cognition records, and examples
- stock_team source code, tests, documentation, templates, configuration rules,
  static dashboard assets, and compact knowledge files
- learning module source files, excluding generated learning datasets

## Excluded

- `.env` and credentials
- broker/account runtime state
- SQLite, pickle, parquet, and large historical CSV datasets
- generated `findings`, caches, logs, scratch files, and archived runtime output
- paper-trading account state and latest generated dashboard manifests

## Compatibility

Runtime code resolves `investing-os` through `INVESTING_OS_HOME` when set and
otherwise uses the directory beside `stock_team`. Historical documents may
still mention old absolute paths because they describe prior runs rather than
active runtime configuration.

## Verification Record

- CLI contract suite: 34 passed on 2026-06-13.
- Replay Stage 0 generated a packet with complete brain preconditions.
- Replay Stage 1 derived from the new workspace Stage 0 path and preserved the
  Yellow permission echo for INTC, MU, and COHR.
- Intraday dashboard generated JSON, Markdown, and HTML outputs from the new
  workspace paths.
- Replay market data remained degraded/fallback data; this validates workflow
  wiring, not production data quality.
- File growth check retained one pre-existing soft-limit warning for
  `investing-os/system/closed-loop-operating-architecture.md` at 391 lines.

The bundled verification interpreter did not already contain `ib_insync`.
`stock_team/requirements.txt` now declares that runtime dependency; IBKR import
verification requires installing the repository requirements.
