# Stock Team CLI Contract

This contract defines the absolute entry points, arguments, input paths, output paths, and schema formats for command execution between the Brain (`investing-os`) and the Muscle (`stock_team`).

All command executions must yield a **Pure Fact Evidence Packet** containing a standardized YAML header, with absolutely zero buy/sell/hold recommendations.

---

## 1. Allowed Commands

### 1.1 Market Context (Stage 0)
Provides the macro/market proxy environmental context prior to daily focus list selection.

* **Command**:
  ```powershell
  python -m stock_team.cli market-context --date YYYY-MM-DD --themes <themes_csv> --universe <universe_json> --out <output_md>
  ```
* **Arguments**:
  - `--date`: The targeted market trading day.
  - `--themes`: Tickers or keywords representing core sector themes (e.g. `semiconductors,cloud`).
  - `--universe`: Absolute path to the Brain's current monitor universe JSON.
  - `--out`: Output destination path for the `pre_market_environment_packet`.

---

### 1.2 Premarket Calculations (Stage 1)
Receives Brain decisions and calculates physical support, entry, and sizing parameters.

* **Command**:
  ```powershell
  python -m stock_team.cli premarket --date YYYY-MM-DD --watchlist <watchlist_json> --decision-sheet <decision_sheet_json> --out <output_md> [--refresh]
  ```
* **Arguments**:
  - `--date`: The targeted market trading day.
  - `--watchlist`: Path to watchlist JSON.
  - `--decision-sheet`: Path to Brain's qualitative decision sheet JSON.
  - `--out`: Output path for the `pre_market_packet`.
  - `--refresh`: Force reload of market prices, bypassing cache.

---

### 1.3 Trade Evidence Exporter
Converts broker fills into ET, maps 1m bar VWAP deviations, and builds post-trade compliance evidence.

* **Command**:
  ```powershell
  python -m stock_team.cli trade-evidence --symbol SYMBOL --date YYYY-MM-DD --fills <fills_json_or_csv> --out <output_md> [--peers SYMBOLS] [--benchmarks SYMBOLS]
  ```
* **Arguments**:
  - `--symbol`: Ticker of the traded asset.
  - `--date`: Trading day of fills.
  - `--fills`: Path to fills markdown/json file.
  - `--out`: Output path for the `contextual_trade_evidence_packet`.

---

### 1.4 Intraday Evidence Dashboard
Reads the Brain's intraday guidance artifact and refreshes factual runtime state against the already-generated Stage 0 and Stage 1 packets.

* **Command**:
  ```powershell
  python -m stock_team.cli intraday-dashboard --guidance <intraday_guidance_json> --out <output_md> [--html-out <output_html>] [--refresh]
  ```
* **Arguments**:
  - `--guidance`: Path to the Brain-generated intraday guidance artifact.
  - `--out`: Optional Markdown dashboard packet output path.
  - `--html-out`: Optional HTML output path. Tests must use this to avoid overwriting the live dashboard.
  - `--refresh`: Refresh runtime market/broker facts only.
  - `--loop`: Keep refreshing runtime evidence outputs until stopped.
  - `--interval-seconds`: Loop interval. Default: `60`.
  - `--iterations`: Optional loop limit for tests, demos, or controlled runs. Omit for continuous operation.
  - `--refresh-timeout-seconds`: Timeout for the runtime refresh subprocess. Default: `10`.
* **Boundary**:
  - Stage 0 and Stage 1 are pre-market anchors. The intraday dashboard must not auto-refresh or regenerate them.
  - The command must fail closed if the referenced Stage 0 or Stage 1 packet is missing.
  - Intraday refresh is limited to runtime evidence: price, VWAP/level position, pass/fail/stale/missing conditions, IBKR exposure, data-source health, manifest, and HTML/Markdown rendering.
  - Runtime refresh subprocesses must use bounded timeouts and report timeout warnings instead of blocking an updater iteration indefinitely.
  - Polygon health checks must use a reusable `requests.Session` plus short TTL caching. Do not use `urllib.urlopen` for intraday health or runtime data paths.
  - Runtime price, VWAP, and volume-ratio facts should use Polygon 1-minute aggregates first, with source/timestamp/staleness metadata exposed in the manifest.
  - If Polygon minute bars are unavailable for a symbol/date, fall back to yfinance/local values and disclose `yfinance_fallback_active: true` plus warnings.
  - Stage 0 may be regenerated intraday only after an explicit Brain/user market-context reset.
  - Stage 1 may be regenerated intraday only after an explicit Brain/user plan or permission-state change.

---

### 1.5 Intraday Monitor Snapshot
Acquires real-time pricing and stop proximity for display or safety diagnostics.

* **Command**:
  ```powershell
  python -m stock_team.cli intraday-snapshot --symbols <symbols_csv> --out <output_md> [--refresh]
  ```

---

### 1.6 Company Packet
Extracts fundamental statements, capex/debt profiles, and corporate news cataloging.

* **Command**:
  ```powershell
  python -m stock_team.cli company-packet --symbol SYMBOL [--peers SYMBOLS] --out <output_md>
  ```

---

## 2. Evidence Packet Standard Header

All output files generated under `--out` must begin with the following YAML header block:

```yaml
---
packet_type: <packet_type_enum>
status: verified
generated_at: <utc_iso_timestamp>
source_system: stock_team
requested_by: Codex/User
command: python -m stock_team.cli <command_name>
inputs:
  date: "YYYY-MM-DD"
  <additional_command_inputs>
data_sources:
  - polygon
  - local_cache
missing_data:
  - <warning_or_missing_source_note>
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - psychological_interpretation
  - final_thesis_adoption
  - permission_state_change
---
```
