# Validation Record: RS Pullback Rebound Intraday

```yaml
tactic_id: rs_pullback_rebound_intraday
status: paper_test
last_updated: 2026-06-07
source_candidate: decision/tactics/rs-pullback-rebound-candidate.md
known_evidence:
  - stock_team daily-data backtest reported 213 trades, 62.91% win rate, 1.33 profit factor
  - high_volume_risk_off environment had negative expectancy
  - leveraged products had larger MAE and lower win rate
```

## Validation Principle

This tactic is not validated as a standalone price pattern.

It must be validated as:

```text
tactic
+
pre-market regime gate
+
intraday runtime gate
+
position / sleeve boundary
```

Any factor used as dashboard pass/fail must appear in this validation record.

Unvalidated factors may appear only as context.

## Factor Role Matrix

| Factor | Pre-Market Use | Intraday Use | Backtest Split | Current Role |
|---|---|---|---|---|
| `qqq_trend_5d_20d` | classify broad structure | no | yes | regime gate |
| `qqq_high_volume_risk_off` | disable hostile days | block runtime deterioration | yes | hard gate candidate |
| `qqq_vwap_state` | no | check runtime stabilization | yes | runtime gate candidate |
| `qqq_opening_range_state` | no | detect breakdown/recovery | yes | runtime gate candidate |
| `vix_direction` | identify volatility expansion | detect runtime spike | yes | regime/runtime gate |
| `market_catalyst_risk` | identify event risk | update if news hits | yes | context/gate candidate |
| `sector_rs_vs_qqq` | require sector not dragging | require sector confirmation | yes | confirmation factor |
| `sector_vwap_state` | no | sector reclaim/rejection | yes | runtime confirmation |
| `sector_high_volume_breakdown` | disable weak sector days | block sector breakdown | yes | hard gate candidate |
| `peer_confirmation` | context | confirm or reject symbol move | yes | context candidate |
| `symbol_rs_vs_market` | preselect strong symbols | require strength to persist | yes | core factor |
| `symbol_rs_vs_sector` | avoid weak symbol inside strong sector | require strength to persist | yes | core factor |
| `symbol_vwap_reclaim` | no | trigger review only | yes | trigger factor candidate |
| `symbol_opening_range_reclaim` | no | trigger/recovery review | yes | trigger factor candidate |
| `volume_confirmation` | no | confirm rebound attempt | yes | trigger confirmation |
| `atr_risk_distance` | reject poor risk distance | monitor invalidation distance | yes | risk factor |
| `ma20_distance` | context for extended/mean-reversion state | context only | yes | context |
| `ma50_distance` | context for deeper support | context only | yes | context |
| `prior_day_high_low` | context for levels | context only | yes | context |
| `permission_state` | block Red/No-Trade | block Red/No-Trade | yes | brain-owned gate |
| `daily_loss_state` | set risk budget | block after daily damage | yes | risk gate candidate |
| `linked_leveraged_exposure` | flag related exposure | flag related exposure | yes | risk context gate |
| `same_symbol_stopout_today` | no | disable same tactic/symbol | yes | hard discipline gate |

## Backtest Requirements For Stock Team

Backtest must report results split by:

- QQQ trend regime
- QQQ high-volume risk-off state
- VIX direction
- sector confirmation present / absent
- symbol RS versus QQQ
- symbol RS versus sector
- VWAP reclaim present / absent
- volume confirmation present / absent
- opening range state
- ATR risk distance bucket
- time of day
- same-symbol re-entry after stop
- leveraged product versus underlying

Required metrics:

- sample count
- win rate
- profit factor
- average win
- average loss
- expectancy
- MAE
- MFE
- max drawdown per event if available
- failure cluster notes

## Promotion Rules

Promotion from `paper_test` to `limited_live` requires:

- backtest split results for all hard gate candidates
- at least 20 forward paper events or a user-approved smaller sample
- evidence that high-volume risk-off disable rule improves expectancy
- evidence that same-symbol stopout disable rule reduces tail loss or emotional relapse
- user review confirming the tactic does not reliably trigger loss-repair behavior

Promotion from `limited_live` to `approved` requires:

- live sample with no sleeve-boundary violations
- no conversion from intraday sleeve to swing/core sleeve
- max loss respected
- post-market reviews completed for all live events
- confidence remains positive after failed trades

## Current Decision

This tactic may be used for:

- paper dashboard monitoring
- structured replay
- limited simulation

It is not approved for automatic live use.

Any live use requires explicit pre-market activation by the brain and user.

