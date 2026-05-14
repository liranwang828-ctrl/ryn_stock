"""
Terminal Dashboard v2.0
========================
Live-updating display for the Agent Team trading system.

Shows:
- 5-account leaderboard with rankings
- Current open positions per account
- Latest signals and resonance status
- Equity curves (ASCII sparkline)
- Safety filter status
- Agent status (muted/suspended/active)
- Session summary

Usage:
    dash = Dashboard(engine)
    dash.render()

    # Live refresh (M3 mode)
    while True:
        dash.render()
        time.sleep(120)  # 2-minute cycle
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Dashboard:
    """
    Terminal dashboard for the Agent Team system.
    Pure ASCII — no external dependencies beyond pandas/numpy.
    """

    WIDTH = 80
    SEP = "─" * WIDTH
    DSEP = "═" * WIDTH

    def __init__(self, paper_engine=None, orchestrator=None):
        self.paper = paper_engine
        self.orch = orchestrator
        self.last_render = None
        self.render_count = 0

    def render(self, mode: str = "", tickers: List[str] = None,
               indicators: Dict[str, Dict] = None,
               signals: Dict[str, Dict] = None,
               safety_filters: List[str] = None):
        """Render full dashboard."""
        self.render_count += 1
        self.last_render = datetime.now()

        # Clear screen
        print("\033[2J\033[H", end="")

        self._header(mode, tickers)
        print(self.DSEP)

        # Left-right split: leaderboard | signals
        if self.paper:
            self._leaderboard()
        else:
            print("  [Paper engine not connected]")
        print()

        if signals:
            self._signals_panel(signals)
        else:
            print("  [No active signals]")
        print()

        if self.paper and self.paper.accounts:
            self._positions_panel()
        print()

        if safety_filters:
            self._safety_panel(safety_filters)
        print()

        if self.paper and self.paper.accounts:
            self._equity_sparklines()

        if self.orch:
            self._agent_status_panel()

        self._footer()

    # ── Header ────────────────────────────────────────────────

    def _header(self, mode: str, tickers: List[str]):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ticker_str = ', '.join(tickers) if tickers else 'N/A'
        print(f"  Agent Team v2.0 Dashboard  │  {now}  │  {mode or 'IDLE'}")
        print(f"  Watchlist: {ticker_str}")
        print(f"  Render #{self.render_count}")

    # ── Leaderboard ───────────────────────────────────────────

    def _leaderboard(self):
        """Print compact 5-account comparison table."""
        if not self.paper or not self.paper.accounts:
            return

        print("  ┌─ LEADERBOARD " + "─" * 60)
        print(f"  │ {'Account':<20s} {'Return':>8s} {'Sharpe':>7s} {'MaxDD':>7s} {'Win%':>6s} {'PF':>6s} {'Trades':>7s}")

        # Sort by Sharpe by default
        accounts = sorted(self.paper.accounts.values(),
                         key=lambda a: a.sharpe_ratio, reverse=True)

        for rank, a in enumerate(accounts, 1):
            medal = {1: '1st', 2: '2nd', 3: '3rd'}.get(rank, f'{rank}th')
            print(f"  │ {medal} {a.label:<16s} {a.total_return_pct:+7.2f}% "
                  f"{a.sharpe_ratio:6.2f}  {a.max_drawdown_pct:-6.2f}% "
                  f"{a.win_rate_pct:5.1f}% {a.profit_factor:5.2f}  "
                  f"{len(a.closed_trades):5d}")

        print("  └" + "─" * 62)

    # ── Signals Panel ─────────────────────────────────────────

    def _signals_panel(self, signals: Dict[str, Dict]):
        """Display current resonance signals for each ticker."""
        print("  ┌─ SIGNALS " + "─" * 67)

        for ticker, sig in signals.items():
            level = sig.get('level', 'NO_ENTRY')
            groups = sig.get('triggered_groups', [])
            symbol = {'STRONG': '★★★', 'MODERATE': '★★☆', 'WEAK': '★☆☆'}.get(level, '---')
            dir_str = sig.get('direction', '→')
            print(f"  │ {ticker:<6s} {symbol} {level:<10s} {dir_str}  Groups: {', '.join(groups) if groups else 'none'}")

        print("  └" + "─" * 67)

    # ── Positions Panel ───────────────────────────────────────

    def _positions_panel(self):
        """Show open positions across all accounts."""
        all_positions = []
        for acct in self.paper.accounts.values():
            for tid, pos in acct.positions.items():
                all_positions.append({
                    'account': acct.label,
                    'ticker': pos.ticker,
                    'direction': pos.direction,
                    'entry': pos.entry_price,
                    'pct': pos.position_pct,
                    'stop': pos.stop_loss_price,
                    'candles': pos.candles_held,
                    'mfe': pos.mfe_pct,
                    'mae': pos.mae_pct,
                })

        if not all_positions:
            print("  [No open positions]")
            return

        print("  ┌─ OPEN POSITIONS " + "─" * 58)
        print(f"  │ {'Account':<14s} {'Ticker':<6s} {'Dir':<4s} {'Entry':>8s} {'Size%':>6s} {'Stop':>8s} {'Bars':>5s} {'MFE':>6s}")
        for p in all_positions:
            print(f"  │ {p['account']:<14s} {p['ticker']:<6s} {p['direction']:<4s} "
                  f"${p['entry']:7.2f} {p['pct']:5.1f}% ${p['stop']:7.2f} "
                  f"{p['candles']:4d}  {p['mfe']:+5.1f}%")
        print("  └" + "─" * 62)

    # ── Safety Panel ──────────────────────────────────────────

    def _safety_panel(self, active_filters: List[str]):
        """Show active safety filters."""
        filter_names = {
            'F1': 'VIX Spike (>35)',
            'F2': 'Major News Shock',
            'F3': 'Circuit Breaker (SPY -5%)',
            'F4': 'Low Liquidity',
            'F5': 'FOMC Blackout',
            'F6': 'Earnings Risk',
            'F7': 'Overnight Gap',
            'F8': 'Correlation Melt-up',
        }

        if active_filters:
            print("  ╔══ SAFETY FILTERS ACTIVE ══╗")
            for f_id in active_filters:
                name = filter_names.get(f_id, f_id)
                print(f"  ║  {f_id}: {name:<40s} ║")
            print("  ╚══════════════════════════╝")
        else:
            print("  [Safety filters: CLEAR]")

    # ── Equity Sparklines ─────────────────────────────────────

    def _equity_sparklines(self):
        """ASCII sparklines of equity curves."""
        print("  ┌─ EQUITY CURVES " + "─" * 32)

        for acct_id, acct in sorted(self.paper.accounts.items()):
            curve = acct.equity_curve
            if len(curve) < 2:
                continue

            # Sample to fit in 40 chars
            sampled = self._sample_curve(curve, 40)
            spark = self._make_sparkline(sampled)

            ret = acct.total_return_pct
            print(f"  │ {acct.label:<14s} {spark}  {ret:+6.2f}%")

        print("  └" + "─" * 62)

    def _sample_curve(self, values: List[float], n: int) -> List[float]:
        """Downsample a list to n evenly-spaced values."""
        if len(values) <= n:
            return values
        step = len(values) / n
        return [values[int(i * step)] for i in range(n)]

    def _make_sparkline(self, values: List[float]) -> str:
        """Create a Unicode sparkline from a list of values."""
        if not values or len(values) < 2:
            return ''

        mn, mx = min(values), max(values)
        if mn == mx:
            return '─' * len(values)

        chars = ' ▁▂▃▄▅▆▇█'
        result = ''
        for v in values:
            idx = int((v - mn) / (mx - mn) * (len(chars) - 1))
            result += chars[min(idx, len(chars) - 1)]
        return result

    # ── Agent Status ──────────────────────────────────────────

    def _agent_status_panel(self):
        """Show agent states: active, muted, suspended."""
        if not self.orch:
            return

        print("  ┌─ AGENT STATUS " + "─" * 30)

        statuses = []
        for agent_id, state in sorted(self.orch.agent_states.items()):
            if state['suspended']:
                status = '⛔ SUSPENDED'
            elif state['muted']:
                status = '🔇 MUTED'
            else:
                status = '✅ ACTIVE'

            acc = state.get('D_accuracy', 1.0)
            statuses.append(f"  │ {agent_id}: {status:<15s}  Acc: {acc:.2f}")

        # Show 4 per row layout
        for s in statuses:
            print(s)

        print("  └" + "─" * 62)

    # ── Session Summary (M5) ─────────────────────────────────

    def render_post_market(self):
        """Render comprehensive post-market review."""
        self.render(mode='M5_POST_MARKET')

        if not self.paper:
            return

        print(f"\n  {'='*60}")
        print(f"  POST-MARKET SUMMARY")
        print(f"  {'='*60}")

        # Trade log
        all_trades = []
        for acct in self.paper.accounts.values():
            all_trades.extend(acct.closed_trades)

        if all_trades:
            print(f"\n  Today's Trades: {len(all_trades)}")
            df_trades = pd.DataFrame(all_trades)
            if 'pnl_dollar' in df_trades.columns:
                total_pnl = df_trades['pnl_dollar'].sum()
                print(f"  Total P&L: ${total_pnl:+,.2f}")

                # By exit reason
                print(f"\n  Exit Breakdown:")
                for reason, group in df_trades.groupby('exit_reason'):
                    count = len(group)
                    pnl = group['pnl_dollar'].sum()
                    print(f"    {reason:<25s}: {count:3d} trades, ${pnl:+,.2f}")

        # Best/worst trade
        if all_trades:
            best = max(all_trades, key=lambda t: t.get('pnl_pct', -999))
            worst = min(all_trades, key=lambda t: t.get('pnl_pct', 999))
            print(f"\n  Best Trade:  {best['ticker']} {best['pnl_pct']:+.2f}% ({best['exit_reason']})")
            print(f"  Worst Trade: {worst['ticker']} {worst['pnl_pct']:+.2f}% ({worst['exit_reason']})")

        # Weight adjustment recommendations
        print(f"\n  Weight Recommendations:")
        best_acct = max(self.paper.accounts.values(),
                       key=lambda a: a.sharpe_ratio)
        print(f"    Suggest adopting {best_acct.label} parameters:")
        print(f"      entry_strictness = {best_acct.entry_strictness_mult}")
        print(f"      stop_atr_mult    = {best_acct.stop_loss_atr_mult}")
        print(f"      resonance_min    = {best_acct.resonance_required}")

    # ── Footer ────────────────────────────────────────────────

    def _footer(self):
        print(f"\n  {'─'*60}")
        if self.last_render:
            print(f"  Last update: {self.last_render.strftime('%H:%M:%S')}  "
                  f"|  Ctrl+C to exit  |  /help for commands")


# ============================================================
# Live Monitor
# ============================================================

def live_monitor(orchestrator, tickers: List[str], interval_seconds: int = 120):
    """
    Run a live monitoring loop with dashboard refresh.
    For M3 real-time monitoring mode.

    Args:
        orchestrator: Configured Orchestrator instance
        tickers: Watchlist
        interval_seconds: Refresh interval (default 120s for M3 2-min cycle)
    """
    dash = Dashboard(paper_engine=orchestrator.paper, orchestrator=orchestrator)

    print("[Dashboard] Live monitor started. Press Ctrl+C to stop.")
    print(f"[Dashboard] Refreshing every {interval_seconds}s")

    try:
        while True:
            # Run one monitoring cycle
            orchestrator._run_monitoring_cycle(tickers)

            # Build signals dict for display
            signals = {}
            for ticker in tickers:
                if ticker in orchestrator.indicators_cache:
                    indicators = orchestrator.indicators_cache[ticker]
                    group_results = orchestrator.resonance.evaluate_all(
                        ticker, indicators, orchestrator.prices
                    )
                    level, count, triggered = orchestrator.resonance.determine_entry_level(group_results)
                    signals[ticker] = {
                        'level': level,
                        'triggered_groups': triggered,
                        'direction': 'LONG'
                    }

            # Render dashboard
            safety = orchestrator.safety.check_all(
                vix=20.0, recent_news=[], spy_change_pct=0.0,
                spy_volume_ratio=1.0, is_fomc_time=False,
                ticker_earnings={}, is_session_start=False,
                is_gap_open=False, sector_correlation_r2=0.5
            )

            dash.render(
                mode='M3_MONITORING',
                tickers=tickers,
                signals=signals,
                safety_filters=safety['active']
            )

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n[Dashboard] Monitor stopped.")


# ============================================================
# Quick Test
# ============================================================

if __name__ == '__main__':
    # Test with paper engine
    from engine.paper_engine import PaperTradingEngine

    engine = PaperTradingEngine()
    engine.create_accounts()

    # Simulate some trades for display
    dash = Dashboard(paper_engine=engine)
    dash.render(
        mode='TEST',
        tickers=['NVDA', 'AAPL', 'MSFT'],
        signals={
            'NVDA': {'level': 'STRONG', 'triggered_groups': ['G_PRICE', 'G_TECH', 'G_SECTOR', 'G_MACRO'], 'direction': 'LONG'},
            'AAPL': {'level': 'MODERATE', 'triggered_groups': ['G_PRICE', 'G_TECH', 'G_MACRO'], 'direction': 'LONG'},
            'MSFT': {'level': 'NO_ENTRY', 'triggered_groups': [], 'direction': 'NEUTRAL'},
        },
        safety_filters=[]
    )
