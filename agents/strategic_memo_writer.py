"""
战略备忘录生成模块 — strategic_memo_writer.py
将 CIO 全量分析结果转换为结构化 strategic_memo_{sym}.json。

数据来源（运行 cio.py --phases 0123 后可用）：
  findings/{Agent}.json           → 各维度分析（TechAgent/FundAgent/...）
  persona_stances.jsonl           → 大师投票（7位，信号+核心论点）
  learning/cio_signals_{date}_{sym}.json → 综合信号
  findings/fundamentals_{sym}.json → yfinance 基本面
  config/positions.json           → 用户论点/证伪条件

用法:
  python3.12 agents/strategic_memo_writer.py NVDA
  python3.12 agents/strategic_memo_writer.py NVDA MRVU LITX IAU
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE      = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR  = os.path.join(BASE, "findings")
CFG_DIR   = os.path.join(BASE, "config")
LEARN_DIR = os.path.join(BASE, "learning")

# ── 枚举集合（spec 定义）──────────────────────────────────────────────────────
TENSION_ENUMS = [
    "strong_fundamentals_macro_headwind",
    "intact_thesis_late_lifecycle",
    "bullish_masters_poor_technical",
    "good_quality_poor_liquidity",
    "thesis_intact_weak_falsifiability",
    "none",
]


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_jsonl_all(path: str) -> list[dict]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


# ── 数据读取层 ─────────────────────────────────────────────────────────────────

def _load_agent_reports(sym: str, cio_signals: dict | None = None) -> dict:
    """
    读取各 Agent 分析报告。
    优先读 per-sym 文件 findings/{Agent}_{sym}_{date}.json（并行安全）；
    其次读全局 {Agent}.json（需 symbol 字段匹配，防并行污染）；
    最后 fallback 到 cio_signals 最小化数据。
    """
    today = _date.today().strftime("%Y-%m-%d")
    agent_names = ["TechAgent", "FundAgent", "MacroAgent", "SentimentAgent",
                   "RiskAgent", "SectorAgent"]
    reports = {}
    for a in agent_names:
        # 1. per-sym 文件（并行安全，cio.py Phase1 已写入）
        per_sym = _load(os.path.join(FIND_DIR, f"{a}_{sym.upper()}_{today}.json"))
        if per_sym:
            reports[a] = per_sym
            continue
        # 2. 全局文件（单股串行场景），需 symbol 匹配
        global_d = _load(os.path.join(FIND_DIR, f"{a}.json"))
        if global_d and global_d.get("symbol", global_d.get("sym", "")).upper() == sym.upper():
            reports[a] = global_d
            continue
        # 3. fallback：cio_signals 最小化（无 key_points）
        if cio_signals:
            sig_data = cio_signals.get("agent_signals", {}).get(a, {})
            if sig_data:
                reports[a] = {
                    "signal":     sig_data.get("signal", "neutral"),
                    "confidence": sig_data.get("confidence", 50),
                    "key_points": [],
                    "analysis":   [],
                    "conclusion": {},
                }
    return reports


def _load_latest_persona_stances(sym: str) -> dict:
    """从 persona_stances.jsonl 读取该标的最新一条大师立场记录"""
    all_recs = _load_jsonl_all(os.path.join(BASE, "persona_stances.jsonl"))
    sym_recs = [r for r in all_recs
                if r.get("symbol", r.get("sym", "")).upper() == sym.upper()
                and r.get("msg_type") == "persona_stances"]
    if not sym_recs:
        return {}
    return sym_recs[-1].get("stances", {})


def load_agent_analysis_per_sym(sym: str, date: str,
                                  find_dir: str = FIND_DIR) -> dict:
    """
    从 per-symbol agent 文件读取完整分析（cio.py Task 1 保存的）。
    key: tech/fund/macro/risk/sentiment/sector
    """
    AGENT_MAP = {
        "TechAgent": "tech", "FundAgent": "fund", "MacroAgent": "macro",
        "RiskAgent": "risk", "SentimentAgent": "sentiment", "SectorAgent": "sector",
    }
    result = {}
    for agent_name, key in AGENT_MAP.items():
        path = os.path.join(find_dir, f"{agent_name}_{sym.upper()}_{date}.json")
        d = _load(path)
        if d:
            result[key] = {
                "signal":     d.get("signal", "neutral"),
                "confidence": d.get("confidence", 50),
                "analysis":   d.get("analysis", []),
                "key_points": d.get("key_points", []),
                "conclusion": d.get("conclusion", {}),
            }
    return result


def load_debate_highlights(sym: str, date: str,
                            find_dir: str = FIND_DIR) -> dict:
    """从 per-sym debate 文件提取辩论摘要"""
    path = os.path.join(find_dir, f"debate_{sym.upper()}_{date}.jsonl")
    records = _load_jsonl_all(path)
    if not records:
        return {"rounds": 0, "consensus_reached": False,
                "key_challenges": [], "dominant_view": "无辩论数据"}

    challenges = [r.get("content", "")[:60] for r in records
                  if r.get("msg_type") == "challenge"]
    rounds = max((r.get("round", 1) for r in records if "round" in r), default=1)
    verdicts = [r.get("content", "") for r in records
                if r.get("msg_type") in ("verdict", "synthesis")]
    dominant = verdicts[-1][:100] if verdicts else "辩论未产生明确结论"

    return {
        "rounds":           rounds,
        "consensus_reached": any(r.get("msg_type") == "consensus" for r in records),
        "key_challenges":   challenges[:4],
        "dominant_view":    dominant,
    }


def build_position_context(sym: str, cur_price: float | None = None,
                            base_dir: str = BASE,
                            pos_sym: str | None = None) -> dict:
    """
    从 positions.json + premarket_summary 构建持仓管理区块。
    pos_sym: 持仓查询 sym（杠杆ETF 用 ETF sym 查持仓，分析 sym 用底层）
    包含：完整论点、证伪条件、加仓策略、减仓策略、当日快照。
    """
    lookup = (pos_sym or sym).upper()
    _pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    pos_cfg   = _pos_data.get("positions", {}).get(lookup, {}) if _pos_data else _load_position_cfg(lookup)
    cost     = float(pos_cfg.get("t1_cost") or pos_cfg.get("cost") or 0)
    if cur_price is None:
        fund_path = os.path.join(base_dir, "findings", f"fundamentals_{sym.upper()}.json")
        try:
            with open(fund_path, encoding="utf-8") as f:
                fund_data = json.load(f)
                cur_price = fund_data.get("cur")
        except Exception:
            pass
        if cur_price is None:
            try:
                dv_path = os.path.join(base_dir, "data_verified.json")
                if os.path.exists(dv_path):
                    with open(dv_path, encoding="utf-8") as f:
                        dv = json.load(f)
                        if dv.get("symbol", "").upper() == sym.upper():
                            cur_price = dv.get("fields", {}).get("close", {}).get("value")
            except Exception:
                pass
        if cur_price is None:
            cur_price = 100.0
    shares   = int(pos_cfg.get("shares") or pos_cfg.get("t1_shares") or 0)
    hard_stop = float(pos_cfg.get("t1_stop_snapshot") or 0) or None
    target_pct= float(pos_cfg.get("target_pct") or 15)
    # 价格节点由 macro_strategy.py 计算，此处为占位，由 premarket_summary 覆盖
    target_price = None

    entry_date_str = pos_cfg.get("date", str(_date.today()))
    try:
        days_held = (_date.today() - _date.fromisoformat(entry_date_str)).days
    except Exception:
        days_held = 0

    pnl_pct = None
    if cur_price and cost > 0:
        pnl_pct = round((cur_price - cost) / cost * 100, 2)

    t2 = pos_cfg.get("t2_conditions", {}) or {}
    flex_add_level = None
    flex_reduce_level = None
    try:
        pm_path = os.path.join(base_dir, "findings",
                               f"premarket_summary_{_date.today()}_{sym.upper()}.json")
        pm = _load(pm_path)
        flex_add_level = (pm.get("post_open_adj") or {}).get("flex_add_adj") or \
                         (pm.get("exit") or {}).get("flex_add_level")
        flex_reduce_level = (pm.get("post_open_adj") or {}).get("flex_reduce_adj") or \
                            (pm.get("exit") or {}).get("flex_reduce_level")
    except Exception:
        pass

    return {
        "thesis_full":            pos_cfg.get("thesis", ""),
        "falsification_conditions": pos_cfg.get("falsification_conditions", []),
        "add_strategy": {
            "t2_conditions":    t2.get("note", ""),
            "t2_price_floor":   t2.get("underlying_price_floor"),
            "t2_etf_floor":     t2.get("etf_price_floor"),
            "flex_add_trigger": flex_add_level,
            "sizing_note":      f"T2 加仓门槛：底层标的>${t2.get('underlying_price_floor', '—')}",
        },
        "reduce_strategy": {
            "target_pct":           target_pct,
            "target_price":         target_price,
            "flex_reduce_trigger":  flex_reduce_level,
            "hard_stop":            hard_stop,
            "time_stop":            next((c for c in pos_cfg.get("falsification_conditions", [])
                                          if "截止" in c or "无法" in c), None),
        },
        "position_snapshot": {
            "cost":               cost,
            "shares":             shares,
            "cur_price":          cur_price,
            "unrealized_pnl_pct": pnl_pct,
            "days_held":          days_held,
            "gtc_placed":         pos_cfg.get("gtc_stop_placed", False),
        },
    }


def build_scenarios(sym: str, cur_price: float | None = None,
                    base_dir: str = BASE,
                    pos_sym: str | None = None) -> dict:
    """构建三情景分析（牛/基准/熊）"""
    lookup = (pos_sym or sym).upper()
    _pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    pos_cfg   = _pos_data.get("positions", {}).get(lookup, {}) if _pos_data else _load_position_cfg(lookup)
    fund      = _load_fundamentals(sym)
    target_pct= float(pos_cfg.get("target_pct") or 15)
    analyst_t = fund.get("target_price")

    is_leveraged = bool(pos_sym) and pos_sym.upper() != sym.upper()
    if cur_price is None:
        cur_price = fund.get("cur")
        if cur_price is None:
            try:
                dv_path = os.path.join(base_dir, "data_verified.json")
                if os.path.exists(dv_path):
                    with open(dv_path, encoding="utf-8") as f:
                        dv = json.load(f)
                        if dv.get("symbol", "").upper() == sym.upper():
                            cur_price = dv.get("fields", {}).get("close", {}).get("value")
            except Exception:
                pass
        if cur_price is None:
            cur_price = 100.0

    if is_leveraged:
        # 杠杆 ETF 场景：用底层股票当前价格做情景计算，ETF 的 cost/stop 不适用
        macro = _load(os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json"))
        underlying_price = (macro.get("market_inputs", {}).get("price")
                            if macro else None)
        base_price = cur_price or underlying_price or (analyst_t * 0.95 if analyst_t else 100.0)
        hard_stop = 0.0  # 底层股票止损由 macro_strategy 计算
    else:
        cost      = float(pos_cfg.get("t1_cost") or pos_cfg.get("cost") or 0)
        hard_stop = float(pos_cfg.get("t1_stop_snapshot") or 0)
        base_price = cur_price or cost or 100.0

    if base_price <= 0:
        base_price = 100.0

    # 目标价过时：低于现价则不作为 bull 情景，降低其意义
    analyst_stale = bool(analyst_t and analyst_t < base_price)
    bull_target = (
        analyst_t if analyst_t and not analyst_stale
        else round(base_price * (1 + target_pct / 50), 2)  # fallback: 2× 目标收益率
    )
    base_target = round(base_price * (1 + target_pct / 100), 2)
    bear_target = hard_stop or round(base_price * 0.85, 2)

    return {
        "bull": {
            "price_target": bull_target,
            "condition":    "论点被市场完全验证，分析师上调目标价",
            "probability":  "medium",
        },
        "base": {
            "price_target": base_target,
            "condition":    f"论点按计划执行，达到目标收益 {target_pct}%",
            "probability":  "high",
        },
        "bear": {
            "price_target": bear_target,
            "condition":    "止损触发，论点破裂",
            "probability":  "low",
        },
    }


def _load_cio_signals(sym: str, date: str) -> dict:
    path = os.path.join(LEARN_DIR, f"cio_signals_{date}_{sym.upper()}.json")
    return _load(path)


def _load_fundamentals(sym: str) -> dict:
    path = os.path.join(FIND_DIR, f"fundamentals_{sym.upper()}.json")
    return _load(path)


def _load_position_cfg(sym: str) -> dict:
    pos_data = _load(os.path.join(CFG_DIR, "positions.json"))
    return pos_data.get("positions", {}).get(sym.upper(), {})


# ── 字段构建函数 ───────────────────────────────────────────────────────────────

def _build_fundamentals_snapshot(fund: dict) -> dict:
    """从 fundamentals_{sym}.json 构建基本面快照（B 级）"""
    # pe_fwd: quick_fundamentals 用 "pe_fwd"，旧版用 "pe_forward"
    pe_fwd = fund.get("pe_fwd") or fund.get("pe_forward") or fund.get("forwardPE")
    # peg: quick_fundamentals 用 "peg"，旧版用 "peg_ratio"
    peg = fund.get("peg") or fund.get("peg_ratio") or fund.get("pegRatio")
    # analyst upside: quick_fundamentals 用 "target_deviation"，旧版 "target_upside_pct"
    upside = fund.get("analyst_upside_pct") or fund.get("target_upside_pct") or fund.get("target_deviation")
    return {
        "pe_ttm":             fund.get("pe_ttm"),
        "pe_fwd":             pe_fwd,
        "peg":                peg,
        "revenue_growth_pct": fund.get("rev_growth_pct") or fund.get("revenue_growth_pct"),
        "gross_margin":       fund.get("gross_margin"),
        "operating_margin":   fund.get("operating_margin"),
        "roe":                fund.get("roe"),
        "fcf_B":              fund.get("fcf_B"),
        "mktcap_B":           fund.get("mktcap_B"),
        "analyst_target":     fund.get("target_price"),
        "analyst_upside_pct": upside,
        "rec_key":            fund.get("rec_key") or fund.get("recommendationKey",""),
        "n_analysts":         fund.get("n_analysts") or fund.get("numberOfAnalystOpinions"),
        "sector":             fund.get("sector",""),
        "industry":           fund.get("industry",""),
        "long_name":          fund.get("long_name",""),
        "last_updated":       _date.today().strftime("%Y-%m-%d"),
    }


def _build_macro_fit(macro_agent: dict) -> dict:
    """从 MacroAgent 分析推导宏观适配度（B 级）"""
    key_points = macro_agent.get("key_points", [])
    analysis   = macro_agent.get("analysis", [])
    signal     = macro_agent.get("signal", "neutral")

    # 从关键点提取逆风关键词
    headwind_keywords = ["逆风", "加息", "通胀", "衰退", "收紧", "dollar强", "利率"]
    tailwind_keywords = ["顺风", "降息", "宽松", "流动性", "美元弱", "降息预期"]

    text = " ".join(key_points + analysis)
    headwinds = [kw for kw in headwind_keywords if kw in text]
    tailwinds = [kw for kw in tailwind_keywords if kw in text]

    if signal == "bullish":
        assessment = "favorable"
    elif signal == "bearish":
        assessment = "challenging"
    else:
        assessment = "neutral"

    return {
        "active_headwinds": headwinds[:3],
        "active_tailwinds": tailwinds[:3],
        "headwind_count":   len(headwinds),
        "assessment":       assessment,
    }


def _build_technical_stage(tech_agent: dict) -> dict:
    """从 TechAgent 推导技术阶段（B 级）"""
    key_points = tech_agent.get("key_points", [])
    analysis   = tech_agent.get("analysis", [])
    signal     = tech_agent.get("signal", "neutral")
    text       = " ".join(key_points + analysis)

    # 简单规则推导 Stage
    if "金叉" in text or "多头" in text or ("RSI" in text and signal == "bullish"):
        stage = "2"
        note = "上升趋势，多头结构"
    elif "死叉" in text or "空头" in text:
        stage = "3" if signal == "neutral" else "4"
        note = "动能减弱" if stage == "3" else "下跌趋势"
    elif signal == "bullish":
        stage = "2"
        note = "技术信号偏多"
    else:
        stage = "3"
        note = "技术信号混合"

    return {"stage": stage, "note": note[:60]}


def _build_master_votes(stances: dict) -> dict:
    """将 persona_stances 转换为 spec 格式的大师投票（B 级）"""
    MASTER_DOMAINS = {
        "minervini":     "technical",
        "druckenmiller": "macro",
        "marks":         "fundamental",
        "lynch":         "fundamental",
        "soros":         "macro",
        "livermore":     "technical",
        "taleb":         "fundamental",
    }

    votes = {}
    bullish_count = neutral_count = bearish_count = 0
    concern_tally = {"technical": 0, "macro": 0, "fundamental": 0, "liquidity": 0}

    for master, data in stances.items():
        if not isinstance(data, dict):
            continue
        signal = data.get("signal", "neutral")
        conf   = data.get("confidence", 50)
        arg    = data.get("core_argument", "")[:60]
        inv    = data.get("invalidation", "")

        if signal == "bullish":
            supports = "strong_yes" if conf >= 70 else "yes"
            direction = "add" if conf >= 75 else "hold"
            bullish_count += 1
        elif signal == "bearish":
            supports = "no"
            direction = "reduce" if conf < 70 else "exit"
            bearish_count += 1
        else:
            supports = "neutral"
            direction = "hold"
            neutral_count += 1

        primary_concern = MASTER_DOMAINS.get(master, "fundamental")
        concern_tally[primary_concern] += 1

        votes[master] = {
            "supports_holding":      supports,
            "primary_concern_type":  primary_concern,
            "position_direction":    direction,
            "core_argument":         arg,
        }

    # 计算 dominant_concern
    max_count = max(concern_tally.values()) if concern_tally else 0
    top_concerns = [k for k, v in concern_tally.items() if v == max_count]
    dominant = top_concerns[0] if len(top_concerns) == 1 else "none"

    votes["_summary"] = {
        "bullish_count":    bullish_count,
        "neutral_count":    neutral_count,
        "bearish_count":    bearish_count,
        "dominant_concern": dominant,
    }
    return votes


def _compute_unified_confidence(stances: dict, cio_signals: dict) -> int:
    """计算综合置信度（1-5 整数）"""
    if not stances:
        overall = cio_signals.get("signal", "neutral")
        return {"bullish": 4, "neutral": 3, "bearish": 2}.get(overall, 3)

    confs = [v.get("confidence", 50) for v in stances.values()
             if isinstance(v, dict) and "confidence" in v]
    if not confs:
        return 3
    avg = sum(confs) / len(confs)
    # 映射到 1-5
    if avg >= 80:  return 5
    if avg >= 65:  return 4
    if avg >= 50:  return 3
    if avg >= 35:  return 2
    return 1


def _infer_main_tensions(tech_stage: str, macro_fit: dict,
                          thesis_score: int, lifecycle: str,
                          tail_risk_pct: float) -> list:
    """规则推导主要矛盾（从枚举集合多选）"""
    tensions = []
    if macro_fit.get("headwind_count", 0) >= 2 and thesis_score >= 7:
        tensions.append("strong_fundamentals_macro_headwind")
    if lifecycle == "late" and thesis_score >= 7:
        tensions.append("intact_thesis_late_lifecycle")
    if tech_stage in ("3", "4"):
        tensions.append("bullish_masters_poor_technical")
    if tail_risk_pct and tail_risk_pct > 25:
        tensions.append("good_quality_poor_liquidity")
    if not tensions:
        tensions.append("none")
    return tensions


def _apply_resolution_rules(tech_stage: str, macro_fit: dict,
                              lifecycle: str, tensions: list,
                              unified_conf: int, tail_risk_pct: float) -> tuple[str, str]:
    """规则推导 resolution_logic 和 strategic_stance（第一条命中即停止）"""
    if tech_stage in ("3", "4"):
        logic = "technical_wins"
        stance = "reduce" if unified_conf >= 3 else "exit_ready"
        return logic, stance
    if macro_fit.get("headwind_count", 0) >= 3:
        return "macro_wins", "hold_reduced"
    if lifecycle == "late":
        return "lifecycle_wins", "reduce"
    if tail_risk_pct and tail_risk_pct > 30:
        adj = {"strong_hold": "hold", "hold": "hold_reduced",
               "hold_reduced": "reduce"}.get(
            {5: "strong_hold", 4: "hold", 3: "hold_reduced"}.get(unified_conf, "reduce"), "reduce")
        return "inconclusive", adj
    # 默认：fundamentals_wins
    stance = {5: "strong_hold", 4: "hold", 3: "hold_reduced",
               2: "reduce", 1: "reduce"}.get(unified_conf, "hold")
    return "fundamentals_wins", stance


def _build_company_intro(sym: str, fund: dict, pos_cfg: dict) -> str:
    """构建公司简介（A 级，从现有数据拼合）"""
    thesis = pos_cfg.get("thesis", "")
    sector = fund.get("sector", "")
    name   = fund.get("long_name", sym)
    return f"{name}（{sym}）{' — ' + sector if sector else ''}。{thesis}"[:200]


def _build_core_facts_and_risks(agents: dict) -> tuple[list, list]:
    """从各 Agent key_points 提取核心支撑事实和主要风险"""
    facts, risks = [], []
    for agent, data in agents.items():
        if not isinstance(data, dict):
            continue
        kps = data.get("key_points", [])
        sig = data.get("signal", "neutral")
        for kp in kps[:2]:
            kp_str = f"[{agent.replace('Agent','')}] {kp}"[:80]
            if sig in ("bullish",):
                facts.append(kp_str)
            elif sig in ("bearish",):
                risks.append(kp_str)
    return facts[:3], risks[:3]


# ── 主函数 ─────────────────────────────────────────────────────────────────────

def build_strategic_memo(sym: str, date: str | None = None,
                          base_dir: str = BASE,
                          pos_sym: str | None = None) -> dict | None:
    """
    构建 strategic_memo_{sym}.json。
    pos_sym: 持仓数据 sym（杠杆 ETF 场景：LITE 分析但持仓在 LITX）
    需要 cio.py --phases 0123 已运行且结果文件存在。
    """
    sym_upper = sym.upper()
    today     = date or _date.today().strftime("%Y-%m-%d")

    # ── 读取所有数据源 ────────────────────────────────────────────────────────
    cio_sigs   = _load_cio_signals(sym_upper, today)
    agents     = _load_agent_reports(sym_upper, cio_signals=cio_sigs)
    stances    = _load_latest_persona_stances(sym_upper)
    fund       = _load_fundamentals(sym_upper)
    # pos_sym 允许从不同标的读持仓（杠杆 ETF 用底层分析，持仓在 ETF）
    pos_cfg    = _load_position_cfg((pos_sym or sym_upper).upper())

    # 必须有 CIO 信号才生成
    if not cio_sigs and not agents:
        print(f"  ⚠️ {sym_upper}: 无 CIO 数据，跳过")
        return None

    # ── 从 per-sym 文件读取丰富数据（需要 Task 1 先运行）────────────────────
    agent_analysis = load_agent_analysis_per_sym(sym_upper, today)
    if not agent_analysis:
        # fallback: 从 cio_signals 构建简化版本
        agent_analysis = {}
        for key, ag_name in [("tech","TechAgent"),("fund","FundAgent"),
                              ("macro","MacroAgent"),("risk","RiskAgent"),
                              ("sentiment","SentimentAgent"),("sector","SectorAgent")]:
            ag_data = agents.get(ag_name, {})
            if ag_data:
                agent_analysis[key] = {
                    "signal": ag_data.get("signal","neutral"),
                    "confidence": ag_data.get("confidence",50),
                    "analysis": ag_data.get("analysis",[]),
                    "key_points": ag_data.get("key_points",[]),
                    "conclusion": ag_data.get("conclusion",{}),
                }

    debate_highlights = load_debate_highlights(sym_upper, today)
    
    # 尝试多种途径拉取并确认当前市价 cur_price，用来作为 position_context 与 scenarios 的绝对非零基准价
    cur_price = fund.get("cur")
    if cur_price is None:
        try:
            dv_path = os.path.join(base_dir, "data_verified.json")
            if os.path.exists(dv_path):
                dv = _load(dv_path)
                if dv.get("symbol", "").upper() == sym_upper:
                    cur_price = dv.get("fields", {}).get("close", {}).get("value")
        except Exception:
            pass
    if cur_price is None:
        import time as _time
        for _attempt in range(3):
            try:
                import yfinance as yf
                ticker = yf.Ticker(sym_upper)
                _info = ticker.info or {}
                cur_price = _info.get("currentPrice") or _info.get("regularMarketPrice")
                if cur_price:
                    break
            except Exception as e:
                err_str = str(e)
                if 'SSL' in err_str or 'TLS' in err_str or 'curl' in err_str.lower():
                    print(f"  [memo] yfinance SSL retry ({_attempt+1}/3)")
                    _time.sleep(2 * (_attempt + 1))
                    continue
                break
    if cur_price is None or not isinstance(cur_price, (int, float)) or cur_price <= 0:
        cur_price = 100.0

    position_context  = build_position_context(sym_upper, cur_price=cur_price, base_dir=BASE, pos_sym=pos_sym)
    scenarios         = build_scenarios(sym_upper, cur_price=cur_price, base_dir=BASE, pos_sym=pos_sym)

    # ── 丰富现有字段 ──────────────────────────────────────────────────────────
    # company_intro: 从 FundAgent 补充
    fund_ag = agent_analysis.get("fund", {})
    # company_intro：优先从 fundamentals 的 description（公司真实业务描述）
    # 其次才是 FundAgent key_points（财务指标，不适合作公司简介）
    company_intro_rich = (
        fund.get("description","")[:200]          # 公司业务描述（最理想）
        or fund.get("long_name","")               # 公司全名（次选）
        or "; ".join(fund_ag.get("key_points", [])[:2])  # FundAgent 财务点（fallback）
        or pos_cfg.get("thesis", "")
    )[:200]

    # core_supporting_facts / main_risks: 从 per-sym agent_analysis 提取（不用全局 agents 文件）

    tech_agent  = agents.get("TechAgent", {})
    fund_agent  = agents.get("FundAgent", {})
    macro_agent = agents.get("MacroAgent", {})
    risk_agent  = agents.get("RiskAgent", {})

    # ── 构建各层 ──────────────────────────────────────────────────────────────

    # Foundation
    fundamentals_snap = _build_fundamentals_snapshot(fund)
    company_intro     = _build_company_intro(sym_upper, fund, pos_cfg)
    sector_intro      = f"所在板块：{fund.get('sector', '未知')}。{fund.get('industry', '')}"[:150]

    # Support & Risk
    macro_fit    = _build_macro_fit(macro_agent)
    tech_stage   = _build_technical_stage(tech_agent)
    # 优先用 per-sym agent_analysis（并行安全），fallback 全局 agents
    _aa_facts, _aa_risks = [], []
    for key, data in agent_analysis.items():
        if not isinstance(data, dict):
            continue
        sig = data.get("signal", "neutral")
        for kp in data.get("key_points", [])[:2]:
            entry = f"[{key.upper()}] {kp}"[:80]
            if sig == "bullish":
                _aa_facts.append(entry)
            elif sig == "bearish":
                _aa_risks.append(entry)
    if _aa_facts or _aa_risks:
        core_facts, main_risks = _aa_facts[:3], _aa_risks[:3]
    else:
        core_facts, main_risks = _build_core_facts_and_risks(agents)

    # Tail risk（来自 RiskAgent）
    risk_kps = risk_agent.get("key_points", [])
    tail_note = "; ".join(risk_kps[:2])[:100]
    tail_loss = None
    try:
        beta = float(fund.get("beta", 1.5) or 1.5)
        tail_loss = round(beta * 15, 1)   # 粗估：beta × SPY 黑天鹅 15%
    except Exception:
        pass

    tail_risk = {
        "max_loss_scenario":      tail_note,
        "structural_fragility":   risk_agent.get("conclusion", {}).get("boundary", "")[:100],
        "estimated_max_loss_pct": tail_loss,
    }

    # Liquidity env（从 MacroAgent 推导）
    macro_signal = macro_agent.get("signal", "neutral")
    liquidity_env = {
        "fed_direction":        "easing" if macro_signal == "bullish" else
                                "tightening" if macro_signal == "bearish" else "neutral",
        "credit_spread_trend":  "narrowing" if macro_signal == "bullish" else
                                "widening" if macro_signal == "bearish" else "stable",
        "institutional_flow":   "inflow" if macro_signal == "bullish" else
                                "outflow" if macro_signal == "bearish" else "neutral",
        "note":                 "; ".join(macro_agent.get("key_points", [])[:1])[:80],
    }

    # Sector RS（来自 SectorAgent）
    sector_agent = agents.get("SectorAgent", {})
    sec_signal   = sector_agent.get("signal", "neutral")
    sector_rs = {
        "trend":       "outperforming" if sec_signal == "bullish" else
                       "underperforming" if sec_signal == "bearish" else "inline",
        "period_days": 30,
        "note":        "; ".join(sector_agent.get("key_points", [])[:1])[:60],
    }

    # Next catalyst（从 positions.json）
    cat_type    = pos_cfg.get("catalyst_type", "")
    cat_deadline = pos_cfg.get("catalyst_deadline", "unknown")
    next_catalyst = {
        "event":      cat_type or "earnings",
        "date":       cat_deadline or "unknown",
        "importance": "high" if pos_cfg.get("catalyst_persistence") == "structural"
                      else "medium" if cat_type else "low",
    }

    # ── Judgment 层 ────────────────────────────────────────────────────────────
    master_votes = _build_master_votes(stances)

    # thesis_quality_score：从大师投票比例 + 基本面质量推算
    total_masters = len(stances)
    bullish_ratio = master_votes.get("_summary", {}).get("bullish_count", 0) / max(total_masters, 1)
    pe = fundamentals_snap.get("pe_ttm") or 999
    thesis_score = min(10, max(1, int(bullish_ratio * 7 + (2 if pe < 50 else 1) + (1 if tail_loss and tail_loss < 25 else 0))))

    # thesis_lifecycle：从 positions.json 论点状态推导
    thesis_status = pos_cfg.get("thesis_status", "intact")
    lifecycle_stage = "early" if thesis_status == "intact" else "late" if thesis_status == "broken" else "mid"

    # falsifiability_quality：从 falsification_conditions 字段推断
    falsif = pos_cfg.get("falsification_conditions", [])
    if len(falsif) >= 2:
        falsif_quality = {"rating": "clear", "note": f"{len(falsif)} 条可观测证伪条件"}
    elif falsif:
        falsif_quality = {"rating": "adequate", "note": "有证伪条件但较少"}
    else:
        falsif_quality = {"rating": "vague", "note": "缺少明确证伪条件"}

    unified_conf = _compute_unified_confidence(stances, cio_sigs)

    best_vehicle = {
        "is_best_vehicle": True,   # 简化：用户持有即认为是选好的工具
        "alternatives":    [],
        "reason":          f"用户持有 {sym_upper}，保留为当前工具",
    }

    # ── Synthesis 层（规则推导，完全确定性）────────────────────────────────────
    tensions = _infer_main_tensions(
        tech_stage["stage"], macro_fit, thesis_score,
        lifecycle_stage, tail_loss or 0,
    )
    resolution_logic, strategic_stance = _apply_resolution_rules(
        tech_stage["stage"], macro_fit, lifecycle_stage,
        tensions, unified_conf, tail_loss or 0,
    )

    # key_condition（从综合决策推导）
    key_condition = (
        f"技术面 Stage {tech_stage['stage']} 是关键制约因素" if resolution_logic == "technical_wins"
        else f"宏观逆风（{macro_fit['headwind_count']} 项）是主要压力"  if resolution_logic == "macro_wins"
        else f"论点已进入 {lifecycle_stage} 阶段，需评估目标" if resolution_logic == "lifecycle_wins"
        else f"基本面论点 intact（{thesis_score}/10），维持持有"
    )[:50]

    synthesis = {
        "main_tensions":    tensions,
        "resolution_logic": resolution_logic,
        "strategic_stance": strategic_stance,
        "confidence":       unified_conf,
        "key_condition":    key_condition,
    }

    # ── Outlook 层 ─────────────────────────────────────────────────────────────
    target_pct = pos_cfg.get("target_pct", 15)
    exit_logic = {
        "target_reached":         f"持仓达到目标收益 {target_pct}% 时分批减仓",
        "proactive_exit_signal":  "; ".join(falsif[:1])[:80] if falsif else "论点破裂信号出现时",
    }
    valid_until = pos_cfg.get("catalyst_deadline") or "next_catalyst_event"

    # ── 组装完整 memo ──────────────────────────────────────────────────────────
    memo = {
        "sym":           sym_upper,
        "analysis_date": today,
        "analyst":       "CIO-phases0123",

        "foundation": {
            "company_intro":        company_intro,
            "sector_intro":         sector_intro,
            "fundamentals_snapshot": fundamentals_snap,
        },

        "support_and_risk": {
            "core_supporting_facts": core_facts,
            "main_risks":            main_risks,
            "tail_risk":             tail_risk,
            "macro_fit":             macro_fit,
            "liquidity_env":         liquidity_env,
            "technical_stage":       tech_stage,
            "sector_relative_strength": sector_rs,
            "next_catalyst":         next_catalyst,
        },

        "judgment": {
            "thesis_quality_score": thesis_score,
            "thesis_quality_note":  f"大师 {int(bullish_ratio*100)}% 看多，基本面评分 {thesis_score}/10",
            "thesis_lifecycle_stage": {"stage": lifecycle_stage, "note": f"论点状态 {thesis_status}"},
            "falsifiability_quality": falsif_quality,
            "best_vehicle":          best_vehicle,
            "master_votes":          master_votes,
            "unified_confidence":    unified_conf,
        },

        "synthesis": synthesis,

        "outlook": {
            "exit_logic":  exit_logic,
            "valid_until": valid_until,
        },
    }

    # ── 读取 company_profile（深度画像）────────────────────────────────────────
    cp_path = os.path.join(base_dir, "findings", f"company_profile_{sym_upper}.json")
    cp = _load(cp_path)   # 可能为空 {}

    # ── 推导证伪条件（从 key_risks + bear_case + 财务指标）────────────────────
    derived_falsification = list(pos_cfg.get("falsification_conditions", []))  # 用户手填的优先
    if not derived_falsification:
        # 从 company_profile 推导
        for risk in cp.get("key_risks", [])[:2]:
            derived_falsification.append(f"【风险触发】{risk[:70]}")
        for bear in cp.get("bear_case", [])[:2]:
            derived_falsification.append(f"【空头兑现】{bear[:70]}")
        # 从财务指标推导
        rev_g = fund.get("rev_growth_pct") or 0
        if rev_g > 30:
            derived_falsification.append(f"【成长失速】营收增速从 {rev_g:.0f}% 跌破 20%，成长溢价消失")
        gm = fund.get("gross_margin") or 0
        if gm > 60:
            derived_falsification.append(f"【毛利压缩】毛利率从 {gm:.0f}% 跌破 55%，定价权丧失信号")
        # 从技术面推导
        cost = float(pos_cfg.get("cost") or pos_cfg.get("t1_cost") or 0)
        if cost > 0:
            hard_stop_auto = None  # 价格节点由 macro_strategy.py 计算，此处为占位，由 premarket_summary 覆盖
            derived_falsification.append("【技术破位】价格跌破动态止损位且放量，结构性空头确认（具体价位见 macro_strategy 节点）")

    # ── 推导支撑论据（从 moat + growth_drivers + 财务指标）──────────────────────
    enriched_facts = list(core_facts)   # 现有的 agent 分析
    if not enriched_facts or len(enriched_facts) < 3:
        # 从护城河补充
        for m in cp.get("competitive_moat", [])[:2]:
            enriched_facts.append(f"[护城河] {m[:80]}")
        # 从增长驱动补充
        for d in cp.get("growth_drivers", [])[:2]:
            enriched_facts.append(f"[增长] {d[:80]}")
        # 从财务指标补充
        fcf = fund.get("fcf_B")
        if fcf and fcf > 10:
            enriched_facts.append(f"[财务] FCF ${fcf:.0f}B，强劲现金流支撑高质量盈利")
        roe = fund.get("roe")
        if roe and roe > 30:
            enriched_facts.append(f"[财务] ROE {roe:.0f}%，资本效率优秀，竞争护城河已变现")

    # ── 推导出场逻辑（从 target_pct + cost + 催化剂 + 证伪条件）─────────────────
    cost_f = float(pos_cfg.get("cost") or pos_cfg.get("t1_cost") or 0)
    tgt_pct= float(pos_cfg.get("target_pct") or 15)
    pos_type = pos_cfg.get("position_type","thesis")
    analyst_tgt = fund.get("target_price")

    # 目标达成出场：论点型用分析师目标价而非简单的%，催化剂型在事件后
    if pos_type == "thesis" and analyst_tgt and analyst_tgt > (cost_f or 0):
        target_reached_text = (
            f"分析师目标价 ${analyst_tgt:.0f}（较成本 +{(analyst_tgt/cost_f-1)*100:.0f}%）附近分批减仓；"
            f"若基本面超预期上修目标价，延迟减仓"
        ) if cost_f else f"分析师目标价 ${analyst_tgt:.0f} 附近分批减仓"
    elif pos_type == "catalyst":
        cat_deadline = pos_cfg.get("catalyst_deadline","")
        target_reached_text = f"催化剂事件（{cat_deadline or '待定'}）完成后，无论盈亏评估是否继续持有"
    else:
        tgt_price = round(cost_f * (1 + tgt_pct/100), 2) if cost_f else None
        target_reached_text = f"达到目标收益 {tgt_pct:.0f}%（${tgt_price}）后分批减仓" if tgt_price else f"达到 {tgt_pct:.0f}% 目标收益"

    # 主动出场：证伪条件触发
    if derived_falsification:
        proactive_text = f"以下任一条件触发：① {derived_falsification[0][:60]}"
        if len(derived_falsification) > 1:
            proactive_text += f"；② {derived_falsification[1][:60]}"
    else:
        proactive_text = "论点破裂信号出现时（参见证伪条件）"

    derived_exit_logic = {
        "target_reached":         target_reached_text,
        "proactive_exit_signal":  proactive_text,
    }

    # ── 持仓策略 add_strategy 补强（如果 t2 条件为空）─────────────────────────
    if not position_context.get("add_strategy",{}).get("t2_conditions") and cost_f > 0:
        lifecycle = memo.get("judgment",{}).get("thesis_lifecycle_stage",{}).get("stage","mid")
        t2_note = ""
        if lifecycle == "late":
            t2_note = "论点进入晚期，不建议加仓"
        elif pos_type == "thesis":
            t2_note = "论点 intact + 回踩 Add1 节点（由 macro_strategy 计算）+ 缩量守住 → T2 加仓机会"
        position_context.setdefault("add_strategy",{})["t2_conditions"] = t2_note
        position_context["add_strategy"]["t2_price_floor"] = None  # 价格节点由 macro_strategy.py 计算，此处为占位，由 premarket_summary 覆盖

    # ── 新区块加入 memo ──────────────────────────────────────────────────────
    memo["position_context"]  = position_context
    memo["agent_analysis"]    = agent_analysis
    memo["debate_highlights"] = debate_highlights
    memo["scenarios"]         = scenarios
    memo["foundation"]["company_intro"] = company_intro_rich
    memo["support_and_risk"]["core_supporting_facts"] = enriched_facts   # 用推导后的
    memo["support_and_risk"]["main_risks"] = main_risks
    memo["support_and_risk"]["derived_falsification"] = derived_falsification  # 新增
    memo["outlook"]["exit_logic"] = derived_exit_logic                          # 覆盖原模板

    return memo


def write_strategic_memo(sym: str, memo: dict, base_dir: str = BASE,
                          also_write_report: bool = True) -> str:
    """
    写出 strategic_memo_{sym}.json，返回路径。
    also_write_report=True 时同时生成可读的 HTML 研究报告。
    """
    path = os.path.join(base_dir, f"strategic_memo_{sym.upper()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memo, f, indent=2, ensure_ascii=False)

    if also_write_report:
        try:
            from agents.report_viewer import write_research_report
            date_str = memo.get("analysis_date", _date.today().strftime("%Y-%m-%d"))
            write_research_report(sym, date_str, base_dir=base_dir)
        except Exception as e:
            print(f"  ⚠️ 研究报告生成失败: {e}")

    return path


def main(syms: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(description="生成 strategic_memo")
    parser.add_argument("syms", nargs="*", help="标的代码列表")
    parser.add_argument("--pos-sym", default=None,
                        help="持仓数据 sym（杠杆ETF场景：如 --pos-sym LITX 让 LITE 读 LITX 的持仓）")
    args = parser.parse_args()

    cli_syms = args.syms or syms or []
    pos_sym  = args.pos_sym

    today = _date.today().strftime("%Y-%m-%d")
    if not cli_syms:
        import glob
        files = glob.glob(os.path.join(LEARN_DIR, f"cio_signals_{today}_*.json"))
        cli_syms = [os.path.basename(f).replace(f"cio_signals_{today}_","").replace(".json","")
                    for f in files]

    if not cli_syms:
        print("无可用 CIO 信号，请先运行: python3.12 agents/cio.py SYM --phases 0123")
        return

    if pos_sym and len(cli_syms) > 1:
        print("⚠️ --pos-sym 只能与单标的一起使用")
        return

    print(f"\n生成 strategic_memo（{len(cli_syms)} 只标的）\n")
    for sym in cli_syms:
        memo = build_strategic_memo(sym, today, pos_sym=pos_sym)
        if memo:
            path = write_strategic_memo(sym, memo)
            sc   = memo.get("synthesis", {})
            suffix = f" [持仓读 {pos_sym}]" if pos_sym else ""
            print(f"  {sym}: stance={sc.get('strategic_stance','?')} "
                  f"conf={sc.get('confidence','?')}/5 "
                  f"-> [OK] {os.path.basename(path)}{suffix}")
            
            if pos_sym:
                import copy
                pos_memo = copy.deepcopy(memo)
                pos_memo["sym"] = pos_sym.upper()
                pos_path = write_strategic_memo(pos_sym, pos_memo)
                print(f"  {pos_sym.upper()}: [leverage-dual] stance={sc.get('strategic_stance','?')} "
                      f"conf={sc.get('confidence','?')}/5 "
                      f"-> [OK] {os.path.basename(pos_path)}")


if __name__ == "__main__":
    main()
