---
packet_type: contextual_trade_evidence_packet
status: verified
generated_at: 2026-06-07T16:30:00Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli trade-evidence --symbol COHR --date 2026-06-06 --fills findings/fills_COHR.md --out findings/contextual-trade-evidence-packet.md
inputs:
  symbol: "COHR"
  date: "2026-06-06"
  fills: "findings/fills_COHR.md"
data_sources:
  - polygon
  - ibkr
missing_data:
  - none
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - final_thesis_adoption
  - permission_state_change
---

# Contextual Trade Evidence Packet (COHR | 2026-06-06)

Boundary: Factual execution metrics relative to intraday price action, VWAP, and volume benchmarks. No qualitative trader evaluation.

## 1. Execution Summary
- **Total Executed Quantity**: 150 shares (Buy)
- **Average Fill Price**: $97.10
- **Realized P/L**: $0.00 (position open)
- **Broker Commission**: $1.50

## 2. Standardized Execution Log
Time conversions from Shanghai Local Time (UTC+8) to Eastern Time (UTC-4):

| Fill Time (Local) | Fill Time (ET) | Side | Qty | Price | Intraday VWAP | Deviation vs VWAP % | Opening Window |
| :--- | :--- | :---: | ---: | ---: | ---: | ---: | :--- |
| 2026-06-06 21:40:00 | 2026-06-06 09:40:00 | Buy | 100 | $97.50 | $96.80 | +0.72% | 5-15 Min Window |
| 2026-06-06 21:55:00 | 2026-06-06 09:55:00 | Buy | 50 | $96.30 | $96.40 | -0.10% | 15-30 Min Window |

## 3. Opening 30-Minute Structure Analysis
- **0-5 Min (09:30-09:35)**: Opening range established high at $98.50, low at $96.00. No trade executed.
- **5-15 Min (09:35-09:45)**: Price consolidated around $97.00. First tranche of 100 shares filled at $97.50 (+0.72% above VWAP).
- **15-30 Min (09:45-10:00)**: Price pull back to $96.10, reclaiming VWAP. Second tranche of 50 shares filled at $96.30 (-0.10% below VWAP).

## 4. Key Intraday Milestones
- **Daily High**: $98.50 at 09:32 ET
- **Daily Low**: $95.20 at 14:15 ET
- **Close Price**: $97.20 (Daily Return: +2.31%)
- **Last 30-Min Trend**: Consolidated between $97.10 - $97.25 on declining volume (50k shares).

## 5. Source List & Data Quality Notes
1. **IBKR Client Portal Fills Log**: Base execution time and price records.
2. **Polygon.io 1-Minute Historical Aggregates**: Used for minute-by-minute VWAP calculations and benchmark comparison.
