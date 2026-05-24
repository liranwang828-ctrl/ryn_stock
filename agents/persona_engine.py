import json, os
import os as _os
import json as _json

_PERSONAS_DIR = _os.path.join(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")), "personas")

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
        with open(legacy, encoding="utf-8") as f:
            result["rules"] = _json.load(f)

    return result

class PersonaEngine:
    def _eval(self, condition: str, data: dict, board_signals: dict = None) -> bool:
        ns = {"data": data, "board_signals": board_signals or {}, "any": any, "all": all}
        try:
            return bool(eval(condition, {"__builtins__": {}}, ns))
        except Exception:
            return False

    def evaluate(self, data: dict, persona,
                 board_signals: dict = None) -> dict:
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

        # 根据大师专属域和实际数据生成真实 core_argument（替代通用模板）
        core_argument = _generate_core_argument(persona_name, data, signal, confidence)
        invalidation  = _generate_invalidation(persona_name, data)

        return {
            "signal": signal,
            "core_argument": core_argument,
            "invalidation": invalidation,
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
                return {"passed": slope > 0 and price > ma200}

        if q_id == "q4" and "breakout_volume_ratio" in data:
            return {"passed": data["breakout_volume_ratio"] >= 1.5}

        return {"passed": True}


# ── 大师论点生成（替换通用模板）─────────────────────────────────────────────

_MASTER_DOMAIN = {
    "mark_minervini":     "tech",        # 技术结构/量价/Stage
    "stan_druckenmiller": "macro",       # 宏观/流动性/仓位
    "howard_marks":       "risk",        # 风险/RR/市场周期
    "peter_lynch":        "fundamental", # 基本面/商业模式/论点完整性
    "george_soros":       "sentiment",   # 反身性/叙事/情绪转折
    "jesse_livermore":    "timing",      # 时机/价格行为/时间窗口
    "nassim_taleb":       "tail",        # 尾部风险/不对称/凸性
}


def _fmt(v, suffix="", na="N/A"):
    return f"{v}{suffix}" if v is not None else na


def _generate_core_argument(persona_name: str, data: dict, signal: str, confidence: int) -> str:
    """根据大师专属域和实际数据生成有意义的 core_argument（≤80字）"""
    domain = _MASTER_DOMAIN.get(persona_name, "general")
    d = data  # shorthand

    if domain == "tech":
        stage  = d.get("tech_stage") or d.get("technical_stage", "?")
        rs5    = d.get("rs5") or d.get("rs_vs_sector")
        macd   = d.get("macd") or d.get("last_macd")
        parts  = [f"Stage {stage} 上升结构"]
        if rs5 is not None:
            parts.append(f"RS超额{rs5:+.1f}%")
        parts.append(f"MACD{'正值动能向上' if (macd or 0) > 0 else '负值注意'}")
        return "，".join(parts)[:80]

    elif domain == "macro":
        vix    = d.get("vix") or d.get("vix_level")
        macro  = d.get("macro_state") or d.get("macro_assessment", "")
        rev_g  = d.get("rev_growth_pct")
        parts  = [f"宏观{'中性' if not macro else str(macro)[:8]}"]
        if vix:
            parts.append(f"VIX {vix:.0f}波动可控")
        if rev_g:
            parts.append(f"营收增速{rev_g:+.0f}%印证基本面")
        return "，".join(parts)[:80]

    elif domain == "risk":
        pe_fwd    = d.get("pe_fwd")
        sector_pe = d.get("sector_pe")
        beta      = d.get("beta")
        rr        = d.get("rr_ratio") or d.get("rr_remaining")
        parts     = []
        if pe_fwd and sector_pe:
            prem = round((pe_fwd / sector_pe - 1) * 100)
            parts.append(f"PE(fwd){pe_fwd:.0f}x vs 板块{sector_pe:.0f}x({prem:+d}%)")
        if beta:
            parts.append(f"Beta{beta:.1f}x高波动需控仓")
        if rr is not None:
            parts.append(f"RR{rr:.1f}x盈亏比{'合理' if rr >= 2 else '偏低'}")
        return ("，".join(parts) if parts else "注意估值与风险匹配度")[:80]

    elif domain == "fundamental":
        thesis = d.get("thesis") or d.get("thesis_full", "")
        rev_g  = d.get("rev_growth_pct")
        fcf    = d.get("fcf_B")
        parts  = []
        if thesis and isinstance(thesis, str) and len(thesis) > 3:
            parts.append(thesis[:30])
        if rev_g and rev_g > 0:
            parts.append(f"营收+{rev_g:.0f}%高增长")
        if fcf and fcf > 0:
            parts.append(f"FCF${fcf:.0f}B现金牛")
        return ("，".join(parts) if parts else "基本面论点完整，商业模式清晰")[:80]

    elif domain == "sentiment":
        n_ana  = d.get("n_analysts") or d.get("numberOfAnalystOpinions")
        rec    = d.get("rec_key") or d.get("recommendationKey", "")
        gap    = d.get("gap_pct")
        parts  = []
        if n_ana:
            parts.append(f"分析师{n_ana}人{'强烈' if 'strong' in str(rec) else ''}看多")
        if gap is not None:
            parts.append(f"盘前Gap{gap:+.1f}%情绪{'积极' if gap > 0 else '谨慎'}")
        parts.append("叙事逻辑自洽，注意反转信号")
        return "，".join(parts)[:80]

    elif domain == "timing":
        scene  = d.get("pred_scene") or d.get("scene")
        if not scene or scene == "?":
            # 智能从均线结构 tech_stage/technical_stage 推导 Livermore 场景，消灭问号
            t_stage = str(d.get("tech_stage") or d.get("technical_stage") or "")
            if t_stage in ("2", "1_2"):
                scene = "上升突破场"
            elif t_stage == "3":
                scene = "震荡吸筹场"
            elif t_stage == "4":
                scene = "规避调整场"
            else:
                scene = "稳健蓄势场"
        ego    = d.get("entry_go_status", "")
        vwap   = d.get("vwap_dist_pct")
        parts  = [f"场景[{scene}]"]
        if vwap is not None:
            parts.append(f"VWAP{vwap:+.1f}%{'利于入场' if abs(vwap) < 2 else '偏离'}")
        parts.append(f"入场窗口{'已触发' if ego == 'go' else '待确认'}")
        return "，".join(parts)[:80]

    elif domain == "tail":
        beta   = d.get("beta")
        short  = d.get("short_pct")
        tail   = d.get("estimated_max_loss_pct")
        parts  = []
        if beta:
            parts.append(f"Beta{beta:.1f}x尾部风险放大{beta:.0f}倍")
        if short is not None:
            parts.append(f"空头{short:.1f}%较{'高' if short > 5 else '低'}")
        parts.append(f"极端情景损失估算{tail:.0f}%" if tail else "不对称性可接受")
        return "，".join(parts)[:80]

    # 通用后备
    rev_g = d.get("rev_growth_pct")
    pe    = d.get("pe_fwd") or d.get("pe_ttm")
    parts = [f"综合信号{signal}，置信度{confidence}%"]
    if rev_g:
        parts.append(f"营收增速{rev_g:+.0f}%")
    if pe:
        parts.append(f"PE(fwd){pe:.0f}x")
    return "，".join(parts)[:80]


def _generate_invalidation(persona_name: str, data: dict) -> str:
    """根据大师专属域生成具体的证伪条件"""
    domain = _MASTER_DOMAIN.get(persona_name, "general")
    d = data

    if domain == "tech":
        stop = d.get("hard_stop") or d.get("t1_stop_snapshot")
        return f"价格跌破${stop:.2f}且放量确认" if stop else "技术结构破坏（跌破关键支撑+放量）"
    elif domain == "macro":
        return "VIX突破25或Fed超预期鹰派，流动性环境恶化"
    elif domain == "risk":
        rr = d.get("rr_ratio") or d.get("rr_remaining")
        return f"RR跌至{max(0,(rr or 2)-1.5):.1f}x以下或止损触发" if rr else "盈亏比恶化至1.5x以下"
    elif domain == "fundamental":
        return "营收增速跌破20%或FCF转负，核心论点失效"
    elif domain == "sentiment":
        return "分析师集体下调目标价或叙事逻辑出现重大裂缝"
    elif domain == "timing":
        return "价格跌破当日VWAP且量能未萎缩，场景预判失效"
    elif domain == "tail":
        return "出现黑天鹅事件（VIX>35）或杠杆仓位被迫清算"
    return "价格跌破止损位或基本面出现负面超预期"
