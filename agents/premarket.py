"""
盘前分析模块 — 每天 9:00-9:25 ET 运行
输出：~/stock_team/premarket_analysis_{date}.json
  每只股票：gap幅度/原因/板块联动/期货方向/预测场景/入场区间/入场确认条件

用法：python3.12 agents/premarket.py [SYM1 SYM2 ...]
     不传参数则读取 config/poll_config.json 中 default_symbols
"""
import sys, os, json, requests, xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import atomic_write_json
import yfinance as yf

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_DIR   = os.path.join(BASE, "config")
OUT_TPL   = os.path.join(BASE, "premarket_analysis_{}.json")

# ── 场景入场条件模板 ────────────────────────────────────────
SCENARIO_ENTRIES = {
    "A": {
        "name":    "强势突破",
        "icon":    "🟢",
        "watch":   "放量突破日内/昨日高点",
        "confirm": "量比>1.3x + 突破K线收盘站上压力位",
        "sizing":  "正常×1.5",
        "stop":    "突破K线低点 - ATR×0.3",
    },
    "B": {
        "name":    "VWAP回踩",
        "icon":    "🔵",
        "watch":   "回踩至VWAP ±1%",
        "confirm": "缩量(<0.8x均量) + 3连阳 + 5分钟涨>0.3%",
        "sizing":  "正常",
        "stop":    "回踩低点 - ATR×0.5",
    },
    "C": {
        "name":    "横盘蓄力",
        "icon":    "🟡",
        "watch":   "区间上沿突破",
        "confirm": "量比>1.5x + 收盘站上上沿",
        "sizing":  "正常",
        "stop":    "区间中值",
    },
    "D": {
        "name":    "冲高回落",
        "icon":    "🟠",
        "watch":   "从日高回落>3%后止跌区（日低±2%）",
        "confirm": "量缩(<0.8x) + 3连阳 + 下影出现",
        "sizing":  "半仓",
        "stop":    "止跌低点 - ATR×0.5",
    },
    "E": {
        "name":    "弱势反弹",
        "icon":    "⚪",
        "watch":   "日低区间 ±1%",
        "confirm": "下影出现 + 3连阳 + 量不继续放大",
        "sizing":  "1/4仓",
        "stop":    "日低下方 ATR×0.3",
    },
    "F": {
        "name":    "跳水下跌",
        "icon":    "🔴",
        "watch":   "不操作",
        "confirm": "等止跌信号出现再重新评估",
        "sizing":  "0",
        "stop":    "—",
    },
    "G": {
        "name":    "板块强股弱",
        "icon":    "🟣",
        "watch":   "当个股RS vs 板块转正",
        "confirm": "RS>0 + 3连阳 + 板块ETF继续强",
        "sizing":  "半仓",
        "stop":    "VWAP - ATR×0.3",
    },
    "H": {
        "name":    "独立领涨",
        "icon":    "💎",
        "watch":   "回踩VWAP或5分钟MA",
        "confirm": "缩量 + 3连阳 + RS继续强于板块",
        "sizing":  "正常×1.5",
        "stop":    "VWAP - ATR×0.3",
    },
}

# ── 新闻情绪关键词（细化催化剂类型）────────────────────────
NEWS_KEYWORDS = {
    "earnings_beat":     ["beat", "earnings", "EPS", "revenue beat", "guidance raise", "profit", "record"],
    "strategic_invest":  ["stake", "investment", "acqui", "buys", "discloses", "reveals holding", "strategic"],
    "analyst_upgrade":   ["upgrade", "target raised", "overweight", "outperform", "initiat", "buy rating"],
    "product_catalyst":  ["800G", "400G", "ramp", "design win", "capacity", "demand", "shipment", "volume"],
    "announcement":      ["contract", "partnership", "deal", "awarded", "wins", "selected", "agreement"],
    "sector_driven":     ["semiconductor", "AI", "quantum", "optical", "space", "defense", "data center"],
    "negative":          ["miss", "downgrade", "cut", "guidance cut", "loss", "warning", "disappoint"],
    "macro":             ["Fed", "rate", "inflation", "GDP", "tariff", "trade", "China", "geopolit"],
}

# 催化剂强度：越高越可能持续上涨而非 sell the news
CATALYST_STRENGTH = {
    "strategic_invest":  3,  # 战略入股 → 强，不容易sell the news
    "product_catalyst":  3,  # 产品/需求 → 强，业务基本面
    "earnings_beat":     2,  # 财报超预期 → 中，已priced in风险
    "announcement":      2,  # 合同/合作 → 中
    "analyst_upgrade":   1,  # 分析师 → 弱，常被sell the news
    "sector_driven":     1,  # 板块带动 → 弱，随板块波动
    "macro":             1,
    "negative":          0,
    "neutral":           1,
}

def fetch_google_news(sym, company_name=""):
    """从 Google News RSS 抓取最新新闻，返回 (headlines, raw_items)"""
    query = f"{sym} {company_name} stock".strip()
    url   = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return [], []
        root  = ET.fromstring(r.text)
        items = root.findall(".//item")[:5]
        headlines, raw = [], []
        for item in items:
            title = item.find("title")
            pub   = item.find("pubDate")
            src   = item.find("source")
            if title is not None and title.text:
                headlines.append(title.text)
                raw.append({
                    "title":  title.text,
                    "date":   pub.text[:16] if pub is not None else "",
                    "source": src.text if src is not None else "",
                })
        return headlines, raw
    except Exception:
        return [], []

def classify_news(headlines):
    """返回 (news_type, catalyst_strength, matched_keywords)"""
    text   = " ".join(headlines).lower()
    scores = {}
    for k, kws in NEWS_KEYWORDS.items():
        matched = [kw for kw in kws if kw.lower() in text]
        scores[k] = len(matched)
    top = max(scores, key=scores.get)
    news_type = top if scores[top] > 0 else "neutral"
    strength  = CATALYST_STRENGTH.get(news_type, 1)
    matched   = [kw for kw in NEWS_KEYWORDS.get(news_type, []) if kw.lower() in text]
    return news_type, strength, matched

def predict_scenario(gap_pct, news_type, catalyst_strength, sector_gap, pre_vol_ratio):
    """
    根据盘前gap/新闻催化剂强度/板块/量推断今日最可能场景
    catalyst_strength: 0-3（3=战略/产品级，1=分析师/板块，0=负面）
    返回 (predicted_scenario, confidence, reasoning)
    """
    reasons = []

    # 大幅高开（≥8%）
    if gap_pct >= 8:
        if catalyst_strength >= 3:
            # 强催化剂（战略入股/产品需求）→ 高开可持续，不容易回落
            reasons.append(f"高开{gap_pct:+.1f}%+强催化剂({news_type})→上涨可持续，关注VWAP回踩入场")
            return "B", "高", " | ".join(reasons)
        elif catalyst_strength == 2 and sector_gap >= 2:
            reasons.append(f"高开{gap_pct:+.1f}%+中等催化剂+板块共振→可能持续，但警惕回踩")
            return "A", "中", " | ".join(reasons)
        elif catalyst_strength <= 1:
            reasons.append(f"高开{gap_pct:+.1f}%+弱催化剂({news_type})→sell the news风险高，等回踩")
            return "D", "高", " | ".join(reasons)
        else:
            reasons.append(f"高开{gap_pct:+.1f}%+催化剂中等→冲高回落后可能V型")
            return "D", "中", " | ".join(reasons)

    # 中幅高开（3-8%）
    elif gap_pct >= 3:
        if catalyst_strength >= 2 and sector_gap >= 1.5:
            reasons.append(f"高开{gap_pct:+.1f}%+催化剂{catalyst_strength}/3+板块同涨→强势，关注VWAP")
            return "A", "中", " | ".join(reasons)
        elif catalyst_strength >= 3:
            reasons.append(f"高开{gap_pct:+.1f}%+强催化剂→有支撑，回踩VWAP可入")
            return "B", "中", " | ".join(reasons)
        elif sector_gap >= 1.5:
            reasons.append(f"高开{gap_pct:+.1f}%+板块同涨→可持续，关注VWAP")
            return "A", "中", " | ".join(reasons)
        else:
            reasons.append(f"高开{gap_pct:+.1f}%板块弱+催化剂弱→可能回踩VWAP")
            return "B", "中", " | ".join(reasons)

    # 小幅高开/平开
    elif gap_pct >= -2:
        if news_type == "negative" or catalyst_strength == 0:
            reasons.append("负面消息+平开→弱势整理")
            return "C", "中", " | ".join(reasons)
        reasons.append(f"平开({gap_pct:+.1f}%)→等待方向选择")
        return "C", "低", " | ".join(reasons)

    # 低开
    elif gap_pct >= -5:
        reasons.append(f"低开{gap_pct:+.1f}%→关注日低支撑，可能弱反弹")
        return "E", "中", " | ".join(reasons)

    # 大幅低开
    else:
        reasons.append(f"低开{gap_pct:+.1f}%→跳水下跌，不操作")
        return "F", "高", " | ".join(reasons)

def fetch_month_context(sym, tick, hd60, spy_pre_chg=0):
    """
    补充近期上下文分析：价格表现、技术位、催化剂时间线、成交量趋势。
    任何子字段失败均捕获异常返回 None，不影响整体。
    """
    result = {
        "perf_1m": None, "perf_3m": None, "rs_1m": None,
        "hi_1m": None, "lo_1m": None,
        "ma20": None, "ma50": None, "above_ma20": None, "above_ma50": None,
        "tech_stage": None,
        "catalyst_timeline": [],
        "vol_trend": None,
    }

    # ── 当前价格 ────────────────────────────────────────────────
    cur = None
    try:
        info = tick.info
        cur = info.get("preMarketPrice") or info.get("regularMarketPrice") or info.get("postMarketPrice")
        if cur is None and hd60 is not None and len(hd60) > 0:
            cur = float(hd60["Close"].iloc[-1])
    except Exception:
        pass

    if cur is None:
        return result

    # ── 价格表现 ────────────────────────────────────────────────
    try:
        if hd60 is not None and len(hd60) >= 21:
            result["perf_1m"] = round((cur / float(hd60["Close"].iloc[-21]) - 1) * 100, 1)
    except Exception:
        pass

    try:
        hd3m = tick.history(period="90d")
        if len(hd3m) >= 63:
            result["perf_3m"] = round((cur / float(hd3m["Close"].iloc[-63]) - 1) * 100, 1)
    except Exception:
        pass

    try:
        if result["perf_1m"] is not None:
            # spy_pre_chg 是当日盘前变动，用作月度近似对比（非精确，但实用）
            # 更精确应拉 SPY 历史，这里以传入的当日方向做粗略参考
            spy_1m = spy_pre_chg  # 保留接口，调用方可传更精准的月度数据
            result["rs_1m"] = round(result["perf_1m"] - spy_1m, 1)
    except Exception:
        pass

    # ── 关键技术位 ──────────────────────────────────────────────
    try:
        if hd60 is not None and len(hd60) >= 21:
            result["hi_1m"] = round(float(hd60["High"].iloc[-21:].max()), 2)
            result["lo_1m"] = round(float(hd60["Low"].iloc[-21:].min()), 2)
    except Exception:
        pass

    ma20 = None
    try:
        if hd60 is not None and len(hd60) >= 20:
            ma20 = round(float(hd60["Close"].rolling(20).mean().iloc[-1]), 2)
            result["ma20"] = ma20
    except Exception:
        pass

    ma50 = None
    try:
        if hd60 is not None and len(hd60) >= 50:
            ma50 = round(float(hd60["Close"].rolling(50).mean().iloc[-1]), 2)
            result["ma50"] = ma50
    except Exception:
        pass

    try:
        result["above_ma20"] = bool(cur > ma20) if ma20 is not None else None
    except Exception:
        pass

    try:
        result["above_ma50"] = bool(cur > ma50) if ma50 is not None else None
    except Exception:
        pass

    # ── 技术状态 ────────────────────────────────────────────────
    try:
        if ma20 is not None and ma50 is not None:
            if cur > ma20 > ma50:
                result["tech_stage"] = "上升趋势"
            elif cur < ma20 < ma50:
                result["tech_stage"] = "下降趋势"
            else:
                result["tech_stage"] = "整理"
        elif ma20 is not None:
            result["tech_stage"] = "上升趋势" if cur > ma20 else "下降趋势"
    except Exception:
        pass

    # ── 催化剂时间线（近30天新闻，最多5条）────────────────────
    try:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        company_name = ""
        try:
            company_name = tick.info.get("shortName", "") or ""
        except Exception:
            pass
        _, raw_items = fetch_google_news(sym, company_name)
        timeline = []
        for item in raw_items:
            try:
                date_str_raw = item.get("date", "")
                if not date_str_raw:
                    timeline.append({"date": "", "title": item["title"][:100], "source": item.get("source", "")})
                    continue
                # pubDate 格式示例: "Tue, 13 May 2026 10:00:00 GMT"
                from email.utils import parsedate_to_datetime
                pub_dt = parsedate_to_datetime(date_str_raw)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt >= cutoff:
                    timeline.append({
                        "date":   pub_dt.strftime("%Y-%m-%d"),
                        "title":  item["title"][:100],
                        "source": item.get("source", ""),
                    })
            except Exception:
                timeline.append({"date": "", "title": item.get("title", "")[:100], "source": item.get("source", "")})
        result["catalyst_timeline"] = timeline[:5]
    except Exception:
        result["catalyst_timeline"] = []

    # ── 成交量趋势 ──────────────────────────────────────────────
    try:
        if hd60 is not None and len(hd60) >= 20:
            vol5  = float(hd60["Volume"].iloc[-5:].mean())
            vol20 = float(hd60["Volume"].iloc[-20:].mean())
            if vol20 > 0:
                ratio = vol5 / vol20
                if ratio > 1.15:
                    result["vol_trend"] = "放大"
                elif ratio < 0.85:
                    result["vol_trend"] = "缩小"
                else:
                    result["vol_trend"] = "平稳"
    except Exception:
        pass

    return result


def analyze_stock(sym, sector_ref, spy_pre_chg, futures_chg):
    tick = yf.Ticker(sym)
    info = tick.info

    # 盘前价格
    pre_price = info.get("preMarketPrice") or info.get("postMarketPrice")
    prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
    if not pre_price or not prev_close:
        h = tick.history(period="2d")
        prev_close = float(h["Close"].iloc[-2]) if len(h) >= 2 else None
        pre_price  = float(h["Close"].iloc[-1]) if len(h) >= 1 else None

    if not pre_price or not prev_close:
        return None

    gap_pct = (pre_price - prev_close) / prev_close * 100

    # 盘前量
    pre_vol = info.get("preMarketVolume") or 0
    avg_vol = info.get("averageVolume") or 1
    pre_vol_ratio = pre_vol / avg_vol if avg_vol > 0 else 0

    # 新闻（Google News RSS 优先，yfinance 兜底）
    company_name = info.get("shortName", "") or info.get("longName", "")
    headlines, news_raw = fetch_google_news(sym, company_name)
    if not headlines:
        try:
            yf_news = tick.news or []
            headlines = [n.get("content", {}).get("title", "") if isinstance(n.get("content"), dict)
                         else n.get("title", "") for n in yf_news[:5]]
            headlines = [h for h in headlines if h]
            news_raw  = [{"title": h, "date": "", "source": "yfinance"} for h in headlines]
        except Exception:
            headlines, news_raw = [], []

    news_type, catalyst_strength, matched_kw = classify_news(headlines)
    top_headline = headlines[0] if headlines else "无新闻"

    # 板块参照
    sector_gap = 0
    if sector_ref:
        try:
            s_info = yf.Ticker(sector_ref).info
            s_pre  = s_info.get("preMarketPrice") or s_info.get("regularMarketPrice")
            s_prev = s_info.get("regularMarketPreviousClose")
            if s_pre and s_prev:
                sector_gap = (s_pre - s_prev) / s_prev * 100
        except Exception:
            pass

    # ATR（改用 60 日数据）
    try:
        hd60 = tick.history(period="60d")
        atr = float((hd60["High"] - hd60["Low"]).rolling(14).mean().iloc[-1])
    except Exception:
        hd60 = None
        atr = abs(gap_pct / 100 * pre_price)

    # 近期上下文
    month_context = fetch_month_context(sym, tick, hd60, spy_pre_chg)

    # 预测场景（传入催化剂强度）
    pred_scene, confidence, reasoning = predict_scenario(
        gap_pct, news_type, catalyst_strength, sector_gap, pre_vol_ratio
    )
    scene_info = SCENARIO_ENTRIES[pred_scene]

    return {
        # ── 盘前已知（静态，不会被后续覆盖）──────────────────────
        "symbol":             sym,
        "prev_close":         round(prev_close, 2),
        "pre_price":          round(pre_price, 2),
        "gap_pct":            round(gap_pct, 2),
        "pre_vol_ratio":      round(pre_vol_ratio, 2),
        "news_type":          news_type,
        "catalyst_strength":  catalyst_strength,
        "matched_keywords":   matched_kw[:3],
        "top_headline":       top_headline[:100],
        "all_headlines":      [n["title"][:80] for n in news_raw[:3]],
        "news_sources":       [n.get("source","") for n in news_raw[:3]],
        "sector_ref":         sector_ref or "—",
        "sector_gap":         round(sector_gap, 2),
        "spy_pre":            round(spy_pre_chg, 2),
        "futures_nq":         round(futures_chg, 2),
        "atr":                round(atr, 2),
        "pred_scene":         pred_scene,
        "confidence":         confidence,
        "reasoning":          reasoning,
        "scene_name":         scene_info["name"],
        "scene_icon":         scene_info["icon"],

        # ── 待观察期逐步填充（初始为 null）────────────────────────
        "actual_open":        None,   # 9:30 真实开盘价
        "opening_hi":         None,   # 观察期内最高点（滚动更新）
        "opening_lo":         None,   # 观察期内最低点（滚动更新）
        "vwap_current":       None,   # 当前VWAP（滚动更新）
        "watch_zone":         None,   # 基于真实VWAP计算的区间（滚动更新）
        "entry_confirm":      None,   # 含具体价位的入场条件（观察期结束后填充）
        "sizing":             None,   # 最终仓位建议（actual_scene确认后填充）
        "stop_basis":         None,   # 止损基准（actual_scene确认后填充）
        "macro_at_open":      None,   # 开盘时的 SPY/QQQ/VIX（第1轮填充）
        "actual_scene":       None,   # 实际场景A-H（观察期结束时填充）
        "pred_vs_actual":     None,   # 预测 vs 实际（观察期结束时填充）
        "obs_minutes":        0,      # 已观察分钟数（每轮更新）
        "obs_complete":       False,  # 观察期是否结束
        "month_context":      month_context,
    }

def run(symbols=None):
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = OUT_TPL.format(date_str)

    # 读取配置
    cfg = json.load(open(os.path.join(CFG_DIR, "poll_config.json")))
    sector_map = cfg.get("sector_map", {})
    if not symbols:
        symbols = cfg.get("default_symbols", [])

    # 大盘盘前
    spy_pre_chg, futures_chg = 0, 0
    try:
        spy_info = yf.Ticker("SPY").info
        spy_pre  = spy_info.get("preMarketPrice")
        spy_prev = spy_info.get("regularMarketPreviousClose")
        if spy_pre and spy_prev:
            spy_pre_chg = (spy_pre - spy_prev) / spy_prev * 100
    except Exception:
        pass
    try:
        nq = yf.Ticker("NQ=F").info
        nq_pre  = nq.get("regularMarketPrice") or nq.get("preMarketPrice")
        nq_prev = nq.get("regularMarketPreviousClose")
        if nq_pre and nq_prev:
            futures_chg = (nq_pre - nq_prev) / nq_prev * 100
    except Exception:
        pass

    now_utc = datetime.now(timezone.utc)
    et_h = (now_utc.hour - 4) % 24
    et_m = now_utc.minute

    print(f"╔{'═'*56}╗")
    print(f"║  盘前分析  {date_str}  {et_h:02d}:{et_m:02d} ET{' '*23}║")
    print(f"╚{'═'*56}╝")
    print(f"SPY盘前: {spy_pre_chg:+.2f}%  NQ期货: {futures_chg:+.2f}%")
    env = "顺风✅" if spy_pre_chg>0.3 and futures_chg>0.3 else \
          "逆风❌" if spy_pre_chg<-0.5 or futures_chg<-0.5 else "中性"
    print(f"大盘环境: {env}\n")

    results = {}
    for sym in symbols:
        sec = sector_map.get(sym, {})
        sec_ref = sec.get("ref") if isinstance(sec, dict) else None
        print(f"分析 {sym}...", end=" ", flush=True)
        r = analyze_stock(sym, sec_ref, spy_pre_chg, futures_chg)
        if r:
            results[sym] = r
            icon = r["scene_icon"]
            print(f"{icon}{r['scene_name']}({r['confidence']})  gap{r['gap_pct']:+.1f}%")
        else:
            print("数据不足，跳过")

    # 输出汇总
    print(f"\n{'─'*58}")
    print(f"{'标的':<6} {'场景':<12} {'Gap':>6} {'板块':>6} {'新闻类型':<16} {'置信'}")
    strength_bar = lambda s: "★"*s + "☆"*(3-s)
    print(f"{'─'*70}")
    for sym, r in results.items():
        cs = r.get("catalyst_strength", 1)
        print(f"{sym:<6} {r['scene_icon']}{r['scene_name']:<10} {r['gap_pct']:>+5.1f}% "
              f"{r['sector_gap']:>+5.1f}% 催化剂{strength_bar(cs)}  {r['news_type']:<18} {r['confidence']}")

    print(f"\n{'─'*70}")
    print("入场预设（含催化剂详情）:")
    for sym, r in results.items():
        cs   = r.get("catalyst_strength", 1)
        kws  = r.get("matched_keywords", [])
        hdls = r.get("all_headlines", [r["top_headline"]])
        srcs = r.get("news_sources", [])
        if r["pred_scene"] != "F":
            print(f"\n  [{sym}] {r['scene_icon']}{r['scene_name']}  催化剂强度:{strength_bar(cs)}({cs}/3)")
            print(f"    Gap: {r['gap_pct']:+.1f}%  {r['reasoning']}")
            print(f"    催化剂关键词: {', '.join(kws) if kws else '无'}")
            for i, (h, s) in enumerate(zip(hdls, srcs or [""]*len(hdls))):
                print(f"    新闻{i+1}[{s}]: {h}")
            print(f"    观察区: {r['watch_zone']}")
            print(f"    入场确认: {r['entry_confirm']}")
            print(f"    仓位: {r['sizing']}  止损: {r['stop_basis']}")

    # 保存
    output = {
        "date": date_str,
        "generated_at": now_utc.isoformat(),
        "macro": {"spy_pre": spy_pre_chg, "nq_futures": futures_chg, "env": env},
        "stocks": results,
        "scenario_templates": SCENARIO_ENTRIES,
    }
    atomic_write_json(output, out_path, indent=2)
    print(f"\n✅ 已保存至 {out_path}")

    # ── 5维扫描（集成）────────────────────────────────────────
    try:
        from agents.market_scanner import scan_all_sectors
        print(f"\n{'─'*58}")
        print("5维市场扫描（强/弱/震荡×板块热度×催化剂×拥挤度）")
        scan_all_sectors(symbols, verbose=True)
    except Exception as e:
        print(f"[5维扫描跳过] {e}")

    return results

if __name__ == "__main__":
    syms = sys.argv[1:] if len(sys.argv) > 1 else None
    run(syms)
