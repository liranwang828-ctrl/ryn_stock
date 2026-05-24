"""
盘后汇总模块 — postmarket_summary.py
组合 postmarket_data_collector 的结构化数据，写出：
  postmarket_summary_{date}_{sym}.json  per-stock
  postmarket_summary_{date}.json        per-day

用法: python3.12 agents/postmarket_summary.py [SYM1 SYM2 ...]
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.postmarket_data_collector import (
    build_execution, build_performance, build_signal_accuracy, generate_suggestions,
)

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")
CFG_DIR  = os.path.join(BASE, "config")


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def build_per_stock_summary(
    sym: str, date: str,
    day_ret_pct: float | None = None,
    base_dir: str = BASE,
) -> dict:
    """构建 per-stock postmarket_summary dict"""
    find_dir = os.path.join(base_dir, "findings")
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    pos = pos_data.get("positions", {}).get(sym.upper(), {})

    execution      = build_execution(sym, date, base_dir=base_dir)
    performance    = build_performance(sym, date, base_dir=base_dir)
    if day_ret_pct is not None:
        performance["day_ret_pct"] = day_ret_pct   # 外部注入（测试用）
    actual_ret     = performance.get("day_ret_pct")
    signal_acc     = build_signal_accuracy(sym, date, day_ret_pct=actual_ret,
                                           base_dir=base_dir)
    suggestions    = generate_suggestions(
        sym=sym, date=date,
        execution=execution,
        performance=performance,
        signal_accuracy=signal_acc,
    )

    return {
        "date":          date,
        "sym":           sym.upper(),
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "execution":     execution,
        "performance":   performance,
        "signal_accuracy": signal_acc,
        "snapshot_thesis_status": pos.get("thesis_status"),  # 收盘快照
        "learning_notes": "",      # 待 LLM 生成（存根）
        "next_day": {
            "suggestions":  suggestions,
            "summary_note": "",    # 待 LLM 生成（存根）
        },
    }


def write_per_stock_summary(sym: str, date: str, data: dict,
                             base_dir: str = BASE) -> str:
    """写出 per-stock JSON，返回路径"""
    find_dir = os.path.join(base_dir, "findings")
    os.makedirs(find_dir, exist_ok=True)
    fname = f"postmarket_summary_{date}_{sym.upper()}.json"
    path  = os.path.join(find_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def build_per_day_summary(date: str, per_stock: list[dict],
                           base_dir: str = BASE) -> dict:
    """构建 per-day postmarket_summary dict（简化，不含相关性矩阵）"""
    syms = [d["sym"] for d in per_stock]
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    positions = pos_data.get("positions", {})

    # 加权平均日收益
    total_val = total_ret = 0.0
    best = worst = None
    for d in per_stock:
        sym = d["sym"]
        pos = positions.get(sym, {})
        shares = float(pos.get("shares", 0) or 0)
        open_p = d.get("performance", {}).get("open_price") or 0.0
        ret    = d.get("performance", {}).get("day_ret_pct") or 0.0
        w      = shares * open_p
        total_val += w
        total_ret += w * ret
        if best is None or ret > (per_stock[[d["sym"] for d in per_stock].index(sym)].get(
                "performance", {}).get("day_ret_pct", 0) or 0):
            best = sym
        if worst is None:
            worst = sym

    total_day_ret = round(total_ret / total_val, 2) if total_val > 0 else None

    # 汇总明日风险
    tomorrow_risks = []
    for d in per_stock:
        for s in d.get("next_day", {}).get("suggestions", []):
            if s["type"] == "tomorrow_risk_calendar":
                tomorrow_risks.extend(s.get("proposed_value", {}).get("events", []))

    pending = sum(
        1 for d in per_stock
        for s in d.get("next_day", {}).get("suggestions", [])
        if s.get("confirmed") is None
    )

    return {
        "date":            date,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "symbols":         syms,
        "portfolio": {
            "total_day_ret_pct":    total_day_ret,
            "best_performer":       best,
            "worst_performer":      worst,
            "correlation_matrix":   {},   # 需要 yfinance 历史数据，后续实现
            "max_correlation_pair": [],
            "max_correlation_value": None,
            "concentration_risk":   "medium",
        },
        "tomorrow_risk_calendar":  list(set(tomorrow_risks)),
        "pending_suggestions_count": pending,
        "llm_review": "",    # 待 LLM 生成（存根）
    }


def write_per_day_summary(date: str, data: dict, base_dir: str = BASE) -> str:
    """写出 per-day JSON，返回路径"""
    find_dir = os.path.join(base_dir, "findings")
    os.makedirs(find_dir, exist_ok=True)
    path = os.path.join(find_dir, f"postmarket_summary_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def main(syms: list[str] | None = None):
    date_str = _date.today().strftime("%Y-%m-%d")
    if not syms:
        cfg  = _load(os.path.join(CFG_DIR, "poll_config.json"))
        syms = cfg.get("default_symbols", [])

    print(f"\n{'='*60}")
    print(f"  盘后复盘 {date_str}  （{len(syms)} 只标的）")
    print(f"{'='*60}\n")

    per_stock_data = []
    for sym in syms:
        try:
            data = build_per_stock_summary(sym, date_str)
            path = write_per_stock_summary(sym, date_str, data)
            per_stock_data.append(data)
            ret = data.get("performance", {}).get("day_ret_pct")
            ret_str = f"{ret:+.1f}%" if ret is not None else "N/A"
            print(f"  {sym}: {ret_str}  OK {os.path.basename(path)}")
        except Exception as e:
            print(f"  {sym}: FAIL {e}")

    if per_stock_data:
        day_data = build_per_day_summary(date_str, per_stock_data)
        day_path = write_per_day_summary(date_str, day_data)
        pending  = day_data.get("pending_suggestions_count", 0)
        print(f"\n  per-day: OK {os.path.basename(day_path)}  （{pending} 条待确认建议）")


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
