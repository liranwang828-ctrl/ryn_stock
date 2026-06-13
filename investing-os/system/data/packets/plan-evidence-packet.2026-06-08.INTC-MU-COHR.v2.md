---
packet_type: plan_evidence_packet
stage: pre_market_stage_1
status: fallback_data
generated_at: 2026-06-08T13:45:51.451538Z
source_system: stock_team
requested_by: investing-os
command: python -m stock_team.cli premarket --date 2026-06-08 --decision-sheet C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.2026-06-08.INTC-MU-COHR.v2.json --out C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.2026-06-08.INTC-MU-COHR.v2.md
brain_input_artifact: C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.2026-06-08.INTC-MU-COHR.v2.json
derived_from_stage0_packet: C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.2026-06-08.INTC-MU-COHR.v2.md
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

# Stage 1 Plan Evidence Packet: INTC + MU + COHR

Boundary:

This packet contains facts, calculations, and rule collisions only.

It does not decide whether trading is allowed.
It does not recommend buy / sell / hold.
It does not adopt or reject the thesis.

## Input Summary

| Field | Value |
|---|---|
| Date | 2026-06-08 |
| Focus Pool | INTC, MU, COHR |
| Permission State Echo | Yellow |
| Stage 0 Source | `pre-market-context-packet.2026-06-08.INTC-MU-COHR.v2.md` |
| Brain Input | `stage1-pre-market-decision-sheet.2026-06-08.INTC-MU-COHR.v2.json` |

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
| INTC | watchlist | semiconductors | candidate_only | observe | — | new intraday action; treat turnaround narrative as thesis; treat weak rebound as core-quality evidence | max_loss=0; position_cap=0; attention=10m |
| MU | watchlist | memory | candidate_only | observe | — | new intraday action; memory-cycle excitement treated as entry signal; average down without written plan | max_loss=0; position_cap=0; attention=10m |
| COHR | swing | optical | researched_draft | observe | — | new intraday action; chase near highs; add while lagging optical/semiconductor peers | max_loss=0; position_cap=0; attention=10m |

## Symbol Factor Calculations

Facts and calculated factors only.

| Symbol | 1D % | 5D % | 20D % | Relative Strength Context | Volume Ratio | ATR(14) | MA20 Distance | MA50 Distance | Prior Day High / Low | Notes |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|---|
| INTC | +11.82% | +1.43% | -11.23% | compare vs SOXX and QQQ | 0.11x | — | — | — | — | production must calculate from Polygon bars |
| MU | -13.25% | -11.02% | +33.62% | compare vs SOXX and QQQ | 1.37x | — | — | — | — | production must calculate from Polygon bars |
| COHR | -10.64% | +4.29% | +18.11% | compare vs LITE and QQQ | 1.04x | — | — | — | — | production must calculate from Polygon bars |

## Requested Formula Outputs

These are calculations requested by the brain. They are not action instructions.

| Symbol | Formula Request | Muscle Output Field | Production Requirement |
|---|---|---|---|

### Computed Level Details

## Rule Collision Results

Only collide brain-provided rules with muscle facts.

| Symbol | Rule ID | Brain Rule | Muscle Fact Used | Triggered | Computed Result |
|---|---|---|---|---|---|
| INTC | yellow_state_conditional_only | permission_state_before_open == Yellow | permission_state_before_open=Yellow | true | `condition_pass_fail_only` |
| MU | yellow_state_conditional_only | permission_state_before_open == Yellow | permission_state_before_open=Yellow | true | `condition_pass_fail_only` |
| COHR | yellow_state_conditional_only | permission_state_before_open == Yellow | permission_state_before_open=Yellow | true | `condition_pass_fail_only` |

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
    "INTC",
    "MU",
    "COHR"
  ],
  "permission_state_echo": "Yellow",
  "symbol_results": {
    "INTC": {
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
    "MU": {
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
    "COHR": {
      "role": "swing",
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
