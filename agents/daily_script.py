"""
今日剧本管理器 — 全天持久化状态，任何时候都能恢复流程
文件路径：~/stock_team/daily_script_{date}.json
"""
import json, os
from datetime import datetime, timezone, timedelta


def calculate_nodes(sym, date_str=None):
    """
    根据 Livermore 框架自动计算三节点初始建议值。
    节点原则：基于资金行为（机构参考价），不是随机ATR倍数。

    节点1（论点支撑/保护位）：机构建仓参考价，跌破论点开始受压
      = max(VWAP昨日收盘, 近期关键低点)
    节点2（论点怀疑位）：大量筹码换手区下沿，跌破论点动摇
      = 近10日最低收盘价 附近
    节点3（论点突破确认位）：前期高点/关键压力，突破论点被验证
      = 近20日最高价 附近

    返回 {"node1": float, "node2": float, "node3": float, "basis": str}
    """
    import json as _json
    import yfinance as yf
    if date_str is None:
        from datetime import datetime as _dt
        date_str = _dt.now().strftime("%Y-%m-%d")

    try:
        t = yf.Ticker(sym)
        # 拉取近30日日线数据
        h = t.history(period="30d")
        if len(h) < 10:
            return {"node1": None, "node2": None, "node3": None, "basis": "数据不足"}

        cur = float(h["Close"].iloc[-1])

        # 节点3：近20日最高收盘价（前期高点）
        node3 = round(float(h["Close"].tail(20).max()), 2)

        # 节点1：近5日最低收盘价（近期支撑）
        node1 = round(float(h["Close"].tail(5).min()), 2)

        # 节点2：近10日最低收盘价（中期支撑）
        node2 = round(float(h["Close"].tail(10).min()), 2)

        # 确保 node1 < node2 < cur < node3 的基本合理性
        if node1 >= node2:
            node1 = round(node2 * 0.95, 2)
        if node2 >= cur:
            node2 = round(cur * 0.95, 2)
            node1 = round(cur * 0.90, 2)
        if node3 <= cur:
            node3 = round(cur * 1.05, 2)

        # 读取 premarket 数据补充 VWAP 信息
        try:
            pm_path = os.path.join(BASE, f"premarket_analysis_{date_str}.json")
            if os.path.exists(pm_path):
                pm = _json.load(open(pm_path, encoding="utf-8"))
                sym_pm = pm.get("stocks", {}).get(sym, {})
                # 如果盘前价格显著低于node1，调整node1
                pre_price = sym_pm.get("pre_price") or sym_pm.get("prev_close")
                if pre_price and pre_price < node1:
                    node1 = round(pre_price * 0.98, 2)
        except Exception:
            pass

        basis = f"节点1={node1}(近5日低), 节点2={node2}(近10日低), 节点3={node3}(近20日高)"
        return {"node1": node1, "node2": node2, "node3": node3, "basis": basis}

    except Exception as e:
        return {"node1": None, "node2": None, "node3": None, "basis": f"计算失败: {e}"}

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
ET   = timezone(timedelta(hours=-4))

# ── 文件路径 ─────────────────────────────────────────────────────

def _script_path(date_str=None):
    d = date_str or datetime.now(ET).strftime("%Y%m%d")
    return os.path.join(BASE, f"daily_script_{d}.json")


def _empty_structure(date_str=None):
    d = date_str or datetime.now(ET).strftime("%Y%m%d")
    # 显示格式 YYYY-MM-DD
    date_fmt = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return {
        "date": date_fmt,
        "generated_at": None,
        "checkpoints": {
            "node0_done": False,
            "node0_time": None,
            "intraday_update_done": False,
            "intraday_update_time": None,
            "eod_review_done": False,
        },
        "primary_stocks": [],
        "secondary_stocks": [],
        "intraday_focus": [],
        "intraday_updated_at": None,
        "stocks": {},
        "positions_snapshot": {},
        "open_alerts": [],
        "last_updated": None,
    }


# ── 读写 ──────────────────────────────────────────────────────────

def load_script(date_str=None):
    """读取今日剧本，不存在则返回空结构"""
    p = _script_path(date_str)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return _empty_structure(date_str)


def save_script(data, date_str=None):
    """保存剧本"""
    data["last_updated"] = datetime.now(ET).strftime("%H:%M")
    p = _script_path(date_str)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 初始化 ────────────────────────────────────────────────────────

def init_script(date_str=None):
    """
    初始化今日剧本（Node 0 运行时调用）。
    从 config/positions.json + config/daily_focus.json +
    learning/poll_state_{date}.json 读取初始数据。
    """
    data = load_script(date_str)
    now_str = datetime.now(ET).strftime("%H:%M")

    # ── 持仓快照 ─────────────────────────────────────────────────
    pos_path = os.path.join(BASE, "config", "positions.json")
    positions_snapshot = {}
    pos_syms = []
    if os.path.exists(pos_path):
        try:
            pdata = json.load(open(pos_path, encoding="utf-8"))
            for sym, info in pdata.get("positions", {}).items():
                positions_snapshot[sym] = {
                    "cost":         float(info.get("t1_cost") or info.get("cost") or 0),
                    "shares":       int(info.get("t1_shares") or info.get("shares") or 0),
                    "thesis":       info.get("thesis", ""),
                    "thesis_status": info.get("thesis_status", "intact"),
                    "position_type": info.get("position_type", "thesis"),
                }
                pos_syms.append(sym)
        except Exception:
            pass

    # ── 关注标的 ─────────────────────────────────────────────────
    focus_path = os.path.join(BASE, "config", "daily_focus.json")
    focus_stocks = []
    if os.path.exists(focus_path):
        try:
            fdata = json.load(open(focus_path, encoding="utf-8"))
            focus_stocks = fdata.get("focus_stocks", [])
        except Exception:
            pass

    # 主关注 = 持仓底层；次关注 = daily_focus 排除持仓 + 信息驱动筛选
    lev_path = os.path.join(BASE, "config", "leveraged_pairs.json")
    lev_etfs = set()
    if os.path.exists(lev_path):
        try:
            lev_cfg = json.load(open(lev_path, encoding="utf-8"))
            lev_etfs = {v["sym"] for v in lev_cfg.values() if isinstance(v, dict)}
        except Exception:
            pass

    exclude = {"BABA", "PONY"} | lev_etfs
    primary = [s for s in pos_syms if s not in exclude]
    # 次关注：daily_focus 配置 + 信息驱动筛选（catalyst_strength >= 2）
    focus_secondary = [s for s in focus_stocks if s not in pos_syms]
    try:
        from agents.candidate_scanner import scan_information_driven
        info_candidates = scan_information_driven(date_fmt)
        info_syms = [c["sym"] for c in info_candidates
                     if c["sym"] not in primary and c["sym"] not in focus_secondary][:5]
    except Exception:
        info_syms = []
    secondary = list(dict.fromkeys(focus_secondary + info_syms))

    # 盘中关注：开盘后更新，初始为空（intraday_focus 字段已在 _empty_structure 中初始化）

    # ── poll_state 论点状态 ───────────────────────────────────────
    d = date_str or datetime.now(ET).strftime("%Y%m%d")
    date_fmt = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    poll_state_path = os.path.join(BASE, "learning", f"poll_state_{date_fmt}.json")
    poll_states = {}
    if os.path.exists(poll_state_path):
        try:
            ps = json.load(open(poll_state_path, encoding="utf-8"))
            poll_states = ps.get("symbols", {})
        except Exception:
            pass

    # ── stocks 初始结构 ──────────────────────────────────────────
    all_syms = list(dict.fromkeys(primary + secondary))
    stocks = {}
    for sym in all_syms:
        ps_sym = poll_states.get(sym, {})
        # 自动计算三节点
        nodes = calculate_nodes(sym, date_fmt)
        stocks[sym] = {
            "thesis_status":  positions_snapshot.get(sym, {}).get("thesis_status", "intact"),
            "node_state":     ps_sym.get("node_state", "B"),
            "gate_status":    ps_sym.get("gate_status", ""),
            "last_price":     ps_sym.get("last_price"),
            "last_rs":        ps_sym.get("last_rs"),
            "node1":          nodes["node1"],
            "node2":          nodes["node2"],
            "node3":          nodes["node3"],
            "node_basis":     nodes["basis"],
        }

    # ── 写回 ────────────────────────────────────────────────────
    data.update({
        "date":               date_fmt,
        "generated_at":       now_str,
        "positions_snapshot": positions_snapshot,
        "primary_stocks":     primary,
        "secondary_stocks":   secondary,
        "stocks":             stocks,
    })
    save_script(data, date_str)
    return data


# ── 检查点 ────────────────────────────────────────────────────────

def mark_checkpoint(name: str, date_str=None):
    """标记检查点完成 (name: node0 / intraday_update / eod_review)"""
    data = load_script(date_str)
    now_str = datetime.now(ET).strftime("%H:%M")
    cp = data.setdefault("checkpoints", {})
    if name == "node0":
        cp["node0_done"] = True
        cp["node0_time"] = now_str
    elif name == "intraday_update":
        cp["intraday_update_done"] = True
        cp["intraday_update_time"] = now_str
    elif name == "eod_review":
        cp["eod_review_done"] = True
    save_script(data, date_str)


# ── 单只股票状态更新 ──────────────────────────────────────────────

def update_stock_state(sym: str, updates: dict, date_str=None):
    """更新单只股票的节点状态（poll.py 每轮调用）"""
    data = load_script(date_str)
    stocks = data.setdefault("stocks", {})
    sym_data = stocks.setdefault(sym, {})
    sym_data.update(updates)
    save_script(data, date_str)


# ── 今日状态摘要 ──────────────────────────────────────────────────

def get_status_summary(date_str=None) -> str:
    """生成今日状态摘要字符串"""
    data = load_script(date_str)
    now_str = datetime.now(ET).strftime("%H:%M")
    date_disp = data.get("date", "?")

    # 检查点
    cp = data.get("checkpoints", {})
    cp0 = "✅" if cp.get("node0_done") else "⬜"
    cp1 = "✅" if cp.get("intraday_update_done") else "⬜"
    cp2 = "✅" if cp.get("eod_review_done") else "⬜"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📋 今日剧本 {date_disp}  {now_str} ET",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"检查点: {cp0} Node0  {cp1} 盘中更新  {cp2} 收盘评估",
        "",
    ]

    # 持仓实时
    pos_snap = data.get("positions_snapshot", {})
    stocks   = data.get("stocks", {})
    if pos_snap:
        lines.append("【持仓实时】")
        # 批量获取价格
        prices = {}
        if pos_snap:
            try:
                import yfinance as yf
                tickers = yf.download(
                    list(pos_snap.keys()),
                    period="1d", progress=False, auto_adjust=True
                )
                close = tickers.get("Close") if hasattr(tickers, "get") else None
                if close is not None:
                    for sym in pos_snap:
                        try:
                            prices[sym] = float(close[sym].dropna().iloc[-1])
                        except Exception:
                            pass
            except Exception:
                pass

        for sym, info in pos_snap.items():
            cost   = info.get("cost", 0)
            thesis = info.get("thesis_status", "intact")
            node   = stocks.get(sym, {}).get("node_state", "B")
            cur    = prices.get(sym)
            if cur and cost:
                pnl = (cur - cost) / cost * 100
                pnl_str = f"{pnl:+.1f}%"
            else:
                pnl_str = "价格获取中"
            lines.append(f"  {sym}: {pnl_str}  论点{thesis}  节点{node}")
    else:
        lines.append("【持仓实时】（尚未初始化，请先运行晨间准备）")

    lines.append("")

    # 关注
    primary   = data.get("primary_stocks", [])
    secondary = data.get("secondary_stocks", [])
    intraday  = data.get("intraday_focus", [])
    lines.append(f"【今日主关注】{' '.join(primary) if primary else '（未设置）'}")
    lines.append(f"【今日次关注】{' '.join(secondary) if secondary else '（未设置）'}")
    if intraday:
        lines.append(f"【盘中关注】{' '.join(intraday)}")
    else:
        lines.append("【盘中关注】待10:00更新")

    lines.append("")

    # 未处理信号
    alerts = data.get("open_alerts", [])
    if alerts:
        lines.append(f"【未处理信号】{len(alerts)} 条：")
        for a in alerts[:3]:
            lines.append(f"  • {a}")
    else:
        lines.append("【未处理信号】无")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 下一步建议
    if not cp.get("node0_done"):
        next_step = "建议：说「早上好」运行晨间准备（生成今日剧本）"
    elif not cp.get("intraday_update_done"):
        next_step = "建议：开盘30分钟后说「更新盘中关注」锁定今日重点标的"
    elif not cp.get("eod_review_done"):
        next_step = "建议：收盘后说「收盘复盘」完成今日评估"
    else:
        next_step = "今日三个检查点均已完成 ✅"

    lines.append(f"下一步: {next_step}")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(get_status_summary())
    elif cmd == "init":
        init_script()
        print("今日剧本已初始化")
    elif cmd == "checkpoint" and len(sys.argv) > 2:
        mark_checkpoint(sys.argv[2])
        print(f"检查点 {sys.argv[2]} 已标记")
    else:
        print("用法: daily_script.py [status|init|checkpoint <name>]")
