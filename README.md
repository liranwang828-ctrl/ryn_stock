# RYN Stock Team — Multi-Agent Investment Analysis System

A multi-agent AI system that analyzes stocks through the lens of 7 domain-specialist agents and 7 investing persona masters. The agents debate, verify data, and reach consensus via a structured 4-phase CIO workflow. A 6-node session scheduler manages the full trading day from pre-market to post-market review.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SESSION MANAGER (6 nodes)                 │
│  Node1:盘前 → Node2:开盘观察 → Node3:盘中主动 →               │
│  Node4:入场执行 → Node5:持仓管理 → Node6:收盘复盘               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CIO ORCHESTRATOR (4 phases)               │
│  Phase 0: Data → Phase 1: 7 Domain Agents (parallel)        │
│  → Phase 1.5: 7 Persona Masters → Phase 2: Debate           │
│  → Phase 3: Safety Filter + Strategy + Report               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    POLLING ENGINE (A/B dual-track)           │
│  A-track: 2-min auto monitoring (signals/stops/scenarios)    │
│  B-track: User queries & trade commands                      │
└─────────────────────────────────────────────────────────────┘
```

## The 7 Domain Agents

Each agent is a specialist analyzing one dimension of a stock:

| Agent | Domain | Key Outputs |
|-------|--------|-------------|
| **TechAgent** | Technical analysis | MACD, RSI, moving averages, VCP patterns, volume confirmation |
| **FundAgent** | Fundamentals | P/E, P/B, EPS, revenue growth, ROE, debt ratios |
| **MacroAgent** | Macro environment | VIX, yield curve, Fed policy, SPY/QQQ trends, sector rotation |
| **SentimentAgent** | News & analyst sentiment | VADER NLP on news headlines, analyst ratings, price targets |
| **CommunityAgent** | Retail sentiment | Reddit, StockTwits, Xueqiu (雪球) bullish/bearish ratios |
| **RiskAgent** | Risk assessment | Beta, VaR, correlation, stop-loss recommendations, position sizing |
| **SectorAgent** | Sector/peer comparison | Relative strength vs sector ETF, peer ranking, sector momentum |

## The 7 Persona Masters

Each domain agent is supervised by an investing legend who evaluates the data through their personal framework:

| Master | Oversees | Philosophy | Veto Triggers |
|--------|----------|------------|---------------|
| **Mark Minervini** | TechAgent | SEPA momentum, Stage 2 trends, volume confirmation | Not in Stage 2, MA misalignment, low volume |
| **Stan Druckenmiller** | MacroAgent | Liquidity-driven, concentrated bets, macro regime first | Fed tightening, yield curve inversion >3mo, VIX>30 rising |
| **Howard Marks** | SentimentAgent | Contrarian, sentiment pendulum, second-level thinking | Universal bullish consensus, extreme valuations |
| **Nassim Taleb** | RiskAgent | Black swans, antifragility, tail risk, asymmetric payoffs | Beta>2.5, SPY correlation>0.85, debt/equity>2.0 |
| **Jesse Livermore** | (unassigned) | Pure price momentum, strongest market/sector/stock, stop-loss | Trading against trend, no stop-loss set |
| **George Soros** | (unassigned) | Reflexivity, self-reinforcing cycles, falsifiable hypotheses | Reflexivity cycle not formed |
| **Peter Lynch** | (unassigned) | GARP, understandable business, PEG ratio, overlooked small-caps | Business model unclear |

Each master has a full knowledge base: worldview, trading history, blind spots, and language patterns loaded from `personas/<name>/`.

## The CIO Workflow (4 Phases)

### Phase 0 — Data Acquisition
- `data_agent.py` fetches price history, fundamentals, and 47 technical indicators via yfinance (with retry+backoff)
- `verifier_agent.py` checks data freshness, completeness, and cross-source consistency
- Output: `data_verified.json` with verified/unverified field counts

### Phase 1 — Parallel Analysis
All 7 domain agents run simultaneously. Each:
1. Reads verified data
2. Computes domain-specific metrics
3. Produces a finding: signal (bullish/bearish/neutral), confidence (0-100), key points, data references
4. Each finding passes through its assigned persona master for evaluation
5. Masters can **veto** (override to neutral with reason), adjust confidence, or add insights

### Phase 1.5 — Persona Debate
- `debate_engine.py` collects all 7 persona stances
- Detects contradictions between masters (e.g., Minervini bullish vs Taleb bearish)
- Runs targeted responses: each master responds to their natural adversary
- Produces `persona_synthesis.json` with weighted consensus signal and confidence

### Phase 2 — Domain Debate
- Agents challenge each other's findings (structured challenge/revision/endorsement messages)
- Data challenges target specific unverified fields
- VerifierAgent resolves data disputes
- Agents can revise their stance (max 2 revisions each)

### Phase 3 — Strategy & Report
- `safety_filter.py` runs 8 pre-trade safety checks (see below)
- `strategy_agent.py` reads persona synthesis as the final decision
- `report_agent.py` generates terminal + HTML report with full analysis chain

## The 6-Node Session Scheduler

`session_manager.py` orchestrates the full trading day:

| Node | Name | Time | Actions |
|------|------|------|---------|
| 1 | 盘前准备 | 9:00-9:25 | Run premarket analysis, generate daily plan |
| 2 | 开盘观察 | 9:30-10:00 | Monitor opening range, confirm/reject plan |
| 3 | 盘中主动期 | 10:00+ | A/B dual-track: auto polling + user queries |
| 4 | 入场执行 | On trigger | Entry guard validates trade against methodology #6/#11 |
| 5 | 持仓管理 | After entry | Trailing stops, trance adds (T2/T3), exit checks |
| 6 | 收盘复盘 | After close | Post-market review, session log, evolution report |

### A/B Dual-Track System (Node 3)
- **A-track**: `poll.py` runs every 2 minutes, monitors all watchlist stocks for signals/stop-loss/scenario changes, pushes alerts to discussion board
- **B-track**: User can query any stock, request CIO analysis, or report trades ("买了 MRVL $178 20股")

## The 8 Safety Filters

`safety_filter.py` runs before any trade entry. Three severity tiers:

| Tier | Meaning | Action |
|------|---------|--------|
| RED | Hard block | Trade rejected |
| ORANGE | Warning | Proceed with caution, reduced size |
| YELLOW | Info | Logged but no restriction |

| Filter | Condition | Default Severity |
|--------|-----------|------------------|
| F1 | VIX spike >30 or up >20% intraday | RED |
| F2 | Major news shock (detected via sentiment pipeline) | ORANGE |
| F3 | Broad market circuit breaker / QQQ drop >5% | RED |
| F4 | Low liquidity (avg volume <100k or vol ratio <0.3) | ORANGE |
| F5 | FOMC blackout (2h window around announcement) | ORANGE |
| F6 | Earnings within 3 days | YELLOW |
| F7 | Overnight gap >5% | ORANGE |
| F8 | Correlation melt-up (>0.9 to SPY, all positions same direction) | YELLOW |

## Paper Trading Engine

`paper_trader.py` runs 3 parallel simulated accounts for A/B testing:

| Account | Entry Threshold | Max Positions | Personality |
|---------|-----------------|---------------|-------------|
| **strict** | ≥8.0 score + RS≥2.0 | 4 | Conservative, only high-conviction |
| **base** | ≥7.5 score + RS≥1.5 | 6 | Balanced (default) |
| **loose** | ≥5.0 score + RS≥0.8 | 6 | Aggressive, more entries |

### Trance System (T1/T2/T3)
- **T1**: Initial entry at VWAP-based stop, ATR-based targets
- **T2**: Add-on via Path A (strength: price higher + volume confirmation) or Path B (pullback: shrinking volume + VWAP support)
- **T3**: Breakout add-on at Target 1 with volume spike

### Mode Decision
- **Intraday**: Default. EOD forced close.
- **Swing**: Triggered when catalyst strength ≥2 OR RS streak ≥5. Held overnight.

### Weekly Evolution
Each weekend, `weekly_evolution_report()` compares win rate, profit factor, and intraday vs swing performance across all 3 accounts, then suggests parameter adjustments.

## 5D Market Scanner

`market_scanner.py` ranks stocks across 5 dimensions:
1. **Signal strength** — persona consensus score
2. **Sector heat** — sector ETF momentum + RS vs sector
3. **Position fit** — portfolio correlation, existing exposure
4. **Catalyst tier** — news/earnings/events impact rating
5. **Crowding score** — institutional ownership, retail sentiment extremes

Top-ranked candidates become the day's watchlist.

## Configuration

| File | Purpose |
|------|---------|
| `config/poll_config.json` | 35-stock watchlist, 10 default_symbols, polling interval, RS thresholds |
| `config/sector_watchlist.json` | 22 sectors, ~80 stocks with overlap maps |
| `config/positions.json` | Active positions with entry price, stop, targets, notes |
| `config/leveraged_pairs.json` | TQQQ/SQQQ etc. mappings |

## Knowledge Base

| File | Content |
|------|---------|
| `knowledge/company_profiles.json` | 26 company profiles: segments, competitors, milestones, narratives |
| `knowledge/trading_methodology.md` | 13 integrated methodologies from Minervini, Druckenmiller, Burry, Marks, Taleb, etc. |
| `personas/*/worldview.md` | Each master's investment philosophy |
| `personas/*/history.md` | Each master's career lessons |
| `personas/*/blindspots.md` | Each master's known weaknesses |
| `personas/*/questions.json` | 5-question evaluation sequence per master |

## Directory Structure

```
ryn_stock_team/
├── agents/              # All agent modules (32 files)
│   ├── cio.py           # Central orchestrator (Phase 0→3)
│   ├── protocol.py      # Shared constants, message factories, persona application
│   ├── session_manager.py  # 6-node daily scheduler (THE entry point)
│   ├── poll.py          # A-track 2-min polling engine (1100 lines)
│   ├── debate_engine.py # 4-step persona debate protocol
│   ├── persona_engine.py   # Persona evaluation (veto→score→insight→signal→confidence)
│   ├── strategy_agent.py   # Final signal synthesis (reads persona_synthesis.json)
│   ├── report_agent.py  # Terminal + HTML report generator
│   ├── safety_filter.py # 8 pre-trade safety filters (F1-F8)
│   ├── paper_trader.py  # 3-account paper trading with T1/T2/T3 trances
│   ├── premarket.py     # Pre-market analysis and gap/scenario prediction
│   ├── daily_plan.py    # Daily trade plan generation (8 scenario patterns)
│   ├── entry_guard.py   # Entry validation against methodology #6/#11
│   ├── market_scanner.py   # 5D scanner: signal×sector×position×catalyst×crowding
│   ├── session_recorder.py # 3-layer trading journal (snapshots/history/summary)
│   ├── cleanup.py       # Old file cleanup and archival
│   ├── [7 domain agents]   # tech_agent, fund_agent, macro_agent, sentiment_agent,
│   │                      # community_agent, risk_agent, sector_agent
│   └── [support agents]    # data_agent, verifier_agent, question_router,
│                          # auto_trigger, quick_debate, multi_stock, stock_report, etc.
├── personas/            # 7 master persona directories + 2 archived
│   ├── mark_minervini/  # Rules, questions, worldview, history, blindspots, language
│   ├── stan_druckenmiller/
│   ├── howard_marks/
│   ├── nassim_taleb/
│   ├── jesse_livermore/
│   ├── george_soros/
│   ├── peter_lynch/
│   └── archive/         # Michael Burry, Warren Buffett (single-file JSON)
├── indicators/          # Technical indicator computation
│   ├── compute_indicators.py  # 47 indicators in 3 tiers (trend, momentum, volatility)
│   └── data_fetcher.py  # Multi-source data provider (yfinance primary)
├── utils/               # Shared utilities
│   ├── log_config.py    # Structured logging
│   ├── retry.py         # Exponential backoff + jitter for API calls
│   └── atomic.py        # Atomic file writes (write-tmp + os.replace)
├── config/              # Runtime configuration
├── knowledge/           # Company profiles, trading methodology
├── templates/           # Jinja2 HTML templates for reports
├── paper_trading/       # Paper trading account state (3 subdirectories)
├── reports/             # Generated HTML reports
└── findings/            # Per-agent finding JSON files (Phase 1 output)
```

## How to Run

### Full daily session (recommended)
```bash
python agents/session_manager.py
```
This starts the interactive 6-node workflow. At each node transition, the system prompts for confirmation before proceeding.

### Single-stock CIO analysis
```bash
python agents/cio.py AAPL
```
Runs Phase 0→3 for one stock. Add `--phases 012` to stop before strategy synthesis, or `--question-type "swing"` for swing trade framing.

### Pre-market scan
```bash
python agents/premarket.py
```
Analyzes all watchlist stocks for overnight gaps, predicts opening scenarios (A-H), and generates the daily plan.

### Paper trading status
```bash
python -c "from agents.paper_trader import get_status, load_portfolio; print(get_status())"
```

### Session summary
```bash
python agents/session_recorder.py build   # Generate today's session journal
python agents/session_recorder.py patterns  # Show last 30 days' behavior patterns
```

## Data Flow

```
yfinance API (with retry)
    │
    ▼
data_agent.py ──► data_verified.json (47 indicators + fundamentals)
    │
    ▼
verifier_agent.py ──► verification status per field
    │
    ▼
7 domain agents (parallel) ──► findings/{Agent}.json
    │
    ▼
apply_persona() ──► master evaluation (veto/score/signal/confidence)
    │
    ▼
discussion_board.jsonl ──► challenge/revision/endorsement messages
    │
    ▼
debate_engine.py ──► persona_stances.jsonl ──► persona_synthesis.json
    │
    ▼
strategy_agent.py ──► strategy_result.json (final signal + confidence)
    │
    ▼
report_agent.py ──► terminal report + reports/{timestamp}.html
```

## Key Design Decisions

- **Persona masters overrule domain agents**. The `strategy_agent.py` reads `persona_synthesis.json` as the primary signal. Domain agent votes are a fallback only if persona synthesis is absent.
- **Atomic file writes throughout**. All JSON outputs use `write-tmp + os.replace` to prevent corruption from concurrent writes.
- **UTF-8 everywhere**. All file I/O explicitly sets `encoding="utf-8"` for Windows compatibility.
- **Backoff + jitter on all API calls**. yfinance fetches retry 3 times with exponential backoff and random jitter to avoid rate limiting.
- **A/B testing via 3 paper accounts**. The weekly evolution report compares strict/base/loose to auto-tune entry parameters.

## Known Limitations

- **LLM integration is placeholder**. `postmarket_review.py` and several debate response functions use hardcoded templates instead of actual LLM calls.
- **No real-time websocket data**. All price data comes from yfinance polling (2-min interval minimum).
- **DST handling is approximate**. Several files use `(now.hour - 4) % 24` for ET conversion, which doesn't account for EST/EDT transitions.
- **3 persona masters lack rules.json**. Soros, Livermore, and Lynch have `questions.json` but no `rules.json`, so their full `evaluate()` path returns empty (they work via `evaluate_with_questions()` instead).
- **CIO and session_manager can collide on discussion_board.jsonl**. CIO truncates the board on start while session_manager appends. Running both simultaneously on the same stock is not recommended.
- **No database backend**. All state is JSON files on disk. A SQL schema exists in `db/schema.sql` but is not wired in.
