# agents/protocol.py
import os
from datetime import datetime, timezone

EXIT_OK   = 0
EXIT_FAIL = 1
EXIT_SKIP = 2

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD_PATH    = os.path.join(BASE, "discussion_board.jsonl")
VERIFIED_PATH = os.path.join(BASE, "data_verified.json")
STRATEGY_PATH = os.path.join(BASE, "strategy_result.json")
FINDINGS_DIR  = os.path.join(BASE, "findings")
LOCK_PATH     = os.path.join(BASE, "run.lock")
QUOTA_PATH    = os.path.join(BASE, "av_quota.json")

def _now():
    """Return the current UTC timestamp as an ISO string."""
    return datetime.now(timezone.utc).isoformat()

def make_finding(agent, symbol, signal, confidence, key_points, data_refs, revision=0, analysis=None, conclusion=None):
    """Build an initial_finding message dict."""
    return {"msg_type": "initial_finding", "from": agent, "symbol": symbol,
            "signal": signal, "confidence": confidence, "revision": revision,
            "key_points": key_points, "data_refs": data_refs, "timestamp": _now(),
            "analysis": analysis or [],
            "conclusion": conclusion or {"judgment": "", "boundary": "", "anticipated_challenge": ""}}

def make_revision(agent, symbol, signal, confidence, key_points, data_refs, revision, analysis=None, conclusion=None):
    """Build a revision message dict from a finding."""
    msg = make_finding(agent, symbol, signal, confidence, key_points, data_refs, revision, analysis, conclusion)
    msg["msg_type"] = "revision"
    return msg

def make_challenge(from_agent, target, content, data_refs):
    """Build a challenge message dict."""
    return {"msg_type": "challenge", "from": from_agent, "target": target,
            "content": content, "data_refs": data_refs, "timestamp": _now()}

def make_endorsement(from_agent, target, content):
    """Build an endorsement message dict."""
    return {"msg_type": "endorsement", "from": from_agent, "target": target,
            "content": content, "timestamp": _now()}

def make_data_challenge(from_agent, target_field, reason):
    """Build a data_challenge message dict."""
    return {"msg_type": "data_challenge", "from": from_agent,
            "target_field": target_field, "reason": reason, "timestamp": _now()}

import glob as _glob

def find_persona(agent_name, persona_dir=None):
    """Find the persona JSON assigned to the given agent name."""
    if persona_dir is None:
        persona_dir = os.path.join(BASE, "personas")
    import json as _json
    for path in _glob.glob(os.path.join(persona_dir, "*.json")):
        try:
            p = _json.load(open(path, encoding="utf-8"))
            if p.get("assigned_to") == agent_name:
                return p
        except Exception:
            continue
    return None

def apply_persona(msg, data, agent_name, board=None, persona_dir=None):
    """Apply persona rules to a message, overlaying master signal and confidence."""
    import json as _json
    from agents.persona_engine import PersonaEngine
    persona = find_persona(agent_name, persona_dir)
    if persona is None:
        return msg
    board_signals = {m["from"]: {"signal": m.get("signal","neutral"), "confidence": m.get("confidence",50)}
                     for m in (board or [])
                     if m.get("msg_type") in ("initial_finding", "revision")}
    pe = PersonaEngine().evaluate(data, persona, board_signals)
    msg["master"]            = persona["master"]
    msg["rule_signal"]       = msg.get("signal", "neutral")
    msg["rule_confidence"]   = msg.get("confidence", 50)
    msg["master_signal"]     = pe["master_signal"]
    msg["master_confidence"] = pe["master_confidence"]
    msg["signal"]            = pe["master_signal"] if pe["master_signal"] != "veto" else "neutral"
    msg["confidence"]        = pe["master_confidence"]
    msg["internal_conflict"] = (msg["rule_signal"] != pe["master_signal"] and
                                pe["master_signal"] != "veto")
    msg["veto_triggered"]    = pe["veto_triggered"]
    msg["entry_score"]       = pe["entry_score"]
    msg["position_max_pct"]  = pe["position_max_pct"]
    msg["stop_loss_pct"]     = pe["stop_loss_pct"]
    msg["key_points"]        = msg.get("key_points", []) + pe["triggered_insights"]
    if pe["debate_insight"] and board:
        msg["debate_challenge"] = pe["debate_insight"]
    return msg

_ANALYSIS_AGENTS = ["TechAgent","FundAgent","MacroAgent","SentimentAgent","CommunityAgent","RiskAgent"]

def compute_phase2_response(agent_name, symbol, board,
                             signal, confidence, points, data_refs, data_dict):
    """Build a Phase 2 response message (revision, challenge, or endorsement) based on board state."""
    own_msgs = [m for m in board if m.get("from") == agent_name
                and m.get("msg_type") in ("initial_finding", "revision")]
    own_revision = max((m.get("revision", 0) for m in own_msgs), default=0)
    if own_revision >= 2:
        return {}

    # 未回应我的 challenge
    unanswered = [
        m for m in board
        if m.get("target") == agent_name and m.get("msg_type") == "challenge"
        and not any(
            r.get("from") == agent_name
            and r.get("msg_type") in ("revision", "endorsement")
            and r.get("timestamp", "") > m.get("timestamp", "")
            for r in board
        )
    ]

    # 构建 revision（含 persona 层）
    rev = make_revision(agent_name, symbol, signal, confidence, points, data_refs, own_revision + 1)
    rev = apply_persona(rev, data_dict, agent_name, board)
    debate_challenge = rev.pop("debate_challenge", None)

    if unanswered:
        ch = unanswered[-1]
        challenger = ch.get("from", "").replace("Agent", "")
        ch_content = ch.get("content", "")[:60]
        master = rev.get("master", agent_name.replace("Agent", ""))
        rev["responding_to"]    = ch.get("from", "")
        rev["response_content"] = (
            f"[{master}回应{challenger}] {ch_content}…"
            f" — 我的判断依据不变：{points[0] if points else '见上方观点'}"
        )
        rev["key_points"] = [rev["response_content"]] + rev.get("key_points", [])
        return rev

    if debate_challenge:
        # 找信号最对立的 agent
        latest = {}
        for m in board:
            if m.get("msg_type") in ("initial_finding", "revision"):
                a = m.get("from", "")
                if a != agent_name and a in _ANALYSIS_AGENTS:
                    if a not in latest or m.get("revision", 0) > latest[a].get("revision", 0):
                        latest[a] = m
        opponents = [
            (a, m) for a, m in latest.items()
            if m.get("signal") != signal and signal != "neutral"
            and m.get("signal") in ("bullish", "bearish")
        ]
        if opponents:
            target, _ = max(opponents, key=lambda x: x[1].get("confidence", 0))
            return make_challenge(
                agent_name, target, debate_challenge,
                [{"field": "debate", "verified": False, "source": "persona_rules"}]
            )

    # 友好洞见分享：找与我信号相同但论据不同的 agent，发 endorsement
    latest = {}
    for m in board:
        if m.get("msg_type") in ("initial_finding", "revision"):
            a = m.get("from", "")
            if a != agent_name and a in _ANALYSIS_AGENTS:
                if a not in latest or m.get("revision", 0) > latest[a].get("revision", 0):
                    latest[a] = m
    allies = [(a, m) for a, m in latest.items()
              if m.get("signal") == signal and signal != "neutral"
              and m.get("master","") != rev.get("master","")]
    if allies and own_revision == 0:  # 只在第一轮分享
        ally_agent, ally_msg = allies[0]
        ally_master = ally_msg.get("master","").replace("Agent","")
        my_master = rev.get("master","")
        ally_point = ally_msg.get("key_points",[""])[0][:60]
        endorsement_content = (
            f"[{my_master}支持{ally_master}] 从不同角度验证了相同结论——"
            f"{ally_point}…这与我的判断相互印证，增加信心。"
        )
        return make_endorsement(agent_name, ally_agent, endorsement_content)

    return rev
