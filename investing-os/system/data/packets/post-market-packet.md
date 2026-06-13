# Post-Market Packet Contract

## Purpose

Carry post-market review output into `investing-os` so execution, emotion, and cognition can be reviewed separately.

This packet is designed for flexible review timing: morning, workday gaps, after work, or weekend catch-up.

## Typical Sources

- `stock_team/agents/postmarket_data_collector.py`
- `stock_team/agents/postmarket_decision_audit.py`
- `stock_team/agents/postmarket_master_eval.py`
- `stock_team/agents/postmarket_review.py`
- `stock_team/agents/postmarket_trade_review.py`
- `stock_team/agents/postmarket_summary.py`
- `stock_team/reports/`
- broker/exported fills reviewed manually

## Destination After Review

- `wiki/journals/{date}-daily-review.md`
- `wiki/historical-cases/`
- `wiki/principles/`
- `system/checks/`
- `templates/post-market-review.md`

## Packet Header

```yaml
packet_type: post_market
status: draft
created_at:
market_date:
source_system:
source_files:
review_owner:
```

## Required Sections

### 0. External Market Context

This section is required before behavior interpretation.

Required fields:

```yaml
market_context_status: complete/partial/missing
data_sources:
market_context_artifacts:
symbols_reviewed:
benchmarks_reviewed:
sector_refs_reviewed:
vix_status:
missing_data:
```

Minimum required evidence:

- traded-symbol intraday K-line
- traded-symbol recent daily K-line
- traded-symbol volume and volume ratio
- SPY / QQQ same-day behavior
- VIX level and direction, or documented unavailable reason
- relevant sector ETF behavior
- relevant peers / underlying symbols
- market state at key trade timestamps

If `market_context_status` is `missing`, the packet may preserve facts and user narrative, but must not extract permanent lessons.

### 1. Facts

Record what happened without judgment:

- market state
- holdings behavior
- trades
- order changes
- realized/unrealized impact
- sleep or attention impact

### 2. Original Plan

Record what the plan said before the market.

If there was no plan, state that explicitly.

### 3. Actions

Compare plan vs actual action.

Separate:

- planned execution
- unplanned execution
- risk management
- emotional reaction

### 4. Emotion

Record emotional state by phase:

- pre-market
- entry
- drawdown
- exit
- after close

### 5. Cognition

Identify:

- high-quality judgments
- weak judgments
- missing thesis
- signal mistaken as thesis
- attention capture
- emotional spillover

### 6. Discipline Check

Evaluate against:

- constitution
- trading principles
- short-term checklist
- risk checklist
- attention budget principle

### 7. Falsification Review

For each material position or trade:

- was thesis falsified?
- was setup invalidated?
- was exit based on plan, risk, or emotion?

### 8. System Updates

Potential updates:

- journal entry
- principle candidate
- checklist update
- historical case
- agent rule
- no update

### 9. Absorption Decision

```yaml
create_journal: yes/no
create_case: yes/no
create_principle: yes/no
update_checklist: yes/no
follow_up_tasks:
reason:
```
