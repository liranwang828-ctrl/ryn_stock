# agents/data_agent.py
"""Usage: data_agent.py <symbol> [--light] [--full]"""
import sys, os, json, argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import BASE, QUOTA_PATH, EXIT_OK, EXIT_FAIL, EXIT_SKIP
from utils import get_logger, fetch_with_retry, atomic_write_json

import yfinance as yf

log = get_logger(__name__)

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
    """Load today's API quota usage, resetting if date has changed."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if os.path.exists(QUOTA_PATH):
        q = json.load(open(QUOTA_PATH, encoding="utf-8"))
        if q.get("date") == today:
            return q
    return {"date": today, "used": 0}

def save_quota(q):
    """Persist current API quota state to disk."""
    atomic_write_json(q, QUOTA_PATH)

def fetch_primary(symbol, light=False):
    """Fetch all primary data from yfinance: price history, fundamentals, and indicators."""
    t = yf.Ticker(symbol)
    hist = fetch_with_retry(lambda: t.history(period="2y"))
    if hist.empty:
        return None
    latest = hist.index[-1]
    fields = {
        "close":  hist["Close"][latest],
        "volume": hist["Volume"][latest],
    }

    # Pre/post-market price (always fetch regardless of light mode)
    try:
        info_quick = fetch_with_retry(lambda: t.info)
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
        info = fetch_with_retry(lambda: t.info)
        prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else hist["Close"][latest]
        close_s = hist["Close"]

        # Compute all 47 technical indicators from the OHLCV engine
        from indicators.compute_indicators import compute_all_indicators
        ind = compute_all_indicators(hist)

        fields.update({
            "prev_close":   prev_close,
            "vol_ma20":     ind.get("Volume_SMA_20"),
            "macd":         ind.get("MACD_line"),
            "rsi14":        ind.get("RSI_14"),
            "pe_ratio":     info.get("trailingPE"),
            "pb_ratio":     info.get("priceToBook"),
            "market_cap":   info.get("marketCap"),
            "revenue":      info.get("totalRevenue"),
            "eps":           info.get("trailingEps"),
            "earnings_date": info.get("earningsDate"),
            "analyst_rec":  info.get("recommendationMean"),
            "target_price": info.get("targetMeanPrice"),
            "beta":         info.get("beta"),
            "52w_high":     info.get("fiftyTwoWeekHigh"),
            "52w_low":      info.get("fiftyTwoWeekLow"),
        })

        # --- Persona fields ---
        import yfinance as _yf
        # Aliases for persona compatibility
        fields["hi52"] = info.get("fiftyTwoWeekHigh")
        fields["fcf"]  = info.get("freeCashflow") or 0
        # Moving averages
        fields["ma50"]  = ind.get("MA50")
        fields["ma150"] = float(close_s.rolling(150).mean().iloc[-1]) if len(hist) >= 150 else None
        fields["ma200"] = ind.get("MA200")

        # Volume breakout ratio — from engine
        fields["volume_breakout_ratio"] = ind.get("Volume_ratio")

        # VCP: last 3 five-day windows price range shrinking
        def vcp_check(h):
            """Detect Volatility Contraction Pattern via shrinking 5-day ranges."""
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
            spy_hist = fetch_with_retry(lambda: _yf.Ticker("SPY").history(period="1y"))
            spy_ma200 = spy_hist["Close"].rolling(200).mean().iloc[-1]
            fields["spy_above_ma200"] = bool(spy_hist["Close"].iloc[-1] > spy_ma200)
            fields["spy_daily_chg"] = float(spy_hist["Close"].iloc[-1] / spy_hist["Close"].iloc[-2] - 1) if len(spy_hist) > 1 else 0.0
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
            vix_hist = fetch_with_retry(lambda: _yf.Ticker("^VIX").history(period="1y"))
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

        # Merge all 47 technical indicators into fields (keep backward-compat fields above)
        if ind:
            fields.update(ind)

    # News headlines (always fetch, used by SentimentAgent)
    try:
        news_raw = fetch_with_retry(lambda: t.news or [])
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
        r = fetch_with_retry(lambda: requests.get(url, timeout=10))
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
    """Parse args, fetch primary and secondary data, and write raw data JSONs."""
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
    atomic_write_json(out_primary, os.path.join(BASE, "data_raw_primary.json"), indent=2)

    secondary, quota = fetch_secondary(args.symbol, quota)
    out_secondary = {
        "symbol": args.symbol,
        "secondary_available": secondary is not None,
        "fields": {k: {"value": _to_python(v)} for k, v in (secondary or {}).items()}
    }
    atomic_write_json(out_secondary, os.path.join(BASE, "data_raw_secondary.json"), indent=2)

if __name__ == "__main__":
    main()
