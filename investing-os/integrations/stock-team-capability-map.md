# Stock Team Capability Map

## Purpose

Clarify how `stock_team` / `lianghua` can help `investing-os` beyond wiki import.

The 20 imported files were cognition assets.

They are not the full value of `stock_team`.

`stock_team` also contains tooling capabilities:

- company research generation
- industry research generation
- pre-market planning
- post-market review
- dashboards and reports
- data collection
- portfolio snapshots
- candidate scanning
- backtesting
- runtime monitoring

These capabilities should remain in `stock_team` and connect to `investing-os` through stable artifacts.

## Core Boundary

```text
investing-os
  owns WHY, principles, framework, templates, wiki, review logic

stock_team / lianghua
  owns data collection, computation, report generation, dashboards, runtime tools
```

## Integration Rule

`stock_team` output should enter `investing-os` through packet contracts before it becomes durable knowledge or a plan.

Packet contracts live in:

- `system/data/packets/company-research-packet.md`
- `system/data/packets/industry-research-packet.md`
- `system/data/packets/pre-market-packet.md`
- `system/data/packets/post-market-packet.md`
- `system/data/packets/runtime-monitor-packet.md`

This keeps generated reports, dashboards, and runtime state separate from durable cognition.

## Why Only 20 Files Were Imported

Phase 2 imported only the high-confidence cognition assets:

- principles
- cases
- AI governance notes
- system/workflow notes
- selected industry research

The remaining files were not useless.

They were different asset types:

- code
- runtime config
- generated output
- dashboards
- reports
- caches
- legacy artifacts

Those should not be dumped into `wiki/`.

They need capability mapping and selective output ingestion.

## Capability Groups

### 1. Company Research

Likely `stock_team` files:

- `agents/report_agent.py`
- `agents/research_ingest.py`
- `agents/company_profile_fetcher.py`
- `agents/fundamentals_tracker.py`
- `agents/quick_fundamentals.py`
- `reports/research_*.md`
- `reports/research_*.html`

`stock_team` can provide:

- company profile data
- generated research drafts
- financial and narrative summaries
- evidence packets
- report pages

`investing-os` should absorb only:

- durable company dossiers
- thesis updates
- falsification points
- open questions
- methodology improvements

Destination:

- `wiki/companies/`
- `templates/company-research.md`
- `templates/thesis.md`
- `templates/falsification.md`

### 2. Industry Research

Likely `stock_team` files:

- `findings/*.md`
- `reports/research_*.md`
- `agents/sector_agent.py`
- `agents/sector_leadership.py`
- `agents/macro_agent.py`
- `agents/tech_agent.py`
- `agents/fund_agent.py`

`stock_team` can provide:

- sector maps
- peer comparisons
- macro and sector context
- generated industry reports
- candidate lists

`investing-os` should absorb only:

- durable industry notes
- value-capture maps
- risk and falsification lists
- monitoring checklists

Destination:

- `wiki/industries/`
- `wiki/methodologies/`

### 3. Pre-Market Planning

Likely `stock_team` files:

- `agents/premarket.py`
- `agents/premarket_summary.py`
- `agents/premarket_checklist.py`
- `agents/premarket_decision.py`
- `agents/premarket_exit_sheet.py`
- `agents/premarket_order_sheet.py`
- `agents/premarket_watchlist_score.py`
- `scripts/fetch_premarket.py`
- `scripts/render_premarket_board.py`
- `reports/premarket_trading_board_*.html`

`stock_team` can provide:

- market context
- watchlist scoring
- holding risk notes
- candidate tables
- pre-market dashboard

`investing-os` should use it to fill:

- `templates/trading-day-plan.md`
- `templates/pre-market-plan.md`
- `system/workflows/trading-day.md`

Rules:

- no plan means no discretionary execution
- signals become review items unless already covered by a written plan
- dashboard output is not a command

### 4. Post-Market Review

Likely `stock_team` files:

- `agents/postmarket_data_collector.py`
- `agents/postmarket_decision_audit.py`
- `agents/postmarket_master_eval.py`
- `agents/postmarket_review.py`
- `agents/postmarket_summary.py`
- `agents/postmarket_trade_review.py`
- `reports/postmarket_sandbox_*.html`

`stock_team` can provide:

- intraday data
- OHLC / VWAP
- peer and QQQ comparison
- execution audit
- trade review drafts

`investing-os` should absorb:

- journal entries
- principle updates
- case updates
- checklist updates
- wiki updates

Destination:

- `wiki/journals/`
- `wiki/historical-cases/`
- `wiki/principles/`
- `system/checks/`

### 5. Runtime Monitoring

Likely `stock_team` files:

- `agents/poll.py`
- `agents/poll_state.py`
- `agents/session_manager.py`
- `agents/entry_guard.py`
- `agents/decision_state_hub.py`
- `agents/intraday_snapshot.py`

`stock_team` can provide:

- alerts
- state transitions
- intraday monitoring
- risk warnings

`investing-os` provides:

- runtime snapshot schema
- principles
- degraded-mode rules
- signal-to-action constraints

Boundary:

- runtime can read validated snapshots
- runtime must not read raw wiki files
- runtime must not generate new discretionary orders without a written plan

### 6. Backtesting And Parameter Review

Likely `stock_team` files:

- `agents/backtest_engine.py`
- `agents/backtest_macro.py`
- `agents/backtest_micro.py`
- `agents/backtest_runner.py`
- `scripts/random_search_v2.py`
- `scripts/factor_ic_analyzer.py`
- `scripts/monte_carlo_bootstrap.py`
- `config/best_weekly_params.json`

`stock_team` can provide:

- parameter testing
- factor review
- stress tests
- historical evidence

`investing-os` should absorb:

- parameter evidence
- falsification evidence
- methodology updates

Boundary:

- backtests can validate tactical parameters
- backtests cannot rewrite principles by themselves
- behavioral guardrails should not be optimized only for return

## Artifact Flow

### Company Or Industry Research

```text
stock_team generated report
|
investing-os import-source note
|
WHY alignment
|
wiki company / industry note
|
thesis / falsification / monitoring checklist
```

### Pre-Market

```text
stock_team pre-market board
|
investing-os trading-day plan
|
human decision
|
allowed actions / no-trade conditions
```

### Post-Market

```text
stock_team data and execution audit
|
investing-os journal
|
principle / case / checklist update
|
cognitive upgrade
```

### Runtime Rules

```text
investing-os principles
|
runtime snapshot
|
stock_team read-only consumption
|
alerts / warnings / review tasks
```

## 1000+ Files Problem

The problem is not that the files are useless.

The problem is that they are mixed together:

- durable knowledge
- generated reports
- code
- runtime config
- cache
- dashboard output
- legacy experiments
- sensitive state

This makes direct import dangerous.

The correct next step is not "import everything".

The correct next step is:

1. capability map
2. output contract
3. selective ingestion
4. runtime snapshot boundary
5. Antigravity code map

## Next Needed Artifact From Antigravity

Antigravity should produce a `stock_team` capability report:

- company research pipeline
- industry research pipeline
- pre-market pipeline
- post-market pipeline
- runtime monitoring pipeline
- backtesting pipeline
- input files
- output files
- generated artifacts
- sensitive files
- tests

Codex can then map those outputs into `investing-os` workflows without touching `stock_team` code.

## Current Capability Report

See:

- `handoff/stock-team-capability-report.md`
