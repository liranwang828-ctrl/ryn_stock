# Contextual Trade Evidence Packet

## Purpose

Carry objective trade-context evidence from `stock_team` into `investing-os`.

This packet supports trade review.

It does not make final cognitive or trading conclusions.

## Typical Source

Future `stock_team` exporter:

```text
symbol + date + fills
|
market data API / local cache
|
contextual trade evidence packet
```

## Packet Header

```yaml
packet_type: contextual_trade_evidence
status: draft
created_at:
source_system: stock_team
requested_by:
symbol:
trade_date:
review_id:
source_files:
data_sources:
missing_data:
```

## Required Sections

### 1. Fill Summary

Include:

- normalized fills
- buy/sell quantities
- average buy/sell prices
- realized P/L if available
- commissions if available
- timestamps with timezone

### 2. Symbol Context

Include:

- open / high / low / close
- intraday VWAP
- high/low timestamps
- volume behavior
- late-session behavior
- split or product-mechanics notes

### 3. Underlying / Peer Context

If relevant:

- underlying symbol
- peer symbols
- sector ETF
- relative strength
- catalyst or news flag

### 4. Market Context

Include:

- SPY
- QQQ
- VIX if available
- market trend
- final 30-minute behavior
- risk-on / risk-off notes

### 5. Fill Against Context

For each material fill:

- fill timestamp
- symbol price at or before fill
- VWAP relationship
- market context at fill
- underlying context at fill
- whether action occurred near high, low, VWAP break, or late-session selloff

### 6. Data Quality

```yaml
price_data_quality:
fill_data_quality:
timezone_assumptions:
adjustment_assumptions:
known_limitations:
```

### 7. Evidence Only Boundary

Allowed outputs:

- facts
- calculations
- context flags
- missing data
- confidence level

Forbidden outputs:

- final trading judgment
- psychological diagnosis
- principle update
- buy/sell recommendation
- autonomous order instruction

## Destination

After review, this packet may feed:

- `wiki/journals/`
- `wiki/historical-cases/`
- `cognition/`
- `decision/`
- `execution/`
- `evolution/`

