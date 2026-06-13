"""
盘前分析模块 — 每天 9:00-9:25 ET 运行
输出：~/stock_team/premarket_analysis_{date}.json
  每只股票：gap幅度/原因/板块联动/期货方向/预测场景/入场区间/入场确认条件

用法：python3.12 agents/premarket.py [SYM1 SYM2 ...]
     不传参数则读取 config/poll_config.json 中 default_symbols
"""
import sys, os, json, requests, xml.etree.ElementTree as ET
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
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

# 板块领头羊映射：若领头羊今日大涨，板块催化剂升级为3
# key=目标股，value=list of (领头羊代码, 阈值%)
SECTOR_LEADERS = {
    "MSTR":  [("COIN", 5.0), ("BTC-USD", 4.0), ("MARA", 5.0)],
    "MARA":  [("COIN", 5.0), ("BTC-USD", 4.0), ("MSTR", 5.0)],
    "RIOT":  [("COIN", 5.0), ("BTC-USD", 4.0)],
    "RGTI":  [("IONQ", 5.0), ("QBTS", 5.0), ("QUBT", 5.0)],
    "QBTS":  [("IONQ", 5.0), ("RGTI", 5.0)],
    "IONQ":  [("RGTI", 5.0), ("QBTS", 5.0)],
    "IREN":  [("COIN", 5.0), ("BTC-USD", 4.0)],
    "CRWV":  [("NVDA", 4.0), ("SMCI", 5.0)],
    "OKLO":  [("SMR", 5.0), ("CCJ", 4.0)],
    "SMR":   [("OKLO", 5.0), ("CCJ", 4.0)],
}

def check_sector_leader_gap(sym):
    """检查板块领头羊是否今日大涨，若是则返回板块催化剂强度3"""
    leaders = SECTOR_LEADERS.get(sym, [])
    fired = []
    for leader_sym, threshold in leaders:
        try:
            info = yf.Ticker(leader_sym).info
            pre  = info.get("preMarketPrice") or info.get("regularMarketPrice")
            prev = info.get("regularMarketPreviousClose")
            if pre and prev:
                chg = (pre - prev) / prev * 100
                if chg >= threshold:
                    fired.append(f"{leader_sym}+{chg:.1f}%")
        except Exception:
            continue
    return fired  # 非空则板块催化剂激活

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

    # 板块领头羊催化剂（层2）：若板块龙头大涨，覆盖个股弱催化剂
    sector_leader_fired = check_sector_leader_gap(sym)
    if sector_leader_fired and catalyst_strength < 3:
        catalyst_strength = 3  # 板块级别催化剂升级为最强
        if news_type == "sector_driven" or news_type == "neutral":
            news_type = "sector_leader"  # 标记为板块领头羊驱动
        matched_kw = matched_kw + [f"板块领头羊:{','.join(sector_leader_fired)}"]

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

    # 财报日历检查
    earnings_warning = None
    try:
        cal = tick.calendar
        if cal is not None and not cal.empty:
            # calendar 通常是 DataFrame，第一列是最近财报日
            import pandas as pd
            if isinstance(cal, pd.DataFrame):
                dates = cal.columns.tolist() if cal.shape[0] == 0 else []
                # Try getting Earnings Date from index
                for col in cal.columns:
                    val = cal[col].iloc[0] if len(cal) > 0 else None
                    if val is not None:
                        try:
                            from datetime import datetime, timedelta
                            ed = pd.Timestamp(val)
                            days_to = (ed - pd.Timestamp.now()).days
                            if 0 <= days_to <= 7:
                                earnings_warning = f"⚠️ 财报在{days_to}天后({ed.strftime('%m-%d')})"
                            elif -3 <= days_to < 0:
                                earnings_warning = f"⚠️ 刚发布财报({ed.strftime('%m-%d')})"
                            break
                        except Exception:
                            pass
    except Exception:
        pass

    # 盘前模式预测（Livermore: 盘前就决定今日模式）
    predicted_mode = "swing"  # default
    mode_reason = "默认波段"
    if gap_pct >= 5 and catalyst_strength <= 1:
        predicted_mode = "intraday"
        mode_reason = f"高开{gap_pct:.1f}%+弱催化剂→高开分发风险，日内出场"
    elif pred_scene == "D":  # 冲高回落
        predicted_mode = "intraday"
        mode_reason = "场景D冲高回落→日内出场"
    elif catalyst_strength >= 3:
        predicted_mode = "swing"
        mode_reason = f"催化剂★★★→波段持有"
    elif gap_pct >= 3 and sector_gap >= 2:
        predicted_mode = "swing"
        mode_reason = "高开+板块共振→波段"

    # 更新 positions_mode.json
    try:
        mode_path = os.path.join(BASE, "config", "positions_mode.json")
        if os.path.exists(mode_path):
            modes = json.load(open(mode_path, encoding="utf-8"))
            if sym in modes or True:  # update for any analyzed symbol
                modes[sym] = {"mode": predicted_mode, "reason": mode_reason}
                json.dump(modes, open(mode_path, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass

    # 直觉评分（非阻塞）
    intuition_line = None
    try:
        from agents.intuition_agent import get_intuition_for_premarket
        intuition_line = get_intuition_for_premarket(
            sym, gap_pct=gap_pct,
            peer_chg=sector_gap,
            short_pct=info.get("shortPercentOfFloat", 0) * 100,
            catalyst_strength=catalyst_strength,
        )
    except Exception:
        pass

    res_dict = {
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
        # NOTE: pred_scene 仅作初始参考，不作操作依据（无效预测已降级）
        # 向后兼容保留字段名，但标签在输出中标注"参考"
        "pred_scene":         pred_scene,   # 参考场景（非预测），实际操作以 actual_scene 为准
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
        "intuition_line":     intuition_line,
        "unified_confidence": None,  # 占位，poll.py 运行时为持仓标的填充
        "earnings_warning":   earnings_warning,
        "predicted_mode":     predicted_mode,
        "mode_reason":        mode_reason,
    }
    
    # ── 3. 期权链前导分析 ──
    try:
        from stock_team.backtest.options_chain_analyzer import OptionChainAnalyzer
        analyzer = OptionChainAnalyzer(sym)
        opt_res = analyzer.analyze()
        if "error" not in opt_res:
            res_dict["options_indicators"] = opt_res
        else:
            res_dict["options_indicators"] = None
    except Exception as e:
        print(f"[Premarket Option Analysis Error] {sym}: {e}")
        res_dict["options_indicators"] = None
        
    return res_dict

def _print_macro_block():
    """读取 findings/macro.json + config/macro_background.json，打印宏观快查块"""
    macro_json_path = os.path.join(BASE, "findings", "macro.json")
    macro_bg_path   = os.path.join(BASE, "config", "macro_background.json")

    m, bg = {}, {}
    if os.path.exists(macro_json_path):
        try: m = json.load(open(macro_json_path, encoding="utf-8"))
        except: pass
    if os.path.exists(macro_bg_path):
        try: bg = json.load(open(macro_bg_path, encoding="utf-8"))
        except: pass

    def _f(v, fmt=None):
        if v is None: return "--"
        return fmt.format(v) if fmt else str(v)

    stale_warn = ""
    updated = bg.get("_updated", "")
    if updated:
        try:
            from datetime import date
            days_old = (date.today() - date.fromisoformat(updated)).days
            if days_old > 45:
                stale_warn = f"  ⚠️ 月度背景已 {days_old} 天未更新，建议刷新"
        except: pass

    y10   = _f(m.get("yield_10y"), "{:.2f}%")
    y3m   = _f(m.get("yield_3m"),  "{:.2f}%")
    sp    = m.get("yield_spread_bp")
    sp_s  = f"{sp:+.0f}bp" if sp is not None else "--"
    curve = m.get("yield_curve", "--")
    curve_warn = " ⚠️" if curve == "倒挂" else ""

    dxy   = _f(m.get("dxy"), "{:.1f}")
    dxy_v = m.get("dxy") or 0
    dxy_s = "偏强" if dxy_v > 103 else "偏弱" if dxy_v < 99 else "中性"
    fed   = _f(m.get("fed_rate"),  "{:.2f}%")
    fomc  = _f(m.get("fomc_next"))
    cpi   = _f(m.get("cpi_latest"))
    trade = m.get("china_trade_note") or bg.get("D_external", {}).get("china_trade_note", "--")

    regime     = bg.get("macro_regime", "--")
    analogy    = bg.get("E_historical_analogy", {}).get("closest_period", "--")
    implication= bg.get("regime_implication", "--")
    bg_date    = updated or "--"

    tone    = m.get("macro_tone", "--")
    score   = m.get("macro_score")
    score_s = f"{score}/10" if score is not None else "--"
    summary = m.get("macro_summary", "")

    fetched = m.get("fetched_at", "")
    ts = fetched[:16].replace("T", " ") if fetched else "--"

    print(f"【宏观快查】{ts}{stale_warn}")
    print("━" * 50)
    print(f"B 周期: 10Y {y10} / 3M {y3m} / 利差 {sp_s}{curve_warn} {curve}")
    print(f"D 外部: DXY {dxy} {dxy_s} | Fed: {fed} | 下次 FOMC: {fomc}")
    print(f"       CPI: {cpi} | 中美贸易: {trade}")
    print(f"月度背景 ({bg_date}): {regime}")
    print(f"  类比: {analogy} → {implication}")
    print(f"宏观定调: {tone} ({score_s}) — {summary}")

    # 今晚叙事（从 market_regime.json 读取，独立于结构主题）
    try:
        _rj = json.load(open(_REGIME_PATH, encoding="utf-8")) if os.path.exists(_REGIME_PATH) else {}
        _on = _rj.get("overnight_signal")
        if _on:
            print(f"{_on}")
    except Exception:
        pass

    print("━" * 50)
    print()


_REGIME_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "market_regime.json")

# 今日叙事：按主题分组的代表性个股，用于检测今晚盘后/盘前最热叙事
_NARRATIVE_THEMES = {
    "太空":     ["RKLB", "ASTS", "RDW", "LUNR", "SPCE"],
    "AI芯片":   ["NVDA", "AMD", "AVGO", "ARM", "SMCI"],
    "网络/云":  ["ANET", "CSCO", "NET", "SNOW", "CRWD"],
    "能源":     ["XOM", "CVX", "COP", "HAL", "SLB"],
    "生物科技": ["MRNA", "EDIT", "NVAX", "CRSP", "REGN"],
    "电动车":   ["TSLA", "RIVN", "NIO", "LCID", "F"],
    "加密/区块":["COIN", "MSTR", "RIOT", "MARA", "HUT"],
    "黄金矿业": ["NEM", "GOLD", "AEM", "KGC", "AGI"],
    "国防":     ["LMT", "RTX", "NOC", "GD", "BA"],
    "消费零售": ["AMZN", "SHOP", "ETSY", "WMT", "TGT"],
}

def _detect_overnight_narrative() -> dict | None:
    """
    扫描今晚盘后/盘前各主题代表股，识别最热叙事。
    返回 {"theme": str, "avg_chg": float, "detail": str, "source": str}
    或 None（无明显夜盘信号）。
    盘后信号有效期标注：明天开盘前。
    """
    theme_results = []

    for theme, stocks in _NARRATIVE_THEMES.items():
        chgs, parts = [], []
        for sym in stocks:
            try:
                si  = yf.Ticker(sym).info
                ext = si.get("postMarketPrice") or si.get("preMarketPrice")
                ref = si.get("regularMarketPrice")  # 今日收盘
                if ext and ref and abs(ext - ref) / ref > 0.001:
                    c = (ext - ref) / ref
                    chgs.append(c)
                    parts.append(f"{sym}{c*100:+.1f}%")
            except Exception:
                pass

        if len(chgs) >= 2:  # 至少2只有数据才算有效
            avg = sum(chgs) / len(chgs)
            src = "盘后" if any(
                yf.Ticker(s).info.get("postMarketPrice") for s in stocks[:2]
            ) else "盘前"
            theme_results.append({
                "theme":    theme,
                "avg_chg":  avg,
                "n":        len(chgs),
                "detail":   " ".join(parts[:3]),
                "source":   src,
            })

    if not theme_results:
        return None

    # 取今晚涨幅最大的前2个主题
    theme_results.sort(key=lambda x: x["avg_chg"], reverse=True)

    # 门槛：第一主题平均涨幅 > 1%
    if theme_results[0]["avg_chg"] < 0.01:
        return None

    top2 = theme_results[:2]
    # 过滤：第二主题也需要 > 0.5% 才显示
    if len(top2) > 1 and top2[1]["avg_chg"] < 0.005:
        top2 = top2[:1]

    return top2  # 返回列表（1-2个）


def detect_market_regime() -> str:
    """
    检测当前市场环境（5值 regime），if-elif 链，第一个满足立即返回。
    写入 config/market_regime.json 供 poll.py 全天复用。
    返回 regime 字符串。
    """
    from datetime import datetime, timezone as _tz

    regime = "sideways"
    signals = []
    confidence = "中"
    vix_cur = None

    try:
        spy_h  = yf.Ticker("SPY").history(period="10d")
        qqq_h  = yf.Ticker("QQQ").history(period="10d")
        vix_h  = yf.Ticker("^VIX").history(period="10d")

        if spy_h.empty or qqq_h.empty or vix_h.empty:
            regime = "sideways"
        else:
            vix_cur    = float(vix_h["Close"].iloc[-1])
            vix_5d_ago = float(vix_h["Close"].iloc[-6]) if len(vix_h) >= 6 else vix_cur
            spy_5d_chg = float((spy_h["Close"].iloc[-1] - spy_h["Close"].iloc[-6]) / spy_h["Close"].iloc[-6]) if len(spy_h) >= 6 else 0
            qqq_5d_chg = float((qqq_h["Close"].iloc[-1] - qqq_h["Close"].iloc[-6]) / qqq_h["Close"].iloc[-6]) if len(qqq_h) >= 6 else 0

            spy_ranges   = ((spy_h["High"] - spy_h["Low"]) / spy_h["Open"]).tail(5)
            high_vol_days = int((spy_ranges > 0.015).sum())

            spy_ma20 = float(spy_h["Close"].rolling(20).mean().iloc[-1]) if len(spy_h) >= 20 else None
            spy_ma50 = float(spy_h["Close"].rolling(50).mean().iloc[-1]) if len(spy_h) >= 50 else None

            # ── 板块热点检测（25+个板块，best-match 而非 first-match）──────

            # 夜盘/盘前流动性薄的主题 ETF → 用代表性成分股均值做代理
            SECTOR_COMPONENTS = {
                "ROKT": ["RKLB", "ASTS", "RDW", "IRDM", "SPCE"],
                "UFO":  ["RKLB", "ASTS", "IRDM", "MAXR", "GSAT"],
                "XAR":  ["LHX", "HEI", "TDG", "AXON", "LDOS"],
                "ITA":  ["RTX", "LMT", "BA", "NOC", "GD"],
                "SOXX": ["NVDA", "AMD", "AVGO", "QCOM", "MU"],
                "SMH":  ["NVDA", "TSM", "ASML", "AMD", "AVGO"],
                "ARKK": ["TSLA", "PLTR", "COIN", "ROKU", "SPOT"],
                "BOTZ": ["ISRG", "ABB", "IRBT", "NVDA", "FANUC"],
                "XBI":  ["MRNA", "EDIT", "NVAX", "CRSP", "CTLT"],
                "IBB":  ["AMGN", "GILD", "REGN", "VRTX", "MRNA"],
                "GDX":  ["NEM", "GOLD", "AEM", "KGC", "AGI"],
                "GDXJ": ["KGC", "AGI", "HL", "PAAS", "MAG"],
                "TAN":  ["ENPH", "SEDG", "FSLR", "CSIQ", "RUN"],
                "ICLN": ["ENPH", "NEE", "FSLR", "BEP", "CWEN"],
                "IWM":  ["SMCI", "ETSY", "MSTR", "AMC", "GME"],
            }

            def _get_overnight_chg(etf: str, prev_close: float) -> tuple:
                """
                获取今日盘前/盘后变动。
                优先用 ETF 自身的 preMarketPrice/postMarketPrice。
                若不可用（None 或等于昨收），改用成分股均值代理。
                返回 (chg: float | None, label: str)
                """
                # 1. 先试 ETF 自身
                try:
                    info = yf.Ticker(etf).info
                    ext = info.get("postMarketPrice") or info.get("preMarketPrice")
                    # 盘后用今日收盘作基准；盘前用昨收（regularMarketPrice 开盘前等于昨收）
                    ref = info.get("regularMarketPrice") or prev_close
                    if ext and ref and abs(ext - ref) / ref > 0.0001:
                        tag = "盘后" if info.get("postMarketPrice") else "盘前"
                        return (ext - ref) / ref, tag
                except Exception:
                    pass

                # 2. ETF 无数据 → 成分股均值
                components = SECTOR_COMPONENTS.get(etf, [])
                if not components:
                    return None, ""
                chgs, detail_parts = [], []
                for sym in components:
                    try:
                        si = yf.Ticker(sym).info
                        ext_s = si.get("postMarketPrice") or si.get("preMarketPrice")
                        # 盘后参考今日收盘；盘前参考昨收（preMarket 在开盘前，regularMarketPrice 此时仍是昨收）
                        pc_s  = si.get("regularMarketPrice") or si.get("regularMarketPreviousClose")
                        if ext_s and pc_s and abs(ext_s - pc_s) / pc_s > 0.0001:
                            c = (ext_s - pc_s) / pc_s
                            chgs.append(c)
                            detail_parts.append(f"{sym}{c*100:+.1f}%")
                    except Exception:
                        pass
                if chgs:
                    avg = sum(chgs) / len(chgs)
                    detail = " ".join(detail_parts[:3])
                    return avg, f"成分股均值({detail})"
                return None, ""

            SECTOR_ETFS = {
                # 11个标准 SPDR 板块
                "XLK":  "科技",   "XLF":  "金融",   "XLE":  "能源",
                "XLV":  "医疗",   "XLI":  "工业",   "XLC":  "通信",
                "XLY":  "消费",   "XLU":  "公用",   "XLRE": "地产",
                "XLB":  "材料",   "XLP":  "必需消费",
                # 热门主题
                "ROKT": "太空",   "UFO":  "太空宽基", "XAR":  "航空航天",
                "ITA":  "国防",   "SOXX": "半导体",   "SMH":  "半导体2",
                "ARKK": "创新成长","BOTZ": "机器人AI",
                "XBI":  "生物科技","IBB":  "生物科技2",
                "GDX":  "黄金矿业","GDXJ": "黄金矿业小",
                "TAN":  "清洁能源","ICLN": "清洁能源2",
                "IWM":  "小盘股",
            }
            sector_perfs = []
            for etf, name in SECTOR_ETFS.items():
                try:
                    eh = yf.Ticker(etf).history(period="7d")
                    if len(eh) >= 6:
                        prev_close = float(eh["Close"].iloc[-1])  # 上一交易日收盘
                        chg5d   = float((prev_close - eh["Close"].iloc[-6]) / eh["Close"].iloc[-6])
                        outperf = chg5d - spy_5d_chg
                        chg_today, today_src = _get_overnight_chg(etf, prev_close)
                        sector_perfs.append({
                            "etf": etf, "name": name,
                            "outperf5d": outperf,
                            "chg_today": chg_today,  # None = 无夜盘数据
                            "today_src": today_src,  # "盘前" | "成分股均值(...)" | ""
                        })
                except Exception:
                    pass

            sector_hot = False
            if sector_perfs:
                # 按5日跑赢幅度排序，取最强板块
                sector_perfs.sort(key=lambda x: x["outperf5d"], reverse=True)
                best = sector_perfs[0]
                if best["outperf5d"] > 0.03:
                    sector_hot = True

                    def _fmt_overnight(item):
                        c, src = item["chg_today"], item["today_src"]
                        if c is None or src == "":
                            return "夜盘无数据"
                        return f"{src}{'↑' if c > 0 else '↓'}{abs(c)*100:.1f}%"

                    signals.append(
                        f"{best['name']}({best['etf']})5日跑赢SPY+{best['outperf5d']*100:.1f}%"
                        f" {_fmt_overnight(best)}"
                    )
                    if len(sector_perfs) > 1 and sector_perfs[1]["outperf5d"] > 0.03:
                        s2 = sector_perfs[1]
                        signals.append(
                            f"次热:{s2['name']}({s2['etf']})+{s2['outperf5d']*100:.1f}%"
                            f" {_fmt_overnight(s2)}"
                        )

            if vix_cur > 25 or high_vol_days >= 2:
                regime = "volatile"
                signals.append(f"VIX={vix_cur:.1f}" if vix_cur > 25 else f"高振幅{high_vol_days}天")
                confidence = "高"
            elif sector_hot:
                regime = "sector_hot"
                confidence = "中"
            elif spy_5d_chg < -0.02 and vix_cur > vix_5d_ago * 1.1:
                regime = "trending_down"
                signals.append(f"SPY5日{spy_5d_chg*100:.1f}% VIX↑")
                confidence = "高"
            elif qqq_5d_chg > 0 and spy_ma20 and spy_ma50 and spy_ma20 > spy_ma50 and vix_cur < 20:
                regime = "trending_up"
                signals.append(f"QQQ5日{qqq_5d_chg*100:.1f}% MA20>MA50 VIX={vix_cur:.1f}")
                confidence = "高"
            else:
                regime = "sideways"
                signals.append("无明确趋势")

    except Exception as e:
        signals = [f"检测失败:{e}"]
        regime = "sideways"

    # ── 今日叙事（双轨：结构主题 vs 今晚叙事，独立不合并）────────
    overnight_list = _detect_overnight_narrative()  # 返回 list[dict] 或 None
    overnight_signal = None
    if overnight_list:
        lines = []
        for idx, ov in enumerate(overnight_list):
            prefix = "[今晚叙事]" if idx == 0 else "  次热叙事"
            lines.append(
                f"{prefix}({ov['source']}) {ov['theme']}"
                f" 均涨{ov['avg_chg']*100:+.1f}%"
                f"（{ov['detail']}）"
            )
        lines.append("⏱盘后信号，明日开盘验证")
        overnight_signal = "\n".join(lines)

    from datetime import datetime, timezone as _tz2
    out = {
        "date":              datetime.now().strftime("%Y-%m-%d"),
        "regime":            regime,
        "confidence":        confidence,
        "signals":           signals,           # 5日结构主题
        "overnight_signal":  overnight_signal,  # 今晚叙事（可能为 None）
        "updated_at":        datetime.now(_tz2.utc).isoformat(),
    }
    os.makedirs(os.path.dirname(_REGIME_PATH), exist_ok=True)
    json.dump(out, open(_REGIME_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return regime


def run(symbols=None):
    date_str = os.environ.get("PREMARKET_DATE") or datetime.now().strftime("%Y-%m-%d")
    out_path = OUT_TPL.format(date_str)

    # 读取配置
    cfg = json.load(open(os.path.join(CFG_DIR, "poll_config.json"), encoding="utf-8"))
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
    # VIX 当前值（用于 macro 输出）
    vix_cur = None
    try:
        _vix_h = yf.Ticker("^VIX").history(period="2d")
        if not _vix_h.empty:
            vix_cur = float(_vix_h["Close"].iloc[-1])
    except Exception:
        pass
    _regime = detect_market_regime()
    print(f"市场环境(Regime): {_regime}")
    _print_macro_block()

    results = {}
    for sym in symbols:
        sec = sector_map.get(sym, {})
        sec_ref = sec.get("ref") if isinstance(sec, dict) else None
        print(f"分析 {sym}...", end=" ", flush=True)
        r = analyze_stock(sym, sec_ref, spy_pre_chg, futures_chg)
        if r:
            results[sym] = r
            icon = r["scene_icon"]
            print(f"参考{icon}{r['scene_name']}({r['confidence']})  gap{r['gap_pct']:+.1f}%")
        else:
            print("数据不足，跳过")

    # 输出汇总
    print(f"\n{'─'*58}")
    print(f"{'标的':<6} {'参考场景':<12} {'Gap':>6} {'板块':>6} {'新闻类型':<16} {'置信'}")
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
            print(f"\n  [{sym}] 参考场景{r['scene_icon']}{r['scene_name']}  催化剂强度:{strength_bar(cs)}({cs}/3)")
            print(f"    Gap: {r['gap_pct']:+.1f}%  {r['reasoning']}")
            print(f"    催化剂关键词: {', '.join(kws) if kws else '无'}")
            for i, (h, s) in enumerate(zip(hdls, srcs or [""]*len(hdls))):
                print(f"    新闻{i+1}[{s}]: {h}")
            print(f"    观察区: {r['watch_zone']}")
            print(f"    入场确认: {r['entry_confirm']}")
            print(f"    仓位: {r['sizing']}  止损: {r['stop_basis']}")
            if r.get("intuition_line"):
                print(f"    {r['intuition_line']}")
            # 统一置信度（仅对当前持仓标的）
            try:
                from stock_team.utils.unified_confidence import compute, format_output
                pos_path = os.path.join(BASE, "config", "positions.json")
                if os.path.exists(pos_path):
                    pos_syms = list(json.load(open(pos_path, encoding="utf-8")).get("positions", {}).keys())
                    if sym in pos_syms:
                        uc = compute(sym)
                        r["unified_confidence"] = format_output(uc)
                        print(f"    {r['unified_confidence']}")
            except Exception:
                pass
            print(f"  预测模式: {'⚡日内' if r.get('predicted_mode')=='intraday' else '🔄波段'}  {r.get('mode_reason','')}")
            if r.get("earnings_warning"):
                print(f"    {r['earnings_warning']}")

    # 保存
    output = {
        "date": date_str,
        "generated_at": now_utc.isoformat(),
        "macro": {
            "spy_pre": spy_pre_chg,
            "nq_futures": futures_chg,
            "env": env.replace("✅", "").replace("❌", "").strip(),
            "vix_level": round(vix_cur, 2) if vix_cur is not None else None,
        },
        "stocks": results,
        "scenario_templates": SCENARIO_ENTRIES,
    }
    json.dump(output, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n✅ 已保存至 {out_path}")

    return results

if __name__ == "__main__":
    syms = sys.argv[1:] if len(sys.argv) > 1 else None
    run(syms)
