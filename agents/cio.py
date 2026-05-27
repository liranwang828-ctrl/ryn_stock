import sys, os, json, argparse, subprocess, time, shutil
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import (BASE, BOARD_PATH, VERIFIED_PATH, STRATEGY_PATH,
                              FINDINGS_DIR, LOCK_PATH, PERSONA_SYNTH_PATH, EXIT_OK, EXIT_FAIL)

PYTHON = sys.executable
AGENTS_DIR = os.path.join(BASE, "agents")

ANALYSIS_AGENTS = [
    "tech_agent", "fund_agent", "macro_agent",
    "sentiment_agent", "risk_agent",
    "sector_agent", "community_agent",
]
AGENT_NAMES = {
    "tech_agent":       "TechAgent",
    "fund_agent":       "FundAgent",
    "macro_agent":      "MacroAgent",
    "sentiment_agent":  "SentimentAgent",
    "risk_agent":       "RiskAgent",
    "sector_agent":     "SectorAgent",
    "community_agent":  "CommunityAgent",
}

def run(script, args, timeout=120):
    path = os.path.join(AGENTS_DIR, script + ".py")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run([PYTHON, path] + args, cwd=BASE, env=env, timeout=timeout)

def acquire_lock(symbol):
    if os.path.exists(LOCK_PATH):
        lock = json.load(open(LOCK_PATH, encoding="utf-8"))
        age  = time.time() - lock.get("start_time", 0)
        if age < 600:
            print(f"[CIO] 已有分析进行中（{age:.0f}s），排队等待...")
            return False
        print("[CIO] 检测到过期锁，清除后继续")
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        json.dump({"start_time": time.time(), "symbol": symbol}, f, ensure_ascii=False)
    return True

def release_lock():
    try: os.remove(LOCK_PATH)
    except FileNotFoundError: pass


# ── 并行执行支持 ──────────────────────────────────────────────────────────────

def _get_rundir(sym):
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    rundir = os.path.join(BASE, "runs", f"{sym}_{today}")
    os.makedirs(os.path.join(rundir, "findings"), exist_ok=True)
    return rundir


def run_parallel(symbols, phases="0123", timeout=420):
    """
    对多个标的并行运行 CIO，每个标的使用独立工作目录，互不冲突。
    返回 (results_dict, rundirs_dict)
      results_dict: {sym: strategy_result_json | {"error": ...}}
      rundirs_dict: {sym: rundir_path}
    """
    procs, rundirs = {}, {}
    for sym in symbols:
        rundir = _get_rundir(sym)
        rundirs[sym] = rundir
        env = dict(os.environ, STOCK_CIO_RUNDIR=rundir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        p = subprocess.Popen(
            [PYTHON, os.path.join(AGENTS_DIR, "cio.py"), sym, "--phases", phases],
            cwd=BASE, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        procs[sym] = p
        print(f"[CIO并行] 🚀 {sym} 已启动 (pid={p.pid})")

    results = {}
    for sym, p in procs.items():
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            print(f"[CIO并行] ⏱️ {sym} 超时，已终止")
        strat_path = os.path.join(rundirs[sym], "strategy_result.json")
        if os.path.exists(strat_path):
            try:
                results[sym] = json.load(open(strat_path, encoding="utf-8"))
            except Exception:
                results[sym] = {"error": "strategy_result.json 解析失败"}
        else:
            results[sym] = {"error": "strategy_result.json 未生成（CIO可能中途失败）"}

    return results, rundirs


def phase0(symbol):
    print(f"[Phase 0] 拉取 {symbol} 数据...")
    r = run("data_agent", [symbol])
    if r.returncode == 2:
        print(f"[Phase 0] 股票 {symbol} 未找到，跳过")
        return False
    if r.returncode != 0:
        print(f"[Phase 0] DataAgent 失败 (code={r.returncode})")
        return False
    r = run("verifier_agent", [])
    if r.returncode != 0:
        print(f"[Phase 0] VerifierAgent 失败")
        return False
    
    # 自动补全基础财务和画像数据链条
    print(f"[Phase 0] 自动拉取 {symbol} 财务基本面与公司画像...")
    run("quick_fundamentals", [symbol])
    run("company_profile_fetcher", [symbol])

    # 自动补全期权链前导分析数据
    print(f"[Phase 0] 自动拉取并计算 {symbol} 期权链前导指标 (GEX / IV Skew / PCR)...")
    try:
        from agents.options_chain_analyzer import OptionChainAnalyzer
        analyzer = OptionChainAnalyzer(symbol)
        opt_res = analyzer.analyze()
        if "error" not in opt_res:
            os.makedirs(FINDINGS_DIR, exist_ok=True)
            opt_path = os.path.join(FINDINGS_DIR, f"options_{symbol}.json")
            with open(opt_path, "w", encoding="utf-8") as f:
                json.dump(opt_res, f, ensure_ascii=False, indent=2)
            # 同时保存按日期命名的备份
            from datetime import date as _dt
            _date_str = str(_dt.today())
            opt_bak_path = os.path.join(FINDINGS_DIR, f"options_{symbol}_{_date_str}.json")
            with open(opt_bak_path, "w", encoding="utf-8") as f:
                json.dump(opt_res, f, ensure_ascii=False, indent=2)
            print(f"[Phase 0] 期权链前导指标成功保存至 {opt_path}")
    except Exception as e:
        print(f"[Phase 0] 自动拉取期权链失败: {e}")

    print("[Phase 0] 完成")
    return True

def phase1(symbol):
    print(f"[Phase 1] 并行启动 7 个 analysis agent...")
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    open(BOARD_PATH, "w", encoding="utf-8").close()

    procs = []
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    for agent in ANALYSIS_AGENTS:
        p = subprocess.Popen([PYTHON, os.path.join(AGENTS_DIR, agent + ".py"), symbol],
                             cwd=BASE, env=env)
        procs.append((agent, p))

    for agent, p in procs:
        try:
            p.wait(timeout=90)
        except subprocess.TimeoutExpired:
            p.kill()
            print(f"[Phase 1] {agent} 超时，已终止")

    for agent in ANALYSIS_AGENTS:
        path = os.path.join(FINDINGS_DIR, f"{AGENT_NAMES[agent]}.json")
        if os.path.exists(path):
            msg = json.load(open(path, encoding="utf-8"))
            if msg:
                with open(BOARD_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    # 保存 per-symbol agent 文件（避免多标的时互相覆盖）
    from datetime import date as _dt
    _date_str = str(_dt.today())
    for _agent in ANALYSIS_AGENTS:
        _src = os.path.join(FINDINGS_DIR, f"{AGENT_NAMES[_agent]}.json")
        if os.path.exists(_src):
            _dst = os.path.join(FINDINGS_DIR, f"{AGENT_NAMES[_agent]}_{symbol}_{_date_str}.json")
            try:
                import shutil
                shutil.copy2(_src, _dst)
            except Exception:
                pass
    print("[Phase 1] 完成")


def phase1_5(symbol):
    """
    Persona 层：7位大师读取所有 Domain Agent 报告，
    通过 evaluate_with_questions 输出初始立场。
    """
    print("[Phase 1.5] 大师层分析...")
    try:
        from agents.debate_engine import collect_domain_findings, collect_persona_stances
        findings = collect_domain_findings()
        stances  = collect_persona_stances(symbol, findings)

        for master, stance in stances.items():
            signal  = stance.get("signal", "?")
            conf    = stance.get("confidence", 0)
            arg     = stance.get("core_argument", "")[:50]
            stopped = f" [停于{stance['stopped_at']}]" if stance.get("stopped_at") else ""
            print(f"  [{master}] {signal}({conf}%) — {arg}{stopped}")

        print("[Phase 1.5] 完成")
        return stances
    except Exception as e:
        print(f"[Phase 1.5] 失败: {e}")
        return {}


def check_consensus(board):
    _AGENTS = ["TechAgent","FundAgent","MacroAgent","SentimentAgent","RiskAgent","SectorAgent"]
    latest = {}
    for msg in board:
        if msg.get("msg_type") not in ("initial_finding", "revision"): continue
        a = msg.get("from")
        if a not in _AGENTS: continue
        if a not in latest or msg.get("revision", 0) > latest[a].get("revision", 0):
            latest[a] = msg
    signals = [m["signal"] for m in latest.values()]
    if len(signals) < 5: return False
    majority = max(set(signals), key=signals.count)
    if signals.count(majority) < 4: return False
    challenges = [m for m in board if m.get("msg_type") == "challenge"]
    for ch in challenges:
        tgt = ch.get("target")
        responded = any(m.get("from") == tgt and m.get("msg_type") in ("revision","endorsement")
                        and m["timestamp"] > ch["timestamp"] for m in board)
        if not responded: return False
    return True

def phase2(symbol):
    print("[Phase 2] 开始辩论...")
    for round_num in range(1, 3):
        print(f"[Phase 2] 第 {round_num} 轮")
        round_start = time.time()

        for agent_script in ANALYSIS_AGENTS:
            agent_name = AGENT_NAMES[agent_script]
            if time.time() - round_start > 300:
                print(f"[Phase 2] 超时，强制结束第 {round_num} 轮")
                break

            out_path = os.path.join(FINDINGS_DIR, f"{agent_name}_r{round_num}.json")
            try:
                env = dict(os.environ)
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
                subprocess.run(
                    [PYTHON, os.path.join(AGENTS_DIR, agent_script + ".py"), symbol, "--round", str(round_num)],
                    cwd=BASE, env=env, timeout=60
                )
            except subprocess.TimeoutExpired:
                print(f"[Phase 2] {agent_name} 超时")
                continue

            if os.path.exists(out_path):
                msg = json.load(open(out_path, encoding="utf-8"))
                if not msg: continue
                with open(BOARD_PATH, "a", encoding="utf-8") as bf:
                    bf.write(json.dumps(msg, ensure_ascii=False) + "\n")

                # Challenge → 立即运行被质疑方回应
                if msg.get("msg_type") == "challenge":
                    target_agent = msg.get("target", "")
                    target_script = next(
                        (s for s, n in AGENT_NAMES.items() if n == target_agent), None
                    )
                    if target_script:
                        print(f"[Phase 2]   ⚡ {agent_name} 质疑 {target_agent}，等待回应...")
                        resp_path = os.path.join(FINDINGS_DIR, f"{target_agent}_r{round_num}_resp.json")
                        try:
                            env = dict(os.environ)
                            env["PYTHONIOENCODING"] = "utf-8"
                            env["PYTHONUTF8"] = "1"
                            subprocess.run(
                                [PYTHON, os.path.join(AGENTS_DIR, target_script + ".py"),
                                 symbol, "--round", str(round_num)],
                                cwd=BASE, env=env, timeout=60
                            )
                            # 被质疑方的普通输出路径
                            normal_out = os.path.join(FINDINGS_DIR, f"{target_agent}_r{round_num}.json")
                            if os.path.exists(normal_out):
                                resp = json.load(open(normal_out, encoding="utf-8"))
                                if resp:
                                    with open(BOARD_PATH, "a", encoding="utf-8") as bf:
                                        bf.write(json.dumps(resp, ensure_ascii=False) + "\n")
                        except subprocess.TimeoutExpired:
                            print(f"[Phase 2]   {target_agent} 回应超时")

                if msg.get("msg_type") == "data_challenge":
                    field = msg.get("target_field", "")
                    try:
                        env = dict(os.environ)
                        env["PYTHONIOENCODING"] = "utf-8"
                        env["PYTHONUTF8"] = "1"
                        subprocess.run(
                            [PYTHON, os.path.join(AGENTS_DIR, "verifier_agent.py"),
                             "--field", field, "--round", str(round_num)],
                            cwd=BASE, env=env, timeout=60
                        )
                    except subprocess.TimeoutExpired:
                        pass
                    vout = os.path.join(FINDINGS_DIR, f"verifier_r{round_num}_{field}.json")
                    if os.path.exists(vout):
                        vmsg = json.load(open(vout, encoding="utf-8"))
                    else:
                        vmsg = {"msg_type": "verify_response", "from": "VerifierAgent",
                                "target_field": field, "result": "unresolvable",
                                "reason": "timeout", "timestamp": datetime.now(timezone.utc).isoformat()}
                    with open(BOARD_PATH, "a", encoding="utf-8") as bf:
                        bf.write(json.dumps(vmsg, ensure_ascii=False) + "\n")

        board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()]
        if check_consensus(board):
            print(f"[Phase 2] 共识达成，提前结束（第 {round_num} 轮）")
            break

    print("[Phase 2] 辩论结束")
    # 保存 per-symbol debate 文件
    from datetime import date as _dt
    _date_str = str(_dt.today())
    _debate_path = os.path.join(FINDINGS_DIR, f"debate_{symbol}_{_date_str}.jsonl")
    try:
        _board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()]
        with open(_debate_path, "w", encoding="utf-8") as _df:
            for _msg in _board:
                _df.write(json.dumps(_msg, ensure_ascii=False) + "\n")
    except Exception:
        pass


def phase2_persona(symbol, stances, question_type="日内/短线交易"):
    """
    Persona 层辩论协议：矛盾识别 + 定向回应（最多1轮）+ 加权裁决
    """
    if not stances:
        print("[Phase 2-Persona] 无大师立场数据，跳过")
        return {}

    print("[Phase 2-Persona] 矛盾识别 + 定向回应...")
    try:
        from agents.debate_engine import (detect_contradictions,
                                          run_targeted_response, weighted_synthesis)
        from agents.question_router import get_primary_masters

        contradictions = detect_contradictions(stances)
        print(f"  识别到 {len(contradictions)} 对矛盾")

        all_responses = {}
        for persona_a, persona_b in contradictions:
            print(f"  ⚡ {persona_a} vs {persona_b}")
            responses = run_targeted_response(symbol, persona_a, persona_b, stances)
            all_responses.update(responses)

        primary = get_primary_masters(question_type)
        synthesis = weighted_synthesis(stances, all_responses, primary_masters=primary)

        print(f"\n[Phase 2-Persona] 大师层综合：{synthesis['consensus_signal']} "
              f"({synthesis['weighted_confidence']}%)")
        if synthesis.get("conditional_map"):
            print(f"  主角分歧，条件映射：{synthesis['conditional_map']}")
        if synthesis.get("unresolved_contradictions"):
            print(f"  未解决矛盾：{synthesis['unresolved_contradictions']}")

        # 保存供 strategy_agent 读取（并行隔离：写入各自 rundir）
        with open(PERSONA_SYNTH_PATH, "w", encoding="utf-8") as f:
            json.dump(synthesis, f, ensure_ascii=False, indent=2)

        print("[Phase 2-Persona] 完成")
        return synthesis
    except Exception as e:
        print(f"[Phase 2-Persona] 失败: {e}")
        return {}


def _infer_question_type(symbol: str) -> str:
    """
    Phase 0 完成后，从 data_verified.json + 盘前分析自动推断问题类型。
    推断优先级：催化剂强度 > 高空头轧空 > 中线成长 > VCP日内 > 高Beta风险 > 默认日内
    """
    try:
        fields = {}
        if os.path.exists(VERIFIED_PATH):
            raw = json.load(open(VERIFIED_PATH, encoding="utf-8")).get("fields", {})
            fields = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in raw.items()}

        # 盘前催化剂强度（从 premarket_analysis 读）
        from datetime import date
        pm_path = os.path.join(BASE, f"premarket_analysis_{date.today()}.json")
        catalyst_strength = 1
        short_pct = 0.0
        if os.path.exists(pm_path):
            pm = json.load(open(pm_path, encoding="utf-8"))
            sym_data = pm.get("stocks", {}).get(symbol, {})
            catalyst_strength = sym_data.get("catalyst_strength", 1)
            # short_pct 从 premarket 5维扫描不一定有，用 verified 的 beta 做代理

        rev_growth  = fields.get("revenue_growth") or 0
        price_3m    = fields.get("price_chg_3m")  or 0
        beta        = fields.get("beta")           or 1.0
        vcp         = fields.get("vcp_detected")   or False
        rs          = fields.get("rs_vs_market")   or 0

        if catalyst_strength >= 3 or rev_growth > 2.0:
            return "催化剂分析"
        elif price_3m > 0.25 and rs > 0:
            return "中线成长股"
        elif vcp:
            return "日内/短线交易"
        elif beta and beta > 2.5:
            return "风险评估"
        else:
            return "日内/短线交易"
    except Exception:
        return "日内/短线交易"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--phases", default="0123")
    parser.add_argument("--question-type", default="日内/短线交易",
                        help="问题类型，影响主角大师选择")
    args = parser.parse_args()

    if not acquire_lock(args.symbol):
        return

    try:
        stances = {}
        if "0" in args.phases:
            ok = phase0(args.symbol)
            if not ok:
                release_lock()
                return

        if "1" in args.phases:
            phase1(args.symbol)

        # ── 自动推断问题类型（若未显式指定）────────────────────────
        question_type = args.question_type  # CLI 显式传入优先
        if question_type == "日内/短线交易":  # 默认值 → 尝试自动推断
            question_type = _infer_question_type(args.symbol)
        from agents.question_router import get_primary_masters as _gpm
        print(f"[问题分类] {question_type}  → 主角大师: {_gpm(question_type)}")

        # 新增：Phase 1.5 大师层分析
        stances = phase1_5(args.symbol)

        if "2" in args.phases:
            phase2(args.symbol)
            phase2_persona(args.symbol, stances, question_type=question_type)

        if "3" in args.phases:
            print("[Phase 3] 汇总输出...")
            run("strategy_agent", [args.symbol])
            run("macro_strategy", [args.symbol])
            # 保存 agent 信号供 harvest_agent 精度追踪
            try:
                from datetime import date as _date
                _signals_path = os.path.join(BASE, "learning",
                                             f"cio_signals_{_date.today()}_{args.symbol}.json")
                if os.path.exists(STRATEGY_PATH):
                    _result = json.load(open(STRATEGY_PATH, encoding="utf-8"))
                    _signals_data = {
                        "sym": args.symbol,
                        "date": str(_date.today()),
                        "signal": _result.get("signal"),
                        "agent_signals": _result.get("agent_signals", {}),
                    }
                    os.makedirs(os.path.dirname(_signals_path), exist_ok=True)
                    with open(_signals_path, "w", encoding="utf-8") as f:
                        json.dump(_signals_data, f, indent=2, ensure_ascii=False)
                    print(f"[cio] agent 信号已保存到 {_signals_path}")
            except Exception as _e:
                pass  # 不阻断主流程
            run("report_agent",   [args.symbol])

            # ── narrative 叙述文件（供 report_viewer 展示完整分析文本）──────────
            try:
                from datetime import date as _dt_n
                _date_str_n = str(_dt_n.today())
                _narrative_path = os.path.join(FINDINGS_DIR, f"narrative_{args.symbol}_{_date_str_n}.json")

                # 读取辩论内容（来自 BOARD_PATH）
                _board_n = []
                if os.path.exists(BOARD_PATH):
                    _board_n = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()]

                # 读取大师立场（persona_stances.jsonl）
                _stances_path = os.path.join(BASE, "persona_stances.jsonl")
                _sym_stances = {}
                if os.path.exists(_stances_path):
                    _all_stances = [json.loads(l) for l in open(_stances_path, encoding="utf-8") if l.strip()]
                    _latest = next((s for s in reversed(_all_stances)
                                    if s.get("symbol","").upper() == args.symbol.upper()
                                    and s.get("msg_type") == "persona_stances"), {})
                    _sym_stances = _latest.get("stances", {})

                # 各 agent 叙述段落（从 per-sym 文件读取）
                _AGENT_MAP_N = {
                    "TechAgent": "tech", "FundAgent": "fund", "MacroAgent": "macro",
                    "RiskAgent": "risk", "SentimentAgent": "sentiment", "SectorAgent": "sector",
                }
                _agent_narratives = {}
                for _ag_n, _key_n in _AGENT_MAP_N.items():
                    _ap_n = os.path.join(FINDINGS_DIR, f"{_ag_n}_{args.symbol}_{_date_str_n}.json")
                    if os.path.exists(_ap_n):
                        _d_n = json.load(open(_ap_n, encoding="utf-8"))
                        _paras_n = _d_n.get("analysis", [])
                        _kps_n   = _d_n.get("key_points", [])
                        _concl_n = _d_n.get("conclusion", {})
                        _narrative_text = " ".join(_paras_n[:3]) if _paras_n else "；".join(_kps_n[:3])
                        _agent_narratives[_key_n] = {
                            "signal":          _d_n.get("signal", "neutral"),
                            "confidence":      _d_n.get("confidence", 50),
                            "narrative":       _narrative_text,
                            "key_points":      _kps_n[:4],
                            "conclusion_text": _concl_n.get("judgment",""),
                            "boundary_text":   _concl_n.get("boundary",""),
                        }

                # 大师叙述
                _master_narratives = {}
                for _master_n, _mdata_n in _sym_stances.items():
                    if not isinstance(_mdata_n, dict):
                        continue
                    _master_narratives[_master_n] = {
                        "signal":       _mdata_n.get("signal","neutral"),
                        "confidence":   _mdata_n.get("confidence", 50),
                        "argument":     _mdata_n.get("core_argument","")[:120],
                        "direction":    _mdata_n.get("position_direction","hold"),
                        "invalidation": _mdata_n.get("invalidation","")[:80],
                    }

                # 辩论摘要：优先 challenge/response，无则用 initial_finding 各 agent 立场
                _debate_dialogue = []
                _challenge_msgs = [m for m in _board_n
                                   if m.get("msg_type") in ("challenge","response") and m.get("content")]
                if _challenge_msgs:
                    for _msg_n in _challenge_msgs[:8]:
                        _debate_dialogue.append({
                            "from":    _msg_n.get("from","?"),
                            "type":    _msg_n.get("msg_type"),
                            "content": str(_msg_n.get("content",""))[:150],
                        })
                else:
                    # 无辩论：用各 agent 的 initial_finding 作为「立场陈述」展示
                    for _msg_n in _board_n:
                        if _msg_n.get("msg_type") == "initial_finding":
                            _kps = _msg_n.get("key_points", [])
                            _concl = (_msg_n.get("conclusion") or {}).get("judgment","")
                            _text = "；".join(_kps[:2]) + (f"。{_concl}" if _concl else "")
                            if _text.strip():
                                _debate_dialogue.append({
                                    "from":    _msg_n.get("from","?"),
                                    "type":    "initial_finding",
                                    "signal":  _msg_n.get("signal","neutral"),
                                    "content": _text[:150],
                                })

                # 综合结论：优先 synthesis/verdict，其次 phase2-persona 的综合立场
                _synthesis_text = ""
                _synth_msgs = [m for m in _board_n if m.get("msg_type") in ("synthesis","verdict")]
                if _synth_msgs:
                    _synthesis_text = str(_synth_msgs[-1].get("content",""))[:300]
                elif _master_narratives:
                    # 用大师平均信号构造简单综合
                    _sigs = [v.get("signal","neutral") for v in _master_narratives.values()]
                    _bull = sum(1 for s in _sigs if s == "bullish")
                    _bear = sum(1 for s in _sigs if s == "bearish")
                    _total = len(_sigs) or 1
                    _synthesis_text = (f"大师评估：{_bull}/{_total} 看多，{_bear}/{_total} 看空。"
                                       f"{'多数看多，持仓信心较强' if _bull > _total/2 else '意见分歧，需审慎'}")

                _narrative = {
                    "sym":               args.symbol,
                    "date":              _date_str_n,
                    "agent_narratives":  _agent_narratives,
                    "master_narratives": _master_narratives,
                    "debate_dialogue":   _debate_dialogue,
                    "synthesis_text":    _synthesis_text,
                }
                with open(_narrative_path, "w", encoding="utf-8") as _nf:
                    json.dump(_narrative, _nf, indent=2, ensure_ascii=False)
                print(f"[cio] narrative → {_narrative_path}")
            except Exception as _e_n:
                pass  # 不阻断主流程
    finally:
        release_lock()

if __name__ == "__main__":
    main()
