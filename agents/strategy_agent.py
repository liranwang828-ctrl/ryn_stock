import sys, os, json, argparse
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, fetch_with_retry, atomic_write_json
log = get_logger(__name__)
from agents.protocol import BASE, BOARD_PATH, STRATEGY_PATH, EXIT_OK

# 七位大师名单
PERSONAS = [
    "mark_minervini",
    "stan_druckenmiller",
    "howard_marks",
    "nassim_taleb",
    "george_soros",
    "jesse_livermore",
    "peter_lynch",
]

ANALYSIS_AGENTS = ["TechAgent","FundAgent","MacroAgent","SentimentAgent","CommunityAgent","RiskAgent"]
# SectorAgent 参与讨论板但不计入综合评分（纯信息层）
SECTOR_AGENT = "SectorAgent"
SIGNAL_VAL = {"bullish": 1, "neutral": 0, "bearish": -1}

def latest_findings(board):
    latest = {}
    for msg in board:
        if msg.get("msg_type") not in ("initial_finding", "revision"):
            continue
        agent = msg.get("from")
        if agent not in ANALYSIS_AGENTS:
            continue
        if agent not in latest or msg.get("revision", 0) > latest[agent].get("revision", 0):
            latest[agent] = msg
    veto_agents = {
        a: {
            "reason":       m.get("veto_triggered", "大师标准不满足"),
            "master":       m.get("master", ""),
            "rule_signal":  m.get("rule_signal", m.get("signal", "neutral")),
            "rule_conf":    m.get("rule_confidence", m.get("confidence", 50)),
            "key_points":   m.get("key_points", []),
            "overnight_chg": next((kp for kp in m.get("key_points", []) if "盘前" in kp or "盘后" in kp), None),
        }
        for a, m in latest.items() if m.get("master_signal") == "veto"
    }
    active = {a: m for a, m in latest.items() if m.get("master_signal") != "veto"}
    return active, veto_agents

def compute_score(findings):
    num = sum(SIGNAL_VAL[f["signal"]] * f["confidence"] for f in findings.values())
    den = sum(f["confidence"] for f in findings.values()) or 1
    return num / den * 100

# 参与 agent 越少，置信度越低（最多6个）
COVERAGE_DECAY = {6: 1.0, 5: 0.92, 4: 0.80, 3: 0.65, 2: 0.50, 1: 0.35, 0: 0.0}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    args = parser.parse_args()

    board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()] if os.path.exists(BOARD_PATH) else []
    findings, veto_agents = latest_findings(board)

    if not findings:
        print("No findings available", file=sys.stderr)
        sys.exit(1)

    score      = compute_score(findings)
    signal     = "bullish" if score >= 15 else "bearish" if score <= -15 else "neutral"
    raw_conf   = min(95, int(50 + abs(score) * 0.5))
    decay      = COVERAGE_DECAY.get(len(findings), 0.3)
    confidence = int(raw_conf * decay)

    key_points = []
    for agent, f in findings.items():
        for kp in f.get("key_points", [])[:2]:
            key_points.append(f"[{agent.replace('Agent','')}] {kp}")

    risk_f    = findings.get("RiskAgent", {})
    # stop_loss is a price ($430); stop_loss_pct is a ratio (0.07) — don't confuse them
    stop_loss = risk_f.get("stop_loss")  # price value from RiskAgent.analyze()

    disputes = []
    challenges = [m for m in board if m.get("msg_type") == "challenge"]
    for ch in challenges:
        frm, tgt = ch.get("from"), ch.get("target")
        resolved  = any(m.get("from") == tgt and m.get("revision", 0) > 0
                        and m["timestamp"] > ch["timestamp"] for m in board)
        if not resolved:
            disputes.append(f"{frm}→{tgt}: {ch.get('content','')[:80]}")

    verified_refs   = [ref for f in findings.values() for ref in f.get("data_refs", []) if ref.get("verified")]
    unverified_refs = [ref for f in findings.values() for ref in f.get("data_refs", []) if not ref.get("verified")]

    # 提取 SectorAgent 信息（不计入评分）
    sector_msgs = [m for m in board if m.get("from") == "SectorAgent"
                   and m.get("msg_type") in ("initial_finding", "revision")]
    sector_info = {}
    if sector_msgs:
        sm = max(sector_msgs, key=lambda m: m.get("revision", 0))
        sector_info = sm.get("sector_info", {})
        sector_info["signal"]     = sm.get("signal", "neutral")
        sector_info["confidence"] = sm.get("confidence", 50)
        sector_info["key_points"] = sm.get("key_points", [])

    result = {
        "symbol":       args.symbol,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "signal":       signal,
        "confidence":   confidence,
        "score":        round(score, 2),
        "key_points":   key_points,
        "stop_loss":    stop_loss,
        "disputes":     disputes,
        "verified_data_count":   len(verified_refs),
        "unverified_data_count": len(unverified_refs),
        "agent_signals": {a: {"signal": f["signal"], "confidence": f["confidence"]}
                          for a, f in findings.items()},
        "veto_agents":    veto_agents,
        "active_count":   len(findings),
        "coverage_decay": decay,
        "sector_info":    sector_info,
    }
    atomic_write_json(result, STRATEGY_PATH, indent=2)

if __name__ == "__main__":
    main()
