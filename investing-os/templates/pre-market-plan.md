# Pre-Market Plan Template

---
date:
session_id:
primary_topics:
  - topic_id:
    topic_name:
    priority:
---

## Pre-Market / 盘前

- Overnight information:
- Market context:
- Focus symbols:
- Key levels or events:

## Topic Review

### Topic

- Questions:
- Evidence:
- Counter Evidence:
- Hypotheses:
- Confidence:
- Next Validation:

## Planned Actions

- If evidence strengthens:
- If evidence weakens:
- If nothing confirms:

## Pre-Authorized Actions

These are not orders. They define what may be considered intraday if every condition remains true.

| Symbol | Topic | Scope | Tactic | Max Loss | Position Cap | Stale Data Limit | Slippage Limit | Manual Confirm |
|---|---|---|---|---:|---:|---:|---:|---|
|  |  | evidence_only / one_preplanned_entry / staged_swing_entry / preplanned_reduce_risk |  |  |  |  |  | yes |

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

- Break thesis confidence:
- Counter evidence overwhelms:
- Validation missing:

## Discipline Reminder

Pre-market and post-market matter most.

Intraday should execute the plan, not invent a new personality.
