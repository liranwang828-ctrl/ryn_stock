"""
Paper Trading Engine v2.0
==========================
Multi-account paper trading simulator with:
- Order execution with slippage and commission
- Position tracking with staged entries
- Multi-target take-profit and trailing stops
- 8 safety filter enforcement
- Daily leaderboard and performance analytics

References: config/paper_trading.yaml, config/paper_accounts_comparison.yaml
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
import pandas as pd
import numpy as np


# ============================================================
# Data Classes
# ============================================================

@dataclass
class Position:
    ticker: str
    direction: str  # LONG / SHORT
    entry_price: float
    entry_time: datetime
    shares: float
    dollars: float
    position_pct: float
    stop_loss_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float
    tp1_pct: float = 50.0
    tp2_pct: float = 25.0
    tp3_pct: float = 25.0
    resonance_level: str = "MODERATE"
    resonance_groups: List[str] = field(default_factory=list)
    peak_price: float = 0.0
    valley_price: float = float('inf')
    candles_held: int = 0
    stages_filled: int = 1
    stop_price_s1: float = 0.0
    stop_price_s2: float = 0.0

    def update_mfe_mae(self, high: float, low: float):
        if high > self.peak_price:
            self.peak_price = high
        if low < self.valley_price:
            self.valley_price = low

    @property
    def mfe_pct(self) -> float:
        if self.direction == 'LONG':
            return (self.peak_price - self.entry_price) / self.entry_price * 100
        return (self.entry_price - self.valley_price) / self.entry_price * 100

    @property
    def mae_pct(self) -> float:
        if self.direction == 'LONG':
            return (self.valley_price - self.entry_price) / self.entry_price * 100
        return (self.entry_price - self.peak_price) / self.entry_price * 100


@dataclass
class Account:
    account_id: str
    label: str
    initial_capital: float
    entry_strictness_mult: float
    stop_loss_atr_mult: float
    take_profit_atr_mult: Dict[str, float]
    resonance_required: int
    max_position_pct: float
    max_correlated_pct: float
    staging_strategy: str
    base_risk_per_trade: float
    time_stop_candles: int
    special_rule: str = ""

    cash: float = 0.0
    equity: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)
    closed_trades: List[Dict] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)

    def __post_init__(self):
        self.cash = self.initial_capital
        self.equity = self.initial_capital
        self.equity_curve = [self.initial_capital]

    @property
    def total_return_pct(self) -> float:
        return (self.equity - self.initial_capital) / self.initial_capital * 100

    @property
    def current_drawdown_pct(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = max(self.equity_curve)
        return (peak - self.equity) / peak * 100

    @property
    def max_drawdown_pct(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for eq in self.equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @property
    def win_rate_pct(self) -> float:
        if not self.closed_trades:
            return 0.0
        wins = sum(1 for t in self.closed_trades if t['pnl_dollar'] > 0)
        return wins / len(self.closed_trades) * 100

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t['pnl_dollar'] for t in self.closed_trades if t['pnl_dollar'] > 0)
        gross_loss = abs(sum(t['pnl_dollar'] for t in self.closed_trades if t['pnl_dollar'] < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')

    @property
    def avg_r_multiple(self) -> float:
        if not self.closed_trades:
            return 0.0
        return np.mean([t.get('r_multiple', 0) for t in self.closed_trades])

    @property
    def sharpe_ratio(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
        if len(returns) < 2 or returns.std() == 0:
            return 0.0
        return float(np.mean(returns) / returns.std() * np.sqrt(252))


@dataclass
class OrderResult:
    success: bool
    trade_id: Optional[str] = None
    fill_price: Optional[float] = None
    reason: str = ""


# ============================================================
# Paper Trading Engine
# ============================================================

class PaperTradingEngine:
    """
    Multi-account paper trading simulator.

    Usage:
        engine = PaperTradingEngine()
        engine.create_accounts()  # loads from paper_accounts_comparison.yaml
        result = engine.execute_entry(account_id='PAPER_B', ticker='NVDA', ...)
        engine.check_exits(current_prices={'NVDA': 125.0})
        engine.leaderboard()
    """

    COMMISSION_RATE = 0.001   # 0.1% per trade
    SLIPPAGE_BPS = 2          # 2 bps slippage on entry, 1 bps on exit
    MIN_SLIPPAGE = 0.01       # minimum $0.01 slippage per share

    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self.session_start = datetime.now()
        self.current_prices: Dict[str, float] = {}
        self.safety_filters_active: List[str] = []
        self.market_regime: str = "ambiguous"
        self.vix_level: float = 20.0
        self.session_trades: List[Dict] = []

    def create_accounts(self, config_path: str = None):
        """Load account definitions from paper_accounts_comparison.yaml."""
        import yaml
        import os

        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                      'config', 'paper_accounts_comparison.yaml')

        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)

        for key, acct_cfg in config['accounts'].items():
            self.accounts[acct_cfg['id']] = Account(
                account_id=acct_cfg['id'],
                label=acct_cfg['label'],
                initial_capital=acct_cfg['initial_capital'],
                entry_strictness_mult=acct_cfg['entry_strictness_mult'],
                stop_loss_atr_mult=acct_cfg['stop_loss_atr_mult'],
                take_profit_atr_mult=acct_cfg['take_profit_atr_mult'],
                resonance_required=acct_cfg['resonance_required'],
                max_position_pct=acct_cfg['max_position_pct'],
                max_correlated_pct=acct_cfg['max_correlated_pct'],
                staging_strategy=acct_cfg['staging_strategy'],
                base_risk_per_trade=acct_cfg['base_risk_per_trade'],
                time_stop_candles=acct_cfg['time_stop_candles'],
                special_rule=acct_cfg.get('special_rule', '')
            )

    # ── Entry Execution ──────────────────────────────────────

    def execute_entry(self, account_id: str, ticker: str, direction: str,
                      entry_price: float, atr: float, resonance_level: str,
                      resonance_groups: List[str], consensus_strength: float,
                      agent_votes: Dict = None, obs_signal: float = 0.0) -> OrderResult:
        """
        Execute a paper trade entry for a specific account.

        Returns OrderResult with fill details.
        """
        account = self.accounts.get(account_id)
        if not account:
            return OrderResult(False, reason=f"Account {account_id} not found")

        # Safety filters — block if any CRITICAL filter active
        if any(f in self.safety_filters_active for f in ['F1', 'F2', 'F3']):
            return OrderResult(False, reason="Critical safety filter active, entry blocked")

        # Resonance minimum check (with strictness multiplier)
        min_groups = max(2, int(account.resonance_required * account.entry_strictness_mult))
        actual_groups = len(resonance_groups)
        if actual_groups < min_groups:
            return OrderResult(False,
                reason=f"Insufficient resonance: {actual_groups} < {min_groups} (required)")

        # Special rules
        if account.special_rule:
            if not self._check_special_rule(account.special_rule, ticker):
                return OrderResult(False, reason=f"Special rule not met: {account.special_rule}")

        # Position size calculation
        risk_amount = account.equity * account.base_risk_per_trade
        stop_distance = account.stop_loss_atr_mult * atr
        position_size_shares = risk_amount / max(stop_distance, 0.001)
        position_size_dollars = position_size_shares * entry_price

        # Cap by max_position_pct
        max_dollars = account.equity * account.max_position_pct
        if position_size_dollars > max_dollars:
            position_size_dollars = max_dollars
            position_size_shares = position_size_dollars / entry_price

        # Cap by available cash
        if position_size_dollars > account.cash:
            position_size_dollars = account.cash
            position_size_shares = position_size_dollars / entry_price

        # Cap by correlated exposure
        correlated_total = self._correlated_exposure(account, ticker)
        if correlated_total + position_size_dollars > account.equity * account.max_correlated_pct:
            position_size_dollars = max(0, account.equity * account.max_correlated_pct - correlated_total)
            position_size_shares = position_size_dollars / entry_price

        if position_size_dollars <= 0:
            return OrderResult(False, reason="Position size zero after limits")

        # Slippage (entry)
        slip_price = entry_price * (1 + self.SLIPPAGE_BPS / 10000)
        if direction == 'SHORT':
            slip_price = entry_price * (1 - self.SLIPPAGE_BPS / 10000)

        commission = position_size_dollars * self.COMMISSION_RATE

        # Compute stops and targets
        if direction == 'LONG':
            stop_loss = slip_price - account.stop_loss_atr_mult * atr
            tp1 = slip_price + account.take_profit_atr_mult.get('T1', 1.5) * atr
            tp2 = slip_price + account.take_profit_atr_mult.get('T2', 3.0) * atr
            tp3 = slip_price + account.take_profit_atr_mult.get('T3', 5.0) * atr
        else:
            stop_loss = slip_price + account.stop_loss_atr_mult * atr
            tp1 = slip_price - account.take_profit_atr_mult.get('T1', 1.5) * atr
            tp2 = slip_price - account.take_profit_atr_mult.get('T2', 3.0) * atr
            tp3 = slip_price - account.take_profit_atr_mult.get('T3', 5.0) * atr

        # Create position
        trade_id = f"PAPER_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        pos = Position(
            ticker=ticker,
            direction=direction,
            entry_price=slip_price,
            entry_time=datetime.now(),
            shares=position_size_shares,
            dollars=position_size_dollars,
            position_pct=position_size_dollars / account.equity * 100,
            stop_loss_price=stop_loss,
            tp1_price=tp1,
            tp2_price=tp2,
            tp3_price=tp3,
            resonance_level=resonance_level,
            resonance_groups=resonance_groups,
            peak_price=slip_price,
            valley_price=slip_price,
        )

        # Update account
        account.positions[trade_id] = pos
        account.cash -= position_size_dollars + commission

        return OrderResult(True, trade_id=trade_id, fill_price=slip_price)

    # ── Exit Checking ────────────────────────────────────────

    def check_exits(self, prices: Dict[str, Dict[str, float]]) -> List[Dict]:
        """
        Check all positions against exit conditions.
        prices: {ticker: {'open': X, 'high': X, 'low': X, 'close': X}}

        Returns list of closed trade dicts.
        """
        closed = []

        for acct_id, account in self.accounts.items():
            # Circuit breaker check (P0)
            if account.current_drawdown_pct > 6.0:
                for tid, pos in list(account.positions.items()):
                    close_data = prices.get(pos.ticker, {})
                    exit_price = close_data.get('close', pos.entry_price)
                    trade = self._close_position(account, tid, pos, exit_price,
                                                'MAX_DRAWDOWN_STOP')
                    closed.append(trade)
                continue  # all positions closed, skip individual checks

            for tid, pos in list(account.positions.items()):
                if pos.ticker not in prices:
                    continue

                bar = prices[pos.ticker]
                high, low, close = bar['high'], bar['low'], bar['close']

                pos.update_mfe_mae(high, low)
                pos.candles_held += 1
                exit_px = None
                exit_reason = None

                # P1: Hard stop loss
                if pos.direction == 'LONG':
                    if low <= pos.stop_loss_price:
                        exit_px = min(close, pos.stop_loss_price)
                        exit_reason = 'HARD_STOP_LOSS'
                else:
                    if high >= pos.stop_loss_price:
                        exit_px = max(close, pos.stop_loss_price)
                        exit_reason = 'HARD_STOP_LOSS'

                # P2: Trailing stop (moved to breakeven/T1 logic)
                if exit_reason is None and pos.peak_price > pos.tp1_price:
                    trail_level = pos.peak_price - 1.0 * self._get_atr(pos.ticker)
                    if pos.direction == 'LONG' and low <= trail_level:
                        exit_px = trail_level
                        exit_reason = 'ATR_TRAILING_STOP'
                    elif pos.direction == 'SHORT' and high >= trail_level:
                        exit_px = trail_level
                        exit_reason = 'ATR_TRAILING_STOP'

                # P3: Take profit
                if exit_reason is None:
                    if pos.direction == 'LONG':
                        if high >= pos.tp3_price and pos.tp3_pct > 0:
                            exit_px = pos.tp3_price
                            exit_reason = 'TAKE_PROFIT_T3'
                        elif high >= pos.tp2_price and pos.tp2_pct > 0:
                            exit_px = pos.tp2_price
                            exit_reason = 'TAKE_PROFIT_T2'
                        elif high >= pos.tp1_price and pos.tp1_pct > 0:
                            exit_px = pos.tp1_price
                            exit_reason = 'TAKE_PROFIT_T1'
                    else:
                        if low <= pos.tp3_price and pos.tp3_pct > 0:
                            exit_px = pos.tp3_price
                            exit_reason = 'TAKE_PROFIT_T3'
                        elif low <= pos.tp2_price and pos.tp2_pct > 0:
                            exit_px = pos.tp2_price
                            exit_reason = 'TAKE_PROFIT_T2'
                        elif low <= pos.tp1_price and pos.tp1_pct > 0:
                            exit_px = pos.tp1_price
                            exit_reason = 'TAKE_PROFIT_T1'

                # P4: Time stop
                if exit_reason is None and pos.candles_held >= account.time_stop_candles:
                    pnl_from_entry = abs(close - pos.entry_price) / pos.entry_price
                    if pnl_from_entry < 0.005:  # flat within 0.5%
                        exit_px = close
                        exit_reason = 'TIME_STOP'

                if exit_reason:
                    trade = self._close_position(account, tid, pos, exit_px, exit_reason)
                    closed.append(trade)

        # Update equity curves
        for account in self.accounts.values():
            account.equity = account.cash + sum(
                p.dollars for p in account.positions.values()
            )
            if not account.equity_curve or account.equity != account.equity_curve[-1]:
                account.equity_curve.append(account.equity)

        self.session_trades.extend(closed)
        return closed

    def _close_position(self, account: Account, trade_id: str, pos: Position,
                        exit_price: float, reason: str) -> Dict:
        """Close a position and record the trade."""
        exit_slip = exit_price * (1 - self.SLIPPAGE_BPS / 20000)  # half slippage on exit
        if pos.direction == 'SHORT':
            exit_slip = exit_price * (1 + self.SLIPPAGE_BPS / 20000)

        commission = pos.dollars * self.COMMISSION_RATE

        if pos.direction == 'LONG':
            pnl_dollar = (exit_slip - pos.entry_price) * pos.shares - commission
        else:
            pnl_dollar = (pos.entry_price - exit_slip) * pos.shares - commission

        pnl_pct = pnl_dollar / pos.dollars * 100
        risk_per_share = abs(pos.entry_price - pos.stop_loss_price)
        r_multiple = (exit_slip - pos.entry_price) / risk_per_share if risk_per_share > 0 else 0
        if pos.direction == 'SHORT':
            r_multiple = -r_multiple

        trade = {
            'trade_id': trade_id,
            'account_id': account.account_id,
            'ticker': pos.ticker,
            'direction': pos.direction,
            'entry_price': pos.entry_price,
            'entry_time': pos.entry_time.isoformat(),
            'exit_price': exit_slip,
            'exit_time': datetime.now().isoformat(),
            'exit_reason': reason,
            'pnl_pct': round(pnl_pct, 4),
            'pnl_dollar': round(pnl_dollar, 2),
            'commission_paid': round(commission, 2),
            'r_multiple': round(r_multiple, 4),
            'mae_pct': round(pos.mae_pct, 4),
            'mfe_pct': round(pos.mfe_pct, 4),
            'holding_period': f"{pos.candles_held} candles",
            'resonance_level': pos.resonance_level,
            'resonance_groups': pos.resonance_groups,
            'position_size_pct': pos.position_pct,
            'stop_loss_price': pos.stop_loss_price,
        }

        account.closed_trades.append(trade)
        account.cash += pos.dollars + pnl_dollar
        del account.positions[trade_id]
        return trade

    # ── Analytics ─────────────────────────────────────────────

    def leaderboard(self) -> pd.DataFrame:
        """Generate leaderboard DataFrame for all accounts."""
        rows = []
        for acct_id, a in self.accounts.items():
            rows.append({
                'Account': a.label,
                'Return %': round(a.total_return_pct, 2),
                'Sharpe': round(a.sharpe_ratio, 2),
                'Max DD %': round(a.max_drawdown_pct, 2),
                'Win Rate %': round(a.win_rate_pct, 1),
                'Profit Factor': round(a.profit_factor, 2),
                'Avg R': round(a.avg_r_multiple, 2),
                'Trades': len(a.closed_trades),
                'Open': len(a.positions),
                'Equity': round(a.equity, 0),
            })
        return pd.DataFrame(rows)

    def account_summary(self, account_id: str) -> Dict:
        """Detailed summary for one account."""
        a = self.accounts[account_id]
        return {
            'account_id': a.account_id,
            'label': a.label,
            'equity': a.equity,
            'cash': a.cash,
            'total_return_pct': a.total_return_pct,
            'sharpe': a.sharpe_ratio,
            'max_drawdown_pct': a.max_drawdown_pct,
            'current_drawdown_pct': a.current_drawdown_pct,
            'win_rate_pct': a.win_rate_pct,
            'profit_factor': a.profit_factor,
            'avg_r_multiple': a.avg_r_multiple,
            'open_positions': len(a.positions),
            'closed_trades': len(a.closed_trades),
            'positions': [asdict(p) for p in a.positions.values()]
        }

    def all_summaries(self) -> Dict[str, Dict]:
        return {aid: self.account_summary(aid) for aid in self.accounts}

    def format_leaderboard(self) -> str:
        """Format leaderboard as ASCII table."""
        return format_leaderboard(self)

    # ── Helpers ──────────────────────────────────────────────

    def _correlated_exposure(self, account: Account, new_ticker: str) -> float:
        """Estimate total correlated exposure for a ticker."""
        total = 0.0
        for pos in account.positions.values():
            if pos.ticker == new_ticker or self._are_correlated(pos.ticker, new_ticker):
                total += pos.dollars
        return total

    def _are_correlated(self, t1: str, t2: str) -> bool:
        """Check if two tickers are in same sector (simplified)."""
        tech = {'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'AMD', 'INTC'}
        finance = {'JPM', 'GS', 'BAC', 'MS', 'C', 'WFC'}
        energy = {'XOM', 'CVX', 'COP', 'SLB', 'EOG'}
        sectors = [tech, finance, energy]
        for s in sectors:
            if t1.upper() in s and t2.upper() in s:
                return True
        return False

    def _check_special_rule(self, rule_text: str, ticker: str) -> bool:
        """Evaluate special rules from account definitions. Simplified check."""
        # In production, this would query indicators and price data.
        # For now, always passes — the actual filtering is done by the orchestrator.
        return True

    def _get_atr(self, ticker: str) -> float:
        """Get current ATR for a ticker. Placeholder — set externally."""
        return 1.5  # default 1.5% ATR

    def set_market_state(self, prices: Dict[str, float], vix: float = 20.0,
                         safety_filters: List[str] = None, regime: str = "ambiguous"):
        self.current_prices = prices
        self.vix_level = vix
        self.safety_filters_active = safety_filters or []
        self.market_regime = regime

    def set_atr_values(self, atr_map: Dict[str, float]):
        self._atr_map = atr_map

    def _get_atr(self, ticker: str) -> float:
        if hasattr(self, '_atr_map') and ticker in self._atr_map:
            return self._atr_map[ticker]
        return 1.5


# ============================================================
# Leaderboard Formatter
# ============================================================

def format_leaderboard(engine: PaperTradingEngine) -> str:
    """Format the leaderboard as an ASCII table matching the YAML spec."""
    df = engine.leaderboard()

    lines = []
    lines.append("╔══════════════╤════════╤════════╤════════╤═══════╤════════╤══════╗")
    lines.append("║ 账号         │ 总收益  │ 夏普   │ 最大回撤│ 胜率  │ 盈亏比 │ R倍数║")
    lines.append("╠══════════════╪════════╪════════╪════════╪═══════╪════════╪══════╣")

    for _, row in df.iterrows():
        lines.append(
            f"║ {row['Account']:12s} │ "
            f"{row['Return %']:+6.1f}% │ "
            f"{row['Sharpe']:5.2f}  │ "
            f"{row['Max DD %']:-6.1f}% │ "
            f"{row['Win Rate %']:4.0f}%  │ "
            f"{row['Profit Factor']:5.1f}  │ "
            f"{row['Avg R']:4.1f}  ║"
        )

    lines.append("╚══════════════╧════════╧════════╧════════╧═══════╧════════╧══════╝")

    # Find best and worst
    if len(df) > 0:
        best_sharpe = df.loc[df['Sharpe'].idxmax()]
        worst_return = df.loc[df['Return %'].idxmin()]
        lines.append(f"  Best: {best_sharpe['Account']} (Highest Sharpe)")
        lines.append(f"  Worst: {worst_return['Account']} (Lowest Return)")

    return '\n'.join(lines)
