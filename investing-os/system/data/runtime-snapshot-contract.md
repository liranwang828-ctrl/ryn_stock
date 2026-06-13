# Runtime Snapshot Contract

## Purpose

Define how `investing-os` can provide validated runtime rules to `stock_team` / `lianghua` without coupling the runtime system to the wiki.

## Boundary

`investing-os` owns:

- discipline intent
- principle definitions
- review logic
- WHY alignment
- parameter rationale

`stock_team` owns:

- runtime loading
- calculations
- monitoring
- execution tooling
- tests

## Rule

`stock_team` must not directly read raw `investing-os` wiki files at runtime.

It may consume only exported, schema-validated snapshots.

## Snapshot Lifecycle

```text
principle or checklist changes
|
parameter review
|
snapshot update
|
schema validation
|
export to stock_team/config/
|
runtime read-only consumption
```

## Snapshot Types

- tactical rules
- risk limits
- watchlist metadata
- signal interpretation rules
- degraded-mode rules

## Required Snapshot Metadata

Each snapshot should include:

- snapshot_id
- version
- created_at
- source_principles
- generated_by
- valid_from
- review_due
- schema_version

## Tactical Rule Shape

```json
{
  "snapshot_id": "tactical-rules-YYYYMMDD",
  "version": "0.1.0",
  "schema_version": "0.1.0",
  "created_at": "YYYY-MM-DDTHH:MM:SS",
  "source_principles": ["PRIN-001"],
  "rules": [
    {
      "id": "cooling_period_after_profit",
      "discipline_intent": "Prevent immediate regret-driven re-entry after profit taking.",
      "parameters": {
        "cooling_minutes": 30
      },
      "parameter_status": "provisional",
      "evidence": "journal review / backtest / manual rule",
      "falsification": "Revise if repeated reviews show the rule increases risk or blocks valid planned execution."
    }
  ]
}
```

## Sensitive Data Rule

Snapshots must not contain:

- secrets
- API keys
- account credentials
- raw account exports
- unredacted personal data

## Degraded Mode Rule

If a required plan is missing, runtime behavior must degrade to:

- read-only monitoring
- alerts
- risk warnings
- review tasks

It must not produce new discretionary trade orders.

