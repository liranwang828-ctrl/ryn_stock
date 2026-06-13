# Branch Report: Packet Absorption Workflow

Date: 2026-06-05

## Summary

Created the `investing-os` workflow for absorbing incoming packets from `stock_team`, ChatGPT, or manual research.

This completes the first stock-team output-intake cleanup item after the Phase 4 mainline.

## Created Files

- `system/workflows/packet-absorption.md`
- `templates/packet-review.md`
- `wiki/sources/README.md`

## Updated Files

- `system/workflows/README.md`
- `templates/README.md`
- `system/workflows/wiki-update.md`
- `handoff/phase-tracker.md`

## Design Choices

- Packets are review envelopes, not durable knowledge.
- Every packet needs an absorption decision before updating wiki, journal, principles, cases, templates, checks, workflows, or runtime parameter maps.
- Packet review separates fact, inference, action suggestion, emotion/behavior observation, and system update candidate.
- Unsupported, unclear, or action-pressure packets can be rejected or kept in inbox.

## Destination Map

- daily execution and emotion -> `wiki/journals/`
- durable behavioral rule -> `wiki/principles/`
- concrete mistake/success pattern -> `wiki/historical-cases/`
- company thesis or dossier -> `wiki/companies/`
- industry structure -> `wiki/industries/`
- repeatable method -> `wiki/methodologies/`
- checklist improvement -> `system/checks/`
- workflow improvement -> `system/workflows/`
- template improvement -> `templates/`
- runtime parameter candidate -> `system/data/runtime-parameter-map.md`

## Next Branch Items

- company and industry dossier workflow
- journal-to-principle promotion workflow
- active snapshot approval dry run

