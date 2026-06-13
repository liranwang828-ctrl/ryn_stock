"""
统一轮询脚本 — 集成快照记录 + ATR止损建议 + RS双轨分析 + 盘初场景框架
用法：python3.12 agents/poll.py AAOI RKLB SNXX INTC [--lev AAOX:2]
"""
import os
os.environ["TZ"] = "America/New_York"
import sys, json, argparse, numpy as np, subprocess
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf
from stock_team.core.session_recorder import write_snapshot, log_action, log_thought
from stock_team.core.paper_trader import (
    try_enter, try_add_tranche, check_exits, get_status,
    eod_close_all, load_trade_history, ACCOUNTS
)

# Session manager 集成（可选，--session 时启用）
try:
    from stock_team.core.session_manager import push_alert as _push_alert
    _HAS_SESSION = True
except ImportError:
    _HAS_SESSION = False

def _session_push(type_, sym, msg, data, enabled=False):
    if enabled and _HAS_SESSION:
        try:
            _push_alert(type_, sym, msg, data)
        except Exception:
            pass

PYTHON = sys.executable

_REGIME_JSON = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "config", "market_regime.json")

def _load_market_regime() -> str:
    """读取盘前写入的 regime，5值枚举，不存在则返回 sideways"""
    try:
        if os.path.exists(_REGIME_JSON):
            d = json.load(open(_REGIME_JSON, encoding="utf-8"))
            r = d.get("regime", "sideways")
            if r in ("trending_up", "trending_down", "sideways", "volatile", "sector_hot"):
                return r
    except Exception:
        pass
    return "sideways"

PENDING_DEBATES = {}

def trigger_quick_debate(sym, a, spy_chg, qqq_chg, vix_cur, vix_dir, rs_streak=0):
    """异步触发 quick_debate.py，不阻塞轮询，且限制5分钟内不可重复触发以避免电脑卡死"""
    now_time = _time.time()
    if sym in PENDING_DEBATES and now_time - PENDING_DEBATES[sym] < 300:
        return
    PENDING_DEBATES[sym] = now_time
    data = {
        "cur":      a["cur"], "chg": a["chg"],
        "rs":       round(a["chg"]-spy_chg, 2),
        "rsi3":     a["rsi3"], "hist": a["hist"],
        "dvwap":    a["dvwap"], "vol": a["vol"],
        "hi":       a["hi"],  "lo":  a["lo"],
        "atr14":    a["atr14"],
        "spy_chg":  spy_chg, "qqq_chg": qqq_chg,
        "vix_cur":  vix_cur, "vix_dir": vix_dir,
        "rs_streak": rs_streak,
    }
    debate_script = os.path.join(os.path.dirname(__file__), "quick_debate.py")
    subprocess.Popen(
        [PYTHON, debate_script, sym, json.dumps(data)],
        cwd=((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

def read_quick_debate(sym):
    """读取上一轮辩论结果（如果存在且足够新）"""
    path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), f"quick_debate_{sym}.json")
    if not os.path.exists(path):
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
        # 只显示最近10分钟内的结果
        t_str = data.get("time", "")
        now   = datetime.now(timezone.utc)
        if t_str:
            from datetime import timedelta
            t_debate = datetime.strptime(
                now.strftime("%Y-%m-%d") + " " + t_str, "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
            if (now - t_debate).total_seconds() > 600:
                return None
        return data
    except Exception:
        return None

# 杠杆映射：底层标的 → 对应杠杆ETF
LEVERAGE_MAP = {}   # 运行时填入，如 {"AAOI": ("AAOX", 2)}

AAOX_COST = None    # 运行时填入持仓成本

# ── 数据采集 ─────────────────────────────────────────────
def _stooq_fallback(sym):
    """Stooq CSV fallback when yfinance fails"""
    import requests
    url = f"https://stooq.com/q/l/?s={sym.lower()}.us&f=sd2ohlcv&h&e=csv"
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            lines = r.text.strip().split('\n')
            if len(lines) >= 2:
                # Parse: sym, date, open, high, low, close, volume
                parts = lines[-1].split(',')
                return float(parts[4])  # close price
    except Exception:
        pass
    return None

# ── 内存缓存与限频架构 ──────────────────────────────────
import time as _time

GLOBAL_CACHE = {}

def _get_cached_history(ticker_obj, sym, key, period, interval=None, ttl=300):
    """获取并缓存 yfinance history"""
    now = _time.time()
    sym_cache = GLOBAL_CACHE.setdefault(sym, {})
    if key in sym_cache:
        cached_time, cached_val = sym_cache[key]
        if now - cached_time < ttl:
            return cached_val
    try:
        if interval:
            df = ticker_obj.history(period=period, interval=interval, timeout=3.0)
        else:
            df = ticker_obj.history(period=period, timeout=3.0)
        if getattr(df, "empty", False):
            if interval:
                df_retry = ticker_obj.history(period=period, interval=interval, timeout=3.0)
            else:
                df_retry = ticker_obj.history(period=period, timeout=3.0)
            if not getattr(df_retry, "empty", False):
                df = df_retry
    except Exception as e:
        if key in sym_cache:
            # 请求失败时，使用过期的缓存兜底
            return sym_cache[key][1]
        raise e
    sym_cache[key] = (now, df)
    return df

def _get_cached_info(ticker_obj, sym, ttl=14400):
    """获取并缓存 yfinance info，优先使用本地个股基本面胶囊以彻底消除网络阻塞和卡死风险"""
    now = _time.time()
    sym_cache = GLOBAL_CACHE.setdefault(sym, {})
    if "info" in sym_cache:
        cached_time, cached_val = sym_cache["info"]
        if now - cached_time < ttl:
            return cached_val
            
    # 优先读取本地数据胶囊 findings/fundamentals_{sym}.json，避免 yfinance 慢查询导致卡死
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
        fund_path = os.path.join(base_dir, "findings", f"fundamentals_{sym.upper()}.json")
        if os.path.exists(fund_path):
            import json
            with open(fund_path, "r", encoding="utf-8") as f:
                fund_data = json.load(f)
            local_info = {
                "targetMeanPrice": fund_data.get("target_price"),
                "fiftyTwoWeekHigh": fund_data.get("hi52"),
                "fiftyTwoWeekLow": fund_data.get("lo52"),
            }
            if local_info.get("fiftyTwoWeekHigh") is not None:
                sym_cache["info"] = (now, local_info)
                return local_info
    except Exception:
        pass

    try:
        # 本地缺失时的极简兜底
        info_dict = ticker_obj.info
    except Exception as e:
        if "info" in sym_cache:
            return sym_cache["info"][1]
        info_dict = {}
    sym_cache["info"] = (now, info_dict)
    return info_dict

def snap(sym, force_h1m=True):
    import pandas as pd
    t = yf.Ticker(sym)
    
    # 活跃标的或触发被动轮询时 ttl 设为 10 秒；其余复用缓存，ttl 设为 180 秒
    h1m_ttl = 10 if force_h1m else 180
    
    try:
        h1m = _get_cached_history(t, sym, "h1m", period="1d", interval="1m", ttl=h1m_ttl)
        h2d = _get_cached_history(t, sym, "h2d", period="5d", ttl=14400)
        h30 = _get_cached_history(t, sym, "h30", period="30d", ttl=14400)
    except Exception as e:
        # Try Stooq fallback
        fb = _stooq_fallback(sym)
        if fb is not None:
            print(f"[Stooq fallback] {sym} close=${fb:.2f}")
            return dict(
                sym=sym, cur=fb, lc=fb, hi=fb, lo=fb, vwap=fb,
                chg=0.0, dvwap=0.0, vol="─平", bars="─────",
                vr=0, vp=0, rsi3=50.0, hist=0.0, prev_hist=0.0,
                macd_cross=False, macd_fail=False, hi_time_mins=0,
                atr14=0.0, atr5=0.0, ma20=None, ma50=None, ma5=None, gain_10d=None,
                tgt_dev=None, h1m=None,
                rsi14_5m=50.0, vol_ratio_5m=1.0, bars5m="─", consec_green_5m=0,
                reversal_signals=[], reversal_score=0, reversal_mode=False,
            )
        return None

    if h1m is None or getattr(h1m, "empty", False) or h2d is None or getattr(h2d, "empty", False) or h30 is None or getattr(h30, "empty", False):
        fb = _stooq_fallback(sym)
        if fb is not None:
            return dict(
                sym=sym, cur=fb, lc=fb, hi=fb, lo=fb, vwap=fb,
                chg=0.0, dvwap=0.0, vol="-", bars="-----",
                vr=0, vp=0, rsi3=50.0, hist=0.0, prev_hist=0.0,
                macd_cross=False, macd_fail=False, hi_time_mins=0,
                atr14=0.0, atr5=0.0, ma20=None, ma50=None, ma5=None, gain_10d=None,
                tgt_dev=None, h1m=None,
                rsi14_5m=50.0, vol_ratio_5m=1.0, bars5m="鈹€", consec_green_5m=0,
                reversal_signals=[], reversal_score=0, reversal_mode=False,
            )
        return None

    lc   = float(h2d["Close"].iloc[-2]) if len(h2d) >= 2 else float(h1m["Close"].iloc[-1])
    cur  = float(h1m["Close"].iloc[-1])
    hi   = float(h1m["High"].max())
    lo   = float(h1m["Low"].min())
    vwap = (h1m["Close"]*h1m["Volume"]).sum() / h1m["Volume"].sum() if h1m["Volume"].sum() > 0 else cur
    # 日高形成时间（ET）
    _hi_idx = h1m["High"].idxmax()
    _hi_et  = _hi_idx.tz_convert("America/New_York")
    hi_time_mins = (_hi_et.hour - 9) * 60 + _hi_et.minute - 30  # 开盘后第几分钟
    vr   = h1m["Volume"].iloc[-3:].mean()
    vp   = h1m["Volume"].iloc[-6:-3].mean() if len(h1m)>=6 else vr
    vol  = "🔽缩" if vr<vp*0.75 else "🔼扩" if vr>vp*1.3 else "─平"
    vol_code = "shrink" if vr<vp*0.75 else "expand" if vr>vp*1.3 else "flat"
    bars = "".join("▲" if float(r["Close"])>=float(r["Open"]) else "▼"
                   for _,r in h1m.tail(5).iterrows())
    c = h1m["Close"]; d = c.diff()
    g = d.clip(lower=0).ewm(span=3,adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(span=3,adjust=False).mean()
    rsi3 = float((100-100/(1+g/l)).iloc[-1]) if not l.empty and (g.iloc[-1]+l.iloc[-1]) > 0 else 50.0
    e3 = c.ewm(span=3,adjust=False).mean()
    e8 = c.ewm(span=8,adjust=False).mean()
    hist = float((e3-e8).iloc[-1]-(e3-e8).ewm(span=5,adjust=False).mean().iloc[-1])
    prev = float((e3-e8).iloc[-2]-(e3-e8).ewm(span=5,adjust=False).mean().iloc[-2]) if len(h1m)>2 else hist

    # ATR (日线)
    if len(h30) >= 14:
        h30["HL"] = h30["High"] - h30["Low"]
        h30["HC"] = abs(h30["High"] - h30["Close"].shift(1))
        h30["LC"] = abs(h30["Low"]  - h30["Close"].shift(1))
        h30["TR"] = h30[["HL","HC","LC"]].max(axis=1)
        atr14 = float(h30["TR"].rolling(14).mean().iloc[-1])
        atr5  = float(h30["TR"].rolling(5).mean().iloc[-1])
    else:
        atr14 = atr5 = (hi - lo)

    # 均线 (日线)
    ma20 = float(h30["Close"].rolling(20).mean().iloc[-1]) if len(h30)>=20 else None
    ma50 = float(h30["Close"].rolling(50).mean().iloc[-1]) if len(h30)>=50 else None
    ma5  = float(h30["Close"].rolling(5).mean().iloc[-1]) if len(h30) >= 5  else None
    gain_10d = round((h30["Close"].iloc[-1] - h30["Close"].iloc[-11]) / h30["Close"].iloc[-11] * 100, 2) if len(h30) >= 11 else None

    info = _get_cached_info(t, sym, ttl=14400)
    tgt_dev  = (info.get("targetMeanPrice",cur)-cur)/cur*100 if info.get("targetMeanPrice") else None
    hi52w    = info.get("fiftyTwoWeekHigh")    # 52周高点（阻力参考）
    lo52w    = info.get("fiftyTwoWeekLow")     # 52周低点（支撑参考）
    prev_close = lc                            # 前日收盘（短期支撑/压力）
    # 相对结构位距离（正=在其上方，负=在其下方）
    dist_hi52w = round((cur - hi52w) / hi52w * 100, 1) if hi52w else None
    dist_lo52w = round((cur - lo52w) / lo52w * 100, 1) if lo52w else None

    # ── 5分钟K线指标 ─────────────────────────────────────────
    # RSI14 on 5-min bars
    try:
        h5m = _get_cached_history(t, sym, "h5m", period="5d", interval="5m", ttl=180)
        h5m_today = h5m[h5m.index.date == datetime.now().date()] if not h5m.empty else pd.DataFrame()
    except Exception:
        h5m_today = pd.DataFrame()
        
    if len(h5m_today) >= 14:
        d5 = h5m_today["Close"].diff()
        g5 = d5.clip(lower=0).ewm(span=14, adjust=False).mean()
        l5 = (-d5.clip(upper=0)).ewm(span=14, adjust=False).mean()
        rsi14_5m = float((100-100/(1+g5/l5)).iloc[-1]) if not l5.empty and (g5.iloc[-1]+l5.iloc[-1]) > 0 else 50.0
    else:
        rsi14_5m = 50.0
    # 量比：当前5分钟成交量 vs 过去20根5分钟均量
    if len(h5m_today) >= 3:
        # 用前一根完整K线的成交量，避免读未完成K线导致量比=0
        ref_vol = float(h5m_today["Volume"].iloc[-2]) if len(h5m_today) >= 2 else float(h5m_today["Volume"].iloc[-1])
        avg_5m_vol = float(h5m_today["Volume"].iloc[:-1].tail(20).mean()) if len(h5m_today) > 1 else ref_vol
        vol_ratio_5m = round(ref_vol / avg_5m_vol, 2) if avg_5m_vol > 0 else 1.0
    else:
        vol_ratio_5m = 1.0
    # 最近3根5分钟K线方向
    if len(h5m_today) >= 3:
        bars5m = "".join("▲" if float(r["Close"])>=float(r["Open"]) else "▼"
                         for _,r in h5m_today.tail(3).iterrows())
    else:
        bars5m = "─"
    # 连续绿色5分钟K线数量
    consec = 0
    for _,r in h5m_today.iloc[::-1].iterrows():
        if float(r["Close"]) >= float(r["Open"]):
            consec += 1
        else:
            break
    consec_green_5m = consec
    # 最近完整5分钟K线的涨跌幅（用于极端速度检测）
    if len(h5m_today) >= 2:
        _bar = h5m_today.iloc[-2]
        _bar_o = float(_bar["Open"])
        candle_drop_5m = round((float(_bar["Close"]) - _bar_o) / _bar_o, 4) if _bar_o != 0 else 0.0
    else:
        candle_drop_5m = 0.0

    # 反转入场信号（底部猎手模式）
    reversal_signals = []
    reversal_score = 0

    if len(h5m_today) >= 5:
        # 1. RSI14_5m 极端超卖
        if rsi14_5m < 25:
            reversal_signals.append(f"RSI14超卖({rsi14_5m:.0f})")
            reversal_score += 2
        elif rsi14_5m < 35:
            reversal_signals.append(f"RSI14偏低({rsi14_5m:.0f})")
            reversal_score += 1

        # 2. 量比萎缩（卖方枯竭）
        if vol_ratio_5m < 0.3:
            reversal_signals.append(f"量萎缩({vol_ratio_5m:.2f}x)")
            reversal_score += 2

        # 3. 价格不创新低（第二次测试守住）
        if len(h5m_today) >= 10:
            recent_lows = h5m_today["Low"].tail(10)
            cur_low = float(recent_lows.min())
            hist_low = float(h5m_today["Low"].min())
            cur_price = float(h5m_today["Close"].iloc[-1])
            if cur_price > hist_low * 1.005 and rsi14_5m < 40:
                reversal_signals.append("守低点")
                reversal_score += 2

        # 4. MACD 底背离
        if len(h5m_today) >= 10:
            c5 = h5m_today["Close"]
            e3_5 = c5.ewm(span=3, adjust=False).mean()
            e8_5 = c5.ewm(span=8, adjust=False).mean()
            macd5 = (e3_5 - e8_5)
            if macd5.iloc[-5:].mean() > macd5.iloc[-10:-5].mean() and float(c5.iloc[-1]) <= float(c5.iloc[-6]):
                reversal_signals.append("MACD底背离")
                reversal_score += 2

        # 5. 首根长下影线
        last_bar = h5m_today.iloc[-1]
        body = abs(float(last_bar["Close"]) - float(last_bar["Open"]))
        lower_wick = float(last_bar["Open"]) - float(last_bar["Low"]) if float(last_bar["Close"]) >= float(last_bar["Open"]) else float(last_bar["Close"]) - float(last_bar["Low"])
        if lower_wick > body * 1.5 and lower_wick > 0:
            reversal_signals.append("长下影线")
            reversal_score += 1

    # reversal_mode
    reversal_mode = reversal_score >= 4 and rsi14_5m < 40

    return dict(
        sym=sym, cur=cur, lc=lc, hi=hi, lo=lo, vwap=vwap,
        chg=(cur-lc)/lc*100 if lc > 0 else 0.0, dvwap=(cur-vwap)/vwap*100 if vwap > 0 else 0.0,
        vol=vol, vol_code=vol_code, bars=bars, vr=vr, vp=vp,
        rsi3=rsi3, hist=hist, prev_hist=prev,
        macd_cross=hist>0 and prev<=0,
        macd_fail=hist<0 and prev>0,
        hi_time_mins=hi_time_mins,
        atr14=atr14, atr5=atr5, ma20=ma20, ma50=ma50, ma5=ma5, gain_10d=gain_10d,
        tgt_dev=tgt_dev, h1m=h1m,
        hi52w=hi52w, lo52w=lo52w, prev_close=prev_close,
        dist_hi52w=dist_hi52w, dist_lo52w=dist_lo52w,
        rsi14_5m=rsi14_5m, vol_ratio_5m=vol_ratio_5m,
        bars5m=bars5m, consec_green_5m=consec_green_5m, candle_drop_5m=candle_drop_5m,
        reversal_signals=reversal_signals, reversal_score=reversal_score,
        reversal_mode=reversal_mode,
    )

def vix_snap():
    t = yf.Ticker("^VIX")
    try:
        h1m = _get_cached_history(t, "^VIX", "h1m", period="1d", interval="1m", ttl=10)
        h2d = _get_cached_history(t, "^VIX", "h2d", period="5d", ttl=14400)
    except Exception:
        return None
    if h1m.empty: return None
    cur = float(h1m["Close"].iloc[-1])
    lc  = float(h2d["Close"].iloc[-2]) if len(h2d)>=2 else cur
    vr = h1m["Close"].iloc[-3:].mean()
    vp = h1m["Close"].iloc[-6:-3].mean() if len(h1m)>=6 else vr
    trend = "↑升" if vr>vp*1.005 else "↓降" if vr<vp*0.995 else "→平"
    bars = "".join("▲" if float(r["Close"])>=float(r["Open"]) else "▼"
                   for _,r in h1m.tail(5).iterrows())
    return dict(cur=cur, lc=lc, chg=(cur-lc)/lc*100 if lc > 0 else 0.0, trend=trend, bars=bars)

# ── ATR止损建议 ────────────────────────────────────────────
def atr_stop_suggestion(a, spy_chg, lev=1):
    """
    根据方法论#8#9#10计算ATR止损建议
    返回：(止损价, 止损类型, 说明)
    """
    cur    = a["cur"]
    atr14  = a["atr14"]
    ma20   = a["ma20"]
    lo5    = a["lo"]           # 日内低点（近似5日低点）
    dvwap  = a["dvwap"]

    # 判断均线距离
    ma_dist = abs(cur - ma20) / cur * 100 if ma20 else 999

    if ma_dist < 5 and ma20:
        # 均线贴近，用均线止损
        buf = max(ma20*0.01, 0.5*atr14)
        base_stop = ma20 - buf
        stop_type = f"MA20止损"
        desc = f"MA20=${ma20:.1f} - 缓冲${buf:.1f}"
    elif ma_dist < 15 and ma20:
        # 结构止损（近期低点 + ATR缓冲）
        base_stop = lo5 - 0.5*atr14
        stop_type = "结构止损"
        desc = f"日低${lo5:.1f} - 0.5×ATR${0.5*atr14:.1f}"
    else:
        # 急涨股：VWAP止损
        vwap = a["vwap"]
        base_stop = vwap - 0.5*atr14
        stop_type = "VWAP止损"
        desc = f"VWAP${vwap:.1f} - 0.5×ATR${0.5*atr14:.1f}"

    # 反拥挤：止损加入噪声偏移（避整数位，±0.3-0.8%）
    import random
    noise = random.uniform(0.003, 0.008)
    actual_stop = base_stop * (1 - noise)

    # 对应杠杆ETF的止损
    lev_stop = actual_stop * lev if lev > 1 else None

    rr = None
    if a.get("tgt_dev") and a["tgt_dev"] > 0:
        potential_gain = cur * a["tgt_dev"] / 100
        potential_loss = cur - actual_stop
        if potential_loss > 0:
            rr = potential_gain / potential_loss

    return actual_stop, stop_type, desc, rr

def grade(rs):
    if rs>2: return "💪💪极强"
    if rs>0.5: return "💪强"
    if rs>-0.5: return "🟡中性"
    if rs>-2: return "🔴弱"
    return "🔴🔴极弱"

def grade_code(rs):
    """结构化 RS 强度枚举（用于统计分析，不依赖 emoji）
    very_strong | strong | neutral | weak | very_weak
    """
    if rs >  2.0: return "very_strong"
    if rs >  0.5: return "strong"
    if rs > -0.5: return "neutral"
    if rs > -2.0: return "weak"
    return "very_weak"

def quick_persona_score(a, spy_chg, qqq_chg, vix_cur, vix_dir, rs_streak=0):
    """
    三大师傅内嵌实时评分（0-10），同步运行无延迟
    返回 {persona: (score, one_liner)}
    """
    rs      = a["chg"] - spy_chg
    cur     = a["cur"]
    rsi3    = a["rsi3"]
    hist    = a["hist"]
    dvwap   = a["dvwap"]
    vol_str = "扩" in a["vol"]
    from_hi = (cur - a["hi"]) / a["hi"] * 100  # 距日高（负数）
    avg_mkt = (spy_chg + qqq_chg) / 2

    # ── Minervini：趋势/技术 ─────────────────────────────────
    ms = 0
    if rs > 3:     ms += 3
    elif rs > 1.5: ms += 2
    elif rs > 0:   ms += 1
    if hist > 0:              ms += 2
    if 40 <= rsi3 <= 72:      ms += 2
    if dvwap > 0:             ms += 2
    if vol_str:               ms += 1
    if rs_streak >= 3:        ms += 1  # 强趋势加分
    ms = min(10, max(0, ms))
    if ms >= 8:   m_line = f"RS{rs:+.1f}%+MACD{'正' if hist>0 else '负'}+趋势强，支持入场"
    elif ms >= 6: m_line = f"技术尚可，RS{rs:+.1f}%，等更强确认"
    elif ms >= 4: m_line = f"信号混合，当前不是最优入场"
    else:         m_line = f"技术弱势，RS{rs:+.1f}%，回避"

    # ── Marks：风险/情绪 ─────────────────────────────────────
    ks = 0
    if vix_cur < 17:            ks += 4
    elif vix_cur < 19:          ks += 3
    elif vix_cur < 22:          ks += 1
    else:                       ks -= 2
    if "降" in vix_dir:         ks += 2
    elif "升" in vix_dir:       ks -= 2
    if rsi3 < 70:               ks += 2
    elif rsi3 > 80:             ks -= 1
    if abs(from_hi) > 3:        ks += 2  # 距高点有空间
    elif abs(from_hi) < 1:      ks -= 1  # 贴高点风险高
    ks = min(10, max(0, ks))
    if ks >= 8:   k_line = f"VIX{vix_cur:.0f}{vix_dir}环境友好，风险可控"
    elif ks >= 6: k_line = f"VIX{vix_cur:.0f}中性，注意{'RSI偏高' if rsi3>70 else '盈亏比'}"
    elif ks >= 4: k_line = f"环境一般，仓位不宜过重"
    else:         k_line = f"VIX{vix_cur:.0f}{'上升' if '升' in vix_dir else '偏高'}，谨慎"

    # ── Druckenmiller：宏观/主题 ─────────────────────────────
    ds = 0
    if avg_mkt > 0.4:   ds += 3
    elif avg_mkt > 0:   ds += 2
    elif avg_mkt > -0.3: ds += 0
    else:               ds -= 2
    if rs > 5:          ds += 3
    elif rs > 2:        ds += 2
    elif rs > 0:        ds += 1
    if rs_streak >= 3:  ds += 2  # 连续强势=主题在发酵
    ds = min(10, max(0, ds))
    if ds >= 8:   d_line = f"大盘顺风{avg_mkt:+.1f}%+RS{rs:+.1f}%，主题行情强"
    elif ds >= 6: d_line = f"大盘{avg_mkt:+.1f}%中性，个股RS{rs:+.1f}%支撑"
    elif ds >= 4: d_line = f"大盘偏弱，个股需有独立催化剂"
    else:         d_line = f"宏观逆风{avg_mkt:+.1f}%，等大盘稳定"

    avg = (ms + ks + ds) / 3

    # ── 结构化字段（用于统计和机器学习，不依赖自然语言）────────
    def _verdict(score):
        """固定枚举：bullish/neutral/bearish，不随措辞变化"""
        if score >= 7: return "bullish"
        if score <= 3: return "bearish"
        return "neutral"

    # consensus_code 五值固定枚举，覆盖入场和退场两个决策：
    #   buy      → 积极入场/加仓（avg≥7）
    #   hold     → 观望，不入不出（avg 5-6）
    #   no_buy   → 不新建仓位，已有仓位可守（avg 3-4）
    #   not_sell → 不要恐慌离场，守住（avg 3-5 时对持仓方向的建议）
    #   sell     → 退出信号，建议减仓/止损（avg≤2）
    # 注意：no_buy ≠ sell（不推荐买入 ≠ 推荐卖出）
    if avg >= 7:
        consensus_code = "buy"
    elif avg >= 5:
        consensus_code = "hold"
    elif avg >= 3:
        consensus_code = "no_buy"      # 入场决策：不进
    elif avg >= 1.5:
        consensus_code = "not_sell"    # 退场决策：别慌，守住
    else:
        consensus_code = "sell"        # 退场决策：退出信号

    return {
        # 原有格式（兼容现有显示代码）
        "Minervini":      (ms, m_line),
        "Marks":          (ks, k_line),
        "Druckenmiller":  (ds, d_line),
        "avg":            round(avg, 1),
        "consensus": "🟢进" if avg >= 7 else "🟡等" if avg >= 5 else "🔴不进",
        # 新增结构化字段（用于统计分析，枚举值固定）
        "consensus_code": consensus_code,
        "verdicts": {
            "Minervini":     _verdict(ms),
            "Marks":         _verdict(ks),
            "Druckenmiller": _verdict(ds),
        },
    }

def pullback_diagnosis(stock_2m, qqq_2m):
    """
    判断个股回调性质：大盘驱动 vs 个股自身问题
    stock_2m: 个股近2分钟涨跌幅%
    qqq_2m:   QQQ近2分钟涨跌幅%
    返回 (diagnosis_label, action_hint)
    """
    if stock_2m >= -0.3:
        return None, None  # 没有明显回调，不诊断

    if qqq_2m < -0.1 and stock_2m < 0:
        amplify = stock_2m / qqq_2m if qqq_2m != 0 else 0
        if amplify > 15:
            return "📡Beta放大", "大盘微跌被放大，可关注企稳后入场"
        elif amplify > 5:
            return "🔗大盘联动", "跟随大盘下跌，等大盘稳定"
        else:
            return "⚠️大盘同跌", "与大盘同步下跌，等大盘反弹"
    elif qqq_2m >= 0 and stock_2m < -0.5:
        return "🔴个股抛压", "大盘平/涨但个股跌，是个股自身卖压，谨慎"
    elif qqq_2m > 0.1 and stock_2m < -1.0:
        return "🔴强个股抛压", "大盘在涨但个股大跌，主力出货信号，回避"
    else:
        return "🟡混合因素", "大盘平，个股轻微回调，关注方向"

# ── 盘初场景框架 ───────────────────────────────────────────
def classify_poll_symbols(symbols, real_positions=None, entry_decisions=None, focus_stocks=None):
    """Split symbols into active/passive polling buckets.

    Focus symbols stay active so today's dashboard focus gets frequent updates.
    """
    real_positions = real_positions or {}
    entry_decisions = entry_decisions or {}
    focus_set = {s.upper() for s in (focus_stocks or [])}

    active_syms = set()
    passive_syms = set()
    for sym in symbols:
        sym_u = sym.upper()
        is_held = sym_u in real_positions
        decision = entry_decisions.get(sym_u, {})
        decision_action = str(decision.get("action", "")).lower()
        is_watch = any(kw in decision_action for kw in ["enter", "watch", "鍙叆鍦?", "瑙傚療"])

        if is_held or is_watch or sym_u in focus_set:
            active_syms.add(sym_u)
        else:
            passive_syms.add(sym_u)

    return active_syms, passive_syms

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
_STOCK_BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
SCENARIO_PATH_TPL  = os.path.join(_STOCK_BASE, "opening_scenarios_{}.json")
PREMARKET_PATH_TPL = os.path.join(_STOCK_BASE, "premarket_analysis_{}.json")
_OBS_LOG = os.path.join(_STOCK_BASE, "learning", "observation_log.jsonl")

# ── 策略参数文件（回测优化目标）────────────────────────────────────────────
def _load_strategy_params():
    """从 config/tactical_rules.json 读取宏观/微观策略参数。"""
    path = os.path.join(_STOCK_BASE, "config", "tactical_rules.json")
    if os.path.exists(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
            return data.get("macro_strategy_params", {}), data.get("micro_strategy_params", {})
        except Exception:
            pass
    # 兼容退路：如果合并规则文件缺失，装载旧策略参数文件
    def _r(name):
        try:
            return json.load(open(os.path.join(_STOCK_BASE, "config", name), encoding="utf-8"))
        except Exception:
            return {}
    return _r("macro_strategy_params.json"), _r("micro_strategy_params.json")

_MACRO_P, _MICRO_P = _load_strategy_params()

def _load_entry_decision() -> dict:
    """
    读取今日 findings/entry_decision_{date}.json 的 decisions 字段。
    文件不存在或解析失败时返回 {} （向后兼容，所有标的按原逻辑处理）。
    """
    try:
        from datetime import datetime as _dt
        date_str = _dt.now().strftime("%Y-%m-%d")
        path     = os.path.join(_STOCK_BASE, "findings", f"entry_decision_{date_str}.json")
        if not os.path.exists(path):
            return {}
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("decisions", {})
    except Exception:
        return {}

# ── 股票形态（8种）+ 入场确认条件 ────────────────────────
PATTERNS = {
    "A": ("强势突破",    "🟢"),
    "B": ("VWAP回踩",   "🔵"),
    "C": ("横盘蓄力",   "🟡"),
    "D": ("冲高回落",   "🟠"),
    "E": ("弱势反弹",   "⚪"),
    "F": ("跳水下跌",   "🔴"),
    "G": ("板块强股弱", "🟣"),
    "H": ("独立领涨",   "💎"),
}

SCENE_ENTRY = {
    "A": {"watch": "放量突破日内高点",          "confirm": "量比>1.3x + 收盘站上压力位",       "sizing": "正常×1.5"},
    "B": {"watch": "回踩至VWAP ±1%",           "confirm": "缩量<0.8x + 3连阳 + 5分钟>0.3%", "sizing": "正常"},
    "C": {"watch": "区间上沿",                  "confirm": "量比>1.5x + 收盘突破上沿",         "sizing": "正常"},
    "D": {"watch": "日高回落>3%后止跌区",       "confirm": "量缩<0.8x + 3连阳 + 下影出现",    "sizing": "半仓"},
    "E": {"watch": "日低区间 ±1%",              "confirm": "下影出现 + 3连阳 + 量不放大",      "sizing": "1/4仓"},
    "F": {"watch": "不操作",                    "confirm": "等止跌信号再重新评估",              "sizing": "0"},
    "G": {"watch": "个股RS vs 板块转正时",      "confirm": "RS>0 + 3连阳 + 板块ETF仍强",      "sizing": "半仓"},
    "H": {"watch": "回踩VWAP或5分钟均线",       "confirm": "缩量 + 3连阳 + RS继续强于板块",   "sizing": "正常×1.5"},
}

def load_premarket(date_str):
    """读取盘前预测，返回 (stocks_dict, full_data)"""
    path = PREMARKET_PATH_TPL.format(date_str)
    if os.path.exists(path):
        data = json.load(open(path, encoding="utf-8"))
        return data.get("stocks", {}), data
    return {}, {}

def update_premarket_obs(date_str, sym, updates):
    """
    增量更新 premarket_analysis 中单只股票的观察期字段
    updates: dict，只合并非 None 的值
    """
    path = PREMARKET_PATH_TPL.format(date_str)
    if not os.path.exists(path):
        return
    try:
        data = json.load(open(path, encoding="utf-8"))
        if sym in data.get("stocks", {}):
            for k, v in updates.items():
                if v is not None:
                    data["stocks"][sym][k] = v
            json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    except Exception:
        pass

# ── 宏观环境（3级）──────────────────────────────────────
MACRO = {
    "UP":           "▲顺风",
    "NEUTRAL":      "─中性",
    "DOWN":         "▼逆风",
    # 新增 5值 regime（来自 market_regime.json）
    "trending_up":    "▲趋势向上",
    "trending_down":  "▼趋势向下",
    "sideways":       "─横盘震荡",
    "volatile":       "⚡高波动",
    "sector_hot":     "🔥板块轮动",
    "normal":         "─中性",
    "bull":           "▲偏多",
    "bear":           "▼偏空",
    "ai_bull":        "▲AI偏多",
}

# ── 策略矩阵：(形态, 宏观) → (操作, 仓位)────────────────
STRATEGY_MATRIX = {
    ("A","UP"):      ("积极入场，回踩VWAP可加仓",    "正常仓×1.5"),
    ("A","NEUTRAL"): ("入场，止损日低下方",          "正常仓"),
    ("A","DOWN"):    ("小仓试探，快进快出",           "半仓"),
    ("B","UP"):      ("VWAP处买，企稳后加仓",        "正常仓"),
    ("B","NEUTRAL"): ("VWAP小仓，等量能恢复",        "半仓"),
    ("B","DOWN"):    ("逆风下VWAP支撑不可靠，观望",   "不操作"),
    ("C","UP"):      ("等放量突破再入，突破前不动",    "等待"),
    ("C","NEUTRAL"): ("不操作，等方向",              "不操作"),
    ("C","DOWN"):    ("不操作，逆风横盘易跌",         "不操作"),
    ("D","UP"):      ("等回踩支撑企稳，不追高",       "观望"),
    ("D","NEUTRAL"): ("不追，警惕进一步下跌",         "不操作"),
    ("D","DOWN"):    ("回避，冲高回落+逆风=危险",      "不操作"),
    ("E","UP"):      ("弱反弹+顺风可小仓博弈",        "1/4仓"),
    ("E","NEUTRAL"): ("观望，动能太弱",              "不操作"),
    ("E","DOWN"):    ("不操作",                     "不操作"),
    ("F","UP"):      ("等止跌信号再看（MACD收窄）",   "不操作"),
    ("F","NEUTRAL"): ("不操作",                     "不操作"),
    ("F","DOWN"):    ("回避",                       "不操作"),
    ("G","UP"):      ("等补涨，板块强时可小仓介入",    "半仓等待"),
    ("G","NEUTRAL"): ("观望，等个股跟上板块",          "不操作"),
    ("G","DOWN"):    ("放弃，板块也会退潮",            "不操作"),
    ("H","UP"):      ("优先做多，龙头效应强",          "正常仓×1.5"),
    ("H","NEUTRAL"): ("做多，注意板块不跟时及时退",    "正常仓"),
    ("H","DOWN"):    ("小仓，独立行情持续性存疑",      "半仓"),
}

def market_minutes_open(et_h, et_m):
    """开盘后已过分钟数，盘前返回 None"""
    open_total = 9 * 60 + 30
    cur_total  = et_h * 60 + et_m
    if cur_total < open_total:
        return None
    return cur_total - open_total

def determine_macro(vix_data, spy_chg, qqq_chg):
    """
    宏观环境三级判断：▲顺风 / ─中性 / ▼逆风
    综合 VIX水平、VIX趋势、SPY/QQQ涨跌
    """
    if vix_data is None:
        return "NEUTRAL", "VIX数据缺失"

    vc    = vix_data["cur"]
    vt    = vix_data["trend"]   # "↑升" / "↓降" / "→平"
    avg   = (spy_chg + qqq_chg) / 2

    score = 0
    reasons = []

    # VIX水平
    if vc < 17:
        score += 2; reasons.append(f"VIX{vc:.0f}低位")
    elif vc < 20:
        score += 0; reasons.append(f"VIX{vc:.0f}中性")
    elif vc < 25:
        score -= 1; reasons.append(f"VIX{vc:.0f}偏高")
    else:
        score -= 3; reasons.append(f"VIX{vc:.0f}高危")

    # VIX趋势
    if vt == "↓降":
        score += 2; reasons.append("VIX下行")
    elif vt == "↑升":
        score -= 2; reasons.append("VIX上升⚠️")

    # 大盘方向
    if avg > 0.4:
        score += 2; reasons.append(f"大盘强{avg:+.1f}%")
    elif avg > 0:
        score += 1; reasons.append(f"大盘微涨{avg:+.1f}%")
    elif avg > -0.4:
        score -= 1; reasons.append(f"大盘微跌{avg:+.1f}%")
    else:
        score -= 2; reasons.append(f"大盘弱{avg:+.1f}%")

    if score >= 3:
        return "UP", " | ".join(reasons)
    elif score <= -1:
        return "DOWN", " | ".join(reasons)
    else:
        return "NEUTRAL", " | ".join(reasons)

def classify_pattern(a, spy_chg, sector_chg=None):
    """
    将单只股票分类为 A-H 8种形态
    sector_chg: 对应板块ETF的今日涨跌幅（用于判断G/H）
    返回 (code, confidence)
    """
    chg        = a["chg"]
    dvwap      = a["dvwap"]
    hist       = a["hist"]
    rs         = chg - spy_chg
    hi, lo, lc = a["hi"], a["lo"], a["lc"]
    vol_strong = "扩" in a["vol"]
    vol_weak   = "缩" in a["vol"]
    open_hi    = (hi - lc) / lc * 100
    pulled_bk  = open_hi - chg

    # G/H：板块对比（需要 sector_chg）
    if sector_chg is not None:
        rs_vs_sector = chg - sector_chg
        if sector_chg > 1.0 and rs_vs_sector < -1.0:
            return "G", "中"   # 板块强但个股落后
        if rs_vs_sector > 2.0 and rs > 1.5:
            conf = "高" if rs_vs_sector > 4 else "中"
            return "H", conf   # 个股显著领先板块

    # F：放量大跌
    if chg < -2.5 and rs < -2.0 and hist < 0:
        return "F", ("高" if chg < -5 else "中")

    # A：放量突破，RS强，MACD正，站VWAP上方
    if chg > 1.5 and vol_strong and rs > 1.0 and hist > 0 and dvwap > 0.3:
        return "A", ("高" if (chg > 3 and rs > 2) else "中")

    # D：冲高后从日高回落超过2%，且跌破VWAP
    if open_hi > 1.5 and pulled_bk > 2.0 and dvwap < -0.3:
        return "D", "中"

    # B：有涨幅，现价贴近VWAP（±0.6%），缩量
    if chg > 0.3 and abs(dvwap) < 0.6 and vol_weak:
        return "B", "中"

    # E：小幅反弹但动能弱（MACD仍负）
    if 0 < chg < 1.5 and hist < 0 and rs < 0:
        return "E", "中"

    # C：区间窄，无放量
    if (hi - lo) / lc * 100 < 1.5 and not vol_strong:
        return "C", "中"

    return "C", "低"

def load_daily_scenarios(date_str):
    path = SCENARIO_PATH_TPL.format(date_str)
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {}

def save_daily_scenarios(date_str, data):
    path = SCENARIO_PATH_TPL.format(date_str)
    json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def get_rs_streak(sym, saved, current_rs):
    """
    计算连续 RS > 1.5% 的轮询次数（强趋势检测）
    从 saved 里读历史 rs_streak，当前轮次更新
    """
    prev = saved.get(sym, {})
    prev_streak = prev.get("rs_streak", 0)
    prev_rs     = prev.get("chg", 0)  # 上一轮 RS 代理

    if current_rs > 1.5:
        return prev_streak + 1
    else:
        return 0  # 中断则重置

def render_opening_block(stocks, spy_chg, qqq_chg, vix_data, et_h, et_m,
                         sector_map=None):
    """
    盘初场景框架（三维：股票形态 × 宏观环境 × 板块强弱）
    - 前30分钟：观察期，禁止操作
    - 30分钟后：输出完整场景矩阵 + 策略建议
    - 后续轮询：标注场景漂移
    """
    mins     = market_minutes_open(et_h, et_m)
    date_str = datetime.now().strftime("%Y-%m-%d")

    if mins is None:
        print("【盘前】尚未开盘，等待 9:30 ET")
        print()
        return

    if mins < 30:
        remain = 30 - mins
        print(f"【盘初观察期 {mins:02d}/30 分钟】还剩 {remain} 分钟 → 禁止操作，只观察")
        # 观察期内也展示实时数据方便监控
        macro_state, macro_reason = determine_macro(vix_data, spy_chg, qqq_chg)
        _regime_file = _load_market_regime()
        if _regime_file != "sideways":
            macro_state = _regime_file
        print(f"  宏观预判：{MACRO[macro_state]}（{macro_reason}）")
        print()
        return

    # ── 宏观环境判断 ──────────────────────────────────────
    macro_state, macro_reason = determine_macro(vix_data, spy_chg, qqq_chg)
    _regime_file = _load_market_regime()
    if _regime_file != "sideways":
        macro_state = _regime_file
    macro_label = MACRO[macro_state]

    # ── 获取板块ETF数据 ──────────────────────────────────
    sector_snaps = {}
    if sector_map:
        unique_refs = {v["ref"] for v in sector_map.values() if "ref" in v}
        for ref in unique_refs:
            try:
                s = snap(ref)
                if s:
                    sector_snaps[ref] = s["chg"]
            except Exception:
                pass

    # ── 逐只分类 ─────────────────────────────────────────
    saved   = load_daily_scenarios(date_str)
    current = {}
    for sym, a in stocks.items():
        if not a:
            continue
        sec_ref  = (sector_map or {}).get(sym, {}).get("ref")
        sec_chg  = sector_snaps.get(sec_ref) if sec_ref else None
        rs_now   = round(a["chg"] - spy_chg, 2)
        streak   = get_rs_streak(sym, saved, rs_now)

        pat, conf = classify_pattern(a, spy_chg, sec_chg)

        # 强趋势豁免：RS连续≥3轮>1.5%，升级为H场景（独立领涨）
        strong_trend = streak >= 3 and rs_now > 1.5
        if strong_trend and pat not in ("F", "D"):
            pat  = "H"
            conf = f"强趋势{streak}轮"

        action, sizing = STRATEGY_MATRIX.get((pat, macro_state),
                                             ("观望", "不操作"))
        current[sym] = {
            "pattern": pat, "conf": conf, "macro": macro_state,
            "chg": round(a["chg"], 2),
            "sector_chg": round(sec_chg, 2) if sec_chg is not None else None,
            "action": action, "sizing": sizing,
            "rs_streak": streak,
            "strong_trend": strong_trend,
        }

    is_first = not saved
    if is_first:
        save_daily_scenarios(date_str, current)
        saved = current

    # ── 读取盘前预测 + 逐步回填观察期数据 ──────────────────
    premarket, _ = load_premarket(date_str)

    # 每轮更新盘前分析文件中的观察期字段
    for sym, a in stocks.items():
        if not a or sym not in premarket:
            continue
        pm = premarket[sym]
        vwap = a["vwap"]
        hi   = a["hi"]
        lo   = a["lo"]
        cur  = a["cur"]
        atr  = a["atr14"]

        updates = {
            "obs_minutes": mins,
            "vwap_current": round(vwap, 2),
            "opening_hi":   round(hi, 2),
            "opening_lo":   round(lo, 2),
            # watch_zone：基于当前真实VWAP动态计算
            "watch_zone": f"${round(vwap*0.99,2)}-${round(vwap*1.01,2)}（VWAP±1%，实时更新）",
        }
        # 第1轮（市场刚开盘≤3min）：记录真实开盘价和宏观状态
        if mins <= 3 and pm.get("actual_open") is None:
            updates["actual_open"]   = round(cur, 2)
            updates["macro_at_open"] = {
                "spy_chg": round(spy_chg, 2),
                "qqq_chg": round(qqq_chg, 2),
                "vix":     round(vix_data["cur"] if vix_data else 0, 1),
            }

        # 观察期结束（30分钟）：填充最终字段
        if mins >= 30 and not pm.get("obs_complete"):
            pat = current.get(sym, {}).get("pattern", "?")
            pred = pm.get("pred_scene", "?")
            entry_info = SCENE_ENTRY.get(pat, {})
            updates.update({
                "actual_scene":   pat,
                "obs_complete":   True,
                "pred_vs_actual": "✅吻合" if pat == pred else f"⚠️预测{pred}→实际{pat}",
                "entry_confirm":  f"[{pat}场景] {entry_info.get('confirm','—')}  "
                                  f"（VWAP实际=${round(vwap,2)}，区间${round(lo,2)}-${round(hi,2)}）",
                "sizing":         entry_info.get("sizing", "—"),
                "stop_basis":     f"VWAP${round(vwap,2)} - ATR${round(atr*0.3,2)}",
            })

        # ── 三节点状态追踪（替代30分钟后的pred_vs_actual对比）──
        # 节点来自 daily_checklist_{date}.json（如果存在），每轮poll都更新
        try:
            import json as _json
            _cl_path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")),
                                    f"daily_checklist_{date_str}.json")
            if os.path.exists(_cl_path):
                _cl = _json.load(open(_cl_path, encoding="utf-8"))
                _sym_cl = _cl.get("symbols", {}).get(sym, {})
                _n1 = _sym_cl.get("node1")  # 支撑节点
                _n2 = _sym_cl.get("node2")  # 怀疑节点
                _n3 = _sym_cl.get("node3")  # 突破节点
                if _n1 and _n2 and _n3:
                    # 判断当前价格的节点状态
                    if cur > _n3:
                        _node_state = "A"      # 突破确认
                    elif cur > _n1:
                        _node_state = "B"      # 论点区间
                    elif cur > _n2:
                        _node_state = "C_warn" # 论点警告
                    else:
                        _node_state = "C_confirm"  # 论点承压
                    updates["node_state"]  = _node_state
                    updates["node1_dist"]  = round((cur - _n1) / _n1 * 100, 2)
                    updates["node2_dist"]  = round((cur - _n2) / _n2 * 100, 2)
                    updates["node3_dist"]  = round((cur - _n3) / _n3 * 100, 2)
                    print(f"    [三节点] {sym}: 状态={_node_state}  "
                          f"N1距离={updates['node1_dist']:+.2f}%  "
                          f"N2距离={updates['node2_dist']:+.2f}%  "
                          f"N3距离={updates['node3_dist']:+.2f}%")
        except Exception:
            pass

        update_premarket_obs(date_str, sym, updates)

    # ── 输出 ─────────────────────────────────────────────
    tag = "首次评估 ✅" if is_first else f"更新（已开盘 {mins} 分钟）"
    print(f"【盘初场景 {tag}】")
    print(f"  宏观环境：{macro_label}  ({macro_reason})")
    print()

    order = {"H":0,"A":1,"B":2,"G":3,"C":4,"D":5,"E":6,"F":7}
    sorted_syms = sorted(current.keys(),
                         key=lambda s: order.get(current[s]["pattern"], 9))

    for sym in sorted_syms:
        c    = current[sym]
        pat  = c["pattern"]
        icon, pname = PATTERNS[pat]
        chg  = c["chg"]
        sc   = c["sector_chg"]
        sec_str = f"{sc:+.1f}%" if sc is not None else " N/A"

        prev_pat   = saved.get(sym, {}).get("pattern", pat)
        drift_flag = f" ⚡{prev_pat}→{pat}" if (prev_pat != pat and not is_first) else ""

        # 盘前预测对比
        pm = premarket.get(sym, {})
        pred = pm.get("pred_scene", "?")
        match_flag = "✅吻合" if pred == pat else (f"⚠️预测{pred}→实际{pat}" if pred != "?" else "")

        # 当前场景的入场确认条件
        entry_info = SCENE_ENTRY.get(pat, {})
        watch   = entry_info.get("watch", "—")
        confirm = entry_info.get("confirm", "—")
        sizing  = entry_info.get("sizing", c["sizing"])

        # 强趋势豁免：H场景入场条件降为5/6（豁免动量条件）
        streak     = c.get("rs_streak", 0)
        is_strong  = c.get("strong_trend", False)
        trend_tag  = f"  🔥强趋势{streak}轮→门槛降为5/6" if is_strong else ""
        if is_strong:
            confirm = "【强趋势豁免】" + confirm.replace("3连阳 + 5分钟涨>0.3% + ", "")

        print(f"  ┌─ {sym} {icon}{pname} [{c['conf']}]  {chg:>+5.1f}%  板块{sec_str}  {macro_label}{drift_flag}  {match_flag}{trend_tag}")
        print(f"  │  观察区: {watch}")
        print(f"  │  入场确认: {confirm}")
        print(f"  │  仓位: {sizing}  策略: {c['action']}")
        if pm.get("reasoning"):
            print(f"  │  盘前判断: {pm['reasoning']}")

        # ── 宏观策略结构位（30分钟后显示）────────────────────────────────
        if mins >= 30 and stocks.get(sym):
            _pop = compute_post_open_plan(sym, stocks[sym], spy_chg, et_h, et_m)
            _rec_icon = {"ENTER_ADD1":"🟢","WATCH_PULLBACK":"👀","WATCH_SIGNAL":"👀",
                         "HOLD":"⚪","DEFEND":"🟠","AVOID":"🔴","FREEZE_CATALYST":"📅"}.get(
                             _pop["entry_rec"], "•")
            print(f"  │  {_rec_icon} [{_pop['entry_rec']}] {_pop['entry_note']}")
            _lvls = _pop.get("key_levels", {})
            _lvl_str = " | ".join(
                f"{k}${v['price']:.0f}({v['dist_pct']:+.1f}%)"
                for k, v in list(_lvls.items())[:4]
            )
            if _lvl_str:
                print(f"  │  结构位: {_lvl_str}")
        print(f"  └")
        print()

    # 场景漂移汇总
    if not is_first:
        drifted = [(s, saved.get(s,{}).get("pattern","?"), current[s]["pattern"])
                   for s in current
                   if saved.get(s,{}).get("pattern") != current[s]["pattern"]]
        if drifted:
            print(f"  ⚡ 场景漂移：" + "  ".join(f"{s}({p0}→{p1})" for s,p0,p1 in drifted))
            print()
            # 场景漂移 → 自动回填 daily_plan
            for s, p0, p1 in drifted:
                try:
                    from stock_team.core.daily_plan import update_scene as _update_scene
                    today_date = datetime.now().strftime("%Y-%m-%d")
                    cur_vwap = stocks[s]["vwap"] if stocks.get(s) else None
                    _update_scene(s, actual_scene=p1, actual_vwap=cur_vwap, date_str=today_date)
                    print(f"  📋 daily_plan 已回填 {s}: actual_scene={p1}")
                except Exception:
                    pass

    if not premarket:
        print(f"  ℹ️  无盘前预测数据，运行 python3.12 agents/premarket.py 生成")
    print()

# ── 主轮询逻辑 ─────────────────────────────────────────────
def load_positions_mode():
    path = os.path.join(CFG_DIR if hasattr(sys.modules[__name__], 'CFG_DIR') else
                        os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "config"),
                        "positions_mode.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {}

def save_positions_mode(modes):
    path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "config", "positions_mode.json")
    json.dump(modes, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def check_mode_switch(sym, a, current_mode, et_h, et_m):
    """
    检查是否需要切换交易模式（swing ↔ intraday）
    返回 (new_mode, [触发原因]) 或 (current_mode, []) 表示无切换
    """
    reasons = []
    elapsed = (et_h - 9) * 60 + et_m - 30  # 开盘后分钟数

    if current_mode == "swing":
        # 信号1：日高在开盘30分钟内形成（观察期内见顶）
        hi_mins = a.get("hi_time_mins", 999)
        if 0 <= hi_mins <= 30 and elapsed > 30:
            reasons.append(f"日高在开盘{hi_mins}分钟内形成")
        # 信号2：RSI3极度超买 + MACD开始转负
        if a["rsi3"] > 90 and a["hist"] < 0:
            reasons.append(f"RSI3={a['rsi3']:.0f}超买+MACD转负")
        # 信号3：放量跌破VWAP
        if a["dvwap"] < -0.8 and "🔼扩" in a["vol"]:
            reasons.append(f"放量跌破VWAP({a['dvwap']:+.1f}%)")
        # 任意一个强信号 或 两个弱信号 → 切换
        if len(reasons) >= 2 or (reasons and "日高在" in reasons[0]):
            return "intraday", reasons

    elif current_mode == "intraday":
        # 信号：午后持续创新高 + RSI3健康
        if elapsed > 150:  # 12:00 PM 之后
            at_high = a["cur"] >= a["hi"] * 0.99
            healthy  = 50 < a["rsi3"] < 78
            if at_high and healthy and "🔽缩" in a["vol"]:
                reasons.append(f"午后仍在日高({a['rsi3']:.0f} RSI3)缩量走强")
                return "swing", reasons

    return current_mode, []

def qqq_5m_chg(qqq_data):
    """QQQ 近5分钟涨跌幅（方法论#11 门控用）"""
    if not qqq_data or qqq_data.get("h1m") is None: return 0.0
    h = qqq_data["h1m"]
    if len(h) < 6: return 0.0
    return float((h["Close"].iloc[-1] - h["Close"].iloc[-6]) / h["Close"].iloc[-6] * 100)

def _get_dynamic_thresholds(macro_state, vix_cur, vix_dir, et_h, et_m):
    """
    根据宏观状态×VIX环境动态计算入场阈值。
    大师圆桌 2026-05-15 共识矩阵。
    """
    # VIX环境分档
    if vix_cur < 18 or (vix_cur < 22 and vix_dir in ("↓降",)):
        vix_env = "friendly"
    elif vix_cur >= 25 and vix_dir == "↑升":
        vix_env = "hostile"
    else:
        vix_env = "neutral"

    # 基础矩阵 [rs_min, vol_min, rsi_min, consec_green]
    matrix = {
        ("ai_bull",   "friendly"): (1.0, 1.3, 45, 2),
        ("ai_bull",   "neutral"):  (1.5, 1.5, 50, 3),
        ("ai_bull",   "hostile"):  (2.5, 2.0, 55, 3),
        ("recovery",  "friendly"): (1.5, 1.5, 50, 3),
        ("recovery",  "neutral"):  (2.0, 1.8, 55, 3),
        ("recovery",  "hostile"):  (3.0, 2.5, 60, 4),
        ("normal",    "friendly"): (2.0, 1.8, 50, 3),
        ("normal",    "neutral"):  (2.5, 2.0, 55, 3),
        ("normal",    "hostile"):  (9.9, 9.9, 99, 99),  # 禁止
        ("bear",      "friendly"): (9.9, 9.9, 99, 99),  # 禁止
        ("bear",      "neutral"):  (9.9, 9.9, 99, 99),  # 禁止
        ("bear",      "hostile"):  (9.9, 9.9, 99, 99),  # 禁止
    }
    key = (macro_state, vix_env)
    rs_min, vol_min, rsi_min, consec_min = matrix.get(key, (2.0, 1.5, 50, 3))

    # 时间段调节
    mins_since_open = max(0, et_h * 60 + et_m - 9 * 60 - 30)
    if mins_since_open < 30:        # 开盘前30分钟
        rs_min   += 1.0
        vol_min  += 0.5
    elif 120 < mins_since_open < 180:  # 午盘低流动性
        vol_min  += 0.3

    return {
        "rs_min": rs_min, "vol_min": vol_min,
        "rsi_min": rsi_min, "consec_min": consec_min,
        "vix_env": vix_env,
    }

def _apply_adjustment_layer(base_thresh, sym, a, spy_chg, et_h, et_m, date_str=None):
    """
    Phase B 动态调节层：在基础阈值之上叠加5维调节。
    大师圆桌2026-05-16共识：时间段/VWAP位置/催化剂/CIO/RS趋势
    返回调节后的 thresh dict（和 base_thresh 格式相同）
    """
    import json as _json
    import os as _os
    _BASE = _((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
    if date_str is None:
        from datetime import datetime as _dt
        date_str = _dt.now().strftime("%Y-%m-%d")

    rs_adj  = 0.0   # RS门槛调节量（正=更严，负=更宽）
    vol_adj = 0.0   # 量比门槛调节量
    adj_log = []    # 调节原因记录

    # ── 1. 时间段调节 ────────────────────────────────────────
    mins_open = max(0, et_h * 60 + et_m - 9 * 60 - 30)
    if mins_open < 30:
        rs_adj  += 1.0
        vol_adj += 0.5
        adj_log.append(f"开盘{mins_open}min内+严")
    elif 150 <= mins_open <= 240:  # 12:00-14:30 午盘低流动性
        vol_adj += 0.3
        adj_log.append("午盘低流动+量")

    # ── 2. VWAP位置调节 ──────────────────────────────────────
    dvwap = a.get("dvwap", 0)
    if dvwap < -1.0:   # 价格在VWAP下方1%+（逆势做多）
        rs_adj += 1.0
        adj_log.append(f"VWAP下方{dvwap:.1f}%+严")
    elif dvwap > 2.0:  # 价格大幅高于VWAP（过热）
        vol_adj += 0.3
        adj_log.append(f"VWAP上方{dvwap:.1f}%+量")

    # ── 3. 催化剂强度调节 ────────────────────────────────────
    try:
        _pm_path = _os.path.join(_BASE, f"premarket_analysis_{date_str}.json")
        if _os.path.exists(_pm_path):
            _pm = _json.load(open(_pm_path, encoding="utf-8"))
            _cat = _pm.get("stocks", {}).get(sym, {}).get("catalyst_strength", 1)
            if _cat >= 3:
                rs_adj  = max(rs_adj  - 0.5, rs_adj  - 0.5)
                vol_adj = max(vol_adj - 0.2, vol_adj - 0.2)
                adj_log.append(f"催化剂★★★宽松")
            elif _cat <= 1:
                rs_adj  += 0.5
                adj_log.append(f"催化剂弱+严")
    except Exception:
        pass

    # ── 4. CIO信号调节 ──────────────────────────────────────
    try:
        _cio_path = _os.path.join(_BASE, "learning", f"cio_signals_{date_str}_{sym}.json")
        if _os.path.exists(_cio_path):
            _cio = _json.load(open(_cio_path, encoding="utf-8"))
            _sig  = _cio.get("signal", "neutral")
            _conf = _cio.get("confidence", 0)
            if _sig == "bullish" and _conf >= 65:
                rs_adj  -= 0.3
                vol_adj -= 0.1
                adj_log.append(f"CIO看涨{_conf}%宽松")
            elif _sig == "bearish":
                rs_adj  += 0.5
                adj_log.append("CIO看空+严")
    except Exception:
        pass

    # ── 5. RS趋势调节（从 opening_scenarios 读 rs_streak）────
    try:
        _sc_path = _os.path.join(_BASE, f"opening_scenarios_{date_str}.json")
        if _os.path.exists(_sc_path):
            _sc = _json.load(open(_sc_path, encoding="utf-8"))
            _streak = _sc.get(sym, {}).get("rs_streak", 0)
            if _streak >= 5:
                rs_adj  -= 0.3
                adj_log.append(f"RS连续强{_streak}轮宽松")
            elif _streak <= -5:
                rs_adj  += 0.5
                adj_log.append(f"RS连续弱{_streak}轮+严")
    except Exception:
        pass

    # ── 叠加上限限制 ─────────────────────────────────────────
    # 总调节不超过：RS±1.5%，量比±0.5x（防止过度调节）
    rs_adj  = max(-1.5, min(1.5, rs_adj))
    vol_adj = max(-0.5, min(0.5, vol_adj))

    result = {
        "rs_min":      round(base_thresh["rs_min"]  + rs_adj,  1),
        "vol_min":     round(base_thresh["vol_min"] + vol_adj, 1),
        "rsi_min":     base_thresh["rsi_min"],    # RSI不调节
        "consec_min":  base_thresh["consec_min"], # 连阳不调节
        "vix_env":     base_thresh["vix_env"],
        "adj_log":     adj_log,
        "rs_adj":      rs_adj,
        "vol_adj":     vol_adj,
    }
    return result

def _check_shrink_pullback(a) -> tuple:
    """
    缩量回踩验证：价格贴 MA5 + 成交量萎缩 + 乖离小。
    返回 (met: bool, reason: str)
    """
    cur  = a.get("cur", 0)
    ma5  = a.get("ma5")
    vr   = a.get("vol_ratio_5m", 1.0)

    if not ma5 or ma5 == 0:
        return False, "MA5数据不可用"

    ma5_dev  = abs(cur - ma5) / ma5 * 100
    price_ok = ma5_dev < 1.0
    vol_ok   = vr < 0.7
    dev_ok   = ma5_dev < 2.0

    met = price_ok and vol_ok and dev_ok
    reason = (
        f"✅ 缩量回踩（MA5偏离{ma5_dev:.1f}% 量比{vr:.2f}x）" if met else
        f"❌ 缩量回踩未满足（MA5偏离{ma5_dev:.1f}% 量比{vr:.2f}x，需<1%偏离+量比<0.7x）"
    )
    return met, reason

def _load_analyst_target(sym: str):
    """从 findings/fundamentals_{sym}.json 读取分析师目标价，失败返回 None"""
    _path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "findings", f"fundamentals_{sym.upper()}.json")
    try:
        if os.path.exists(_path):
            return json.load(open(_path, encoding="utf-8")).get("target_price")
    except Exception:
        pass
    return None

def _global_veto(a, vix_cur, vix_dir, qqq5m, macro_state, et_h, et_m):
    """
    全局否决：任一触发禁止当日一切新建/加仓操作。
    参数从 config/macro_strategy_params.json 读取。
    返回 veto_reason: str | None
    """
    gv   = _MACRO_P.get("market_regime", {})
    obs  = _MACRO_P.get("observation", {})
    _vix_panic = gv.get("vix_panic_threshold", 25)
    _qqq_drop  = gv.get("qqq5m_veto", -0.5)
    _ma_dev    = gv.get("ma20_dev_veto_pct", 10.0)
    _no_h      = obs.get("no_trade_after_et_h", 15)
    _no_m      = obs.get("no_trade_after_et_m", 30)

    if vix_cur and vix_cur > _vix_panic and vix_dir == "↑升":
        return f"VIX>{vix_cur:.0f} 且↑升，市场恐慌模式"
    if macro_state == "bear":
        return "宏观 Regime = bear，禁止新建/加仓"
    if et_h * 60 + et_m >= _no_h * 60 + _no_m:
        return f"尾盘（{_no_h}:{_no_m:02d}后）禁止新建仓位"
    if qqq5m is not None and qqq5m < _qqq_drop:
        return f"QQQ 5分钟 {qqq5m:+.2f}% 急跌"
    ma20 = a.get("ma20"); cur = a.get("cur", 0)
    if ma20 and ma20 > 0 and (cur - ma20) / ma20 * 100 > _ma_dev:
        return f"MA20 乖离率 {(cur-ma20)/ma20*100:.1f}%（>{_ma_dev}%，均值回归风险极高）"
    return None


# ── 场景含义表 ────────────────────────────────────────────────────────────
_SCENE_META = {
    "A": ("顺风", "放量突破 + RS强 + MACD正 + VWAP上方",   "high"),
    "H": ("顺风", "个股显著领先板块（+2%以上）",              "high"),
    "B": ("观望", "贴 VWAP 缩量，等待方向确认",              "medium"),
    "C": ("中性", "区间震荡，无明确方向",                    "low"),
    "E": ("弱势", "小幅反弹但 MACD 仍负、RS 负",            "low"),
    "D": ("逆风", "冲高回落 >2%，跌破 VWAP，分销特征",      "none"),
    "F": ("逆风", "放量大跌（>2.5%），论点需重新评估",       "none"),
    "G": ("逆风", "板块强但个股弱（跑输板块>1%），选股劣势", "none"),
}


def compute_post_open_plan(sym, a, spy_chg, et_h, et_m):
    """
    开盘30分钟后生成当日战术入场计划。
    整合：场景分类 × 宏观策略结构价位 × 全局 veto × 52周结构。
    返回 dict，写入 post_open_adj。
    """
    macro_nodes = _load_macro_nodes(sym)
    add1        = (macro_nodes.get("add1") or {})
    tp1         = (macro_nodes.get("tp1") or {})
    sd          = (macro_nodes.get("scenario_downgrade") or {})
    cat_fw      = (macro_nodes.get("catalyst_framework") or {})
    cat_window  = cat_fw.get("pre_reduce_active", False)

    cur       = a.get("cur", 0)
    hi52w     = a.get("hi52w")
    lo52w     = a.get("lo52w")
    ma50      = a.get("ma50")
    ma20      = a.get("ma20")
    add1_p    = add1.get("price")
    tp1_p     = tp1.get("price")
    b2b_p     = (sd.get("bull_to_base") or {}).get("price")  # 情景降级警戒线

    scene, conf = classify_pattern(a, spy_chg)
    ctx_label, ctx_reason, entry_quality = _SCENE_META.get(scene, ("未知", "", "low"))

    # ── 结构位分析 ──────────────────────────────────────────────
    levels = {}
    if add1_p:
        levels["Add1支撑"] = (add1_p, round((cur - add1_p) / cur * 100, 1))
    if tp1_p:
        levels["TP1阻力"] = (tp1_p, round((tp1_p - cur) / cur * 100, 1))
    if b2b_p:
        levels["降级警戒"] = (b2b_p, round((cur - b2b_p) / cur * 100, 1))
    if ma50:
        levels["MA50"] = (ma50, round((cur - ma50) / cur * 100, 1))
    if hi52w:
        levels["52W高"] = (hi52w, round((cur - hi52w) / hi52w * 100, 1))
    if lo52w:
        levels["52W低"] = (lo52w, round((cur - lo52w) / lo52w * 100, 1))

    # ── 入场建议逻辑 ────────────────────────────────────────────
    _ep   = _MACRO_P.get("entry_plan", {})
    _add1_tol  = _ep.get("add1_tolerance_pct", 2.0) / 100
    _add1_high = _ep.get("add1_high_dist_pct", 5.0) / 100
    _sd_warn   = _MACRO_P.get("scenario_downgrade", {}).get("warn_within_pct", 2.0) / 100

    if cat_window:
        rec = "FREEZE_CATALYST"
        note = f"催化剂窗口期（前3天），禁止新建/加仓，等结果后重新评估"
    elif entry_quality == "none":
        rec = "AVOID"
        note = f"场景{scene}({ctx_label}): {ctx_reason}，当日不操作"
    elif b2b_p and cur < b2b_p * (1 + _sd_warn):
        rec = "DEFEND"
        note = f"现价${cur:.2f} 接近/跌破情景降级线${b2b_p:.2f}，先守止损，不加仓"
    elif add1_p and cur <= add1_p * (1 + _add1_tol) and entry_quality in ("high", "medium"):
        rec = "ENTER_ADD1"
        note = (f"场景{scene}({ctx_label}) + 价格在Add1支撑${add1_p:.2f}附近"
                f"（±{abs(round((cur-add1_p)/cur*100,1))}%），"
                f"等缩量确认后可加仓/入场")
    elif add1_p and cur > add1_p * (1 + _add1_high) and entry_quality == "high":
        rec = "WATCH_PULLBACK"
        note = (f"场景{scene}(顺风)但价格比Add1支撑高{round((cur-add1_p)/cur*100,1)}%，"
                f"等回踩 Add1${add1_p:.2f} 再加")
    elif entry_quality == "high" and (not add1_p):
        rec = "WATCH_SIGNAL"
        note = f"场景{scene}(顺风)但无宏观策略节点，等Flex信号确认"
    else:
        rec = "HOLD"
        note = f"场景{scene}({ctx_label})，维持现仓，无操作信号"

    return {
        "scene":          scene,
        "scene_label":    ctx_label,
        "scene_reason":   ctx_reason,
        "entry_rec":      rec,
        "entry_note":     note,
        "key_levels":     {k: {"price": v[0], "dist_pct": v[1]} for k, v in levels.items()},
        "catalyst_window": cat_window,
        "computed_at_mins": et_h * 60 + et_m - 9 * 60 - 30,  # 开盘后分钟数
    }


def strategy_gate(a, spy_chg, vix_cur, vix_dir, qqq5m, macro_state="normal", et_h=10, et_m=0, sym=""):
    """
    方法论 #6/#11 策略门控
    返回 (passed, n_required, checks_dict, block_reason)
    """
    # ── 乖离率过滤（追涨防护，三档处理）──────────────────────
    cur  = a.get("cur", 0)
    ma20 = a.get("ma20")
    _ma_veto  = None
    _ma_warn  = ""
    _ma_dev   = 0.0
    if ma20 and ma20 > 0:
        _ma_dev = (cur - ma20) / ma20 * 100
        if _ma_dev > 10:
            _ma_veto = f"乖离率{_ma_dev:.1f}%严重超出（>10%均值回归风险）"
        elif _ma_dev > 5:
            _ma_veto = f"乖离率{_ma_dev:.1f}%禁止追高（>5%上限）"
        elif _ma_dev > 2:
            _ma_warn = f"⚠️ 乖离率{_ma_dev:.1f}%偏高，建议小仓"
    if _ma_veto:
        return False, 0, {"乖离率": (False, f"{_ma_dev:.1f}%")}, _ma_veto, {}

    rs     = a["chg"] - spy_chg
    rsi3   = a["rsi3"]
    hist   = a["hist"]
    n_req  = 5 if vix_cur >= 18 else 3   # #6: VIX18-20→N=5

    # ── 黄金否决权（任一触发=禁止）──────────────────────────
    gold_veto = None
    if vix_cur > 25 and vix_dir == "↑升":
        gold_veto = f"VIX>{vix_cur:.0f}且↑升"
    elif macro_state == "bear":
        gold_veto = "宏观regime=bear"
    elif et_h * 60 + et_m >= 15 * 60 + 30:
        gold_veto = "尾盘禁止新建仓（15:30后）"
    if gold_veto:
        return False, 0, {}, gold_veto

    # ── 动态阈值 ────────────────────────────────────────────
    thresh = _get_dynamic_thresholds(macro_state, vix_cur, vix_dir, et_h, et_m)
    # Phase B：动态调节层
    thresh = _apply_adjustment_layer(thresh, sym, a, spy_chg, et_h, et_m)
    rs_min     = thresh["rs_min"]
    vol_min    = thresh["vol_min"]
    rsi_min    = thresh["rsi_min"]
    consec_min = thresh["consec_min"]

    checks = {
        f"RS>{rs_min:.1f}%":     (rs > rs_min,            f"RS{rs:+.1f}%"),
        "MACD>0":                 (hist > 0,               f"MACD{hist:+.3f}"),
        f"RSI14_5m≥{rsi_min}":  (a.get("rsi14_5m", 50) >= rsi_min,
                                   f"RSI14_5m={a.get('rsi14_5m', 50):.0f}"),
        f"连阳≥{consec_min}根":  (a.get("consec_green_5m", 0) >= consec_min,
                                   f"连阳{a.get('consec_green_5m', 0)}根"),
        f"量比≥{vol_min:.1f}x":  (a.get("vol_ratio_5m", 1.0) >= vol_min,
                                   f"量比{a.get('vol_ratio_5m', 1.0):.2f}x"),
        "VIX方向":               (vix_dir in ("→平", "↓降"), vix_dir),
        "QQQ5m≥thresh":          (qqq5m >= -0.1, f"QQQ5m{qqq5m:+.2f}%"),
    }
    passed = all(v for v, _ in checks.values())

    # #11 绝对禁止加仓（任一触发→block）
    block = None
    if qqq5m < -0.5:  block = f"QQQ5分钟{qqq5m:+.2f}%急跌"
    elif rsi3 < 35:   block = f"RSI3={rsi3:.0f}动能崩溃"

    return passed, n_req, checks, block, thresh

def fmt_gate(checks, passed, n_req, block, thresh=None):
    ok = "✅" if passed else "❌"
    parts = []
    for name, (v, val) in checks.items():
        parts.append(f"{'✅' if v else '❌'}{name}({val})")
    status = f"🔴禁止:{block}" if block else (f"🟢通过[需{n_req}次连续]" if passed else "🟡未通过")
    status_line = f"  │ 【#6/#11门控】{status}  " + "  ".join(parts)
    if thresh and thresh.get("adj_log"):
        adj_str = " | ".join(thresh["adj_log"])
        return status_line + f"\n  │ 【调节层】{adj_str}  RS实际阈值{thresh['rs_min']:.1f}%  量比实际{thresh['vol_min']:.1f}x"
    return status_line


def check_flex_signals(a, spy_chg, et_h, et_m,
                       position=None, portfolio_total=None, sym=None):
    """
    检测 Flex 仓位的触发条件（超买减/超卖加）。
    三层联合判断：技术面 + 价格层（vs成本/分析师目标）+ 组合配置层（当前占比 vs target）

    position: positions.json 中该标的的 dict（含 target_pct/min_pct/max_pct/cost/shares）
    portfolio_total: 当前组合总市值（含现金），用于计算占比

    返回: {"flex_reduce": bool, "flex_add": bool,
           "reduce_score": int, "add_score": int,
           "reduce_checks": dict, "add_checks": dict,
           "alloc_pct": float, "alloc_vs_target": str}
    """
    # 时间窗口检查（从 micro_strategy_params 读取）
    _fs_p = _MICRO_P.get("flex_signals", {})
    _tw_start = _fs_p.get("time_window_start_h", 10)
    _tw_end   = _fs_p.get("time_window_end_h", 15)
    in_window = _tw_start <= et_h <= _tw_end

    cur   = a.get("cur", 0)
    rsi14 = a.get("rsi14_5m", 50)
    dvwap = a.get("dvwap", 0)
    vol_r = a.get("vol_ratio_5m", 1.0)
    macd_top_div = a.get("macd_fail", False)
    macd_bot_div = a.get("macd_cross", False)

    # ── 组合配置层 ────────────────────────────────────────────
    alloc_pct       = 0.0
    alloc_vs_target = "未知"
    price_ok_reduce = True   # 默认：不限制减仓
    price_ok_add    = True   # 默认：不限制加仓
    over_max        = False
    under_min       = False

    if position and portfolio_total and portfolio_total > 0 and cur > 0:
        shares         = int(position.get("shares", 0))
        cost           = float(position.get("cost", cur))
        target_pct     = float(position.get("target_pct", 5.0))
        min_pct        = float(position.get("min_pct", 2.0))
        max_pct        = float(position.get("max_pct", 10.0))
        analyst_target = None
        try:
            _fp = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "findings",
                               f"fundamentals_{a.get('sym','').upper()}.json")
            if os.path.exists(_fp):
                analyst_target = json.load(open(_fp, encoding="utf-8")).get("target_price")
        except Exception:
            pass

        alloc_pct   = cur * shares / portfolio_total * 100
        over_max    = alloc_pct > max_pct
        under_min   = alloc_pct < min_pct

        if alloc_pct > target_pct + 1:
            alloc_vs_target = f"超配{alloc_pct:.1f}%>{target_pct}%"
        elif alloc_pct < target_pct - 1:
            alloc_vs_target = f"欠配{alloc_pct:.1f}%<{target_pct}%"
        else:
            alloc_vs_target = f"正常{alloc_pct:.1f}%≈{target_pct}%"

        # 减仓价格条件：至少盈利10% OR 已超过分析师目标价90%
        profit_pct = (cur - cost) / cost * 100 if cost > 0 else 0
        price_ok_reduce = (profit_pct >= 10.0 or
                           (analyst_target and cur >= analyst_target * 0.90))

        # 加仓价格条件：优先用宏观策略 add1.price（TA支撑位），fallback 成本×1.05
        thesis_intact = position.get("thesis_status", "intact") == "intact"
        _macro_add1_price = None
        _cat_window_active = False
        if sym:
            _mn = _load_macro_nodes(sym)
            _macro_add1_price = (_mn.get("add1") or {}).get("price")
            _cat_window_active = (_mn.get("catalyst_framework") or {}).get("pre_reduce_active", False)
        if _macro_add1_price:
            # 在 add1 支撑位 ±2% 内 + 论点完好
            price_ok_add = (cur <= _macro_add1_price * 1.02) and thesis_intact
        else:
            price_ok_add = (cur <= cost * 1.05) and thesis_intact

    # ── 技术面检测（阈值从 micro_strategy_params 读取）────────────────────
    _rsi_ob  = _fs_p.get("rsi14_5m_overbought", 75)
    _rsi_os  = _fs_p.get("rsi14_5m_oversold",   35)
    _vwap_r  = _fs_p.get("vwap_reduce_threshold", 1.5)
    _vwap_a  = _fs_p.get("vwap_add_threshold",   -1.5)
    _vol_ex  = _fs_p.get("vol_ratio_expand",      1.3)
    _vol_sh  = _fs_p.get("vol_ratio_shrink",      0.7)
    _min_sig = _fs_p.get("min_signals_required",  3)

    reduce_checks = {
        f"RSI14>{_rsi_ob}": rsi14 > _rsi_ob,
        f"VWAP+{_vwap_r}%": dvwap > _vwap_r,
        "量放大":            vol_r > _vol_ex,
        "MACD顶背离":        macd_top_div,
    }
    add_checks = {
        f"RSI14<{_rsi_os}": rsi14 < _rsi_os,
        f"VWAP{_vwap_a}%":  dvwap < _vwap_a,
        "量萎缩":            vol_r < _vol_sh,
        "MACD底背离":        macd_bot_div,
    }
    reduce_score = sum(1 for v in reduce_checks.values() if v)
    add_score    = sum(1 for v in add_checks.values() if v)

    flex_reduce = (in_window and reduce_score >= _min_sig
                   and price_ok_reduce
                   and (over_max or alloc_pct > float(position.get("target_pct", 5)) + 1
                        if position else True))

    flex_add = (in_window and add_score >= _min_sig
                and price_ok_add
                and not _cat_window_active
                and (under_min or alloc_pct < float(position.get("target_pct", 5)) - 1
                     if position else True))

    return {
        "flex_reduce":    flex_reduce,
        "flex_add":       flex_add,
        "reduce_score":   reduce_score,
        "add_score":      add_score,
        "reduce_checks":  reduce_checks,
        "add_checks":     add_checks,
        "in_window":      in_window,
        "alloc_pct":      round(alloc_pct, 1),
        "alloc_vs_target": alloc_vs_target,
        "price_ok_reduce": price_ok_reduce,
        "price_ok_add":    price_ok_add,
    }

# ── 持仓论点健康度 ─────────────────────────────────────────

POSITIONS_PATH = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "config", "positions.json")

def load_real_positions():
    """读取真实持仓（config/positions.json）"""
    if not os.path.exists(POSITIONS_PATH):
        return {}
    try:
        data = json.load(open(POSITIONS_PATH, encoding="utf-8"))
        return data.get("positions", {})
    except Exception:
        return {}


def load_plan_for_sym(sym):
    """读取 daily_plan_{date}.json 中该标的的止损/目标价"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    plan_path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")),
                             f"daily_plan_{date_str}.json")
    if not os.path.exists(plan_path):
        return None
    try:
        plan = json.load(open(plan_path, encoding="utf-8"))
        return plan.get("stocks", {}).get(sym)
    except Exception:
        return None


def _load_company_profile(sym):
    """读取 knowledge/company_profiles.json 中的公司基本面信息"""
    try:
        cp = os.path.join(_STOCK_BASE, "knowledge", "company_profiles.json")
        if os.path.exists(cp):
            return json.load(open(cp, encoding="utf-8")).get(sym, {})
    except Exception:
        pass
    return {}


def master_thesis_judgment(sym, a, spy_chg, diag_label):
    """
    持仓个股出现异常回调时，大师判断：大盘压力 vs 论点变化。
    使用 company_profiles.json (论点) + premarket (催化剂强度+板块) 综合判断。
    返回格式化行列表，供 print 直接调用。
    """
    rs    = round(a["chg"] - spy_chg, 2)
    today = datetime.now().strftime("%Y-%m-%d")

    profile          = _load_company_profile(sym)
    thesis           = profile.get("thesis", profile.get("one_liner", ""))
    catalyst_strength = 1
    sector_gap        = 0.0
    try:
        pm = os.path.join(_STOCK_BASE, f"premarket_analysis_{today}.json")
        if os.path.exists(pm):
            pd_ = json.load(open(pm, encoding="utf-8")).get("stocks", {}).get(sym, {})
            catalyst_strength = pd_.get("catalyst_strength", 1)
            sector_gap        = pd_.get("sector_gap", 0.0)
    except Exception:
        pass

    indiv = diag_label in ("🔴个股抛压", "🔴强个股抛压")

    # Livermore: 价格行为
    if indiv and spy_chg > 0 and rs < -1.5:
        liv = ("⚠️论点动摇", f"大盘正收益但RS{rs:.1f}%，主力在退出")
    elif sector_gap < -1.5:
        liv = ("📡大盘压力", f"板块今日{sector_gap:+.1f}%拖累，非个股独立问题")
    else:
        liv = ("🟡混合", f"RS{rs:.1f}%，等更多价格确认")

    # Marks: 催化剂/论点完整性
    if catalyst_strength >= 3 and indiv:
        marks = ("📡大盘压力", f"催化剂★★★仍有效，回调是情绪非基本面")
    elif catalyst_strength <= 1 and rs < -1.5:
        marks = ("⚠️论点动摇", f"催化剂弱({catalyst_strength}/3)+个股跌，检查持仓理由")
    else:
        marks = ("🟡守止损", f"催化剂中等({catalyst_strength}/3)，守止损观察")

    # Druckenmiller: 宏观+板块
    if spy_chg < -0.5:
        druck = ("📡大盘压力", f"SPY{spy_chg:+.1f}%，宏观整体偏弱")
    elif indiv and rs < -2:
        druck = ("⚠️论点检查", f"大盘不弱但RS{rs:.1f}%，检查论点是否改变")
    else:
        druck = ("📡大盘压力", f"整体宏观环境制约，等方向")

    stances = [liv[0], marks[0], druck[0]]
    if stances.count("⚠️论点动摇") >= 2 or "⚠️论点检查" in stances:
        verdict, icon = "论点可能动摇 — 考虑减仓或重新评估", "🔴"
    elif stances.count("📡大盘压力") >= 2:
        verdict, icon = "大盘压力为主 — 守止损，不追杀", "🟡"
    else:
        verdict, icon = "信号混合 — 密切观察，守止损", "🟡"

    lines = [f"│ 🧠大师判断[大盘vs论点] {icon} {verdict}"]
    if thesis:
        lines.append(f"│   持仓论点: {thesis[:58]}")
    lines.append(f"│   Livermore:{liv[0]}  {liv[1][:46]}")
    lines.append(f"│   Marks    :{marks[0]}  {marks[1][:46]}")
    lines.append(f"│   Druck    :{druck[0]}  {druck[1][:46]}")
    return lines


def _load_macro_nodes(sym: str) -> dict:
    """读取 macro_strategy_{sym}.json 的 nodes 字段"""
    try:
        path = os.path.join(_STOCK_BASE, f"macro_strategy_{sym.upper()}.json")
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8")).get("nodes", {})
    except Exception:
        pass
    return {}


def _load_premarket_thesis(sym: str) -> dict:
    """读取今日 premarket_summary 的 thesis 字段（含论点监控层数据）"""
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(_STOCK_BASE, "findings",
                            f"premarket_summary_{date_str}_{sym.upper()}.json")
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8")).get("thesis") or {}
    except Exception:
        pass
    return {}


def evaluate_thesis_health(sym, a, spy_chg, position, stocks=None):
    """
    评估持仓论点健康度。
    position: {"cost": float, "shares": int, ...}
    返回: {"status": "intact"|"weakening"|"broken",
            "signals": [...], "action": str,
            "rr_ratio": float, "stop": float, "t1_target": float, "gain_pct": float}
    """
    cost    = float(position["cost"])
    shares  = int(position.get("shares", 0))
    cur     = a["cur"]
    gain_pct = (cur - cost) / cost * 100

    # ── 读取宏观策略精确节点（优先于 daily_plan 的估算值）──────────
    macro_nodes   = _load_macro_nodes(sym)
    pm_thesis     = _load_premarket_thesis(sym)

    # 止损：macro_strategy dynamic_stop > daily_plan > ATR 估算
    ds_price = (macro_nodes.get("dynamic_stop") or {}).get("price")
    plan     = load_plan_for_sym(sym)
    hard_stop = (ds_price
                 or (plan["stop"] if plan and plan.get("stop") else None)
                 or round(cost - a["atr14"] * 0.3, 2))
    soft_stop = cost

    signals = []

    # 板块联动止损收紧
    if stocks:
        try:
            from agents.sector_leadership import get_adjusted_stop_multiplier
            multiplier = get_adjusted_stop_multiplier(sym, stocks)
            if multiplier < 1.0:
                orig_dist = cost - hard_stop
                if orig_dist > 0:
                    old_hard_stop = hard_stop
                    hard_stop = round(cost - (orig_dist * multiplier), 2)
                    signals.append(f"⚠️ 板块风险收紧：龙头破位，个股止损由 ${old_hard_stop:.2f} 收紧至 ${hard_stop:.2f} (收紧系数 {multiplier})")
        except Exception:
            pass

    # 目标价：macro_strategy tp1 > daily_plan > 成本+3%
    tp1_price = (macro_nodes.get("tp1") or {}).get("price")
    tp2_price = (macro_nodes.get("tp2") or {}).get("price")
    t1_tgt = (tp1_price
              or (plan["t1_target"] if plan and plan.get("t1_target") else None)
              or round(cost * 1.03, 2))
    t2_tgt = (tp2_price
              or (plan["t2_target"] if plan and plan.get("t2_target") else None)
              or round(cost * 1.06, 2))
    stop = hard_stop

    # 情景降级价位（来自 premarket_summary 或 macro_strategy）
    scene_down  = (pm_thesis.get("scenario_downgrade")
                   or macro_nodes.get("scenario_downgrade") or {})
    b2b_price   = (scene_down.get("bull_to_base") or {}).get("price")   # bull→base 触发价
    ba2b_price  = (scene_down.get("base_to_bear") or {}).get("price")   # base→bear 触发价

    # 催化剂窗口（来自 premarket_summary）
    cat_window  = pm_thesis.get("catalyst_window_active", False)
    cat_pct     = pm_thesis.get("catalyst_pre_reduce_pct", 20)

    # 证伪条件（用于盘中展示）
    falsif_list = pm_thesis.get("falsification_conditions", [])

    # 时间止损
    time_stop_date = pm_thesis.get("time_stop_date")

    scene, _ = classify_pattern(a, spy_chg)

    signals = []
    status  = "intact"

    # ── 1. 硬线触发（结构止损，最高优先）────────────────
    if cur <= hard_stop:
        signals.append(f"🔴 硬线触发！现价${cur:.2f} ≤ 结构止损${hard_stop:.2f}，建议立即执行")
        status = "broken"

    # ── 1b. 软线触发（跌破成本，论点未必破裂）────────────
    elif cur <= soft_stop:
        dist_pct = (soft_stop - cur) / soft_stop * 100
        dist_hard = (cur - hard_stop) / cur * 100
        signals.append(
            f"🟠 软线触发：现价${cur:.2f} 跌破成本${soft_stop:.2f}（浮亏{dist_pct:.1f}%），"
            f"结构止损${hard_stop:.2f}仍有{dist_hard:.1f}%空间，论点需再确认"
        )
        if status == "intact":
            status = "weakening"

    # ── 2. 场景D/F + 放量 = 论点破裂 ─────────────────────
    if scene in ("D", "F"):
        vol_strong = "扩" in a["vol"]
        if vol_strong:
            signals.append(f"🔴 场景{scene}+放量 = 分销信号，催化剂可能已兑现，论点破裂")
            status = "broken"
        else:
            signals.append(f"⚠️ 场景{scene}，动能减弱，论点动摇")
            if status == "intact":
                status = "weakening"

    # ── 3. T1目标触达（Minervini机械规则）────────────────
    if cur >= t1_tgt:
        signals.append(f"🎯 T1目标${t1_tgt:.2f}已触达，建议减半仓 + 止损移至成本${cost:.2f}")
        if status == "intact":
            status = "weakening"

    # ── 4. 风险/回报比（Taleb）──────────────────────────
    remain_up   = t1_tgt - cur
    remain_down = cur - stop
    rr = round(remain_up / remain_down, 2) if remain_down > 0 else 0.0
    if rr < 0.5 and remain_down > 0:
        signals.append(f"⚠️ RR倒置：剩余上行${remain_up:.1f} vs 下行风险${remain_down:.1f}（RR={rr:.1f}x）")
        if status == "intact":
            status = "weakening"

    # ── 5. 接近硬线预警（<3%）────────────────────────────
    hard_dist_pct = (cur - hard_stop) / cur * 100 if cur > hard_stop else 0
    if 0 < hard_dist_pct < 3 and status == "intact":
        signals.append(f"🔶 接近结构止损！距硬线${hard_stop:.2f}仅{hard_dist_pct:.1f}%，成本软线${soft_stop:.2f}")
        status = "weakening"

    # ── 6. T2加仓条件（仅论点完好时显示）────────────────
    if status == "intact":
        vol_ratio = a["vr"] / a["vp"] if a.get("vp", 0) > 0 else 1.0
        t2a_ok = (cur > cost * 1.005 and vol_ratio > 0.85 and a["hist"] > 0)
        if t2a_ok:
            _shrink_ok, _shrink_reason = _check_shrink_pullback(a)
            if _shrink_ok:
                signals.append(f"⚡ T2A条件满足（价格站稳+量比{vol_ratio:.2f}x+MACD正）{_shrink_reason}")
            else:
                signals.append(f"⚡ T2A基础满足（{_shrink_reason}，等缩量回踩再加仓）")

    # ── 预期重定价框架（三种市场对论点的定价状态）──────────────
    # 状态1：利好不涨（预期转弱）
    _catalyst_strength = position.get("catalyst_strength", 0) or 0
    _prev_close = a.get("prev_close", cur)
    _today_chg_pct = (cur - _prev_close) / max(_prev_close, 0.01) * 100 if _prev_close else 0
    if _catalyst_strength >= 3 and _today_chg_pct <= -0.5:
        signals.append("⚠️ 预期转弱：有强催化剂但今日下跌，市场已充分定价或论点被质疑")
        if status == "intact":
            status = "weakening"

    # 状态2：预期兑现风险（近10日大涨后）
    _gain_10d = a.get("gain_10d")
    if _gain_10d is not None and _gain_10d > 15:
        signals.append(f"⚠️ 预期兑现风险：10日涨{_gain_10d:.1f}%，短期涨幅已充分定价，关注减速信号")

    # 状态3：超越共识定价（现价 > 分析师目标价）
    _analyst_target = _load_analyst_target(sym)
    if _analyst_target and cur > _analyst_target:
        _over_pct = (cur - _analyst_target) / _analyst_target * 100
        signals.append(f"⚠️ 超越共识定价：现价${cur:.1f}超分析师目标${_analyst_target:.1f}（+{_over_pct:.1f}%），安全边际消失")

    # ── 宏观策略框架检查（参数从 micro_strategy_params 读取）──────────────
    _th_p     = _MICRO_P.get("thesis_health", {})
    _sd_warn  = _th_p.get("scene_downgrade_warn_pct", 2.0)

    # 7. 情景降级价位接近检查
    if b2b_price and cur > 0:
        dist_b2b = (cur - b2b_price) / cur * 100
        if dist_b2b < 0:
            signals.append(f"🔴 情景已降级：现价${cur:.2f}跌破 bull→base 警戒线${b2b_price:.2f}，论点转 weakening")
            if status == "intact":
                status = "weakening"
        elif dist_b2b < _sd_warn:
            signals.append(f"🟠 接近情景降级线：距 bull→base${b2b_price:.2f}仅{dist_b2b:.1f}%，监控放量下破")
            if status == "intact":
                status = "weakening"

    if ba2b_price and cur > 0:
        dist_ba2b = (cur - ba2b_price) / cur * 100
        if dist_ba2b < 0:
            signals.append(f"🔴 base→bear 价位已破（${ba2b_price:.2f}），论点破裂确认，联动动态止损")
            status = "broken"
        elif dist_ba2b < _sd_warn:
            signals.append(f"🔶 接近 base→bear 价位${ba2b_price:.2f}（{dist_ba2b:.1f}%），同时接近动态止损，极度危险")

    # 8. 催化剂窗口期（冻结加仓）
    if cat_window:
        signals.append(f"📅 催化剂窗口期：Add1/Add2 已冻结，建议盘前缩仓 {cat_pct}%，等催化剂结果后再操作")

    # 9. 时间止损临近提醒（≤3天）
    if time_stop_date:
        try:
            from datetime import date as _date_cls
            days_left = (_date_cls.fromisoformat(time_stop_date) - _date_cls.today()).days
            if days_left <= 3:
                signals.append(f"⏰ 时间止损到期（{time_stop_date}，{days_left}天后）→ 今日必须重新评估论点")
        except Exception:
            pass

    # 10. 证伪条件展示（有条件时提示盯盘方向）
    if falsif_list and status == "intact":
        signals.append(f"🔒 盯盘：{falsif_list[0][:60]}")

    # ── 下跌性质分类（仅在论点动摇/破裂时追加） ─────────────────
    if status in ("weakening", "broken"):
        pb = classify_pullback(sym, a, spy_chg, position, t1_tgt)
        signals.append(pb["label"] + " → " + pb["recommendation"])

    # ── action ────────────────────────────────────────────
    if status == "broken":
        action = "⛔ 建议减仓/止损执行"
    elif status == "weakening":
        action = "⚠️ 密切关注，准备减仓"
    else:
        has_t2 = any("T2A" in s for s in signals)
        # 催化剂窗口期内冻结加仓提示
        if has_t2 and cat_window:
            action = "✅ 持有（催化剂窗口期，Add1/Add2 已冻结）"
        else:
            action = "✅ 持有" + ("，T2条件满足可加仓" if has_t2 else "")

    return {
        "status":    status,
        "signals":   signals,
        "action":    action,
        "rr_ratio":  rr,
        "stop":      hard_stop,
        "hard_stop": hard_stop,
        "soft_stop": soft_stop,
        "t1_target": t1_tgt,
        "gain_pct":  round(gain_pct, 2),
        "scene":     scene,
        "shares":    shares,
        "cost":      cost,
        # 宏观策略框架数据（供下游使用）
        "scenario_downgrade":    scene_down,
        "catalyst_window_active": cat_window,
        "falsification_conditions": falsif_list,
    }


def _write_observation_log(stocks, spy_chg, vc, vt, qqq5m, macro_state):
    """
    每次 poll 对所有关注标的写入信号快照 + 系统判断，
    盘后由 harvest_agent 配对实际结果，转化为可学习的经验。
    写入 learning/observation_log.jsonl
    """
    now_utc  = datetime.now(timezone.utc)
    et_h     = (now_utc.hour - 4) % 24
    today    = now_utc.strftime("%Y-%m-%d")
    time_str = f"{et_h:02d}:{now_utc.minute:02d}"
    phase    = "morning" if et_h < 11 else "midday" if et_h < 14 else "afternoon"

    pos_syms = set()
    try:
        _p = json.load(open(os.path.join(_STOCK_BASE, "config", "positions.json"), encoding="utf-8"))
        pos_syms = set(_p.get("positions", {}).keys())
    except Exception:
        pass

    kl_map = {}
    try:
        _dp = os.path.join(_STOCK_BASE, f"daily_plan_{today}.json")
        if os.path.exists(_dp):
            _plan = json.load(open(_dp, encoding="utf-8"))
            for _s, _v in _plan.get("stocks", {}).items():
                kl_map[_s] = {"stop":  _v.get("t1_stop"),
                               "t1":    _v.get("t1_target1"),
                               "t2":    _v.get("t1_target2"),
                               "scene": _v.get("predicted_scene"),
                               "catalyst_strength": _v.get("catalyst_strength", 1)}
    except Exception:
        pass

    os.makedirs(os.path.dirname(_OBS_LOG), exist_ok=True)
    with open(_OBS_LOG, "a", encoding="utf-8") as _f:
        for sym, a in stocks.items():
            if not a:
                continue
            rs = round(a["chg"] - spy_chg, 2)
            gate_passed, _, gate_checks, gate_block, _ = strategy_gate(
                a, spy_chg, vc, vt, qqq5m, macro_state, sym=sym)

            obs = []
            if gate_block:           obs.append(f"门控禁止:{gate_block}")
            elif gate_passed:        obs.append("入场门通过")
            if a["rsi3"] >= 80:      obs.append(f"RSI3={a['rsi3']:.0f}超买")
            elif a["rsi3"] <= 20:    obs.append(f"RSI3={a['rsi3']:.0f}超卖")
            if a.get("hist", 0) > 0: obs.append("MACD正")
            else:                    obs.append("MACD负")
            if rs >= 2.0:            obs.append(f"RS极强+{rs:.1f}%")
            elif rs >= 1.0:          obs.append(f"RS强+{rs:.1f}%")
            elif rs <= -2.0:         obs.append(f"RS极弱{rs:.1f}%")

            _f.write(json.dumps({
                "date":        today,
                "time":        time_str,
                "session":     phase,
                "sym":         sym,
                "is_position": sym in pos_syms,
                "price":       round(a["cur"], 2),
                "chg_pct":     round(a["chg"], 2),
                "rs_pct":          rs,
                "rs_grade_code":   grade_code(rs),
                "vwap_dist":       round(a.get("dvwap", 0), 2),
                "rsi3":            a["rsi3"],
                "macd":            round(a.get("hist", 0), 3),
                "vol_ratio":       round(a.get("vol_ratio_5m", 1.0), 2),
                "vol_code":        a.get("vol_code", "flat"),
                "gate_pass":   gate_passed,
                "gate_block":  gate_block or "",
                "gate_detail": {k: v for k, (v, _) in gate_checks.items()},
                "key_obs":     " | ".join(obs) if obs else "信号混合",
                "key_levels":  kl_map.get(sym, {}),
                "spy_chg":     round(spy_chg, 2),
                "qqq5m":       round(qqq5m, 3),
                "vix":         round(vc, 1),
                "vix_dir":     vt,
                "macro":       macro_state,
                # C: Lynch建议加入催化剂背景，让技术信号有基本面依据
                "catalyst_strength": kl_map.get(sym, {}).get("catalyst_strength", 1),
            }, ensure_ascii=False) + "\n")


_MACRO_JSON_PIVOT = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "findings", "macro.json")

def check_macro_pivot(real_positions, poll_state, et_h, et_m):
    """
    检测 macro_tone 是否发生拐点（与上轮存储值不同）。
    只在 ET 9:30-16:00 运行。返回 pivot_info dict 或 None。
    """
    in_hours = (et_h == 9 and et_m >= 30) or (10 <= et_h < 16)
    if not in_hours:
        return None
    try:
        macro = json.load(open(_MACRO_JSON_PIVOT, encoding="utf-8"))
        tone_now = macro.get("macro_tone")
    except Exception:
        return None
    tone_prev = poll_state.get("macro_tone_prev") if poll_state else None
    if not tone_prev or tone_prev == tone_now or not tone_now:
        return None

    yield_curve = macro.get("yield_curve", "")
    dxy         = macro.get("dxy") or 0
    macro_score = macro.get("macro_score", 5)

    active_vars = set()
    if yield_curve == "倒挂":
        active_vars.add("rate_up")
        if macro_score <= 5:
            active_vars.add("credit_tight")
    if dxy > 103:
        active_vars.add("dollar_strong")
    if macro_score <= 3:
        active_vars.add("recession")

    improved, worsened = [], []
    for sym, pos in (real_positions or {}).items():
        ms = pos.get("macro_sensitivity", {})
        mt = pos.get("macro_type", "")
        if not ms:
            continue
        neg_now = [v for v in active_vars if ms.get(v) == "负"]
        if tone_prev == "偏空" and tone_now in ("中性", "偏多"):
            if neg_now:
                improved.append({"sym": sym, "macro_type": mt, "variables": neg_now})
        elif tone_prev in ("偏多", "中性") and tone_now == "偏空":
            if len(neg_now) >= 2:
                worsened.append({"sym": sym, "macro_type": mt, "variables": neg_now})
        else:
            if neg_now:
                worsened.append({"sym": sym, "macro_type": mt, "variables": neg_now})

    return {"from": tone_prev, "to": tone_now, "improved": improved, "worsened": worsened}


def fmt_macro_pivot(pivot):
    """格式化并打印宏观拐点提示"""
    if not pivot:
        return
    print(f"\n⚡ 宏观拐点：{pivot['from']} → {pivot['to']}")
    var_cn = {"rate_up": "利率高位", "credit_tight": "信贷紧缩",
              "dollar_strong": "美元强势", "recession": "衰退风险", "inflation": "通胀高位"}
    if pivot["improved"]:
        print("   宏观逆风减少，论点支撑改善：")
        for item in pivot["improved"]:
            vs = "/".join(var_cn.get(v, v) for v in item["variables"])
            print(f"     {item['sym']} [{item['macro_type']}] {vs}↑改善")
    if pivot["worsened"]:
        print("   宏观逆风增加，建议确认论点是否仍成立：")
        for item in pivot["worsened"]:
            vs = "/".join(var_cn.get(v, v) for v in item["variables"])
            print(f"     {item['sym']} [{item['macro_type']}] {vs}↓恶化")
    print()


def get_time_window(et_h, et_m, trading_mode="active"):
    """返回 (window_name, hint) 或 (None, None)。时间区间左闭右开。"""
    t = et_h * 60 + et_m

    if trading_mode == "constrained":
        # 约束模式：只有两个窗口
        if 9 * 60 + 30 <= t < 10 * 60:
            return ("开盘观察期", "观察开盘方式，参数校准，不入场")
        if 10 * 60 <= t < 10 * 60 + 30:
            return ("执行窗口", "满足条件则入场挂 GTC 单，10:30后走人")
        return (None, None)

    # active 模式：原有四窗口逻辑（不变）
    if 9 * 60 + 30 <= t < 9 * 60 + 35:
        return ("开盘5分钟", "主力意图首次表达，方向比幅度重要")
    if 9 * 60 + 35 <= t < 10 * 60:
        return ("开盘窗口", "高波动，需更强量能确认才入场")
    if 11 * 60 + 30 <= t < 13 * 60:
        return ("午盘低量", "噪声高，提高入场门槛，不适合追价")
    if 15 * 60 <= t < 16 * 60:
        return ("尾盘方向窗口", "大单驱动，方向性移动可信度高")
    return (None, None)


def _load_trade_quality(n: int = 10) -> dict:
    """
    读取最近 n 笔交易质量，用于 constrained 模式的热手/冷手判断。
    返回 {"state": str, "reason": str, "n": int}
    """
    _path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "learning", "trade_log.json")
    try:
        data = json.load(open(_path, encoding="utf-8"))
        trades = [t for t in data.get("trades", []) if t.get("pnl_pct") is not None]
        trades = trades[-n:]
        if len(trades) < 3:
            return {"state": "正常", "reason": f"交易记录不足（{len(trades)}/3笔）", "n": len(trades)}

        wins = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
        per_plan = sum(1 for t in trades if t.get("per_plan", True))
        win_rate = wins / len(trades)
        plan_rate = per_plan / len(trades)

        if win_rate >= 0.6 and plan_rate >= 0.8:
            state = "热手"
            reason = f"近{len(trades)}笔胜率{win_rate:.0%}，按计划执行{plan_rate:.0%}"
        elif win_rate <= 0.3 or plan_rate <= 0.5:
            state = "冷手"
            reason = f"近{len(trades)}笔胜率{win_rate:.0%}，按计划执行{plan_rate:.0%}"
        else:
            state = "正常"
            reason = f"近{len(trades)}笔胜率{win_rate:.0%}"

        return {"state": state, "reason": reason, "win_rate": win_rate,
                "plan_rate": plan_rate, "n": len(trades)}
    except Exception:
        return {"state": "正常", "reason": "trade_log不可读", "n": 0}


def calc_trading_state(real_positions, stocks, old_state, new_contradictions,
                       trading_mode="active"):
    """
    计算热手/冷手状态。
    old_state: 上轮 poll_state（load_poll_state() 结果）
    new_contradictions: 本轮新增矛盾次数（高评分但价格跌）
    返回 dict。
    """
    # constrained 模式：基于近期交易质量，不依赖当日矛盾计数
    if trading_mode == "constrained":
        tq = _load_trade_quality(n=10)
        pnl_list = []
        for sym, pos in (real_positions or {}).items():
            a = (stocks or {}).get(sym)
            if not a: continue
            cost = float(pos.get("cost", 0))
            if cost > 0:
                pnl_list.append((a["cur"] - cost) / cost * 100)
        current_pnl = round(sum(pnl_list) / len(pnl_list), 2) if pnl_list else 0.0
        return {
            "state": tq["state"],
            "contradiction_count": 0,
            "current_pnl": current_pnl,
            "today_peak_pnl": current_pnl,
            "pnl_drawdown": 0.0,
            "reason": tq["reason"],
        }
    # active 模式：原有逻辑（继续往下执行）

    prev_contradiction = old_state.get("contradiction_count", 0) if old_state else 0
    total_contradiction = prev_contradiction + new_contradictions

    pnl_list = []
    for sym, pos in (real_positions or {}).items():
        a = (stocks or {}).get(sym)
        if not a: continue
        cost = float(pos.get("cost", 0))
        if cost > 0:
            pnl_list.append((a["cur"] - cost) / cost * 100)
    current_pnl = round(sum(pnl_list) / len(pnl_list), 2) if pnl_list else 0.0

    prev_peak = old_state.get("today_peak_pnl", current_pnl) if old_state else current_pnl
    today_peak_pnl = max(prev_peak, current_pnl)
    pnl_drawdown = round(today_peak_pnl - current_pnl, 2)

    if total_contradiction >= 2 or pnl_drawdown > 2.0:
        state = "冷手"
        reasons = []
        if total_contradiction >= 2:
            reasons.append(f"矛盾{total_contradiction}次")
        if pnl_drawdown > 2.0:
            reasons.append(f"浮盈从+{today_peak_pnl:.1f}%回落至{current_pnl:+.1f}%")
        reason = " | ".join(reasons)
    elif total_contradiction == 0 and current_pnl > 0:
        state = "热手"
        reason = f"无矛盾 | 整体浮盈{current_pnl:+.1f}%"
    else:
        state = "正常"
        reason = ""

    return {
        "state": state,
        "contradiction_count": total_contradiction,
        "current_pnl": current_pnl,
        "today_peak_pnl": today_peak_pnl,
        "pnl_drawdown": pnl_drawdown,
        "reason": reason,
    }


def classify_pullback(sym, a, spy_chg, position, t1_tgt):
    """
    下跌性质四分类，在 evaluate_thesis_health 触发 weakening/broken 时调用。
    返回 {"category": str, "label": str, "recommendation": str}
    """
    from datetime import date as _date
    cur = a["cur"]

    if cur >= t1_tgt:
        return {"category": "cycle_end",
                "label": "📌 论点周期收尾：T1目标已触达",
                "recommendation": "建议主动评估是否续持，而非等待"}
    deadline = position.get("catalyst_deadline")
    if deadline:
        try:
            if _date.today() > _date.fromisoformat(str(deadline)):
                return {"category": "cycle_end",
                        "label": "📌 论点周期收尾：催化剂窗口已关闭",
                        "recommendation": "建议主动评估是否续持，而非等待"}
        except: pass

    diff = a["chg"] - spy_chg
    if diff < -1.5:
        return {"category": "stock_event",
                "label": f"🏢 个股事件驱动：跌幅超大盘{diff:.1f}pp",
                "recommendation": "排查是否有新的负面信息/论点动摇"}
    if abs(diff) < 0.8:
        return {"category": "market_drag",
                "label": f"🌊 大盘拖累：与SPY涨跌差{diff:+.1f}pp，基本同步",
                "recommendation": "等大盘稳定，论点暂未受影响"}
    return {"category": "sector",
            "label": f"🔄 板块联动/混合：与SPY差{diff:+.1f}pp",
            "recommendation": "对照同板块ETF确认是否板块轮动"}


def check_extreme_speed(sym, a):
    """
    检测极端下跌速度（速度×量能组合）。返回警告字符串或 None。
    使用 snap() 已计算的 candle_drop_5m 和 vol_ratio_5m。
    """
    drop = a.get("candle_drop_5m", 0.0)
    vol  = a.get("vol_ratio_5m", 1.0)
    if drop >= 0:
        return None
    drop_pct = drop * 100
    if drop < -0.05 and vol > 1.5:
        return (f"🚨🚨 极端下跌：5min跌幅{drop_pct:.1f}%+大放量{vol:.1f}x，"
                f"建议执行止损（注意流动性，限价优于市价）")
    if drop < -0.03 and vol > 1.2:
        return (f"🚨 速度异常：5min跌幅{drop_pct:.1f}%+放量{vol:.1f}x，"
                f"建议立即核查论点，考虑减半仓（避免市价单）")
    if drop < -0.03 and vol < 0.5:
        return (f"⚠️ 流动性真空下跌：跌幅{drop_pct:.1f}%但量能极萎缩{vol:.1f}x，"
                f"可能是假跌，暂缓操作")
    return None


def _run_poll_tick(symbols, sector_map=None, lev_map=None, cost_map=None, session=False, active_syms=None, passive_syms=None, should_poll_passive=True):
    # 读取上次状态
    _prev_state = {}
    try:
        from agents.poll_state import load_poll_state
        _prev_state = load_poll_state()
    except Exception:
        pass

    # ── 读取交易模式配置 ─────────────────────────────────────────
    _cfg_path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "config", "poll_config.json")
    _trading_cfg = {}
    try:
        _trading_cfg = json.load(open(_cfg_path, encoding="utf-8"))
    except Exception:
        pass
    _trading_mode = _trading_cfg.get("trading_mode", "active")
    # 读取今日盘前入场决策（Constrained Mode 下过滤信号）
    _entry_decisions = _load_entry_decision()
    _window = _trading_cfg.get("trading_window", {"start_et_hhmm": "0930", "end_et_hhmm": "1030"})
    _win_start = int(_window.get("start_et_hhmm", "0930"))
    _win_end   = int(_window.get("end_et_hhmm", "1030"))

    def _in_trading_window(h, m):
        t = h * 100 + m
        return _win_start <= t <= _win_end

    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    et_h = (datetime.now(timezone.utc).hour-4)%24
    et_m = datetime.now(timezone.utc).minute

    spy  = snap("SPY"); qqq = snap("QQQ"); vix = vix_snap()
    
    stocks = {}
    for sym in symbols:
        is_active = active_syms is None or sym in active_syms
        force_h1m = is_active or should_poll_passive
        stocks[sym] = snap(sym, force_h1m=force_h1m)

    # Real-time macro regime
    try:
        from learning.features import get_macro_regime
        # 接入全局缓存限频，TTL 为 4 小时
        spy_daily = _get_cached_history(yf.Ticker("SPY"), "SPY", "spy_daily_1y", period="1y", ttl=14400)
        macro_state = get_macro_regime(spy_daily, len(spy_daily)-1) if len(spy_daily) > 0 else "normal"
    except Exception:
        macro_state = "normal"

    vc    = vix["cur"] if vix else 20
    vchg  = vix["chg"] if vix else 0
    vt    = vix["trend"] if vix else "→平"
    vb    = vix["bars"] if vix else "─"
    vlvl  = "🟡中性" if vc<=20 else "🟠偏高" if vc<=25 else "🔴高危"
    spy_chg = spy["chg"] if spy else 0
    qqq_chg = qqq["chg"] if qqq else 0

    # 组合风险联动：读取 portfolio_risk_agent 的最近输出（引入缓存限制子进程频繁开辟以降低 CPU 负载）
    global _LAST_RISK_RUN_TIME, _CACHED_VAR_PCT
    if "_LAST_RISK_RUN_TIME" not in globals():
        _LAST_RISK_RUN_TIME = 0.0
        _CACHED_VAR_PCT = None

    _portfolio_var_pct = _CACHED_VAR_PCT
    _cur_t = _time.time()
    
    # 距离上次执行超过 900 秒（15分钟），或者缓存为空时，才起子进程重算
    if _portfolio_var_pct is None or (_cur_t - _LAST_RISK_RUN_TIME) >= 900:
        try:
            import subprocess as _sp
            import re as _re
            _r = _sp.run([PYTHON, os.path.join(os.path.dirname(__file__), "portfolio_risk_agent.py"), "--summary-only"],
                         cwd=((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), capture_output=True, text=True, timeout=30)
            for _line in _r.stdout.split("\n"):
                if "预计亏损" in _line:
                    _m = _re.search(r'\((-[\d.]+)%\)', _line)
                    if _m:
                        _portfolio_var_pct = float(_m.group(1))
                        _CACHED_VAR_PCT = _portfolio_var_pct
                        _LAST_RISK_RUN_TIME = _cur_t
        except Exception:
            pass
    qqq5m   = qqq_5m_chg(qqq)
    mkt = 0
    for chg in [spy_chg, qqq_chg]:
        mkt += 2 if chg>0.3 else 1 if chg>0 else -2 if chg<-0.5 else -1
    mkt += 2 if vt=="↓降" else -2 if vt=="↑升" else 0
    eok = mkt >= 1
    ml = "🟢顺风" if mkt>=4 else "🟡中性" if mkt>=1 else "🟠谨慎" if mkt>=-1 else "🔴逆风"

    # 板块ETF涨跌：供盘中快照、分类与 dashboard 统一使用
    sector_snaps = {}
    if sector_map:
        unique_refs = {
            v.get("ref")
            for v in sector_map.values()
            if isinstance(v, dict) and v.get("ref")
        }
        for ref in unique_refs:
            try:
                s = snap(ref)
                if s and s.get("chg") is not None:
                    sector_snaps[ref] = float(s.get("chg", 0.0) or 0.0)
            except Exception:
                pass

    # ── 写入快照 ──────────────────────────────────────────
    snap_data = {}
    for sym, a in stocks.items():
        if not a: continue
        _rs = round(a["chg"]-spy_chg, 2)
        sec_ref = (sector_map or {}).get(sym, {}).get("ref") if isinstance(sector_map, dict) else None
        sec_chg = sector_snaps.get(sec_ref) if sec_ref else None
        rs_vs_sector = round(float(a["chg"]) - sec_chg, 2) if sec_chg is not None else None
        snap_data[sym] = {
            "cur": a["cur"], "chg": a["chg"],
            "rs":  _rs,
            "rs_grade_code": grade_code(_rs),          # 枚举：very_strong|strong|neutral|weak|very_weak
            "rsi3": a["rsi3"], "hist": a["hist"],
            "dvwap": a["dvwap"],
            "vol":  a["vol"],
            "vol_code": a.get("vol_code", "flat"),     # 枚举：expand|flat|shrink
            "bars": a["bars"], "atr14": a["atr14"],
            "sector_ref": sec_ref,
            "sector_chg": round(sec_chg, 2) if sec_chg is not None else None,
            "rs_vs_sector": rs_vs_sector if rs_vs_sector is not None else 0.0,
        }
    if vix:
        write_snapshot(snap_data, vix, spy_chg, qqq_chg)

    # ── 输出 ──────────────────────────────────────────────
    # 市场状态感知
    _mkt_open   = (et_h > 9 or (et_h == 9 and et_m >= 30)) and et_h < 16
    _mkt_closed = et_h >= 16
    _mins_left  = max(0, 16*60 - et_h*60 - et_m) if _mkt_open else 0
    _mins_open  = max(0, et_h*60 + et_m - 9*60 - 30) if _mkt_open else 0
    if _mkt_closed:
        _mkt_tag = "🔔 已收盘"
    elif _mkt_open:
        _mkt_tag = f"🟢 盘中 已开{_mins_open}分钟 距收盘{_mins_left//60}h{_mins_left%60}m"
    else:
        _mkt_tag = "⏳ 未开盘"

    print(f"{'='*60}")
    print(f"  轮询  美东{et_h:02d}:{et_m:02d}  {_mkt_tag}")
    print(f"{'='*60}")
    _win_name, _win_hint = get_time_window(et_h, et_m, trading_mode=_trading_mode)
    if _win_name:
        print(f"⏱ 当前窗口：{_win_name}（{_win_hint}）")
    if _trading_mode == "constrained" and not _in_trading_window(et_h, et_m):
        if et_h * 100 + et_m > _win_end:
            print("⏰ 交易窗口已关闭（10:30 ET）— GTC单接管，轮询监控模式")
    ev = "VIX↑升⚠️" if vt=="↑升" else "VIX↓回落✅" if vt=="↓降" else f"VIX{vc:.0f}→平"
    print(f"【环境】{ev} | SPY{spy_chg:+.2f}% QQQ{qqq_chg:+.2f}%  {mkt:+d}/6→{ml}  宏观:{macro_state}")
    # 上轮快照 + 今日极值摘要（跨轮次连续性）
    try:
        from agents.poll_state import format_prev_state_line, format_today_summary_line, format_master_summary_line
        _prev_line = format_prev_state_line(_prev_state)
        if _prev_line:
            # 只保留本次轮询的 symbols，过滤持仓外的噪音
            _watched = set(symbols)
            _prev_parts = []
            for _p in _prev_line.split("  "):
                if any(_p.startswith(s) for s in _watched):
                    _prev_parts.append(_p)
            if _prev_parts:
                _ts = _prev_state.get("last_updated", "?")
                print("【上轮 " + _ts + "】" + "  ".join(_prev_parts))
        _today_line = format_today_summary_line(_prev_state, watched_syms=set(symbols))
        if _today_line:
            print(_today_line)
        _master_line = format_master_summary_line(_prev_state, watched_syms=set(symbols))
        if _master_line:
            print(_master_line)
    except Exception:
        pass
    print(f"VIX {vc:.1f}({vchg:+.1f}%) {vlvl} {vt} {vb}")
    print(f"SPY {spy['bars'] if spy else '─────'}  QQQ {qqq['bars'] if qqq else '─────'}")

    # 组合 VaR 警告（阈值 -8%）
    if _portfolio_var_pct and _portfolio_var_pct < -8:
        print(f"⚠️  组合VaR警告: 大盘跌5%预计亏损{_portfolio_var_pct:.1f}%（超过-8%阈值，建议减仓）")

    # 每月第一个周一：提示运行基本面季度追踪
    _today = datetime.now()
    if _today.weekday() == 0 and _today.day <= 7:
        print(f"📅  本月第一个周一：建议运行季度基本面追踪 → python3.12 agents/fundamentals_tracker.py")

    # 时间感知
    try:
        from stock_team.utils.market_calendar import get_context, format_context
        cal_ctx = get_context()
        if cal_ctx.get("warnings"):
            for w in cal_ctx["warnings"]:
                print(w)
    except Exception:
        pass
    print()

    # 模拟盘状态（三账号）
    live_prices = {sym: a["cur"] for sym, a in stocks.items() if a}
    print(get_status(live_prices, ACCOUNTS))
    print()

    # 盘初场景框架
    render_opening_block(stocks, spy_chg, qqq_chg, vix, et_h, et_m,
                         sector_map=sector_map)

    # ── 真实持仓健康度（优先级最高）──────────────────────────
    real_positions = load_real_positions()

    # ── 组合总市值（用于 flex 占比计算）────────────────────────────
    try:
        _cfg_raw = json.load(open(os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")),
                                               "config", "positions.json"), encoding="utf-8"))
        _cash = float(_cfg_raw.get("cash", 0))
        _portfolio_total = _cash + sum(
            stocks[s]["cur"] * real_positions[s].get("shares", 0)
            for s in real_positions if s in stocks and stocks.get(s)
        )
    except Exception:
        _portfolio_total = 0

    # ── 宏观拐点检测 ──────────────────────────────────────────────
    from agents.poll_state import load_poll_state as _load_ps
    _pivot = check_macro_pivot(real_positions, _load_ps(), et_h, et_m)
    fmt_macro_pivot(_pivot)

    # 只显示轮询标的中有持仓的
    held_syms = [s for s in symbols if s in real_positions and stocks.get(s)]
    # 也检查 positions 中有、但不在 symbols 列表里的持仓（仅做警告）
    unmonitored = [s for s in real_positions
                   if s not in symbols and s not in ("_comment",)]

    if held_syms or unmonitored:
        print("━"*60)
        print("📊 持仓管理（Thesis Health）")
        print("━"*60)

    for sym in held_syms:
        pos    = real_positions[sym]
        a      = stocks[sym]
        # 极端速度检测（优先级最高，在持仓分析前显示）
        _speed_warn = check_extreme_speed(sym, a)
        if _speed_warn:
            print(f"\n{_speed_warn}")
        health = evaluate_thesis_health(sym, a, spy_chg, pos, stocks=stocks)

        st_icon = {"intact": "🟢", "weakening": "🟡", "broken": "🔴"}[health["status"]]
        pnl_icon = "📈" if health["gain_pct"] >= 0 else "📉"
        print(f"{st_icon} {sym}  持仓{health['shares']}股@${health['cost']:.2f}  "
              f"现${a['cur']:.2f}  {pnl_icon}{health['gain_pct']:+.1f}%")
        print(f"   止损${health['stop']:.2f}  T1目标${health['t1_target']:.2f}  "
              f"RR剩余{health['rr_ratio']:.1f}x  场景{health['scene']}")
        for sig in health["signals"]:
            print(f"   {sig}")
        print(f"   → {health['action']}")
        # 论点动摇/破裂时触发大师判断
        if health["status"] in ("weakening", "broken"):
            for line in master_thesis_judgment(sym, a, spy_chg, ""):
                print(line.replace("│ ", "   "))
        print()

        # session push
        if health["status"] in ("broken", "weakening") and health["signals"]:
            _session_push(
                f"thesis_{health['status']}", sym,
                health["signals"][0],
                {"status": health["status"], "gain_pct": health["gain_pct"],
                 "action": health["action"]},
                enabled=session
            )

    if unmonitored:
        print(f"⚠️ 持仓中未监控标的：{', '.join(unmonitored)}（加入 symbols 列表以监控）")
        print()

    # 持仓监控
    for sym, (lev_sym, lev_n) in (lev_map or {}).items():
        lev_a = snap(lev_sym) if lev_sym else None
        base_a = stocks.get(sym)
        if not lev_a or not base_a: continue
        cost = (cost_map or {}).get(lev_sym)
        if not cost: continue
        pnl = (lev_a["cur"]-cost)/cost*100
        rs_lev = lev_a["chg"] - spy_chg
        base_stop, stop_type, stop_desc, _ = atr_stop_suggestion(base_a, spy_chg)
        lev_stop = lev_a["cur"] * (base_stop/base_a["cur"])
        # 明确区分软线（保本）和硬线（结构止损）
        near_hard_stop = lev_a["cur"] < lev_stop * 1.03   # 距结构止损<3%
        below_cost     = lev_a["cur"] < cost              # 跌破成本（软线）
        if pnl > 3:
            pos_act = f"✅ 浮盈{pnl:.1f}%，软线→成本${cost}（结构止损${lev_stop:.2f}）"
        elif pnl >= 0:
            pos_act = f"🟡 微盈{pnl:.1f}%，守住（结构止损${lev_stop:.2f}）"
        elif near_hard_stop:
            pos_act = f"🔴 浮亏{pnl:.1f}%，⚠️接近结构止损${lev_stop:.2f}（硬线）"
        elif below_cost:
            pos_act = f"🟠 浮亏{pnl:.1f}%，破软线成本${cost}，结构止损${lev_stop:.2f}仍安全"
        else:
            pos_act = f"🔴 浮亏{pnl:.1f}%，守止损（结构止损${lev_stop:.2f}）"
        print(f"{'━'*60}")
        print(f"{lev_sym} 持仓 成本${cost}  现${lev_a['cur']:.2f}({lev_a['chg']:+.2f}%) 浮{pnl:+.1f}%")
        print(f"  {lev_a['bars']} {lev_a['vol']}  RSI3={lev_a['rsi3']:.0f}  MACD={lev_a['hist']:+.2f}{'🟢' if lev_a['hist']>0 else '🔴'}")
        print(f"  底层{sym} ATR14=${base_a['atr14']:.1f}  {stop_type}→参考${lev_stop:.2f}")
        print(f"  → {pos_act}")
        # 检测 Flex 信号（新框架：监控超买超卖触发条件）
        _lev_pos_cfg = real_positions.get(lev_sym, {})
        _fs = check_flex_signals(base_a, spy_chg, et_h, et_m,
                                 position=_lev_pos_cfg, portfolio_total=_portfolio_total)
        _alloc_str = f"配置:{_fs['alloc_vs_target']}" if _fs['alloc_pct'] else ""
        if _fs["flex_reduce"] and _fs["price_ok_reduce"]:
            print(f"  🔴 Flex减仓 技术{_fs['reduce_score']}/4 {_alloc_str}")
        elif _fs["flex_add"] and _fs["price_ok_add"]:
            print(f"  🟢 Flex加仓 技术{_fs['add_score']}/4 {_alloc_str}")
        elif _fs["in_window"]:
            prc_note = "" if _fs["price_ok_reduce"] or _fs["price_ok_add"] else " (价格条件不满足)"
            print(f"  ⚪ Flex观察 减:{_fs['reduce_score']}/4 加:{_fs['add_score']}/4 {_alloc_str}{prc_note}")
        print(f"{'━'*60}")
        print()

    # RS排行（含强趋势标记）
    rs_list = [(sym, a["chg"]-spy_chg, a) for sym,a in stocks.items() if a]
    rs_list.sort(key=lambda x: x[1], reverse=True)

    # 从 current（场景分类结果）获取 rs_streak
    scene_current = {}
    try:
        date_str_now = datetime.now().strftime("%Y-%m-%d")
        _sc = load_daily_scenarios(date_str_now)
        scene_current = _sc if _sc else {}
    except Exception:
        pass

    _new_contradictions = 0  # 本轮新增矛盾次数（高评分但价格下跌）
    _persona_scores = {}  # 收集本轮各股大师评分，供 save_poll_state 写入
    _veto_details = {}
    _stop_details = {}

    print("── RS排行 ──")
    for sym, rs, a in rs_list:
        mn = " ✦" if a.get("macd_cross") else " ✗" if a.get("macd_fail") else ""
        streak = scene_current.get(sym, {}).get("rs_streak", 0)
        fire   = f" 🔥{streak}轮" if streak >= 3 else (f" {streak}轮" if streak > 0 else "")
        print(f"  {sym:8s} RS{rs:+.2f}% {grade(rs):8s}  "
              f"MACD{a['hist']:+.3f}{'🟢' if a['hist']>0 else '🔴'}  "
              f"RSI3={a['rsi3']:.0f}  "
              f"ATR14=${a['atr14']:.1f}{mn}{fire}")
    print()

    # 各标的详情 + ATR止损
    for sym, rs, a in rs_list:
        stop, stop_type, stop_desc, rr = atr_stop_suggestion(a, spy_chg)
        _stop_details[sym] = {
            "stop": stop,
            "stop_type": stop_type,
            "stop_desc": stop_desc,
            "rr": rr
        }
        rf_sym = (sector_map or {}).get(sym, {})
        rf_name = rf_sym.get("ref_name", "") if rf_sym else ""
        bounce = (a["cur"]-a["lo"])/a["lo"]*100
        mn = " ✦翻正" if a.get("macd_cross") else " ✗假突破" if a.get("macd_fail") else ""
        rt = "⚠️超卖" if a["rsi3"]<25 else "⚠️超买" if a["rsi3"]>82 else ""

        # 近2分钟涨跌（用于回调诊断）
        h1m_bars = a.get("h1m")
        stock_2m = qqq_2m = 0.0
        if h1m_bars is not None and len(h1m_bars) >= 3:
            stock_2m = float((h1m_bars["Close"].iloc[-1] - h1m_bars["Close"].iloc[-3])
                             / h1m_bars["Close"].iloc[-3] * 100)
        if qqq and qqq.get("h1m") is not None and len(qqq["h1m"]) >= 3:
            qh = qqq["h1m"]
            qqq_2m = float((qh["Close"].iloc[-1] - qh["Close"].iloc[-3])
                           / qh["Close"].iloc[-3] * 100)
        diag_label, diag_hint = pullback_diagnosis(stock_2m, qqq_2m)

        print(f"┌─{sym} ${a['cur']:.2f}({a['chg']:+.2f}%) RS{rs:+.2f}% {grade(rs)}{mn}")
        if rf_name: print(f"│ 板块参照[{rf_name}]  VIX{vc:.0f}{vt}  大盘{mkt:+d}/6")
        print(f"│ VWAP${a['vwap']:.2f}({a['dvwap']:+.1f}%)  高${a['hi']:.2f}  低${a['lo']:.2f}(弹+{bounce:.1f}%)")
        print(f"│ {a['bars']} {a['vol']}  RSI3={a['rsi3']:.0f}{rt}  MACD={a['hist']:+.3f}{'🟢' if a['hist']>0 else '🔴'}")
        if diag_label:
            print(f"│ 2m: 个股{stock_2m:+.2f}% QQQ{qqq_2m:+.2f}%  {diag_label} → {diag_hint}")
            # 持仓标的出现个股抛压时，大师判断大盘压力 vs 论点变化
            if diag_label in ("🔴个股抛压", "🔴强个股抛压") and sym in real_positions:
                for line in master_thesis_judgment(sym, a, spy_chg, diag_label):
                    print(line)

        # 反转入场信号（仅在 reversal_mode=True 时显示）
        if a.get("reversal_mode"):
            sigs = " | ".join(a.get("reversal_signals", []))
            score = a.get("reversal_score", 0)
            print(f"│ 🔄反转信号[{score}分] {sigs}")
            print(f"│   底部猎手：等量缩止跌+首根阳线确认再入")

        # Persona 实时评分（B）
        streak_now = scene_current.get(sym, {}).get("rs_streak", 0) if scene_current else 0
        ps  = quick_persona_score(a, spy_chg, qqq_chg, vc, vt, rs_streak=streak_now)
        # 收集大师评分供写入状态文件（语料积累）
        # 同时保存结构化字段 verdict（固定枚举），避免依赖自然语言措辞
        _persona_scores[sym] = {
            "avg":            ps["avg"],
            "consensus":      ps["consensus"],
            "consensus_code": ps.get("consensus_code", "hold"),   # 固定：buy/hold/no_buy
            "Minervini":     {"score": ps["Minervini"][0],     "reason": ps["Minervini"][1],
                              "verdict": ps["verdicts"]["Minervini"]},
            "Marks":         {"score": ps["Marks"][0],         "reason": ps["Marks"][1],
                              "verdict": ps["verdicts"]["Marks"]},
            "Druckenmiller": {"score": ps["Druckenmiller"][0], "reason": ps["Druckenmiller"][1],
                              "verdict": ps["verdicts"]["Druckenmiller"]},
        }
        bar = lambda s: "█"*int(s) + "░"*(10-int(s))
        print(f"│ ── 师傅评分 ── 综合{ps['avg']}/10  {ps['consensus']}")
        print(f"│ Minervini  {ps['Minervini'][0]:>2}/10 [{bar(ps['Minervini'][0])}]  {ps['Minervini'][1]}")
        print(f"│ Marks      {ps['Marks'][0]:>2}/10 [{bar(ps['Marks'][0])}]  {ps['Marks'][1]}")
        print(f"│ Druck      {ps['Druckenmiller'][0]:>2}/10 [{bar(ps['Druckenmiller'][0])}]  {ps['Druckenmiller'][1]}")

        # 矛盾检测：高评分但价格下跌
        if ps["avg"] >= 7 and a.get("chg", 0) <= -0.3:
            _new_contradictions += 1

        # 读取上轮快速辩论结果（A）
        debate = read_quick_debate(sym)
        if debate:
            cons = debate.get("consensus","")
            avg  = debate.get("avg_score","?")
            t    = debate.get("time","")
            votes_str = "  ".join(
                f"{'🟢' if v=='进' else '🟡' if v=='等' else '🔴'}{p[:4]}:{v}"
                for p, v in debate.get("votes",{}).items()
            )
            print(f"│ ── 快速辩论({t}) ── {cons}  平均{avg}/10")
            print(f"│ {votes_str}")
            for p, r in debate.get("results",{}).items():
                print(f"│   {p[:4]}: {r.get('reason','')[:50]}")

        # ATR止损建议
        ma_dist = abs(a["cur"]-a["ma20"])/a["cur"]*100 if a["ma20"] else 999
        ma20_str = f"MA20=${a['ma20']:.0f}(距{ma_dist:.0f}%)" if a["ma20"] else "MA20:N/A"
        print(f"│ ATR14=${a['atr14']:.1f}  ATR5=${a['atr5']:.1f}  {ma20_str}")
        rr_str = f"  R:R≈1:{rr:.1f}" if rr else ""
        print(f"│ 📍{stop_type}: ${stop:.2f}  [{stop_desc}]{rr_str}")

        # ── 模式切换检查 ─────────────────────────────────────────
        _modes = load_positions_mode()
        _cur_mode = _modes.get(sym, {}).get("mode") if isinstance(_modes.get(sym), dict) else _modes.get(sym)
        if _cur_mode:
            _new_mode, _switch_reasons = check_mode_switch(sym, a, _cur_mode, et_h, et_m)
            if _new_mode != _cur_mode:
                _icon = "📉" if _new_mode == "intraday" else "📈"
                print(f"│ {_icon} 模式切换 {_cur_mode}→{_new_mode}  触发: {' + '.join(_switch_reasons)}")
                if _new_mode == "intraday":
                    print(f"│   建议: 下次反弹至VWAP(${a['vwap']:.2f})附近减仓/出场")
                else:
                    print(f"│   建议: 维持持仓，不随意止损")
                _modes[sym] = {"mode": _new_mode, "reason": " + ".join(_switch_reasons)}
                save_positions_mode(_modes)
            else:
                mode_icon = "🔄波段" if _cur_mode == "swing" else "⚡日内"
                print(f"│ {mode_icon}模式  {' | '.join(_switch_reasons) if _switch_reasons else '维持'}")

        # 信号强度 → 触发快速辩论（A）
        should_debate = ps["avg"] >= 6 and rs > 1.5
        existing_debate = read_quick_debate(sym)
        if should_debate and existing_debate is None:
            trigger_quick_debate(sym, a, spy_chg, qqq_chg, vc, vt, rs_streak=streak_now)
            print(f"│ ⚡ 快速辩论已触发（综合{ps['avg']}/10，结果下轮显示）")
            _session_push("signal", sym,
                          f"⚡入场信号 {sym}",
                          {"score": ps["avg"], "rs": round(rs, 2)},
                          enabled=session)

        # 模拟盘自动操作（三账号并行）
        signal_info = {"pattern": scene_current.get(sym,{}).get("pattern","?"),
                       "rs_streak": streak_now}
        pm_catalyst = 1
        try:
            from datetime import date as _date
            pm_file = os.path.join(_STOCK_BASE, f"premarket_analysis_{_date.today()}.json")
            if os.path.exists(pm_file):
                _pm = json.load(open(pm_file, encoding="utf-8"))
                pm_catalyst = _pm.get("stocks",{}).get(sym,{}).get("catalyst_strength",1)
        except Exception:
            pass

        # Constrained Mode: 盘前已决策"不入场"的焦点股 → 跳过 strategy_gate，只显示状态行
        _sym_decision = _entry_decisions.get(sym)
        if _sym_decision and _sym_decision.get("decision") == "不入场" and _trading_mode == "constrained":
            _hard = _sym_decision.get("hard_vetoes", [])
            print(f"│ 盘前决策: ❌ 不入场 — {_hard[0] if _hard else _sym_decision.get('reason','')}")
            print(f"└{'─'*59}")
            continue   # 跳过 strategy_gate 和入场逻辑

        # Constrained Mode: 盘前"观察"状态 → 显示软否决提醒
        if _sym_decision and _sym_decision.get("decision") == "观察" and _trading_mode == "constrained":
            _soft = _sym_decision.get("soft_vetoes", [])
            if _soft:
                print(f"│ 盘前决策: ⚠️ 观察中 — 软否决: {', '.join(_soft[:2])}")

        # ── 全局否决检查（替代 strategy_gate 的黄金否决权）────────────────
        _veto = _global_veto(a, vc, vt, qqq5m, macro_state, et_h, et_m)
        _veto_details[sym] = _veto
        # 板块联动龙头破位否决检查
        try:
            from agents.sector_leadership import is_leader_broken
            _ldr_broken, _ldr_desc = is_leader_broken(sym, stocks)
            if _ldr_broken:
                _veto = f"板块龙头破位否决 ({_ldr_desc})"
        except Exception:
            pass
        if _veto:
            print(f"│ 🚫 全局否决: {_veto}")

        # ── 开盘后战术计划（30分钟后显示）────────────────────────────────
        _mins_open = max(0, et_h * 60 + et_m - 9 * 60 - 30)
        if _mins_open >= 30:
            _pop = compute_post_open_plan(sym, a, spy_chg, et_h, et_m)
            _rec_icons = {
                "ENTER_ADD1": "🟢", "WATCH_PULLBACK": "👀", "WATCH_SIGNAL": "👀",
                "HOLD": "⚪", "DEFEND": "🟠", "AVOID": "🔴", "FREEZE_CATALYST": "📅",
            }
            _icon = _rec_icons.get(_pop["entry_rec"], "•")
            print(f"│ {_icon} [{_pop['entry_rec']}] 场景{_pop['scene']}({_pop['scene_label']}) {_pop['entry_note']}")
            # 关键结构位摘要（最多2个）
            _lvls = _pop.get("key_levels", {})
            _lvl_strs = [f"{k}${v['price']:.0f}({v['dist_pct']:+.1f}%)"
                         for k, v in list(_lvls.items())[:3]]
            if _lvl_strs:
                print(f"│   结构: {' | '.join(_lvl_strs)}")

        # ── Flex 监控（技术+价格+配置）────────────────────────────────────
        _pos_cfg = real_positions.get(sym, {})
        _fs2 = check_flex_signals(a, spy_chg, et_h, et_m,
                                  position=_pos_cfg, portfolio_total=_portfolio_total,
                                  sym=sym)
        if _fs2["flex_reduce"] and _fs2["price_ok_reduce"]:
            print(f"│ 🔴Flex减仓 技术{_fs2['reduce_score']}/4 配置:{_fs2['alloc_vs_target']}")
        elif _fs2["flex_add"] and _fs2["price_ok_add"]:
            print(f"│ 🟢Flex加仓 技术{_fs2['add_score']}/4 配置:{_fs2['alloc_vs_target']}")
        elif _fs2["in_window"] and _fs2["alloc_pct"] > 0:
            if "超配" in _fs2["alloc_vs_target"] or "欠配" in _fs2["alloc_vs_target"]:
                print(f"│ ⚪ 配置:{_fs2['alloc_vs_target']}（等技术信号）")

        for _acct in ACCOUNTS:
            # 止损/止盈检查（始终执行，不受否决影响）
            _exit = check_exits(sym, a["cur"], hi=a["hi"], lo=a["lo"], acct=_acct, stocks=stocks)
            if _exit:
                print(f"│ 📊{_exit}")
                try:
                    _trace = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "sym": sym, "action": "exit", "acct": _acct,
                        "price": a["cur"], "rsi3": a["rsi3"], "hist": a["hist"],
                        "dvwap": a["dvwap"], "rs": round(rs, 2),
                        "macro_state": macro_state if 'macro_state' in dir() else "unknown",
                        "score": ps["avg"],
                    }
                    with open(os.path.join(_STOCK_BASE, "learning", "decision_trace.jsonl"), "a", encoding="utf-8") as _tf:
                        _tf.write(json.dumps(_trace) + "\n")
                except Exception:
                    pass
            # T1 新仓入场：全局否决通过 + post_open_plan 允许入场
            _pop_rec = (_pop.get("entry_rec") if _mins_open >= 30 else None)
            _entry_allowed = (not _veto and
                              (_pop_rec in ("ENTER_ADD1", "WATCH_SIGNAL") if _pop_rec else True))
            if _entry_allowed:
                _entry = try_enter(sym, a["cur"], a["vwap"], a["atr14"],
                                   rs, ps["avg"], signal_info, spy_chg,
                                   live_prices=live_prices,
                                   catalyst_strength=pm_catalyst, acct=_acct)
                if _entry:
                    print(f"│ 📊{_entry}")
                    try:
                        _trace = {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "sym": sym, "action": "enter", "acct": _acct,
                            "price": a["cur"], "rsi3": a["rsi3"], "hist": a["hist"],
                            "dvwap": a["dvwap"], "rs": round(rs, 2),
                            "macro_state": macro_state if 'macro_state' in dir() else "unknown",
                            "score": ps["avg"],
                        }
                        with open(os.path.join(_STOCK_BASE, "learning", "decision_trace.jsonl"), "a", encoding="utf-8") as _tf:
                            _tf.write(json.dumps(_trace) + "\n")
                    except Exception:
                        pass
            # T2/T3 加仓（全局否决 或 post_open 不允许则跳过）
            if _entry_allowed:
                _add = try_add_tranche(
                    sym, a["cur"], a["vwap"],
                    vol_ratio=round(a["vr"]/a["vp"], 2) if a.get("vp",0)>0 else 1.0,
                    rsi3=a["rsi3"],
                    hist=a["hist"],
                    qqq_5m=qqq5m,
                    acct=_acct
                )
                if _add:
                    print(f"│ 📊{_add}")

        # 对应杠杆ETF的止损（如果有配置）
        if sym in (lev_map or {}):
            lev_sym, lev_n = lev_map[sym]
            lev_a2 = snap(lev_sym)
            if lev_a2:
                lev_stop = lev_a2["cur"] * (stop/a["cur"])
                print(f"│ {lev_sym}({lev_n}x)对应止损: ${lev_stop:.2f}  "
                      f"（底层${stop:.2f}×{lev_n}倍折算）")
        print("└")
        print()

    # 收盘前强制平仓（15:55-16:00 ET）
    if 15*60+55 <= et_h*60+et_m <= 16*60:
        for _acct in ACCOUNTS:
            eod_msg = eod_close_all(live_prices, acct=_acct)
            if eod_msg:
                print(f"📊 [{_acct}] 收盘平仓：")
                print(eod_msg)
        print()

    # 近期模拟盘交易记录（base账号代表）
    trades = load_trade_history(4, acct="base")
    if trades:
        print("── 模拟盘近期操作(base) ──")
        for t in trades:
            sym_  = t.get("sym","?")
            act   = t.get("action","?")
            price = t.get("price","?")
            pnl   = f" {t['pnl_pct']:+.1f}%" if "pnl_pct" in t else ""
            tm    = t.get("time","")[:16].replace("T"," ")
            print(f"  {tm}  {sym_} {act} ${price}{pnl}")
        print()

    # 观察日志（所有关注标的，供盘后经验配对）
    try:
        _write_observation_log(stocks, spy_chg, vc, vt, qqq5m, macro_state)
    except Exception:
        pass

    # ── 🔬 期权链主力墙与关键价格防线日内监控 (Options Wall Alert Desk) ──
    try:
        for _sym, _a in (stocks or {}).items():
            if _sym == "TSM" and _a and "cur" in _a:
                _p = _a["cur"]
                # TSM Put Wall = $400, Call Wall = $450
                if _p <= 405.0:
                    print(f"\n🚨 [期权警戒] TSM 现价 ${_p:.2f} 逼近主力防守 Put Wall $400.00! 警惕机构防御破位风险！")
                elif _p >= 445.0:
                    print(f"\n🚀 [期权突破] TSM 现价 ${_p:.2f} 逼近主力阻力 Call Wall $450.00! 注意可能产生 Gamma 向上挤压！")
            elif _sym == "LITX" and _a and "cur" in _a:
                _p = _a["cur"]
                # LITX Trailing Stop at $110.0 (simulated stop or target trailing protection)
                if _p <= 112.0:
                    print(f"\n🚨 [止损防线] LITX 现价 ${_p:.2f} 逼近追踪止损利润保护区 ($110.00)！请准备执行利润保护！")
    except Exception as _e:
        print(f"[Option Wall Alert Error]: {_e}")

    # ── 热手/冷手追踪 ───────────────────────────────────────────
    from agents.poll_state import load_poll_state as _lps
    _old_state = _lps()
    _ts = calc_trading_state(real_positions, stocks, _old_state, _new_contradictions,
                             trading_mode=_trading_mode)
    if _ts["state"] == "冷手":
        print(f"\n📊 今日判断状态: 🔴 冷手（{_ts['reason']}）→ 建议减少新仓决策")
    elif _ts["state"] == "热手":
        print(f"📊 今日判断状态: 🟢 热手（{_ts['reason']}）")

    # 写入轮询状态（供下次轮询读取）
    try:
        from agents.poll_state import save_poll_state
        save_poll_state(stocks, real_positions, spy_chg, qqq_chg, vc, vt, macro_state, mkt, et_h, et_m,
                        persona_scores=_persona_scores, trading_state_info=_ts)
    except Exception:
        pass

    # 大师评分时间序列（每次 poll append，Soros建议：用于盘后准确率验证）
    if _persona_scores:
        try:
            _now_local = datetime.now()
            _date_str = _now_local.strftime("%Y-%m-%d")
            _time_str = f"{et_h:02d}:{_now_local.minute:02d}"
            _ms_log = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "learning",
                                   f"master_score_log_{_date_str}.jsonl")
            _entry = {
                "time": _time_str,
                "spy_chg": round(spy_chg, 2),
                "qqq_chg": round(qqq_chg, 2),
                "vix": round(vc, 1),
                "macro": macro_state,
                "scores": {
                    sym: {
                        "price": stocks[sym]["cur"] if stocks.get(sym) else 0,
                        "rs": round(stocks[sym]["chg"] - spy_chg, 2) if stocks.get(sym) else 0,
                        "master": ps,
                    }
                    for sym, ps in _persona_scores.items()
                }
            }
            with open(_ms_log, "a", encoding="utf-8") as _f:
                _f.write(json.dumps(_entry, ensure_ascii=False) + "\n")
                
            # 双写进入 SQLite WAL 数据库，防范高频 IO 并发锁冲突
            try:
                from stock_team.data_ingest.data_hub import write_master_score_db
                write_master_score_db(_date_str, _time_str, _entry)
            except Exception:
                pass
        except Exception:
            pass

    # ── intraday_snapshot（每轮追加 JSONL，合并 poll_state 新字段）──────────
    try:
        from stock_team.data_ingest.intraday_snapshot import write_snapshot_entry
        _snap_date = datetime.now().strftime("%Y-%m-%d")
        _vix_spike = (vc > 0 and _old_state and
                      _old_state.get("market_context", {}).get("vix", 0) > 0 and
                      vc / _old_state["market_context"]["vix"] - 1 > 0.10) or \
                     (qqq5m < -1.0)
        _session_min = max(0, et_h * 60 + et_m - 9 * 60 - 30)
        _snap_ps_path = os.path.join(
            ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "learning",
            f"poll_state_{_snap_date}.json")

        for _snap_sym, _snap_data in stocks.items():
            try:
                _snap_pm_path = os.path.join(
                    ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "findings",
                    f"premarket_summary_{_snap_date}_{_snap_sym}.json")
                _snap_pm = {}
                if os.path.exists(_snap_pm_path):
                    with open(_snap_pm_path, encoding="utf-8") as _f:
                        _snap_pm = json.load(_f)

                _master = _persona_scores.get(_snap_sym, {}) or {}
                _veto = _veto_details.get(_snap_sym)
                _stop_info = _stop_details.get(_snap_sym, {})
                _snap_price_now = {
                    "price":           float(_snap_data.get("cur", 0.0) or 0.0),
                    "chg_pct":         round(float(_snap_data.get("chg", 0.0) or 0.0), 2),
                    "vwap_dist_pct":   round(float(_snap_data.get("dvwap", 0.0) or 0.0), 2),
                    "rs_vs_spy":       round(float(_snap_data.get("chg", 0.0) or 0.0) - spy_chg, 2),
                    "rs_vs_sector":    0.0,
                    "rsi14_5m":        round(float(_snap_data.get("rsi14_5m", 50.0) or 50.0), 1),
                    "vol_ratio":       round(float(_snap_data.get("vol_ratio_5m", 1.0) or 1.0), 2),
                    "gate_status":     "未通过" if _veto else "已通过",
                    "gate_pass":       [] if _veto else ["all"],
                    "gate_block":      [_veto] if _veto else [],
                    "master_avg":      round(float(_master.get("avg", 0) or 0), 2) if _master else None,
                    "master_consensus": _master.get("consensus_code") if _master else None,
                    "stop":            round(float(_stop_info.get("stop", 0.0) or 0.0), 2),
                    "stop_type":       _stop_info.get("stop_type", "N/A"),
                }

                _post_cal = bool(_snap_pm.get("post_open_adj"))

                write_snapshot_entry(
                    sym=_snap_sym,
                    date=_snap_date,
                    price_now=_snap_price_now,
                    premarket_summary=_snap_pm,
                    session_min=_session_min,
                    post_open_calibrated=_post_cal,
                    prev_poll_state=_old_state or {},
                    vix_spike=bool(_vix_spike),
                    poll_state_path=_snap_ps_path,
                )
            except Exception:
                pass
    except Exception:
        pass

    # ── session_state missed_alerts 更新（每轮同步，纯脚本）──────────────────
    try:
        from stock_team.core.daily_plan_writer import update_session_state_from_alerts
        update_session_state_from_alerts(_snap_date)
    except Exception:
        pass

    # ── daily_dashboard HTML 生成 ────────────────────────────────────────────
    # 优化提示：将磁盘 HTML 写入限频在每 60 秒至多一次，既能保证本地 file:// 用户刷新时看到最新盘中价格与详情，又彻底避免了频繁 I/O 导致系统卡死。
    global _LAST_HTML_WRITE_TIME
    if "_LAST_HTML_WRITE_TIME" not in globals():
        _LAST_HTML_WRITE_TIME = 0.0
    _now_t = _time.time()
    if _now_t - _LAST_HTML_WRITE_TIME >= 60:
        try:
            from stock_team.server.dashboard_writer import write_dashboard
            write_dashboard(_snap_date)
            _LAST_HTML_WRITE_TIME = _now_t
        except Exception:
            pass

    # ── Phase B: 15:45 日内仓位减仓提醒 ─────────────────────────
    if et_h == 15 and 44 <= et_m <= 50:
        intraday_pos = [sym for sym, pos in real_positions.items()
                        if pos.get("mode") == "intraday" or
                        any(s.get("mode") == "intraday" for s in [pos] if isinstance(s, dict))]
        # 也检查 positions_mode.json
        try:
            _pm_path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "config", "positions_mode.json")
            if os.path.exists(_pm_path):
                _pm = json.load(open(_pm_path, encoding="utf-8"))
                for _sym, _md in _pm.items():
                    if isinstance(_md, dict) and _md.get("mode") == "intraday" and _sym in real_positions:
                        if _sym not in intraday_pos:
                            intraday_pos.append(_sym)
        except Exception:
            pass
        if intraday_pos:
            print(f"⏰ 【15:45 减仓建议（非指令）】以下持仓为日内模式，建议评估是否过夜：{', '.join(intraday_pos)}")
            for _sym in intraday_pos:
                _a = stocks.get(_sym)
                if _a:
                    _pos = real_positions.get(_sym, {})
                    _cost = float(_pos.get("cost", 0) or _pos.get("t1_cost", 0))
                    _pnl = (_a["cur"] - _cost) / _cost * 100 if _cost > 0 else 0
                    print(f"   {_sym}: 现${_a['cur']:.2f}  浮盈{_pnl:+.1f}%  {'过夜✅' if _pnl > 0 else '建议减仓⚠️'}")

    # 检查点提醒（基于 ET 时间）
    try:
        from stock_team.core.daily_script import load_script
        _script = load_script()
        _cp = _script.get("checkpoints", {})

        # 8:05-9:00：Node 0 未完成提醒
        if 8 <= et_h <= 9 and not _cp.get("node0_done"):
            print("⏰ 【检查点提醒】今日剧本未生成，建议运行晨间准备（说'早上好'）")

        # 10:00-10:05：盘中关注未更新提醒
        if et_h == 10 and et_m <= 5 and not _cp.get("intraday_update_done"):
            print("⏰ 【检查点提醒】开盘30分钟，请更新今日盘中关注标的（说'更新盘中关注'）")
    except Exception:
        pass

    print(f"快照已写入 knowledge/snapshots_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
    print(f"记录操作: 对话中说 '记录：买了/卖了 XXX $价格 因为...'")

def run_poll(symbols, sector_map=None, lev_map=None, cost_map=None, session=False, once=False):
    import time
    import threading
    
    global _LAST_TICK_TIME
    _LAST_TICK_TIME = time.time()

    def cpu_watchdog():
        global _LAST_TICK_TIME
        start_time = time.time()
        while True:
            time.sleep(5)
            # Give a very generous 300 seconds for the cold-start initial fetches, then 150 seconds for subsequent ticks
            current_elapsed = time.time() - start_time
            limit = 300 if current_elapsed < 300 else 150
            if time.time() - _LAST_TICK_TIME > limit:
                print(f"\n🚨 [Watchdog] ERROR: Poll loop is frozen/blocked for too long ({time.time() - _LAST_TICK_TIME:.1f}s > {limit}s)! Executing autonomous emergency shutdown...", flush=True)
                import os
                os._exit(9)

    if not once:
        watchdog_thread = threading.Thread(target=cpu_watchdog, name="PollWatchdog", daemon=True)
        watchdog_thread.start()

    poll_cfg = {}
    try:
        with open(os.path.join(BASE, "config", "poll_config.json"), encoding="utf-8") as f:
            poll_cfg = json.load(f)
    except Exception:
        poll_cfg = {}

    last_passive_poll_time = 0
    last_dashboard_cache_time = 0
    passive_interval = int(poll_cfg.get("passive_interval_seconds", 600))
    active_interval = int(poll_cfg.get("active_interval_seconds", 60))
    dashboard_cache_interval = int(poll_cfg.get("dashboard_cache_interval_seconds", 180))
    active_interval = max(15, active_interval)
    passive_interval = max(active_interval, passive_interval)
    dashboard_cache_interval = max(active_interval, dashboard_cache_interval)
    max_active_symbols = int(poll_cfg.get("max_active_symbols", 6))
    max_total_symbols = int(poll_cfg.get("max_total_symbols", 8))
    focus_stocks = []
    try:
        _focus_path = os.path.join(BASE, "config", "daily_focus.json")
        if os.path.exists(_focus_path):
            with open(_focus_path, encoding="utf-8") as f:
                focus_stocks = json.load(f).get("focus_stocks", [])
    except Exception:
        focus_stocks = []

    if poll_cfg.get("poll_scope", "daily_focus_only") == "daily_focus_only":
        focus_order = [str(s).upper().strip() for s in focus_stocks if str(s).strip()]
        symbols = [s for s in focus_order if s]
        if not symbols:
            print("⚠️ 今日关注为空，daily_focus_only 模式不启动默认轮询。")
            return
    
    if max_total_symbols > 0 and len(symbols) > max_total_symbols:
        focus_order = [s.upper() for s in focus_stocks]
        ordered = []
        for sym in [*focus_order, *symbols]:
            sym_u = str(sym).upper().strip()
            if sym_u and sym_u not in ordered:
                ordered.append(sym_u)
        symbols = ordered[:max_total_symbols]

    if once:
        print("\n[System] 启动单次无状态指标采集...")
        print(f"监控总标的列表: {', '.join(symbols)}")
        _LAST_TICK_TIME = time.time()
        try:
            real_positions = load_real_positions()
        except Exception:
            real_positions = {}
        try:
            _entry_decisions = _load_entry_decision()
        except Exception:
            _entry_decisions = {}
        active_syms, passive_syms = classify_poll_symbols(
            symbols,
            real_positions=real_positions,
            entry_decisions=_entry_decisions,
            focus_stocks=focus_stocks,
        )
        print(f"[Once] [单次 Tick] 正在拉取标的...")
        # Poll all symbols in single-run mode
        _run_poll_tick(
            symbols=symbols,
            sector_map=sector_map,
            lev_map=lev_map,
            cost_map=cost_map,
            session=session,
            active_syms=active_syms | passive_syms,
            passive_syms=set(),
            should_poll_passive=True
        )
        try:
            from stock_team.server.dashboard_cache import write_dashboard_cache
            from stock_team.server.dashboard_writer import build_dashboard_context
            _cache_date = datetime.now().strftime("%Y-%m-%d")
            _cache_ctx = build_dashboard_context(_cache_date, base_dir=BASE)
            write_dashboard_cache(BASE, _cache_ctx)
        except Exception:
            pass
        print("[Once] Single tick completed successfully.")
        return

    print("\n🚀 [System] 启动低负载盘中监控（双队列缓存版）...")
    print(f"活跃队列刷新频率: {active_interval}秒 | 被动队列刷新频率: {passive_interval}秒 | dashboard缓存: {dashboard_cache_interval}秒")
    print(f"监控总标的列表: {', '.join(symbols)}")
    print("支持 Ctrl+C 随时安全优雅退出。")
    
    try:
        while True:
            _LAST_TICK_TIME = time.time()

            # 1. 动态重新加载最新持仓和盘前入场决策
            try:
                real_positions = load_real_positions()
            except Exception:
                real_positions = {}
            try:
                _entry_decisions = _load_entry_decision()
            except Exception:
                _entry_decisions = {}
                
            # 2. 对 Symbols 进行分流
            active_syms, passive_syms = classify_poll_symbols(
                symbols,
                real_positions=real_positions,
                entry_decisions=_entry_decisions,
                focus_stocks=focus_stocks,
            )
            if max_active_symbols > 0 and len(active_syms) > max_active_symbols:
                focus_order = [s.upper() for s in focus_stocks]
                active_ordered = []
                for sym in [*focus_order, *symbols]:
                    sym_u = str(sym).upper().strip()
                    if sym_u in active_syms and sym_u not in active_ordered:
                        active_ordered.append(sym_u)
                keep_active = set(active_ordered[:max_active_symbols])
                passive_syms = set(passive_syms) | (set(active_syms) - keep_active)
                active_syms = keep_active
                    
            current_time = time.time()
            should_poll_passive = (current_time - last_passive_poll_time) >= passive_interval
            
            print(f"\n" + "="*80)
            print(f"⏰ [轮询 Tick] 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 活跃标的(10s刷新): {list(active_syms)}")
            if should_poll_passive:
                print(f"💤 被动标的(3m间隔已满，本次刷新): {list(passive_syms)}")
            else:
                print(f"💤 被动标的(缓存复用中): {list(passive_syms)}")
            print("="*80)
            
            # 3. 运行单个 Tick
            _run_poll_tick(
                symbols=symbols,
                sector_map=sector_map,
                lev_map=lev_map,
                cost_map=cost_map,
                session=session,
                active_syms=active_syms,
                passive_syms=passive_syms,
                should_poll_passive=should_poll_passive
            )

            if (current_time - last_dashboard_cache_time) >= dashboard_cache_interval:
                try:
                    from stock_team.server.dashboard_cache import write_dashboard_cache
                    from stock_team.server.dashboard_writer import build_dashboard_context
                    _cache_date = datetime.now().strftime("%Y-%m-%d")
                    _cache_ctx = build_dashboard_context(_cache_date, base_dir=BASE)
                    write_dashboard_cache(BASE, _cache_ctx)
                    last_dashboard_cache_time = current_time
                except Exception:
                    pass
            
            if should_poll_passive:
                last_passive_poll_time = current_time
                
            # 4. 睡眠等待下一个 Tick
            time.sleep(active_interval)
            
    except KeyboardInterrupt:
        print("\n👋 收到退出信号 (Ctrl+C)，盘中轮询已安全优雅终止。")

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))

def load_config():
    """自动从 config/ 读取所有配置，不需要命令行参数"""
    cfg_dir = os.path.join(BASE, "config")

    # 轮询配置
    poll_cfg = json.load(open(os.path.join(cfg_dir, "poll_config.json"), encoding="utf-8"))
    symbols   = poll_cfg.get("default_symbols", [])
    sector_map = poll_cfg.get("sector_map", {})

    # 杠杆映射
    lev_map = {}
    lev_cfg_path = os.path.join(cfg_dir, "leveraged_pairs.json")
    if os.path.exists(lev_cfg_path):
        lev_cfg = json.load(open(lev_cfg_path, encoding="utf-8"))
        for base, info in lev_cfg.items():
            if base.startswith("_"): continue
            lev_map[base] = (info["sym"], info["leverage"])

    # 持仓成本
    cost_map = {}
    pos_path = os.path.join(cfg_dir, "positions.json")
    if os.path.exists(pos_path):
        pos_cfg = json.load(open(pos_path, encoding="utf-8"))
        for sym, info in pos_cfg.get("positions", {}).items():
            cost_map[sym] = float(info["cost"])

    return symbols, sector_map, lev_map, cost_map

def ask_missing_info(lev_map, cost_map):
    """检查是否有持仓但缺成本信息，如果是则提示（不中断运行）"""
    missing = []
    for base, (lev_sym, _) in lev_map.items():
        if lev_sym not in cost_map:
            missing.append(lev_sym)
    if missing:
        print(f"[WARNING] 以下持仓未配置成本价，持仓监控功能未启用：{', '.join(missing)}")
        print(f"   告诉我持仓成本即可自动更新，例如：'记录：持有 AAOX 成本 $69'")
        print()

def update_position(sym, cost, shares=None, date=None):
    """更新持仓配置（供外部调用）"""
    _base = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
    pos_path = os.path.join(_base, "config", "positions.json")
    pos_cfg = json.load(open(pos_path, encoding="utf-8"))
    pos_cfg["positions"][sym] = {
        "cost": cost,
        "shares": shares or 0,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
    }
    json.dump(pos_cfg, open(pos_path, "w", encoding="utf-8"), indent=2)
    print(f"[Config] {sym} 持仓已更新: 成本${cost} 股数{shares or '未知'}")

def remove_position(sym):
    """清除持仓（止损/止盈出场后调用）"""
    _base = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
    pos_path = os.path.join(_base, "config", "positions.json")
    pos_cfg = json.load(open(pos_path, encoding="utf-8"))
    if sym in pos_cfg["positions"]:
        del pos_cfg["positions"][sym]
        json.dump(pos_cfg, open(pos_path, "w", encoding="utf-8"), indent=2)
        print(f"[Config] {sym} 持仓已清除")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自动轮询 - 从config/读取配置")
    parser.add_argument("symbols", nargs="*", help="覆盖默认标的列表（可选）")
    parser.add_argument("--add-position", nargs=2, metavar=("SYM", "COST"),
                        help="添加持仓: --add-position AAOX 69")
    parser.add_argument("--remove-position", metavar="SYM",
                        help="清除持仓: --remove-position AAOX")
    parser.add_argument("--session", action="store_true",
                        help="会话模式：信号/场景变化写入 session_manager 队列")
    parser.add_argument("--once", action="store_true",
                        help="单次执行模式：运行一轮指标后立即退出")
    args = parser.parse_args()

    # 持仓操作
    if args.add_position:
        update_position(args.add_position[0], float(args.add_position[1]))
        sys.exit(0)
    if args.remove_position:
        remove_position(args.remove_position)
        sys.exit(0)

    # 自动加载配置
    symbols, sector_map, lev_map, cost_map = load_config()

    # 允许命令行覆盖标的列表
    if args.symbols:
        symbols = args.symbols

    # 提示缺少的信息（不阻断运行）
    ask_missing_info(lev_map, cost_map)

    run_poll(symbols, sector_map=sector_map, lev_map=lev_map, cost_map=cost_map,
             session=args.session, once=args.once)
