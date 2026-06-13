# Pre-Market Decision Sheet Schema

This document defines the schema of the inputs that `investing-os` (the Brain) must pass to `stock_team` (the Muscle) prior to market open. It strictly forbids the Brain from passing hardcoded price levels, requiring abstract logic keys instead.

## JSON Schema

The decision sheet is a per-symbol dictionary containing strategic choices, limits, and rules:

```json
{
  "symbol": "COHR",
  "role": "swing",
  "thesis_ref": "SOXX sector relative strength rebound after 60D consolidation",
  "allowed_tactics": ["rs_pullback_rebound"],
  "forbidden_actions": ["new_short_term_risk", "loss_repair_averaging"],
  "entry_strategy": "CONSOLIDATION_FLOOR",
  "invalidation_rule": "MA20_MINUS_1X_ATR",
  "portfolio_risk_budget_pct": 0.005,
  "position_cap": 0.10,
  "attention_budget_mins": 30,
  "evidence_required": ["trade_evidence", "company_packet"]
}
```

## Field Descriptions

| Field | Owner | Type | Description |
| :--- | :---: | :---: | :--- |
| `symbol` | Brain | String | Target ticker symbol |
| `role` | Brain | String | Position role (`core`, `swing`, `short_term`, `watchlist`) |
| `thesis_ref` | Brain | String | Qualitative reason for monitoring this symbol |
| `allowed_tactics` | Brain | Array | Pre-authorized strategy templates |
| `forbidden_actions` | Brain | Array | Forbidden actions for today (discipline constraints) |
| `entry_strategy` | Brain | Enum | Calculation rule for entry price (Must match keys in `rule-catalog.json`) |
| `invalidation_rule` | Brain | Enum | Calculation rule for invalidation stop (Must match keys in `rule-catalog.json`) |
| `portfolio_risk_budget_pct`| Brain | Float | Risk budget allocation as a percent of account Net Liquidation (e.g. `0.005` for 0.5% risk) |
| `position_cap` | Brain | Float | Maximum portfolio sizing weight allowed (e.g. `0.10` for 10%) |
| `attention_budget_mins` | Brain | Int | Max visual monitoring time allowed to prevent overtrading |
| `evidence_required` | Brain | Array | Artifacts required to unlock execution permissions |
