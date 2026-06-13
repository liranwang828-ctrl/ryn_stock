import sys
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Ensure UTF-8 Console Printing
sys.stdout.reconfigure(encoding='utf-8')

# Import DataFeatureBroker from the joint backtest engine
sys.path.append(os.path.dirname(__file__))
from stock_team.backtest.joint_backtest_engine import DataFeatureBroker

class WeeklyRebalanceEngine:
    def __init__(self, tickers, initial_cash=100000.0, fee_rate=0.0003, verbose=True,
                 use_breathing_stop_guard=True, use_monday_gap_guard=True,
                 monday_gap_threshold=-0.02, qqq_gap_threshold=-0.015,
                 breathing_profit_threshold=10.0, hwm_stop_loss_pct=0.08,
                 custom_slippage_rate=0.0005, waterfall_slippage_rate=0.015,
                 hwm_slippage_rate=0.005, latency_minutes=0,
                 orthogonalize_factors=False,
                 use_double_pool=False,
                 core_tickers=None,
                 core_ratio=0.60,
                 min_core_factor_score=-0.15,
                 core_downsize_pct=0.30):
        self.tickers = tickers
        self.initial_cash = initial_cash
        self.fee_rate = fee_rate
        self.verbose = verbose
        self.use_breathing_stop_guard = use_breathing_stop_guard
        self.use_monday_gap_guard = use_monday_gap_guard
        self.monday_gap_threshold = monday_gap_threshold
        self.qqq_gap_threshold = qqq_gap_threshold
        self.breathing_profit_threshold = breathing_profit_threshold
        self.hwm_stop_loss_pct = hwm_stop_loss_pct
        self.orthogonalize_factors = orthogonalize_factors
        
        # Institutional parameters for slippage & execution latency sweeps
        self.custom_slippage_rate = custom_slippage_rate
        self.waterfall_slippage_rate = waterfall_slippage_rate
        self.hwm_slippage_rate = hwm_slippage_rate
        self.latency_minutes = latency_minutes
        
        self.broker = DataFeatureBroker()
        self.daily_sgov_rate = 0.05 / 252  # Annualized 5% SGOV interest
        
        # Portfolio state
        self.cash = initial_cash
        self.positions = {}  # {ticker: {"shares": float, "cost": float, "highest_close": float, "atr": float}}
        self.trades_log = []
        self.equity_curve = []
        
        # Double pool attributes
        self.use_double_pool = use_double_pool
        self.core_tickers = core_tickers if core_tickers is not None else ["NVDA", "COHR", "MSFT", "GOOGL", "IAU"]
        self.core_ratio = core_ratio
        self.min_core_factor_score = min_core_factor_score
        self.core_downsize_pct = core_downsize_pct
        self.core_cash = 0.0  # Isolated cash belonging to the Core Pool
        self.tactical_cash = initial_cash  # Tactical pool cash
        
    def load_all_data(self, days=1825):
        """
        Load daily and intraday data for all tickers, QQQ and VIX.
        """
        # Skip loading if already pre-loaded to avoid massive I/O bottleneck in parameter sweeps
        if hasattr(self, 'daily_data') and self.daily_data and hasattr(self, 'intraday_data') and self.intraday_data:
            if self.verbose:
                print("📡 检测到内存中已存在预载数据，跳过物理磁盘加载。")
            return

        if self.verbose:
            print("📡 正在获取/加载所有标的的日线与日内缓存数据...")
            
        self.daily_data = {}
        self.intraday_data = {}
        
        # Load daily data for ranking
        for t in self.tickers:
            df = self.broker.get_daily_indicators(t)
            if not df.empty:
                df.index = pd.to_datetime(df.index).tz_localize(None)
                self.daily_data[t] = df
                
        # Load QQQ daily index as benchmark
        self.qqq_daily = self.broker.get_daily_indicators("QQQ")
        if not self.qqq_daily.empty:
            self.qqq_daily.index = pd.to_datetime(self.qqq_daily.index).tz_localize(None)
            
        # Load VIX daily index for risk sizing
        self.vix_daily = self.broker.get_daily_indicators("^VIX")
        if not self.vix_daily.empty:
            self.vix_daily.index = pd.to_datetime(self.vix_daily.index).tz_localize(None)
            
        # Load intraday 5-min data for Monday tactical entry
        for t in self.tickers:
            df = self.broker.process_and_merge(t, days=days)
            if not df.empty:
                df.index = pd.to_datetime(df.index).tz_localize(None)
                # Pre-split by date into a dict to speed up weekly query by 50,000x
                self.intraday_data[t] = {d: grp for d, grp in df.groupby(df.index.date)}
                
    def calculate_factors(self, date):
        """
        Calculate relative strength and vol-price correlation for all tickers on Friday.
        """
        # Get QQQ 50-day return on this date
        qqq_df = self.qqq_daily
        qqq_past = qqq_df[qqq_df.index <= date]
        if len(qqq_past) < 51:
            return {}
            
        qqq_close_today = qqq_past['Close'].iloc[-1]
        qqq_close_prev = qqq_past['Close'].iloc[-51]
        qqq_ret_50d = (qqq_close_today - qqq_close_prev) / qqq_close_prev
        qqq_ret_50d_abs = abs(qqq_ret_50d) if abs(qqq_ret_50d) > 0.005 else 0.005
        
        # Load VIX to determine if it's a bull market
        vix_past = self.vix_daily[self.vix_daily.index <= date] if not self.vix_daily.empty else pd.DataFrame()
        vix_val = vix_past['Close'].iloc[-1] if not vix_past.empty else 18.0
        
        # Bull market is defined by VIX < 18
        is_bull_market = vix_val < 18.0
        defensive_value_tickers = {'XOM', 'CVX', 'COP', 'JNJ', 'PFE', 'MRK', 'ABBV', 'NEE', 'AMT', 'PG', 'KO', 'PEP', 'BAC', 'MS', 'GS', 'UNH', 'JPM'}
        
        raw_candidates = {}
        
        for t, df in self.daily_data.items():
            past = df[df.index <= date]
            if len(past) < 51:
                continue
                
            # Filter out style drag / defensive value stocks during bull markets
            if is_bull_market and t in defensive_value_tickers:
                continue
                
            row = past.iloc[-1]
            stage_2 = row.get('Stage_2', 0)
            
            # Master-Level Offensive Upgrade: Multi-Scale Relative Strength & Momentum Acceleration
            close_today = row['Close']
            
            # Stock multi-scale returns
            close_prev_10 = past['Close'].iloc[-11] if len(past) >= 11 else past['Close'].iloc[-1]
            close_prev_20 = past['Close'].iloc[-21] if len(past) >= 21 else past['Close'].iloc[-1]
            close_prev_50 = past['Close'].iloc[-51] if len(past) >= 51 else past['Close'].iloc[-1]
            
            ret_10 = (close_today - close_prev_10) / close_prev_10 if close_prev_10 > 0 else 0.0
            ret_20 = (close_today - close_prev_20) / close_prev_20 if close_prev_20 > 0 else 0.0
            ret_50 = (close_today - close_prev_50) / close_prev_50 if close_prev_50 > 0 else 0.0
            
            # QQQ multi-scale returns
            qqq_close_10 = qqq_past['Close'].iloc[-11] if len(qqq_past) >= 11 else qqq_past['Close'].iloc[-1]
            qqq_close_20 = qqq_past['Close'].iloc[-21] if len(qqq_past) >= 21 else qqq_past['Close'].iloc[-1]
            qqq_close_50 = qqq_past['Close'].iloc[-51] if len(qqq_past) >= 51 else qqq_past['Close'].iloc[-1]
            
            q_ret_10 = (qqq_close_today - qqq_close_10) / qqq_close_10 if qqq_close_10 > 0 else 0.005
            q_ret_20 = (qqq_close_today - qqq_close_20) / qqq_close_20 if qqq_close_20 > 0 else 0.005
            q_ret_50 = (qqq_close_today - qqq_close_50) / qqq_close_50 if qqq_close_50 > 0 else 0.005
            
            rs_10 = ret_10 / (abs(q_ret_10) if abs(q_ret_10) > 0.005 else 0.005)
            rs_20 = ret_20 / (abs(q_ret_20) if abs(q_ret_20) > 0.005 else 0.005)
            rs_50 = ret_50 / (abs(q_ret_50) if abs(q_ret_50) > 0.005 else 0.005)
            
            # Weighted RS score (More responsive to acceleration)
            rs_score = 0.2 * rs_10 + 0.3 * rs_20 + 0.5 * rs_50
            rs_score = np.clip(rs_score, -5.0, 5.0)
            
            # Momentum Acceleration Bonus: 20% booster for accelerating winners
            boost_factor = 1.0
            if rs_10 > rs_50 > 0:
                boost_factor = 1.20
            
            # Factor 2: Rolling 20-day price-volume correlation
            past_20 = past.tail(20)
            price_pct = past_20['Close'].pct_change()
            vol_pct = past_20['Volume'].pct_change()
            vol_price_corr = price_pct.corr(vol_pct)
            if np.isnan(vol_price_corr):
                vol_price_corr = 0.0
                
            # Compute rolling 20-day daily standard deviation (volatility) for Beta-adjusted HWM stop
            daily_vol = price_pct.std()
            if np.isnan(daily_vol) or daily_vol == 0:
                daily_vol = 0.015  # Fallback to 1.5%
            # Dynamic HWM trailing stop percentage (3 * daily_vol * sqrt(5))
            hwm_trail = np.clip(3.0 * daily_vol * np.sqrt(5), 0.08, 0.20)
            
            # We ONLY select stocks that are currently in Stage 2
            if stage_2 == 1:
                raw_candidates[t] = {
                    "rs_score": rs_score,
                    "corr": vol_price_corr,
                    "close": close_today,
                    "atr": past['Close'].diff().abs().rolling(14).mean().iloc[-1],
                    "hwm_trail": hwm_trail,
                    "boost_factor": boost_factor
                }
                
        # Symmetric Orthogonalization of Factor Matrix if enabled
        if self.orthogonalize_factors and len(raw_candidates) >= 2:
            tickers_list = list(raw_candidates.keys())
            # N x 2 matrix
            X = np.array([[raw_candidates[t]["rs_score"], raw_candidates[t]["corr"]] for t in tickers_list])
            
            # Mean normalization
            X_mean = X.mean(axis=0)
            X_std = X.std(axis=0)
            X_std[X_std == 0] = 1e-8
            X_norm = (X - X_mean) / X_std
            
            # Compute covariance / correlation matrix
            sigma = np.dot(X_norm.T, X_norm)
            try:
                eigenvalues, eigenvectors = np.linalg.eigh(sigma)
                eigenvalues = np.maximum(eigenvalues, 1e-9)
                D_inv_half = np.diag(1.0 / np.sqrt(eigenvalues))
                S = np.dot(np.dot(eigenvectors, D_inv_half), eigenvectors.T)
                X_orth = np.dot(X_norm, S)
                
                # Unpack back to candidates
                for idx, t in enumerate(tickers_list):
                    raw_candidates[t]["rs_score_orth"] = X_orth[idx, 0]
                    raw_candidates[t]["corr_orth"] = X_orth[idx, 1]
            except Exception:
                # Fallback to unorthogonalized on linear algebra error
                for t in tickers_list:
                    raw_candidates[t]["rs_score_orth"] = raw_candidates[t]["rs_score"]
                    raw_candidates[t]["corr_orth"] = raw_candidates[t]["corr"]
        else:
            for t in raw_candidates:
                raw_candidates[t]["rs_score_orth"] = raw_candidates[t]["rs_score"]
                raw_candidates[t]["corr_orth"] = raw_candidates[t]["corr"]
                
        # Compute final scores using orthogonalized pure factors
        scores = {}
        for t, val in raw_candidates.items():
            rs_eff = val["rs_score_orth"]
            corr_eff = val["corr_orth"]
            
            score = (0.8 * rs_eff + 0.2 * corr_eff) * val["boost_factor"]
            scores[t] = {
                "score": score,
                "rs_score": val["rs_score"],
                "corr": val["corr"],
                "close": val["close"],
                "atr": val["atr"],
                "hwm_trail": val["hwm_trail"]
            }
            
        return scores

    def run_backtest(self, start_date_str="2021-06-01", end_date_str="2026-05-30", K=5):
        """
        Execute the weekly rebalancing backtest.
        """
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime(end_date_str)
        
        self.load_all_data()
        
        # Find all trading days from QQQ
        trading_days = sorted(list(self.qqq_daily[(self.qqq_daily.index >= start_date) & (self.qqq_daily.index <= end_date)].index))
        
        if not trading_days:
            print("🔴 无有效交易日，回测终止。")
            return
            
        # If double pool is active, pre-allocate core holdings and split cash
        if self.use_double_pool:
            total_core_capital = self.initial_cash * self.core_ratio
            self.core_cash = 0.0
            self.tactical_cash = self.initial_cash * (1.0 - self.core_ratio)
            self.cash = self.tactical_cash
            
            # Divide core capital equally among available core tickers
            active_cores = [c for c in self.core_tickers if c in self.daily_data]
            if active_cores:
                capital_per_core = total_core_capital / len(active_cores)
                start_d = trading_days[0]
                for c in active_cores:
                    c_df = self.daily_data[c]
                    past_c = c_df[c_df.index <= start_d]
                    if not past_c.empty:
                        start_price = past_c['Close'].iloc[-1]
                        c_shares = capital_per_core / start_price
                        self.positions[c] = {
                            "shares": c_shares,
                            "cost": start_price,
                            "highest_close": start_price,
                            "atr": c_df['Close'].diff().abs().rolling(14).mean().loc[past_c.index[-1]] if len(past_c) >= 14 else start_price * 0.03,
                            "hwm_trail": 0.12,
                            "entry_date": start_d,
                            "pool": "core",
                            "downsized": False,
                            "target_shares": c_shares
                        }
                        if self.verbose:
                            print(f"🏰 [双池初始化] 轨一核心仓建仓: {c} 买入 {c_shares:.1f} 股 @ ${start_price:.2f} (分配资金: ${capital_per_core:.2f})")
            
        current_portfolio_value = self.cash
        self.equity_curve = [{"Timestamp": trading_days[0], "Equity": self.cash}]
        
        # Group trading days by calendar week (we rebalance on the first trading day of the week, i.e., Monday,
        # based on the factors calculated on the last trading day of the previous week, i.e., Friday)
        weeks = {}
        for d in trading_days:
            year, week, _ = d.isocalendar()
            week_key = (year, week)
            if week_key not in weeks:
                weeks[week_key] = []
            weeks[week_key].append(d)
            
        sorted_week_keys = sorted(list(weeks.keys()))
        
        if self.verbose:
            print(f"📊 规划完成。模拟周数: {len(sorted_week_keys)} 周，总计交易天数: {len(trading_days)} 天")
            
        # Keep track of active positions
        # self.positions = {ticker: {"shares": float, "cost": float, "highest_close": float, "atr": float}}
        
        for w_idx in range(len(sorted_week_keys)):
            week_key = sorted_week_keys[w_idx]
            week_days = weeks[week_key]
            
            # 1. Execute Daily Simulation inside the current week
            for d in week_days:
                # Accrue SGOV Cash Interest Daily
                self.cash *= (1.0 + self.daily_sgov_rate)
                if self.use_double_pool:
                    self.core_cash *= (1.0 + self.daily_sgov_rate)
                
                # Check mid-week stop-losses on daily Close/Low
                active_tickers = list(self.positions.keys())
                for t in active_tickers:
                    pos = self.positions[t]
                    # Core Pool holdings are protected from short-term daily stops (long-only lock)
                    if self.use_double_pool and pos.get("pool") == "core":
                        continue
                    if t not in self.daily_data:
                        continue
                    day_rows = self.daily_data[t][self.daily_data[t].index == d]
                    if day_rows.empty:
                        continue
                    row = day_rows.iloc[0]
                    pos = self.positions[t]
                    
                    # 【修复 temporal alignment 假止损】: 
                    # 如果当前模拟日 d 就是建仓/加仓首日，且 Low 发生在建仓前，采用安全保护：
                    # 仅在建仓首日使用 Close 校验止损，次日开始恢复常规 Low 校验
                    entry_date = pos.get("entry_date", d)
                    check_low_price = row["Close"] if d == entry_date else row["Low"]
                    
                    # Stop-loss checks (必须在更新 highest_close 之前使用昨日 peak close 算止损线，防 Look-Ahead)
                    hwm_trail_val = pos.get("hwm_trail", self.hwm_stop_loss_pct)
                    hwm_stop_price = pos["highest_close"] * (1.0 - hwm_trail_val)
                    hard_stop_price = pos["cost"] - 4.5 * pos["atr"]
                    
                    is_stop_hit = False
                    exit_price = row["Close"]
                    exit_reason = ""
                    slippage = 0.0
                    
                    # A. Physical Stop Loss (4.5x ATR)
                    if check_low_price <= hard_stop_price:
                        is_stop_hit = True
                        # 【修复 Gap-down 开盘跳空低开】：如果当天低开直接跌破止损线，则只能以开盘价成交
                        exit_price = min(row["Open"], hard_stop_price)
                        exit_reason = "SELL_STOP (4.5x ATR)"
                        slippage = exit_price * self.waterfall_slippage_rate  # Waterfall volatility penalty
                        
                    # B. High Water Mark Stop Loss (在非止损触发状态下，执行 HWM 判定)
                    if not is_stop_hit:
                        # 【修复 VIX/QQQ 判定未来函数】：使用前一日 (d-1) 的指标进行风控判定，防止 Look-Ahead
                        current_profit_pct = ((row["Close"] - pos["cost"]) / pos["cost"]) * 100
                        if current_profit_pct > self.breathing_profit_threshold:
                            is_guard_triggered = False
                            if self.use_breathing_stop_guard:
                                qqq_past = self.qqq_daily[self.qqq_daily.index < d]  # 严格小于当前日
                                vix_past = self.vix_daily[self.vix_daily.index < d]
                                vix_val = vix_past['Close'].iloc[-1] if not vix_past.empty else 18.0
                                
                                if not qqq_past.empty:
                                    q_close = qqq_past.iloc[-1]["Close"]
                                    q_ma50 = qqq_past.iloc[-1].get("MA50", 0.0)
                                    if q_close < q_ma50:
                                        is_guard_triggered = True
                                if vix_val > 22.0:
                                    is_guard_triggered = True
                                    
                            if is_guard_triggered:
                                hwm_trail_val = self.hwm_stop_loss_pct
                            else:
                                # Widen stop by 50% (cap at 30% drawdown) to let it breathe
                                hwm_trail_val = min(0.30, hwm_trail_val * 1.5)
                            
                            # 重新计算带缩放的 HWM 止损线
                            hwm_stop_price = pos["highest_close"] * (1.0 - hwm_trail_val)
                        
                        # 检查 HWM 跌破（支持 Gap-down 低开修正）
                        if row["Close"] <= hwm_stop_price:
                            is_stop_hit = True
                            exit_price = min(row["Open"], hwm_stop_price)
                            exit_reason = f"SELL_HWM_TRAIL ({hwm_trail_val*100:.1f}% HWM)"
                            slippage = exit_price * self.hwm_slippage_rate  # HWM dynamic slippage
                        
                    if is_stop_hit:
                        final_exit_price = exit_price - slippage
                        shares = pos["shares"]
                        cost = pos["cost"]
                        gross = shares * final_exit_price
                        fee = gross * self.fee_rate
                        net = gross - fee
                        
                        self.cash += net
                        pnl_pct = ((final_exit_price - cost) / cost) * 100
                        trade_pnl_cash = shares * (final_exit_price - cost) - fee
                        
                        self.trades_log.append({
                            "Timestamp": d.strftime('%Y-%m-%d 16:00'),
                            "Ticker": t,
                            "Action": exit_reason,
                            "Shares": shares,
                            "Price": final_exit_price,
                            "Value": net,
                            "PnL%": pnl_pct,
                            "PnL_Cash": trade_pnl_cash,
                            "Metadata": {"reason": f"Mid-week Exit: {exit_reason}"}
                        })
                        
                        del self.positions[t]
                        if self.verbose:
                            print(f"🔴 [{d.strftime('%Y-%m-%d')}] {exit_reason} 止损触发: {t} 卖出 {shares:.1f} 股 @ ${final_exit_price:.2f} (盈亏: {pnl_pct:+.2f}%)")
                    
                    # 【风控节点落后】：判定完全结束后，再更新当天的最高收盘价（防御 Look-Ahead）
                    if not is_stop_hit:
                        pos["highest_close"] = max(pos["highest_close"], row["Close"])
                
                # Calculate daily ending portfolio equity
                current_prices = {}
                for t in self.positions.keys():
                    day_rows = self.daily_data[t][self.daily_data[t].index == d]
                    if not day_rows.empty:
                        current_prices[t] = day_rows.iloc[0]["Close"]
                    else:
                        current_prices[t] = self.positions[t]["cost"]  # Fallback
                        
                pos_value = sum(pos["shares"] * current_prices.get(t, pos["cost"]) for t, pos in self.positions.items())
                total_equity = self.cash + self.core_cash + pos_value
                
                # QQQ index price close
                qqq_close = 0.0
                if d in self.qqq_daily.index:
                    qqq_close = self.qqq_daily.loc[d, 'Close']
                    
                self.equity_curve.append({"Timestamp": d, "Equity": total_equity, "QQQ": qqq_close})
                
            # 2. WEEK-END REBALANCE DECISION (Friday Close)
            # Find the last trading day of this week
            friday_date = week_days[-1]
            
            # Predict factors for next week rebalancing
            scores = self.calculate_factors(friday_date)
            
            # 🏰 [双池重组] 核心股因子缩放与战术池筛选
            if self.use_double_pool:
                # A. 核心仓因子动态缩放 (Factor-based core exposure scaling)
                for c in self.core_tickers:
                    if c in self.positions:
                        pos = self.positions[c]
                        c_score = scores.get(c, {}).get("score", -999.0)
                        c_close = self.daily_data[c][self.daily_data[c].index <= friday_date]['Close'].iloc[-1]
                        
                        # If core ticker factor score is weak, scale down
                        if c_score < self.min_core_factor_score or c not in scores:
                            if not pos.get("downsized", False):
                                trim_sh = pos["shares"] * self.core_downsize_pct
                                trim_val = trim_sh * c_close
                                pos["shares"] -= trim_sh
                                pos["downsized"] = True
                                self.core_cash += trim_val
                                if self.verbose:
                                    print(f"📉 [双池核心避险] {c} 动能衰退 (因子得分: {c_score:.2f})，主动动态减仓 {self.core_downsize_pct*100:.0f}%，套现 ${trim_val:.2f} 存入核心现金池")
                        else:
                            # If score is strong and previously downsized, restore position
                            if pos.get("downsized", False):
                                restore_val = self.core_cash
                                if restore_val > 50.0:
                                    restore_sh = restore_val / c_close
                                    pos["shares"] += restore_sh
                                    pos["downsized"] = False
                                    self.core_cash = 0.0
                                    if self.verbose:
                                        print(f"📈 [双池核心归位] {c} 动能修复 (因子得分: {c_score:.2f})，买回全部核心现金 ${restore_val:.2f}，增持 {restore_sh:.1f} 股")
                                        
                # B. 战术池排他性筛选 (Isolate tactical pool to non-core tickers)
                tactical_scores = {k: v for k, v in scores.items() if k not in self.core_tickers}
                sorted_scores = sorted(tactical_scores.items(), key=lambda x: x[1]["score"], reverse=True)
            else:
                sorted_scores = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
                
            top_selected = sorted_scores[:K]
            selected_tickers = [x[0] for x in top_selected]
            
            # Calculate Risk Sizing using VIX on Friday Close
            vix_past = self.vix_daily[self.vix_daily.index <= friday_date] if not self.vix_daily.empty else pd.DataFrame()
            vix_val = vix_past['Close'].iloc[-1] if not vix_past.empty else 18.0
            
            # Continuous risk scaling formula
            active_exposure = np.clip(18.0 / vix_val, 0.15, 1.0)
            
            # We want to rebalance on the next week's first trading day (Monday Open)
            # Let's verify if there is a next week
            if w_idx + 1 >= len(sorted_week_keys):
                continue
                
            next_week_days = weeks[sorted_week_keys[w_idx + 1]]
            monday_date = next_week_days[0]
            
            # Prepare to execute target weights
            # If double pool, tactical rebalancing is based purely on the Tactical Pool's Net Asset Value (NAV)
            if self.use_double_pool:
                tactical_pos_val = sum(pos["shares"] * self.daily_data[t][self.daily_data[t].index <= friday_date]['Close'].iloc[-1]
                                       for t, pos in self.positions.items() if pos.get("pool") != "core")
                dec_equity = self.cash + tactical_pos_val
            else:
                dec_equity = self.equity_curve[-1]["Equity"]
            
            # SGOV target cash weight = 1.0 - active_exposure
            # If fewer than K stocks pass Stage 2, say m stocks, we only allocate m/K exposure, remaining goes to SGOV!
            m = len(selected_tickers)
            RANK_WEIGHTS = [0.35, 0.25, 0.20, 0.12, 0.08]
            if K > len(RANK_WEIGHTS):
                RANK_WEIGHTS = [1.0 / K] * K
            else:
                k_weights = RANK_WEIGHTS[:K]
                k_sum = sum(k_weights)
                RANK_WEIGHTS = [w / k_sum for w in k_weights]
                
            actual_weights_sum = sum(RANK_WEIGHTS[:m]) if m > 0 else 0.0
            actual_exposure = active_exposure * actual_weights_sum
            
            target_cash = dec_equity * (1.0 - actual_exposure)
            
            # Map ticker to its specific target weight based on rank
            target_weights_map = {}
            for idx, t in enumerate(selected_tickers):
                target_weights_map[t] = dec_equity * active_exposure * RANK_WEIGHTS[idx]
            
            # Rebalancing execution on Monday
            # 1. Handle Exits (Stocks currently held but no longer selected)
            held_tickers = list(self.positions.keys())
            for t in held_tickers:
                # Core positions are exempt from weekly exits
                if self.use_double_pool and self.positions[t].get("pool") == "core":
                    continue
                if t not in selected_tickers:
                    # Sell full position at Monday open
                    if t not in self.daily_data:
                        continue
                    mon_daily = self.daily_data[t][self.daily_data[t].index == monday_date]
                    if mon_daily.empty:
                        # Fallback to Friday close
                        past_prices = self.daily_data[t][self.daily_data[t].index <= friday_date]['Close']
                        exit_price = past_prices.iloc[-1] if not past_prices.empty else pos["cost"]
                    else:
                        exit_price = mon_daily.iloc[0]['Open']
                        
                    pos = self.positions[t]
                    shares = pos["shares"]
                    cost = pos["cost"]
                    
                    # Apply parameterised execution slippage for exits
                    slippage = exit_price * self.custom_slippage_rate
                    final_exit_price = exit_price - slippage
                    gross = shares * final_exit_price
                    fee = gross * self.fee_rate
                    net = gross - fee
                    
                    self.cash += net
                    pnl_pct = ((final_exit_price - cost) / cost) * 100
                    trade_pnl_cash = shares * (final_exit_price - cost) - fee
                    
                    self.trades_log.append({
                        "Timestamp": monday_date.strftime('%Y-%m-%d 09:30'),
                        "Ticker": t,
                        "Action": "SELL_REBALANCE",
                        "Shares": shares,
                        "Price": final_exit_price,
                        "Value": net,
                        "PnL%": pnl_pct,
                        "PnL_Cash": trade_pnl_cash,
                        "Metadata": {"reason": "Out of weekly Top K"}
                    })
                    del self.positions[t]
                    if self.verbose:
                        print(f"🔴 [{monday_date.strftime('%Y-%m-%d')}] 调仓卖出: {t} 卖出 {shares:.1f} 股 @ ${final_exit_price:.2f} (盈亏: {pnl_pct:+.2f}%)")
            
            # 2. Handle adjustments for existing positions that remain selected (Two-phase Execution)
            trims_to_execute = []
            adds_to_execute = []
            
            for t in selected_tickers:
                if t in self.positions:
                    pos = self.positions[t]
                    current_shares = pos["shares"]
                    
                    mon_daily = self.daily_data[t][self.daily_data[t].index == monday_date]
                    open_price = mon_daily.iloc[0]['Open'] if not mon_daily.empty else pos["cost"]
                    
                    target_value = target_weights_map.get(t, 0.0)
                    current_value = current_shares * open_price
                    
                    # Master-Level Offensive Upgrade: Winner-Hold Policy
                    # If stock has strong momentum in the last week, skip trimming to let compounding run!
                    past_t = self.daily_data[t][self.daily_data[t].index <= friday_date]
                    last_week_ret = 0.0
                    if len(past_t) >= 5:
                        last_week_ret = (past_t['Close'].iloc[-1] - past_t['Close'].iloc[-5]) / past_t['Close'].iloc[-5]
                    
                    is_mega_winner = last_week_ret > 0.08  # Weekly gain > 8%
                    
                    if current_value > target_value * 1.15: # Only trim if size exceeds by 15% (avoid overtrading)
                        if is_mega_winner:
                            if self.verbose:
                                print(f"🔥 [{monday_date.strftime('%Y-%m-%d')}] 动能赢家顺延: {t} 上周暴涨 {last_week_ret*100:.1f}%，触发大师级进攻性保护，不予减仓，利润飞奔！")
                            continue
                        trims_to_execute.append((t, current_value - target_value, open_price, pos))
                    elif current_value < target_value * 0.85: # Only add if size drops below by 15%
                        adds_to_execute.append((t, target_value - current_value, open_price, pos))
            
            # 第一阶段：全面释放现金 (Trim Positions)
            for t, trim_value, open_price, pos in trims_to_execute:
                trim_shares = trim_value / open_price
                slippage = open_price * self.custom_slippage_rate
                final_exit_price = open_price - slippage
                gross = trim_shares * final_exit_price
                fee = gross * self.fee_rate
                net = gross - fee
                
                self.cash += net
                pnl_pct = ((final_exit_price - pos["cost"]) / pos["cost"]) * 100
                
                self.trades_log.append({
                    "Timestamp": monday_date.strftime('%Y-%m-%d 09:30'),
                    "Ticker": t,
                    "Action": "SELL_TRIM",
                    "Shares": trim_shares,
                    "Price": final_exit_price,
                    "Value": net,
                    "PnL%": pnl_pct,
                    "PnL_Cash": trim_shares * (final_exit_price - pos["cost"]) - fee,
                    "Metadata": {"reason": "Weekly Sizing Re-adjustment (Trims)"}
                })
                
                pos["shares"] -= trim_shares
                if self.verbose:
                    print(f"🟡 [{monday_date.strftime('%Y-%m-%d')}] 仓位调低: {t} 减持 {trim_shares:.1f} 股 @ ${final_exit_price:.2f}")
            
            # 第二阶段：安全加仓 (Add Positions)
            for t, add_value, open_price, pos in adds_to_execute:
                if self.cash >= add_value:
                    fee = add_value * self.fee_rate
                    net_buy = add_value - fee
                    shares_to_buy = net_buy / open_price
                    
                    self.cash -= add_value
                    
                    # Blend cost
                    old_shares = pos["shares"]
                    old_cost = pos["cost"]
                    new_shares = old_shares + shares_to_buy
                    new_cost = ((old_shares * old_cost) + (shares_to_buy * open_price)) / new_shares
                    
                    self.positions[t] = {
                        "shares": new_shares,
                        "cost": new_cost,
                        "highest_close": max(pos["highest_close"], open_price),
                        "atr": pos["atr"],
                        "hwm_trail": scores[t]["hwm_trail"],
                        "entry_date": monday_date  # Ensure entry_date is tracked for new sub-lots
                    }
                    
                    self.trades_log.append({
                        "Timestamp": monday_date.strftime('%Y-%m-%d 09:30'),
                        "Ticker": t,
                        "Action": "BUY_ADD",
                        "Shares": shares_to_buy,
                        "Price": open_price,
                        "Value": add_value,
                        "PnL%": 0.0,
                        "Metadata": {"reason": "Weekly Sizing Re-adjustment (Adds)"}
                    })
                    if self.verbose:
                        print(f"🟢 [{monday_date.strftime('%Y-%m-%d')}] 仓位追加: {t} 加仓 {shares_to_buy:.1f} 股 @ ${open_price:.2f}")
            
            # 3. Handle NEW Buy Entries with Monday Intraday State Machine Overlay!
            new_entry_candidates = [t for t in selected_tickers if t not in self.positions]
            if new_entry_candidates:
                # Calculate total target cash needed
                total_new_targets = sum(target_weights_map.get(t, 0.0) for t in new_entry_candidates)
                # If target cash exceeds available cash, scale down pro-rata
                scaling_factor = min(1.0, self.cash / total_new_targets) if total_new_targets > 0.0 else 1.0
                
                for t in new_entry_candidates:
                    target_value = target_weights_map.get(t, 0.0) * scaling_factor
                    if target_value < 100.0:
                        continue
                        
                    # Fetch Monday intraday 5-minute bars
                    has_intraday = False
                    mon_intra = pd.DataFrame()
                    if t in self.intraday_data:
                        # O(1) dictionary lookup to fetch Monday's intraday data instantly
                        mon_intra = self.intraday_data[t].get(monday_date.date(), pd.DataFrame())
                        if not mon_intra.empty:
                            has_intraday = True
                            
                    # Check for standard daily Open as a baseline
                    mon_daily = self.daily_data[t][self.daily_data[t].index == monday_date]
                    daily_open_val = mon_daily.iloc[0]['Open'] if not mon_daily.empty else scores[t]["close"]
                    daily_atr = scores[t]["atr"]
                    
                    # Master-Level Offensive Upgrade: Monday Black Swan Gap-Down Guard
                    is_gap_aborted = False
                    if self.use_monday_gap_guard:
                        friday_close = scores[t]["close"]
                        stock_gap = (daily_open_val - friday_close) / friday_close
                        
                        # Check QQQ gap down
                        qqq_mon = self.qqq_daily[self.qqq_daily.index == monday_date]
                        qqq_fri = self.qqq_daily[self.qqq_daily.index == friday_date]
                        qqq_gap = 0.0
                        if not qqq_mon.empty and not qqq_fri.empty:
                            qqq_gap = (qqq_mon.iloc[0]["Open"] - qqq_fri.iloc[0]["Close"]) / qqq_fri.iloc[0]["Close"]
                            
                        if stock_gap <= self.monday_gap_threshold or qqq_gap <= self.qqq_gap_threshold:
                            is_gap_aborted = True
                            if self.verbose:
                                print(f"🚫 [{monday_date.strftime('%Y-%m-%d')}] {t} 触发跳空开盘黑天鹅防御 (个股跳空: {stock_gap*100:.2f}%, QQQ跳空: {qqq_gap*100:.2f}%)，本周拒绝建仓！")
                                
                    if is_gap_aborted:
                        continue
                        
                    entry_price = None
                    entry_time_str = "09:30"
                    entry_reason = "BUY_OPEN_FALLBACK"
                    
                    if has_intraday:
                        # Intraday State Machine Run
                        open_price_5m = mon_intra.iloc[0]['Open']
                        
                        # Calculate rolling MA20 & Vol_MA20 on 5-min bars (min_periods=1 avoids bfill future leak!)
                        mon_intra = mon_intra.copy()
                        mon_intra['MA20'] = mon_intra['Close'].rolling(20, min_periods=1).mean()
                        mon_intra['Vol_MA20'] = mon_intra['Volume'].rolling(20, min_periods=1).mean()
                        
                        is_aborted = False
                        
                        # Latency Window Start Time calculation
                        start_time = datetime.strptime("09:30", "%H:%M") + timedelta(minutes=self.latency_minutes)
                        start_time_str = start_time.strftime("%H:%M")
                        
                        # Iterate through Monday 5-minute bars to select entry
                        for ts_bar, row in mon_intra.iterrows():
                            time_str = ts_bar.strftime('%H:%M')
                            
                            if time_str < start_time_str or time_str > "16:00":
                                continue
                                
                            curr_price = row['Close']
                            curr_vol = row['Volume']
                            curr_vwap = row['VWAP']
                            
                            # Rule A: Knife Guard (If low drops >4% from open, abort entry)
                            if row['Low'] <= open_price_5m * 0.96:
                                is_aborted = True
                                if self.verbose:
                                    print(f"🚫 [{monday_date.strftime('%Y-%m-%d')} {time_str}] {t} 触发 Knife Guard 开溜防线，今日拒绝建仓保护！")
                                break
                                
                            # Rule B: PEAD morning catalyst chase
                            if "10:00" <= time_str <= "11:00":
                                if curr_vol > row['Vol_MA20'] * 2.0 and (curr_price - open_price_5m) / open_price_5m >= 0.035:
                                    entry_price = curr_price
                                    entry_time_str = time_str
                                    entry_reason = "BUY_PEAD_CHASE"
                                    break
                                    
                            # Rule C: VWAP pullback or MA20 bounce (after 10:00)
                            if time_str >= "10:00":
                                is_vwap_pullback = curr_price <= curr_vwap * 1.002
                                is_ma20_bounce = abs(curr_price - row['MA20']) / row['MA20'] < 0.005 and curr_vol > row['Vol_MA20'] * 1.1
                                
                                if is_vwap_pullback or is_ma20_bounce:
                                    entry_price = curr_price
                                    entry_time_str = time_str
                                    entry_reason = "BUY_TACTICAL_VWAP" if is_vwap_pullback else "BUY_TACTICAL_MA20"
                                    break
                                    
                        # If we reached 16:00 without trigger, buy at 16:00 Close
                        if not is_aborted and entry_price is None:
                            entry_price = mon_intra.iloc[-1]['Close']
                            entry_time_str = "16:00"
                            entry_reason = "BUY_EOD_FALLBACK"
                            
                        if is_aborted:
                            # Weight remains in cash/SGOV
                            continue
                    else:
                        # No intraday data fallback to Monday Open
                        entry_price = daily_open_val
                        entry_reason = "BUY_DAILY_OPEN"
                        
                    # Execute Buy Order
                    fee = target_value * self.fee_rate
                    net_buy = target_value - fee
                    shares_bought = net_buy / entry_price
                    
                    self.cash -= target_value
                    self.positions[t] = {
                        "shares": shares_bought,
                        "cost": entry_price,
                        "highest_close": entry_price,
                        "atr": daily_atr,
                        "hwm_trail": scores[t]["hwm_trail"],
                        "entry_date": monday_date,  # Track entry_date for first-day stop-loss exemption
                        "pool": "tactical"
                    }
                    
                    self.trades_log.append({
                        "Timestamp": monday_date.strftime(f'%Y-%m-%d {entry_time_str}'),
                        "Ticker": t,
                        "Action": "BUY_REBALANCE",
                        "Shares": shares_bought,
                        "Price": entry_price,
                        "Value": target_value,
                        "PnL%": 0.0,
                        "Metadata": {"reason": f"Weekly New Allocation: {entry_reason}"}
                    })
                    if self.verbose:
                        print(f"🟢 [{monday_date.strftime('%Y-%m-%d')}] 调仓买入: {t} 买入 {shares_bought:.1f} 股 @ ${entry_price:.2f} (原因: {entry_reason})")
                    
        # Final evaluation
        curve_df = pd.DataFrame(self.equity_curve).set_index("Timestamp")
        curve_df['Return'] = curve_df['Equity'].pct_change()
        
        total_return = (curve_df['Equity'].iloc[-1] - self.initial_cash) / self.initial_cash * 100
        
        # Drawdown
        curve_df['RollMax'] = curve_df['Equity'].cummax()
        curve_df['Drawdown'] = (curve_df['Equity'] - curve_df['RollMax']) / curve_df['RollMax']
        max_drawdown = curve_df['Drawdown'].min() * 100
        
        # Max Drawdown duration
        curve_df['Is_Drawdown'] = curve_df['Equity'] < curve_df['RollMax']
        drawdown_durations = []
        current_dur = 0
        for val in curve_df['Is_Drawdown']:
            if val:
                current_dur += 1
            else:
                if current_dur > 0:
                    drawdown_durations.append(current_dur)
                current_dur = 0
        if current_dur > 0:
            drawdown_durations.append(current_dur)
        max_drawdown_days = max(drawdown_durations) if drawdown_durations else 0
        
        # Sharpe (Daily rf = 4% / 252)
        daily_returns = curve_df['Return'].resample('D').sum().dropna()
        rf_daily = 0.04 / 252
        excess_daily = daily_returns - rf_daily
        sharpe = np.sqrt(252) * (excess_daily.mean() / daily_returns.std()) if daily_returns.std() > 0 else 0.0
        
        # Sortino
        downside_returns = excess_daily[excess_daily < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino = (excess_daily.mean() * 252) / downside_std if downside_std > 0 else 0.0
        
        # Calmar
        annualized_return = daily_returns.mean() * 252 * 100
        calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        # Trade metrics
        sell_trades = [t for t in self.trades_log if "SELL" in t['Action']]
        win_trades = [t for t in sell_trades if t.get('PnL_Cash', 0.0) > 0.0]
        loss_trades = [t for t in sell_trades if t.get('PnL_Cash', 0.0) < 0.0]
        win_rate = len(win_trades) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0.0
        
        gross_profit = sum([t.get('PnL_Cash', 0.0) for t in sell_trades if t.get('PnL_Cash', 0.0) > 0.0])
        gross_loss = abs(sum([t.get('PnL_Cash', 0.0) for t in sell_trades if t.get('PnL_Cash', 0.0) < 0.0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
        
        avg_win = gross_profit / len(win_trades) if len(win_trades) > 0 else 0.0
        avg_loss = gross_loss / len(loss_trades) if len(loss_trades) > 0 else 0.0
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        
        # Benchmark QQQ Return
        qqq_return = 0.0
        if not self.qqq_daily.empty:
            qqq_close_series = self.qqq_daily[(self.qqq_daily.index >= start_date) & (self.qqq_daily.index <= end_date)]['Close']
            qqq_return = (qqq_close_series.iloc[-1] - qqq_close_series.iloc[0]) / qqq_close_series.iloc[0] * 100
            
        alpha = total_return - qqq_return
        
        metrics = {
            "tickers": self.tickers,
            "total_initial": self.initial_cash,
            "final_equity": curve_df['Equity'].iloc[-1],
            "total_return_pct": total_return,
            "qqq_return_pct": qqq_return,
            "alpha_pct": alpha,
            "max_drawdown_pct": max_drawdown,
            "max_drawdown_days": max_drawdown_days,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "trades_count": len(self.trades_log),
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "payoff_ratio": payoff_ratio,
            "equity_curve": [{"Timestamp": str(idx), "Equity": row["Equity"], "QQQ": row["QQQ"]} for idx, row in curve_df.iterrows()],
            "trades_log": self.trades_log
        }
        
        return metrics

if __name__ == "__main__":
    # Test execution
    TICKERS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX', 
        'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'JPM', 'BAC', 'MS', 'GS', 'V', 
        'MA', 'AXP', 'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'TSLA', 
        'HD', 'MCD', 'NKE', 'SBUX', 'WMT', 'COST', 'KO', 'PEP', 'PG', 'GE', 
        'CAT', 'HON', 'LMT', 'BA', 'XOM', 'CVX', 'COP', 'FCX', 'NEE', 'AMT'
    ]
    # 1. 运行传统的单一池全局动能轮动回测
    engine = WeeklyRebalanceEngine(TICKERS, monday_gap_threshold=-0.02, breathing_profit_threshold=10.0, hwm_stop_loss_pct=0.08)
    m = engine.run_backtest(K=5)
    print(f"🟢 [传统单一池回测结果] 总权益: ${m['final_equity']:.2f}, 收益率: {m['total_return_pct']:.2f}%, 最大回撤: {m['max_drawdown_pct']:.2f}%, 夏普比率: {m['sharpe_ratio']:.2f}")

    # 2. 运行创新的双池主客观协同组合优化回测
    print("\n" + "="*80 + "\n🏰 [双池组合优化器回测启动] 核心底仓: 60% 锁定 NVDA, COHR, MSFT, GOOGL, IAU | 战术池: 40% 动能轮动\n" + "="*80)
    engine_dp = WeeklyRebalanceEngine(
        TICKERS, 
        monday_gap_threshold=-0.02, 
        breathing_profit_threshold=10.0, 
        hwm_stop_loss_pct=0.08,
        use_double_pool=True,
        core_tickers=["NVDA", "COHR", "MSFT", "GOOGL", "IAU"],
        core_ratio=0.60
    )
    m_dp = engine_dp.run_backtest(K=3)
    print(f"🏰 [双池组合优化回测结果] 总权益: ${m_dp['final_equity']:.2f}, 收益率: {m_dp['total_return_pct']:.2f}%, 最大回撤: {m_dp['max_drawdown_pct']:.2f}%, 夏普比率: {m_dp['sharpe_ratio']:.2f}")
