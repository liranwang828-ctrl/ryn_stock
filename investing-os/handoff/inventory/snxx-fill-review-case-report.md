# SNXX Fill Review And Case Report

Date: 2026-06-05

## Summary

Absorbed user-provided broker screenshots for SNXX into a full fill review and historical case.

## Created Files

- `wiki/journals/2026-06-04-snxx-fill-review.md`
- `wiki/historical-cases/CASE-004-snxx-attention-capture.md`

## Updated Files

- `wiki/historical-cases/README.md`
- `cognition/mistake-patterns.md`
- `cognition/emotional-patterns.md`
- `decision/risk-budget.md`
- `decision/decision-log.md`
- `execution/intraday.md`
- `system/checks/short-term-trade-checklist.md`
- `evolution/learning-loop.md`
- `evolution/system-update-log.md`

## Screenshot-Based Fill Summary

Approximate values from visible screenshot data:

```yaml
total_buy_quantity: 650
total_sell_quantity: 650
estimated_buy_amount: 19931.85
estimated_average_buy_price: 30.66
estimated_sell_amount: 19437.00
estimated_average_sell_price: 29.90
visible_realized_pnl: -508.63
round_trip_notional: 39368.85
```

## Main Finding

The trade was not only an averaging-down mistake.

It also showed:

```text
signal entry
|
averaging down
|
partial profitable exits
|
re-risking
|
forced exit
```

## System Lesson

Partial recovery does not reset trade quality.

If the original trade had no thesis, re-entry after partial exit requires a fresh plan.

## Decision State

SNXX remains:

- `blocked_pending_review`

Next review:

- compare against last 20 short-term trades for similar re-risking behavior

