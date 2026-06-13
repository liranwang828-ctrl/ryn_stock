# Execution Intraday

## Purpose

Protect decisions from market pressure.

## Rules

- watch only predefined symbols
- act only on predefined triggers
- do not create thesis from price movement
- do not average down without prewritten add rule
- record emotional impulses instead of obeying them
- blocked symbols cannot be traded
- plan-required symbols require a written plan before action
- VWAP or volume signals can create review, not permission

## Permission States

Intraday execution uses permission states.

| State | Trigger | Allowed | Blocked |
|---|---|---|---|
| Normal | no active emotional or risk breach | planned trades, research, reviews | planless trades |
| Yellow | attention capture or small short-term loss | existing plan execution, risk reduction | new hand-feel trades |
| Orange | any short-term stop-loss, leveraged loss, or repeated checking | risk reduction, prewritten swing actions only | new short-term trades, re-entry attempts |
| Red | major drawdown, principal affected, emotional breakdown, or unresolved high-risk position | reduce unmanaged risk, journal, research | all new risk-taking |
| Recovery | after Red, before user-approved reset | research, review, planned risk repair | leverage, revenge trades, new tactics |

Rule:

Major drawdown automatically moves the system into Red until open risk, emotional state, and next-session plan are reviewed.

## Attention Budget

If continuous monitoring exceeds the attention budget:

1. pause
2. write facts
3. restate thesis
4. restate risk
5. decide whether the trade is still planned

If thesis is missing:

- do not add
- do not widen risk
- close, reduce, or move to review according to plan

## Spillover Guard

Before changing unrelated holdings during a stressful trade, classify the decision:

- thesis change
- planned risk management
- emotional spillover
- unclear

If unclear and not urgent, defer until review.

## Re-Risking Guard

After a partial profitable exit in a low-quality trade:

1. ask whether original thesis existed
2. ask whether trade quality improved or only emotion improved
3. check whether the symbol/underlying has sustained or lost the high area
4. check whether broad market is fading into the close
5. require a fresh plan before re-entry
6. if no fresh plan exists, do not rebuild exposure

Rule:

Partial recovery does not reset trade quality.

Late-session rule:

If it is after 15:30 ET and the trade is below VWAP or the underlying is fading, do not add to a thesis-missing trade.

## Hope Override Guard

If the user notices symbol or peer weakness but wants to continue because it may reverse:

1. stop adding
2. write the adverse evidence
3. write what would make the trade stop now
4. reduce, exit, or move to review if no clear invalidation exists

Rule:

Seeing weakness and hoping for reversal is not a valid add reason.

## Stop-Loss No-Trade Guard

After any failed short-term trade and stop-loss:

1. stop looking for new short-term opportunities
2. write the stop-loss event
3. classify the emotional state
4. allow only risk reduction or prewritten swing-plan execution
5. wait until next session or explicit review reset before new short-term trades

Rule:

A short-term stop-loss means hand-feel is impaired for the rest of the session.
