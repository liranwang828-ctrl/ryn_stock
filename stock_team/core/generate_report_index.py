"""
报告统一索引生成器 — generate_report_index.py
自动扫描 reports/ 目录下所有的 HTML/Markdown 报告，
按日期倒序分类整理成一个极具设计感的“复盘与研报统一导航主页” (reports/index.html)，
解决报告零散、编排混乱的问题。
"""
import os, sys, glob, re
from datetime import datetime

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
REPORTS_DIR = os.path.join(BASE, "reports")


def generate_index(reports_dir: str = REPORTS_DIR) -> str:
    """扫描并生成 reports/index.html"""
    print("  正在扫描 reports 目录，自动生成报告索引主页...")
    os.makedirs(reports_dir, exist_ok=True)
    
    html_files = glob.glob(os.path.join(reports_dir, "*.html"))
    
    # 建立日期分组数据库
    # registry = { "YYYY-MM-DD": { "dashboards": [], "sandboxes": [], "research": [], "debates": [] } }
    registry = {}
    
    def get_or_create_date(d_str):
        if d_str not in registry:
            registry[d_str] = {
                "dashboards": [],
                "sandboxes": [],
                "research": [],
                "debates": []
            }
        return registry[d_str]

    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    
    for path in html_files:
        fname = os.path.basename(path)
        if fname in ["index.html", "preview_dashboard.html", "layout_comparison_demo.html", "watchlist_console.html"]:
            continue
            
        # 尝试提取日期
        match = date_pattern.search(fname)
        file_date = "2026-05-26"  # 默认兜底
        if match:
            file_date = match.group(1)
            
        entry = {
            "name": fname,
            "path": fname, # 相对路径
            "size": round(os.path.getsize(path) / 1024, 1)
        }
        
        # 分类归档
        if "daily_dashboard" in fname:
            get_or_create_date(file_date)["dashboards"].append(entry)
        elif "postmarket_sandbox" in fname:
            get_or_create_date(file_date)["sandboxes"].append(entry)
        elif "discussion" in fname or "debate" in fname:
            # 净化辩论文件命名显示
            # discussion_2026-05-26_lite_cohr_v3.html -> LITE vs COHR 深度论证 (V3)
            title = "多Agent专题论证"
            if "lite_cohr" in fname:
                ver = "V3" if "v3" in fname else ("V2" if "v2" in fname else "V1")
                title = f"光模块 LITE vs COHR 深度讨论辩论 ({ver})"
            entry["title"] = title
            get_or_create_date(file_date)["debates"].append(entry)
        else:
            # 个股研报或行业研报
            # 2026-05-26_COHR.html -> COHR 个股深度研报
            sym_match = re.search(r"\d{4}-\d{2}-\d{2}_([A-Z]+)\.html", fname)
            if sym_match:
                entry["title"] = f"{sym_match.group(1)} 盘前深度评级研报"
            else:
                entry["title"] = fname.replace(".html", "").replace("_", " ")
            get_or_create_date(file_date)["research"].append(entry)

    # 日期倒序排序
    sorted_dates = sorted(registry.keys(), reverse=True)
    
    # 构造 HTML 结构
    rows_html = ""
    for d in sorted_dates:
        day_data = registry[d]
        
        # 是否有任何内容
        has_content = any([day_data["dashboards"], day_data["sandboxes"], day_data["research"], day_data["debates"]])
        if not has_content:
            continue
            
        dash_links = ""
        for item in day_data["dashboards"]:
            dash_links += f"""
            <a href="{item['path']}" target="_blank" class="rep-link dash-link">
                <span class="icon">🖥️</span>
                <div class="rep-text">
                    <span class="rep-name">每日交易主仪表盘</span>
                    <span class="rep-sub">Size: {item['size']} KB</span>
                </div>
            </a>
            """
            
        sandbox_links = ""
        for item in day_data["sandboxes"]:
            sandbox_links += f"""
            <a href="{item['path']}" target="_blank" class="rep-link sandbox-link">
                <span class="icon">⏱️</span>
                <div class="rep-text">
                    <span class="rep-name">盘后分析沙盒复盘报告</span>
                    <span class="rep-sub">LLM大师点评 + 最优入场审计 · {item['size']} KB</span>
                </div>
            </a>
            """
            
        research_links = ""
        for item in day_data["research"]:
            research_links += f"""
            <a href="{item['path']}" target="_blank" class="rep-link research-link">
                <span class="icon">📝</span>
                <div class="rep-text">
                    <span class="rep-name">{item.get('title', item['name'])}</span>
                    <span class="rep-sub">{item['size']} KB</span>
                </div>
            </a>
            """
            
        debate_links = ""
        for item in day_data["debates"]:
            debate_links += f"""
            <a href="{item['path']}" target="_blank" class="rep-link debate-link">
                <span class="icon">⚖️</span>
                <div class="rep-text">
                    <span class="rep-name">{item.get('title', item['name'])}</span>
                    <span class="rep-sub">{item['size']} KB</span>
                </div>
            </a>
            """
            
        if not dash_links: dash_links = "<div class='no-doc'>当日无看板</div>"
        if not sandbox_links: sandbox_links = "<div class='no-doc'>当日未运行复盘沙盒</div>"
        if not research_links: research_links = "<div class='no-doc'>无个股盘前研报</div>"
        if not debate_links: debate_links = "<div class='no-doc'>无专题论证辩论</div>"

        # 添加到行列表
        rows_html += f"""
        <div class="date-group-card">
            <div class="date-sidebar">
                <div class="sticky-date">
                    <div class="date-icon">📅</div>
                    <div class="date-text">{d}</div>
                </div>
            </div>
            <div class="date-main-content">
                <div class="group-grid">
                    <!-- 看板 -->
                    <div class="group-column">
                        <h3>📊 每日主控制台</h3>
                        <div class="links-list">{dash_links}</div>
                    </div>
                    <!-- 沙盒复盘 -->
                    <div class="group-column">
                        <h3>⚡ 盘后复盘沙盒</h3>
                        <div class="links-list">{sandbox_links}</div>
                    </div>
                    <!-- 盘前个股研报 -->
                    <div class="group-column">
                        <h3>🔍 个股盘前分析</h3>
                        <div class="links-list">{research_links}</div>
                    </div>
                    <!-- 辩论讨论 -->
                    <div class="group-column">
                        <h3>💬 专题论证与辩论</h3>
                        <div class="links-list">{debate_links}</div>
                    </div>
                </div>
            </div>
        </div>
        """

    # 完整 HTML
    index_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>统一研报与复盘报告控制台门户 — stock_team Portal</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.5);
            --bg-card-border: rgba(255, 255, 255, 0.05);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --primary: #6366f1;
            --success: #10b981;
            --danger: #f43f5e;
            --warning: #f59e0b;
        }}
        
        * {{
            box-shadow: border-box;
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            padding: 40px 24px;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
            background-attachment: fixed;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--bg-card-border);
            padding: 32px;
            border-radius: 24px;
            margin-bottom: 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.8px;
            background: linear-gradient(to right, #f8fafc, #c7d2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .portal-stats {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            font-weight: 500;
            background: rgba(255, 255, 255, 0.05);
            padding: 6px 14px;
            border-radius: 30px;
            border: 1px solid var(--bg-card-border);
        }}
        
        /* Date Group Card */
        .date-group-card {{
            background: var(--bg-card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--bg-card-border);
            border-radius: 24px;
            margin-bottom: 24px;
            display: flex;
            overflow: hidden;
            transition: border-color 0.2s;
        }}
        
        .date-group-card:hover {{
            border-color: rgba(255, 255, 255, 0.1);
        }}
        
        .date-sidebar {{
            width: 200px;
            background: rgba(0, 0, 0, 0.2);
            border-right: 1px solid var(--bg-card-border);
            padding: 32px 24px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }}
        
        .sticky-date {{
            position: sticky;
            top: 24px;
        }}
        
        .date-icon {{
            font-size: 1.8rem;
            margin-bottom: 8px;
        }}
        
        .date-text {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--text-primary);
        }}
        
        .date-main-content {{
            flex-grow: 1;
            padding: 28px;
        }}
        
        .group-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
        }}
        
        .group-column {{
            display: flex;
            flex-direction: column;
        }}
        
        .group-column h3 {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            font-weight: 600;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 8px;
        }}
        
        .links-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            flex-grow: 1;
        }}
        
        /* Links Style */
        .rep-link {{
            background: rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.02);
            border-radius: 12px;
            padding: 12px 16px;
            color: var(--text-primary);
            text-decoration: none;
            display: flex;
            gap: 12px;
            align-items: center;
            transition: all 0.2s;
        }}
        
        .rep-link:hover {{
            background: rgba(255, 255, 255, 0.03);
            border-color: rgba(99, 102, 241, 0.3);
            transform: translateY(-1px);
        }}
        
        .icon {{
            font-size: 1.2rem;
            flex-shrink: 0;
        }}
        
        .rep-text {{
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        .rep-name {{
            font-size: 0.85rem;
            font-weight: 600;
            line-height: 1.3;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .rep-sub {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 2px;
        }}
        
        /* Card Types Coloring Hover */
        .dash-link:hover {{ border-color: rgba(99, 102, 241, 0.4); }}
        .sandbox-link:hover {{ border-color: rgba(245, 158, 11, 0.4); }}
        .research-link:hover {{ border-color: rgba(16, 185, 129, 0.4); }}
        .debate-link:hover {{ border-color: rgba(139, 92, 246, 0.4); }}
        
        .no-doc {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-style: italic;
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.01);
            border-radius: 8px;
            border: 1px dashed rgba(255, 255, 255, 0.03);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-grow: 1;
            min-height: 50px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div>
                <h1>🔮 stock_team 统一报告控制台门户</h1>
                <p style="color:var(--text-secondary);font-size:0.95rem;margin-top:4px;">聚合每日仪表盘、盘前评级研报、多Agent深度辩论、以及盘后分析沙盒复盘报告</p>
            </div>
            <div class="portal-stats">
                扫描到的文档：{len(html_files)} 份
            </div>
        </header>
        
        <!-- Master Watchlist Control Console Entrance (Master Panel) -->
        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(16, 185, 129, 0.1) 100%); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(99, 102, 241, 0.25); padding: 24px; border-radius: 24px; margin-bottom: 32px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 8px 32px rgba(99, 102, 241, 0.1);">
            <div style="display: flex; align-items: center; gap: 20px;">
                <div style="font-size: 2.5rem; background: rgba(99, 102, 241, 0.1); width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; border-radius: 20px; border: 1px solid rgba(99, 102, 241, 0.2);">🔮</div>
                <div>
                    <h2 style="font-family: 'Outfit', sans-serif; font-size: 1.3rem; font-weight: 800; background: linear-gradient(to right, #ffffff, #c7d2fe); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">S/A/B/C/D/E 值得关注标的最优点位控制台</h2>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; line-height: 1.4;">
                        今日交易核心聚焦 · 2y行情大盘相对强度 (RS vs QQQ) · 底部反弹斜率与财报避雷 · 黄金击球买区偏差实时计算
                    </p>
                </div>
            </div>
            <a href="watchlist_console.html" style="background: linear-gradient(135deg, #6366f1, #10b981); color: white; text-decoration: none; padding: 12px 24px; border-radius: 30px; font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 0.9rem; box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35); transition: all 0.2s; display: flex; align-items: center; gap: 8px;">
                进入点位控制大表单 ➔
            </a>
        </div>

        <!-- Rows Grouped by Date -->
        {rows_html}
        
        <!-- Footer -->
        <footer style="text-align:center;padding:32px 0;color:var(--text-secondary);font-size:0.8rem;border-top:1px solid rgba(255, 255, 255, 0.05);margin-top:40px;">
            <p>Antigravity stock_team Portal System · {datetime.now().strftime("%Y-%m-%d")}</p>
        </footer>
    </div>
</body>
</html>
    """
    
    out_path = os.path.join(reports_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(index_html)
        
    print(f"[OK] 统一报告门户已生成！您可以直接打开访问：{os.path.abspath(out_path)}")
    return out_path


if __name__ == "__main__":
    generate_index()
