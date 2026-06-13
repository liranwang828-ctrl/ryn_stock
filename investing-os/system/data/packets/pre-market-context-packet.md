---
packet_type: pre_market_environment_packet
status: verified
generated_at: 2026-06-09T15:04:01.460141Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli market-context
inputs:
  date: "2026-06-08"
  as_of: ""
  as_of_et: ""
  themes: "semiconductors,ai_infrastructure,memory,optical"
  pre_market_snapshot: ""
  offline_fixture: "C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-market-context-fixture.2026-06-08.INTC-MU-COHR.replay.json"
  universe: "C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-pre-market-universe.2026-06-08.INTC-MU-COHR.v2.json"
data_sources:
  - replay_fixture_from_prior_stage0_packet
  - replay_fixture_from_stock_team_cache
missing_data:
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - trading_permission_state
  - symbol_selection_recommendation
  - final_thesis_adoption
  - psychological_interpretation
---

# Pre-Market Environment Packet (2026-06-08)

Boundary: factual environment context only. No symbol selection or trading permission.

## 1. Yesterday / Recent Market Context

| Symbol | Label | Price | Yesterday % | 5D % | 20D % | Volume Ratio | Source |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| QQQ | Nasdaq 100 proxy | 705.06 | -4.78% | -4.50% | +1.46% | 2.4x | replay_fixture_from_prior_stage0_packet |
| SPY | S&P 500 proxy | 737.55 | -2.58% | -2.50% | +0.82% | 1.9x | replay_fixture_from_prior_stage0_packet |
| IWM | Small-cap risk proxy | 281.65 | -3.55% | -3.02% | -0.22% | 1.4x | replay_fixture_from_prior_stage0_packet |
| VIXY | VIX ETF proxy | 24.31 | +7.23% | +4.38% | -9.46% | 2.0x | replay_fixture_from_prior_stage0_packet |

## 2. Sector / Theme Heat

| Theme | Proxy | 5D % | 20D % | Source |
| :--- | :---: | ---: | ---: | :--- |
| semiconductors | SOXX | -5.15% | +9.63% | replay_fixture_from_prior_stage0_packet |
| ai_infrastructure | SMH | -4.88% | +5.48% | replay_fixture_from_prior_stage0_packet |
| memory | MU | -7.65% | +28.05% | replay_fixture_from_stock_team_cache |
| optical | LITE | +1.02% | -3.24% | replay_fixture_from_stock_team_cache |

## 3. Universe Input Quality

- universe_count: 3
- universe_required_fields_complete: true
- brain_precondition_state_complete: true
- permission_state_before_open_echo: Red
- source_positions_present: true
- prior_review_present: true
- cognition_state_present: true
- forbidden_actions_echo:
  - new_short_term_trade
  - new_leveraged_product_trade
  - loss_repair_reentry
  - adding_to_unresolved_MUU_risk
- field_gaps: none

## 4. Universe Relevance Map

This section maps market/theme facts to the brain-provided universe only. It is not symbol selection.

| Symbol | Role | Theme | Research Status | Theme 5D % | Theme 20D % | Notes |
| :--- | :---: | :--- | :---: | ---: | ---: | :--- |
| INTC | watchlist | semiconductors | candidate_only | -5.15% | +9.63% | evidence mapping only |
| MU | watchlist | memory | candidate_only | -7.65% | +28.05% | evidence mapping only |
| COHR | swing | optical | researched_draft | +1.02% | -3.24% | evidence mapping only |

## 5. Catalysts To Notice

- [macro] Rate-path and inflation expectation risk remained a Stage0 observation variable. (cognition_replay_pending_fact_verification)
- [market_structure] Rebound quality must be evaluated by breadth and leadership persistence, not by one-day strongest names. (2026-06-08-market-rebound-cognition-review)
- [personal_risk] Narrow high-beta strength may increase FOMO risk after major drawdown recovery state. (2026-06-08-market-rebound-cognition-review)

## 6. Missing Data / Warnings

- none
