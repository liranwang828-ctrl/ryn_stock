---
packet_type: runtime_monitor_packet
status: verified
generated_at: 2026-06-07T14:30:00Z
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli intraday-snapshot --symbols "COHR,NVDA" --out findings/runtime-monitor-packet.md
inputs:
  symbols: "COHR,NVDA"
  refresh: "true"
data_sources:
  - polygon
  - local_cache
missing_data:
  - ibkr_feed_delayed_5s
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - final_thesis_adoption
  - permission_state_change
---

# Intraday Snapshot Runtime Packet (2026-06-07)

Boundary: Factual intraday quote monitoring & proximity alerts only.

## 1. Intraday Snapshot Indicators

| Ticker | Current Price | Preset Entry | Hard Stop | Distance to Stop % | Cooldown Until | State |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| COHR | $97.20 | $96.00 | $82.00 | +15.63% | none | monitored |
| NVDA | $206.20 | — | $205.00 | +0.58% | none | ⚠️ close_to_stop |

## 2. Technical Factors & VWAP Deviation

- **COHR**:
  - Last Price: $97.20 (above VWAP $96.80 by +0.41%)
  - Volume Ratio: 1.3x (elevated intraday volume)
- **NVDA**:
  - Last Price: $206.20 (below VWAP $210.50 by -2.04%)
  - Volume Ratio: 0.9x

## 3. Position Proximity Alerts
* **[WARNING] NVDA** is currently trading at `$206.20`, which is **+0.58%** ($1.20) away from its preset hard stop floor of `$205.00`.
* COHR is trading safely within parameters.

## 4. Missing Data & Warnings
- ibkr_feed_delayed_5s: IBKR gateway connection latency detected. Quotes derived via Polygon.io REST aggregates.
