# Research Report Reliability Design

## Status

- Date: 2026-07-19
- Status: approved
- Scope: fix the logic ambiguity in reading-layer research reports and define a reusable reliability gate
- First repair target:
  - `investing-os/dashboards/reports/AMAT-reality-layer-report.html`
- Out of scope:
  - full automated report generation
  - quantitative scoring engine
  - options-data pipeline overhaul

## Background

The current reading-layer reports already have:

- company role positioning
- Reality confirmed / unconfirmed split
- key price anchors
- event / price / interpretation timeline

But one important logic bug surfaced in the AMAT report:

- when price stretched to a high, the prose could be read as if the company became weaker
- when price pulled back, the prose could be read as if the company became stronger

The real issue is not the data.

The issue is dimension mixing.

The report sometimes uses one sentence to talk about multiple things at once:

- Reality
- Price
- Behavior
- Odds

That creates the most dangerous kind of error:

- the report sounds reasonable
- but the investment meaning becomes inverted

## Goal

Add a reusable reliability check so each research report clearly separates:

- what got stronger or weaker in Reality
- what got more stretched or cheaper in Price
- what improved or worsened in Behavior
- what became more or less attractive in Odds

The report should help the user act more clearly, not blur these layers together.

## Core Principle

Price moving down does not automatically mean the company got stronger.

Price moving up does not automatically mean the company got weaker.

The report must explicitly distinguish:

1. Reality state
2. Price state
3. Behavior state
4. Odds state

## Reliability Framework

### 1. Dimension Separation

Every major conclusion must have an obvious subject.

The reader should be able to tell whether a sentence is describing:

- the business / industry Reality
- market expectations
- the current valuation or price stretch
- the current tape / trend behavior
- the investing odds

If one sentence tries to do more than one of these jobs, it should be split.

### 2. High / Pullback Semantics

When a stock reaches an aggressive high:

- that usually says more about Price stretch or expectation expansion
- it does not automatically say Reality is weaker

When a stock has a deep pullback:

- that usually says Behavior weakened
- it may improve Odds if Reality remains intact
- it does not automatically say the stock is stronger

### 3. Timeline Interpretation Rule

Each timeline node may still use:

- Event
- Price
- Interpretation

But the interpretation line must explain which dimension changed:

- Reality strengthened
- Price stretched
- Behavior weakened
- Odds improved after repricing

It should not jump directly from price move to investment recommendation.

### 4. Key Price Anchor Rule

Key prices are action-support tools.

They can justify:

- watch level
- probe level
- thesis upgrade level
- thesis downgrade level

But they cannot independently prove:

- the business improved
- the industry Reality deteriorated

### 5. Current View Rule

The “current investment view” block should be readable as four separate judgments:

- Reality
- Price
- Behavior
- Odds

This can be written as one paragraph or a short list, but all four dimensions must be visible.

## Output

This design adds three reusable artifacts:

1. a reliability checklist under `investing-os/system/checks/`
2. template guidance in `investing-os/dashboards/research-report-template.html`
3. a first repaired example in `investing-os/dashboards/reports/AMAT-reality-layer-report.html`

## Success Criteria

The repair is successful if:

- the AMAT report no longer implies that pullback equals strengthening
- the report explicitly separates Reality / Price / Behavior / Odds
- future reports have a canonical checklist to pass before they are treated as trustworthy reading surfaces
