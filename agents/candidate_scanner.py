"""
候选池扫描器 — 每天盘前运行，从更宽的宇宙中生成今日候选标的

两类入口：
  A. 盘前异动型：盘前涨幅 > 4% + 盘前量比 > 1.2x
  B. 超卖反弹型：近2日跌幅 > 3% + 空头比例 > 10%

用法：
  python3.12 agents/candidate_scanner.py           # 扫描全部关注列表
  python3.12 agents/candidate_scanner.py --top 10  # 输出前10只

输出：候选池排名 + 触发原因，可直接喂给 premarket.py 和 CIO
"""
import sys, os, json, argparse
from datetime import datetime, timezone

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf

def get_ticker(symbol):
    from curl_cffi import requests as curl_requests
    class TimeoutSession(curl_requests.Session):
        def request(self, *args, **kwargs):
            if 'timeout' not in kwargs or kwargs['timeout'] is None:
                kwargs['timeout'] = 10.0
            return super().request(*args, **kwargs)
    session = TimeoutSession(impersonate="chrome")
    return yf.Ticker(symbol, session=session)


_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
CFG_DIR  = os.path.join(BASE, "config")

# 已知板块领头羊：当这些股票大涨，联动标的自动进候选池
LEADER_PAIRS = [
    ("COIN",    5.0, ["MSTR", "MARA", "RIOT", "IREN"]),
    ("BTC-USD", 4.0, ["MSTR", "MARA", "RIOT"]),
    ("IONQ",    5.0, ["RGTI", "QBTS", "QUBT"]),
    ("NVDA",    4.0, ["CRWV", "SMCI", "IREN"]),
    ("CSCO",    8.0, ["ANET", "INFN"]),
]

def load_all_symbols():
    """从关注列表+板块列表加载所有候选标的"""
    syms = set()
    # poll config
    cfg_path = os.path.join(CFG_DIR, "poll_config.json")
    if os.path.exists(cfg_path):
        cfg = json.load(open(cfg_path, encoding="utf-8"))
        syms.update(cfg.get("default_symbols", []))
        syms.update(cfg.get("watchlist", []))
    # sector watchlist
    sec_path = os.path.join(CFG_DIR, "sector_watchlist.json")
    if os.path.exists(sec_path):
        sec = json.load(open(sec_path, encoding="utf-8"))
        for sector in sec.get("sectors", {}).values():
            syms.update(sector.get("stocks", []))
    # 移除中概股（用户偏好）
    exclude = {"BABA", "PONY", "PDD", "JD", "BIDU", "NIO", "LI", "XPEV"}
    return [s for s in syms if s not in exclude and not s.startswith("_")]

def get_stock_snapshot(sym):
    """获取单只股票的盘前快照数据"""
    try:
        t = get_ticker(sym)
        info = t.info
        h5d  = t.history(period="5d")
        if h5d.empty or len(h5d) < 3:
            raise ValueError("No historical price history returned from yfinance")

        prev_close = float(h5d["Close"].iloc[-1])  # 昨收
        close_2d   = float(h5d["Close"].iloc[-3])  # 2日前

        # 盘前价
        pre_price = info.get("preMarketPrice") or info.get("regularMarketPrice") or prev_close
        gap_pct   = (pre_price - prev_close) / prev_close * 100 if prev_close else 0

        # 盘前量比
        pre_vol   = info.get("preMarketVolume") or 0
        avg_vol   = info.get("averageVolume") or 1
        vol_ratio = pre_vol / avg_vol if avg_vol > 0 else 0

        # 近2日跌幅
        recent_2d = (prev_close - close_2d) / close_2d * 100 if close_2d else 0

        # 空头比例
        short_pct = (info.get("shortPercentOfFloat") or 0) * 100

        # 成功记录状态
        try:
            from agents.error_logger import record_yfinance_status
            record_yfinance_status(sym, True)
        except Exception:
            pass

        return {
            "sym":        sym,
            "prev_close": round(prev_close, 2),
            "pre_price":  round(pre_price, 2),
            "gap_pct":    round(gap_pct, 2),
            "vol_ratio":  round(vol_ratio, 2),
            "recent_2d":  round(recent_2d, 2),
            "short_pct":  round(short_pct, 1),
        }
    except Exception as e:
        # 失败记录状态
        try:
            from agents.error_logger import record_yfinance_status
            record_yfinance_status(sym, False, str(e))
        except Exception:
            pass
        return None

def check_leader_triggers():
    """检查板块领头羊是否触发，返回需要加入候选池的联动标的"""
    triggered = {}
    for leader, threshold, followers in LEADER_PAIRS:
        try:
            t = get_ticker(leader)
            info = t.info
            pre  = info.get("preMarketPrice") or info.get("regularMarketPrice")
            prev = info.get("regularMarketPreviousClose")
            if pre and prev:
                chg = (pre - prev) / prev * 100
                if chg >= threshold:
                    for f in followers:
                        if f not in triggered:
                            triggered[f] = []
                        triggered[f].append(f"{leader}+{chg:.1f}%")
        except Exception:
            continue
    return triggered

def score_candidate(snap, leader_trigger=None):
    """给候选标的打分，返回 (score, reasons)"""
    score, reasons = 0, []

    # A. 盘前异动型
    if snap["gap_pct"] >= 4.0:
        score += 30
        reasons.append(f"盘前+{snap['gap_pct']:.1f}%")
    elif snap["gap_pct"] >= 2.0:
        score += 15
        reasons.append(f"盘前+{snap['gap_pct']:.1f}%(轻度)")

    if snap["vol_ratio"] >= 1.2:
        score += 15
        reasons.append(f"量比{snap['vol_ratio']:.1f}x")

    # B. 超卖反弹型
    if snap["recent_2d"] <= -3.0 and snap["short_pct"] >= 10:
        score += 35
        reasons.append(f"近2日{snap['recent_2d']:.1f}%+空头{snap['short_pct']:.0f}%→轧空设置")
    elif snap["recent_2d"] <= -3.0:
        score += 15
        reasons.append(f"近2日{snap['recent_2d']:.1f}%超卖")

    # C. 板块领头羊联动
    if leader_trigger:
        score += 25
        reasons.append(f"板块联动:{','.join(leader_trigger)}")

    return score, reasons

def scan(top_n=15):
    print(f"{'='*60}")
    print(f"  候选池扫描  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"{'='*60}")

    # 1. 检查板块领头羊
    print("检查板块领头羊触发...")
    leader_triggers = check_leader_triggers()
    if leader_triggers:
        for sym, leaders in leader_triggers.items():
            print(f"  >> {sym} 被触发：{', '.join(leaders)}")
    else:
        print("  无板块领头羊触发")

    # 2. 加载全部标的
    all_syms = load_all_symbols()
    # 确保领头羊联动标的也在列表里
    for sym in leader_triggers:
        if sym not in all_syms:
            all_syms.append(sym)

    print(f"\n扫描 {len(all_syms)} 只标的...")

    # 3. 拉取快照并打分
    candidates = []
    for sym in all_syms:
        snap = get_stock_snapshot(sym)
        if snap is None:
            continue
        lt = leader_triggers.get(sym)
        score, reasons = score_candidate(snap, lt)
        if score > 0:
            candidates.append({**snap, "score": score, "reasons": reasons})

    # 4. 排序输出
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top = candidates[:top_n]

    print(f"\n{'─'*60}")
    print(f"  今日候选池 TOP {min(top_n, len(top))}  ({len(candidates)} 只有信号)")
    print(f"{'─'*60}")
    for i, c in enumerate(top, 1):
        print(f"\n#{i:2d} {c['sym']:6s} ${c['pre_price']:.2f}  得分{c['score']}")
        print(f"     盘前{c['gap_pct']:+.1f}%  量比{c['vol_ratio']:.1f}x  近2日{c['recent_2d']:+.1f}%  空头{c['short_pct']:.0f}%")
        for r in c["reasons"]:
            print(f"     → {r}")

    syms_out = [c["sym"] for c in top]
    print(f"\n{'─'*60}")
    print(f"建议输入 premarket.py: python3.12 agents/premarket.py {' '.join(syms_out)}")

    # 5. 保存结果
    out = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now(timezone.utc).strftime("%H:%M UTC"),
        "candidates": top,
        "leader_triggers": leader_triggers,
    }
    out_path = os.path.join(BASE, f"candidates_{datetime.now().strftime('%Y-%m-%d')}.json")
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"已保存: {out_path}")
    return top

def panic_pressure_test(symbols=None, spy_threshold=-1.0):
    """
    恐慌压力测试：大盘下跌时筛选相对强势股
    spy_threshold: SPY跌幅超过此值时触发测试（默认-1%）
    返回按RS排名的结果
    """

    # 检查是否满足"恐慌"条件
    spy_h = get_ticker("SPY").history(period="5d")
    if spy_h.empty:
        return []
    spy_1d = (float(spy_h["Close"].iloc[-1]) - float(spy_h["Close"].iloc[-2])) / float(spy_h["Close"].iloc[-2]) * 100
    spy_5d = (float(spy_h["Close"].iloc[-1]) - float(spy_h["Close"].iloc[-5])) / float(spy_h["Close"].iloc[-5]) * 100

    # 宇宙：从永久列表+关注列表+板块列表合并
    universe = set(symbols or [])
    wl_path = os.path.join(BASE, "watchlist_permanent.json")
    if os.path.exists(wl_path):
        wl = json.load(open(wl_path, encoding="utf-8"))
        for tier in ["quality_stable", "strong_catalyst", "watching"]:
            universe.update(wl.get(tier, {}).keys())
    universe.update(load_all_symbols())
    universe -= {"BABA", "PONY", "PDD", "JD", "BIDU"}

    results = []
    for sym in universe:
        if sym.startswith("_"):
            continue
        try:
            h = get_ticker(sym).history(period="10d")
            if len(h) < 5:
                continue
            d1  = (float(h["Close"].iloc[-1]) - float(h["Close"].iloc[-2])) / float(h["Close"].iloc[-2]) * 100
            d5  = (float(h["Close"].iloc[-1]) - float(h["Close"].iloc[-5])) / float(h["Close"].iloc[-5]) * 100
            rs1 = d1 - spy_1d
            rs5 = d5 - spy_5d
            vol_ratio = float(h["Volume"].iloc[-1]) / float(h["Volume"].iloc[:-1].mean())
            results.append({
                "sym": sym, "d1": round(d1,2), "d5": round(d5,2),
                "rs1": round(rs1,2), "rs5": round(rs5,2),
                "vol_ratio": round(vol_ratio,2),
                "quality_score": round(rs5*0.6 + rs1*0.4, 2)
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["quality_score"], reverse=True)

    print(f"\n{'='*60}")
    print(f"  恐慌压力测试  SPY今日{spy_1d:+.1f}% / 5日{spy_5d:+.1f}%")
    print(f"{'='*60}")

    tiers = [("[极强] RS5d>4%", lambda r: r["rs5"] > 4),
             ("[强势] RS5d 0-4%", lambda r: 0 <= r["rs5"] <= 4),
             ("[中性] RS5d -3~0%", lambda r: -3 <= r["rs5"] < 0),
             ("[弱势] RS5d<-3%", lambda r: r["rs5"] < -3)]

    for label, fn in tiers:
        group = [r for r in results if fn(r)]
        if group:
            print(f"\n{label}:")
            for r in group[:10]:
                vr = f"量比{r['vol_ratio']:.1f}x" if r["vol_ratio"] > 1.3 else ""
                print(f"  {r['sym']:6} 1日{r['d1']:+5.1f}% 5日{r['d5']:+5.1f}% RS5d{r['rs5']:+5.1f}% {vr}")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="候选池扫描器")
    parser.add_argument("--top", type=int, default=15, help="输出前N只候选")
    args = parser.parse_args()
    scan(top_n=args.top)
