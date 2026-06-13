# Tactics

Purpose:

Define repeatable trading tactics that may be activated by the brain after evidence review.

A tactic is not active just because it is documented.

## Core Rule

```text
No tactic enters pre-market or intraday pass/fail monitoring unless its required factors are documented and its validation record exists.
```

## Statuses

| Status | Meaning | Allowed Use |
|---|---|---|
| candidate | idea or imported pattern | research only |
| paper_test | can be monitored without live action | dashboard observation |
| limited_live | small user-approved live use | restricted execution |
| approved | validated enough for normal planning | pre-market activation allowed |
| disabled | temporarily blocked | no new use |
| retired | abandoned | archive only |

## Current Tactics

| Tactic | Status | Notes |
|---|---|---|
| `rs-pullback-rebound-candidate.md` | evidence_received_pending_review | Original broad candidate from review/backtest evidence |
| `rs-pullback-rebound-intraday.md` | paper_test | Strict intraday-only sleeve-based version |

## Required Files Per Tactic

Each tactic should have:

- tactic definition
- factor role matrix
- validation record
- activation rules
- disabled conditions
- post-market review requirements

