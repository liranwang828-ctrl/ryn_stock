---
packet_type: plan_evidence_packet
stage: pre_market_stage_1
status: demo_contract
generated_at: 2026-06-06T00:00:00Z
source_system: stock_team
requested_by: investing-os
command: python -m stock_team.cli premarket
brain_input_artifact: C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.MU-NVDA.demo.json
derived_from_stage0_packet: D:\gemini\lianghua\stock_team\scratch\simulation_outputs\stage0_environment_MU-NVDA-COHR-INTC_2026-06-06.md
calculation_mode: demo_calculation
data_sources:
  - polygon_or_cache_required_in_production
missing_data:
  - premarket_gap_not_available_in_demo
  - catalyst_feed_not_connected_in_demo
warnings:
  - demo_values_are_contract_examples_not_live_market_data
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - permission_state_change
  - final_thesis_adoption
  - psychological_interpretation
  - invented_entry_support_sizing
---

# Stage 1 Plan Evidence Packet: MU + NVDA

Boundary:

This packet contains facts, calculations, and rule collisions only.

It does not decide whether trading is allowed.
It does not recommend buy / sell / hold.
It does not adopt or reject the thesis.

## Input Summary

| Field | Value |
|---|---|
| Date | 2026-06-06 |
| Focus Pool | MU, NVDA |
| Permission State Echo | Red |
| Stage 0 Source | `stage0_environment_MU-NVDA-COHR-INTC_2026-06-06.md` |
| Brain Input | `stage1-pre-market-decision-sheet.MU-NVDA.demo.json` |

## Stage 0 Market Context Echo

These are echoed facts from Stage 0 so the symbol packet remains interpretable.

| Proxy | 1D % | 5D % | 20D % | Volume Ratio | Source |
|---|---:|---:|---:|---:|---|
| QQQ | -4.80 | -4.50 | 1.46 | 2.39 | stage0_packet |
| SPY | -2.58 | -2.50 | 0.82 | 1.92 | stage0_packet |
| IWM | -3.55 | -3.02 | -0.22 | 1.38 | stage0_packet |
| VIXY | 7.23 | 4.38 | -9.46 | 2.05 | stage0_packet |

## Brain Decision Echo

Echo brain-owned fields exactly. `stock_team` must not alter them.

| Symbol | Role | Theme | Research Status | Plan Mode | Allowed Tactics | Forbidden Actions | Risk Budget |
|---|---|---|---|---|---|---|---|
| MU | watchlist | memory | partially_researched | observe | observe_only; rs_pullback_rebound_candidate_review | new_short_term_risk_without_user_confirmation; leveraged_expansion; loss_repair_averaging; role_drift_from_watchlist_to_trade | max_loss=0; position_cap=0; attention=15m |
| NVDA | core | ai_infrastructure | core_position_research_pending | ignore_or_observe | core_hold_observation | intraday_noise_reaction; short_term_thesis_override; core_position_turns_into_trade | max_loss=0; position_cap=0; attention=10m |

## Symbol Factor Calculations

Facts and calculated factors only.

| Symbol | 1D % | 5D % | 20D % | Relative Strength Context | Volume Ratio | ATR(14) | MA20 Distance | MA50 Distance | Prior Day High / Low | Notes |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|---|
| MU | demo | demo | demo | compare vs SOXX and QQQ | demo | demo | demo | demo | demo | production must calculate from Polygon bars |
| NVDA | demo | demo | demo | compare vs SMH and QQQ | demo | demo | demo | demo | demo | production must calculate from Polygon bars |

## Requested Formula Outputs

These are calculations requested by the brain. They are not action instructions.

| Symbol | Formula Request | Muscle Output Field | Production Requirement |
|---|---|---|---|
| MU | MA20, MA50, previous day high/low, 5D anchored VWAP if available | `computed_levels.MU` | Return exact values, source, timestamp, and stale flag |
| MU | ATR(14) distance from current price and last close | `risk_distance.MU` | Return ATR value, distance %, and source bars |
| NVDA | MA20, MA50, previous day high/low, ATR(14) | `computed_levels.NVDA` | Return exact values, source, timestamp, and stale flag |

## Rule Collision Results

Only collide brain-provided rules with muscle facts.

| Symbol | Rule ID | Brain Rule | Muscle Fact Used | Triggered | Computed Result |
|---|---|---|---|---|---|
| MU | red_state_no_new_risk | If permission state is Red, return evidence only | permission_state_before_open=Red | true | evidence_only_no_action_readiness |
| MU | loss_repair_guard | If symbol interest is connected to trapped leveraged exposure, flag for brain review | symbol=MU; related trapped exposure context supplied by brain | true | risk_context_for_brain_review |
| NVDA | core_position_no_intraday_action | If role is core and plan mode is ignore_or_observe, return context evidence only | role=core; plan_mode=ignore_or_observe | true | context_only |

## Missing Data

- premarket_gap_not_available_in_demo
- catalyst_feed_not_connected_in_demo
- production packet must include Polygon freshness or cache freshness

## Warnings

- This demo packet intentionally contains no live price-derived values.
- In production, any fallback to yfinance must appear in `missing_data` or `warnings`.
- If a requested formula cannot be calculated, return `missing`, not an invented level.

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
  "focus_pool": ["MU", "NVDA"],
  "permission_state_echo": "Red",
  "symbol_results": {
    "MU": {
      "role": "watchlist",
      "plan_mode": "observe",
      "calculation_status": "demo_missing_live_values",
      "rule_collisions": [
        {
          "rule_id": "red_state_no_new_risk",
          "triggered": true,
          "computed_result": "evidence_only_no_action_readiness"
        },
        {
          "rule_id": "loss_repair_guard",
          "triggered": true,
          "computed_result": "risk_context_for_brain_review"
        }
      ]
    },
    "NVDA": {
      "role": "core",
      "plan_mode": "ignore_or_observe",
      "calculation_status": "demo_missing_live_values",
      "rule_collisions": [
        {
          "rule_id": "core_position_no_intraday_action",
          "triggered": true,
          "computed_result": "context_only"
        }
      ]
    }
  }
}
```
