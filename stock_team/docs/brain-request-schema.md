# Brain Request Schema

This document defines the schema of requests initiated by `investing-os` (the Brain) when requesting quantitative packets from `stock_team` (the Muscle).

## 1. Company / Industry Research Request

```json
{
  "request_type": "company_research_request",
  "symbol": "COHR",
  "research_questions": [
    "Verify quarterly revenue growth vs historical average",
    "Identify key semiconductor peer relative strength parameters"
  ],
  "hypotheses_to_verify": {
    "moat_exists": "technology_barrier_semiconductor",
    "fcf_healthy": "operating_cashflow_vs_capex"
  }
}
```

## 2. Trade Review Request

```json
{
  "request_type": "trade_review_request",
  "symbol": "COHR",
  "trade_date": "2026-06-05",
  "rules_to_audit": [
    "did_entry_occur_below_vwap",
    "did_stop_loss_comply_with_max_loss_budget"
  ]
}
```
