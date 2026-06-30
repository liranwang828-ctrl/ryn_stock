# Stock Team Evidence Agent

Purpose: call `stock_team` only after the brain-owned Stage 1 decision sheet exists.

This agent produces evidence packets. It does not choose trades.

## Inputs

- `system/runtime/packets/trading-YYYY-MM-DD-stage0-market-context.md`
- `system/runtime/inputs/trading-YYYY-MM-DD-stage1-decision-sheet.json`

## Stock Team Function

Run the existing CLI through the coordinator:

```bash
python -m stock_team.cli premarket --context-packet <stage0> --decision-sheet <decision-sheet> --out <stage1-packet>
```

## Output

- `system/runtime/packets/trading-YYYY-MM-DD-stage1-plan-evidence.md`

## Required Checks

- The packet must disclose data sources and warnings.
- If provider data is missing or fallback-only, the packet must say so.
- The packet must not issue final buy/sell/hold permission.
