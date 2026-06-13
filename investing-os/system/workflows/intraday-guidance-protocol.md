# Intraday Guidance Protocol

Purpose:

Project the whole investing-os cognition system into the pre-market plan and intraday guidance page.

The goal is not to create a trading signal dashboard.

The goal is to answer:

```text
Am I still inside the plan?
What am I allowed to do now?
What evidence is missing?
Which personal failure modes are active?
```

## Core Principle

The cognition system exists to serve disciplined execution during the trading day.

Files are not the final product.

Their practical output should appear in:

- pre-market plan
- intraday guidance sheet
- post-market review
- system updates

## System Inputs

### Constitution / WHY

Used to check:

- risk management before return
- no gambling-style trades
- no FOMO
- no trades outside understanding
- AI assists, user decides

Primary files:

- `WHY.md`
- `constitution.md`
- `framework.md`
- `system/checks/why-alignment-checklist.md`

### Cognition

Used to check:

- emotional state
- recent mistake patterns
- active bias risk
- strengths and weaknesses
- profit-streak overconfidence
- revenge / repair trading risk
- attention capture risk

Primary files:

- `cognition/self-model.md`
- `cognition/emotional-patterns.md`
- `cognition/bias-map.md`
- `cognition/mistake-patterns.md`
- `cognition/strengths-and-weaknesses.md`

### Decision

Used to check:

- position role
- thesis validity
- falsification condition
- risk budget
- approved tactic
- current watchlist

Primary files:

- `decision/position-roles.md`
- `decision/portfolio-thesis.md`
- `decision/falsification-map.md`
- `decision/risk-budget.md`
- `decision/current-watchlist.md`
- `decision/tactics/`

### Execution

Used to check:

- pre-market plan
- intraday behavior rules
- post-market review requirements
- daily / weekly workflow

Primary files:

- `execution/pre-market.md`
- `execution/intraday.md`
- `execution/post-market.md`
- `execution/daily-operating-loop.md`
- `execution/weekly-use-cases.md`

### Evolution

Used to check:

- adopted lessons
- pending lessons
- promotion rules
- latest system update
- whether an experience has already changed the system

Primary files:

- `evolution/promotion-queue.md`
- `evolution/promotion-rules.md`
- `evolution/system-update-log.md`
- `system/traceability/lesson-index.json`
- `system/traceability/file-lineage-index.json`

### Stock Team Evidence

Used to check facts only:

- market state
- QQQ / SPY / VIX
- sector and peer context
- symbol price / VWAP / volume / key levels
- IBKR position and fills if available
- missing data and stale data

Primary packet types:

- `pre-market-packet.md`
- `runtime-monitor-packet.md`
- `contextual-trade-evidence-packet.md`
- `post-market-packet.md`
- `company-research-packet.md`
- `industry-research-packet.md`

## State Machine

### Green

Meaning:

- pre-market plan is complete
- evidence is sufficient
- market has not invalidated the setup
- emotional state is stable
- no active red-line violation

Allowed:

- execute pre-approved actions only
- observe planned levels
- record decisions

Not allowed:

- expand strategy beyond pre-market plan
- increase risk without fresh plan
- use profit streak as confidence proof

### Yellow

Meaning:

- market, evidence, or emotion has partially diverged from plan
- symbol is near key level
- evidence is stale or incomplete
- attention capture risk is rising

Allowed:

- observe
- reduce risk
- execute small pre-planned actions
- create a fresh intraday check before any new risk

Requires before new risk:

- thesis
- trigger
- invalidation
- max loss
- position role
- attention budget

### Red

Meaning:

- stop-loss or major drawdown occurred
- revenge / repair trading risk is active
- market risk-off invalidates short-term tactics
- single symbol is binding attention or emotion
- user is trying to recover loss rather than follow plan

Allowed:

- reduce risk
- execute pre-planned exit
- review
- record facts
- ask for evidence

Forbidden:

- new short-term risk
- leveraged risk expansion
- averaging down to repair loss
- re-entry after short-term stop
- new tactic not approved pre-market

### No-Trade

Meaning:

- emotional control is compromised
- repeated rule violation occurred
- sleep / exhaustion risk is high
- one symbol has captured life / emotion / decision

Allowed:

- risk reduction
- journal
- post-market review
- system update proposal

Forbidden:

- all new risk
- discretionary short-term trades
- strategy experimentation

## Intraday State Change

`stock_team` facts may change market evidence.

Only `investing-os` can interpret those facts into permission state.

```text
stock_team packet
|
facts and missing data
|
investing-os interpretation
|
permission state
|
allowed / forbidden actions
|
intraday guidance sheet
```

## Intraday Guidance To Stock Team

After Stage 1, `investing-os` may produce an intraday guidance artifact for `stock_team`.

Template:

- `templates/intraday-guidance-to-stock-team.json`

Demo:

- `system/simulations/inputs/intraday-guidance.NVDA-conditional.demo.json`

This artifact tells `stock_team`:

- which symbols are in scope
- whether each symbol is observe-only, conditional-action, or reduce-risk-only
- which evidence conditions to monitor
- which levels are formulas to calculate
- which UI labels are forbidden
- where to write the latest evidence dashboard manifest

It does not give `stock_team` permission authority.

`stock_team` may display condition pass / fail states, freshness, missing data, and packet links.

`stock_team` must not display:

- buy / sell / hold recommendation
- permission approved
- should enter / should exit
- direct execution controls

## Dashboard Split

`investing-os` operating console:

- next safe action
- permission state
- allowed / forbidden actions
- cognitive risk guards
- link to latest `stock_team` evidence dashboard

`stock_team` evidence dashboard:

- packet readiness
- runtime snapshot freshness
- condition pass / fail facts
- data source health
- missing data
- generated packet links

Stable manifest contract:

- `integrations/stock-team-latest-dashboard-manifest.md`

## Pre-Market To Intraday Projection

The pre-market plan must produce:

- role for each active position
- ignore / observe / act classification
- key levels
- allowed tactics
- forbidden tactics
- max risk
- evidence required for action
- emotional red flags
- default intraday permission state

The intraday guidance sheet then tracks:

- whether each item is still inside plan
- which evidence has changed
- which personal failure modes are active
- whether permission state tightened
- what next action is allowed

## Output Rule

The intraday guidance page should output:

```yaml
current_state:
plan_alignment:
allowed_actions:
forbidden_actions:
evidence_ready:
evidence_missing:
active_cognitive_risks:
next_safe_action:
```

It must not output:

```yaml
buy:
sell:
hold:
price_target_as_command:
```

## Review Loop

After market close:

- compare planned state changes against actual state changes
- identify whether the user stayed inside the plan
- identify which cognition files were useful
- identify which files failed to affect behavior
- update promotion queue if needed
- update dashboard / report lineage if durable lessons were adopted
