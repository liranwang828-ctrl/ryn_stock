# Key Price Anchors Design

## Status

- Date: 2026-07-19
- Status: proposed
- Scope: define how research reports should derive and present key investment prices
- Initial targets:
  - NBIS verification-layer reading report
  - AMAT reality-layer reading report
- Out of scope:
  - full automated options-flow ingestion
  - broker execution logic
  - intraday trading automation

## Background

The current reading-layer report is good at answering:

- what the company is
- what the market is trading
- what Reality has or has not confirmed
- what needs validation next

But it still lacks a direct bridge from research to actual investing action.

For real investing use, the report also needs to answer:

- at what prices the company becomes worth watching closely
- at what prices a probe position becomes reasonable
- at what prices conviction can be upgraded
- at what prices the thesis must be downgraded

Without this layer, the report remains a strong research note but not yet a practical decision surface.

## Goal

Add a reusable “key price anchors” methodology that can be applied across company reports.

This methodology must translate research judgment into price levels without pretending that one technical tool alone can determine fair entry.

## Design Principle

Key prices should never come from a single source.

They must be derived from layered evidence.

Different tools answer different questions:

- market structure answers where meaningful price interaction happened
- moving averages and anchored VWAP answer how current participants are positioned
- options positioning answers short-term pinning or pressure zones
- thesis judgment answers what price actually changes the investment decision

The final output should combine these layers rather than replace one with another.

## Core Framework

The key price system uses four layers.

### Layer 1: Market Structure Prices

This is the base layer.

It should include:

- recent swing highs and lows
- gap levels
- breakout / breakdown zones
- multi-week range boundaries
- high-volume acceptance areas when visible

This layer answers:

- where price previously changed behavior
- where supply or demand clearly appeared
- what zones are structurally important even before adding indicators

This is the most stable layer and should exist in every report.

### Layer 2: Trading Behavior Prices

This layer refines structure with positioning behavior.

It should include:

- 20DMA
- 50DMA
- anchored VWAP from the most relevant event
- anchored VWAP from earnings, breakout day, or major reset day when relevant
- short recent trend slope

This layer answers:

- whether the stock is in healthy pullback or deeper trend damage
- whether the current price is above or below the average cost basis of the latest important move
- whether buyers still control the tape after a major catalyst

Moving averages describe trend state.

Anchored VWAP describes cost-basis gravity around a specific event.

### Layer 3: Derivatives / Positioning Prices

This layer is optional but valuable when data is available and current.

It should include:

- call wall
- put wall
- large open-interest strikes
- major gamma pin zones
- expiration-sensitive pressure levels

This layer answers:

- why price may stall near a certain level
- why certain round numbers matter more than normal
- whether a structural level is being reinforced by positioning

This layer should never be the sole basis for mid-term investment decisions because it is fast-moving and perishable.

### Layer 4: Thesis Prices

This is the final investment translation layer.

It combines research judgment with the first three layers.

It should define:

- watch price
- probe price
- conviction-upgrade price
- thesis-downgrade price

This layer answers:

- when the stock becomes interesting enough to monitor actively
- when the odds justify a starter position
- when price recovery or continued strength is actually confirming the thesis
- when price behavior is invalidating the thesis

This is the layer the user actually acts on.

## Output Model

Each report should present a dedicated block:

### Key Price Anchors

It should contain five rows:

1. Current price context
2. Watch zone
3. Probe zone
4. Thesis-upgrade zone
5. Thesis-downgrade zone

Each row should include:

- the price or price range
- the main reason
- the evidence layer used
- a short action interpretation

Example structure:

| Anchor | Price | Why it matters | Main evidence layer | Action meaning |
|---|---|---|---|---|
| Watch zone | $X–Y | Returns to structural support + anchored VWAP | Structure + behavior | Start focused monitoring |
| Probe zone | $X–Y | Better odds if pullback holds | Structure + thesis | Small test position only |
| Upgrade zone | Above $X | Recovery confirms demand | Behavior + thesis | Raise conviction |
| Downgrade zone | Below $X | Thesis damage / failed support | Structure + thesis | Reduce or stop forcing idea |

## Calculation Order

The report should determine these prices in a fixed order:

1. Mark structure first
2. Overlay moving averages and anchored VWAP
3. Check whether derivatives positioning reinforces nearby levels
4. Translate the combined picture into thesis prices

This order matters because:

- technical indicators without structure are noisy
- options levels without thesis are tactical only
- thesis prices without market structure are too subjective

## Event Anchoring Rules

Anchored VWAP should not be applied randomly.

The report should choose one or more anchors from:

- last earnings gap or major earnings reset
- major financing / strategic investment day
- major breakout day
- major narrative reset day

The report should explicitly state which event anchor was used.

## Timeframe Rules

The report is for swing / position-investing support, not scalping.

So the price system should prioritize:

- daily structure
- multi-week behavior
- event-based anchors

It should not overfit:

- 1-minute noise
- random intraday spikes
- stale derivatives data

## Company-Type Adaptation

Different company layers should use the same structure, but with different emphasis.

### Verification-Layer Companies

Emphasis:

- bigger gap between watch zone and probe zone
- heavier weight on thesis uncertainty
- stronger downgrade discipline

### Reality-Layer Companies

Emphasis:

- more confidence in structure and earnings-based anchors
- more focus on pullback quality versus trend continuation
- tighter connection between valuation concern and upgrade zone

## Success Criteria

This design is successful if:

1. every report can convert research into practical price anchors
2. the user can immediately distinguish watch, probe, upgrade, and downgrade zones
3. each price has an explainable evidence basis
4. the system avoids fake precision while remaining decision-useful

