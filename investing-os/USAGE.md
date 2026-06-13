# Practical Usage Guide

## Purpose

Explain how to actually use `investing-os` during research, trading, review, and `stock_team` integration.

The repository has four core systems:

1. `cognition/`: how judgment improves or fails.
2. `decision/`: current thesis, role, risk, watchlist, and falsification state.
3. `execution/`: how to act under market pressure.
4. `evolution/`: how trading and research update the system.

Supporting layers:

- `wiki/`: long-term memory.
- `system/`: workflows, checks, data contracts, and snapshot infrastructure.
- `templates/`: structured forms.
- `integrations/`: external tool boundaries.

## Daily Use Map

### After Work: Pre-Market

Your timezone makes after-work time the practical pre-market window.

Use:

- `system/workflows/trading-day.md`
- `system/workflows/pre-market.md`
- `templates/trading-day-plan.md`
- `templates/pre-market-plan.md`
- `system/checks/why-alignment-checklist.md`
- `system/checks/signal-to-action-checklist.md`

Update:

- `decision/current-watchlist.md`
- `decision/position-roles.md`
- trading-day plan
- watchlist notes
- no-trade conditions
- alerts to review

If using `stock_team`:

- consume pre-market output through `system/data/packets/pre-market-packet.md`
- review with `templates/packet-review.md`
- only then write a plan
- record calls in `integrations/stock-team-call-log.md`

### Before Sleep: Risk Lock

Use:

- `templates/trading-day-plan.md`
- `system/workflows/trading-day.md`
- `system/checks/position-role-checklist.md`
- `system/checks/short-term-trade-checklist.md`

Update:

- `decision/risk-budget.md` if a real boundary changes
- open-order review
- sleep-before-risk check
- position risk notes

Core question:

Can I safely sleep through the market?

### During Market: Low Intervention

Use:

- `system/workflows/intraday.md`
- `system/workflows/signal-processing.md`
- `system/checks/signal-to-action-checklist.md`
- `system/checks/short-term-trade-checklist.md`

Allowed:

- execute prewritten plan
- respond to predefined alerts
- reduce risk if plan allows
- record emotion or impulse

Forbidden:

- invent new trades from price movement alone
- treat signals as commands
- average down without a prewritten add rule
- let a low-conviction trade hijack sleep or attention

If using `stock_team` runtime alerts:

- consume them through `system/data/packets/runtime-monitor-packet.md`
- alerts create review tasks, not trade permission
- record calls in `integrations/stock-team-call-log.md`

### Morning / Daytime Review

Use:

- `system/workflows/post-market.md`
- `templates/post-market-review.md`
- `templates/journal-entry.md`
- `system/workflows/journal-to-principle-promotion.md`

Update:

- `execution/post-market.md` if an execution rule needs changing
- `wiki/journals/`
- principle candidates if a repeatable pattern appears
- historical cases if the trade has durable lesson value
- checklists if an execution gap is discovered

If using `stock_team`:

- consume post-market output through `system/data/packets/post-market-packet.md`
- review with `templates/packet-review.md`
- absorb through `system/workflows/packet-absorption.md`
- record calls in `integrations/stock-team-call-log.md`

### Weekend Review

Use:

- `system/workflows/weekend-review.md`
- `system/workflows/wiki-update.md`
- `system/workflows/journal-to-principle-promotion.md`
- `system/data/runtime-parameter-map.md`

Update:

- `cognition/`
- `decision/`
- `evolution/system-update-log.md`
- journals
- principle candidates
- historical cases
- checklist improvements
- runtime parameter candidates
- company and industry research priorities

Weekend is where temporary context becomes durable cognition.

## Research Use Map

### Company Research

Use:

- `system/workflows/company-research.md`
- `system/workflows/company-dossier-lifecycle.md`
- `templates/company-research.md`
- `wiki/companies/company-dossier-template.md`

Update:

- `wiki/companies/`
- `templates/thesis.md`
- `templates/falsification.md`
- `templates/valuation.md`
- `system/data/snapshots/examples/watchlist-metadata.example.json` only as a future candidate, never directly active

If using `stock_team` company reports:

- consume through `system/data/packets/company-research-packet.md`
- review through `templates/packet-review.md`
- absorb through `system/workflows/packet-absorption.md`

Rule:

A company report is not a thesis by default.

### Industry Research

Use:

- `system/workflows/industry-dossier-lifecycle.md`
- `templates/industry-research.md`
- `wiki/industries/industry-dossier-template.md`

Update:

- `wiki/industries/`
- `wiki/methodologies/`
- company research priorities
- watchlist metadata candidates

If using `stock_team` industry reports:

- consume through `system/data/packets/industry-research-packet.md`
- review through `templates/packet-review.md`
- absorb through `system/workflows/packet-absorption.md`

Rule:

An industry note is not a buy list.

## Evolution Use Map

### Journal To Principle

Use:

- `system/workflows/journal-to-principle-promotion.md`
- `templates/principle-candidate.md`
- `templates/principle.md`

Update:

- `wiki/principles/candidates/`
- `wiki/principles/`
- `system/checks/`
- `wiki/historical-cases/`

Rule:

One painful event can create a candidate.

Active principles require review.

### Principle To Runtime Snapshot

Use:

- `system/data/runtime-parameter-map.md`
- `system/data/runtime-snapshot-contract.md`
- `system/workflows/runtime-snapshot-approval.md`
- `system/checks/snapshot-approval-checklist.md`

Update:

- `system/data/snapshots/drafts/`
- `system/data/snapshots/approvals/`
- `system/data/snapshots/changelog.md`

Do not update:

- `system/data/snapshots/active/` without explicit approval

Rule:

Runtime systems may consume only approved active snapshots.

## Stock Team Integration Map

`stock_team` should remain the tooling layer.

It can provide:

- company reports
- industry reports
- pre-market boards
- post-market reviews
- runtime alerts
- data and calculations
- dashboards

`investing-os` decides what becomes cognition.

Flow:

```text
stock_team output
|
packet contract
|
call log
|
packet review
|
absorption decision
|
journal / wiki / principle / case / checklist / snapshot candidate
```

Orchestration workflow:

- `system/workflows/stock-team-orchestration.md`

Experience output map:

- `evolution/experience-output-map.md`

## What Is Currently Used

Actively used now:

- `cognition/`
- `decision/`
- `execution/`
- `evolution/`
- `WHY.md`
- `PROJECT.md`
- `constitution.md`
- `framework.md`
- `system/workflows/`
- `system/checks/`
- `system/data/packets/`
- `system/data/schemas/`
- `system/data/snapshots/`
- `templates/`
- `wiki/principles/`
- `wiki/journals/`
- `wiki/historical-cases/`
- `wiki/industries/`
- `handoff/`
- `integrations/`

Partially used / waiting for real usage:

- `wiki/companies/`: structure exists, but no active company dossiers yet.
- `wiki/principles/candidates/`: candidate workflow exists, but no candidates yet.
- `system/data/snapshots/drafts/`: no real draft snapshots yet.
- `system/data/snapshots/active/`: intentionally empty.
- `agents/`: boundaries exist, but detailed agent role prompts are not yet built.
- `system/automation/`: reserved for future reminders and scheduled checks.

## First Real Operating Loop

The next practical cycle should be:

1. Write a pre-market plan after work.
2. Use stock_team or manual inputs only as packet sources.
3. During market, act only on the plan.
4. Do post-market review when available.
5. Convert review into journal.
6. Promote only repeatable lessons into candidates or principles.
7. Update company/industry dossiers during weekend research.

This is how the system evolves without becoming a signal machine.
