"""Decoupled Tactic Simulator.

Contains K-line data loaders, Eastern Time normalizers, and strategy rules
such as VWAP reclaim entries and ATR/HWM stop-loss simulations.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import pandas as pd

# Standard normalization helper
def _normalize_bar(bar: dict[str, Any]) -> dict[str, Any]:
    return {
        **bar,
        "open": float(bar["open"]),
        "high": float(bar["high"]),
        "low": float(bar["low"]),
        "close": float(bar["close"]),
        "volume": float(bar["volume"]),
        "time": bar.get("time") or bar["timestamp"][11:16],
    }


def _learning_dir() -> Path:
    learning_dir = Path("D:/gemini/lianghua/stock_team/learning")
    if not learning_dir.exists():
        learning_dir = Path.cwd() / "learning"
    return learning_dir


def build_local_cache_context(date_range: dict[str, str]) -> dict[str, Any]:
    learning_dir = _learning_dir()
    context: dict[str, Any] = {
        "learning_dir": learning_dir,
        "market_regimes": {},
        "benchmark_returns": {},
    }

    qqq_intra_path = learning_dir / "intraday_cache_QQQ.csv"
    if qqq_intra_path.exists():
        try:
            df_bench = pd.read_csv(qqq_intra_path)
            start_date = date_range.get("start")
            end_date = date_range.get("end")
            df_bench["dt"] = pd.to_datetime(df_bench["Datetime"], utc=True)
            df_bench["dt_et"] = df_bench["dt"].dt.tz_convert("America/New_York")
            df_bench["DateStr"] = df_bench["dt_et"].dt.strftime("%Y-%m-%d")
            if start_date:
                df_bench = df_bench[df_bench["DateStr"] >= start_date]
            if end_date:
                df_bench = df_bench[df_bench["DateStr"] <= end_date]
            df_bench["TimestampStr"] = df_bench["dt_et"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            df_bench = df_bench[(df_bench["TimeStr"] >= "09:30") & (df_bench["TimeStr"] <= "16:00")]
            df_bench["bench_ret"] = df_bench.groupby("DateStr")["Close"].pct_change(12)
            context["benchmark_returns"] = df_bench.set_index("TimestampStr")["bench_ret"].to_dict()
        except Exception:
            context["benchmark_returns"] = {}

    qqq_path = learning_dir / "daily_cache_QQQ.csv"
    vix_path = learning_dir / "daily_cache_^VIX.csv"
    spy_path = learning_dir / "daily_cache_SPY.csv"
    regimes = {}
    if qqq_path.exists() and vix_path.exists():
        df_qqq = pd.read_csv(qqq_path)
        df_vix = pd.read_csv(vix_path)
        df_spy = pd.read_csv(spy_path) if spy_path.exists() else pd.DataFrame()

        df_qqq["DateStr"] = pd.to_datetime(df_qqq["Date"], utc=True).dt.strftime("%Y-%m-%d")
        df_vix["DateStr"] = pd.to_datetime(df_vix["Date"], utc=True).dt.strftime("%Y-%m-%d")
        df_qqq["ma20"] = df_qqq["Close"].rolling(20).mean()

        if not df_spy.empty:
            df_spy["DateStr"] = pd.to_datetime(df_spy["Date"], utc=True).dt.strftime("%Y-%m-%d")
            df_spy["vol_ma20"] = df_spy["Volume"].rolling(20).mean()
            df_spy = df_spy.set_index("DateStr")

        df_qqq = df_qqq.set_index("DateStr")
        df_vix = df_vix.set_index("DateStr")

        for dt in df_qqq.index:
            if dt in df_vix.index:
                q_close = df_qqq.loc[dt, "Close"]
                q_ma20 = df_qqq.loc[dt, "ma20"]
                v_close = df_vix.loc[dt, "Close"]

                s_vol = 1.0
                s_vol_ma = 1.0
                if not df_spy.empty and dt in df_spy.index:
                    s_vol = df_spy.loc[dt, "Volume"]
                    s_vol_ma = df_spy.loc[dt, "vol_ma20"]

                if q_close < q_ma20 and v_close >= 25 and s_vol > 1.3 * s_vol_ma:
                    regime = "high_volume_risk_off"
                elif q_close < q_ma20 and v_close >= 20:
                    regime = "qqq_downtrend_vix_rising"
                elif abs(q_close - q_ma20) / (q_ma20 or 1.0) <= 0.015 and v_close < 20:
                    regime = "qqq_flat_low_vix"
                else:
                    regime = "qqq_uptrend_low_vix"
                regimes[dt] = regime
    context["market_regimes"] = regimes
    return context


def _with_intraday_features(
    bars: list[dict[str, Any]],
    benchmark_returns: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    if not bars:
        return []
    df = pd.DataFrame(bars)

    # DateStr and TimeStr (if not present)
    df["DateStr"] = df["timestamp"].str[:10]
    df["TimeStr"] = df["timestamp"].str[11:16]
    
    # VWAP and volume ratio reset by regular-session date.
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_pv = (typical * df["volume"]).groupby(df["DateStr"]).cumsum()
    cum_vol = df["volume"].groupby(df["DateStr"]).cumsum()
    df["vwap"] = cum_pv / cum_vol.replace(0, 1)
    
    rolling_vol_20 = df.groupby("DateStr")["volume"].transform(
        lambda s: s.shift(1).rolling(20, min_periods=1).mean()
    )
    df["volume_ratio"] = df["volume"] / rolling_vol_20
    df["volume_ratio"] = df["volume_ratio"].fillna(1.0)
    
    # EMA20, SMA50, SMA20, STD20, Bollinger Bands
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["sma20"] = df["close"].rolling(20, min_periods=1).mean()
    df["sma50"] = df["close"].rolling(50, min_periods=1).mean()
    df["std20"] = df["close"].rolling(20, min_periods=1).std()
    df["bollinger_upper"] = df["sma20"] + 2 * df["std20"].fillna(0.0)
    
    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd_line"] = ema12 - ema26
    df["signal_line"] = df["macd_line"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["signal_line"]
    
    # RSI14
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    df["rsi"] = 100 - (100 / (1 + rs))
    
    # Fill NAs
    for col in ["ema20", "sma20", "sma50", "bollinger_upper", "macd_line", "signal_line", "macd_hist", "rsi"]:
        df[col] = df[col].fillna(df["close"])
        
    # ORB30 / ORB60 Highs
    orb30_mask = (df["TimeStr"] >= "09:30") & (df["TimeStr"] <= "10:00")
    orb30_highs = df[orb30_mask].groupby("DateStr")["high"].max().to_dict()
    df["orb30_high"] = df["DateStr"].map(orb30_highs)
    
    orb60_mask = (df["TimeStr"] >= "09:30") & (df["TimeStr"] <= "10:30")
    orb60_highs = df[orb60_mask].groupby("DateStr")["high"].max().to_dict()
    df["orb60_high"] = df["DateStr"].map(orb60_highs)
    
    df["orb30_high"] = df["orb30_high"].fillna(df["high"])
    df["orb60_high"] = df["orb60_high"].fillna(df["high"])
    
    # Benchmark Relative Strength
    if benchmark_returns is not None:
        df["bench_ret"] = df["timestamp"].map(benchmark_returns)
    else:
        context = build_local_cache_context({"start": df["DateStr"].min(), "end": df["DateStr"].max()})
        df["bench_ret"] = df["timestamp"].map(context.get("benchmark_returns", {}))

    M = 12
    df["stock_ret"] = df.groupby("DateStr")["close"].pct_change(M)
    df["rs_diff"] = (df["stock_ret"] - df["bench_ret"].fillna(0.0)) * 100.0
    df["rs_diff"] = df["rs_diff"].fillna(0.0)
    
    return df.to_dict(orient="records")


def _compute_daily_atr14(daily_df: pd.DataFrame) -> pd.Series:
    high = daily_df["High"]
    low = daily_df["Low"]
    close = daily_df["Close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    atr = atr.fillna(close * 0.02)
    return atr


def compute_dynamic_slippage(close: float, atr14: float, gap_pct: float, leverage: int = 1) -> float:
    base_friction = 0.0002  # 0.02%
    vol_ratio = (atr14 / close) if (close > 0 and atr14 > 0) else 0.02
    vol_penalty = vol_ratio * 0.03
    gap_penalty = abs(gap_pct) * 0.03 if gap_pct > 0 else 0.0
    total_slip = (base_friction + vol_penalty + gap_penalty) * leverage
    return min(max(total_slip, 0.0002), 0.0035)


def compute_leverage_decay(leverage: int, hold_days: float) -> float:
    if leverage <= 1:
        return 0.0
    daily_decay = 0.0003 if leverage == 2 else 0.0008 if leverage == 3 else 0.0004 * (leverage - 1)
    return daily_decay * hold_days


def _load_local_data_for_symbol(
    symbol: str,
    date_range: dict[str, str],
    cache_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    learning_dir = (cache_context or {}).get("learning_dir") or _learning_dir()
        
    intraday_path = learning_dir / f"intraday_cache_{symbol}.csv"
    daily_path = learning_dir / f"daily_cache_{symbol}.csv"
    
    if not intraday_path.exists():
        return [], {}
        
    df_intra = pd.read_csv(intraday_path)
    
    # Timezone-aware Eastern Time normalization
    df_intra["dt"] = pd.to_datetime(df_intra["Datetime"], utc=True)
    df_intra["dt_et"] = df_intra["dt"].dt.tz_convert("America/New_York")
    df_intra["DateStr"] = df_intra["dt_et"].dt.strftime("%Y-%m-%d")
    df_intra["TimeStr"] = df_intra["dt_et"].dt.strftime("%H:%M")
    df_intra["TimestampStr"] = df_intra["dt_et"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    
    start_date = date_range.get("start")
    end_date = date_range.get("end")
    if start_date:
        df_intra = df_intra[df_intra["DateStr"] >= start_date]
    if end_date:
        df_intra = df_intra[df_intra["DateStr"] <= end_date]
    df_intra = df_intra[(df_intra["TimeStr"] >= "09:30") & (df_intra["TimeStr"] <= "16:00")]
        
    if df_intra.empty:
        return [], {}
        
    bars_frame = pd.DataFrame({
        "timestamp": df_intra["TimestampStr"],
        "open": df_intra["Open"].astype(float),
        "high": df_intra["High"].astype(float),
        "low": df_intra["Low"].astype(float),
        "close": df_intra["Close"].astype(float),
        "volume": df_intra["Volume"].astype(float),
        "time": df_intra["TimeStr"],
        "market_regime": "unknown",
        "sector_regime": "unknown",
    })
    bars = bars_frame.to_dict(orient="records")
        
    daily_metrics = {}
    if daily_path.exists():
        df_daily = pd.read_csv(daily_path)
        df_daily["DateStr"] = df_daily["Date"].astype(str)
        atr = _compute_daily_atr14(df_daily)
        df_daily["atr"] = atr
        df_daily["gap_pct"] = (df_daily["Open"] - df_daily["Close"].shift(1)) / df_daily["Close"].shift(1)
        df_daily["gap_pct"] = df_daily["gap_pct"].fillna(0.0)
        
        for _, row in df_daily.iterrows():
            daily_metrics[row["DateStr"]] = {
                "atr": float(row["atr"]),
                "gap_pct": float(row["gap_pct"])
            }
            
    regimes = (cache_context or {}).get("market_regimes")
    if regimes is None:
        regimes = build_local_cache_context(date_range).get("market_regimes", {})
                
    for bar in bars:
        dt = bar["timestamp"][:10]
        if dt in regimes:
            bar["market_regime"] = regimes[dt]
            
    return bars, daily_metrics


def _check_entry_trigger(prev: dict[str, Any], bar: dict[str, Any], entry_model: dict[str, Any], hyperparameters: dict[str, Any]) -> bool:
    t_type = entry_model.get("type")
    
    if t_type == "channel_reclaim":
        ind = entry_model.get("indicator", "vwap")
        if ind not in bar or ind not in prev:
            return False
        return prev["close"] < prev[ind] and bar["close"] > bar[ind]
        
    elif t_type == "channel_breakout":
        ind = entry_model.get("indicator")
        if not ind or ind not in bar or ind not in prev:
            return False
        return prev["close"] <= prev[ind] and bar["close"] > bar[ind]
        
    elif t_type == "mean_reversion":
        ind = entry_model.get("indicator", "sma20")
        ma_col = ind if ind in bar else "sma20"
        if ma_col not in bar:
            return False
        deviation_pct = float(hyperparameters.get("deviation_pct", 2.0))
        return bar["close"] <= bar[ma_col] * (1.0 - deviation_pct / 100.0)
        
    elif t_type == "trend_pullback":
        ind = entry_model.get("indicator", "ema20")
        if ind not in bar or ind not in prev:
            return False
        ma_rising = bar[ind] > prev[ind]
        touch_ma = bar["low"] <= bar[ind]
        close_above_ma = bar["close"] > bar[ind]
        reversal = bar["close"] > prev["close"]
        return ma_rising and touch_ma and close_above_ma and reversal
        
    return False


def _check_entry_filters(prev: dict[str, Any], bar: dict[str, Any], filters: list[dict[str, Any]], hyperparameters: dict[str, Any]) -> bool:
    for f in filters:
        f_type = f.get("type")
        if f_type == "relative_volume":
            min_vol_ratio = float(f.get("min_volume_ratio", hyperparameters.get("min_volume_ratio", 1.2)))
            ratio = bar.get("volume_ratio")
            if ratio is None or ratio < min_vol_ratio:
                return False
                
        elif f_type == "relative_strength":
            min_rs_diff = float(f.get("min_rs_diff", hyperparameters.get("min_rs_diff", 1.5)))
            rs_val = bar.get("rs_diff")
            if rs_val is None or rs_val < min_rs_diff:
                return False
                
        elif f_type == "macd":
            sig = f.get("signal", "bullish_crossover")
            if sig == "bullish_crossover":
                macd_line = bar.get("macd_line")
                sig_line = bar.get("signal_line")
                if macd_line is None or sig_line is None or macd_line <= sig_line:
                    return False
            elif sig == "histogram_rising":
                cur_hist = bar.get("macd_hist")
                prev_hist = prev.get("macd_hist")
                if cur_hist is None or prev_hist is None or cur_hist <= prev_hist:
                    return False
                    
        elif f_type == "rsi":
            min_val = float(f.get("min_value", 30))
            max_val = float(f.get("max_value", 70))
            rsi_val = bar.get("rsi")
            if rsi_val is None or rsi_val < min_val or rsi_val > max_val:
                return False
                
    return True


def _simulate_trade_exit_modular(
    symbol: str,
    entry_bar: dict[str, Any],
    future_bars: list[dict[str, Any]],
    strategy: dict[str, Any],
    hyperparameters: dict[str, Any],
    daily_metrics: dict[str, dict[str, Any]] = None,
    entry_sequence_idx: int = 0
) -> tuple[dict[str, Any], int]:
    entry_price = entry_bar["close"]
    entry_date = entry_bar["timestamp"][:10]
    
    # Fetch daily ATR
    atr = entry_price * 0.02
    if daily_metrics and entry_date in daily_metrics:
        atr = daily_metrics[entry_date].get("atr", atr)
        
    exit_model = strategy.get("exit_model", {})
    exit_type = exit_model.get("type", "fixed_pct")
    
    stop_loss_pct = float(hyperparameters.get("stop_loss_pct", 1.5))
    take_profit_pct = float(hyperparameters.get("take_profit_pct", 3.0))
    sl_atr_multiplier = float(hyperparameters.get("sl_atr_multiplier", 1.5))
    tp_atr_multiplier = float(hyperparameters.get("tp_atr_multiplier", 2.5))
    tp1_multiplier = float(hyperparameters.get("tp1_multiplier", 1.5))
    tp2_multiplier = float(hyperparameters.get("tp2_multiplier", 3.0))
    leverage = int(hyperparameters.get("leverage", 1))
    
    if exit_type == "fixed_pct":
        sl_price = entry_price * (1.0 - stop_loss_pct / 100.0)
        tp_price = entry_price * (1.0 + take_profit_pct / 100.0)
    elif exit_type in ("atr_static", "atr_trailing_stop"):
        sl_price = entry_price - sl_atr_multiplier * atr
        tp_price = entry_price + tp_atr_multiplier * atr
    elif exit_type == "partial_scaling":
        sl_price = entry_price - sl_atr_multiplier * atr
        tp1_price = entry_price + tp1_multiplier * atr
        tp2_price = entry_price + tp2_multiplier * atr
    elif exit_type == "time_exit":
        sl_price = entry_price - sl_atr_multiplier * atr
        tp_price = entry_price + tp_atr_multiplier * atr
        
    highest_close = entry_price
    highest_high = entry_bar["high"]
    
    exit_bar = entry_bar
    exit_price = entry_price
    exit_reason = "end_of_day"
    exit_idx = entry_sequence_idx
    
    lows = [entry_bar["low"]]
    highs = [entry_bar["high"]]
    
    tp1_hit = False
    tp1_bar = None
    tp1_exit_price = None
    tp1_exit_idx = None
    
    for idx_offset, bar in enumerate(future_bars):
        current_idx = entry_sequence_idx + 1 + idx_offset
        lows.append(bar["low"])
        highs.append(bar["high"])
        
        highest_close = max(highest_close, bar["close"])
        highest_high = max(highest_high, bar["high"])
        
        # 1. Time Exit Check
        max_hold_bars = int(hyperparameters.get("max_hold_bars", 24))
        if exit_type == "time_exit" and len(lows) >= max_hold_bars:
            exit_bar = bar
            exit_price = bar["close"]
            exit_reason = "time_exit"
            exit_idx = current_idx
            break
            
        # 2. Stop Loss Check
        if exit_type == "atr_trailing_stop":
            cur_stop = max(sl_price, highest_close - sl_atr_multiplier * atr)
        elif exit_type == "partial_scaling":
            if tp1_hit:
                cur_stop = entry_price
            else:
                cur_stop = sl_price
        else:
            cur_stop = sl_price
            
        if bar["low"] <= cur_stop:
            exit_bar = bar
            exit_price = cur_stop
            exit_reason = "stop_loss"
            exit_idx = current_idx
            break
            
        # 3. Take Profit Check
        if exit_type == "partial_scaling":
            if not tp1_hit and bar["high"] >= tp1_price:
                tp1_hit = True
                tp1_bar = bar
                tp1_exit_price = tp1_price
                tp1_exit_idx = current_idx
            elif tp1_hit and bar["high"] >= tp2_price:
                exit_bar = bar
                exit_price = tp2_price
                exit_reason = "take_profit"
                exit_idx = current_idx
                break
        else:
            if bar["high"] >= tp_price:
                exit_bar = bar
                exit_price = tp_price
                exit_reason = "take_profit"
                exit_idx = current_idx
                break
                
        # 4. End of Day Check
        is_last_of_day = False
        if bar["time"] >= "15:55":
            is_last_of_day = True
        elif idx_offset + 1 < len(future_bars):
            next_bar = future_bars[idx_offset + 1]
            if next_bar["timestamp"][:10] != bar["timestamp"][:10]:
                is_last_of_day = True
        else:
            is_last_of_day = True
            
        if is_last_of_day:
            exit_bar = bar
            exit_price = bar["close"]
            exit_reason = "end_of_day"
            exit_idx = current_idx
            break
            
    exit_date = exit_bar["timestamp"][:10]
    
    entry_atr = daily_metrics.get(entry_date, {}).get("atr", entry_price * 0.02) if daily_metrics else entry_price * 0.02
    entry_gap = daily_metrics.get(entry_date, {}).get("gap_pct", 0.0) if daily_metrics else 0.0
    exit_atr = daily_metrics.get(exit_date, {}).get("atr", exit_price * 0.02) if daily_metrics else exit_price * 0.02
    exit_gap = daily_metrics.get(exit_date, {}).get("gap_pct", 0.0) if daily_metrics else 0.0
    
    entry_slip = compute_dynamic_slippage(entry_price, entry_atr, entry_gap, leverage)
    exit_slip = compute_dynamic_slippage(exit_price, exit_atr, exit_gap, leverage)
    
    if exit_type == "partial_scaling" and tp1_hit:
        tp1_ret = (tp1_exit_price / entry_price - 1.0)
        final_ret = (exit_price / entry_price - 1.0)
        raw_return = 0.5 * tp1_ret + 0.5 * final_ret
        
        tp1_exit_date = tp1_bar["timestamp"][:10]
        tp1_exit_atr = daily_metrics.get(tp1_exit_date, {}).get("atr", tp1_exit_price * 0.02) if daily_metrics else tp1_exit_price * 0.02
        tp1_exit_gap = daily_metrics.get(tp1_exit_date, {}).get("gap_pct", 0.0) if daily_metrics else 0.0
        tp1_slip = compute_dynamic_slippage(tp1_exit_price, tp1_exit_atr, tp1_exit_gap, leverage)
        
        total_slip = entry_slip + 0.5 * tp1_slip + 0.5 * exit_slip
    else:
        raw_return = (exit_price / entry_price - 1.0)
        total_slip = entry_slip + exit_slip
        
    entry_dt = pd.to_datetime(entry_bar["timestamp"])
    exit_dt = pd.to_datetime(exit_bar["timestamp"])
    hold_days = (exit_dt - entry_dt).total_seconds() / 86400.0
    decay = compute_leverage_decay(leverage, hold_days)
    
    net_return_pct = (raw_return - total_slip - decay) * 100.0
    mae_pct = (min(lows) / entry_price - 1.0) * 100.0
    mfe_pct = (max(highs) / entry_price - 1.0) * 100.0
    
    return {
        "symbol": symbol,
        "entry_time": entry_bar["timestamp"],
        "exit_time": exit_bar["timestamp"],
        "entry_price": entry_price,
        "exit_price": exit_price,
        "return_pct": net_return_pct,
        "mae_pct": mae_pct,
        "mfe_pct": mfe_pct,
        "market_regime": entry_bar.get("market_regime", "unknown"),
        "sector_regime": entry_bar.get("sector_regime", "unknown"),
        "trigger": f"{strategy.get('entry_model', {}).get('type')}_{strategy.get('entry_model', {}).get('indicator', 'vwap')}",
        "exit_reason": exit_reason,
        "entry_vwap": entry_bar.get("vwap"),
        "entry_volume_ratio": entry_bar.get("volume_ratio"),
    }, exit_idx


def _simulate_all_trades(
    symbol: str,
    bars: list[dict[str, Any]],
    params: dict[str, Any],
    daily_metrics: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    strategy = params.get("strategy", {})
    entry_model = strategy.get("entry_model", {})
    filters = strategy.get("filters", [])
    
    action_start = params.get("action_window_start", "10:00")
    action_end = params.get("action_window_end", "11:00")
    
    events = []
    idx = 1
    while idx < len(bars):
        prev = bars[idx - 1]
        bar = bars[idx]
        
        if not (action_start <= bar["time"] <= action_end):
            idx += 1
            continue
            
        triggered = _check_entry_trigger(prev, bar, entry_model, params)
        if not triggered:
            idx += 1
            continue
            
        filters_ok = _check_entry_filters(prev, bar, filters, params)
        if not filters_ok:
            idx += 1
            continue
            
        event, exit_idx = _simulate_trade_exit_modular(
            symbol=symbol,
            entry_bar=bar,
            future_bars=bars[idx + 1:],
            strategy=strategy,
            hyperparameters=params,
            daily_metrics=daily_metrics,
            entry_sequence_idx=idx
        )
        events.append(event)
        idx = exit_idx + 1
    return events


def _first_strategy_event(
    symbol: str,
    bars: list[dict[str, Any]],
    params: dict[str, Any],
) -> dict[str, Any] | None:
    strategy = params.get("strategy", {})
    entry_model = strategy.get("entry_model", {})
    filters = strategy.get("filters", [])
    
    for idx in range(1, len(bars)):
        prev = bars[idx - 1]
        bar = bars[idx]
        
        triggered = _check_entry_trigger(prev, bar, entry_model, params)
        if not triggered:
            continue
            
        filters_ok = _check_entry_filters(prev, bar, filters, params)
        if not filters_ok:
            continue
            
        event, _ = _simulate_trade_exit_modular(
            symbol=symbol,
            entry_bar=bar,
            future_bars=bars[idx + 1:],
            strategy=strategy,
            hyperparameters=params,
            daily_metrics=None,
            entry_sequence_idx=idx
        )
        return event
    return None


def run_simulation_to_events(
    symbol: str,
    mode: str,
    date_range: dict[str, str],
    params: dict[str, Any],
    bars_by_symbol: dict[str, list[dict[str, Any]]] = None,
    cache_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    # Loads and simulates K-line data to generate events
    is_local = (mode == "local_cache") or (not bars_by_symbol or not bars_by_symbol.get(symbol))
    
    if is_local:
        bars, daily_metrics = _load_local_data_for_symbol(symbol, date_range, cache_context=cache_context)
    else:
        bars = [_normalize_bar(b) for b in bars_by_symbol.get(symbol, [])]
        daily_metrics = {}
        
    if not bars:
        return []
        
    benchmark_returns = (cache_context or {}).get("benchmark_returns") if is_local else None
    bars = _with_intraday_features(bars, benchmark_returns=benchmark_returns)
    
    if mode == "intraday_ohlcv_fixture" and not is_local:
        event = _first_strategy_event(symbol, bars, params)
        return [event] if event else []
    else:
        return _simulate_all_trades(symbol, bars, params, daily_metrics)
