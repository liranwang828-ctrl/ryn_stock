# Industry Research Packet Contract

## Purpose

Carry industry, sector, supply-chain, or theme research into `investing-os`.

The goal is to improve worldview, industry structure understanding, and value-capture judgment.

## Typical Sources

- `stock_team/agents/sector_agent.py`
- `stock_team/agents/sector_leadership.py`
- `stock_team/agents/macro_agent.py`
- `stock_team/agents/tech_agent.py`
- `stock_team/agents/fund_agent.py`
- `stock_team/findings/*sector*.json`
- `stock_team/findings/*industry*.md`
- `stock_team/reports/research_*.md`

## Destination After Review

- `wiki/industries/{industry}.md`
- `wiki/methodologies/`
- `wiki/companies/`
- `templates/industry-research.md`

## Packet Header

```yaml
packet_type: industry_research
status: draft
created_at:
source_system:
source_files:
industry:
theme:
review_owner:
```

## Required Sections

### 1. WHY Alignment

Explain why this industry matters to the operating system.

Connect it to:

- long-term technology trend
- cognition gap
- value creation
- risk management

### 2. Industry Map

Describe:

- value chain
- key layers
- bottlenecks
- suppliers
- customers
- substitutes
- regulatory or geopolitical constraints

### 3. Value Capture

Identify where profits may accumulate.

Separate:

- technology importance
- business-model quality
- bargaining power
- pricing power
- capital intensity

### 4. Candidate Companies

List candidates by role, not by excitement.

For each candidate:

- role in value chain
- why it matters
- main uncertainty
- research priority

### 5. Historical Analogy

Use history to compare structure, not price paths.

Record:

- similar cycle
- similarity
- difference
- overfitting risk

### 6. Falsification

What would show the industry thesis is wrong, too early, or already priced in?

### 7. Monitoring Plan

Define:

- metrics
- events
- earnings signals
- customer adoption signals
- policy or macro signals

### 8. Absorption Decision

```yaml
absorb_to_industry_wiki: yes/no
create_company_research_packets:
create_principle_candidate: yes/no
next_review_date:
reason:
```

