"""
盘中快照模块 — intraday_snapshot.py
每次 poll 追加一条 JSONL 记录到 intraday_snapshot_{date}_{sym}.jsonl。
所有函数均为纯函数或纯 I/O，易于单元测试。

核心入口：write_snapshot_entry(sym, date, price_now_dict, ...) → None
"""
import json, os
from datetime import datetime, timezone, timedelta

BASE      = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR  = os.path.join(BASE, "findings")
POLL_STATE_TPL = os.path.join(BASE, "learning", "poll_state_{}.json")

RED_EVENTS    = {"hard_stop_breach", "entry_go", "vix_spike"}
YELLOW_EVENTS = {"gate_flip", "consensus_shift", "thesis_breach"}
COOLDOWN_MINUTES = 10


def compute_dist_fields(price: float, nodes: dict) -> dict:
    """
    计算当前价格距各节点的距离百分比。
    分母统一用 price，节点为 None 时对应字段返回 None。
    """
    def _dist(ref):
        if ref is None or price == 0:
            return None
        return round((ref - price) / price * 100, 2)

    eb  = nodes.get("entry_base")
    hs  = nodes.get("hard_stop")
    tgt = nodes.get("target")
    fa  = nodes.get("flex_add")
    fr  = nodes.get("flex_reduce")

    return {
        "dist_to_entry_pct":       None if eb is None else round((price - eb)  / price * 100, 2),
        "dist_to_stop_pct":        None if hs is None else round((price - hs)  / price * 100, 2),
        "dist_to_target_pct":      _dist(tgt),
        "dist_to_flex_add_pct":    None if fa is None else round((price - fa)  / price * 100, 2),
        "dist_to_flex_reduce_pct": _dist(fr),
    }


def compute_thesis_signal(
    price: float, hard_stop: float | None, dist_to_stop_pct: float | None,
    thesis_status: str, falsification_count: int,
) -> str:
    """
    纯规则推导论点信号（优先级从高到低，第一条命中即停止）。
    返回: "breach" | "warning" | "intact"
    """
    if hard_stop is not None and price <= hard_stop:
        return "breach"
    if thesis_status == "broken":
        return "breach"
    if thesis_status == "weakening" and dist_to_stop_pct is not None and dist_to_stop_pct < 3.0:
        return "breach"   # spec 规则 3：weakening + 接近止损 → breach
    if thesis_status == "weakening":
        return "warning"
    if dist_to_stop_pct is not None and dist_to_stop_pct < 3.0:
        return "warning"
    if falsification_count > 0 and dist_to_stop_pct is not None and dist_to_stop_pct < 5.0:
        return "warning"
    return "intact"


def compute_entry_go_status(
    session_min: int,
    post_open_calibrated: bool,
    entry_go: bool | None,
) -> str:
    """
    纯规则推导入场窗口状态（优先级从高到低）。
    返回: "expired" | "go" | "abort" | "pending"
    """
    if session_min >= 60:
        return "expired"
    if not post_open_calibrated:
        return "pending"
    if entry_go is True:
        return "go"
    if entry_go is False:
        return "abort"
    return "pending"


def get_effective_nodes(summary: dict) -> dict:
    """
    从 premarket_summary 提取当前生效的价格节点。
    post_open_adj 中非 null 的 *_adj 值优先覆盖原始值。
    """
    entry = summary.get("entry") or {}
    exit_ = summary.get("exit") or {}
    adj   = summary.get("post_open_adj") or {}

    def _pick(adj_key, *fallbacks):
        v = adj.get(adj_key)
        if v is not None:
            return v
        for fb_key in fallbacks:
            val = exit_.get(fb_key)
            if val is not None:
                return val
            val = entry.get(fb_key)
            if val is not None:
                return val
        return None

    return {
        "entry_base":  _pick("entry_base_adj",  "entry_base"),
        "hard_stop":   _pick("hard_stop_adj",   "hard_stop",    "stop_loss"),
        "target":      _pick("target_adj",       "target_price"),
        "flex_add":    _pick("flex_add_adj",     "flex_add_level"),
        "flex_reduce": _pick("flex_reduce_adj",  "flex_reduce_level"),
    }


def build_node_snapshot(nodes: dict) -> dict:
    """复制节点快照（用于 JSONL 中的 node_snapshot 字段）"""
    return {
        "entry_base":  nodes.get("entry_base"),
        "hard_stop":   nodes.get("hard_stop"),
        "target":      nodes.get("target"),
        "flex_add":    nodes.get("flex_add"),
        "flex_reduce": nodes.get("flex_reduce"),
    }


def build_plan_vs_now(
    price: float,
    summary: dict,
    session_min: int,
    post_open_calibrated: bool,
) -> dict:
    """构建 plan_vs_now 字段（纯规则，不依赖 LLM）"""
    nodes  = get_effective_nodes(summary)
    thesis = summary.get("thesis") or {}
    adj    = summary.get("post_open_adj") or {}

    dist   = compute_dist_fields(price, nodes)
    thesis_status       = thesis.get("status", "intact")
    falsification_count = len(thesis.get("today_falsification", []))

    thesis_sig = compute_thesis_signal(
        price=price,
        hard_stop=nodes.get("hard_stop"),
        dist_to_stop_pct=dist.get("dist_to_stop_pct"),
        thesis_status=thesis_status,
        falsification_count=falsification_count,
    )

    entry_go_val = adj.get("entry_go") if adj else None
    ego_status = compute_entry_go_status(
        session_min=session_min,
        post_open_calibrated=post_open_calibrated,
        entry_go=entry_go_val,
    )

    entry = summary.get("entry") or {}
    entry_conditions_total = len(entry.get("entry_conditions", []))

    return {
        **dist,
        "entry_conditions_met":   0,
        "entry_conditions_total": entry_conditions_total,
        "scene_match":            None,
        "thesis_signal":          thesis_sig,
        "entry_go_status":        ego_status,
    }


def detect_event(
    price: float, hard_stop: float | None,
    thesis_signal: str, prev_thesis_signal: str | None,
    gate_status: str, prev_gate_status: str | None,
    master_consensus: str | None, prev_master_consensus: str | None,
    session_min: int, entry_go_status: str, prev_entry_go_status: str | None,
    vix_spike: bool,
) -> str | None:
    """
    检测本轮是否触发事件（优先级：🔴 > 🟡）。
    返回事件 key 或 None。
    entry_go 自然受限于 post_open_adj 校准逻辑（仅 10:00 附近触发）。
    """
    # 🔴 即时事件
    if hard_stop is not None and price <= hard_stop:
        return "hard_stop_breach"
    if entry_go_status == "go" and prev_entry_go_status != "go":
        return "entry_go"
    if vix_spike:
        return "vix_spike"
    # 🟡 冷却事件（per-sym 10分钟冷却）
    if thesis_signal == "breach" and prev_thesis_signal is not None and prev_thesis_signal != "breach":
        return "thesis_breach"
    if gate_status != prev_gate_status and prev_gate_status is not None:
        return "gate_flip"
    if master_consensus != prev_master_consensus and prev_master_consensus is not None:
        return "consensus_shift"
    return None


def in_cooldown(sym: str, poll_state: dict) -> bool:
    """检查该标的是否在冷却期内"""
    cool = poll_state.get("symbols", {}).get(sym, {}).get("cooldown_until")
    if not cool:
        return False
    try:
        return datetime.now().strftime("%H:%M:%S") < cool
    except Exception:
        return False


def set_cooldown(sym: str, poll_state_path: str) -> str:
    """设置冷却到期时间（当前时间 + 10 分钟），返回 cooldown_until 字符串"""
    until = (datetime.now() + timedelta(minutes=COOLDOWN_MINUTES)).strftime("%H:%M:%S")
    try:
        with open(poll_state_path, encoding="utf-8") as f:
            state = json.load(f)
        state.setdefault("symbols", {}).setdefault(sym, {})["cooldown_until"] = until
        with open(poll_state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return until


def append_snapshot(sym: str, date: str, record: dict,
                    find_dir: str = FIND_DIR) -> str:
    """追加一条 JSONL 记录，并写入 SQLite 高性能数据库"""
    os.makedirs(find_dir, exist_ok=True)
    fname = f"intraday_snapshot_{date}_{sym.upper()}.jsonl"
    path  = os.path.join(find_dir, fname)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
    # 双写进入 SQLite WAL 数据库，提升盘中并发读取稳定性
    try:
        from agents.data_hub import write_snapshot_db
        write_snapshot_db(record)
    except Exception:
        pass
        
    return path


def read_latest_snapshot(sym: str, date: str,
                          find_dir: str = FIND_DIR) -> dict | None:
    """读取最新一条 JSONL 记录，文件不存在时返回 None"""
    fname = f"intraday_snapshot_{date}_{sym.upper()}.jsonl"
    path  = os.path.join(find_dir, fname)
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


def update_poll_state(
    sym: str,
    plan_vs_now: dict,
    last_action_now: str | None,
    last_event: str | None,
    last_event_at: str | None,
    cooldown_until: str | None,
    poll_state_path: str,
    master_consensus: str | None = None,
) -> None:
    """将本轮关键字段合并写入 poll_state（只追加，不覆盖已有字段）"""
    try:
        with open(poll_state_path, encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {"symbols": {}}

    sym_state = state.setdefault("symbols", {}).setdefault(sym, {})
    sym_state["plan_vs_now"] = {k: plan_vs_now.get(k) for k in
                                 ("entry_conditions_met", "entry_conditions_total",
                                  "dist_to_stop_pct", "dist_to_target_pct",
                                  "thesis_signal", "entry_go_status")}
    sym_state["last_action_now"]  = last_action_now
    sym_state["last_event"]       = last_event
    sym_state["last_event_at"]    = last_event_at
    sym_state["cooldown_until"]   = cooldown_until
    if master_consensus is not None:
        sym_state["master_consensus"] = master_consensus

    try:
        with open(poll_state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def write_snapshot_entry(
    sym: str,
    date: str,
    price_now: dict,
    premarket_summary: dict,
    session_min: int,
    post_open_calibrated: bool,
    prev_poll_state: dict,
    vix_spike: bool = False,
    find_dir: str = FIND_DIR,
    poll_state_path: str | None = None,
) -> None:
    """
    主入口：由 poll.py 每轮末尾调用。
    构建本轮 JSONL 记录并追加，同时更新 poll_state。
    """
    if poll_state_path is None:
        poll_state_path = POLL_STATE_TPL.format(date)

    pvn = build_plan_vs_now(
        price=price_now.get("price", 0.0),
        summary=premarket_summary,
        session_min=session_min,
        post_open_calibrated=post_open_calibrated,
    )

    prev_sym = prev_poll_state.get("symbols", {}).get(sym, {})
    prev_pvn = prev_sym.get("plan_vs_now", {})
    cur_consensus = price_now.get("master_consensus")

    event = detect_event(
        price=price_now.get("price", 0.0),
        hard_stop=get_effective_nodes(premarket_summary).get("hard_stop"),
        thesis_signal=pvn["thesis_signal"],
        prev_thesis_signal=prev_pvn.get("thesis_signal"),
        gate_status=price_now.get("gate_status", ""),
        prev_gate_status=prev_sym.get("gate_status"),
        master_consensus=cur_consensus,
        prev_master_consensus=prev_sym.get("master_consensus"),
        session_min=session_min,
        entry_go_status=pvn["entry_go_status"],
        prev_entry_go_status=prev_pvn.get("entry_go_status"),
        vix_spike=vix_spike,
    )

    is_red    = event in RED_EVENTS
    on_cool   = not is_red and in_cooldown(sym, prev_poll_state)
    llm_triggered = event is not None and not on_cool
    cooldown_until = None
    if llm_triggered and event in YELLOW_EVENTS:
        cooldown_until = set_cooldown(sym, poll_state_path)

    ts_str = datetime.now().strftime("%H:%M:%S")
    nodes  = get_effective_nodes(premarket_summary)

    # ── 触发盘中事件大模型智能分析 ──────────────────────────────────────
    action_now = None
    if llm_triggered:
        try:
            from agents.llm_client import LLMClient
            client = LLMClient()
            if client.is_configured():
                # 读取当前的宏观背景数据作为底座
                macro_info = {}
                macro_path = os.path.join(BASE, "findings", "macro.json")
                if os.path.exists(macro_path):
                    try:
                        with open(macro_path, encoding="utf-8") as f:
                            macro_info = json.load(f)
                    except Exception:
                        pass
                
                system_prompt = (
                    "You are the expert Chief Investment Officer (CIO) of a professional trading desk. "
                    "You monitor intraday stock events and must output a JSON action directive.\n"
                    "Your JSON must strictly match this format:\n"
                    "{\n"
                    "  \"conclusion\": \"<short action in Chinese, e.g., '减仓 20%', '强行止损出场', '可Flex加仓', '继续观望'>\",\n"
                    "  \"urgency\": \"<'immediate' or 'normal'>\",\n"
                    "  \"note\": \"<detailed professional rationale in Chinese explaining the tactical action, max 3 sentences>\"\n"
                    "}"
                )
                
                prompt = (
                    f"An intraday event has been triggered on stock {sym.upper()}.\n"
                    f"Event Triggered: {event}\n"
                    f"Current Price: ${price_now.get('price', 0.0)}\n"
                    f"Daily Change: {price_now.get('chg_pct', 0.0)}%\n"
                    f"VWAP Distance: {price_now.get('vwap_dist_pct', 0.0)}%\n"
                    f"RSI (5m): {price_now.get('rsi14_5m', 'N/A')}\n"
                    f"Volume Ratio: {price_now.get('vol_ratio', 'N/A')}\n"
                    f"Today's Macro Environment:\n"
                    f"VIX: {macro_info.get('vix', 'N/A')}\n"
                    f"VIX Spike Status: {vix_spike}\n"
                    f"SPY Change: {macro_info.get('spy_chg', 'N/A')}%\n"
                    f"QQQ (5m) Change: {macro_info.get('qqq_5m', 'N/A')}%\n"
                    f"Master Consensus Score: {cur_consensus}\n"
                    f"Technical Nodes:\n"
                    f"Entry Base: ${nodes.get('entry_base')}\n"
                    f"Hard Stop: ${nodes.get('hard_stop')}\n"
                    f"Target: ${nodes.get('target')}\n"
                    f"Flex Add Price: ${nodes.get('flex_add')}\n"
                    f"Flex Reduce Price: ${nodes.get('flex_reduce')}\n\n"
                    f"Please analyze this situation and provide the JSON action directive in Chinese."
                )
                
                llm_response = client.call_llm(prompt=prompt, system_prompt=system_prompt, json_mode=True)
                action_now = json.loads(llm_response)
        except Exception as e:
            # 优雅降级，防止交易轮询因为网络或API报错而中断
            action_now = {
                "conclusion": "事件触发评估",
                "urgency": "immediate" if is_red else "normal",
                "note": f"系统触发了 {event} 大模型评估，但调用时出现异常: {str(e)}"
            }

    record = {
        "ts": ts_str,
        "meta": {
            "date":                 date,
            "sym":                  sym.upper(),
            "session_min":          session_min,
            "llm_triggered":        llm_triggered,
            "llm_trigger":          event if llm_triggered else None,
            "cooldown_until":       cooldown_until,
            "post_open_calibrated": post_open_calibrated,
        },
        "price_now":     price_now,
        "plan_vs_now":   pvn,
        "node_snapshot": build_node_snapshot(nodes),
        "action_now":    action_now,
    }

    append_snapshot(sym, date, record, find_dir=find_dir)

    update_poll_state(
        sym=sym,
        plan_vs_now=pvn,
        last_action_now=json.dumps(action_now, ensure_ascii=False) if action_now else None,
        last_event=event if llm_triggered else None,
        last_event_at=ts_str if llm_triggered else None,
        cooldown_until=cooldown_until,
        poll_state_path=poll_state_path,
        master_consensus=cur_consensus,
    )
