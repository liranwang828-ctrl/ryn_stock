import os
import sys
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# Ensure root of stock_team is in path
BASE = next(p for p in [os.path.abspath(__file__)] + [os.path.dirname(os.path.abspath(__file__))] + [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))] + [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))] if os.path.exists(os.path.join(p, "templates")))
sys.path.insert(0, BASE)

def fetch_data(symbol, start_date="2021-01-01", end_date="2026-06-01"):
    """Fetch daily data with caching safety"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval="1d")
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"[ERROR] Failed to fetch {symbol}: {e}")
        return pd.DataFrame()

def run_backtest():
    print("[BACKTEST] Fetching macro and sector data...")
    # Benchmarks & Sectors
    qqq = fetch_data("QQQ")
    spy = fetch_data("SPY")
    vix = fetch_data("^VIX")
    soxx = fetch_data("SOXX")
    
    # Leveraged comparison
    tqqq = fetch_data("TQQQ")
    soxl = fetch_data("SOXL")
    
    # Target symbols
    targets = {
        "NVDA": {"sector": "SOXX", "leverage": "SOXL"},
        "AMD": {"sector": "SOXX", "leverage": "SOXL"},
        "COHR": {"sector": "SOXX", "leverage": "SOXL"},
        "AAOI": {"sector": "SOXX", "leverage": "SOXL"}
    }
    
    target_dfs = {}
    for sym in targets:
        print(f"[BACKTEST] Fetching target symbol {sym}...")
        target_dfs[sym] = fetch_data(sym)

    # Verify we have enough data
    if qqq.empty or spy.empty or vix.empty:
        print("[ERROR] Critical benchmark data is missing.")
        return

    print("[BACKTEST] Computing technical indicators...")
    # Clean and align data
    common_idx = qqq.index
    
    # QQQ Indicators
    qqq_close = qqq["Close"]
    qqq_ma20 = qqq_close.rolling(20).mean()
    qqq_ma200 = qqq_close.rolling(200).mean()
    
    # VIX Indicators
    vix_close = vix["Close"].reindex(common_idx, method="ffill")
    vix_diff5 = vix_close.diff(5)
    
    # SPY Indicators
    spy_close = spy["Close"]
    spy_vol = spy["Volume"]
    spy_vol_ma20 = spy_vol.rolling(20).mean()
    
    # Sector Indicators (SOXX)
    soxx_close = soxx["Close"].reindex(common_idx, method="ffill")
    soxx_ret5 = soxx_close.pct_change(5)
    
    trades = []
    
    for sym, meta in targets.items():
        df = target_dfs[sym]
        if df.empty:
            continue
        df = df.reindex(common_idx).ffill() # Align to QQQ dates
        
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        
        # Pullback from 20-day high
        high20 = high.rolling(20).max()
        pullback_pct = (high20 - close) / high20
        
        # Target returns
        target_ret5 = close.pct_change(5)
        qqq_ret5 = qqq_close.pct_change(5)
        
        # Relative Strength
        rs5 = (target_ret5 - qqq_ret5) * 100
        
        # ATR14
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean()
        
        # Stabilization / Rebound conditions
        # Rebound trigger: Close > Prev Close AND Low >= Prev Low (reversal)
        prev_close = close.shift(1)
        prev_low = low.shift(1)
        stabilized = (close > prev_close) & (low >= prev_low)
        
        # Sector relative return
        sec_close = soxx_close if meta["sector"] == "SOXX" else qqq_close
        sec_ret5 = sec_close.pct_change(5)
        sector_rs = (sec_ret5 - qqq_ret5) * 100
        
        # Leveraged comparison data
        lev_df = soxl if meta["leverage"] == "SOXL" else tqqq
        lev_df = lev_df.reindex(common_idx).ffill()
        
        n_days = len(df)
        i = 20
        last_exit_idx = -100
        last_trade_was_stop = False
        last_trade_was_tp1 = False
        
        while i < n_days - 15:
            # Check setup criteria
            is_pullback = pullback_pct.iloc[i] >= 0.05
            has_rs = rs5.iloc[i] >= 1.5
            is_stabilized = stabilized.iloc[i]
            
            # Entry condition
            if is_pullback and has_rs and is_stabilized:
                entry_date = df.index[i]
                entry_price = close.iloc[i]
                atr_val = atr14.iloc[i]
                
                if pd.isna(atr_val) or atr_val <= 0:
                    i += 1
                    continue
                
                # Determine entry type (re-entry or first attempt)
                days_since_exit = i - last_exit_idx
                if days_since_exit <= 5:
                    if last_trade_was_stop:
                        entry_type = "re_entry_stop"
                    elif last_trade_was_tp1:
                        entry_type = "re_entry_tp1"
                    else:
                        entry_type = "first_attempt"
                else:
                    entry_type = "first_attempt"
                
                # Determine regimes
                q_close = qqq_close.iloc[i]
                q_ma20 = qqq_ma20.iloc[i]
                v_close = vix_close.iloc[i]
                s_vol = spy_vol.iloc[i]
                s_vol_ma = spy_vol_ma20.iloc[i]
                
                # Market Regime Split
                if q_close < q_ma20 and v_close >= 25 and s_vol > 1.3 * s_vol_ma:
                    regime = "high_volume_risk_off"
                elif q_close < q_ma20 and v_close >= 20:
                    regime = "qqq_downtrend_vix_rising"
                elif abs(q_close - q_ma20) / q_ma20 <= 0.015 and v_close < 20:
                    regime = "qqq_flat_low_vix"
                else:
                    regime = "qqq_uptrend_low_vix"
                
                # VIX Direction (5-day change)
                vix_dir = "rising" if vix_diff5.iloc[i] > 0 else "falling"
                
                # QQQ Direction (5-day return)
                qqq_dir = "up" if qqq_ret5.iloc[i] > 0 else "down"
                
                # Sector confirmation
                sec_rs_val = sector_rs.iloc[i]
                if sec_rs_val > 0.5:
                    sector_state = "outperforming"
                elif sec_rs_val < -0.5:
                    sector_state = "underperforming"
                else:
                    sector_state = "inline"
                
                # Trade Management
                stop_price = entry_price - 1.5 * atr_val
                tp1_price = entry_price + 1.0 * atr_val
                
                # Trailing stop or exit parameters
                trade_pnl = 0
                max_ae = 0
                lowest_price = entry_price
                
                tp1_hit = False
                exit_price = None
                exit_idx = -1
                
                # Leveraged ETF prices at entry and daily tracking
                lev_entry = lev_df["Close"].iloc[i]
                lev_lowest = lev_entry
                lev_exit = None
                
                for j in range(i + 1, min(i + 15, n_days)):
                    day_low = low.iloc[j]
                    day_high = high.iloc[j]
                    day_close = close.iloc[j]
                    
                    # Track lowest price for MAE
                    if day_low < lowest_price:
                        lowest_price = day_low
                        
                    lev_low = lev_df["Low"].iloc[j]
                    if lev_low < lev_lowest:
                        lev_lowest = lev_low
                    
                    # Check stop loss
                    if day_low <= stop_price:
                        exit_price = stop_price
                        exit_idx = j
                        trade_pnl = (stop_price - entry_price) / entry_price
                        lev_exit = lev_df["Close"].iloc[j] # approximate exit
                        break
                    
                    # Check TP1 (50% scale-out)
                    if not tp1_hit and day_high >= tp1_price:
                        tp1_hit = True
                        # Track remaining 50% using entry_price as break-even trailing stop
                        # Or 10-day time exit
                    
                    # Exit remaining position
                    if tp1_hit:
                        # Break-even hit
                        if day_low <= entry_price:
                            exit_price = entry_price
                            exit_idx = j
                            trade_pnl = 0.5 * (tp1_price - entry_price) / entry_price + 0.5 * 0.0
                            lev_exit = lev_df["Close"].iloc[j]
                            break
                        # Time exit after 10 days
                        if j - i >= 10:
                            exit_price = day_close
                            exit_idx = j
                            trade_pnl = 0.5 * (tp1_price - entry_price) / entry_price + 0.5 * (day_close - entry_price) / entry_price
                            lev_exit = lev_df["Close"].iloc[j]
                            break
                    else:
                        # No TP1 hit, time exit after 10 days
                        if j - i >= 10:
                            exit_price = day_close
                            exit_idx = j
                            trade_pnl = (day_close - entry_price) / entry_price
                            lev_exit = lev_df["Close"].iloc[j]
                            break
                
                # If trade did not exit within window (e.g. holiday/missing data), force close
                if exit_idx == -1:
                    exit_idx = min(i + 10, n_days - 1)
                    exit_price = close.iloc[exit_idx]
                    trade_pnl = (exit_price - entry_price) / entry_price
                    lev_exit = lev_df["Close"].iloc[exit_idx]
                
                # Compute MAE
                max_ae = (entry_price - lowest_price) / entry_price
                lev_mae = (lev_entry - lev_lowest) / lev_entry
                
                # Leveraged ETF PnL
                lev_pnl = (lev_exit - lev_entry) / lev_entry
                
                last_exit_idx = exit_idx
                last_trade_was_stop = (not tp1_hit) and (exit_price == stop_price)
                last_trade_was_tp1 = tp1_hit
                
                trades.append({
                    "symbol": sym,
                    "entry_date": entry_date.strftime("%Y-%m-%d"),
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "pnl": trade_pnl,
                    "lev_pnl": lev_pnl,
                    "mae": max_ae,
                    "lev_mae": lev_mae,
                    "regime": regime,
                    "vix_dir": vix_dir,
                    "qqq_dir": qqq_dir,
                    "sector_state": sector_state,
                    "entry_type": entry_type
                })
                
                # Advance pointer to exit day to avoid overlapping trades
                i = exit_idx
            
            i += 1

    if not trades:
        print("[WARNING] No trades triggered under current rules.")
        return

    # Calculate statistics
    df_trades = pd.DataFrame(trades)
    
    total_trades = len(df_trades)
    wins = df_trades[df_trades["pnl"] > 0]
    losses = df_trades[df_trades["pnl"] <= 0]
    
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    avg_win = wins["pnl"].mean() if len(wins) > 0 else 0
    avg_loss = losses["pnl"].mean() if len(losses) > 0 else 0
    
    sum_gains = wins["pnl"].sum()
    sum_losses = losses["pnl"].abs().sum()
    profit_factor = sum_gains / sum_losses if sum_losses > 0 else float("inf")
    
    # Calculate max drawdown of cumulative returns
    cum_returns = np.cumprod(1 + df_trades["pnl"])
    peaks = np.maximum.accumulate(cum_returns)
    drawdowns = (cum_returns - peaks) / peaks
    max_dd = drawdowns.min() if len(drawdowns) > 0 else 0
    
    # Max Adverse Excursion (MAE)
    mean_mae = df_trades["mae"].mean()
    max_mae = df_trades["mae"].max()
    
    # Expectancy by regime
    expectancy_by_regime = df_trades.groupby("regime")["pnl"].mean().to_dict()
    # Expectancy by VIX direction
    expectancy_by_vix_dir = df_trades.groupby("vix_dir")["pnl"].mean().to_dict()
    # Expectancy by QQQ direction
    expectancy_by_qqq_dir = df_trades.groupby("qqq_dir")["pnl"].mean().to_dict()
    # Expectancy by entry type
    expectancy_by_entry_type = df_trades.groupby("entry_type")["pnl"].mean().to_dict()
    # Sector confirmation impact
    expectancy_by_sector = df_trades.groupby("sector_state")["pnl"].mean().to_dict()
    
    # Leveraged vs Underlying comparison
    stock_avg = df_trades["pnl"].mean()
    lev_avg = df_trades["lev_pnl"].mean()
    stock_win_rate = (df_trades["pnl"] > 0).mean()
    lev_win_rate = (df_trades["lev_pnl"] > 0).mean()
    stock_max_mae = df_trades["mae"].max()
    lev_max_mae = df_trades["lev_mae"].max()
    
    # Identify recommended disable conditions
    disable_conditions = []
    if expectancy_by_regime.get("high_volume_risk_off", 0) < 0:
        disable_conditions.append("QQQ in high-volume risk-off (expectancy is negative)")
    if expectancy_by_regime.get("qqq_downtrend_vix_rising", 0) < 0:
        disable_conditions.append("QQQ in downtrend with rising VIX")
    if expectancy_by_vix_dir.get("rising", 0) < 0:
        disable_conditions.append("VIX direction is rising (5-day slope > 0)")
    if expectancy_by_sector.get("underperforming", 0) < 0:
        disable_conditions.append("Sector underperforming QQQ (lack of confirmation)")
    if expectancy_by_entry_type.get("re_entry_stop", 0) < 0:
        disable_conditions.append("Re-entry after stop-loss (typically lower win-rate and negative expectancy)")

    # Construct findings report
    report_path = os.path.join(BASE, "findings", "rs_pullback_backtest_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"win_rate: {win_rate:.4f}\n")
        f.write(f"average_win: {avg_win:.4f}\n")
        f.write(f"average_loss: {avg_loss:.4f}\n")
        f.write(f"profit_factor: {profit_factor:.4f}\n")
        f.write(f"max_drawdown: {max_dd:.4f}\n")
        f.write(f"max_adverse_excursion:\n")
        f.write(f"  mean_mae: {mean_mae:.4f}\n")
        f.write(f"  max_mae: {max_mae:.4f}\n")
        f.write(f"expectancy_by_regime:\n")
        for r, exp in expectancy_by_regime.items():
            f.write(f"  {r}: {exp:.4f}\n")
        f.write(f"effect_of_VIX_direction:\n")
        for d, exp in expectancy_by_vix_dir.items():
            f.write(f"  {d}: {exp:.4f}\n")
        f.write(f"effect_of_QQQ_direction:\n")
        for d, exp in expectancy_by_qqq_dir.items():
            f.write(f"  {d}: {exp:.4f}\n")
        f.write(f"effect_of_re_entry:\n")
        for e, exp in expectancy_by_entry_type.items():
            f.write(f"  {e}: {exp:.4f}\n")
        f.write(f"leveraged_vs_underlying_comparison:\n")
        f.write(f"  underlying_avg_return: {stock_avg:.4f}\n")
        f.write(f"  leveraged_avg_return: {lev_avg:.4f}\n")
        f.write(f"  underlying_win_rate: {stock_win_rate:.4f}\n")
        f.write(f"  leveraged_win_rate: {lev_win_rate:.4f}\n")
        f.write(f"  underlying_max_mae: {stock_max_mae:.4f}\n")
        f.write(f"  leveraged_max_mae: {lev_max_mae:.4f}\n")
        f.write(f"recommended_disable_conditions:\n")
        for cond in disable_conditions:
            f.write(f"  - \"{cond}\"\n")
        f.write("data_quality_notes: \"Yahoo Finance daily data from 2021 to 2026. All data aligned to QQQ trading days. Leveraged calculations are approximated using daily high/low values for SOXL and TQQQ.\"\n")
        f.write("---\n\n")
        
        f.write("# RS Pullback Rebound Tactic Backtest Evidence Packet\n\n")
        f.write("## Overview\n")
        f.write("This evidence packet documents the quantitative backtest results for the **RS Pullback Rebound Tactic** ")
        f.write("using historical daily data from 2021-01-01 to 2026-06-01. The backtest evaluated NVDA, AMD, COHR, and AAOI ")
        f.write("against QQQ, SPY, VIX, and their sector and leverage pairings.\n\n")
        
        f.write("## Performance Metrics\n")
        f.write(f"- **Total Trades Triggered**: {total_trades}\n")
        f.write(f"- **Win Rate**: {win_rate:.2%}\n")
        f.write(f"- **Average Win**: {avg_win:.2%}\n")
        f.write(f"- **Average Loss**: {avg_loss:.2%}\n")
        f.write(f"- **Profit Factor**: {profit_factor:.2f}\n")
        f.write(f"- **Max Drawdown**: {max_dd:.2%}\n")
        f.write(f"- **Max Adverse Excursion (MAE)**: Mean = {mean_mae:.2%}, Max = {max_mae:.2%}\n\n")
        
        f.write("## Regime Splits & Expectancy Analysis\n")
        f.write("### 1. Market Regime Expectancy\n")
        for r, exp in expectancy_by_regime.items():
            f.write(f"- **{r}**: {exp:.2%} average return per trade\n")
        f.write("\n")
        
        f.write("### 2. VIX Direction Effect\n")
        for d, exp in expectancy_by_vix_dir.items():
            f.write(f"- **VIX {d}**: {exp:.2%} average return\n")
        f.write("\n")
        
        f.write("### 3. Sector Confirmation Impact\n")
        for s, exp in expectancy_by_sector.items():
            f.write(f"- **Sector {s}**: {exp:.2%} average return\n")
        f.write("\n")
        
        f.write("### 4. Entry Type & Re-entry Impact\n")
        for e, exp in expectancy_by_entry_type.items():
            f.write(f"- **{e}**: {exp:.2%} average return\n")
        f.write("\n")
        
        f.write("## Leveraged vs. Underlying Comparison\n")
        f.write("| Metric | Underlying Stock | Leveraged Product |\n")
        f.write("| --- | --- | --- |\n")
        f.write(f"| **Average Return** | {stock_avg:.2%} | {lev_avg:.2%} |\n")
        f.write(f"| **Win Rate** | {stock_win_rate:.2%} | {lev_win_rate:.2%} |\n")
        f.write(f"| **Max Adverse Excursion (MAE)** | {stock_max_mae:.2%} | {lev_max_mae:.2%} |\n\n")
        
        f.write("## Recommended Disable Conditions\n")
        for cond in disable_conditions:
            f.write(f"- **Disable if**: {cond}\n")
        f.write("\n")
        
        f.write("## Trade Log Summary\n")
        f.write("| Date | Symbol | Entry | Exit | PnL | Regime | Entry Type |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for idx, row in df_trades.head(30).iterrows():
            f.write(f"| {row['entry_date']} | {row['symbol']} | ${row['entry_price']:.2f} | ${row['exit_price']:.2f} | {row['pnl']:.2%} | {row['regime']} | {row['entry_type']} |\n")
        
    print(f"[SUCCESS] Backtest completed. Report saved to {report_path}")

if __name__ == "__main__":
    run_backtest()
