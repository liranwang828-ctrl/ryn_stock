"""
Dashboard 鍐欏叆妯″潡 鈥?dashboard_writer.py
璇诲彇鎵€鏈?B 绾?JSON锛岀敓鎴?reports/daily_dashboard_{date}.html銆?

鐢ㄦ硶: python3.12 agents/dashboard_writer.py
     鎴栫敱 poll.py 姣忚疆鏈熬璋冪敤 write_dashboard()
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
    normalized = {k: (dict(v) if isinstance(v, dict) else v) for k, v in nodes.items()}
    key_levels = (((daily_plan or {}).get("per_symbol") or {}).get(sym.upper()) or {}).get("key_levels", {}) or {}
    pm = (premarket or {}).get(sym.upper()) or {}
    pm_exit = pm.get("exit") or {}

    flex_reduce = normalized.get("flex_reduce")
    if not isinstance(flex_reduce, dict):
        flex_reduce = {}
    if flex_reduce.get("price") is None:
        flex_reduce_price = key_levels.get("flex_reduce") or pm_exit.get("flex_reduce_level")
        if flex_reduce_price is not None:
            flex_reduce["price"] = flex_reduce_price
    normalized["flex_reduce"] = flex_reduce

    scene = normalized.get("scenario_downgrade")
    if not isinstance(scene, dict):
        scene = {}
    if scene.get("price") is None:
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
    """杩斿洖 {sym: premarket_summary_dict}"""
    result = {}
    for sym in symbols:
        path = os.path.join(find_dir, f"premarket_summary_{date}_{sym}.json")
        d = _load(path)
        if d:
            result[sym] = d
    return result

def load_intraday_latest(date: str, symbols: list[str],
                          find_dir: str = FIND_DIR) -> dict:
    """娴兼ê鍘涙禒?SQLite WAL 閺佺増宓佹惔鎾诡嚢閸欐牗娓堕弬鏉挎彥閻撗嶇礉閼汇儱銇戠拹銉﹀灗閺冪姵鏆熼幑顔煎灟閸ョ偤鈧偓閼?JSONL 绾板孩鏋冩禒?"""
    base_dir = os.path.dirname(find_dir)
    dashboard_cache = load_dashboard_cache(base_dir)
    cached_intraday = dashboard_cache.get("intraday") if isinstance(dashboard_cache, dict) else {}
    result = {}
    for sym in symbols:
        path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym}.jsonl")
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
            chart_rows = rows
            chart_source = None
            chart_source_date = None
            if len(rows) < 8:
                prev_date, prev_rows = _find_previous_intraday_tail(date, sym, find_dir, limit=10)
                if len(prev_rows) >= len(rows):
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
    for sym in symbols:
        path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym}.jsonl")
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


def load_portfolio_snapshot(date: str, find_dir: str = FIND_DIR) -> dict:
    path = os.path.join(find_dir, f"portfolio_snapshot_{date}.json")
    return _load(path)


def load_postmarket_day(date: str, find_dir: str = FIND_DIR) -> dict:
    path = os.path.join(find_dir, f"postmarket_summary_{date}.json")
    return _load(path)


def load_session_state(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, "learning", f"session_state_{date}.json")
    return _load(path)


def load_daily_plan(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, f"daily_plan_{date}.json")
    return _load(path)


def load_dashboard_cache(base_dir: str = BASE) -> dict:
    try:
        from agents.dashboard_cache import load_dashboard_cache as _load_dashboard_cache
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


# 鈹€鈹€ 涓婁笅鏂囨瀯寤?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def build_dashboard_context(date: str, symbols: list[str] | None = None,
                             base_dir: str = BASE) -> dict:
    """构建 Jinja2 渲染上下文。"""
    find_dir = os.path.join(base_dir, "findings")
    dashboard_cache = load_dashboard_cache(base_dir)

    if symbols is None:
        pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
        excluded = set(pos_data.get("_excluded", []))
        all_syms = [s for s in pos_data.get("positions", {}).keys() if s not in excluded]
        cfg = _load(os.path.join(base_dir, "config", "poll_config.json"))
        all_syms = list(dict.fromkeys(all_syms + cfg.get("default_symbols", [])))
        
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
                   os.path.exists(os.path.join(find_dir, f"premarket_summary_{date}_{s}.json")) or
                   os.path.exists(os.path.join(find_dir, f"intraday_snapshot_{date}_{s}.jsonl")) or
                   s in dynamic_syms]
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
        snapshots = sorted(glob.glob(os.path.join(find_dir, "portfolio_snapshot_*.json")))
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
    daily_plan   = load_daily_plan(date, base_dir)
    learning_st  = _load_learning_state(base_dir, dashboard_cache)
    poll_cfg     = _load(os.path.join(base_dir, "config", "poll_config.json"))
    sector_map_cfg = (poll_cfg.get("sector_map") or {}) if isinstance(poll_cfg, dict) else {}
    try:
        from agents.market_clock import get_market_clock
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
                    "premarket_summary_path": f"findings/premarket_summary_{date}_{sym_upper}.json",
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
                "premarket_summary_path": f"findings/premarket_summary_{date}_{sym_upper}.json",
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
            if f.startswith("portfolio_snapshot_") and f.endswith(".json"):
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
        snap = load_portfolio_snapshot(d_str, find_dir)
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

    # 2. 鎵弿 reports/ 鐩綍涓嬫墍鏈?CIO 娣卞害杈╄鍙婇暱鏈熺爺绌舵姤鍛?
    all_cio_reports = []
    all_research_reports = []
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

    # 10. 鏋勫缓姣忓彧鏍囩殑鐨勪笁鎬佹姤鍛婄姸鎬?+ macro_strategy 鑺傜偣 + premarket 璇︽儏
    report_status = {}
    macro_nodes_all = {}
    premarket_details = {}
    rpt_d = os.path.join(base_dir, "reports")
    for s in symbols:
        sym_upper = s.upper()
        memo_path = os.path.join(base_dir, f"strategic_memo_{sym_upper}.json")
        macro_path = os.path.join(base_dir, f"macro_strategy_{sym_upper}.json")
        prem_path = os.path.join(find_dir, f"premarket_summary_{date}_{sym_upper}.json")
        cio_rpt = os.path.join(rpt_d, f"{date}_{sym_upper}.html") if os.path.exists(rpt_d) else ""

        status = {
            "has_cio": os.path.exists(cio_rpt) if cio_rpt else False,
            "has_memo": os.path.exists(memo_path),
            "has_macro_nodes": os.path.exists(macro_path),
            "has_premarket_summary": os.path.exists(prem_path),
        }
        report_status[sym_upper] = status

        if os.path.exists(macro_path):
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

        if os.path.exists(prem_path):
            try:
                with open(prem_path, encoding="utf-8") as f:
                    premarket_details[sym_upper] = json.load(f)
            except Exception:
                pass

        it = intraday.get(sym_upper)
        chart = it.get("mini_chart") if isinstance(it, dict) else None
        if isinstance(chart, dict) and not chart.get("nodes"):
            macro_chart_nodes = _chart_nodes_from_macro_nodes(macro_nodes_all.get(sym_upper))
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

    return {
        "report_status":          report_status,
        "macro_nodes":            macro_nodes_all,
        "premarket_details":      premarket_details,
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
        "daily_plan":             daily_plan,
        "learning":               learning_st,
        "cio_reports":            cio_reports,
        "has_memo_syms":          has_memo_syms,
        "research_reports":       research_reports,
        "available_dates":        sorted_dates,
        "watchlist":              watchlist_list,
        "portfolio_history_json": json.dumps(portfolio_history),
        "all_cio_reports":        all_cio_reports,
        "all_research_reports":   all_research_reports,
        "trades_history":         combined_trades, # 妯℃嫙鐩樺彴璐?
        "focus_list":             focus_list,      # 浠婃棩鍏虫敞鍒楄〃
        "candidates_list":        candidates_list,  # 鐩樺墠鎵弿鍊欓€夎偂
        "real_trades":            real_trades,     # 瀹炵洏鐪熷疄浜ゆ槗鍙拌处
        "cash":                   cash_val,
        "nav":                    nav_val,
        "positions_config":       pos_data,        # 瀹炵洏鎸佷粨閰嶇疆鍏冩暟鎹?
        "loose_portfolio":        loose_portfolio,  # 妯℃嫙瀹芥澗缁勫悎
        "benchmark_portfolio":    benchmark_portfolio, # 妯℃嫙鍩哄噯缁勫悎
        "server_port":            server_port,     # 浠〃鐩樺悗绔繍琛岀鍙?
        "market_clock":           market_clock,
    }



# HTML generation

def write_dashboard(date: str, symbols: list[str] | None = None,
                    base_dir: str = BASE) -> str:
    """Generate daily_dashboard_{date}.html and return the output path."""
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
    path = os.path.join(base_dir, "reports", f"daily_dashboard_{date}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main():
    date_str = _date.today().strftime("%Y-%m-%d")
    path = write_dashboard(date_str)
    print(f"Dashboard: {path}")


if __name__ == "__main__":
    main()

