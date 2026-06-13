# Company Dossier Lifecycle

## Purpose

Define how company research becomes durable company knowledge.

This workflow is for converting research packets, manual notes, and stock-team generated reports into `wiki/companies/` dossiers.

## Core Rule

A company report is not a thesis by default.

A thesis exists only after the research answers:

- what the company does
- why it matters now
- where value is captured
- what can prove the thesis wrong
- what risk boundary applies

## Lifecycle States

### 1. Research Candidate

Use when:

- the company is interesting but not understood
- source data is incomplete
- there is no thesis yet

Allowed outputs:

- open questions
- research task
- company research packet review

Forbidden outputs:

- trade plan
- position sizing
- active watchlist trigger

### 2. Dossier Draft

Use when:

- enough facts exist to summarize the business
- value-capture question is still unresolved
- valuation or falsification is incomplete

Allowed outputs:

- `wiki/companies/{symbol}.md` draft
- follow-up research tasks
- industry map links

Forbidden outputs:

- high-conviction label
- thesis-backed action

### 3. Thesis Candidate

Use when:

- business model is understood
- industry position is understood
- value capture is plausible
- falsification is written
- risk is identified

Allowed outputs:

- thesis draft
- watchlist metadata candidate
- valuation scenario
- pre-market review input

Forbidden outputs:

- automatic trade permission

### 4. Active Dossier

Use when:

- thesis is reviewed
- falsification is clear
- risk boundary is clear
- monitoring plan exists

Allowed outputs:

- watchlist metadata snapshot candidate
- position-role checklist input
- thesis update
- post-market review reference

### 5. Invalidated Or Archived

Use when:

- thesis is disproven
- business structure changed
- original reason no longer matters
- research was low quality or obsolete

Allowed outputs:

- historical case
- archive note
- no-trade state

## Dossier Required Sections

Minimum durable company dossier:

- company identity
- one-sentence positioning
- business model
- industry context
- value capture
- moat / pricing power
- financial quality
- valuation frame
- catalysts
- risks
- falsification
- monitoring plan
- source notes
- review due date

## Packet Intake

Company research packets should go through:

- `system/workflows/packet-absorption.md`
- `templates/packet-review.md`

Only then should durable content enter:

- `wiki/companies/`
- `templates/thesis.md`
- `templates/falsification.md`
- `system/data/snapshots/examples/watchlist-metadata.example.json` as a future candidate, never directly active

## Review Triggers

Review a company dossier when:

- earnings are released
- major product/customer/capex news appears
- valuation changes materially
- industry thesis changes
- position size or emotional attention increases
- falsification signal appears
- review due date passes

## Promotion Rules

### Research Candidate To Dossier Draft

Requires:

- business summary
- source list
- open questions

### Dossier Draft To Thesis Candidate

Requires:

- value capture
- risk
- falsification
- valuation frame

### Thesis Candidate To Active Dossier

Requires:

- reviewed thesis
- monitoring plan
- position-role compatibility
- no unresolved critical questions

## Safety Boundary

Company dossier status never authorizes a trade by itself.

It only improves the quality of:

- research
- watchlist classification
- plan writing
- risk review
- post-market reflection

