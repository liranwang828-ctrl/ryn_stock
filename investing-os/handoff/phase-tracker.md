# Investing OS Phase Tracker

Date: 2026-06-05

## Purpose

Keep the project from drifting as new useful branches appear.

The repository center of gravity is now:

1. `cognition/`
2. `decision/`
3. `execution/`
4. `evolution/`

`wiki/`, `system/`, `templates/`, `integrations/`, and `handoff/` are supporting layers.

The system now has two related but separate integration directions:

1. Incoming outputs from `stock_team` into `investing-os`.
2. Approved discipline snapshots from `investing-os` into `stock_team`.

They should not block each other.

## Mainline: Principle To Runtime Export

This was the original Phase 4 path.

### Phase 4A: Runtime Snapshot Draft

Status: completed.

Created:

- `system/data/schemas/tactical-rules.schema.json`
- `system/data/snapshots/examples/tactical-rules.example.json`
- `system/data/runtime-parameter-map.md`
- `handoff/inventory/phase4a-runtime-snapshot-report.md`

Meaning:

- `investing-os` has a draft machine-readable format for tactical discipline rules.
- All current rules are `monitor_only`.
- Parameters are provisional.
- No `stock_team` code consumes these files yet.

### Phase 4B: Approval And Promotion Workflow

Status: completed.

Goal:

- define how a snapshot moves from `draft` to `active`
- prevent accidental runtime consumption of unapproved rules
- define review, approval, expiry, and rollback process

Created:

- `system/data/snapshots/README.md`
- `system/data/snapshots/drafts/README.md`
- `system/data/snapshots/active/README.md`
- `system/data/snapshots/retired/README.md`
- `system/data/snapshots/approvals/README.md`
- `system/data/snapshots/approvals/snapshot-approval-record-template.md`
- `system/data/snapshots/changelog.md`
- `system/checks/snapshot-approval-checklist.md`
- `system/workflows/runtime-snapshot-approval.md`

Boundary:

- Codex can define this inside `investing-os`.
- Antigravity does not need to modify `stock_team` for this step.

### Phase 4C: Additional Snapshot Schemas

Status: completed.

Created schemas:

- `system/data/schemas/risk-limits.schema.json`
- `system/data/schemas/watchlist-metadata.schema.json`
- `system/data/schemas/signal-interpretation.schema.json`
- `system/data/schemas/degraded-mode.schema.json`

Created examples:

- `system/data/snapshots/examples/risk-limits.example.json`
- `system/data/snapshots/examples/watchlist-metadata.example.json`
- `system/data/snapshots/examples/signal-interpretation.example.json`
- `system/data/snapshots/examples/degraded-mode.example.json`

Meaning:

- runtime rules are no longer limited to tactical discipline
- risk boundaries, symbol roles, signal interpretation, and fail-closed behavior now have draft formats
- no examples are active or approved for runtime consumption

### Phase 4D: Runtime Consumer Design

Status: handoff request prepared, Antigravity-owned future work.

Goal:

- map how `stock_team` would consume approved snapshots read-only
- define tests and failure modes
- ensure fail-closed behavior

Prepared request:

- `handoff/requests/phase4d-runtime-consumer-request.md`

Boundary:

- Antigravity works in `stock_team`.
- Codex provides contracts from `investing-os`.

## Branch: Stock Team Output Intake

This branch was inserted after the user noticed `stock_team` can do more than provide wiki files.

### Capability Map

Status: completed.

Created / updated:

- `integrations/stock-team-capability-map.md`
- `handoff/stock-team-capability-report.md`

Meaning:

- `stock_team` remains the tooling layer for reports, pre-market, post-market, monitoring, dashboards, and data collection.
- `investing-os` remains the cognition, discipline, review, and knowledge layer.

### Packet Contracts

Status: completed.

Created:

- `system/data/packets/company-research-packet.md`
- `system/data/packets/industry-research-packet.md`
- `system/data/packets/pre-market-packet.md`
- `system/data/packets/post-market-packet.md`
- `system/data/packets/runtime-monitor-packet.md`

Meaning:

- `stock_team` outputs should enter `investing-os` through review envelopes.
- Generated reports should not be dumped directly into `wiki/`.
- Packet review decides whether something becomes a journal, company dossier, industry note, principle, checklist, or case.

### Packet Producer Implementation

Status: Antigravity-owned future work.

Goal:

- map existing `stock_team` pipelines to packet outputs
- add exporters or adapters if needed
- keep `investing-os` read-only from `stock_team`

Boundary:

- Antigravity works in `stock_team`.
- Codex does not modify `stock_team` unless explicitly asked.

### Packet Absorption Workflow

Status: completed.

Created:

- `system/workflows/packet-absorption.md`
- `templates/packet-review.md`
- `wiki/sources/README.md`

Meaning:

- incoming packets from `stock_team`, ChatGPT, or manual research now have a review path
- packets do not directly become wiki or runtime knowledge
- absorption decisions determine whether content enters journal, principles, cases, companies, industries, methods, checks, workflows, templates, or runtime parameter candidates

### Company And Industry Dossier Lifecycle

Status: completed.

Created:

- `system/workflows/company-dossier-lifecycle.md`
- `system/workflows/industry-dossier-lifecycle.md`
- `wiki/companies/company-dossier-template.md`
- `wiki/industries/industry-dossier-template.md`

Meaning:

- generated company reports do not automatically become theses
- generated industry reports do not automatically become buy lists
- company and industry research now have lifecycle states before becoming active durable knowledge

### Journal To Principle Promotion Workflow

Status: completed.

Created:

- `system/workflows/journal-to-principle-promotion.md`
- `templates/principle-candidate.md`
- `wiki/principles/candidates/README.md`

Meaning:

- journal observations now have a promotion path
- one event can create a candidate, but active principles require review
- not every emotional lesson should become a permanent rule

### Active Snapshot Approval Dry Run

Status: completed.

Created:

- `system/data/snapshots/approvals/dry-run-tactical-rules-20260605-example.md`
- `handoff/inventory/active-snapshot-approval-dry-run-report.md`

Meaning:

- the approval workflow was exercised without creating an active snapshot
- the tactical-rules example remained `draft`
- the decision was `keep_draft`

### Daily Review Encoding Repair

Status: completed.

Updated:

- `wiki/journals/2026-06-04-daily-review.md`

Meaning:

- the source journal for PRIN-006 is now human-readable Chinese
- the SNXX attention-budget lesson remains usable for future reviews

### Core Four-System Refactor

Status: completed.

Created:

- `OPERATING-MODEL.md`
- `cognition/`
- `decision/`
- `execution/`
- `evolution/`

Meaning:

- the repository is no longer centered on wiki or research output
- trading and research are nutrient sources for the four core systems
- `wiki/` is long-term memory, not the operating center
- `system/` is infrastructure, not the cognition core

### First Operating Pass

Status: completed.

Source:

- `wiki/journals/2026-06-04-daily-review.md`

Updated:

- `cognition/`
- `decision/`
- `execution/`
- `evolution/`

Meaning:

- SNXX review now changes operating state, not only wiki memory
- COHR / ORCL / INTC are plan-required pending exit audit
- SNXX is blocked pending full review
- attention budget and spillover guards are now execution rules

## Current Recommended Next Step

Continue Codex-owned `investing-os` absorption workflows while Phase 4D waits for Antigravity.

Reason:

- Packet contracts solved the intake confusion.
- Phase 4B created the approval gate.
- Phase 4C created additional schema contracts without touching `stock_team`.
- Runtime consumer handoff is now prepared for Antigravity.
- Codex can still continue independent `investing-os` work without blocking Antigravity.

## Independent Work Split

Codex should own:

- Phase 4B approval workflow
- Phase 4C additional snapshot schemas
- packet absorption rules inside `investing-os`
- wiki/template/checklist evolution

Antigravity should own:

- `stock_team` command and pipeline map
- packet producer design inside `stock_team`
- runtime snapshot consumer design inside `stock_team`
- tests and failure-mode review for `stock_team`

Neither side depends on the other for the immediate next step.
