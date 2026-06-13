# Risk Budget

## Purpose

Define risk as more than capital exposure.

Risk includes:

- capital risk
- thesis risk
- liquidity risk
- event risk
- attention risk
- sleep risk
- emotional spillover risk

## Current Guardrails

### Attention Budget

Low-conviction short-term trades must not receive more attention than core holdings.

Reference:

- `wiki/principles/PRIN-006-cognitive-attention-budget.md`

Operating rule:

- if a low-conviction trade is watched continuously for more than 30 minutes, pause and restart with fact / thesis / risk
- if thesis is missing, do not add
- if sleep is threatened, reduce, close, or explicitly accept risk before sleep

### Plan Requirement

No short-term trade without:

- thesis
- trigger
- maximum loss
- invalidation
- add rule
- attention budget

If any item is missing, the trade is `no_trade`.

### Sleep Risk

If a position cannot be safely held while sleeping, it requires reduction, closure, or explicit risk acceptance before sleep.

### Emotional Spillover Risk

If one trade may be influencing unrelated holdings:

- freeze new discretionary actions
- label decisions as thesis, risk, or emotion
- defer non-urgent actions until review

Reference:

- `wiki/journals/2026-06-04-daily-review.md`

Nuance:

Emotional spillover can accidentally reduce risk.

It is still not clean risk management.

When it happens, classify:

- process quality
- outcome quality
- whether the same action would be taken under a clean state

### Blocked Symbol Risk

SNXX is blocked pending full review.

No new action is allowed unless a new plan includes:

- thesis
- trigger
- maximum loss
- invalidation
- add rule
- attention budget
- sleep-risk decision

### Re-Risking After Partial Recovery

If a low-quality or thesis-missing trade receives a partial profitable exit:

- default action is risk reduction
- re-entry requires a new plan
- prior recovery does not validate the original trade

Forbidden:

- rebuild exposure because the trade "almost worked"
- treat partial recovery as thesis confirmation
- use realized partial gain as emotional permission to continue

### Implicit Thesis Risk

A real investment view is not enough for a short-term trade.

Before action, theme must become:

- concrete symbol thesis
- time horizon
- position size
- invalidation
- add rule
- re-entry rule
- attention budget

If any are missing, the trade remains `plan_required`.

### Hope Override Risk

If adverse evidence is noticed but the user continues because of hope:

- no add is allowed
- fresh invalidation must be written
- attention budget is considered breached
- trade moves to reduce/exit/review mode

## Update Rule

Risk limits should be updated only from:

- repeated journal evidence
- explicit manual guardrail decision
- reviewed portfolio-level risk change
