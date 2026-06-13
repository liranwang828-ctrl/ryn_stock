import sys
import os
import json
import random
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Ensure UTF-8 Console Printing
sys.stdout.reconfigure(encoding='utf-8')

# Set random seed for Methodology #10 reproducibility
random.seed(42)

# ==============================================================================
# MODULE A: DATA & FEATURE BROKER (数据与特征经纪) - 支持 方法论 #13, #15
# ==============================================================================
class DataFeatureBroker:
    def __init__(self, cache_dir="learning"):
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def get_intraday_data(self, ticker, days=60):
        cache_path = os.path.join(self.cache_dir, f"intraday_cache_{ticker}.csv")
        if os.path.exists(cache_path):
            file_size_kb = os.path.getsize(cache_path) / 1024
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
            # Protect large 2-year Massive.com high-frequency cache files (usually > 600KB)
            # from being wiped out by yfinance's limited 60-day pull.
            if file_size_kb > 600 or (datetime.now() - mtime < timedelta(hours=12)):
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                if not df.empty:
                    return df.sort_index()
                    
        print(f"📡 正在拉取 {ticker} 的 5分钟 K线...")
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="60d", interval="5m")
            if df.empty:
                return pd.DataFrame()
            df = df.sort_index()
            df.to_csv(cache_path)
            return df
        except Exception as e:
            print(f"🔴 获取 {ticker} 数据失败: {e}")
            return pd.DataFrame()

    def get_daily_indicators(self, ticker):
        """
        获取个股的日线数据，计算 MA50, MA150, MA200 用于 Minervini Stage 2 过滤。
        """
        cache_path = os.path.join(self.cache_dir, f"daily_cache_{ticker}.csv")
        
        # Always use local offline cache if it exists to ensure fast, deterministic sweeps and bypass yfinance rate limits
        if os.path.exists(cache_path):
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            if not df.empty:
                df.index = pd.to_datetime(df.index, utc=True)
                return df
                
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="7y", interval="1d")
            if df.empty:
                return pd.DataFrame()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['MA150'] = df['Close'].rolling(window=150).mean()
            df['MA200'] = df['Close'].rolling(window=200).mean()
            df['MA200_trend'] = df['MA200'].diff(periods=10)
            
            # Methodology #6: Stage 2 Filter
            df['Stage_2'] = (
                (df['Close'] > df['MA150']) & 
                (df['Close'] > df['MA200']) & 
                (df['MA150'] > df['MA200']) & 
                (df['MA50'] > df['MA150']) & 
                (df['MA200_trend'] > 0)
            ).astype(int)
            
            df.to_csv(cache_path)
            return df
        except Exception as e:
            print(f"🔴 获取 {ticker} 日线数据失败: {e}")
            return pd.DataFrame()

    def process_and_merge(self, ticker, days=60):
        """
        合并高频 5-Min 数据与日线 Stage 2 特征。
        """
        intraday_df = self.get_intraday_data(ticker, days)
        daily_df = self.get_daily_indicators(ticker)
        
        if intraday_df.empty or daily_df.empty:
            return pd.DataFrame()
            
        df = intraday_df.copy()
        df.index = pd.to_datetime(df.index, utc=True).tz_convert('America/New_York')
        df['DateOnly'] = df.index.date
        df['TimeOnly'] = df.index.strftime('%H:%M')
        
        # Calculate分时 VWAP (Methodology #15)
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['TP_Vol'] = df['Typical_Price'] * df['Volume']
        df['Cum_TP_Vol'] = df.groupby('DateOnly')['TP_Vol'].cumsum()
        df['Cum_Vol'] = df.groupby('DateOnly')['Volume'].cumsum()
        df['VWAP'] = df['Cum_TP_Vol'] / df['Cum_Vol']
        
        # Calculate Rolling MA20 for intraday K-lines (Methodology #9) (min_periods=1 causal rolling)
        df['MA20'] = df['Close'].rolling(window=20, min_periods=1).mean()
        
        # Calculate ATR 14 (Methodology #8)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift(1))
        low_close = np.abs(df['Low'] - df['Close'].shift(1))
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(14, min_periods=1).mean()
        
        # Merge daily Stage 2 status (strictly T-1 shifted to prevent look-ahead bias)
        daily_df = daily_df.copy()
        daily_df.index = pd.to_datetime(daily_df.index, utc=True).tz_convert('America/New_York')
        daily_df['DateOnly'] = daily_df.index.date
        
        daily_df['Stage_2_shifted'] = daily_df['Stage_2'].shift(1)
        daily_df['MA50_shifted'] = daily_df['MA50'].shift(1)
        
        stage2_map = daily_df.set_index('DateOnly')['Stage_2_shifted'].to_dict()
        df['Stage_2'] = df['DateOnly'].map(stage2_map).fillna(0).astype(int)
        
        ma50_map = daily_df.set_index('DateOnly')['MA50_shifted'].to_dict()
        df['MA50'] = df['DateOnly'].map(ma50_map).ffill().bfill()
        
        # Vol MA20 for comparison
        df['Vol_MA20'] = df['Volume'].rolling(window=20, min_periods=1).mean()
        
        # Qlib Candlestick Features
        df['kmid'] = (df['Close'] - df['Open']) / df['Open']
        df['klen'] = (df['High'] - df['Low']) / df['Open']
        df['kup'] = (df['High'] - np.maximum(df['Open'], df['Close'])) / df['Open']
        df['klow'] = (np.minimum(df['Open'], df['Close']) - df['Low']) / df['Open']
        
        # RSI 14
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).rolling(window=14, min_periods=1).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14, min_periods=1).mean()
        rs = gain / (loss + 1e-12)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['BB_Mid'] = df['Close'].rolling(window=20, min_periods=1).mean()
        df['BB_Std'] = df['Close'].rolling(window=20, min_periods=1).std().fillna(0.0)
        df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
        df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
        
        return df

# ==============================================================================
# MODULE B: TACTICAL STATE MACHINE (单兵战术状态机)
# ==============================================================================
class TacticalStateMachine:
    """
    完全对齐：方法论 #1, #2, #4, #5, #6, #8, #9, #10, #11, #12, #13, #14, #15
    """
    def __init__(self, ticker, rules, catalyst_level="★☆☆"):
        self.ticker = ticker
        self.rules = rules
        self.catalyst_level = catalyst_level # Methodology #12: ★★★ vs ★☆☆
        
        # Position States: "OUT", "T1_IN", "T2_IN", "FULL_IN" (Methodology #11 strict 3-tier)
        self.state = "OUT"
        
        # Multi-Horizon Hybrid routing trackers
        self.holding_type = None            # "LONG_TERM" or "SHORT_TERM"
        self.long_term_max_close = 0.0      # Tracking peak daily closing price
        self.daily_open_price = 0.0         # Tracking daily open price of the stock
        
        # Long-term trend track config parameters
        cfg = self.rules.get("methodology_15_low_catalyst_rs", {})
        self.long_term_ma_buffer = cfg.get("long_term_ma_buffer_pct", 2.0) / 100.0   # 2% MA50 buffer
        self.long_term_trail_pct = cfg.get("long_term_trail_pct", 12.0) / 100.0     # 12% peak close trail
        self.long_term_atr_mult  = cfg.get("long_term_atr_multiplier", 4.5)         # 4.5x ATR
        
        # Trackers
        self.t1_shares = 0.0
        self.t2_shares = 0.0
        self.t3_shares = 0.0
        self.avg_cost = 0.0
        self.stop_loss = 0.0
        
        # Methodology #6: Consecutive Confirmation Counters
        self.rs_consecutive = 0
        self.ml_consecutive = 0
        
        # Methodology #10: Noise Entry Delay
        self.delay_timer = 0
        self.pending_entry_signal = None
        
        # Methodology #11: Sizing entry tracker
        self.t1_entry_bar_count = 0
        
        # Daily Session trackers
        self.current_date = None
        self.open_high = 0.0
        self.open_low = 999999.0
        self.open_peak_vol = 0.0
        self.open_peak_price = 0.0
        self.pullback_low = 999999.0
        self.pullback_vol = 0.0
        self.thesis_fail_cooldown = 0
        self.rng = random.Random(42)
        
    def reset_daily_session(self, date):
        self.current_date = date
        self.open_high = 0.0
        self.open_low = 999999.0
        self.open_peak_vol = 0.0
        self.open_peak_price = 0.0
        self.pullback_low = 999999.0
        self.pullback_vol = 0.0
        self.rs_consecutive = 0
        self.ml_consecutive = 0
        self.delay_timer = 0
        self.pending_entry_signal = None
        self.t1_entry_bar_count = 0
        self.thesis_fail_cooldown = 0
        self.stop_freeze_bars_remaining = 0  # 入场冻结期倒计时（T1建仓后 N 个Bar内不触发止损）
        self.daily_open_price = 0.0         # Reset daily open price
        
    def process_bar(self, bar, time_str, ml_score, rs_factor, sector_leader_vwap_status=True, qqq_trend_ok=True, is_vix_panic=False, qqq_strong=False, regime_rs_penalty=0.0, regime_cutoff_override=None, market_regime="A"):
        """
        核心状态机。包含 15 条方法论的所有量化判定规则。
        """
        # Decrement cool-off timer
        if self.thesis_fail_cooldown > 0:
            self.thesis_fail_cooldown -= 1
            
        curr_price = bar['Close']
        curr_vol = bar['Volume']
        curr_vwap = bar['VWAP']
        stage_2 = bar['Stage_2']
        atr = bar['ATR']
        
        if time_str < "09:30" or time_str > "16:00":
            return None
            
        # Capture the daily open price on the first bar of the day
        if self.daily_open_price == 0.0 or time_str == "09:30":
            self.daily_open_price = bar['Open']
            
        # PEAD Programmatic Catalyst Detector (Dynamic Horizon Upgrading)
        # 若处于 Stage 2 且在 10:00 - 11:00 期间较今日开盘大涨超过 3.5%，并伴随天量突破
        is_pead_catalyst = False
        if stage_2 == 1 and self.daily_open_price > 0.0:
            if "10:00" <= time_str <= "11:00" and curr_vol > bar.get('Vol_MA20', curr_vol) * 2.0:
                if (curr_price - self.daily_open_price) / self.daily_open_price >= 0.035:
                    is_pead_catalyst = True
                    # Dynamic Horizon Upgrading: If already holding a position, upgrade to LONG_TERM
                    if self.state != "OUT" and self.holding_type != "LONG_TERM":
                        self.holding_type = "LONG_TERM"
                        self.stop_loss = curr_price - self.long_term_atr_mult * atr
                        self.long_term_max_close = curr_price
            
        # ------------------ 方法论 #1: 开盘区间 (09:30-10:00) 确立 ------------------
        if "09:30" <= time_str <= "10:00":
            if bar['High'] > self.open_high: self.open_high = bar['High']
            if bar['Low'] < self.open_low: self.open_low = bar['Low']
            
            # 方法论 #15: 盘初天量 Peak 探测
            if curr_vol > self.open_peak_vol:
                self.open_peak_vol = curr_vol
                self.open_peak_price = bar['High']
                
        # ------------------ 方法论 #15: 缩量贴地滑行探测 (09:45-10:45) ------------------
        if "09:45" <= time_str <= "10:45" and self.open_peak_vol > 0:
            if bar['Low'] < self.pullback_low:
                self.pullback_low = bar['Low']
                self.pullback_vol = curr_vol
                
        vc_ratio = (self.pullback_vol / self.open_peak_vol) if self.open_peak_vol > 0 else 1.0
        
        # Load parameters and principle switches
        cfg = self.rules["methodology_15_low_catalyst_rs"]
        vc_thresh = cfg["vc_threshold_pct"] / 100.0
        stop_loss_pct = cfg["bracket_stop_loss_pct"] / 100.0
        atr_multiplier = cfg.get("atr_stop_multiplier", 1.5)
        
        # Methodology #13 and #6 parameters
        rs_strong_threshold = cfg.get("rs_strong_threshold", 1.8)
        ml_score_threshold = cfg.get("ml_score_threshold", 0.75)
        ml_confirm_bars = cfg.get("ml_confirm_bars", 3)
        t1_wait_bars = cfg.get("t1_wait_bars", 5)
        open_high_vol_multiplier = cfg.get("open_high_vol_multiplier", 1.2)
        
        # ── 三档市场环境覆盖参数 (Regime A / B / C) ──────────────────
        # Regime A (VIX<20, QQQ正): 正常参数，强势日动态放宽
        # Regime B (VIX 20-25 | QQQ小幅负): RS门槛+0.5，入场窗口收至11:30
        # Regime C (VIX>25 | QQQ<-0.3%): 恐慌期精确狙击，半仓+宽止损+RS≥2.5
        entry_cutoff_base = cfg.get("entry_cutoff_time", "13:00")
        regime_size_multiplier = 1.0    # 仓位缩放比例
        regime_atr_override    = None   # ATR倍数覆盖
        regime_hwm_override    = None   # HWM追踪比例覆盖
        regime_freeze_override = None   # 冻结期覆盖
        
        if market_regime == "C":
            # 🔴 Regime C — 极端恐慌/熊市大考 (大盘趋势彻底向下 QQQ < MA200 或 VIX > 25)
            rs_strong_threshold = 2.5              # 只买超强逆势龙头
            entry_cutoff        = "10:30"          # 严格限制开盘前1小时
            regime_size_multiplier = 0.3           # 极低仓位规避风险 (30% 仓位比例)
            regime_hwm_override    = 0.960         # 严格收紧防线，4% 移动止损锁死风险
            regime_freeze_override = 6             # 增加建仓免止损冻结期 (30分钟)，过滤日内洗盘
            ml_confirm_bars        = 4             # 方法论 #6 深度调优：熊市大考极严过滤 (20分钟确认)
        elif market_regime == "B":
            # 🟡 Regime B — 震荡牛市 / 谨慎震荡期 (QQQ 均线配置不稳或 VIX 偏高)
            rs_strong_threshold += 0.5             # RS 相对强度门槛加严 +0.5
            entry_cutoff = regime_cutoff_override or "11:30"
            regime_hwm_override = 0.950            # 正常风控，5% 移动止损
            regime_size_multiplier = 0.5           # 50% position sizing scale-back
            ml_confirm_bars        = 2             # 方法论 #6 深度调优：震荡市中等确认 (10分钟确认)
        else:
            # 🟢 Regime A — 极速多头 / 单边疯牛市 (QQQ > MA200 且 MA50 > MA200 且 VIX < 20)
            # 大师级风控松绑：松开止损，让子弹飞！
            regime_hwm_override = 0.920            # 🚀 松绑止损至 8.0%!
            regime_atr_override = 4.5              # 🚀 初始 ATR 止损扩大至 4.5 倍
            regime_size_multiplier = 1.0           # 满仓进入
            rs_strong_threshold += regime_rs_penalty
            entry_cutoff_base = cfg.get("entry_cutoff_time", "13:00")
            ml_confirm_bars        = 1             # 方法论 #6 深度调优：单边牛市闪击入场 (5分钟即买)
            if qqq_strong:
                ml_confirm_bars = max(1, ml_confirm_bars - 1)
                entry_cutoff_h = int(entry_cutoff_base[:2])
                entry_cutoff_m = int(entry_cutoff_base[3:]) + 60 # 强势日交易时间向下午盘动态延伸 1 小时
                if entry_cutoff_m >= 60:
                    entry_cutoff_h += 1
                    entry_cutoff_m -= 60
                entry_cutoff = f"{entry_cutoff_h:02d}:{entry_cutoff_m:02d}"
            else:
                entry_cutoff = entry_cutoff_base
        
        # 应用覆盖值（如果 regime 设置了）
        if regime_atr_override is not None:
            atr_multiplier = regime_atr_override
        if regime_freeze_override is not None:
            stop_freeze_bars_eff = regime_freeze_override
        else:
            stop_freeze_bars_eff = cfg.get("stop_freeze_bars", 2)
        
        # Principle Switches (Categorical & Boolean)
        use_noise_delay = cfg.get("use_noise_delay", True)
        use_t2_confirm = cfg.get("use_t2_confirm", True)
        trailing_stop_type = cfg.get("trailing_stop_type", "MA20")
        stop_loss_type = cfg.get("stop_loss_type", "ATR")
        
        # ----------------- 状态 B: 任何持仓状态下的风控 -----------------
        if self.state != "OUT":
            is_washout_period = ("09:30" <= time_str <= "10:00")
            
            # ------------------ 方法论 #2: 行业板块论点失效联防 (NVIDIA联防) ------------------
            # 大师约束一：初仓 (T1) 属于侦察探路性质，不触发重大行业联防斩仓；只有当仓位追加到 T2 或全仓 (FULL) 时，才触发重仓联防保护。
            if not sector_leader_vwap_status and self.state in ["T2_IN", "FULL_IN"]:
                self.state = "OUT"
                self.holding_type = None  # Reset holding type on exit
                # 大师约束二：一旦触发龙头联防，进入 30 分钟（6 个 5分钟 Bar）的交易冷却冷静期，避免频繁摩擦拉锯
                self.thesis_fail_cooldown = 6
                return {
                    "action": "SELL_THESIS_FAIL",
                    "ticker": self.ticker,
                    "price": curr_price,
                    "is_waterfall": True, # 视为紧急撤退，滑点大
                    "metadata": {
                        "vc_ratio": vc_ratio,
                        "ml_score": ml_score,
                        "rs_factor": rs_factor,
                        "stage_2": stage_2,
                        "atr": atr,
                        "rules_triggered": ["Methodology #2 (Sector Leader Joint Defense Failure)"]
                    }
                }
                
            # 🟢 长线趋势轨风控信道
            if self.holding_type == "LONG_TERM":
                # 盘中彻底豁免 5分钟 HWM 追踪止损！仅在 16:00 收盘 Bar 进行日线大周期决策
                if time_str == "16:00":
                    self.long_term_max_close = max(self.long_term_max_close, curr_price)
                    
                    is_ma50_broken = curr_price < bar.get('MA50', 0.0) * (1.0 - self.long_term_ma_buffer)
                    is_drawdown_too_wide = curr_price <= self.long_term_max_close * (1.0 - self.long_term_trail_pct)
                    
                    if is_ma50_broken or is_drawdown_too_wide:
                        self.state = "OUT"
                        reason_str = f"Daily Close broke MA50 (buffer {self.long_term_ma_buffer*100:.1f}%)" if is_ma50_broken else f"Peak Close drop > {self.long_term_trail_pct*100:.1f}%"
                        self.holding_type = None  # Reset holding type on exit
                        return {
                            "action": "SELL_DAILY_MA50", # 路由出局，次日开盘 T+1 执行
                            "ticker": self.ticker,
                            "price": curr_price,
                            "is_waterfall": False,
                            "metadata": {
                                "holding_type": "LONG_TERM",
                                "reason": reason_str,
                                "close_price": curr_price,
                                "ma50": bar.get('MA50', 0.0),
                                "max_close": self.long_term_max_close,
                                "rules_triggered": ["LONG_TERM Parameterized Trend Exit"]
                            }
                        }
                        
                # 检查硬性止损线 (参数化 ATR 物理防线)，防止黑天鹅极端崩溃
                if curr_price <= self.stop_loss and not is_washout_period:
                    self.state = "OUT"
                    self.holding_type = None  # Reset holding type on exit
                    return {
                        "action": "SELL_STOP",
                        "ticker": self.ticker,
                        "price": curr_price,
                        "is_waterfall": True, # 硬性防线跌破，滑点大
                        "metadata": {
                            "holding_type": "LONG_TERM",
                            "reason": f"Hard stop break ({self.long_term_atr_mult}x ATR)",
                            "rules_triggered": ["Methodology #8 (Hard ATR Stop)"]
                        }
                    }
            
            # 🟡 短线波段轨风控信道 (沿用原有高频严密追踪止损)
            else:
                # ------------------ 方法论 #8: 大师 ATR 动态止损 ------------------
                # 入场冻结期：T1建仓后 N 个Bar内，忽略止损噪声（方法论 #4 扩展）
                if self.stop_freeze_bars_remaining > 0:
                    self.stop_freeze_bars_remaining -= 1
                    return None

                # Unified Trailing Stop (PATCH: T1_IN and T2_IN also use HWM / MA20 trailing stop)
                # Only activate trailing stop once price exceeds avg_cost by 2% or state is FULL_IN
                # This protects early positions while letting profits run on trends.
                trigger_exit = False
                action_name = "SELL_HWM_TRAIL"
                if curr_price > self.avg_cost * 1.02 or self.state == "FULL_IN":
                    if trailing_stop_type == "MA20":
                        ma20_atr_offset = cfg.get("ma20_trail_atr_multiplier", 0.5)
                        if curr_price <= bar['MA20'] - ma20_atr_offset * atr:
                            trigger_exit = True
                            action_name = "SELL_MA20_TRAIL"
                    elif trailing_stop_type == "HighWaterMark":
                        if curr_price <= self.stop_loss:
                            trigger_exit = True
                            action_name = "SELL_HWM_TRAIL"
                            
                    if trigger_exit and not is_washout_period:
                        self.state = "OUT"
                        self.holding_type = None  # Reset holding type on exit
                        return {
                            "action": action_name,
                            "ticker": self.ticker,
                            "price": curr_price,
                            "is_waterfall": False,
                            "metadata": {
                                "vc_ratio": vc_ratio,
                                "ml_score": ml_score,
                                "rs_factor": rs_factor,
                                "stage_2": stage_2,
                                "atr": atr,
                                "rules_triggered": [f"Methodology #9 (Unified {action_name})"]
                            }
                        }
                        
                    # Update trailing stop line (Frozen during washout 09:30-10:00)
                    if not is_washout_period:
                        if trailing_stop_type == "HighWaterMark":
                            hwm_pct = regime_hwm_override if regime_hwm_override else cfg.get("hwm_trail_pct", 0.970)
                            
                            # Dynamic Profit Tightening for HighWaterMark
                            profit_lock = cfg.get("profit_lock_threshold", 1.04)
                            tightened_pct = cfg.get("tightened_trailing_stop_pct", 0.980)
                            if curr_price > self.avg_cost * profit_lock:
                                hwm_pct = max(hwm_pct, tightened_pct)
                                
                            self.stop_loss = max(self.stop_loss, curr_price * hwm_pct)
                        else:
                            profit_lock = cfg.get("profit_lock_threshold", 1.04)
                            tightened_pct = cfg.get("tightened_trailing_stop_pct", 0.985)
                            if curr_price > self.avg_cost * profit_lock:
                                self.stop_loss = max(self.stop_loss, curr_price * tightened_pct)

                # Staged stop management (Quant Master fix, only if HWM is not triggered)
                if not is_washout_period and not trigger_exit:
                    if self.avg_cost > 0 and atr > 0:
                        if curr_price >= self.avg_cost + 1.0 * atr:
                            tighter_stop = curr_price - (atr_multiplier * atr * 0.6)
                            self.stop_loss = max(self.stop_loss, tighter_stop)
                    
                # 检查硬性止损线是否被击穿
                if curr_price <= self.stop_loss and not is_washout_period:
                    is_waterfall = (curr_vol > bar['Vol_MA20'] * 2.0) and (curr_price < bar['Open'])
                    self.state = "OUT"
                    self.holding_type = None  # Reset holding type on exit
                    return {
                        "action": "SELL_STOP",
                        "ticker": self.ticker,
                        "price": curr_price,
                        "is_waterfall": is_waterfall,
                        "metadata": {
                            "vc_ratio": vc_ratio,
                            "ml_score": ml_score,
                            "rs_factor": rs_factor,
                            "stage_2": stage_2,
                            "atr": atr,
                            "stop_loss": self.stop_loss,
                            "rules_triggered": ["Methodology #8 (ATR Stop Loss)"]
                        }
                    }
                
        # ----------------- 交易状态转移规则 -----------------
        
        # 1. STATE: OUT -> T1_IN (方法论 #11: T1 建仓)
        if self.state == "OUT":
            # 严格限制 T1 新开仓仅能在允许窗口内触发（默认 13:00，QQQ 强势时动态延伸至 13:30）
            if time_str > entry_cutoff:
                return None
                
            # ------------------ 方法论 #13: 强趋势豁免机制 ------------------
            is_strong_trend = rs_factor >= rs_strong_threshold # 连续强相对强度，直接豁免部分技术指标
            
            # ------------------ 方法论 #6: 连续 N 次信号确认过滤器 ------------------
            if ml_score >= ml_score_threshold: self.ml_consecutive += 1
            else: self.ml_consecutive = 0
            
            if rs_factor >= 1.5: self.rs_consecutive += 1
            else: self.rs_consecutive = 0
            
            # 连续性确认：日线 Stage 2 (ML Score) 必须连续稳定 ml_confirm_bars 以上，而价格收复 VWAP 信号当下满足即可
            is_confirmed = (self.ml_consecutive >= ml_confirm_bars and self.rs_consecutive >= 1) or is_strong_trend
            
            # ------------------ 方法论 #12: 催化剂分流场景判定 ------------------
            # S级 (★★★) 激活 Scenario B (回踩直接买)；B级 (★☆☆) 激活 Scenario D (必须 Reclaim)
            # PEAD Programmatic Catalyst Detector
            # 若处于 Stage 2 且在 10:00 - 11:00 期间较今日开盘大涨超过 3.5%，并伴随天量突破
            is_pead_catalyst = False
            if stage_2 == 1 and self.daily_open_price > 0.0:
                if "10:00" <= time_str <= "11:00" and curr_vol > bar.get('Vol_MA20', curr_vol) * 2.0:
                    if (curr_price - self.daily_open_price) / self.daily_open_price >= 0.035:
                        is_pead_catalyst = True
            
            # S级 (★★★) 激活 Scenario B (回踩直接买)；或自动触发 PEAD 强催化
            is_catalyst_s = (self.catalyst_level == "★★★") or is_pead_catalyst
            
            # QQQ Trend Filter: Only trigger T1 buys when QQQ is in a healthy momentum trend (qqq_trend_ok = True)
            if stage_2 == 1 and is_confirmed and self.thesis_fail_cooldown == 0 and qqq_trend_ok:
                is_vc_valid = vc_ratio <= vc_thresh
                is_reclaimed = curr_price > curr_vwap
                # 新增 ORB (开盘区间突破) 开仓通道 (仅在 Regime A 疯牛市中，个股为 Stage 2 且未持有仓位时有效)
                is_orb_valid = False
                if market_regime == "A" and self.open_high > 0 and "10:00" <= time_str <= "13:00":
                    if curr_price > self.open_high * 1.001 and curr_vol > self.open_peak_vol * 1.1:
                        is_orb_valid = True
                
                # 新增战术二：经典低吸抄底 (Dip Buying)
                is_dip_buy = False
                if (bar['RSI'] < 30 or curr_price <= bar['BB_Lower']) and "10:00" <= time_str <= "15:00":
                    if bar['klow'] > 1.2 * abs(bar['kmid']) and curr_price > curr_vwap:
                        is_dip_buy = True
                
                # 新增战术三：趋势跟随回踩买入 (MA20 Bounce)
                is_trend_follow = False
                if curr_price > bar['MA20'] and "10:00" <= time_str <= "15:00":
                    if abs(curr_price - bar['MA20']) / bar['MA20'] < 0.005 and curr_vol > bar['Vol_MA20'] * 1.1:
                        if bar['kmid'] > 0:
                            is_trend_follow = True
                
                # Scenario B, Scenario D, ORB Breakout, Dip Buying, or Trend Follow trigger
                trigger_buy = False
                trigger_reason = []
                if is_pead_catalyst:
                    trigger_buy = True # Programmatic PEAD 天量突破狙击
                    trigger_reason.append("PEAD_Momentum_Breakout")
                elif is_catalyst_s and is_vc_valid and curr_price <= curr_vwap * 1.005:
                    trigger_buy = True # 强势股回踩直接狙击
                    trigger_reason.append("Scenario_B_Pullback")
                elif not is_catalyst_s and is_vc_valid and is_reclaimed:
                    trigger_buy = True # 普通股必须 Reclaim VWAP
                    trigger_reason.append("Scenario_D_Reclaim")
                elif is_orb_valid:
                    trigger_buy = True # ORB 突破开仓
                    trigger_reason.append("ORB_Breakout")
                elif is_dip_buy:
                    trigger_buy = True # 低吸抄底开仓
                    trigger_reason.append("Dip_Buying_Oversold")
                elif is_trend_follow:
                    trigger_buy = True # 趋势跟随开仓
                    trigger_reason.append("MA20_Trend_Follow")
                    
                if trigger_buy:
                    # ------------------ 方法论 #10: 反拥挤 1-3分钟 随机延迟 ------------------
                    # ORB 动量突破要求瞬间成交，豁免延迟
                    if use_noise_delay and not is_orb_valid:
                        if self.delay_timer == 0:
                            self.delay_timer = self.rng.randint(1, 3) # 延迟 1-3 个 Bar
                            self.pending_entry_signal = "T1"
                            return None
                    else:
                        # 豁免延迟，直接立刻入场
                        self.state = "T1_IN"
                        self.avg_cost = curr_price
                        self.t1_entry_bar_count = 0
                        
                        # 确定持仓类型与初始止损
                        if is_catalyst_s and stage_2 == 1:
                            self.holding_type = "LONG_TERM"
                            self.stop_loss = curr_price - self.long_term_atr_mult * atr
                            self.long_term_max_close = curr_price
                        else:
                            self.holding_type = "SHORT_TERM"
                            # 止损防线逻辑开关
                            if stop_loss_type == "OpenLow" and self.open_low < 999999:
                                self.stop_loss = max(self.open_low * 0.99, curr_price - atr_multiplier * atr)
                            else:
                                self.stop_loss = curr_price - atr_multiplier * atr
                            
                        self.pending_entry_signal = None
                        t1_size = 15.0 if is_vix_panic else 33.3
                        return {
                            "action": "BUY_T1",
                            "ticker": self.ticker,
                            "price": curr_price,
                            "size_pct": t1_size,
                            "stop_loss": self.stop_loss,
                            "metadata": {
                                "holding_type": self.holding_type,
                                "vc_ratio": vc_ratio,
                                "ml_score": ml_score,
                                "rs_factor": rs_factor,
                                "stage_2": stage_2,
                                "atr": atr,
                                "rules_triggered": trigger_reason or ["Methodology #15 (Low VC pullback)", "Methodology #6 (ML/RS confirmation)"]
                            }
                        }
                        
            # Delay timer execution
            if self.delay_timer > 0:
                self.delay_timer -= 1
                if self.delay_timer == 0 and self.pending_entry_signal == "T1":
                    self.state = "T1_IN"
                    self.avg_cost = curr_price
                    self.t1_entry_bar_count = 0
                    
                    # 确定持仓类型与初始止损
                    if is_catalyst_s and stage_2 == 1:
                        self.holding_type = "LONG_TERM"
                        self.stop_loss = curr_price - self.long_term_atr_mult * atr
                        self.long_term_max_close = curr_price
                    else:
                        self.holding_type = "SHORT_TERM"
                        # ------------------ 方法论 #5: 止损位置选择优先级 ------------------
                        if stop_loss_type == "OpenLow" and self.open_low < 999999:
                            self.stop_loss = max(self.open_low * 0.99, curr_price - atr_multiplier * atr)
                        else:
                            self.stop_loss = curr_price - atr_multiplier * atr
                    
                    # 入场冻结期：建仓后头 N 个 5分钟 Bar 内，不触发止损（过滤建仓噪声）
                    self.stop_freeze_bars_remaining = stop_freeze_bars_eff
                    
                    self.pending_entry_signal = None
                    # 仓位大小：Regime C 恐慌期半仓；VIX panic 模式也缩仓
                    base_t1_size = 33.3
                    if is_vix_panic:
                        base_t1_size = 15.0
                    t1_size = base_t1_size * regime_size_multiplier
                    return {
                        "action": "BUY_T1",
                        "ticker": self.ticker,
                        "price": curr_price,
                        "size_pct": t1_size,
                        "stop_loss": self.stop_loss,
                        "metadata": {
                            "holding_type": self.holding_type,
                            "vc_ratio": vc_ratio,
                            "ml_score": ml_score,
                            "rs_factor": rs_factor,
                            "stage_2": stage_2,
                            "atr": atr,
                            "rules_triggered": ["Methodology #15 (Low VC pullback)", "Methodology #6 (ML/RS confirmation)"]
                        }
                    }
                    
        # 2. STATE: T1_IN -> T2_IN (方法论 #11: T2 确认追加) 或 T1_IN -> FULL_IN (若 use_t2_confirm 为 False)
        elif self.state == "T1_IN":
            self.t1_entry_bar_count += 1
            
            if not use_t2_confirm:
                # 豁免 T2 过渡仓追加，若放量突破早盘 H 则直接一步打满到 FULL_IN (大幅提高牛市利用率)
                if curr_price >= self.open_high and curr_vol > bar['Vol_MA20'] * open_high_vol_multiplier:
                    self.state = "FULL_IN"
                    self.stop_loss = self.avg_cost * 1.005 # 锁定微利
                    return {
                        "action": "BUY_T3", # 视为直接打满
                        "ticker": self.ticker,
                        "price": curr_price,
                        "size_pct": 66.7, # 扣除 T1 的 33.3% 之后，买入余下 66.7% 仓位
                        "stop_loss": self.stop_loss,
                        "metadata": {
                            "vc_ratio": vc_ratio,
                            "ml_score": ml_score,
                            "rs_factor": rs_factor,
                            "stage_2": stage_2,
                            "atr": atr,
                            "open_high": self.open_high,
                            "rules_triggered": ["Methodology #11 (Direct FULL Breakthrough, T2 Skipped)"]
                        }
                    }
            else:
                # 规则：T1入场 t1_wait_bars 后，如果价格仍然守住成本线上方，追加 T2 确认仓
                if self.t1_entry_bar_count >= t1_wait_bars and curr_price >= self.avg_cost:
                    self.state = "T2_IN"
                    # T2 止损宽松：给 avg_cost 以下 1% 的缓冲，避免正常回测被扫出
                    self.stop_loss = self.avg_cost * 0.990
                    return {
                        "action": "BUY_T2",
                        "ticker": self.ticker,
                        "price": curr_price,
                        "size_pct": 33.3,
                        "stop_loss": self.stop_loss,
                        "metadata": {
                            "vc_ratio": vc_ratio,
                            "ml_score": ml_score,
                            "rs_factor": rs_factor,
                            "stage_2": stage_2,
                            "atr": atr,
                            "t1_entry_bar_count": self.t1_entry_bar_count,
                            "rules_triggered": ["Methodology #11 (T2 Confirmation Expansion)"]
                        }
                    }
                
        # 3. STATE: T2_IN -> FULL_IN (方法论 #11: T3 突破加满)
        elif self.state == "T2_IN":
            # 规则：放量突破早盘 H 区间或日高，加满
            if curr_price >= self.open_high and curr_vol > bar['Vol_MA20'] * open_high_vol_multiplier:
                self.state = "FULL_IN"
                self.stop_loss = self.avg_cost * 1.005 # 锁死微利
                return {
                    "action": "BUY_T3",
                    "ticker": self.ticker,
                    "price": curr_price,
                    "size_pct": 33.4,
                    "stop_loss": self.stop_loss,
                    "metadata": {
                        "vc_ratio": vc_ratio,
                        "ml_score": ml_score,
                        "rs_factor": rs_factor,
                        "stage_2": stage_2,
                        "atr": atr,
                        "open_high": self.open_high,
                        "rules_triggered": ["Methodology #11 (T3 Breakthrough Expansion)"]
                    }
                }
                
        # 4. STATE: FULL_IN -> OUT (均线/HighWaterMark 移动止盈已合并至状态 B 统一处理)
        elif self.state == "FULL_IN":
            pass
                
        return None

# ==============================================================================
# MODULE C: PORTFOLIO COMMANDER (组合调度器)
# ==============================================================================
class PortfolioCommander:
    """
    管理全局资产配置。
    包含：
    - 方法论 #3: 杠铃仓位分配（90%避险池，10%活跃轮动池）
    - 方法论 #11: 德鲁肯米勒资本排队置换
    - 方法论 #14: 瀑布惩罚滑点
    """
    def __init__(self, initial_cash=100000.0, fee_rate=0.0003, verbose=True, use_barbell=True, position_sizing_factor=0.10):
        self.total_initial = initial_cash
        self.fee_rate = fee_rate
        self.verbose = verbose
        self.use_barbell = use_barbell
        self.position_sizing_factor = position_sizing_factor
        
        # 方法论 #3: 杠铃资产配置 (90% SGOV避险池，10% 活跃狙击池)
        if use_barbell:
            self.hedge_pool = initial_cash * 0.90 
            self.sniper_cash = initial_cash * 0.10
        else:
            self.hedge_pool = 0.0
            self.sniper_cash = initial_cash
        self.daily_sgov_rate = 0.05 / 252 # 年化 5% SGOV 避险利息
        
        self.positions = {}
        self.last_known_prices = {}
        self.equity_curve = []
        self.trades_log = []
        
    def calculate_total_equity(self, current_prices, qqq_price=0.0):
        # Update last known prices from the current active prices
        for ticker, price in current_prices.items():
            self.last_known_prices[ticker] = price
            
        pos_value = 0.0
        for ticker, pos in self.positions.items():
            # Robust price retrieval: current price -> last known price -> purchase cost (defensive)
            price = current_prices.get(ticker, self.last_known_prices.get(ticker, pos["cost"]))
            pos_value += pos["shares"] * price
            
        # 总权益 = 避险池现金 + 狙击池现金 + 股票持仓市值
        return self.hedge_pool + self.sniper_cash + pos_value
        
    def accrue_daily_interest(self):
        # 每日增计大后方 SGOV 避险池的现金利息 (方法论 #3)
        self.hedge_pool *= (1.0 + self.daily_sgov_rate)
        
    def execute_order(self, request, timestamp, qqq_price=0.0):
        ticker = request["ticker"]
        action = request["action"]
        price = request["price"]
        
        if action in ["SELL_STOP", "SELL_MA20_TRAIL", "SELL_THESIS_FAIL", "SELL_BREAKEVEN"]:
            if ticker not in self.positions or self.positions[ticker]["shares"] <= 0:
                return
                
            shares = self.positions[ticker]["shares"]
            cost = self.positions[ticker]["cost"]
            
            # 方法论 #14: 利弗莫尔瀑布滑点罚则
            slippage = 0.0
            if request.get("is_waterfall", False) or action == "SELL_THESIS_FAIL":
                slippage = price * 0.015 # 紧急逃生滑点 1.5%
                
            final_exit_price = price - slippage
            gross = shares * final_exit_price
            fee = gross * self.fee_rate
            net = gross - fee
            
            # 回收现金至活跃的狙击池
            self.sniper_cash += net
            pnl_pct = ((final_exit_price - cost) / cost) * 100
            
            trade_pnl_cash = shares * (final_exit_price - cost) - fee
            self.trades_log.append({
                "Timestamp": timestamp,
                "Ticker": ticker,
                "Action": action,
                "Shares": shares,
                "Price": final_exit_price,
                "Value": net,
                "PnL%": pnl_pct,
                "PnL_Cash": trade_pnl_cash,
                "Metadata": request.get("metadata", {})
            })
            
            del self.positions[ticker]
            rules_str = ", ".join(request.get("metadata", {}).get("rules_triggered", []))
            if self.verbose:
                print(f"🔴 [{timestamp}] {action} 执行: {ticker} 卖出 {shares:.1f} 股 @ ${final_exit_price:.2f} (盈亏: {pnl_pct:+.2f}%, 罚滑点: ${shares*slippage:.2f}) | 触发规则: {rules_str}")
            
        elif action in ["BUY_T1", "BUY_T2", "BUY_T3"]:
            size_pct = request["size_pct"]
            
            # 使用配置文件的仓位系数（如 10% 或更大幅度，防爆仓）
            target_value = (self.hedge_pool + self.sniper_cash) * self.position_sizing_factor * (size_pct / 100.0)
            
            # 方法论 #11: 德鲁肯米勒资本排队置换
            if self.sniper_cash < target_value:
                target_value = min(target_value, self.sniper_cash)
                
            if target_value < 50.0:
                return
                
            fee = target_value * self.fee_rate
            net_buy = target_value - fee
            shares_bought = net_buy / price
            
            self.sniper_cash -= target_value
            
            if ticker not in self.positions:
                self.positions[ticker] = {"shares": shares_bought, "cost": price}
            else:
                old_shares = self.positions[ticker]["shares"]
                old_cost = self.positions[ticker]["cost"]
                new_shares = old_shares + shares_bought
                new_cost = ((old_shares * old_cost) + (shares_bought * price)) / new_shares
                self.positions[ticker] = {"shares": new_shares, "cost": new_cost}
                
            self.trades_log.append({
                "Timestamp": timestamp,
                "Ticker": ticker,
                "Action": action,
                "Shares": shares_bought,
                "Price": price,
                "Value": target_value,
                "PnL%": 0.0,
                "Metadata": request.get("metadata", {})
            })
            rules_str = ", ".join(request.get("metadata", {}).get("rules_triggered", []))
            if self.verbose:
                print(f"🟢 [{timestamp}] {action} 执行: {ticker} 买入 {shares_bought:.1f} 股 @ ${price:.2f} (占用狙击现金: ${target_value:.2f}) | 触发规则: {rules_str}")
                
    def sync_qqq_fallback(self, qqq_price, market_regime, current_prices):
        if qqq_price <= 0:
            return
            
        if market_regime == "C":
            # 🔴 Regime C: 一键平仓所有多头，100% 避险 (一键强制出清个股)
            active_tickers = list(self.positions.keys())
            for t in active_tickers:
                price = current_prices.get(t, self.last_known_prices.get(t, self.positions[t]["cost"]))
                shares = self.positions[t]["shares"]
                cost = self.positions[t]["cost"]
                gross = shares * price
                fee = gross * self.fee_rate
                net = gross - fee
                self.hedge_pool += net
                pnl_pct = ((price - cost) / cost) * 100
                self.trades_log.append({
                    "Timestamp": "熊市清仓",
                    "Ticker": t,
                    "Action": "SELL_FORCE_C",
                    "Shares": shares,
                    "Price": price,
                    "Value": net,
                    "PnL%": pnl_pct,
                    "PnL_Cash": shares * (price - cost) - fee,
                    "Metadata": {"reason": "Regime C Force Cashout"}
                })
                del self.positions[t]
                if self.verbose:
                    print(f"🔴 熊市警报！一键强制平仓个股 {t} @ ${price:.2f}，资金全量收回避险池。")

# ==============================================================================
# MAIN EVENT LOOP
# ==============================================================================
def run_joint_backtest(tickers, days=90, custom_rules=None, verbose=True):
    import builtins
    def print(*args, **kwargs):
        if verbose:
            builtins.print(*args, **kwargs)
            
    if custom_rules is not None:
        rules = custom_rules
    else:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "tactical_rules.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
        else:
            rules = {
                "methodology_15_low_catalyst_rs": {
                    "vc_threshold_pct": 30.0,
                    "bracket_stop_loss_pct": 0.8,
                    "atr_stop_multiplier": 1.5,
                    "t1_size_pct": 33.3,
                    "t2_t3_size_pct": 66.7
                }
            }
        
    broker = DataFeatureBroker()
    
    # 1. Load QQQ benchmark data
    print("📡 正在获取 QQQ 大盘指数作为基准参考...")
    qqq_df = broker.process_and_merge("QQQ", days)
    if qqq_df.empty:
        print("🔴 无法获取 QQQ 指标，基准对齐失效。")
        
    # 2. Load VIX daily index for macro filter
    print("📡 正在获取 VIX 恐慌指数以支持宏观风控...")
    vix_df = broker.get_daily_indicators("^VIX")
    vix_map = {}
    vix_roc_map = {}
    if not vix_df.empty:
        vix_df['DateOnly'] = vix_df.index.date
        vix_map = vix_df.set_index('DateOnly')['Close'].to_dict()
        vix_df['ROC'] = vix_df['Close'].pct_change()
        vix_roc_map = vix_df.set_index('DateOnly')['ROC'].to_dict()
        
    # Calculate QQQ daily macro MAs for autonomous regime classification
    print("📡 正在获取 QQQ 日线大盘数据以计算大周期均线...")
    qqq_daily_df = broker.get_daily_indicators("QQQ")
    qqq_ma5_map = {}
    qqq_ma50_map = {}
    qqq_ma200_map = {}
    if not qqq_daily_df.empty:
        qqq_daily_df['DateOnly'] = qqq_daily_df.index.date
        qqq_daily_df['MA5'] = qqq_daily_df['Close'].rolling(window=5).mean()
        qqq_ma5_map = qqq_daily_df.set_index('DateOnly')['MA5'].to_dict()
        qqq_ma50_map = qqq_daily_df.set_index('DateOnly')['MA50'].to_dict()
        qqq_ma200_map = qqq_daily_df.set_index('DateOnly')['MA200'].to_dict()
        
    # 3. Load daily news events and catalysts database (Methodology #12)
    event_db = {}
    harvest_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning", "daily_harvest.jsonl")
    if os.path.exists(harvest_path):
        try:
            with open(harvest_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        date_key = entry.get("date") # e.g. "2026-05-26"
                        ticker_key = entry.get("ticker")
                        if date_key and ticker_key:
                            if date_key not in event_db:
                                event_db[date_key] = {}
                            event_db[date_key][ticker_key] = {
                                "catalyst_level": entry.get("catalyst_level", "★☆☆"),
                                "sentiment": entry.get("sentiment_score", 0.0)
                            }
                    except Exception:
                        pass
            print(f"📖 成功导入本地事件舆情与催化剂数据库 | 包含 {len(event_db)} 个交易日的记录")
        except Exception as e:
            print(f"⚠️ 读取 daily_harvest.jsonl 失败: {e}")
            
    print("🧠 正在加载高频 5分钟 因子数据与 Stage 2 前置过滤...")
    data_dict = {}
    for ticker in tickers:
        df = broker.process_and_merge(ticker, days)
        if not df.empty:
            data_dict[ticker] = df
            
    if not data_dict:
        print("🔴 缺少数据，回测中止。")
        return
        
    all_timestamps = sorted(list(set().union(*(df.index for df in data_dict.values()))))
    
    # Filter timestamps to cover only the last 'days' calendar days of data, if specified
    if days and all_timestamps:
        latest_date = all_timestamps[-1].date()
        start_date = latest_date - timedelta(days=days)
        all_timestamps = [ts for ts in all_timestamps if ts.date() >= start_date]
        
        # Slice qqq_df to the same range so that the benchmark calculation is 100% correct
        if not qqq_df.empty:
            qqq_df = qqq_df[qqq_df.index.date >= start_date]
        
    print(f"📊 混合池化完成. 模拟总 Bar 数: {len(all_timestamps)}")
    
    # Initialize 15-Methodology machines
    state_machines = {}
    for ticker in data_dict.keys():
        # Set default base catalyst level (SNOW to ★★★, others to ★☆☆)
        level = "★★★" if ticker == "SNOW" else "★☆☆"
        state_machines[ticker] = TacticalStateMachine(ticker, rules, level)
        
    use_barbell = rules.get("use_barbell", True)
    position_sizing_factor = rules.get("methodology_15_low_catalyst_rs", {}).get("position_sizing_factor", 0.10)
    commander = PortfolioCommander(initial_cash=100000.0, verbose=verbose, use_barbell=use_barbell, position_sizing_factor=position_sizing_factor)
    
    current_date = None
    breadth_pct = 0.5       # Pre-initialize market breadth
    nvda_below_vwap_consecutive = 0
    daily_open_cache = {}   # {ticker: today's open price} — refreshed each new trading day
    qqq_daily_open_cache = {}  # {date: QQQ open price} — pre-built once from qqq_df
    
    # Pre-build QQQ daily open cache
    if not qqq_df.empty:
        for ts_idx in qqq_df.index:
            d = ts_idx.date()
            if d not in qqq_daily_open_cache:
                qqq_daily_open_cache[d] = qqq_df.loc[ts_idx, 'Open']
                
    print("🚀 正在预构建内存数据索引 (100x 回测加速)...")
    bar_data_lookup = {ts: {} for ts in all_timestamps}
    for ticker, df in data_dict.items():
        df_dict = df.to_dict('index')
        for ts_idx, row in df_dict.items():
            if ts_idx in bar_data_lookup:
                bar_data_lookup[ts_idx][ticker] = row
    
    regime_history = []
    current_day_regime = "A"
    queued_requests = []
    
    for ts in all_timestamps:
        ts_date = ts.date()
        time_str = ts.strftime('%H:%M')
        
        # Reset daily and accrue SGOV interest (Methodology #3)
        if ts_date != current_date:
            current_date = ts_date
            commander.accrue_daily_interest()
            for sm in state_machines.values():
                sm.reset_daily_session(ts_date)
            # Refresh daily open price cache and pre-compute breadth_pct once per day using pre-built cache
            daily_open_cache = {}
            stage2_count = 0
            total_valid = 0
            if ts in bar_data_lookup:
                for t, row in bar_data_lookup[ts].items():
                    daily_open_cache[t] = row['Open']
                    total_valid += 1
                    if row.get('Stage_2', 0) == 1:
                        stage2_count += 1
            breadth_pct = (stage2_count / total_valid) if total_valid > 0 else 0.5
            
            # 【修复 Regime 前瞻偏差】：强制使用昨日（T-1）收盘价数据决定今日 Regime，拒绝未来函数
            past_vix_dates = [k for k in vix_map.keys() if k < ts_date]
            yesterday_vix_date = max(past_vix_dates) if past_vix_dates else None
            
            vix_now = vix_map.get(yesterday_vix_date, 18.0) if yesterday_vix_date else 18.0
            vix_roc = vix_roc_map.get(yesterday_vix_date, 0.0) if yesterday_vix_date else 0.0
            
            past_qqq_dates = [k for k in qqq_ma50_map.keys() if k < ts_date]
            yesterday_qqq_date = max(past_qqq_dates) if past_qqq_dates else None
            
            if yesterday_qqq_date:
                q_close = qqq_daily_df[qqq_daily_df['DateOnly'] == yesterday_qqq_date]['Close'].iloc[0]
                q_ma50 = qqq_ma50_map.get(yesterday_qqq_date, 0.0)
                q_ma200 = qqq_ma200_map.get(yesterday_qqq_date, 0.0)
            else:
                q_close = 0.0
                q_ma50 = 0.0
                q_ma200 = 0.0
                
            raw_c = (q_close < q_ma200) or (vix_now > 25.0) or (vix_roc >= 0.12)
            raw_b = (not raw_c) and (
                (vix_now >= 20.0) or 
                (q_close < q_ma50) or
                (breadth_pct < 0.35)
            )
            raw_regime = "C" if raw_c else ("B" if raw_b else "A")
            
            regime_history.append(raw_regime)
            if len(regime_history) > 5:
                regime_history.pop(0)
                
            from collections import Counter
            votes = Counter(regime_history)
            current_day_regime = votes.most_common(1)[0][0]
            
        # Sector leader joint defense mapping (Methodology #2) - TEMPORARILY DISABLED BY USER DECISION
        sector_leader_ok = True
        
        # QQQ price now (Open of current bar)
        qqq_price_now = 0.0
        if not qqq_df.empty and ts in qqq_df.index:
            qqq_price_now = bar_data_lookup[ts].get("QQQ", {}).get("Open", qqq_df.loc[ts, 'Open'])
            
        # ══════════════════════════════════════════════════════════
        # T+1 EXECUTION ENGINE: Execute pending queued requests at the CURRENT Open price!
        # ══════════════════════════════════════════════════════════
        if queued_requests:
            queued_sells = [q for q in queued_requests if "SELL" in q["action"]]
            queued_buys = [q for q in queued_requests if "BUY" in q["action"]]
            
            # 1. First execute all exits (sells) to free up capital
            for req in queued_sells:
                ticker = req["ticker"]
                if ticker in bar_data_lookup[ts]:
                    req["price"] = bar_data_lookup[ts][ticker]["Open"] # Force T+1 Open execution
                    commander.execute_order(req, ts.strftime('%m-%d %H:%M'), qqq_price=qqq_price_now)
                    
            # 2. Next execute position additions (BUY_T2, BUY_T3)
            for req in queued_buys:
                if req["action"] in ["BUY_T2", "BUY_T3"]:
                    ticker = req["ticker"]
                    if ticker in bar_data_lookup[ts]:
                        req["price"] = bar_data_lookup[ts][ticker]["Open"]
                        commander.execute_order(req, ts.strftime('%m-%d %H:%M'), qqq_price=qqq_price_now)
                        
            # 3. Sort BUY_T1 orders by their rs_factor, and execute with de-correlation gate
            queued_buys_new = [q for q in queued_buys if q["action"] == "BUY_T1"]
            queued_buys_new.sort(key=lambda x: x["metadata"].get("rs_factor", 1.0), reverse=True)
            
            max_active_positions = rules.get("methodology_15_low_catalyst_rs", {}).get("max_active_positions", 5)
            if current_day_regime == "B":
                max_active_positions = 2 # 🚨 Regime B transitional limit
                
            max_new_buys_per_bar = rules.get("methodology_15_low_catalyst_rs", {}).get("max_new_buys_per_bar", 3)
            new_buys_in_bar = 0
            
            for req in queued_buys_new:
                ticker = req["ticker"]
                if ticker in bar_data_lookup[ts]:
                    req["price"] = bar_data_lookup[ts][ticker]["Open"]
                    rs = req["metadata"].get("rs_factor", 1.0)
                    
                    if ticker in commander.positions:
                        commander.execute_order(req, ts.strftime('%m-%d %H:%M'), qqq_price=qqq_price_now)
                    elif len(commander.positions) < max_active_positions and new_buys_in_bar < max_new_buys_per_bar:
                        commander.execute_order(req, ts.strftime('%m-%d %H:%M'), qqq_price=qqq_price_now)
                        new_buys_in_bar += 1
                    else:
                        if verbose:
                            if new_buys_in_bar >= max_new_buys_per_bar:
                                print(f"🚫 [{ts.strftime('%m-%d %H:%M')}] {ticker} 新开仓被拦截！原因: 触发单次Bar开仓『信号去相关门』上限 ({new_buys_in_bar}/{max_new_buys_per_bar})")
                            else:
                                print(f"🚫 [{ts.strftime('%m-%d %H:%M')}] {ticker} 新开仓被拦截！原因: 触发全局持仓上限 ({len(commander.positions)}/{max_active_positions})")
            
            # Processed all queued requests
            queued_requests = []
                
        # Sector leader joint defense mapping (Methodology #2) - TEMPORARILY DISABLED BY USER DECISION
        sector_leader_ok = True
            
        # ══════════════════════════════════════════════════════════
        # 市场环境分级过滤器 (5日投票平滑后的 Regime 绑定)
        # ══════════════════════════════════════════════════════════
        qqq_trend_ok = True
        qqq_strong = False
        regime_rs_penalty = 0.0
        regime_cutoff_override = None
        market_regime = current_day_regime

        if market_regime == "C":
            qqq_trend_ok = True
        elif market_regime == "B":
            qqq_trend_ok = True
            regime_rs_penalty = 0.5
            regime_cutoff_override = "11:30"
        else:
            qqq_trend_ok = True
            # Check intraday strong momentum on QQQ
            if not qqq_df.empty and ts in qqq_df.index:
                qqq_bar = qqq_df.loc[ts]
                qqq_open_today = qqq_daily_open_cache.get(ts_date, qqq_bar['Open'])
                qqq_intraday_ret = (qqq_bar['Close'] - qqq_open_today) / qqq_open_today if qqq_open_today > 0 else 0
                qqq_strong = qqq_intraday_ret >= 0.003

            
        # VIX Macro Filter: If VIX is in a panic state (vix_close >= 23.0), we trigger risk overlays
        # 【修复 VIX 前瞻偏差】：使用昨日 VIX 收盘价判定恐慌状态
        vix_close = vix_map.get(yesterday_vix_date, 15.0) if yesterday_vix_date else 15.0
        is_vix_panic = vix_close >= 23.0
        
        current_prices = {t: bar_data_lookup[ts][t]['Close'] for t in bar_data_lookup[ts].keys()}
        
        # 1. 收集当前 Bar 的所有 Tactical 决策请求 (信号去相关门第一阶段)
        pending_sells = []
        pending_buys_existing = []  # BUY_T2, BUY_T3
        pending_buys_new = []       # BUY_T1
        
        for ticker, sm in state_machines.items():
            if ticker not in bar_data_lookup[ts]:
                continue
                
            bar = bar_data_lookup[ts][ticker]
            
            # Fetch dynamic daily catalyst level & sentiment score (Methodology #12)
            date_str_key = ts_date.strftime("%Y-%m-%d")
            ticker_events = event_db.get(date_str_key, {}).get(ticker, {})
            
            dynamic_level = ticker_events.get("catalyst_level")
            if dynamic_level:
                sm.catalyst_level = dynamic_level
                
            dynamic_sentiment = ticker_events.get("sentiment", 0.0)
            
            # Map ML score and RS factor dynamically using the real news sentiment!
            ml_score = 0.85 if bar['Stage_2'] == 1 else 0.40
            if dynamic_sentiment > 0.3:
                ml_score = min(1.0, ml_score + 0.15)
            elif dynamic_sentiment < -0.3:
                ml_score = max(0.0, ml_score - 0.25)
                
            # Compute TRUE Relative Strength vs QQQ (Methodology #6):
            # RS = (ticker_intraday_return) / (QQQ_intraday_return)  — same-day comparison
            ticker_open_today = daily_open_cache.get(ticker, bar['Close'])
            ticker_return = (bar['Close'] - ticker_open_today) / ticker_open_today if ticker_open_today > 0 else 0
            if not qqq_df.empty and ts in qqq_df.index:
                qqq_open_today = qqq_daily_open_cache.get(ts_date, qqq_df.loc[ts, 'Close'])
                qqq_return = (qqq_df.loc[ts, 'Close'] - qqq_open_today) / qqq_open_today if qqq_open_today > 0 else 0
                if abs(qqq_return) > 0.002:   # Bug Fix: raise threshold to 0.2% to prevent RS explosion
                    rs_factor = ticker_return / abs(qqq_return)  # >1 = leading, <1 = lagging
                    rs_factor = min(rs_factor, 5.0)   # Bug Fix: cap RS at 5.0x (prevents math explosion on nearly-flat QQQ days)
                elif ticker_return > 0.001:   # stock clearly up, QQQ flat
                    rs_factor = 2.5
                elif ticker_return < -0.001:  # stock clearly down, QQQ flat
                    rs_factor = 0.3
                else:
                    rs_factor = 1.0   # both flat = neutral
            else:
                # Fallback: VWAP proxy
                rs_factor = 1.9 if bar['Close'] > bar['VWAP'] else 0.9
            
            # Sentiment boost
            if dynamic_sentiment > 0.5:
                rs_factor = min(5.0, rs_factor + 0.5)
                
            request = sm.process_bar(bar, time_str, ml_score, rs_factor, sector_leader_ok, qqq_trend_ok, is_vix_panic, qqq_strong, regime_rs_penalty, regime_cutoff_override, market_regime=market_regime)
            if request:
                queued_requests.append(request)
                
        # 6. 牛市Q/熊市出清的资金重置 (100% 资金效率托底同步)
        qqq_price_close = 0.0
        if not qqq_df.empty and ts in qqq_df.index:
            qqq_price_close = bar_data_lookup[ts].get("QQQ", {}).get("Close", qqq_df.loc[ts, 'Close'])
            
        current_prices_close = {t: bar_data_lookup[ts][t]['Close'] for t in bar_data_lookup[ts].keys()}
        commander.sync_qqq_fallback(qqq_price_close, market_regime, current_prices_close)
        
        # Track equity curve using close price
        end_equity = commander.calculate_total_equity(current_prices_close, qqq_price_close)
        commander.equity_curve.append({"Timestamp": ts, "Equity": end_equity})
        
    # ==============================================================================
    # EVALUATION & QUANT PERFORMANCE DASHBOARD
    # ==============================================================================
    curve_df = pd.DataFrame(commander.equity_curve).set_index("Timestamp")
    curve_df['Return'] = curve_df['Equity'].pct_change()
    
    total_return = (curve_df['Equity'].iloc[-1] - commander.total_initial) / commander.total_initial * 100
    
    # Calculate Max Drawdown
    curve_df['RollMax'] = curve_df['Equity'].cummax()
    curve_df['Drawdown'] = (curve_df['Equity'] - curve_df['RollMax']) / curve_df['RollMax']
    max_drawdown = curve_df['Drawdown'].min() * 100
    
    # Calculate Max Drawdown Duration (trading days)
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
    max_drawdown_bars = max(drawdown_durations) if drawdown_durations else 0
    max_drawdown_days = round(max_drawdown_bars / 78, 1) # 78 bars per day
    
    # Sharpe (Risk-Free = 4% annualized = 0.04 / 252 daily)
    daily_returns = curve_df['Return'].resample('D').sum().dropna()
    rf_daily = 0.04 / 252
    excess_daily = daily_returns - rf_daily
    sharpe = np.sqrt(252) * (excess_daily.mean() / daily_returns.std()) if daily_returns.std() > 0 else 0.0
    
    # Sortino (Risk-Free = 4%)
    downside_returns = excess_daily[excess_daily < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino = (excess_daily.mean() * 252) / downside_std if downside_std > 0 else 0.0
    
    # Calmar (Annualized Return / Max Drawdown)
    annualized_return = daily_returns.mean() * 252 * 100
    calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
    
    # Trade statistics
    sell_trades = [t for t in commander.trades_log if "SELL" in t['Action']]
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
    alpha = total_return
    if not qqq_df.empty:
        qqq_close_series = qqq_df['Close']
        qqq_return = (qqq_close_series.iloc[-1] - qqq_close_series.iloc[0]) / qqq_close_series.iloc[0] * 100
        alpha = total_return - qqq_return
        
    print("\n" + "="*60)
    print("      🚀 15条方法论高频量化回测绩效仪表盘")
    print("="*60)
    print(f"回测标的池   : {list(data_dict.keys())}")
    print(f"账户初始资金 : ${commander.total_initial:,.2f}")
    print(f"  • SGOV避险池: ${commander.hedge_pool:,.2f}")
    print(f"  • 活跃狙击池: ${commander.sniper_cash:,.2f}")
    print(f"最终账户总值 : ${curve_df['Equity'].iloc[-1]:,.2f}")
    print("-" * 60)
    print(f"累计账户收益 : {total_return:+.2f}% | 同期 QQQ大盘收益: {qqq_return:+.2f}%")
    print(f"超额收益 Alpha: {alpha:+.2f}%  {'🟢 (跑赢大盘)' if alpha > 0 else '🔴 (未跑赢大盘)'}")
    print("-" * 60)
    print(f"历史最大回撤 : {max_drawdown:.2f}% | 最长回撤恢复天数: {max_drawdown_days} 天")
    print(f"年化夏普比率 : {sharpe:.2f}  | 年化索提诺比率: {sortino:.2f} | 年化卡玛比率: {calmar:.2f}")
    print("-" * 60)
    print(f"执行交易总数 : {len(commander.trades_log)} 次 (完成交易笔数: {len(sell_trades)} 次)")
    print(f"交易胜率     : {win_rate:.1f}%")
    print(f"获利因子 (PF): {profit_factor:.2f}  {'🟢 (期望值为正)' if profit_factor >= 1.0 else '🔴 (期望值为负)'}")
    print(f"平均盈亏比   : {payoff_ratio:.2f} (平均盈利: ${avg_win:.2f} / 平均亏损: ${avg_loss:.2f})")
    print("="*60 + "\n")
    
    # Save JSON findings
    report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "findings", "joint_backtest_report.json")
    metrics = {
        "tickers": list(data_dict.keys()),
        "total_initial": commander.total_initial,
        "final_equity": curve_df['Equity'].iloc[-1],
        "total_return_pct": total_return,
        "qqq_return_pct": qqq_return,
        "alpha_pct": alpha,
        "max_drawdown_pct": max_drawdown,
        "max_drawdown_days": max_drawdown_days,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "trades_count": len(commander.trades_log),
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "payoff_ratio": payoff_ratio,
        "equity_curve": commander.equity_curve,
        "trades_log": commander.trades_log
    }
    with open(report_path, "w", encoding="utf-8") as f:
        # Save a copy without the timestamp object for clean JSON serialization
        metrics_serializable = metrics.copy()
        metrics_serializable["equity_curve"] = [{"Timestamp": str(x["Timestamp"]), "Equity": x["Equity"]} for x in commander.equity_curve]
        json.dump(metrics_serializable, f, indent=2)
    return metrics

if __name__ == "__main__":
    run_joint_backtest(["ARM", "NVDA", "SNOW", "AMD", "COHR", "VST", "SYM", "AVGO", "MRVL", "ANET", "CSCO", "LITE", "MU", "TSM", "VRT"], days=90)
