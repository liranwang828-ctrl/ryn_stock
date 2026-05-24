"""
系统健康检查 — 一键查看所有关键组件状态
用法: python3.12 agents/health_check.py
"""
import sys, os, json
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
LRN  = os.path.join(BASE, "learning")
ET   = timezone(timedelta(hours=-4))

def check(label, ok, detail=""):
    icon = "✅" if ok else "❌"
    print(f"  {icon} {label:35} {detail}")

def run():
    now = datetime.now(ET)
    print(f"\n{'═'*60}")
    print(f"  系统健康检查  {now.strftime('%Y-%m-%d %H:%M ET')}")
    print(f"{'═'*60}\n")

    # ── 数据文件 ──────────────────────────────────────────────
    print("【数据文件】")
    import pandas as pd
    pq = os.path.join(LRN, "historical_features.parquet")
    if os.path.exists(pq):
        df = pd.read_parquet(pq)
        check("历史特征矩阵", True, f"{len(df)}行 {len(df['sym'].unique())}只标的")
    else:
        check("历史特征矩阵", False, "未生成，需运行 bootstrap_agent.py")

    harvest_p = os.path.join(LRN, "daily_harvest.jsonl")
    rows = [json.loads(l) for l in open(harvest_p, encoding="utf-8") if l.strip()] if os.path.exists(harvest_p) else []
    last_harvest = rows[-1].get("harvest_date", rows[-1].get("date","?")) if rows else "从未"
    today = now.strftime("%Y-%m-%d")
    check("每日记录(harvest)", bool(rows) and last_harvest >= today, f"最近:{last_harvest}  共{len(rows)}条")

    trace_p = os.path.join(LRN, "decision_trace.jsonl")
    traces = [l for l in open(trace_p, encoding="utf-8") if l.strip()] if os.path.exists(trace_p) else []
    check("决策溯源", len(traces) > 0, f"{len(traces)}条{'（空-需真实交易触发）' if not traces else ''}")

    fund_p = os.path.join(LRN, "fundamentals_history.jsonl")
    fund_rows = [l for l in open(fund_p, encoding="utf-8") if l.strip()] if os.path.exists(fund_p) else []
    check("基本面历史", len(fund_rows) > 0, f"{len(fund_rows)}条{'（空-需运行 fundamentals_tracker.py）' if not fund_rows else ''}")

    # ── 模型状态 ──────────────────────────────────────────────
    print("\n【模型状态】")
    import joblib
    for track in ["intraday", "swing"]:
        path = os.path.join(LRN, f"model_{track}.pkl")
        if os.path.exists(path):
            pkg = joblib.load(path)
            blend = pkg.get("model_macro_blend")
            mac   = pkg.get("model_macro") is not None
            mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
            check(f"model_{track}", True, f"更新:{mtime}  blend={blend}  macro={mac}")
        else:
            check(f"model_{track}", False, "不存在，需运行 bootstrap_agent.py")

    # 大师准确率
    acc_p = os.path.join(LRN, "master_accuracy.json")
    if os.path.exists(acc_p):
        acc = json.load(open(acc_p, encoding="utf-8"))
        any_updated = any(v.get("total",0)>0 for k,v in acc.items() if not k.startswith("_"))
        check("master_accuracy", any_updated, "（全是0.5=未更新，需CIO运行+harvest）" if not any_updated else "已追踪")

    cio_sigs = [f for f in os.listdir(LRN) if f.startswith("cio_signals_")] if os.path.isdir(LRN) else []
    check("CIO信号存档", len(cio_sigs) > 0, f"{len(cio_sigs)}个{'（空=CIO未运行或未部署）' if not cio_sigs else ''}")

    # ── 配置文件 ──────────────────────────────────────────────
    print("\n【配置文件】")
    for fname, label in [
        ("config/positions.json",         "持仓配置"),
        ("config/positions_mode.json",    "交易模式配置"),
        ("config/leveraged_pairs.json",   "杠杆ETF映射"),
        ("watchlist_permanent.json",      "永久观察列表"),
        ("learning/quality_archive.json", "质量档案"),
    ]:
        path = os.path.join(BASE, fname)
        exists = os.path.exists(path)
        check(label, exists, f"{'存在' if exists else '缺失'}")

    # ── 定时任务 ──────────────────────────────────────────────
    print("\n【定时任务】")
    cron_p = os.path.join(os.path.expanduser("~"), ".claude", "scheduled_tasks.json")
    if os.path.exists(cron_p):
        raw = json.load(open(cron_p, encoding="utf-8"))
        task_list = raw.get("tasks", raw) if isinstance(raw, dict) else raw
        active = [t for t in task_list if isinstance(t, dict) and not t.get("deleted")]
        check("Cron 任务", len(active) > 0, f"{len(active)}个活跃")
        for t in active[:5]:
            print(f"    • {t.get('cron','')}  {t.get('prompt','')[:50]}")
    else:
        check("Cron 任务", False, "无定时任务")

    # ── 数据源 ────────────────────────────────────────────────
    print("\n【数据源】")
    import yfinance as yf
    try:
        h = yf.Ticker("SPY").history(period="1d")
        check("yfinance", not h.empty, "正常")
    except Exception as e:
        check("yfinance", False, str(e)[:40])

    import requests
    try:
        r = requests.get("https://stooq.com/q/l/?s=spy.us&f=sd2c&h&e=csv", timeout=5)
        check("Stooq备用", r.status_code==200, "正常")
    except Exception:
        check("Stooq备用", False, "无法访问")

    # ── 错误日志 ────────────────────────────────────────────────
    print("\n【近24小时错误】")
    try:
        from agents.error_logger import get_recent_errors
        errs = get_recent_errors(hours=24)
        if errs:
            check("错误日志", False, f"近24h {len(errs)}条错误")
            for e in errs[-3:]:
                print(f"    [{e['ts'][11:16]}] {e['source']}: {e['msg'][:60]}")
        else:
            check("错误日志", True, "近24h无错误")
    except Exception:
        check("错误日志", True, "模块未加载")

    print(f"\n{'─'*60}")
    print(f"  检查完成  {datetime.now(ET).strftime('%H:%M ET')}")
    print(f"{'─'*60}\n")

if __name__ == "__main__":
    run()
