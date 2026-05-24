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
import json, os, re, sys, subprocess
from datetime import datetime, timezone

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))

NODE_NAMES = {
    0: "晨间准备(8:00-9:00)",
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
        return json.load(open(p, encoding="utf-8"))
    return {"node": 1, "active_symbols": [], "alert_queue": []}

def _save_state(state, date_str=None):
    p = _state_path(date_str)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

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
    with open(board, "a", encoding="utf-8") as f:
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


_MORNING_KEYWORDS = re.compile(
    r"(早上好|早安|开始今天|今天开始|morning|晨间|盘前准备|早间|早上|起床了|开工)", re.IGNORECASE
)

def handle_text(text: str, date_str=None):
    """
    路由用户文本（优先级）：
    1. translator.py LLM意图识别层（B方向）
    2. 交易记录动词（entry_guard）
    3. 返回 None（正常对话）
    """
    stripped = text.strip()

    # ── 优先：LLM意图识别层 ───────────────────────────────────
    try:
        from agents.translator import handle as _translate
        result = _translate(stripped)
        if result is not None:
            return result
    except Exception:
        pass  # fallback to rule-based

    # ── 回退：交易记录动词 ────────────────────────────────────
    if _TRADE_PATTERN.match(stripped):
        if handle_trade_text:
            return handle_trade_text(stripped, date_str)
        return "⚠️ entry_guard 模块未加载，请检查安装"
    return None


PYTHON = sys.executable
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

    if node == 0:
        # 快速健康检查（只显示警告）
        try:
            from agents.health_check import run as _hc
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                _hc()
            hc_out = buf.getvalue()
            warnings = [l for l in hc_out.split('\n') if '❌' in l]
            if warnings:
                lines.append("\n⚠️  系统健康警告:")
                for w in warnings[:5]:
                    lines.append(f"  {w.strip()}")
        except Exception:
            pass

        # ── 晨间完整流程（7步）────────────────────────────────
        # Step 0: 宏观状态 + 模型健康
        # 昨日信号验证摘要（反馈闭环）
        try:
            from datetime import date as _date, timedelta as _td
            _yesterday = (_date.today() - _td(days=1)).strftime("%Y-%m-%d")
            _obs_path = os.path.join(BASE, "learning", "observation_outcomes.jsonl")
            if os.path.exists(_obs_path):
                _obs = [json.loads(l) for l in open(_obs_path, encoding="utf-8")
                        if l.strip() and json.loads(l).get("date") == _yesterday]
                if _obs:
                    _pass_c = sum(1 for o in _obs if o.get("gate_pass") and o.get("signal_correct"))
                    _pass_t = sum(1 for o in _obs if o.get("gate_pass") and o.get("signal_correct") is not None)
                    _blk_c  = sum(1 for o in _obs if o.get("gate_block") and o.get("signal_correct"))
                    _blk_t  = sum(1 for o in _obs if o.get("gate_block") and o.get("signal_correct") is not None)
                    _msg = f"  昨日信号验证({_yesterday}): "
                    # A: 样本<10条不显示百分比，避免误导
                    if _pass_t >= 10:
                        _msg += f"入场门通过正确率 {_pass_c}/{_pass_t}({_pass_c/_pass_t:.0%})  "
                    elif _pass_t > 0:
                        _msg += f"入场门通过 {_pass_c}/{_pass_t}(样本不足)  "
                    if _blk_t >= 10:
                        _msg += f"门控禁止正确率 {_blk_c}/{_blk_t}({_blk_c/_blk_t:.0%})"
                    elif _blk_t > 0:
                        _msg += f"门控禁止 {_blk_c}/{_blk_t}(样本不足)"
                    lines.append(_msg)
        except Exception:
            pass

        lines.append("\n【Step 0/7】宏观状态 + 模型健康检查")
        try:
            import yfinance as yf
            from learning.features import get_macro_regime
            spy_h = yf.Ticker("SPY").history(period="1y")
            macro = get_macro_regime(spy_h, len(spy_h)-1)
            vix   = float(yf.Ticker("^VIX").history(period="1d")["Close"].iloc[-1])
            lines.append(f"  宏观状态: {macro}  VIX={vix:.1f}")
        except Exception:
            lines.append("  宏观状态: 获取失败")
        # 模型退化检查（已简化：仅保留 harvest_path 供 Step 1 使用）
        harvest_path = os.path.join(BASE, "learning", "daily_harvest.jsonl")

        # Step 1: 昨日结果确认（harvest）
        lines.append("\n【Step 1/7】昨日结果记录")
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        harvest_done = os.path.exists(harvest_path) and any(
            yesterday in l for l in open(harvest_path, encoding="utf-8") if l.strip()
        ) if os.path.exists(harvest_path) else False
        if harvest_done:
            lines.append("  ✅ 昨日 harvest 已完成")
        else:
            lines.append("  ⚠️  昨日 harvest 未记录，正在补录...")
            r_h = subprocess.run(
                [PYTHON, os.path.join(AGENTS_DIR, "harvest_agent.py")],
                cwd=BASE, capture_output=True, text=True, timeout=120
            )
            lines.append(_get_out(r_h, fallback="（harvest 失败）", maxlen=500))

        # Step 3: 组合风险快照
        lines.append("\n【Step 3/7】组合风险快照")
        r0 = subprocess.run(
            [PYTHON, os.path.join(AGENTS_DIR, "portfolio_risk_agent.py")],
            cwd=BASE, capture_output=True, text=True, timeout=60
        )
        lines.append(_get_out(r0, fallback="（无组合数据）", maxlen=1500))

        # Step 4: leader-pair 快速触发检查（不做全量扫描）
        lines.append("\n【Step 4】leader-pair 触发检查")
        try:
            from agents.candidate_scanner import check_leader_triggers
            _triggers = check_leader_triggers()
            if _triggers:
                for _sym, _leaders in _triggers.items():
                    lines.append(f"  ⚡ {_sym} 被触发（{', '.join(_leaders)}）→ 加入今日关注")
                    if _sym not in (active_syms or []):
                        active_syms = list(active_syms or []) + [_sym]
            else:
                lines.append("  无领头羊触发")
        except Exception as _e:
            lines.append(f"  leader-pair 检查失败: {_e}")

        # 读取候选池结果，合并到 active_symbols
        today = datetime.now().strftime("%Y-%m-%d")
        cand_path = os.path.join(BASE, f"candidates_{today}.json")
        cand_syms = []
        if os.path.exists(cand_path):
            cdata = json.load(open(cand_path, encoding="utf-8"))
            cand_syms = [c["sym"] for c in cdata.get("candidates", [])[:8]]

        # 合并持仓底层标的
        pos_path = os.path.join(BASE, "config", "positions.json")
        pos_syms = []
        if os.path.exists(pos_path):
            pdata = json.load(open(pos_path, encoding="utf-8"))
            lev_path = os.path.join(BASE, "config", "leveraged_pairs.json")
            lev_etfs = set()
            if os.path.exists(lev_path):
                lev_cfg = json.load(open(lev_path, encoding="utf-8"))
                lev_etfs = {v["sym"] for v in lev_cfg.values() if isinstance(v, dict)}
            exclude = {"BABA", "PONY"}
            pos_syms = [s for s in pdata.get("positions", {}).keys()
                        if s not in exclude and s not in lev_etfs]

        all_syms = list(dict.fromkeys(cand_syms + pos_syms + (active_syms or [])))
        if all_syms:
            state["active_symbols"] = all_syms
            _save_state(state, date_str)

        # Step 3.7: 持仓出场评估（与入场决策对称）
        lines.append("\n【Step 3.7】持仓出场评估")
        if pos_syms:
            try:
                from agents.premarket_exit_sheet import (
                    generate_exit_sheet, fmt_exit_sheet, write_exit_decision
                )
                _exit_decisions = generate_exit_sheet(pos_syms)
                lines.append(fmt_exit_sheet(_exit_decisions))
                write_exit_decision(_exit_decisions)
            except Exception as _e:
                lines.append(f"  出场评估失败: {_e}")
        else:
            lines.append("  无当前持仓，跳过")

        # Step 5: 恐慌压力测试（如果大盘昨日跌>1%）
        try:
            spy_1d = float(spy_h["Close"].iloc[-1]) / float(spy_h["Close"].iloc[-2]) - 1 if len(spy_h) >= 2 else 0
            if spy_1d < -0.01:
                lines.append(f"\n【Step 5/7】恐慌压力测试（昨日SPY{spy_1d:.1%}）")
                r_pt = subprocess.run(
                    [PYTHON, "-c",
                     "import sys; sys.path.insert(0,'.'); "
                     "from agents.candidate_scanner import panic_pressure_test; "
                     "panic_pressure_test()"],
                    cwd=BASE, capture_output=True, text=True, timeout=120
                )
                lines.append(_get_out(r_pt, fallback="", maxlen=1500))
            else:
                lines.append("\n【Step 5/7】压力测试：大盘昨日正常，跳过")
        except Exception:
            pass

        # Step 6: 盘前分析（含直觉评分+财报日历+模式预测）
        # 确定盘前分析标的：焦点股+持仓（不跑全量watchlist）
        _premarket_syms = list(dict.fromkeys(
            (locals().get("_focus_syms") or []) + pos_syms
        ))
        if not _premarket_syms:
            _premarket_syms = list(dict.fromkeys(cand_syms[:3] + pos_syms))
        lines.append(f"\n【Step 5】盘前分析（{len(_premarket_syms)}只: {' '.join(_premarket_syms)}）")
        if _premarket_syms:
            r2 = subprocess.run(
                [PYTHON, os.path.join(AGENTS_DIR, "premarket.py")] + _premarket_syms,
                cwd=BASE, capture_output=True, text=True, timeout=300
            )
            lines.append(_get_out(r2, fallback="（无盘前数据）", maxlen=4000))

        # Step 6.5: 盘前清单（论点健康+今日行动预设）
        lines.append(f"\n【Step 6.5】盘前操作清单")
        try:
            from agents.premarket_checklist import generate_checklist as _gen_cl
            _cl_output = _gen_cl(pos_syms + cand_syms[:3])  # 持仓+前3候选
            lines.append(_cl_output)
        except Exception as _e:
            lines.append(f"  清单生成失败: {_e}")

        # Step 6.6-6.8: Constrained Mode 盘前决策三件套
        _cfg_path = os.path.join(BASE, "config", "poll_config.json")
        _trading_mode = "active"
        try:
            _cfg = json.load(open(_cfg_path, encoding="utf-8"))
            _trading_mode = _cfg.get("trading_mode", "active")
        except Exception:
            pass

        if _trading_mode == "constrained":
            # Step 6.6: 半自动选股评分 → 今日关注推荐
            lines.append("\n【Step 6.6】关注列表评分（Constrained Mode）")
            _score_out = os.path.join(BASE, "findings", "today_focus.json")
            _r_score = subprocess.run(
                [PYTHON, os.path.join(AGENTS_DIR, "premarket_watchlist_score.py"),
                 "--no-interactive", "--output", "findings/today_focus.json"],
                cwd=BASE, capture_output=True, text=True, timeout=120
            )
            lines.append(_get_out(_r_score, fallback="（评分失败）", maxlen=1000))

            # 从评分输出读今日关注标的
            _focus_syms = []
            try:
                if os.path.exists(_score_out):
                    _fd = json.load(open(_score_out, encoding="utf-8"))
                    _focus_syms = [r["sym"] for r in _fd.get("selected", [])]
            except Exception:
                pass
            if not _focus_syms:
                _focus_syms = (all_syms or pos_syms)[:2]

            # Step 6.7: 条件订单表
            if _focus_syms:
                lines.append(f"\n【Step 6.7】条件订单表（{' '.join(_focus_syms)}）")
                _r_order = subprocess.run(
                    [PYTHON, os.path.join(AGENTS_DIR, "premarket_order_sheet.py")]
                    + _focus_syms,
                    cwd=BASE, capture_output=True, text=True, timeout=120
                )
                lines.append(_get_out(_r_order, fallback="（订单表生成失败）", maxlen=2000))

            # Step 6.8: 分层否决入场决策
            if _focus_syms:
                lines.append(f"\n【Step 6.8】入场决策（{' '.join(_focus_syms)}）")
                _r_dec = subprocess.run(
                    [PYTHON, os.path.join(AGENTS_DIR, "premarket_decision.py")]
                    + _focus_syms,
                    cwd=BASE, capture_output=True, text=True, timeout=120
                )
                lines.append(_get_out(_r_dec, fallback="（决策失败）", maxlen=1000))

            # Step 6.9: premarket_summary 聚合（B级 JSON + A级终端报告）
            if _focus_syms:
                lines.append(f"\n【Step 6.9】盘前汇总（{' '.join(_focus_syms)}）")
                _r_summ = subprocess.run(
                    [PYTHON, os.path.join(AGENTS_DIR, "premarket_summary.py")]
                    + _focus_syms,
                    cwd=BASE, capture_output=True, text=True, timeout=60
                )
                lines.append(_get_out(_r_summ, fallback="（汇总生成失败）", maxlen=2000))

        # Step 7: CIO 持仓健康（周一 Phase 1 only + thesis=weakening 提示）
        focus_syms = []
        try:
            _fp = os.path.join(BASE, "config", "daily_focus.json")
            if os.path.exists(_fp):
                focus_syms = json.load(open(_fp, encoding="utf-8")).get("focus_stocks", [])
        except Exception:
            pass
        cio_syms = list(dict.fromkeys(pos_syms + [s for s in focus_syms if s not in pos_syms]))

        _is_monday = datetime.now().weekday() == 0

        if cio_syms and _is_monday:
            lines.append(f"\n【Step 3.5】持仓健康周报（CIO Phase 1，周一例行，约2分钟）")
            lines.append(f"  标的: {' '.join(cio_syms)}")
            try:
                from agents.cio import run_parallel as _cio_parallel
                _cio_res, _ = _cio_parallel(cio_syms, phases="01", timeout=180)
                _review = {"date": datetime.now().strftime("%Y-%m-%d"), "symbols": {}}
                for _sym, _res in _cio_res.items():
                    _sig  = _res.get("master_signal", _res.get("signal", "neutral"))
                    _conf = _res.get("master_conf",   _res.get("confidence", 0))
                    _icon = "✅" if _sig == "bullish" else "🔴" if _sig == "bearish" else "⚠️"
                    lines.append(f"  {_icon} [{_sym}] {_sig}({_conf}%)")
                    _review["symbols"][_sym] = {
                        "signal": _sig, "confidence": _conf,
                        "recommendation": "hold" if _sig != "bearish" else "review_needed"
                    }
                _rev_path = os.path.join(BASE, "findings",
                                          f"holdings_review_{datetime.now().strftime('%Y-%m-%d')}.json")
                with open(_rev_path, "w", encoding="utf-8") as _rf:
                    json.dump(_review, _rf, ensure_ascii=False, indent=2)
                lines.append(f"  周报写入: findings/holdings_review_{datetime.now().strftime('%Y-%m-%d')}.json")
            except Exception as _e:
                lines.append(f"  CIO Phase 1 失败: {_e}")
        elif cio_syms:
            lines.append(f"\n【Step 3.5】持仓健康：非周一，跳过 CIO 周报")
            # thesis=weakening 提示
            for _sym in cio_syms:
                try:
                    _positions_data = json.load(open(os.path.join(BASE, "config", "positions.json"), encoding="utf-8"))
                    _ts = _positions_data.get("positions", {}).get(_sym, {}).get("thesis_status", "intact")
                    if _ts in ("weakening", "broken"):
                        lines.append(f"  ⚠️  {_sym} 论点{_ts} — 建议运行深度审查:")
                        lines.append(f"     python3.12 agents/cio.py {_sym} --phases 0123")
                except Exception:
                    pass

        lines.append(f"\n{'═'*50}")
        lines.append(f"✅ 晨间准备完成")

        # 读取 entry_decision 输出 poll 建议
        _ed_path = os.path.join(BASE, "findings",
                                 f"entry_decision_{datetime.now().strftime('%Y-%m-%d')}.json")
        try:
            with open(_ed_path, encoding="utf-8") as _edf:
                _ed = json.load(_edf)
            _poll_syms = _ed.get("poll_symbols", [])
            _poll_needed = _ed.get("poll_needed", False)
            _dec_summary = []
            for _s, _d in _ed.get("decisions", {}).items():
                _icon = {"可入场": "✅", "观察": "⚠️", "不入场": "❌"}.get(_d.get("decision",""), "?")
                _dec_summary.append(f"{_icon}{_s}")
            lines.append(f"盘前决策: {' | '.join(_dec_summary) or '无'}")
            if _poll_needed and _poll_syms:
                _sym_str = " ".join(_poll_syms)
                lines.append(f"\n📡 今日需要轮询（{len(_poll_syms)}只标的）")
                lines.append(f"启动命令：")
                lines.append(f"/loop 2m /tool/pandora/bin/python3.12 agents/poll.py {_sym_str} --session 2>&1 | tail -60")
            else:
                lines.append(f"\n✅ 今日无入场机会，GTC 单已接管，无需轮询")
                if pos_syms:
                    lines.append(f"若持仓有异常可手动：python3.12 agents/poll.py {' '.join(pos_syms)} --session")
        except Exception:
            _fs_safe = locals().get("_focus_syms") or []
            lines.append(f"今日关注标的({len(_fs_safe)}只): {' '.join(_fs_safe)}")
            lines.append("→ 9:30 说'开盘了'进入盘中监控，或说'再看看XXX'做追加分析")

    elif node == 1:
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
        # 模拟盘强制收盘平仓
        try:
            from agents.paper_trader import eod_close_all, ACCOUNTS
            import yfinance as _yf
            _live = {s: _yf.Ticker(s).info.get("regularMarketPrice", 0)
                     for s in (active_syms or [])}
            eod_close_all(_live, ACCOUNTS)
            lines.append("✅ 模拟盘三账号已按收盘价强制平仓")
        except Exception as _e:
            lines.append(f"⚠️ 模拟盘收盘平仓失败: {_e}")

        # 收盘复盘
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
