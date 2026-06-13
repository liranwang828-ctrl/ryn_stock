# Runtime Monitor Packet Contract

## Purpose

Carry runtime monitoring signals from `stock_team` into `investing-os` without letting runtime tools become decision makers.

This packet is for alerts, audits, and discipline checks. It is not for autonomous trading.

## Typical Sources

- `stock_team/agents/poll.py`
- `stock_team/agents/stop_rules.py`
- `stock_team/agents/stop_review.py`
- `stock_team/agents/risk_agent.py`
- `stock_team/agents/order_manager.py`
- `stock_team/agents/order_executor.py`
- `stock_team/config/positions.json`
- `stock_team/config/market_regime.json`
- `stock_team/config/risk_limits.json`

## Destination After Review

- `system/data/runtime-parameter-map.md`
- `system/checks/`
- `wiki/journals/`
- `wiki/principles/`
- `system/data/snapshots/`

## Packet Header

```yaml
packet_type: runtime_monitor
status: draft
created_at:
market_date:
source_system:
source_files:
review_owner:
```

## Required Sections

### 1. Signal Summary

Record:

- signal name
- affected symbol
- severity
- timestamp
- source rule
- whether data was complete

### 2. Rule Context

Link the signal to a principle, checklist, or runtime parameter.

If there is no linked principle, treat it as informational only.

### 3. Current State

Include:

- position role
- position size context
- market regime
- volatility context
- relevant alerts

### 4. Recommended Review

Allowed recommendations:

- review position
- review risk
- pause new entries
- check thesis
- update journal
- escalate to human

Forbidden recommendations:

- execute order automatically
- bypass checklist
- increase risk because of signal strength
- change runtime rule without review

### 5. Degraded Mode

If required data is missing or stale:

- mark packet as degraded
- block action-oriented conclusions
- allow only informational alerts

### 6. Absorption Decision

```yaml
create_alert_review: yes/no
create_journal_note: yes/no
update_runtime_snapshot_candidate: yes/no
update_principle_candidate: yes/no
reason:
```

