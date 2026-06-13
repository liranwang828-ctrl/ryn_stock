"""
premarket_exit_sheet.py — 持仓出场评估模块

与 premarket_decision.py 对称，为每只持仓盘前生成三态出场建议。

用法:
    python3.12 agents/premarket_exit_sheet.py            # 评估所有持仓
    python3.12 agents/premarket_exit_sheet.py MRVU BABA  # 指定持仓
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf
from datetime import datetime, date as _date

_BASE       = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
_POS_PATH   = os.path.join(_BASE, "config", "positions.json")
_MACRO_PATH = os.path.join(_BASE, "findings", "macro.json")
_FINDINGS   = os.path.join(_BASE, "findings")


def _load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def _parse_time_deadline(text: str):
    """
    从证伪条件文本中提取"截止 YYYY-MM-DD"日期。
    返回 (days_remaining, date_str)，无日期时返回 (None, None)。
    days_remaining < 0 表示已过期。
    """
    m = re.search(r'截止\s*(\d{4}-\d{2}-\d{2})', text)
    if not m:
        return None, None
    date_str = m.group(1)
    try:
        deadline = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (deadline - _date.today()).days, date_str
    except Exception:
        return None, None


def _fetch_price_and_atr(sym: str):
    """获取当前价、ATR14、近5日低点。失败返回 None。"""
    try:
        h = yf.Ticker(sym).history(period="30d")
        if h.empty or len(h) < 5:
            return None
        cur   = float(h["Close"].iloc[-1])
        atr14 = float((h["High"] - h["Low"]).tail(14).mean()) if len(h) >= 14 \
                else float((h["High"] - h["Low"]).mean())
        lo5   = float(h["Low"].tail(5).min())
        return {"cur": cur, "atr14": round(atr14, 2), "lo5": round(lo5, 2)}
    except Exception:
        return None


def _compute_stop_levels(sym: str, pos_cfg: dict):
    """
    计算硬止损和软止损。

    返回 (hard_stop, soft_stop, stop_source, tech_data)
    stop_source: "manual_gtc" | "node1" | "auto_atr"

    优先级：
      t1_stop_snapshot not in (None, 0) → manual_gtc
      node1 not in (None, 0)            → node1
      否则                               → auto_atr（lo5 - atr14×0.3）
    """
    t1_stop   = pos_cfg.get("t1_stop_snapshot")
    node1_val = pos_cfg.get("node1")
    cost      = float(pos_cfg.get("t1_cost") or pos_cfg.get("cost") or 0)
    soft_stop = cost

    tech = _fetch_price_and_atr(sym)

    if t1_stop not in (None, 0):
        return float(t1_stop), soft_stop, "manual_gtc", tech

    if node1_val not in (None, 0):
        return float(node1_val), soft_stop, "node1", tech

    # auto ATR
    if tech:
        auto_stop = round(tech["lo5"] - tech["atr14"] * 0.3, 2)
        return auto_stop, soft_stop, "auto_atr", tech

    return None, soft_stop, "auto_atr", None


def evaluate_exit(sym: str, pos_cfg: dict, macro: dict,
                  premarket_data: dict | None = None) -> dict:
    """
    对单只持仓进行出场评估。在函数内部通过 yfinance 获取实时价格和技术数据。

    三态输出：应出场 / 考虑减仓 / 继续持有

    硬触发（任一满足 → 应出场）：
      - 价格 < hard_stop
      - thesis_status = "broken"
      - 时间证伪条件已过期（days <= 0）

    软触发（≥1 满足 → 考虑减仓）：
      - thesis_status = "weakening"
      - 价格在浮亏区（hard_stop < cur < soft_stop）且论点非 intact
      - 距硬止损不足 3%（0 < hard_dist_pct < 3）
      - RR 剩余 < 1.0（论点型持仓有三层过滤，见下方）
      - 时间证伪条件将在 ≤3 天内到期

    三层过滤（论点型持仓 / 杠杆产品 / 催化剂日）：
      [L1] 论点型 + rr_remaining_low：改为 target_revision_needed（非 reduce）
           触发上修提示的条件：cur 超过原目标 5%+，或 catalyst_strength ≥ 2，或 |gap| > 5%
      [L2] 杠杆≥2 + pnl < min_threshold (25%)：压制 rr_remaining_low，未达最低门槛不止盈
      [L3] 论点型 + price_in_loss_zone：intact 时压制，weakening 时保留
    """
    sym = sym.upper()
    hard_stop, soft_stop, stop_source, tech = _compute_stop_levels(sym, pos_cfg)
    cur   = tech["cur"]   if tech else None

    hard_triggers       = []
    soft_triggers       = []
    falsification_check = []  # 需人工确认的基本面条件

    # ── 硬触发 ──────────────────────────────────────────────────
    # H1: 价格 < 硬止损
    hard_dist_pct = None
    if cur is not None and hard_stop is not None:
        hard_dist_pct = round((cur - hard_stop) / cur * 100, 1)
        if cur < hard_stop:
            hard_triggers.append("price < hard_stop")

    # H2: thesis_status = broken
    if pos_cfg.get("thesis_status") == "broken":
        hard_triggers.append("thesis_status=broken")

    # H3/S3: 解析 falsification_conditions 中的时间条件
    for cond in (pos_cfg.get("falsification_conditions") or []):
        days, date_str = _parse_time_deadline(cond)
        if days is not None:
            if days <= 0:
                hard_triggers.append(f"time_condition_expired ({date_str})")
            elif days <= 3:
                soft_triggers.append(f"time_condition_expiring_{days}d")
                falsification_check.append(cond[:80])
            else:
                falsification_check.append(cond[:80])
        else:
            # 非时间条件：展示给用户确认
            falsification_check.append(cond[:80])

    # ── 软触发 ──────────────────────────────────────────────────
    # S1: thesis_status = weakening
    if pos_cfg.get("thesis_status") == "weakening":
        soft_triggers.append("thesis_status=weakening")

    # S2: 价格在浮亏区（soft_stop > cur > hard_stop）
    # [L3] 论点型 + intact → 压制；weakening 时保留
    _position_type  = pos_cfg.get("position_type", "thesis")
    _thesis_status  = pos_cfg.get("thesis_status", "intact")
    _is_thesis_type = (_position_type == "thesis")
    if cur is not None and hard_stop is not None and soft_stop is not None:
        if hard_stop < cur < soft_stop:
            if _is_thesis_type and _thesis_status == "intact":
                pass   # [L3] 论点 intact 时不因浮亏触发减仓
            else:
                soft_triggers.append("price_in_loss_zone")

    # S3: 接近硬止损（0% < hard_dist_pct < 3%）
    if hard_dist_pct is not None and 0 < hard_dist_pct < 3:
        soft_triggers.append("approaching_hard_stop")

    # S4: RR 剩余 < 1.0（含三层过滤）
    rr         = None
    cost       = float(pos_cfg.get("t1_cost") or pos_cfg.get("cost") or 0)
    target_pct = pos_cfg.get("target_pct")

    # 从 premarket_data 获取催化剂信息（三层过滤 L1/L2 需要）
    _pm         = premarket_data or {}
    _catalyst   = int(_pm.get("catalyst_strength", 0) or 0)
    _gap_pct    = float(_pm.get("gap_pct", 0) or 0)
    _news_type  = _pm.get("news_type", "")

    # 杠杆倍数（从 leveraged_pairs.json 读取）
    _lev = 1
    try:
        _lev_path = os.path.join(_BASE, "config", "leveraged_pairs.json")
        if os.path.exists(_lev_path):
            _lev_data = _load_json(_lev_path)
            for _und, _info in _lev_data.items():
                if _info.get("sym", "").upper() == sym.upper():
                    _lev = int(_info.get("leverage", 1))
                    break
    except Exception:
        pass

    # 最低收益门槛（杠杆≥2 要求 25%，否则 10%）
    _min_threshold = 0.25 if _lev >= 2 else 0.10
    _pnl_pct = (cur - cost) / cost if (cost > 0 and cur) else 0

    if target_pct and cost > 0 and cur and hard_stop and cur > hard_stop:
        target = cost * (1 + float(target_pct) / 100)
        denom  = cur - hard_stop
        if denom > 0:
            rr = round((target - cur) / denom, 1)
            if rr < 1.0:
                # ─── 三层过滤 ─────────────────────────────────────────
                # [L2] 杠杆产品未达最低收益门槛 → 压制止盈信号
                if _pnl_pct < _min_threshold:
                    pass   # 未达最低门槛，不触发 rr_remaining_low

                # [L1] 论点型持仓 → rr_remaining_low 改为 target_revision_needed
                elif _is_thesis_type:
                    # 判断是否需要触发上修目标的提示
                    _surpassed = (rr < -0.05)           # 已超目标价 5%+
                    _big_gap   = abs(_gap_pct) > 5.0    # 暴涨/暴跌超过 5%
                    _strong_cat = _catalyst >= 2         # 强催化剂（财报/战略入股）
                    if _surpassed or _big_gap or _strong_cat:
                        soft_triggers.append("target_revision_needed")
                    # 否则：价格刚过目标但无特殊信号，论点型继续持有

                # [普通持仓] 正常触发 rr_remaining_low
                else:
                    soft_triggers.append("rr_remaining_low")

    # ── 决策 ────────────────────────────────────────────────────
    if hard_triggers:
        decision = "应出场"
        reason   = hard_triggers[0]
    elif soft_triggers:
        decision = "考虑减仓"
        reason   = " + ".join(soft_triggers[:2])
    else:
        decision = "继续持有"
        reason   = "无触发条件"

    return {
        "sym":                sym,
        "decision":           decision,
        "hard_stop":          hard_stop,
        "soft_stop":          soft_stop,
        "stop_source":        stop_source,
        "cur":                cur,
        "hard_dist_pct":      hard_dist_pct,
        "hard_triggers":      hard_triggers,
        "soft_triggers":      soft_triggers,
        "falsification_check": falsification_check,
        "rr_remaining":       rr,
        "reason":             reason,
    }


def generate_exit_sheet(pos_syms: list) -> dict:
    """
    批量评估持仓列表，返回 {sym: evaluate_exit() 结果}。
    从 positions.json 读取持仓配置，evaluate_exit 内部获取实时价格。
    同时读取 premarket_analysis（若存在）传入催化剂信息，用于三层过滤。
    """
    pos_data = _load_json(_POS_PATH).get("positions", {})
    macro    = _load_json(_MACRO_PATH)

    # 读取今日 premarket_analysis（催化剂信息）
    from datetime import date as _date_cls
    _today = _date_cls.today().strftime("%Y-%m-%d")
    _pm_path = os.path.join(os.path.dirname(_POS_PATH),
                            f"../premarket_analysis_{_today}.json")
    _pm_all = _load_json(os.path.normpath(_pm_path)).get("stocks", {})

    results  = {}
    for sym in pos_syms:
        sym     = sym.upper()
        pos_cfg = pos_data.get(sym, {})
        if not pos_cfg:
            continue
        pm_data = _pm_all.get(sym, {})   # 今日盘前数据（catalyst_strength/gap_pct）
        results[sym] = evaluate_exit(sym, pos_cfg, macro, premarket_data=pm_data)
    return results

def write_exit_decision(decisions: dict, findings_dir: str = None) -> None:
    """写入 findings/exit_decision_{date}.json（merge 模式，并行安全）"""
    import sys
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

    _fdir    = findings_dir or _FINDINGS
    os.makedirs(_fdir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path     = os.path.join(_fdir, f"exit_decision_{date_str}.json")
    # 文件锁保证并行写安全
    lock_path = path + ".lock"
    with open(lock_path, "w", encoding="utf-8") as lf:
        _flock(lf)
        try:
            # 读取现有数据并 merge（保留其他 sym 的结果）
            existing = {}
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        existing = json.load(f).get("positions", {})
                except Exception:
                    existing = {}
            existing.update(decisions)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"date": date_str, "positions": existing},
                          f, ensure_ascii=False, indent=2)
        finally:
            _funlock(lf)


def fmt_exit_sheet(decisions: dict) -> str:
    """格式化为人类可读输出，含 ❌/⚠️/✅ 标记"""
    date_str   = datetime.now().strftime("%Y-%m-%d")
    lines      = [f"\n【今日持仓出场评估】{date_str}\n"]
    _icons     = {"应出场": "❌", "考虑减仓": "⚠️", "继续持有": "✅"}
    _src_label = {
        "manual_gtc": "GTC 已挂",
        "node1":      "node1",
        "auto_atr":   "⚠️ ATR估算，建议设 GTC",
    }
    for sym, d in decisions.items():
        icon = _icons.get(d.get("decision", ""), "?")
        lines.append(f"{sym}  {icon} {d.get('decision', '?')}")

        hs   = d.get("hard_stop")
        ss   = d.get("soft_stop")
        cur  = d.get("cur")
        dist = d.get("hard_dist_pct")
        src  = _src_label.get(d.get("stop_source", ""), d.get("stop_source", ""))

        if hs is not None and cur is not None:
            dist_str = f"  距硬线 {dist:+.1f}%" if dist is not None else ""
            lines.append(f"  硬止损 ${hs:.2f}（{src}）  现价 ${cur:.2f}{dist_str}")
        if ss is not None:
            lines.append(f"  软止损（成本）${ss:.2f}")
        for t in d.get("hard_triggers", []):
            lines.append(f"  触发（硬）: {t}")
        for t in d.get("soft_triggers", []):
            lines.append(f"  触发（软）: {t}")
        for fc in d.get("falsification_check", []):
            lines.append(f"  ⚠️ 请确认证伪条件: {fc[:70]}")
        rr = d.get("rr_remaining")
        if rr is not None:
            lines.append(f"  RR剩余 {rr:.1f}x")
        lines.append("")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="持仓出场评估")
    parser.add_argument("symbols", nargs="*", help="持仓代码（空则评估所有持仓）")
    args = parser.parse_args()

    pos_data = _load_json(_POS_PATH).get("positions", {})
    if args.symbols:
        pos_syms = [s.upper() for s in args.symbols]
    else:
        pos_syms = [s for s, d in pos_data.items()
                    if (d.get("shares") or d.get("t1_shares") or 0) > 0]

    results = generate_exit_sheet(pos_syms)
    print(fmt_exit_sheet(results))
    write_exit_decision(results)
    print(f"✅ 出场评估写入 findings/exit_decision_{datetime.now().strftime('%Y-%m-%d')}.json")


if __name__ == "__main__":
    main()
