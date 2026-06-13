"""
轮询状态持久化模块 — 跨轮次连续性
存储路径：learning/poll_state_{date}.json
"""
import os, json
from datetime import datetime, timezone

__possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = __possible_base if os.path.exists(os.path.join(__possible_base, "templates")) else os.path.expanduser("~/stock_team")
_LEARNING = os.path.join(BASE, "learning")


def _read_current_macro_tone():
    """读取 findings/macro.json 的 macro_tone，用于下轮拐点比较"""
    _path = os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "findings", "macro.json")
    if os.path.exists(_path):
        try:
            return json.load(open(_path, encoding="utf-8")).get("macro_tone")
        except: pass
    return None


def _today_path():
    date_str = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_LEARNING, f"poll_state_{date_str}.json")


def load_poll_state():
    """
    读取今日轮询状态文件。
    文件不存在或解析失败时返回空 dict（静默降级）。
    """
    path = _today_path()
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def save_poll_state(stocks, real_positions, spy_chg, qqq_chg, vc, vt, macro_state, mkt, et_h, et_m,
                    persona_scores=None, trading_state_info=None):
    """
    每次 poll 末尾调用，写入 learning/poll_state_{date}.json。

    参数：
        stocks        — {sym: snap_dict} 本轮拉取的行情数据
        real_positions— {sym: {cost, shares, ...}} 真实持仓
        spy_chg       — SPY 今日涨跌%
        qqq_chg       — QQQ 今日涨跌%
        vc            — VIX 当前值
        vt            — VIX 趋势（"↑升"/"↓降"/"→平"）
        macro_state   — 宏观 regime 字符串
        mkt           — 市场得分（-6~+6）
        et_h, et_m    — 美东时间 时/分
    """
    # ── 读取旧状态（用于累计字段：today_high/low、gate_pass_streak、alerts_sent）
    old_state = load_poll_state()
    old_syms  = old_state.get("symbols", {})

    now_utc  = datetime.now(timezone.utc)
    date_str = now_utc.strftime("%Y-%m-%d")
    time_str = f"{et_h:02d}:{et_m:02d}"

    # ── 读取门控结果（用于 gate_pass_streak）
    _gate_results = {}
    try:
        from stock_team.core.poll import strategy_gate, qqq_5m_chg, snap as _snap
        _qqq = _snap("QQQ")
        _qqq5m = qqq_5m_chg(_qqq) if _qqq else 0.0
        for sym, a in stocks.items():
            if not a:
                continue
            passed, _, checks, block = strategy_gate(
                a, spy_chg, vc, vt, _qqq5m, macro_state=macro_state)
            # gate_missing：未通过的条件 + 差距
            missing = []
            for name, (ok, val) in checks.items():
                if not ok:
                    missing.append(f"{name}({val})")
            _gate_results[sym] = {
                "passed": passed,
                "block":  block,
                "missing": missing,
            }
    except Exception:
        pass

    # ── 读取 T2 条件（从 strategy_gate checks 派生）
    def _t2_conditions(sym, a):
        """返回 (met_list, missing_list) 对应任务要求的 T2 监控条件"""
        if not a:
            return [], []
        rs = round(a.get("chg", 0) - spy_chg, 2)
        hist = a.get("hist", 0)
        vol_ratio = a.get("vol_ratio_5m", 1.0)
        consec = a.get("consec_green_5m", 0)
        # 持仓成本（用于"价格>成本×1.005"判断）
        cost = float(real_positions.get(sym, {}).get("cost", 0))

        met, missing = [], []
        if cost > 0 and a["cur"] > cost * 1.005:
            met.append(f"价格>${cost*1.005:.2f}")
        elif cost > 0:
            missing.append(f"价格≥成本×1.005")

        if rs > 0:
            met.append(f"RS>{rs:+.2f}%")
        else:
            missing.append(f"RS>0%(当前{rs:+.2f}%)")

        if hist > 0:
            met.append("MACD>0")
        else:
            missing.append("MACD>0")

        if consec >= 3:
            met.append(f"连阳≥3根({consec}根)")
        else:
            missing.append(f"连阳≥3根(当前{consec}根)")

        if vol_ratio > 1.5:
            met.append(f"量比>{vol_ratio:.2f}x")
        else:
            missing.append(f"量比>1.5x(当前{vol_ratio:.2f}x)")

        return met, missing

    # ── 构建 symbols 字段
    symbols_out = {}
    for sym, a in stocks.items():
        if not a:
            continue

        old_sym = old_syms.get(sym, {})
        gate_r  = _gate_results.get(sym, {})
        passed  = gate_r.get("passed", False)
        block   = gate_r.get("block", None)
        missing = gate_r.get("missing", [])

        # gate_pass_streak：连续通过次数，block 或失败则重置
        old_streak = old_sym.get("gate_pass_streak", 0)
        if block:
            streak = 0
            gate_status = f"禁止:{block}"
        elif passed:
            streak = old_streak + 1
            gate_status = f"已通过{streak}次"
        else:
            streak = 0
            gate_status = "未通过"

        # today_high/low：跨轮次累计
        old_hi = old_sym.get("today_high_price", a["cur"])
        old_lo = old_sym.get("today_low_price",  a["cur"])
        today_hi = max(old_hi, a["hi"], a["cur"])
        today_lo = min(old_lo, a["lo"], a["cur"])

        # today_high/low_nbil（持仓浮盈%极值）
        cost = float(real_positions.get(sym, {}).get("cost", 0))
        if cost > 0:
            hi_pnl = round((today_hi - cost) / cost * 100, 2)
            lo_pnl = round((today_lo - cost) / cost * 100, 2)
        else:
            hi_pnl = None
            lo_pnl = None

        t2_met, t2_miss = _t2_conditions(sym, a)

        # 大师评分（语料积累：每2分钟一条）
        ps_entry = {}
        if persona_scores and sym in persona_scores:
            ps_entry = persona_scores[sym]

        symbols_out[sym] = {
            "last_price":        round(a["cur"], 2),
            "last_rs":           round(a["chg"] - spy_chg, 2),
            "last_macd":         round(a.get("hist", 0), 3),
            "last_rsi14_5m":     round(a.get("rsi14_5m", 50), 1),
            "last_vol_ratio":    round(a.get("vol_ratio_5m", 1.0), 2),
            "last_consec_green": a.get("consec_green_5m", 0),
            "gate_pass_streak":  streak,
            "gate_status":       gate_status,
            "gate_missing":      missing,
            "t2_conditions_met": t2_met,
            "t2_missing":        t2_miss,
            "today_high_price":  round(today_hi, 2),
            "today_low_price":   round(today_lo, 2),
            "today_high_pnl":    hi_pnl,
            "today_low_pnl":     lo_pnl,
            "alerts_sent":       old_sym.get("alerts_sent", []),
            "master_score":      ps_entry,  # 本轮大师评分（语料积累）
        }

    # ── positions_summary
    positions_out = {}
    for sym, pos in real_positions.items():
        a = stocks.get(sym)
        cost = float(pos.get("cost", 0))
        cur  = a["cur"] if a else cost
        pnl  = round((cur - cost) / cost * 100, 2) if cost > 0 else 0.0

        old_pos = old_state.get("positions_summary", {}).get(sym, {})
        old_max = old_pos.get("today_max_pnl", pnl)
        old_min = old_pos.get("today_min_pnl", pnl)
        today_max_pnl = round(max(old_max, pnl), 2)
        today_min_pnl = round(min(old_min, pnl), 2)

        positions_out[sym] = {
            "cost":          cost,
            "current":       round(cur, 2),
            "pnl_pct":       pnl,
            "today_max_pnl": today_max_pnl,
            "today_min_pnl": today_min_pnl,
        }

    # ── market_context
    market_context = {
        "spy_chg":    round(spy_chg, 2),
        "qqq_chg":    round(qqq_chg, 2),
        "vix":        round(vc, 1),
        "vix_dir":    vt,
        "macro":      macro_state,
        "gate_score": f"{mkt:+d}/6",
    }

    state = {
        "date":             date_str,
        "last_updated":     time_str,
        "macro_tone_prev":  _read_current_macro_tone(),
        "symbols":          symbols_out,
        "positions_summary": positions_out,
        "market_context":    market_context,
        "contradiction_count": (trading_state_info or {}).get("contradiction_count", 0),
        "today_peak_pnl":      (trading_state_info or {}).get("today_peak_pnl", 0.0),
        "trading_state":       (trading_state_info or {}).get("state", "正常"),
    }

    os.makedirs(_LEARNING, exist_ok=True)
    try:
        json.dump(state, open(_today_path(), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
    except Exception:
        pass


def format_master_summary_line(prev_state, watched_syms=None):
    """
    每轮固定显示上一轮大师评分 + 理由摘要。
    格式：
    【大师上轮】NBIS Mine5:RS+2.4%趋势强  Marks5:仓位谨慎  ANET Mine2:技术弱
    """
    if not prev_state:
        return None
    syms  = prev_state.get("symbols", {})
    t_str = prev_state.get("last_updated", "?")
    lines = []

    for sym, info in syms.items():
        if watched_syms and sym not in watched_syms:
            continue
        ms = info.get("master_score", {})
        if not ms:
            continue
        parts = []
        for master_key, abbr in [("Minervini", "Mine"), ("Marks", "Marks"), ("Druckenmiller", "Druck")]:
            m = ms.get(master_key, {})
            score  = m.get("score", "?")
            reason = m.get("reason", "")[:14]  # 截短到14字
            if score != "?" and score > 0:
                parts.append(f"{abbr}{score}:{reason}")
        if parts:
            lines.append(f"{sym}[{'  '.join(parts)}]")

    if not lines:
        return None
    return f"【大师 {t_str}】" + "  ".join(lines)


def format_today_summary_line(state, watched_syms=None):
    """
    今日关键节点摘要：高低价格 + 持仓浮盈极值 + 止损警告次数
    格式：【今日】NBIS 高$228.8 低$210.8  NBIL 高+6.7% 低-8.9%  MRVU 高+0.8% 低-4.5%
    """
    if not state:
        return None
    syms = state.get("symbols", {})
    pos  = state.get("positions_summary", {})
    parts = []

    # 非持仓关注标的：今日高低价
    pos_keys = set(pos.keys())
    for sym, info in syms.items():
        if watched_syms and sym not in watched_syms:
            continue
        if sym in pos_keys:
            continue
        hi = info.get("today_high_price")
        lo = info.get("today_low_price")
        if hi is not None and lo is not None:
            parts.append(f"{sym} 高${hi:.1f} 低${lo:.1f}")

    # 持仓标的：今日浮盈高低极值（只显示有意义的，过滤 0%/0% 的）
    for sym, pinfo in pos.items():
        mx = pinfo.get("today_max_pnl")
        mn = pinfo.get("today_min_pnl")
        if mx is not None and mn is not None and (mx != 0.0 or mn != 0.0):
            parts.append(f"{sym} 高{mx:+.1f}% 低{mn:+.1f}%")

    if not parts:
        return None
    return "【今日】" + "  ".join(parts)


def format_prev_state_line(prev_state):
    """
    将上轮状态格式化为一行摘要，插入到 poll 输出的【环境】之后。
    格式：【上轮】NBIS$222.5(RS+1.4%)  MRVL$181.3(RS-0.1%)  NBIL:-0.1%  MRVU:+0.3%
    返回字符串，无数据时返回 None。
    """
    if not prev_state:
        return None

    syms   = prev_state.get("symbols", {})
    pos    = prev_state.get("positions_summary", {})
    t_str  = prev_state.get("last_updated", "?")
    parts  = []

    # 非持仓关注标的：价格+RS+大师评分简写
    pos_keys = set(pos.keys())
    for sym, info in syms.items():
        if sym in pos_keys:
            continue
        price = info.get("last_price", 0)
        rs    = info.get("last_rs", 0)
        ms    = info.get("master_score", {})
        if ms:
            m = ms.get("Minervini", {}).get("score", "?")
            k = ms.get("Marks", {}).get("score", "?")
            d = ms.get("Druckenmiller", {}).get("score", "?")
            parts.append(f"{sym}${price}(RS{rs:+.1f}% M:{m} K:{k} D:{d})")
        else:
            parts.append(f"{sym}${price}(RS{rs:+.1f}%)")

    # 持仓标的：浮盈% + 大师评分
    for sym, pinfo in pos.items():
        pnl  = pinfo.get("pnl_pct", 0)
        # 从 symbols 里找大师评分
        ms   = syms.get(sym, {}).get("master_score", {})
        if ms:
            m = ms.get("Minervini", {}).get("score", "?")
            k = ms.get("Marks", {}).get("score", "?")
            parts.append(f"{sym}:{pnl:+.1f}%(M:{m} K:{k})")
        else:
            parts.append(f"{sym}:{pnl:+.1f}%")

    if not parts:
        return None
    return f"【上轮 {t_str}】" + "  ".join(parts)