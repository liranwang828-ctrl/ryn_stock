# Trading Quick Judge And Knowledge Tree Design

> Date: 2026-05-30
> Scope: Personal trading knowledge capture and daily decision support
> Status: Design note for future implementation

## Problem

Recent intraday discussion has produced useful judgment patterns, but they still live mostly inside long conversations:

- how to distinguish a `true breakdown` from `breakdown + weak lateral action`
- when `VWAP reclaim -> hold -> expansion` is a real executable signal
- how to tell whether the market is in `defensive mode` or `offensive mode`
- why software / security / optics / storage are not just “AI” as one bucket, but different capital-destination regimes
- how to keep `day trade`, `swing trade`, and `long-term thesis` from bleeding into each other

The current issue is not lack of insight; it is retrieval speed.

The user needs:

1. a very fast intraday judgment layer that can be used in seconds
2. a slower but durable knowledge structure that explains why the quick rules exist

## Goal

Create a two-layer personal trading knowledge artifact:

- a **Quick Judge Card** for live use
- a **Knowledge Tree** for review, training, and future lesson accumulation

The Quick Judge Card should reduce hesitation during market hours.
The Knowledge Tree should turn repeated conversations into durable trading intuition.

## Proposed Structure

### Layer 1: Quick Judge Card

This is the operational page.

It should be short enough to read while watching the tape and should answer:

- What kind of day is this?
- Is this a strong-stock pullback or a weak-stock failure?
- Is the `VWAP` move real or fake?
- Should I:
  - cut immediately
  - wait 3-10 minutes
  - try a small position
  - avoid chasing

Suggested sections:

1. `Environment First`
   - `QQQ`
   - `VIX`
   - `BTC`
   - broad software / infra / optics / security relative tone

2. `Strong vs Weak Template`
   - strong stock pullback
   - weak stock failed reclaim
   - complex story stock losing sponsorship

3. `VWAP Decision Rules`
   - reclaim
   - hold
   - second expansion
   - fake reclaim warning signs

4. `Execution Mapping`
   - immediate exit
   - filtered exit
   - small test entry
   - no-chase rule

5. `Timeframe Discipline`
   - day trade
   - swing trade
   - long-term thesis
   - rules for not changing contract mid-trade

### Layer 2: Knowledge Tree

This is the explanation page.

It should store the slower logic behind the quick rules and grow over time.

Suggested branches:

1. `Environment`
   - offensive day
   - defensive day
   - month-end / pension rebalance bias
   - crypto risk filter

2. `Sector Capital Flow`
   - software / security
   - optics / storage
   - power / infrastructure
   - when capital rotates inside AI instead of leaving AI

3. `Stock Types`
   - pure exposure stocks
   - complex platform stocks
   - weak broken stocks
   - high-beta event stocks

4. `Execution Patterns`
   - `VWAP reclaim -> hold -> expansion`
   - breakdown then weak lateral action
   - failed high-gap continuation
   - high-beta chase traps

5. `Position-Timeframe Discipline`
   - how to manage day trades
   - how to upgrade or refuse to upgrade into swings
   - how long-term thesis should differ from tactical setups

6. `Case Studies`
   - `BABA / SYM`: right direction, poor exit timing
   - `SNOW / NBIS / ARM`: missed reclaim opportunities
   - `IOT`: short-term success without full long-term thesis reversal
   - `COHR vs LITE`: complexity discount vs cleaner exposure

## Recommended Form

Use two markdown documents in `knowledge/`:

- `knowledge/trading_playbook_quick_judge.md`
- `knowledge/trading_knowledge_tree.md`

Why markdown first:

- fastest to create and revise
- easy to review manually
- easy to reference in future sessions
- low implementation load while dashboard work is intentionally paused

## Maintenance Rule

New lessons should not be written free-form only.

Each meaningful new experience should update one of these:

- add or revise one Quick Judge rule
- add a new Knowledge Tree node
- append one compact case study under an existing node

This keeps future conversations cumulative instead of repetitive.

## Non-Goals

This design does not require:

- dashboard integration right now
- new API endpoints
- automatic market polling
- a new UI workflow

The immediate objective is durable personal judgment, not product surface expansion.

## Success Criteria

The artifact is successful if:

1. the user can use the Quick Judge Card during market hours in under 10 seconds
2. the user can explain a decision afterward using Knowledge Tree language
3. new lessons from postmarket review can be slotted into the tree without rewriting the whole system
4. intraday conversations become shorter, because the shared vocabulary is already established
