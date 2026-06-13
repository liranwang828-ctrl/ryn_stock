# Phase 4B Report: Snapshot Approval Workflow

Date: 2026-06-05

## Summary

Phase 4B defined the approval, promotion, retirement, and rollback workflow for runtime snapshots.

No `stock_team` code was modified.

No active runtime snapshots were created.

## Created Files

- `system/data/snapshots/README.md`
- `system/data/snapshots/drafts/README.md`
- `system/data/snapshots/active/README.md`
- `system/data/snapshots/retired/README.md`
- `system/data/snapshots/approvals/README.md`
- `system/data/snapshots/approvals/snapshot-approval-record-template.md`
- `system/data/snapshots/changelog.md`
- `system/checks/snapshot-approval-checklist.md`
- `system/workflows/runtime-snapshot-approval.md`

## Updated Files

- `system/data/snapshots/examples/tactical-rules.example.json`
- `system/workflows/README.md`
- `system/data/README.md`
- `system/checks/README.md`
- `handoff/phase-tracker.md`

## Design Choices

- Snapshots now have explicit lifecycle directories: `drafts`, `active`, `retired`, `examples`, and `approvals`.
- Runtime systems may consume only files under `system/data/snapshots/active/`.
- No active snapshots exist yet.
- Every active snapshot must have an approval record and changelog entry.
- Provisional parameters should stay `monitor_only` unless explicitly approved as manual guardrails.
- Degraded mode must fail closed and block new discretionary orders.
- Rollback requires a reason, reviewer, affected snapshot IDs, and changelog entry.

## Correction

The Phase 4A example snapshot had one `null` parameter value.

Because the tactical-rules schema does not allow `null` in rule parameters, it was changed to `"TBD"` so the example remains schema-compatible while still signaling an unresolved value.

## Verification Targets

- Snapshot directories exist.
- Approval checklist exists.
- Approval workflow exists.
- Example snapshot parses as JSON.
- Example snapshot contains no `null` values.
- Phase tracker marks Phase 4B as completed and Phase 4C as next.

## Next Step

Phase 4C: define additional snapshot schemas.

Recommended order:

1. `risk-limits` schema.
2. `watchlist-metadata` schema.
3. `signal-interpretation` schema.
4. `degraded-mode` schema, if it needs to be reusable outside tactical rules.

