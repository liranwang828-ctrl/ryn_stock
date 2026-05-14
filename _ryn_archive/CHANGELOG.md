# Changelog

All notable changes to the Ryn Stock Team project.

## [2.0.0] — 2026-05-14

### Added (Phase 1: Core Configuration)
- `config/agent_definitions.yaml` — 9 agent + 2 system role definitions with strict data boundaries
- `config/mode_participation_matrix.yaml` — 5-mode participation matrix with static weights
- `config/data_catalog.yaml` — 17 shared data tables with complete field schemas and 47-indicator whitelist

### Added (Phase 2: Debate Protocol)
- `config/debate_protocol_v2.yaml` — 3-round debate structure (independent → challenge → synthesis)
- `prompts/agent_system_prompts.md` — Per-agent system prompt templates with mode-specific overrides
- Data Validator (DV) pre-validation gate for anti-fabrication

### Added (Phase 3: Trading Strategy)
- `config/observation_framework.yaml` — 6-category observation indicator system with composite scoring
- `config/trading_strategy.yaml` — 5-group resonance entry logic (G_PRICE, G_TECH, G_SECTOR, G_MACRO, G_SENTIMENT) with STRONG/MODERATE/WEAK/NO_ENTRY levels
- 8 market safety filters (F1-F8: VIX spike, news shock, circuit breaker, low liquidity, FOMC blackout, earnings risk, overnight gap, correlation melt-up)
- Multi-target take-profit (T1/T2/T3) with ATR trailing stop, time stop, and max drawdown circuit breaker

### Added (Phase 4: Dynamic Weights)
- `config/dynamic_weights.yaml` — D_accuracy × D_regime × D_freshness weight formula
- `config/fabrication_penalties.yaml` — UNSUBSTANTIATED vs FABRICATION classification with escalation tiers
- A7-specific zero-tolerance policy with steeper penalties

### Added (Phase 5: Paper Trading & Execution)
- `config/paper_trading.yaml` — Paper trading simulator with commission (0.1%), slippage model, analytics
- `config/paper_accounts_comparison.yaml` — 5 virtual accounts: conservative (A), balanced/Baseline (B), aggressive (C), momentum (D), contrarian (E)
- `config/position_staging.yaml` — 3 staging strategies: pyramiding (30-40-30%), scale-in at levels (25-35-40%), time-based (33-33-34%)
- `schemas/trade_record_schema.json` — 36-field JSON Schema for trade records
- `config/MASTER_CONFIG.yaml` — Consolidated entry point with configurable parameters and pending decisions

### Added (Indicators Engine)
- `indicators/compute_indicators.py` — 47 technical indicators computed locally from OHLCV using pandas/numpy
  - 6 categories: trend (10), momentum (8), volatility (7), volume (5), support/resistance (11), candlestick (6)
  - 3-tier efficiency: Tier 1 session-static (~9ms), Tier 2 5-min cache (~1ms), Tier 3 every 2min (<1ms)
- `indicators/data_fetcher.py` — Multi-source OHLCV provider (cloud DB → Yahoo Finance fallback)
- `indicators/test_indicators.py` — Smoke test with synthetic data (46/47 indicators verified)

### Added (Execution Engine)
- `engine/orchestrator.py` — Main session runner: mode scheduling (M1-M5), data pipeline, resonance evaluation, debate simulation, multi-account trade execution
- `engine/paper_engine.py` — Paper trading simulator: 5-account management, order matching with slippage/commission, multi-target exits, leaderboard
- `engine/backtest.py` — Walk-forward backtest framework + parameter grid sweep optimizer
- `engine/dashboard.py` — ASCII terminal dashboard: leaderboard, positions, signals, equity sparklines, agent status

### Added (Data Pipelines)
- `pipelines/news_pipeline.py` — Multi-source news/sentiment/macro pipeline (Finnhub, Reddit, Yahoo Finance)

### Added (Database)
- `db/schema.sql` — 21 CREATE TABLE statements + 3 views, PostgreSQL/SQLite ready

### Added (Project)
- `.gitignore` — Python, IDE, secrets, data, cache exclusions
- `requirements.txt` — Core Python dependencies
- `CHANGELOG.md` — This file

### Pending
- LLM API integration (currently simulated debate, needs DeepSeek API connection)
- Cloud database connection string configuration
- API keys for Finnhub/Reddit news pipeline
- Web dashboard (terminal dashboard exists, web UI pending)
- Grid sweep parameter optimization (requires 20 sessions of baseline data)
- 6 user decisions documented in `config/MASTER_CONFIG.yaml` under `pending_user_decisions`

---

## [Unreleased]

### Changed (2026-05-14)
- `pipelines/news_pipeline.py` — Sentiment engine upgraded from keyword counting to NLP:
  - VADER sentiment (NLTK) replaces all crude keyword matching
  - FinBERT optional integration for financial-domain sentiment
  - StockTwits free API for retail trader sentiment
  - Xueqiu (雪球) Chinese retail investor community sentiment
  - SentimentAggregator with cross-source confidence-weighted scoring
  - SentimentSignal dataclass: compound, confidence, source_count, trend, breakdown
  - Chinese bullish/bearish keyword lexicon (30+ terms)
- `requirements.txt` — Added `nltk>=3.8`, optional `transformers` and `torch` for FinBERT

### Planned
- [ ] DeepSeek API integration for live 9-agent debate
- [ ] Web dashboard with real-time charts
- [ ] Mobile notifications for trade signals
- [ ] Real brokerage API integration (IBKR, Alpaca)
- [ ] Backtesting against 5 years of historical data
- [ ] Machine learning regime classifier
- [ ] Automated parameter optimization based on regime detection
