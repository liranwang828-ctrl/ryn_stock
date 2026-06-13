"""
盘后复盘分析沙盒主入口 — postmarket_sandbox.py
核心功能：
1. 编排并运行完整的盘后沙盒复盘流水线：
   Step 1: 数据聚合与交易动作自动识别 (build_trade_context)
   Step 2: 抓取日内分时行情，进行深度交易动作复盘 (postmarket_trade_review)
   Step 3: 进行决策质量审计、计划匹配、覆写评估及关键价位有效性分析 (postmarket_decision_audit)
   Step 4: 启动 7 位大师的 LLM 深度点评进程 (postmarket_master_eval)
   Step 5: 整合并输出结构化 JSON 文件 (postmarket_summary_{date}.json)
   Step 6: 输出极具美感、玻璃拟态、交互式的 HTML 盘后复盘报告 (reports/postmarket_sandbox_{date}.html)
"""
import sys, os, json, glob
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stock_team.data_ingest.postmarket_data_collector import build_trade_context
from stock_team.data_ingest.postmarket_trade_review import review_all_trades
from stock_team.data_ingest.postmarket_decision_audit import generate_audit_report
from stock_team.data_ingest.postmarket_master_eval import eval_all_masters
from stock_team.data_ingest.postmarket_review import _market_3tier_review, _load_today_data

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))


def generate_html_report(date_str: str, trade_review: dict, decision_audit: dict, master_eval: dict, today_data: dict, base_dir: str = BASE) -> str:
    """
    生成高度美观、玻璃拟态、交互式的 HTML 复盘报告。
    使用深色极简风格，配合和谐的 HSL 渐变，带微交互动效。
    """
    trades = trade_review.get("reviewed_trades", [])
    pnl = today_data.get("position_pnl", {})
    total_gain = sum(v["gain_amt"] for v in pnl.values()) if pnl else 0.0
    
    # 构造 HTML 的大盘部分（三段式复盘的数据汇总）
    # 由于大盘三段式复盘在 postmarket_review.py 里是 print 出来的，我们在这里直接用 yfinance 拉取用于展示
    import yfinance as yf
    spy_chg = qqq_chg = vix_cur = vix_chg = 0.0
    try:
        spy = yf.Ticker("SPY").history(period="2d")
        qqq = yf.Ticker("QQQ").history(period="2d")
        vix = yf.Ticker("^VIX").history(period="2d")
        if len(spy) >= 2: spy_chg = (spy["Close"].iloc[-1] - spy["Close"].iloc[-2]) / spy["Close"].iloc[-2] * 100
        if len(qqq) >= 2: qqq_chg = (qqq["Close"].iloc[-1] - qqq["Close"].iloc[-2]) / qqq["Close"].iloc[-2] * 100
        if not vix.empty:
            vix_cur = vix["Close"].iloc[-1]
            if len(vix) >= 2: vix_chg = (vix["Close"].iloc[-1] - vix["Close"].iloc[-2]) / vix["Close"].iloc[-2] * 100
    except Exception:
        pass

    # 1. 构建 Trades 表格 HTML
    trades_html = ""
    if not trades:
        trades_html = "<tr><td colspan='7' style='text-align:center;color:#94a3b8;'>今日无交易成交。</td></tr>"
    else:
        for t in trades:
            rev = t["review"]
            score = rev["score"]
            verdict = rev["verdict"]
            is_buy = "BUY" in t["action"] or "ADD" in t["action"]
            action_class = "action-buy" if is_buy else "action-sell"
            action_cn = "🟢 买入" if is_buy else "🔴 卖出"
            
            # 分数颜色
            score_color = "#f43f5e" # red
            if score >= 85: score_color = "#10b981" # green
            elif score >= 70: score_color = "#10b981"
            elif score >= 55: score_color = "#f59e0b" # yellow
            
            trades_html += f"""
            <tr class="trade-row">
                <td style="font-weight:600;font-family:'Outfit',sans-serif;">{t['sym']}</td>
                <td><span class="action-badge {action_class}">{action_cn}</span></td>
                <td style="font-family:'Outfit',sans-serif;">${t['cost']:.2f}</td>
                <td style="font-family:'Outfit',sans-serif;">{t['shares']}</td>
                <td style="font-family:'Outfit',sans-serif;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-weight:700;color:{score_color};">{score}</span>
                        <div class="score-bar-bg"><div class="score-bar-fill" style="width:{score}%;background-color:{score_color};"></div></div>
                    </div>
                </td>
                <td><span style="font-weight:600;">{verdict}</span></td>
                <td style="max-width:300px;font-size:0.85rem;color:#cbd5e1;line-height:1.4;">
                    <strong>最优切入点：</strong>{rev['optimal_entry']}<br>
                    <strong>微观诊断：</strong>{rev['micro_factor_suggestion']}
                </td>
            </tr>
            """

    # 2. 构建审计结果 HTML
    audits = decision_audit.get("entry_audit", {}).get("decisions_audit", [])
    audit_html = ""
    if not audits:
        audit_html = "<div style='color:#94a3b8;padding:12px;'>暂无今日决策审计记录。</div>"
    else:
        for a in audits:
            status_class = "audit-aligned"
            status_cn = "契合系统"
            if a["audit_status"] == "user_override":
                status_class = "audit-override"
                status_cn = "用户覆写(买)"
            elif a["audit_status"] == "user_override_sell":
                status_class = "audit-override-sell"
                status_cn = "用户覆写(卖)"
                
            ret_color = "#f43f5e" if a["day_ret_pct"] < 0 else "#10b981"
            ret_str = f"{a['day_ret_pct']:+.2f}%"
            
            audit_html += f"""
            <div class="audit-card">
                <div class="audit-card-header">
                    <span class="audit-sym">{a['sym']}</span>
                    <span class="audit-badge {status_class}">{status_cn}</span>
                </div>
                <div class="audit-card-body">
                    <div class="audit-meta-row">
                        <span>盘前系统建议: <strong style="color:#6366f1;">{a['sys_recommendation'].upper()}</strong> (得分 {a['sys_score']})</span>
                        <span>日内涨跌: <strong style="color:{ret_color};">{ret_str}</strong></span>
                    </div>
                    <p class="audit-desc">{a['detail']}</p>
                </div>
            </div>
            """

    # 3. 构建支撑位校验 HTML
    levels = decision_audit.get("level_audit", {}).get("key_level_audits", [])
    levels_html = ""
    if not levels:
        levels_html = "<div style='color:#94a3b8;padding:12px;'>今日无关键支撑位验证记录。</div>"
    else:
        for l in levels:
            status_class = "level-normal"
            status_cn = "支撑上方"
            if l["status"] == "fake_breach_recover":
                status_class = "level-recover"
                status_cn = "虚破收回 🛡️"
            elif l["status"] == "perfect_support":
                status_class = "level-perfect"
                status_cn = "极佳支撑 🎯"
            elif l["status"] == "breached":
                status_class = "level-breached"
                status_cn = "支撑破位 ⚠️"
                
            levels_html += f"""
            <div class="level-card">
                <div class="level-card-header">
                    <span class="level-sym">{l['sym']}</span>
                    <span class="level-badge {status_class}">{status_cn}</span>
                </div>
                <div class="level-card-body">
                    <div class="level-meta-row">
                        <span>设定支撑: <strong>${l['plan_support']:.2f}</strong></span>
                        <span>日内最低: <strong>${l['actual_low']:.2f}</strong> (偏差 {l['deviation_low_pct']:+.1f}%)</span>
                    </div>
                    <p class="level-desc">{l['analysis']}</p>
                </div>
            </div>
            """

    # 4. 构建 7 大师 LLM 复盘点评面板 HTML
    master_evals = master_eval.get("evaluations", {})
    master_tabs_html = ""
    master_panes_html = ""
    
    first_master = True
    for i, (m_name, ev) in enumerate(master_evals.items()):
        active_class = "active" if first_master else ""
        display_style = "display: block;" if first_master else "display: none;"
        first_master = False
        
        # 标签页按钮
        master_tabs_html += f"""
        <button class="tab-btn {active_class}" onclick="openMasterTab(event, 'pane-{m_name}')">
            {m_name}
            <span class="tab-score">{ev.get('score', 70)}分</span>
        </button>
        """
        
        # 亮点、担忧、明日建议
        h_html = "".join([f"<li>{h}</li>" for h in ev.get("highlights", [])]) or "<li>未识别到显著亮点</li>"
        c_html = "".join([f"<li>{c}</li>" for c in ev.get("concerns", [])]) or "<li>暂无重大隐患</li>"
        a_html = "".join([f"<li>{a}</li>" for a in ev.get("action_items", [])]) or "<li>暂无特定行动建议</li>"
        
        score_val = ev.get('score', 70)
        score_color = "#f43f5e"
        if score_val >= 80: score_color = "#10b981"
        elif score_val >= 60: score_color = "#f59e0b"
        
        master_panes_html += f"""
        <div id="pane-{m_name}" class="tab-pane" style="{display_style}">
            <div class="pane-header">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span class="pane-master-title">{m_name} 大师复盘</span>
                    <span class="pane-verdict">{ev.get('verdict', '中性')}</span>
                </div>
                <div class="pane-score-badge" style="background-color:{score_color}1a;color:{score_color};border:1px solid {score_color}40;">
                    评定分：{score_val}
                </div>
            </div>
            
            <div class="master-quote">
                “ {ev.get('eval_text', '')} ”
            </div>
            
            <div class="pane-grid">
                <div class="pane-col">
                    <h4 style="color:#10b981;margin-bottom:8px;font-size:0.95rem;display:flex;align-items:center;gap:6px;">🟢 今日闪光点</h4>
                    <ul>{h_html}</ul>
                </div>
                <div class="pane-col">
                    <h4 style="color:#f43f5e;margin-bottom:8px;font-size:0.95rem;display:flex;align-items:center;gap:6px;">🔴 警惕隐患点</h4>
                    <ul>{c_html}</ul>
                </div>
                <div class="pane-col">
                    <h4 style="color:#6366f1;margin-bottom:8px;font-size:0.95rem;display:flex;align-items:center;gap:6px;">📋 明日行动建议</h4>
                    <ul>{a_html}</ul>
                </div>
            </div>
        </div>
        """

    # 5. 生成完整 HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 盘后分析沙盒复盘报告 — {date_str}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --bg-card-border: rgba(255, 255, 255, 0.05);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --primary: #6366f1;
            --success: #10b981;
            --danger: #f43f5e;
            --warning: #f59e0b;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            padding: 24px;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.1) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
            background-attachment: fixed;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        /* Glassmorphism Header */
        header {{
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--bg-card-border);
            padding: 24px 32px;
            border-radius: 20px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #f8fafc, #a5b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .date-badge {{
            background: linear-gradient(135deg, var(--primary), #4f46e5);
            color: white;
            padding: 8px 16px;
            border-radius: 30px;
            font-weight: 700;
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }}
        
        /* Grid Layout */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 24px;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--bg-card-border);
            padding: 20px;
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s, border-color 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.1);
        }}
        
        .stat-label {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
            margin-bottom: 6px;
        }}
        
        .stat-value {{
            font-size: 1.8rem;
            font-weight: 800;
            font-family: 'Outfit', sans-serif;
        }}
        
        .stat-sub {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}
        
        /* Main Section Card */
        .section-card {{
            background: var(--bg-card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--bg-card-border);
            border-radius: 20px;
            padding: 28px;
            margin-bottom: 24px;
        }}
        
        .section-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 12px;
        }}
        
        /* Table Styles */
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        
        th {{
            color: var(--text-secondary);
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }}
        
        td {{
            padding: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            font-size: 0.9rem;
            vertical-align: middle;
        }}
        
        .trade-row:hover td {{
            background: rgba(255, 255, 255, 0.01);
        }}
        
        .action-badge {{
            padding: 4px 10px;
            border-radius: 30px;
            font-size: 0.8rem;
            font-weight: 700;
            display: inline-block;
        }}
        
        .action-buy {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        
        .action-sell {{
            background: rgba(244, 63, 94, 0.15);
            color: var(--danger);
            border: 1px solid rgba(244, 63, 94, 0.3);
        }}
        
        /* Progress Bar for Score */
        .score-bar-bg {{
            width: 80px;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            overflow: hidden;
            display: inline-block;
        }}
        
        .score-bar-fill {{
            height: 100%;
            border-radius: 4px;
        }}
        
        /* Master Tabs Interface */
        .tabs-container {{
            display: flex;
            gap: 24px;
            margin-top: 16px;
        }}
        
        .tabs-sidebar {{
            width: 240px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .tab-btn {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.03);
            color: var(--text-secondary);
            padding: 14px 18px;
            border-radius: 12px;
            cursor: pointer;
            text-align: left;
            font-weight: 600;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .tab-btn:hover {{
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }}
        
        .tab-btn.active {{
            background: linear-gradient(135deg, var(--primary), #4f46e5);
            color: white;
            border-color: transparent;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
        }}
        
        .tab-score {{
            font-size: 0.75rem;
            background: rgba(255, 255, 255, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Outfit', sans-serif;
        }}
        
        .tabs-content {{
            flex-grow: 1;
            background: rgba(255, 255, 255, 0.015);
            border: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 24px;
        }}
        
        .tab-pane {{
            animation: fadeIn 0.3s ease-in-out;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .pane-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 14px;
        }}
        
        .pane-master-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
        }}
        
        .pane-verdict {{
            font-size: 0.85rem;
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            padding: 3px 10px;
            border-radius: 30px;
            border: 1px solid rgba(99, 102, 241, 0.3);
            font-weight: 600;
        }}
        
        .pane-score-badge {{
            padding: 4px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
        }}
        
        .master-quote {{
            font-style: italic;
            color: #cbd5e1;
            font-size: 1.05rem;
            background: rgba(255, 255, 255, 0.02);
            border-left: 4px solid var(--primary);
            padding: 16px 20px;
            border-radius: 0 12px 12px 0;
            margin-bottom: 24px;
            line-height: 1.6;
        }}
        
        .pane-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }}
        
        .pane-col {{
            background: rgba(0, 0, 0, 0.15);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255, 255, 255, 0.02);
        }}
        
        .pane-col ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .pane-col li {{
            font-size: 0.85rem;
            color: #cbd5e1;
            margin-bottom: 8px;
            position: relative;
            padding-left: 14px;
            line-height: 1.4;
        }}
        
        .pane-col li::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: var(--primary);
            font-weight: bold;
        }}
        
        /* Audit Cards Layout */
        .audit-split {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        
        .audit-card, .level-card {{
            background: rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.02);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 14px;
        }}
        
        .audit-card-header, .level-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            padding-bottom: 8px;
        }}
        
        .audit-sym, .level-sym {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 1.05rem;
            color: var(--text-primary);
        }}
        
        .audit-badge, .level-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        
        .audit-aligned {{ background: rgba(16, 185, 129, 0.1); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.2); }}
        .audit-override {{ background: rgba(99, 102, 241, 0.1); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.2); }}
        .audit-override-sell {{ background: rgba(245, 158, 11, 0.1); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.2); }}
        
        .level-normal {{ background: rgba(255, 255, 255, 0.05); color: var(--text-secondary); }}
        .level-perfect {{ background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .level-recover {{ background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3); }}
        .level-breached {{ background: rgba(244, 63, 94, 0.15); color: var(--danger); border: 1px solid rgba(244, 63, 94, 0.3); }}
        
        .audit-meta-row, .level-meta-row {{
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }}
        
        .audit-desc, .level-desc {{
            font-size: 0.85rem;
            color: #cbd5e1;
            line-height: 1.4;
        }}
    </style>
    <script>
        function openMasterTab(evt, paneId) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tab-pane");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].style.display = "none";
            }}
            tablinks = document.getElementsByClassName("tab-btn");
            for (i = 0; i < tablinks.length; i++) {{
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }}
            document.getElementById(paneId).style.display = "block";
            evt.currentTarget.className += " active";
        }}
    </script>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div>
                <h1>📊 AI 盘后分析沙盒复盘报告</h1>
                <p style="color:var(--text-secondary);font-size:0.9rem;margin-top:4px;">对称盘前分析沙盒 · 基于实际分时行情与多维大师 LLM 点评</p>
            </div>
            <div class="date-badge">美东时间：{date_str}</div>
        </header>
        
        <!-- Stats Summary Grid -->
        <div class="dashboard-grid">
            <div class="stat-card">
                <span class="stat-label">今日成交总笔数</span>
                <span class="stat-value" style="color:var(--primary);">{trade_review.get('total_trades_count', 0)} 笔</span>
                <span class="stat-sub">新买入 {sum(1 for t in trades if "BUY" in t['action'])} 笔 | 补仓 {sum(1 for t in trades if "ADD" in t['action'])} 笔</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">当日净流向</span>
                <span class="stat-value" style="color:{'var(--success)' if trade_review.get('net_flow', 0) >= 0 else 'var(--danger)'};">
                    ${trade_review.get('net_flow', 0):+,.0f}
                </span>
                <span class="stat-sub">买入 ${trade_review.get('total_bought_value', 0):,.0f} | 卖出 ${trade_review.get('total_sold_value', 0):,.0f}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">多大师综合复盘评分</span>
                <span class="stat-value" style="color:var(--warning);">{master_eval.get('avg_master_score', 70)} / 100</span>
                <span class="stat-sub">大师共识：{master_eval.get('consensus', '中性')}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">主观覆写决策审计</span>
                <span class="stat-value" style="color:var(--success);">{decision_audit.get('entry_audit', {}).get('override_success_rate', 100)}% 胜率</span>
                <span class="stat-sub">覆写总数 {decision_audit.get('entry_audit', {}).get('override_total', 0)} 笔 | 成功 {decision_audit.get('entry_audit', {}).get('override_success_count', 0)} 笔</span>
            </div>
        </div>
        
        <!-- 今日成交分时复盘 -->
        <div class="section-card">
            <h2 class="section-title">⏱️ 今日成交微观诊断与最优入场点对齐</h2>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>标的</th>
                            <th>操作</th>
                            <th>执行价格</th>
                            <th>股数</th>
                            <th>点位质量得分</th>
                            <th>评级</th>
                            <th>日内分时统计与微观诊断（Optimal Entry Analysis）</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trades_html}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- 大师点评 -->
        <div class="section-card">
            <h2 class="section-title">👥 多大师 LLM 深度复盘（基于 rules & worldview 真实推理）</h2>
            <div class="tabs-container">
                <div class="tabs-sidebar">
                    {master_tabs_html}
                </div>
                <div class="tabs-content">
                    {master_panes_html}
                </div>
            </div>
        </div>
        
        <!-- 决策审计与点位校验 -->
        <div class="section-card">
            <h2 class="section-title">⚖️ 盘前决策审计与支撑点位有效性验证</h2>
            <div class="audit-split">
                <!-- 覆写与纪律审计 -->
                <div>
                    <h3 style="margin-bottom:16px;color:var(--primary);font-size:1.1rem;font-family:'Outfit',sans-serif;border-left:3px solid var(--primary);padding-left:8px;">主观覆写与执行纪律审计</h3>
                    {audit_html}
                </div>
                <!-- 关键点位审计 -->
                <div>
                    <h3 style="margin-bottom:16px;color:var(--success);font-size:1.1rem;font-family:'Outfit',sans-serif;border-left:3px solid var(--success);padding-left:8px;">盘前预设支撑位有效性对齐</h3>
                    {levels_html}
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <footer style="text-align:center;padding:24px 0;color:var(--text-secondary);font-size:0.8rem;border-top:1px solid rgba(255, 255, 255, 0.05);margin-top:40px;">
            <p>Antigravity stock_team Postmarket Sandbox System · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </footer>
    </div>
</body>
</html>
    """
    
    # 写入报告
    rep_dir = os.path.join(base_dir, "reports")
    os.makedirs(rep_dir, exist_ok=True)
    out_path = os.path.join(rep_dir, f"postmarket_sandbox_{date_str}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return out_path


def run_postmarket_sandbox(date_str: str = None, base_dir: str = BASE) -> dict:
    """
    运行盘后复盘分析沙盒主流程
    """
    if not date_str:
        # 默认昨天
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
    print(f"\n============================================================")
    # 运行大盘三段式复盘 (输出至控制台)
    _market_3tier_review(date_str)
    
    # Step 1: 加载基础数据并识别交易
    print(f"  [Step 1/6] 正在聚合决策背景数据...")
    today_data = _load_today_data(date_str)
    
    # Step 2: 深度交易动作复盘
    print(f"  [Step 2/6] 正在抓取日内 1-minute 走势并分析交易质量...")
    trade_review = review_all_trades(date_str, base_dir=base_dir)
    
    # Step 3: 进行决策质量审计
    print(f"  [Step 3/6] 正在进行决策审计和价位对齐...")
    decision_audit = generate_audit_report(date_str, trade_review, base_dir=base_dir)
    
    # Step 4: 启动多大师 LLM 深度点评
    print(f"  [Step 4/6] 正在启动大师点评流程 (LLM 基于 persona.json + worldview.md 深度推理)...")
    master_eval = eval_all_masters(today_data, trade_review, date_str, base_dir=base_dir)
    
    # Step 5: 整合并输出结构化 JSON 文件
    print(f"  [Step 5/6] 正在生成今日盘后总结总结 JSON 文件...")
    # 对齐盘前 summary
    consolidated_summary = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "today_data": today_data,
        "trade_review": trade_review,
        "decision_audit": decision_audit,
        "master_eval": master_eval,
        "suggestions": [] # 整合明日可应用建议
    }
    
    # 从大师和数据中提取合并建议
    # 1. 大师行动建议合并
    merged_suggs = []
    seen_desc = set()
    
    # 合并来自大师的建议
    for m_name, ev in master_eval.get("evaluations", {}).items():
        for item in ev.get("action_items", []):
            if item not in seen_desc:
                seen_desc.add(item)
                merged_suggs.append({
                    "type": "master_suggestion",
                    "priority": "high" if ev.get("score", 70) <= 60 else "medium",
                    "description": f"【{m_name} 大师建议】{item}",
                    "proposed_value": {"master": m_name, "action": item},
                    "confirmed": None, "applied_at": None, "applied_to": None
                })
                
    # 2. 从 trade_review 中对得分偏低（低于 70）的标的自动生成微观微调建议
    for t in trade_review.get("reviewed_trades", []):
        score = t["review"]["score"]
        if score < 70 and "BUY" in t["action"]:
            desc = f"【微观因子微调建议】今日 {t['sym']} 买入点位偏高（得分 {score}），原因：{t['review']['reason']}"
            if desc not in seen_desc:
                seen_desc.add(desc)
                merged_suggs.append({
                    "type": "trigger_deep_research" if score < 55 else "lesson_record",
                    "priority": "high" if score < 55 else "low",
                    "description": desc,
                    "proposed_value": {
                        "sym": t["sym"],
                        "lesson": f"{t['sym']}今日追高买入（得分{score}），应在支撑位挂限价单而非开盘追市价单。",
                        "reason": f"交易点位得分低 ({score})"
                    },
                    "confirmed": None, "applied_at": None, "applied_to": None
                })
                
    consolidated_summary["suggestions"] = merged_suggs
    
    # 写入 postmarket_summary_{date}.json
    find_dir = os.path.join(base_dir, "findings")
    out_json_path = os.path.join(find_dir, f"postmarket_summary_{date_str}.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(consolidated_summary, f, indent=2, ensure_ascii=False)
        
    # Step 6: 输出 HTML 盘后复盘报告
    print(f"  [Step 6/6] 正在渲染极具视觉震撼效果的 HTML 盘后复盘交互报告...")
    html_path = generate_html_report(date_str, trade_review, decision_audit, master_eval, today_data, base_dir=base_dir)
    
    # 自动更新统一报告门户索引
    try:
        from stock_team.core.generate_report_index import generate_index
        generate_index(reports_dir=os.path.join(base_dir, "reports"))
    except Exception as e:
        print(f"  [WARNING] 无法更新统一报告门户索引: {e}")
        
    print(f"============================================================")
    print(f"[OK] 盘后分析沙盒完整复盘成功！")
    print(f"- 结构化数据：{os.path.abspath(out_json_path)}")
    print(f"- 交互式HTML报告：{os.path.abspath(html_path)}")
    print(f"- 统一报告导航主页：{os.path.abspath(os.path.join(base_dir, 'reports', 'index.html'))}")
    print(f"============================================================\n")
    
    return consolidated_summary


if __name__ == "__main__":
    date_input = sys.argv[1] if len(sys.argv) > 1 else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    run_postmarket_sandbox(date_input)
