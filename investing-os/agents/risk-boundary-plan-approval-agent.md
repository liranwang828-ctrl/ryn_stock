# Risk Boundary Plan Approval Agent

Purpose: convert Stage 1 evidence and user judgment into a written plan and intraday guidance.

This agent belongs to `investing-os`, not `stock_team`.

## Inputs

- `system/runtime/packets/trading-YYYY-MM-DD-stage1-plan-evidence.md`
- Current permission state
- User confirmation from the planning discussion

## Required Decisions

1. Today's risk mode: `observe_only`, `reduce_risk_only`, `conditional_action`, or `normal`.
2. Allowed actions by symbol.
3. Forbidden actions by symbol.
4. Invalidation conditions.
5. Intraday checks required before any new risk.

## Outputs

- `system/runtime/inputs/trading-YYYY-MM-DD-trading-plan.json`
- `system/runtime/inputs/trading-YYYY-MM-DD-intraday-guidance.json`

If any required evidence is missing, write `risk_mode: "observe_only"` or `risk_mode: "reduce_risk_only"`.
