# Agent Responsibility Split

Date: 2026-06-05

## Purpose

Reduce coordination overhead by giving each agent a separate work surface.

Agents should produce compatible outputs, but they should not edit the same files or own the same decisions.

The agents should not create blocking dependencies on each other.

Each agent should be able to finish its own work independently and expose results through stable artifacts.

## Agent A: investing-os Steward

Owner: Codex in this thread.

Scope:

- `investing-os/`
- WHY alignment
- Project governance
- Wiki structure
- Import contracts
- Templates
- Agent boundary documents
- Runtime snapshot contract definitions
- Handoff documentation

Primary job:

Turn the user's cognition, workflows, rules, and review loops into a clean, durable operating system.

Allowed actions:

- Create and edit `investing-os` documentation.
- Define import rules.
- Define wiki templates.
- Define snapshot schemas and governance.
- Review inventory output.
- Decide where imported knowledge should land.

Forbidden actions:

- Do not edit `stock_team` or `lianghua`.
- Do not move, copy, delete, or rewrite source assets from `stock_team`.
- Do not refactor execution code.
- Do not generate trading actions.

## Agent B: stock_team / lianghua Engineer

Owner: peer agent / colleague.

Scope:

- `stock_team`
- `lianghua`
- Quantitative scripts
- Runtime configuration
- Tests
- Inventory generation
- Execution engine refactoring proposals

Primary job:

Understand and improve the quantitative tooling layer without changing the cognition repository.

Allowed actions:

- Read and inventory `stock_team`.
- Propose code refactors.
- Add tests in `stock_team` when approved.
- Prepare runtime snapshot consumers.
- Identify generated outputs, code, raw data, runtime configs, and sensitive files.

Forbidden actions:

- Do not edit `investing-os` unless explicitly asked.
- Do not import cognition assets into `investing-os`.
- Do not change WHY, Constitution, Framework, AGENTS, templates, or wiki structure.
- Do not delete source assets without explicit user approval.
- Do not let signals become trading commands.

## Collaboration Boundary

The two systems interact through artifacts, not shared ownership.

```text
stock_team / lianghua
|
inventory manifest
runtime needs
signal output
test results
|
investing-os
|
import contracts
wiki knowledge
discipline rules
validated runtime snapshots
```

## Artifact Contract

Agent B may produce:

- inventory manifests
- code maps
- runtime config maps
- test reports
- signal samples
- refactoring proposals

Agent A may produce:

- import contracts
- wiki templates
- destination mapping
- WHY alignment reviews
- snapshot schemas
- governance updates

## Independence Rule

Codex and Antigravity should not wait on each other for ordinary progress.

Codex can complete the `investing-os` side independently:

- import contracts
- wiki templates
- destination mapping
- permanent knowledge structure
- runtime snapshot schema
- governance and handoff docs

Antigravity can complete the `stock_team` / `lianghua` side independently:

- code inventory
- runtime config classification
- test structure proposal
- execution-engine refactor proposal
- generated-data and sensitive-file classification
- snapshot consumer design

The only shared surface is the artifact contract:

```text
inventory manifest
import destination map
runtime snapshot schema
runtime config map
test report
```

If one side is unavailable, the other side should continue within its own scope and write assumptions clearly.

No agent should edit the other side's repository to unblock itself.

## Handoff Rule

If an agent needs work in the other agent's scope, it should write a request document in `handoff/requests/`.

It should not cross the boundary and edit the other system directly.

## Current Decision

Codex will proceed with the investing-os side:

- create `wiki/inbox/`
- define import contracts
- strengthen principle and case templates
- define runtime snapshot schema location and rules

The peer agent should remain paused on Phase 2 until Codex-owned import contracts are ready.
