#!/usr/bin/env python3
import sys, os, json, readline, subprocess, time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from agents.protocol import BASE, STRATEGY_PATH, LOCK_PATH, VERIFIED_PATH
from agents.cio import phase0, phase1, phase2, acquire_lock, release_lock
from utils import get_logger, fetch_with_retry, atomic_write_json

log = get_logger(__name__)
PYTHON     = sys.executable
AGENTS_DIR = os.path.join(BASE, "agents")
WATCHLIST  = os.path.join(BASE, "watchlist.json")

def load_watchlist():
    return json.load(open(WATCHLIST))

def run_full_analysis(symbol):
    print(f"\n[CIO] 开始分析 {symbol}...")
    if not acquire_lock(symbol):
        return
    try:
        ok = phase0(symbol)
        if not ok: return
        phase1(symbol)
        phase2(symbol)
        subprocess.run([PYTHON, os.path.join(AGENTS_DIR, "strategy_agent.py"), symbol], cwd=BASE)
        subprocess.run([PYTHON, os.path.join(AGENTS_DIR, "report_agent.py"), symbol], cwd=BASE)
    finally:
        release_lock()

def check_schedule(last_run_times, cfg):
    now_utc = datetime.now(timezone.utc)
    hhmm    = now_utc.strftime("%H:%M")
    for trigger_time in [cfg["schedule"]["pre_market_utc"], cfg["schedule"]["post_market_utc"]]:
        if hhmm == trigger_time and last_run_times.get(trigger_time, "") != now_utc.strftime("%Y-%m-%d"):
            last_run_times[trigger_time] = now_utc.strftime("%Y-%m-%d")
            return True
    return False

def check_events(cfg):
    alerts = cfg.get("alerts", {})
    triggered = []
    import yfinance as yf
    for symbol in cfg.get("watchlist", []):
        try:
            t    = yf.Ticker(symbol)
            hist = fetch_with_retry(lambda: t.history(period="30d"))
            if len(hist) < 15: continue
            close    = hist["Close"].iloc[-1]
            prev     = hist["Close"].iloc[-2]
            volume   = hist["Volume"].iloc[-1]
            vol_ma20 = hist["Volume"].rolling(20).mean().iloc[-1]
            chg_pct  = abs(close - prev) / prev * 100
            if chg_pct > alerts.get("price_change_pct", 3):
                triggered.append((symbol, f"价格异动 {chg_pct:.1f}%")); continue
            if vol_ma20 and volume > vol_ma20 * alerts.get("volume_ratio", 2.0):
                triggered.append((symbol, "成交量暴增")); continue
            delta = hist["Close"].diff()
            gain  = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
            loss  = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
            rsi14 = (100 - 100 / (1 + gain / loss)).iloc[-1]
            if rsi14 > alerts.get("rsi14_high", 75):
                triggered.append((symbol, f"RSI-14={rsi14:.1f} 进入超买"))
            elif rsi14 < alerts.get("rsi14_low", 25):
                triggered.append((symbol, f"RSI-14={rsi14:.1f} 进入超卖"))
        except Exception:
            continue
    return triggered

def handle_user_input(user_input, cfg):
    ui = user_input.strip().lower()
    if not ui: return
    if ui == "status":
        if os.path.exists(LOCK_PATH):
            lock = json.load(open(LOCK_PATH))
            age  = time.time() - lock.get("start_time", 0)
            print(f"[状态] 分析进行中: {lock.get('symbol')} ({age:.0f}s)")
        else:
            print("[状态] 空闲")
        return
    if ui == "last":
        if os.path.exists(STRATEGY_PATH):
            result = json.load(open(STRATEGY_PATH))
            subprocess.run([PYTHON, os.path.join(AGENTS_DIR, "report_agent.py"), result["symbol"]], cwd=BASE)
        else:
            print("[提示] 尚无历史报告")
        return
    if ui.startswith("analyze "):
        run_full_analysis(ui.split()[1].upper()); return
    if ui.startswith("add "):
        symbol = ui.split()[1].upper()
        wl = json.load(open(WATCHLIST))
        if symbol not in wl["watchlist"]:
            wl["watchlist"].append(symbol)
            atomic_write_json(wl, WATCHLIST, indent=2)
            print(f"[自选股] 已添加 {symbol}")
        return
    if ui == "list":
        print("[自选股]", ", ".join(json.load(open(WATCHLIST))["watchlist"])); return
    if ui in ("quit", "exit", "q"):
        print("再见！"); sys.exit(0)
    symbol = ui.upper()
    if symbol.isalpha():
        run_full_analysis(symbol)
    else:
        print("[提示] 命令: analyze <symbol> | add <symbol> | list | status | last | quit")

def main():
    print("=== Stock Agent Team ===")
    print("输入股票代码分析，或 quit 退出\n")
    cfg = load_watchlist()
    last_run_times = {}
    last_event_check = 0
    queued_inputs  = []

    while True:
        if check_schedule(last_run_times, cfg) and not os.path.exists(LOCK_PATH):
            for sym in cfg["watchlist"]:
                run_full_analysis(sym)
        if time.time() - last_event_check > 300:
            last_event_check = time.time()
            if not os.path.exists(LOCK_PATH):
                for sym, reason in check_events(cfg):
                    print(f"\n[警报] {sym}: {reason}，触发分析...")
                    run_full_analysis(sym)
        if queued_inputs and not os.path.exists(LOCK_PATH):
            for qi in queued_inputs:
                handle_user_input(qi, cfg)
            queued_inputs.clear()
        try:
            user_input = input(">>> ").strip()
            if os.path.exists(LOCK_PATH):
                print("[提示] 分析进行中，输入已排队")
                queued_inputs.append(user_input)
            else:
                handle_user_input(user_input, cfg)
        except (EOFError, KeyboardInterrupt):
            print("\n退出"); break

if __name__ == "__main__":
    main()
