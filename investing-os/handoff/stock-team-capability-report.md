# Stock Team Capability Report

Date: 2026-06-05  
Prepared by: Codex  
Mode: read-only inspection of `D:\gemini\lianghua\stock_team`

## Purpose

This report maps `stock_team` capabilities so they can support `investing-os` without dumping code, generated files, or runtime state into the wiki.

The earlier 20-file import covered high-confidence cognition assets.

This report covers the broader tooling layer.

## Core Finding

`stock_team` is not only a source of wiki material.

It is a production toolbox for:

- company research
- industry research
- pre-market planning
- post-market review
- dashboards and reports
- runtime monitoring
- backtesting and parameter review
- portfolio and risk snapshots

These capabilities should remain in `stock_team`.

`investing-os` should consume selected outputs after interpretation.

## Capability Map

### 1. Company Research Pipeline

Likely modules:

- `agents/report_agent.py`
- `agents/report_viewer.py`
- `agents/research_ingest.py`
- `agents/company_profile_fetcher.py`
- `agents/fundamentals_tracker.py`
- `agents/quick_fundamentals.py`
- `agents/strategic_memo_writer.py`
- domain agents: `tech_agent.py`, `fund_agent.py`, `macro_agent.py`, `risk_agent.py`, `sentiment_agent.py`, `sector_agent.py`

Observed outputs:

- `findings/company_profile_{SYM}.json`
- `findings/fundamentals_{SYM}.json`
- `findings/{Agent}_{SYM}_{date}.json`
- `findings/debate_{SYM}_{date}.jsonl`
- `reports/research_{SYM}.html`
- `reports/research_{SYM}_{date}.md`
- dated HTML reports such as `reports/2026-05-26_COHR.html`

Current inventory signal:

- `reports` contains many `research_*` files.
- Existing report count observed: 77 `research_*` report files.

How it should connect to `investing-os`:

```text
stock_team generated company report
|
investing-os import-source note
|
company dossier / thesis / falsification
|
wiki/companies/
```

Do not import raw generated report folders wholesale.

### 2. Industry Research Pipeline

Likely modules:

- `agents/sector_agent.py`
- `agents/sector_leadership.py`
- `agents/macro_agent.py`
- `agents/tech_agent.py`
- `agents/fund_agent.py`
- `agents/strategic_memo_writer.py`

Observed outputs:

- `findings/*industry*.md`
- `findings/*sector*.json`
- `reports/research_*`
- research packages under `research_package/` and `scratch/AI_research_package/`

How it should connect to `investing-os`:

```text
stock_team industry packet
|
WHY alignment
|
value-capture map / risks / monitoring checklist
|
wiki/industries/
```

The durable output should be a structured industry note, not a generated report dump.

### 3. Pre-Market Planning Pipeline

Likely modules:

- `agents/premarket.py`
- `agents/premarket_summary.py`
- `agents/premarket_checklist.py`
- `agents/premarket_consensus_lock.py`
- `agents/premarket_decision.py`
- `agents/premarket_exit_sheet.py`
- `agents/premarket_order_sheet.py`
- `agents/premarket_watchlist_score.py`
- `agents/daily_plan.py`
- `agents/daily_plan_writer.py`
- `scripts/fetch_premarket.py`
- `scripts/render_premarket_board.py`

Observed outputs:

- `findings/premarket_summary_{date}_{SYM}.json`
- `findings/order_sheet_{date}.json`
- `findings/entry_decision_{date}.json`
- `findings/exit_decision_{date}.json`
- `daily_plan_{date}.json`
- `reports/premarket_trading_board_{date}.html`

How it should connect to `investing-os`:

```text
stock_team pre-market board / JSONs
|
templates/trading-day-plan.md
|
human allowed actions / no-trade conditions
```

Boundary:

- pre-market output can inform a plan
- pre-market output is not itself permission to trade
- if data is missing, no action-oriented conclusion

### 4. Post-Market Review Pipeline

Likely modules:

- `agents/postmarket_data_collector.py`
- `agents/postmarket_decision_audit.py`
- `agents/postmarket_master_eval.py`
- `agents/postmarket_review.py`
- `agents/postmarket_sandbox.py`
- `agents/postmarket_summary.py`
- `agents/postmarket_trade_review.py`

Observed outputs:

- `findings/postmarket_summary_{date}_{SYM}.json`
- `findings/postmarket_summary_{date}.json`
- `reports/postmarket_sandbox_{date}.html`

Observed report count:

- `reports` contains 5 `postmarket_*` report files.

How it should connect to `investing-os`:

```text
stock_team post-market summary / audit
|
wiki/journals/
|
principle / case / checklist updates
```

Boundary:

- post-market tools provide evidence
- `investing-os` decides what becomes durable cognition

### 5. Runtime Monitoring Pipeline

Likely modules:

- `agents/poll.py`
- `agents/poll_state.py`
- `agents/session_manager.py`
- `agents/session_recorder.py`
- `agents/intraday_snapshot.py`
- `agents/entry_guard.py`
- `agents/decision_state_hub.py`

Observed behavior:

- intraday polling
- snapshot recording
- alert pushing
- optional session-manager integration
- paper-trader / entry guard paths

Observed outputs:

- `findings/intraday_snapshot_{date}_{SYM}.jsonl`
- `session_state_{date}.json`
- `session_events_{date}.jsonl`
- decision-state files

How it should connect to `investing-os`:

```text
investing-os runtime snapshot
|
stock_team read-only runtime consumption
|
alerts / warnings / review tasks
```

Boundary:

- no direct reading of raw wiki files at runtime
- no new discretionary orders when daily plan is missing
- writes must go through code-level guards

### 6. Backtesting And Parameter Review Pipeline

Likely modules:

- `agents/backtest_engine.py`
- `agents/backtest_macro.py`
- `agents/backtest_micro.py`
- `agents/backtest_result.py`
- `agents/backtest_runner.py`
- `scripts/random_search_v2.py`
- `scripts/run_parameter_sweep.py`
- `scripts/weekly_engine_parameter_sweep.py`
- `scripts/weekly_oos_validator.py`
- `scripts/walk_forward_analysis.py`
- `scripts/monte_carlo_bootstrap.py`
- `scripts/factor_ic_analyzer.py`

Observed outputs:

- `findings/backtest_report_{date}.json`
- `findings/backtest_result_{date}.json`
- `findings/backtest_log.jsonl`
- `findings/backtest_trades_{SYM}.json`
- `findings/signal_thresholds_optimized.json`
- `findings/best_search_params.json`

How it should connect to `investing-os`:

```text
backtest / parameter evidence
|
runtime-parameter-map.md
|
snapshot parameter status update
```

Boundary:

- backtests can validate tactical parameters
- backtests cannot rewrite durable principles by themselves
- behavioral guardrails should not be optimized only for return

### 7. Dashboard And Report Surface

Likely modules:

- `agents/dashboard_writer.py`
- `agents/dashboard_server.py`
- `agents/dashboard_cache.py`
- `agents/dashboard_experience_loop.py`
- `agents/generate_report_index.py`
- `agents/generate_watchlist_ui.py`
- `agents/report_viewer.py`

Observed outputs:

- `reports/index.html`
- `reports/daily_dashboard_{date}.html`
- `reports/premarket_trading_board_{date}.html`
- `reports/postmarket_sandbox_{date}.html`
- `reports/research_*.html`

How it should connect to `investing-os`:

Dashboards are working surfaces, not durable knowledge.

Only insights from dashboards should enter:

- `wiki/journals/`
- `wiki/companies/`
- `wiki/industries/`
- `system/checks/`

## Runtime Config Map

Current config files observed:

- `best_weekly_params.json`
- `daily_focus.json`
- `decision_thresholds.json`
- `leveraged_pairs.json`
- `macro_background.json`
- `macro_strategy_params.json`
- `market_regime.json`
- `market_relationships.json`
- `master_watchlist.json`
- `micro_strategy_params.json`
- `poll_config.json`
- `portfolio_macro_guard.json`
- `positions.json`
- `positions_mode.json`
- `sector_registry.json`
- `sector_watchlist.json`
- `server_port.json`
- `tactical_rules.json`
- `target_orders_rebalance.json`
- `today_focus.json`

Suggested classification:

### Account / Position State

- `positions.json`
- `positions_mode.json`
- `target_orders_rebalance.json`

Handle with extra care.

Do not import into `investing-os` wiki.

### Watchlist / Focus

- `master_watchlist.json`
- `sector_watchlist.json`
- `daily_focus.json`
- `today_focus.json`

Potential `investing-os` use:

- trading-day plan
- weekly watchlist review

### Tactical Parameters

- `decision_thresholds.json`
- `macro_strategy_params.json`
- `micro_strategy_params.json`
- `tactical_rules.json`
- `best_weekly_params.json`

Potential `investing-os` use:

- runtime parameter map
- tactical rule snapshot

### Market / Sector Context

- `market_regime.json`
- `market_relationships.json`
- `macro_background.json`
- `sector_registry.json`

Potential `investing-os` use:

- industry map
- pre-market context

### App / Server Config

- `poll_config.json`
- `server_port.json`

Keep in `stock_team`.

## Tests Observed

`tests/` contains coverage for major capability groups:

- pre-market: `test_premarket_*`
- post-market: `test_postmarket_summary.py`
- research/report: `test_report_agent.py`, `test_research_ingest.py`, `test_research_report.py`
- dashboard: `test_dashboard_*`
- agents: `test_tech_agent.py`, `test_fund_agent.py`, `test_risk_agent.py`, `test_sentiment_agent.py`, `test_strategy_agent.py`
- backtest: `test_backtest_*`
- session/runtime: `test_session_manager.py`, `test_poll_*`

This means `stock_team` has enough existing structure to be treated as a tool platform, not just a pile of files.

## Recommended Output Contracts

### Company Research Packet

Minimum fields:

- symbol
- generated_at
- source_files
- business_summary
- revenue_structure
- moat
- valuation_notes
- risk
- falsification
- open_questions
- confidence / uncertainty

`investing-os` destination:

- `wiki/companies/{symbol}.md`

### Industry Research Packet

Minimum fields:

- industry
- generated_at
- source_files
- value_chain
- value_capture
- key_companies
- risks
- falsification
- monitoring_checklist

`investing-os` destination:

- `wiki/industries/{industry}.md`

### Pre-Market Packet

Minimum fields:

- date
- market_context
- holdings
- watchlist
- allowed_actions
- forbidden_actions
- risk_alerts
- missing_data

`investing-os` destination:

- `templates/trading-day-plan.md`

### Post-Market Packet

Minimum fields:

- date
- actions
- execution_audit
- thesis_changes
- risk_changes
- emotion_flags
- suggested_journal_updates
- suggested_system_updates

`investing-os` destination:

- `wiki/journals/`

### Runtime Monitor Packet

Minimum fields:

- timestamp
- symbol
- alert_type
- facts
- linked_plan
- linked_rule
- allowed_actions
- forbidden_actions
- review_required

`investing-os` destination:

- review queue / journal, not direct trade action

## Immediate Next Step For Codex

Completed: packet contracts were created in `investing-os/system/data/packets/`:

- `company-research-packet.md`
- `industry-research-packet.md`
- `pre-market-packet.md`
- `post-market-packet.md`
- `runtime-monitor-packet.md`

These contracts define how `stock_team` output can enter `investing-os` without dumping generated reports, code, or runtime state into the wiki.

## Future Next Step For Antigravity

When resumed, Antigravity should map each `stock_team` pipeline to:

- command entry point
- input files
- output files
- tests
- generated artifacts
- sensitive files
- failure modes

Antigravity should not modify `investing-os` while doing that.
