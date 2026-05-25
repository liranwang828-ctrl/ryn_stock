"""
盘前汇总模块 — premarket_summary.py
读取 6 个盘前输出文件 + strategic_memo（若存在），
为每只标的合并输出 premarket_summary_{date}_{sym}.json（B级）
并打印 A 级终端报告（4-5行/股，不存文件）。

用法: python3.12 agents/premarket_summary.py [SYM1 SYM2 ...]
     不传参数则读 config/poll_config.json 中 default_symbols
"""
import json, os, sys
from datetime import date as _date, datetime, timezone

BASE      = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
CFG_DIR   = os.path.join(BASE, "config")
FIND_DIR  = os.path.join(BASE, "findings")

_ENTRY_DEC = {"可入场": "enter", "观察": "watch", "不入场": "pass"}
_EXIT_DEC  = {"继续持有": "hold", "考虑减仓": "reduce", "应出场": "exit"}
_ENV_MAP   = {"顺风": "favorable", "中性": "neutral", "逆风": "challenging"}
_CONF_MAP  = {"高": 4, "中": 3, "低": 2}
_STAGE_MAP = {"weak": "reduce", "broken": "exit_ready",
              "intact": "hold", "weakening": "hold_reduced"}
_TECH_STAGE = {
    (True,  True):  "2",
    (True,  False): "3",
    (False, False): "4",
    (False, True):  "4",
}


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_macro_strategy(sym: str, base_dir: str = BASE) -> dict:
    """读取宏观策略节点（若存在）。"""
    return _load(os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json"))


def _strip_env(raw: str) -> str:
    return raw.replace("✅", "").replace("❌", "").strip()


def _alignment(stance: str, entry_dec: str, exit_dec: str | None) -> dict:
    EXIT_STANCES   = {"exit_ready", "avoid"}
    REDUCE_STANCES = {"hold_reduced", "reduce"}

    if stance in EXIT_STANCES and entry_dec in ("enter", "watch"):
        return {"strategic_vs_tactical": "contradiction",
                "note": f"strategic={stance} 但 entry={entry_dec}"}
    if stance in EXIT_STANCES and exit_dec == "hold":
        return {"strategic_vs_tactical": "contradiction",
                "note": f"strategic={stance} 但 exit=hold"}
    if stance in REDUCE_STANCES and entry_dec == "enter":
        return {"strategic_vs_tactical": "tension",
                "note": f"strategic={stance} 但仍计划 enter"}
    return {"strategic_vs_tactical": "consistent", "note": ""}


def _build_strategic_lite(stock_snap: dict, thesis_status: str,
                           entry_dec: str, exit_dec: str | None) -> dict:
    mc_env    = stock_snap.get("_env_raw", "中性")
    cs        = stock_snap.get("catalyst_strength", 0)
    conf      = stock_snap.get("_confidence_raw", "中")
    stance    = _STAGE_MAP.get(thesis_status, "hold")
    unif_conf = _CONF_MAP.get(conf, 3)
    macro_fit = _ENV_MAP.get(mc_env, "neutral")
    am20      = stock_snap.get("_above_ma20", True)
    am50      = stock_snap.get("_above_ma50", True)
    tech_stage = _TECH_STAGE.get((am20, am50), "4")
    bin_risk  = cs >= 2
    ac        = _alignment(stance, entry_dec, exit_dec)

    return {
        "source": "premarket_inferred",
        "memo_date": None, "memo_valid_until": None,
        "strategic_stance": stance,
        "unified_confidence": unif_conf,
        "thesis_lifecycle": None,
        "key_condition": stock_snap.get("_reasoning", ""),
        "next_catalyst": {
            "event": stock_snap.get("news_type", "neutral"),
            "date": "unknown",
            "importance": "high" if cs >= 3 else "medium" if cs >= 1 else "low",
            "days_away": None,
        },
        "main_tensions": [],
        "macro_fit": macro_fit,
        "technical_stage": tech_stage,
        "binary_risk_flag": bin_risk,
        "alignment_check": ac,
    }


def _build_strategic_full(memo: dict, entry_dec: str, exit_dec: str | None,
                           today: _date) -> dict:
    next_cat_raw = memo.get("support_and_risk", {}).get("next_catalyst", {})
    cat_date_str = next_cat_raw.get("date", "unknown")
    try:
        cat_date  = _date.fromisoformat(cat_date_str)
        days_away = (cat_date - today).days
    except Exception:
        days_away = None

    importance = next_cat_raw.get("importance", "low")
    bin_risk   = (days_away is not None and days_away <= 2 and importance == "high")
    stance     = memo.get("synthesis", {}).get("strategic_stance", "hold")
    ac         = _alignment(stance, entry_dec, exit_dec)

    return {
        "source": "strategic_memo",
        "memo_date": memo.get("analysis_date"),
        "memo_valid_until": memo.get("outlook", {}).get("valid_until"),
        "strategic_stance": stance,
        "unified_confidence": memo.get("judgment", {}).get("unified_confidence"),
        "thesis_lifecycle": memo.get("judgment", {}).get(
            "thesis_lifecycle_stage", {}).get("stage"),
        "key_condition": memo.get("synthesis", {}).get("key_condition", ""),
        "next_catalyst": {
            "event": next_cat_raw.get("event", ""),
            "date": cat_date_str,
            "importance": importance,
            "days_away": days_away,
        },
        "main_tensions": memo.get("synthesis", {}).get("main_tensions", []),
        "macro_fit": memo.get("support_and_risk", {}).get(
            "macro_fit", {}).get("assessment", "neutral"),
        "technical_stage": memo.get("support_and_risk", {}).get(
            "technical_stage", {}).get("stage", "2"),
        "binary_risk_flag": bin_risk,
        "alignment_check": ac,
    }


def _sizing_rule(unified_conf: int | None, bin_risk: bool, lite: bool) -> str:
    if bin_risk or (unified_conf is not None and unified_conf <= 2):
        base = "×0.5"
    elif unified_conf is not None and unified_conf >= 5:
        base = "×1.5"
    else:
        base = "×1.0"
    if lite and base == "×1.5":
        base = "×1.0"
    return base


def _risk_flag(headlines: list[str], main_risks: list[str]) -> tuple[bool, str]:
    text = " ".join(headlines).lower()
    for risk in main_risks:
        for word in risk.lower().split():
            if len(word) > 3 and word in text:
                return True, word
    return False, ""


def build_summary(sym: str, date_str: str, base_dir: str = BASE) -> dict:
    find_dir = os.path.join(base_dir, "findings")
    today    = _date.fromisoformat(date_str)

    pre   = _load(os.path.join(base_dir, f"premarket_analysis_{date_str}.json"))
    ord_  = _load(os.path.join(find_dir, f"order_sheet_{date_str}.json"))
    entr  = _load(os.path.join(find_dir, f"entry_decision_{date_str}.json"))
    exit_ = _load(os.path.join(find_dir, f"exit_decision_{date_str}.json"))
    chkl  = _load(os.path.join(base_dir, f"daily_checklist_{date_str}.json"))
    memo  = _load(os.path.join(base_dir, f"strategic_memo_{sym.upper()}.json"))
    poll_cfg = _load(os.path.join(base_dir, "config", "poll_config.json"))
    sector_map_cfg = (poll_cfg.get("sector_map") or {}) if isinstance(poll_cfg, dict) else {}

    sym_upper = sym.upper()

    macro = pre.get("macro", {})
    market_context = {
        "spy_pre_chg":       macro.get("spy_pre", 0.0),
        "nq_futures":        macro.get("nq_futures", 0.0),
        "env":               _strip_env(macro.get("env", "中性")),
        "vix_level":         macro.get("vix_level"),
        "macro_events_today": macro.get("macro_events_today", []),
    }

    stk = pre.get("stocks", {}).get(sym_upper, {})
    mc  = stk.get("month_context", {})

    main_risks = memo.get("support_and_risk", {}).get("main_risks", []) if memo else []
    rflag, rnote = _risk_flag(stk.get("all_headlines", []), main_risks)

    stock_snapshot = {
        "gap_pct":        stk.get("gap_pct", 0.0),
        "pred_scene":     stk.get("pred_scene"),
        "news_type":      stk.get("news_type", "neutral"),
        "catalyst_strength": stk.get("catalyst_strength", 0),
        "pre_vol_ratio":  stk.get("pre_vol_ratio", 0.0),
        "overnight_note": ord_.get("symbols", {}).get(sym_upper, {}).get("overnight_note", ""),
        "sector_ref":     stk.get("sector_ref") or ord_.get("symbols", {}).get(sym_upper, {}).get("sector_ref", "") or (sector_map_cfg.get(sym_upper, {}) or {}).get("ref", ""),
        "sector_gap_pct": stk.get("sector_gap", 0.0),
        "rs_vs_sector":   round(mc.get("rs_1m", 0.0) - stk.get("sector_gap", 0.0), 2),
        "sector_note":    ord_.get("symbols", {}).get(sym_upper, {}).get("regime_note", ""),
        "risk_flag":      rflag,
        "risk_note":      rnote,
        "_env_raw":          _strip_env(macro.get("env", "中性")),
        "_confidence_raw":   stk.get("confidence", "中"),
        "_above_ma20":       mc.get("above_ma20", True),
        "_above_ma50":       mc.get("above_ma50", True),
        "_reasoning":        stk.get("reasoning", ""),
    }

    ord_sym  = ord_.get("symbols", {}).get(sym_upper, {})
    entr_sym = entr.get(sym_upper, entr)
    raw_dec  = entr_sym.get("decision", "不入场")
    entry_dec = _ENTRY_DEC.get(raw_dec, "pass")

    entry = {
        "decision":          entry_dec,
        "hard_vetoes":       entr_sym.get("hard_vetoes", []),
        "soft_vetoes":       entr_sym.get("soft_vetoes", []),
        "entry_base":        ord_sym.get("entry_base"),
        "stop_loss":         ord_sym.get("stop_loss"),
        "target_price":      ord_sym.get("target_price"),
        "rr_ratio":          ord_sym.get("rr_ratio"),
        "sizing":            "×1.0",
        "entry_conditions":  ord_sym.get("entry_conditions", []),
        "cancel_conditions": ord_sym.get("cancel_conditions", []),
    }

    pos_data = exit_.get("positions", {}).get(sym_upper)
    chk_sym  = chkl.get("symbols", {}).get(sym_upper)
    is_held  = pos_data is not None or (chk_sym and chk_sym.get("has_position"))

    if is_held and pos_data:
        raw_exit = pos_data.get("decision", "继续持有")
        exit_dec = _EXIT_DEC.get(raw_exit, "hold")
        exit_sect = {
            "decision":         exit_dec,
            "hard_stop":        pos_data.get("hard_stop"),
            "stop_source":      pos_data.get("stop_source", "auto_atr"),
            "hard_dist_pct":    pos_data.get("hard_dist_pct"),
            "hard_triggers":    pos_data.get("hard_triggers", []),
            "soft_triggers":    pos_data.get("soft_triggers", []),
            "target_price":     ord_sym.get("target_price"),
            "current_rr_ratio": pos_data.get("rr_remaining"),
            "flex_add_level":   ord_sym.get("flex_add_level"),
            "flex_reduce_level": ord_sym.get("flex_reduce_level"),
        }
        # 从宏观策略读取精确节点（优先级高于 order_sheet/exit_decision）
        macro = _load_macro_strategy(sym_upper, base_dir)
        macro_nodes = macro.get("nodes", {})

        if exit_sect and macro_nodes:
            ds = macro_nodes.get("dynamic_stop", {})
            tp1 = macro_nodes.get("tp1", {})
            add1 = macro_nodes.get("add1", {})
            flex_reduce = macro_nodes.get("flex_reduce", {})
            if ds.get("price"):
                exit_sect["hard_stop"]       = ds["price"]
                exit_sect["stop_source"]     = "macro_strategy"
            if tp1.get("price"):
                exit_sect["target_price"]    = tp1["price"]
            if add1 and add1.get("price"):
                exit_sect["flex_add_level"]  = add1["price"]
            if flex_reduce and flex_reduce.get("price"):
                exit_sect["flex_reduce_level"] = flex_reduce["price"]

        # ── 论点监控层：从 memo + macro_strategy 读取 ──────────────────────────
        sr_memo = memo.get("support_and_risk", {}) if memo else {}
        pc_memo = memo.get("position_context", {}) if memo else {}
        # 证伪条件：优先 derived_falsification（推导），其次 positions 手填
        falsif_list = (sr_memo.get("derived_falsification")
                       or pc_memo.get("falsification_conditions", [])
                       or pos_data.get("falsification_check", []))

        # 情景降级价位 + 催化剂窗口 + 时间止损（来自 macro_strategy）
        scene_down  = macro_nodes.get("scenario_downgrade", {})
        cat_fw      = macro_nodes.get("catalyst_framework", {})
        ts_node     = macro_nodes.get("time_stop", {})
        add1_node   = macro_nodes.get("add1") or {}

        thesis = {
            "status":               chk_sym.get("thesis_status", "intact") if chk_sym else "intact",
            "daily_action":         chk_sym.get("daily_action", "B") if chk_sym else "B",
            "position_type":        chk_sym.get("position_type", "thesis") if chk_sym else "thesis",
            "today_falsification":  pos_data.get("falsification_check", []),
            # 论点监控层（新增）
            "falsification_conditions": falsif_list[:3],
            "scenario_downgrade":   scene_down,
            "catalyst_window_active": cat_fw.get("pre_reduce_active", False),
            "catalyst_pre_reduce_pct": cat_fw.get("pre_reduce_pct"),
            "time_stop_date":       ts_node.get("review_date"),
            "add1_conditions":      add1_node.get("conditions", []),
            "add1_invalidation":    add1_node.get("invalidation", ""),
        }
    else:
        exit_dec  = None
        exit_sect = None
        thesis    = None
        macro_nodes = {}  # 未持仓时无节点数据

    thesis_status = thesis["status"] if thesis else "intact"
    if memo:
        sc = _build_strategic_full(memo, entry_dec, exit_dec, today)
    else:
        sc = _build_strategic_lite(stock_snapshot, thesis_status, entry_dec, exit_dec)

    unif_conf = sc.get("unified_confidence")
    bin_risk  = sc.get("binary_risk_flag", False)
    lite_mode = sc["source"] == "premarket_inferred"
    entry["sizing"] = _sizing_rule(unif_conf, bin_risk, lite_mode)

    for k in ("_env_raw", "_confidence_raw", "_above_ma20", "_above_ma50", "_reasoning"):
        stock_snapshot.pop(k, None)

    return {
        "date":             date_str,
        "sym":              sym_upper,
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "market_context":   market_context,
        "stock_snapshot":   stock_snapshot,
        "entry":            entry,
        "exit":             exit_sect,
        "thesis":           thesis,
        "strategic_context": sc,
        "post_open_adj":    None,
        "_lite_mode":       lite_mode,   # 供 _print_a_level 显示降级警告
    }


def _print_a_level(d: dict) -> None:
    sym = d["sym"]
    ss  = d["stock_snapshot"]
    en  = d["entry"]
    ex  = d.get("exit") or {}
    th  = d.get("thesis") or {}
    sc  = d["strategic_context"]

    scene  = ss.get("pred_scene") or "?"
    line1  = (f"{sym} | gap {ss['gap_pct']:+.1f}% | 场景{scene} | "
              f"板块{ss['sector_ref']}{ss['sector_gap_pct']:+.1f}% "
              f"RS{ss['rs_vs_sector']:+.1f}%")

    status = th.get("status", "—")
    action = th.get("daily_action", "—")
    hs     = ex.get("hard_stop")
    hdist  = ex.get("hard_dist_pct") or 0
    tgt    = ex.get("target_price") or en.get("target_price")
    rr     = ex.get("current_rr_ratio") or en.get("rr_ratio") or 0
    line2  = (f"论点{status} / {action}类 | "
              f"止损${hs or '—'}({hdist:.1f}%) / 目标${tgt or '—'} / RR={rr:.1f}")

    fl_add = ex.get("flex_add_level", "—")
    fl_red = ex.get("flex_reduce_level", "—")
    brf    = sc.get("binary_risk_flag", False)
    ali    = sc.get("alignment_check", {}).get("strategic_vs_tactical", "—")
    line3  = (f"加仓${fl_add} / 减仓${fl_red} | "
              f"binary_risk={'true' if brf else 'false'} | alignment={ali}")

    src    = sc.get("source", "?")
    stance = sc.get("strategic_stance", "—")
    conf   = sc.get("unified_confidence", "—")
    lc     = sc.get("thesis_lifecycle") or "—"
    key_c  = (sc.get("key_condition") or "")[:30]
    line4  = f"strategic[{src[:4]}]: {stance}(conf={conf}/{lc}) | key: {key_c}"

    rf    = ss.get("risk_flag", False)
    rnote = ss.get("risk_note", "")
    line5 = f"risk_flag={'true → 命中: ' + rnote if rf else 'false'}"

    # ── 论点监控层（新增）────────────────────────────────────────────────────
    extra_lines = []

    # 催化剂窗口警告
    if th.get("catalyst_window_active"):
        pct = th.get("catalyst_pre_reduce_pct", "")
        extra_lines.append(f"⚠️  催化剂窗口期（前3天）→ 建议缩仓 {pct}%，冻结 Add1/Add2")

    # 情景降级价位
    sd = th.get("scenario_downgrade", {})
    b2b = sd.get("bull_to_base", {})
    ba2b = sd.get("base_to_bear", {})
    if b2b.get("price") or ba2b.get("price"):
        extra_lines.append(
            f"📉 情景警戒: bull→base=${b2b.get('price','—')}  "
            f"base→bear=${ba2b.get('price','—')}"
        )

    # 时间止损提醒（≤7天时出现）
    ts_date = th.get("time_stop_date")
    if ts_date:
        try:
            days_left = (_date.fromisoformat(ts_date) - _date.today()).days
            if days_left <= 7:
                extra_lines.append(f"⏰ 时间止损 {ts_date}（{days_left}天后）→ 届时重新评估论点")
        except Exception:
            pass

    # 今日证伪条件（最多2条）
    falsif = th.get("falsification_conditions", [])
    if falsif:
        extra_lines.append("🔒 证伪条件:")
        for fc in falsif[:2]:
            extra_lines.append(f"   · {fc[:70]}")

    # ── 降级警告（无研究报告时）────────────────────────────────────────────
    if d.get("_lite_mode"):
        extra_lines.append(
            f"⚠️  [降级] {sym} 无研究报告（strategic_memo 缺失），战略数据全为 TA 推断，"
            f"情景/证伪/节点均不可用。建议先运行：全面分析 {sym}"
        )

    lines = [line1, line2, line3, line4, line5] + extra_lines
    print("\n".join(lines))
    print()


def write_summary(sym: str, d: dict, base_dir: str = BASE) -> str:
    fname = f"premarket_summary_{d['date']}_{sym.upper()}.json"
    path  = os.path.join(base_dir, "findings", fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    return path


def main(syms: list[str] | None = None):
    date_str = _date.today().strftime("%Y-%m-%d")
    if not syms:
        with open(os.path.join(CFG_DIR, "poll_config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        syms = cfg.get("default_symbols", [])

    print(f"\n{'='*60}")
    print(f"  盘前汇总报告 {date_str}  （{len(syms)} 只标的）")
    print(f"{'='*60}\n")

    for sym in syms:
        try:
            d    = build_summary(sym, date_str)
            path = write_summary(sym, d)
            _print_a_level(d)
            print(f"  ✅ {os.path.basename(path)}\n")
        except Exception as e:
            print(f"  ❌ {sym} 生成失败: {e}\n")


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
