"""
Orchestrator v2.0 — Agent Team Core Engine
===========================================
Main execution loop that ties together:
- Mode scheduling (M1-M5 based on market hours)
- Config loading (all YAML files)
- Agent participation (per mode_participation_matrix)
- Debate protocol (3-round via debate_protocol_v2)
- Signal generation (resonance groups from trading_strategy)
- Safety filter enforcement
- Paper trading execution (via PaperTradingEngine)

Usage:
    orch = Orchestrator()
    orch.run_session(tickers=['NVDA', 'AAPL', 'MSFT'])
"""

import os
import sys
import time
import yaml
import json
from datetime import datetime, time as dtime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.compute_indicators import compute_all_indicators, to_table_rows, merge_tiers
from indicators.data_fetcher import DataFetcher
from engine.paper_engine import PaperTradingEngine
from pipelines.news_pipeline import NewsPipeline


# ============================================================
# Config Loader
# ============================================================

@dataclass
class SessionConfig:
    """All config loaded and ready for a session."""
    data_catalog: Dict
    agent_definitions: Dict
    mode_matrix: Dict
    debate_protocol: Dict
    dynamic_weights: Dict
    fabrication_penalties: Dict
    observation_framework: Dict
    trading_strategy: Dict
    paper_trading: Dict
    position_staging: Dict
    paper_accounts: Dict

    @classmethod
    def load_all(cls, config_dir: str = None) -> 'SessionConfig':
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

        def load_yaml(name):
            path = os.path.join(config_dir, name)
            with open(path, encoding='utf-8') as f:
                return yaml.safe_load(f)

        return cls(
            data_catalog=load_yaml('data_catalog.yaml'),
            agent_definitions=load_yaml('agent_definitions.yaml'),
            mode_matrix=load_yaml('mode_participation_matrix.yaml'),
            debate_protocol=load_yaml('debate_protocol_v2.yaml'),
            dynamic_weights=load_yaml('dynamic_weights.yaml'),
            fabrication_penalties=load_yaml('fabrication_penalties.yaml'),
            observation_framework=load_yaml('observation_framework.yaml'),
            trading_strategy=load_yaml('trading_strategy.yaml'),
            paper_trading=load_yaml('paper_trading.yaml'),
            position_staging=load_yaml('position_staging.yaml'),
            paper_accounts=load_yaml('paper_accounts_comparison.yaml'),
        )


# ============================================================
# Data Validator (DV — System Role)
# ============================================================

class DataValidator:
    """
    System-level data validation gate.
    Verifies agent claims against actual data tables before they enter debate.
    """

    def __init__(self):
        self.indicator_whitelist: List[str] = []
        self.fabrication_log: List[Dict] = []

    def load_whitelist(self, data_catalog: Dict):
        tech_table = data_catalog['tables']['technical_indicators']
        whitelist = tech_table.get('indicator_whitelist', {})
        self.indicator_whitelist = []
        for category in whitelist.values():
            for ind in category:
                self.indicator_whitelist.append(ind['name'])

    def validate_claim(self, agent_id: str, claim: Dict) -> Dict:
        """
        Validate an agent's factual claim.
        claim: {'type': 'indicator_value'|'price_level'|'news_event'|...,
                'ticker': 'NVDA', 'indicator': 'RSI_14', 'claimed_value': 75.0,
                'actual_value': 72.3}
        Returns: {'valid': bool, 'violation': str|None}
        """
        claim_type = claim.get('type', '')

        if claim_type == 'indicator_value':
            indicator = claim.get('indicator', '')
            if indicator not in self.indicator_whitelist:
                return {'valid': None, 'violation': 'UNSUBSTANTIATED',
                       'reason': f"Indicator '{indicator}' not in whitelist — system did not compute it"}
            claimed = claim.get('claimed_value')
            actual = claim.get('actual_value')
            if actual is not None and claimed is not None:
                if abs(claimed - actual) > 0.01:  # tolerance for rounding
                    return {'valid': False, 'violation': 'FABRICATION',
                           'reason': f"Claimed {indicator}={claimed}, actual={actual}"}
            return {'valid': True, 'violation': None}

        elif claim_type == 'price_level':
            claimed = claim.get('claimed_value')
            actual = claim.get('actual_value')
            if actual is not None and claimed is not None:
                if abs(claimed - actual) / actual > 0.02:  # 2% tolerance
                    return {'valid': False, 'violation': 'FABRICATION',
                           'reason': f"Claimed price {claimed}, actual {actual}"}
            return {'valid': True, 'violation': None}

        elif claim_type == 'news_event':
            headline = claim.get('headline', '')
            source = claim.get('source', '')
            if not headline or not source:
                return {'valid': None, 'violation': 'UNSUBSTANTIATED',
                       'reason': "News claim without headline or source — unverifiable"}
            return {'valid': True, 'violation': None}

        return {'valid': True, 'violation': None}

    def log_violation(self, session_id: str, agent_id: str, violation_type: str,
                      claim_text: str, cited_source: str, dv_finding: str):
        self.fabrication_log.append({
            'session_id': session_id,
            'agent_id': agent_id,
            'violation_type': violation_type,
            'claim_text': claim_text,
            'cited_source': cited_source,
            'dv_finding': dv_finding,
            'timestamp': datetime.now().isoformat()
        })


# ============================================================
# Resonance Signal Engine
# ============================================================

class ResonanceEngine:
    """
    Evaluate resonance groups from trading_strategy.yaml
    using actual indicator values.
    """

    def __init__(self, strategy_config: Dict):
        self.config = strategy_config
        self.groups = strategy_config['resonance_groups']

    def evaluate_all(self, ticker: str, indicators: Dict[str, float],
                     prices: Dict[str, pd.DataFrame],
                     sector_data: Dict = None,
                     macro_data: Dict = None,
                     sentiment_data: Dict = None) -> Dict[str, Dict]:
        """
        Evaluate all 5 resonance groups for a ticker.
        Returns: {group_id: {'passed': bool, 'score': int, 'components': {...}}}
        """
        results = {}

        # G_PRICE: Price structure
        g_price = self._eval_g_price(ticker, prices.get(ticker), indicators)
        results['G_PRICE'] = g_price

        # G_TECH: Technical indicators
        g_tech = self._eval_g_tech(indicators)
        results['G_TECH'] = g_tech

        # G_SECTOR: Sector confirmation
        g_sector = self._eval_g_sector(sector_data or {})
        results['G_SECTOR'] = g_sector

        # G_MACRO: Macro safety
        g_macro = self._eval_g_macro(macro_data or {})
        results['G_MACRO'] = g_macro

        # G_SENTIMENT: Sentiment confirmation
        g_sentiment = self._eval_g_sentiment(sentiment_data or {})
        results['G_SENTIMENT'] = g_sentiment

        return results

    def _eval_g_price(self, ticker: str, df: Optional[pd.DataFrame],
                      indicators: Dict) -> Dict:
        """Evaluate G_PRICE resonance group."""
        passed = 0
        details = {}

        if df is not None and len(df) >= 3:
            price = df['close'].iloc[-1]
            vwap = indicators.get('VWAP')
            prev_close = indicators.get('Prev_day_close')

            # above_vwap
            if vwap and price > vwap:
                details['above_vwap'] = True
                passed += 1
            else:
                details['above_vwap'] = False

            # above_prev_close
            if prev_close and price > prev_close:
                details['above_prev_close'] = True
                passed += 1
            else:
                details['above_prev_close'] = False

            # higher_lows
            lows = df['low'].iloc[-3:].values
            if len(lows) == 3 and lows[0] > lows[1] > lows[2]:
                details['higher_lows'] = True
                passed += 1
            else:
                details['higher_lows'] = False
        else:
            details = {'above_vwap': False, 'above_prev_close': False, 'higher_lows': False}

        return {'passed': passed >= 3, 'score': passed, 'components': details}

    def _eval_g_tech(self, indicators: Dict) -> Dict:
        """Evaluate G_TECH resonance group."""
        passed = 0
        details = {}

        adx = indicators.get('ADX_14', 0)
        ma20 = indicators.get('MA20')
        price = indicators.get('close') or indicators.get('current_price', 0)
        ma20_slope = indicators.get('MA20_slope', 0)

        # adx_strong
        if adx and adx > 25:
            details['adx_strong'] = True
            passed += 1
        elif ma20 and price and price > ma20 and ma20_slope > 0:
            details['adx_strong'] = True  # fallback
            passed += 1
        else:
            details['adx_strong'] = False

        # above_ma20
        if ma20 and price and price > ma20:
            details['above_ma20'] = True
            passed += 1
        else:
            details['above_ma20'] = False

        # not_at_resistance
        r1 = indicators.get('Pivot_R1')
        if r1 and price and price < r1 * 0.98:
            details['not_at_resistance'] = True
            passed += 1
        elif r1 is None:
            details['not_at_resistance'] = True  # no resistance data = pass
            passed += 1
        else:
            details['not_at_resistance'] = False

        return {'passed': passed >= 3, 'score': passed, 'components': details}

    def _eval_g_sector(self, sector_data: Dict) -> Dict:
        """Evaluate G_SECTOR resonance group."""
        passed = 0
        details = {}

        sec_return = sector_data.get('sector_etf_return_session', 0)
        spy_return = sector_data.get('spy_return_session', 0)
        breadth = sector_data.get('breadth_pct', 0)

        if sec_return - spy_return > 0.003:
            details['sector_outperformance'] = True
            passed += 1
        else:
            details['sector_outperformance'] = False

        if breadth > 55:
            details['breadth_healthy'] = True
            passed += 1
        else:
            details['breadth_healthy'] = False

        # If no sector data, assume neutral (not passed, not failed — skip this group)
        if not sector_data:
            details['_no_data'] = True

        return {'passed': passed >= 2, 'score': passed, 'components': details}

    def _eval_g_macro(self, macro_data: Dict) -> Dict:
        """Evaluate G_MACRO resonance group."""
        passed = 0
        details = {}

        vix = macro_data.get('VIX', 20)
        spread = macro_data.get('10Y_2Y_spread', 0.5)
        is_fomc = macro_data.get('is_fomc_day', False)

        details['vix_safe'] = vix < 30
        details['no_deep_inversion'] = spread > -0.3
        details['no_fomc'] = not is_fomc

        passed = sum([details['vix_safe'], details['no_deep_inversion'], details['no_fomc']])

        return {'passed': passed >= 3, 'score': passed, 'components': details}

    def _eval_g_sentiment(self, sentiment_data: Dict) -> Dict:
        """Evaluate G_SENTIMENT resonance group."""
        passed = 0
        details = {}

        social_z = sentiment_data.get('social_sentiment_zscore', 0)
        news_pol = sentiment_data.get('avg_news_polarity_24h', 0)
        pcr = sentiment_data.get('put_call_ratio', 1.0)

        details['social_positive'] = social_z > 0
        details['news_positive'] = news_pol > 0
        details['low_put_call'] = pcr < 1.0
        passed = sum(details.values())

        # If no sentiment data at all, don't count this group
        if not sentiment_data:
            details['_no_data'] = True

        return {'passed': passed >= 3, 'score': passed, 'components': details}

    def determine_entry_level(self, group_results: Dict[str, Dict]) -> Tuple[str, int, List[str]]:
        """
        Determine entry level from resonance group results.
        Returns: (level, group_count, triggered_groups)
        STRONG = 4+, MODERATE = 3, WEAK = 2, NO_ENTRY = 0-1
        """
        triggered = [gid for gid, r in group_results.items() if r['passed']]
        count = len(triggered)

        if count >= 4:
            return 'STRONG', count, triggered
        elif count >= 3:
            return 'MODERATE', count, triggered
        elif count >= 2:
            return 'WEAK', count, triggered
        return 'NO_ENTRY', count, triggered


# ============================================================
# Safety Filter Engine
# ============================================================

class SafetyFilterEngine:
    """Evaluate 8 safety filters from trading_strategy.yaml."""

    def __init__(self, strategy_config: Dict):
        self.filters = strategy_config.get('safety_filters', {})

    def check_all(self, vix: float, recent_news: List[Dict], spy_change_pct: float,
                  spy_volume_ratio: float, is_fomc_time: bool,
                  ticker_earnings: Dict[str, bool], is_session_start: bool,
                  is_gap_open: bool, sector_correlation_r2: float) -> Dict[str, List[str]]:
        """
        Check all safety filters.
        Returns: {'active': ['F1', 'F2', ...], 'blocked': ['F1', ...], 'warnings': ['F6', ...]}
        """
        active = []
        blocked = []  # block all entries
        warnings = []  # block specific tickers or reduce size

        # F1: VIX spike
        if vix > 35:
            active.append('F1')
            blocked.append('F1')

        # F2: Major news shock
        high_severity_recent = any(
            n.get('severity') == 'HIGH' for n in recent_news
            if n.get('timestamp') and
            (datetime.now() - datetime.fromisoformat(n['timestamp'])).seconds < 1800
        )
        if high_severity_recent:
            active.append('F2')
            blocked.append('F2')

        # F3: Circuit breaker
        if spy_change_pct < -5:
            active.append('F3')
            blocked.append('F3')

        # F4: Low liquidity
        if spy_volume_ratio < 0.5:
            active.append('F4')
            blocked.append('F4')

        # F5: FOMC blackout
        if is_fomc_time:
            active.append('F5')
            blocked.append('F5')

        # F6: Earnings risk (ticker-specific)
        if any(ticker_earnings.values()):
            active.append('F6')
            warnings.append('F6')

        # F7: Overnight gap
        if is_session_start and is_gap_open:
            active.append('F7')
            blocked.append('F7')

        # F8: Correlation melt-up
        if sector_correlation_r2 > 0.9:
            active.append('F8')
            blocked.append('F8')

        return {'active': active, 'blocked': blocked, 'warnings': warnings}


# ============================================================
# Orchestrator
# ============================================================

class Orchestrator:
    """
    Main orchestrator for the Agent Team trading system.

    Lifecycle per session:
        1. Pre-market (M1): Load data, compute indicators, brief agents
        2. Opening observation (M2): Watch first 30 min, check gap/filter
        3. Real-time monitoring (M3): 2-min cycles, signal check, debate
        4. Strategy execution (M4): Execute trades, manage positions
        5. Post-market review (M5): Leaderboard, weight feedback, agent scoring
    """

    # Market hours (Eastern)
    PRE_MARKET_START = dtime(4, 0)    # 4:00 AM
    MARKET_OPEN = dtime(9, 30)        # 9:30 AM
    OPENING_OBSERVE_END = dtime(10, 0)  # 10:00 AM
    MARKET_CLOSE = dtime(16, 0)       # 4:00 PM
    POST_MARKET = dtime(16, 15)       # 4:15 PM

    def __init__(self, config_dir: str = None):
        self.config = SessionConfig.load_all(config_dir)
        self.session_id = f"SES_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_mode = None
        self.dv = DataValidator()
        self.dv.load_whitelist(self.config.data_catalog)

        # Engines
        self.resonance = ResonanceEngine(self.config.trading_strategy)
        self.safety = SafetyFilterEngine(self.config.trading_strategy)
        self.paper = PaperTradingEngine()
        self.paper.create_accounts()
        self.fetcher = DataFetcher()
        self.news_pipeline = NewsPipeline()

        # State
        self.indicators_cache: Dict[str, Dict] = {}
        self.tier3_cache: Dict[str, Dict] = {}
        self.prices: Dict[str, pd.DataFrame] = {}
        self.watchlist: List[str] = []
        self.session_log: List[Dict] = []
        self.agent_states: Dict[str, Dict] = {}
        self.debate_rounds: List[Dict] = []

        self._init_agent_states()

    def _init_agent_states(self):
        """Initialize agent state trackers."""
        for agent_id in [f'A{i}' for i in range(1, 10)]:
            agent_def = self.config.agent_definitions.get('agents', {}).get(agent_id, {})
            self.agent_states[agent_id] = {
                'muted': False,
                'suspended': False,
                'mute_remaining_sessions': 0,
                'fabrication_count': 0,
                'unsubstantiated_count': 0,
                'decisions_last_20': [],
                'D_accuracy': 1.0,
                'D_regime': 1.0,
                'D_freshness': 1.0,
                'W_final': agent_def.get('static_weight', 0),
            }

    # ── Mode Detection ───────────────────────────────────────

    def detect_mode(self) -> str:
        """Detect current trading mode based on time of day."""
        now = datetime.now().time()
        today = datetime.now().date()

        # Check if weekend
        if today.weekday() >= 5:
            return 'IDLE'

        if now < self.MARKET_OPEN:
            if now >= self.PRE_MARKET_START:
                return 'M1_PRE_MARKET'
            return 'IDLE'

        if now < self.OPENING_OBSERVE_END:
            return 'M2_OPENING'

        if now < self.MARKET_CLOSE:
            return 'M3_MONITORING'

        return 'M5_POST_MARKET'

    # ── Session Runner ───────────────────────────────────────

    def run_session(self, tickers: List[str] = None, mode: str = None):
        """
        Run a full trading session or a specific mode.

        Args:
            tickers: Watchlist tickers
            mode: Force a specific mode ('M1', 'M2', 'M3', 'M4', 'M5'). If None, auto-detect.
        """
        if tickers is None:
            tickers = ['SPY', 'QQQ']

        self.watchlist = tickers
        mode = mode or self.detect_mode()

        print(f"\n{'='*60}")
        print(f"  Agent Team v2.0 — Session {self.session_id}")
        print(f"  Mode: {mode}  |  Tickers: {', '.join(tickers)}")
        print(f"  Time: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")

        if mode == 'IDLE':
            print("[Orchestrator] Market closed. Run backtest or review instead.")
            return

        # Step 1: Fetch data
        self._fetch_data(tickers)

        # Step 2: Compute indicators
        self._compute_indicators(tickers)

        # Step 3: Run mode-specific logic
        if mode == 'M1_PRE_MARKET':
            self._run_pre_market(tickers)
        elif mode == 'M2_OPENING':
            self._run_opening(tickers)
        elif mode == 'M3_MONITORING':
            self._run_monitoring_cycle(tickers)
        elif mode == 'M4_EXECUTION':
            self._run_execution(tickers)
        elif mode == 'M5_POST_MARKET':
            self._run_post_market(tickers)

        # Step 4: Log session
        self._log_session()

    # ── Data Pipeline ────────────────────────────────────────

    def _fetch_data(self, tickers: List[str]):
        """Fetch OHLCV and news/sentiment/macro data."""
        print("[Orchestrator] Fetching market data...")

        # OHLCV via DataFetcher (cloud DB + Yahoo Finance)
        for ticker in tickers:
            try:
                df = self.fetcher.get_ohlcv(ticker, period='6mo', interval='1d')
                if not df.empty:
                    self.prices[ticker] = df
                    print(f"  {ticker}: {len(df)} bars loaded")
            except Exception as e:
                print(f"  {ticker}: fetch failed — {e}")

        # News, sentiment, macro
        try:
            news_data = self.news_pipeline.fetch_all(tickers)
            self.session_log.append({'step': 'news_fetch', 'counts': {
                k: len(v) for k, v in news_data.items()
            }})
        except Exception as e:
            print(f"  News pipeline: {e}")
            self.session_log.append({'step': 'news_fetch', 'error': str(e)})

    def _compute_indicators(self, tickers: List[str]):
        """Compute all 47 indicators for each ticker using efficiency tiers."""
        print("[Orchestrator] Computing indicators...")

        for ticker in tickers:
            if ticker not in self.prices:
                continue

            df = self.prices[ticker]
            try:
                # Tier 1: session-static (35 indicators, ~9ms)
                tier1 = compute_all_indicators(df)  # Full compute for now
                self.indicators_cache[ticker] = tier1

                computed = sum(1 for v in tier1.values() if v is not None)
                print(f"  {ticker}: {computed}/47 indicators computed")
            except Exception as e:
                print(f"  {ticker}: indicator compute failed — {e}")

    # ── Mode Runners ─────────────────────────────────────────

    def _run_pre_market(self, tickers: List[str]):
        """M1: Pre-market briefing. All agents review data, no trading."""
        print("\n[M1] Pre-Market Briefing")
        print("-" * 40)

        # Agents that participate in M1
        m1_agents = ['A1', 'A2', 'A3', 'A4', 'A7']
        print(f"  Participating agents: {', '.join(m1_agents)}")

        for agent_id in m1_agents:
            if self.agent_states[agent_id]['suspended']:
                print(f"  {agent_id}: SUSPENDED — skipped")
                continue
            agent_def = self.config.agent_definitions.get('agents', {}).get(agent_id, {})
            print(f"  {agent_id} ({agent_def.get('name', 'Unknown')}): "
                  f"Reviewing {agent_def.get('authoritative_tables', [])}")

        # Check macro conditions
        vix = 20.0  # placeholder — would come from macro_indicators
        print(f"\n  Macro Check: VIX={vix}, Market regime assessment pending")

        # Check for overnight gaps, news events
        print(f"  Pre-market scan complete. {len(tickers)} tickers in watchlist.")

    def _run_opening(self, tickers: List[str]):
        """M2: Opening observation. First 30 minutes — no entries, just watch."""
        print("\n[M2] Opening Observation (first 30 min)")
        print("-" * 40)

        # Check for gap open (F7)
        spy_prices = self.prices.get('SPY')
        if spy_prices is not None and len(spy_prices) >= 2:
            prev_close = spy_prices['close'].iloc[-2]
            current = spy_prices['close'].iloc[-1]
            gap_pct = abs(current - prev_close) / prev_close * 100
            print(f"  SPY: prev_close={prev_close:.2f}, current={current:.2f}, gap={gap_pct:.2f}%")
            if gap_pct > 2:
                print(f"  F7 ACTIVE: Overnight gap > 2%. Blocking entries until stabilization.")

        print(f"  Monitoring {len(tickers)} tickers for opening patterns...")
        print(f"  No entries executed (observation-only mode).")

    def _run_monitoring_cycle(self, tickers: List[str]):
        """M3: Real-time 2-min monitoring cycle. Check signals, run debate, execute."""
        print("\n[M3] Real-Time Monitoring Cycle")
        print("-" * 40)

        for ticker in tickers:
            if ticker not in self.indicators_cache:
                continue

            indicators = self.indicators_cache[ticker]
            atr = indicators.get('ATR_14', 1.5) or 1.5

            # Step 1: Evaluate resonance groups
            group_results = self.resonance.evaluate_all(
                ticker, indicators, self.prices
            )
            level, count, triggered = self.resonance.determine_entry_level(group_results)

            print(f"\n  {ticker}: Resonance = {level} ({count}/5 groups: {triggered})")
            for gid, result in group_results.items():
                status = 'PASS' if result['passed'] else 'FAIL'
                print(f"    {gid}: {status} ({result['score']} components)")

            # Step 2: Check safety filters
            safety = self.safety.check_all(
                vix=20.0, recent_news=[], spy_change_pct=0.0,
                spy_volume_ratio=1.0, is_fomc_time=False,
                ticker_earnings={}, is_session_start=False,
                is_gap_open=False, sector_correlation_r2=0.5
            )

            if safety['blocked']:
                print(f"    SAFETY BLOCKED: {safety['blocked']}")
                continue

            # Step 3: If resonance >= WEAK, run debate (simulated here)
            if level in ('STRONG', 'MODERATE', 'WEAK'):
                # Run debate protocol (3 rounds)
                debate_outcome = self._run_debate(ticker, level, group_results)
                consensus_strength = debate_outcome.get('consensus_strength', 0)

                if consensus_strength >= 0.6 or level == 'STRONG':
                    # Step 4: Execute across all 5 paper accounts
                    self._execute_across_accounts(
                        ticker, level, triggered, indicators, atr, consensus_strength
                    )

            # Step 5: Check exits for existing positions
            current_prices = {t: {
                'high': self.prices[t]['high'].iloc[-1],
                'low': self.prices[t]['low'].iloc[-1],
                'close': self.prices[t]['close'].iloc[-1],
            } for t in tickers if t in self.prices}
            closed = self.paper.check_exits(current_prices)
            if closed:
                for t in closed:
                    print(f"    EXIT: {t['ticker']} @ {t['exit_price']:.2f} "
                          f"({t['exit_reason']}) P&L: ${t['pnl_dollar']:+.2f}")

    def _run_execution(self, tickers: List[str]):
        """M4: Strategy execution mode. Active trading with full agent debate."""
        print("\n[M4] Strategy Execution")
        print("-" * 40)
        # M4 is like M3 but with full agent participation (A1-A9 + DC + DV)
        self._run_monitoring_cycle(tickers)  # Same logic, full agent roster

    def _run_post_market(self, tickers: List[str]):
        """M5: Post-market review. Leaderboard, weight feedback, agent scoring."""
        print("\n[M5] Post-Market Review")
        print("-" * 40)

        # Leaderboard
        print("\n  Leaderboard:")
        print(self.paper.format_leaderboard())

        # Agent performance scoring
        print("\n  Agent Accuracy (rolling 20):")
        for agent_id, state in self.agent_states.items():
            decisions = state['decisions_last_20']
            if decisions:
                correct = sum(1 for d in decisions if d.get('was_correct'))
                acc = correct / len(decisions) * 100
                print(f"    {agent_id}: {acc:.0f}% ({correct}/{len(decisions)})")

        # Fabrication report
        if self.dv.fabrication_log:
            print(f"\n  Fabrication Events: {len(self.dv.fabrication_log)}")
            for event in self.dv.fabrication_log:
                print(f"    {event['agent_id']}: {event['violation_type']} — {event['dv_finding']}")

        # Weight feedback
        print("\n  Weight Adjustments:")

    # ── Debate Simulator ─────────────────────────────────────

    def _run_debate(self, ticker: str, entry_level: str,
                    group_results: Dict) -> Dict:
        """
        Run 3-round debate protocol (simulated).
        In production, this calls the LLM for each agent.

        Returns: {'consensus_strength': float, 'direction': str, 'agent_votes': dict}
        """
        # Round 1: Independent analysis (each agent produces opinion)
        round1 = self._debate_round1(ticker, group_results)

        # Round 2: Challenge with evidence
        round2 = self._debate_round2(round1)

        # Round 3: Synthesis and vote
        round3 = self._debate_round3(round2)

        self.debate_rounds = [round1, round2, round3]
        return round3

    def _debate_round1(self, ticker: str, group_results: Dict) -> Dict:
        """R1: Each agent independently analyzes."""
        opinions = {}
        for agent_id in ['A1', 'A2', 'A3', 'A4', 'A5', 'A7', 'A8']:
            if self.agent_states[agent_id]['muted']:
                opinions[agent_id] = {'status': 'MUTED'}
                continue
            # Simulated — in production, this calls the LLM
            opinions[agent_id] = {
                'direction': 'BULLISH',
                'conviction': 6,
                'reasoning': f"Resonance analysis for {ticker}",
                'data_cited': []
            }
        return {'round': 1, 'opinions': opinions}

    def _debate_round2(self, round1: Dict) -> Dict:
        """R2: Challenge phase — agents question each other's evidence."""
        challenges = []
        for agent_id, opinion in round1['opinions'].items():
            if opinion.get('status') == 'MUTED':
                continue
            # Simulated
            challenges.append({
                'challenger': 'DC',
                'target': agent_id,
                'question': 'Verify data source',
                'response': 'Data confirmed from technical_indicators table'
            })
        return {'round': 2, 'challenges': challenges, 'round1': round1}

    def _debate_round3(self, round2: Dict) -> Dict:
        """R3: Synthesis and final vote."""
        direction_votes = {'BULLISH': 5, 'BEARISH': 1, 'NEUTRAL': 1}
        total = sum(direction_votes.values())
        consensus = max(direction_votes, key=direction_votes.get)
        strength = direction_votes[consensus] / total if total > 0 else 0

        return {
            'round': 3,
            'consensus_direction': consensus,
            'consensus_strength': round(strength, 2),
            'vote_distribution': direction_votes,
            'agent_votes': {'A1': 'BULLISH', 'A7': 'BULLISH', 'A8': 'BULLISH'}
        }

    # ── Execution ─────────────────────────────────────────────

    def _execute_across_accounts(self, ticker: str, entry_level: str,
                                 groups: List[str], indicators: Dict,
                                 atr: float, consensus_strength: float):
        """Execute entry across all 5 paper accounts."""
        price = self.prices[ticker]['close'].iloc[-1]
        print(f"\n    Executing entry: {ticker} @ ${price:.2f} [{entry_level}]")

        for acct_id, account in self.paper.accounts.items():
            result = self.paper.execute_entry(
                account_id=acct_id,
                ticker=ticker,
                direction='LONG',
                entry_price=price,
                atr=atr,
                resonance_level=entry_level,
                resonance_groups=groups,
                consensus_strength=consensus_strength,
            )

            if result.success:
                print(f"      {account.label}: ENTERED @ ${result.fill_price:.2f}")
            else:
                print(f"      {account.label}: SKIPPED ({result.reason})")

    # ── Logging ──────────────────────────────────────────────

    def _log_session(self):
        """Log session summary."""
        summary = {
            'session_id': self.session_id,
            'mode': self.current_mode or self.detect_mode(),
            'timestamp': datetime.now().isoformat(),
            'tickers': self.watchlist,
            'paper_summary': self.paper.all_summaries(),
            'fabrication_events': len(self.dv.fabrication_log),
            'trades_executed': len(self.paper.session_trades),
        }
        self.session_log.append({'type': 'session_summary', 'data': summary})
        print(f"\n[Orchestrator] Session logged: {self.session_id}")


# ============================================================
# Quick Run
# ============================================================

if __name__ == '__main__':
    orch = Orchestrator()
    orch.run_session(tickers=['AAPL', 'MSFT', 'NVDA'])
