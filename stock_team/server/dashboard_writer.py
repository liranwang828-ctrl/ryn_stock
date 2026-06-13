"""
Dashboard 鍐欏叆妯″潡 鈥?dashboard_writer.py
璇诲彇鎵€鏈?B 绾?JSON锛岀敓鎴?reports/dashboard.html銆?

鐢ㄦ硶: python3.12 agents/dashboard_writer.py
     鎴栫敱 poll.py 姣忚疆鏈熬璋冪敤 write_dashboard()
"""
import json, os, sys
from collections import deque
from datetime import datetime, timezone, date as _date
from stock_team.utils.workspace_paths import investing_os_home

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")
TPL_DIR  = os.path.join(BASE, "templates")
RPT_DIR  = os.path.join(BASE, "reports")


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _latest_dated_file(directory: str, pattern: str) -> tuple[str | None, str | None]:
    """Return latest YYYY-MM-DD file matching a glob pattern with one date group."""
    import glob
    import re
    latest: tuple[str, str] | None = None
    for path in glob.glob(os.path.join(directory, pattern)):
        name = os.path.basename(path)
        match = re.search(r"(20\d{2}-\d{2}-\d{2})", name)
        if not match:
            continue
        file_date = match.group(1)
        if latest is None or file_date > latest[0]:
            latest = (file_date, path)
    if not latest:
        return None, None
    return latest[0], latest[1]


def _nodes_from_premarket_summary(summary: dict | None) -> dict:
    if not isinstance(summary, dict):
        return {}
    entry = summary.get("entry") or {}
    exit_data = summary.get("exit") or {}
    nodes: dict[str, dict] = {}

    entry_base = entry.get("entry_base") or entry.get("entry_base_adj")
    hard_stop = exit_data.get("hard_stop") or entry.get("stop_loss")
    target = exit_data.get("target_price") or entry.get("target_price")
    flex_add = exit_data.get("flex_add_level") or entry_base
    flex_reduce = exit_data.get("flex_reduce_level") or target

    if entry_base is not None:
        nodes["entry_base"] = {"price": entry_base, "source": "premarket_summary"}
    if hard_stop is not None:
        nodes["dynamic_stop"] = {"price": hard_stop, "source": "premarket_summary"}
    if flex_add is not None:
        nodes["add1"] = {"price": flex_add, "source": "premarket_summary"}
    if flex_reduce is not None:
        nodes["flex_reduce"] = {"price": flex_reduce, "source": "premarket_summary"}
    if target is not None:
        nodes["tp1"] = {"price": target, "source": "premarket_summary"}
    return nodes


def _read_last_jsonl(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)
                except Exception:
                    pass
    return last


def _read_all_jsonl(path: str) -> list[dict]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def _read_tail_jsonl(path: str, limit: int = 11) -> list[dict]:
    tail = deque(maxlen=max(int(limit), 1))
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except Exception:
                continue
            if isinstance(value, dict):
                tail.append(value)
    return list(tail)


def _clean_gate_status_text(text: str | None) -> str | None:
    """Normalize gate_status for display."""
    if not text:
        return text
    s = str(text).strip()
    while s and s[0] in "│┃|-— ":
        s = s[1:].lstrip()
    if "  ❌" in s:
        s = s.split("  ❌", 1)[0].strip()
    if "  ✅" in s:
        s = s.split("  ✅", 1)[0].strip()
    return s


def _normalize_intraday_record(rec: dict) -> dict:
    if not isinstance(rec, dict):
        return rec
    price_now = rec.get("price_now")
    if isinstance(price_now, dict):
        rec = dict(rec)
        price_now = dict(price_now)
        price_now["gate_status"] = _clean_gate_status_text(price_now.get("gate_status"))
        if price_now.get("master_consensus") is None:
            price_now["master_consensus"] = "neutral"
        if price_now.get("master_avg") is None:
            price_now["master_avg"] = 5.0
"""
Dashboard 鍐欏叆妯″潡 鈥?dashboard_writer.py
璇诲彇鎵€鏈?B 绾?JSON锛岀敓鎴?reports/dashboard.html銆?

鐢ㄦ硶: python3.12 agents/dashboard_writer.py
     鎴栫敱 poll.py 姣忚疆鏈殑末璋冪敤 write_dashboard()
"""
import json, os, sys
from collections import deque
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")
TPL_DIR  = os.path.join(BASE, "templates")
RPT_DIR  = os.path.join(BASE, "reports")


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _latest_dated_file(directory: str, pattern: str) -> tuple[str | None, str | None]:
    """Return latest YYYY-MM-DD file matching a glob pattern with one date group."""
    import glob
    import re
    latest: tuple[str, str] | None = None
    for path in glob.glob(os.path.join(directory, pattern)):
        name = os.path.basename(path)
        match = re.search(r"(20\d{2}-\d{2}-\d{2})", name)
        if not match:
            continue
        file_date = match.group(1)
        if latest is None or file_date > latest[0]:
            latest = (file_date, path)
    if not latest:
        return None, None
    return latest[0], latest[1]


def _nodes_from_premarket_summary(summary: dict | None) -> dict:
    if not isinstance(summary, dict):
        return {}
    entry = summary.get("entry") or {}
    exit_data = summary.get("exit") or {}
    nodes: dict[str, dict] = {}

    entry_base = entry.get("entry_base") or entry.get("entry_base_adj")
    hard_stop = exit_data.get("hard_stop") or entry.get("stop_loss")
    target = exit_data.get("target_price") or entry.get("target_price")
    flex_add = exit_data.get("flex_add_level") or entry_base
    flex_reduce = exit_data.get("flex_reduce_level") or target

    if entry_base is not None:
        nodes["entry_base"] = {"price": entry_base, "source": "premarket_summary"}
    if hard_stop is not None:
        nodes["dynamic_stop"] = {"price": hard_stop, "source": "premarket_summary"}
    if flex_add is not None:
        nodes["add1"] = {"price": flex_add, "source": "premarket_summary"}
    if flex_reduce is not None:
        nodes["flex_reduce"] = {"price": flex_reduce, "source": "premarket_summary"}
    if target is not None:
        nodes["tp1"] = {"price": target, "source": "premarket_summary"}
    return nodes


def _read_last_jsonl(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)
                except Exception:
                    pass
    return last


def _read_all_jsonl(path: str) -> list[dict]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def _read_tail_jsonl(path: str, limit: int = 11) -> list[dict]:
    tail = deque(maxlen=max(int(limit), 1))
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except Exception:
                continue
            if isinstance(value, dict):
                tail.append(value)
    return list(tail)


def _clean_gate_status_text(text: str | None) -> str | None:
    """Normalize gate_status for display."""
    if not text:
        return text
    s = str(text).strip()
    while s and s[0] in "│┃|-— ":
        s = s[1:].lstrip()
    if "  ❌" in s:
        s = s.split("  ❌", 1)[0].strip()
    if "  ✅" in s:
        s = s.split("  ✅", 1)[0].strip()
    return s


def _normalize_intraday_record(rec: dict) -> dict:
    if not isinstance(rec, dict):
        return rec
    price_now = rec.get("price_now")
    if isinstance(price_now, dict):
        rec = dict(rec)
        price_now = dict(price_now)
        price_now["gate_status"] = _clean_gate_status_text(price_now.get("gate_status"))
        if price_now.get("master_consensus") is None:
            price_now["master_consensus"] = "neutral"
        if price_now.get("master_avg") is None:
            price_now["master_avg"] = 5.0
        rec["price_now"] = price_now
    plan_vs_now = rec.get("plan_vs_now")
    if isinstance(plan_vs_now, dict):
        rec = dict(rec)
        plan_vs_now = dict(plan_vs_now)
        if plan_vs_now.get("entry_go_status") is None:
            plan_vs_now["entry_go_status"] = "pending"
        rec["plan_vs_now"] = plan_vs_now
    return rec


def _normalize_macro_nodes(sym: str, nodes: dict, daily_plan: dict | None = None, premarket: dict | None = None) -> dict:
    if not isinstance(nodes, dict):
        nodes = {}
    
    # 1. 强制将所有节点值统一转换为 {"price": ...} 字典形式，支持直接为数字的旧版/简版格式
    normalized = {}
    for k, v in nodes.items():
        if isinstance(v, dict):
            normalized[k] = dict(v)
        elif v is not None:
            normalized[k] = {"price": _coerce_price(v), "source": "macro_strategy"}
        else:
            normalized[k] = {}

    # 2. 键名对齐与映射 (支持多种不同格式下的策略节点互通)
    # hard_stop / stop_loss -> dynamic_stop
    if "dynamic_stop" not in normalized or normalized["dynamic_stop"].get("price") is None:
        stop_val = normalized.get("hard_stop") or normalized.get("stop_loss")
        if stop_val and stop_val.get("price") is not None:
            normalized["dynamic_stop"] = stop_val

    # target / target_price / tp1 -> tp1
    if "tp1" not in normalized or normalized["tp1"].get("price") is None:
        target_val = normalized.get("target") or normalized.get("target_price") or normalized.get("tp1")
        if target_val and target_val.get("price") is not None:
            normalized["tp1"] = target_val

    # flex_add / add1 -> add1
    if "add1" not in normalized or normalized["add1"].get("price") is None:
        add_val = normalized.get("flex_add") or normalized.get("add1")
        if add_val and add_val.get("price") is not None:
            normalized["add1"] = add_val

    key_levels = (((daily_plan or {}).get("per_symbol") or {}).get(sym.upper()) or {}).get("key_levels", {}) or {}
    pm = (premarket or {}).get(sym.upper()) or {}
    pm_exit = pm.get("exit") or {}

    # flex_reduce 对齐
    flex_reduce = normalized.get("flex_reduce")
    if not isinstance(flex_reduce, dict):
        flex_reduce = {}
    if flex_reduce.get("price") is None:
        flex_reduce_price = key_levels.get("flex_reduce") or pm_exit.get("flex_reduce_level")
        if flex_reduce_price is not None:
            flex_reduce["price"] = flex_reduce_price
    normalized["flex_reduce"] = flex_reduce

    # soft_stop -> scenario_downgrade 对齐
    scene = normalized.get("scenario_downgrade")
    if not isinstance(scene, dict):
        scene = {}
    if scene.get("price") is None:
        soft_stop_val = normalized.get("soft_stop")
        if soft_stop_val and soft_stop_val.get("price") is not None:
            scene["price"] = soft_stop_val.get("price")
            scene["label"] = soft_stop_val.get("label", "Soft warning")
        else:
            bull_to_base = scene.get("bull_to_base") or {}
            base_to_bear = scene.get("base_to_bear") or {}
            scene["price"] = bull_to_base.get("price") or base_to_bear.get("price")
            if scene.get("basis") is None:
                scene["basis"] = bull_to_base.get("basis") or base_to_bear.get("basis")
    normalized["scenario_downgrade"] = scene

    return normalized


def _coerce_price(value: object) -> float | None:
    try:
        if value is None:
            return None
        price = float(value)
    except Exception:
        return None
    if price != price:
        return None
    return round(price, 2)


def _apply_portfolio_price_overrides(portfolio: dict | None, pos_data: dict | None) -> None:
    """Overlay local broker price snapshots onto portfolio rows without fetching market data."""
    if not isinstance(portfolio, dict) or not isinstance(pos_data, dict):
        return
    positions_cfg = pos_data.get("positions") or {}
    details = portfolio.get("positions_detail")
    if not isinstance(details, list):
        return

    total_exposure = 0.0
    var_loss = 0.0
    pnl_weighted = 0.0
    holdings_value = 0.0

    for row in details:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("sym") or "").upper()
        cfg = positions_cfg.get(sym) or {}
        broker_price = _coerce_price(cfg.get("broker_last_price"))
        if broker_price is not None:
            row["cur_price"] = broker_price
            row["price"] = broker_price
            row["price_source"] = "broker_last_price"
        else:
            row.setdefault("price_source", row.get("source") or "portfolio_snapshot")

        shares = float(row.get("shares") or cfg.get("shares") or 0.0)
        leverage = float(row.get("leverage") or 1.0)
        cost = float(row.get("cost") or cfg.get("cost") or 0.0)
        cur_price = float(row.get("cur_price") or 0.0)
        market_value = cur_price * shares
        net_exposure = market_value * leverage
        row["shares"] = shares
        row["market_value"] = round(market_value, 4)
        row["net_exposure"] = round(net_exposure, 4)
        if cost > 0:
            row["unrealized_pnl_pct"] = round((cur_price - cost) / cost * 100, 2)
        beta = float(row.get("beta") or 1.0)
        row["var_5pct_loss"] = round(net_exposure * beta * 0.05, 4)

        holdings_value += market_value
        total_exposure += net_exposure
        var_loss += float(row.get("var_5pct_loss") or 0.0)
        pnl_weighted += float(row.get("unrealized_pnl_pct") or 0.0) * market_value

    totals = portfolio.setdefault("totals", {})
    if holdings_value > 0:
        totals["holdings_value"] = round(holdings_value, 2)
        totals["total_exposure"] = round(total_exposure, 2)
        totals["var_5pct_loss"] = round(var_loss, 2)
        totals["total_unrealized_pnl_pct"] = round(pnl_weighted / holdings_value, 2)


def _candle_padding(row: dict) -> float:
    chg_pct = _coerce_price(((row.get("price_now") or {}).get("chg_pct")))
    if chg_pct is None:
        return 0.05
    return round(max(abs(chg_pct) * 0.05, 0.05), 2)


def _build_mini_chart(rows: list[dict] | None, fallback_rec: dict | None = None) -> dict | None:
    valid_rows: list[dict] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        price = _coerce_price(((row.get("price_now") or {}).get("price")))
        if price is None:
            continue
        valid_rows.append(row)

    if not valid_rows and isinstance(fallback_rec, dict):
        fallback_price = _coerce_price(((fallback_rec.get("price_now") or {}).get("price")))
        if fallback_price is not None:
            valid_rows = [fallback_rec]

    if not valid_rows:
        return None

    if len(valid_rows) > 10:
        valid_rows = valid_rows[-10:]

    candles: list[dict] = []
    prev_price = None
    slot_offset = max(0, 10 - len(valid_rows))
    for idx, row in enumerate(valid_rows):
        price = _coerce_price(((row.get("price_now") or {}).get("price")))
        if price is None:
            continue
        open_price = prev_price if prev_price is not None else price
        pad = _candle_padding(row)
        candles.append({
            "ts": str(row.get("ts") or ""),
            "open": open_price,
            "high": round(max(open_price, price) + pad, 2),
            "low": round(min(open_price, price) - pad, 2),
            "close": price,
            "slot": slot_offset + idx,
        })
        prev_price = price

    if not candles:
        return None

    node_source = {}
    for row in reversed(valid_rows):
        candidate = row.get("node_snapshot")
        if isinstance(candidate, dict) and candidate:
            node_source = candidate
            break
    if not node_source and isinstance(fallback_rec, dict):
        candidate = fallback_rec.get("node_snapshot")
        if isinstance(candidate, dict):
            node_source = candidate

    nodes = []
    node_prices = []
    for name, value in node_source.items():
        if isinstance(value, dict):
            node_price = _coerce_price(value.get("price"))
        else:
            node_price = _coerce_price(value)
        if node_price is None:
            continue
        nodes.append({"name": name, "price": node_price})
        node_prices.append(node_price)

    all_prices = [p for candle in candles for p in (candle["low"], candle["high"])] + node_prices
    price_low = round(min(all_prices), 2) if all_prices else None
    price_high = round(max(all_prices), 2) if all_prices else None

    return {
        "kind": "candles",
        "count": len(candles),
        "candles": candles,
        "nodes": nodes,
        "range": {"low": price_low, "high": price_high},
    }


def _find_previous_intraday_tail(date: str, sym: str, find_dir: str, limit: int = 10) -> tuple[str | None, list[dict]]:
    if not os.path.isdir(find_dir):
        return None, []
    prefix = "intraday_snapshot_"
    suffix = f"_{sym.upper()}.jsonl"
    candidates: list[str] = []
    try:
        for name in os.listdir(find_dir):
            if not (name.startswith(prefix) and name.endswith(suffix)):
                continue
            prev_date = name[len(prefix):-len(suffix)]
            if prev_date < date:
                candidates.append(prev_date)
    except Exception:
        return None, []
    if not candidates:
        return None, []

    prev_date = sorted(candidates)[-1]
    path = os.path.join(find_dir, f"intraday_snapshot_{prev_date}_{sym.upper()}.jsonl")
    return prev_date, _read_tail_jsonl(path, limit=limit)


def _chart_nodes_from_macro_nodes(nodes: dict | None) -> list[dict]:
    if not isinstance(nodes, dict):
        return []
    candidates = [
        ("hard_stop", (nodes.get("dynamic_stop") or {}).get("price")),
        ("target", (nodes.get("tp1") or {}).get("price")),
        ("flex_add", (nodes.get("add1") or {}).get("price")),
        ("scenario_downgrade", (nodes.get("scenario_downgrade") or {}).get("price")),
    ]
    result = []
    seen = set()
    for name, value in candidates:
        price = _coerce_price(value)
        if price is None or (name, price) in seen:
            continue
        result.append({"name": name, "price": price})
        seen.add((name, price))
    return result


def _merge_symbol_cache(dst: dict | None, src: dict | None, symbols: list[str]) -> bool:
    if not isinstance(dst, dict) or not isinstance(src, dict):
        return False

    changed = False
    symbol_set = {s.upper() for s in symbols or []}

    def _merge_missing(dst_node, src_node):
        nonlocal changed
        if not isinstance(dst_node, dict) or not isinstance(src_node, dict):
            return
        for key, src_value in src_node.items():
            if key not in dst_node or dst_node.get(key) is None:
                if isinstance(src_value, dict):
                    dst_node[key] = json.loads(json.dumps(src_value))
                else:
                    dst_node[key] = src_value
                changed = True
            elif isinstance(dst_node.get(key), dict) and isinstance(src_value, dict):
                _merge_missing(dst_node[key], src_value)

    for sym in symbol_set:
        if sym in src:
            if sym not in dst or dst.get(sym) is None:
                dst[sym] = json.loads(json.dumps(src.get(sym)))
                changed = True
            else:
                _merge_missing(dst.get(sym), src.get(sym))

    dst_ps = dst.get("per_symbol") if isinstance(dst.get("per_symbol"), dict) else None
    src_ps = src.get("per_symbol") if isinstance(src.get("per_symbol"), dict) else None
    if isinstance(src_ps, dict):
        if not isinstance(dst_ps, dict):
            dst_ps = {}
            dst["per_symbol"] = dst_ps
        for sym in symbol_set:
            if sym in src_ps:
                if sym not in dst_ps or dst_ps.get(sym) is None:
                    dst_ps[sym] = json.loads(json.dumps(src_ps.get(sym)))
                    changed = True
                else:
                    _merge_missing(dst_ps.get(sym), src_ps.get(sym))

    return changed


# 鈹€鈹€ 鏁版嵁鍔犺浇鍑芥暟 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def load_premarket_summaries(date: str, symbols: list[str],
                              find_dir: str = FIND_DIR) -> dict:
    """返回 {sym: premarket_summary_dict}"""
    from stock_team.utils.capsule_utils import get_premarket_summary_path, get_strategy_path
    base_dir = os.path.dirname(find_dir)
    result = {}
    for sym in symbols:
        sym_upper = sym.upper()
        # 优先加载今日太空舱盘前计划（含回退兼容）
        path = get_premarket_summary_path(sym_upper, date, base_dir)
        d = _load(path)
        
        # 弹性降级自愈加载专属 strategy.json
        if not d:
            strat_path = get_strategy_path(sym_upper, base_dir)
            if os.path.exists(strat_path):
                strat = _load(strat_path)
                if strat:
                    d = {
                        "_fallback_mode": True,
                        "entry": {
                            "entry_base": strat.get("key_levels", {}).get("entry_low") or strat.get("key_levels", {}).get("entry_base"),
                            "stop_loss": strat.get("key_levels", {}).get("stop_loss"),
                            "target_price": strat.get("key_levels", {}).get("target_price"),
                            "decision": "watch (fallback)"
                        },
                        "exit": {
                            "flex_add_level": strat.get("exit_plan", {}).get("flex_add_level"),
                            "flex_reduce_level": strat.get("exit_plan", {}).get("flex_reduce_level"),
                            "hard_stop": strat.get("key_levels", {}).get("stop_loss")
                        },
                        "thesis": {
                            "status": strat.get("thesis", {}).get("status", "intact"),
                            "today_falsification": strat.get("thesis", {}).get("today_falsification") or []
                        }
                    }
        if d:
            result[sym_upper] = d
    return result

def load_intraday_latest(date: str, symbols: list[str],
                          find_dir: str = FIND_DIR) -> dict:
    """娴兼ê鍘涙禒?SQLite WAL 閺佺増宓佹惔鎾诡嚢閸欐牗娓堕弬鏉挎彥閻撗嶇礉閼汇儱銇戠拹銉﹀灗閺冪姵鏆熼幑顔煎灟閸ョ偤鈧偓閼?JSONL 绾板孩鏋冩禒?"""
    base_dir = os.path.dirname(find_dir)
    dashboard_cache = load_dashboard_cache(base_dir)
    cached_intraday = dashboard_cache.get("intraday") if isinstance(dashboard_cache, dict) else {}
    result = {}
    from stock_team.utils.capsule_utils import get_intraday_snapshot_path
    for sym in symbols:
        path = get_intraday_snapshot_path(sym, date, base_dir)
        rows = _read_tail_jsonl(path, limit=10)

        latest = None
        last = _read_last_jsonl(path)
        if last:
            latest = _normalize_intraday_record(last)
        if latest is None and isinstance(cached_intraday, dict) and isinstance(cached_intraday.get(sym), dict):
            latest = _normalize_intraday_record(cached_intraday.get(sym))
        if latest is None and rows:
            latest = _normalize_intraday_record(rows[-1])

        if latest:
            # 允许从最新价格缓存中覆盖现价，以支持手动刷新并解决现价获取/更新延迟问题
            if isinstance(cached_intraday, dict) and isinstance(cached_intraday.get(sym), dict):
                cached_rec = cached_intraday.get(sym)
                if cached_rec.get("price_now"):
                    latest = dict(latest)
                    price_now = dict(latest.get("price_now") or {})
                    cached_price_now = cached_rec.get("price_now")
                    c_asof = cached_price_now.get("price_asof", "")
                    l_asof = price_now.get("price_asof", "")
                    if not l_asof or c_asof >= l_asof:
                        if cached_price_now.get("price") is not None:
                            price_now["price"] = cached_price_now.get("price")
                        if cached_price_now.get("chg_pct") is not None:
                            price_now["chg_pct"] = cached_price_now.get("chg_pct")
                        price_now["price_source"] = cached_price_now.get("price_source") or "cache_refresh"
                        price_now["price_asof"] = c_asof
                        latest["price_now"] = price_now
                        
            chart_rows = rows
            chart_source = None
            chart_source_date = None
            if len(rows) < 8:
                prev_date, prev_rows = _find_previous_intraday_tail(date, sym, find_dir, limit=10)
                if prev_rows and len(prev_rows) >= len(rows):
                    chart_rows = prev_rows
                    chart_source = "previous_close"
                    chart_source_date = prev_date

            mini_chart = _build_mini_chart(chart_rows, latest)
            if mini_chart:
                latest = dict(latest)
                if chart_source:
                    meta = dict(latest.get("meta") or {})
                    meta["chart_source"] = chart_source
                    meta["chart_source_date"] = chart_source_date
                    latest["meta"] = meta
                    mini_chart["source"] = chart_source
                    mini_chart["source_date"] = chart_source_date
                latest["mini_chart"] = mini_chart
            result[sym] = latest
            continue

        prev_date, prev_rows = _find_previous_intraday_tail(date, sym, find_dir, limit=10)
        mini_chart = _build_mini_chart(prev_rows, prev_rows[-1] if prev_rows else None)
        if mini_chart and prev_rows:
            latest = {
                "ts": "",
                "meta": {
                    "sym": sym.upper(),
                    "date": date,
                    "chart_source": "previous_close",
                    "chart_source_date": prev_date,
                },
                "price_now": {},
                "plan_vs_now": {"entry_go_status": "pending"},
                "node_snapshot": prev_rows[-1].get("node_snapshot") or {},
                "action_now": None,
            }
            mini_chart["source"] = "previous_close"
            mini_chart["source_date"] = prev_date
            latest["mini_chart"] = mini_chart
            result[sym] = latest
    return result

def load_intraday_events(date: str, symbols: list[str],
                          find_dir: str = FIND_DIR) -> list[dict]:
    """浼樺厛浠?SQLite WAL 鏁版嵁搴撹鍙栦粖鏃ュ喅绛栦簨浠舵祦锛岃嫢澶辫触鎴栨棤鏁版嵁鍒欏洖閫€鑷?JSONL 纰庢枃浠?"""
    base_dir = os.path.dirname(find_dir)
    dashboard_cache = load_dashboard_cache(base_dir)
    events = []
    from stock_team.utils.capsule_utils import get_intraday_snapshot_path
    for sym in symbols:
        path = get_intraday_snapshot_path(sym, date, base_dir)
        for rec in _read_all_jsonl(path):
            if rec.get("meta", {}).get("llm_triggered"):
                events.append(rec)
    if isinstance(dashboard_cache, dict):
        cache_events = dashboard_cache.get("events")
        if isinstance(cache_events, list):
            wanted = {s.upper() for s in symbols}
            for rec in cache_events:
                if not isinstance(rec, dict):
                    continue
                meta = rec.get("meta") if isinstance(rec.get("meta"), dict) else {}
                rec_sym = str(meta.get("sym") or rec.get("sym") or "").upper()
                rec_date = str(meta.get("date") or rec.get("date") or "")
                if rec_sym in wanted and (not rec_date or rec_date == date) and meta.get("llm_triggered"):
                    events.append(rec)
    events.sort(key=lambda r: r.get("ts", ""))
    deduped = []
    seen = set()
    for rec in events:
        meta = rec.get("meta") if isinstance(rec.get("meta"), dict) else {}
        key = (
            str(meta.get("sym") or rec.get("sym") or "").upper(),
            str(rec.get("ts") or ""),
            str(meta.get("llm_trigger") or ""),
            str(rec.get("id") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rec)
    return deduped


def load_portfolio_snapshot(date: str, find_dir: str = FIND_DIR, prefer_current: bool = True) -> dict:
    if prefer_current:
        current_path = os.path.join(find_dir, "portfolio_snapshot_current.json")
        current = _load(current_path)
        if current:
            return current
    path = os.path.join(find_dir, f"portfolio_snapshot_{date}.json")
    return _load(path)


def load_postmarket_day(date: str, find_dir: str = FIND_DIR) -> dict:
    path = os.path.join(find_dir, f"postmarket_summary_{date}.json")
    return _load(path)


def load_session_state(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, "learning", f"session_state_{date}.json")
    return _load(path)


def load_session_lock(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, "findings", "session_lock.json")
    data = _load(path)
    if not isinstance(data, dict) or data.get("date") != date:
        return {}
    return data


def load_daily_plan(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, f"daily_plan_{date}.json")
    return _load(path)


def load_decision_state(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, "findings", f"decision_state_{date}.json")
    data = _load(path)
    if not isinstance(data, dict) or not isinstance(data.get("symbols"), dict):
        return {"date": date, "symbols": {}}
    return data


def load_dashboard_cache(base_dir: str = BASE) -> dict:
    try:
        from stock_team.server.dashboard_cache import load_dashboard_cache as _load_dashboard_cache
        return _load_dashboard_cache(base_dir)
    except Exception:
        return {}


def _compact_learning_text(value: object, limit: int = 160) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _load_learning_state(base_dir: str, dashboard_cache: dict | None = None) -> dict:
    cached_learning = {}
    if isinstance(dashboard_cache, dict) and isinstance(dashboard_cache.get("learning"), dict):
        cached_learning = dashboard_cache.get("learning") or {}

    index = {}
    index_path = os.path.join(base_dir, "learning", "knowledge_index.json")
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding="utf-8") as f:
                raw_index = json.load(f)
            if isinstance(raw_index, dict):
                index = raw_index
        except Exception:
            index = {}

    if not index and cached_learning:
        index = cached_learning

    source_coverage = {
        "observation": 0,
        "lesson": 0,
        "decision": 0,
        "outcome": 0,
        "knowledge_node": 0,
    }
    if isinstance(index, dict):
        coverage = index.get("source_coverage")
        if isinstance(coverage, dict):
            for kind in source_coverage:
                try:
                    source_coverage[kind] = int(coverage.get(kind, 0) or 0)
                except Exception:
                    source_coverage[kind] = 0

    latest_lessons: list[dict] = []
    latest_observations: list[dict] = []
    open_questions: list[str] = []

    for row in index.get("latest_lessons", []) if isinstance(index, dict) else []:
        if not isinstance(row, dict):
            continue
        compact = dict(row)
        compact["summary"] = _compact_learning_text(compact.get("summary"))
        latest_lessons.append(compact)

    for row in index.get("latest_observations", []) if isinstance(index, dict) else []:
        if not isinstance(row, dict):
            continue
        compact = dict(row)
        compact["summary"] = _compact_learning_text(compact.get("summary"))
        latest_observations.append(compact)

    for question in index.get("open_questions", []) if isinstance(index, dict) else []:
        q = _compact_learning_text(question)
        if q and q not in open_questions:
            open_questions.append(q)

    return {
        "scope": (index.get("scope") if isinstance(index, dict) else None) or "all_time",
        "source_coverage": source_coverage,
        "latest_lessons": latest_lessons,
        "latest_observations": latest_observations,
        "open_questions": open_questions[:3],
    }


def _derive_fallback_next_action(
    session_state: dict | None,
    market_clock: dict | None,
    focus_list: list[str],
    report_status: dict[str, dict],
) -> dict | None:
    if isinstance(session_state, dict) and session_state.get("next_action"):
        return session_state.get("next_action")

    phase = ((market_clock or {}).get("phase") or "").lower()
    ready_symbols = [
        sym for sym in focus_list
        if ((report_status.get(sym) or {}).get("today_state") == "ready")
    ]
    pending_symbols = [
        sym for sym in focus_list
        if sym not in ready_symbols
    ]

    if not focus_list:
        return {
            "priority": "normal",
            "instruction": "先确定今日关注标的，再进入盘前到盘中的主流程。",
        }
    if phase in {"rest_day", "closed", "weekend"}:
        if ready_symbols:
            return {
                "priority": "normal",
                "instruction": f"休市阶段，优先复核已准备好的关注标的：{', '.join(ready_symbols[:3])}。",
            }
        return {
            "priority": "immediate",
            "instruction": f"休市阶段先补齐今日关注的准备状态，优先处理：{', '.join(pending_symbols[:3])}。",
        }
    if phase == "premarket":
        if ready_symbols:
            return {
                "priority": "normal",
                "instruction": f"盘前先锁定今日主盯标的：{', '.join(ready_symbols[:3])}。",
            }
        return {
            "priority": "immediate",
            "instruction": "盘前先补齐今日关注的计划与节点，再进入盘中执行。",
        }
    if phase == "regular":
        if ready_symbols:
            return {
                "priority": "immediate",
                "instruction": f"盘中优先盯住已 ready 的标的：{', '.join(ready_symbols[:3])}。",
            }
        return {
            "priority": "immediate",
            "instruction": "盘中先确认哪只关注标的具备可执行信息，再决定主盯对象。",
        }
    return {
        "priority": "normal",
        "instruction": "先看市场阶段，再确认今日关注里谁已经 ready。",
    }


# 鈹€鈹€ 涓婁笅鏂囨瀯寤?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def _build_focus_priority_summary(
    focus_list: list[str],
    report_status: dict[str, dict],
    macro_nodes_all: dict[str, dict],
    intraday: dict[str, dict],
    daily_plan: dict | None,
) -> dict:
    ranked: list[dict] = []
    per_symbol = (daily_plan or {}).get("per_symbol") or {}

    for idx, sym in enumerate(focus_list):
        rs = report_status.get(sym) or {}
        intraday_sym = intraday.get(sym) or {}
        price_now = intraday_sym.get("price_now") or {}
        gate_status = str(price_now.get("gate_status") or "").lower()
        action_now = (intraday_sym.get("action_now") or {}).get("conclusion")
        plan_action = (per_symbol.get(sym) or {}).get("action_now")
        macro_nodes = macro_nodes_all.get(sym) or {}

        score = 0
        reasons: list[str] = []

        if rs.get("today_state") == "ready":
            score += 35
            reasons.append("今日已就绪")
        elif rs.get("trade_plan_state") == "today":
            score += 24
            reasons.append("已有今日计划")
        elif rs.get("trade_plan_state") == "historical":
            score += 12
            reasons.append("可复用历史计划")

        if rs.get("research_base_state") == "ready":
            score += 15
            reasons.append("研究底座完整")
        if rs.get("has_macro_nodes") or macro_nodes:
            score += 12
            reasons.append("节点可用")

        effective_action = str(action_now or plan_action or "").lower()
        if effective_action in {"enter", "watch", "hold", "reduce", "exit"}:
            score += 10
            reasons.append(f"动作={effective_action}")

        if gate_status in {"通过", "ok", "pass"}:
            score += 6
            reasons.append("门控通过")

        ranked.append({
            "sym": sym,
            "score": score,
            "reasons": reasons or ["待补充更多信息"],
            "rank_seed": idx,
        })

    ranked.sort(key=lambda item: (-item["score"], item["rank_seed"]))
    lead = ranked[0] if ranked else None
    return {
        "lead_symbol": lead["sym"] if lead else None,
        "lead_score": lead["score"] if lead else 0,
        "lead_reason": " / ".join((lead or {}).get("reasons", [])[:3]) if lead else "",
        "queue": [item["sym"] for item in ranked[:3]],
        "items": ranked,
    }

def calculate_cooling_states(real_trades, cooling_minutes=30):
    """
    Scans real_trades for recent sell transactions (take_profits) and calculates 
    remaining cooling seconds.
    """
    cooling = {}
    now = datetime.now(timezone.utc)
    for t in real_trades:
        sym = t.get("symbol", "").upper()
        if not sym or sym in cooling:
            continue
        is_sell = t.get("type") == "sell" or t.get("action") == "sell"
        if is_sell:
            try:
                ts_str = t.get("timestamp") or t.get("date")
                if ts_str:
                    if "T" in ts_str:
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    else:
                        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                        
                    delta = (now - dt).total_seconds()
                    cooling_seconds = cooling_minutes * 60
                    if delta < cooling_seconds:
                        cooling[sym] = {
                            "remaining_seconds": int(cooling_seconds - delta),
                            "timestamp": ts_str,
                            "price": t.get("price"),
                            "shares": t.get("shares")
                        }
            except Exception:
                pass
    return cooling

def calculate_deviation_audit(real_trades, premarket_plans, date_str):
    """
    Compares trade prices with premarket plan levels to calculate disciplinary deviation scores.
    """
    audits = []
    today_trades = [t for t in real_trades if (t.get("date") or "").startswith(date_str) or (t.get("timestamp") or "").startswith(date_str)]
    
    for t in today_trades:
        sym = t.get("symbol", "").upper()
        plan = premarket_plans.get(sym)
        if not plan:
            continue
            
        entry_cfg = plan.get("entry", {})
        exit_cfg = plan.get("exit", {})
        
        entry_base = entry_cfg.get("entry_base") or entry_cfg.get("entry_base_adj")
        hard_stop = exit_cfg.get("hard_stop") or entry_cfg.get("stop_loss")
        target = exit_cfg.get("target_price") or entry_cfg.get("target_price")
        
        actual_price = t.get("price")
        trade_type = t.get("type") or t.get("action")
        
        if not actual_price:
            continue
            
        deviation_pct = 0.0
        score = 100
        rating = "Excellent"
        note = ""
        
        if trade_type in ["buy", "BUY"]:
            if entry_base:
                deviation_pct = (actual_price - entry_base) / entry_base * 100
                abs_dev = abs(deviation_pct)
                if abs_dev <= 1.0:
                    score = 100
                    rating = "Perfect"
                    note = f"完美买点！偏离计划入场位 {deviation_pct:+.2f}%"
                elif abs_dev <= 3.0:
                    score = 90
                    rating = "Good"
                    note = f"执行良好。偏离计划入场位 {deviation_pct:+.2f}%"
                elif abs_dev <= 5.0:
                    score = 75
                    rating = "Warning"
                    note = f"轻微追高/偏离。偏离计划入场位 {deviation_pct:+.2f}%"
                else:
                    score = 50
                    rating = "Discipline Breach"
                    note = f"严重追高！偏离计划入场位 {deviation_pct:+.2f}%"
            else:
                note = "盘前未设定明确的买入基准位"
                score = 80
                rating = "Unrated"
        elif trade_type in ["sell", "SELL", "stop_hit"]:
            if hard_stop and abs(actual_price - hard_stop) / hard_stop * 100 < 2.0:
                deviation_pct = (actual_price - hard_stop) / hard_stop * 100
                score = 100
                rating = "Disciplined Stop"
                note = f"纪律性止损出场，与计划止损线相差 {deviation_pct:+.2f}%"
            elif target and actual_price >= target:
                deviation_pct = (actual_price - target) / target * 100
                score = 100
                rating = "Disciplined Profit"
                note = f"完美止盈出场！与计划止盈线相差 {deviation_pct:+.2f}%"
            else:
                deviation_pct = 0.0
                score = 85
                rating = "Manual Exit"
                note = "手动离场，非预设止损/止盈点触发"
                
        audits.append({
            "symbol": sym,
            "timestamp": t.get("timestamp") or t.get("date"),
            "action": trade_type.upper(),
            "shares": t.get("shares"),
            "actual_price": actual_price,
            "plan_entry": entry_base,
            "plan_stop": hard_stop,
            "deviation_pct": round(deviation_pct, 2),
            "score": score,
            "rating": rating,
            "note": note
        })
        
    return audits

def build_dashboard_context(date: str, symbols: list[str] | None = None,
                             base_dir: str = BASE) -> dict:
    """构建 Jinja2 渲染上下文。"""
    from stock_team.utils.capsule_utils import (
        get_capsule_dir,
        get_current_nodes_path,
        get_intraday_snapshot_path,
        get_latest_premarket_plan_path,
        get_premarket_summary_path,
    )
    find_dir = os.path.join(base_dir, "findings")
    dashboard_cache = load_dashboard_cache(base_dir)

    if symbols is None:
        pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
        excluded = set(pos_data.get("_excluded", []))
        all_syms = [s for s in pos_data.get("positions", {}).keys() if s not in excluded]
        cfg = _load(os.path.join(base_dir, "config", "poll_config.json"))
        all_syms = list(dict.fromkeys(all_syms + cfg.get("default_symbols", [])))
        focus_data_initial = _load(os.path.join(base_dir, "config", "daily_focus.json"))
        focus_list_initial = [
            str(s).upper()
            for s in focus_data_initial.get("focus_stocks", [])
            if str(s).strip()
        ]
        all_syms = list(dict.fromkeys(all_syms + focus_list_initial))
        
        # 鑷姩鎰熷簲浠婃棩鐢熸垚鐨?CIO 鎶ュ憡涓寘鍚殑鑷畾涔夎偂绁?
        dynamic_syms = []
        rpt_dir = os.path.join(base_dir, "reports")
        if os.path.exists(rpt_dir):
            for f in os.listdir(rpt_dir):
                if f.startswith(f"{date}_") and f.endswith(".html"):
                    sym = f[len(date)+1:-5]
                    # 鎺掗櫎 daily_dashboard 寮€澶寸殑鎶ュ憡
                    if sym and not sym.startswith("daily_dashboard") and sym not in dynamic_syms:
                        dynamic_syms.append(sym.upper())
                        
        all_syms = list(dict.fromkeys(all_syms + dynamic_syms))
        
        # 鏄剧ず浠婃棩鏈夌洏鍓嶆眹鎬汇€佺洏涓揩鐓ф垨浠婃棩鍔ㄦ€佺敓鎴愪簡鎶ュ憡鐨勬爣鐨?
        symbols = [s for s in all_syms if
                   os.path.exists(get_premarket_summary_path(s, date, base_dir)) or
                   os.path.exists(get_intraday_snapshot_path(s, date, base_dir)) or
                   os.path.exists(get_current_nodes_path(s, base_dir)) or
                   s in dynamic_syms or
                   s in focus_list_initial]
        if not symbols:   # fallback锛氳嫢鏃犱换浣曟暟鎹枃浠讹紝鏄剧ず鍏ㄩ儴
            symbols = all_syms

    premarket    = load_premarket_summaries(date, symbols, find_dir)
    intraday     = load_intraday_latest(date, symbols, find_dir)
    events       = load_intraday_events(date, symbols, find_dir)
    portfolio    = load_portfolio_snapshot(date, find_dir)
    
    # ── 智能弹性加载持仓 (防止页面数据留白/恐慌) ──────────────────────────
    is_stale_portfolio = False
    portfolio_source_date = date

    if not portfolio or not portfolio.get("positions_detail"):
        # 降级级别 1: 扫描并加载最近一天的历史快照
        import glob
        snapshots = sorted(
            p for p in glob.glob(os.path.join(find_dir, "portfolio_snapshot_*.json"))
            if not os.path.basename(p).startswith("portfolio_snapshot_current")
        )
        if snapshots:
            latest_snap_path = snapshots[-1]
            try:
                with open(latest_snap_path, "r", encoding="utf-8") as f:
                    portfolio = json.load(f)
                is_stale_portfolio = True
                fn = os.path.basename(latest_snap_path)
                portfolio_source_date = fn[len("portfolio_snapshot_"):-5]
            except Exception:
                pass

    if not portfolio or not portfolio.get("positions_detail"):
        # 降级级别 2 (极致兜底): 直接读取静态配置底表 positions.json 模拟折算
        try:
            pos_cfg_path = os.path.join(base_dir, "config", "positions.json")
            if os.path.exists(pos_cfg_path):
                with open(pos_cfg_path, "r", encoding="utf-8") as f:
                    pos_data = json.load(f)
                
                portfolio = {
                    "totals": {
                        "total_value": 0.0,
                        "cash": pos_data.get("cash", 0.0),
                        "holdings_value": 0.0,
                        "total_profit": 0.0,
                        "total_profit_pct": 0.0,
                        "total_unrealized_pnl_pct": 0.0,  # 补上 total_unrealized_pnl_pct 字段以对齐 daily_dashboard.html.j2 模板渲染
                        "leverage_ratio": 0.0,
                        "var_5pct_loss": 0.0,
                        "var_5pct_pct": 0.0
                    },
                    "positions_detail": []
                }
                
                total_holdings_val = 0.0
                for sym, info in pos_data.get("positions", {}).items():
                    shares = info.get("shares", 0)
                    cost = info.get("cost", 0.0)
                    val = shares * cost
                    total_holdings_val += val
                    portfolio["positions_detail"].append({
                        "sym": sym,
                        "name": info.get("note", sym),
                        "shares": shares,
                        "cost": cost,
                        "price": cost,
                        "cur_price": cost,  # 补上 cur_price 字段以对齐 daily_dashboard.html.j2 模板渲染
                        "market_value": val,  # 补上 market_value 字段以对齐模板渲染
                        "days_held": 0,  # 补上 days_held 字段以对齐模板渲染
                        "value": val,
                        "profit": 0.0,
                        "profit_pct": 0.0,
                        "ratio": 0.0,
                        "macro_type": info.get("macro_type", "成长型")
                    })
                
                portfolio["totals"]["holdings_value"] = total_holdings_val
                portfolio["totals"]["total_value"] = total_holdings_val + pos_data.get("cash", 0.0)
                is_stale_portfolio = True
                portfolio_source_date = "静态持仓配置底表"
        except Exception:
            pass

    postmarket_d = load_postmarket_day(date, find_dir)
    session_st   = load_session_state(date, base_dir)
    session_lock = load_session_lock(date, base_dir)
    daily_plan   = load_daily_plan(date, base_dir)
    decision_st  = load_decision_state(date, base_dir)
    learning_st  = _load_learning_state(base_dir, dashboard_cache)
    poll_cfg     = _load(os.path.join(base_dir, "config", "poll_config.json"))
    sector_map_cfg = (poll_cfg.get("sector_map") or {}) if isinstance(poll_cfg, dict) else {}
    try:
        from stock_team.utils.market_clock import get_market_clock
        market_clock = get_market_clock()
    except Exception:
        market_clock = {}

    if isinstance(dashboard_cache, dict):
        if isinstance(dashboard_cache.get("premarket"), dict):
            if not premarket:
                premarket = dashboard_cache.get("premarket") or {}
            else:
                _merge_symbol_cache(premarket, dashboard_cache.get("premarket"), symbols)
        if isinstance(dashboard_cache.get("intraday"), dict):
            if not intraday:
                intraday = dashboard_cache.get("intraday") or {}
            else:
                _merge_symbol_cache(intraday, dashboard_cache.get("intraday"), symbols)
        if not events and isinstance(dashboard_cache.get("events"), list):
            events = dashboard_cache.get("events") or []
        if not portfolio and isinstance(dashboard_cache.get("portfolio"), dict):
            portfolio = dashboard_cache.get("portfolio") or {}
        if isinstance(dashboard_cache.get("postmarket_day"), dict):
            if not postmarket_d:
                postmarket_d = dashboard_cache.get("postmarket_day") or {}
            else:
                _merge_symbol_cache(postmarket_d, dashboard_cache.get("postmarket_day"), symbols)
        if isinstance(dashboard_cache.get("session_state"), dict):
            if not session_st:
                session_st = dashboard_cache.get("session_state") or {}
            else:
                _merge_symbol_cache(session_st, dashboard_cache.get("session_state"), symbols)
        if isinstance(dashboard_cache.get("daily_plan"), dict):
            if not daily_plan:
                daily_plan = dashboard_cache.get("daily_plan") or {}
            else:
                cache_daily_plan = dashboard_cache.get("daily_plan") or {}
                if isinstance(daily_plan, dict) and isinstance(cache_daily_plan, dict):
                    if not daily_plan.get("per_symbol") and cache_daily_plan.get("per_symbol"):
                        daily_plan["per_symbol"] = cache_daily_plan.get("per_symbol") or {}
                    else:
                        _merge_symbol_cache(daily_plan, cache_daily_plan, symbols)
        if not learning_st and isinstance(dashboard_cache.get("learning"), dict):
            learning_st = dashboard_cache.get("learning") or {}
        if not market_clock and isinstance(dashboard_cache.get("market_clock"), dict):
            market_clock = dashboard_cache.get("market_clock") or {}

    # Normalize older or partial daily_plan records so summary tables never render blank defaults.
    if isinstance(daily_plan, dict):
        per_symbol_dp = daily_plan.setdefault("per_symbol", {})
        for sym in symbols:
            sym_upper = sym.upper()
            dp_sym = per_symbol_dp.get(sym_upper)
            if isinstance(dp_sym, dict):
                dp_sym = dict(dp_sym)
                if dp_sym.get("entry_go_status") is None:
                    pvn_status = (intraday.get(sym_upper, {}).get("plan_vs_now", {}) or {}).get("entry_go_status")
                    dp_sym["entry_go_status"] = pvn_status or "pending"
                per_symbol_dp[sym_upper] = dp_sym
        daily_plan["per_symbol"] = per_symbol_dp

    # 鈹€鈹€ 鏁版嵁鑷剤涓?Schema 骞惰建鍚堝苟鍣?(Data Self-Healing & Schema Normalization) 鈹€鈹€
    # 璇诲彇浠婃棩鍏虫敞涓偂
    focus_path = os.path.join(base_dir, "config", "daily_focus.json")
    focus_data = _load(focus_path)
    focus_list_internal = [s.upper() for s in focus_data.get("focus_stocks", [])]

    if not daily_plan:
        daily_plan = {
            "date": date,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_context": {"env": "neutral", "vix_level": None, "macro_events": []},
            "symbols_today": list(dict.fromkeys(symbols + focus_list_internal)),
            "per_symbol": {},
            "stocks": {},
            "schedule": [],
            "gtc_required": [],
            "pending_suggestions_total": 0
        }

    # Sector-relative strength must come from cached data only.
    # We only copy existing cached fields across views; no live fetches and no recomputation here.
    def _copy_sector_fields(dst: dict | None, src: dict | None) -> bool:
        if not isinstance(dst, dict) or not isinstance(src, dict):
            return False
        changed = False
        dst_ss = dst.get("stock_snapshot")
        if not isinstance(dst_ss, dict):
            dst_ss = {}
            dst["stock_snapshot"] = dst_ss
        dst_pn = dst.get("price_now")
        if not isinstance(dst_pn, dict):
            dst_pn = {}
            dst["price_now"] = dst_pn
        src_ss = src.get("stock_snapshot") if isinstance(src.get("stock_snapshot"), dict) else {}
        src_pn = src.get("price_now") if isinstance(src.get("price_now"), dict) else {}

        def _src_value(key: str):
            for source in (src_pn, src_ss):
                if source.get(key) not in (None, ""):
                    return source.get(key)
            return None

        for key in ("sector_ref", "sector_gap_pct", "rs_vs_sector"):
            value = _src_value(key)
            if value is None:
                continue
            if dst_ss.get(key) is None:
                dst_ss[key] = value
                changed = True
            if dst_pn.get(key) is None:
                dst_pn[key] = value
                changed = True
        return changed

    for sym in symbols:
        sym_upper = sym.upper()
        pm_sym = premarket.get(sym_upper)
        it = intraday.get(sym_upper)
        cache_pm = (dashboard_cache.get("premarket") or {}).get(sym_upper) if isinstance(dashboard_cache, dict) else None
        cache_it = (dashboard_cache.get("intraday") or {}).get(sym_upper) if isinstance(dashboard_cache, dict) else None

        if isinstance(pm_sym, dict):
            if isinstance(it, dict):
                _copy_sector_fields(pm_sym, it)
            if isinstance(cache_pm, dict):
                _copy_sector_fields(pm_sym, cache_pm)

        if isinstance(it, dict):
            if isinstance(pm_sym, dict):
                _copy_sector_fields(it, pm_sym)
            if isinstance(cache_it, dict):
                _copy_sector_fields(it, cache_it)

    # 鏅鸿兘骞惰建鍚堝苟锛氬鏋?daily_plan 鍚湁 stocks锛屽皢鍏跺苟鍏?per_symbol锛屽疄鐜颁袱涓啓鍏ユā鍧楃殑鏃犵紳骞惰建
    per_symbol = daily_plan.setdefault("per_symbol", {})
    if "stocks" in daily_plan and isinstance(daily_plan["stocks"], dict):
        for sym, stk in daily_plan["stocks"].items():
            sym_upper = sym.upper()
            if sym_upper not in per_symbol or not per_symbol[sym_upper].get("key_levels", {}).get("hard_stop"):
                # 濡傛灉 per_symbol 涓病鏈夎鏍囩殑锛屾垨鑰呮牳蹇冪偣浣嶄负绌猴紝鍒欒繘琛岃嚜鎰堝苟杞ㄥ悎骞?
                pm_sym = premarket.get(sym_upper) or {}
                pm_entry = pm_sym.get("entry") or {}
                pm_exit = pm_sym.get("exit") or {}
                sc = pm_sym.get("strategic_context") or {}

                # 鐐逛綅鑷€傚簲铻嶅悎鎻愬彇
                entry_base = pm_entry.get("entry_base") or stk.get("watch_zone_hi")
                hard_stop = pm_exit.get("hard_stop") or pm_exit.get("stop_loss") or stk.get("t1_stop") or stk.get("stop")
                target = pm_exit.get("target_price") or pm_entry.get("target_price") or stk.get("t1_target1") or stk.get("t1_target")
                flex_add = pm_exit.get("flex_add_level") or stk.get("watch_zone_lo")
                flex_reduce = pm_exit.get("flex_reduce_level") or stk.get("t1_target2") or stk.get("t2_target")

                per_symbol[sym_upper] = {
                            "premarket_summary_path": get_premarket_summary_path(sym_upper, date, base_dir),
                    "action_now": stk.get("predicted_scene") or pm_entry.get("decision") or sc.get("strategic_stance") or "watch",
                    "key_levels": {
                        "entry_base": entry_base,
                        "hard_stop": hard_stop,
                        "flex_add": flex_add,
                        "flex_reduce": flex_reduce,
                        "target": target
                    },
                    "entry_go_status": None,
                    "pending_suggestions": 0,
                    "memo_valid": True,
                    "is_lite_inferred": stk.get("is_lite_inferred", False)
                }
        if "symbols_today" not in daily_plan or not daily_plan["symbols_today"]:
            daily_plan["symbols_today"] = list(per_symbol.keys())
    
    # 濉厖閭ｄ簺鏈夋暟鎹絾鏈啓鍏?daily_plan 鐨勬爣鐨勶紝褰诲簳瑙ｅ喅鈥滄暟鎹己澶辨樉绀轰负鈥斺€濋棶棰?
    per_symbol_data = daily_plan.setdefault("per_symbol", {})
    for sym in symbols:
        sym_upper = sym.upper()
        if sym_upper not in per_symbol_data:
            pm_sym = premarket.get(sym_upper) or {}
            pm_entry = pm_sym.get("entry") or {}
            pm_exit = pm_sym.get("exit") or {}
            sc = pm_sym.get("strategic_context") or {}

            entry_base = pm_entry.get("entry_base") or pm_entry.get("entry_base_adj")
            hard_stop = pm_exit.get("hard_stop") or pm_exit.get("stop_loss")
            target = pm_exit.get("target_price") or pm_entry.get("target_price")
            flex_add = pm_exit.get("flex_add_level") or pm_exit.get("flex_add_adj")
            flex_reduce = pm_exit.get("flex_reduce_level") or pm_exit.get("flex_reduce_adj")

            is_lite = pm_sym.get("_lite_mode", False) or not (entry_base and hard_stop)

            per_symbol_data[sym_upper] = {
                        "premarket_summary_path": get_premarket_summary_path(sym_upper, date, base_dir),
                "action_now": pm_entry.get("decision") or sc.get("strategic_stance") or "watch",
                "key_levels": {
                    "entry_base": entry_base,
                    "hard_stop": hard_stop,
                    "flex_add": flex_add,
                    "flex_reduce": flex_reduce,
                    "target": target
                },
                "entry_go_status": None,
                "pending_suggestions": 0,
                "memo_valid": True,
                "is_lite_inferred": is_lite
            }

    for sym_upper, data in per_symbol_data.items():
        if isinstance(data, dict) and data.get("entry_go_status") is None:
            data["entry_go_status"] = (intraday.get(sym_upper, {}).get("plan_vs_now", {}) or {}).get("entry_go_status") or "pending"

    # 妫€鏌ュ摢浜涙爣鐨勬湁浠婃棩 CIO 鎶ュ憡锛堟寜鑲＄エ鍙峰懡鍚嶏級
    rpt_dir = os.path.join(base_dir, "reports")
    cio_reports = {s for s in symbols
                   if os.path.exists(os.path.join(rpt_dir, f"{date}_{s}.html"))}

    # 妫€鏌ュ摢浜涙爣鐨勬湁 strategic_memo锛堢洿鎺ユ鏌ユ枃浠跺瓨鍦紝涓嶄緷璧?premarket_summary锛?
    has_memo_syms = {s for s in symbols
                     if os.path.exists(os.path.join(base_dir, f"strategic_memo_{s}.json"))}

    # 妫€鏌ュ摢浜涙爣鐨勬湁浠婃棩鍙鐮旂┒鎶ュ憡锛坮eport_viewer 鐢熸垚锛?
    research_reports = {s for s in symbols
                        if os.path.exists(os.path.join(rpt_dir, f"research_{s}.html"))}

    # 鍔ㄦ€佹壂鎻忔墍鏈夊彲鐢ㄧ殑鍘嗗彶鏃ユ湡浠ユ彁渚涘欢缁€ф敮鎸?
    available_dates = set()
    if os.path.exists(find_dir):
        for f in os.listdir(find_dir):
            if f.startswith("portfolio_snapshot_") and f.endswith(".json") and f != "portfolio_snapshot_current.json":
                d_str = f[len("portfolio_snapshot_"):-5]
                if len(d_str) == 10:
                    available_dates.add(d_str)
            elif f.startswith("premarket_summary_") and f.endswith(".json"):
                parts = f.split("_")
                if len(parts) >= 3:
                    d_str = parts[2]
                    if len(d_str) == 10:
                        available_dates.add(d_str)
    if os.path.exists(base_dir):
        for f in os.listdir(base_dir):
            if f.startswith("daily_plan_") and f.endswith(".json"):
                d_str = f[len("daily_plan_"):-5]
                if len(d_str) == 10:
                    available_dates.add(d_str)
    available_dates.add(date)
    sorted_dates = sorted(list(available_dates), reverse=True)

    # 鍔犺浇鑷€夎偂鍒楄〃
    wl_path = os.path.join(base_dir, "watchlist.json")
    watchlist_list = []
    if os.path.exists(wl_path):
        try:
            with open(wl_path, encoding="utf-8") as f:
                wl_data = json.load(f)
                watchlist_list = wl_data.get("watchlist", [])
        except Exception:
            pass

    # 1. 鏋勫缓鍘嗗彶鍑€鍊肩粍鍚堣蛋鍔?timeline
    portfolio_history = []
    for d_str in sorted(list(available_dates)):
        snap = load_portfolio_snapshot(d_str, find_dir, prefer_current=False)
        if snap and snap.get("totals"):
            totals = snap["totals"]
            portfolio_history.append({
                "date": d_str,
                "total_value": totals.get("total_value", 0.0),
                "total_exposure": totals.get("total_exposure", 0.0),
                "leverage_ratio": totals.get("leverage_ratio", 1.0),
                "unrealized_pnl_pct": totals.get("total_unrealized_pnl_pct", 0.0)
            })
    if not portfolio_history:
        portfolio_history.append({
            "date": date,
            "total_value": 100000.0,
            "total_exposure": 0.0,
            "leverage_ratio": 1.0,
            "unrealized_pnl_pct": 0.0
        })
    portfolio_history.sort(key=lambda x: x["date"])

    # 2. 扫秒 reports/ 目录下所有 CIO 深度辩论及长期研究报告
    all_cio_reports = []
    all_research_reports = []
    all_discussion_reports = []
    rpt_dir = os.path.join(base_dir, "reports")
    if os.path.exists(rpt_dir):
        for f in os.listdir(rpt_dir):
            if f.endswith(".html"):
                if f.startswith("research_"):
                    sym = f[len("research_"):-5].upper()
                    all_research_reports.append({
                        "symbol": sym,
                        "filename": f,
                        "path": f"/reports/{f}"
                    })
                elif f.startswith("discussion_"):
                    # discussion_YYYY-MM-DD_session.html or discussion_session.html
                    import re
                    match = re.search(r"discussion_(\d{4}-\d{2}-\d{2})_(.+)\.html", f)
                    if match:
                        d_str = match.group(1)
                        sess = match.group(2).upper()
                    else:
                        d_str = date
                        sess = f[len("discussion_"):-5].upper()
                    all_discussion_reports.append({
                        "date": d_str,
                        "session": sess,
                        "filename": f,
                        "path": f"/reports/{f}"
                    })
                elif len(f) >= 16 and f[4] == '-' and f[7] == '-' and f[10] == '_':
                    parts = f.split("_")
                    d_str = parts[0]
                    sym = "_".join(parts[1:])[:-5].upper()
                    if not sym.startswith("DAILY_DASHBOARD"):
                        all_cio_reports.append({
                            "date": d_str,
                            "symbol": sym,
                            "filename": f,
                            "path": f"/reports/{f}"
                        })
    all_cio_reports.sort(key=lambda x: (x["date"], x["symbol"]), reverse=True)
    all_research_reports.sort(key=lambda x: x["symbol"])
    all_discussion_reports.sort(key=lambda x: (x["date"], x["session"]), reverse=True)

    # 3. 璇诲彇 paper_trading 缁勫悎鐨勫巻鍙蹭氦鏄撳彴璐?(浠呯敤浜庢ā鎷熶氦鏄撳彴璐?
    trades_history_list = []
    trades_path = os.path.join(base_dir, "paper_trading", "trades.jsonl")
    if os.path.exists(trades_path):
        trades_history_list = _read_all_jsonl(trades_path)
        
    loose_trades_path = os.path.join(base_dir, "paper_trading", "loose", "trades.jsonl")
    loose_trades = []
    if os.path.exists(loose_trades_path):
        loose_trades = _read_all_jsonl(loose_trades_path)
        
    combined_trades = []
    for t in trades_history_list:
        t["acct_label"] = "core/main"
        combined_trades.append(t)
    for t in loose_trades:
        t["acct_label"] = "paper/loose"
        combined_trades.append(t)
    combined_trades.sort(key=lambda x: x.get("time", ""), reverse=True)

    # 4. 鍔犺浇浠婃棩鍏虫敞鍒楄〃 config/daily_focus.json
    focus_path = os.path.join(base_dir, "config", "daily_focus.json")
    focus_data = _load(focus_path)
    focus_list = [s.upper() for s in focus_data.get("focus_stocks", [])]

    # 5. 鍔犺浇浠婃棩鐩樺墠鎵弿鑷姩鎺ㄨ崘 candidates_{date}.json
    candidates_path = os.path.join(base_dir, f"candidates_{date}.json")
    candidates_data = _load(candidates_path)
    candidates_list = candidates_data.get("candidates", [])

    # 6. 璇诲彇瀹炵洏鐪熷疄鎴愪氦鍙拌处 knowledge/trading_history.jsonl
    real_trades = []
    th_path = os.path.join(base_dir, "knowledge", "trading_history.jsonl")
    if os.path.exists(th_path):
        with open(th_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        if rec.get("type") in ["buy", "sell", "stop_hit"]:
                            real_trades.append(rec)
                    except Exception:
                        pass
    real_trades.reverse()  # 鍊掑簭锛屾渶鏂板湪鏈€涓?

    # 7. 鍔犺浇鍙敤鐜伴噾骞跺姩鎬佽绠?NAV (鎬诲噣璧勪骇) 涓庣粍鍚堟潈閲?
    pos_path = os.path.join(base_dir, "config", "positions.json")
    pos_data = _load(pos_path)
    cash_val = float(pos_data.get("cash", 7034.90))
    _apply_portfolio_price_overrides(portfolio, pos_data)

    holdings_value = 0.0
    if portfolio and "positions_detail" in portfolio:
        for d in portfolio["positions_detail"]:
            holdings_value += float(d.get("market_value", 0.0))
    nav_val = holdings_value + cash_val

    if portfolio and "totals" in portfolio:
        portfolio["totals"]["total_value"] = nav_val
        portfolio["totals"]["cash"] = cash_val
        portfolio["totals"]["holdings_value"] = holdings_value
        # 鏉犳潌璁＄畻 = 鎬绘暈鍙?/ NAV
        tot_exp = float(portfolio["totals"].get("total_exposure", 0.0))
        portfolio["totals"]["leverage_ratio"] = round(tot_exp / nav_val, 2) if nav_val > 0 else 0.0
        # VaR 鐧惧垎姣旇绠?
        var_loss = float(portfolio["totals"].get("var_5pct_loss", 0.0))
        portfolio["totals"]["var_5pct_pct"] = round(var_loss / nav_val * 100, 1) if nav_val > 0 else 0.0

    # 8. 鍔犺浇妯℃嫙鐩樿处鎴锋暟鎹?
    loose_portfolio = _load(os.path.join(base_dir, "paper_trading", "loose", "portfolio.json"))
    benchmark_portfolio = _load(os.path.join(base_dir, "paper_trading", "portfolio.json"))

    # 9. 鍔犺浇 yfinance 鏁版嵁鍋ュ悍鐘舵€?
    yf_status_path = os.path.join(base_dir, "logs", "yfinance_status.json")
    data_health = {"status": "stable", "errors": []}
    if os.path.exists(yf_status_path):
        try:
            with open(yf_status_path, "r", encoding="utf-8") as f:
                data_health = json.load(f)
        except Exception:
            pass

    # 璇诲彇鏈嶅姟鍣ㄥ疄闄呰繍琛岀殑绔彛
    server_port = 8080
    try:
        port_path = os.path.join(base_dir, "config", "server_port.json")
        if os.path.exists(port_path):
            with open(port_path, "r", encoding="utf-8") as pf:
                port_data = json.load(pf)
                server_port = port_data.get("port", 8080)
    except Exception:
        pass

    # 10. 构建每只标的的三态报告状态 + macro_strategy 节点 + premarket 详情
    report_status = {}
    macro_nodes_all = {}
    premarket_details = {}
    rpt_d = os.path.join(base_dir, "reports")
    
    # ── 🔬 Load options chain indicators from premarket_analysis_{date}.json ──
    pm_analysis_path = os.path.join(base_dir, f"premarket_analysis_{date}.json")
    pm_analysis_data = {}
    if os.path.exists(pm_analysis_path):
        try:
            with open(pm_analysis_path, encoding="utf-8") as f:
                pm_analysis_data = json.load(f).get("stocks", {})
        except Exception:
            pass

    for s in symbols:
        sym_upper = s.upper()
        capsule_dir = get_capsule_dir(sym_upper, base_dir)
        capsule_memo = os.path.join(capsule_dir, "strategic_memo.json")
        memo_path = capsule_memo if os.path.exists(capsule_memo) else os.path.join(base_dir, f"strategic_memo_{sym_upper}.json")
        macro_path = os.path.join(base_dir, f"macro_strategy_{sym_upper}.json")
        prem_path = get_premarket_summary_path(sym_upper, date, base_dir)
        latest_plan_path = get_latest_premarket_plan_path(sym_upper, base_dir)
        current_nodes_path = get_current_nodes_path(sym_upper, base_dir)
        latest_plan = _load(latest_plan_path) if os.path.exists(latest_plan_path) else {}
        current_nodes = _load(current_nodes_path) if os.path.exists(current_nodes_path) else {}
        current_plan_date = latest_plan.get("date") if isinstance(latest_plan, dict) else None
        cio_rpt = os.path.join(rpt_d, f"{date}_{sym_upper}.html") if os.path.exists(rpt_d) else ""
        latest_cio_date, latest_cio_path = _latest_dated_file(rpt_d, f"*_ {sym_upper}.html".replace("_ ", "_")) if os.path.exists(rpt_d) else (None, None)
        
        capsule_plans_dir = os.path.join(capsule_dir, "plans")
        if os.path.exists(capsule_plans_dir):
            latest_premarket_date, latest_premarket_path = _latest_dated_file(capsule_plans_dir, "premarket_summary_*.json")
        else:
            latest_premarket_date, latest_premarket_path = _latest_dated_file(find_dir, f"premarket_summary_*_{sym_upper}.json")
        research_path = os.path.join(rpt_d, f"research_{sym_upper}.html") if os.path.exists(rpt_d) else ""

        has_today_current_plan = bool(latest_plan) and current_plan_date == date
        latest_effective_date = current_plan_date or latest_premarket_date
        status = {
            "has_cio": os.path.exists(cio_rpt) if cio_rpt else False,
            "has_any_cio": bool(latest_cio_path),
            "has_memo": os.path.exists(memo_path),
            "has_macro_nodes": os.path.exists(current_nodes_path) or os.path.exists(macro_path),
            "has_premarket_summary": has_today_current_plan or os.path.exists(prem_path),
            "has_any_premarket_summary": bool(latest_plan) or bool(latest_premarket_path),
            "has_research_report": os.path.exists(research_path) if research_path else False,
            "latest_cio_date": latest_cio_date,
            "latest_premarket_date": latest_effective_date,
        }
        status["research_base_state"] = "ready" if (
            status["has_research_report"] or status["has_any_cio"] or status["has_memo"]
        ) else "missing"
        status["trade_plan_state"] = (
            "today" if (
                status["has_premarket_summary"] or
                (isinstance(current_nodes, dict) and current_nodes.get("date") == date)
            )
            else "historical" if status["has_any_premarket_summary"]
            else "missing"
        )
        status["today_state"] = "ready" if status["has_premarket_summary"] else "needs_refresh"
        report_status[sym_upper] = status

        if isinstance(current_nodes, dict) and current_nodes.get("nodes"):
            macro_nodes_all[sym_upper] = _normalize_macro_nodes(
                sym_upper,
                current_nodes.get("nodes", {}),
                daily_plan=daily_plan,
                premarket=premarket,
            )
        elif os.path.exists(macro_path):
            try:
                with open(macro_path, encoding="utf-8") as f:
                    ms = json.load(f)
                    macro_nodes_all[sym_upper] = _normalize_macro_nodes(
                        sym_upper,
                        ms.get("nodes", {}),
                        daily_plan=daily_plan,
                        premarket=premarket,
                    )
            except Exception:
                pass

        if isinstance(latest_plan, dict) and latest_plan:
            premarket_details[sym_upper] = latest_plan
        elif os.path.exists(prem_path):
            try:
                with open(prem_path, encoding="utf-8") as f:
                    premarket_details[sym_upper] = json.load(f)
            except Exception:
                pass
        elif latest_premarket_path:
            try:
                with open(latest_premarket_path, encoding="utf-8") as f:
                    historical_pm = json.load(f)
                    premarket_details[sym_upper] = historical_pm
                    if sym_upper not in macro_nodes_all:
                        historical_nodes = _nodes_from_premarket_summary(historical_pm)
                        if historical_nodes:
                            macro_nodes_all[sym_upper] = _normalize_macro_nodes(
                                sym_upper,
                                historical_nodes,
                                daily_plan=daily_plan,
                                premarket=premarket,
                            )
            except Exception:
                pass

        # Merge options_indicators from premarket_analysis_{date}.json if available
        if sym_upper in pm_analysis_data:
            opt_ind = pm_analysis_data[sym_upper].get("options_indicators")
            if opt_ind:
                if sym_upper not in premarket_details:
                    premarket_details[sym_upper] = {}
                premarket_details[sym_upper]["options_indicators"] = opt_ind

        it = intraday.get(sym_upper)
        chart = it.get("mini_chart") if isinstance(it, dict) else None
        if isinstance(chart, dict) and not chart.get("nodes"):
            macro_chart_nodes = _chart_nodes_from_macro_nodes(macro_nodes_all.get(sym_upper))
            if not macro_chart_nodes:
                # Fallback to premarket summary entry / stop levels
                pm_data = premarket_details.get(sym_upper) or {}
                pm_entry = pm_data.get("entry") or {}
                macro_chart_nodes = []
                if pm_entry.get("entry_base"):
                    macro_chart_nodes.append({"name": "entry_base", "price": pm_entry["entry_base"]})
                if pm_entry.get("stop_loss"):
                    macro_chart_nodes.append({"name": "hard_stop", "price": pm_entry["stop_loss"]})
                if pm_entry.get("target_price"):
                    macro_chart_nodes.append({"name": "target", "price": pm_entry["target_price"]})
            
            if macro_chart_nodes:
                chart["nodes"] = macro_chart_nodes
                prices = [p for candle in chart.get("candles", []) for p in (candle.get("low"), candle.get("high"))]
                prices += [node["price"] for node in macro_chart_nodes]
                prices = [p for p in prices if p is not None]
                if prices:
                    chart["range"] = {"low": round(min(prices), 2), "high": round(max(prices), 2)}

    # 琛ュ厖娴佸叆涓績锛氬皢宸叉湁 premarket_summary 浣嗕笉鍦ㄥ€欓€夊垪琛ㄧ殑鏍囩殑娉ㄥ叆
    for sym_upper, status in report_status.items():
        if status.get("has_premarket_summary") and sym_upper not in [c.get("sym","") for c in candidates_list]:
            candidates_list.append({"sym": sym_upper, "score": 0, "recent_2d": 0, "reasons": ["宸叉湁鐩樺墠鍒嗘瀽"]})

    focus_readiness = []
    for sym in focus_list:
        rs = report_status.get(sym, {}) or {}
        focus_readiness.append({
            "sym": sym,
            "research_base_state": rs.get("research_base_state", "missing"),
            "trade_plan_state": rs.get("trade_plan_state", "missing"),
            "today_state": rs.get("today_state", "missing"),
            "has_any_cio": bool(rs.get("has_any_cio")),
            "has_research_report": bool(rs.get("has_research_report")),
            "has_macro_nodes": bool(rs.get("has_macro_nodes")) or bool(macro_nodes_all.get(sym)),
            "latest_cio_date": rs.get("latest_cio_date"),
            "latest_premarket_date": rs.get("latest_premarket_date"),
        })

    focus_priority_summary = _build_focus_priority_summary(
        focus_list,
        report_status,
        macro_nodes_all,
        intraday,
        daily_plan,
    )

    if not isinstance(session_st, dict):
        session_st = {}
    if not session_st.get("next_action"):
        session_st["next_action"] = _derive_fallback_next_action(
            session_st,
            market_clock,
            focus_list,
            report_status,
        )

    # Calculate cooling states, deviation audits, and load IB events
    cooling_states = calculate_cooling_states(real_trades)
    deviation_audits = calculate_deviation_audit(real_trades, premarket, date)
    
    ib_events = []
    ib_log_path = os.path.join(investing_os_home(BASE), "system", "data", "packets", "ib_event_log.json")
    if os.path.exists(ib_log_path):
        try:
            with open(ib_log_path, "r", encoding="utf-8") as f:
                ib_data = json.load(f)
                if isinstance(ib_data, list):
                    ib_events = ib_data
                elif isinstance(ib_data, dict):
                    ib_events = [ib_data]
        except Exception:
            pass
    ib_events = sorted(ib_events, key=lambda e: e.get("timestamp", ""), reverse=True)

    return {
        "report_status":          report_status,
        "macro_nodes":            macro_nodes_all,
        "premarket_details":      premarket_details,
        "cooling_states":         cooling_states,
        "deviation_audits":       deviation_audits,
        "ib_events":              ib_events,
        "date":                   date,
        "generated_at":           datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "data_health":            data_health,
        "symbols":                symbols,
        "premarket":              premarket,
        "intraday":               intraday,
        "events":                 events,
        "portfolio":              portfolio,
        "is_stale_portfolio":     is_stale_portfolio,
        "portfolio_source_date":  portfolio_source_date,
        "postmarket_day":         postmarket_d,
        "session_state":          session_st,
        "session_lock":           session_lock,
        "daily_plan":             daily_plan,
        "decision_state":         decision_st,
        "learning":               learning_st,
        "cio_reports":            cio_reports,
        "has_memo_syms":          has_memo_syms,
        "research_reports":       research_reports,
        "available_dates":        sorted_dates,
        "watchlist":              watchlist_list,
        "portfolio_history_json": json.dumps(portfolio_history),
        "all_cio_reports":        all_cio_reports,
        "all_research_reports":   all_research_reports,
        "all_discussion_reports": all_discussion_reports,
        "trades_history":         combined_trades, # 妯℃嫙鐩樺彴璐?
        "focus_list":             focus_list,      # 浠婃棩鍏虫敞鍒楄〃
        "candidates_list":        candidates_list,  # 鐩樺墠鎵弿鍊欓€夎偂
        "real_trades":            real_trades,     # 瀹炵洏鐪蟶浜ゆ槗鍙拌处
        "cash":                   cash_val,
        "nav":                    nav_val,
        "positions_config":       pos_data,        # 瀹炵洏鎸佷粨閰嶇疆鍏冩暟鎹?
        "loose_portfolio":        loose_portfolio,  # 妯℃嫙瀹芥澗缁勫悎
        "benchmark_portfolio":    benchmark_portfolio, # 妯℃嫙鍩哄噯缁勫悎
        "server_port":            server_port,     # 浠〃鐩樺悗绔繍琛岀鍙?
        "market_clock":           market_clock,
        "watchlist_live":         _load(os.path.join(base_dir, "findings", "watchlist_live_status.json")),
        "focus_readiness":        focus_readiness,
        "focus_priority_summary": focus_priority_summary,
    }



# HTML generation

def write_dashboard(date: str, symbols: list[str] | None = None,
                    base_dir: str = BASE) -> str:
    """Generate dashboard.html and return the output path."""
    try:
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(os.path.join(base_dir, "templates")),
                          autoescape=False,
                          auto_reload=True, cache_size=0)
        tmpl = env.get_template("daily_dashboard.html.j2")
    except Exception as e:
        return f"[dashboard_writer] Jinja2 load failed: {e}"

    ctx  = build_dashboard_context(date, symbols, base_dir)
    html = tmpl.render(**ctx)

    os.makedirs(os.path.join(base_dir, "reports"), exist_ok=True)
    path = os.path.join(base_dir, "reports", f"dashboard.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def build_dashboard_route_snapshot(ctx: dict) -> dict:
    session_state = ctx.get("session_state") or {}
    market_clock = ctx.get("market_clock") or {}
    symbols = ctx.get("focus_list") or ctx.get("symbols") or []
    priority = ctx.get("focus_priority_summary") or {}
    return {
        "phase_label": session_state.get("market_phase") or market_clock.get("phase") or "unknown",
        "top_symbols": list(symbols[:5]),
        "has_focus": bool(symbols),
        "daily_plan_date": (ctx.get("daily_plan") or {}).get("date"),
        "has_next_action": bool(session_state.get("next_action")),
        "lead_focus_symbol": priority.get("lead_symbol"),
    }


def main():
    date_str = _date.today().strftime("%Y-%m-%d")
    path = write_dashboard(date_str)
    print(f"Dashboard: {path}")


if __name__ == "__main__":
    main()

