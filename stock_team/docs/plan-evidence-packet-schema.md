# Plan Evidence Packet Schema

This document defines the output schema of the `premarket` command (Plan Evidence Packet). 
It explicitly decouples qualitative decisions (the Brain) from quantitative observations (the Muscle).

## YAML Front Matter Layout

```yaml
---
packet_type: pre_market_packet
status: verified
generated_at: 2026-06-06T12:01:21Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli premarket
inputs:
  date: "2026-06-06"
  watchlist: "D:\gemini\lianghua\stock_team\watchlist_test.json"
  decision_sheet: "D:\gemini\lianghua\stock_team\tests\fixtures\pre-market-decision-sheet.example.json"
data_sources:
  - yfinance
  - local_cache
missing_data: []
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - final_thesis_adoption
  - permission_state_change
  - invented_entry_support_sizing
---
```

## Markdown Structural Sections

### 1. Market Context Overview
Facts about the general market indexes:
* SPY Pre-market price & Day Change%
* NQ Futures Change%
* VIX Spot Level

### 2. Brain Decision Echo (主脑输入回显)
A summary table showing exactly what the Brain instructed the Muscle to track (strictly rules and limits, no hardcoded physical prices):
* **Ticker**
* **Role** (Core / Swing / Short-term / Watchlist)
* **Entry Strategy** (Enum)
* **Invalidation Rule** (Enum)
* **Risk Budget %** (R-value allocation)
* **Position Cap %**
* **Allowed Tactics** (authorized methods)
* **Forbidden Actions** (discipline constraints)

### 3. Muscle Candidate Factors (肌肉计算候选因子)
Objective quantitative variables calculated by the Muscle for today:
* **Ticker**
* **Premarket Gap %**
* **14-Day ATR** (objective volatility)
* **5-Day RS vs Sector ETF** (relative strength benchmarked)
* **Premarket Volume Ratio**
* **Prior High & Low**

### 4. Rule Collision Results (规则碰撞与纪律计算)
The resulting physical prices and shares computed by the Muscle when Brain rules intersect with market data:
* **Ticker**
* **Computed Entry Base** (Formula-derived physical entry level)
* **Computed Support Floor** (Formula-derived physical invalidation level)
* **Computed Sizing Shares** (Physical purchase shares calculated as: `(NetLiquidation * Risk_Budget_Pct) / (Entry_Base - Support_Floor)`)
* **Rule Checked**: (e.g. `If gap_pct > 2% then scale size by 50%`)
* **Status**: (`TRIGGERED` or `PASSED`)
* **Sizing Discipline Check**: (e.g. `computed_multiplier: 0.5` due to triggered gap penalty)
* **Invalidation Trigger Alert**: Warning if invalidation levels are violated (e.g. `breached_condition: premarket_price_below_support_floor`)

### 5. Source List & Data Quality Notes
* Standard citations of API services used and timestamp freshness logs.
