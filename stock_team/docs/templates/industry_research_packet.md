---
packet_type: industry_research_packet
status: verified
generated_at: 2026-06-07T18:30:00Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli industry-packet --theme optical --symbols "COHR,LITE,AAOI" --out findings/industry-packet-COHR.md
inputs:
  theme: "optical"
  symbols: "COHR,LITE,AAOI"
data_sources:
  - yfinance
  - local_cache
missing_data:
  - none
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - final_thesis_adoption
  - permission_state_change
---

# Industry Research Evidence Packet: Optical Theme (COHR Peers)

## 1. Peers Relative Strength Matrix

Price returns relative to Benchmark QQQ and Sector ETF SOXX over different horizons:

| Symbol | 5D vs QQQ | 20D vs QQQ | 60D vs QQQ | 5D vs SOXX | 20D vs SOXX | 60D vs SOXX |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **COHR** | +3.40% | +12.50% | -4.50% | +1.20% | +8.40% | -2.10% |
| **LITE** | +0.80% | +5.10% | -8.20% | -1.40% | +1.00% | -5.80% |
| **AAOI** | -2.15% | -4.20% | -15.40% | -4.35% | -8.30% | -13.00% |

## 2. Peer Performance Ranking by Return

Horizons sorted from strongest to weakest:
- **5-Day Horizon**: COHR (+3.40%) > LITE (+0.80%) > AAOI (-2.15%)
- **20-Day Horizon**: COHR (+12.50%) > LITE (+5.10%) > AAOI (-4.20%)

## 3. Drawdown & Volatility Stats

- **COHR**:
  - Drawdown from 60D High: -12.40% (60D High: $110.00 | Last Price: $96.36)
  - 14D ATR: $4.20
  - Volume Trend: 10D Average Volume 1.5M shares. Current Volume 1.8M shares (expanding).
- **LITE**:
  - Drawdown from 60D High: -18.20% (60D High: $62.00 | Last Price: $50.72)
  - 14D ATR: $2.40
  - Volume Trend: 10D Average Volume 800k shares. Current Volume 600k shares (shrinking).
- **AAOI**:
  - Drawdown from 60D High: -38.50% (60D High: $18.50 | Last Price: $11.38)
  - 14D ATR: $1.10
  - Volume Trend: 10D Average Volume 1.2M shares. Current Volume 1.1M shares.

## 4. Key Daily Levels & Anchors

- **COHR**: Support 20D: $92.50 | Resistance 20D: $102.40 | Support 60D: $85.00
- **LITE**: Support 20D: $48.20 | Resistance 20D: $54.10 | Support 60D: $44.50
- **AAOI**: Support 20D: $10.20 | Resistance 20D: $13.50 | Support 60D: $8.90
