# Event Reconstruction Packet

## Purpose

Carry factual reconstruction for one event into `investing-os`.

Use cases:

- actual trade
- missed opportunity
- false positive
- rule exception
- condition trigger without trade

This packet helps answer whether the event was a valid opportunity, false signal, execution delay, data issue, or plan mismatch.

It does not decide the lesson.

## Packet Header

```yaml
packet_type: event_reconstruction
status: draft / complete / partial
created_at:
source_system: stock_team
requested_by: investing-os
event_id:
event_type:
symbol:
tactic:
trigger_time:
data_sources:
missing_data:
warnings:
forbidden_sections_absent:
  - psychological_interpretation
  - final_lesson
  - buy_sell_hold_recommendation
  - principle_update
```

## Required Sections

### 1. Event Timeline

Include trigger, entry window, fills if any, condition flips, market / sector changes, and post-trigger windows.

### 2. Conditions At Trigger

For each planned condition:

| Condition | Status | Value | Source | Freshness |
|---|---|---|---|---|
|  | pass / fail / partial / missing |  |  |  |

### 3. Condition Quality

Pass / fail is not enough. Include quality when possible:

- strong
- acceptable
- weak
- noisy
- missing

Examples:

- VWAP reclaim held for only two minutes
- volume was a single spike without follow-through
- RS was positive but weakening

### 4. Post-Trigger Path

For `5m`, `15m`, and `30m` after trigger:

- MFE
- MAE
- close relative to trigger
- VWAP relationship
- volume continuation
- benchmark / sector confirmation

### 5. Missed Opportunity / False Positive Analysis

Facts only:

- whether the entry window was available
- whether slippage limit was exceeded
- whether signal failed before reasonable execution
- whether the setup worked after trigger
- whether later data contradicted the original pass conditions

### 6. Data Quality

```yaml
market_data_quality:
condition_data_quality:
timezone_assumptions:
stale_sources:
known_limitations:
```

## Destination

This packet may feed:

- trade review
- daily report
- lesson candidate
- tactic event database
- periodic tactic summary
