import sys, os, json, argparse
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import BASE, BOARD_PATH, STRATEGY_PATH, PERSONA_SYNTH_PATH, EXIT_OK

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

    board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
    findings, veto_agents = latest_findings(board)

    if not findings:
        print("No findings available", file=sys.stderr)
        sys.exit(1)

    # ── 执行层（专业 Agent）：权重 0.4 ──────────────────────────
    score      = compute_score(findings)
    agent_signal = "bullish" if score >= 15 else "bearish" if score <= -15 else "neutral"
    raw_conf   = min(95, int(50 + abs(score) * 0.5))
    decay      = COVERAGE_DECAY.get(len(findings), 0.3)
    agent_conf = int(raw_conf * decay)
    agent_val  = SIGNAL_VAL[agent_signal]

    # ── 管理层（大师综合）：权重 0.6 ────────────────────────────
    synth_path = PERSONA_SYNTH_PATH
    master_val, master_conf, master_source = agent_val, agent_conf, "agent_fallback"
    if os.path.exists(synth_path):
        try:
            synth       = json.load(open(synth_path, encoding="utf-8"))
            master_val  = SIGNAL_VAL.get(synth.get("consensus_signal", agent_signal), agent_val)
            master_conf = int(synth.get("weighted_confidence", agent_conf))
            master_source = "persona_synthesis"
        except Exception:
            pass

    # ── 混合：大师 0.6 + 执行层 0.4 ────────────────────────────
    W_MASTER, W_AGENT = 0.6, 0.4
    blended_val  = master_val * W_MASTER + agent_val * W_AGENT
    blended_conf = int(master_conf * W_MASTER + agent_conf * W_AGENT)
    signal     = "bullish" if blended_val > 0.12 else "bearish" if blended_val < -0.12 else "neutral"
    confidence = blended_conf

    # ── 动态大师权重（基于历史准确率）────────────────────────────
    LRN_DIR = os.path.join(BASE, "learning")
    acc_path = os.path.join(LRN_DIR, "master_accuracy.json")
    if os.path.exists(acc_path):
        try:
            acc_data = json.load(open(acc_path, encoding="utf-8"))
            # Reweight: agents with accuracy > 0.55 get 1.2x, < 0.45 get 0.8x
            adjusted_scores = {}
            for agent, f in findings.items():
                agent_acc = acc_data.get(agent, {}).get("accuracy", 0.5)
                weight_mult = 1.2 if agent_acc > 0.55 else (0.8 if agent_acc < 0.45 else 1.0)
                adjusted_scores[agent] = {**f, "confidence": f["confidence"] * weight_mult}
            score = compute_score(adjusted_scores)
            signal = "bullish" if score >= 15 else "bearish" if score <= -15 else "neutral"
        except Exception:
            pass  # Fall back to original score

    # ── 宏观折扣（#1）+ 入场条件（#2）────────────────────────────
    macro_factors = {}
    entry_gates   = {}
    macro_discount = 1.0
    try:
        import yfinance as yf
        vix_h = yf.Ticker("^VIX").history(period="1d", interval="1m")
        spy_h = yf.Ticker("SPY").history(period="2d")
        qqq_h = yf.Ticker("QQQ").history(period="1d", interval="5m")

        vix_cur  = float(vix_h["Close"].iloc[-1]) if not vix_h.empty else 18.0
        vix_prev = float(vix_h["Close"].iloc[-6]) if len(vix_h) >= 6 else vix_cur
        vix_trend = "↑升" if vix_cur > vix_prev * 1.005 else \
                    "↓降" if vix_cur < vix_prev * 0.995 else "→平"

        spy_lc  = float(spy_h["Close"].iloc[-2]) if len(spy_h) >= 2 else float(spy_h["Close"].iloc[-1])
        spy_cur = float(spy_h["Close"].iloc[-1])
        spy_chg = (spy_cur - spy_lc) / spy_lc * 100

        qqq_5m = 0.0
        if len(qqq_h) >= 6:
            qqq_5m = (float(qqq_h["Close"].iloc[-1]) - float(qqq_h["Close"].iloc[-6])) \
                     / float(qqq_h["Close"].iloc[-6]) * 100

        macro_factors = {
            "vix": round(vix_cur, 1), "vix_trend": vix_trend,
            "spy_chg": round(spy_chg, 2), "qqq_5m": round(qqq_5m, 2),
        }

        # VIX 水平折扣
        if vix_cur > 25:    macro_discount *= 0.65
        elif vix_cur > 20:  macro_discount *= 0.80
        # VIX 上升额外折扣
        if vix_trend == "↑升": macro_discount *= 0.90
        # 大盘当日下跌折扣
        if spy_chg < -1.0:  macro_discount *= 0.85

        confidence = int(confidence * macro_discount)

        # 入场条件判断（方法论#6/#11门控）
        entry_gates = {
            "VIX<20":     vix_cur < 20,
            "VIX方向":    vix_trend in ("→平", "↓降"),
            "QQQ5m≥-0.1%": qqq_5m >= -0.1,
            "SPY>-1%":    spy_chg > -1.0,
        }
    except Exception:
        pass

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
        "coverage_decay":  decay,
        "agent_signal":    agent_signal,
        "agent_conf":      agent_conf,
        "master_signal":   "bullish" if master_val > 0.12 else "bearish" if master_val < -0.12 else "neutral",
        "master_conf":     master_conf,
        "master_source":   master_source,
        "blend_weights":   {"master": W_MASTER, "agent": W_AGENT},
        "sector_info":     sector_info,
        "macro_factors":   macro_factors,
        "macro_discount":  round(macro_discount, 3),
        "entry_gates":     entry_gates,
    }
    json.dump(result, open(STRATEGY_PATH, "w", encoding="utf-8"), indent=2)

if __name__ == "__main__":
    main()
