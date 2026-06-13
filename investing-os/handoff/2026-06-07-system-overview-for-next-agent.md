# 2026-06-07 System Overview for Next Agent

Purpose: help the next Codex / ChatGPT / Antigravity session understand the cognition system, stock_team, workflow, dashboard, and current boundaries.

## 1. System Meaning

This project is not an auto-trading bot.

It is:

```text
Personal Cognition
x AI Amplifier
x Discipline Execution System
```

The central goal is cognitive evolution. Returns are a byproduct.

The user's role:

- define worldview
- do research
- make final judgment
- bear final risk
- decide whether a lesson becomes part of the system

AI / agents:

- gather information
- calculate evidence
- organize reports
- check discipline
- surface missing data
- help review mistakes

They do not replace the user's cognition.

## 2. Two-System Architecture

### Brain: investing-os

Path:

```text
C:\Users\rriww\Documents\investing-os
```

Role:

- owns WHY
- owns cognition
- owns decision framework
- owns trading permission
- owns tactic status
- owns lesson absorption
- owns dashboard / operating console as user entry

### Muscle: stock_team

Path:

```text
D:\gemini\lianghua\stock_team
```

Role:

- evidence engine
- Polygon / IBKR / cache integration
- calculation engine
- backtest runner
- packet producer
- evidence dashboard producer

It must not:

- give buy / sell / hold recommendations
- approve trading permission
- adopt thesis
- update principles
- interpret psychology
- mutate investing-os decisions
- create a competing user workflow

## 3. Core investing-os Structure

Important directories:

```text
cognition/       personal patterns, errors, bias map, self model
decision/        tactics, factor library, risk budget, portfolio thesis
execution/       pre-market, intraday, post-market operating loops
evolution/       promotion rules, learning loop, system update log
system/          workflows, packets, contracts, checks, architecture
templates/       repeatable report and packet formats
handoff/         agent handoffs and session records
dashboards/      visual operating surfaces
```

Meaning:

- `cognition/` represents the user's self-knowledge.
- `decision/` represents how cognition becomes rules, tactics, and risk.
- `execution/` represents how daily market work is performed.
- `evolution/` represents how experience changes the system.
- `system/` represents contracts, workflow wiring, and machine-readable surfaces.

## 4. Core stock_team Structure

Read:

```text
D:\gemini\lianghua\stock_team\docs\ACTIVE_WORKSPACE.md
```

Active directories:

```text
backtest/        tactic backtest and future adapters
core/            trade evidence, IBKR, poll, premarket helpers
data_ingest/     Polygon / data acquisition / postmarket collection
config/          request examples and runtime config
docs/            contracts and workspace guidance
templates/       dashboard / report templates
tests/unit/core/ active tests for current contracts
reports/         current dashboard files only
findings/        current active packet outputs only
```

Old generated artifacts were moved to:

```text
D:\gemini\lianghua\stock_team\archive\cleanup_2026-06-07
```

Do not build new work from old `agents/*`, old root scripts, or old archived reports unless explicitly restoring historical context.

## 5. Daily Workflow

### Stage 0: Pre-Market Context

User / investing-os first decides the universe:

- current holdings
- analyzed watchlist
- researched themes
- symbols worth checking

stock_team then produces market context:

- QQQ / SPY / IWM / VIX proxy state
- sector / theme heat
- recent returns
- volume context
- factual catalysts
- universe input quality

Canonical packet:

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md
```

### Stage 1: Pre-Market Plan Evidence

investing-os and user choose focus pool and define decision sheet.

stock_team calculates:

- returns
- RS
- ATR
- MA20 / MA50 distance
- prior day high / low
- volume
- linked leverage exposure facts
- rule collision facts

Canonical packet:

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.md
```

### Intraday Guidance

investing-os generates the actual intraday guidance:

- current permission state
- allowed actions
- forbidden actions
- symbol role
- tactic permission
- attention budget
- evidence needed

stock_team should later generate an intraday evidence dashboard from this guidance.

Important packet:

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\intraday-dashboard-packet.md
```

### Post-Market / Review

stock_team provides:

- fills
- IBKR position/account facts
- QQQ / VIX / sector / symbol charts
- VWAP
- first 30 minutes behavior
- key nodes
- missed opportunities
- tactic event summaries

investing-os and user discuss:

- what happened
- what was planned
- what was violated
- what was learned
- where lessons should land

Lessons are not auto-promoted. The user confirms absorption.

## 6. Dashboard Meaning

There are two dashboard concepts.

### investing-os Dashboard

Purpose:

- user-facing operating console
- shows cognition system
- shows current permissions
- shows daily entry points
- shows missing evidence
- shows pending lessons
- links to reports
- helps the user see where experience enters the system

Relevant files:

```text
C:\Users\rriww\Documents\investing-os\dashboards\
```

Key idea:

The dashboard is not just a file browser. It should become the trading operation entry.

### stock_team Dashboard

Purpose:

- evidence dashboard
- real-time or near-real-time factual state
- IBKR / Polygon / packet readiness
- data freshness
- monitored symbols and conditions
- no recommendations

Active files:

```text
D:\gemini\lianghua\stock_team\reports\dashboard.html
D:\gemini\lianghua\stock_team\reports\index.html
D:\gemini\lianghua\stock_team\reports\latest_evidence_dashboard.json
```

Relationship:

- investing-os dashboard links to latest stock_team dashboard.
- stock_team dashboard does not replace investing-os.
- stock_team dashboard answers: what facts are available now?
- investing-os answers: what do these facts mean under my system?

## 7. Backtest System Current State

Read:

```text
C:\Users\rriww\Documents\investing-os\handoff\2026-06-07-backtest-system-session-record.md
D:\gemini\lianghua\stock_team\docs\tactic-backtest-contract.md
```

Current command:

```powershell
python -m stock_team.cli tactic-backtest --request "<request json>" --out "<packet md>" --json-out "<summary json>"
```

Current modes:

- `fixture_events`
- `intraday_ohlcv_fixture`

Current demo tactic:

```text
rs_pullback_rebound_intraday
```

Demo request:

```text
D:\gemini\lianghua\stock_team\config\tactic_backtest_rs_intraday_demo_v1.json
```

Demo output:

```text
D:\gemini\lianghua\stock_team\findings\tactic_backtest_rs_intraday_demo_v1.md
D:\gemini\lianghua\stock_team\findings\tactic_backtest_rs_intraday_demo_v1.json
```

Next step:

- add Polygon-first historical 1m / 5m adapter
- convert Polygon bars into normalized OHLCV
- reuse the same event generator
- do real historical validation

## 8. Lessons and Absorption

Experience should flow like this:

```text
trade / research
-> evidence packet
-> user review
-> candidate lesson
-> recommended landing file
-> user confirms
-> system update
```

Important:

- do not auto-promote lessons to personal cognition
- present candidate lessons first
- show source report / date
- record lineage

Relevant areas:

```text
C:\Users\rriww\Documents\investing-os\system\traceability\
C:\Users\rriww\Documents\investing-os\evolution\
C:\Users\rriww\Documents\investing-os\cognition\
C:\Users\rriww\Documents\investing-os\decision\
```

## 9. Key Files to Read First

For architecture:

- `C:\Users\rriww\Documents\investing-os\system\closed-loop-operating-architecture.md`
- `C:\Users\rriww\Documents\investing-os\system\architecture.md`
- `C:\Users\rriww\Documents\investing-os\system\workflows\brain-muscle-handshake-protocol.md`
- `C:\Users\rriww\Documents\investing-os\system\workflows\stock-team-orchestration.md`

For workflow:

- `C:\Users\rriww\Documents\investing-os\system\workflows\command-router.md`
- `C:\Users\rriww\Documents\investing-os\system\workflows\trading-day.md`
- `C:\Users\rriww\Documents\investing-os\system\workflows\intraday.md`
- `C:\Users\rriww\Documents\investing-os\system\workflows\post-market-trade-review.md`

For cognition:

- `C:\Users\rriww\Documents\investing-os\cognition\self-model.md`
- `C:\Users\rriww\Documents\investing-os\cognition\mistake-patterns.md`
- `C:\Users\rriww\Documents\investing-os\cognition\emotional-patterns.md`
- `C:\Users\rriww\Documents\investing-os\cognition\bias-map.md`

For decisions:

- `C:\Users\rriww\Documents\investing-os\decision\factors\factor-library.md`
- `C:\Users\rriww\Documents\investing-os\decision\tactics\rs-pullback-rebound-intraday.md`
- `C:\Users\rriww\Documents\investing-os\decision\tactics\validation-records\rs-pullback-rebound-intraday.md`
- `C:\Users\rriww\Documents\investing-os\decision\risk-budget.md`

For stock_team:

- `D:\gemini\lianghua\stock_team\docs\ACTIVE_WORKSPACE.md`
- `D:\gemini\lianghua\stock_team\docs\tactic-backtest-contract.md`
- `D:\gemini\lianghua\stock_team\cli.py`
- `D:\gemini\lianghua\stock_team\backtest\tactic_backtest_system.py`
- `D:\gemini\lianghua\stock_team\tests\unit\core\test_tactic_backtest_system.py`

## 10. Operating Rules for Next Agent

- Start from investing-os unless the task explicitly says to work inside stock_team.
- Do not let stock_team become a second brain.
- Do not let dashboards produce decisions.
- Do not absorb lessons without user confirmation.
- Do not delete archived files unless user explicitly asks.
- When touching investing-os, run:

```powershell
C:\Users\rriww\Documents\investing-os\tools\check-file-growth.ps1
```

- When touching tactic-backtest, run:

```powershell
python -m pytest tests\unit\core\test_tactic_backtest_system.py tests\unit\core\test_cli.py::test_cli_tactic_backtest_generation tests\unit\core\test_cli.py::test_cli_tactic_backtest_ohlcv_fixture_generation tests\unit\core\test_cli.py::test_cli_help -q
```

## 11. Current Final Interpretation

The project is now structurally coherent:

- investing-os is the cognition and decision operating system
- stock_team is the evidence engine
- dashboard is becoming the user-facing operating console
- backtest system is the validation bridge between tactic hypothesis and trading permission

The next big milestone is real data:

```text
Polygon historical bars -> tactic backtest -> evidence packet -> investing-os validation record
```

Do that next before approving or using the short-term tactic live.
