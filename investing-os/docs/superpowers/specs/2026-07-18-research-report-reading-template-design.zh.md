# Research Report Reading Template Design

## Status

- Date: 2026-07-18
- Status: proposed
- Scope: readable HTML-style research report template for company + industry hybrid reports
- Initial targets:
  - NBIS verification-layer report
  - AMAT reality-layer report
- Out of scope:
  - automated data ingestion changes
  - dashboard routing changes
  - changes to the underlying markdown research source format

## Background

The current NBIS and AMAT research outputs are already useful as research drafts.

They have:

- company framing
- industry-layer framing
- reality vs unconfirmed split
- key validation checkpoints
- structured research cards

But they still read more like strong internal notes than polished reading reports.

The main issue is not content absence.

It is presentation hierarchy.

The most important information is still buried in the same visual layer as ordinary body text.

That makes repeat reading, comparison, and review slower than necessary.

## Goal

Create a reusable reading template that makes research reports:

1. easier to scan
2. easier to compare across company types
3. more visually structured
4. still backed by the same markdown research source

## Target Use Case

This template is for reports where:

- a company is analyzed inside an industry or value-chain layer
- the output includes both interpretation and monitoring
- the reader may want both a fast read and a deep read

It should work for both:

- verification-layer companies like NBIS
- reality-layer companies like AMAT

## Design Problem

The current markdown reports have four readability gaps:

1. critical conclusions are not visually elevated enough
2. event timelines are text-heavy instead of scan-friendly
3. company layer and industry layer are not visually coupled enough
4. the structured card is useful but not yet presented as a decision surface

## Chosen Approach

Use a dual-layer report:

- top layer for fast reading
- lower layer for full research depth

The top layer should feel like a designed report.

The lower layer should preserve the full narrative and analytical detail.

## Reading Template Structure

The reading version should contain five blocks.

### 1. Hero Summary

This is the report entry point.

It should show:

- company name and ticker
- report title
- one-sentence positioning
- current stance
- layer classification

Examples:

- Verification Layer
- Reality Indicator Layer
- Commercialization Layer

The user should know the report's core category within seconds.

### 2. Four Core Cards

Immediately below the hero, show four compact cards:

- What the market is trading
- Reality confirmed
- Reality unconfirmed
- Next 1–2 quarter validation

These are the highest-value reading surfaces in the entire report.

They should be visible without requiring deep reading.

### 3. Event / Price / Interpretation Timeline

This block should convert the current text-heavy event history into a readable timeline.

Each line item should ideally show:

- date
- event
- market or price reaction
- interpretation now

Interpretation should clearly mark whether the event mainly supports:

- Reality
- Narrative
- Mixed

This block is especially important for high-volatility names like NBIS.

### 4. Company × Industry Coupling Block

The company should not be read in isolation.

This block should visually connect:

- company role
- industry layer
- value capture position
- comparable companies

It can be implemented as:

- two-column layout
- paired cards
- stacked comparison rows

The key requirement is that the user can immediately understand:

- what the company does
- where it sits in the value chain
- what kind of company it should be compared against

### 5. Full Research Body

The designed reading layer should not replace the research body.

It should sit above it.

The lower section should preserve:

- the full narrative
- bull / bear framing
- falsification logic
- next actions
- source notes
- structured research card

This keeps the report readable without losing depth.

## Company-Type Adaptation

The same reading template should support different company types, but emphasize different questions.

### For Verification-Layer Reports

The template should naturally emphasize:

- what still requires validation
- what the market is prematurely pricing
- what event would upgrade the company

### For Reality-Layer Reports

The template should naturally emphasize:

- what is already being proven in numbers
- what part of the cycle is being monetized
- whether price has outrun duration

This means the template stays structurally consistent, while the content emphasis shifts by layer.

## Source Model

The template should be generated or derived from the same markdown report, not maintained as a completely separate research system.

That keeps:

- source of truth stable
- editing simple
- future automation possible

The report source should remain brain-owned markdown.

The reading version should be a consumption layer.

## Intended File Shape

If implementation proceeds, expected work likely includes:

- one report reading template or HTML fragment pattern
- one first rendered reading example, likely for NBIS or AMAT
- no destructive rewrite of existing markdown reports

## Success Criteria

This design is successful if:

1. the report becomes easier to scan in under one minute
2. the most important decision information is visually elevated
3. company and industry context are easier to read together
4. the same template can be reused for both NBIS-like and AMAT-like reports
