# Runtime Parameter Map

## Purpose

Map durable principles to candidate runtime parameters.

This map is not an execution config.

It is the human-readable bridge between `wiki/principles/` and exported tactical rule snapshots.

## Status

Current status: draft.

No runtime system should consume these parameters yet.

## Principles To Runtime Candidates

| Principle | Runtime rule ID | Candidate parameters | Status | Evidence |
|---|---|---|---|---|
| PRIN-001 | `leveraged_tool_discipline` | requires underlying structure check; requires max holding duration; requires stop condition | provisional | PRIN-001 |
| PRIN-002 | `hand_feel_trade_limit` | chart/volume/VWAP confirmation required; time-window check; max trades per day TBD | provisional | PRIN-002, CASE-002 |
| PRIN-003 | `profit_taking_cooling_period` | first take-profit ratio 20%-30%; cooling period 15-30 minutes; valid follow-up sell triggers | provisional | PRIN-003, CASE-001 |
| PRIN-004 | `sector_sympathy_rules` | catalyst scope required; peer confirmation required; chart/volume/VWAP confirmation required | provisional | PRIN-004 |
| PRIN-005 | `vwap_volume_confirmation` | relative volume threshold; breakout volume multiple; pullback volume contraction range; underlying VWAP check for leveraged products | provisional | PRIN-005, CASE-002, CASE-003 |
| PRIN-006 | `cognitive_attention_budget` | max continuous monitoring minutes; pause after attention breach; add rule before averaging down | provisional | PRIN-006, 2026-06-04 daily review |

## Parameter Status Definitions

### provisional

The parameter came from source notes, user review, or initial principle design.

It is not validated enough to become a hard runtime rule.

### journal_validated

The parameter has repeated support from manual trading journals.

### backtest_validated

The parameter has quantitative support from tests or backtests where the domain allows it.

### manual_guardrail

The parameter is a behavioral or safety boundary that should not be optimized only for return.

## Export Rule

Runtime snapshots may include provisional parameters, but must mark them clearly.

Tools consuming snapshots must treat provisional parameters as alerts or monitor-only unless explicitly approved.

## No Direct Wiki Runtime Rule

`stock_team` / `lianghua` should never read `wiki/principles/*.md` directly at runtime.

They may consume only schema-validated snapshots.

