---
packet_type: company_research_packet
status: verified
generated_at: 2026-06-07T18:00:00Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli company-packet --symbol ORCL --peers "MSFT,AMZN" --out findings/company-packet-ORCL.md
inputs:
  symbol: "ORCL"
  peers: "MSFT,AMZN"
data_sources:
  - yfinance
  - polygon_news_api
  - local_cache
missing_data:
  - none
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - final_thesis_adoption
  - permission_state_change
---

# Company Research Evidence Packet (ORCL)

## 1. Business Description & Overview
- **Name**: Oracle Corporation
- **Sector**: Technology | **Industry**: Software—Infrastructure
- **Summary**: Provides products and services that address enterprise information technology environments, including cloud SaaS/PaaS/IaaS offerings.

## 2. Quarterly Revenue Structure & Margin Trends

| Metric | 2026-02-28 | 2025-11-30 | 2025-08-31 | 2025-05-31 |
| :--- | ---: | ---: | ---: | ---: |
| **Total Revenue** | $13,280.0M | $12,940.0M | $12,450.0M | $14,290.0M |
| **Gross Profit** | $9,560.0M | $9,280.0M | $8,910.0M | $10,410.0M |
| **Operating Income** | $4,850.0M | $4,710.0M | $4,220.0M | $5,690.0M |
| **Net Income** | $3,540.0M | $3,410.0M | $2,930.0M | $4,140.0M |
| **Gross Margin %** | 71.99% | 71.72% | 71.57% | 72.85% |
| **Operating Margin %**| 36.52% | 36.40% | 33.90% | 39.82% |

## 3. OCI Cloud Growth & RPO Backlog Signals
- **OCI (Oracle Cloud Infrastructure) Revenue**: $1.8B (+42.5% YoY in latest quarter).
- **RPO (Remaining Performance Obligations)**: $80.2B (+29.0% YoY).
- **OCI Backlog growth rate**: +34.0% YoY.

## 4. Capex, Funding & Debt Signals
- **Capital Expenditure (Capex)**: $2.4B (supporting AI OCI data center buildouts).
- **Total Debt**: $87.5B.
- **Cash and Cash Equivalents**: $9.8B.

## 5. Relative Strength & Key Technical Levels
- **Drawdown from 60D High**: -4.80% (60D High: $148.00 | Last Price: $140.90)
- **Key Support Levels**: Support 20D: $138.20 | Support 60D: $132.50
- **Key Resistance Levels**: Resistance 20D: $146.50 | Resistance 60D: $148.00
- **Price RS vs Benchmarks**:
  - 5D vs QQQ: +1.20%
  - 20D vs QQQ: -0.45%
  - 5D vs IGV: +0.80%

## 6. Polygon Corporate News Headlines
- `[2026-06-05]` Oracle signs OCI GPU capacity partnership with Google Cloud (polygon)
- `[2026-06-02]` Oracle earnings expectations build ahead of next week's release (polygon)
