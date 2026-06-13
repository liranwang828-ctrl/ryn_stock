# Peer Handoff: investing-os

Date: 2026-06-05  
Audience: peer-level collaborator / coding agent  
Primary next task: code and repository structure analysis

## Objective

You are taking over a new independent project called `investing-os`.

Your immediate job is not to add trading features. Your job is to understand and organize the current file structure, clarify each directory's role, and prepare the project for future code-oriented work without drifting away from the user's core intent.

## Project Location

```text
C:\Users\rriww\Documents\investing-os
```

This project is intentionally separate from:

```text
C:\Users\rriww\Documents\STOCK
```

Do not move it back under `STOCK`.

## Project Identity

`investing-os` is a personal cognition x AI trading operating system.

It is not an automatic trading bot.

It is not a quant backtesting engine.

It is not a raw data warehouse.

It is the user's cognition, discipline, AI-agent, workflow, and knowledge layer.

Read these files first:

1. `WHY.md`
2. `PROJECT.md`
3. `constitution.md`
4. `framework.md`
5. `AGENTS.md`
6. `integrations/lianghua.md`

## Core Thesis

The project exists because the user believes:

- Trading is cognition monetization.
- Cognition is not information or knowledge; it is judgment under uncertainty.
- AI is an amplifier, not cognition itself.
- Agent Team should help transform cognition into action, enforce discipline, support learning, and reveal errors.
- Final judgment and final risk always remain human-owned.

Short version:

```text
Cognition is the engine.
AI is the amplifier.
Discipline is the moat.
Review is the evolution mechanism.
Long-termism is the direction.
Returns are a byproduct.
```

## Current File Structure

Current top-level structure:

```text
investing-os/
+-- WHY.md
+-- README.md
+-- PROJECT.md
+-- constitution.md
+-- framework.md
+-- AGENTS.md
+-- agents/
+-- handoff/
+-- integrations/
+-- system/
+-- templates/
+-- wiki/
```

### Root Files

- `WHY.md`: highest-level origin and purpose. Treat it as the north star.
- `README.md`: public entry and directory map.
- `PROJECT.md`: governance, entry rules, non-goals, and project rhythm.
- `constitution.md`: personal beliefs, identity, forbidden behaviors, and trading principles.
- `framework.md`: investment process from worldview to exit.
- `AGENTS.md`: agent roles, output rules, and AI boundaries.

### `agents/`

Role definitions for AI collaborators.

Currently only has a README placeholder. Future work may split Research, Industry, Valuation, Risk, Journal, and Reflection agents into separate files.

Do not let agents become decision makers. They can collect, summarize, calculate, question, and organize.

### `integrations/`

Defines how external projects connect.

Important file:

- `integrations/lianghua.md`

### `system/`

Operational architecture.

Contains:

- `architecture.md`: layered architecture.
- `evolution-loop.md`: trade-review-cognition upgrade loop.
- `workflows/`: repeatable workflows.
- `checks/`: discipline and alignment checks.
- `data/`: future data interface notes.
- `automation/`: future reminders and scheduled workflows.

### `templates/`

Reusable execution templates.

Important current templates:

- `trading-day-plan.md`
- `weekend-review.md`
- `signal-review.md`
- `company-research.md`
- `trade-plan.md`
- `valuation.md`
- `risk-checklist.md`
- `thesis.md`
- `falsification.md`

### `wiki/`

Long-term knowledge layer.

Sections:

- `principles/`
- `methodologies/`
- `industries/`
- `companies/`
- `historical-cases/`
- `journals/`
- `sources/`

Wiki stores durable knowledge, not temporary conversation context.

### `handoff/`

Structured handoff documents.

This directory was created because the user wants handoff to become a formal project practice.

## Two-System Collaboration Model

There are two conceptual systems:

```text
investing-os = cognition, discipline, review, agents, wiki, workflows
lianghua = quantitative research, signals, indicators, backtests, tooling
```

They should collaborate through interpretation, not by merging everything into one repository.

### investing-os Responsibilities

- Preserve the WHY.
- Manage investment framework and discipline.
- Store durable knowledge.
- Define agent behavior and boundaries.
- Convert signals into questions, reviews, or planned actions.
- Maintain journals, thesis, risk checks, and wiki updates.

### lianghua Responsibilities

- Generate quantitative signals.
- Calculate indicators.
- Run backtests.
- Hold raw data and strategy code.
- Explore experiments.
- Produce quantitative observations.

### Boundary

`lianghua` output does not directly become trading action.

It must pass through:

```text
Signal
|
Context check
|
Thesis check
|
Risk check
|
Emotion check
|
Human decision
```

Hard rule:

New signals can trigger research.

New signals cannot trigger unplanned trades.

Only signals already defined in a written plan may trigger execution.

## User Context And Usage Scenario

The user is in Asia/Shanghai timezone while US market hours are offset.

Typical weekday rhythm:

```text
After work = US pre-market
Before sleep / sleep = US intraday
Morning or daytime = asynchronous review if time allows
Weekend = deeper review and company research
```

Available time:

- Weekdays: flexible, about 60-180 minutes when free.
- Weekends: roughly 4-5 hours total for review and research.

The system should therefore be asynchronous and plan-driven.

It should not assume the user can monitor the market continuously.

## Practical Workflow Design

### Trading Day

After work:

- Review holdings.
- Review watchlist.
- Check major events.
- Write allowed actions.
- Write no-trade conditions.
- Set alerts.

Before sleep:

- Check open orders.
- Check position risk.
- Check whether anything affects sleep.
- Remove unnecessary emotional orders.

Morning or daytime:

- Review what happened.
- Update journal if needed.
- Update thesis or risk if material events occurred.

Relevant files:

- `system/workflows/trading-day.md`
- `templates/trading-day-plan.md`

### Weekend

Weekend is the main cognitive upgrade window.

Suggested split:

- 60 minutes weekly review.
- 2 hours deep company or industry research.
- 60 minutes system/wiki/template/agent updates.
- 30-60 minutes next week plan.

Relevant files:

- `system/workflows/weekend-review.md`
- `templates/weekend-review.md`

### Signal Handling

Signals should be classified as:

- Information signal
- Market signal
- Thesis signal
- Risk signal
- System signal

Relevant files:

- `system/workflows/signal-processing.md`
- `system/checks/signal-to-action-checklist.md`
- `templates/signal-review.md`

## What To Do Next

Recommended next work for you:

1. Produce a repository map with a short description of every file.
2. Identify which files are stable governance documents and which are operational templates.
3. Check for duplication between README, PROJECT, constitution, framework, and WHY.
4. Propose a clean naming convention for future files.
5. Decide whether future code belongs under `tools/`, `scripts/`, or a separate project.
6. Define how `lianghua` output should be imported as notes without importing code.
7. Prepare a first pass of `agents/*.md` role files if the user asks for it.

## What Not To Do Yet

Do not:

- Build an automatic trading bot.
- Move `investing-os` under `STOCK`.
- Merge `lianghua` code into this repository.
- Add raw market data.
- Add live trading execution.
- Let signals become direct trading commands.
- Replace human judgment with agent output.
- Over-engineer automation before the manual workflow is stable.

## Important Guardrails

Before major changes, run:

- `system/checks/why-alignment-checklist.md`
- `system/checks/signal-to-action-checklist.md` when signals are involved.

Any new workflow, template, integration, or code path should be traceable back to `WHY.md`.

## Open Questions For The User

Ask these only when they become relevant:

- Where is the real active `lianghua` project located?
- What language and stack does `lianghua` use?
- Should `investing-os` eventually contain code, or remain mostly Markdown plus integrations?
- Should there be a separate `watchlists/` directory?
- Should journal entries be daily files, weekly files, or grouped by thesis?
- Should private trading records be kept in this repo or outside it?

## Current Git State

`investing-os` is an independent Git repository.

As of this handoff, most files are newly created and uncommitted.

Do not assume the outer `STOCK` repository owns this project.

