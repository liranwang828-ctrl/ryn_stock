# Runtime Snapshots

Runtime snapshots are machine-readable exports from `investing-os`.

They are the only approved path for runtime systems to consume discipline rules.

Runtime systems must not read raw wiki, principle, journal, or checklist files directly.

## Directory Policy

- `drafts/`: snapshots being prepared or reviewed.
- `active/`: approved snapshots that may be consumed by external runtime systems.
- `retired/`: old active snapshots kept for audit and rollback context.
- `examples/`: non-runtime examples used for schema and documentation.
- `approvals/`: human-readable approval records.

## Promotion Rule

A snapshot may move from `drafts/` to `active/` only after:

1. Schema validation passes.
2. Source principles and evidence are listed.
3. Every rule has a discipline intent and falsification note.
4. Provisional parameters are `monitor_only` unless explicitly approved as manual guardrails.
5. Degraded mode forbids new discretionary orders.
6. Approval is recorded under `approvals/`.
7. `changelog.md` is updated.

## Active Snapshot Rule

Only one active snapshot of the same type should exist at a time.

If a new tactical-rules snapshot becomes active, the previous tactical-rules active snapshot should move to `retired/`.

## Rollback Rule

Rollback means restoring the most recent retired active snapshot.

Rollback requires:

- reason
- affected snapshot IDs
- rollback date
- reviewer
- changelog entry

## Current State

No active runtime snapshots exist yet.

The current example snapshot is documentation only and must not be consumed by runtime systems.

## Snapshot Types Currently Defined

- `tactical-rules`: discipline and tactical behavior boundaries.
- `risk-limits`: account, symbol, strategy, and asset-class risk boundaries.
- `watchlist-metadata`: symbol roles, thesis status, allowed actions, and no-trade states.
- `signal-interpretation`: rules for turning signals into alerts or review tasks, not commands.
- `degraded-mode`: reusable fail-closed behavior when plans, data, or context are missing.
