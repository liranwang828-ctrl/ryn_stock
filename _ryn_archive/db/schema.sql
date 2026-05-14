-- Agent Team v2.0 — Database Schema
-- Generated from config/data_catalog.yaml
-- Target: PostgreSQL (primary) / SQLite (local dev fallback)
--
-- Usage:
--   PostgreSQL: psql -h <host> -U <user> -d <db> -f db/schema.sql
--   SQLite:     sqlite3 agent_team.db < db/schema.sql  (run through sqlite_translate.sql)

-- ============================================================
-- 1. market_news
-- ============================================================
CREATE TABLE IF NOT EXISTS market_news (
    news_id         TEXT PRIMARY KEY,
    headline        TEXT NOT NULL,
    source          TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH')),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    related_tickers TEXT[],  -- PostgreSQL array; SQLite: use JSON or comma-separated
    sentiment_polarity REAL CHECK (sentiment_polarity >= -1.0 AND sentiment_polarity <= 1.0)
);
CREATE INDEX IF NOT EXISTS idx_market_news_timestamp ON market_news (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_news_severity ON market_news (severity);
CREATE INDEX IF NOT EXISTS idx_market_news_tickers ON market_news USING GIN (related_tickers);

-- ============================================================
-- 2. earnings_calendar
-- ============================================================
CREATE TABLE IF NOT EXISTS earnings_calendar (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    report_date     DATE NOT NULL,
    estimate_eps    REAL,
    estimate_revenue REAL
);
CREATE INDEX IF NOT EXISTS idx_earnings_ticker ON earnings_calendar (ticker);
CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings_calendar (report_date);

-- ============================================================
-- 3. social_sentiment
-- ============================================================
CREATE TABLE IF NOT EXISTS social_sentiment (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    source          TEXT NOT NULL CHECK (source IN ('reddit', 'twitter', 'stocktwits')),
    score           REAL CHECK (score >= -1.0 AND score <= 1.0),
    volume          INTEGER CHECK (volume >= 0),
    sample_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trending_rank   INTEGER
);
CREATE INDEX IF NOT EXISTS idx_social_ticker ON social_sentiment (ticker);
CREATE INDEX IF NOT EXISTS idx_social_timestamp ON social_sentiment (sample_timestamp DESC);

-- ============================================================
-- 4. wsb_mentions
-- ============================================================
CREATE TABLE IF NOT EXISTS wsb_mentions (
    id                 SERIAL PRIMARY KEY,
    ticker             TEXT NOT NULL,
    mention_count      INTEGER CHECK (mention_count >= 0),
    sentiment_polarity REAL CHECK (sentiment_polarity >= -1.0 AND sentiment_polarity <= 1.0),
    timestamp          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_wsb_ticker ON wsb_mentions (ticker);
CREATE INDEX IF NOT EXISTS idx_wsb_timestamp ON wsb_mentions (timestamp DESC);

-- ============================================================
-- 5. kol_opinions
-- ============================================================
CREATE TABLE IF NOT EXISTS kol_opinions (
    kol_id           TEXT NOT NULL,
    kol_name         TEXT NOT NULL,
    ticker           TEXT NOT NULL,
    opinion          TEXT,
    conviction       INTEGER CHECK (conviction >= 1 AND conviction <= 10),
    statement_date   DATE NOT NULL,
    confidence_score REAL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    PRIMARY KEY (kol_id, statement_date)
);
CREATE INDEX IF NOT EXISTS idx_kol_ticker ON kol_opinions (ticker);

-- ============================================================
-- 6. macro_indicators
-- ============================================================
CREATE TABLE IF NOT EXISTS macro_indicators (
    indicator_name TEXT NOT NULL,
    value          REAL,
    change_pct     REAL,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    period         TEXT NOT NULL DEFAULT 'daily',
    PRIMARY KEY (indicator_name, period, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_macro_name ON macro_indicators (indicator_name);
CREATE INDEX IF NOT EXISTS idx_macro_timestamp ON macro_indicators (timestamp DESC);

-- ============================================================
-- 7. factor_scores
-- ============================================================
CREATE TABLE IF NOT EXISTS factor_scores (
    ticker          TEXT NOT NULL,
    momentum_score  INTEGER CHECK (momentum_score >= 1 AND momentum_score <= 10),
    value_score     INTEGER CHECK (value_score >= 1 AND value_score <= 10),
    quality_score   INTEGER CHECK (quality_score >= 1 AND quality_score <= 10),
    low_vol_score   INTEGER CHECK (low_vol_score >= 1 AND low_vol_score <= 10),
    composite_score INTEGER CHECK (composite_score >= 1 AND composite_score <= 10),
    calc_date       DATE NOT NULL,
    PRIMARY KEY (ticker, calc_date)
);

-- ============================================================
-- 8. fundamentals
-- ============================================================
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker         TEXT NOT NULL,
    pe_ttm         REAL,
    forward_pe     REAL,
    pb             REAL,
    ps             REAL,
    ev_ebitda      REAL,
    roe            REAL,
    roic           REAL,
    debt_to_equity REAL,
    fcf_yield      REAL,
    rev_growth_3y  REAL,
    report_date    DATE NOT NULL,
    PRIMARY KEY (ticker, report_date)
);

-- ============================================================
-- 9. analyst_estimates
-- ============================================================
CREATE TABLE IF NOT EXISTS analyst_estimates (
    ticker           TEXT PRIMARY KEY,
    avg_target       REAL,
    high_target      REAL,
    low_target       REAL,
    num_analysts     INTEGER CHECK (num_analysts >= 0),
    rating_consensus TEXT CHECK (rating_consensus IN ('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'))
);

-- ============================================================
-- 10. price_history
-- ============================================================
CREATE TABLE IF NOT EXISTS price_history (
    ticker  TEXT NOT NULL,
    date    DATE NOT NULL,
    open    REAL NOT NULL,
    high    REAL NOT NULL,
    low     REAL NOT NULL,
    close   REAL NOT NULL,
    volume  BIGINT,
    MA20    REAL,
    MA50    REAL,
    MA200   REAL,
    VWAP    REAL,
    ATR14   REAL,
    ADX14   REAL,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_price_ticker ON price_history (ticker);
CREATE INDEX IF NOT EXISTS idx_price_date ON price_history (date);

-- ============================================================
-- 11. technical_indicators
-- ============================================================
CREATE TABLE IF NOT EXISTS technical_indicators (
    ticker         TEXT NOT NULL,
    indicator_name TEXT NOT NULL,
    value          REAL,
    signal         TEXT CHECK (signal IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ticker, indicator_name, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_tech_ticker ON technical_indicators (ticker);
CREATE INDEX IF NOT EXISTS idx_tech_name ON technical_indicators (indicator_name);
CREATE INDEX IF NOT EXISTS idx_tech_timestamp ON technical_indicators (timestamp DESC);

-- ============================================================
-- 12. volume_profile
-- ============================================================
CREATE TABLE IF NOT EXISTS volume_profile (
    ticker          TEXT NOT NULL,
    volume          INTEGER,
    avg_volume_20d  INTEGER,
    up_volume       INTEGER,
    down_volume     INTEGER,
    buy_sell_ratio  REAL,
    calc_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (ticker, calc_date)
);

-- ============================================================
-- 13. sector_data
-- ============================================================
CREATE TABLE IF NOT EXISTS sector_data (
    id                    SERIAL PRIMARY KEY,
    sector_etf_price      REAL,
    spy_price             REAL,
    sector_etf_return_3d  REAL,
    spy_return_3d         REAL,
    breadth_pct           REAL,
    sector_volatility_30d REAL,
    timestamp             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sector_timestamp ON sector_data (timestamp DESC);

-- ============================================================
-- 14. options_flow
-- ============================================================
CREATE TABLE IF NOT EXISTS options_flow (
    ticker            TEXT PRIMARY KEY,
    put_call_ratio    REAL,
    unusual_activity  BOOLEAN DEFAULT FALSE,
    last_updated      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 15. risk_metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS risk_metrics (
    ticker             TEXT NOT NULL,
    var_95             REAL,
    var_99             REAL,
    beta               REAL,
    correlation_to_spy REAL CHECK (correlation_to_spy >= -1.0 AND correlation_to_spy <= 1.0),
    volatility_30d     REAL,
    max_drawdown_1y    REAL,
    sharpe_ratio       REAL,
    calc_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (ticker, calc_date)
);

-- ============================================================
-- 16. correlation_matrix
-- ============================================================
CREATE TABLE IF NOT EXISTS correlation_matrix (
    ticker_1       TEXT NOT NULL,
    ticker_2       TEXT NOT NULL,
    correlation_60d REAL CHECK (correlation_60d >= -1.0 AND correlation_60d <= 1.0),
    correlation_1y  REAL CHECK (correlation_1y >= -1.0 AND correlation_1y <= 1.0),
    PRIMARY KEY (ticker_1, ticker_2),
    CHECK (ticker_1 < ticker_2)  -- enforce canonical ordering
);

-- ============================================================
-- 17. trade_log
-- ============================================================
CREATE TABLE IF NOT EXISTS trade_log (
    trade_id     TEXT PRIMARY KEY,
    ticker       TEXT NOT NULL,
    entry_time   TIMESTAMPTZ NOT NULL,
    exit_time    TIMESTAMPTZ,
    pnl_pct      REAL,
    entry_reason TEXT,
    exit_reason  TEXT
);
CREATE INDEX IF NOT EXISTS idx_trade_ticker ON trade_log (ticker);
CREATE INDEX IF NOT EXISTS idx_trade_entry ON trade_log (entry_time DESC);

-- ============================================================
-- 18. agent_decision_log
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_decision_log (
    id             SERIAL PRIMARY KEY,
    session_id     TEXT NOT NULL,
    agent_id       TEXT NOT NULL CHECK (agent_id IN ('A1','A2','A3','A4','A5','A6','A7','A8','A9')),
    direction      TEXT NOT NULL CHECK (direction IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    conviction     INTEGER CHECK (conviction >= 1 AND conviction <= 10),
    recommendation TEXT CHECK (recommendation IN ('BUY', 'SELL', 'HOLD', 'NO_ACTION')),
    was_correct    BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_decision_session ON agent_decision_log (session_id);
CREATE INDEX IF NOT EXISTS idx_decision_agent ON agent_decision_log (agent_id);

-- ============================================================
-- 19. fabrication_log
-- ============================================================
CREATE TABLE IF NOT EXISTS fabrication_log (
    id              SERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL,
    agent_id        TEXT NOT NULL CHECK (agent_id IN ('A1','A2','A3','A4','A5','A6','A7','A8','A9')),
    violation_type  TEXT NOT NULL CHECK (violation_type IN ('FABRICATION', 'UNSUBSTANTIATED')),
    claim_text      TEXT NOT NULL,
    cited_source    TEXT,
    dv_finding      TEXT,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    penalty_applied TEXT CHECK (penalty_applied IN ('MUTE', 'WARNING', 'SUSPENSION'))
);
CREATE INDEX IF NOT EXISTS idx_fab_session ON fabrication_log (session_id);
CREATE INDEX IF NOT EXISTS idx_fab_agent ON fabrication_log (agent_id);

-- ============================================================
-- 20. paper_trade_records (extended trade_log for paper trading)
-- ============================================================
CREATE TABLE IF NOT EXISTS paper_trade_records (
    trade_id              TEXT PRIMARY KEY,
    account_id            TEXT NOT NULL,
    trade_type            TEXT NOT NULL DEFAULT 'PAPER' CHECK (trade_type IN ('PAPER', 'LIVE')),
    ticker                TEXT NOT NULL,
    direction             TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    entry_price           REAL NOT NULL,
    entry_time            TIMESTAMPTZ NOT NULL,
    entry_reason          TEXT,
    position_size_shares  REAL,
    position_size_dollars REAL,
    position_size_pct     REAL,
    stop_loss_price       REAL,
    tp1_price             REAL,
    tp2_price             REAL,
    tp3_price             REAL,
    exit_price            REAL,
    exit_time             TIMESTAMPTZ,
    exit_reason           TEXT,
    pnl_pct               REAL,
    pnl_dollar            REAL,
    commission_paid       REAL DEFAULT 0,
    slippage_paid         REAL DEFAULT 0,
    holding_period        TEXT,
    r_multiple            REAL,
    mae_pct               REAL,
    mfe_pct               REAL,
    exit_efficiency       REAL,
    resonance_level       TEXT CHECK (resonance_level IN ('STRONG', 'MODERATE', 'WEAK')),
    resonance_groups      TEXT[],  -- PostgreSQL array of group IDs
    consensus_strength    REAL,
    agent_votes           JSONB,
    fabrication_flags     JSONB,
    market_regime         TEXT,
    vix_at_entry          REAL,
    safety_filters_active TEXT[],
    obs_signal_at_entry   REAL,
    notes                 TEXT,
    reviewed_by_A9        BOOLEAN DEFAULT FALSE,
    A9_review_notes       TEXT
);
CREATE INDEX IF NOT EXISTS idx_paper_account ON paper_trade_records (account_id);
CREATE INDEX IF NOT EXISTS idx_paper_ticker ON paper_trade_records (ticker);
CREATE INDEX IF NOT EXISTS idx_paper_entry ON paper_trade_records (entry_time DESC);

-- ============================================================
-- 21. paper_account_snapshots (daily equity curve tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS paper_account_snapshots (
    id            SERIAL PRIMARY KEY,
    account_id    TEXT NOT NULL,
    session_date  DATE NOT NULL,
    equity        REAL NOT NULL,
    cash          REAL,
    positions     INTEGER,
    daily_pnl_pct REAL,
    drawdown_pct  REAL,
    sharpe_rolling REAL,
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_snapshot_account ON paper_account_snapshots (account_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_date ON paper_account_snapshots (session_date DESC);

-- ============================================================
-- Views for common queries
-- ============================================================

-- Leaderboard: latest snapshot per account
CREATE OR REPLACE VIEW v_leaderboard AS
SELECT
    a.account_id,
    a.equity,
    a.daily_pnl_pct,
    a.drawdown_pct,
    a.sharpe_rolling,
    a.session_date,
    ROW_NUMBER() OVER (PARTITION BY a.account_id ORDER BY a.session_date DESC) = 1 AS is_latest
FROM paper_account_snapshots a;

-- Agent accuracy: rolling 20-session correct rate
CREATE OR REPLACE VIEW v_agent_accuracy AS
SELECT
    agent_id,
    session_id,
    COUNT(*) FILTER (WHERE was_correct) * 1.0 / NULLIF(COUNT(*), 0) AS accuracy
FROM agent_decision_log
GROUP BY agent_id, session_id
ORDER BY session_id DESC;

-- Fabrication count per agent, last 10 sessions
CREATE OR REPLACE VIEW v_fabrication_recent AS
SELECT
    agent_id,
    COUNT(*) AS violation_count,
    COUNT(*) FILTER (WHERE violation_type = 'FABRICATION') AS fabrication_count,
    COUNT(*) FILTER (WHERE violation_type = 'UNSUBSTANTIATED') AS unsubstantiated_count
FROM fabrication_log
WHERE timestamp >= NOW() - INTERVAL '10 days'
GROUP BY agent_id;
