import os
import math
import datetime
import json
import yfinance as yf
import pandas as pd
import numpy as np

class OptionChainAnalyzer:
    """
    Advanced Option Chain Trend Analyzer
    Provides:
      - IV Skew (OTM Put IV vs OTM Call IV)
      - Net Gamma Exposure (GEX) by Strike
      - Zero-Gamma Level, Call Wall, and Put Wall
      - Put/Call Open Interest & Volume Ratios (PCR)
      - Volatility Smile Simulator (fallback when real-time free options data is zeroed out)
    """
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.ticker = yf.Ticker(self.symbol)
        
    def fetch_current_price(self):
        try:
            hist = self.ticker.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            info = self.ticker.info
            return float(info.get('regularMarketPrice') or info.get('previousClose') or 0.0)
        except Exception:
            return 0.0

    def normal_pdf(self, x):
        return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)

    def calculate_gamma(self, S, K, T, r, sigma):
        """
        Black-Scholes Gamma Formula:
        Gamma = N'(d1) / (S * sigma * sqrt(T))
        """
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0.0
        try:
            d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            pdf_d1 = self.normal_pdf(d1)
            gamma = pdf_d1 / (S * sigma * math.sqrt(T))
            return gamma
        except Exception:
            return 0.0

    def get_expiration_dates(self):
        try:
            return list(self.ticker.options)
        except Exception:
            return []

    def run_simulation(self, S):
        """
        Volatility Smile & OI Distribution Simulator (Sophisticated Fallback)
        Used when yfinance returns zeroed-out or stale options chain data.
        """
        # Determine base parameters based on stock style
        vol_bases = {
            "TSM": (0.35, -0.20, 0.40, 5000),   # ATM IV, skew, smile, base OI
            "NOW": (0.28, -0.15, 0.35, 2000),
            "SYM": (0.55, -0.25, 0.50, 4000),
            "VST": (0.42, -0.18, 0.45, 3000),
            "LITX": (0.38, -0.18, 0.40, 1500)
        }
        
        atm_iv, skew_coef, smile_coef, base_oi = vol_bases.get(self.symbol, (0.30, -0.18, 0.40, 2000))
        
        # Generate strikes: 30 strikes around current price, spaced appropriately
        # Stocks > $100 use $5 or $10 spacing, stocks < $100 use $1 or $2.5 spacing
        if S > 500:
            spacing = 10.0
        elif S > 100:
            spacing = 5.0
        elif S > 20:
            spacing = 2.5
        else:
            spacing = 1.0
            
        atm_strike = round(S / spacing) * spacing
        strikes = [atm_strike + i * spacing for i in range(-15, 16)]
        
        # We simulate the nearest monthly expiration (say, 23 DTE)
        exp_date = (datetime.date.today() + datetime.timedelta(days=23)).strftime("%Y-%m-%d")
        
        sim_calls = []
        sim_puts = []
        
        for K in strikes:
            if K <= 0:
                continue
            # Distance from ATM
            pct_diff = (K - S) / S
            
            # Volatility smile formula
            sigma = atm_iv + skew_coef * pct_diff + smile_coef * (pct_diff ** 2)
            sigma = max(0.05, min(1.5, sigma)) # bound IV
            
            # Simulated open interest: bell curve around ATM + spikes at round strikes
            oi_bell = base_oi * math.exp(-0.5 * (pct_diff / 0.08)**2)
            
            # Add institutional spikes at round strikes (multiples of $10 or $50)
            round_spike = 1.0
            if K % 10 == 0:
                round_spike = 2.0
            if K % 50 == 0:
                round_spike = 4.0
                
            oi = int(oi_bell * round_spike)
            # Add some random noise
            oi = int(oi * (0.8 + 0.4 * (hash(str(K)) % 100) / 100.0))
            oi = max(5, oi)
            
            # Simulated volume: a fraction of open interest
            vol = int(oi * (0.05 + 0.15 * (hash(str(K) + "vol") % 100) / 100.0))
            vol = max(1, vol)
            
            # Simulated prices using standard intrinsic/extrinsic approximation
            extrinsic = S * atm_iv * 0.1 * math.exp(-0.5 * (pct_diff / 0.1)**2)
            
            call_intrinsic = max(0.0, S - K)
            call_price = call_intrinsic + extrinsic
            
            put_intrinsic = max(0.0, K - S)
            put_price = put_intrinsic + extrinsic
            
            sim_calls.append({
                "strike": float(K),
                "openInterest": int(oi),
                "volume": int(vol),
                "impliedVolatility": float(sigma),
                "lastPrice": round(call_price, 2)
            })
            
            sim_puts.append({
                "strike": float(K),
                "openInterest": int(oi * (1.1 + 0.1 * pct_diff)), # slightly more put OI for OTM puts
                "volume": int(vol * (0.9 + 0.1 * pct_diff)),
                "impliedVolatility": float(sigma + 0.02), # puts slightly higher IV
                "lastPrice": round(put_price, 2)
            })
            
        return pd.DataFrame(sim_calls), pd.DataFrame(sim_puts), exp_date

    def analyze(self, force_simulation=False):
        """
        Performs full analysis of the option chain.
        Returns a structured dictionary of metrics.
        """
        S = self.fetch_current_price()
        if S <= 0.0:
            return {"error": f"Could not fetch current price for {self.symbol}"}
            
        expirations = self.get_expiration_dates()
        
        calls_df, puts_df = None, None
        chosen_expiration = None
        is_simulated = False
        
        # Strategy: we want to look at the nearest monthly or a highly liquid expiration (15 to 45 DTE).
        # Monthly expirations are usually the 3rd Friday of the month.
        target_exp = None
        today = datetime.date.today()
        
        if expirations and not force_simulation:
            # Let's search for the first monthly expiration or nearest liquid one
            for exp in expirations:
                try:
                    exp_dt = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
                    days = (exp_dt - today).days
                    # Prefer expirations between 10 and 50 days to expiration
                    if 10 <= days <= 50:
                        target_exp = exp
                        break
                except Exception:
                    continue
            if not target_exp and len(expirations) > 0:
                target_exp = expirations[0]
                
            if target_exp:
                try:
                    chain = self.ticker.option_chain(target_exp)
                    # Check if yfinance returned actual non-zero data
                    calls_temp = chain.calls
                    puts_temp = chain.puts
                    
                    # Check if openInterest and impliedVolatility are zeroed out (stale premarket data)
                    valid_calls = calls_temp[(calls_temp['openInterest'] > 0) & (calls_temp['impliedVolatility'] > 0.001)]
                    if len(valid_calls) > 2:
                        calls_df = calls_temp.copy()
                        puts_df = puts_temp.copy()
                        chosen_expiration = target_exp
                    else:
                        # Stale yfinance data detected, we will fall back to simulation
                        pass
                except Exception:
                    pass
                    
        # If we failed to get real data, run the simulator!
        if calls_df is None or puts_df is None:
            calls_df, puts_df, chosen_expiration = self.run_simulation(S)
            is_simulated = True
            
        # ── 1. Calculate Put/Call Ratios ──
        total_call_oi = calls_df['openInterest'].sum()
        total_put_oi = puts_df['openInterest'].sum()
        pcr_oi = float(total_put_oi / total_call_oi) if total_call_oi > 0 else 1.0
        
        total_call_vol = calls_df['volume'].fillna(0).sum()
        total_put_vol = puts_df['volume'].fillna(0).sum()
        pcr_vol = float(total_put_vol / total_call_vol) if total_call_vol > 0 else 1.0
        
        # ── 2. Calculate IV Skew (OTM Put IV vs OTM Call IV) ──
        # OTM Put Strike ~ S * 0.95, OTM Call Strike ~ S * 1.05
        put_target_strike = S * 0.95
        call_target_strike = S * 1.05
        
        # Find closest strikes in the dataframes
        closest_put_idx = (puts_df['strike'] - put_target_strike).abs().idxmin()
        closest_call_idx = (calls_df['strike'] - call_target_strike).abs().idxmin()
        
        put_otm_iv = float(puts_df.loc[closest_put_idx, 'impliedVolatility'])
        call_otm_iv = float(calls_df.loc[closest_call_idx, 'impliedVolatility'])
        
        skew = put_otm_iv - call_otm_iv
        
        # ── 3. Calculate Black-Scholes Gamma & GEX ──
        exp_dt = datetime.datetime.strptime(chosen_expiration, "%Y-%m-%d").date()
        days_to_exp = (exp_dt - today).days
        days_to_exp = max(0.5, days_to_exp) # half day floor
        T = days_to_exp / 365.0
        r = 0.05 # 5% risk free rate
        
        # Net GEX calculation by Strike
        gex_by_strike = {}
        
        # Call GEX
        for _, row in calls_df.iterrows():
            strike = float(row['strike'])
            iv = float(row['impliedVolatility'])
            oi = float(row['openInterest'])
            if iv > 0.001 and oi > 0:
                gamma = self.calculate_gamma(S, strike, T, r, iv)
                # GEX standard formula: Gamma * OI * 100 * S * S * 0.01 (expressed in dollar impact per 1% move)
                gex = gamma * oi * 100 * S * S * 0.01
                gex_by_strike[strike] = gex_by_strike.get(strike, 0.0) + gex
                
        # Put GEX (subtracted to reflect negative MM positioning or standard put offsets)
        for _, row in puts_df.iterrows():
            strike = float(row['strike'])
            iv = float(row['impliedVolatility'])
            oi = float(row['openInterest'])
            if iv > 0.001 and oi > 0:
                gamma = self.calculate_gamma(S, strike, T, r, iv)
                gex = -gamma * oi * 100 * S * S * 0.01
                gex_by_strike[strike] = gex_by_strike.get(strike, 0.0) + gex
                
        # Locate Call Wall, Put Wall and Zero GEX Level
        # Call Wall: highest Call OI strike
        call_wall_idx = calls_df['openInterest'].idxmax()
        call_wall = float(calls_df.loc[call_wall_idx, 'strike'])
        call_wall_oi = int(calls_df.loc[call_wall_idx, 'openInterest'])
        
        # Put Wall: highest Put OI strike
        put_wall_idx = puts_df['openInterest'].idxmax()
        put_wall = float(puts_df.loc[put_wall_idx, 'strike'])
        put_wall_oi = int(puts_df.loc[put_wall_idx, 'openInterest'])
        
        # Zero-Gamma Level (where GEX crosses zero near spot price)
        # We sort strikes and find where GEX signs flip
        sorted_gex = sorted(gex_by_strike.items())
        zero_gamma_level = S
        min_gex_diff = float('inf')
        for i in range(len(sorted_gex) - 1):
            s1, g1 = sorted_gex[i]
            s2, g2 = sorted_gex[i+1]
            if g1 * g2 < 0: # Flip sign!
                # linear interpolation
                ratio = abs(g1) / (abs(g1) + abs(g2))
                z_level = s1 + ratio * (s2 - s1)
                diff = abs(z_level - S)
                if diff < min_gex_diff:
                    min_gex_diff = diff
                    zero_gamma_level = z_level
                    
        total_gex = sum(gex_by_strike.values())
        
        # Determine market sentiment based on skew and PCR
        # High PCR (>1.3) + high positive skew -> defensive put buying (Bearish/Defensive)
        # Low PCR (<0.7) + flat/negative skew -> aggressive call buying (Bullish/Speculative)
        if skew > 0.08 and pcr_oi > 1.2:
            sentiment = "Defensive (防守看跌)"
            sentiment_color = "red"
        elif skew < 0.02 and pcr_oi < 0.8:
            sentiment = "Speculative (极度看涨)"
            sentiment_color = "green"
        elif skew > 0.04:
            sentiment = "Normal Skew (温和防守)"
            sentiment_color = "yellow"
        else:
            sentiment = "Neutral (偏多震荡)"
            sentiment_color = "blue"

        # Determine option ATM IV (approximate closest to S)
        closest_atm_idx = (calls_df['strike'] - S).abs().idxmin()
        atm_iv_pct = float(calls_df.loc[closest_atm_idx, 'impliedVolatility']) * 100
        
        # Build GEX data list for charting (keep 10 strikes around spot for visualization)
        gex_list = []
        for strike, gex in sorted_gex:
            if S * 0.8 <= strike <= S * 1.2:
                gex_list.append({"strike": strike, "gex": round(gex, 2)})

        return {
            "symbol": self.symbol,
            "current_price": round(S, 2),
            "expiration": chosen_expiration,
            "days_to_expiration": int(days_to_exp),
            "is_simulated": is_simulated,
            "atm_iv_percent": round(atm_iv_pct, 1),
            "skew_value": round(skew, 4),
            "skew_put_iv": round(put_otm_iv, 4),
            "skew_call_iv": round(call_otm_iv, 4),
            "pcr_oi": round(pcr_oi, 2),
            "pcr_vol": round(pcr_vol, 2),
            "call_wall": round(call_wall, 2),
            "call_wall_oi": call_wall_oi,
            "put_wall": round(put_wall, 2),
            "put_wall_oi": put_wall_oi,
            "zero_gamma_level": round(zero_gamma_level, 2),
            "total_gex_dollars": round(total_gex, 2),
            "sentiment": sentiment,
            "sentiment_color": sentiment_color,
            "gex_chart_data": gex_list
        }

if __name__ == "__main__":
    import pprint
    # Test for TSM
    analyzer = OptionChainAnalyzer("TSM")
    res = analyzer.analyze()
    pprint.pprint(res)
