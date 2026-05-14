import sys, os, json, argparse
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import BASE, STRATEGY_PATH, BOARD_PATH
from jinja2 import Environment, FileSystemLoader

SIGNAL_ICON  = {"bullish": "↑ 看涨", "bearish": "↓ 看空", "neutral": "→ 中性"}
SIGNAL_COLOR = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}
W = 62   # report width

def hr(char="─", w=W):
    """Return a horizontal rule string of the given character and width."""
    return char * w

def section(title):
    """Return a centered section header string."""
    pad = (W - len(title) - 2) // 2
    return f"{'─'*pad} {title} {'─'*(W - pad - len(title) - 2)}"

def fmt_ts(ts):
    """Format an ISO timestamp for display (YYYY-MM-DD HH:MM UTC)."""
    return ts[:16].replace("T", " ") + " UTC" if ts else ""

def load_board():
    """Read and parse the discussion board JSONL file."""
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
    """Render a single agent's full analysis block for terminal output."""
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
    """Extract news items from SentimentAgent key_points for display."""
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
    """Render the debate board as a chronological conversation highlighting challenge-response chains."""
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
    """Build the full terminal-formatted analysis report string."""
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

    lines.append("")
    lines.append("═" * W)
    return "\n".join(lines)

def write_html(result, board=None):
    """Render the analysis report as HTML using the Jinja2 template."""
    if board is None:
        board = load_board()
    env    = Environment(loader=FileSystemLoader(os.path.join(BASE, "templates")))
    tmpl   = env.get_template("report.html.j2")
    ts_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
    os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)
    path   = os.path.join(BASE, "reports", f"{ts_tag}.html")
    open(path, "w", encoding="utf-8").write(tmpl.render(**result, board=board,
                                      agent_msgs=latest_per_agent(board)))
    return path

def main():
    """Load strategy results, render HTML report, and print terminal summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    args   = parser.parse_args()
    result = json.load(open(STRATEGY_PATH, encoding="utf-8"))
    board  = load_board()
    path = write_html(result, board)
    print(terminal_summary(result, board))
    print(f"[报告] 已保存: {path}")

if __name__ == "__main__":
    main()
