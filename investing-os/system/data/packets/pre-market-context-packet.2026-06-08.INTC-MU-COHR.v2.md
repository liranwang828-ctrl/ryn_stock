---
packet_type: pre_market_environment_packet
status: verified
generated_at: 2026-06-08T13:45:21.693212Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli market-context
inputs:
  date: "2026-06-08"
  themes: "QQQ,SPY,IWM,VIXY,SMH,SOXX"
  offline_fixture: ""
  universe: "C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-pre-market-universe.2026-06-08.INTC-MU-COHR.v2.json"
data_sources:
  - polygon_cache
missing_data:
  - no_proxy_configured_for_theme_QQQ
  - no_proxy_configured_for_theme_SPY
  - no_proxy_configured_for_theme_IWM
  - no_proxy_configured_for_theme_VIXY
  - no_proxy_configured_for_theme_SMH
  - no_proxy_configured_for_theme_SOXX
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
| QQQ | Nasdaq 100 proxy | 705.06 | -4.80% | -4.50% | +1.46% | 2.4x | polygon_cache |
| SPY | S&P 500 proxy | 737.55 | -2.58% | -2.50% | +0.82% | 1.9x | polygon_cache |
| IWM | Small-cap risk proxy | 281.65 | -3.55% | -3.02% | -0.22% | 1.4x | polygon_cache |
| VIXY | VIX ETF proxy | 24.31 | +7.23% | +4.38% | -9.46% | 2.0x | polygon_cache |

## 2. Sector / Theme Heat

| Theme | Proxy | 5D % | 20D % | Source |
| :--- | :---: | ---: | ---: | :--- |
| QQQ | QQQ | -4.50% | +1.46% | polygon_cache |
| SPY | SPY | -2.50% | +0.82% | polygon_cache |
| IWM | IWM | -3.02% | -0.22% | polygon_cache |
| VIXY | VIXY | +4.38% | -9.46% | polygon_cache |
| SMH | SMH | -4.88% | +5.48% | polygon_cache |
| SOXX | SOXX | -5.15% | +9.63% | polygon_cache |

## 3. Universe Input Quality

- universe_count: 3
- universe_required_fields_complete: true
- field_gaps: none

## 4. Universe Relevance Map

This section maps market/theme facts to the brain-provided universe only. It is not symbol selection.

| Symbol | Role | Theme | Research Status | Theme 5D % | Theme 20D % | Notes |
| :--- | :---: | :--- | :---: | ---: | ---: | :--- |
| INTC | watchlist | semiconductors | candidate_only | — | — | evidence mapping only |
| MU | watchlist | memory | candidate_only | — | — | evidence mapping only |
| COHR | swing | optical | researched_draft | — | — | evidence mapping only |

## 5. Catalysts To Notice

- [macro] Stock Market Today: Dow, Nasdaq S&P 500 Futures Rise As Israel, Iran Exchange Missile Strikes—SK Telecom, Nebius, AMD In Focus (UPDATED) (Benzinga) (polygon)
- [macro] Cathie Wood Calls Fed's 2022 Rate Hikes A 'Massive Mistake,' Says Kevin Warsh Will Fix It (Benzinga) (polygon)
- [macro] Nasdaq 100's Worst Day Since Trump Tariff Shock, Crypto Carnage Worsens: This Week On Wall Street (Benzinga) (polygon)
- [company] [INTC] Intel Comeback or AMD Takeover? Which Chip Stock Will Win the AI CPU War? (The Motley Fool) (polygon)
- [company] [INTC] What Jensen Huang Said About GPUs In 2009 Sounds Almost Unbelievable Today— And Why Nvidia Is Coming For The CPU Too (Benzinga) (polygon)
- [company] [MU] Why Micron Technology Stock Skyrocketed 87.8% Last Month But Is Falling in June (The Motley Fool) (polygon)
- [company] [MU] 3 High-Growth Artificial Intelligence (AI) Stocks to Buy With $5,000 Right Now (The Motley Fool) (polygon)
- [company] [COHR] The Anthropic IPO Could Make These 5 AI Stocks Unexpected Winners (The Motley Fool) (polygon)
- [company] [COHR] The Hidden Nvidia Trade Nobody on Wall Street Is Talking About (The Motley Fool) (polygon)

## 6. Missing Data / Warnings

- no_proxy_configured_for_theme_QQQ
- no_proxy_configured_for_theme_SPY
- no_proxy_configured_for_theme_IWM
- no_proxy_configured_for_theme_VIXY
- no_proxy_configured_for_theme_SMH
- no_proxy_configured_for_theme_SOXX
