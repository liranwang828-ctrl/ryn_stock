# Branch Report: Experience Output Map

Date: 2026-06-05

## Summary

Created the map that defines what experience should be produced after orchestrated workflows and where it should land.

This completes the loop:

```text
user request
|
stock_team evidence if needed
|
packet / call log
|
investing-os interpretation
|
experience output into core systems
```

## Created Files

- `evolution/experience-output-map.md`

## Updated Files

- `system/workflows/stock-team-orchestration.md`
- `execution/weekly-use-cases.md`
- `evolution/README.md`
- `USAGE.md`

## Covered Use Cases

- pre-market planning
- intraday check
- post-market review
- contextual trade review
- company analysis
- industry analysis
- weekly summary
- learning session

## Core Rule

Every orchestrated workflow ends with:

```yaml
experience_decision:
  cognition_update:
  decision_update:
  execution_update:
  evolution_update:
  wiki_update:
  checklist_update:
  runtime_candidate:
  no_update_reason:
```

## Why This Matters

Evidence collection is not the endpoint.

The system must decide what the evidence teaches and where that learning belongs.

