# System Architecture

This directory contains operating workflows and extensible system modules.

## Modules

- `workflows/`: repeatable investment workflows
- `data/`: local data interfaces and raw-data notes
- `checks/`: discipline and risk checklists
- `automation/`: future scheduled jobs and reminders

## Core Operating Files

- `architecture.md`: extensible architecture
- `evolution-loop.md`: cognition upgrade loop
- `file-growth-policy.md`: keeps core files short and pushes detail into reports / lineage
- `workflows/trading-day.md`: timezone-offset trading day rhythm
- `workflows/weekend-review.md`: weekly deep review and research rhythm
- `workflows/signal-processing.md`: signal interpretation workflow

## Boundary

The system can automate process.

The system must not automate final investment judgment.

## File Growth Boundary

Core files should stay readable.

When a file approaches 300 lines, convert it into an index and move details into topic files, reports, cases, or lesson lineage.

See:

- `file-growth-policy.md`
