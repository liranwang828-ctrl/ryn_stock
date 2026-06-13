# Evidence Request Lifecycle

Purpose:

Turn every `stock_team` call into a traceable investing-os request, not an ad hoc script run.

## Trigger

Use this workflow when a review, pre-market plan, intraday check, company research, industry research, or backtest needs external market / fill / financial evidence.

## Lifecycle

```text
user asks investing-os
|
route request with command-router.md
|
create evidence request from template
|
run approved stock_team CLI command
|
save packet artifact
|
record call log
|
absorb packet into cognition / decision / execution / evolution
|
update dashboard indexes if durable lessons or reports changed
```

## Required Artifacts

Before calling `stock_team`, create or fill:

- `templates/stock-team-evidence-request.md`

After calling `stock_team`, update:

- `integrations/stock-team-call-log.md`

If the evidence changes durable system state, also update the relevant traceability indexes:

- `system/traceability/reports-index.json`
- `system/traceability/lesson-index.json`
- `system/traceability/file-lineage-index.json`
- `system/traceability/capability-history.json`

## Absorption Rule

Facts from `stock_team` do not enter the system directly as decisions.

They must be interpreted by `investing-os` through one of:

- `system/workflows/packet-absorption.md`
- `system/workflows/post-market.md`
- `system/workflows/company-research.md`
- `system/workflows/daily-report.md`

## Boundary Check

Reject or quarantine any packet that contains:

- buy / sell / hold recommendation
- trading permission decision
- final thesis adoption
- psychological interpretation
- live execution instruction

If this happens, record the issue in:

- `integrations/stock-team-call-log.md`

and do not absorb the packet until the boundary violation is corrected.
