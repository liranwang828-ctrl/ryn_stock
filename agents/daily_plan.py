"""
daily_plan.py — 当日交易计划生成与管理
"""
import sys, os, json, math, random
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import atomic_write_json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def calc_stop(vwap: float, atr14: float, seed: int = None) -> float:
    """ATR止损：VWAP - ATR×0.3 + 反拥挤噪声 + 整数位检测"""
    if seed is not None:
        random.seed(seed)
    base_stop = vwap - atr14 * 0.3
    noise = random.uniform(0.003, 0.008)
    actual_stop = base_stop * (1 - noise)
    nearest_int = round(actual_stop)
    if abs(actual_stop - nearest_int) <= 0.1:
        actual_stop -= 0.3
    return round(actual_stop, 2)


def infer_scene(vol_ratio, above_prev_high, rs, macd_positive, range_pct,
                near_vwap, high_pullback_pct, below_vwap, rebound_pct,
                etf_up, rs_vs_sector) -> str:
    """Infer the actual scene A-H from observed market signals."""
    if vol_ratio >= 1.5 and rs <= -3.0 and below_vwap:
        return "F"
    if vol_ratio >= 1.3 and above_prev_high and rs > 0 and macd_positive:
        return "A"
    if rs_vs_sector >= 3.0 and vol_ratio >= 1.3:
        return "H"
    if etf_up and rs < 0:
        return "G"
    if high_pullback_pct >= 3.0 and below_vwap:
        return "D"
    if near_vwap and not below_vwap and vol_ratio < 1.0:
        return "B"
    if range_pct < 1.5 and vol_ratio < 1.0:
        return "C"
    if 1.0 <= rebound_pct <= 2.0 and not macd_positive:
        return "E"
    return "A"


_SCENE_ENTRY_HINT = {
    "A":"放量突破确认，追入或回踩突破点","B":"VWAP附近缩量企稳，3根阳线后入",
    "C":"等区间上沿放量突破再入","D":"止跌后下影确认再考虑轻仓",
    "E":"等量价齐升信号，谨慎","F":"不操作，等止跌信号",
    "G":"等RS转正再入","H":"个股领涨，VWAP或5分钟MA回踩入",
}
_T2_CONDITION_A_TPL = "价格>T1成本×1.005 + 量比>0.85x"
_T2_CONDITION_B_TPL = "缩量回踩0.3-2.5% + 守VWAP"

def _build_stock_plan(pre_data: dict, date_str: str, seed: int = None) -> dict:
    """Build a trading plan for a single stock from premarket data."""
    vwap  = pre_data.get("vwap_current") or pre_data.get("pre_price", 100.0)
    atr14 = pre_data.get("atr", 5.0)
    watch_lo = round(vwap * 0.99, 2)
    watch_hi = round(vwap * 1.01, 2)
    t1_stop   = calc_stop(vwap=vwap, atr14=atr14, seed=seed)
    entry_mid = (watch_lo + watch_hi) / 2
    t1_target1 = round(entry_mid + atr14 * 0.7, 2)
    t1_target2 = round(entry_mid + atr14 * 1.4, 2)
    scene = pre_data.get("pred_scene", "B")
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "predicted_scene": scene, "catalyst": pre_data.get("top_headline"),
        "catalyst_strength": pre_data.get("catalyst_strength", 1),
        "watch_zone_lo": watch_lo, "watch_zone_hi": watch_hi,
        "t1_entry_hint": _SCENE_ENTRY_HINT.get(scene, "参考VWAP入场"),
        "t1_stop": t1_stop, "t1_target1": t1_target1, "t1_target2": t1_target2,
        "t2_condition_a": _T2_CONDITION_A_TPL, "t2_condition_b": _T2_CONDITION_B_TPL,
        "t2_stop_mode": "t1_cost", "plan_status": "active",
        "actual_scene": None, "actual_vwap": None, "entered": False, "added_at": now_utc,
    }


def _plan_path(date_str: str) -> str:
    """Return the daily plan JSON file path for a given date."""
    return os.path.join(BASE, f"daily_plan_{date_str}.json")

def _pre_path(date_str: str) -> str:
    """Return the premarket analysis JSON file path for a given date."""
    return os.path.join(BASE, f"premarket_analysis_{date_str}.json")

def _load_plan(date_str: str) -> dict:
    """Load the daily plan from disk, returning a default skeleton if missing."""
    path = _plan_path(date_str)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"date": date_str,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "stocks": {}}

def _save_plan(plan: dict, date_str: str) -> None:
    """Atomically write the daily plan to disk."""
    path = _plan_path(date_str)
    atomic_write_json(plan, path, indent=2)

def generate_plan(symbols: list, date_str: str = None, seed: int = None) -> dict:
    """Generate the daily trading plan from premarket data for given symbols."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pre_path = _pre_path(date_str)
    if not os.path.exists(pre_path):
        raise FileNotFoundError(f"premarket 文件不存在：{pre_path}")
    with open(pre_path, encoding="utf-8") as f:
        pre = json.load(f)
    target_syms = set(symbols) if symbols else set(pre["stocks"].keys())
    plan = _load_plan(date_str)
    plan["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for sym, pre_data in pre["stocks"].items():
        if sym in target_syms:
            plan["stocks"][sym] = _build_stock_plan(pre_data, date_str, seed=seed)
    _save_plan(plan, date_str)
    return plan


def get_plan(symbol: str, date_str: str = None) -> dict:
    """Retrieve the daily plan for a single symbol."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan = _load_plan(date_str)
    return plan["stocks"].get(symbol.upper())

def get_all(date_str: str = None) -> dict:
    """Retrieve all daily plans for the given date."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan = _load_plan(date_str)
    return plan.get("stocks", {})


def add_symbol(symbol: str, date_str: str = None, seed: int = None) -> dict:
    """Add a new symbol to the existing daily plan."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sym = symbol.upper()
    pre_path = _pre_path(date_str)
    if not os.path.exists(pre_path):
        raise FileNotFoundError(f"premarket 文件不存在：{pre_path}")
    with open(pre_path, encoding="utf-8") as f:
        pre = json.load(f)
    if sym not in pre["stocks"]:
        raise KeyError(f"premarket 中无标的：{sym}")
    plan = _load_plan(date_str)
    plan["stocks"][sym] = _build_stock_plan(pre["stocks"][sym], date_str, seed=seed)
    _save_plan(plan, date_str)
    return plan["stocks"][sym]


def update_scene(symbol: str, actual_scene: str, actual_vwap: float = None,
                 date_str: str = None, infer_kwargs: dict = None) -> dict:
    """Update the actual scene and/or VWAP for a symbol in the daily plan."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sym = symbol.upper()
    plan = _load_plan(date_str)
    if sym not in plan["stocks"]:
        raise KeyError(f"标的不在当日计划中：{sym}")
    stock = plan["stocks"][sym]
    if actual_scene is None and infer_kwargs:
        actual_scene = infer_scene(**infer_kwargs)
    if actual_scene is not None:
        stock["actual_scene"] = actual_scene
    if actual_vwap is not None:
        stock["actual_vwap"] = actual_vwap
        stock["watch_zone_lo"] = round(actual_vwap * 0.99, 2)
        stock["watch_zone_hi"] = round(actual_vwap * 1.01, 2)
    _save_plan(plan, date_str)
    return stock


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="daily_plan — 当日交易计划")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("generate"); p.add_argument("symbols", nargs="*"); p.add_argument("--date", default=None)
    p = sub.add_parser("add"); p.add_argument("symbol"); p.add_argument("--date", default=None)
    p = sub.add_parser("update"); p.add_argument("symbol"); p.add_argument("scene"); p.add_argument("--vwap", type=float, default=None); p.add_argument("--date", default=None)
    p = sub.add_parser("get"); p.add_argument("symbol"); p.add_argument("--date", default=None)
    p = sub.add_parser("all"); p.add_argument("--date", default=None)
    args = parser.parse_args()
    if args.cmd == "generate":
        result = generate_plan(args.symbols or None, date_str=args.date)
        print(f"✅ 已生成 {len(result['stocks'])} 只股票的计划")
        for sym, s in result["stocks"].items():
            print(f"  {sym}: 场景={s['predicted_scene']} 止损={s['t1_stop']} 目标1={s['t1_target1']} 目标2={s['t1_target2']}")
    elif args.cmd == "add":
        s = add_symbol(args.symbol, date_str=args.date)
        print(f"✅ 已加入 {args.symbol}: 场景={s['predicted_scene']} 止损={s['t1_stop']}")
    elif args.cmd == "update":
        s = update_scene(args.symbol, actual_scene=args.scene, actual_vwap=args.vwap, date_str=args.date)
        print(f"✅ 已更新 {args.symbol}: actual_scene={s['actual_scene']} actual_vwap={s['actual_vwap']}")
    elif args.cmd == "get":
        s = get_plan(args.symbol, date_str=args.date)
        print(json.dumps(s, indent=2, ensure_ascii=False) if s else f"❌ 未找到 {args.symbol}")
    elif args.cmd == "all":
        print(json.dumps(get_all(date_str=args.date), indent=2, ensure_ascii=False))
    else:
        parser.print_help()
