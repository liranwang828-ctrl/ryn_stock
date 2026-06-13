# Pre-Market Packet Contract

## Purpose

Carry pre-market planning output into `investing-os` before the market creates emotional pressure.

This packet is especially important because the user's timezone makes after-work time the practical pre-market window.

## Typical Sources

- `stock_team/agents/premarket.py`
- `stock_team/agents/premarket_summary.py`
- `stock_team/agents/premarket_checklist.py`
- `stock_team/agents/premarket_decision.py`
- `stock_team/agents/premarket_exit_sheet.py`
- `stock_team/agents/premarket_order_sheet.py`
- `stock_team/scripts/fetch_premarket.py`
- `stock_team/scripts/render_premarket_board.py`
- `stock_team/reports/premarket_trading_board_{date}.html`

## Destination After Review

- `templates/trading-day-plan.md`
- `templates/pre-market-plan.md`
- `templates/trade-plan.md`
- `system/workflows/trading-day.md`
- `wiki/journals/`

## Packet Header

```yaml
packet_type: pre_market
status: draft
created_at:
market_date:
source_system:
source_files:
review_owner:
```

## Required Sections

### 1. Market Context

Include:

- SPY / QQQ / VIX state
- major macro events
- sector strength or weakness
- overnight news that affects current holdings

### 2. Holdings Review

For each holding:

- thesis status
- risk status
- planned action
- no-action condition
- alert condition

### 3. Watchlist Review

For each watched symbol:

- thesis or setup
- trigger
- invalidation
- maximum risk
- whether action is allowed tonight

### 4. Allowed Actions

Allowed actions must be finite and explicit.

Examples:

- hold
- reduce if predefined condition occurs
- add only if trigger and risk budget are both valid
- no new short-term trades

### 5. No-Trade Conditions

Record when the correct action is to do nothing.

Include:

- missing data
- unclear thesis
- emotional pressure
- sleep-risk violation
- event risk not priced

### 6. Sleep-Before-Risk Lock

Before sleep, confirm:

- open orders reviewed
- position risk acceptable
- no position can hijack sleep
- no low-confidence trade has high attention budget

### 7. Absorption Decision

```yaml
write_trading_day_plan: yes/no
create_trade_plan:
create_alerts:
create_review_tasks:
reason:
```

## Guardrail

This packet may recommend a plan draft.

It does not authorize a trade by itself.

