"""
交易意图识别层 (Trading Intent Translator)
任何自然语言 → 意图分类 → 系统动作

用法:
  from agents.translator import translate
  result = translate("早上好，今天想盯MRVL和ANET")

不需要记命令，直说就行。
"""
import re, os, json, subprocess
from datetime import datetime, timezone, timedelta

BASE   = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
import sys; PYTHON = sys.executable
AGENTS = os.path.join(BASE, "agents")
ET     = timezone(timedelta(hours=-4))

# ── 意图规则表 ─────────────────────────────────────────────────
# 每条规则: (pattern, intent, extractor_fn)
# extractor_fn(match, text) → dict of params

def _extract_syms(text):
    """从文本中提取股票代码"""
    raw = re.findall(r'\b([A-Z]{2,5})\b', text)
    stop = {"ET","AM","PM","OK","VS","AI","US","CIO","RSI","ATR","VIX","SPY","QQQ",
            "VCP","FCF","OCF","ROE","EPS","IPO","ETF","GDP","FED","BTC","NFP"}
    return [s for s in raw if s not in stop]

INTENT_RULES = [
    # ── 晨间流程 ────────────────────────────────────────────────
    (r"(早上好|早安|开工|开始今天|今天开始|morning|晨间|起来了|来了|上线了)",
     "morning", lambda m, t: {}),

    # ── 设置关注标的 ─────────────────────────────────────────────
    (r"(今天看|今天盯|今天做|关注|添加标的|加入|今日标的).{0,30}([A-Z]{2,5})",
     "set_symbols", lambda m, t: {"syms": _extract_syms(t)}),

    # ── 开盘/启动监控 ────────────────────────────────────────────
    (r"(开盘了|9[:：]30|开始监控|启动监控|开始盯|轮询|开始盘中|进入盘中)",
     "start_poll", lambda m, t: {"syms": _extract_syms(t)}),

    # ── 盘前分析 ─────────────────────────────────────────────────
    (r"(盘前分析|盘前看看|看看盘前|分析一下|帮我看看).{0,20}([A-Z]{2,5})?",
     "premarket", lambda m, t: {"syms": _extract_syms(t)}),

    # ── CIO 全量分析 ─────────────────────────────────────────────
    (r"(全量分析|深度分析|CIO|大师看看|让大师分析).{0,20}([A-Z]{2,5})",
     "cio", lambda m, t: {"syms": _extract_syms(t)}),

    # ── 候选池扫描 ───────────────────────────────────────────────
    (r"(有什么看的|今天有什么机会|扫一下|候选池|扫描标的)",
     "scan", lambda m, t: {}),

    # ── 组合风险/持仓状态 ────────────────────────────────────────
    (r"(看看持仓|持仓状态|组合风险|今天盈亏|涨了多少|亏了多少|风险快照)",
     "portfolio", lambda m, t: {}),

    # ── 买入记录（触发 quick_mode）─────────────────────────────
    # 排除带价格的完整交易记录（那类由 entry_guard 处理）
    (r"(买了|买入了|成交了|入场了|刚买)(?!\s+[A-Z]{2,5}\s+\$\d).{0,20}([A-Z]{2,5})",
     "buy_quick", lambda m, t: {"syms": _extract_syms(t)}),

    # ── 新建仓位（触发 planning_mode）──────────────────────────
    (r"(新建仓位|建仓|我要买|准备买|想买).{0,20}([A-Z]{2,5})",
     "new_position", lambda m, t: {"syms": _extract_syms(t)}),

    # ── 收盘/收市 ────────────────────────────────────────────────
    (r"(收盘了|收市了|今天结束|下班了|收工|盘后|盘后记录)",
     "close", lambda m, t: {}),

    # ── 止损/止盈提醒 ────────────────────────────────────────────
    (r"(止损设|止盈设|提醒我|价格到|跌到|涨到).{0,30}(\$?\d+)",
     "alert_price", lambda m, t: {"syms": _extract_syms(t),
                                   "price": re.search(r'\$?(\d+\.?\d*)', t).group(1) if re.search(r'\$?(\d+\.?\d*)', t) else ""}),

    # ── 查看新闻/消息 ────────────────────────────────────────────
    (r"(有什么消息|最新新闻|为什么跌|为什么涨|什么原因).{0,20}([A-Z]{2,5})?",
     "news", lambda m, t: {"syms": _extract_syms(t)}),
]

# ── 编译规则 ────────────────────────────────────────────────────
_COMPILED = [(re.compile(pat, re.IGNORECASE), intent, fn)
             for pat, intent, fn in INTENT_RULES]


def _run(script, *args, timeout=300):
    r = subprocess.run(
        [PYTHON, os.path.join(AGENTS, script)] + list(args),
        cwd=BASE, capture_output=True, text=True, timeout=timeout
    )
    out = (r.stdout or "") + (r.stderr or "")
    return out[-4000:] if len(out) > 4000 else out


def translate(text: str) -> tuple[str, str]:
    """
    解析自然语言意图，返回 (intent, result_text)
    intent: 意图名称，用于上层决策
    result_text: 执行结果或空字符串（空=无法识别，走正常对话）
    """
    for pattern, intent, extractor in _COMPILED:
        m = pattern.search(text)
        if not m:
            continue
        params = extractor(m, text)
        syms = params.get("syms", [])

        # ── 执行对应动作 ──────────────────────────────────────
        if intent == "morning":
            from agents.session_manager import run_node
            return intent, run_node(0)

        elif intent == "set_symbols":
            if syms:
                from agents.session_manager import _load_state, _save_state
                state = _load_state()
                state["active_symbols"] = list(dict.fromkeys(
                    state.get("active_symbols", []) + syms))
                _save_state(state)
                return intent, f"✅ 已设置关注标的: {' '.join(state['active_symbols'])}"

        elif intent == "start_poll":
            from agents.session_manager import _load_state, run_node
            state = _load_state()
            if syms:
                state["active_symbols"] = list(dict.fromkeys(
                    state.get("active_symbols", []) + syms))
                from agents.session_manager import _save_state
                _save_state(state)
            active = state.get("active_symbols", [])
            return intent, run_node(3)

        elif intent == "premarket":
            from agents.session_manager import _load_state
            state = _load_state()
            targets = syms or state.get("active_symbols", [])
            if targets:
                out = _run("premarket.py", *targets)
                return intent, out
            return intent, "⚠️ 请指定要分析的标的，例如：盘前分析MRVL和ANET"

        elif intent == "cio":
            if syms:
                # 只分析第一只（CIO串行）
                out = _run("cio.py", syms[0], "--phases", "0123", timeout=600)
                return intent, out
            return intent, "⚠️ 请指定要分析的标的，例如：大师分析NVDA"

        elif intent == "scan":
            out = _run("candidate_scanner.py", "--top", "10")
            return intent, out

        elif intent == "portfolio":
            out = _run("portfolio_risk_agent.py")
            return intent, out

        elif intent == "close":
            out = _run("harvest_agent.py")
            return intent, f"✅ 收盘记录完成\n{out[-1000:]}"

        elif intent == "alert_price":
            price = params.get("price", "")
            sym_str = syms[0] if syms else "?"
            return intent, f"📌 提醒已记录：{sym_str} 到 ${price} 时提醒（功能建设中，请在轮询中手动确认）"

        elif intent == "news":
            from agents.session_manager import _load_state
            targets = syms or _load_state().get("active_symbols", [])[:2]
            if targets:
                import yfinance as yf
                lines = []
                for sym in targets[:3]:
                    news = yf.Ticker(sym).news or []
                    lines.append(f"【{sym}】")
                    for n in news[:3]:
                        t = n.get("content", {}).get("title") if isinstance(n.get("content"), dict) else n.get("title", "")
                        if t: lines.append(f"  • {t[:80]}")
                return intent, "\n".join(lines)
            return intent, "⚠️ 请指定标的，例如：MRVL有什么消息"

        elif intent == "buy_quick":
            syms = params.get("syms", [])
            sym_str = syms[0] if syms else "未知标的"
            return intent, f"检测到买入记录：{sym_str}。请告知成本价和股数，我来更新持仓记录。"

        elif intent == "new_position":
            syms = params.get("syms", [])
            sym_str = syms[0] if syms else "未知标的"
            return intent, f"准备为 {sym_str} 建仓。请确认：position_type（论点/催化剂/趋势/Flex）和一句话论点。"

    return "unknown", ""


def handle(text: str) -> str | None:
    """
    对外接口：识别意图并执行，返回结果字符串
    返回 None 表示不是交易意图，继续正常对话
    """
    intent, result = translate(text)
    if intent == "unknown" or not result:
        return None
    return result
