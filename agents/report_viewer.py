"""
研究报告可视化模块 — report_viewer.py（Notion 研报风）
将 strategic_memo_{sym}.json 渲染为可读 HTML 研究报告。

输出: reports/research_{sym}_{date}.html
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")
RPT_DIR  = os.path.join(BASE, "reports")


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _v(val, fmt=None, suffix="", na="—"):
    if val is None:
        return na
    if fmt:
        return fmt.format(val) + suffix
    return str(val) + suffix


def _pct(v, na="—"):
    return f"{v:+.1f}%" if v is not None else na


def _dollar(v, na="—"):
    return f"${v:.2f}" if v is not None else na


def _stars(n, total=5):
    n = int(n or 0)
    return "★" * n + "☆" * (total - n)


def _signal_badge(signal, confidence=None):
    colors = {
        "bullish":  ("rgba(16, 185, 129, 0.08)", "#10b981", "rgba(16, 185, 129, 0.25)"),
        "bearish":  ("rgba(244, 63, 94, 0.08)", "#f43f5e", "rgba(244, 63, 94, 0.25)"),
        "neutral":  ("rgba(245, 158, 11, 0.08)", "#f59e0b", "rgba(245, 158, 11, 0.25)"),
        "buy":      ("rgba(16, 185, 129, 0.08)", "#10b981", "rgba(16, 185, 129, 0.25)"),
        "no_buy":   ("rgba(244, 63, 94, 0.08)", "#f43f5e", "rgba(244, 63, 94, 0.25)"),
        "not_sell": ("rgba(245, 158, 11, 0.08)", "#f59e0b", "rgba(245, 158, 11, 0.25)"),
        "hold":     ("rgba(59, 130, 246, 0.08)", "#3b82f6", "rgba(59, 130, 246, 0.25)"),
    }
    bg, text, border = colors.get(signal, colors["neutral"])
    label = {"bullish": "看多", "bearish": "看空", "neutral": "中性",
             "buy": "买入", "no_buy": "不买", "not_sell": "不卖",
             "hold": "持有"}.get(signal, signal)
    conf_str = f" {confidence}%" if confidence else ""
    return (f'<span style="background:{bg};color:{text};border:1px solid {border};'
            f'padding:2.5px 12px;border-radius:12px;font-size:0.82em;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.02em;box-shadow: 0 0 10px {bg}">'
            f'{label}{conf_str}</span>')


def _stance_banner_cfg(stance):
    cfg = {
        "strong_hold": ("🟢", "rgba(16, 185, 129, 0.08)", "#10b981", "强力持有"),
        "hold":        ("🔵", "rgba(59, 130, 246, 0.08)", "#3b82f6", "持有"),
        "hold_reduced":("🟡", "rgba(245, 158, 11, 0.08)", "#f59e0b", "减仓持有"),
        "reduce":      ("🟠", "rgba(249, 115, 22, 0.08)", "#f97316", "考虑减仓"),
        "exit_ready":  ("🔴", "rgba(244, 63, 94, 0.08)", "#f43f5e", "准备出场"),
        "avoid":       ("⛔", "rgba(244, 63, 94, 0.08)", "#f43f5e", "回避"),
    }
    return cfg.get(stance, ("⚪", "rgba(255, 255, 255, 0.02)", "#9ca3af", stance or "—"))


def _card(title, body, icon=""):
    return (f'<div class="card"><div class="card-title">{icon} {title}</div>'
            f'{body}</div>')


def _kv_table(rows):
    html = '<table class="kv-table">'
    for row in rows:
        label, value = row[0], row[1]
        color = row[2] if len(row) > 2 else ""
        style = f'color:{color}; font-weight: 600;' if color else ""
        html += f'<tr><td class="kv-label">{label}</td><td style="{style}">{value}</td></tr>'
    html += '</table>'
    return html


CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg: #080b11;
  --bg-gradient: radial-gradient(circle at 50% 0%, #111827 0%, #080d16 60%, #03070c 100%);
  --card: rgba(13, 20, 35, 0.45);
  --border: rgba(255, 255, 255, 0.05);
  --border-hover: rgba(99, 102, 241, 0.3);
  --text: #f9fafb;
  --muted: #94a3b8;
  --accent: #6366f1;
  --accent-gradient: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  
  --green: #10b981;
  --green-bg: rgba(16, 185, 129, 0.08);
  --green-border: rgba(16, 185, 129, 0.2);
  
  --red: #f43f5e;
  --red-bg: rgba(244, 63, 94, 0.08);
  --red-border: rgba(244, 63, 94, 0.2);
  
  --yellow: #f59e0b;
  --radius: 14px;
  --shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.35);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  background-image: var(--bg-gradient);
  color: var(--text);
  font-size: 15px;
  line-height: 1.65;
  min-height: 100vh;
}

/* Custom Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(17, 24, 39, 0.3); }
::-webkit-scrollbar-thumb { background: rgba(99, 102, 241, 0.15); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99, 102, 241, 0.35); }

.top-bar {
  background: rgba(13, 20, 35, 0.7);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  padding: 1.1rem 2rem;
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
}

.top-bar h1 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.55rem;
  font-weight: 800;
  background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.top-bar .meta {
  color: var(--muted);
  font-size: 0.82rem;
  font-family: 'JetBrains Mono', monospace;
}

.top-bar a {
  color: #a5b4fc;
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4px 12px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.01);
  transition: all 0.2s;
}

.top-bar a:hover {
  color: #ffffff;
  border-color: var(--accent);
  background: rgba(99, 102, 241, 0.08);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.15);
}

.stance-banner {
  padding: 1.4rem 2rem;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.25);
}

.stance-label {
  font-family: 'Outfit', sans-serif;
  font-size: 1.8rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  text-shadow: 0 0 15px rgba(255, 255, 255, 0.05);
}

.stance-conf {
  font-size: 0.88rem;
  font-weight: 600;
  margin-top: 2px;
}

.stance-key {
  font-size: 0.95rem;
  max-width: 580px;
  line-height: 1.6;
  color: #cbd5e1;
  border-left: 2px solid rgba(255, 255, 255, 0.1);
  padding-left: 15px;
}

.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px 24px;
}

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; margin-bottom: 24px; }

@media (max-width: 850px) {
  .grid-2, .grid-3 { grid-template-columns: 1fr; gap: 20px; }
  .stance-key { border-left: none; padding-left: 0; }
}

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow), inset 0 1px 1px 0 rgba(255, 255, 255, 0.03);
  margin-bottom: 24px;
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.card:hover {
  border-color: var(--border-hover);
  box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.08), inset 0 1px 1px 0 rgba(255, 255, 255, 0.05);
  transform: translateY(-3px);
}

.card-title {
  font-family: 'Outfit', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 18px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-h2 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.25rem;
  font-weight: 800;
  background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 32px 0 16px;
  padding-bottom: 6px;
  border-bottom: 2px solid var(--accent);
  display: inline-block;
}

.kv-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.kv-table tr { border-bottom: 1px solid rgba(255, 255, 255, 0.04); transition: background 0.2s; }
.kv-table tr:hover { background: rgba(255, 255, 255, 0.01); }
.kv-table tr:last-child { border-bottom: none; }
.kv-label { color: var(--muted); padding: 9px 8px 9px 0; width: 38%; vertical-align: top; font-weight: 500; }
.kv-table td { padding: 9px 4px; }
.kv-table th { padding: 8px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-size: 0.76rem; border-bottom: 2px solid rgba(255, 255, 255, 0.06); }

.master-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 16px; }
.master-card {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-left: 3px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  padding: 16px;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15), inset 0 1px 0px rgba(255, 255, 255, 0.02);
}
.master-card:hover {
  background: rgba(255, 255, 255, 0.035);
  border-color: rgba(99, 102, 241, 0.2);
  transform: translateY(-2px);
}
.master-card-bullish {
  border-left-color: var(--green);
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.03), inset 0 1px 0px rgba(255, 255, 255, 0.02);
}
.master-card-bearish {
  border-left-color: var(--red);
  box-shadow: 0 4px 15px rgba(244, 63, 94, 0.03), inset 0 1px 0px rgba(255, 255, 255, 0.02);
}
.master-card-neutral {
  border-left-color: var(--yellow);
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.03), inset 0 1px 0px rgba(255, 255, 255, 0.02);
}

.master-name { font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1.05rem; color: #ffffff; display: flex; justify-content: space-between; align-items: center; }
.master-domain { color: var(--muted); font-size: 0.78rem; margin-top: 2px; margin-bottom: 10px; }
.master-arg { font-size: 0.88rem; color: #cbd5e1; line-height: 1.55; }
.master-inv { font-size: 0.8rem; color: #f43f5e; margin-top: 8px; font-style: italic; border-left: 2px solid #f43f5e; padding-left: 8px; background: rgba(244, 63, 94, 0.03); padding-top: 2px; padding-bottom: 2px; border-radius: 0 4px 4px 0; }

.tab-bar { display: flex; gap: 6px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 20px; flex-wrap: wrap; padding-bottom: 8px; }
.tab-btn {
  padding: 8px 18px;
  cursor: pointer;
  border: 1px solid transparent;
  background: none;
  color: var(--muted);
  font-size: 0.88rem;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.tab-btn:hover { color: #ffffff; background: rgba(255,255,255,0.03); }
.tab-btn.active { color: #ffffff; background: var(--accent-gradient); box-shadow: 0 4px 15px rgba(99,102,241,0.25); }
.tab-pane { display: none; animation: tabFade 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.tab-pane.active { display: block; }

@keyframes tabFade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

.kp-item { color: var(--green); font-size: 0.9rem; padding: 7px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.02); display: flex; align-items: flex-start; gap: 8px; line-height: 1.5; }
.kp-item:last-child { border-bottom: none; }
.para-item { font-size: 0.92rem; padding: 8px 0; color: #cbd5e1; line-height: 1.65; }
.concl-box { margin-top: 14px; padding: 12px 16px; background: rgba(99, 102, 241, 0.04); border-left: 3px solid var(--accent); border-radius: 0 10px 10px 0; font-size: 0.88rem; line-height: 1.55; border-top: 1px solid rgba(99, 102, 241, 0.06); border-bottom: 1px solid rgba(99, 102, 241, 0.06); border-right: 1px solid rgba(99, 102, 241, 0.06); }

.scenario-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.scenario-card {
  background: rgba(255, 255, 255, 0.015) !important;
  border: 1px solid rgba(255, 255, 255, 0.04) !important;
  border-radius: 12px !important;
  padding: 18px !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2) !important;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
.scenario-card:hover {
  background: rgba(255, 255, 255, 0.03) !important;
  border-color: rgba(99, 102, 241, 0.25) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 24px rgba(99,102,241,0.06) !important;
}
.scenario-price { font-family: 'Outfit', sans-serif; font-size: 1.7rem; font-weight: 800; line-height: 1.1; margin-top: 6px; }
.scenario-lbl { font-family: 'Outfit', sans-serif; font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
.scenario-cond { font-size: 0.86rem; margin-top: 10px; line-height: 1.5; color: #cbd5e1; }

.falsif-item { padding: 9px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.03); font-size: 0.88rem; display: flex; gap: 10px; align-items: flex-start; line-height: 1.5; }
.falsif-item:last-child { border-bottom: none; }

.debate-msg { padding: 12px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.04); font-size: 0.88rem; line-height: 1.6; }
.debate-msg:last-child { border-bottom: none; }

.synth-box { margin-top: 16px; padding: 14px 16px; background: rgba(99, 102, 241, 0.04); border-left: 3px solid var(--accent); border-radius: 0 10px 10px 0; font-size: 0.9rem; line-height: 1.6; border: 1px solid rgba(99, 102, 241, 0.06); border-left-width: 3px; }

.green { color: var(--green); }
.red { color: var(--red); }
.yellow { color: var(--yellow); }
.muted { color: var(--muted); }
.bold { font-weight: 700; color: #ffffff; }
.small { font-size: 0.8em; }
p.note { font-size: 0.82rem; color: var(--muted); font-style: italic; padding: 6px 0; }
</style>"""

SCRIPT = """<script>
function showTab(group,name,el){
  document.querySelectorAll('[data-group="'+group+'"].tab-pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('[data-group="'+group+'"].tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById(group+'-'+name).classList.add('active');
  el.classList.add('active');
}
window.addEventListener('load',function(){
  document.querySelectorAll('.tab-bar').forEach(bar=>{
    var first=bar.querySelector('.tab-btn');
    if(first)first.click();
  });
});
</script>"""


def render_trading_nodes(macro: dict, prev_macro: dict = None) -> str:
    """渲染宏观策略交易节点 HTML Section，可选与上次对比显示 delta。"""
    if not macro:
        return ""
    nodes = macro.get("nodes", {})
    if not nodes:
        return ""
    prev_nodes = (prev_macro or {}).get("nodes", {})

    def _delta(key: str, subkey: str = "price", prev_key: str = None) -> str:
        """计算节点价格变化，返回彩色 HTML。"""
        try:
            cur = nodes.get(key, {})
            prv = prev_nodes.get(prev_key or key, {})
            cur_p = cur.get(subkey) if isinstance(cur, dict) else None
            prv_p = prv.get(subkey) if isinstance(prv, dict) else None
            if cur_p is None or prv_p is None or not isinstance(cur_p, (int, float)):
                return ""
            diff = cur_p - prv_p
            if abs(diff) < 0.01:
                return ""
            pct  = diff / prv_p * 100
            sign = "↑" if diff > 0 else "↓"
            col  = "green" if diff > 0 else "red"
            return f"<span class='{col}' style='font-size:0.8em'> {sign}{abs(diff):.2f} ({pct:+.1f}%)</span>"
        except Exception:
            return ""

    def _row(label, price, basis, extra="", delta_html=""):
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "—"
        return (f"<tr><td class='kv-label'>{label}</td>"
                f"<td class='bold'>{price_str}{delta_html}</td>"
                f"<td class='muted small'>{basis or ''}</td>"
                f"<td class='small'>{extra}</td></tr>")

    ds   = nodes.get("dynamic_stop", {})
    fe   = nodes.get("force_exit", {})
    add1 = nodes.get("add1") or {}
    add2 = nodes.get("add2") or {}
    tp1  = nodes.get("tp1", {})
    tp2  = nodes.get("tp2", {})
    sd   = nodes.get("scenario_downgrade", {})

    rows = [
        _row("动态止损",       ds.get("price"),  ds.get("basis", ""),  ds.get("invalidation", ""), _delta("dynamic_stop")),
        _row("强制清仓(熊市)", fe.get("price_bear"), fe.get("basis_bear", ""), "论点破裂兜底",       _delta("force_exit", "price_bear")),
        _row("Add1 加仓",     add1.get("price"), add1.get("basis", ""), add1.get("invalidation", ""), _delta("add1")),
        _row("Add2 加仓",     add2.get("price") if add2 else None, add2.get("basis", "") if add2 else "", "需 confidence≥4", _delta("add2") if add2 else ""),
        _row("TP1 目标(30%)", tp1.get("price"),  tp1.get("basis", ""), "第一批减仓",               _delta("tp1")),
        _row("TP2 目标(全清)", tp2.get("price"), tp2.get("basis", ""), tp2.get("invalidation", ""), _delta("tp2")),
        _row("情景降级 bull→base", sd.get("bull_to_base", {}).get("price"), sd.get("bull_to_base", {}).get("basis", ""), "", _delta("scenario_downgrade", "price")),
        _row("情景降级 base→bear", sd.get("base_to_bear", {}).get("price"), sd.get("base_to_bear", {}).get("basis", ""), "", _delta("scenario_downgrade", "price", "scenario_downgrade")),
    ]

    re_entry  = nodes.get("re_entry") or {}
    entry_inv = nodes.get("entry_invalidation", {})
    rows += [
        _row("追涨上限", entry_inv.get("price"), entry_inv.get("basis", ""), "超此价不追入", _delta("entry_invalidation")),
        _row("重建仓位", re_entry.get("price"),  re_entry.get("basis", ""),
             re_entry.get("invalidation", "") if re_entry else "止损后论点intact时重建", _delta("re_entry")),
    ]

    ts = nodes.get("time_stop", {})
    time_str  = f"时间止损: {ts.get('review_date', '?')} — {ts.get('condition', '')}" if ts else ""
    has_delta = bool(prev_nodes)
    delta_note = f"<span class='muted small'>△ 较上次: {prev_macro.get('market_data_date','?')}</span>" if has_delta else ""

    return f"""
<h2 class="section-h2">📐 交易节点（宏观策略）</h2>
<div class="card">
  <div class="card-title">价格节点 · 计算依据 · 失效条件 &nbsp;{delta_note}
    <a href="trading_nodes_guide.html" target="_blank"
       style="float:right;font-size:0.82em;color:var(--accent)">📖 节点使用说明 →</a>
  </div>
  <table class="kv-table">
    <tr><th>节点</th><th>价格</th><th>计算依据</th><th>失效/说明</th></tr>
    {''.join(rows)}
  </table>
  {f'<p class="note">{time_str}</p>' if time_str else ''}
  <p class="note muted">系数版本: {macro.get("evolution", {}).get("rule_version", "?")} |
  数据日期: {macro.get("market_data_date", "?")}</p>
</div>
"""


def _underlying_sym(sym: str) -> str:
    """若 sym 是杠杆 ETF，返回底层股票代码；否则返回 sym 本身。"""
    pairs = _load(os.path.join(BASE, "config", "leveraged_pairs.json"))
    # leveraged_pairs.json 是 underlying→etf 映射，构建反向表
    etf_to_underlying = {v["sym"].upper(): k.upper()
                         for k, v in pairs.items()
                         if isinstance(v, dict) and "sym" in v}
    return etf_to_underlying.get(sym.upper(), sym.upper())


def render_research_report(sym: str, date: str) -> str:
    sym_upper  = sym.upper()
    # 自动感应与补全：如果 macro_strategy_{SYM}.json 缺失，自动调用后台脚本生成
    macro_path = os.path.join(BASE, f"macro_strategy_{sym_upper}.json")
    if not os.path.exists(macro_path):
        try:
            import subprocess
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            subprocess.run([sys.executable, os.path.join(BASE, "agents", "macro_strategy.py"), sym_upper], cwd=BASE, env=env, check=True)
        except Exception:
            pass

    # 杠杆 ETF：分析内容读底层股票 memo，节点用 ETF 自身的 macro_strategy
    ana_sym      = _underlying_sym(sym_upper)   # 底层股票（badge 永远显示此值）
    is_leveraged = ana_sym != sym_upper
    data_sym     = ana_sym                       # 实际读取数据用的 sym（fallback 时变为 ETF）

    memo = _load(os.path.join(BASE, f"strategic_memo_{ana_sym}.json"))
    if not memo:
        memo = _load(os.path.join(BASE, f"strategic_memo_{sym_upper}.json"))
        data_sym = sym_upper  # fallback 到 ETF 自身数据，但 badge 仍显示底层 sym
    pm   = _load(os.path.join(FIND_DIR, f"premarket_summary_{date}_{sym_upper}.json"))
    fund = _load(os.path.join(FIND_DIR, f"fundamentals_{data_sym}.json"))
    narr = _load(os.path.join(FIND_DIR, f"narrative_{data_sym}_{date}.json"))

    # Extract memo sections
    synth    = memo.get("synthesis", {})
    judg     = memo.get("judgment", {})
    sr       = memo.get("support_and_risk", {})
    fnd      = memo.get("foundation", {})
    outlook  = memo.get("outlook", {})
    pos_ctx  = memo.get("position_context", {})
    ag_an    = memo.get("agent_analysis", {})
    debate   = memo.get("debate_highlights", {})
    scens    = memo.get("scenarios", {})
    mvotes   = judg.get("master_votes", {})
    mvsum    = mvotes.get("_summary", {})
    fsnap    = fnd.get("fundamentals_snapshot", {})
    pos_snap = pos_ctx.get("position_snapshot", {})

    # Narrative data (from cio Phase3 — richer text)
    ag_narr   = narr.get("agent_narratives", {})
    ma_narr   = narr.get("master_narratives", {})
    debate_d  = narr.get("debate_dialogue", [])
    synth_txt = narr.get("synthesis_text", "")

    # 公司画像（company_profile_{sym}.json — 深度研究数据）
    prof = _load(os.path.join(FIND_DIR, f"company_profile_{data_sym}.json"))

    stance = synth.get("strategic_stance", "hold")
    conf   = synth.get("confidence", 0)
    emoji, banner_bg, banner_color, stance_label = _stance_banner_cfg(stance)
    cur_price = pos_snap.get("cur_price")
    pnl_pct   = pos_snap.get("unrealized_pnl_pct")
    now_str   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── TOP BAR ───────────────────────────────────────────────────────────────
    leveraged_badge = (
        f"<span style='font-size:0.72em;background:#8250df;color:#fff;"
        f"padding:2px 8px;border-radius:12px;margin-left:8px'>2× {ana_sym}</span>"
        if is_leveraged else ""
    )
    top_bar = f"""
<div class="top-bar">
  <h1>{sym_upper}{leveraged_badge}</h1>
  <span class="muted">{(fnd.get('company_intro') or '')[:55]}</span>
  <div style="flex:1"></div>
  <div class="meta">{now_str} &nbsp;|&nbsp;
    <a href="../findings/premarket_summary_{date}_{sym_upper}.json" target="_blank">盘前数据</a> &nbsp;|&nbsp;
    <a href="../strategic_memo_{data_sym}.json" target="_blank">原始 Memo ({data_sym})</a>
  </div>
</div>"""

    # ── STANCE BANNER ────────────────────────────────────────────────────────
    pnl_str = (f'<span class="{"green" if (pnl_pct or 0)>=0 else "red"}">{_pct(pnl_pct)}</span>'
               if pnl_pct is not None else "")
    stance_banner = f"""
<div class="stance-banner" style="background:{banner_bg}">
  <div>
    <div class="stance-label" style="color:{banner_color}">{emoji} {stance_label.upper()}</div>
    <div class="stance-conf muted">{_stars(conf)} 置信度 {conf}/5</div>
  </div>
  <div class="stance-key">{synth.get('key_condition','')}</div>
  <div style="margin-left:auto;text-align:right">
    <div class="bold">{_dollar(cur_price)}</div>
    <div class="small muted">{pnl_str} 浮盈 &nbsp;|&nbsp; {pos_snap.get('days_held',0)} 天</div>
  </div>
</div>"""

    # ── FUNDAMENTALS ─────────────────────────────────────────────────────────
    # 优先 fsnap（memo），fallback 直接读 fund（fundamentals_{sym}.json，字段名可能不同）
    def _fget(snap_key, *fund_keys):
        v = fsnap.get(snap_key)
        if v is not None:
            return v
        for k in fund_keys:
            v = fund.get(k)
            if v is not None:
                return v
        return None

    analyst_t = _fget("analyst_target", "target_price")
    analyst_u = _fget("analyst_upside_pct", "target_upside_pct", "target_deviation")
    # 用底层股票的当前价检测目标价是否过时（macro_strategy 有最新价格）
    _macro_und = _load(os.path.join(BASE, f"macro_strategy_{data_sym}.json"))
    _und_price = (_macro_und.get("market_inputs", {}).get("price")
                  if _macro_und else None) or cur_price
    analyst_stale = bool(analyst_t and _und_price and analyst_t < _und_price)
    pe_fwd_v  = _fget("pe_fwd", "pe_fwd", "pe_forward", "forwardPE")
    peg_v     = _fget("peg", "peg", "peg_ratio", "pegRatio")
    rev_g_v   = _fget("revenue_growth_pct", "rev_growth_pct", "revenue_growth_pct")
    gm_v      = _fget("gross_margin", "gross_margin")
    om_v      = _fget("operating_margin", "operating_margin")
    roe_v     = _fget("roe", "roe")
    sector_pe_v = fund.get("sector_pe")
    sector_etf  = fund.get("sector_etf","")
    rec_v     = _fget("rec_key", "rec_key", "recommendationKey")
    n_ana_v   = _fget("n_analysts", "n_analysts", "numberOfAnalystOpinions")

    pe_compare = ""
    if pe_fwd_v and sector_pe_v and pe_fwd_v > 0:
        prem = round((pe_fwd_v / sector_pe_v - 1) * 100)
        pe_compare = f"  vs 板块({sector_etf}) {sector_pe_v:.0f}x → {prem:+d}%"

    # 智能单位：< 0.1B 时用 $M，避免 "$-0.0B"
    def _dollar_smart(val_b, na="—"):
        if val_b is None:
            return na
        if abs(val_b) < 0.1:
            return f"${val_b * 1000:.1f}M"
        return f"${val_b:.1f}B"

    # PE (TTM)：亏损股显示"亏损"而非"—"
    pe_ttm_v = _fget('pe_ttm', 'pe_ttm')
    eps_fwd_v = _fget('eps_fwd', 'eps_fwd', 'forwardEps') or fund.get('eps_fwd')
    is_loss_making = (pe_ttm_v is None and eps_fwd_v is not None and eps_fwd_v < 0) or \
                     (pe_fwd_v is not None and pe_fwd_v < 0)
    pe_ttm_str = f"{pe_ttm_v:.1f}x" if pe_ttm_v and pe_ttm_v > 0 else \
                 (f"<span style='color:var(--red)'>亏损</span>" if is_loss_making else "—")

    # PE (Fwd)：负数时标红 + 注释
    if pe_fwd_v and pe_fwd_v > 0:
        pe_fwd_str = f"{pe_fwd_v:.1f}x{pe_compare}"
    elif pe_fwd_v and pe_fwd_v < 0:
        pe_fwd_cmp = f"  vs 板块({sector_etf}) {sector_pe_v:.0f}x" if sector_pe_v else ""
        pe_fwd_str = f"<span style='color:var(--red)'>{pe_fwd_v:.1f}x (亏损){pe_fwd_cmp}</span>"
    else:
        pe_fwd_str = "—"

    # PEG：亏损股显示"亏损N/A"
    peg_str = f"{peg_v:.2f}" if peg_v else \
              ("<span style='color:var(--muted)'>亏损N/A</span>" if is_loss_making else "—")

    # 毛利率/运营利润率：0.0也是有效值
    gm_om_str = f"{gm_v:.1f}% / {om_v:.1f}%" if gm_v is not None and om_v is not None else "—"

    fcf_b_v = _fget('fcf_B', 'fcf_B')
    rev_b_v = fund.get('rev_ttm_B')

    fund_html = _kv_table([
        ("PE (TTM)",    pe_ttm_str),
        ("PE (Fwd)",    pe_fwd_str),
        ("PEG",         peg_str),
        ("营收增速",     _pct(rev_g_v)),
        ("营收(TTM)",   _dollar_smart(rev_b_v)),
        ("毛利率/运营利润率", gm_om_str),
        ("ROE",         f"{roe_v:.1f}%" if roe_v else "—"),
        ("FCF",         _dollar_smart(fcf_b_v)),
        ("现金",        _dollar_smart(fund.get('cash_B'))),
        ("分析师评级",  f"{str(rec_v).upper()} ({n_ana_v}人)" if rec_v and n_ana_v else (rec_v or "—")),
        ("目标价", (
            f"<span style='color:var(--red)'>{_dollar(analyst_t)} ⚠️ 低于现价，目标价已过时</span>"
            if analyst_stale else
            f"{_dollar(analyst_t)} ({_pct(analyst_u)} 空间)" if analyst_t else "—"
        )),
    ])

    # ── POSITION SNAPSHOT ────────────────────────────────────────────────────
    pos_html = _kv_table([
        ("成本价",   _dollar(pos_snap.get("cost")),
         "var(--green)" if (pnl_pct or 0)>0 else "var(--red)" if (pnl_pct or 0)<0 else ""),
        ("持仓量",   f"{pos_snap.get('shares','—')} 股"),
        ("当前价",   _dollar(cur_price)),
        ("浮盈",     _pct(pnl_pct),
         "var(--green)" if (pnl_pct or 0)>=0 else "var(--red)"),
        ("持仓天数",  f"{pos_snap.get('days_held',0)} 天"),
        ("GTC 状态", "✅ 已挂" if pos_snap.get("gtc_placed") else "❌ 未挂",
         "" if pos_snap.get("gtc_placed") else "var(--red)"),
    ])

    # 持仓策略 section 已由"宏观策略节点"取代，不再单独渲染

    # ── FALSIFICATION ────────────────────────────────────────────────────────
    # 证伪条件：优先 memo.support_and_risk.derived_falsification（推导），
    # 其次 position_context.falsification_conditions（用户手填）
    falsif_raw = (sr.get("derived_falsification")
                  or pos_ctx.get("falsification_conditions", []))
    falsif_items = "".join(
        f'<div class="falsif-item"><span>🔒</span><span>{fc}</span></div>'
        for fc in falsif_raw
    ) or '<p class="note">暂无证伪条件（运行 company_profile_fetcher.py 或在 positions.json 手填）</p>'

    # ── MASTER VOTES ─────────────────────────────────────────────────────────
    MASTER_INFO = {
        "minervini":     ("Minervini",    "技术/量价/VCP"),
        "druckenmiller": ("Druckenmiller","宏观/流动性/仓位"),
        "marks":         ("Howard Marks", "风险/市场周期"),
        "lynch":         ("Peter Lynch",  "基本面/论点完整"),
        "soros":         ("George Soros", "反身性/情绪转折"),
        "livermore":     ("Livermore",    "价格行为/时间窗口"),
        "taleb":         ("Nassim Taleb", "尾部风险/不对称"),
    }
    master_cards = ""
    for key, mdata in mvotes.items():
        if key == "_summary" or not isinstance(mdata, dict):
            continue
        name, domain = MASTER_INFO.get(key, (key.title(), ""))
        sig = {"strong_yes":"bullish","yes":"bullish","neutral":"neutral","no":"bearish"}.get(
            mdata.get("supports_holding","neutral"), "neutral")
        badge = _signal_badge(sig)
        # Use narrative if available (richer), fallback to memo
        mn    = ma_narr.get(key, {})
        arg   = mn.get("argument") or mdata.get("core_argument","")
        inv   = mn.get("invalidation") or ""
        direct= mn.get("direction") or mdata.get("position_direction","hold")
        master_cards += f"""
<div class="master-card master-card-{sig}">
  <div class="master-name">{name} {badge}</div>
  <div class="master-domain muted small">{domain} → <b>{direct}</b></div>
  <div class="master-arg">{arg[:100]}</div>
  {"<div class='master-inv'>证伪："+inv+"</div>" if inv else ""}
</div>"""

    masters_summary = (f"看多 {mvsum.get('bullish_count',0)} &nbsp; "
                       f"中性 {mvsum.get('neutral_count',0)} &nbsp; "
                       f"看空 {mvsum.get('bearish_count',0)}")

    # ── SIX-DIMENSION ANALYSIS (TABS) ─────────────────────────────────────────
    AGENT_LABELS = {
        "tech":"📈 技术", "fund":"💰 基本面", "macro":"🌍 宏观",
        "risk":"⚠️ 风险", "sentiment":"💬 情绪", "sector":"🏭 板块",
    }
    tab_btns = tab_panes = ""
    for idx, (key, label) in enumerate(AGENT_LABELS.items()):
        active = "active" if idx == 0 else ""
        tab_btns += (f'<button class="tab-btn {active}" data-group="agents" '
                     f'onclick="showTab(\'agents\',\'{key}\',this)">{label}</button>')
        # Data: prefer narrative (richer), fallback to agent_analysis from memo
        ag_n = ag_narr.get(key, {})
        ag_m = ag_an.get(key, {})
        sig  = ag_n.get("signal") or ag_m.get("signal","neutral")
        conf_ag = ag_n.get("confidence") or ag_m.get("confidence",0)
        badge = _signal_badge(sig, conf_ag)
        # Key points
        kps = ag_n.get("key_points") or ag_m.get("key_points",[])
        kp_html = "".join(f'<div class="kp-item">✅ {kp}</div>' for kp in kps[:4])
        # Analysis paragraphs
        paras = ag_n.get("narrative","") or " ".join(ag_m.get("analysis",[])[:2])
        para_html = f'<div class="para-item">{paras}</div>' if paras else ""
        # Conclusion
        concl = ag_n.get("conclusion_text") or (ag_m.get("conclusion",{}) or {}).get("judgment","")
        bound = ag_n.get("boundary_text") or (ag_m.get("conclusion",{}) or {}).get("boundary","")
        concl_html = (f'<div class="concl-box"><b>结论：</b>{concl}<br>'
                      f'{"<b>边界：</b>"+bound if bound else ""}</div>') if concl else ""
        no_data = '<p class="note">暂无分析数据（需运行 CIO 全量分析后重新生成）</p>'
        tab_panes += f"""
<div id="agents-{key}" class="tab-pane {active}" data-group="agents">
  <div style="margin-bottom:8px">{badge}</div>
  {kp_html or para_html or no_data}
  {para_html if kp_html else ""}
  {concl_html}
</div>"""

    agents_block = _card("六维度分析",
        f'<div class="tab-bar">{tab_btns}</div>{tab_panes}', "🔬")

    # ── DEBATE ───────────────────────────────────────────────────────────────
    # Use dialogue from narrative if available, else debate_highlights
    dialogue_html = ""
    if debate_d:
        for msg in debate_d[:6]:
            type_label = "💬 质疑" if msg.get("type") == "challenge" else "↩️ 回应"
            dialogue_html += f"""
<div class="debate-msg">
  <span class="muted small">{msg.get('from','?')} {type_label}</span><br>
  {msg.get('content','')}
</div>"""
    elif debate.get("key_challenges"):
        for c in debate.get("key_challenges",[]):
            dialogue_html += f'<div class="debate-msg">💬 {c}</div>'
    else:
        dialogue_html = '<p class="note">无辩论数据（需运行 CIO phases 01 或 0123）</p>'

    st = synth_txt or debate.get("dominant_view","")
    synth_box = (f'<div class="synth-box"><b>综合结论：</b>{st}</div>') if st else ""
    debate_block = _card(
        f"大师辩论 — {debate.get('rounds',0)} 轮 {'(共识达成)' if debate.get('consensus_reached') else ''}",
        dialogue_html + synth_box, "⚡")

    # ── SCENARIOS ────────────────────────────────────────────────────────────
    scen_cfg = {
        "bull":("#e6f4ea","#1a7f37","🐂 牛市情景"),
        "base":("#ddf4ff","#0550ae","📊 基准情景"),
        "bear":("#ffeef0","#cf222e","🐻 熊市情景"),
    }
    scen_html = '<div class="scenario-grid">'
    for key in ["bull","base","bear"]:
        sc = scens.get(key, {})
        bg, color, lbl = scen_cfg[key]
        scen_html += f"""
<div class="scenario-card" style="background:{bg}">
  <div class="scenario-lbl" style="color:{color}">{lbl}</div>
  <div class="scenario-price" style="color:{color}">{_dollar(sc.get('price_target'))}</div>
  <div class="scenario-cond">{sc.get('condition','—')}</div>
  <div class="small muted" style="margin-top:6px">概率：{sc.get('probability','—')}</div>
</div>"""
    scen_html += '</div>'

    # 杠杆 ETF 换算：显示底层情景价格对应的 ETF 目标价
    if is_leveraged:
        try:
            lev_pairs = _load(os.path.join(BASE, "config", "leveraged_pairs.json"))
            lev_info  = lev_pairs.get(ana_sym.upper(), {})
            leverage  = float(lev_info.get("leverage", 2))
            macro_und = _load(os.path.join(BASE, f"macro_strategy_{ana_sym}.json"))
            macro_etf = _load(os.path.join(BASE, f"macro_strategy_{sym_upper}.json"))
            und_cur   = (macro_und.get("market_inputs", {}).get("price")) if macro_und else None
            etf_cur   = (macro_etf.get("market_inputs", {}).get("price")) if macro_etf else None
            if und_cur and etf_cur:
                rows_lev = []
                for key, (_, color, lbl) in [
                    ("bull", ("#f0fff4", "#1a7f37", "🐂")),
                    ("base", ("#f6f8fa", "#1f2328", "📊")),
                    ("bear", ("#ffeef0", "#cf222e", "🐻")),
                ]:
                    sc = scens.get(key, {})
                    und_target = sc.get("price_target")
                    if und_target and und_cur:
                        ret_und = (und_target - und_cur) / und_cur
                        etf_target = round(etf_cur * (1 + leverage * ret_und), 2)
                        rows_lev.append(
                            f"<span style='color:{color}'>{lbl} {ana_sym} ${und_target:.2f}"
                            f"（{ret_und:+.1%}）→ {sym_upper} ≈ <b>${etf_target:.2f}</b></span>"
                        )
                scen_html += (
                    f"<div style='margin-top:12px;padding:10px;background:#f6f8fa;"
                    f"border-radius:6px;font-size:0.84em'>"
                    f"<div style='font-weight:600;margin-bottom:6px'>"
                    f"📐 {sym_upper} 对应目标价（{leverage:.0f}× 杠杆，{ana_sym} 当前 ${und_cur:.2f}，{sym_upper} 当前 ${etf_cur:.2f}）</div>"
                    + "<br>".join(rows_lev)
                    + "</div>"
                )
        except Exception:
            pass

    scen_block = _card("情景分析", scen_html, "🎯")

    # ── OUTLET ────────────────────────────────────────────────────────────────
    el = outlook.get("exit_logic", {})
    exit_block = _card("出场逻辑", _kv_table([
        ("目标达成出场", el.get("target_reached","—")),
        ("主动出场信号", el.get("proactive_exit_signal","—")),
        ("有效期至",     outlook.get("valid_until","—")),
    ]), "🚪")

    # ── THESIS + RISK ─────────────────────────────────────────────────────────
    facts = sr.get("core_supporting_facts", [])
    risks = sr.get("main_risks", [])
    facts_html = "".join(f'<div class="kp-item">✅ {f}</div>' for f in facts) or '<p class="note">暂无数据</p>'
    risks_html = "".join(f'<div class="kp-item" style="color:var(--yellow)">⚠️ {r}</div>' for r in risks) or '<p class="note">暂无数据</p>'

    # ── PROFILE SECTIONS (avoiding nested f-string issues) ────────────────────
    prof_section = ""
    if prof:
        moat_items = "".join(f'<div class="kp-item">🛡️ {m}</div>' for m in prof.get("competitive_moat", [])) or '<p class="note">运行 company_profile_fetcher.py 生成护城河分析</p>'
        drivers_items = "".join(f'<div class="kp-item">🚀 {d}</div>' for d in prof.get("growth_drivers", [])) or '<p class="note">暂无数据</p>'
        
        peers_pe = prof.get("peers_pe")
        competitors_rows = ""
        if prof.get("competitors"):
            for c in prof.get("competitors", []):
                pe_str = f'  <span class="muted">PE: {peers_pe.get(c["sym"], "—")}x</span>' if c.get("sym") and peers_pe else ""
                competitors_rows += f'<tr><td class="kv-label">{c["name"]}</td><td class="small">{c["angle"]}{pe_str}</td></tr>'
        competitors_table = f'<table class="kv-table">{competitors_rows}</table>' if competitors_rows else '<p class="note">暂无竞争对手数据</p>'
        
        risks_items = "".join(f'<div class="kp-item" style="color:var(--red)">⚠️ {r}</div>' for r in prof.get("key_risks", [])) or '<p class="note">暂无风险数据</p>'
        
        prof_section = f"""<div class="grid-2">
  {_card("竞争护城河", moat_items, "🛡️")}
  {_card("增长驱动", drivers_items, "🚀")}
</div>
<div class="grid-2">
  {_card("竞争格局", competitors_table, "⚔️")}
  {_card("主要风险", risks_items, "⚠️")}
</div>"""

    cases_section = ""
    if prof and (prof.get("bull_case") or prof.get("bear_case")):
        bull_items = "".join(f'<div class="kp-item">🟢 {b}</div>' for b in prof.get("bull_case", [])) or '<p class="note">暂无数据</p>'
        bear_items = "".join(f'<div class="kp-item" style="color:var(--red)">🔴 {b}</div>' for b in prof.get("bear_case", [])) or '<p class="note">暂无数据</p>'
        cases_section = f"""<div class="grid-2">
  {_card("多头核心论点 (Bull Case)", bull_items, "📈")}
  {_card("空头核心论点 (Bear Case)", bear_items, "📉")}
</div>"""

    # ── ASSEMBLE ─────────────────────────────────────────────────────────────
    h2 = lambda t, i="": f'<h2 class="section-h2">{i} {t}</h2>'
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>{sym_upper} 研究报告 {date}</title>
{CSS}</head>
<body>
{top_bar}
{stance_banner}
<div class="main">

{h2("公司概况与持仓","🏢")}
<div class="grid-2">
  {_card("公司概况",
    f'<div class="small" style="margin-bottom:10px">'
    f'<span class="bold">{fund.get("long_name","") or sym_upper}</span>'
    f'&nbsp;&nbsp;<span class="muted">{fund.get("sector","")}/{fund.get("industry","")}</span>'
    f'{"&nbsp;|&nbsp;" + fund.get("country","") if fund.get("country") else ""}'
    f'{"&nbsp;|&nbsp;" + format(fund.get("employees",0),",.0f") + " 人" if fund.get("employees") else ""}'
    f'</div>'
    + (f'<div style="margin-bottom:10px">'
       + "".join(f'<div style="padding:3px 0;font-size:0.86em;border-bottom:1px solid #f0f0f0">📊 <b>{seg["segment"]}</b> ${seg["revenue_B"]:.1f}B ({seg["pct"]}%) &nbsp;<span class="green">+{seg["growth_yoy"]}%</span>&nbsp;<span class="muted small">{seg.get("note","")}</span></div>'
                 for seg in prof.get("revenue_breakdown",[]))
       + f'</div>' if prof.get("revenue_breakdown") else "")
    + f'<div style="padding:8px;background:#f6f8fa;border-radius:6px;font-size:0.86em">'
    f'<b>持仓论点：</b>{pos_ctx.get("thesis_full","—")}</div>',
    "🏢")}
  {_card("基本面", fund_html, "💰")}
</div>

<!-- 护城河 + 增长驱动 + 竞争格局 -->
{prof_section}

<!-- 多/空头论点（有搜索数据时显示） -->
{cases_section}

<!-- 持仓论点 + 证伪条件 + 快照 -->
<div class="grid-2">
  {_card("证伪条件", falsif_items, "🔒")}
  {_card("持仓快照", pos_html, "📊")}
</div>

{h2(f"大师投票 — {masters_summary}","🎓")}
{_card("7 位大师立场", f'<div class="master-grid">{master_cards}</div>')}

{h2("六维度分析","🔬")}
{agents_block}

{h2("支撑论据","📌")}
{_card("核心支撑论据",
  "".join(f'<div class="kp-item">✅ {f}</div>' for f in sr.get("core_supporting_facts",[]))
  or '<p class="note">暂无数据</p>', "✅")}

{h2("情景分析","🎯")}
{scen_block}

{h2("辩论 · 综合结论","⚡")}
{debate_block}

{render_trading_nodes(
    _load(os.path.join(BASE, f"macro_strategy_{sym_upper}.json")),
    _load(os.path.join(BASE, f"macro_strategy_{sym_upper}_prev.json")),
)}

{h2("出场逻辑","🚪")}
{exit_block}

</div>
{SCRIPT}
</body></html>"""


def render_nodes_guide() -> str:
    """渲染交易节点使用说明——独立静态 HTML，不依赖任何股票数据。"""
    NODES = [
        {
            "name": "动态止损",
            "icon": "🛑",
            "type": "止损",
            "when": "建仓后全程有效，持仓期间唯一的价格止损线",
            "trigger": "价格收盘跌破此位（跳空低开→市价立即执行，不等收盘确认）",
            "lifecycle": "三阶段升级：① 初始锚定于 MA50/结构低点 − k1×ATR；② 浮盈 ≥8% 时上移至成本价（保本线）；③ 浮盈 ≥15% 时跟随 MA20 每日滚动",
            "invalid": "当日收盘反回 stop + 0.5×ATR 且缩量 → 视为假突破，记录但不自动恢复",
            "relation": "base→bear 情景降级与此位接近（设计意图）；Force Exit 是更远的兜底线",
            "action": "触发时无条件清仓，不做犹豫。收到假突破信号后观察次日量价再决定是否重建",
        },
        {
            "name": "强制清仓",
            "icon": "🚨",
            "type": "止损",
            "when": "论点完全破裂时的最终防线，正常情况下不应触及",
            "trigger": "① 熊市情景价（分析师最悲观目标）；② 催化剂暴雷价（entry − fe_catalyst×ATR）。任一满足即执行",
            "lifecycle": "持仓全程有效。分析师目标下调时自动更新熊市情景价",
            "invalid": "无失效条件，始终作为兜底线存在",
            "relation": "动态止损先触发；Force Exit 是动态止损被穿越（跳空）后的最终防线",
            "action": "触发时全仓市价清出，无需等待盘中确认。与动态止损的区别：动态止损是日内正常止损，Force Exit 是灾难性下跌时的最后一道门",
        },
        {
            "name": "情景降级 bull→base",
            "icon": "🟡",
            "type": "论点监控",
            "when": "论点还未破裂但开始弱化，作为预警信号",
            "trigger": "价格跌破 MA20 − k5×ATR（短期均线支撑失守）",
            "lifecycle": "持仓全程监控。不是出场信号，是论点状态更新信号",
            "invalid": "价格重新站上此位即解除预警",
            "relation": "触发后论点状态从 intact → weakening；若继续下跌触及 base→bear 则进一步降级；Add1/Add2 在论点 weakening 时自动冻结",
            "action": "收到预警后：① 核查证伪条件是否被触碰；② 暂停加仓计划；③ 关注是否进一步恶化。不需要立刻减仓",
        },
        {
            "name": "情景降级 base→bear",
            "icon": "🔴",
            "type": "论点监控",
            "when": "论点正式破裂，动态止损评估应随之执行",
            "trigger": "价格跌破 MA50 − k6×ATR（与动态止损价位接近，联动关系）",
            "lifecycle": "触发后论点状态从 weakening → broken，通常此时动态止损同步触发",
            "invalid": "不可逆。论点破裂后需完整重新评估才能恢复",
            "relation": "价位与动态止损几乎重合（设计意图）。优先级：动态止损执行出场，情景降级更新标签",
            "action": "若已触发动态止损则同步处理；若价格刚好在两者之间需人工判断是否提前清仓",
        },
        {
            "name": "Add1 加仓",
            "icon": "➕",
            "type": "加仓",
            "when": "论点完好 + 价格正常回调至技术支撑，分批建仓的第二批",
            "trigger": "价格回落到 max(Fib38.2%, MA50 + k2×ATR) 区间，同时：论点 intact + 成交量萎缩（vol_ratio < 0.8）+ 不在催化剂窗口内",
            "lifecycle": "三个条件必须同时满足才有效。催化剂前3天/后1天内自动冻结",
            "invalid": "① 放量跌破 MA50；② 论点转 weakening；③ 催化剂窗口开启。任一发生即取消",
            "relation": "触发后加仓量由持仓计划决定，不影响 TP1/TP2 的目标价。Add2 需要更高置信度才能激活",
            "action": "缩量回踩到位且论点无异常时可执行。放量回调不加，可能是趋势反转信号",
        },
        {
            "name": "Add2 加仓",
            "icon": "➕➕",
            "type": "加仓",
            "when": "高置信度持仓（unified_confidence ≥ 4）时允许的第三批加仓",
            "trigger": "价格进一步回落到 Fib61.8%/MA200 区域，条件比 Add1 更严格",
            "lifecycle": "仅在 unified_confidence ≥ 4 时激活，否则显示 —。论点转 weakening 后立即取消",
            "invalid": "unified_confidence < 4；论点转 weakening；催化剂窗口内",
            "relation": "Add1 之后的加仓机会，通常对应更深的回调。适合基本面极强、长期高置信度的核心持仓",
            "action": "Add2 对应的回调幅度通常较大（-15% 以上），需要对论点极度确信才操作",
        },
        {
            "name": "TP1 目标(30%)",
            "icon": "🎯",
            "type": "减仓",
            "when": "首次达到近期阻力位，分批出场的第一步",
            "trigger": "价格触及近90日高点区域（× 0.995 留缓冲）。开盘跳空高于 TP1 → 按开盘价执行",
            "lifecycle": "一次性触发。TP1 执行后减仓 30%，剩余仓位以 TP2 为目标",
            "invalid": "分析师目标大幅下调（超10%）时重新计算 TP1",
            "relation": "TP1 触发后 TP2 成为唯一目标。Flex Reduce 可在 TP1 前触发小额减仓，但不能替代 TP1",
            "action": "价格到达后不等犹豫，按计划减仓30%。高位的不确定性比等待更多涨幅的确定性更大",
        },
        {
            "name": "TP2 目标(全清)",
            "icon": "🏁",
            "type": "减仓",
            "when": "论点实现，价格达到分析师目标折扣价，全仓出场",
            "trigger": "价格触及 min(分析师目标 × 0.90, 历史前高)",
            "lifecycle": "TP1 触发后持续有效。分析师目标下调超10%时自动重算",
            "invalid": "分析师目标大幅下调 → 重算后 TP2 降低；论点破裂后出场逻辑转为止损，TP2 失效",
            "relation": "TP2 触发即结束持仓。若论点还非常强且分析师上调目标，可选择持续持有（但需人工决策）",
            "action": "全仓清出后记录完整交易到 trading_lessons.json，更新论点准确率统计",
        },
        {
            "name": "Flex 减仓",
            "icon": "⚡",
            "type": "减仓",
            "when": "盘中出现技术性超买信号，动态小额减仓锁定短期收益",
            "trigger": "VWAP 偏离 + RSI > 70 警戒，由 poll.py 每2分钟检测",
            "lifecycle": "盘中动态，每日盘前 --refresh 更新价位。单次减量上限15%（不超过当批计划量的50%）",
            "invalid": "论点 weakening 后禁用；Flex 不能替代 TP1/TP2 的系统性减仓",
            "relation": "Flex 是战术性减仓，TP1/TP2 是战略性减仓。Flex 触发后剩余仓位仍等待 TP1",
            "action": "Flex 减仓后价格回落 → 可考虑 Flex 加仓对应。不要因为 Flex 多次触发而过早清仓",
        },
        {
            "name": "催化剂节点",
            "icon": "📅",
            "type": "事件",
            "when": "重大催化剂（财报/政策）前后3天窗口期内",
            "trigger": "① 前缩仓：催化剂 importance=high + days_away ≤ 3 → 建议缩至安全仓位；② 后加仓：结果超预期 + 价格站上 post_add_trigger；③ 后清仓：结果暴雷 + 价格跌破 post_force_exit",
            "lifecycle": "仅在催化剂窗口期内（前3天/后1天）有效。窗口外自动关闭",
            "invalid": "催化剂已过去或结果已知后窗口关闭",
            "relation": "窗口内自动冻结 Add1/Add2 的价格触发；后加仓触发后相当于一次 Add1 执行",
            "action": "前缩仓不是强制，是建议——高影响催化剂的尾部风险用仓位控制，而非止损控制",
        },
        {
            "name": "时间止损",
            "icon": "⏰",
            "type": "时间",
            "when": "持仓超过预设天数但价格未向目标方向移动，论点需要重评估",
            "trigger": "普通：持仓 > N天（默认30天）且价格未向 TP1 移动5%以上 → 强制重评估；杠杆ETF衰减：持有 > D天（默认14天）且底层标的涨幅 < M% → 清仓（避免复利损耗侵蚀本金）",
            "lifecycle": "基于日历时间，不依赖价格。杠杆ETF的衰减止损比普通时间止损更严格",
            "invalid": "价格在期限内达到 TP1 的5%范围内 → 时间止损自动解除",
            "relation": "独立于价格节点。即使价格没有触及任何止损位，时间到期也需要主动重评估",
            "action": "时间止损触发 ≠ 必须出场。是强制问自己：论点还成立吗？如果答案是YES且有新催化剂 → 可以重置时间；如果论点没有新进展 → 考虑清仓",
        },
        {
            "name": "追涨上限",
            "icon": "🚫",
            "type": "入场",
            "when": "尚未建仓时防止追高入场",
            "trigger": "计划入场价 + 0.5×ATR 以上 → 当日不入场",
            "lifecycle": "仅对未建仓标的有效。一旦建仓后此节点自动失效",
            "invalid": "已建仓后永久失效",
            "relation": "与 Entry 配合使用。stock-premarket 的 entry_decision 会参考此位",
            "action": "开盘跳空超过追涨上限 → 放弃当日入场，等回调或等下一个催化剂机会",
        },
        {
            "name": "重建仓位",
            "icon": "🔄",
            "type": "入场",
            "when": "被动态止损触发出场后，若论点仍然完整，可在此价位重建",
            "trigger": "MA50 + k_reentry×ATR 区间，条件：thesis_status = intact + 距止损出场 ≥ 3天",
            "lifecycle": "仅在止损出场后激活。论点 weakening 时不允许重建",
            "invalid": "距止损出场不足3天；论点已转 weakening/broken",
            "relation": "是 Add1 的特殊版本（入场条件相似但出发点不同）。重建前建议重新跑 stock-deep-research 确认论点",
            "action": "不要因为\"被止损了\"就急于重建。3天冷静期是必须的。重建前问：论点有什么新的支撑？",
        },
    ]

    type_colors = {
        "止损": ("rgba(244,63,94,0.06)", "#f43f5e"),
        "加仓": ("rgba(16,185,129,0.06)", "#10b981"),
        "减仓": ("rgba(245,158,11,0.06)", "#f59e0b"),
        "论点监控": ("rgba(99,102,241,0.06)", "#6366f1"),
        "时间": ("rgba(139,92,246,0.06)", "#8b5cf6"),
        "事件": ("rgba(236,72,153,0.06)", "#ec4899"),
        "入场": ("rgba(59,130,246,0.06)", "#3b82f6"),
    }

    cards = []
    for n in NODES:
        bg, ac = type_colors.get(n["type"], ("rgba(255,255,255,0.02)", "rgba(255,255,255,0.15)"))
        cards.append(f"""
<div style="background:{bg};backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border:1px solid {ac}30;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 8px 32px 0 rgba(0,0,0,0.37);transition:all 0.3s ease">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
    <span style="font-size:1.6em">{n['icon']}</span>
    <span style="font-weight:700;font-size:1.15em;font-family:'Outfit',sans-serif;color:#ffffff">{n['name']}</span>
    <span style="font-size:0.75em;font-weight:700;background:{ac}20;color:{ac};border:1px solid {ac}40;padding:2px 10px;border-radius:6px;text-transform:uppercase;font-family:'Plus Jakarta Sans',sans-serif">{n['type']}</span>
  </div>
  <table style="width:100%;border-collapse:collapse;font-size:0.88em;color:#e2e8f0;font-family:'Plus Jakarta Sans',sans-serif">
    <tr style="border-bottom:1px solid rgba(255,255,255,0.06)">
      <td style="color:#94a3b8;padding:8px 8px 8px 0;width:100px;vertical-align:top;font-weight:600">📌 适用场景</td>
      <td style="padding:8px 4px;line-height:1.6">{n['when']}</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.06)">
      <td style="color:#94a3b8;padding:8px 8px 8px 0;vertical-align:top;font-weight:600">⚡ 触发条件</td>
      <td style="padding:8px 4px;line-height:1.6;font-family:'JetBrains Mono',monospace;color:#f1f5f9">{n['trigger']}</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.06)">
      <td style="color:#94a3b8;padding:8px 8px 8px 0;vertical-align:top;font-weight:600">🔄 生命周期</td>
      <td style="padding:8px 4px;line-height:1.6">{n['lifecycle']}</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.06)">
      <td style="color:#94a3b8;padding:8px 8px 8px 0;vertical-align:top;font-weight:600">❌ 失效条件</td>
      <td style="padding:8px 4px;line-height:1.6">{n['invalid']}</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.06)">
      <td style="color:#94a3b8;padding:8px 8px 8px 0;vertical-align:top;font-weight:600">🔗 节点关系</td>
      <td style="padding:8px 4px;line-height:1.6">{n['relation']}</td>
    </tr>
    <tr>
      <td style="color:#6366f1;padding:8px 8px 8px 0;vertical-align:top;font-weight:600">✅ 操作建议</td>
      <td style="padding:8px 4px;font-weight:600;color:#818cf8;line-height:1.6">{n['action']}</td>
    </tr>
  </table>
</div>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>交易节点使用说明</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{{
  --bg:#030712;
  --bg-gradient:radial-gradient(circle at top, #0f172a 0%, #030712 100%);
  --card:rgba(17, 24, 39, 0.45);
  --border:rgba(255, 255, 255, 0.05);
  --border-hover:rgba(99, 102, 241, 0.3);
  --text:#f9fafb;
  --muted:#94a3b8;
  --accent:#6366f1;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  font-family:'Plus Jakarta Sans',sans-serif;
  background:var(--bg);
  background-image:var(--bg-gradient);
  color:var(--text);
  font-size:15px;
  line-height:1.65;
  padding:40px;
  min-height:100vh;
}}
.top-bar{{
  background:var(--card);
  backdrop-filter:blur(16px);
  -webkit-backdrop-filter:blur(16px);
  border:1px solid var(--border);
  border-radius:14px;
  padding:24px 28px;
  margin-bottom:28px;
  box-shadow:0 10px 30px 0 rgba(0,0,0,0.25);
}}
h1{{
  font-family:'Outfit',sans-serif;
  font-size:1.8em;
  font-weight:800;
  margin-bottom:8px;
  color:#ffffff;
}}
.subtitle{{
  color:var(--muted);
  font-size:0.92em;
}}
.toc{{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin-top:20px;
}}
.toc a{{
  font-size:0.82em;
  font-weight:600;
  padding:6px 12px;
  border-radius:8px;
  text-decoration:none;
  border:1px solid var(--border);
  color:var(--text);
  background:rgba(255, 255, 255, 0.02);
  transition:all 0.3s ease;
}}
.toc a:hover{{
  border-color:var(--border-hover);
  background:rgba(99, 102, 241, 0.15);
  transform:translateY(-2px);
  box-shadow:0 4px 12px rgba(99,102,241,0.2);
}}
.section-h{{
  font-family:'Outfit',sans-serif;
  font-size:1.15em;
  font-weight:700;
  color:#ffffff;
  text-transform:uppercase;
  letter-spacing:.08em;
  margin:40px 0 16px;
  padding-bottom:8px;
  border-bottom:1px solid rgba(255,255,255,0.08);
}}
.lifecycle-note{{
  background:var(--card);
  backdrop-filter:blur(16px);
  -webkit-backdrop-filter:blur(16px);
  border:1px solid var(--border);
  border-radius:14px;
  padding:20px;
  margin-bottom:28px;
  font-size:0.9em;
  color:var(--muted);
  line-height:1.7;
  box-shadow:0 10px 30px 0 rgba(0,0,0,0.25);
}}
.lifecycle-note strong {{
  color: #ffffff;
}}
</style></head>
<body>
<div class="top-bar">
  <h1>📐 交易节点使用说明</h1>
  <p class="subtitle">宏观策略（Macro Strategy）生成的13个价格节点，每个节点的适用场景、触发条件、生命周期和操作建议</p>
  <div class="toc">
    {''.join(f"<a href='#{n['name']}'>{n['icon']} {n['name']}</a>" for n in NODES)}
  </div>
</div>

<div class="lifecycle-note">
  <strong>节点生命周期总览</strong>：动态止损 / 强制清仓 持仓全程有效 →
  情景降级 持续监控论点状态 →
  Add1/Add2 等待回调触发（可被冻结）→
  TP1 触发后 TP2 接力 →
  时间止损 独立计时 →
  追涨上限 / 重建仓位 仅在特定阶段激活
</div>

<div class="section-h">🛑 止损类</div>
{''.join(f'<div id="{n["name"]}">{c}</div>' for n, c in zip(NODES, cards) if n['type'] == '止损')}

<div class="section-h">📡 论点监控类</div>
{''.join(f'<div id="{n["name"]}">{c}</div>' for n, c in zip(NODES, cards) if n['type'] == '论点监控')}

<div class="section-h">🎯 减仓类</div>
{''.join(f'<div id="{n["name"]}">{c}</div>' for n, c in zip(NODES, cards) if n['type'] == '减仓')}

<div class="section-h">➕ 加仓类</div>
{''.join(f'<div id="{n["name"]}">{c}</div>' for n, c in zip(NODES, cards) if n['type'] == '加仓')}

<div class="section-h">📅 事件 / 时间类</div>
{''.join(f'<div id="{n["name"]}">{c}</div>' for n, c in zip(NODES, cards) if n['type'] in ('事件', '时间'))}

<div class="section-h">🚪 入场类</div>
{''.join(f'<div id="{n["name"]}">{c}</div>' for n, c in zip(NODES, cards) if n['type'] == '入场')}

<p style="color:var(--muted);font-size:0.8em;margin-top:32px;text-align:center">
  由 macro_strategy.py 自动计算 · 系数通过历史回测自动优化 · 本文档随 report_viewer.py 自动更新
</p>
</body></html>"""


def write_nodes_guide(base_dir: str = BASE) -> str:
    """写出独立的节点使用说明 HTML，供直接浏览器打开。"""
    os.makedirs(os.path.join(base_dir, "reports"), exist_ok=True)
    path = os.path.join(base_dir, "reports", "trading_nodes_guide.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_nodes_guide())
    return path


def write_research_report(sym: str, date: str, base_dir: str = BASE) -> str:
    html = render_research_report(sym, date)
    os.makedirs(os.path.join(base_dir, "reports"), exist_ok=True)
    path = os.path.join(base_dir, "reports", f"research_{sym.upper()}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main(syms=None):
    date_str = _date.today().strftime("%Y-%m-%d")
    if not syms:
        import glob
        files = glob.glob(os.path.join(BASE, "strategic_memo_*.json"))
        syms = [os.path.basename(f).replace("strategic_memo_","").replace(".json","")
                for f in files]
    if not syms:
        print("无 strategic_memo 文件，请先运行全量分析")
        return
    guide_path = write_nodes_guide()
    print(f"\n生成研究报告（{len(syms)} 只）\n")
    for sym in syms:
        path = write_research_report(sym, date_str)
        print(f"  {sym}: [OK] {os.path.basename(path)}")
    print(f"  [GUIDE] 使用说明: {os.path.basename(guide_path)}")


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
