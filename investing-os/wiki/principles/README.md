# Principles

Durable rules and beliefs.

Principles should be updated only after repeated evidence, not after one emotional event.

## Naming

Use:

```text
PRIN-[number]-[english-short-name].md
```

Example:

```text
PRIN-001-leveraged-tool-discipline.md
```

## Current Principles

- `PRIN-001-leveraged-tool-discipline.md`
- `PRIN-002-hand-feel-trade-limit.md`
- `PRIN-003-profit-taking-cooling-period.md`
- `PRIN-004-sector-sympathy-rules.md`
- `PRIN-005-vwap-volume-rules.md`
- `PRIN-006-cognitive-attention-budget.md`

## Required Structure

Use `templates/principle.md`.

A principle must contain:

- metadata
- core assertion
- why it exists
- trigger conditions
- execution constraints
- forbidden behavior
- falsification or revision conditions
- drift audit
- related cases
- runtime parameters, if any

## Rule

Principles describe discipline intent.

Runtime numbers belong in exported parameter snapshots, not directly in the principle unless they are clearly labeled as historical or provisional.
