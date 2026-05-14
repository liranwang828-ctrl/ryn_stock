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
    """
    Simple Moving Average
    Formula: SMA = sum(close[-period:]) / period
    """
    if len(close) < period:
        return None
    return float(close.rolling(window=period).mean().iloc[-1])


def compute_ema(close: pd.Series, period: int) -> float:
    """
    Exponential Moving Average
    Formula: EMA_t = α × price_t + (1-α) × EMA_{t-1}
             where α = 2 / (period + 1)
    """
    if len(close) < period:
        return None
    return float(close.ewm(span=period, adjust=False).mean().iloc[-1])


def compute_ma_slope(close: pd.Series, period: int = 20, lookback: int = 5) -> float:
    """
    MA slope = rate of change of the MA over `lookback` periods
    Formula: (MA_t - MA_{t-lookback}) / MA_{t-lookback} / lookback
    Positive → uptrend accelerating. Negative → downtrend.
    """
    ma = close.rolling(window=period).mean()
    if len(ma) < period + lookback:
        return None
    return float((ma.iloc[-1] - ma.iloc[-lookback]) / ma.iloc[-lookback] / lookback)


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    """
    Average Directional Index — trend strength (not direction)
    Formula:
        TR  = max(H-L, |H-C_prev|, |L-C_prev|)
        +DM = if H-H_prev > L_prev-L and H-H_prev > 0 → H-H_prev else 0
        -DM = if L_prev-L > H-H_prev and L_prev-L > 0 → L_prev-L else 0
        ATR = Wilder smoothed TR (period)
        +DI = 100 × Wilder(+DM) / ATR
        -DI = 100 × Wilder(-DM) / ATR
        DX  = 100 × |+DI - -DI| / (+DI + -DI)
        ADX = Wilder smoothed DX (period)
    Returns (ADX, +DI, -DI)
    """
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
    """
    Parabolic SAR — trailing stop that flips with trend
    Formula (simplified incremental, intended for bar-by-bar iteration):
        Initial: SAR[0] = lowest low of first N bars (uptrend)
        SAR_t = SAR_{t-1} + AF × (EP_{t-1} - SAR_{t-1})
        EP = extreme point (highest high in uptrend, lowest low in downtrend)
        AF increments by af_step each new EP, capped at af_max
        Flip: when price crosses SAR, reset SAR to prior EP, flip direction
    Implemented via vectorized approximation using Wilder's method.
    """
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
    """
    Relative Strength Index
    Formula:
        avg_gain = Wilder smoothed average of gains over `period`
        avg_loss = Wilder smoothed average of losses over `period`
        RS = avg_gain / avg_loss
        RSI = 100 - 100/(1 + RS)
    """
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
    """
    MACD (Moving Average Convergence Divergence)
    Formula:
        MACD_line = EMA(fast) - EMA(slow)
        MACD_signal = EMA(MACD_line, signal)
        MACD_histogram = MACD_line - MACD_signal
    Returns (MACD_line, signal_line, histogram)
    """
    if len(close) < slow + signal:
        return None, None, None
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - macd_signal
    return float(macd_line.iloc[-1]), float(macd_signal.iloc[-1]), float(histogram.iloc[-1])


def compute_stochastic(high, low, close, k_period: int = 14, d_period: int = 3):
    """
    Stochastic Oscillator
    Formula:
        %K = 100 × (close - lowest_low(k)) / (highest_high(k) - lowest_low(k))
        %D = SMA(%K, d_period)
    Returns (%K, %D)
    """
    if len(close) < k_period:
        return None, None
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    stoch_k = 100.0 * (close - lowest_low) / (highest_high - lowest_low)
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return float(stoch_k.iloc[-1]), float(stoch_d.iloc[-1])


def compute_williams_r(high, low, close, period: int = 14) -> float:
    """
    Williams %R
    Formula:
        %R = -100 × (highest_high(period) - close) / (highest_high(period) - lowest_low(period))
    Oscillates between -100 and 0. > -20 overbought, < -80 oversold.
    """
    if len(close) < period:
        return None
    hh = high.rolling(window=period).max()
    ll = low.rolling(window=period).min()
    wr = -100.0 * (hh - close) / (hh - ll)
    return float(wr.iloc[-1])


def compute_cci(high, low, close, period: int = 20) -> float:
    """
    Commodity Channel Index
    Formula:
        TP = (H + L + C) / 3
        CCI = (TP - SMA(TP, period)) / (0.015 × mean_absolute_deviation(TP, period))
    """
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
    """
    Bollinger Bands
    Formula:
        Middle = SMA(close, period)
        Upper  = Middle + std_mult × std(close, period)
        Lower  = Middle - std_mult × std(close, period)
        Width  = (Upper - Lower) / Middle
    Returns (upper, middle, lower, width)
    """
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
    """
    Average True Range
    Formula:
        TR = max(H-L, |H-C_prev|, |L-C_prev|)
        ATR = Wilder smoothed TR (EWM, alpha=1/period)
    """
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
    """
    Keltner Channels
    Formula:
        Middle = EMA(close, ema_period)
        ATR    = ATR(ema_period)  ← use ATR with same period
        Upper  = Middle + atr_mult × ATR
        Lower  = Middle - atr_mult × ATR
    Returns (upper, middle, lower)
    """
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
    """
    Volume ratio = current volume / 20-period average volume
    > 1.5 = unusually high volume
    """
    if len(volume) < period:
        return None
    avg = volume.rolling(window=period).mean().iloc[-1]
    return float(volume.iloc[-1]) / avg if avg else None


def compute_obv(close: pd.Series, volume: pd.Series) -> float:
    """
    On-Balance Volume
    Formula:
        OBV_t = OBV_{t-1} + volume  if close > close_prev
        OBV_t = OBV_{t-1} - volume  if close < close_prev
        OBV_t = OBV_{t-1}           if close = close_prev
    Returns latest OBV value.
    """
    direction = np.sign(close.diff())
    obv = (direction * volume).cumsum()
    return float(obv.iloc[-1])


def compute_vwap(high, low, close, volume) -> float:
    """
    Volume-Weighted Average Price — intraday
    Formula:
        VWAP = sum(TP × volume) / sum(volume)
        where TP = (H + L + C) / 3
    For intraday: compute from session start.
    For daily analysis: use entire DataFrame range.
    """
    tp = (high + low + close) / 3.0
    total_pv = (tp * volume).sum()
    total_v = volume.sum()
    return float(total_pv / total_v) if total_v != 0 else None


def compute_mfi(high, low, close, volume, period: int = 14) -> float:
    """
    Money Flow Index — volume-weighted RSI
    Formula:
        TP = (H + L + C) / 3
        Raw Money Flow = TP × volume
        Positive MF = sum of Raw MF where TP > TP_prev, over period
        Negative MF = sum of Raw MF where TP < TP_prev, over period
        Money Ratio = Positive MF / Negative MF
        MFI = 100 - 100/(1 + Money Ratio)
    """
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
    """
    Daily Pivot Points (floor trader method)
    Formula:
        PP = (H_prev + L_prev + C_prev) / 3
        R1 = 2 × PP - L_prev
        R2 = PP + (H_prev - L_prev)
        S1 = 2 × PP - H_prev
        S2 = PP - (H_prev - L_prev)
    """
    pp = (prev_high + prev_low + prev_close) / 3.0
    return {
        'Pivot_PP': round(pp, 2),
        'Pivot_R1': round(2 * pp - prev_low, 2),
        'Pivot_R2': round(pp + (prev_high - prev_low), 2),
        'Pivot_S1': round(2 * pp - prev_high, 2),
        'Pivot_S2': round(pp - (prev_high - prev_low), 2),
    }


def compute_fibonacci(high: pd.Series, low: pd.Series, lookback: int = 20) -> Dict:
    """
    Fibonacci retracement levels from most recent swing high/low
    Formula:
        range = swing_high - swing_low
        Fib 38.2% = swing_high - 0.382 × range (uptrend retracement)
        Fib 50.0% = swing_high - 0.500 × range
        Fib 61.8% = swing_high - 0.618 × range
    Uses highest high and lowest low over `lookback` period as swing points.
    """
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
    """
    Candle body ratio = |close - open| / (high - low)
    0 = doji (no body).  1 = marubozu (no wick).
    """
    rng = h - l
    if rng == 0:
        return 0.0
    return float(abs(c - o) / rng)


def compute_wick_ratios(o, h, l, c) -> tuple:
    """
    Upper wick ratio = (high - max(open, close)) / (high - low)
    Lower wick ratio = (min(open, close) - low) / (high - low)
    Long lower wick = potential reversal up.
    Long upper wick = potential reversal down.
    """
    rng = h - l
    if rng == 0:
        return 0.0, 0.0
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    return float(upper_wick / rng), float(lower_wick / rng)


def compute_consecutive_direction(close: pd.Series) -> tuple:
    """
    Count consecutive bullish (close > prev close) and bearish candles.
    Returns (consecutive_green, consecutive_red).
    """
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
    """
    Compute all 40+ technical indicators from OHLCV DataFrame.

    Args:
        df: DataFrame with columns [open, high, low, close, volume],
            indexed by datetime. Must have at least 60 rows for reliable calculation.

    Returns:
        Flat dict of {indicator_name: value_or_None}, ready to insert into
        the technical_indicators table.

        If an indicator cannot be computed (insufficient data), its value is None.
        A7 MUST check for None and say "not available" instead of fabricating.
    """
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
    """
    Session-static indicators. Call ONCE at M1 start.
    Uses DAILY bars — these values are valid all session.

    Cost: ~30 indicators, ~50ms on 200 bars.
    """
    # Compute all from daily bars
    full = compute_all_indicators(df_daily)
    return {k: full[k] for k in TIER_1_NAMES if k in full}


def compute_tier2(df_intraday: pd.DataFrame) -> Dict[str, Optional[float]]:
    """
    5-minute cache indicators. Call every 5 min during M2/M3.
    Uses INTRADAY bars (e.g., 1-min or 2-min intervals).

    Cost: ~7 indicators, ~5ms on 390 bars (full session of 1-min bars).
    """
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
    """
    Every-2-minute indicators. Call every M3 monitoring cycle.
    Only computes indicators that change with the latest bar.

    Cost: ~10 indicators, ~2ms on any number of bars (reads latest only).
    """
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
    """
    Merge all three tiers into a complete indicator dict.
    Tier 3 overrides Tier 2 overrides Tier 1 (fresher data wins).
    Use this to assemble the full technical_indicators table row set.
    """
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
    """
    Convert the flat dict from compute_all_indicators() into a list of
    dicts suitable for inserting into the `technical_indicators` table.

    Each row matches: {ticker, indicator_name, value, signal, timestamp}
    - signal is derived from indicator value using standard thresholds
    - None values are NOT included (A7 can't use missing indicators)
    """
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
