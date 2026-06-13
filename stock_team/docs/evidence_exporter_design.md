# Contextual Trade Evidence Exporter Technical Design & Packet Map

**Date**: 2026-06-05  
**Owner**: Antigravity  
**Target Repository**: `D:\gemini\lianghua\stock_team`  

This document defines the technical design for the `stock_team` contextual trade evidence exporter and maps the existing multi-agent quant pipelines to `investing-os` output packets.

---

## 1. Packet Producer Map (Task 2)

We map the existing `stock_team` codebases and outputs to the unified packet templates in `investing-os/system/data/packets/`:

| Pipeline / Feature | Candidate Module (stock_team) | Input Files | Output File | OS Target Packet | Command Entry Point |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pre-Market Plan** | `agents/premarket_summary.py` | `premarket_analysis_{date}.json`<br>`daily_plan_{date}.json` | `findings/pre-market-packet-{date}.md` | `pre-market-packet.md` | `python agents/premarket_summary.py --date {date}` |
| **Post-Market Review** | `agents/postmarket_trade_review.py` | `findings/postmarket_trade_review_{date}.json` | `findings/post-market-packet-{date}.md` | `post-market-packet.md` | `python agents/postmarket_trade_review.py --date {date}` |
| **Company Research** | `agents/company_profile_fetcher.py`<br>`agents/cio.py` | `knowledge/company_profiles.json` | `findings/company-research-packet-{SYM}.md` | `company-research-packet.md` | `python agents/cio.py --symbol {SYM}` |
| **Sector/Industry** | `agents/sector_agent.py` | `findings/AI_GPU_compute_industry_{date}.md` | `findings/industry-research-packet-{sector}.md` | `industry-research-packet.md` | `python agents/sector_agent.py --sector {sector}` |
| **Runtime Alerts** | `agents/poll.py` | `findings/watchlist_live_status.json`<br>`config/tactical_rules.json` | `findings/runtime-monitor-packet-{date}.md` | `runtime-monitor-packet.md` | `python agents/poll.py` |
| **Trade Evidence** | `scripts/export_trade_evidence.py` | Fills Markdown/JSON<br>Polygon.io 1m aggregate bars | `findings/contextual-trade-evidence-{SYM}-{date}.md` | `contextual-trade-evidence-packet.md` | `python scripts/export_trade_evidence.py --symbol {SYM} --date {date} --fills {path}` |

---

## 2. Evidence Exporter CLI Specification

The exporter will be implemented as a command-line script at `D:\gemini\lianghua\stock_team\scripts\export_trade_evidence.py` with the following parameters:

```bash
python scripts/export_trade_evidence.py \
  --symbol <SYMBOL> \
  --date <YYYY-MM-DD> \
  --fills <path_to_fills_file> \
  [--peers <SYM1,SYM2>] \
  [--benchmarks <SYM1,SYM2>] \
  [--output <path_to_output_file>]
```

### Argument Specifications
*   `--symbol` (Required): The ticker symbol traded (e.g. `SNXX`).
*   `--date` (Required): The trade date in New York timezone (e.g. `2026-06-04`).
*   `--fills` (Required): Path to a markdown journal file or JSON containing the fill table. The script will parse the table.
*   `--peers` (Optional): Comma-separated list of peer tickers (e.g. `SNDK`).
*   `--benchmarks` (Optional): Comma-separated list of benchmark indexes (default: `QQQ,SPY`).
*   `--output` (Optional): The destination file to write the packet. Defaults to `findings/contextual-trade-evidence-{symbol}-{date}.md`.

---

## 3. Data Query & Calculations Strategy

### 3.1. Polygon.io Integration
The script will load the `POLYGON_API_KEY` from `stock_team/.env` and fetch 1-minute aggregate bars:
*   **Endpoint**: `https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{date}/{date}?adjusted=true&sort=asc&limit=50000&apiKey={apiKey}`
*   **Response Fields**: `o` (open), `h` (high), `l` (low), `c` (close), `v` (volume), `t` (timestamp in ms).

### 3.2. Timezone Handling
*   Polygon returns UTC timestamps in milliseconds.
*   The New York market hours for `2026-06-04` are `09:30:00 EST` to `16:00:00 EST`.
*   The script will map all timestamps to Eastern Time (ET) for calculating daily high/low times, and present them in ET for market alignment, alongside Shanghai/Beijing local time (CST) to correspond with the user's screenshots.

### 3.3. Key Objective Calculations
1.  **`day_change`**: percentage difference between the close of the last bar (usually 16:00 ET) and the close of the previous trading day.
2.  **`high_time_et`**: the exact minute bar that contains the high of the regular session, formatted as `HH:MM` ET.
3.  **`last_30m_change`**: percentage price change between the close at `15:30` ET and the close at `16:00` ET.
4.  **`intraday_vwap`**: volume-weighted average price up to each bar, calculated as `sum(Close * Volume) / sum(Volume)`.

---

## 4. Call Log Compatibility (Task 4)

To ensure the output integrates with `investing-os/integrations/stock-team-call-log.md`, the exporter will include a metadata block at the top of each generated packet:

```yaml
packet_type: contextual_trade_evidence
status: draft
created_at: 2026-06-05T19:50:00Z
source_system: stock_team
requested_by: Antigravity
symbol: SNXX
trade_date: 2026-06-04
review_id: SNXX-2026-06-04-review
source_files:
  - D:\gemini\lianghua\stock_team\scripts\export_trade_evidence.py
  - C:\Users\rriww\Documents\investing-os\wiki\journals\2026-06-04-snxx-fill-review.md
data_sources:
  - Polygon.io (1-minute aggregates)
missing_data: []
```

---

## 5. Risk and Failure-Mode Review

| Risk Scenario | Detection Mechanism | Fail-Safe Response |
| :--- | :--- | :--- |
| **Invalid/Expired API Key** | HTTP 403 / 401 response from Polygon | Log a clean error: `[ERROR] Invalid POLYGON_API_KEY. Exiting.` Return Exit Code `EXIT_FAIL` (1). Do not generate a corrupted or empty file. |
| **Missing Peer or Benchmark Ticker** | HTTP 404 or empty results list | Warn the user in the logs: `[WARN] No data for benchmark {ticker}. skipping benchmark section.` Generate the packet with a `missing_data` note. |
| **Timestamp Mismatch in Fills** | Time parsed from fills is outside New York trading hours | Check hours. If timestamps are local Shanghai time, convert to ET. If mapping fails, mark `fill_data_quality: warning` in the packet footer. |
| **Rate Limiting** | HTTP 429 response from Polygon | Back off and retry up to 3 times with exponential sleep. If it still fails, fail-safe with `EXIT_FAIL`. |

---

## 6. Test Plan

We will add a unit test suite at `D:\gemini\lianghua\stock_team\tests\unit\core\test_evidence_exporter.py` validating:
1.  **Fills Parsing**: Test parsing table strings from journals.
2.  **Timezone Shifts**: Verify ET to CST conversions.
3.  **Late Session Change Math**: Check percentage calculation between 15:30 and 16:00.
4.  **Evidence Boundary Lock**: Verify no subjective adjectives (e.g., "bad", "FOMO", "should buy") are generated.
