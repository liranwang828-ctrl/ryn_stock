import sys, os, json, argparse
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, atomic_write_json
log = get_logger(__name__)
from agents.protocol import BASE, BOARD_PATH, STRATEGY_PATH

ANALYSIS_AGENTS = ["TechAgent","FundAgent","MacroAgent","SentimentAgent","CommunityAgent","RiskAgent"]
PERSONA_SYNTHESIS = os.path.join(BASE, "persona_synthesis.json")
SIGNAL_VAL = {"bullish": 1, "neutral": 0, "bearish": -1}

def latest_findings(board):
    """Extract the latest finding per agent and separate active vs vetoed agents."""
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
        }
        for a, m in latest.items() if m.get("master_signal") == "veto"
    }
    active = {a: m for a, m in latest.items() if m.get("master_signal") != "veto"}
    return active, veto_agents

def load_persona_synthesis():
    """Load the persona synthesis JSON file if it exists."""
    if not os.path.exists(PERSONA_SYNTHESIS):
        return None
    return json.load(open(PERSONA_SYNTHESIS, encoding="utf-8"))

COVERAGE_DECAY = {6: 1.0, 5: 0.92, 4: 0.80, 3: 0.65, 2: 0.50, 1: 0.35, 0: 0.0}

def main():
    """Compute the final strategy signal from findings, persona synthesis, and debate board."""
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    args = parser.parse_args()

    board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
    findings, veto_agents = latest_findings(board)
    persona = load_persona_synthesis()

    # 以大师层共识为最终信号
    if persona:
        signal     = persona["consensus_signal"]
        confidence = persona["weighted_confidence"]
        if persona.get("conditional_map"):
            confidence = max(10, confidence - 10)
        decay      = COVERAGE_DECAY.get(len(findings), 0.3)
        confidence = int(confidence * decay)
    else:
        # 无大师层时回退到领域Agent加权
        num = sum(SIGNAL_VAL[f["signal"]] * f["confidence"] for f in findings.values())
        den = sum(f["confidence"] for f in findings.values()) or 1
        score  = num / den * 100
        signal = "bullish" if score >= 15 else "bearish" if score <= -15 else "neutral"
        confidence = int(min(95, 50 + abs(score) * 0.5) * COVERAGE_DECAY.get(len(findings), 0.3))

    key_points = []
    for agent, f in findings.items():
        for kp in f.get("key_points", [])[:2]:
            key_points.append(f"[{agent.replace('Agent','')}] {kp}")

    risk_f    = findings.get("RiskAgent", {})
    stop_loss = risk_f.get("stop_loss")

    disputes = []
    challenges = [m for m in board if m.get("msg_type") == "challenge"]
    for ch in challenges:
        frm, tgt = ch.get("from"), ch.get("target")
        resolved = any(m.get("from") == tgt and m.get("revision", 0) > 0
                       and m["timestamp"] > ch["timestamp"] for m in board)
        if not resolved:
            disputes.append(f"{frm}->{tgt}: {ch.get('content','')[:80]}")

    verified_refs   = [ref for f in findings.values() for ref in f.get("data_refs", []) if ref.get("verified")]
    unverified_refs = [ref for f in findings.values() for ref in f.get("data_refs", []) if not ref.get("verified")]

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
        "key_points":   key_points,
        "stop_loss":    stop_loss,
        "disputes":     disputes,
        "verified_data_count":   len(verified_refs),
        "unverified_data_count": len(unverified_refs),
        "agent_signals": {a: {"signal": f["signal"], "confidence": f["confidence"]}
                          for a, f in findings.items()},
        "veto_agents":    veto_agents,
        "active_count":   len(findings),
        "coverage_decay": COVERAGE_DECAY.get(len(findings), 0.3),
        "persona_synthesis": persona,
        "sector_info":    sector_info,
    }
    atomic_write_json(result, STRATEGY_PATH, indent=2)

if __name__ == "__main__":
    main()
