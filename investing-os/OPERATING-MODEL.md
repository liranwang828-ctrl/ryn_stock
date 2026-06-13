# Operating Model

## Core Assertion

`investing-os` is not centered on wiki, research, or stock_team.

It is centered on four living systems:

1. Cognition core
2. Decision system
3. Execution system
4. Evolution system

Research and trading are nutrient sources.

AI and `stock_team` are amplifiers and tools.

Wiki is long-term memory.

## System Diagram

```text
trading experience        research experience        stock_team output
        |                         |                         |
        +------------ nutrient stream ----------------------+
                                  |
                                  v
                          evolution/
                                  |
            +---------------------+---------------------+
            |                     |                     |
            v                     v                     v
       cognition/ ----------> decision/ ----------> execution/
            ^                     |                     |
            |                     v                     v
            +------------- review and learning <--------+
```

## Four Core Systems

### Cognition Core

Question:

Who am I as an investor, and how does my judgment improve or fail?

Main files:

- `cognition/self-model.md`
- `cognition/bias-map.md`
- `cognition/emotional-patterns.md`
- `cognition/mistake-patterns.md`
- `cognition/strengths-and-weaknesses.md`

### Decision System

Question:

Given my cognition and research, what is the current judgment state?

Main files:

- `decision/portfolio-thesis.md`
- `decision/position-roles.md`
- `decision/risk-budget.md`
- `decision/falsification-map.md`
- `decision/current-watchlist.md`
- `decision/decision-log.md`

### Execution System

Question:

How do I act consistently with the decision state under market pressure?

Main files:

- `execution/daily-operating-loop.md`
- `execution/pre-market.md`
- `execution/intraday.md`
- `execution/post-market.md`

### Evolution System

Question:

How does every trade, review, and research session improve the system?

Main files:

- `evolution/learning-loop.md`
- `evolution/promotion-rules.md`
- `evolution/system-update-log.md`

## Supporting Layers

### `wiki/`

Long-term memory:

- principles
- cases
- journals
- companies
- industries
- methodologies

### `system/`

Infrastructure:

- workflows
- checks
- data contracts
- packet contracts
- snapshot schemas

### `templates/`

Forms used to create structured notes.

### `integrations/`

Boundaries for external tools.

### `handoff/`

Coordination and transfer records.

### `agents/`

AI roles and boundaries.

## Nutrient Rule

Every meaningful trading or research event should ask:

1. What did this teach cognition?
2. What changed in decision state?
3. What execution rule worked or failed?
4. What should evolve in the system?

If the answer is "nothing", it may remain temporary context.

