"""
Technical Indicator Computation Engine
=======================================
Input: pandas DataFrame with columns [open, high, low, close, volume], datetime index
Output: flat dict of all computed indicators, ready to insert into technical_indicators table

All indicators are computed LOCALLY from OHLCV data — no external API needed.
Formulas are documented inline for auditability.

COMPUTATION TIERS (efficiency):
  TIER_1 (session-static):  Compute ONCE at M1 start from daily bars.   ~30 indicators.
                            Includes: MA20+, ADX, MACD, BB, ATR, pivots, fib, SAR, CCI.
  TIER_2 (5-min cache):     Recompute every 5 min from intraday bars.    ~7 indicators.
                            Includes: MA5/MA10, RSI, Stoch, MFI, WilliamsR.
  TIER_3 (every 2 min):     Recompute every M3 cycle from latest bars.   ~10 indicators.
                            Includes: VWAP, Volume ratio, candle body/wick, consecutive bars.

Usage:
    df = yf.download('AAPL', period='6mo', interval='1d')
    indicators = compute_all_indicators(df)        # Full compute (M1 start)
    tier3 = compute_tier3(df_intraday)              # Fast compute (M3 every 2 min)
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from functools import lru_cache

# ============================================================
# UTILITY
# ============================================================


def _safe_div(a: float, b: float, fallback: float = 0.0) -> float:
    """Safely divide a by b, returning fallback on zero division."""
    return a / b if b and b != 0 else fallback


def _rolling_window(arr: np.ndarray, window: int):
    """Sliding window generator for manual indicator calc if needed."""
    shape = (arr.shape[0] - window + 1, window)
    strides = (arr.strides[0], arr.strides[0])
    return np.lib.stride_tricks.sliding_window_view(arr, window)


# ============================================================
# CATEGORY 1: TREND INDICATORS
# ============================================================


def compute_ma(close: pd.Series, period: int) -> float:
    """Compute simple moving average for the given period."""
    # Formula: SMA = sum(close[-period:]) / period
    if len(close) < period:
        return None
    return float(close.rolling(window=period).mean().iloc[-1])


def compute_ema(close: pd.Series, period: int) -> float:
    """Compute exponential moving average for the given period."""
    # Formula: EMA_t = α × price_t + (1-α) × EMA_{t-1}, where α = 2 / (period + 1)
    if len(close) < period:
        return None
    return float(close.ewm(span=period, adjust=False).mean().iloc[-1])


def compute_ma_slope(close: pd.Series, period: int = 20, lookback: int = 5) -> float:
    """Compute the rate of change of the moving average slope."""
    # Formula: (MA_t - MA_{t-lookback}) / MA_{t-lookback} / lookback
    # Positive → uptrend accelerating. Negative → downtrend.
    ma = close.rolling(window=period).mean()
    if len(ma) < period + lookback:
        return None
    return float((ma.iloc[-1] - ma.iloc[-lookback]) / ma.iloc[-lookback] / lookback)


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    """Compute Average Directional Index, +DI, and -DI for trend strength."""
    # Formula: TR = max(H-L, |H-C_prev|, |L-C_prev|); ATR = Wilder(TR)
    # +DI = 100 × Wilder(+DM) / ATR; -DI = 100 × Wilder(-DM) / ATR
    # DX = 100 × |+DI - -DI| / (+DI + -DI); ADX = Wilder(DX)
    if len(close) < period * 2:
        return None, None, None

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()

    # Handle NaN from zero-division: if both +DI and -DI are zero, ADX is 0 (no trend)
    adx = adx.fillna(0)
    plus_di = plus_di.fillna(0)
    minus_di = minus_di.fillna(0)

    return float(adx.iloc[-1]), float(plus_di.iloc[-1]), float(minus_di.iloc[-1])


def compute_parabolic_sar(high, low, close,
                          af_start=0.02, af_step=0.02, af_max=0.20) -> float:
    """Compute Parabolic SAR trailing stop and trend direction."""
    # SAR_t = SAR_{t-1} + AF × (EP_{t-1} - SAR_{t-1}); AF accelerates to af_max
    # Flip: when price crosses SAR, reset SAR to prior EP, flip direction
    n = len(close)
    if n < 20:
        return None

    sar = np.zeros(n)
    ep = np.zeros(n)
    af = np.zeros(n)
    trend = np.ones(n)  # +1 uptrend, -1 downtrend

    # Initial trend: first bar direction
    trend[0] = 1
    sar[0] = low.iloc[0]
    ep[0] = high.iloc[0]
    af[0] = af_start

    for i in range(1, n):
        prev_sar = sar[i-1]
        prev_ep = ep[i-1]
        prev_af = af[i-1]
        prev_trend = trend[i-1]

        # New SAR
        sar[i] = prev_sar + prev_af * (prev_ep - prev_sar)

        # Clamp SAR: in uptrend it must be below prior two lows; in downtrend above prior two highs
        if prev_trend == 1:
            sar[i] = min(sar[i], low.iloc[i-1], low.iloc[max(0, i-2)])
        else:
            sar[i] = max(sar[i], high.iloc[i-1], high.iloc[max(0, i-2)])

        # Check flip
        if prev_trend == 1:
            if low.iloc[i] < sar[i]:
                trend[i] = -1
                sar[i] = ep[i-1]  # reset to EP
                ep[i] = low.iloc[i]
                af[i] = af_start
                continue
            # Update EP and AF
            if high.iloc[i] > prev_ep:
                ep[i] = high.iloc[i]
                af[i] = min(prev_af + af_step, af_max)
            else:
                ep[i] = prev_ep
                af[i] = prev_af
        else:
            if high.iloc[i] > sar[i]:
                trend[i] = 1
                sar[i] = ep[i-1]
                ep[i] = high.iloc[i]
                af[i] = af_start
                continue
            if low.iloc[i] < prev_ep:
                ep[i] = low.iloc[i]
                af[i] = min(prev_af + af_step, af_max)
            else:
                ep[i] = prev_ep
                af[i] = prev_af

        trend[i] = prev_trend

    return float(sar[-1]), int(trend[-1])


# ============================================================
# CATEGORY 2: MOMENTUM INDICATORS
# ============================================================


def compute_rsi(close: pd.Series, period: int = 14) -> float:
    """Compute Relative Strength Index for the given period."""
    # RSI = 100 - 100/(1 + RS), where RS = avg_gain / avg_loss (Wilder smoothed)
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(100.0)  # If no losses, RSI = 100
    return float(rsi.iloc[-1])


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Compute MACD line, signal line, and histogram."""
    # MACD_line = EMA(fast) - EMA(slow); Signal = EMA(MACD_line); Histogram = MACD_line - Signal
    if len(close) < slow + signal:
        return None, None, None
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - macd_signal
    return float(macd_line.iloc[-1]), float(macd_signal.iloc[-1]), float(histogram.iloc[-1])


def compute_stochastic(high, low, close, k_period: int = 14, d_period: int = 3):
    """Compute Stochastic Oscillator %K and %D."""
    # %K = 100 × (close - lowest_low) / (highest_high - lowest_low); %D = SMA(%K, d_period)
    if len(close) < k_period:
        return None, None
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    stoch_k = 100.0 * (close - lowest_low) / (highest_high - lowest_low)
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return float(stoch_k.iloc[-1]), float(stoch_d.iloc[-1])


def compute_williams_r(high, low, close, period: int = 14) -> float:
    """Compute Williams %R oscillator."""
    # %R = -100 × (highest_high - close) / (highest_high - lowest_low); > -20 overbought, < -80 oversold
    if len(close) < period:
        return None
    hh = high.rolling(window=period).max()
    ll = low.rolling(window=period).min()
    wr = -100.0 * (hh - close) / (hh - ll)
    return float(wr.iloc[-1])


def compute_cci(high, low, close, period: int = 20) -> float:
    """Compute Commodity Channel Index."""
    # TP = (H+L+C)/3; CCI = (TP - SMA(TP)) / (0.015 × mean_absolute_deviation(TP))
    if len(close) < period:
        return None
    tp = (high + low + close) / 3.0
    tp_sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - tp_sma) / (0.015 * mad)
    return float(cci.iloc[-1])


# ============================================================
# CATEGORY 3: VOLATILITY INDICATORS
# ============================================================


def compute_bollinger_bands(close: pd.Series, period: int = 20, std_mult: float = 2.0):
    """Compute Bollinger Bands upper, middle, lower, and width."""
    # Middle = SMA(close); Upper/Lower = Middle ± std_mult × std(close); Width = (Upper-Lower)/Middle
    if len(close) < period:
        return None, None, None, None
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + std_mult * std
    lower = middle - std_mult * std
    width = (upper - lower) / middle
    return (float(upper.iloc[-1]), float(middle.iloc[-1]),
            float(lower.iloc[-1]), float(width.iloc[-1]))


def compute_atr(high, low, close, period: int = 14) -> float:
    """Compute Average True Range for the given period."""
    # TR = max(H-L, |H-C_prev|, |L-C_prev|); ATR = Wilder smoothed TR (EWM, alpha=1/period)
    if len(close) < period + 1:
        return None
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return float(atr.iloc[-1])


def compute_keltner_channels(high, low, close, ema_period: int = 20, atr_mult: float = 2.0):
    """Compute Keltner Channels upper, middle, and lower."""
    # Middle = EMA(close); Upper/Lower = Middle ± atr_mult × ATR
    if len(close) < ema_period * 2:
        return None, None, None
    middle = close.ewm(span=ema_period, adjust=False).mean()
    atr_val = compute_atr(high, low, close, ema_period)
    if atr_val is None:
        return None, None, None
    upper = float(middle.iloc[-1]) + atr_mult * atr_val
    lower = float(middle.iloc[-1]) - atr_mult * atr_val
    return upper, float(middle.iloc[-1]), lower


# ============================================================
# CATEGORY 4: VOLUME INDICATORS
# ============================================================


def compute_volume_sma(volume: pd.Series, period: int = 20) -> float:
    """Volume 20-period SMA"""
    if len(volume) < period:
        return None
    return float(volume.rolling(window=period).mean().iloc[-1])


def compute_volume_ratio(volume: pd.Series, period: int = 20) -> float:
    """Compute ratio of current volume to period average volume."""
    # > 1.5 = unusually high volume
    if len(volume) < period:
        return None
    avg = volume.rolling(window=period).mean().iloc[-1]
    return float(volume.iloc[-1]) / avg if avg else None


def compute_obv(close: pd.Series, volume: pd.Series) -> float:
    """Compute On-Balance Volume cumulative value."""
    # OBV accumulates volume on up days, subtracts on down days, unchanged on flat days
    direction = np.sign(close.diff())
    obv = (direction * volume).cumsum()
    return float(obv.iloc[-1])


def compute_vwap(high, low, close, volume) -> float:
    """Compute Volume-Weighted Average Price."""
    # VWAP = sum(TP × volume) / sum(volume), where TP = (H+L+C)/3
    tp = (high + low + close) / 3.0
    total_pv = (tp * volume).sum()
    total_v = volume.sum()
    return float(total_pv / total_v) if total_v != 0 else None


def compute_mfi(high, low, close, volume, period: int = 14) -> float:
    """Compute Money Flow Index for the given period."""
    # MFI = 100 - 100/(1 + Money Ratio); Money Ratio = Positive MF / Negative MF (TP-weighted)
    if len(close) < period + 1:
        return None
    tp = (high + low + close) / 3.0
    raw_mf = tp * volume
    tp_diff = tp.diff()
    pos_mf = raw_mf.where(tp_diff > 0, 0.0).rolling(window=period).sum()
    neg_mf = raw_mf.where(tp_diff < 0, 0.0).rolling(window=period).sum()
    mr = pos_mf / neg_mf.replace(0, np.nan)
    mfi = 100.0 - (100.0 / (1.0 + mr))
    return float(mfi.iloc[-1])


# ============================================================
# CATEGORY 5: SUPPORT / RESISTANCE
# ============================================================


def compute_pivot_points(prev_high: float, prev_low: float, prev_close: float) -> Dict:
    """Compute daily pivot points and support/resistance levels (floor trader method)."""
    # PP = (H+L+C)/3; R1 = 2×PP-L; R2 = PP+(H-L); S1 = 2×PP-H; S2 = PP-(H-L)
    pp = (prev_high + prev_low + prev_close) / 3.0
    return {
        'Pivot_PP': round(pp, 2),
        'Pivot_R1': round(2 * pp - prev_low, 2),
        'Pivot_R2': round(pp + (prev_high - prev_low), 2),
        'Pivot_S1': round(2 * pp - prev_high, 2),
        'Pivot_S2': round(pp - (prev_high - prev_low), 2),
    }


def compute_fibonacci(high: pd.Series, low: pd.Series, lookback: int = 20) -> Dict:
    """Compute Fibonacci retracement levels from recent swing high/low."""
    # Fib = swing_high - ratio × (swing_high - swing_low) at 38.2%, 50.0%, 61.8%
    if len(high) < lookback:
        return {}
    swing_high = float(high.iloc[-lookback:].max())
    swing_low = float(low.iloc[-lookback:].min())
    rng = swing_high - swing_low
    return {
        'Fib_382': round(swing_high - 0.382 * rng, 2),
        'Fib_500': round(swing_high - 0.500 * rng, 2),
        'Fib_618': round(swing_high - 0.618 * rng, 2),
    }


def compute_prev_day_levels(high: pd.Series, low: pd.Series, close: pd.Series):
    """Previous session high, low, close — simplest S/R levels."""
    if len(close) < 2:
        return None, None, None
    return float(high.iloc[-2]), float(low.iloc[-2]), float(close.iloc[-2])


# ============================================================
# CATEGORY 6: CANDLESTICK PATTERNS
# ============================================================


def compute_candle_body_ratio(o, h, l, c) -> float:
    """Compute ratio of candle body to total range (0=doji, 1=marubozu)."""
    rng = h - l
    if rng == 0:
        return 0.0
    return float(abs(c - o) / rng)


def compute_wick_ratios(o, h, l, c) -> tuple:
    """Compute upper and lower wick ratios."""
    # Long lower wick = potential reversal up; long upper wick = potential reversal down
    rng = h - l
    if rng == 0:
        return 0.0, 0.0
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    return float(upper_wick / rng), float(lower_wick / rng)


def compute_consecutive_direction(close: pd.Series) -> tuple:
    """Count consecutive bullish and bearish candles."""
    if len(close) < 2:
        return 0, 0
    diff = close.diff()

    green_count = 0
    for v in diff.iloc[::-1]:
        if v > 0:
            green_count += 1
        else:
            break

    red_count = 0
    for v in diff.iloc[::-1]:
        if v < 0:
            red_count += 1
        else:
            break

    return green_count, red_count


# ============================================================
# MAIN: COMPUTE ALL INDICATORS
# ============================================================

def compute_all_indicators(df: pd.DataFrame) -> Dict[str, Optional[float]]:
    """Compute all 40+ technical indicators from OHLCV DataFrame."""
    # Ensure lowercase column names
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    required = {'open', 'high', 'low', 'close', 'volume'}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"DataFrame missing required columns. Need {required}")

    open_ = df['open']
    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume']

    # Ensure enough data for all indicators (R2)
    if len(df) < 60:
        # Not enough bars for reliable indicators, return all None
        return {}

    result: Dict[str, Optional[float]] = {}

    # ── Trend ──────────────────────────────────────────────
    result['MA5'] = compute_ma(close, 5)
    result['MA10'] = compute_ma(close, 10)
    result['MA20'] = compute_ma(close, 20)
    result['MA50'] = compute_ma(close, 50)
    result['MA200'] = compute_ma(close, 200)
    result['MA20_slope'] = compute_ma_slope(close, 20, 5)

    adx, plus_di, minus_di = compute_adx(high, low, close, 14)
    result['ADX_14'] = adx
    result['DI_plus'] = plus_di
    result['DI_minus'] = minus_di

    sar_result = compute_parabolic_sar(high, low, close)
    if sar_result:
        result['Parabolic_SAR'] = sar_result[0]
    else:
        result['Parabolic_SAR'] = None

    # ── Momentum ───────────────────────────────────────────
    result['RSI_14'] = compute_rsi(close, 14)
    macd_line, macd_signal, macd_hist = compute_macd(close, 12, 26, 9)
    result['MACD_line'] = macd_line
    result['MACD_signal'] = macd_signal
    result['MACD_histogram'] = macd_hist

    stoch_k, stoch_d = compute_stochastic(high, low, close, 14, 3)
    result['Stoch_K'] = stoch_k
    result['Stoch_D'] = stoch_d
    result['Williams_R'] = compute_williams_r(high, low, close, 14)
    result['CCI_20'] = compute_cci(high, low, close, 20)

    # ── Volatility ─────────────────────────────────────────
    bb_upper, bb_mid, bb_lower, bb_width = compute_bollinger_bands(close, 20, 2.0)
    result['BB_upper'] = bb_upper
    result['BB_middle'] = bb_mid
    result['BB_lower'] = bb_lower
    result['BB_width'] = bb_width

    result['ATR_14'] = compute_atr(high, low, close, 14)

    kc_upper, kc_mid, kc_lower = compute_keltner_channels(high, low, close, 20, 2.0)
    result['Keltner_upper'] = kc_upper
    result['Keltner_middle'] = kc_mid
    result['Keltner_lower'] = kc_lower

    # ── Volume ─────────────────────────────────────────────
    result['Volume_SMA_20'] = compute_volume_sma(volume, 20)
    result['Volume_ratio'] = compute_volume_ratio(volume, 20)
    result['OBV'] = compute_obv(close, volume)
    result['VWAP'] = compute_vwap(high, low, close, volume)
    result['MFI_14'] = compute_mfi(high, low, close, volume, 14)

    # ── Support / Resistance ───────────────────────────────
    if len(close) >= 2:
        prev_h, prev_l, prev_c = compute_prev_day_levels(high, low, close)
        result['Prev_day_high'] = prev_h
        result['Prev_day_low'] = prev_l
        result['Prev_day_close'] = prev_c

        pivots = compute_pivot_points(prev_h or 0, prev_l or 0, prev_c or 0)
        result.update(pivots)
    else:
        for key in ['Prev_day_high', 'Prev_day_low', 'Prev_day_close',
                     'Pivot_PP', 'Pivot_R1', 'Pivot_R2', 'Pivot_S1', 'Pivot_S2']:
            result[key] = None

    fibs = compute_fibonacci(high, low, 20)
    result['Fib_382'] = fibs.get('Fib_382')
    result['Fib_500'] = fibs.get('Fib_500')
    result['Fib_618'] = fibs.get('Fib_618')

    # ── Candlestick (latest bar) ──────────────────────────
    last_open = float(open_.iloc[-1])
    last_high = float(high.iloc[-1])
    last_low = float(low.iloc[-1])
    last_close = float(close.iloc[-1])

    result['Candle_body_ratio'] = compute_candle_body_ratio(last_open, last_high, last_low, last_close)
    upper_w, lower_w = compute_wick_ratios(last_open, last_high, last_low, last_close)
    result['Upper_wick_ratio'] = upper_w
    result['Lower_wick_ratio'] = lower_w

    green_n, red_n = compute_consecutive_direction(close)
    result['Consecutive_green'] = green_n
    result['Consecutive_red'] = red_n

    # Round all floats to 4 decimal places for cleanliness
    for k, v in result.items():
        if v is not None and isinstance(v, float):
            result[k] = round(v, 4)

    return result


# ============================================================
# COMPUTATION TIERS — Efficiency Optimization
# ============================================================
# Not all indicators need to be recomputed every 2 minutes.
# Session-static indicators change imperceptibly intraday (daily bars).
# Only ~10 indicators need per-cycle recomputation in M3.

# ── Tier 1: SESSION-STATIC ─────────────────────────────────
# Compute ONCE at M1 start from daily bars. ~30 indicators.
# These indicators use DAILY OHLCV and barely change intraday.
TIER_1_NAMES = [
    # Trend (long-period)
    'MA20', 'MA50', 'MA200', 'MA20_slope',
    'ADX_14', 'DI_plus', 'DI_minus', 'Parabolic_SAR',
    # Momentum (daily scale)
    'MACD_line', 'MACD_signal', 'MACD_histogram',
    'CCI_20', 'Williams_R',
    # Volatility (daily scale)
    'BB_upper', 'BB_middle', 'BB_lower', 'BB_width',
    'ATR_14', 'Keltner_upper', 'Keltner_middle', 'Keltner_lower',
    # Volume (daily scale)
    'Volume_SMA_20', 'OBV', 'MFI_14',
    # S/R (from previous day — static all session)
    'Pivot_PP', 'Pivot_R1', 'Pivot_R2', 'Pivot_S1', 'Pivot_S2',
    'Fib_382', 'Fib_500', 'Fib_618',
    'Prev_day_high', 'Prev_day_low', 'Prev_day_close',
]

# ── Tier 2: 5-MINUTE CACHE ────────────────────────────────
# Recompute every 5 minutes from intraday bars. ~7 indicators.
# These use recent intraday bars and change moderately fast.
TIER_2_NAMES = [
    # Short MAs (respond faster)
    'MA5', 'MA10',
    # Momentum (14-period on 1-2min bars — changes gradually)
    'RSI_14', 'Stoch_K', 'Stoch_D',
    # Volume (needs accumulating intraday data)
    'Volume_ratio',
]

# ── Tier 3: EVERY 2 MINUTES (M3 real-time) ────────────────
# Recompute every M3 monitoring cycle. ~10 indicators.
# These reflect the latest few bars and change rapidly.
TIER_3_NAMES = [
    # Price structure (latest bar only)
    'Candle_body_ratio', 'Upper_wick_ratio', 'Lower_wick_ratio',
    'Consecutive_green', 'Consecutive_red',
    # Intraday volume-weighted (changes every bar)
    'VWAP',
    # Short MAs (optional — included in Tier 2 if 5-min cache)
    'MA5', 'MA10',
]

# Overlap note: MA5, MA10, Volume_ratio appear in both Tier 2 and Tier 3.
# Tier 2 computes them every 5 min; Tier 3 refreshes them every 2 min for
# the most time-sensitive use cases. De-dup in merge.


def compute_tier1(df_daily: pd.DataFrame) -> Dict[str, Optional[float]]:
    """Compute session-static indicators from daily bars (call once at session start)."""
    # Compute all from daily bars
    full = compute_all_indicators(df_daily)
    return {k: full[k] for k in TIER_1_NAMES if k in full}


def compute_tier2(df_intraday: pd.DataFrame) -> Dict[str, Optional[float]]:
    """Compute 5-minute cache indicators from intraday bars."""
    result = {}
    o, h, l, c, v = (df_intraday['open'], df_intraday['high'],
                      df_intraday['low'], df_intraday['close'],
                      df_intraday['volume'])

    result['MA5'] = compute_ma(c, min(5, len(c)))
    result['MA10'] = compute_ma(c, min(10, len(c)))
    result['RSI_14'] = compute_rsi(c, 14)
    result['Stoch_K'], result['Stoch_D'] = compute_stochastic(h, l, c, 14, 3)
    result['Volume_ratio'] = compute_volume_ratio(v, min(20, len(v)))

    for k, v in result.items():
        if v is not None and isinstance(v, float):
            result[k] = round(v, 4)
    return result


def compute_tier3(df_intraday: pd.DataFrame) -> Dict[str, Optional[float]]:
    """Compute per-cycle indicators from latest intraday bars."""
    result = {}
    if len(df_intraday) < 1:
        return result

    latest = df_intraday.iloc[-1]
    o, h, l, c = (float(latest['open']), float(latest['high']),
                   float(latest['low']), float(latest['close']))

    # Candle structure — latest bar only (O(1))
    result['Candle_body_ratio'] = compute_candle_body_ratio(o, h, l, c)
    uw, lw = compute_wick_ratios(o, h, l, c)
    result['Upper_wick_ratio'] = uw
    result['Lower_wick_ratio'] = lw

    # Consecutive direction — scan backwards until reversal (O(k), k = streak length)
    green_n, red_n = compute_consecutive_direction(df_intraday['close'])
    result['Consecutive_green'] = green_n
    result['Consecutive_red'] = red_n

    # VWAP — cumulative intraday (O(n) but n=current session bars, ~50-200)
    if 'volume' in df_intraday.columns and df_intraday['volume'].sum() > 0:
        result['VWAP'] = compute_vwap(df_intraday['high'], df_intraday['low'],
                                       df_intraday['close'], df_intraday['volume'])
    else:
        result['VWAP'] = None

    # Short MAs from intraday
    c = df_intraday['close']
    result['MA5'] = compute_ma(c, min(5, len(c)))
    result['MA10'] = compute_ma(c, min(10, len(c)))

    for k, v in result.items():
        if v is not None and isinstance(v, float):
            result[k] = round(v, 4)
    return result


def merge_tiers(tier1: Dict, tier2: Dict, tier3: Dict) -> Dict[str, Optional[float]]:
    """Merge tier dicts with later tiers overriding earlier ones."""
    merged = {}
    merged.update(tier1)   # Base: session-static
    merged.update(tier2)   # Overlay: 5-min refresh
    merged.update(tier3)   # Overlay: 2-min latest
    return merged


# ============================================================
# PIPELINE: Full session indicator flow
# ============================================================
#
# M1 START (once):
#   df_daily = fetcher.get_ohlcv(ticker, period='6mo', interval='1d')
#   tier1 = compute_tier1(df_daily)
#   → Insert into technical_indicators table
#   → These 30 indicators are valid ALL SESSION
#
# M2 OPENING / M3 MONITORING (every 5 min):
#   df_intraday = fetcher.get_ohlcv(ticker, period='1d', interval='2m')
#   tier2 = compute_tier2(df_intraday)
#   → Update the 7 Tier-2 indicators in the table
#
# M3 EVERY 2 MINUTES:
#   tier3 = compute_tier3(df_intraday)   # reuse same df, just latest bar
#   → Update the 10 Tier-3 indicators in the table
#   → Cost: ~2ms per ticker per cycle
#
# FULL REFRESH (for M4 execution or M5 review):
#   full = merge_tiers(tier1, tier2, tier3)
#   → All 47 indicators fresh


# ============================================================
# FORMATTER: Convert result dict to technical_indicators table rows
# ============================================================

def to_table_rows(ticker: str, indicators: Dict[str, Optional[float]],
                  timestamp: str) -> list:
    """Convert indicator dict to a list of table row dicts with derived signals."""
    rows = []
    for name, value in indicators.items():
        if value is None:
            continue  # Don't insert indicators that couldn't be computed

        signal = _derive_signal(name, value)
        rows.append({
            'ticker': ticker,
            'indicator_name': name,
            'value': value,
            'signal': signal,
            'timestamp': timestamp,
        })
    return rows


def _derive_signal(name: str, value: float) -> str:
    """Derive BULLISH/BEARISH/NEUTRAL signal from indicator value."""
    bullish_set = {
        'MA5', 'MA10', 'MA20', 'MA50', 'MA200',  # vs price — handled externally
    }
    # Indicators where higher = bullish
    higher_bullish = {
        'DI_plus', 'OBV', 'Volume_ratio', 'Candle_body_ratio',
        'Consecutive_green',
    }
    # Indicators where lower = bullish
    lower_bullish = {
        'DI_minus', 'Consecutive_red',
    }

    # Trend indicators
    if name == 'ADX_14':
        return 'BULLISH' if value > 25 else 'NEUTRAL'
    if name == 'MA20_slope':
        return 'BULLISH' if value > 0 else 'BEARISH'
    if name == 'Parabolic_SAR':
        return 'NEUTRAL'  # SAR is a level, not a signal

    # Momentum
    if name == 'RSI_14':
        return 'BEARISH' if value > 70 else ('BULLISH' if value < 30 else 'NEUTRAL')
    if name == 'MACD_line' or name == 'MACD_histogram':
        return 'BULLISH' if value > 0 else 'BEARISH'
    if name == 'MACD_signal':
        return 'NEUTRAL'  # signal line alone is neutral
    if name == 'Stoch_K' or name == 'Stoch_D':
        return 'BULLISH' if value < 20 else ('BEARISH' if value > 80 else 'NEUTRAL')
    if name == 'Williams_R':
        return 'BULLISH' if value < -80 else ('BEARISH' if value > -20 else 'NEUTRAL')
    if name == 'CCI_20':
        return 'BULLISH' if value < -100 else ('BEARISH' if value > 100 else 'NEUTRAL')

    # Volatility — all neutral as they're context, not direction
    if name.startswith('BB_') or name.startswith('Keltner_') or name == 'ATR_14':
        return 'NEUTRAL'

    # Volume
    if name == 'VWAP':
        return 'NEUTRAL'  # vs price comparison is external
    if name == 'MFI_14':
        return 'BULLISH' if value < 20 else ('BEARISH' if value > 80 else 'NEUTRAL')
    if name == 'Volume_SMA_20':
        return 'NEUTRAL'
    if name == 'Volume_ratio':
        return 'BULLISH' if value > 1.5 else 'NEUTRAL'

    # S/R — neutral (context, not direction)
    if name.startswith('Pivot_') or name.startswith('Fib_') or name.startswith('Prev_day_'):
        return 'NEUTRAL'

    # Candlestick
    if name == 'Upper_wick_ratio':
        return 'BEARISH' if value > 0.6 else 'NEUTRAL'
    if name == 'Lower_wick_ratio':
        return 'BULLISH' if value > 0.6 else 'NEUTRAL'

    if name in higher_bullish:
        return 'BULLISH' if value > 0 else 'NEUTRAL'
    if name in lower_bullish:
        return 'BULLISH' if value < 0 else ('BEARISH' if value > 0 else 'NEUTRAL')

    return 'NEUTRAL'
