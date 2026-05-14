import sys, os, json, argparse, subprocess, time, shutil
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import (BASE, BOARD_PATH, VERIFIED_PATH, STRATEGY_PATH,
                              FINDINGS_DIR, LOCK_PATH, EXIT_OK, EXIT_FAIL)
from utils import get_logger, atomic_write_json, atomic_append_jsonl

log = get_logger(__name__)
PYTHON = sys.executable
AGENTS_DIR = os.path.join(BASE, "agents")

ANALYSIS_AGENTS = [
    "tech_agent", "fund_agent", "macro_agent",
    "sentiment_agent", "community_agent", "risk_agent",
    "sector_agent",
]
AGENT_NAMES = {
    "tech_agent":      "TechAgent",
    "fund_agent":      "FundAgent",
    "macro_agent":     "MacroAgent",
    "sentiment_agent": "SentimentAgent",
    "community_agent": "CommunityAgent",
    "risk_agent":      "RiskAgent",
    "sector_agent":    "SectorAgent",
}

def run(script, args, timeout=120):
    path = os.path.join(AGENTS_DIR, script + ".py")
    return subprocess.run([PYTHON, path] + args, cwd=BASE, timeout=timeout)

def acquire_lock(symbol):
    if os.path.exists(LOCK_PATH):
        lock = json.load(open(LOCK_PATH))
        age  = time.time() - lock.get("start_time", 0)
        if age < 600:
            print(f"[CIO] 已有分析进行中（{age:.0f}s），排队等待...")
            return False
        print("[CIO] 检测到过期锁，清除后继续")
    atomic_write_json({"start_time": time.time(), "symbol": symbol}, LOCK_PATH)
    return True

def release_lock():
    try: os.remove(LOCK_PATH)
    except FileNotFoundError: pass

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
    print("[Phase 0] 完成")
    return True

def phase1(symbol):
    print(f"[Phase 1] 并行启动 6 个分析 agent...")
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    open(BOARD_PATH, "w").close()

    procs = []
    for agent in ANALYSIS_AGENTS:
        p = subprocess.Popen([PYTHON, os.path.join(AGENTS_DIR, agent + ".py"), symbol],
                             cwd=BASE)
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
            msg = json.load(open(path))
            if msg:
                    atomic_append_jsonl(msg, BOARD_PATH)
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
    _AGENTS = ["TechAgent","FundAgent","MacroAgent","SentimentAgent","CommunityAgent","RiskAgent"]
    latest = {}
    for msg in board:
        if msg.get("msg_type") not in ("initial_finding", "revision"): continue
        a = msg.get("from")
        if a not in _AGENTS: continue
        if a not in latest or msg.get("revision", 0) > latest[a].get("revision", 0):
            latest[a] = msg
    signals = [m["signal"] for m in latest.values()]
    if len(signals) < 6: return False
    majority = max(set(signals), key=signals.count)
    if signals.count(majority) < 5: return False
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
                subprocess.run(
                    [PYTHON, os.path.join(AGENTS_DIR, agent_script + ".py"), symbol, "--round", str(round_num)],
                    cwd=BASE, timeout=60
                )
            except subprocess.TimeoutExpired:
                print(f"[Phase 2] {agent_name} 超时")
                continue

            if os.path.exists(out_path):
                msg = json.load(open(out_path))
                if not msg: continue
                atomic_append_jsonl(msg, BOARD_PATH)

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
                            subprocess.run(
                                [PYTHON, os.path.join(AGENTS_DIR, target_script + ".py"),
                                 symbol, "--round", str(round_num)],
                                cwd=BASE, timeout=60
                            )
                            # 被质疑方的普通输出路径
                            normal_out = os.path.join(FINDINGS_DIR, f"{target_agent}_r{round_num}.json")
                            if os.path.exists(normal_out):
                                resp = json.load(open(normal_out))
                                if resp:
                                    atomic_append_jsonl(resp, BOARD_PATH)
                        except subprocess.TimeoutExpired:
                            print(f"[Phase 2]   {target_agent} 回应超时")

                if msg.get("msg_type") == "data_challenge":
                    field = msg.get("target_field", "")
                    try:
                        subprocess.run(
                            [PYTHON, os.path.join(AGENTS_DIR, "verifier_agent.py"),
                             "--field", field, "--round", str(round_num)],
                            cwd=BASE, timeout=60
                        )
                    except subprocess.TimeoutExpired:
                        pass
                    vout = os.path.join(FINDINGS_DIR, f"verifier_r{round_num}_{field}.json")
                    if os.path.exists(vout):
                        vmsg = json.load(open(vout))
                    else:
                        vmsg = {"msg_type": "verify_response", "from": "VerifierAgent",
                                "target_field": field, "result": "unresolvable",
                                "reason": "timeout", "timestamp": datetime.now(timezone.utc).isoformat()}
                    atomic_append_jsonl(vmsg, BOARD_PATH)

        board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()]
        if check_consensus(board):
            print(f"[Phase 2] 共识达成，提前结束（第 {round_num} 轮）")
            break

    print("[Phase 2] 辩论结束")


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

        # 保存供 strategy_agent 读取
        synth_path = os.path.join(BASE, "persona_synthesis.json")
        atomic_write_json(synthesis, synth_path, indent=2)

        print("[Phase 2-Persona] 完成")
        return synthesis
    except Exception as e:
        print(f"[Phase 2-Persona] 失败: {e}")
        return {}


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

        # 新增：Phase 1.5 大师层分析
        stances = phase1_5(args.symbol)

        if "2" in args.phases:
            phase2(args.symbol)
            phase2_persona(args.symbol, stances, question_type=getattr(args, 'question_type', '日内/短线交易'))  # 新增

        if "3" in args.phases:
            print("[Phase 3] 安全检查...")
            from agents.safety_filter import check_all, print_report
            data = json.load(open(VERIFIED_PATH))
            fields = data.get("fields", {})
            blocked, report = check_all(fields, args.symbol)
            print_report(report)

            if blocked:
                print("[Phase 3] WARNING: Safety filter hard block, skipping strategy")
                # Save report for audit
                atomic_write_json(report, os.path.join(BASE, "safety_report.json"), indent=2)
            else:
                print("[Phase 3] 汇总输出...")
                run("strategy_agent", [args.symbol])
                run("report_agent",   [args.symbol])
    finally:
        release_lock()

if __name__ == "__main__":
    main()
