# Codex x Antigravity Collaboration Protocol

Date: 2026-06-05

## Core Rule

Codex and Antigravity work independently.

They should not block each other, wait for each other, or edit each other's owned files.

## Ownership

### Codex Owns `investing-os`

Codex is responsible for:

- WHY alignment
- project governance
- wiki structure
- import contracts
- templates
- destination mapping
- runtime snapshot schema
- handoff documentation

Codex must not edit:

- `stock_team`
- `lianghua`
- execution engine code
- runtime account state
- raw market data

### Antigravity Owns `stock_team` / `lianghua`

Antigravity is responsible for:

- code inventory
- runtime config classification
- generated-data classification
- sensitive-file classification
- test structure proposal
- execution-engine refactor proposal
- snapshot consumer design

Antigravity must not edit:

- `investing-os` governance files
- `WHY.md`
- `PROJECT.md`
- `constitution.md`
- `framework.md`
- `AGENTS.md`
- `wiki/`
- `templates/`
- `system/`

unless the user explicitly asks for it.

## Shared Artifacts

The two agents coordinate only through stable artifacts:

- inventory manifest
- inventory summary
- import destination map
- runtime config map
- runtime snapshot schema
- test report
- handoff request

## No Cross-Editing

If one agent needs something from the other side, it writes a request in:

```text
handoff/requests/
```

It does not modify the other side directly.

## No Hidden Dependencies

Each side should be able to finish its current phase independently.

If an assumption is needed, write it down and continue within owned scope.

## Integration Point

Integration happens only after both sides produce artifacts.

```text
Codex artifact: import destination map / snapshot schema
Antigravity artifact: code map / runtime config map / test report
|
user review
|
approved integration step
```

## Safety Rule

No asset migration, deletion, runtime refactor, or trading-action automation should happen without explicit user approval for that phase.

