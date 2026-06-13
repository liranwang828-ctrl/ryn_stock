# Extensible Architecture

This repository is designed to grow from a manual operating system into an AI-assisted research and discipline platform.

## Layers

```text
Constitution
|
Investment framework
|
Knowledge wiki
|
Templates
|
Agent workflows
|
Data and automation
```

## 1. Constitution Layer

Files:

- `constitution.md`

Purpose:

- Define identity
- Define beliefs
- Define forbidden behavior
- Preserve decision boundaries

Change rule:

Only update after repeated evidence from journals and reviews.

## 2. Framework Layer

Files:

- `framework.md`

Purpose:

- Convert worldview into repeatable investment process
- Define research, valuation, risk, execution, and exit logic

Change rule:

Update when a process failure repeats or when a better method is proven.

## 3. Knowledge Layer

Files:

- `wiki/`

Purpose:

- Store durable knowledge
- Keep context retrievable
- Separate long-term knowledge from short-term conversation

Change rule:

Wiki notes should be evidence-based and source-aware.

## 4. Template Layer

Files:

- `templates/`

Purpose:

- Standardize daily execution
- Reduce emotional improvisation
- Create comparable records over time

Change rule:

Templates should evolve when reviews show missing fields or unnecessary friction.

## 5. Agent Layer

Files:

- `AGENTS.md`
- `agents/`

Purpose:

- Define AI roles
- Constrain agent behavior
- Make AI output auditable

Change rule:

Agents should be updated when the human framework improves.

## 6. System Layer

Files:

- `system/`

Purpose:

- Store workflows, checks, data definitions, and future automation
- Keep operational logic separate from knowledge notes

Change rule:

System modules should remain composable and human-supervised.

## 7. File Growth Layer

As the system learns, files must not become large undifferentiated knowledge dumps.

Rule:

```text
index files summarize
detail files explain
lineage files trace
dashboard connects
```

Soft limit:

- 300 lines

Hard limit:

- 500 lines

When core files grow too large, split them into topic files while keeping the original file as an index.

See:

- `system/file-growth-policy.md`
- `system/closed-loop-operating-architecture.md`

## Future Extension Ideas

- Add `watchlists/` for structured observation lists.
- Add `portfolios/` for position snapshots and risk summaries.
- Add `scripts/` for local data parsing and report generation.
- Add `dashboards/` for visual review.
- Add scheduled reminders for pre-market and post-market workflows.
- Add source connectors for filings, earnings transcripts, and financial statements.

## Non-Goals

- Fully automated trading
- Outsourcing final decisions to AI
- Replacing personal judgment
- Optimizing for short-term excitement
