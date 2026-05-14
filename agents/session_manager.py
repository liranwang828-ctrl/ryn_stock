"""
session_manager.py — 工作流编排器
节点状态 / A轨道提醒队列 / 自然语言文本路由

公开接口：
  advance_node(node)           → str
  get_status()                 → dict
  add_symbol(sym)              → None
  push_alert(type,sym,msg,data)→ None
  drain_alerts()               → list
  handle_text(text,date_str)   → str | None
"""
import sys, json, os, re, subprocess
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import atomic_write_json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NODE_NAMES = {
    1: "盘前(9:00-9:25)",
    2: "开盘观察(9:30-10:00)",
    3: "盘中主动期(10:00+)",
    4: "入场执行",
    5: "持仓管理",
    6: "收盘复盘",
}

def _state_path(date_str=None):
    d = date_str or datetime.now().strftime("%Y%m%d")
    return os.path.join(BASE, f"session_state_{d}.json")

def _load_state(date_str=None):
    p = _state_path(date_str)
    if os.path.exists(p):
        return json.load(open(p))
    return {"node": 1, "active_symbols": [], "alert_queue": []}

def _save_state(state, date_str=None):
    p = _state_path(date_str)
    atomic_write_json(state, p, indent=2)

def advance_node(node: int, date_str=None) -> str:
    if node < 1 or node > 6:
        raise ValueError(f"node must be 1-6, got {node}")
    state = _load_state(date_str)
    state["node"] = node
    _save_state(state, date_str)
    return f"节点推进 → {NODE_NAMES[node]}"

def get_status(date_str=None) -> dict:
    state = _load_state(date_str)
    return {
        "node":           state["node"],
        "node_name":      NODE_NAMES[state["node"]],
        "active_symbols": state.get("active_symbols", []),
        "pending_alerts": len(state.get("alert_queue", [])),
    }

def add_symbol(sym: str, date_str=None):
    state = _load_state(date_str)
    syms = state.setdefault("active_symbols", [])
    if sym not in syms:
        syms.append(sym)
    _save_state(state, date_str)


BOARD_FILE = "discussion_board.jsonl"

def push_alert(type_: str, symbol: str, message: str, data: dict,
               date_str=None):
    now = datetime.now(timezone.utc)
    entry = {
        "time":    now.strftime("%H:%M"),
        "type":    type_,
        "symbol":  symbol,
        "message": message,
        "data":    data,
    }
    # 1. 写入 discussion_board.jsonl（永久日志）
    board = os.path.join(BASE, BOARD_FILE)
    with open(board, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # 2. 加入待读队列
    state = _load_state(date_str)
    state.setdefault("alert_queue", []).append(entry)
    _save_state(state, date_str)


def drain_alerts(date_str=None) -> list:
    """返回所有待读提醒并清空队列"""
    state = _load_state(date_str)
    alerts = state.get("alert_queue", [])
    state["alert_queue"] = []
    _save_state(state, date_str)
    return alerts


def format_alert(alert: dict) -> str:
    """格式化单条提醒供对话显示"""
    t, msg = alert["time"], alert["message"]
    return f"[{t}] {msg}"


# 交易关键词检测
_TRADE_PATTERN = re.compile(
    r'^(买了|卖了|止损了|止盈了|减仓了|加仓了)\s', re.IGNORECASE
)

try:
    from agents.entry_guard import handle_trade_text
except ImportError:
    try:
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.dirname(__file__))
        from entry_guard import handle_trade_text
    except ImportError:
        handle_trade_text = None


def handle_text(text: str, date_str=None):
    """
    路由用户文本：
    - 以交易动词开头 → 调用 entry_guard.handle_trade_text
    - 其他 → 返回 None（正常对话）
    """
    if _TRADE_PATTERN.match(text.strip()):
        if handle_trade_text:
            return handle_trade_text(text.strip(), date_str)
        return "⚠️ entry_guard 模块未加载，请检查安装"
    return None


PYTHON     = sys.executable
AGENTS_DIR = os.path.join(BASE, "agents")

NODE_NEXT_PROMPTS = {
    1: "📋 请告诉我今天关注哪些标的（如：MRVL AAOI LITE），确认后自动生成今日计划",
    2: "🟢 计划生成完成。9:30 开盘进入观察期，回复「是」启动轮询",
    3: ("🔄 双轨并行已启动。\n"
        "  A轨道：每2分钟自动监控，信号/止损/场景变化时推送提醒\n"
        "  B轨道：可随时向我提问或报告交易（「买了 MRVL $178 20股」）\n"
        "  收盘时说「收盘复盘」进入节点6"),
    4: "📍 入场守卫已显示。记录仓位后进入持仓管理",
    5: "📡 持仓监控中，A轨道持续运行",
    6: "✅ 今日交易结束",
}


def run_node(node: int, symbols=None, date_str=None) -> str:
    """
    执行当前节点的自动脚本，返回输出摘要 + 下一步提示。
    节点转换由用户确认后调用。
    """
    state = _load_state(date_str)
    if symbols:
        state["active_symbols"] = list(symbols)
    active_syms = state.get("active_symbols", [])
    state["node"] = node
    _save_state(state, date_str)

    sep = "=" * 50
    lines = [f"\n{sep}", f"节点{node}: {NODE_NAMES[node]}", sep]

    def _get_out(r, fallback="（无输出）", maxlen=3000):
        raw = r.stdout if isinstance(r.stdout, str) and r.stdout else (
              r.stderr if isinstance(r.stderr, str) and r.stderr else fallback)
        return raw[-maxlen:] if len(raw) > maxlen else raw

    if node == 1:
        if active_syms:
            script = os.path.join(AGENTS_DIR, "premarket.py")
            r = subprocess.run(
                [PYTHON, script] + active_syms,
                cwd=BASE, capture_output=True, text=True, timeout=120
            )
            lines.append(_get_out(r))
        else:
            lines.append("（未指定标的，等待用户指定关注标的）")

    elif node == 2:
        if not active_syms:
            lines.append("⚠️ 未设置关注标的，请先告知标的后再进入节点2")
        else:
            script = os.path.join(AGENTS_DIR, "daily_plan.py")
            r = subprocess.run(
                [PYTHON, script, "generate"] + active_syms,
                cwd=BASE, capture_output=True, text=True, timeout=120
            )
            lines.append(_get_out(r))

    elif node == 3:
        if active_syms:
            # 立即运行一次 poll，显示当前市况快照
            poll_script = os.path.join(AGENTS_DIR, "poll.py")
            r = subprocess.run(
                [PYTHON, poll_script] + active_syms + ["--session"],
                cwd=BASE, capture_output=True, text=True, timeout=60
            )
            lines.append(_get_out(r, fallback="（poll 无输出）", maxlen=2000))
            lines.append(f"\n💡 持续轮询命令: /loop 2m poll.py {' '.join(active_syms)} --session")
        else:
            lines.append("⚠️ 未设置标的，无法启动 poll")

    elif node == 6:
        script = os.path.join(AGENTS_DIR, "postmarket_review.py")
        if os.path.exists(script):
            r = subprocess.run(
                [PYTHON, script],
                cwd=BASE, capture_output=True, text=True, timeout=180
            )
            lines.append(_get_out(r))
        else:
            lines.append("（postmarket_review.py 未找到，请手动复盘）")

    else:
        lines.append(f"节点{node} 无自动脚本，等待用户操作")

    lines.append("")
    lines.append(NODE_NEXT_PROMPTS.get(node, ""))
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser(description="Session Manager CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status")

    run_p = sub.add_parser("run")
    run_p.add_argument("node", type=int)
    run_p.add_argument("symbols", nargs="*")

    adv = sub.add_parser("advance")
    adv.add_argument("node", type=int)

    addsym = sub.add_parser("add")
    addsym.add_argument("symbol")

    sub.add_parser("drain")

    txt = sub.add_parser("handle")
    txt.add_argument("text")

    args = parser.parse_args()
    if args.cmd == "status":
        s = get_status()
        print(f"节点{s['node']}: {s['node_name']}")
        print(f"关注标的: {', '.join(s['active_symbols']) or '（无）'}")
        print(f"待读提醒: {s['pending_alerts']} 条")
    elif args.cmd == "advance":
        print(advance_node(args.node))
    elif args.cmd == "add":
        add_symbol(args.symbol)
        print(f"已加入: {args.symbol}")
    elif args.cmd == "drain":
        alerts = drain_alerts()
        if not alerts:
            print("（无待读提醒）")
        for a in alerts:
            print(format_alert(a))
    elif args.cmd == "handle":
        result = handle_text(args.text)
        if result:
            print(result)
        else:
            print("（非交易文本，跳过路由）")
    elif args.cmd == "run":
        syms = args.symbols if args.symbols else None
        print(run_node(args.node, symbols=syms))
    else:
        parser.print_help()
