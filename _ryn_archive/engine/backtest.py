"""
Backtest Framework v2.0
========================
Walk-forward historical replay across all 5 paper trading accounts.

Usage:
    bt = BacktestRunner()
    results = bt.run(tickers=['NVDA', 'AAPL'], period='6mo')
    bt.report(results)
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.compute_indicators import compute_all_indicators
from indicators.data_fetcher import DataFetcher
from engine.paper_engine import PaperTradingEngine
from engine.orchestrator import ResonanceEngine, SafetyFilterEngine


@dataclass
class BacktestResult:
    ticker: str = ""
    account_results: Dict[str, Dict] = field(default_factory=dict)
    benchmark_return: float = 0.0
    total_bars: int = 0
    signals_generated: int = 0
    trades_executed: int = 0

    @property
    def best_account(self) -> str:
        if not self.account_results:
            return ''
        return max(self.account_results,
                  key=lambda a: self.account_results[a].get('total_return_pct', -999))

    @property
    def worst_account(self) -> str:
        if not self.account_results:
            return ''
        return min(self.account_results,
                  key=lambda a: self.account_results[a].get('total_return_pct', 999))


class BacktestRunner:
    """
    Walk-forward backtest engine.

    For each bar in the historical data:
    1. Compute indicators (with lookback warmup)
    2. Evaluate resonance groups
    3. Check safety filters
    4. If signal: execute paper trade across all 5 accounts
    5. Check exits at each bar
    6. Track equity curves
    """

    WARMUP_BARS = 50  # minimum bars before first trade

    def __init__(self):
        self.fetcher = DataFetcher()
        self.resonance = None
        self.safety = None
        self.engine = None

    def run(self, tickers: List[str], period: str = '6mo',
            interval: str = '1d') -> BacktestResult:
        """
        Run backtest for a list of tickers.

        Args:
            tickers: Stock symbols
            period: Lookback period (Yahoo Finance format)
            interval: Bar interval ('1d' for swing, '1h' or '15m' for intraday)

        Returns:
            BacktestResult with per-account metrics
        """
        print(f"\n{'='*60}")
        print(f"  Backtest: {', '.join(tickers)}  |  {period}  |  {interval}")
        print(f"{'='*60}")

        # Load configs for resonance and safety engines
        self._load_configs()

        # Fetch data
        data = {}
        for ticker in tickers:
            try:
                df = self.fetcher.get_ohlcv(ticker, period=period, interval=interval)
                if not df.empty:
                    data[ticker] = df
                    print(f"  {ticker}: {len(df)} bars")
            except Exception as e:
                print(f"  {ticker}: FETCH FAILED — {e}")

        if not data:
            print("[Backtest] No data available. Aborting.")
            return BacktestResult()

        # Align all DataFrames to common date range
        common_idx = None
        for df in data.values():
            if common_idx is None:
                common_idx = set(df.index)
            else:
                common_idx &= set(df.index)
        common_idx = sorted(common_idx)

        if len(common_idx) < self.WARMUP_BARS + 10:
            print(f"[Backtest] Insufficient data: {len(common_idx)} bars. Need {self.WARMUP_BARS + 10}+")
            return BacktestResult()

        # Align data
        for ticker in data:
            data[ticker] = data[ticker].loc[data[ticker].index.isin(common_idx)]

        # Initialize paper engine
        self.engine = PaperTradingEngine()
        self.engine.create_accounts()

        # Main walk-forward loop
        total_signals = 0
        total_trades = 0
        benchmark_returns = []

        for i in range(self.WARMUP_BARS, len(common_idx)):
            current_date = common_idx[i]
            window_start = common_idx[max(0, i - 100)]  # 100-bar lookback for indicators

            for ticker, df in data.items():
                # Slice data up to current bar (no lookahead)
                window = df.loc[window_start:current_date].copy()

                if len(window) < 20:  # minimum for most indicators
                    continue

                try:
                    indicators = compute_all_indicators(window)
                except Exception:
                    continue

                current_bar = df.loc[current_date]
                current_price = current_bar['close']
                atr = indicators.get('ATR_14', current_price * 0.02) or current_price * 0.02

                # Evaluate resonance
                group_results = self.resonance.evaluate_all(
                    ticker, indicators, {ticker: window}
                )
                level, count, triggered = self.resonance.determine_entry_level(group_results)

                # Safety check
                safety = self.safety.check_all(
                    vix=20.0, recent_news=[], spy_change_pct=0.0,
                    spy_volume_ratio=1.0, is_fomc_time=False,
                    ticker_earnings={}, is_session_start=False,
                    is_gap_open=False, sector_correlation_r2=0.5
                )

                if safety['blocked']:
                    continue

                if level in ('STRONG', 'MODERATE', 'WEAK') and count >= 2:
                    total_signals += 1

                    # Execute across all accounts
                    for acct_id in self.engine.accounts:
                        result = self.engine.execute_entry(
                            account_id=acct_id,
                            ticker=ticker,
                            direction='LONG',
                            entry_price=float(current_price),
                            atr=float(atr),
                            resonance_level=level,
                            resonance_groups=triggered,
                            consensus_strength=0.5 if level == 'WEAK' else 0.7
                        )
                        if result.success:
                            total_trades += 1

                # Check exits: update with current bar's OHLC
                prices = {
                    ticker: {
                        'high': float(current_bar['high']),
                        'low': float(current_bar['low']),
                        'close': float(current_price),
                    }
                }
                self.engine.set_market_state(prices)
                closed = self.engine.check_exits(prices)

            # Benchmark: SPY buy-and-hold
            if 'SPY' in data:
                spy_start = data['SPY']['close'].iloc[self.WARMUP_BARS]
                spy_current = data['SPY']['close'].iloc[i]
                benchmark_returns.append((spy_current - spy_start) / spy_start * 100)

        # Build result
        result = BacktestResult(
            ticker=','.join(tickers),
            total_bars=len(common_idx) - self.WARMUP_BARS,
            signals_generated=total_signals,
            trades_executed=total_trades,
            benchmark_return=benchmark_returns[-1] if benchmark_returns else 0.0,
        )

        for acct_id, account in self.engine.accounts.items():
            result.account_results[acct_id] = {
                'label': account.label,
                'total_return_pct': account.total_return_pct,
                'sharpe': account.sharpe_ratio,
                'max_drawdown_pct': account.max_drawdown_pct,
                'win_rate_pct': account.win_rate_pct,
                'profit_factor': account.profit_factor,
                'avg_r_multiple': account.avg_r_multiple,
                'total_trades': len(account.closed_trades),
                'final_equity': account.equity,
                'special_rule': account.special_rule,
            }

        return result

    def report(self, result: BacktestResult):
        """Print formatted backtest report."""
        print(f"\n{'='*60}")
        print(f"  BACKTEST RESULTS")
        print(f"  Ticker(s): {result.ticker}")
        print(f"  Period: {result.total_bars} bars")
        print(f"  Signals: {result.signals_generated} | Trades: {result.trades_executed}")
        print(f"  Benchmark (SPY): {result.benchmark_return:+.2f}%")
        print(f"{'='*60}")

        # Header
        print(f"\n{'Account':<16s} {'Return':>8s} {'Sharpe':>7s} {'MaxDD':>7s} "
              f"{'Win%':>6s} {'PF':>6s} {'AvgR':>6s} {'Trades':>7s}")

        for acct_id, r in sorted(result.account_results.items()):
            print(f"{r['label']:<16s} {r['total_return_pct']:+7.2f}% "
                  f"{r['sharpe']:6.2f}  {r['max_drawdown_pct']:-6.2f}% "
                  f"{r['win_rate_pct']:5.1f}% {r['profit_factor']:5.2f} "
                  f"{r['avg_r_multiple']:5.2f}  {r['total_trades']:5d}")

        # Best/worst
        print(f"\n  Best:  {self.engine.accounts[result.best_account].label} "
              f"(+{result.account_results[result.best_account]['total_return_pct']:.2f}%)")
        print(f"  Worst: {self.engine.accounts[result.worst_account].label} "
              f"({result.account_results[result.worst_account]['total_return_pct']:+.2f}%)")
        print(f"  vs SPY: {result.account_results[result.best_account]['total_return_pct'] - result.benchmark_return:+.2f}% alpha")

    def _load_configs(self):
        """Load strategy configs for signal generation."""
        import yaml
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

        with open(os.path.join(config_dir, 'trading_strategy.yaml'), encoding='utf-8') as f:
            strategy = yaml.safe_load(f)

        self.resonance = ResonanceEngine(strategy)
        self.safety = SafetyFilterEngine(strategy)

    # ── Grid Sweep (parameter optimization) ──────────────────

    def grid_sweep(self, tickers: List[str], period: str = '2mo',
                   entry_range: Tuple[float, float, float] = (0.5, 2.0, 0.25),
                   stop_range: Tuple[float, float, float] = (1.0, 4.0, 0.5),
                   tp_range: Tuple[float, float, float] = (1.0, 3.0, 0.5)) -> pd.DataFrame:
        """
        Run parameter sweep across entry_strictness, stop_atr, and take_profit T1.
        Returns DataFrame with all combinations ranked by Sharpe.
        """
        print(f"\n{'='*60}")
        print(f"  GRID SWEEP: {', '.join(tickers)}  |  {period}")
        print(f"  Entry: [{entry_range[0]}, {entry_range[1]}] step={entry_range[2]}")
        print(f"  Stop:  [{stop_range[0]}, {stop_range[1]}] step={stop_range[2]}")
        print(f"  TP T1: [{tp_range[0]}, {tp_range[1]}] step={tp_range[2]}")
        print(f"{'='*60}")

        entry_vals = list(np.arange(*entry_range))
        stop_vals = list(np.arange(*stop_range))
        tp_vals = list(np.arange(*tp_range))

        total_combos = len(entry_vals) * len(stop_vals) * len(tp_vals)
        print(f"  Total combinations: {total_combos}")

        results = []
        count = 0

        for entry_mult in entry_vals:
            for stop_mult in stop_vals:
                for tp_t1 in tp_vals:
                    count += 1
                    if count % 10 == 0:
                        print(f"    {count}/{total_combos}...")

                    # Create temporary engine with these params
                    bt = BacktestRunner()
                    bt._load_configs()

                    # Override account B (balanced) parameters
                    bt.engine = PaperTradingEngine()

                    # Create single account with sweep params
                    from engine.paper_engine import Account
                    acct = Account(
                        account_id='SWEEP',
                        label='Grid Sweep',
                        initial_capital=100000,
                        entry_strictness_mult=round(entry_mult, 2),
                        stop_loss_atr_mult=round(stop_mult, 2),
                        take_profit_atr_mult={'T1': round(tp_t1, 2), 'T2': round(tp_t1 * 2, 2), 'T3': round(tp_t1 * 4, 2)},
                        resonance_required=3,
                        max_position_pct=0.25,
                        max_correlated_pct=0.40,
                        staging_strategy='pyramiding',
                        base_risk_per_trade=0.02,
                        time_stop_candles=8,
                    )
                    bt.engine.accounts = {'SWEEP': acct}

                    # Run quick backtest
                    try:
                        result = bt.run(tickers, period=period, interval='1d')
                        if 'SWEEP' in result.account_results:
                            r = result.account_results['SWEEP']
                            results.append({
                                'entry_strictness': round(entry_mult, 2),
                                'stop_atr_mult': round(stop_mult, 2),
                                'tp_t1_atr': round(tp_t1, 2),
                                'return_pct': r['total_return_pct'],
                                'sharpe': r['sharpe'],
                                'max_dd_pct': r['max_drawdown_pct'],
                                'win_rate_pct': r['win_rate_pct'],
                                'profit_factor': r['profit_factor'],
                                'trades': r['total_trades'],
                            })
                    except Exception as e:
                        print(f"      Failed: {e}")
                        continue

        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values('sharpe', ascending=False)
        return df


# ============================================================
# Quick Run
# ============================================================

if __name__ == '__main__':
    runner = BacktestRunner()
    result = runner.run(tickers=['AAPL', 'MSFT'], period='3mo', interval='1d')
    runner.report(result)
