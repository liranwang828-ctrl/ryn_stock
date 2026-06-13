# RS Pullback Rebound Intraday

```yaml
tactic_id: rs_pullback_rebound_intraday
status: paper_test
confidence: low_to_medium
parent_candidate: decision/tactics/rs-pullback-rebound-candidate.md
validation_record: decision/tactics/validation-records/rs-pullback-rebound-intraday.md
```

## Scope / Role Boundary

This tactic is intraday-only.

It cannot convert into:

- swing position
- core position
- loss-repair position
- thesis-based hold

Any overnight carry is exception handling, not tactic success.

## Sleeve Boundary

This tactic may be applied to a ticker that also has a swing or core thesis, but only through a separately declared intraday sleeve.

The intraday sleeve must have:

- separate position size
- separate max loss
- separate entry reason
- separate exit plan
- separate review record

The intraday sleeve cannot be merged into a swing or core sleeve after entry.

## What It Tries To Capture

Temporary imbalance repair inside an already strong intraday structure.

The pattern:

```text
strong symbol or theme
|
market / sector pullback or intraday disagreement
|
symbol retains relative strength
|
market and sector stop deteriorating
|
symbol reclaims approved anchor with volume
|
short intraday rebound attempt
```

This is not:

- bottom fishing
- loss repair
- averaging down
- betting on market reversal
- converting a failed day trade into a thesis

## Why It Might Work

Strong symbols may attract buyers first when market stress pauses.

The edge, if any, comes from:

- pre-existing relative strength
- sector/theme confirmation
- market stabilization
- reclaim of a monitored anchor
- volume confirmation
- risk distance that remains acceptable before entry

## Pre-Market Regime Gate

This tactic cannot be activated by symbol setup alone.

Pre-market must classify the regime:

| Regime | Meaning | Permission |
|---|---|---|
| supportive | Market and sector context support rebound tactics | May monitor |
| mixed | Some stress remains, but not full risk-off | Monitor only with tighter conditions |
| hostile | Risk-off context likely dominates symbol setup | Observe only |
| disallowed | Market/volatility/catalyst risk invalidates tactic | Disabled |

Required pre-market factors:

- `qqq_trend_5d_20d`
- `qqq_high_volume_risk_off`
- `vix_direction`
- `market_catalyst_risk`
- `sector_rs_vs_qqq`
- `sector_high_volume_breakdown`
- `symbol_rs_vs_market`
- `symbol_rs_vs_sector`
- `atr_risk_distance`
- `permission_state`
- `linked_leveraged_exposure`

## Intraday Runtime Gate

Even if activated pre-market, runtime execution requires fresh confirmation.

Required runtime factors:

- `qqq_high_volume_risk_off`
- `qqq_vwap_state`
- `qqq_opening_range_state`
- `vix_direction`
- `sector_rs_vs_qqq`
- `sector_vwap_state`
- `symbol_rs_vs_market`
- `symbol_rs_vs_sector`
- `symbol_vwap_reclaim`
- `symbol_opening_range_reclaim`
- `volume_confirmation`
- `atr_risk_distance`
- `daily_loss_state`
- `same_symbol_stopout_today`

## Required Pre-Trade Definition

Before any live use, the intraday sleeve must define:

- symbol
- sleeve id
- max loss
- position cap
- entry anchor
- invalidation condition
- partial profit logic
- final exit logic
- latest exit time
- whether overnight is possible only as exception handling

## Disabled If

- QQQ is high-volume risk-off.
- VIX is expanding quickly.
- Sector proxy is breaking down.
- Symbol strength is only a weak bounce, not relative strength.
- The user has stopped out on the same symbol/tactic today.
- The trade is connected to repairing a related leveraged exposure.
- Account state is Red or No-Trade.
- Entry requires chasing outside the approved trigger window.

## Dashboard Contract

Dashboard may show:

- factor status: pass / fail / partial / stale / missing
- data freshness
- missing data
- linked evidence packets
- runtime exception flags

Dashboard must not show:

- buy / sell / hold
- can trade
- should enter
- should exit
- permission approved
- recommended shares

## Post-Market Review

Every live or paper event must record:

- pre-market regime
- runtime gate status at trigger time
- entry/skip reason
- MFE / MAE
- exit quality
- whether any condition became stale
- whether the tactic caused attention capture
- whether the sleeve boundary was respected

