---
packet_type: plan_evidence_packet
stage: pre_market_stage_1
status: fallback_data
generated_at: 2026-06-08T13:10:31.302116Z
source_system: stock_team
requested_by: investing-os
command: python -m stock_team.cli premarket --date 2026-06-08 --decision-sheet C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.2026-06-08.cognition-v1.json --out C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.2026-06-08.cognition-v1.md
brain_input_artifact: C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.2026-06-08.cognition-v1.json
derived_from_stage0_packet: C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.2026-06-08.cognition-v1.md
data_sources:
  - yfinance
missing_data:
warnings:
  - polygon_api_key_missing_or_failed; fell back to yfinance sandbox data which is not production grade
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - permission_state_change
  - final_thesis_adoption
  - psychological_interpretation
  - invented_entry_support_sizing
---

# Stage 1 Plan Evidence Packet: RKLB + NVDA + AVGO + PLTR + NET

Boundary:

This packet contains facts, calculations, and rule collisions only.

It does not decide whether trading is allowed.
It does not recommend buy / sell / hold.
It does not adopt or reject the thesis.

## Input Summary

| Field | Value |
|---|---|
| Date | 2026-06-08 |
| Focus Pool | RKLB, NVDA, AVGO, PLTR, NET |
| Permission State Echo | Yellow |
| Stage 0 Source | `pre-market-context-packet.2026-06-08.cognition-v1.md` |
| Brain Input | `stage1-pre-market-decision-sheet.2026-06-08.cognition-v1.json` |

## Stage 0 Market Context Echo

These are echoed facts from Stage 0 so the symbol packet remains interpretable.

| Proxy | 1D % | 5D % | 20D % | Volume Ratio | Source |
|---|---:|---:|---:|---:|---|
| QQQ | -4.80 | -4.50 | +1.46 | 2.4 | stage0_packet |
| SPY | -2.58 | -2.50 | +0.82 | 1.9 | stage0_packet |
| IWM | -3.55 | -3.02 | -0.22 | 1.4 | stage0_packet |
| VIXY | +7.23 | +4.38 | -9.46 | 2.0 | stage0_packet |

## Brain Decision Echo

Echo brain-owned fields exactly. `stock_team` must not alter them.

| Symbol | Role | Theme | Research Status | Plan Mode | Allowed Tactics | Forbidden Actions | Risk Budget |
|---|---|---|---|---|---|---|---|
| RKLB | watchlist | ai_infrastructure | candidate_only | observe | — | new intraday action; leader-subset membership treated as entry signal | max_loss=0; position_cap=0; attention=10m |
| NVDA | watchlist | ai_infrastructure | partially_researched | observe | — | short-term thesis drift; core position turns into trade | max_loss=0; position_cap=0; attention=10m |
| AVGO | watchlist | semiconductors | candidate_only | observe | — | new intraday action; technical signal treated as thesis | max_loss=0; position_cap=0; attention=10m |
| PLTR | watchlist | ai_infrastructure | candidate_only | observe | — | new intraday action; momentum treated as durable thesis | max_loss=0; position_cap=0; attention=10m |
| NET | watchlist | cloud | candidate_only | observe | — | new intraday action; leader-subset membership treated as entry signal | max_loss=0; position_cap=0; attention=10m |

## Symbol Factor Calculations

Facts and calculated factors only.

| Symbol | 1D % | 5D % | 20D % | Relative Strength Context | Volume Ratio | ATR(14) | MA20 Distance | MA50 Distance | Prior Day High / Low | Notes |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|---|
| RKLB | -8.23% | -23.28% | +40.09% | compare vs SMH and QQQ | 0.00x | $10.39 | -10.04% | +19.36% | $151.00 / $77.93 | production must calculate from Polygon bars |
| NVDA | -6.20% | -2.86% | -3.03% | compare vs SMH and QQQ | 0.00x | $7.97 | -3.82% | +3.58% | $236.26 / $204.33 | production must calculate from Polygon bars |
| AVGO | -7.92% | -13.66% | -6.50% | compare vs SOXX and QQQ | 0.00x | $16.76 | -7.16% | -0.03% | $495.00 / $385.59 | production must calculate from Polygon bars |
| PLTR | -4.35% | -13.42% | -1.11% | compare vs SMH and QQQ | 0.00x | $6.90 | -2.13% | -3.04% | $163.70 / $128.75 | production must calculate from Polygon bars |
| NET | -6.90% | +3.43% | -2.60% | compare vs IGV and QQQ | 0.00x | $13.28 | +13.91% | +18.33% | $276.82 / $185.75 | production must calculate from Polygon bars |

## Requested Formula Outputs

These are calculations requested by the brain. They are not action instructions.

| Symbol | Formula Request | Muscle Output Field | Production Requirement |
|---|---|---|---|

### Computed Level Details

## Rule Collision Results

Only collide brain-provided rules with muscle facts.

| Symbol | Rule ID | Brain Rule | Muscle Fact Used | Triggered | Computed Result |
|---|---|---|---|---|---|
| RKLB | yellow_state_conditional_only | permission_state_before_open == Yellow | permission_state_before_open=Yellow | true | `condition_pass_fail_only` |
| NVDA | yellow_state_conditional_only | permission_state_before_open == Yellow | permission_state_before_open=Yellow | true | `condition_pass_fail_only` |
| AVGO | yellow_state_conditional_only | permission_state_before_open == Yellow | permission_state_before_open=Yellow | true | `condition_pass_fail_only` |
| PLTR | yellow_state_conditional_only | permission_state_before_open == Yellow | permission_state_before_open=Yellow | true | `condition_pass_fail_only` |
| NET | yellow_state_conditional_only | permission_state_before_open == Yellow | permission_state_before_open=Yellow | true | `condition_pass_fail_only` |

## Missing Data

- none

## Warnings

- polygon_api_key_missing_or_failed; fell back to yfinance sandbox data which is not production grade

## Forbidden Content Check

| Forbidden Content | Present |
|---|---|
| buy / sell / hold recommendation | false |
| permission state change | false |
| final thesis adoption | false |
| psychological interpretation | false |
| invented entry / support / sizing | false |

## Machine-Readable Summary

```json
{
  "packet_type": "plan_evidence_packet",
  "stage": "pre_market_stage_1",
  "focus_pool": [
    "RKLB",
    "NVDA",
    "AVGO",
    "PLTR",
    "NET"
  ],
  "permission_state_echo": "Yellow",
  "symbol_results": {
    "RKLB": {
      "role": "watchlist",
      "plan_mode": "observe",
      "calculation_status": "verified",
      "rule_collisions": [
        {
          "rule_id": "yellow_state_conditional_only",
          "triggered": true,
          "computed_result": "condition_pass_fail_only"
        }
      ]
    },
    "NVDA": {
      "role": "watchlist",
      "plan_mode": "observe",
      "calculation_status": "verified",
      "rule_collisions": [
        {
          "rule_id": "yellow_state_conditional_only",
          "triggered": true,
          "computed_result": "condition_pass_fail_only"
        }
      ]
    },
    "AVGO": {
      "role": "watchlist",
      "plan_mode": "observe",
      "calculation_status": "verified",
      "rule_collisions": [
        {
          "rule_id": "yellow_state_conditional_only",
          "triggered": true,
          "computed_result": "condition_pass_fail_only"
        }
      ]
    },
    "PLTR": {
      "role": "watchlist",
      "plan_mode": "observe",
      "calculation_status": "verified",
      "rule_collisions": [
        {
          "rule_id": "yellow_state_conditional_only",
          "triggered": true,
          "computed_result": "condition_pass_fail_only"
        }
      ]
    },
    "NET": {
      "role": "watchlist",
      "plan_mode": "observe",
      "calculation_status": "verified",
      "rule_collisions": [
        {
          "rule_id": "yellow_state_conditional_only",
          "triggered": true,
          "computed_result": "condition_pass_fail_only"
        }
      ]
    }
  }
}
```
