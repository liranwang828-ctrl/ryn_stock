# Pre-Market Plan Template

## Date

## Overnight Information

## Market Context

## Watchlist

## Key Levels Or Events

## Planned Actions

## Pre-Authorized Actions

These are not orders. They define what may be considered intraday if every condition remains true.

| Symbol | Scope | Tactic | Max Loss | Position Cap | Trigger Window | Stale Data Limit | Slippage Limit | Manual Confirm |
|---|---|---|---:|---:|---:|---:|---:|---|
|  | evidence_only / one_preplanned_entry / staged_swing_entry / preplanned_reduce_risk |  |  |  |  |  |  | yes |

## Fast Consistency Check

This check should take 5-10 seconds. It does not reopen the thesis.

- data_fresh:
- same_permission_state:
- no_exception_triggered:
- position_cap_not_exceeded:
- daily_loss_limit_not_exceeded:
- not_repair_trading:

## Intraday Exception Rules

| Exception | Trigger | Effect |
|---|---|---|
| market_breakdown |  | pause_for_brain_review / downgrade_to_red / no_trade |
| data_stale |  | pause_for_brain_review |
| account_mismatch |  | pause_for_brain_review |
| repair_motive |  | no_trade |

## No-Trade Conditions

## Discipline Reminder

Pre-market and post-market matter most.

Intraday should execute the plan, not invent a new personality.
