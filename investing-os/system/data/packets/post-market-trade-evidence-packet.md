# Post-Market Trade Evidence Packet

## Purpose

Carry objective post-market trade evidence from `stock_team` into `investing-os`.

This is the first input to review. It answers what happened in the account and market. It does not explain user psychology or decide lessons.

## Packet Header

```yaml
packet_type: post_market_trade_evidence
status: draft / complete / partial
created_at:
source_system: stock_team
requested_by: investing-os
trade_date:
request_artifact:
intraday_guidance_artifact:
ibkr_connected: true/false
data_sources:
missing_data:
warnings:
forbidden_sections_absent:
  - psychological_interpretation
  - final_trading_judgment
  - buy_sell_hold_recommendation
  - principle_update
```

## Required Sections

### 1. Account Summary

Include account value if available, realized / unrealized P/L, commissions, margin or leverage exposure, and positions before / after.

### 2. Orders And Fills

For each order or fill, include order id, fill id, symbol, side, quantity, price, timestamp, venue, commission, order type, and time in force when available.

### 3. Planned Vs Actual

Compare against `intraday_guidance` as factual alignment only.

| Symbol | Planned Mode | Planned Scope | Actual Activity | Alignment |
|---|---|---|---|---|
|  | observe_only / conditional_action_allowed / reduce_risk_only |  |  | inside_plan / outside_plan / unclear |

### 4. Full-Day Market Tape

Include full-session behavior, not only close-to-close return:

- QQQ / SPY / IWM full-day intraday path
- VIX proxy level / direction, or unavailable reason
- open, high, low, close
- high / low timestamps
- VWAP relationship
- volume ratio and volume expansion windows
- opening 30 minutes, midday, final 30 minutes
- risk-on / risk-off phase changes with timestamps

### 5. Sector And Theme Full-Day Tape

For relevant themes and planned symbols, include:

- sector ETF / proxy, such as SOXX, SMH, IGV, LITE, or user-defined proxy
- full-day intraday path
- VWAP relationship
- volume behavior
- relative strength versus QQQ / SPY
- key timestamps where theme behavior changed

### 6. Opening 30-Minute Structure

For market benchmarks, relevant sectors, and traded / reviewed symbols, split the opening 30 minutes into:

- `0-5m`
- `5-15m`
- `15-30m`

For each window, include:

- open / high / low / close for the window
- cumulative volume and relative volume if available
- VWAP relationship
- opening range high / low
- whether the symbol / benchmark held, reclaimed, or rejected VWAP
- whether price broke opening range high / low
- direction consistency: trend / chop / reversal
- market breadth proxy if available
- relative strength versus benchmark during the window
- relevant fill timestamps inside the window
- condition pass / fail changes inside the window

Opening 30-minute output should be factual and timestamped. It must not label a setup as tradable.

### 7. Symbol Full-Day Tape

For each traded or reviewed symbol, include:

- intraday OHLCV path
- VWAP and price/VWAP relationship
- premarket gap if available
- opening range
- high / low and timestamps
- volume ratio
- reclaim / rejection / breakdown attempts
- MA / ATR / approved anchor context if requested by the plan
- late-session behavior

### 8. Key Intraday Nodes

List factual timestamps that matter for review:

- first plan trigger
- condition pass / fail flip
- VWAP reclaim / rejection
- high-volume candle
- market breakdown / recovery
- sector confirmation / divergence
- user fill timestamps
- final 30-minute change

### 9. Fill Against Market Context

For each material fill, include symbol price, VWAP relationship, distance from approved anchor, QQQ / SPY state, sector proxy state, peer state, volume context, and whether required conditions were pass / fail / missing at that time.

### 10. Exception And Rule Events

List factual triggers such as stale data, condition flip, market breakdown, IBKR mismatch, daily loss limit breach, position cap breach, or unplanned symbol activity.

Do not interpret motive.

### 11. Data Quality

```yaml
ibkr_data_quality:
market_data_quality:
timezone_assumptions:
missing_symbols:
stale_sources:
known_limitations:
```

## Destination

After review, `investing-os` may use this packet to create a daily report, trade review report, lesson candidates, promotion queue entries, historical case entries, dashboard HTML, and traceability links.

Absorption requires user review.
