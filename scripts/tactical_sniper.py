import sys
import os
import json
import yfinance as yf
import pandas as pd
import numpy as np

# Ensure UTF-8 Console Printing
sys.stdout.reconfigure(encoding='utf-8')

# Global Configurations with Fallbacks
DEFAULT_RULES = {
    "methodology_14_high_beta_gap": {
        "vc_threshold_pct": 30.0,
        "bracket_stop_loss_pct": 1.5,
        "t1_size_pct": 30.0,
        "t2_t3_size_pct": 70.0
    },
    "methodology_15_low_catalyst_rs": {
        "vc_threshold_pct": 30.0,
        "bracket_stop_loss_pct": 0.5,
        "t1_size_pct": 30.0,
        "t2_t3_size_pct": 70.0,
        "nvda_exit_trigger": True
    }
}

def load_tactical_rules():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "tactical_rules.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
                # Verify basic keys exist
                if "methodology_14_high_beta_gap" in rules and "methodology_15_low_catalyst_rs" in rules:
                    return rules
        except Exception as e:
            print(f"⚠️ 警告: 读取 config/tactical_rules.json 失败 ({e})，使用默认参数...")
    return DEFAULT_RULES

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/tactical_sniper.py <TICKER> [DATE]")
        sys.exit(1)
        
    ticker_sym = sys.argv[1].upper()
    target_date = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Load Dynamic Rules
    rules = load_tactical_rules()
    
    print(f"==================================================")
    print(f"🎯 盘后/盘中单兵战术狙击器: {ticker_sym} 深度扫描中...")
    print(f"==================================================")
    
    ticker = yf.Ticker(ticker_sym)
    
    # Download 5m data for the last 5 days
    try:
        df = ticker.history(period="5d", interval="5m")
    except Exception as e:
        print(f"🔴 获取 {ticker_sym} 数据失败: {e}")
        sys.exit(1)
        
    if df.empty:
        print(f"🔴 {ticker_sym} 的 intraday 数据为空，请检查代码拼写或网络状态。")
        sys.exit(1)
        
    # Group by date to work on the most recent session
    df['Date'] = df.index.date
    unique_dates = df['Date'].unique()
    
    if target_date:
        try:
            target_dt = pd.to_datetime(target_date).date()
            if target_dt in unique_dates:
                session_df = df[df['Date'] == target_dt].copy()
            else:
                print(f"⚠️ 指定日期 {target_date} 不在近5日交易数据中，自动选择最新交易日...")
                session_df = df[df['Date'] == unique_dates[-1]].copy()
        except:
            session_df = df[df['Date'] == unique_dates[-1]].copy()
    else:
        session_df = df[df['Date'] == unique_dates[-1]].copy()
        
    if session_df.empty:
        print("🔴 无法定位有效的交易 Session。")
        sys.exit(1)
        
    actual_date = session_df['Date'].iloc[0]
    print(f"📅 交易 Session 日期: {actual_date}")
    
    # Calculate VWAP
    session_df['Typical_Price'] = (session_df['High'] + session_df['Low'] + session_df['Close']) / 3
    session_df['TP_Vol'] = session_df['Typical_Price'] * session_df['Volume']
    session_df['Cum_TP_Vol'] = session_df['TP_Vol'].cumsum()
    session_df['Cum_Vol'] = session_df['Volume'].cumsum()
    session_df['VWAP'] = session_df['Cum_TP_Vol'] / session_df['Cum_Vol']
    
    total_bars = len(session_df)
    if total_bars < 1:
        print("🔴 该 Session 的 K 线柱数不足，无法分析。")
        sys.exit(1)
        
    # 1. Open Peak Spotting (First 3 bars: 09:30 - 09:45)
    open_bars = session_df.iloc[:3]
    opening_peak_idx = open_bars['Volume'].idxmax()
    opening_peak_bar = open_bars.loc[opening_peak_idx]
    
    open_time = opening_peak_idx.strftime('%H:%M')
    open_peak_price = opening_peak_bar['High']
    open_peak_vol = opening_peak_bar['Volume']
    
    # 2. Pullback Phase Scan (Looking for lowest price in the next 14 bars after peak)
    peak_loc = session_df.index.get_loc(opening_peak_idx)
    pullback_pool = session_df.iloc[peak_loc+1 : min(peak_loc+15, total_bars)]
    
    if not pullback_pool.empty:
        pullback_min_idx = pullback_pool['Low'].idxmin()
        pullback_bar = pullback_pool.loc[pullback_min_idx]
        
        pb_time = pullback_min_idx.strftime('%H:%M')
        pb_price = pullback_bar['Low']
        pb_vol = pullback_bar['Volume']
        
        # Volume Contraction Ratio
        vc_ratio = (pb_vol / open_peak_vol) * 100
    else:
        pb_time = "N/A"
        pb_price = 0.0
        pb_vol = 0.0
        vc_ratio = 100.0
        
    # 3. Current Live / Latest Bar Status
    latest_idx = session_df.index[-1]
    latest_bar = session_df.loc[latest_idx]
    
    curr_time = latest_idx.strftime('%H:%M')
    curr_price = latest_bar['Close']
    curr_vwap = latest_bar['VWAP']
    curr_vol = latest_bar['Volume']
    vwap_dist = ((curr_price - curr_vwap) / curr_vwap) * 100
    
    # 4. Check for VWAP Reclaim
    reclaim_signal = "NO"
    if len(session_df) >= 3:
        last_3 = session_df.iloc[-3:]
        was_below = any(last_3.iloc[:-1]['Close'] < last_3.iloc[:-1]['VWAP'])
        now_above = last_3.iloc[-1]['Close'] > last_3.iloc[-1]['VWAP']
        if was_below and now_above:
            reclaim_signal = "⚡ YES (CROSS OVER)"
        elif now_above:
            reclaim_signal = "🟢 HUGGING ABOVE"
        else:
            reclaim_signal = "🔴 BELOW VWAP"
            
    # 5. Classify Ticker Setup type dynamically based on gap/catalyst structure
    # For simplicity, we treat high-gap (>8%) or specific tickers as Methodology #14, others as #15
    # Let's check opening gap relative to yesterday's close if available in session
    # We load parameters depending on classification
    is_high_beta_gap = vwap_dist > 5.0 or (latest_bar['Open'] / df.iloc[df.index.get_loc(session_df.index[0]) - 1]['Close'] > 1.08 if df.index.get_loc(session_df.index[0]) > 0 else False)
    
    if is_high_beta_gap:
        setup_name = "Methodology #14: High-Beta Gap"
        cfg = rules["methodology_14_high_beta_gap"]
    else:
        setup_name = "Methodology #15: Low-Catalyst RS"
        cfg = rules["methodology_15_low_catalyst_rs"]
        
    vc_thresh = cfg["vc_threshold_pct"]
    stop_loss_pct = cfg["bracket_stop_loss_pct"]
            
    # 6. Determine Sniper Action Decision using dynamic config parameters
    decision = "⏳ 观望 (WAITING)"
    reason = "盘中数据不足或未见异动"
    
    if curr_price < curr_vwap:
        if curr_vol > open_peak_vol * 0.5:
            decision = "🔴 瀑布警报 (WATERFALL DANGER)"
            reason = "股价运行于 VWAP 下方且成交量放大，判定为抛压出货"
        else:
            decision = "⏳ 观察洗盘 (WATCHING)"
            reason = f"股价在 VWAP 下方缩量运行，等待 Reclaim 阳线确认 (当前阻力位: {curr_vwap:.2f})"
    else:
        if vc_ratio <= vc_thresh:
            if curr_price >= open_peak_price:
                decision = "🎯 T2/T3 突破加仓 (BREAKOUT ADD)"
                reason = f"缩量回调(VC:{vc_ratio:.1f}%)获得VWAP支撑后，股价已突破早盘日高 {open_peak_price:.2f}"
            else:
                decision = "🎯 T1 单兵狙击点 (SNIPER BUY)"
                reason = f"天量RS确认，回踩极度缩量(VC:{vc_ratio:.1f}%, 阈值:{vc_thresh:.0f}%)，现已收复并站稳VWAP {curr_vwap:.2f}"
        else:
            decision = "⚠️ 警惕假拉升 (CAUTION)"
            reason = f"虽然价格站上 VWAP，但回踩期量能收缩不足(VC:{vc_ratio:.1f}%, 阈值:{vc_thresh:.0f}%)，机构洗盘筹码锁定度低"

    # Print Breathtaking ASCII Dashboard
    print(f"📊 识别战术模板 : {setup_name}")
    print(f"\n[📊 1. 首K突变 RS 相对强度探测]")
    print(f"   • 开盘峰值时间 : {open_time}")
    print(f"   • 首K冲高日高   : ${open_peak_price:.2f}")
    print(f"   • 首K天量成交量 : {open_peak_vol:,} 股")
    
    print(f"\n[📉 2. 回调洗盘期量能衰竭度 (Volume Contraction)]")
    print(f"   • 回调洗盘低点 : ${pb_price:.2f} ({pb_time})")
    print(f"   • 极限收缩成交量: {pb_vol:,} 股")
    print(f"   • 核心 VC 收缩比: {vc_ratio:.2f}% " + (f"(🟢 满足 <{vc_thresh:.0f}% 洗盘标准)" if vc_ratio <= vc_thresh else f"(🔴 >{vc_thresh:.0f}% 浮筹未洗净)"))
    
    print(f"\n[⚡ 3. 当前实时量价与 VWAP 关系]")
    print(f"   • 当前监控时间 : {curr_time}")
    print(f"   • 当前股价 / VWAP: ${curr_price:.2f} / ${curr_vwap:.2f}")
    print(f"   • 偏离度 (Distance): {vwap_dist:+.2f}%")
    print(f"   • VWAP 状态信号 : {reclaim_signal}")
    
    print(f"\n[🔮 4. 战术单兵狙击决策板]")
    print(f"   ==================================================")
    print(f"   🎯 战术决断: {decision}")
    print(f"   ✍️ 决断理由: {reason}")
    print(f"   ==================================================")
    print(f"   * 止损配置级别: {stop_loss_pct}% (基于方法论)")
    print(f"   * 止损参考价位: 设在洗盘日低 ${pb_price:.2f} 之下 (约 ${pb_price*(1 - stop_loss_pct/100.0):.2f})")
    print(f"==================================================\n")

if __name__ == "__main__":
    main()
