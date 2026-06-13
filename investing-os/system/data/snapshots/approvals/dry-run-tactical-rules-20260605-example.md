# Snapshot Approval Dry Run: Tactical Rules Example

## Metadata

```yaml
snapshot_id: tactical-rules-20260605-example
snapshot_type: tactical-rules
snapshot_file: system/data/snapshots/examples/tactical-rules.example.json
schema_file: system/data/schemas/tactical-rules.schema.json
approval_status: keep_draft
reviewer: Codex
review_date: 2026-06-05
valid_from: 2026-06-05
review_due: 2026-07-05
previous_active_snapshot: none
```

## 1. Purpose

Dry run the Phase 4B approval workflow against the Phase 4A tactical-rules example.

This is not an approval to activate the snapshot.

## 2. Source Evidence

Durable principles:

- PRIN-001
- PRIN-002
- PRIN-003
- PRIN-004
- PRIN-005
- PRIN-006

Journal evidence:

- `wiki/journals/2026-06-04-daily-review.md`

Case evidence:

- CASE-001
- CASE-002
- CASE-003

Manual guardrails:

- degraded mode forbids new discretionary orders when the daily plan is missing

## 3. Schema Validation

```yaml
schema_validation_passed: partial
validation_command: node JSON parse and manual approval-gate checks
validation_result: JSON parsed; required approval-gate checks passed; full JSON Schema validator not run in this dry run
```

Checked:

- snapshot ID: `tactical-rules-20260605-example`
- status: `draft`
- rule count: 6
- all rules are `monitor_only`
- all rules have evidence
- all rules have falsification
- no `null` parameters
- degraded mode forbids new discretionary orders

## 4. Rule Review

### leveraged_tool_discipline

```yaml
source_principle: PRIN-001
runtime_status: monitor_only
parameter_status: provisional
approved_behavior: alerts for missing stop, holding duration, or underlying structure review
forbidden_behavior: intraday upgrade of leveraged products into long-term holdings
reason: valid as monitor-only; not approved as hard runtime block
```

### hand_feel_trade_limit

```yaml
source_principle: PRIN-002
runtime_status: monitor_only
parameter_status: provisional
approved_behavior: alerts for missing confirmation and late-session exception review
forbidden_behavior: hand-feel trade without confirmation
reason: valid as monitor-only; max trades per day remains unresolved
```

### profit_taking_cooling_period

```yaml
source_principle: PRIN-003
runtime_status: monitor_only
parameter_status: provisional
approved_behavior: cooling-period and valid-trigger alerts
forbidden_behavior: regret-driven follow-up selling during cooling period
reason: valid as monitor-only; numeric ranges need more journal evidence before active use
```

### sector_sympathy_rules

```yaml
source_principle: PRIN-004
runtime_status: monitor_only
parameter_status: provisional
approved_behavior: catalyst-scope and peer-confirmation alerts
forbidden_behavior: buying peers only because they moved
reason: valid as monitor-only; industry-specific reliability still needs review
```

### vwap_volume_confirmation

```yaml
source_principle: PRIN-005
runtime_status: monitor_only
parameter_status: provisional
approved_behavior: VWAP context and volume-confirmation alerts
forbidden_behavior: treating VWAP as standalone command
reason: valid as monitor-only; signal interpretation should remain review-oriented
```

### cognitive_attention_budget

```yaml
source_principle: PRIN-006
runtime_status: monitor_only
parameter_status: provisional
approved_behavior: attention budget breach alert and fact/thesis/risk restart prompt
forbidden_behavior: averaging down without predefined add rule
reason: valid as monitor-only; one journal source is strong but still early
```

## 5. Degraded Mode Review

Confirmed:

- missing daily plan cannot create new discretionary orders
- allowed degraded actions are monitoring, risk alerts, review tasks, and manual-plan requests
- degraded behavior is compatible with the user's timezone-offset trading workflow

## 6. Risk Review

Potential risks if activated too early:

- provisional parameters may become false precision
- monitor-only alerts could be interpreted as hard trade commands
- runtime consumer does not exist yet
- full JSON Schema validation was not run in this dry run
- `stock_team` has not implemented fail-closed consumer tests

Fail-closed behavior:

- keep this snapshot out of `active/`
- do not export to `stock_team`
- use only as documentation and future approval practice

## 7. Approval Decision

Decision:

- `keep_draft`

Reason:

The snapshot is structurally useful and passes manual dry-run checks, but it is an example file, contains provisional parameters, has no runtime consumer, and has not passed a full activation review.

## 8. Rollback Plan

No rollback is required because no active snapshot was created.

If a future active tactical-rules snapshot causes issues, restore the most recent retired tactical-rules snapshot after recording a changelog entry.

