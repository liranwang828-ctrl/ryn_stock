# Execution Pre-Market

## Purpose

Turn decision state into a concrete plan before the market creates pressure.

## Required Checks

- file growth health check completed with `./tools/check-file-growth.ps1`
- portfolio thesis reviewed
- position roles reviewed
- risk budget reviewed
- watchlist states reviewed
- no-trade conditions written
- blocked symbols confirmed
- plan-required symbols have explicit plan or no action
- theme trades have been converted into symbol, horizon, invalidation, add rule, re-entry rule, and attention budget

## Output

Use:

- `templates/trading-day-plan.md`
- `templates/pre-market-plan.md`

## Stock Team Input

If `stock_team` provides pre-market output, it enters through:

- `system/data/packets/pre-market-packet.md`

It must be reviewed before becoming a plan.

## Current Hard No-Trade

- SNXX until full 2026-06-04 trade review is complete

## Current Plan-Required Symbols

- COHR
- ORCL
- INTC

These require review of thesis, risk, and possible emotional spillover before any new action.
