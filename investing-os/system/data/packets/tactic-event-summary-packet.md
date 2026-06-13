# Tactic Event Summary Packet

## Purpose

Carry periodic statistical evidence about a tactic into `investing-os`.

This is for weekly, monthly, or tactic-review sessions.

It answers:

```text
How has this tactic behaved across recent events?
Which environments helped or hurt it?
Which conditions have predictive value?
Which failure modes repeat?
```

It does not decide whether the tactic should be adopted, changed, or retired.

## Packet Header

```yaml
packet_type: tactic_event_summary
status: draft / complete / partial
created_at:
source_system: stock_team
requested_by: investing-os
tactic:
period:
symbols:
event_count:
data_sources:
missing_data:
warnings:
forbidden_sections_absent:
  - strategy_adoption_decision
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - principle_update
```

## Required Sections

### 1. Event Universe

Include all relevant events, not only trades:

- traded
- missed
- false positive
- condition trigger without action
- rule exception

### 2. Outcome Metrics

Include:

- event count
- average / median MFE
- average / median MAE
- 5m / 15m / 30m post-trigger outcomes
- trigger window availability
- slippage requirement
- execution delay distribution

### 3. Environment Breakdown

Group outcomes by:

- market regime
- QQQ risk-on / risk-off
- VIX direction
- sector confirmation
- opening 30m vs later day
- time of day

### 4. Condition Quality Breakdown

Group outcomes by:

- VWAP reclaim quality
- volume confirmation quality
- relative strength quality
- benchmark / sector alignment
- data freshness

### 5. Failure Modes

Facts only:

- common false positive patterns
- common missed opportunity patterns
- conditions that pass but fail quickly
- environments where MAE is too large
- environments that may deserve disable rules

### 6. Data Quality

```yaml
event_database_quality:
market_data_quality:
survivorship_bias_risk:
missing_untraded_events:
known_limitations:
```

## Destination

This packet may feed:

- weekend review
- tactic review
- promotion queue
- risk-budget review
- checklist update proposal
- runtime parameter candidate
