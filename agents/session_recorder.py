"""
交易记录系统 — 分层存储

层1: snapshots_{date}.jsonl     → 日内2分钟快照，盘后自动删除
层2: trading_history.jsonl      → 永久保留：每次操作 + 决策时的市场快照
层3: session_{date}.md          → 每日摘要，永久保留（由层2自动生成）
"""
import sys, os, json, glob
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR  = os.path.join(BASE, "knowledge")
os.makedirs(LOG_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(LOG_DIR, "trading_history.jsonl")

def today():
    return datetime.now().strftime("%Y-%m-%d")

def snapshot_path():
    return os.path.join(LOG_DIR, f"snapshots_{today()}.jsonl")

# ── 层1：日内快照（自动删除）─────────────────────────────
def write_snapshot(stocks_data: dict, vix_data: dict, spy_chg: float, qqq_chg: float):
    """每2分钟写一行快照，盘后自动清理"""
    ts = datetime.now(timezone.utc).strftime("%H:%M")
    entry = {
        "time": ts,
        "spy": round(spy_chg, 2),
        "qqq": round(qqq_chg, 2),
        "vix": round(vix_data.get("cur", 20), 1),
        "vix_trend": vix_data.get("trend", "→平"),
        "stocks": {
            sym: {
                "price": round(d.get("cur", 0), 2),
                "chg":   round(d.get("chg", 0), 2),
                "rs":    round(d.get("chg", 0) - spy_chg, 2),  # 相对大盘强度
                "rsi3":  round(d.get("rsi3", 50), 0),
                "macd":  round(d.get("hist", 0), 3),
                "vwap":  round(d.get("dvwap", 0), 1),
                "vol":   d.get("vol", "─"),
                "bars":  d.get("bars", "─────"),
            }
            for sym, d in stocks_data.items() if d
        }
    }
    with open(snapshot_path(), "a") as f:
        f.write(json.dumps(entry) + "\n")

def cleanup_old_snapshots(keep_days=1):
    """删除超过 keep_days 天的快照文件"""
    cutoff = datetime.now() - timedelta(days=keep_days)
    for f in glob.glob(os.path.join(LOG_DIR, "snapshots_*.jsonl")):
        date_str = os.path.basename(f).replace("snapshots_","").replace(".jsonl","")
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date.date() < cutoff.date():
                os.remove(f)
                print(f"[SessionLog] 已删除过期快照: {f}")
        except: pass

# ── 层2：永久决策记录 ─────────────────────────────────────
def _get_latest_snapshot():
    """拿到最近一条快照作为决策时的市场上下文"""
    path = snapshot_path()
    if not os.path.exists(path): return {}
    lines = [l for l in open(path) if l.strip()]
    return json.loads(lines[-1]) if lines else {}

def log_action(action_type: str, sym: str, price: float, reason: str = "",
               stop: float = None, target: float = None, size: str = "",
               tags: list = None):
    """
    永久记录一次操作 + 决策时的完整市场状态

    action_type: buy / sell / stop_hit / partial_sell / observation / plan
    reason: 用自己的话描述为什么，越详细越好
    tags: ["开盘区间突破", "RS极强", "MACD翻正"] 等标签方便后续归纳
    """
    ts_utc = datetime.now(timezone.utc).isoformat()
    mkt_ctx = _get_latest_snapshot()  # 决策时的市场快照

    entry = {
        "date":    today(),
        "time":    datetime.now(timezone.utc).strftime("%H:%M UTC"),
        "type":    action_type,
        "sym":     sym,
        "price":   price,
        "reason":  reason,
        "stop":    stop,
        "target":  target,
        "size":    size,
        "tags":    tags or [],
        # 决策时的完整市场状态（精简保留）
        "market_ctx": {
            "spy_chg": mkt_ctx.get("spy", 0),
            "qqq_chg": mkt_ctx.get("qqq", 0),
            "vix":     mkt_ctx.get("vix", 0),
            "vix_trend": mkt_ctx.get("vix_trend", ""),
            "sym_state": mkt_ctx.get("stocks", {}).get(sym, {}),
        },
        "ts": ts_utc,
    }

    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[SessionLog ✓] {entry['time']} {action_type.upper()} {sym} ${price}")
    if reason: print(f"  原因: {reason}")
    return entry

def log_thought(category: str, content: str, sym: str = ""):
    """
    记录想法/观察/搜索，永久保留

    category: idea / search / observation / question / mistake / lesson
    """
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    mkt_ctx = _get_latest_snapshot()
    entry = {
        "date":     today(),
        "time":     ts,
        "type":     "thought",
        "category": category,
        "sym":      sym,
        "content":  content,
        "market_ctx": {
            "spy_chg": mkt_ctx.get("spy", 0),
            "vix":     mkt_ctx.get("vix", 0),
        },
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[SessionLog ✓] {ts} [{category}] {content[:60]}")

# ── 层3：每日摘要（从层2生成）────────────────────────────
def build_daily_summary(date=None):
    """从 trading_history 提取当日记录，生成 session_{date}.md"""
    d = date or today()
    if not os.path.exists(HISTORY_FILE):
        print("[SessionLog] 无历史记录"); return

    today_entries = [json.loads(l) for l in open(HISTORY_FILE) if l.strip()
                     and json.loads(l).get("date") == d]

    if not today_entries:
        print(f"[SessionLog] {d} 无记录"); return

    actions  = [e for e in today_entries if e["type"] != "thought"]
    thoughts = [e for e in today_entries if e["type"] == "thought"]

    # 构建日记
    md = f"# 交易日记 {d}\n\n"

    if actions:
        md += "## 操作记录\n\n"
        for a in actions:
            md += f"### {a['time']} | {a['type'].upper()} {a['sym']} ${a['price']}\n"
            if a.get("reason"): md += f"**原因**: {a['reason']}\n"
            if a.get("stop"):   md += f"**止损**: ${a['stop']}\n"
            if a.get("target"): md += f"**目标**: ${a['target']}\n"
            if a.get("size"):   md += f"**仓位**: {a['size']}\n"
            if a.get("tags"):   md += f"**标签**: {', '.join(a['tags'])}\n"
            ctx = a.get("market_ctx", {})
            if ctx:
                sym_s = ctx.get("sym_state", {})
                md += f"\n决策时市场状态:\n"
                md += f"- SPY {ctx.get('spy_chg',0):+.2f}%  VIX {ctx.get('vix',0):.1f}{ctx.get('vix_trend','')}\n"
                if sym_s:
                    md += (f"- {a['sym']}: ${sym_s.get('price',0):.2f}  "
                           f"RS{sym_s.get('rs',0):+.2f}%  "
                           f"RSI3={sym_s.get('rsi3',0):.0f}  "
                           f"MACD={sym_s.get('macd',0):+.3f}  "
                           f"{sym_s.get('bars','')}\n")
            md += "\n"

    # 未知条件（自动检测）
    unknowns = []
    for a in actions:
        if not a.get("reason"): unknowns.append(f"❓ {a['sym']} {a['type']} 的具体理由未记录")
        if a["type"]=="buy" and not a.get("stop"): unknowns.append(f"❓ {a['sym']} 止损依据未记录")

    if unknowns:
        md += "## 复盘前需明确的未知条件\n\n"
        for u in unknowns: md += f"- {u}\n"
        md += "\n"

    if thoughts:
        md += "## 想法/观察/教训\n\n"
        for t in thoughts:
            icon = {"idea":"💡","search":"🔍","observation":"👁","mistake":"❌","lesson":"📚","question":"❓"}.get(t["category"],"📝")
            md += f"- {t['time']} {icon}[{t['category']}] {t['content']}"
            if t.get("sym"): md += f"（关于 {t['sym']}）"
            md += "\n"
        md += "\n"

    md += "## 盘后问题（供 agent 复盘讨论）\n\n"
    md += "- 今日操作有哪些可以改进？\n"
    md += "- 止损/入场时机是否合理？\n"
    md += "- 明日值得关注的机会？\n"

    out = os.path.join(LOG_DIR, f"session_{d}.md")
    open(out, "w").write(md)
    print(f"[SessionLog] 日记已生成: {out}")
    return out

# ── 归纳统计（长期分析）─────────────────────────────────
def summarize_patterns(n_days=30):
    """从 trading_history 归纳最近 N 天的行为模式"""
    if not os.path.exists(HISTORY_FILE): return
    entries = [json.loads(l) for l in open(HISTORY_FILE) if l.strip()]
    actions = [e for e in entries if e["type"] != "thought"]
    if not actions: return

    total = len(actions)
    buys  = [a for a in actions if a["type"] == "buy"]
    tags  = {}
    for a in actions:
        for t in a.get("tags", []):
            tags[t] = tags.get(t, 0) + 1

    print(f"\n=== 最近 {n_days} 天行为模式（共 {total} 次操作）===")
    print(f"  买入: {len(buys)} 次")
    if tags:
        print("  常用标签:")
        for tag, cnt in sorted(tags.items(), key=lambda x: -x[1])[:10]:
            print(f"    {tag}: {cnt}次")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "build":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        build_daily_summary(date)
    elif cmd == "cleanup":
        cleanup_old_snapshots(1)
    elif cmd == "patterns":
        summarize_patterns()
    elif cmd == "action":
        # python session_recorder.py action buy AAOX 69 "RS极强" 65 80 "RS极强,MACD翻正"
        _, _, act, sym, price, *rest = sys.argv
        reason = rest[0] if len(rest)>0 else ""
        stop   = float(rest[1]) if len(rest)>1 else None
        tgt    = float(rest[2]) if len(rest)>2 else None
        tags   = rest[3].split(",") if len(rest)>3 else []
        log_action(act, sym, float(price), reason, stop, tgt, tags=tags)
    elif cmd == "thought":
        # python session_recorder.py thought lesson "今天LITE暴跌是板块预警" AAOI
        _, _, cat, content, *rest = sys.argv
        sym = rest[0] if rest else ""
        log_thought(cat, content, sym)
    else:
        print("用法: build | cleanup | patterns | action | thought")
