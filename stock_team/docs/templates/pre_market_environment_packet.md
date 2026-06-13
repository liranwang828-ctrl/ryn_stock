---
packet_type: pre_market_environment_packet
status: verified
generated_at: 2026-06-07T00:00:00Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli market-context --date 2026-06-06 --themes "semiconductors,cloud" --universe watchlist_test.json --out findings/market-context-packet.md
inputs:
  date: "2026-06-06"
  themes: "semiconductors,cloud"
  universe: "watchlist_test.json"
data_sources:
  - polygon
  - local_cache
missing_data:
  - VIX_futures_delayed_15m
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - final_thesis_adoption
  - permission_state_change
---

# Pre-Market Environment Packet (2026-06-06)

Boundary: factual environment context only. No symbol selection or trading permission.

## 1. Yesterday / Recent Market Context

| Symbol | Label | Price | Yesterday % | 5D % | 20D % | Volume Ratio | Source |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| QQQ | Nasdaq 100 proxy | 445.50 | +0.25% | +1.20% | -2.30% | 1.1x | polygon |
| SPY | S&P 500 proxy | 520.10 | +0.10% | +0.80% | -1.10% | 0.9x | polygon |
| IWM | Small-cap risk proxy | 198.50 | -0.15% | -0.40% | -3.50% | 1.2x | polygon |
| VIXY | VIX ETF proxy | 13.40 | -1.20% | -4.50% | +12.00% | 0.8x | polygon |

## 2. Sector / Theme Heat

| Theme | Proxy | 5D % | 20D % | Source |
| :--- | :---: | ---: | ---: | :--- |
| semiconductors | SOXX | +3.40% | -4.50% | polygon |
| cloud | IGV | +1.20% | -2.10% | polygon_cache |

## 3. Universe Input Quality

- universe_count: 5
- universe_required_fields_complete: true
- field_gaps: none

## 4. Universe Relevance Map

This section maps market/theme facts to the brain-provided universe only. It is not symbol selection.

| Symbol | Role | Theme | Research Status | Theme 5D % | Theme 20D % | Notes |
| :--- | :---: | :--- | :---: | ---: | ---: | :--- |
| NVDA | core | semiconductors | approved | +3.40% | -4.50% | evidence mapping only |
| COHR | swing | semiconductors | approved | +3.40% | -4.50% | evidence mapping only |
| VST | swing | utilities | review_needed | — | — | no utility theme proxy configured |
| NOW | swing | cloud | approved | +1.20% | -2.10% | evidence mapping only |
| GOOGL | core | cloud | approved | +1.20% | -2.10% | evidence mapping only |

## 5. Catalysts To Notice
- [macro] CBOE VIX Spot dropped below 14.50 (polygon)
- [earnings] NVDA reporting results next Wednesday post-market (polygon)

## 6. Missing Data / Warnings
- VIX_futures_delayed_15m: Local proxy socket timeout during futures fetch. Fallback to spot indices.
