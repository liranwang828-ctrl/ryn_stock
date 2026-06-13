# Closed-Loop Operating Architecture

Date: 2026-06-07

Purpose:

Define the complete closed loop between `investing-os` and `stock_team`.

This is the current operating blueprint for:

- company / industry research
- pre-market planning
- intraday guidance
- stock_team evidence dashboard
- post-market review
- event reconstruction
- periodic tactic summary
- absorption into the cognition system

## Core Boundary

`investing-os` is the brain.

It owns:

- WHY / constitution
- cognition system
- decision rules
- permission state
- thesis / falsification
- risk boundary
- user-facing operating console
- final interpretation
- absorption into knowledge

`stock_team` is the muscle.

It owns:

- factual evidence packets
- Polygon / IBKR / cache data access
- calculations
- condition pass / fail
- data freshness
- dashboards for evidence readiness
- event reconstruction
- tactic statistics

`stock_team` must not output:

- buy / sell / hold recommendation
- permission approval
- final thesis adoption
- psychological interpretation
- principle update
- live execution controls

## Whole-System Flow

```text
company / industry research
|
company dossier / thesis candidate / monitoring plan
|
pre-market Stage 0 market context
|
focus pool discussion
|
pre-market Stage 1 decision sheet
|
stock_team plan evidence packet
|
intraday guidance artifact
|
stock_team evidence dashboard + runtime snapshots
|
post-market trade evidence packet
|
user interview + cognitive review
|
event reconstruction if needed
|
lesson candidates
|
absorption decision
|
daily report / HTML / dashboard / lineage
|
periodic tactic summary
|
tactic / checklist / risk-budget / cognition updates
```

## 1. Research Loop

Purpose:

Build the cognitive base before any trade plan exists.

Brain artifacts:

- `templates/company-research.md`
- `templates/industry-research.md`
- `system/workflows/company-research.md`
- `system/workflows/company-dossier-lifecycle.md`
- `system/workflows/industry-dossier-lifecycle.md`

Muscle packets:

- `system/data/packets/company-research-packet.md`
- `system/data/packets/industry-research-packet.md`

Research outputs may update:

- `wiki/companies/`
- `wiki/industries/`
- `decision/current-watchlist.md`
- thesis candidates
- falsification maps
- monitoring plans

Rule:

A company report does not authorize a trade.

It can only become:

- research candidate
- dossier draft
- thesis candidate
- active dossier after review

## 2. Pre-Market Loop

### Stage 0: Market Context

Brain gives:

- allowed universe from positions / watchlist / researched names
- themes to contextualize

Muscle returns:

- QQQ / SPY / IWM / VIX proxy facts
- sector / theme heat
- recent market behavior
- universe relevance map
- catalyst facts if available
- missing data / freshness

Contract:

- `system/data/packets/pre-market-context-packet.md`

Canonical physical path:

- `C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`

Stage 0 must not select symbols or grant permission.

### Stage 1: Decision Sheet

Brain and user choose the focus pool.

Brain writes:

- `templates/pre-market-decision-sheet.json`

Required for any intraday conditional action:

- `pre_authorized_actions`
- `fast_consistency_check`
- `exception_rules`
- `risk_budget`
- `forbidden_actions`

Muscle returns:

- `system/data/packets/plan-evidence-packet.md`

Stage 1 reads the canonical Stage 0 packet by default:

- `C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`

If pre-authorized action fields are missing, intraday mode defaults to:

- `observe_only`
- `reduce_risk_only`

## 3. Intraday Loop

Brain writes the intraday guidance artifact:

- `templates/intraday-guidance-to-stock-team.json`

Demo:

- `system/simulations/inputs/intraday-guidance.NVDA-conditional.demo.json`

The artifact defines:

- symbols in scope
- intraday mode
- permission state
- pre-authorized scope
- max loss
- position cap
- required evidence conditions
- levels to monitor
- exception rules
- forbidden UI labels

Supported intraday modes:

- `observe_only`
- `conditional_action_allowed`
- `reduce_risk_only`

Supported permission scopes:

- `evidence_only`
- `one_preplanned_entry`
- `staged_swing_entry`
- `preplanned_reduce_risk`

Muscle dashboard displays only:

- condition pass / fail / partial / stale / missing
- VWAP / RS / ATR / volume / benchmark facts
- data freshness
- missing data
- packet readiness
- latest packet links

Muscle dashboard must not display:

- buy / sell / hold
- can trade
- should enter
- permission approved
- direct execution controls

Latest dashboard manifest:

- `integrations/stock-team-latest-dashboard-manifest.md`

Stable path expected from `stock_team`:

```text
D:\gemini\lianghua\stock_team\reports\latest_evidence_dashboard.json
```

## 4. Fast Consistency Check

Fast check exists to avoid slow re-analysis when a pre-authorized setup triggers.

It should answer:

```text
Is this still the same trade that was pre-authorized?
```

Required checks:

- data fresh
- same permission state
- no exception triggered
- position cap not exceeded
- daily loss limit not exceeded
- not repair trading

If all pass, the brain may show:

```text
pre-authorized conditions remain valid; user confirmation still required
```

If any fail:

```text
pause_for_brain_review
```

## 5. Intraday Exception Rules

Exception rules are defined by the brain before or during plan review.

Common examples:

- QQQ / SPY high-volume breakdown
- VIX proxy spike
- sector confirmation flips negative
- condition pass becomes stale
- IBKR position mismatch
- daily loss limit breach
- position cap breach
- repair / revenge motive
- user tries to change tactic intraday

Muscle may detect:

```yaml
exception_detected: true
exception_type:
requires_brain_review: true
```

Only the brain changes permission state.

## 6. Post-Market Trade Evidence Loop

Before cognitive review, stock_team should provide objective evidence.

Brain request:

- `templates/post-market-trade-evidence-request.json`

Muscle packet:

- `system/data/packets/post-market-trade-evidence-packet.md`

Must include:

- IBKR orders / fills / positions / P&L / commissions / exposure when connected
- full-day market tape: QQQ / SPY / IWM / VIX proxy
- full-day sector / theme tape
- full-day traded-symbol tape
- VWAP / volume / RS / key levels
- opening 30-minute structure
- key intraday nodes
- fill overlay against market / sector / VWAP / volume context
- planned vs actual alignment
- data quality

Opening 30 minutes must split:

- `0-5m`
- `5-15m`
- `15-30m`

Each window should include:

- OHLC
- cumulative volume / relative volume
- VWAP relationship
- opening range high / low
- VWAP reclaim / rejection
- opening range break
- trend / chop / reversal
- relative strength
- fills inside the window
- condition pass / fail changes

## 7. User Review And Absorption Loop

After evidence arrives, `investing-os` conducts the review with the user.

Workflow:

- `system/workflows/post-market-trade-review.md`

Templates:

- `templates/contextual-trade-review.md`
- `templates/post-market-review.md`
- `templates/review-report-standard.md`

The brain asks about:

- original intent
- invalidation
- add / reduce reasoning
- plan alignment
- emotion and attention
- unrelated holdings
- best pause timestamp

The review is not complete until:

- evidence packet received
- user interview complete
- review report created
- lessons extracted
- absorption decision recorded
- dashboard HTML generated if archived
- lineage updated

## 8. Event Reconstruction Loop

Use when a single event requires more evidence.

Examples:

- missed opportunity
- false positive
- trade entered after trigger
- trigger passed but failed quickly
- data stale
- slippage / delay problem

Brain request:

- `templates/event-reconstruction-request.json`

Muscle packet:

- `system/data/packets/event-reconstruction-packet.md`

Muscle returns:

- event timeline
- conditions at trigger
- condition quality
- post-trigger MFE / MAE for 5m / 15m / 30m
- VWAP / volume / RS context
- data freshness
- missed window analysis
- false-positive path if applicable

Brain decides what, if anything, should be learned.

## 9. Periodic Tactic Summary Loop

Use in weekend / monthly reviews.

Purpose:

Evaluate whether a tactic or signal works across many events.

Brain request:

- `templates/tactic-event-summary-request.json`

Muscle packet:

- `system/data/packets/tactic-event-summary-packet.md`

Muscle returns:

- event count
- traded / missed / false-positive counts
- MFE / MAE distribution
- 5m / 15m / 30m outcomes
- opening 30m vs later-day performance
- QQQ risk-on / risk-off grouping
- VIX direction grouping
- sector confirmation grouping
- condition quality vs outcome
- execution delay distribution
- possible disable-environment candidates

Brain may then propose updates to:

- `decision/tactics/`
- `decision/risk-budget.md`
- `system/checks/`
- `execution/`
- `evolution/promotion-queue.md`

No tactic change is final without absorption decision.

## 10. Knowledge Absorption

Nothing durable enters cognition by default.

All evidence and reports pass through:

- `system/workflows/packet-absorption.md`
- `system/traceability/schema.md`

Flow:

```text
evidence packet
|
report / interview
|
lesson candidate
|
recommended landing
|
user decision
|
target file update
|
lineage record
|
HTML / dashboard refresh
```

Possible destinations:

- `cognition/`
- `decision/`
- `execution/`
- `evolution/`
- `wiki/companies/`
- `wiki/industries/`
- `wiki/journals/`
- `wiki/historical-cases/`
- `decision/tactics/`
- `system/checks/`
- `templates/`

Rule:

A review is not complete until absorption status is explicit.

## 11. Antigravity Implementation Scope

Antigravity should implement only inside:

```text
D:\gemini\lianghua\stock_team
```

Primary tasks:

1. Stable CLI producers for all evidence packet types.
2. Polygon-first market data with cache / freshness metadata.
3. IBKR position / order / fill / P&L evidence extraction.
4. Stage 0 market context packet.
5. Stage 1 plan evidence packet.
6. Intraday evidence dashboard from brain guidance artifact.
7. Latest dashboard manifest.
8. Post-market trade evidence packet.
9. Event reconstruction packet.
10. Tactic event summary packet.
11. Packet producer map.
12. Smoke tests and regression fixtures.

Required boundary:

Every packet must include missing-data notes and forbidden-section checks.

## 12. System Status

The philosophy and contract architecture are now closed-loop.

Remaining work is mostly engineering:

- implement stock_team producers
- generate example packets
- connect dashboard manifest to operating console
- run full daily simulation
- iterate after real usage
