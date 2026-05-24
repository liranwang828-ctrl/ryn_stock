"""
宏观策略模块 — macro_strategy.py
综合 strategic_memo + 实时市场数据，系统性制定所有交易节点。
输出: macro_strategy_{sym}.json

用法:
  python3.12 agents/macro_strategy.py NVDA          # 全量生成
  python3.12 agents/macro_strategy.py NVDA --refresh # 只更新动态节点
"""
import json, os, sys, argparse
from datetime import datetime, timezone, date as _date, timedelta

import yfinance as yf
import numpy as np
import pandas as pd

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")
CFG_DIR  = os.path.join(BASE, "config")

DEFAULT_EVOLUTION = {
    "rule_version": "1.0",
    "k1": 1.0, "k2": 0.2, "k3": 0.0, "k4": 0.90,
    "k5": 0.5, "k6": 1.0, "k_reentry": 0.3,
    "fe_catalyst": 2.0, "c1": 0.5, "c2": 1.5,
    "Z_pre_reduce_pct": 20,
    "N_time_stop": 30, "D_decay_stop": 14, "M_decay_min_pct": 5.0,
    "last_backtest_date": None, "backtest_score": None, "outcomes_count": 0,
}


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_market_data(sym: str, period: str = "6mo") -> dict:
    """从 yfinance 抓取并计算所有所需市场指标。对 SSL 错误重试最多 3 次。"""
    import time as _time
    ticker = None
    hist   = pd.DataFrame()
    info   = {}
    for _attempt in range(3):
        try:
            ticker = yf.Ticker(sym)
            hist   = ticker.history(period=period)
            info   = ticker.info or {}
            if not hist.empty:
                break
        except Exception as e:
            err_str = str(e)
            if 'SSL' in err_str or 'TLS' in err_str or 'curl' in err_str.lower():
                print(f"  ⚠️ macro_strategy SSL error (attempt {_attempt+1}/3): {err_str[:80]}")
                _time.sleep(2 * (_attempt + 1))
                continue
            break

    if hist.empty or len(hist) < 21:
        return {}

    closes  = hist["Close"].values
    highs   = hist["High"].values
    lows    = hist["Low"].values
    volumes = hist["Volume"].values

    price = float(closes[-1])

    # 移动均线
    ma20  = float(np.mean(closes[-20:])) if len(closes) >= 20 else price
    ma50  = float(np.mean(closes[-50:])) if len(closes) >= 50 else price
    ma200 = float(np.mean(closes[-200:])) if len(closes) >= 200 else price

    # ATR (Average True Range)
    def _atr(n: int) -> float:
        tr_list = []
        for i in range(1, min(n + 1, len(closes))):
            tr = max(highs[-i] - lows[-i],
                     abs(highs[-i] - closes[-i-1]),
                     abs(lows[-i]  - closes[-i-1]))
            tr_list.append(tr)
        return float(np.mean(tr_list)) if tr_list else 0.0

    atr14 = _atr(14)
    atr21 = _atr(21)

    # 摆动高低点
    swing_high_90d = float(np.max(highs[-90:])) if len(highs) >= 90 else float(np.max(highs))
    swing_low_90d  = float(np.min(lows[-90:]))  if len(lows)  >= 90 else float(np.min(lows))
    swing_low_14d  = float(np.min(lows[-14:]))  if len(lows)  >= 14 else float(np.min(lows))

    # Fibonacci 回撤（高点：近90日，低点：近14日结构支撑）
    fib_range = swing_high_90d - swing_low_14d
    fib_382 = round(swing_high_90d - 0.382 * fib_range, 2) if fib_range > 0 else price
    fib_618 = round(swing_high_90d - 0.618 * fib_range, 2) if fib_range > 0 else price

    # RSI-14
    def _rsi(n: int = 14) -> float:
        if len(closes) < n + 1:
            return 50.0
        deltas = np.diff(closes[-(n+1):])
        gains  = deltas[deltas > 0]
        losses = -deltas[deltas < 0]
        avg_gain = float(np.mean(gains))  if len(gains)  > 0 else 0.0
        avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.001
        rs = avg_gain / avg_loss
        return round(100 - 100 / (1 + rs), 1)

    rsi14 = _rsi(14)

    # 成交量比（近5日均量 / 近20日均量）
    vol_5  = float(np.mean(volumes[-5:]))  if len(volumes) >= 5  else 0.0
    vol_20 = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else 1.0
    volume_ratio = round(vol_5 / vol_20, 2) if vol_20 > 0 else 1.0

    # 分析师目标价
    analyst_target = info.get("targetMeanPrice") or info.get("targetMedianPrice")

    return {
        "price":          round(price, 2),
        "ma20":           round(ma20, 2),
        "ma50":           round(ma50, 2),
        "ma200":          round(ma200, 2),
        "atr14":          round(atr14, 2),
        "atr21":          round(atr21, 2),
        "fib_382":        fib_382,
        "fib_618":        fib_618,
        "swing_high_90d": round(swing_high_90d, 2),
        "swing_low_90d":  round(swing_low_90d, 2),
        "swing_low_14d":  round(swing_low_14d, 2),
        "rsi14":          rsi14,
        "volume_ratio":   volume_ratio,
        "analyst_target": float(analyst_target) if analyst_target else None,
        "sentiment_score": None,  # 由 memo 注入，见 build_nodes()
    }


def calc_entry_nodes(mkt: dict, ev: dict, entry_base: float,
                     unified_confidence: int, thesis_status: str) -> dict:
    """计算买入方向的所有节点：Entry Invalidation / Add1 / Add2 / Re-entry"""
    atr14  = mkt["atr14"]
    ma50   = mkt["ma50"]
    fib382 = mkt["fib_382"]
    fib618 = mkt["fib_618"]
    sw_low = mkt["swing_low_14d"]

    # Entry Invalidation：超过此价不追入
    inv_price = round(entry_base + 0.5 * atr14, 2)

    # Add1：max(Fib38.2%, MA50 + k2*ATR)，结构低点覆盖规则
    add1_base = max(fib382, round(ma50 + ev["k2"] * atr14, 2))
    # 若近14日结构低点比 max() 低超过 0.5*ATR，结构优先
    if add1_base - sw_low > 0.5 * atr14:
        add1_price = round(sw_low, 2)
        add1_basis = f"结构低点={sw_low}（优先于max={round(add1_base,2)}，差距>{round(0.5*atr14,2)}）"
    else:
        add1_price = round(add1_base, 2)
        add1_basis = f"max(Fib38.2%={fib382}, MA50({ma50})+{ev['k2']}×ATR14({atr14})={round(ma50+ev['k2']*atr14,2)})"

    add1 = {
        "price":       add1_price,
        "basis":       add1_basis,
        "conditions":  ["论点 intact", "vol_ratio < 0.8", "催化剂窗口外"],
        "invalidation":"放量跌破 MA50 → 取消 Add1",
    }

    # Add2：Fib61.8%，仅高置信度
    add2 = None
    if unified_confidence >= 4:
        add2_price = round(max(fib618, mkt["ma200"] + ev["k3"] * atr14), 2)
        add2 = {
            "price":       add2_price,
            "basis":       f"Fib61.8%={fib618}",
            "conditions":  ["unified_confidence ≥ 4"],
            "invalidation":"论点转 weakening → 取消",
        }

    # Re-entry：仅论点 intact
    re_entry = None
    if thesis_status == "intact":
        re_entry_price = round(ma50 + ev["k_reentry"] * atr14, 2)
        re_entry = {
            "price":       re_entry_price,
            "basis":       f"MA50({ma50}) + {ev['k_reentry']}×ATR14({atr14})",
            "conditions":  ["thesis_status = intact", "距止损出场 ≥ 3天"],
            "invalidation":"距止损出场不足3天 或 论点转 weakening → 取消",
        }

    return {
        "entry_invalidation": {"price": inv_price, "basis": f"entry_base({entry_base}) + 0.5×ATR14"},
        "add1":      add1,
        "add2":      add2,
        "re_entry":  re_entry,
    }


def calc_stop_nodes(mkt: dict, ev: dict, entry_base: float,
                    bear_scenario_price: float) -> dict:
    """计算止损方向节点：Dynamic Stop + Force Exit"""
    atr14  = mkt["atr14"]
    ma50   = mkt["ma50"]
    sw_low = mkt["swing_low_14d"]

    anchor     = max(ma50, sw_low)
    stop_price = round(anchor - ev["k1"] * atr14, 2)

    dynamic_stop = {
        "price":  stop_price,
        "basis":  f"max(MA50={ma50}, 近14日结构低点={sw_low}) − {ev['k1']}×ATR14({atr14}) = {stop_price}",
        "trail_activation": {
            "breakeven_trigger_pct": 8,
            "ma20_trail_trigger_pct": 15,
        },
        "invalidation": f"收盘反回 stop+0.5×ATR({round(stop_price+0.5*atr14,2)}) 且缩量 → 假突破",
        "gap_rule":     "开盘直接低于此价 → 市价出场",
    }

    catalyst_exit = round(entry_base - ev["fe_catalyst"] * atr14, 2)
    force_exit = {
        "price_bear":       bear_scenario_price,
        "price_catalyst":   catalyst_exit,
        "basis_bear":       "memo.scenarios.bear.price_target",
        "basis_catalyst":   f"entry({entry_base}) − {ev['fe_catalyst']}×ATR14({atr14})",
        "gap_rule":         "开盘低于此价 → 市价执行",
    }

    return {"dynamic_stop": dynamic_stop, "force_exit": force_exit}


def calc_target_nodes(mkt: dict, ev: dict) -> dict:
    """计算目标方向节点：TP1 / TP2 / Flex Reduce"""
    atr14        = mkt["atr14"]
    swing_high   = mkt["swing_high_90d"]
    analyst_tgt  = mkt["analyst_target"]
    price        = mkt["price"]

    if swing_high > price:
        tp1_price = round(swing_high * 0.995, 2)
    else:
        tp1_price = round(price + 1.5 * atr14, 2)

    tp1 = {
        "price":      tp1_price,
        "basis":      f"近90日高点区域 swing_high={swing_high}",
        "reduce_pct": 30,
        "gap_rule":   "开盘高于 TP1 → 按开盘价执行",
    }

    # 目标价过时检测：低于现价说明分析师尚未更新，不能作为减仓目标
    analyst_stale = bool(analyst_tgt and analyst_tgt < price)

    if analyst_tgt and not analyst_stale:
        tp2_candidate = round(analyst_tgt * ev["k4"], 2)
        tp2_price     = min(tp2_candidate, round(swing_high * 1.05, 2))
        tp2_basis     = f"分析师目标${analyst_tgt} × {ev['k4']} = {tp2_candidate}"
        tp2_invalid   = "分析师目标下调超10% → 重算"
    else:
        tp2_price = round(swing_high * 1.05, 2)
        if analyst_stale:
            tp2_basis   = (f"⚠️ 分析师目标${analyst_tgt}低于现价（过时），"
                           f"改用 swing_high({swing_high}) × 1.05")
            tp2_invalid = "分析师更新目标价后重算"
        else:
            tp2_basis   = f"无分析师目标，swing_high({swing_high}) × 1.05"
            tp2_invalid = "分析师覆盖后重算"

    tp2 = {
        "price":            tp2_price,
        "basis":            tp2_basis,
        "reduce_pct":       100,
        "invalidation":     tp2_invalid,
        "analyst_stale":    analyst_stale,
        "analyst_raw":      analyst_tgt,
    }

    flex_reduce = {
        "note":           "盘中动态，--refresh 每日更新",
        "max_reduce_pct": 15,
        "basis":          "VWAP 偏离 + RSI > 70",
    }

    return {"tp1": tp1, "tp2": tp2, "flex_reduce": flex_reduce}


def calc_scenario_nodes(mkt: dict, ev: dict, catalyst: dict = None,
                        today: _date = None, entry_base: float = None) -> dict:
    atr14 = mkt["atr14"]
    ma20  = mkt["ma20"]
    ma50  = mkt["ma50"]

    scenario_downgrade = {
        "bull_to_base": {
            "price": round(ma20 - ev["k5"] * atr14, 2),
            "basis": f"MA20({ma20}) − {ev['k5']}×ATR14({atr14})",
        },
        "base_to_bear": {
            "price": round(ma50 - ev["k6"] * atr14, 2),
            "basis": f"MA50({ma50}) − {ev['k6']}×ATR14({atr14})",
        },
    }

    cat_active = False
    pre_reduce_pct = ev["Z_pre_reduce_pct"]
    post_add = post_exit = None

    if catalyst and today:
        try:
            cat_date  = _date.fromisoformat(catalyst["date"])
            days_away = (cat_date - today).days
            cat_active = (0 <= days_away <= 3 and catalyst.get("importance") == "high")
            if entry_base and mkt.get("atr14"):
                post_add  = round(entry_base + ev["c1"] * atr14, 2)
                post_exit = round(entry_base - ev["c2"] * atr14, 2)
        except Exception:
            pass

    catalyst_framework = {
        "pre_reduce_active": cat_active,
        "pre_reduce_days":   3,
        "pre_reduce_pct":    pre_reduce_pct,
        "post_add_trigger":  post_add,
        "post_force_exit":   post_exit,
        "next_catalyst":     catalyst,
    }

    return {
        "scenario_downgrade":  scenario_downgrade,
        "catalyst_framework":  catalyst_framework,
    }


def calc_time_stop(ev: dict, today: _date, catalyst_date: str,
                   position_type: str) -> dict:
    use_decay = (position_type == "trend")

    if use_decay:
        return {
            "type":        "decay",
            "decay_days":  ev["D_decay_stop"],
            "min_progress": ev["M_decay_min_pct"],
            "condition":   f"持有>{ev['D_decay_stop']}天且底层标的涨幅<{ev['M_decay_min_pct']}%",
            "review_date": str(today + timedelta(days=ev["D_decay_stop"])),
        }

    if catalyst_date:
        try:
            cat_d  = _date.fromisoformat(catalyst_date)
            review = cat_d + timedelta(days=7)
        except Exception:
            review = today + timedelta(days=ev["N_time_stop"])
    else:
        review = today + timedelta(days=ev["N_time_stop"])

    return {
        "type":        "standard",
        "review_date": str(review),
        "condition":   f"持仓超{ev['N_time_stop']}天且未向TP1移动5%",
        "decay_stop":  None,
    }


def build_nodes(sym: str, mkt: dict, memo: dict, pos: dict,
                entry_base: float = None) -> dict:
    """整合所有节点计算器，返回完整节点字典。"""
    today = _date.today()
    existing = _load(os.path.join(BASE, f"macro_strategy_{sym.upper()}.json"))
    ev = {**DEFAULT_EVOLUTION, **existing.get("evolution", {})}

    entry_base   = entry_base or pos.get("cost", mkt["price"])
    unified_conf = memo.get("judgment", {}).get("unified_confidence", 3)
    thesis_status = pos.get("thesis_status", "intact")
    position_type = pos.get("position_type", "thesis")
    bear_price   = memo.get("scenarios", {}).get("bear", {}).get("price_target", 0)
    catalyst     = memo.get("support_and_risk", {}).get("next_catalyst", {})
    cat_date_str = catalyst.get("date") if catalyst else None

    sent_conf = memo.get("agent_analysis", {}).get("sentiment", {}).get("confidence", 50)
    mkt["sentiment_score"] = round(sent_conf / 100, 2)

    entry_nodes  = calc_entry_nodes(mkt, ev, entry_base, unified_conf, thesis_status)
    stop_nodes   = calc_stop_nodes(mkt, ev, entry_base, bear_price)
    target_nodes = calc_target_nodes(mkt, ev)
    scene_nodes  = calc_scenario_nodes(mkt, ev, catalyst, today, entry_base)
    time_node    = calc_time_stop(ev, today, cat_date_str, position_type)

    return {
        **entry_nodes,
        **stop_nodes,
        **target_nodes,
        **scene_nodes,
        "time_stop": time_node,
    }


def write_macro_strategy(sym: str, mkt: dict, memo: dict, nodes: dict,
                         base_dir: str = BASE) -> str:
    existing = _load(os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json"))
    ev = {**DEFAULT_EVOLUTION, **existing.get("evolution", {})}

    out = {
        "sym":              sym.upper(),
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "market_data_date": str(_date.today()),
        "nodes":            nodes,
        "market_inputs":    mkt,
        "memo_inputs": {
            "strategic_stance":    memo.get("synthesis", {}).get("strategic_stance"),
            "unified_confidence":  memo.get("judgment", {}).get("unified_confidence"),
            "next_catalyst":       memo.get("support_and_risk", {}).get("next_catalyst"),
            "scenario_bear_price": memo.get("scenarios", {}).get("bear", {}).get("price_target"),
            "scenario_base_price": memo.get("scenarios", {}).get("base", {}).get("price_target"),
            "scenario_bull_price": memo.get("scenarios", {}).get("bull", {}).get("price_target"),
        },
        "evolution": ev,
    }

    path     = os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json")
    prev_path = os.path.join(base_dir, f"macro_strategy_{sym.upper()}_prev.json")
    # 覆盖前保存前一版本，供 report_viewer 渲染 delta 列
    if os.path.exists(path):
        import shutil
        shutil.copy2(path, prev_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return path


def backtest_node(node_type: str, node_price: float, entry_price: float,
                  price_history: list) -> dict:
    """
    简单单节点回测：给定历史价格序列，判断节点是否被击中。
    node_type: 'dynamic_stop' | 'tp1' | 'tp2'
    """
    if not price_history or node_price is None:
        return {"hit": False, "hit_rate": 0.0, "days_to_hit": None}

    hit_days = []
    for i, price in enumerate(price_history):
        if node_type == "dynamic_stop" and price <= node_price:
            hit_days.append(i)
        elif node_type in ("tp1", "tp2") and price >= node_price:
            hit_days.append(i)

    hit = len(hit_days) > 0
    hit_rate = round(len(hit_days) / len(price_history), 3)
    days_to_hit = hit_days[0] if hit_days else None

    return {"hit": hit, "hit_rate": hit_rate, "days_to_hit": days_to_hit}


def scan_parameters(outcomes: list, param_name: str,
                    param_range: list) -> dict:
    """
    扫描单个参数的最优值。
    使用启发式权重：止损类参数（k1）越大止损越保守，tp类（k4）越小目标越保守。
    注：精确优化需要历史 OHLCV 重新回测，当前版本为 v1 启发式实现。
    """
    if not outcomes:
        return {"best_value": param_range[len(param_range)//2],
                "metric": 0.0, "note": "无数据，返回中间值"}

    stop_outcomes = [o for o in outcomes if o["node_type"] == "dynamic_stop"]
    tp_outcomes   = [o for o in outcomes if o["node_type"] in ("tp1", "tp2")]

    base_stop_hit = (sum(1 for o in stop_outcomes if o["outcome"] == "hit")
                     / len(stop_outcomes)) if stop_outcomes else 0.5
    base_tp_hit   = (sum(1 for o in tp_outcomes   if o["outcome"] == "hit")
                     / len(tp_outcomes))   if tp_outcomes   else 0.5

    best_value, best_score = param_range[0], -999.0
    for val in param_range:
        # 启发式：k1 越大 → 止损设置越低 → 被扫概率理论上越低
        if param_name in ("k1", "k2", "k3", "k5", "k6"):
            adjusted_stop = min(base_stop_hit / max(val, 0.1), 1.0)
            adjusted_tp   = base_tp_hit
        # 启发式：k4 越小 → 目标价越保守 → 命中率理论上越高
        elif param_name in ("k4",):
            adjusted_stop = base_stop_hit
            adjusted_tp   = min(base_tp_hit / max(val, 0.1), 1.0)
        else:
            adjusted_stop = base_stop_hit
            adjusted_tp   = base_tp_hit

        score = adjusted_tp - adjusted_stop
        if score > best_score:
            best_score, best_value = score, val

    return {"param_name": param_name, "best_value": best_value,
            "metric": round(best_score, 3), "n_outcomes": len(outcomes)}


def record_outcome(sym: str, node_type: str, planned_price: float,
                   actual_trigger_price: float, outcome: str,
                   pnl_impact: float, base_dir: str = BASE) -> None:
    """记录节点实际结果到 learning/macro_strategy_outcomes.jsonl"""
    import time
    record = {
        "sym":                  sym,
        "date":                 str(_date.today()),
        "node_type":            node_type,
        "planned_price":        planned_price,
        "actual_trigger_price": actual_trigger_price,
        "outcome":              outcome,
        "pnl_impact":           pnl_impact,
        "ts":                   time.time(),
    }
    path = os.path.join(base_dir, "learning", "macro_strategy_outcomes.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def update_evolution(sym: str, base_dir: str = BASE) -> dict:
    """
    读取历史记录，扫描关键系数，更新 macro_strategy_{sym}.json 的 evolution 字段。
    需要 ≥ 10 条记录才运行。
    """
    outcomes_path = os.path.join(base_dir, "learning", "macro_strategy_outcomes.jsonl")
    outcomes = []
    try:
        with open(outcomes_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    if r.get("sym") == sym.upper():
                        outcomes.append(r)
    except Exception:
        pass

    if len(outcomes) < 10:
        print(f"[evolution] {sym}: 记录数 {len(outcomes)} < 10，跳过参数扫描")
        return {}

    updates = {}
    for param, rng in [("k1", [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]),
                       ("k4", [0.80, 0.85, 0.90, 0.95, 1.0])]:
        result = scan_parameters(outcomes, param, rng)
        updates[param] = result["best_value"]
        print(f"[evolution] {sym} {param}: {result['best_value']} (score={result['metric']})")

    macro_path = os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json")
    macro = _load(macro_path)
    if macro:
        macro["evolution"].update(updates)
        macro["evolution"]["last_backtest_date"] = str(_date.today())
        macro["evolution"]["outcomes_count"] = len(outcomes)
        with open(macro_path, "w", encoding="utf-8") as f:
            json.dump(macro, f, ensure_ascii=False, indent=2)
    return updates


def main():
    parser = argparse.ArgumentParser(description="宏观策略节点生成")
    parser.add_argument("symbol")
    parser.add_argument("--refresh", action="store_true",
                        help="只更新动态节点（Flex/Time/Catalyst），不重抓全量数据")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD（供测试用）")
    args = parser.parse_args()

    sym = args.symbol.upper()
    date_str = args.date or str(_date.today())

    memo = _load(os.path.join(BASE, f"strategic_memo_{sym}.json"))
    if not memo:
        print(f"[macro_strategy] ⚠️ strategic_memo_{sym}.json 不存在，跳过")
        return

    positions = _load(os.path.join(CFG_DIR, "positions.json"))
    pos = (positions.get("positions") or {}).get(sym, {})

    order_sheet = _load(os.path.join(FIND_DIR, f"order_sheet_{date_str}.json"))
    entry_base = (order_sheet.get(sym) or {}).get("entry_base") or pos.get("cost")

    print(f"[macro_strategy] 抓取 {sym} 市场数据...")
    mkt = fetch_market_data(sym)
    if not mkt:
        print(f"[macro_strategy] ❌ 无法获取市场数据")
        return

    nodes = build_nodes(sym, mkt, memo, pos, entry_base)
    path  = write_macro_strategy(sym, mkt, memo, nodes)
    print(f"[macro_strategy] ✅ 已保存: {path}")

    n = nodes
    ds = n.get("dynamic_stop", {})
    print(f"  止损: ${ds.get('price','?')}  TP1: ${n.get('tp1',{}).get('price','?')}  "
          f"TP2: ${n.get('tp2',{}).get('price','?')}  Add1: ${n.get('add1',{}).get('price','?')}")


if __name__ == "__main__":
    main()
