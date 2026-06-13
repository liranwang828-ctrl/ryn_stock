# Intraday Workflow

> [!NOTE]
> *Temporarily modified by Antigravity; pending validation by Codex.*

## Goal

Execute the plan with minimum emotional interference, driven by active/event-driven quantitative monitoring and zero manual thesis drift.

## Rules

- Run file growth health check before any durable intraday write or absorption: `./tools/check-file-growth.ps1`.
- Watch only predefined symbols in the watchlist and position configuration.
- Act only on predefined triggers and bracket orders set at the broker.
- Do not invent new trades from price movement alone.
- Record emotional impulses instead of obeying them.

---

## Intraday Monitoring Coordination

To minimize bandwidth consumption, API rate-limiting, and context switching, the intraday monitoring operates in a hybrid **Active Pull & Local Streaming** model.

### 1. Local TWS Live Streaming (Primary)
Run the local Interactive Brokers streaming client to monitor active quotes and auto-sync position modifications:
```powershell
# In stock_team repository
python agents/ibkr_monitor.py
```
This script:
- Automatically reads symbols from [current-watchlist.md](file:///C:/Users/rriww/Documents/investing-os/decision/current-watchlist.md) and `stock_team/config/positions.json`.
- Connects to TWS or IB Gateway locally (0 internet loopback overhead).
- Calculates real-time VWAP and Stop-Loss distances in memory.
- Writes updates to `system/data/packets/intraday_snapshot.json` and updates `intraday_snapshot.md` when events trigger.
- Syncs execution details to `positions.json` automatically on fills.

### 2. Stateless On-Demand Query (Fallback)
If TWS is offline, perform an on-demand yfinance/Polygon snapshot check:
```powershell
# In stock_team repository
python agents/poll.py [symbols] --once
```
This command runs a single-iteration scan, updates the snapshot files, and exits immediately.

---

## Data Transmission Schema

The monitoring scripts write their results to [intraday_snapshot.json](file:///C:/Users/rriww/Documents/investing-os/system/data/packets/intraday_snapshot.json). The master brain ingests this file to render dashboards or evaluate trade plans.

### JSON Contract Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "IntradaySnapshotPacket",
  "type": "object",
  "required": ["timestamp", "source", "account", "positions", "alerts"],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of when the snapshot was generated"
    },
    "source": {
      "type": "string",
      "enum": ["ibkr_stream", "yfinance_once", "polygon_once", "offline_fallback"]
    },
    "account": {
      "type": "object",
      "required": ["cash", "net_liquidation", "unrealized_pnl", "day_pnl"],
      "properties": {
        "cash": { "type": "number" },
        "net_liquidation": { "type": "number" },
        "unrealized_pnl": { "type": "number" },
        "day_pnl": { "type": "number" }
      }
    },
    "positions": {
      "type": "object",
      "description": "Mapping from uppercase symbol to position detail",
      "additionalProperties": {
        "type": "object",
        "required": ["cost", "shares", "current_price", "market_value", "unrealized_pnl", "pct_of_portfolio"],
        "properties": {
          "cost": { "type": "number" },
          "shares": { "type": "number" },
          "current_price": { "type": "number" },
          "market_value": { "type": "number" },
          "unrealized_pnl": { "type": "number" },
          "pct_of_portfolio": { "type": "number" }
        }
      }
    },
    "alerts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["symbol", "level", "alert_type", "message"],
        "properties": {
          "symbol": { "type": "string" },
          "level": { "type": "string", "enum": ["RED", "YELLOW", "INFO"] },
          "alert_type": { "type": "string", "description": "e.g., hard_stop_breach, vwap_deviation, thesis_breach" },
          "message": { "type": "string" }
        }
      }
    }
  }
}
```

---

## Output

If alert is triggered or actions are taken:
1. Review the generated [intraday_snapshot.md](file:///C:/Users/rriww/Documents/investing-os/system/data/packets/intraday_snapshot.md) for rationale.
2. Log command executions in [stock-team-call-log.md](file:///C:/Users/rriww/Documents/investing-os/integrations/stock-team-call-log.md).
3. If orders are filled, verify that the local background listener updated `stock_team/config/positions.json` accordingly.
