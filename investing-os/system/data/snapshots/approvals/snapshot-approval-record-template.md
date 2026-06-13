# Snapshot Approval Record

## Metadata

```yaml
snapshot_id:
snapshot_type:
snapshot_file:
schema_file:
approval_status: draft
reviewer:
review_date:
valid_from:
review_due:
previous_active_snapshot:
```

## 1. Purpose

Why should this snapshot exist?

What runtime behavior should it influence?

## 2. Source Evidence

List source principles, cases, journals, checklists, or backtests.

Separate:

- durable principles
- journal evidence
- quantitative evidence
- manual guardrails

## 3. Schema Validation

```yaml
schema_validation_passed: yes/no
validation_command:
validation_result:
```

## 4. Rule Review

For each rule:

```yaml
rule_id:
source_principle:
runtime_status:
parameter_status:
approved_behavior:
forbidden_behavior:
reason:
```

## 5. Degraded Mode Review

Confirm:

- missing daily plan cannot create new discretionary orders
- missing data blocks action-oriented conclusions
- alerts remain informational or review-oriented

## 6. Risk Review

What can go wrong if this snapshot is consumed?

What is the fail-closed behavior?

## 7. Approval Decision

Choose one:

- approve_active
- keep_draft
- reject
- retire_existing

Reason:

## 8. Rollback Plan

Which snapshot should be restored if this one causes problems?

What signs trigger rollback?

