# Phase 4D Request: Runtime Snapshot Consumer Design

Date: 2026-06-05

Requested by: Codex  
Owner: Antigravity  
Target system: `stock_team` / `lianghua`  
Mode: design first, no runtime behavior change without user approval

## Purpose

Design how `stock_team` should consume approved `investing-os` runtime snapshots.

This is a request for a design and implementation plan, not permission to modify trading behavior.

## Context

`investing-os` has defined snapshot contracts for:

- tactical rules
- risk limits
- watchlist metadata
- signal interpretation
- degraded mode

These files live under:

```text
investing-os/system/data/schemas/
investing-os/system/data/snapshots/
```

The approval workflow says runtime systems may consume only:

```text
investing-os/system/data/snapshots/active/
```

No active snapshots exist yet.

## Required Boundary

`stock_team` must not read:

- `investing-os/wiki/`
- `investing-os/templates/`
- `investing-os/constitution.md`
- `investing-os/framework.md`
- `investing-os/WHY.md`
- `investing-os/system/checks/`
- `investing-os/system/data/snapshots/drafts/`
- `investing-os/system/data/snapshots/examples/`

`stock_team` may read only approved active snapshots after design approval:

```text
investing-os/system/data/snapshots/active/
```

## Consumer Requirements

### 1. Read-Only Consumption

`stock_team` should treat `investing-os` snapshots as read-only inputs.

It must not write back into `investing-os`.

### 2. Schema Validation

Before using any snapshot:

1. detect snapshot type
2. load matching schema
3. validate JSON structure
4. reject invalid snapshot
5. fail closed

Invalid snapshots must not be partially consumed.

### 3. Status Enforcement

Runtime consumers may use only snapshots with:

```json
"status": "active"
```

Files with `draft`, `retired`, or missing status must be ignored or rejected.

### 4. One Active Snapshot Per Type

If more than one active snapshot exists for the same type, consumer behavior should fail closed.

Do not pick one silently.

### 5. Fail-Closed Behavior

If snapshot loading fails, validation fails, data is stale, or context is missing:

- no new discretionary orders
- no generated buy/sell command
- alerts and review tasks only
- manual review required

### 6. No AI Override

LLM output must not override snapshot restrictions.

If an AI-generated suggestion conflicts with a snapshot:

- flag conflict
- block action-oriented conclusion
- require manual review

### 7. No Direct Trading Permission

Snapshots can provide:

- alerts
- boundaries
- forbidden actions
- manual review requirements
- plan update candidates
- journal prompts

Snapshots cannot provide:

- direct buy command
- direct sell command
- autonomous order sizing
- broker execution approval

## Snapshot Type Handling

### Tactical Rules

Expected use:

- discipline alerts
- forbidden-action checks
- monitor-only prompts

Do not turn monitor-only rules into hard execution blocks unless separately approved.

### Risk Limits

Expected use:

- risk boundary alerts
- manual review triggers
- hard blocks only when explicitly marked and approved

### Watchlist Metadata

Expected use:

- symbol role lookup
- no-trade state detection
- thesis status awareness
- allowed/forbidden action context

If symbol metadata is missing, default to no new discretionary trade.

### Signal Interpretation

Expected use:

- convert raw market signals into alerts or review tasks
- prevent signal-to-command drift

Signals should not create trade permission.

### Degraded Mode

Expected use:

- shared fail-closed behavior
- missing plan/data/context handling

Degraded mode should always block new discretionary orders.

## Antigravity Deliverables

Please produce, in `stock_team` scope only:

1. Runtime consumer map:
   - candidate modules
   - current config loading paths
   - likely insertion points
   - current tests
2. Design proposal:
   - loader shape
   - validation approach
   - fail-closed behavior
   - logging/reporting surface
3. Test plan:
   - no active snapshots
   - invalid JSON
   - schema mismatch
   - duplicate active snapshots
   - draft snapshot present
   - retired snapshot present
   - missing required data
   - AI suggestion conflicts with snapshot
4. Risk review:
   - accidental direct trading permission
   - fail-open paths
   - hidden wiki coupling
   - stale snapshot handling
5. Implementation plan:
   - phases
   - files to modify
   - tests to add
   - rollback plan

## Do Not Do Yet

Do not:

- modify order execution behavior
- connect to broker actions
- consume draft or example snapshots
- create active snapshots
- move files between repositories
- delete existing `stock_team` files
- edit `investing-os`

## Acceptance Criteria For Design

The design is acceptable when it proves:

- `stock_team` reads only approved active snapshots
- invalid or missing snapshots fail closed
- runtime tools never read raw wiki docs
- AI cannot override discipline boundaries
- no snapshot becomes an autonomous trading decision
- tests cover the main failure modes

