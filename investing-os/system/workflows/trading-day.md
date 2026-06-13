# Trading Day Workflow

This workflow is designed for a timezone where workday daytime is offset from US trading hours.

## Core Rhythm

```text
After work = pre-market
Before sleep = risk lock
During market = mostly asleep, system-assisted
Morning/daytime = asynchronous review
Weekend = deep review and research
```

## After Work: Pre-Market Plan

Time budget: 30-60 minutes.

Purpose: make decisions before the market creates emotional pressure.

Steps:

1. Review holdings for material information.
2. Review watchlist for predefined triggers.
3. Check major market events.
4. Decide whether trading is allowed tonight.
5. Write planned actions.
6. Write no-trade conditions.
7. Set alerts if needed.
8. Confirm risk if sleeping through market hours.

Do not produce trade conclusions if required fresh data is missing.

Minimum context to check:

- QQQ / SPY / VIX
- current holdings
- today's watchlist
- sector mainlines
- fresh pre-market or decision-state notes when available

Output:

- `templates/trading-day-plan.md`

## Before Sleep: Risk Lock

Time budget: 5-10 minutes.

Steps:

1. Check open orders.
2. Check position risk.
3. Check whether any position affects sleep.
4. Remove emotional or unnecessary orders.
5. Confirm no unplanned action is needed.

Output:

- Sleep-before-risk section in `templates/trading-day-plan.md`

## During Market: Low Intervention

Rules:

- Do not invent new trades.
- Do not act on new signals unless already covered by the plan.
- Let alerts create review tasks, not emotional actions.
- Serve only existing plans, new confirmed catalysts, new confirmed structures, or user-initiated risk checks.
- Do not actively expand unrelated candidate pools during market hours.

## Morning Or Daytime: Asynchronous Review

Time budget: 15-45 minutes when available.

Light review:

- What happened?
- Did the plan execute?
- Did anything affect thesis or risk?

Full review:

- Update journal.
- Update thesis.
- Update risk notes.
- Update wiki if there is durable learning.

Minimum review data when available:

- intraday chart
- OHLC / VWAP / intraday position
- recent 5/10 day structure
- QQQ same-day behavior
- relevant sector or peer behavior

## If Review Was Missed

Before the next pre-market plan, complete a short catch-up review.

No new plan should be written on top of an unreviewed prior day if material events occurred.
