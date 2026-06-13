# Branch Report: Stock Team Orchestration Verification

Date: 2026-06-05

## Summary

Created the verifiable mechanism for `investing-os` to orchestrate `stock_team` evidence calls.

The user can start from `investing-os`.

`stock_team` remains the evidence/tooling layer.

## Created Files

- `system/workflows/stock-team-orchestration.md`
- `system/data/packets/contextual-trade-evidence-packet.md`
- `integrations/stock-team-call-log.md`
- `execution/weekly-use-cases.md`

## Updated Files

- `system/data/packets/README.md`
- `integrations/README.md`
- `system/workflows/README.md`
- `USAGE.md`
- `execution/README.md`

## Trust Mechanism

Every `stock_team` call must leave:

- call log entry
- inputs
- command/script used
- output artifact path
- data source
- missing data
- downstream use

## First Logged Call

The SNXX contextual review call was logged in:

- `integrations/stock-team-call-log.md`

It used:

- `stock_team/.env`
- Polygon 1-minute aggregates API
- symbols: SNXX, SNDK, QQQ, SPY
- date: 2026-06-04

## Weekly Use Cases Covered

- pre-market planning
- intraday check
- post-market review
- contextual trade review
- company analysis
- industry analysis
- weekly summary
- learning / mistake pattern review

## Rule

The user should not need to coordinate two systems manually.

The user asks `investing-os`.

`investing-os` decides whether `stock_team` evidence is needed and records the call.

