"""
市场扫描器 — 5维分析矩阵
维度：个股信号 × 板块热度 × 板块内地位 × 催化剂 × 拥挤度

用法：
  from agents.market_scanner import score_stock_5d, scan_all_sectors
  python3.12 agents/market_scanner.py          # 扫描全部板块
  python3.12 agents/market_scanner.py MRVL AMD # 指定标的
"""
import os, sys, json
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf

BASE         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTOR_CFG   = os.path.join(BASE, "config", "sector_watchlist.json")
COMPANY_CFG  = os.path.join(BASE, "knowledge", "company_profiles.json")
SPY_CACHE    = {}   # 缓存SPY数据避免重复请求

# ── 维度1：个股信号 ─────────────────────────────────────────
def score_stock_signal(h30, close, rsi, atr):
    """
    个股信号：强势/回调机会/震荡蓄力/弱势
    返回 (label, icon, score_1_5)
    """
    ma20  = float(h30["Close"].rolling(20).mean().iloc[-1])
    ma50  = float(h30["Close"].rolling(50).mean().iloc[-1]) if len(h30)>=50 else ma20
    d5    = (close - float(h30["Close"].iloc[-6]))/float(h30["Close"].iloc[-6])*100 if len(h30)>=6 else 0
    d20   = (close - float(h30["Close"].iloc[-21]))/float(h30["Close"].iloc[-21])*100 if len(h30)>=21 else 0

    above_ma20 = close > ma20
    above_ma50 = close > ma50

    # 强势：站均线上方，RSI健康，近期涨势
    if above_ma20 and above_ma50 and 55 <= rsi <= 78 and d5 > 2:
        return "强势突破", "📈", 5
    if above_ma20 and above_ma50 and rsi > 78:
        return "强势超买", "🔥", 4
    # 回调机会：从高位回落，但趋势未破
    if above_ma50 and not above_ma20 and rsi < 65 and d5 < -3:
        return "回调机会", "🔵", 4
    if above_ma20 and 45 <= rsi <= 62 and -3 <= d5 <= 1:
        return "强势整理", "🟡", 4
    # 震荡蓄力：均线走平，RSI中性，ATR收窄
    atr_pct = atr / close * 100
    if 42 <= rsi <= 60 and abs(d20) < 15 and atr_pct < 5:
        return "震荡蓄力", "⚪", 3
    if 40 <= rsi <= 65 and -10 <= d20 <= 10:
        return "区间震荡", "🟡", 3
    # 弱势
    if not above_ma50 and rsi < 50 and d5 < -5:
        return "弱势下跌", "📉", 1
    if not above_ma20 and rsi < 55:
        return "偏弱整理", "🟠", 2
    return "中性", "─", 3

# ── 维度2：板块热度 ─────────────────────────────────────────
_sector_heat_cache = {}

def score_sector_heat(sector_etf):
    """
    板块热度：🔥🔥过热 / 🔥热 / 🌱启动 / ❄️降温 / ❄️❄️冷
    返回 (label, icon, score_1_5, reasoning)
    """
    if sector_etf in _sector_heat_cache:
        return _sector_heat_cache[sector_etf]
    if not sector_etf:
        return "无参照", "─", 3, "无板块ETF参照"

    try:
        if "SPY" not in SPY_CACHE:
            SPY_CACHE["SPY"] = yf.Ticker("SPY").history(period="90d")
        spy_h = SPY_CACHE["SPY"]
        sec_h = yf.Ticker(sector_etf).history(period="90d")

        if sec_h.empty or len(sec_h) < 5:
            return "数据不足", "─", 3, "数据不足"

        def rel(n):
            if len(sec_h) < n or len(spy_h) < n:
                return 0
            s = (sec_h["Close"].iloc[-1]-sec_h["Close"].iloc[-n])/sec_h["Close"].iloc[-n]*100
            m = (spy_h["Close"].iloc[-1]-spy_h["Close"].iloc[-n])/spy_h["Close"].iloc[-n]*100
            return s - m

        w1 = rel(5)    # 1周超额
        m1 = rel(20)   # 1月超额
        m3 = rel(60)   # 3月超额

        if m1 > 20 and w1 > 3:
            r = "🔥🔥过热", "🔥🔥", 5, f"1月超SPY{m1:+.0f}%，1周仍{w1:+.1f}%"
        elif m1 > 10 and w1 > 1:
            r = "🔥热", "🔥", 4, f"1月超SPY{m1:+.0f}%，趋势强"
        elif w1 > 2 and m1 < 8:
            r = "🌱刚启动", "🌱", 4, f"1周超SPY{w1:+.1f}%，1月{m1:+.0f}%，轮动初期"
        elif m1 > 5 and w1 < -2:
            r = "❄️降温", "❄️", 2, f"1月曾超SPY{m1:+.0f}%，但1周回落{w1:+.1f}%"
        elif m1 < -5 and w1 < 0:
            r = "❄️❄️冷", "❄️❄️", 1, f"1月落后SPY{m1:+.0f}%，持续弱势"
        else:
            r = "─中性", "─", 3, f"1月{m1:+.0f}%，1周{w1:+.1f}%，跟随大盘"

        _sector_heat_cache[sector_etf] = r
        return r
    except Exception as e:
        return "计算失败", "─", 3, str(e)[:30]

# ── 维度3：板块内地位 ────────────────────────────────────────
def score_sector_position(stock_ret_m1, sector_rel_m1):
    """
    板块内地位：龙头 / 跟随 / 落后
    stock_ret_m1: 个股1月绝对涨幅
    sector_rel_m1: 板块1月相对SPY超额
    """
    # 个股相对板块的超额
    stock_vs_sector = stock_ret_m1 - (sector_rel_m1 + _spy_m1())

    if stock_vs_sector > 10:
        return "板块龙头", "💎", 5
    elif stock_vs_sector > 3:
        return "领先板块", "⬆", 4
    elif stock_vs_sector > -3:
        return "跟随板块", "→", 3
    elif stock_vs_sector > -10:
        return "落后板块", "⬇", 2
    else:
        return "显著落后", "📉", 1

def _spy_m1():
    if "SPY" not in SPY_CACHE:
        SPY_CACHE["SPY"] = yf.Ticker("SPY").history(period="90d")
    h = SPY_CACHE["SPY"]
    if len(h) >= 20:
        return (h["Close"].iloc[-1]-h["Close"].iloc[-20])/h["Close"].iloc[-20]*100
    return 0

# ── 维度4：催化剂 ────────────────────────────────────────────
def score_catalyst(sym, news_headlines=None):
    """
    催化剂：有明确事件 / 等待中 / 已耗尽 / 负面风险
    返回 (label, icon, score_1_5, detail)
    """
    try:
        info = yf.Ticker(sym).info
        earn_ts = info.get("earningsTimestamp")
        now     = datetime.now(timezone.utc).timestamp()

        days_to_earn = None
        if earn_ts:
            days_to_earn = (earn_ts - now) / 86400

        # 公司知识库里的里程碑
        profile = {}
        if os.path.exists(COMPANY_CFG):
            try:
                profiles = json.load(open(COMPANY_CFG))
                profile  = profiles.get(sym, {})
            except: pass

        detail_parts = []

        # 财报催化剂
        if days_to_earn is not None:
            if 0 < days_to_earn <= 14:
                detail_parts.append(f"财报{days_to_earn:.0f}天后")
                cat_score = 5
                cat_label = "财报将至"
                cat_icon  = "📅"
            elif 14 < days_to_earn <= 45:
                detail_parts.append(f"财报{days_to_earn:.0f}天后")
                cat_score = 4
                cat_label = "有财报"
                cat_icon  = "📅"
            else:
                cat_score = 3
                cat_label = "等待中"
                cat_icon  = "⏳"
        else:
            cat_score = 3
            cat_label = "等待中"
            cat_icon  = "⏳"

        # 新闻催化剂（如果传入了最近新闻）
        if news_headlines:
            text = " ".join(news_headlines).lower()
            strong_kw = ["stake","acqui","partnership","contract","earnings beat","record"]
            weak_kw   = ["miss","downgrade","cut","loss","warning","layoff"]
            if any(k in text for k in strong_kw):
                cat_score = max(cat_score, 4)
                cat_label = "强催化剂"
                cat_icon  = "⚡"
                detail_parts.append("近期正面新闻")
            elif any(k in text for k in weak_kw):
                cat_score = min(cat_score, 2)
                cat_label = "负面风险"
                cat_icon  = "⚠️"
                detail_parts.append("近期负面新闻")

        detail = "  ".join(detail_parts) if detail_parts else "无明确事件"
        return cat_label, cat_icon, cat_score, detail

    except Exception as e:
        return "未知", "─", 3, str(e)[:20]

# ── 维度5：拥挤度 ────────────────────────────────────────────
def score_crowding(rsi, short_pct, d5, d20):
    """
    拥挤度：空旷（低关注）/ 适中 / 拥挤 / 严重拥挤
    返回 (label, icon, score_1_5, reasoning)
    """
    score  = 0
    parts  = []

    # RSI
    if rsi > 82:
        score += 3; parts.append(f"RSI{rsi:.0f}严重超买")
    elif rsi > 72:
        score += 2; parts.append(f"RSI{rsi:.0f}偏热")
    elif rsi > 60:
        score += 1; parts.append(f"RSI{rsi:.0f}正常")
    else:
        parts.append(f"RSI{rsi:.0f}健康")

    # 短仓比（做空压力）
    if short_pct:
        if short_pct > 15:
            score -= 1; parts.append(f"空头{short_pct:.0f}%高（反向支撑）")
        elif short_pct > 8:
            score += 1; parts.append(f"空头{short_pct:.0f}%中等")
        else:
            score += 1; parts.append(f"空头{short_pct:.0f}%低（无对冲）")

    # 短期涨幅
    if d5 > 15:
        score += 2; parts.append(f"5日+{d5:.0f}%急涨")
    elif d5 > 8:
        score += 1; parts.append(f"5日+{d5:.0f}%")

    # 20日涨幅
    if d20 > 50:
        score += 2; parts.append(f"20日+{d20:.0f}%过热")
    elif d20 > 25:
        score += 1; parts.append(f"20日+{d20:.0f}%较热")

    if score >= 6:
        return "严重拥挤", "🚨", 1, " | ".join(parts[:2])
    elif score >= 4:
        return "较拥挤", "⚠️", 2, " | ".join(parts[:2])
    elif score >= 2:
        return "适中", "─", 3, " | ".join(parts[:2])
    elif score >= 0:
        return "低拥挤", "✅", 4, " | ".join(parts[:2])
    else:
        return "空旷反向", "💎", 5, " | ".join(parts[:2])

# ── 综合评估 ────────────────────────────────────────────────
COMBINED_MATRIX = {
    # (个股分, 板块热度分, 拥挤分) → (操作, 优先级)
    # 个股强(4-5) × 板块热(4-5) × 不拥挤(3-5)  → 最佳
    (5, 5, 4): ("🟢最佳入场：强势+热板块+不拥挤", "高"),
    (5, 4, 4): ("🟢积极入场：顺势入场", "高"),
    (4, 5, 3): ("🟡谨慎入场：板块过热注意拥挤", "中"),
    (4, 4, 4): ("🟢入场：个股+板块共振", "高"),
    (5, 5, 2): ("⚠️追高风险：强势但拥挤，等回踩", "中"),
    (5, 5, 1): ("🔴严重拥挤，等待回调再入", "低"),
    (4, 3, 4): ("🟡独立行情H：关注但板块中性", "中"),
    (3, 4, 4): ("🔵蓄力+热板块：等突破信号", "中"),
    (3, 5, 4): ("🔵弹簧已压：热板块整理，突破信号强", "中"),
    (4, 2, 5): ("💎逆向+冷板块回调：耐心等催化剂", "低"),
    (3, 3, 5): ("⚪震荡观望，无板块支撑", "低"),
    (2, 4, 5): ("🔵弱势热板块：等补涨，G场景", "中"),
    (2, 2, 5): ("❌弱+冷+无拥挤：放弃", "无"),
    (1, 1, 5): ("❌全面弱势，回避", "无"),
}

def get_combined_action(sig_score, heat_score, crowd_score, cat_score):
    """综合5维给出操作建议"""
    # 催化剂加权
    if cat_score >= 5:
        sig_score  = min(5, sig_score + 1)
        heat_score = min(5, heat_score + 1)

    # 找最近匹配
    key = (min(5, max(1, sig_score)), min(5, max(1, heat_score)), min(5, max(1, crowd_score)))
    if key in COMBINED_MATRIX:
        return COMBINED_MATRIX[key]

    # 模糊匹配
    if sig_score >= 4 and heat_score >= 4 and crowd_score >= 3:
        return ("🟢入场机会：各维度配合", "高")
    elif sig_score >= 4 and crowd_score <= 2:
        return ("⚠️信号好但拥挤，等回踩", "中")
    elif sig_score <= 2:
        return ("❌个股弱势，回避", "无")
    elif heat_score <= 2:
        return ("⚪板块冷，等轮动信号", "低")
    else:
        return ("─中性观望", "低")

# ── 完整5维评估 ──────────────────────────────────────────────
def score_stock_5d(sym, sector_etf=None, news_headlines=None):
    """
    对单只股票做完整5维评估
    返回完整报告字典
    """
    try:
        tick = yf.Ticker(sym)
        info = tick.info
        h30  = tick.history(period="60d")

        if h30.empty:
            return None

        close = info.get("regularMarketPrice") or float(h30["Close"].iloc[-1])
        short_pct = (info.get("shortPercentOfFloat") or 0) * 100

        atr  = float((h30["High"]-h30["Low"]).rolling(14).mean().iloc[-1])
        ma20 = float(h30["Close"].rolling(20).mean().iloc[-1])

        dd   = h30["Close"].diff()
        gain = dd.clip(lower=0).rolling(14).mean()
        loss = (-dd.clip(upper=0)).rolling(14).mean()
        rsi  = float((100-100/(1+gain/loss)).iloc[-1])

        d5  = (close-float(h30["Close"].iloc[-6]))/float(h30["Close"].iloc[-6])*100 if len(h30)>=6 else 0
        d20 = (close-float(h30["Close"].iloc[-21]))/float(h30["Close"].iloc[-21])*100 if len(h30)>=21 else 0

        # 维度1：个股信号
        sig_label, sig_icon, sig_score = score_stock_signal(h30, close, rsi, atr)

        # 维度2：板块热度
        heat_label, heat_icon, heat_score, heat_reason = score_sector_heat(sector_etf)

        # 维度3：板块内地位
        sector_rel_m1 = 0
        if sector_etf and heat_score > 1:
            try:
                sec_h = yf.Ticker(sector_etf).history(period="30d")
                if len(sec_h) >= 20:
                    sector_rel_m1 = (sec_h["Close"].iloc[-1]-sec_h["Close"].iloc[-20])/sec_h["Close"].iloc[-20]*100 - _spy_m1()
            except: pass
        pos_label, pos_icon, pos_score = score_sector_position(d20, sector_rel_m1)

        # 维度4：催化剂
        cat_label, cat_icon, cat_score, cat_detail = score_catalyst(sym, news_headlines)

        # 维度5：拥挤度
        crowd_label, crowd_icon, crowd_score, crowd_reason = score_crowding(rsi, short_pct, d5, d20)

        # 综合判断
        action, priority = get_combined_action(sig_score, heat_score, crowd_score, cat_score)

        return {
            "sym":    sym,
            "close":  close,
            "d5":     round(d5, 1),
            "d20":    round(d20, 1),
            "rsi":    round(rsi, 1),
            "ma20":   round(ma20, 2),

            "d1_signal":  {"label":sig_label,   "icon":sig_icon,   "score":sig_score},
            "d2_heat":    {"label":heat_label,   "icon":heat_icon,  "score":heat_score,  "reason":heat_reason},
            "d3_position":{"label":pos_label,    "icon":pos_icon,   "score":pos_score},
            "d4_catalyst":{"label":cat_label,    "icon":cat_icon,   "score":cat_score,   "detail":cat_detail},
            "d5_crowd":   {"label":crowd_label,  "icon":crowd_icon, "score":crowd_score, "reason":crowd_reason},

            "action":   action,
            "priority": priority,
        }
    except Exception as e:
        return {"sym": sym, "error": str(e)}

# ── 全板块扫描 ───────────────────────────────────────────────
def scan_all_sectors(symbols=None, verbose=True):
    """
    扫描所有板块标的，输出5维评估表
    symbols: 指定标的列表，None则扫描全部
    """
    cfg = json.load(open(SECTOR_CFG)) if os.path.exists(SECTOR_CFG) else {"sectors": {}}
    overlap = cfg.get("sector_overlap_map", {})

    # 构建 sym→sector_etf 映射
    sym_to_etf = {}
    for sec_name, sec_info in cfg["sectors"].items():
        if sec_info.get("excluded"):
            continue
        etf = sec_info.get("etf")
        for s in sec_info.get("stocks", []):
            if s not in sym_to_etf:
                sym_to_etf[s] = (etf, sec_name)

    target_syms = symbols if symbols else list(sym_to_etf.keys())

    results = []
    for sym in target_syms:
        etf, sec_name = sym_to_etf.get(sym, (None, "未知板块"))
        r = score_stock_5d(sym, etf)
        if r and "error" not in r:
            r["sector_name"] = sec_name
            r["overlap"]     = overlap.get(sym, [])
            results.append(r)

    # 按优先级和综合分排序
    priority_order = {"高": 0, "中": 1, "低": 2, "无": 3}
    results.sort(key=lambda x: (
        priority_order.get(x.get("priority","无"), 3),
        -sum([x["d1_signal"]["score"], x["d2_heat"]["score"],
              x["d4_catalyst"]["score"], x["d5_crowd"]["score"]])
    ))

    if verbose:
        _print_scan_results(results)

    return results

def _print_scan_results(results):
    now = datetime.now(timezone.utc)
    et  = (now.hour - 4) % 24
    print(f"\n{'═'*72}")
    print(f"  5维市场扫描  {et:02d}:{now.minute:02d} ET  共{len(results)}只")
    print(f"{'═'*72}")

    for r in results:
        if r.get("priority") == "无":
            continue  # 跳过明确回避

        sym      = r["sym"]
        sec      = r["sector_name"]
        ovl      = f"⇄{','.join(r['overlap'][:2])}" if r.get("overlap") else ""
        d1 = r["d1_signal"];  d2 = r["d2_heat"]
        d3 = r["d3_position"]; d4 = r["d4_catalyst"]; d5 = r["d5_crowd"]
        pri_icon = {"高":"🟢","中":"🟡","低":"⚪"}.get(r["priority"],"─")

        print(f"\n{pri_icon} {sym:<6} ${r['close']:.0f}  [{sec}]{ovl}")
        print(f"  {d1['icon']}{d1['label']}({d1['score']}/5)  "
              f"{d2['icon']}{d2['label']}({d2['score']}/5)  "
              f"{d3['icon']}{d3['label']}  "
              f"{d4['icon']}{d4['label']}  "
              f"{d5['icon']}{d5['label']}")
        print(f"  板块热度: {d2['reason']}")
        if d4['detail'] != "无明确事件":
            print(f"  催化剂: {d4['detail']}")
        if d5['reason']:
            print(f"  拥挤度: {d5['reason']}")
        print(f"  → {r['action']}")

    # 汇总：今日优先级高的
    high = [r for r in results if r.get("priority") == "高"]
    if high:
        print(f"\n{'─'*50}")
        print(f"  今日优先关注({len(high)}只)：{' '.join(r['sym'] for r in high)}")

if __name__ == "__main__":
    syms = sys.argv[1:] if len(sys.argv) > 1 else None
    scan_all_sectors(syms)
