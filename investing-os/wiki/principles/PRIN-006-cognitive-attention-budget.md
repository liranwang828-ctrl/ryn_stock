# PRIN-006: Cognitive Attention Budget

## Metadata

- ID: PRIN-006
- Title: Cognitive Attention Budget
- Version: 1.0
- Status: active
- Created: 2026-06-05
- Updated: 2026-06-05
- Source: `wiki/journals/2026-06-04-daily-review.md`

## Core Assertion

A low-conviction short-term trade must not receive more attention than core positions or high-conviction thesis work.

Attention is a risk budget.

## Why It Exists

Capital exposure can look small while cognitive exposure becomes large.

A small short-term position can still damage the system if it captures attention, delays sleep, creates emotional spillover, or forces decisions in unrelated holdings.

This principle exists to manage cognitive position sizing, not only financial position sizing.

## Trigger Conditions

Apply this principle when:

- a short-term trade is being monitored continuously
- the trade lacks a written thesis
- the user starts adding to lower cost
- attention shifts from the portfolio to one low-conviction ticker
- sleep or next-day judgment may be affected
- a single trade begins influencing unrelated sell decisions

## Execution Constraints

Before any short-term trade, define:

- thesis
- trigger
- maximum loss
- invalidation condition
- add rule
- maximum attention budget

If attention exceeds the budget, pause and record:

- facts
- current thesis
- risk
- whether the trade is still planned

If no thesis exists, the trade may be closed, reduced, or moved to review, but it must not receive unlimited attention.

## What This Principle Forbids

- Turning a signal into a thesis
- Turning a losing trade into a cost-reduction project
- Adding because price fell without thesis strengthening
- Letting a single low-conviction position hijack sleep
- Letting one short-term trade spill into unrelated portfolio decisions

## Falsification Or Revision Conditions

Revise this principle only if repeated journal reviews show that focused monitoring of low-conviction short-term trades improves decisions without increasing emotional risk, sleep risk, or spillover risk.

Do not revise it because one monitored trade eventually recovered.

## Drift Audit

- Did the position size look small while attention size became large?
- Did the trade affect sleep?
- Did the user keep watching because of plan or because of loss aversion?
- Did the trade affect decisions in unrelated positions?
- Was add behavior planned before entry?

## Related Cases

- `wiki/journals/2026-06-04-daily-review.md`

## Related Workflows

- `system/checks/short-term-trade-checklist.md`
- `templates/trade-plan.md`
- `templates/trading-day-plan.md`
- `system/workflows/trading-day.md`

## Runtime Parameters

Candidate parameters:

- maximum continuous monitoring time
- maximum number of unplanned checks per trade
- maximum short-term trade size without written thesis
- maximum allowed adds without prewritten add rule

These parameters are reviewable and should be validated through journals before becoming runtime rules.

