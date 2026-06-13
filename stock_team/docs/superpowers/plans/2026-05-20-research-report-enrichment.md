# Research Report Enrichment 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让研究报告（strategic_memo JSON + HTML）从当前稀薄状态升级为完备的投研报告，包含全量 Agent 分析、持仓策略、大师辩论、情景分析，并以 Notion 研报风重新设计 HTML。

**Architecture:** 三步串行：(1) 修复 cio.py 数据丢失问题 → 保存 per-sym agent 文件；(2) strategic_memo_writer.py 重构，读取丰富数据源；(3) report_viewer.py 完全重写为 Notion 浅色研报风。

**Tech Stack:** Python 3.12, json, yfinance, Jinja2-style f-string HTML

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/cio.py` | 修改（phase1 末尾 + phase2 末尾）| 保存 per-sym agent 文件和辩论文件 |
| `agents/strategic_memo_writer.py` | 重构 | 读取丰富数据，填充所有字段 |
| `agents/report_viewer.py` | 重写 | Notion 研报风 HTML |
| `tests/test_research_report.py` | 新建 | 核心函数单元测试 |

---

## Task 1：cio.py — per-symbol 数据保存

**Files:**
- Modify: `agents/cio.py`（phase1 末尾约 135 行，phase2 末尾约 260 行）

---

- [ ] **Step 1.1：在 phase1() 末尾添加 per-sym agent 文件保存**

找到 `phase1(symbol)` 函数末尾（约第 133-135 行，在 `print("[Phase 1] 完成")` 前），插入：

```python
    # 保存 per-symbol agent 文件（避免多标的时互相覆盖）
    from datetime import date as _dt
    _date_str = str(_dt.today())
    for _agent in ANALYSIS_AGENTS:
        _src = os.path.join(FINDINGS_DIR, f"{AGENT_NAMES[_agent]}.json")
        if os.path.exists(_src):
            _dst = os.path.join(FINDINGS_DIR, f"{AGENT_NAMES[_agent]}_{symbol}_{_date_str}.json")
            try:
                import shutil
                shutil.copy2(_src, _dst)
            except Exception:
                pass
```

- [ ] **Step 1.2：在 phase2() 末尾添加 per-sym debate 文件保存**

找到 `phase2(symbol)` 函数末尾（约 260 行，`print("[Phase 2] 辩论结束")` 后），插入：

```python
    # 保存 per-symbol debate 文件
    from datetime import date as _dt
    _date_str = str(_dt.today())
    _debate_path = os.path.join(FINDINGS_DIR, f"debate_{symbol}_{_date_str}.jsonl")
    try:
        _board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()]
        with open(_debate_path, "w", encoding="utf-8") as _df:
            for _msg in _board:
                _df.write(json.dumps(_msg, ensure_ascii=False) + "\n")
    except Exception:
        pass
```

- [ ] **Step 1.3：验证**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 agents/cio.py NVDA --phases 01 2>&1 | tail -5
ls findings/TechAgent_NVDA_*.json findings/debate_NVDA_*.jsonl 2>/dev/null
```

预期：找到 `TechAgent_NVDA_2026-05-20.json` 等文件。

- [ ] **Step 1.4：Commit**

```bash
git add agents/cio.py
git commit -m "feat: cio.py saves per-symbol agent files + debate files to prevent overwrite"
```

---

## Task 2：strategic_memo_writer.py — 全面重构

**Files:**
- Modify: `agents/strategic_memo_writer.py`（全面重写数据读取和字段填充）
- Create: `tests/test_research_report.py`

---

- [ ] **Step 2.1：写测试（先建框架）**

```python
# tests/test_research_report.py
import sys, os, json, datetime
sys.path.insert(0, os.path.expanduser("~/stock_team"))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _make_agent_file(tmp_path, agent, sym, date, signal="bullish", analysis=None, key_points=None):
    path = tmp_path / "findings" / f"{agent}_{sym}_{date}.json"
    _write(str(path), {
        "from": agent, "symbol": sym, "signal": signal,
        "confidence": 70,
        "analysis": analysis or ["分析段落1", "分析段落2"],
        "key_points": key_points or ["关键点A", "关键点B"],
        "conclusion": {"judgment": "测试结论", "boundary": "测试边界"},
    })


def _make_debate_file(tmp_path, sym, date):
    path = tmp_path / "findings" / f"debate_{sym}_{date}.jsonl"
    os.makedirs(str(tmp_path / "findings"), exist_ok=True)
    msgs = [
        {"from": "TechAgent", "msg_type": "challenge", "content": "我质疑基本面论断", "symbol": sym},
        {"from": "FundAgent", "msg_type": "response", "content": "基本面数据支持论断", "symbol": sym},
    ]
    with open(str(path), "w") as f:
        for m in msgs:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")


def _make_positions(tmp_path, sym):
    _write(str(tmp_path / "config" / "positions.json"), {
        "positions": {sym: {
            "cost": 184.0, "shares": 30, "date": "2026-05-12",
            "thesis": "NVIDIA GPU数据中心AI算力垄断",
            "thesis_status": "intact",
            "falsification_conditions": ["跌破$200且跑输SOX", "Blackwell出货延迟超3个月"],
            "t2_conditions": {"note": "NVDA>$240回踩买", "underlying_price_floor": 240.0},
            "target_pct": 25.0,
            "position_type": "thesis",
            "gtc_stop_placed": False,
            "t1_stop_snapshot": 215.0,
        }},
        "_excluded": [],
    })


def test_build_position_context(tmp_path):
    """position_context 包含论点/证伪/加减仓策略"""
    from agents.strategic_memo_writer import build_position_context
    _make_positions(tmp_path, "NVDA")
    ctx = build_position_context("NVDA", base_dir=str(tmp_path))
    assert ctx["thesis_full"] == "NVIDIA GPU数据中心AI算力垄断"
    assert len(ctx["falsification_conditions"]) == 2
    assert ctx["reduce_strategy"]["target_pct"] == 25.0
    assert ctx["position_snapshot"]["cost"] == 184.0


def test_load_agent_analysis(tmp_path):
    """从 per-sym agent 文件读取完整分析"""
    from agents.strategic_memo_writer import load_agent_analysis_per_sym
    date = "2026-05-20"
    _make_agent_file(tmp_path, "TechAgent", "NVDA", date,
                     analysis=["MACD金叉", "RSI健康"], key_points=["Stage 2"])
    result = load_agent_analysis_per_sym("NVDA", date, find_dir=str(tmp_path / "findings"))
    assert "tech" in result
    assert result["tech"]["analysis"] == ["MACD金叉", "RSI健康"]
    assert result["tech"]["key_points"] == ["Stage 2"]


def test_load_debate_highlights(tmp_path):
    """从 per-sym debate 文件提取辩论摘要"""
    from agents.strategic_memo_writer import load_debate_highlights
    date = "2026-05-20"
    _make_debate_file(tmp_path, "NVDA", date)
    result = load_debate_highlights("NVDA", date, find_dir=str(tmp_path / "findings"))
    assert result["rounds"] >= 1
    assert len(result["key_challenges"]) > 0


def test_build_scenarios(tmp_path):
    """三情景分析基于 target_pct 和 hard_stop 构建"""
    from agents.strategic_memo_writer import build_scenarios
    _make_positions(tmp_path, "NVDA")
    scenarios = build_scenarios("NVDA", cur_price=224.0, base_dir=str(tmp_path))
    assert "bull" in scenarios and "base" in scenarios and "bear" in scenarios
    assert scenarios["base"]["price_target"] > 224.0   # 目标价高于当前价
    assert scenarios["bear"]["price_target"] < 224.0   # 熊市低于当前价
```

- [ ] **Step 2.2：运行测试，确认 FAIL**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_research_report.py -v 2>&1 | head -20
```

- [ ] **Step 2.3：在 strategic_memo_writer.py 中添加新的纯函数**

在现有代码的 `# ── 数据读取层` 部分后追加以下函数（不删除现有函数）：

```python
# ── 新增数据读取函数 ─────────────────────────────────────────────────────────

def load_agent_analysis_per_sym(sym: str, date: str,
                                  find_dir: str = FIND_DIR) -> dict:
    """
    从 per-symbol agent 文件读取完整分析（cio.py Task 1 保存的）。
    key: tech/fund/macro/risk/sentiment/sector
    """
    AGENT_MAP = {
        "TechAgent": "tech", "FundAgent": "fund", "MacroAgent": "macro",
        "RiskAgent": "risk", "SentimentAgent": "sentiment", "SectorAgent": "sector",
    }
    result = {}
    for agent_name, key in AGENT_MAP.items():
        path = os.path.join(find_dir, f"{agent_name}_{sym.upper()}_{date}.json")
        d = _load(path)
        if d:
            result[key] = {
                "signal":     d.get("signal", "neutral"),
                "confidence": d.get("confidence", 50),
                "analysis":   d.get("analysis", []),
                "key_points": d.get("key_points", []),
                "conclusion": d.get("conclusion", {}),
            }
    return result


def load_debate_highlights(sym: str, date: str,
                            find_dir: str = FIND_DIR) -> dict:
    """从 per-sym debate 文件提取辩论摘要"""
    path = os.path.join(find_dir, f"debate_{sym.upper()}_{date}.jsonl")
    records = _load_jsonl_all(path)
    if not records:
        return {"rounds": 0, "consensus_reached": False,
                "key_challenges": [], "dominant_view": "无辩论数据"}

    challenges = [r.get("content", "")[:60] for r in records
                  if r.get("msg_type") == "challenge"]
    rounds = max((r.get("round", 1) for r in records if "round" in r), default=1)
    # 最后一条 synthesis 或 verdict 作为主导观点
    verdicts = [r.get("content", "") for r in records
                if r.get("msg_type") in ("verdict", "synthesis")]
    dominant = verdicts[-1][:100] if verdicts else "辩论未产生明确结论"

    return {
        "rounds":           rounds,
        "consensus_reached": any(r.get("msg_type") == "consensus" for r in records),
        "key_challenges":   challenges[:4],
        "dominant_view":    dominant,
    }


def build_position_context(sym: str, cur_price: float | None = None,
                            base_dir: str = BASE) -> dict:
    """
    从 positions.json + premarket_summary 构建持仓管理区块。
    包含：完整论点、证伪条件、加仓策略、减仓策略、当日快照。
    """
    pos_cfg  = _load_position_cfg(sym)
    cost     = float(pos_cfg.get("t1_cost") or pos_cfg.get("cost") or 0)
    shares   = int(pos_cfg.get("shares") or pos_cfg.get("t1_shares") or 0)
    hard_stop = float(pos_cfg.get("t1_stop_snapshot") or 0) or None
    target_pct= float(pos_cfg.get("target_pct") or 15)
    target_price = round(cost * (1 + target_pct / 100), 2) if cost else None

    # 计算持仓天数
    entry_date_str = pos_cfg.get("date", str(_date.today()))
    try:
        days_held = (_date.today() - _date.fromisoformat(entry_date_str)).days
    except Exception:
        days_held = 0

    # 浮盈
    pnl_pct = None
    if cur_price and cost > 0:
        pnl_pct = round((cur_price - cost) / cost * 100, 2)

    # T2 加仓条件
    t2 = pos_cfg.get("t2_conditions", {}) or {}
    flex_add_level = None
    try:
        pm_path = os.path.join(base_dir, "findings",
                               f"premarket_summary_{_date.today()}_{sym.upper()}.json")
        pm = _load(pm_path)
        flex_add_level = (pm.get("post_open_adj") or {}).get("flex_add_adj") or \
                         (pm.get("exit") or {}).get("flex_add_level")
        flex_reduce_level = (pm.get("post_open_adj") or {}).get("flex_reduce_adj") or \
                            (pm.get("exit") or {}).get("flex_reduce_level")
    except Exception:
        flex_reduce_level = None

    return {
        "thesis_full":            pos_cfg.get("thesis", ""),
        "falsification_conditions": pos_cfg.get("falsification_conditions", []),
        "add_strategy": {
            "t2_conditions":    t2.get("note", ""),
            "t2_price_floor":   t2.get("underlying_price_floor"),
            "t2_etf_floor":     t2.get("etf_price_floor"),
            "flex_add_trigger": flex_add_level,
            "sizing_note":      f"T2 加仓门槛：底层标的>${t2.get('underlying_price_floor', '—')}",
        },
        "reduce_strategy": {
            "target_pct":           target_pct,
            "target_price":         target_price,
            "flex_reduce_trigger":  flex_reduce_level,
            "hard_stop":            hard_stop,
            "time_stop":            next((c for c in pos_cfg.get("falsification_conditions", [])
                                          if "截止" in c or "无法" in c), None),
        },
        "position_snapshot": {
            "cost":               cost,
            "shares":             shares,
            "cur_price":          cur_price,
            "unrealized_pnl_pct": pnl_pct,
            "days_held":          days_held,
            "gtc_placed":         pos_cfg.get("gtc_stop_placed", False),
        },
    }


def build_scenarios(sym: str, cur_price: float | None = None,
                    base_dir: str = BASE) -> dict:
    """
    构建三情景分析（牛/基准/熊）。
    基于 target_pct / hard_stop / tail_risk 推导。
    """
    pos_cfg   = _load_position_cfg(sym)
    fund      = _load_fundamentals(sym)
    cost      = float(pos_cfg.get("t1_cost") or pos_cfg.get("cost") or 0)
    target_pct= float(pos_cfg.get("target_pct") or 15)
    hard_stop = float(pos_cfg.get("t1_stop_snapshot") or 0)
    analyst_t = fund.get("target_price")
    base_price= cur_price or cost

    # 牛市：分析师目标价或 cost × (1 + target_pct × 2)
    bull_target = analyst_t or round(base_price * (1 + target_pct / 50), 2)
    # 基准：cost × (1 + target_pct)
    base_target = round(base_price * (1 + target_pct / 100), 2)
    # 熊市：hard_stop 或 cost × 0.85
    bear_target = hard_stop or round(base_price * 0.85, 2)

    return {
        "bull": {
            "price_target": bull_target,
            "condition":    "论点被市场完全验证，分析师上调目标价",
            "probability":  "medium",
        },
        "base": {
            "price_target": base_target,
            "condition":    f"论点按计划执行，达到目标收益 {target_pct}%",
            "probability":  "high",
        },
        "bear": {
            "price_target": bear_target,
            "condition":    "止损触发，论点破裂",
            "probability":  "low",
        },
    }
```

- [ ] **Step 2.4：更新 build_strategic_memo() 主函数，调用新函数并填充字段**

在 `build_strategic_memo()` 里，在读取数据源之后（`agents = _load_agent_reports(...)` 那一行附近），替换为使用 per-sym 函数，并在 return 之前加入新区块：

```python
    # ── 新增：从 per-sym 文件读取丰富数据 ────────────────────────────────────
    # 读 per-sym agent 分析（Task 1 保存的，比 cio_signals 更完整）
    agent_analysis = load_agent_analysis_per_sym(sym_upper, today)
    # 如果 per-sym 文件不存在，fallback 到现有逻辑（cio_signals）
    if not agent_analysis:
        agent_analysis = {}
        for key, ag_name in [("tech","TechAgent"),("fund","FundAgent"),
                              ("macro","MacroAgent"),("risk","RiskAgent"),
                              ("sentiment","SentimentAgent"),("sector","SectorAgent")]:
            ag_data = agents.get(ag_name, {})
            if ag_data:
                agent_analysis[key] = {
                    "signal": ag_data.get("signal","neutral"),
                    "confidence": ag_data.get("confidence",50),
                    "analysis": ag_data.get("analysis",[]),
                    "key_points": ag_data.get("key_points",[]),
                    "conclusion": ag_data.get("conclusion",{}),
                }

    # 读辩论内容
    debate_highlights = load_debate_highlights(sym_upper, today)

    # 持仓管理区块
    position_context = build_position_context(sym_upper, base_dir=base_dir)

    # 情景分析
    scenarios = build_scenarios(sym_upper, base_dir=base_dir)

    # ── 丰富现有字段 ──────────────────────────────────────────────────────────
    # company_intro：从 FundAgent 补充
    fund_analysis = agent_analysis.get("fund", {})
    company_intro_rich = (
        fnd.get("company_intro") or
        "; ".join(fund_analysis.get("key_points", [])[:2]) or
        pos_cfg.get("thesis", "")
    )[:200]

    # core_supporting_facts：从 bullish agent 分析提取
    rich_facts = []
    for key in ["tech", "fund", "sentiment"]:
        ag = agent_analysis.get(key, {})
        if ag.get("signal") == "bullish":
            for kp in ag.get("key_points", [])[:1]:
                rich_facts.append(f"[{key.upper()}] {kp}")
    core_facts = rich_facts[:3] or core_facts

    # main_risks：从 RiskAgent + bearish agents 提取
    rich_risks = []
    risk_ag = agent_analysis.get("risk", {})
    rich_risks.extend(f"[风险] {kp}" for kp in risk_ag.get("key_points", [])[:2])
    for key in ["macro", "sector"]:
        ag = agent_analysis.get(key, {})
        if ag.get("signal") in ("bearish", "neutral"):
            for kp in ag.get("key_points", [])[:1]:
                rich_risks.append(f"[{key.upper()}] {kp}")
    main_risks = rich_risks[:4] or main_risks

    # 更新 foundation
    fnd_updated = {
        **fnd,
        "company_intro": company_intro_rich,
    }
```

然后在 `return memo` 前，把新区块加进 memo dict：

```python
    # 新增区块加入 memo
    memo["position_context"]   = position_context
    memo["agent_analysis"]     = agent_analysis
    memo["debate_highlights"]  = debate_highlights
    memo["scenarios"]          = scenarios

    # 更新现有字段（丰富版）
    memo["foundation"]["company_intro"] = company_intro_rich
    memo["support_and_risk"]["core_supporting_facts"] = core_facts
    memo["support_and_risk"]["main_risks"] = main_risks

    return memo
```

- [ ] **Step 2.5：运行测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_research_report.py -v --tb=short
```

- [ ] **Step 2.6：冒烟测试**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 agents/strategic_memo_writer.py NVDA 2>&1
python3.12 -c "
import json
m = json.load(open('strategic_memo_NVDA.json'))
print('position_context:', list(m.get('position_context',{}).keys()))
print('agent_analysis agents:', list(m.get('agent_analysis',{}).keys()))
print('scenarios:', list(m.get('scenarios',{}).keys()))
print('debate rounds:', m.get('debate_highlights',{}).get('rounds'))
print('core_facts:', len(m['support_and_risk']['core_supporting_facts']))
" 2>/dev/null
```

- [ ] **Step 2.7：Commit**

```bash
git add agents/strategic_memo_writer.py tests/test_research_report.py
git commit -m "feat: strategic_memo_writer — position_context/agent_analysis/debate/scenarios + richer existing fields"
```

---

## Task 3：report_viewer.py — Notion 研报风完整重写

**Files:**
- Modify: `agents/report_viewer.py`（完整重写 render_research_report()）

---

- [ ] **Step 3.1：完整重写 report_viewer.py**

用以下内容**替换**整个文件（保留函数签名 `render_research_report(sym, date)` 和 `write_research_report(sym, date)`，重写实现）：

```python
"""
研究报告可视化模块 — report_viewer.py（Notion 研报风）
将 strategic_memo_{sym}.json 渲染为可读 HTML 研究报告。

输出: reports/research_{sym}_{date}.html
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE     = os.path.expanduser("~/stock_team")
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
        "bullish":  ("#e6f4ea", "#1a7f37", "#2da44e"),
        "bearish":  ("#ffeef0", "#cf222e", "#ff818c"),
        "neutral":  ("#f0f3f9", "#57606a", "#8c959f"),
        "buy":      ("#e6f4ea", "#1a7f37", "#2da44e"),
        "no_buy":   ("#ffeef0", "#cf222e", "#ff818c"),
        "not_sell": ("#fff8e1", "#7d5a00", "#e8ac09"),
    }
    bg, text, border = colors.get(signal, colors["neutral"])
    label = {"bullish": "看多", "bearish": "看空", "neutral": "中性",
             "buy": "买入", "no_buy": "不买", "not_sell": "不卖"}.get(signal, signal)
    conf_str = f" {confidence}%" if confidence else ""
    return (f'<span style="background:{bg};color:{text};border:1px solid {border};'
            f'padding:2px 10px;border-radius:12px;font-size:0.8em;font-weight:600">'
            f'{label}{conf_str}</span>')


def _stance_banner(stance):
    cfg = {
        "strong_hold": ("🟢", "#e6f4ea", "#1a7f37", "强力持有"),
        "hold":        ("🔵", "#ddf4ff", "#0550ae", "持有"),
        "hold_reduced":("🟡", "#fff8e1", "#7d5a00", "减仓持有"),
        "reduce":      ("🟠", "#fff0e0", "#bc4c00", "考虑减仓"),
        "exit_ready":  ("🔴", "#ffeef0", "#cf222e", "准备出场"),
        "avoid":       ("⛔", "#ffeef0", "#cf222e", "回避"),
    }
    emoji, bg, color, label = cfg.get(stance, ("⚪", "#f6f8fa", "#57606a", stance or "—"))
    return emoji, bg, color, label


def _card(title, body, icon=""):
    return f"""
<div class="card">
  <div class="card-title">{icon} {title}</div>
  {body}
</div>"""


def _kv_table(rows):
    html = '<table class="kv-table">'
    for label, value, *extra in rows:
        color = extra[0] if extra else ""
        style = f'color:{color}' if color else ""
        html += f'<tr><td class="kv-label">{label}</td><td style="{style}">{value}</td></tr>'
    html += '</table>'
    return html


def _section_header(title, icon=""):
    return f'<h2 class="section-h2">{icon} {title}</h2>'


CSS = """
<style>
:root {
  --bg:       #f6f8fa;
  --card:     #ffffff;
  --border:   #d0d7de;
  --text:     #1f2328;
  --muted:    #57606a;
  --accent:   #0969da;
  --green:    #1a7f37;
  --red:      #cf222e;
  --yellow:   #7d5a00;
  --radius:   8px;
  --shadow:   0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
               'Helvetica Neue', sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 15px;
  line-height: 1.65;
  padding: 0;
}

/* Top header */
.top-bar {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 16px 32px;
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.top-bar h1 { font-size: 1.5em; font-weight: 700; }
.top-bar .meta { color: var(--muted); font-size: 0.85em; }
.top-bar a { color: var(--accent); font-size: 0.8em; }

/* Stance banner */
.stance-banner {
  padding: 20px 32px;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}
.stance-label { font-size: 1.8em; font-weight: 700; }
.stance-conf  { font-size: 1em; }
.stance-key   { font-size: 0.9em; max-width: 600px; }

/* Main layout */
.main { max-width: 1200px; margin: 0 auto; padding: 24px 32px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px; }

/* Cards */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
  margin-bottom: 16px;
}
.card-title {
  font-size: 0.8em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

/* Section headers */
.section-h2 {
  font-size: 1.1em;
  font-weight: 600;
  color: var(--text);
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent);
  display: inline-block;
}

/* KV table */
.kv-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
.kv-table tr { border-bottom: 1px solid #f0f0f0; }
.kv-table tr:last-child { border-bottom: none; }
.kv-label { color: var(--muted); padding: 5px 8px 5px 0; width: 40%; vertical-align: top; }
.kv-table td { padding: 5px 4px; }

/* Master cards */
.master-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.master-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px;
}
.master-name { font-weight: 600; font-size: 0.95em; }
.master-domain { color: var(--muted); font-size: 0.78em; margin-bottom: 8px; }
.master-arg { font-size: 0.88em; color: var(--text); margin-top: 6px; }

/* Agent tabs */
.tab-bar { display: flex; gap: 4px; border-bottom: 2px solid var(--border); margin-bottom: 16px; flex-wrap: wrap; }
.tab-btn {
  padding: 6px 14px; cursor: pointer; border: none; background: none;
  color: var(--muted); font-size: 0.85em; font-weight: 500;
  border-bottom: 2px solid transparent; margin-bottom: -2px;
}
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-pane { display: none; }
.tab-pane.active { display: block; }

/* Analysis block */
.analysis-block { margin-bottom: 12px; }
.analysis-block .kp { color: var(--green); font-size: 0.88em; padding: 3px 0; }
.analysis-block .para { color: var(--text); font-size: 0.9em; padding: 3px 0; border-bottom: 1px dashed #e8e8e8; }

/* Scenario cards */
.scenario-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.scenario-card { border-radius: 8px; padding: 16px; }
.scenario-price { font-size: 1.5em; font-weight: 700; }
.scenario-label { font-size: 0.75em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.scenario-cond { font-size: 0.85em; margin-top: 8px; }

/* Falsification items */
.falsif-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 0.88em;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.falsif-item:last-child { border-bottom: none; }

/* Helpers */
.green { color: var(--green); }
.red   { color: var(--red); }
.yellow{ color: var(--yellow); }
.muted { color: var(--muted); }
.bold  { font-weight: 600; }
.small { font-size: 0.82em; }
p.note { font-size: 0.88em; color: var(--muted); font-style: italic; padding: 8px 0; }
</style>
"""

SCRIPT = """
<script>
function showTab(group, name, el) {
  document.querySelectorAll(`[data-group="${group}"].tab-pane`).forEach(p => p.classList.remove('active'));
  document.querySelectorAll(`[data-group="${group}"].tab-btn`).forEach(b => b.classList.remove('active'));
  document.getElementById(`${group}-${name}`).classList.add('active');
  el.classList.add('active');
}
// 自动激活第一个 tab
document.querySelectorAll('.tab-bar').forEach(bar => {
  const first = bar.querySelector('.tab-btn');
  if (first) first.click();
});
</script>
"""


def render_research_report(sym: str, date: str) -> str:
    sym_upper = sym.upper()
    memo      = _load(os.path.join(BASE, f"strategic_memo_{sym_upper}.json"))
    pm        = _load(os.path.join(FIND_DIR, f"premarket_summary_{date}_{sym_upper}.json"))
    fund      = _load(os.path.join(FIND_DIR, f"fundamentals_{sym_upper}.json"))

    # ── 提取数据 ────────────────────────────────────────────────────────────
    synth   = memo.get("synthesis", {})
    judg    = memo.get("judgment", {})
    sr      = memo.get("support_and_risk", {})
    fnd     = memo.get("foundation", {})
    outlook = memo.get("outlook", {})
    pos_ctx = memo.get("position_context", {})
    ag_an   = memo.get("agent_analysis", {})
    debate  = memo.get("debate_highlights", {})
    scens   = memo.get("scenarios", {})
    mvotes  = judg.get("master_votes", {})
    mvsum   = mvotes.get("_summary", {})
    fsnap   = fnd.get("fundamentals_snapshot", {})

    stance = synth.get("strategic_stance", "hold")
    conf   = synth.get("confidence", 0)
    emoji, banner_bg, banner_color, stance_label = _stance_banner(stance)

    pm_entry = pm.get("entry", {}) or {}
    pm_exit  = pm.get("exit", {}) or {}
    pm_snap  = pm.get("stock_snapshot", {}) or {}
    pos_snap = pos_ctx.get("position_snapshot", {})
    cur_price= pos_snap.get("cur_price")
    pnl_pct  = pos_snap.get("unrealized_pnl_pct")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── TOP BAR ───────────────────────────────────────────────────────────────
    top_bar = f"""
<div class="top-bar">
  <h1>{sym_upper}</h1>
  <span class="muted">{fnd.get('company_intro','')[:60]}</span>
  <div style="flex:1"></div>
  <div class="meta">
    {now_str} &nbsp;|&nbsp;
    <a href="../findings/premarket_summary_{date}_{sym_upper}.json" target="_blank">盘前数据</a> &nbsp;|&nbsp;
    <a href="../strategic_memo_{sym_upper}.json" target="_blank">原始 Memo</a>
  </div>
</div>"""

    # ── STANCE BANNER ────────────────────────────────────────────────────────
    pnl_str = (f'<span class="{"green" if pnl_pct and pnl_pct >= 0 else "red"}">'
               f'{_pct(pnl_pct)}</span>') if pnl_pct is not None else ""
    stance_banner_html = f"""
<div class="stance-banner" style="background:{banner_bg}">
  <div>
    <div class="stance-label" style="color:{banner_color}">{emoji} {stance_label.upper()}</div>
    <div class="stance-conf muted">{_stars(conf)} 置信度 {conf}/5</div>
  </div>
  <div class="stance-key">{synth.get('key_condition','')}</div>
  <div style="margin-left:auto;text-align:right">
    <div class="bold">{_dollar(cur_price)}</div>
    <div class="small muted">{pnl_str} 浮盈</div>
    <div class="small muted">持仓 {pos_snap.get('days_held',0)} 天</div>
  </div>
</div>"""

    # ── 基本面 + 持仓快照 ────────────────────────────────────────────────────
    fund_rows = [
        ("PE (TTM)", _v(fsnap.get("pe_ttm") or fund.get("pe_ttm"))),
        ("PE (Fwd)", _v(fsnap.get("pe_fwd") or fund.get("pe_forward"))),
        ("PEG",      _v(fsnap.get("peg") or fund.get("peg_ratio"))),
        ("营收增速",  _pct(fsnap.get("revenue_growth_pct") or fund.get("revenue_growth_pct"))),
        ("FCF",      f"${fsnap.get('fcf_B','—')}B" if fsnap.get("fcf_B") else
                     fund.get("fcf_B_str","—")),
        ("分析师目标", f"{_dollar(fsnap.get('analyst_target') or fund.get('target_price'))} "
                      f"({_pct(fsnap.get('analyst_upside_pct') or fund.get('target_upside_pct'))} 空间)"),
    ]
    pos_rows = [
        ("成本价",   _dollar(pos_snap.get("cost")),
         "var(--green)" if pnl_pct and pnl_pct > 0 else "var(--red)" if pnl_pct and pnl_pct < 0 else ""),
        ("持仓量",   f"{pos_snap.get('shares','—')} 股"),
        ("当前价",   _dollar(cur_price)),
        ("浮盈",     _pct(pnl_pct), "var(--green)" if pnl_pct and pnl_pct >= 0 else "var(--red)"),
        ("持仓天数",  f"{pos_snap.get('days_held',0)} 天"),
        ("GTC 状态", "✅ 已挂" if pos_snap.get("gtc_placed") else "❌ 未挂",
         "" if pos_snap.get("gtc_placed") else "var(--red)"),
    ]

    fund_block = _card("基本面快照", _kv_table(fund_rows), "💰")
    pos_block  = _card("当日持仓", _kv_table(pos_rows), "📊")

    # ── 持仓策略 ────────────────────────────────────────────────────────────
    add_st  = pos_ctx.get("add_strategy", {})
    red_st  = pos_ctx.get("reduce_strategy", {})
    falsif  = pos_ctx.get("falsification_conditions", [])

    strategy_html = f"""
    <div class="grid-2">
      {_card("加仓策略", _kv_table([
          ("T2 触发条件", add_st.get("t2_conditions","—")),
          ("底层标的门槛", _dollar(add_st.get("t2_price_floor"))),
          ("ETF 触发价",  _dollar(add_st.get("t2_etf_floor"))),
          ("Flex 加仓价", _dollar(add_st.get("flex_add_trigger"))),
          ("说明",        add_st.get("sizing_note","—")),
      ]), "📈")}
      {_card("减仓策略", _kv_table([
          ("目标收益",    _pct(red_st.get("target_pct"))),
          ("目标价",      _dollar(red_st.get("target_price"))),
          ("Flex 减仓价", _dollar(red_st.get("flex_reduce_trigger"))),
          ("硬止损",      _dollar(red_st.get("hard_stop"))),
          ("时间止损",    red_st.get("time_stop","—")),
      ]), "📉")}
    </div>"""

    falsif_html = "".join(
        f'<div class="falsif-item"><span>🔒</span><span>{fc}</span></div>'
        for fc in falsif
    ) or '<p class="note">暂无证伪条件</p>'
    falsif_block = _card("论点证伪条件", falsif_html, "🛡️")

    thesis_block = _card("持仓论点",
        f'<p style="font-size:1em;line-height:1.7">{pos_ctx.get("thesis_full","—")}</p>', "📋")

    # ── 大师投票 ────────────────────────────────────────────────────────────
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
        sig = {"strong_yes": "bullish", "yes": "bullish",
               "neutral": "neutral", "no": "bearish"}.get(
            mdata.get("supports_holding", "neutral"), "neutral")
        badge = _signal_badge(sig)
        direct= mdata.get("position_direction", "hold")
        arg   = mdata.get("core_argument", "")[:80]
        master_cards += f"""
<div class="master-card">
  <div class="master-name">{name} {badge}</div>
  <div class="master-domain muted small">{domain} → <b>{direct}</b></div>
  <div class="master-arg">{arg}</div>
</div>"""

    masters_block = _card(
        f"大师投票 — 看多 {mvsum.get('bullish_count',0)} 中性 {mvsum.get('neutral_count',0)} 看空 {mvsum.get('bearish_count',0)}",
        f'<div class="master-grid">{master_cards}</div>', "🎓")

    # ── 六维度分析（Tab） ───────────────────────────────────────────────────
    AGENT_LABELS = {
        "tech": "📈 技术", "fund": "💰 基本面", "macro": "🌍 宏观",
        "risk": "⚠️ 风险", "sentiment": "💬 情绪", "sector": "🏭 板块",
    }
    tab_btns = ""
    tab_panes = ""
    for idx, (key, label) in enumerate(AGENT_LABELS.items()):
        active = "active" if idx == 0 else ""
        tab_btns += (f'<button class="tab-btn {active}" data-group="agents" '
                     f'onclick="showTab(\'agents\',\'{key}\',this)">{label}</button>')
        ag = ag_an.get(key, {})
        sig_b = _signal_badge(ag.get("signal","neutral"), ag.get("confidence"))
        kps = "".join(f'<div class="kp">✅ {kp}</div>'
                      for kp in ag.get("key_points", []))
        paras = "".join(f'<div class="para">{p}</div>'
                        for p in ag.get("analysis", []))
        concl = ag.get("conclusion", {})
        concl_html = ""
        if concl:
            concl_html = f"""
<div style="margin-top:10px;padding:10px;background:#f6f8fa;border-radius:6px;font-size:0.88em">
  <b>结论：</b>{concl.get('judgment','—')}<br>
  <b>边界：</b>{concl.get('boundary','—')}
</div>"""
        tab_panes += f"""
<div id="agents-{key}" class="tab-pane {active}" data-group="agents">
  <div style="margin-bottom:8px">{sig_b}</div>
  <div class="analysis-block">{kps}{paras}</div>
  {concl_html}
  {"<p class='note'>暂无分析数据（需运行 CIO 全量分析后重新生成）</p>" if not ag else ""}
</div>"""

    agents_block = _card("六维度分析",
        f'<div class="tab-bar">{tab_btns}</div>{tab_panes}', "🔬")

    # ── 辩论摘要 ────────────────────────────────────────────────────────────
    challenges_html = "".join(
        f'<div class="falsif-item"><span>💬</span><span>{c}</span></div>'
        for c in debate.get("key_challenges", [])
    ) or '<p class="note">无辩论数据</p>'
    debate_block = _card(
        f"大师辩论 — {debate.get('rounds',0)} 轮 {'(共识达成)' if debate.get('consensus_reached') else ''}",
        challenges_html + f'<p style="margin-top:8px;font-size:0.88em"><b>主导观点：</b>{debate.get("dominant_view","—")}</p>',
        "⚡")

    # ── 情景分析 ────────────────────────────────────────────────────────────
    scen_colors = {
        "bull": ("#e6f4ea", "#1a7f37"),
        "base": ("#ddf4ff", "#0550ae"),
        "bear": ("#ffeef0", "#cf222e"),
    }
    scen_labels = {"bull": "🐂 牛市情景", "base": "📊 基准情景", "bear": "🐻 熊市情景"}
    scen_html = '<div class="scenario-grid">'
    for key in ["bull", "base", "bear"]:
        sc = scens.get(key, {})
        bg, color = scen_colors[key]
        scen_html += f"""
<div class="scenario-card" style="background:{bg}">
  <div class="scenario-label" style="color:{color}">{scen_labels[key]}</div>
  <div class="scenario-price" style="color:{color}">{_dollar(sc.get('price_target'))}</div>
  <div class="scenario-cond">{sc.get('condition','—')}</div>
  <div class="small muted" style="margin-top:6px">概率：{sc.get('probability','—')}</div>
</div>"""
    scen_html += '</div>'
    scen_block = _card("情景分析", scen_html, "🎯")

    # ── 出场逻辑 ────────────────────────────────────────────────────────────
    exit_l = outlook.get("exit_logic", {})
    exit_rows = [
        ("目标达成出场", exit_l.get("target_reached", "—")),
        ("主动出场信号", exit_l.get("proactive_exit_signal", "—")),
        ("有效期至",     outlook.get("valid_until", "—")),
    ]
    exit_block = _card("出场逻辑", _kv_table(exit_rows), "🚪")

    # ── 组装页面 ────────────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{sym_upper} 研究报告 {date}</title>
{CSS}
</head>
<body>
{top_bar}
{stance_banner_html}
<div class="main">

{_section_header("公司概况与持仓", "🏢")}
<div class="grid-2">
  {_card("公司简介", f'<p style="line-height:1.8">{fnd.get("company_intro","—")}</p><p style="margin-top:8px" class="muted small">{fnd.get("sector_intro","")}</p>', "🏢")}
  {thesis_block}
</div>
<div class="grid-2">
  {fund_block}
  {pos_block}
</div>

{_section_header("持仓管理策略", "⚙️")}
{strategy_html}
{falsif_block}

{_section_header("大师投票", "🎓")}
{masters_block}

{_section_header("六维度分析", "🔬")}
{agents_block}

{_section_header("情景分析", "🎯")}
{scen_block}

{_section_header("辩论与综合", "⚡")}
<div class="grid-2">
  {debate_block}
  {exit_block}
</div>

</div>
{SCRIPT}
</body>
</html>"""


def write_research_report(sym: str, date: str, base_dir: str = BASE) -> str:
    html = render_research_report(sym, date)
    os.makedirs(os.path.join(base_dir, "reports"), exist_ok=True)
    path = os.path.join(base_dir, "reports", f"research_{sym.upper()}_{date}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main(syms=None):
    date_str = _date.today().strftime("%Y-%m-%d")
    if not syms:
        import glob
        files = glob.glob(os.path.join(BASE, "strategic_memo_*.json"))
        syms  = [os.path.basename(f).replace("strategic_memo_","").replace(".json","")
                 for f in files]
    if not syms:
        print("无 strategic_memo 文件，请先运行全量分析")
        return
    print(f"\n生成研究报告（{len(syms)} 只）\n")
    for sym in syms:
        path = write_research_report(sym, date_str)
        print(f"  {sym}: ✅ {os.path.basename(path)}")


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
```

- [ ] **Step 3.2：生成报告并在浏览器查看**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 agents/report_viewer.py NVDA MRVU LITX IAU 2>&1
ls -la reports/research_*_2026-05-20.html
```

- [ ] **Step 3.3：Commit**

```bash
git add agents/report_viewer.py tests/test_research_report.py
git commit -m "feat: report_viewer Notion研报风完全重写 — 公司概况/持仓策略/大师投票/六维度/情景分析"
```

---

## Task 5：cio.py — Phase 3 输出叙述性 narrative 文件

**核心思想**：CIO 在运行 Phase 3 时已经拥有所有上下文（agent 分析 + 大师立场 + 辩论）。让 Phase 3 直接输出一个 `findings/narrative_{sym}_{date}.json`，包含预格式化的叙述文本，report_viewer 直接读取展示，无需二次处理。

**文件:**
- Modify: `agents/cio.py`（phase3 末尾）
- Modify: `agents/report_viewer.py`（读取并展示 narrative）

---

- [ ] **Step 5.1：在 cio.py phase3 末尾写 narrative 文件**

找到 `cio.py` 的 `phase3(symbol)` 函数或主流程 Phase 3 调用位置（约第 310-400 行），在 `run("report_agent", [symbol])` 之后插入：

```python
    # ── 输出叙述性 narrative 文件（供 report_viewer 直接使用）────────────────
    try:
        from datetime import date as _dt
        _date_str = str(_dt.today())
        _narrative_path = os.path.join(FINDINGS_DIR, f"narrative_{symbol}_{_date_str}.json")

        # 读取各数据源
        _board = []
        if os.path.exists(BOARD_PATH):
            _board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()]

        _stances = []
        if os.path.exists(os.path.join(BASE, "persona_stances.jsonl")):
            _stances = [json.loads(l) for l in
                        open(os.path.join(BASE, "persona_stances.jsonl")) if l.strip()]
        # 只取当前标的最新一条
        _sym_stances = next((s for s in reversed(_stances)
                             if s.get("symbol","").upper() == symbol.upper()
                             and s.get("msg_type") == "persona_stances"), {})

        # 各 agent 叙述段落
        _agent_narratives = {}
        for _ag in ["TechAgent","FundAgent","MacroAgent","RiskAgent","SentimentAgent","SectorAgent"]:
            _ap = os.path.join(FINDINGS_DIR, f"{_ag}_{symbol}_{_date_str}.json")
            if os.path.exists(_ap):
                _d = json.load(open(_ap, encoding="utf-8"))
                _paras = _d.get("analysis", [])
                _kps   = _d.get("key_points", [])
                _concl = _d.get("conclusion", {})
                _sig   = _d.get("signal", "neutral")
                _conf  = _d.get("confidence", 50)
                _key   = _ag.replace("Agent","").lower()
                # 合成叙述段落
                _narrative_text = " ".join(_paras[:3]) if _paras else ""
                if not _narrative_text and _kps:
                    _narrative_text = "；".join(_kps[:3])
                _agent_narratives[_key] = {
                    "signal":    _sig,
                    "confidence": _conf,
                    "narrative": _narrative_text,
                    "key_points": _kps[:4],
                    "conclusion_text": _concl.get("judgment",""),
                    "boundary_text":   _concl.get("boundary",""),
                }

        # 大师叙述（从 persona_stances 提取每位大师的完整表述）
        _master_narratives = {}
        for _master, _mdata in _sym_stances.get("stances", {}).items():
            if not isinstance(_mdata, dict):
                continue
            _master_narratives[_master] = {
                "signal":    _mdata.get("signal","neutral"),
                "confidence": _mdata.get("confidence", 50),
                "argument":  _mdata.get("core_argument","")[:120],
                "direction": _mdata.get("position_direction","hold"),
                "invalidation": _mdata.get("invalidation","")[:80],
            }

        # 辩论叙述（提取 challenge 和 response 的核心内容）
        _debate_narrative = []
        for _msg in _board:
            if _msg.get("msg_type") in ("challenge","response") and _msg.get("content"):
                _debate_narrative.append({
                    "from":    _msg.get("from","?"),
                    "type":    _msg.get("msg_type"),
                    "content": str(_msg.get("content",""))[:150],
                })
        _debate_narrative = _debate_narrative[:8]  # 最多保留 8 条关键发言

        # 综合投资建议叙述（从 Phase 2-Persona synthesis 提取）
        _synthesis_text = ""
        _synth_recs = [m for m in _board if m.get("msg_type") in ("synthesis","verdict")]
        if _synth_recs:
            _synthesis_text = str(_synth_recs[-1].get("content",""))[:300]

        _narrative = {
            "sym":              symbol,
            "date":             _date_str,
            "agent_narratives": _agent_narratives,
            "master_narratives": _master_narratives,
            "debate_dialogue":  _debate_narrative,
            "synthesis_text":   _synthesis_text,
        }
        with open(_narrative_path, "w", encoding="utf-8") as _nf:
            json.dump(_narrative, _nf, indent=2, ensure_ascii=False)
        print(f"[cio] narrative 叙述文件 → {_narrative_path}")
    except Exception as _e:
        pass  # 不阻断主流程
```

- [ ] **Step 5.2：在 report_viewer.py 读取 narrative 并展示**

在 `render_research_report()` 函数开头的数据读取区加载 narrative 文件：

```python
    # 读取 narrative 叙述文件（CIO Phase 3 输出，比 memo 更丰富）
    narrative = _load(os.path.join(FIND_DIR, f"narrative_{sym_upper}_{date}.json"))
    ag_narr   = narrative.get("agent_narratives", {})
    ma_narr   = narrative.get("master_narratives", {})
    debate_d  = narrative.get("debate_dialogue", [])
    synth_txt = narrative.get("synthesis_text", "")
```

然后在**六维度分析 Tab** 里，每个 Tab 的 analysis block 改为优先读 `ag_narr`：

```python
    # 六维度分析 Tab 构建（读取 narrative 叙述优先）
    for idx, (key, label) in enumerate(AGENT_LABELS.items()):
        ag_mem = ag_an.get(key, {})         # memo 里的 agent_analysis（key_points）
        ag_n   = ag_narr.get(key, {})       # narrative 里的完整叙述段落
        narrative_text = ag_n.get("narrative", "")
        conclusion_text= ag_n.get("conclusion_text", "")
        boundary_text  = ag_n.get("boundary_text", "")
        key_points     = ag_n.get("key_points", []) or ag_mem.get("key_points", [])
        sig            = ag_n.get("signal") or ag_mem.get("signal", "neutral")
        conf           = ag_n.get("confidence") or ag_mem.get("confidence", 0)
        # ... 展示时优先用 narrative_text 而非 paras 列表
```

在**大师投票区**，每张大师卡片加上完整的 `argument` 和 `invalidation`：

```python
        # 从 ma_narr 读取完整大师叙述
        mn = ma_narr.get(key, {})
        full_arg    = mn.get("argument", mdata.get("core_argument",""))[:120]
        invalidation= mn.get("invalidation","")[:80]
        # 卡片里加一行：[证伪条件: {invalidation}]
```

在**辩论摘要区**，展示 `debate_d`（真实对话而非摘要）：

```python
    # 辩论对话展示（来自 narrative.debate_dialogue）
    dialogue_html = ""
    for msg in debate_d:
        type_label = "💬 质疑" if msg["type"] == "challenge" else "↩️ 回应"
        dialogue_html += f"""
<div style="padding:8px 0;border-bottom:1px solid #f0f0f0;font-size:0.88em">
  <span class="muted small">{msg['from']} {type_label}</span><br>
  {msg['content']}
</div>"""
    if synth_txt:
        dialogue_html += f"""
<div style="margin-top:12px;padding:12px;background:#f6f8fa;border-radius:6px;font-size:0.9em">
  <b>综合结论：</b>{synth_txt}
</div>"""
```

- [ ] **Step 5.3：测试 — 跑一次完整流程验证 narrative 文件生成**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 agents/cio.py NVDA --phases 0123 2>&1 | grep "narrative"
ls findings/narrative_NVDA_*.json 2>/dev/null && echo "✅ narrative 文件生成"
/tool/pandora/bin/python3.12 agents/strategic_memo_writer.py NVDA 2>&1 | tail -3
/tool/pandora/bin/python3.12 agents/report_viewer.py NVDA 2>&1
```

- [ ] **Step 5.4：Commit**

```bash
git add agents/cio.py agents/report_viewer.py
git commit -m "feat: cio Phase3 outputs narrative_{sym}.json + report_viewer reads full dialogue/narratives"
```

---

## Task 4：CHANGELOG 更新

- [ ] **Step 4.1：更新 CHANGELOG.md 顶部**

```
## 2026-05-20 研究报告全面升级

### 架构修复
- `agents/cio.py` — per-symbol agent 文件保存，防止多标的覆盖

### 新增/重构
- `agents/strategic_memo_writer.py` — position_context/agent_analysis/debate/scenarios 四个新区块，现有字段大幅丰富
- `agents/report_viewer.py` — Notion 研报风完整重写，公司概况/持仓策略/大师投票卡片/六维度 Tab/情景分析/辩论
- `tests/test_research_report.py` — 核心函数单元测试
```

- [ ] **Step 4.2：Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: CHANGELOG 研究报告升级"
```
