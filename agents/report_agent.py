import sys, os, json, argparse
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import BASE, STRATEGY_PATH, BOARD_PATH
from jinja2 import Environment, FileSystemLoader

SIGNAL_ICON  = {"bullish": "↑ 看涨", "bearish": "↓ 看空", "neutral": "→ 中性"}
SIGNAL_COLOR = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}
W = 62   # report width

def hr(char="─", w=W):
    return char * w

def section(title):
    pad = (W - len(title) - 2) // 2
    return f"{'─'*pad} {title} {'─'*(W - pad - len(title) - 2)}"

def fmt_ts(ts):
    return ts[:16].replace("T", " ") + " UTC" if ts else ""

def load_board():
    if os.path.exists(BOARD_PATH):
        return [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()]
    return []

def latest_per_agent(board):
    """返回每个 agent 的最新 finding/revision 消息。"""
    latest = {}
    for m in board:
        if m.get("msg_type") not in ("initial_finding", "revision"):
            continue
        a = m.get("from", "")
        if a not in latest or m.get("revision", 0) > latest[a].get("revision", 0):
            latest[a] = m
    return latest

def render_agent_block(agent, msg, label="参与评分"):
    """渲染单个 agent 的完整分析块。"""
    lines = []
    name   = agent.replace("Agent", "")
    master = msg.get("master", "")
    signal = msg.get("signal", "neutral")
    conf   = msg.get("confidence", 0)
    rule_s = msg.get("rule_signal", signal)
    rule_c = msg.get("rule_conf",   conf)
    is_veto = msg.get("master_signal") == "veto"

    if is_veto:
        lines.append(f"  ✗ {name}  [{master}]  — 否决")
        lines.append(f"    否决理由: {msg.get('veto_triggered','')}")
        lines.append(f"    规则层判断: {SIGNAL_ICON.get(rule_s)} ({rule_c}%)  {SIGNAL_COLOR.get(rule_s,'')}")
    else:
        lines.append(f"  ◆ {name}  [{master}]")
        lines.append(f"    信号: {SIGNAL_ICON.get(signal)} ({conf}%)  {SIGNAL_COLOR.get(signal,'')}")

    kps = msg.get("key_points", [])
    if kps:
        lines.append("    观点:")
        for kp in kps:
            lines.append(f"      · {kp}")
    return lines

def render_news(board, agent_msgs):
    """从 SentimentAgent 的 key_points 中提取新闻。"""
    lines = []
    sent_msg = agent_msgs.get("SentimentAgent", {})
    # 搜集含 📈/📉/📰 的新闻行
    news_kps = [kp for kp in sent_msg.get("key_points", [])
                if any(e in kp for e in ("📈","📉","📰","── 近期新闻 ──"))]
    if not news_kps:
        return lines
    lines.append(section("近期新闻（消息面）"))
    lines.append("")
    for kp in news_kps:
        if "近期新闻" in kp:
            continue
        lines.append(f"  {kp}")
    lines.append("")
    return lines

def render_debate(board):
    """把讨论板按时间线渲染成对话格式，突出 challenge ↔ 回应链。"""
    debate_msgs = [m for m in board
                   if m.get("msg_type") in
                   ("challenge","revision","endorsement","data_challenge","verify_response")]
    if not debate_msgs:
        return []

    lines = [section("辩论过程（有来有回）"), ""]
    type_labels = {
        "challenge":       ("质疑", "⚡"),
        "revision":        ("修正/回应", "🔄"),
        "endorsement":     ("背书", "✓ "),
        "data_challenge":  ("数据质疑", "❓"),
        "verify_response": ("核实回应", "🔍"),
    }

    # 标记哪些 revision 是对 challenge 的回应
    challenge_targets = {}  # agent_name → last challenge content targeting them
    for m in board:
        if m.get("msg_type") == "challenge":
            tgt = m.get("target", "")
            challenge_targets[tgt] = (m.get("from",""), m.get("content",""), m.get("timestamp",""))

    for m in debate_msgs:
        mtype = m.get("msg_type", "")
        frm   = m.get("from", "").replace("Agent", "")
        tgt   = m.get("target", "").replace("Agent", "")
        master= m.get("master", "")
        label, icon = type_labels.get(mtype, (mtype, "•"))
        ts    = fmt_ts(m.get("timestamp", ""))

        if mtype == "challenge":
            lines.append(f"  {icon} {frm}【{master}】→ {tgt}  [{label}]  {ts}")
            content = m.get("content", "")
            for chunk in [content[i:i+56] for i in range(0, len(content), 56)]:
                lines.append(f"    ┌── {chunk}")
            lines.append("")

        elif mtype == "revision":
            rev = m.get("revision", "")
            # 是否在回应 challenge
            resp_to = m.get("responding_to", "")
            resp_content = m.get("response_content", "")
            if resp_to:
                resp_frm = resp_to.replace("Agent", "")
                lines.append(f"  🔄 {frm}【{master}】 ← 回应{resp_frm}  rev={rev}  {ts}")
                if resp_content:
                    for chunk in [resp_content[i:i+56] for i in range(0, len(resp_content), 56)]:
                        lines.append(f"    └── {chunk}")
            else:
                lines.append(f"  🔄 {frm}【{master}】 [更新立场]  rev={rev}  {ts}")

            # 内部矛盾（自我论证）
            rule_s = m.get("rule_signal", "")
            mast_s = m.get("master_signal", "")
            if m.get("internal_conflict") and rule_s and mast_s:
                lines.append(f"    ⚖ 内部分歧: 规则层判断{SIGNAL_ICON.get(rule_s,'?')} "
                              f"vs {master}否决→{SIGNAL_ICON.get(mast_s,'?')}")

            new_sig  = m.get("signal", "")
            new_conf = m.get("confidence", "")
            if new_sig:
                lines.append(f"    • 最终信号: {SIGNAL_ICON.get(new_sig)} ({new_conf}%)")
            kps = [kp for kp in m.get("key_points", [])
                   if not kp.startswith("[") or "回应" in kp]
            for kp in kps[:3]:
                lines.append(f"    • {kp}")
            lines.append("")

        elif mtype == "endorsement":
            lines.append(f"  {icon} {frm} → {tgt} [背书]  {ts}")
            content = m.get("content", "")
            if content:
                lines.append(f"    └── {content[:56]}")
            lines.append("")

        elif mtype == "data_challenge":
            lines.append(f"  {icon} {frm} [数据质疑]  字段: {m.get('target_field','')}  {ts}")
            lines.append(f"    └── {m.get('reason','')[:56]}")
            lines.append("")

        elif mtype == "verify_response":
            res = m.get("result","")
            lines.append(f"  {icon} VerifierAgent [核实] → {res}  {ts}")
            detail = m.get("detail", {})
            if detail:
                disp = str(detail)[:56]
                lines.append(f"    └── {disp}")
            lines.append("")

    return lines

def terminal_summary(result, board=None):
    if board is None:
        board = load_board()

    ts      = fmt_ts(result.get("timestamp", ""))
    sym     = result["symbol"]
    active_n = result.get("active_count", len(result.get("agent_signals", {})))
    decay   = result.get("coverage_decay", 1.0)
    raw_c   = int(result['confidence'] / decay) if decay else 0

    lines = [
        "",
        "═" * W,
        f"  {sym}  行情分析报告   {ts}",
        "═" * W,
        f"  数据质量: verified {result['verified_data_count']} 字段 / "
        f"unverified {result['unverified_data_count']} 字段",
        f"  覆盖度:   {active_n}/6 个 agent 参与评分  "
        f"(置信度折扣 ×{decay:.0%})",
        "",
    ]

    # ── 参与评分的 agent ──
    agent_msgs = latest_per_agent(board)
    lines.append(section("参与评分的 Agent"))
    lines.append("")
    for agent in result.get("agent_signals", {}):
        msg = agent_msgs.get(agent, {})
        if not msg:
            msg = {"signal": result["agent_signals"][agent]["signal"],
                   "confidence": result["agent_signals"][agent]["confidence"]}
        lines += render_agent_block(agent, msg, "参与评分")
        lines.append("")

    # ── 被大师否决的 agent ──
    veto_agents = result.get("veto_agents", {})
    if veto_agents:
        lines.append(section("被大师否决的 Agent（仅供参考）"))
        lines.append("")
        for agent, veto in veto_agents.items():
            if isinstance(veto, dict):
                veto_msg = {
                    "master":        veto.get("master", ""),
                    "master_signal": "veto",
                    "veto_triggered":veto.get("reason", ""),
                    "rule_signal":   veto.get("rule_signal", "neutral"),
                    "rule_conf":     veto.get("rule_conf", 0),
                    "signal":        veto.get("rule_signal", "neutral"),
                    "confidence":    veto.get("rule_conf", 0),
                    "key_points":    veto.get("key_points", []),
                }
            else:
                veto_msg = {"master": "", "master_signal": "veto",
                            "veto_triggered": veto, "key_points": []}
            # 优先从 board 拿完整消息
            board_msg = agent_msgs.get(agent)
            if board_msg:
                veto_msg.update({k: board_msg[k] for k in
                                 ("key_points","rule_signal","rule_confidence",
                                  "master","veto_triggered") if k in board_msg})
                veto_msg["rule_conf"] = board_msg.get("rule_confidence",
                                        board_msg.get("confidence", 0))
            lines += render_agent_block(agent, veto_msg, "否决")
            lines.append("")

    # ── 板块分析 ──
    sector_info = result.get("sector_info", {})
    if sector_info:
        lines.append(section("板块分析"))
        lines.append("")
        si_name  = sector_info.get("sector", "")
        si_etf   = sector_info.get("etf", "")
        si_sig   = sector_info.get("signal", "neutral")
        si_conf  = sector_info.get("confidence", 0)
        si_peers = sector_info.get("peers", [])
        # 公司标签和说明（来自 COMPANY_OVERRIDES）
        from agents.sector_agent import COMPANY_OVERRIDES
        sym = result.get("symbol","").upper()
        ov = COMPANY_OVERRIDES.get(sym, {})
        tags = ov.get("tags", [])
        note = ov.get("note", "")
        lines.append(f"  板块: {si_name}  参考ETF: {si_etf}")
        if tags:
            lines.append(f"  业务标签: {' | '.join(tags)}")
        if note:
            lines.append(f"  公司定位: {note}")
        lines.append(f"  板块信号: {SIGNAL_ICON.get(si_sig)} ({si_conf}%)  {SIGNAL_COLOR.get(si_sig,'')}")
        for kp in sector_info.get("key_points", []):
            lines.append(f"  {kp}")
        lines.append("")

    # ── 近期新闻 ──
    lines += render_news(board, agent_msgs)

    # ── 辩论过程 ──
    debate_lines = render_debate(board)
    if debate_lines:
        lines += debate_lines

    # ── 综合结论 ──
    lines.append(section("综合结论"))
    lines.append("")
    signal = result["signal"]
    conf   = result["confidence"]
    lines.append(f"  信号:  {SIGNAL_ICON.get(signal)}  {SIGNAL_COLOR.get(signal,'')}")
    agent_conf  = result.get("agent_conf", raw_c)
    master_conf = result.get("master_conf")
    master_src  = result.get("master_source", "")
    blend       = result.get("blend_weights", {})
    if master_conf is not None and master_src == "persona_synthesis":
        lines.append(f"  信心:  {conf}%  "
                     f"(执行层{agent_conf}%×{blend.get('agent',0.4):.0%} + 大师层{master_conf}%×{blend.get('master',0.6):.0%} → 宏观折扣后)")
    else:
        lines.append(f"  信心:  {conf}%  "
                     f"(原始 {raw_c}% × 覆盖折扣 {decay:.0%})")
    if result.get("stop_loss"):
        lines.append(f"  止损:  ${result['stop_loss']:.2f}")
    else:
        lines.append("  止损:  基本面止损，无固定价格")

    if result.get("disputes"):
        lines.append("")
        lines.append("  ⚠ 未解决分歧（风险项）:")
        for d in result["disputes"]:
            lines.append(f"    · {d}")

    # ── 宏观前提声明（#3）────────────────────────────────────────
    macro = result.get("macro_factors", {})
    if macro:
        disc   = result.get("macro_discount", 1.0)
        gates  = result.get("entry_gates", {})
        vix    = macro.get("vix", "?")
        trend  = macro.get("vix_trend", "")
        spy    = macro.get("spy_chg", 0)
        qqq5m  = macro.get("qqq_5m", 0)
        disc_s = f"×{disc:.0%} 折扣已应用" if disc < 0.99 else "无折扣"
        all_ok = all(gates.values()) if gates else True
        gate_s = " ".join(f"{'✅' if v else '❌'}{k}" for k, v in gates.items())
        lines.append("")
        lines.append(f"  【宏观前提】VIX={vix}{trend} | SPY{spy:+.2f}% | QQQ5m{qqq5m:+.2f}%  置信度{disc_s}")
        lines.append(f"  入场条件:  {'🟢全通过' if all_ok else '🔴部分未通过'}  {gate_s}")
        lines.append("  ※ 若大盘转逆风（VIX↑ / QQQ<-0.5%），本结论置信度自动打折")

    lines.append("")
    lines.append("═" * W)
    return "\n".join(lines)

def generate_cio_llm_synthesis(sym: str, result: dict, board: list) -> str:
    """调用大模型为深度分析报告合成 CIO 综合决策综述 (包括宏观、技术、板块共振与大师辩论总结)"""
    try:
        from agents.llm_client import LLMClient
        client = LLMClient()
        if not client.is_configured():
            return None
        
        # 格式化各个维度的信号
        agent_sigs = []
        for ag, s in result.get("agent_signals", {}).items():
            agent_sigs.append(f"{ag.replace('Agent','')}: {s.get('signal')} ({s.get('confidence')}%)")
        agent_sigs_str = ", ".join(agent_sigs)
        
        # 格式化板块定位
        sec = result.get("sector_info", {})
        sec_str = f"细分行业: {sec.get('sector')} (参考ETF: {sec.get('etf')}), 板块信号: {sec.get('signal')} ({sec.get('confidence')}%)"
        
        # 格式化宏观指标
        mac = result.get("macro_factors", {})
        mac_str = f"VIX: {mac.get('vix')} (趋势: {mac.get('vix_trend')}), SPY今日变化: {mac.get('spy_chg')}%, QQQ今日5m变化: {mac.get('qqq_5m')}%"
        
        # 格式化大师辩论对话
        debate_lines = []
        from agents.report_agent import latest_per_agent
        agent_msgs = latest_per_agent(board)
        for ag, msg in agent_msgs.items():
            debate_lines.append(f"{ag.replace('Agent','')}: signal={msg.get('signal')}, key_points={msg.get('key_points', [])[:2]}")
        debate_str = "\n".join(debate_lines)
        
        system_prompt = (
            "You are the senior Chief Investment Officer (CIO) of an elite multi-strategy hedge fund.\n"
            "You need to synthesize today's multi-agent quantitative reports, master debates, and macro factors into a single highly professional investment summary.\n"
            "Write a cohesive three-paragraph review in Chinese:\n"
            "- Paragraph 1: Outlines the tactical stance on this stock based on current price trend, technical setup, and macro water temperature.\n"
            "- Paragraph 2: Evaluates the specific sector synergy, industry correlations, leader-follower transmission (e.g. NVDA leading AMD, or Azure spend driving software), and relative strength.\n"
            "- Paragraph 3: Summarizes the master debate consensus, highlights critical risk warning flags, and provides concrete execution guidance.\n"
            "Ensure your tone is elegant, authoritative, and completely objective. Max 400 characters total."
        )
        
        prompt = (
            f"Please synthesize the investment thesis for stock: {sym.upper()}\n"
            f"Unified Signal: {result.get('signal')} (Confidence: {result.get('confidence')}%)\n"
            f"Multi-Agent Signals: {agent_sigs_str}\n"
            f"Sector Outlook: {sec_str}\n"
            f"Macro Water Temp: {mac_str}\n"
            f"Master Debates & Stances:\n{debate_str}\n\n"
            f"Generate the professional Chinese summary:"
        )
        
        response = client.call_llm(prompt=prompt, system_prompt=system_prompt)
        return response.strip()
    except Exception as e:
        return f"CIO 大模型决策综述生成失败: {str(e)}"


def write_html(result, board=None):
    if board is None:
        board = load_board()
    env    = Environment(loader=FileSystemLoader(os.path.join(BASE, "templates")))
    tmpl   = env.get_template("report.html.j2")
    
    # 按 symbol + 日期命名，支持并行跑不冲突
    sym    = result.get("symbol", result.get("sym", "UNKNOWN")).upper()
    date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)
    path   = os.path.join(BASE, "reports", f"{date_tag}_{sym}.html")
    
    # 保证向后兼容，当 result 中缺少全新引入的属性时提供优雅默认值，避免 Jinja2 渲染崩溃
    render_ctx = {
        "coverage_decay": 1.0,
        "active_count": 6,
        "agent_signal": "neutral",
        "agent_conf": 50,
        "master_signal": "neutral",
        "master_conf": 50,
        "master_source": "unknown",
        "macro_factors": {},
        "macro_discount": 1.0,
        "entry_gates": {},
        "sector_info": {},
        "veto_agents": {},
    }
    render_ctx.update(result)
    
    # ── 触发大模型综述合成 ──────────────────────────────────────────
    cio_synthesis = generate_cio_llm_synthesis(sym, render_ctx, board)
    render_ctx["cio_llm_synthesis"] = cio_synthesis
    
    # ── 加载持仓论点与硬证伪边界 ──────────────────────────────────────────
    positions_cfg = {}
    try:
        pos_path = os.path.join(BASE, "config", "positions.json")
        if os.path.exists(pos_path):
            with open(pos_path, encoding="utf-8") as f:
                pos_data = json.load(f)
                positions_cfg = pos_data.get("positions", {}).get(sym, {})
    except Exception:
        pass
    render_ctx["positions_cfg"] = positions_cfg
    
    open(path, "w", encoding="utf-8").write(tmpl.render(**render_ctx, board=board,
                                      agent_msgs=latest_per_agent(board)))
    return path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    args   = parser.parse_args()
    result = json.load(open(STRATEGY_PATH, encoding="utf-8"))
    board  = load_board()
    print(terminal_summary(result, board))
    path = write_html(result, board)
    print(f"[报告] 已保存: {path}")

if __name__ == "__main__":
    main()
