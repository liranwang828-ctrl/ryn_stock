"""
Fundamentals Tracker — 追踪基本面变化
每次财报后运行（约每季度一次）：记录营收/毛利率/FCF变化趋势

用法: python3.12 agents/fundamentals_tracker.py [--symbols ...]
"""
import sys, os, json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
HIST_PATH = os.path.join(BASE, "learning", "fundamentals_history.jsonl")
QUALITY_PATH = os.path.join(BASE, "learning", "quality_archive.json")

def track_fundamentals(sym):
    try:
        t = yf.Ticker(sym)
        info = t.info
        today = datetime.now().strftime("%Y-%m-%d")

        record = {
            "sym": sym, "date": today,
            "rev_growth": round((info.get("revenueGrowth") or 0) * 100, 1),
            "gross_margin": round((info.get("grossMargins") or 0) * 100, 1),
            "fcf_margin": round(((info.get("operatingCashflow") or 0) - abs(info.get("capitalExpenditures") or 0)) / max(info.get("totalRevenue") or 1, 1) * 100, 1),
            "revenue": info.get("totalRevenue") or 0,
            "eps": info.get("trailingEps") or 0,
        }

        with open(HIST_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # Check for deterioration vs last quarter
        history = [json.loads(l) for l in open(HIST_PATH, encoding="utf-8") if l.strip() and json.loads(l).get("sym") == sym]
        if len(history) >= 2:
            prev = history[-2]
            curr = history[-1]
            warnings = []
            if curr["rev_growth"] < prev["rev_growth"] - 10:
                warnings.append(f"营收增速下滑 {prev['rev_growth']:.0f}%→{curr['rev_growth']:.0f}%")
            if curr["gross_margin"] < prev["gross_margin"] - 3:
                warnings.append(f"毛利率下滑 {prev['gross_margin']:.0f}%→{curr['gross_margin']:.0f}%")

            if warnings and os.path.exists(QUALITY_PATH):
                qa = json.load(open(QUALITY_PATH, encoding="utf-8"))
                if sym in qa:
                    qa[sym]["fundamental_warnings"] = warnings
                    qa[sym]["last_check"] = today
                    json.dump(qa, open(QUALITY_PATH, "w", encoding="utf-8"), indent=2)
                    print(f"⚠️  {sym} 基本面警告: {'; '.join(warnings)}")
        return record
    except Exception as e:
        print(f"  {sym}: 获取失败 {e}")
        return None

def run(symbols=None):
    if not symbols:
        # Use all symbols from quality_archive
        qa = json.load(open(QUALITY_PATH, encoding="utf-8")) if os.path.exists(QUALITY_PATH) else {}
        symbols = [s for s in qa.keys() if not s.startswith("_") and qa[s].get("quality_pass")]

    print(f"Fundamentals Tracker: {len(symbols)}只标的")
    for sym in symbols:
        print(f"  {sym}...", end=" ", flush=True)
        r = track_fundamentals(sym)
        if r:
            print(f"营收增速{r['rev_growth']:+.0f}%  毛利率{r['gross_margin']:.0f}%  FCF{r['fcf_margin']:+.0f}%")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="*")
    args = parser.parse_args()
    run(args.symbols)
