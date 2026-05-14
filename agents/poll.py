"""
统一轮询脚本 — 集成快照记录 + ATR止损建议 + RS双轨分析 + 盘初场景框架
用法：python3.12 agents/poll.py AAOI RKLB SNXX INTC [--lev AAOX:2]
"""
import sys, os, json, argparse, numpy as np, subprocess
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf
from agents.session_recorder import write_snapshot, log_action, log_thought
from agents.paper_trader import (
    try_enter, try_add_tranche, check_exits, get_status,
    eod_close_all, load_trade_history, ACCOUNTS
)

# Session manager 集成（可选，--session 时启用）
try:
    from agents.session_manager import push_alert as _push_alert
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

def trigger_quick_debate(sym, a, spy_chg, qqq_chg, vix_cur, vix_dir, rs_streak=0):
    """异步触发 quick_debate.py，不阻塞轮询"""
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
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

def read_quick_debate(sym):
    """读取上一轮辩论结果（如果存在且足够新）"""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f"quick_debate_{sym}.json")
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
def snap(sym):
    t = yf.Ticker(sym)
    h1m = t.history(period="1d", interval="1m")
    h2d = t.history(period="5d")
    h30 = t.history(period="30d")
    if h1m.empty or len(h2d) < 2: return None

    lc   = float(h2d["Close"].iloc[-2])
    cur  = float(h1m["Close"].iloc[-1])
    hi   = float(h1m["High"].max())
    lo   = float(h1m["Low"].min())
    vwap = (h1m["Close"]*h1m["Volume"]).sum() / h1m["Volume"].sum()
    vr   = h1m["Volume"].iloc[-3:].mean()
    vp   = h1m["Volume"].iloc[-6:-3].mean() if len(h1m)>=6 else vr
    vol  = "🔽缩" if vr<vp*0.75 else "🔼扩" if vr>vp*1.3 else "─平"
    bars = "".join("▲" if float(r["Close"])>=float(r["Open"]) else "▼"
                   for _,r in h1m.tail(5).iterrows())
    c = h1m["Close"]; d = c.diff()
    g = d.clip(lower=0).ewm(span=3,adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(span=3,adjust=False).mean()
    rsi3 = float((100-100/(1+g/l)).iloc[-1])
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

    info = t.info
    tgt_dev = (info.get("targetMeanPrice",cur)-cur)/cur*100 if info.get("targetMeanPrice") else None

    return dict(
        sym=sym, cur=cur, lc=lc, hi=hi, lo=lo, vwap=vwap,
        chg=(cur-lc)/lc*100, dvwap=(cur-vwap)/vwap*100,
        vol=vol, bars=bars, vr=vr, vp=vp,
        rsi3=rsi3, hist=hist, prev_hist=prev,
        macd_cross=hist>0 and prev<=0,
        macd_fail=hist<0 and prev>0,
        atr14=atr14, atr5=atr5, ma20=ma20, ma50=ma50,
        tgt_dev=tgt_dev, h1m=h1m,
    )

def vix_snap():
    t = yf.Ticker("^VIX")
    h1m = t.history(period="1d", interval="1m")
    h2d = t.history(period="5d")
    if h1m.empty: return None
    cur = float(h1m["Close"].iloc[-1])
    lc  = float(h2d["Close"].iloc[-2]) if len(h2d)>=2 else cur
    vr = h1m["Close"].iloc[-3:].mean()
    vp = h1m["Close"].iloc[-6:-3].mean() if len(h1m)>=6 else vr
    trend = "↑升" if vr>vp*1.005 else "↓降" if vr<vp*0.995 else "→平"
    bars = "".join("▲" if float(r["Close"])>=float(r["Open"]) else "▼"
                   for _,r in h1m.tail(5).iterrows())
    return dict(cur=cur, lc=lc, chg=(cur-lc)/lc*100, trend=trend, bars=bars)

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
    return {
        "Minervini":      (ms, m_line),
        "Marks":          (ks, k_line),
        "Druckenmiller":  (ds, d_line),
        "avg":            round(avg, 1),
        "consensus": "🟢进" if avg >= 7 else "🟡等" if avg >= 5 else "🔴不进",
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
_STOCK_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIO_PATH_TPL  = os.path.join(_STOCK_BASE, "opening_scenarios_{}.json")
PREMARKET_PATH_TPL = os.path.join(_STOCK_BASE, "premarket_analysis_{}.json")

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
            json.dump(data, open(path, "w"), indent=2, ensure_ascii=False)
    except Exception:
        pass

# ── 宏观环境（3级）──────────────────────────────────────
MACRO = {
    "UP":      "▲顺风",
    "NEUTRAL": "─中性",
    "DOWN":    "▼逆风",
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
    json.dump(data, open(path, "w"), indent=2, ensure_ascii=False)

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
        print(f"  宏观预判：{MACRO[macro_state]}（{macro_reason}）")
        print()
        return

    # ── 宏观环境判断 ──────────────────────────────────────
    macro_state, macro_reason = determine_macro(vix_data, spy_chg, qqq_chg)
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

    if not premarket:
        print(f"  ℹ️  无盘前预测数据，运行 python3.12 agents/premarket.py 生成")
    print()

# ── 主轮询逻辑 ─────────────────────────────────────────────
def qqq_5m_chg(qqq_data):
    """QQQ 近5分钟涨跌幅（方法论#11 门控用）"""
    if not qqq_data or qqq_data.get("h1m") is None: return 0.0
    h = qqq_data["h1m"]
    if len(h) < 6: return 0.0
    return float((h["Close"].iloc[-1] - h["Close"].iloc[-6]) / h["Close"].iloc[-6] * 100)

def strategy_gate(a, spy_chg, vix_cur, vix_dir, qqq5m):
    """
    方法论 #6/#11 策略门控
    返回 (passed, n_required, checks_dict, block_reason)
    """
    rs     = a["chg"] - spy_chg
    rsi3   = a["rsi3"]
    hist   = a["hist"]
    n_req  = 5 if vix_cur >= 18 else 3   # #6: VIX18-20→N=5

    checks = {
        "RS>1.5%":    (rs > 1.5,        f"RS{rs:+.1f}%"),
        "MACD>0":     (hist > 0,         f"MACD{hist:+.3f}"),
        "RSI3≥50":    (rsi3 >= 50,       f"RSI3={rsi3:.0f}"),
        "VIX方向":    (vix_dir in ("→平","↓降"), vix_dir),
        "QQQ5m≥-0.1%":(qqq5m >= -0.1,   f"QQQ5m{qqq5m:+.2f}%"),
    }
    passed = all(v for v, _ in checks.values())

    # #11 绝对禁止加仓（任一触发→block）
    block = None
    if qqq5m < -0.5:  block = f"QQQ5分钟{qqq5m:+.2f}%急跌"
    elif rsi3 < 35:   block = f"RSI3={rsi3:.0f}动能崩溃"

    return passed, n_req, checks, block

def fmt_gate(checks, passed, n_req, block):
    ok = "✅" if passed else "❌"
    parts = []
    for name, (v, val) in checks.items():
        parts.append(f"{'✅' if v else '❌'}{name}({val})")
    status = f"🔴禁止:{block}" if block else (f"🟢通过[需{n_req}次连续]" if passed else "🟡未通过")
    return f"  │ 【#6/#11门控】{status}  " + "  ".join(parts)

def run_poll(symbols, sector_map=None, lev_map=None, cost_map=None, session=False):
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    et_h = (datetime.now(timezone.utc).hour-4)%24
    et_m = datetime.now(timezone.utc).minute

    spy  = snap("SPY"); qqq = snap("QQQ"); vix = vix_snap()
    stocks = {sym: snap(sym) for sym in symbols}

    vc    = vix["cur"] if vix else 20
    vchg  = vix["chg"] if vix else 0
    vt    = vix["trend"] if vix else "→平"
    vb    = vix["bars"] if vix else "─"
    vlvl  = "🟡中性" if vc<=20 else "🟠偏高" if vc<=25 else "🔴高危"
    spy_chg = spy["chg"] if spy else 0
    qqq_chg = qqq["chg"] if qqq else 0
    qqq5m   = qqq_5m_chg(qqq)
    mkt = 0
    for chg in [spy_chg, qqq_chg]:
        mkt += 2 if chg>0.3 else 1 if chg>0 else -2 if chg<-0.5 else -1
    mkt += 2 if vt=="↓降" else -2 if vt=="↑升" else 0
    eok = mkt >= 1
    ml = "🟢顺风" if mkt>=4 else "🟡中性" if mkt>=1 else "🟠谨慎" if mkt>=-1 else "🔴逆风"

    # ── 写入快照 ──────────────────────────────────────────
    snap_data = {}
    for sym, a in stocks.items():
        if not a: continue
        snap_data[sym] = {
            "cur": a["cur"], "chg": a["chg"],
            "rs":  round(a["chg"]-spy_chg, 2),
            "rsi3": a["rsi3"], "hist": a["hist"],
            "dvwap": a["dvwap"], "vol": a["vol"],
            "bars": a["bars"], "atr14": a["atr14"],
        }
    if vix:
        write_snapshot(snap_data, vix, spy_chg, qqq_chg)

    # ── 输出 ──────────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  轮询  {now} UTC  美东{et_h:02d}:{et_m:02d}")
    print(f"{'='*60}")
    ev = "VIX↑升⚠️" if vt=="↑升" else "VIX↓回落✅" if vt=="↓降" else f"VIX{vc:.0f}→平"
    print(f"【环境】{ev} | SPY{spy_chg:+.2f}% QQQ{qqq_chg:+.2f}%  {mkt:+d}/6→{ml}")
    print(f"VIX {vc:.1f}({vchg:+.1f}%) {vlvl} {vt} {vb}")
    print(f"SPY {spy['bars'] if spy else '─────'}  QQQ {qqq['bars'] if qqq else '─────'}")
    print()

    # 模拟盘状态（三账号）
    live_prices = {sym: a["cur"] for sym, a in stocks.items() if a}
    print(get_status(live_prices, ACCOUNTS))
    print()

    # 盘初场景框架
    render_opening_block(stocks, spy_chg, qqq_chg, vix, et_h, et_m,
                         sector_map=sector_map)

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
        if pnl > 3:     pos_act = f"✅ 浮盈{pnl:.1f}%，止损→成本${cost}"
        elif pnl >= 0:  pos_act = f"🟡 微盈{pnl:.1f}%，守止损"
        elif lev_a["cur"] < cost*0.935: pos_act = f"🔴 浮亏{pnl:.1f}%，接近止损"
        else:           pos_act = f"🔴 浮亏{pnl:.1f}%，守止损"
        print(f"{'━'*60}")
        print(f"{lev_sym} 持仓 成本${cost}  现${lev_a['cur']:.2f}({lev_a['chg']:+.2f}%) 浮{pnl:+.1f}%")
        print(f"  {lev_a['bars']} {lev_a['vol']}  RSI3={lev_a['rsi3']:.0f}  MACD={lev_a['hist']:+.2f}{'🟢' if lev_a['hist']>0 else '🔴'}")
        print(f"  底层{sym} ATR14=${base_a['atr14']:.1f}  {stop_type}→参考${lev_stop:.2f}")
        print(f"  → {pos_act}")
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

        # Persona 实时评分（B）
        streak_now = scene_current.get(sym, {}).get("rs_streak", 0) if scene_current else 0
        ps  = quick_persona_score(a, spy_chg, qqq_chg, vc, vt, rs_streak=streak_now)
        bar = lambda s: "█"*int(s) + "░"*(10-int(s))
        print(f"│ ── 师傅评分 ── 综合{ps['avg']}/10  {ps['consensus']}")
        print(f"│ Minervini  {ps['Minervini'][0]:>2}/10 [{bar(ps['Minervini'][0])}]  {ps['Minervini'][1]}")
        print(f"│ Marks      {ps['Marks'][0]:>2}/10 [{bar(ps['Marks'][0])}]  {ps['Marks'][1]}")
        print(f"│ Druck      {ps['Druckenmiller'][0]:>2}/10 [{bar(ps['Druckenmiller'][0])}]  {ps['Druckenmiller'][1]}")

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

        # ── 策略门控 #6/#11 ───────────────────────────────────
        _gate_ok, _n_req, _checks, _block = strategy_gate(
            a, spy_chg, vc, vt, qqq5m)
        print(fmt_gate(_checks, _gate_ok, _n_req, _block))

        for _acct in ACCOUNTS:
            # 止损/止盈检查（不受门控限制，始终执行）
            _exit = check_exits(sym, a["cur"], hi=a["hi"], lo=a["lo"], acct=_acct)
            if _exit:
                print(f"│ 📊{_exit}")
            # T1 新仓入场（门控不通过则跳过）
            if not _gate_ok or _block:
                pass  # 门控拦截，不入场
            else:
                _entry = try_enter(sym, a["cur"], a["vwap"], a["atr14"],
                                   rs, ps["avg"], signal_info, spy_chg,
                                   live_prices=live_prices,
                                   catalyst_strength=pm_catalyst, acct=_acct)
                if _entry:
                    print(f"│ 📊{_entry}")
            # T2/T3 加仓（门控不通过或有 block 则跳过）
            if not _block:
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

    print(f"快照已写入 knowledge/snapshots_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
    print(f"记录操作: 对话中说 '记录：买了/卖了 XXX $价格 因为...'")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        print(f"⚠️  以下持仓未配置成本价，持仓监控功能未启用：{', '.join(missing)}")
        print(f"   告诉我持仓成本即可自动更新，例如：'记录：持有 AAOX 成本 $69'")
        print()

def update_position(sym, cost, shares=None, date=None):
    """更新持仓配置（供外部调用）"""
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pos_path = os.path.join(_base, "config", "positions.json")
    pos_cfg = json.load(open(pos_path, encoding="utf-8"))
    pos_cfg["positions"][sym] = {
        "cost": cost,
        "shares": shares or 0,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
    }
    json.dump(pos_cfg, open(pos_path, "w"), indent=2)
    print(f"[Config] {sym} 持仓已更新: 成本${cost} 股数{shares or '未知'}")

def remove_position(sym):
    """清除持仓（止损/止盈出场后调用）"""
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pos_path = os.path.join(_base, "config", "positions.json")
    pos_cfg = json.load(open(pos_path, encoding="utf-8"))
    if sym in pos_cfg["positions"]:
        del pos_cfg["positions"][sym]
        json.dump(pos_cfg, open(pos_path, "w"), indent=2)
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
             session=args.session)
