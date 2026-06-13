# Stock Team Latest Dashboard Manifest

Purpose:

Let `investing-os` link to the latest `stock_team` evidence dashboard without knowing how `stock_team` renders or stores dashboard internals.

`investing-os` owns the operating console.

`stock_team` owns the evidence dashboard.

## Manifest Path

Expected stable path:

```text
D:\gemini\lianghua\stock_team\reports\latest_evidence_dashboard.json
```

## Required Shape

```json
{
  "manifest_type": "stock_team_latest_evidence_dashboard",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "trading_date": "YYYY-MM-DD",
  "status": "ready | partial | stale | error",
  "dashboard_path": "D:\\gemini\\lianghua\\stock_team\\reports\\daily\\YYYY-MM-DD\\evidence-dashboard.html",
  "source_guidance": "C:\\Users\\rriww\\Documents\\investing-os\\system\\simulations\\inputs\\intraday-guidance.NVDA-conditional.demo.json",
  "symbols": ["NVDA", "MU"],
  "packet_status": {
    "stage0_market_context": "ready | missing | stale",
    "stage1_plan_evidence": "ready | missing | stale",
    "runtime_snapshot": "ready | missing | stale",
    "ibkr_position_snapshot": "ready | missing | stale"
  },
  "data_source_health": {
    "polygon": "ready | stale | error | missing",
    "ibkr": "ready | stale | error | missing",
    "local_cache": "fresh | stale | unused"
  },
  "missing_data": [],
  "warnings": [],
  "forbidden_behavior_check": {
    "buy_sell_hold_recommendations_present": false,
    "permission_state_present": false,
    "direct_execution_controls_present": false
  }
}
```

## Investing-OS Consumption

The operating console should show only:

- dashboard status
- generated time
- missing-data summary
- link to `dashboard_path`

It should not copy the full `stock_team` dashboard into the main operating console.
