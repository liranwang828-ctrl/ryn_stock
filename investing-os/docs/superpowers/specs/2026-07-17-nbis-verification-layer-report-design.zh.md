# NBIS Verification Layer Report Design

## Status

- Date: 2026-07-17
- Status: proposed
- Scope: first reusable company + industry hybrid research report format
- Primary example target: NBIS
- Out of scope:
  - dashboard rendering changes
  - automated ingestion pipeline changes
  - stock_team orchestration changes

## Background

We want a research report format that can be reused often, not a one-off note.

The report should combine:

- investing-os cognition and methodology
- stock_team evidence-oriented support
- company-level analysis
- industry / value-chain role analysis

NBIS is a strong first example because it is not a fully verified core asset.

It sits closer to the AI commercialization and business-model verification layer.

That makes it a better test of our research system than a simpler "good company / bad company" write-up.

## Goal

Create a reusable hybrid report format that:

1. explains a company's role inside an industry or value-chain layer
2. distinguishes confirmed Reality from unconfirmed Narrative
3. identifies the next one to two quarters of validation
4. ends with an actionable investment stance without pretending certainty

## Chosen Use Case

This first report serves two goals at once:

- medium-term validation tracking for the next one to two quarters
- longer-horizon framing for where the company sits in the AI value chain

It should therefore be:

- readable as a full research report
- reusable as a structured research object

## Chosen Output Form

Two linked outputs:

1. a readable research report
2. a structured research card at the end

The readable report helps interpretation.

The structured card helps future reuse in daily, hypothesis, and research-database workflows.

## Design Options Considered

### Option A — Company-only report

Focus only on NBIS as a company note.

Pros:

- quickest to write

Cons:

- loses the industry-role context
- weak reuse value

### Option B — Industry-only verification-layer note

Focus on the AI commercialization / verification layer and mention NBIS as one example.

Pros:

- strong framework value

Cons:

- too indirect for investment use

### Option C — Hybrid company + industry report

Use a short industry frame and then place NBIS inside it.

Pros:

- best fit for investing-os methodology
- best reusable structure
- strongest bridge from framework to decision

Cons:

- more structure to write than a plain company memo

## Chosen Approach

Use Option C.

The report should not study NBIS in isolation.

It should first define the relevant AI value-chain layer, then explain NBIS's role inside that layer.

## Core Research Questions

The report should answer:

1. What role does NBIS play in the AI commercialization / verification layer?
2. What is the market currently pricing into NBIS?
3. What has been confirmed in Reality?
4. What remains unconfirmed?
5. What are the next one to two quarter validation events?
6. What stance is justified now: observe, probe, or upgrade candidate?

## Report Structure

The readable report should have six sections.

### 1. Role in the AI Ecosystem

Define:

- what layer the company belongs to
- why that layer matters
- how it differs from hardware Reality indicators and software commercialization leaders

### 2. Why It Is a Verification-Layer Company

Explain:

- what part of the business model still requires validation
- why current price can move faster than confirmed Reality
- why this is not yet a fully verified core holding

### 3. What the Market Is Trading

Describe:

- current narrative
- implied expectations
- what kind of future success the market seems to be discounting

### 4. Reality Confirmed vs Reality Unconfirmed

This is the report's most important analytical split.

Confirmed:

- what can already be supported by evidence

Unconfirmed:

- what still depends on future execution, monetization, scale, or market adoption

### 5. Next One to Two Quarter Validation Map

List the most important future checkpoints:

- earnings
- customer or revenue signals
- profitability or margin signals
- adoption or demand signals
- any industry-layer evidence that changes the company's role

### 6. Investment View

Conclude:

- current stance
- why it is not yet a fully verified core asset
- what would upgrade it
- what would weaken it

## Embedded Industry Layer

The report should contain a short industry framing section inside the opening part.

It should define a simple AI layer map such as:

- Reality Indicator Layer
- Demand Indicator Layer
- Commercialization Indicator Layer
- Verification Layer

The goal is not to write a separate long industry dossier.

The goal is to make the company report intelligible inside a reusable industry frame.

## Structured Research Card

The report should end with a fixed card using these fields:

- Company
- Industry Theme
- Role in Value Chain
- Current Narrative
- Reality Confirmed
- Reality Unconfirmed
- Key Hypotheses
- Bull Case
- Bear Case
- Next 3 Validation Events
- Current Stance
- Upgrade Trigger
- Downgrade Trigger

## Source Logic

investing-os should own:

- question framing
- methodology
- role classification
- hypothesis framing
- final stance wording

stock_team should support:

- evidence packet inputs
- data extraction
- structured fact support

The final report should remain brain-owned and interpretation-owned by investing-os.

## Intended File Shape

If implementation proceeds, the first example should likely create:

- one NBIS report under `investing-os/wiki/companies/`
- optionally one supporting verification-layer note or section reference under `investing-os/wiki/industries/`
- one structured card appended in the same report or created as a linked artifact

## Success Criteria

This design is successful if:

1. the report explains NBIS through both company and industry lenses
2. the report clearly separates confirmed Reality from unconfirmed Narrative
3. the report gives usable next-quarter validation checkpoints
4. the output can be reused later for other companies in the same format
