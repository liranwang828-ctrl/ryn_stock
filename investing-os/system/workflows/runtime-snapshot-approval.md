# Runtime Snapshot Approval Workflow

## Purpose

Define how a runtime snapshot moves from draft to active without letting unreviewed rules reach runtime tooling.

## Roles

`investing-os` owns:

- principle interpretation
- parameter rationale
- approval decision
- changelog and rollback record

`stock_team` owns:

- runtime consumer implementation
- read-only loading
- runtime tests
- fail-closed behavior

## Lifecycle

```text
principle / checklist / journal update
|
runtime parameter map update
|
draft snapshot
|
schema validation
|
snapshot approval checklist
|
approval record
|
active snapshot
|
runtime read-only consumption
|
review / retire / rollback
```

## Step 1: Prepare Draft

Place draft snapshots in:

- `system/data/snapshots/drafts/`

Draft rules may be incomplete, but must not be consumed by runtime systems.

## Step 2: Validate Schema

Validate the snapshot against its declared schema.

If validation fails, keep the snapshot in draft.

Do not patch runtime consumers to tolerate invalid snapshots.

## Step 3: Run Approval Checklist

Use:

- `system/checks/snapshot-approval-checklist.md`

The review must confirm:

- WHY alignment
- source evidence
- parameter status
- forbidden actions
- degraded mode
- rollback plan

## Step 4: Create Approval Record

Create an approval record under:

- `system/data/snapshots/approvals/`

Use:

- `system/data/snapshots/approvals/snapshot-approval-record-template.md`

## Step 5: Promote To Active

Only after approval:

1. Set snapshot status to `active`.
2. Move or copy the approved snapshot to `system/data/snapshots/active/`.
3. Retire any previous active snapshot of the same type.
4. Update `system/data/snapshots/changelog.md`.

## Step 6: Runtime Consumption

Runtime systems may consume only files under:

- `system/data/snapshots/active/`

Runtime consumption must be read-only.

Runtime systems must fail closed if:

- no active snapshot exists
- schema validation fails
- required daily plan is missing
- required data is stale or missing

## Step 7: Review, Retire, Or Roll Back

Review active snapshots before `review_due`.

Retire a snapshot if:

- source principles change materially
- repeated journal reviews contradict the rule
- runtime behavior creates unacceptable risk
- parameters become stale

Rollback to the most recent retired snapshot if the active snapshot causes discipline or risk issues.

