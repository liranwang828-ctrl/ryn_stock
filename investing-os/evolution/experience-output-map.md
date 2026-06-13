# Experience Output Map

## Purpose

Define what experience should be produced after each orchestrated workflow and where it should land in `investing-os`.

The goal is to prevent evidence collection from becoming an endpoint.

Evidence must feed:

- cognition
- decision
- execution
- evolution
- wiki
- checks
- templates

## Core Rule

Every orchestrated workflow should end with an experience decision:

```text
What did this teach?
Where should it land?
What should change next time?
```

If nothing should change, record that explicitly.

## Destination Types

### Cognition Output

Use when experience reveals:

- bias
- emotional pattern
- mistake pattern
- strength or weakness
- self-model update

Destination:

- `cognition/self-model.md`
- `cognition/bias-map.md`
- `cognition/emotional-patterns.md`
- `cognition/mistake-patterns.md`
- `cognition/strengths-and-weaknesses.md`

### Decision Output

Use when experience changes:

- thesis
- position role
- watchlist state
- risk budget
- falsification condition
- decision log

Destination:

- `decision/portfolio-thesis.md`
- `decision/position-roles.md`
- `decision/current-watchlist.md`
- `decision/risk-budget.md`
- `decision/falsification-map.md`
- `decision/decision-log.md`

### Execution Output

Use when experience changes:

- pre-market process
- intraday rule
- post-market process
- risk lock behavior
- no-trade condition

Destination:

- `execution/daily-operating-loop.md`
- `execution/pre-market.md`
- `execution/intraday.md`
- `execution/post-market.md`
- `system/checks/`

### Evolution Output

Use when experience changes the operating system:

- principle candidate
- historical case
- checklist update
- runtime parameter candidate
- system update log

Destination:

- `evolution/system-update-log.md`
- `evolution/promotion-rules.md`
- `wiki/principles/candidates/`
- `wiki/historical-cases/`
- `system/data/runtime-parameter-map.md`

### Knowledge Output

Use when experience adds durable external knowledge:

- company understanding
- industry structure
- methodology
- source note

Destination:

- `wiki/companies/`
- `wiki/industries/`
- `wiki/methodologies/`
- `wiki/sources/`

## Use Case Output Rules

### Pre-Market Planning

Required outputs:

- allowed actions
- no-trade conditions
- watchlist state
- sleep risk awareness

Possible experience outputs:

- `decision/current-watchlist.md`: if a symbol state changes
- `decision/position-roles.md`: if a role changes
- `execution/pre-market.md`: if process gap appears
- `wiki/journals/`: if plan should be archived

Do not output:

- new principle from plan alone
- active runtime snapshot
- trade permission from stock_team data alone

### Intraday Check

Required outputs:

- fact summary
- plan match / plan mismatch
- allowed action state
- missing-data note

Possible experience outputs:

- `decision/decision-log.md`: if action state changes
- `execution/intraday.md`: if a rule failed
- `system/checks/`: if checklist needs improvement
- `wiki/journals/`: if emotional or execution data matters

Do not output:

- new thesis from signal alone
- buy/sell command without plan

### Post-Market Review

Required outputs:

- plan vs action
- emotion
- decision quality
- risk review
- system update candidates

Possible experience outputs:

- `wiki/journals/`
- `cognition/`
- `decision/`
- `execution/`
- `evolution/system-update-log.md`
- `wiki/principles/candidates/`
- `wiki/historical-cases/`

Do not output:

- overfit principle from one regret event
- hidden action rule without review

### Contextual Trade Review

Required outputs:

- fill path
- market context
- symbol context
- trader interview
- mistake / strength classification
- system update decision

Possible experience outputs:

- `wiki/journals/`
- `wiki/historical-cases/`
- `cognition/mistake-patterns.md`
- `cognition/emotional-patterns.md`
- `decision/risk-budget.md`
- `execution/intraday.md`
- `system/checks/short-term-trade-checklist.md`
- `evolution/system-update-log.md`

Do not output:

- final psychological conclusion without interview
- market-fact claim without evidence
- principle promotion without review

### Company Analysis

Required outputs:

- company role
- value capture
- thesis candidate
- falsification
- risks
- open questions

Possible experience outputs:

- `wiki/companies/`
- `decision/portfolio-thesis.md`
- `decision/falsification-map.md`
- `decision/current-watchlist.md`
- `wiki/methodologies/`

Do not output:

- buy list
- active watchlist upgrade without review
- thesis without falsification

### Industry Analysis

Required outputs:

- worldview link
- supply chain
- bottleneck
- value capture
- key companies by role
- counter-thesis

Possible experience outputs:

- `wiki/industries/`
- `wiki/methodologies/`
- `wiki/companies/` research tasks
- `decision/current-watchlist.md`

Do not output:

- sector trade from theme excitement
- peer trade without catalyst scope

### Weekly Summary

Required outputs:

- what improved
- what repeated
- what broke
- what changed in cognition, decision, execution, and evolution
- next week focus

Possible experience outputs:

- `cognition/`
- `decision/`
- `execution/`
- `evolution/system-update-log.md`
- `wiki/principles/candidates/`
- `wiki/historical-cases/`
- `system/data/runtime-parameter-map.md`

Do not output:

- too many new rules
- action pressure for next week without thesis

### Learning Session

Required outputs:

- concept learned
- relevance to worldview
- decision implication
- execution implication
- open question

Possible experience outputs:

- `cognition/self-model.md`
- `wiki/methodologies/`
- `wiki/industries/`
- `wiki/companies/`
- `evolution/system-update-log.md`

Do not output:

- knowledge dump with no decision or cognition implication

## Experience Decision Template

Use at the end of every meaningful workflow:

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

## No-Update Rule

Sometimes the correct output is no system change.

That is valid if:

- no new pattern appeared
- evidence was insufficient
- the event repeated an already captured lesson
- the issue belongs in temporary context only

Record:

```yaml
no_update_reason:
follow_up_needed:
```

