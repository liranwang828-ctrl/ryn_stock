# agents/data_agent.py
"""Usage: data_agent.py <symbol> [--light] [--full]"""
import sys, os, json, argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from stock_team.utils.protocol import BASE, QUOTA_PATH, EXIT_OK, EXIT_FAIL, EXIT_SKIP

import yfinance as yf

def _to_python(v):
    """Convert numpy scalar types to native Python types for JSON serialization."""
    try:
        import numpy as np
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
    except ImportError:
        pass
    return v

def load_quota():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if os.path.exists(QUOTA_PATH):
        q = json.load(open(QUOTA_PATH, encoding="utf-8"))
        if q.get("date") == today:
            return q
    return {"date": today, "used": 0}

def save_quota(q):
    json.dump(q, open(QUOTA_PATH, "w", encoding="utf-8"))

def get_ticker(symbol):
    from curl_cffi import requests as curl_requests
    class TimeoutSession(curl_requests.Session):
        def request(self, *args, **kwargs):
            if 'timeout' not in kwargs or kwargs['timeout'] is None:
                kwargs['timeout'] = 10.0
            return super().request(*args, **kwargs)
    session = TimeoutSession(impersonate="chrome")
    return yf.Ticker(symbol, session=session)

def get_api_key():
    """Reads POLYGON_API_KEY from .env file"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(env_path):
        return None
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("POLYGON_API_KEY="):
                key = line.strip().split("=")[1].strip()
                if "your_actual_api_key_here" in key or not key:
                    return None
                return key
    return None

def fetch_polygon_news(symbol, api_key):
    """Fetches news from Polygon.io and formats it like yfinance news"""
    if not api_key:
        return []
    import requests
    url = f"https://api.polygon.io/v2/reference/news?ticker={symbol.upper()}&limit=8&apiKey={api_key}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        res = r.json()
        results = res.get("results", [])
        headlines = []
        for n in results:
            title = n.get("title", "")
            publisher = n.get("publisher", {}).get("name", "")
            pub_utc = n.get("published_utc", "")
            dt_n = pub_utc[5:10] if pub_utc else "?"
            summary = n.get("description", "") or n.get("title", "")
            if title:
                headlines.append({
                    "title": title,
                    "publisher": publisher,
                    "time": dt_n,
                    "summary": summary[:120],
                })
        return headlines
    except Exception:
        return []

def fetch_polygon_daily_bars(symbol, api_key):
    """Fetches past 2 years of daily bars from Polygon.io and returns a pandas DataFrame like yfinance history"""
    import pandas as pd
    import requests
    from datetime import datetime, timedelta
    
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=730)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start_str}/{end_str}?adjusted=true&sort=asc&limit=5000&apiKey={api_key}"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code != 200:
            return pd.DataFrame()
        res = r.json()
        results = res.get("results", [])
        if not results:
            return pd.DataFrame()
            
        data = []
        for b in results:
            dt = datetime.fromtimestamp(b["t"] / 1000.0, tz=timezone.utc)
            data.append({
                "Date": dt,
                "Open": b["o"],
                "High": b["h"],
                "Low": b["l"],
                "Close": b["c"],
                "Volume": b["v"]
            })
        df = pd.DataFrame(data)
        df.set_index("Date", inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def fetch_polygon_ticker_details(symbol, api_key):
    """Fetches ticker description details from Polygon.io"""
    import requests
    url = f"https://api.polygon.io/v3/reference/tickers/{symbol.upper()}?apiKey={api_key}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return {}
        res = r.json().get("results", {})
        return {
            "long_name": res.get("name"),
            "website": res.get("homepage_url"),
            "description": res.get("description"),
            "employees": res.get("total_employees"),
            "industry": res.get("sic_description"),
            "sector": res.get("sic_description", "").split("—")[0].strip() if res.get("sic_description") else ""
        }
    except Exception:
        return {}

def fetch_primary(symbol, light=False):
    api_key = get_api_key()
    hist = pd.DataFrame()
    poly_details = {}
    
    if api_key:
        print(f"📡 [Polygon.io] Fetching daily bars & metadata for {symbol}...")
        hist = fetch_polygon_daily_bars(symbol, api_key)
        poly_details = fetch_polygon_ticker_details(symbol, api_key)
        
    t = None
    if hist.empty:
        print(f"⚠️ [Polygon.io] Failed or empty. Falling back to yfinance for {symbol}...")
        t = get_ticker(symbol)
        hist = t.history(period="2y")
        if hist.empty:
            return None
            
    latest = hist.index[-1]
    fields = {
        "close":  hist["Close"][latest],
        "volume": hist["Volume"][latest],
    }

    # Pre/post-market price
    pre = None
    post = None
    try:
        # Try fetching real-time quote via Polygon first if key available
        if api_key:
            import requests
            # Fetch previous close and current day quote details
            q_url = f"https://api.polygon.io/v2/last/nbbo/{symbol.upper()}?apiKey={api_key}"
            q_res = requests.get(q_url, timeout=5)
            if q_res.status_code == 200:
                q_data = q_res.json().get("results", {})
                # Use ask price as a proxy for premarket if before open
                pre = q_data.get("P") # Price of NBBO
        
        # Fallback to yfinance quote for premarket
        if not pre:
            if not t:
                t = get_ticker(symbol)
            info_quick = t.info
            pre  = info_quick.get("preMarketPrice")
            post = info_quick.get("postMarketPrice")
            
        last_close = float(hist["Close"].iloc[-1])
        ext_price = pre or post
        fields["pre_market_price"]  = pre
        fields["post_market_price"] = post
        fields["has_extended_price"] = ext_price is not None
        fields["overnight_chg"] = float((ext_price - last_close) / last_close) if ext_price else 0.0
        fields["extended_session"] = "pre" if pre else "post" if post else "none"
    except Exception:
        fields["pre_market_price"]  = None
        fields["post_market_price"] = None
        fields["has_extended_price"] = False
        fields["overnight_chg"] = 0.0
        fields["extended_session"] = "none"

    if not light:
        if not t:
            t = get_ticker(symbol)
        info = t.info if t else {}
        
        prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else hist["Close"][latest]
        vol_ma20 = hist["Volume"].rolling(20).mean().iloc[-1]
        close_s = hist["Close"]
        ema12 = close_s.ewm(span=12, adjust=False).mean()
        ema26 = close_s.ewm(span=26, adjust=False).mean()
        macd  = (ema12 - ema26).iloc[-1]
        delta = close_s.diff()
        gain  = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
        loss  = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
        rsi14 = (100 - 100 / (1 + gain / loss)).iloc[-1]
        fields.update({
            "prev_close":   prev_close,
            "vol_ma20":     vol_ma20,
            "macd":         macd,
            "rsi14":        rsi14,
            "pe_ratio":     info.get("trailingPE"),
            "pb_ratio":     info.get("priceToBook"),
            "market_cap":   info.get("marketCap"),
            "revenue":      info.get("totalRevenue"),
            "eps":          info.get("trailingEps"),
            "analyst_rec":  info.get("recommendationMean"),
            "target_price": info.get("targetMeanPrice"),
            "beta":         info.get("beta"),
            "52w_high":     info.get("fiftyTwoWeekHigh"),
            "52w_low":      info.get("fiftyTwoWeekLow"),
            # ── 公司概况（优先从 Polygon.io 提取，yfinance 降级）─────────────
            "long_name":        poly_details.get("long_name") or info.get("longName") or info.get("shortName", ""),
            "sector":           poly_details.get("sector") or info.get("sector", ""),
            "industry":         poly_details.get("industry") or info.get("industry", ""),
            "description":      (poly_details.get("description") or info.get("longBusinessSummary") or "")[:300],
            "employees":        poly_details.get("employees") or info.get("fullTimeEmployees"),
            "country":          info.get("country", ""),
            # ── 更多估值指标 ──────────────────────────────────────────
            "pe_fwd":           info.get("forwardPE"),
            "peg":              info.get("pegRatio"),
            "price_to_book":    info.get("priceToBook"),
            "rev_growth_pct":   round((info.get("revenueGrowth") or 0) * 100, 1),
            "gross_margin":     round((info.get("grossMargins") or 0) * 100, 1),
            "operating_margin": round((info.get("operatingMargins") or 0) * 100, 1),
            "roe":              round((info.get("returnOnEquity") or 0) * 100, 1),
            "fcf_B":            round((info.get("freeCashflow") or 0) / 1e9, 2),
            "short_pct":        round((info.get("shortPercentOfFloat") or 0) * 100, 1),
            "n_analysts":       info.get("numberOfAnalystOpinions"),
            "rec_key":          info.get("recommendationKey", ""),
            "inst_pct":         round((info.get("heldPercentInstitutions") or 0) * 100, 1),
        })

        # --- Persona fields ---
        # Aliases for persona compatibility
        fields["hi52"] = info.get("fiftyTwoWeekHigh")
        fields["fcf"]  = info.get("freeCashflow") or 0
        # Moving averages
        fields["ma50"]  = float(close_s.rolling(50).mean().iloc[-1])  if len(hist) >= 50  else None
        fields["ma150"] = float(close_s.rolling(150).mean().iloc[-1]) if len(hist) >= 150 else None
        fields["ma200"] = float(close_s.rolling(200).mean().iloc[-1]) if len(hist) >= 200 else None

        # Volume breakout ratio
        fields["volume_breakout_ratio"] = float(hist["Volume"].iloc[-1] / vol_ma20) if vol_ma20 else None

        # VCP: last 3 five-day windows price range shrinking
        def vcp_check(h):
            if len(h) < 15: return False
            r1 = float(h["High"].iloc[-5:].max()   - h["Low"].iloc[-5:].min())
            r2 = float(h["High"].iloc[-10:-5].max() - h["Low"].iloc[-10:-5].min())
            r3 = float(h["High"].iloc[-15:-10].max()- h["Low"].iloc[-15:-10].min())
            return r1 < r2 < r3
        fields["vcp_detected"] = vcp_check(hist)

        # Price change 3 months
        p3m = hist["Close"].iloc[-63] if len(hist) >= 63 else hist["Close"].iloc[0]
        fields["price_chg_3m"] = float((hist["Close"].iloc[-1] - p3m) / p3m)

        # Max drawdown 1 year
        roll_max = hist["Close"].rolling(252, min_periods=1).max()
        fields["hist_max_drawdown"] = float(abs(((hist["Close"] - roll_max) / roll_max).min()))

        # SPY/VIX macro proxies
        try:
            spy_hist = pd.DataFrame()
            if api_key:
                spy_hist = fetch_polygon_daily_bars("SPY", api_key)
            if spy_hist.empty:
                spy_hist = get_ticker("SPY").history(period="1y")
                
            spy_ma200 = spy_hist["Close"].rolling(200).mean().iloc[-1]
            fields["spy_above_ma200"] = bool(spy_hist["Close"].iloc[-1] > spy_ma200)
            spy_ret = spy_hist["Close"].pct_change().tail(60)
            stk_ret = hist["Close"].pct_change().tail(60)
            aligned = stk_ret.reindex(spy_ret.index, method="nearest").dropna()
            spy_al  = spy_ret.reindex(aligned.index).dropna()
            if len(aligned) > 5:
                fields["correlation_with_spy"] = float(aligned.corr(spy_al))
            else:
                fields["correlation_with_spy"] = 0.5
            fields["rs_vs_market"] = float(hist["Close"].iloc[-1] / hist["Close"].iloc[-2]) / \
                                     float(spy_hist["Close"].iloc[-1] / spy_hist["Close"].iloc[-2]) \
                                     if len(spy_hist) > 1 else 1.0
            fields["sector_inflow_positive"] = bool(spy_hist["Close"].iloc[-1] > spy_ma200)
            fields["sector_healthy"]          = fields["sector_inflow_positive"]
        except Exception:
            fields["spy_above_ma200"]       = True
            fields["correlation_with_spy"]  = 0.5
            fields["rs_vs_market"]          = 1.0
            fields["sector_inflow_positive"] = True
            fields["sector_healthy"]         = True

        try:
            vix_hist = pd.DataFrame()
            if api_key:
                vix_hist = fetch_polygon_daily_bars("VIX", api_key)
            if vix_hist.empty:
                vix_hist = get_ticker("^VIX").history(period="1y")
                
            vix_val  = float(vix_hist["Close"].iloc[-1])
            vix_delta = vix_val - float(vix_hist["Close"].iloc[-5])
            fields["vix"]           = vix_val
            fields["vix_trend"]     = "rising" if vix_delta > 0.5 else "falling" if vix_delta < -0.5 else "flat"
            fields["vix_percentile"]= float((vix_hist["Close"] < vix_val).mean())
        except Exception:
            fields["vix"] = 18.0; fields["vix_trend"] = "flat"; fields["vix_percentile"] = 0.5

        # Fundamental extras from info
        cash        = info.get("totalCash") or 0
        total_assets= info.get("totalAssets") or 1
        total_debt  = info.get("totalDebt") or 0
        shares      = info.get("sharesOutstanding") or 1
        bv          = info.get("bookValue") or 0
        equity      = bv * shares or 1
        fcf_val     = info.get("freeCashflow") or 0
        ocf_val     = info.get("operatingCashflow") or 0   # 经营性现金流（比FCF更能反映主业）
        cur_price   = hist["Close"].iloc[-1]
        fields["cash_ratio"]           = float(cash / total_assets) if total_assets else None
        fields["de_ratio"]             = float(total_debt / equity)
        fields["gross_margin"]         = info.get("grossMargins")
        fields["revenue_growth"]       = info.get("revenueGrowth")
        fields["insider_pct"]          = info.get("heldPercentInsiders")
        fields["institutional_ownership_pct"] = info.get("heldPercentInstitutions")
        fields["p_fcf"]                = float(cur_price * shares / fcf_val) if fcf_val and fcf_val > 0 else None
        fields["roe5y_avg"]            = info.get("returnOnEquity")
        fields["operating_cashflow"]   = ocf_val
        # FCF 质量判断：FCF 为负但经营性现金流为正 → CapEx 驱动，属扩产投资而非主业亏损
        fields["fcf_capex_driven"]     = bool(fcf_val <= 0 and ocf_val > 0)
        # 综合现金流健康度：FCF > 0 或（FCF < 0 但 OCF > 0 且 OCF > |FCF| * 0.5）
        fields["fcf_healthy"]          = bool(
            fcf_val > 0 or (fcf_val <= 0 and ocf_val > 0 and ocf_val > abs(fcf_val) * 0.5)
        )
        tgt = info.get("targetMeanPrice") or cur_price
        fields["upside_pct"]    = float((tgt - cur_price) / cur_price)
        fields["downside_pct"]  = 0.08   # default proxy
        fields["stop_loss_defined"] = True
        fields["position_pct"]  = 0.0
        fields["pe_percentile_30y"] = 15.0
        fields["pe_percentile_90y"] = 35.0
        fields["community_bull_pct"]= 0.5   # default; overwritten by CommunityAgent
        # Macro config from watchlist.json (user-configurable)
        try:
            wl = json.load(open(os.path.join(BASE, "watchlist.json"), encoding="utf-8"))
            mc = wl.get("macro_config", {})
        except Exception:
            mc = {}
        fields["fed_hiking"]               = mc.get("fed_hiking",               False)
        fields["fed_easing"]               = mc.get("fed_easing",               False)
        fields["fed_pause"]                = mc.get("fed_pause",                True)
        fields["fed_cut_this_month"]       = mc.get("fed_cut_this_month",       False)
        fields["treasury10y_monthly_delta"]= mc.get("treasury10y_monthly_delta",0.0)
        fields["yield_curve_inverted"]     = mc.get("yield_curve_inverted",     False)
        fields["curve_inverted_months"]    = mc.get("curve_inverted_months",    0)

    # News headlines (always fetch, used by SentimentAgent)
    try:
        api_key = get_api_key()
        headlines = fetch_polygon_news(symbol, api_key)
        # Fallback to yfinance news if Polygon news fails or returns empty
        if not headlines:
            news_raw = t.news or []
            headlines = []
            for n in news_raw[:8]:
                # yfinance ≥0.2.50 嵌套格式: {'id': ..., 'content': {...}}
                # 旧格式: {'title': ..., 'publisher': ..., 'providerPublishTime': ...}
                if "content" in n:
                    c = n["content"]
                    title     = c.get("title", "")
                    publisher = (c.get("provider") or {}).get("displayName", "")
                    pub_date  = c.get("pubDate", "")
                    dt_n = pub_date[:10] if pub_date else "?"
                    summary   = c.get("summary", "") or c.get("description", "")
                else:
                    title     = n.get("title", "")
                    publisher = n.get("publisher", "")
                    ts_n      = n.get("providerPublishTime", 0)
                    dt_n      = datetime.fromtimestamp(ts_n, tz=timezone.utc).strftime("%m-%d") if ts_n else "?"
                    summary   = ""
                if title:
                    headlines.append({
                        "title":     title,
                        "publisher": publisher,
                        "time":      dt_n,
                        "summary":   summary[:120],
                    })
        fields["news_headlines"] = headlines
    except Exception:
        fields["news_headlines"] = []

    return fields

def fetch_secondary(symbol, quota):
    """Fetch close/volume from Alpha Vantage if quota allows."""
    key = os.environ.get("ALPHA_VANTAGE_KEY", "")
    if not key or quota["used"] >= 20:
        return None, quota
    import requests
    url = (f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
           f"&symbol={symbol}&apikey={key}")
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get("Global Quote", {})
        if not data:
            return None, quota
        quota["used"] += 1
        save_quota(quota)
        return {"close": float(data.get("05. price", 0)),
                "volume": int(data.get("06. volume", 0))}, quota
    except Exception:
        return None, quota

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--light", action="store_true")
    args = parser.parse_args()

    quota = load_quota()
    primary = fetch_primary(args.symbol, light=args.light)
    if primary is None:
        sys.exit(EXIT_SKIP)

    out_primary = {
        "symbol": args.symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "light": args.light,
        "fields": {k: {"value": _to_python(v)} for k, v in primary.items() if v is not None}
    }
    json.dump(out_primary, open(os.path.join(BASE, "data_raw_primary.json"), "w", encoding="utf-8"), indent=2)

    secondary, quota = fetch_secondary(args.symbol, quota)
    out_secondary = {
        "symbol": args.symbol,
        "secondary_available": secondary is not None,
        "fields": {k: {"value": _to_python(v)} for k, v in (secondary or {}).items()}
    }
    json.dump(out_secondary, open(os.path.join(BASE, "data_raw_secondary.json"), "w", encoding="utf-8"), indent=2)

    # 注入公司档案（knowledge/company_profiles.json）供 CIO agents 使用
    try:
        _cp_path = os.path.join(BASE, "knowledge", "company_profiles.json")
        if os.path.exists(_cp_path):
            _profiles = json.load(open(_cp_path, encoding="utf-8"))
            _profile  = _profiles.get(args.symbol, {})
            if _profile:
                _profile_out = {
                    "symbol": args.symbol,
                    "profile": _profile,
                }
                json.dump(_profile_out,
                          open(os.path.join(BASE, "company_profile_current.json"), "w", encoding="utf-8"),
                          indent=2, ensure_ascii=False)
    except Exception:
        pass

if __name__ == "__main__":
    main()
