"""
premarket_decision.py — 盘前分层否决入场决策框架

用法:
    python3.12 agents/premarket_decision.py LITE  # 输出今日入场决策
"""
import sys, os, json, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_BASE            = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
_THRESHOLDS_PATH = os.path.join(_BASE, "config", "decision_thresholds.json")
_MACRO_PATH      = os.path.join(_BASE, "findings", "macro.json")
_REGIME_PATH     = os.path.join(_BASE, "config", "market_regime.json")
_POS_PATH        = os.path.join(_BASE, "config", "positions.json")
_FINDINGS        = os.path.join(_BASE, "findings")

_DEFAULT_THRESHOLDS = {
    "hard_vetoes": {
        "rr_min":               2.0,
        "qqq_premarket_min":    -0.015,
        "macro_score_min":      4,
        "watchlist_score_min":  50,
    },
    "soft_vetoes": {
        "ma20_dev_max":  0.05,
        "rs5_min":       0.0,
        "max_headwinds": 2,
    },
    "macro_type_overrides": {},
}


def load_thresholds(macro_type: str = "") -> dict:
    """
    读取 config/decision_thresholds.json，不存在则返回默认值。
    若 macro_type 在 macro_type_overrides 中有条目，覆盖对应硬否决阈值。
    """
    if os.path.exists(_THRESHOLDS_PATH):
        try:
            with open(_THRESHOLDS_PATH, encoding="utf-8") as f:
                t = json.load(f)
        except Exception:
            t = copy.deepcopy(_DEFAULT_THRESHOLDS)
    else:
        t = copy.deepcopy(_DEFAULT_THRESHOLDS)

    overrides = t.get("macro_type_overrides", {}).get(macro_type, {})
    if overrides:
        t = copy.deepcopy(t)
        t["hard_vetoes"] = {**t.get("hard_vetoes", {}), **overrides}
    return t


def _check_hard_vetoes(order_sheet: dict, macro: dict, pos_cfg: dict,
                       qqq_premarket_chg: float, watchlist_score: int,
                       thresholds: dict) -> list:
    """
    检查6条硬否决，返回触发的否决描述列表。列表为空表示无硬否决。
    按优先级排序：thesis → RR → QQQ → macro_score → watchlist_score → overnight
    """
    hv  = thresholds.get("hard_vetoes", {})
    pos = pos_cfg or {}
    vetoes = []

    # 1. thesis_status（最高优先级）
    status = pos.get("thesis_status", "intact")
    if status in ("weakening", "broken"):
        vetoes.append(f"thesis_status={status}（论点已{'弱化' if status=='weakening' else '破裂'}）")

    # 2. RR
    rr = float(order_sheet.get("rr_ratio") or 0)
    if rr < hv.get("rr_min", 2.0):
        vetoes.append(f"RR={rr:.1f}x < {hv.get('rr_min', 2.0):.1f}x（盈亏比不合格）")

    # 3. QQQ 盘前
    qqq_min = hv.get("qqq_premarket_min", -0.015)
    if qqq_premarket_chg < qqq_min:
        vetoes.append(f"QQQ盘前{qqq_premarket_chg:.1%}（逆风超过阈值{qqq_min:.1%}）")

    # 4. macro_score
    ms = macro.get("macro_score", 10)
    ms_min = hv.get("macro_score_min", 4)
    if ms < ms_min:
        vetoes.append(f"macro_score={ms} < {ms_min}（宏观环境不足）")

    # 5. watchlist_score
    s_min = hv.get("watchlist_score_min", 50)
    if watchlist_score < s_min:
        vetoes.append(f"watchlist_score={watchlist_score} < {s_min}（综合评分不足）")

    # 6. overnight_note 含"区间失效"
    on = order_sheet.get("overnight_note") or ""
    if "区间失效" in on:
        vetoes.append("overnight_note含'区间失效'（隔夜价大幅高出入场区间）")

    return vetoes


def _count_macro_headwinds(macro: dict, pos_cfg: dict) -> int:
    """活跃宏观逆风数量（对该标的为负向）"""
    ms = (pos_cfg or {}).get("macro_sensitivity", {})
    if not ms:
        return 0
    count = 0
    yc  = macro.get("yield_curve", "")
    dxy = float(macro.get("dxy") or 0)
    ms_val = macro.get("macro_score", 6)
    try:
        cpi = float(str(macro.get("cpi_latest", "0")).replace("%", ""))
    except Exception:
        cpi = 0
    if yc == "倒挂"  and ms.get("rate_up")      == "负": count += 1
    if dxy > 103     and ms.get("dollar_strong") == "负": count += 1
    if cpi > 3.5     and ms.get("inflation")     == "负": count += 1
    if ms_val <= 3   and ms.get("recession")     == "负": count += 1
    return count


def _is_regime_mismatch(sym: str, pos_cfg: dict, regime: dict,
                         watchlist_result: dict) -> bool:
    """
    当前 regime 为 sector_hot 且叙事未命中该标的时，视为 regime 错位。
    trending_up/down/sideways/volatile 不触发此条件。
    """
    # pos_cfg 保留以备将来按 macro_type 细化 regime 错位逻辑
    if regime.get("regime") != "sector_hot":
        return False
    return not watchlist_result.get("narrative_hit", False)


def _is_stage2_insufficient(sym: str, watchlist_result: dict) -> bool:
    """
    Stage 2 结构不足：RS5日≤0 且 MA20不向上倾斜（两者同时成立才触发）。
    MA20斜率：用 yfinance 10日数据判断 MA20[-1] > MA20[-6]。
    数据不可用时返回 False（保守，不触发否决）。
    """
    rs5 = watchlist_result.get("rs5")
    if rs5 is None or rs5 > 0:
        return False
    try:
        import yfinance as yf
        # 注意：period="15d" 只有约11个交易日，用10日均线近似MA20斜率
        h = yf.Ticker(sym).history(period="15d")["Close"]
        if len(h) >= 11:
            ma20_today   = float(h.tail(10).mean())
            ma20_5d_ago  = float(h.iloc[-11:-1].mean())
            return not (ma20_today > ma20_5d_ago)
    except Exception:
        pass
    return False


def _check_soft_vetoes(sym: str, watchlist_result: dict, macro: dict,
                        pos_cfg: dict, regime: dict,
                        master_confidence_all_low: bool,
                        thresholds: dict) -> list:
    """
    检查6条软否决，返回触发的否决描述列表。
    ≥2条触发时 evaluate_entry() 将输出"观察"。
    """
    sv = thresholds.get("soft_vetoes", {})
    vetoes = []

    # 1. MA20乖离超阈值（追高）
    dev = watchlist_result.get("ma20_dev")
    dev_max = sv.get("ma20_dev_max", 0.05)
    if dev is not None and dev > dev_max:
        vetoes.append(f"MA20乖离+{dev:.1%}（超过阈值+{dev_max:.0%}，追高风险）")

    # 2. RS5日超额为负（相对弱势）
    rs5 = watchlist_result.get("rs5")
    rs5_min = sv.get("rs5_min", 0.0)
    if rs5 is not None and rs5 < rs5_min:
        vetoes.append(f"RS5日超额{rs5:+.1f}%（相对弱势，低于阈值{rs5_min:+.1f}%）")

    # 3. 活跃宏观逆风项数
    headwinds = _count_macro_headwinds(macro, pos_cfg)
    max_hw = sv.get("max_headwinds", 2)
    if headwinds >= max_hw:
        vetoes.append(f"活跃宏观逆风{headwinds}项（≥{max_hw}项阈值）")

    # 4. 大师置信度全部为"低"
    if master_confidence_all_low:
        vetoes.append("大师置信度全部为'低'（分析信心不足）")

    # 5. Regime 错位
    if _is_regime_mismatch(sym, pos_cfg, regime, watchlist_result):
        vetoes.append(f"Regime错位（当前sector_hot但{sym}叙事未命中）")

    # 6. Stage 2 结构不足
    if _is_stage2_insufficient(sym, watchlist_result):
        vetoes.append(f"{sym} Stage 2结构不足（RS5日≤0且MA20不向上倾斜）")

    return vetoes


def evaluate_entry(
    sym: str,
    order_sheet: dict,
    watchlist_result: dict,
    macro: dict,
    pos_cfg: dict,
    regime: dict,
    qqq_premarket_chg: float,
    thresholds: dict = None,
    master_confidence_all_low: bool = False,
) -> dict:
    """
    执行分层否决检查，返回入场决策 dict。

    返回结构:
      decision: "可入场" | "观察" | "不入场"
      hard_vetoes: list[str]
      soft_vetoes:  list[str]
      reason: str
    """
    macro_type = (pos_cfg or {}).get("macro_type", "")
    if thresholds is None:
        thresholds = load_thresholds(macro_type=macro_type)

    score = watchlist_result.get("score", 0)

    hard = _check_hard_vetoes(order_sheet, macro, pos_cfg,
                              qqq_premarket_chg, score, thresholds)
    soft = _check_soft_vetoes(sym, watchlist_result, macro, pos_cfg,
                              regime, master_confidence_all_low, thresholds)

    if hard:
        decision = "不入场"
        reason   = f"硬否决触发（{hard[0]}）"
    elif len(soft) >= 2:
        decision = "观察"
        reason   = f"{len(soft)}个软否决，观察窗口30分钟内给出最终决定"
    else:
        decision = "可入场"
        reason   = "无硬否决" + (f"，1个软否决（{soft[0]}）" if soft else "，信号全部通过")

    return {
        "sym":         sym.upper(),
        "decision":    decision,
        "hard_vetoes": hard,
        "soft_vetoes": soft,
        "reason":      reason,
        "score":       score,
        "rr_ratio":    order_sheet.get("rr_ratio"),
    }


def fmt_decision(d: dict) -> str:
    """格式化决策输出为人类可读文本"""
    icon = {"可入场": "✅", "观察": "⚠️", "不入场": "❌"}.get(d["decision"], "?")
    lines = [
        "",
        "━" * 48,
        f"  {d['sym']} 盘前入场决策",
        "━" * 48,
        f"  {icon} {d['decision']}",
        f"  {d['reason']}",
    ]
    if d["hard_vetoes"]:
        lines.append("  [硬否决]")
        for v in d["hard_vetoes"]:
            lines.append(f"    × {v}")
    if d["soft_vetoes"]:
        lines.append("  [软否决]")
        for v in d["soft_vetoes"]:
            lines.append(f"    ⚠ {v}")
    lines.append("━" * 48)
    return "\n".join(lines)


def _load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def write_entry_decision(decisions: dict, pos_syms: list,
                          findings_dir: str = None) -> None:
    """
    写入 findings/entry_decision_{date}.json。

    decisions: {sym: evaluate_entry() 返回值} — 仅含焦点股，不含持仓股
    pos_syms:  当前有仓位的持仓股列表（不论决策如何，都需要 poll 监控止损）

    输出字段：
      decisions    — 原样写入
      poll_needed  — 任意焦点股非"不入场"，或持仓股存在时为 True
      poll_symbols — 非"不入场"焦点股 + 所有持仓股（去重）
    """
    from datetime import datetime as _dt
    _fdir = findings_dir or _FINDINGS
    os.makedirs(_fdir, exist_ok=True)

    date_str = _dt.now().strftime("%Y-%m-%d")

    # focus stocks with non-不入场 decision
    entry_syms = [sym for sym, d in decisions.items()
                  if d.get("decision") != "不入场"]
    poll_syms  = list(dict.fromkeys(entry_syms + list(pos_syms)))
    poll_needed = bool(poll_syms)

    out_path  = os.path.join(_fdir, f"entry_decision_{date_str}.json")
    lock_path = out_path + ".lock"
    import sys, json as _json
    # 跨平台锁机制
    def _flock(file):
        if sys.platform == "win32":
            import msvcrt
            try:
                msvcrt.locking(file.fileno(), 1, 1)
            except OSError:
                pass
        else:
            import fcntl
            fcntl.flock(file, fcntl.LOCK_EX)

    def _funlock(file):
        if sys.platform == "win32":
            import msvcrt
            try:
                msvcrt.locking(file.fileno(), 0, 1)
            except OSError:
                pass
        else:
            import fcntl
            fcntl.flock(file, fcntl.LOCK_UN)

    with open(lock_path, "w", encoding="utf-8") as lf:
        _flock(lf)
        try:
            # merge 现有 decisions（并行安全）
            existing_decisions = {}
            existing_poll_syms = []
            if os.path.exists(out_path):
                try:
                    with open(out_path, encoding="utf-8") as f:
                        prev = _json.load(f)
                        existing_decisions = prev.get("decisions", {})
                        existing_poll_syms = prev.get("poll_symbols", [])
                except Exception:
                    pass
            existing_decisions.update(decisions)
            merged_poll = list(dict.fromkeys(
                list(existing_poll_syms) + poll_syms
            ))
            output = {
                "date":         date_str,
                "decisions":    existing_decisions,
                "poll_needed":  bool(merged_poll),
                "poll_symbols": merged_poll,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                _json.dump(output, f, ensure_ascii=False, indent=2)
        finally:
            _funlock(lf)


def main():
    import argparse
    import yfinance as yf
    from stock_team.core.premarket_order_sheet import generate_order_sheet
    from stock_team.core.premarket_watchlist_score import score_stock
    from datetime import datetime as _dt

    parser = argparse.ArgumentParser(description="盘前入场决策框架")
    parser.add_argument("symbols", nargs="+", help="股票代码，如 LITE RKLB")
    args = parser.parse_args()

    macro  = _load_json(os.path.join(_BASE, "findings", "macro.json"))
    regime = _load_json(_REGIME_PATH)
    pos    = _load_json(_POS_PATH).get("positions", {})

    try:
        info     = yf.Ticker("QQQ").info
        qqq_cur  = info.get("regularMarketPrice", 0)
        qqq_prev = info.get("regularMarketPreviousClose", qqq_cur)
        qqq_chg  = (qqq_cur - qqq_prev) / qqq_prev if qqq_prev else 0
    except Exception:
        qqq_chg = 0.0

    all_results = {}   # {sym: evaluate_entry() result}
    for sym in args.symbols:
        sym        = sym.upper()
        pos_cfg    = pos.get(sym, {})
        thresholds = load_thresholds(macro_type=pos_cfg.get("macro_type", ""))
        os_data    = generate_order_sheet(sym)
        wr         = score_stock(sym, macro, regime, pos_cfg=pos_cfg)

        result = evaluate_entry(
            sym=sym, order_sheet=os_data, watchlist_result=wr,
            macro=macro, pos_cfg=pos_cfg, regime=regime,
            qqq_premarket_chg=qqq_chg, thresholds=thresholds,
        )
        print(fmt_decision(result))
        all_results[sym] = result

    # Write entry_decision_{date}.json
    # pos_syms: all positions with shares (t1_shares or shares > 0)
    _pos_syms = [s for s in pos
                 if (pos[s].get("shares") or pos[s].get("t1_shares") or 0) > 0]
    write_entry_decision(all_results, _pos_syms)
    print(f"\n✅ 决策写入 findings/entry_decision_{_dt.now().strftime('%Y-%m-%d')}.json")

    # 同步生成持仓出场评估（与入场决策并列）
    try:
        from stock_team.core.premarket_exit_sheet import generate_exit_sheet, fmt_exit_sheet, write_exit_decision
        _exit_syms = [s for s in pos if (pos[s].get("shares") or pos[s].get("t1_shares") or 0) > 0]
        if _exit_syms:
            _exit_results = generate_exit_sheet(_exit_syms)
            print(fmt_exit_sheet(_exit_results))
            write_exit_decision(_exit_results)
    except Exception as _e:
        print(f"出场评估失败: {_e}")


if __name__ == "__main__":
    main()
