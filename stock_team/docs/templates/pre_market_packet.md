---
packet_type: pre_market_packet
status: verified
generated_at: 2026-06-07T00:05:00Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli premarket --date 2026-06-06 --watchlist watchlist_test.json --decision-sheet decision_sheet_test.json --out findings/pre-market-packet.md
inputs:
  date: "2026-06-06"
  watchlist: "watchlist_test.json"
  decision_sheet: "decision_sheet_test.json"
data_sources:
  - polygon
  - local_cache
missing_data:
  - VIX_live_feed_unavailable
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - final_thesis_adoption
  - permission_state_change
---

# Pre-Market Plan Evidence Packet (2026-06-06)

## 1. Market Context Overview
- **SPY Pre-Market Chg**: +0.12%
- **NQ Futures**: +0.22%
- **VIX Level**: 13.40 (stable)
- **Market Regime Tone**: risk_on

## 2. Brain Decision Echo
This section echoes the exact rules and budgets provided by the Brain (`investing-os`).

| Ticker | Role | Allowed Tactics | Entry Strategy | Invalidation Rule | Risk Budget % | Position Cap |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| COHR | swing | rs_pullback_rebound | rs_pullback_rebound | rs_pullback_rebound | 0.50% | 10.0% |
| NVDA | core | hold_inactive | hold_inactive | hold_inactive | 0.00% | 15.0% |

## 3. Muscle Candidate Factors
Calculated market data and indicator factors at pre-market.

| Ticker | Gap % | 14-Day ATR | RS vs Sector % | Vol Ratio | Prev Close |
| :--- | :---: | :---: | :---: | :---: | :---: |
| COHR | +1.20% | $4.20 | +2.10% | 1.1x | $95.00 |
| NVDA | +0.40% | $6.80 | +0.80% | 0.9x | $220.00 |

## 4. Rule Collision Results & Sizing Calculations
*Account Net Liquidation (Retrieved): $100,000.00*

### COHR Quantitative Check
- **Tactic Applied**: `rs_pullback_rebound`
- **Computed Entry Base**: $96.00 (MA20 price)
- **Computed Support Floor**: $82.00 (MA20 - 1.5 * ATR)
- **Computed Sizing Shares**: 35 shares (Based on allowed loss: $500.00 | Risk per share: $14.00)
- **rule_collision_result**: passed, computed_multiplier: 1.0
- **breached_condition**: none

### NVDA Quantitative Check
- **Tactic Applied**: `hold_inactive`
- **Computed Entry Base**: —
- **Computed Support Floor**: $205.00 (retrieved from current positions stop-loss)
- **Computed Sizing Shares**: 0 (Hold only, zero new risk budget allowed)
- **rule_collision_result**: passed
- **breached_condition**: none

## 5. Source List & Data Quality Notes
1. **Polygon.io**: Real-time ticker aggregates & daily bars.
2. **yfinance**: Fallback verification database (unused for this packet).
3. **Local Position Database**: `positions.json` used for NVDA stop reference.
