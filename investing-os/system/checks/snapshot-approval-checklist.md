# Snapshot Approval Checklist

Use this before moving any runtime snapshot to `system/data/snapshots/active/`.

## WHY Alignment

- Does the snapshot serve cognition, discipline, or risk control?
- Does it avoid turning AI or runtime tooling into the decision maker?
- Does it preserve human responsibility for final judgment and risk?

## Schema

- Snapshot parses as JSON.
- Snapshot validates against the declared schema.
- Snapshot ID, version, status, source, rules, and degraded mode are present.
- Snapshot status is `active` only after approval.

## Source Evidence

- Every rule links to a source principle.
- Every rule has evidence.
- Every rule has falsification.
- Parameters have a status.
- Provisional parameters remain `monitor_only` unless explicitly approved as manual guardrails.

## Runtime Boundary

- Runtime systems consume only snapshots, not raw wiki files.
- Snapshot does not contain secrets, credentials, account exports, or personal sensitive data.
- Snapshot does not contain direct buy/sell commands.
- Snapshot does not authorize autonomous trading.

## Fail-Closed Behavior

- Missing daily plan blocks new discretionary orders.
- Missing or stale data blocks action-oriented conclusions.
- Degraded mode allows alerts, review tasks, and manual-plan requests only.

## Approval Record

- Approval record exists under `system/data/snapshots/approvals/`.
- Changelog entry is prepared.
- Review due date is set.
- Rollback plan is documented.

## Final Decision

```yaml
approve_active: yes/no
reviewer:
decision_date:
reason:
```

