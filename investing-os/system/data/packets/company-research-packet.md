# Company Research Packet Contract

## Purpose

Carry a generated or manual company research output into `investing-os` for review.

This packet converts stock-team style company reports into durable cognition only after human review.

## Typical Sources

- `stock_team/agents/report_agent.py`
- `stock_team/agents/research_ingest.py`
- `stock_team/agents/company_profile_fetcher.py`
- `stock_team/agents/fundamentals_tracker.py`
- `stock_team/findings/company_profile_{SYM}.json`
- `stock_team/findings/fundamentals_{SYM}.json`
- `stock_team/reports/research_{SYM}.md`
- `stock_team/reports/research_{SYM}.html`

## Destination After Review

- `wiki/companies/{symbol}.md`
- `templates/company-research.md`
- `templates/thesis.md`
- `templates/falsification.md`
- `templates/valuation.md`

## Packet Header

```yaml
packet_type: company_research
status: draft
created_at:
source_system:
source_files:
symbol:
company_name:
research_date:
review_owner:
```

## Required Sections

### 1. Research Question

What question is this research trying to answer?

Examples:

- Is this company a value capturer in the AI infrastructure chain?
- Is the current thesis still valid after earnings?
- Is this only a signal trade, or does it deserve company-level understanding?

### 2. Facts

Separate facts from generated interpretation.

Include:

- business segments
- revenue drivers
- margin structure
- balance-sheet signals
- customer / supplier dependence
- management notes
- recent catalysts

### 3. Thesis Candidate

State the possible investment thesis in plain language.

Do not promote the thesis to durable wiki status until reviewed.

### 4. Value Capture

Answer:

- Where is value created?
- Who captures it?
- Why this company rather than peers?
- What bottleneck or scarce resource matters?

### 5. Valuation Frame

Record:

- valuation method
- key assumptions
- upside/downside ranges
- assumptions most likely to be wrong

### 6. Falsification

List what would prove the thesis wrong.

Include:

- business falsification
- financial falsification
- market-structure falsification
- timing or catalyst failure

### 7. Risk

Record:

- position risk
- thesis risk
- liquidity risk
- emotional / attention risk
- event risk

### 8. Action Boundary

Allowed outputs:

- add to watchlist
- update company dossier
- create open question
- create thesis draft
- create no-trade condition

Forbidden outputs:

- direct buy/sell command
- automatic position sizing
- rule update without review

### 9. Absorption Decision

```yaml
absorb_to_wiki: yes/no
absorb_to_template: yes/no
absorb_to_principle: yes/no
absorb_to_watchlist: yes/no
next_review_date:
reason:
```

