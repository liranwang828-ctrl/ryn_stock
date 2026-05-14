"""多标的并行分析 + 比较辩论"""
import os, sys, json, subprocess
from concurrent.futures import ThreadPoolExecutor

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON  = sys.executable

def compare_stocks(symbols: list, question: str = "") -> dict:
    """A vs B 比较入口"""
    from agents.question_router import classify_question
    route = classify_question(question, symbols)
    print(f"[MultiStock] 问题类型: {route['type']} | 主角: {route['primary_masters'][:3]}")

    # 并行拉数据
    all_data = {}
    with ThreadPoolExecutor(max_workers=min(len(symbols), 4)) as ex:
        futures = {ex.submit(_run_phase01, sym): sym for sym in symbols}
        for fut in futures:
            sym = futures[fut]
            try:
                all_data[sym] = fut.result(timeout=120)
                print(f"  ✅ {sym} 分析完成")
            except Exception as e:
                print(f"  ❌ {sym} 失败: {e}")

    # 对每只股票运行 Persona 层
    from agents.debate_engine import (collect_persona_stances, detect_contradictions,
                                       run_targeted_response, weighted_synthesis)
    results = {}
    for sym, data in all_data.items():
        if not data:
            continue
        stances = collect_persona_stances(sym, data.get("findings", {}),
                                          question_type=route["type"])
        contradictions = detect_contradictions(stances)
        responses = {}
        for a, b in contradictions:
            resp = run_targeted_response(sym, a, b, stances)
            responses.update(resp)
        synthesis = weighted_synthesis(stances, responses,
                                       primary_masters=route["primary_masters"])
        results[sym] = {"stances": stances, "synthesis": synthesis}

    # 排序输出
    ranked = sorted(results.items(),
                    key=lambda x: x[1]["synthesis"].get("weighted_confidence", 0),
                    reverse=True)
    print("\n[MultiStock] 比较结果（按置信度排序）：")
    for sym, data in ranked:
        s = data["synthesis"]
        print(f"  {sym}: {s['consensus_signal']} ({s['weighted_confidence']}%)")

    return results


def _run_phase01(symbol: str) -> dict:
    """单股票 Phase 0+1"""
    agents_dir = os.path.join(BASE, "agents")
    subprocess.run([PYTHON, os.path.join(agents_dir, "data_agent.py"), symbol],
                   cwd=BASE, capture_output=True, timeout=60)
    subprocess.run([PYTHON, os.path.join(agents_dir, "verifier_agent.py")],
                   cwd=BASE, capture_output=True, timeout=30)
    findings = {}
    findings_dir = os.path.join(BASE, "findings")
    for name in ["TechAgent","FundAgent","MacroAgent","SentimentAgent","RiskAgent","SectorAgent"]:
        fp = os.path.join(findings_dir, f"{name}.json")
        if os.path.exists(fp):
            try: findings[name] = json.load(open(fp, encoding="utf-8"))
            except: pass
    return {"symbol": symbol, "findings": findings}
