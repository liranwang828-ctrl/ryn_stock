"""
盘后数据收集模块 — postmarket_data_collector.py
纯规则计算 execution / performance / signal_accuracy / suggestions。
无 LLM 调用，全部可单元测试。

用法：由 postmarket_summary.py 调用，不直接运行。
"""
import json, os
from datetime import datetime, date as _date, timezone

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


def _read_last_jsonl(path: str) -> dict | None:
    """读取 JSONL 文件最后一条，文件不存在或为空时返回 None"""
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


# ── build_execution ────────────────────────────────────────────────────────

def build_execution(sym: str, date: str, base_dir: str = BASE) -> dict:
    """
    读取 premarket_summary + intraday_snapshot，计算今日执行情况。
    """
    find_dir = os.path.join(base_dir, "findings")
    pm = _load(os.path.join(find_dir, f"premarket_summary_{date}_{sym.upper()}.json"))
    adj = pm.get("post_open_adj") or {}

    # plan_entry_triggered：来自 post_open_adj.entry_go
    entry_go = adj.get("entry_go")
    plan_entry_triggered = bool(entry_go) if entry_go is not None else None

    # plan_exit_triggered：读 intraday_snapshot 末条的 thesis_signal
    snap_path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym.upper()}.jsonl")
    snap_last = _read_last_jsonl(snap_path)
    plan_exit_triggered = None
    if snap_last:
        ts = snap_last.get("plan_vs_now", {}).get("thesis_signal")
        plan_exit_triggered = ts == "breach"

    return {
        "plan_entry_triggered": plan_entry_triggered,
        "actual_entry":         None,    # 由 translator.py 记录，此处暂为 null
        "plan_exit_triggered":  plan_exit_triggered,
        "actual_exit":          None,
        "followed_plan":        "na",
        "deviation_note":       "",
    }


# ── build_performance ──────────────────────────────────────────────────────

def build_performance(sym: str, date: str, base_dir: str = BASE) -> dict:
    """
    计算今日损益和持仓天数。
    open_price / close_price 从 yfinance 获取（若失败则返回 null）。
    """
    find_dir = os.path.join(base_dir, "findings")
    pm   = _load(os.path.join(find_dir, f"premarket_summary_{date}_{sym.upper()}.json"))
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    pos  = pos_data.get("positions", {}).get(sym.upper(), {})

    hard_stop  = (pm.get("exit") or {}).get("hard_stop")
    target     = (pm.get("exit") or {}).get("target_price") or \
                 (pm.get("entry") or {}).get("target_price")

    entry_date_str = pos.get("date", date)
    try:
        entry_date = _date.fromisoformat(entry_date_str)
        today_date = _date.fromisoformat(date)
        days_held  = (today_date - entry_date).days
    except Exception:
        days_held  = 0

    thesis_updated_str = pos.get("thesis_updated", date)
    try:
        thesis_date = _date.fromisoformat(thesis_updated_str)
        today_date2 = _date.fromisoformat(date)
        thesis_days = (today_date2 - thesis_date).days
    except Exception:
        thesis_days = 0

    # 尝试获取 yfinance 价格（失败时返回 null）
    open_price = close_price = day_ret_pct = None
    try:
        import yfinance as yf
        ticker = yf.Ticker(sym.upper())
        hist   = ticker.history(period="2d")
        if not hist.empty and len(hist) >= 1:
            row        = hist.iloc[-1]
            open_price = round(float(row["Open"]), 2)
            close_price= round(float(row["Close"]), 2)
            if open_price and open_price > 0:
                day_ret_pct = round((close_price - open_price) / open_price * 100, 2)
    except Exception:
        pass

    vs_target_pct = None
    if close_price is not None and target:
        vs_target_pct = round((close_price - target) / target * 100, 2)

    vs_stop_pct = None
    if close_price is not None and hard_stop:
        vs_stop_pct = round((close_price - hard_stop) / close_price * 100, 2)

    return {
        "open_price":   open_price,
        "close_price":  close_price,
        "day_ret_pct":  day_ret_pct,
        "vs_target_pct": vs_target_pct,
        "vs_stop_pct":   vs_stop_pct,
        "days_held":    days_held,
        "thesis_days":  thesis_days,
    }


# ── build_signal_accuracy ──────────────────────────────────────────────────

def build_signal_accuracy(sym: str, date: str, day_ret_pct: float | None,
                           base_dir: str = BASE) -> dict:
    """
    纯规则推导今日各信号准确性（全部 B 级，无 LLM）。
    """
    find_dir = os.path.join(base_dir, "findings")
    pm  = _load(os.path.join(find_dir, f"premarket_summary_{date}_{sym.upper()}.json"))
    adj = pm.get("post_open_adj") or {}

    # pred_scene / actual_scene
    pred_scene   = (pm.get("stock_snapshot") or {}).get("pred_scene")
    actual_scene = adj.get("scene_confirmed")
    pred_scene_correct = (pred_scene == actual_scene) if (pred_scene and actual_scene) else None

    # intraday 末条
    snap_path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym.upper()}.jsonl")
    snap_last = _read_last_jsonl(snap_path)
    master_consensus = None
    if snap_last:
        master_consensus = snap_last.get("price_now", {}).get("master_consensus")

    # master_consensus_correct
    master_correct = None
    if master_consensus and day_ret_pct is not None:
        if master_consensus == "buy":
            master_correct = day_ret_pct > 0
        elif master_consensus == "no_buy":
            master_correct = day_ret_pct < 0

    # gate_correct：gate 通过且 entry_go=True → day_ret > 0
    gate_correct = None
    entry_go_status = (snap_last.get("plan_vs_now", {}).get("entry_go_status")
                       if snap_last else None)
    gate_status = (snap_last.get("price_now", {}).get("gate_status")
                   if snap_last else None)
    if gate_status == "通过" and entry_go_status == "go" and day_ret_pct is not None:
        gate_correct = day_ret_pct > 0

    # thesis_signal_correct：breach 是否真的对应大跌（< -2%）
    thesis_signal = (snap_last.get("plan_vs_now", {}).get("thesis_signal")
                     if snap_last else None)
    thesis_sig_correct = None
    if thesis_signal == "breach" and day_ret_pct is not None:
        thesis_sig_correct = day_ret_pct < -2.0

    # entry_go_outcome
    entry_go_outcome = None
    if adj.get("entry_go") is True and day_ret_pct is not None:
        if day_ret_pct > 1.0:
            entry_go_outcome = "profitable"
        elif day_ret_pct >= -1.0:
            entry_go_outcome = "break_even"
        else:
            entry_go_outcome = "loss"
    elif adj.get("entry_go") is False:
        entry_go_outcome = "not_triggered"

    return {
        "pred_scene_correct":       pred_scene_correct,
        "actual_scene":             actual_scene,
        "master_consensus_correct": master_correct,
        "gate_correct":             gate_correct,
        "thesis_signal_correct":    thesis_sig_correct,
        "entry_go_outcome":         entry_go_outcome,
    }


# ── generate_suggestions ───────────────────────────────────────────────────

def generate_suggestions(
    sym: str, date: str,
    execution: dict,
    performance: dict,
    signal_accuracy: dict,
) -> list[dict]:
    """
    规则驱动生成 12 类建议草稿（不依赖 LLM）。
    优先级：breach > warning > low。
    """
    suggs = []

    day_ret     = performance.get("day_ret_pct", 0.0) or 0.0
    thesis_days = performance.get("thesis_days", 0) or 0
    vs_stop     = performance.get("vs_stop_pct")
    followed    = execution.get("followed_plan", "na")
    ts_correct  = signal_accuracy.get("thesis_signal_correct")

    # 1. thesis_status：今日大跌（< -3%）或论点破裂信号
    if day_ret < -3.0 or ts_correct is True:
        suggs.append({
            "type": "thesis_status",
            "priority": "high",
            "description": f"{sym} 今日跌幅 {day_ret:.1f}%，建议重新评估论点状态",
            "proposed_value": {"new_status": "weakening"},
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 2. stop_move：今日明显上涨（> 3%）且利润充足
    if day_ret > 3.0 and vs_stop is not None and vs_stop > 8.0:
        suggs.append({
            "type": "stop_move",
            "priority": "medium",
            "description": f"{sym} 今日涨幅 {day_ret:.1f}%，考虑上移止损锁定利润",
            "proposed_value": {"new_stop": None},  # 由用户填写具体价位
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 3. time_stop_eval：thesis_days 超过 14 天
    if thesis_days > 14:
        suggs.append({
            "type": "time_stop_eval",
            "priority": "medium",
            "description": f"{sym} 持仓 {thesis_days} 天，建议评估时间止损",
            "proposed_value": {"thesis_days": thesis_days, "expected_days": 14},
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 4. trigger_deep_research：亏损连续或跌幅 > 5%
    if day_ret < -5.0:
        suggs.append({
            "type": "trigger_deep_research",
            "priority": "high",
            "description": f"{sym} 今日跌 {day_ret:.1f}%，建议重新做深度研究",
            "proposed_value": {"reason": f"单日跌幅 {day_ret:.1f}%"},
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 5. thesis_confirmation：今日大涨 + gate 通过
    if day_ret > 3.0 and signal_accuracy.get("gate_correct") is True:
        suggs.append({
            "type": "thesis_confirmation",
            "priority": "low",
            "description": f"{sym} 今日涨 {day_ret:.1f}%，gate 通过，论点积极确认",
            "proposed_value": {"signal": "gate_pass_positive_day", "add_opportunity": True},
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 6. lesson_record：每日必有
    lesson = f"{sym} {date}: " + (
        f"计划执行{'良好' if followed == 'yes' else '偏差'}，"
        f"今日{'+' if day_ret >= 0 else ''}{day_ret:.1f}%"
    )
    suggs.append({
        "type": "lesson_record",
        "priority": "low",
        "description": lesson[:80],
        "proposed_value": {"lesson": lesson[:100]},
        "confirmed": None, "applied_at": None, "applied_to": None,
    })

    return suggs
