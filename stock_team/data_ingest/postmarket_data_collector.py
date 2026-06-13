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


def _find_prev_snapshot_date(date_str: str, base_dir: str = BASE) -> str | None:
    """在 findings 目录下寻找比 date_str 小的最接近的 portfolio_snapshot 日期"""
    import glob
    find_dir = os.path.join(base_dir, "findings")
    paths = glob.glob(os.path.join(find_dir, "portfolio_snapshot_*.json"))
    dates = []
    for p in paths:
        fname = os.path.basename(p)
        # portfolio_snapshot_2026-05-25.json
        d_part = fname.replace("portfolio_snapshot_", "").replace(".json", "")
        if d_part < date_str:
            dates.append(d_part)
    if not dates:
        return None
    dates.sort()
    return dates[-1]


def build_trade_context(date_str: str, base_dir: str = BASE) -> dict:
    """
    汇聚今日交易的决策上下文。
    比对今日 positions.json 与昨日 portfolio_snapshot_{prev_date}.json，
    结合 tranches 的更新日期，自动识别今日的买入、卖出和加仓动作，并载入盘前决策背景。
    """
    find_dir = os.path.join(base_dir, "findings")
    
    # 1. 加载今日持仓和昨日快照
    today_pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    today_pos = today_pos_data.get("positions", {})
    
    prev_date = _find_prev_snapshot_date(date_str, base_dir=base_dir)
    prev_pos = {}
    if prev_date:
        prev_snap = _load(os.path.join(find_dir, f"portfolio_snapshot_{prev_date}.json"))
        for p in prev_snap.get("positions_detail", []):
            prev_pos[p["sym"].upper()] = p
            
    # 2. 识别今日交易动作
    trades = []

    history_path = os.path.join(base_dir, "knowledge", "trading_history.jsonl")
    manual_trades = []
    if os.path.exists(history_path):
        with open(history_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get("date") != date_str or row.get("scene") != "manual_user_report":
                    continue
                action_type = str(row.get("type", "")).lower()
                if action_type == "buy":
                    action = "BUY_ADD" if row.get("price_inferred") else "BUY"
                elif action_type == "sell":
                    action = "SELL_CLEAR" if row.get("clear_position") else "SELL_PARTIAL"
                else:
                    continue
                manual_trades.append({
                    "sym": str(row.get("sym", "")).upper(),
                    "action": action,
                    "cost": float(row.get("price") or 0),
                    "shares": int(float(row.get("shares") or 0)),
                    "note": row.get("reason", "manual_user_report"),
                    "date": date_str,
                    "source": "trading_history.manual_user_report",
                    "raw_trade": row,
                })

    if manual_trades:
        trades = manual_trades
        daily_plan = _load(os.path.join(base_dir, f"daily_plan_{date_str}.json"))
        entry_decision = _load(os.path.join(find_dir, f"entry_decision_{date_str}.json"))
        for t in trades:
            sym = t["sym"]
            t["premarket_summary"] = _load(os.path.join(find_dir, f"premarket_summary_{date_str}_{sym}.json"))
            t["macro_strategy"] = _load(os.path.join(base_dir, f"macro_strategy_{sym}.json"))
            if entry_decision:
                t["entry_decision_detail"] = entry_decision.get("decisions", {}).get(sym, {})
            else:
                t["entry_decision_detail"] = {}
        return {
            "date": date_str,
            "prev_date": prev_date,
            "trades": trades,
            "daily_plan": daily_plan,
            "entry_decision": entry_decision,
            "portfolio_snapshot_prev": prev_pos,
            "positions_today": today_pos,
            "trade_source": "trading_history.manual_user_report",
        }
    
    # 检测买入 / 加仓
    for sym, pos in today_pos.items():
        sym_upper = sym.upper()
        
        # 2a. 检查是否是全新买入 (昨日持仓中没有)
        if sym_upper not in prev_pos:
            # 过滤掉 SGOV 这类纯现金管理工具，除非确实需要
            trades.append({
                "sym": sym_upper,
                "action": "BUY",
                "cost": float(pos.get("cost", 0)),
                "shares": int(pos.get("shares", 0)),
                "note": pos.get("note", "新买入"),
                "date": pos.get("date", date_str)
            })
            continue
            
        # 2b. 检查是否有新增分仓 (Tranche) 日期是今日
        # 支持 t1_date, t2_date, t3_date 等
        added_tranche = False
        for t_idx in range(1, 4):
            t_date = pos.get(f"t{t_idx}_date")
            if t_date == date_str:
                trades.append({
                    "sym": sym_upper,
                    "action": f"ADD_T{t_idx}",
                    "cost": float(pos.get(f"t{t_idx}_cost", 0)),
                    "shares": int(pos.get(f"t{t_idx}_shares", 0)),
                    "note": pos.get("note", f"补仓T{t_idx}"),
                    "date": date_str
                })
                added_tranche = True
                break
        if added_tranche:
            continue
            
        # 2c. 通过股数变化对比 (做兜底)
        prev_shares = int(prev_pos[sym_upper].get("shares", 0))
        curr_shares = int(pos.get("shares", 0))
        if curr_shares > prev_shares:
            # 股数增加了，但没标记 tranche_date (或者 tranche_date 已经是今天)
            diff_shares = curr_shares - prev_shares
            # 计算边际成本
            curr_total_cost = float(pos.get("cost", 0)) * curr_shares
            prev_total_cost = float(prev_pos[sym_upper].get("cost", 0)) * prev_shares
            est_cost = round((curr_total_cost - prev_total_cost) / diff_shares, 2) if diff_shares > 0 else float(pos.get("cost", 0))
            trades.append({
                "sym": sym_upper,
                "action": "BUY_ADD",
                "cost": est_cost,
                "shares": diff_shares,
                "note": pos.get("note", "加仓（自动检测）"),
                "date": date_str
            })
            
    # 检测卖出 (昨日有而今日没有，或者今日股数减少了)
    for sym_upper, pos in prev_pos.items():
        if sym_upper not in today_pos:
            # 全清仓
            trades.append({
                "sym": sym_upper,
                "action": "SELL_CLEAR",
                "cost": float(pos.get("cur_price", pos.get("cost", 0))), # 估算卖价
                "shares": int(pos.get("shares", 0)),
                "note": "清仓（自动检测）",
                "date": date_str
            })
        elif int(today_pos[sym_upper].get("shares", 0)) < int(pos.get("shares", 0)):
            # 部分减仓
            prev_shares = int(pos.get("shares", 0))
            curr_shares = int(today_pos[sym_upper].get("shares", 0))
            diff_shares = prev_shares - curr_shares
            trades.append({
                "sym": sym_upper,
                "action": "SELL_PARTIAL",
                "cost": float(today_pos[sym_upper].get("broker_last_price", today_pos[sym_upper].get("cost", 0))),
                "shares": diff_shares,
                "note": "减仓（自动检测）",
                "date": date_str
            })

    # 3. 载入决策审计上下文 (premarket, daily_plan, entry_decision)
    daily_plan = _load(os.path.join(base_dir, f"daily_plan_{date_str}.json"))
    entry_decision = _load(os.path.join(find_dir, f"entry_decision_{date_str}.json"))
    
    # 4. 对今日交易进行补充信息填充
    for t in trades:
        sym = t["sym"]
        # premaket_summary
        t["premarket_summary"] = _load(os.path.join(find_dir, f"premarket_summary_{date_str}_{sym}.json"))
        # macro_strategy
        t["macro_strategy"] = _load(os.path.join(base_dir, f"macro_strategy_{sym}.json"))
        # entry_decision 中该标的的决议
        if entry_decision:
            t["entry_decision_detail"] = entry_decision.get("decisions", {}).get(sym, {})
        else:
            t["entry_decision_detail"] = {}

    return {
        "date": date_str,
        "prev_date": prev_date,
        "trades": trades,
        "daily_plan": daily_plan,
        "entry_decision": entry_decision,
        "portfolio_snapshot_prev": prev_pos,
        "positions_today": today_pos
    }

