# Intraday Guidance Automation Backlog

Purpose:

Record the future automation work needed to turn the intraday guidance demo into a live-but-disciplined operating page.

## Phase 1: Static Demo And Manual Generation

- [x] Define intraday guidance protocol.
- [x] Define intraday guidance sheet template.
- [x] Create HTML demo.
- [ ] Generate a real guidance sheet from the next pre-market plan.
- [ ] Archive generated guidance sheets by date.

## Phase 2: Pre-Market Projection

- [ ] Convert pre-market plan into structured fields:
  - position roles
  - key levels
  - allowed tactics
  - forbidden actions
  - risk budget
  - cognitive risks
  - initial permission state
- [ ] Add a generator script for static HTML guidance pages.
- [ ] Link each daily guidance page from operating console.

## Phase 3: Stock Team Evidence Integration

- [ ] Consume `pre-market-packet.md`.
- [ ] Consume `runtime-monitor-packet.md`.
- [ ] Consume `IBKR position snapshot` packet when available.
- [ ] Consume QQQ / SPY / VIX / sector runtime context.
- [ ] Show missing-data and stale-data warnings.

## Phase 4: Permission State Recalculation

- [ ] Implement investing-os interpretation rules for Green / Yellow / Red / No-Trade.
- [ ] Ensure `stock_team` never outputs permission state.
- [ ] Record state changes with timestamp and evidence source.
- [ ] Require user confirmation before any new-risk action in Yellow.
- [ ] Block new short-term / leveraged risk in Red and No-Trade.

## Phase 5: Post-Market Audit

- [ ] Compare actual actions against intraday guidance state.
- [ ] Identify plan-consistent and plan-breaking actions.
- [ ] Identify which cognitive risks activated.
- [ ] Propose lessons to promotion queue.
- [ ] Update dashboard lineage and capability history when lessons are adopted.

## Boundary

This automation must never become an execution robot.

It may display:

- current state
- plan alignment
- allowed / forbidden action categories
- evidence readiness
- missing data
- next safe process action

It must not display:

- buy / sell / hold recommendation
- direct order instruction
- autonomous execution
- trading permission from `stock_team`
