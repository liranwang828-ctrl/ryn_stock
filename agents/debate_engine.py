"""
辩论引擎 - 四步辩论协议

Step 1: 大师各自发言（基于 evaluate_with_questions）
Step 2: 矛盾识别（bullish vs bearish）
Step 3: 定向回应（最多1轮）
Step 4: 加权裁决
"""
import os
import json
from datetime import datetime, timezone

BASE              = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINDINGS_DIR      = os.path.join(BASE, "findings")
BOARD_PATH        = os.path.join(BASE, "discussion_board.jsonl")
PERSONA_LOG_PATH  = os.path.join(BASE, "persona_stances.jsonl")

PERSONA_FILE_MAP = {
    "minervini":     "mark_minervini",
    "druckenmiller": "stan_druckenmiller",
    "marks":         "howard_marks",
    "taleb":         "nassim_taleb",
    "soros":         "george_soros",
    "livermore":     "jesse_livermore",
    "lynch":         "peter_lynch",
}

# 主角列表（权重=2）
PRIMARY_MASTERS = ["minervini", "druckenmiller", "marks"]


def _get_persona_file_name(master: str) -> str:
    """获取大师对应的文件名"""
    return PERSONA_FILE_MAP.get(master, master)


def _extract_data_for_personas(domain_findings: dict) -> dict:
    """从 domain findings 提取用于 evaluate_with_questions 的数据字典"""
    data = {}
    for domain_key, findings in domain_findings.items():
        if isinstance(findings, dict):
            data.update(findings)
    return data


def _derive_core_argument(master: str, stance: dict) -> str:
    """从 stance 派生简短核心论点"""
    signal = stance.get("signal", "neutral")
    stopped = stance.get("stopped_at_question")
    if stopped:
        return f"{master}: 在 {stopped} 止步，{signal}"
    return stance.get("core_argument", f"{master}: {signal}")


def _log_persona_stances(symbol: str, stances: dict) -> None:
    """将大师立场写入 persona_stances.jsonl（独立于 domain agent 的 board）"""
    try:
        entry = {
            "from":     "PersonaLayer",
            "ts":       datetime.now(timezone.utc).isoformat(),
            "msg_type": "persona_stances",
            "symbol":   symbol,
            "stances":  stances,
        }
        with open(PERSONA_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def collect_domain_findings() -> dict:
    """收集 findings 目录下所有 domain JSON 文件"""
    findings = {}
    if not os.path.isdir(FINDINGS_DIR):
        return findings
    for fname in os.listdir(FINDINGS_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(FINDINGS_DIR, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    key = fname.replace(".json", "")
                    findings[key] = json.load(f)
            except Exception:
                pass
    return findings


def collect_persona_stances(symbol: str, domain_findings: dict,
                             question_type: str = "日内/短线交易") -> dict:
    """
    Step 1: 对每位大师调用 evaluate_with_questions，收集各自立场。

    Returns:
        {master_name: {"signal", "core_argument", "confidence", ...}}
    """
    try:
        from agents.persona_engine import PersonaEngine
        engine = PersonaEngine()
    except ImportError:
        return {}

    data = _extract_data_for_personas(domain_findings)
    stances = {}

    for master, file_name in PERSONA_FILE_MAP.items():
        try:
            result = engine.evaluate_with_questions(file_name, data)
            stances[master] = {
                "signal":        result.get("signal", "neutral"),
                "core_argument": result.get("core_argument", ""),
                "confidence":    result.get("confidence", 50),
                "invalidation":  result.get("invalidation", ""),
                "stopped_at":    result.get("stopped_at_question"),
            }
        except Exception as e:
            stances[master] = {
                "signal":        "neutral",
                "core_argument": f"评估失败: {e}",
                "confidence":    50,
            }

    _log_persona_stances(symbol, stances)
    return stances


def detect_contradictions(stances: dict) -> list:
    """
    Step 2: 识别 bullish vs bearish 矛盾对。
    neutral 不参与矛盾识别。

    Returns:
        [(master_a, master_b), ...] 矛盾对列表
    """
    contradictions = []
    names = list(stances.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            sig_a = stances[a].get("signal", "neutral")
            sig_b = stances[b].get("signal", "neutral")
            if (sig_a == "bullish" and sig_b == "bearish") or \
               (sig_a == "bearish" and sig_b == "bullish"):
                contradictions.append((a, b))
    return contradictions


def run_targeted_response(symbol: str, persona_a: str, persona_b: str,
                          stances: dict) -> dict:
    """
    Step 3: 生成两位大师之间的定向回应（最多1轮）。

    response_type:
        "A" = 攻击对方论点（成功挑战）
        "D" = 防御自身论点
        "C" = 妥协/部分认同

    Returns:
        {persona: {response_type, response, new_confidence, opponent}}
    """
    responses = {}
    stance_a = stances.get(persona_a, {})
    stance_b = stances.get(persona_b, {})

    sig_a = stance_a.get("signal", "neutral")
    sig_b = stance_b.get("signal", "neutral")
    conf_a = stance_a.get("confidence", 50)
    conf_b = stance_b.get("confidence", 50)
    arg_a = stance_a.get("core_argument", "")
    arg_b = stance_b.get("core_argument", "")

    # 较高信心者倾向于攻击，较低信心者倾向于防御
    if conf_a >= conf_b:
        # A 攻击 B
        responses[persona_a] = {
            "response_type":  "A",
            "response":       f"{persona_a} 挑战 {persona_b}：{arg_b} 忽视了 {arg_a} 的核心逻辑",
            "new_confidence": min(conf_a + 5, 95),
            "opponent":       persona_b,
        }
        # B 防御
        conf_b_new = max(conf_b - 5, 5)
        responses[persona_b] = {
            "response_type":  "D",
            "response":       f"{persona_b} 坚持：{arg_b}，{sig_b} 立场不变",
            "new_confidence": conf_b_new,
            "opponent":       persona_a,
        }
    else:
        # B 攻击 A
        responses[persona_b] = {
            "response_type":  "A",
            "response":       f"{persona_b} 挑战 {persona_a}：{arg_a} 忽视了 {arg_b} 的核心逻辑",
            "new_confidence": min(conf_b + 5, 95),
            "opponent":       persona_a,
        }
        # A 防御
        conf_a_new = max(conf_a - 5, 5)
        responses[persona_a] = {
            "response_type":  "D",
            "response":       f"{persona_a} 坚持：{arg_a}，{sig_a} 立场不变",
            "new_confidence": conf_a_new,
            "opponent":       persona_b,
        }

    return responses


def weighted_synthesis(stances: dict, responses: dict,
                       primary_masters: list = None) -> dict:
    """
    Step 4: 加权裁决。

    - primary_masters 中的大师权重=2，其余=1
    - 被对方 A 型回应成功挑战后权重折半
    - 主角分歧时额外返回 conditional_map

    Returns:
        {consensus_signal, weighted_confidence, unresolved_contradictions,
         synthesis_reasoning, [conditional_map]}
    """
    if primary_masters is None:
        primary_masters = PRIMARY_MASTERS

    weighted_scores = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
    total_weight = 0.0

    for master, stance in stances.items():
        signal = stance.get("signal", "neutral")
        conf   = stance.get("confidence", 50)
        weight = 2.0 if master in primary_masters else 1.0

        # 被对方 A 型回应挑战 → 权重折半
        for resp_master, resp in responses.items():
            if resp.get("response_type") == "A" and resp.get("opponent") == master:
                weight *= 0.5
                break

        # 优先使用回应后的新信心度
        updated_conf = responses.get(master, {}).get("new_confidence", conf)

        if signal not in weighted_scores:
            signal = "neutral"
        weighted_scores[signal] += weight * updated_conf / 100
        total_weight += weight

    if total_weight > 0:
        for k in weighted_scores:
            weighted_scores[k] /= total_weight

    consensus = max(weighted_scores, key=weighted_scores.get)
    confidence = int(weighted_scores[consensus] * 100)

    # 检查主角之间是否存在分歧
    primary_signals = {
        m: stances[m].get("signal", "neutral")
        for m in primary_masters if m in stances
    }
    unique_signals = set(s for s in primary_signals.values() if s != "neutral")
    has_split = len(unique_signals) > 1

    # 主角之间未解矛盾
    primary_stances_only = {m: stances[m] for m in primary_masters if m in stances}
    unresolved = [
        f"{a} vs {b}"
        for a, b in detect_contradictions(primary_stances_only)
    ]

    result = {
        "consensus_signal":          consensus,
        "weighted_confidence":        confidence,
        "unresolved_contradictions": unresolved,
        "synthesis_reasoning":       (
            f"加权共识：{consensus}({confidence}%)，"
            f"主角{'存在分歧' if has_split else '基本一致'}"
        ),
    }

    if has_split:
        result["conditional_map"] = {
            sig: [m for m, s in primary_signals.items() if s == sig]
            for sig in unique_signals
        }

    return result
