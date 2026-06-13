# Stock Team Call Log

> [!NOTE]
> *Temporarily modified by Antigravity; pending validation by Codex.*

> [!WARNING]
> Codex validation note, 2026-06-06: the `ibkr_sync` and `intraday_monitor` entries below are treated as unapproved direct muscle/runtime experiments unless separately re-authorized through an `investing-os` workflow. They are kept as factual records, not as approved operating precedent.

This log records every `stock_team` call made from an `investing-os` workflow.

The purpose is verification. The user should be able to see whether evidence was actually requested, what command was used, what output was produced, and how it was used.

## Entry Template

```yaml
date: YYYY-MM-DD
requested_by: user / scheduler / Codex
use_case: trade_review / company_research / intraday_monitor / ibkr_sync
purpose: Brief description of the command goal
stock_team_command: Exact CLI command executed
working_directory: Base path where command ran
inputs:
  symbols: [LIST_OF_SYMBOLS]
  params: {additional options}
output_artifact: Path to generated output packet
status: success / failed / offline_fallback
data_sources:
  - Source API (e.g. IBKR TWS local socket, yfinance, Polygon)
missing_data:
  - Any data fields requested but not found/fetched
used_in:
  - Related workflow files or decisions
notes: Important observations
```

## Entries

```yaml
date: 2026-06-06
requested_by: user / scheduler
use_case: intraday_monitor
purpose: Start the local low-bandwidth TWS monitor for watchlist and position symbols
stock_team_command: python agents/ibkr_monitor.py
working_directory: D:/gemini/lianghua/stock_team
inputs:
  symbols: [MSFT, NVDA, GOOGL, COHR, ORCL, INTC, SNXX, CRDU, NOW, INTW, VST, ASPI]
output_artifact: C:/Users/rriww/Documents/investing-os/system/data/packets/intraday_snapshot.json
status: success
data_sources:
  - IBKR Gateway local socket (localhost:4001)
  - C:/Users/rriww/Documents/investing-os/decision/current-watchlist.md (source of symbols)
missing_data: []
used_in:
  - C:/Users/rriww/Documents/investing-os/system/workflows/intraday.md
notes: Initialized connection successfully on port 4001. Consumed 0 internet bandwidth. Cached fallback prices loaded for weekend data.
codex_validation: unapproved_runtime_experiment_do_not_treat_as_standard_flow
```

```yaml
date: 2026-06-06
requested_by: user
use_case: ibkr_sync
purpose: Verify API connectivity to the local Interactive Brokers client and fetch account details
stock_team_command: python agents/ibkr_test_connection.py
working_directory: D:/gemini/lianghua/stock_team
inputs:
  symbols: []
output_artifact: console_stdout
status: success
data_sources:
  - IBKR Gateway local socket (localhost:4001)
missing_data: []
used_in:
  - C:/Users/rriww/Documents/investing-os/system/workflows/intraday.md
notes: Verified connection to Live Gateway on port 4001.
codex_validation: unapproved_runtime_experiment_do_not_treat_as_standard_flow
```

```yaml
date: 2026-06-05
requested_by: user / Codex
use_case: trade_review
purpose: Retrieve SNXX/SNDK/QQQ/SPY 1-minute context for 2026-06-04 SNXX review.
stock_team_command: inline read-only Python using Polygon API key from stock_team/.env
working_directory: C:/Users/rriww/Documents/investing-os
inputs:
  symbols: [SNXX, SNDK, QQQ, SPY]
  date: 2026-06-04
  fills_source: user-provided broker screenshots
output_artifact: wiki/journals/2026-06-04-snxx-contextual-review.md
status: success
data_sources:
  - stock_team/.env POLYGON_API_KEY
  - Polygon 1-minute aggregates API
missing_data:
  - VIX intraday context not queried in first pass
  - SNDK catalyst/news not verified
used_in:
  - wiki/journals/2026-06-04-snxx-contextual-review.md
  - wiki/historical-cases/CASE-004-snxx-attention-capture.md
notes: API key was read from stock_team only and not stored in investing-os.
```

```yaml
date: 2026-06-05
requested_by: user / Codex
use_case: company_research
purpose: Retrieve COHR/LITE/AAOI/SOXX/QQQ recent daily aggregate context for COHR company research packet.
stock_team_command: inline read-only Node.js using Polygon API key from stock_team/.env
working_directory: C:/Users/rriww/Documents/STOCK
inputs:
  symbols: [COHR, LITE, AAOI, SOXX, QQQ]
  date_range: 2026-05-20 to 2026-06-04
output_artifact: system/data/packets/drafts/company-research-COHR-2026-06-05.md
status: success
data_sources:
  - stock_team/.env POLYGON_API_KEY
  - Polygon daily aggregates API
missing_data:
  - refreshed valuation data beyond stock_team 2026-05-26 profile
  - complete peer financial comparison
used_in:
  - system/data/packets/drafts/company-research-COHR-2026-06-05.md
  - wiki/sources/packet-review-COHR-2026-06-05.md
notes: API key was read from stock_team only and not stored in investing-os.
```

```yaml
date: 2026-06-05
requested_by: user / Codex
use_case: exit_review
purpose: Retrieve COHR/ORCL/INTC/QQQ/SPY 1-minute and after-hours context for 2026-06-04 swing exit review.
stock_team_command: inline read-only Node.js using Polygon API key from stock_team/.env
working_directory: C:/Users/rriww/Documents/STOCK
inputs:
  symbols: [COHR, ORCL, INTC, QQQ, SPY]
  date: 2026-06-04
  fills_source: user-provided broker screenshots
output_artifact: wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md
status: success
data_sources:
  - stock_team/.env POLYGON_API_KEY
  - Polygon 1-minute aggregates API
missing_data:
  - complete original thesis for each swing position
  - full cost-basis history
  - ORCL 19:59 after-hours bar was not present in returned summary
used_in:
  - wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md
  - decision/decision-log.md
  - decision/current-watchlist.md
  - decision/falsification-map.md
  - execution/post-market.md
notes: API key was read from stock_team only and not stored in investing-os.
```
