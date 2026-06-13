# Unified Investing Operating System Architecture

Date: 2026-06-13

Status: approved design, awaiting written-spec review

## 1. Purpose

Build one personal investing product from the existing `investing-os` and
`stock_team` systems without rewriting either system.

The product optimizes for cognitive evolution first. Trading performance and
risk outcomes are feedback on decision quality, not permission for tools or
models to replace the user's judgment.

The user should experience one system with two internal, constrained kernels:

- `investing-os`: cognition, meaning, governance, plans, review, and learning.
- `stock_team`: evidence collection, calculations, backtests, and factual output.

The two kernels live in the same repository, are developed and tested together,
and remain separated by explicit ownership and data contracts.

## 2. Design Principles

1. One product and one user entry point, with modular internal ownership.
2. Reuse existing commands, packets, workflows, dashboards, and tests.
3. Add a thin coordinator instead of creating a second business implementation.
4. Enforce strict dependencies, but do not force a complete trading workflow
   every day.
5. Automate data and calculation work; stop for meaning, permission, exceptions,
   and lesson absorption.
6. Fail closed for production trading data. Degraded evidence is allowed for
   research, rehearsal, or user-approved observation only.
7. Preserve every important state transition and decision lineage.

## 3. Existing Capabilities To Preserve

### 3.1 Investing OS

Preserve:

- cognition records and personal patterns
- decision rules, risk budget, tactic status, and plans
- pre-market, intraday, post-market, and research workflows
- Packet templates and brain-muscle boundary contracts
- promotion queue, lesson lineage, and traceability indexes
- `dashboards/operating-console.html`
- `dashboards/growth-dashboard-draft.html`

The Operating Console remains the cognition-system home page. The Growth
Dashboard remains the cognition structure, lineage, capability, and report
view. Neither is replaced by the daily workflow UI.

### 3.2 Stock Team

Preserve and invoke through the coordinator:

- `market-context`
- `premarket`
- `intraday-snapshot`
- `intraday-dashboard`
- `trade-evidence`
- `company-packet`
- `industry-packet`
- `stage-context-backtest`
- `tactic-backtest`

Also preserve the underlying data adapters, metric calculation, caches,
backtest engines, Packet renderers, and active CLI tests.

### 3.3 Existing Contracts

Continue using:

- brain-muscle handshake protocol
- Stock Team CLI contract and evidence Packet headers
- runtime snapshot contract for approved rules
- degraded-mode schema
- traceability schema and indexes

The coordinator adds workflow state. It does not replace these contracts.

## 4. Target Architecture

```text
User
  |
  +-- Operating Console / Daily Workspace / Growth Dashboard
  +-- Conversation
  |
Session Router + Workflow Coordinator
  |
  +-- Investing OS cognition and governance kernel
  +-- Stock Team evidence and calculation kernel
  |
Packets + Runtime Snapshots + Traceability + Dashboard Manifest
```

### 4.1 Interaction Layer

The hybrid entry consists of:

- Dashboard: state, data health, blockers, backlog, artifacts, and legal actions.
- Conversation: interpretation, disagreement, focus selection, permission,
  plan approval, review, and lesson approval.

Dashboard buttons and natural-language requests must be translated into the
same coordinator action contract.

### 4.2 Session Router

The router identifies the user's activity type before creating state:

- `trading`
- `observation`
- `research`
- `review`
- `maintenance`

No file is required for a day with no activity. Research or discussion must not
create a trading session unless the user intends to enter the trading workflow.

### 4.3 Workflow Coordinator

The coordinator is the sole workflow controller. It owns:

- state transitions and prerequisite checks
- calls to existing Stock Team CLI commands
- tool timeout, retry, and error classification
- human confirmation gates
- artifact registration and hashes
- cross-day recovery
- generation of the read-only Dashboard manifest

It does not own market calculations, cognition, strategy meaning, or execution.
It must not place orders or emit final buy, sell, or hold commands.

## 5. Session Model

### 5.1 Trading Session

A full trading session may use:

```text
IDLE
-> DAY_INITIALIZED
-> STAGE0_READY
-> DISCUSSION_REQUIRED
-> FOCUS_CONFIRMED
-> STAGE1_READY
-> PLAN_CONFIRMATION
-> INTRADAY_ACTIVE
-> MARKET_CLOSED
-> REVIEW_REQUIRED
-> DAY_ARCHIVED
```

This is a dependency graph, not a mandatory daily checklist.

Rules:

- A production Stage 1 requires same-day valid Stage 0 evidence and a
  user-confirmed focus pool.
- Intraday monitoring without an approved plan is observation only.
- Intraday refresh may update runtime facts but may not regenerate Stage 0,
  Stage 1, or approved plan anchors.
- A no-trade day may close with a short no-trade record instead of a fabricated
  trade review.

### 5.2 Other Session Types

- Observation: market facts may refresh, but no new trade authorization exists.
- Research: company, industry, factor, or tactic work independent of today.
- Review: review a prior trade, period, behavior pattern, or historical case.
- Maintenance: data repair, contract checks, backtests, and system work.

### 5.3 Transverse States

- `BLOCKED_DATA`: required production evidence is invalid or missing.
- `WAITING_USER`: a human confirmation gate is pending.
- `DEGRADED_OBSERVE`: user-approved observation with degraded evidence.
- `FAILED_TOOL`: a tool failed and recovery information is recorded.

These states preserve the prior valid stage and do not silently advance it.

## 6. Daily Trading Flow

### 6.1 Initialize

Inputs:

- market date and calendar
- current positions and exposure facts when available
- active watchlist and researched candidates
- current permission and risk snapshot

Output: trading session state with a brain-owned universe request.

### 6.2 Stage 0

Reuse `python -m stock_team.cli market-context`.

The Packet must include explicit as-of time, timezone, market window, sources,
freshness, missing data, and warnings. Production flow requires evidence from
before 09:30 ET for that market date.

Invalid, post-open, stale, or missing production data produces `BLOCKED_DATA`.
The user may explicitly choose degraded observation; it cannot authorize risk.

### 6.3 Cognition Discussion

The user and Investing OS interpret Stage 0, discuss permission and priorities,
and confirm the focus pool. The discussion record must distinguish facts,
assumptions, interpretation, and user judgment.

Output: a versioned focus decision and Stage 1 decision sheet.

### 6.4 Stage 1

Reuse `python -m stock_team.cli premarket`.

It reads the same-day canonical Stage 0 artifact and the confirmed decision
sheet. It calculates evidence and rule collisions without granting permission.

Output: `plan-evidence-packet.md` and its artifact registration.

### 6.5 Plan Confirmation

Investing OS produces the plan, including permission, risk budget, allowed and
forbidden actions, exceptions, and pre-authorized conditions. The user approves
a specific version before the session becomes active.

### 6.6 Intraday

Reuse `intraday-snapshot` and `intraday-dashboard`.

Only runtime facts refresh: price, VWAP or levels, conditions, data health,
positions, account exposure, warnings, and freshness. Backtests and Stage 0/1
generation do not run in this loop.

### 6.7 Post-Market

Reuse `trade-evidence` and existing post-market workflows. The system prepares
facts, a review draft, open questions, and candidate lessons. The user decides
what each result means and whether any lesson is absorbed.

## 7. Cross-Day Recovery

An unfinished prior day must not trap the user in an obsolete session.

When a new market date begins and yesterday is still `INTRADAY_ACTIVE` or
`REVIEW_REQUIRED`, the coordinator may prefetch today's Stage 0 evidence but
must not freeze yesterday without user confirmation.

The Dashboard presents three choices:

1. Quick review, then start today (recommended).
2. Confirm freeze and schedule a full review later.
3. Complete the full review before starting today.

A quick review checks at minimum:

- fills and end-of-day position consistency
- material divergence from the approved plan
- unresolved account, leverage, or risk issues

After choice 1, yesterday becomes `QUICK_REVIEWED`. After choice 2, it becomes
`CLOSED_UNREVIEWED` with a dated backlog item. Choice 3 follows the full review
workflow. Until the user chooses, yesterday remains `REVIEW_PENDING`.

Ordinary review debt does not block today's Stage 0. Unresolved position,
account, leverage, or major rule-risk issues become a required risk check before
today's plan can be approved.

## 8. Research And Learning Path

Research is available at any time and is isolated from the active trading plan:

```text
Brain question and falsification conditions
-> Stock Team evidence or backtest
-> cognition discussion and conflict check
-> candidate queue
-> user approval
-> Investing OS adoption and lineage update
```

Existing entry points map as follows:

| Purpose | Existing command | Investing OS destination |
|---|---|---|
| Company research | `company-packet` | dossier / thesis candidate |
| Industry research | `industry-packet` | industry dossier / sector map |
| Macro or stage validation | `stage-context-backtest` | factor / gate evidence |
| Intraday tactic validation | `tactic-backtest` | tactic validation record |
| Trade review | `trade-evidence` | journal / case / lesson candidate |

All results default to `candidate_only`. An approved rule takes effect no earlier
than the next new trading session and records its version and source lineage.
Research may alert the user to reconsider a live plan, but cannot mutate it.

## 9. Dashboard Architecture

### 9.1 Operating Console

Retain `investing-os/dashboards/operating-console.html` as the product home page.
Preserve its permission, next actions, evidence gaps, routes, Packets, and pending
lessons. Add:

- current session type and state
- primary and alternate legal actions
- current blockers and recovery actions
- cross-day review debt
- links to Daily Workspace and recent artifacts

Its data should move from hand-maintained state toward the unified manifest.

### 9.2 Growth Dashboard

Retain `growth-dashboard-draft.html`, including the cognition map, lesson
lineage, capability radar, report archive, and current tasks. Add current
candidate-review status when the traceability indexes support it. This page is
not a trading workflow controller.

### 9.3 Daily Workspace

Add a focused daily page for Stage 0, discussion readiness, Stage 1, plan state,
intraday evidence, cross-day recovery, and review entry points.

### 9.4 Evidence View

Reuse Stock Team's evidence dashboard as a detail view. It is not a competing
product home page and cannot make decisions.

The first implementation phase should keep the current static HTML/JavaScript
approach and use a generated JSON manifest. A large frontend rewrite is out of
scope.

## 10. Data Contracts

### 10.1 Session State

Add schemas for trading and activity sessions. A trading state minimally holds:

```json
{
  "session_id": "trading-2026-06-15",
  "session_type": "trading",
  "market_date": "2026-06-15",
  "state": "STAGE0_READY",
  "state_version": 7,
  "artifacts": [
    {"role": "stage0", "path": "...", "sha256": "..."}
  ],
  "data_quality": {"status": "production_ready", "warnings": []},
  "pending_confirmations": [],
  "allowed_actions": [],
  "backlog_links": [],
  "last_error": null,
  "updated_at": "..."
}
```

Runtime storage should live under `investing-os/system/runtime/` and remain
separate from approved rules and evidence Packets.

### 10.2 Coordinator Action

Dashboard and conversation actions share this shape:

```json
{
  "intent": "start_stage0",
  "session_id": "trading-2026-06-15",
  "expected_state": "DAY_INITIALIZED",
  "user_confirmation": false,
  "parameters": {},
  "idempotency_key": "..."
}
```

The coordinator rejects stale `expected_state` values and unauthorized
transitions.

### 10.3 Dashboard Manifest

The read-only manifest projects session state, evidence health, current
permission snapshot, legal actions, backlog, and artifact links. It contains no
credentials and does not become a second authority for state.

## 11. Reliability And Error Handling

- Actions are idempotent. Repeated clicks or retried requests must not duplicate
  artifacts or transitions.
- State updates use optimistic `state_version` checks.
- Only one state-writing task may run per session.
- Generated files are written to a temporary path, validated, then atomically
  replaced.
- Every tool call has a bounded timeout and retry policy.
- Network and temporary provider failures may retry. Contract errors and human
  gates do not retry automatically.
- Error state records command, input versions, error class, retryability, and
  last known valid state.
- Page refresh, model change, or process restart restores state from the state
  file and verifies registered artifact hashes.

Data quality levels are explicit:

- `production_ready`
- `degraded`
- `stale`
- `missing`

Only `production_ready` may advance a production trading dependency without
additional user action.

## 12. Security And Ownership

- The coordinator and Stock Team must not place orders.
- Stock Team may write evidence and runtime outputs, but not cognition or
  decision files.
- Only a user-approved adoption action writes a candidate lesson or rule into
  long-term cognition or decision artifacts.
- Credentials, raw account exports, and sensitive broker state remain local and
  excluded from Git.
- Every transition records the triggering action, input versions, artifact
  hashes, timestamp, and confirmation where applicable.
- Lower-capability models may implement scoped tasks and submit candidates, but
  cannot reinterpret system boundaries or approve trading and learning states.

## 13. Acceptance Scenarios

1. Production data completes Stage 0 through review with existing commands.
2. Missing Stage 0 data blocks production flow and offers degraded observation.
3. A company-only discussion creates research activity but no trading session.
4. A no-trade day closes without a fabricated trade review.
5. An unreviewed prior day presents three choices and is not auto-frozen.
6. Today's Stage 0 may prefetch while the prior-day choice is pending.
7. An unresolved material risk blocks today's plan approval, not Stage 0.
8. A tool timeout is visible, retryable, and does not duplicate artifacts.
9. Repeated UI actions produce one transition.
10. Restarting the page or model restores the same state and artifacts.
11. A backtest result enters the candidate queue without changing today's plan.
12. User-approved learning updates the target file, lineage indexes, and Growth
    Dashboard data.
13. Existing Operating Console and Growth Dashboard content remains available.
14. Existing CLI contract tests continue to pass after coordinator integration.

## 14. Implementation Phases

This architecture should be delivered as separately reviewable plans and
changes, not one large implementation.

### Phase 1: Coordinator Foundation

- session and action schemas
- state store and transition validation
- coordinator CLI
- adapters for existing Stock Team commands
- idempotency, atomic writes, and targeted tests

### Phase 2: Unified Interaction

- Dashboard manifest
- Operating Console integration
- Daily Workspace
- cross-day recovery choices
- restart and retry behavior

### Phase 3: Production Trading Loop

- production-quality Stage 0 collector
- production data quality gates
- end-to-end Stage 0 through post-market validation
- retained source directories remain untouched until this passes

### Phase 4: Research And Learning Integration

- activity sessions
- candidate queue adapters
- approval and adoption action
- traceability and Growth Dashboard refresh

### Phase 5: Operational Hardening

- background scheduling where useful
- IBKR runtime integration
- provider resilience and observability
- broader integration and recovery tests

## 15. Out Of Scope

- automated order placement
- automatic trading permission decisions
- automatic lesson adoption
- replacing the existing CLI business logic
- a large frontend framework rewrite
- intraday backtest or optimization inside the live refresh loop
- full factor optimization before the operating loop is stable

## 16. Guidance For Lower-Capability Implementers

Each implementation task must specify:

- exact existing files and commands to reuse
- exact files allowed to change
- input and output contracts
- forbidden behavior and ownership boundary
- tests to add or run
- acceptance scenario covered

Implementers must not redesign the architecture, rename established contracts,
or combine phases without explicit approval. Any ambiguity or contract conflict
must be returned for higher-level review rather than resolved by invention.
