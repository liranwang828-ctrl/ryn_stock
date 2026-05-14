import json, os
import os as _os
import json as _json

_PERSONAS_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "personas")

def load_persona_full(persona_name: str) -> dict:
    """加载大师的完整分层知识库（灵魂文件 + 规则文件）"""
    persona_dir = _os.path.join(_PERSONAS_DIR, persona_name)
    result = {"name": persona_name}

    for fname in ["worldview", "history", "blindspots", "language"]:
        fpath = _os.path.join(persona_dir, f"{fname}.md")
        if _os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                result[fname] = f.read()

    for fname in ["questions", "rules"]:
        fpath = _os.path.join(persona_dir, f"{fname}.json")
        if _os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                result[fname] = _json.load(f)

    # 向后兼容：旧版单文件 JSON
    legacy = _os.path.join(_PERSONAS_DIR, f"{persona_name}.json")
    if not result.get("rules") and _os.path.exists(legacy):
        with open(legacy) as f:
            result["rules"] = _json.load(f)

    return result

class PersonaEngine:
    """Evaluates persona rules against market data."""

    def _eval(self, condition: str, data: dict, board_signals: dict = None) -> bool:
        """Evaluate a single condition expression against market data."""
        ns = {"data": data, "board_signals": board_signals or {}, "any": any, "all": all}
        try:
            return bool(eval(condition, {"__builtins__": {}}, ns))
        except Exception:
            return False

    def evaluate(self, data: dict, persona,
                 board_signals: dict = None) -> dict:
        """Score a persona's entry/exit rules against market data and return a signal."""
        if isinstance(persona, str):
            persona = json.load(open(persona, encoding="utf-8"))

        # Step 0: debate trigger check (runs regardless of veto, so board conflicts are always surfaced)
        debate_insight = None
        for dt in persona.get("debate_triggers", []):
            if self._eval(dt["condition"], data, board_signals):
                debate_insight = dt["insight"]
                break

        # Step 1: veto check
        for vc in persona.get("veto_conditions", []):
            if self._eval(vc["condition"], data, board_signals):
                return {
                    "master_signal":      "veto",
                    "master_confidence":  0,
                    "entry_score":        0,
                    "veto_triggered":     vc["reason"],
                    "triggered_insights": [f"[{persona['master']}否决] {vc['reason']}"],
                    "position_max_pct":   persona.get("position_sizing", {}).get("max_pct", 5),
                    "stop_loss_pct":      persona.get("exit_logic", {}).get("hard_stop_pct"),
                    "debate_insight":     debate_insight,
                }

        # Step 2: entry score
        entry_score = 0
        triggered_insights = []
        for ec in persona.get("entry_conditions", []):
            if self._eval(ec["condition"], data, board_signals):
                entry_score += ec.get("weight", 0)
                triggered_insights.append(ec["insight"])

        # Step 3: market insight checks (sorted by priority asc, then confidence_delta desc)
        checks = sorted(persona.get("market_insight_checks", []),
                        key=lambda c: (c.get("priority", 99), -abs(c.get("confidence_delta", 0))))
        signal_override = None
        confidence_delta = 0
        for chk in checks:
            if self._eval(chk["condition"], data, board_signals):
                triggered_insights.append(chk["insight"])
                confidence_delta += chk.get("confidence_delta", 0)
                if signal_override is None and chk.get("signal_override") not in (None, "null"):
                    signal_override = chk["signal_override"]

        # Step 4: determine master_signal
        if signal_override:
            master_signal = signal_override
        elif entry_score >= 60:
            master_signal = "bullish"
        elif entry_score <= 20:
            master_signal = "bearish"
        else:
            master_signal = "neutral"

        # Step 5: confidence
        base = min(95, 50 + abs(entry_score - 40))
        master_confidence = max(0, min(95, base + confidence_delta))

        return {
            "master_signal":      master_signal,
            "master_confidence":  master_confidence,
            "entry_score":        entry_score,
            "veto_triggered":     None,
            "triggered_insights": triggered_insights,
            "position_max_pct":   persona.get("position_sizing", {}).get("max_pct", 5),
            "stop_loss_pct":      persona.get("exit_logic", {}).get("hard_stop_pct"),
            "debate_insight":     debate_insight,
        }

    def evaluate_with_questions(self, persona_name: str, data: dict) -> dict:
        """基于大师的强制问题序列评估，返回 signal/core_argument/invalidation/confidence/stopped_at_question"""
        persona = load_persona_full(persona_name)
        questions = persona.get("questions", {}).get("sequence", [])
        confidence = persona.get("questions", {}).get("confidence_base", 50)

        for q in questions:
            q_result = self._eval_question(q, data)
            if not q_result["passed"]:
                action = q.get("fail_action", "reduce_confidence")
                if action == "early_stop":
                    return {
                        "signal": q["fail_output"]["signal"],
                        "core_argument": q["fail_output"]["core_argument"],
                        "invalidation": q["fail_output"]["invalidation"],
                        "confidence": 0,
                        "stopped_at_question": q["id"],
                    }
                elif action == "veto":
                    return {
                        "signal": "neutral",
                        "core_argument": q.get("veto_reason", "条件不满足"),
                        "invalidation": "等待该条件满足",
                        "confidence": 0,
                        "stopped_at_question": q["id"],
                    }
                elif action == "reduce_confidence":
                    confidence -= q.get("fail_penalty", 10)

        signal = "bullish" if confidence >= 60 else "neutral" if confidence >= 40 else "bearish"
        return {
            "signal": signal,
            "core_argument": f"所有{len(questions)}个问题通过",
            "invalidation": "价格跌破止损位或技术结构改变",
            "confidence": max(0, confidence),
            "stopped_at_question": None,
        }

    def _eval_question(self, question: dict, data: dict) -> dict:
        """评估单个问题，数据缺失时默认通过（不惩罚）"""
        q_id = question["id"]
        required = question.get("data_required", [])
        for key in required:
            if key not in data:
                return {"passed": True}

        if q_id == "q1":
            # Minervini Stage 2 / Livermore 最强 / Soros 反身性 / Lynch 商业模式
            # 通用：检查 ma200_slope > 0 and current_price > ma200（如有）
            slope = data.get("ma200_slope")
            price = data.get("current_price")
            ma200 = data.get("ma200")
            if slope is not None and price is not None and ma200 is not None:
                return {"passed": bool(slope > 0 and price > ma200)}

        if q_id == "q4" and "breakout_volume_ratio" in data:
            return {"passed": data["breakout_volume_ratio"] >= 1.5}

        return {"passed": True}
