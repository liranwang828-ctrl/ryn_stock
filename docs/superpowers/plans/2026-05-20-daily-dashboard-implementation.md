# daily_dashboard 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/dashboard_writer.py` + `templates/daily_dashboard.html.j2`，每次 poll 结束后生成 `reports/daily_dashboard_{date}.html`（静态 HTML，meta refresh 30s），聚合所有 B 级 JSON 数据可视化展示。

**Architecture:** `dashboard_writer.py` 读取所有 B 级 JSON 文件，构建上下文字典，通过 Jinja2 渲染 `daily_dashboard.html.j2`。HTML 含4个 Tab（总览 / 盘中 / 事件日志 / 盘后复盘），纯 CSS + JS，无外部依赖，meta refresh 自动刷新。poll.py 最后追加 3 行调用。

**Tech Stack:** Python 3.12, jinja2（已有）, 纯 HTML/CSS/JS

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/dashboard_writer.py` | 新建 | 读取所有 JSON，构建 Jinja2 上下文 |
| `templates/daily_dashboard.html.j2` | 新建 | 4-Tab HTML 模板 |
| `agents/poll.py` | 修改（3 行）| 每轮末尾调用 write_dashboard |
| `tests/test_dashboard_writer.py` | 新建 | 单元测试：数据加载函数 |

---

## Task 1：dashboard_writer.py — 数据加载

**Files:**
- Create: `agents/dashboard_writer.py`
- Create: `tests/test_dashboard_writer.py`

---

- [ ] **Step 1.1：写测试**

```python
# tests/test_dashboard_writer.py
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/stock_team"))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_load_premarket_summaries_returns_dict(tmp_path):
    """load_premarket_summaries 返回 {sym: summary} 字典"""
    from agents.dashboard_writer import load_premarket_summaries
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    _write(str(findings / f"premarket_summary_{date}_NVDA.json"), {
        "date": date, "sym": "NVDA",
        "stock_snapshot": {"gap_pct": 1.5, "pred_scene": "B"},
        "entry": {"decision": "enter", "sizing": "×1.0"},
        "exit": None, "thesis": None,
        "market_context": {"env": "顺风", "vix_level": 18.5},
        "strategic_context": {"source": "premarket_inferred", "strategic_stance": "hold"},
        "post_open_adj": None,
    })
    result = load_premarket_summaries(date, symbols=["NVDA"], find_dir=str(findings))
    assert "NVDA" in result
    assert result["NVDA"]["entry"]["decision"] == "enter"


def test_load_intraday_latest_returns_dict(tmp_path):
    """load_intraday_latest 返回 {sym: latest_record} 字典"""
    from agents.dashboard_writer import load_intraday_latest
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    record = {"ts": "10:30:00", "meta": {"sym": "NVDA", "date": date,
              "session_min": 60, "llm_triggered": False, "llm_trigger": None,
              "cooldown_until": None, "post_open_calibrated": True},
              "price_now": {"price": 220.0, "chg_pct": 1.5, "gate_status": "通过",
                            "master_avg": 6.5, "master_consensus": "buy"},
              "plan_vs_now": {"thesis_signal": "intact", "entry_go_status": "go",
                              "dist_to_stop_pct": 5.2},
              "node_snapshot": {}, "action_now": None}
    with open(str(findings / f"intraday_snapshot_{date}_NVDA.jsonl"), "w") as f:
        f.write(json.dumps(record) + "\n")

    result = load_intraday_latest(date, symbols=["NVDA"], find_dir=str(findings))
    assert "NVDA" in result
    assert result["NVDA"]["price_now"]["price"] == 220.0


def test_load_intraday_events_filters_llm(tmp_path):
    """load_intraday_events 只返回 llm_triggered=True 的条目"""
    from agents.dashboard_writer import load_intraday_events
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()
    r1 = {"ts": "09:30:00", "meta": {"sym": "NVDA", "date": date, "session_min": 0,
          "llm_triggered": False, "llm_trigger": None, "cooldown_until": None,
          "post_open_calibrated": False},
          "price_now": {}, "plan_vs_now": {}, "node_snapshot": {}, "action_now": None}
    r2 = {"ts": "10:00:00", "meta": {"sym": "NVDA", "date": date, "session_min": 30,
          "llm_triggered": True, "llm_trigger": "entry_go", "cooldown_until": None,
          "post_open_calibrated": True},
          "price_now": {"price": 218.0}, "plan_vs_now": {"entry_go_status": "go"},
          "node_snapshot": {}, "action_now": {"conclusion": "enter", "note": "entry_go 触发"}}

    with open(str(findings / f"intraday_snapshot_{date}_NVDA.jsonl"), "w") as f:
        f.write(json.dumps(r1) + "\n")
        f.write(json.dumps(r2) + "\n")

    events = load_intraday_events(date, symbols=["NVDA"], find_dir=str(findings))
    assert len(events) == 1
    assert events[0]["meta"]["llm_trigger"] == "entry_go"


def test_build_dashboard_context_schema(tmp_path):
    """build_dashboard_context 返回必要的顶层 key"""
    from agents.dashboard_writer import build_dashboard_context
    date = "2026-05-20"
    findings = tmp_path / "findings"
    findings.mkdir()

    ctx = build_dashboard_context(date, symbols=["NVDA"],
                                  base_dir=str(tmp_path))
    required = {"date", "generated_at", "symbols", "premarket",
                "intraday", "events", "portfolio", "postmarket_day",
                "session_state", "daily_plan"}
    assert required == set(ctx.keys()), f"缺少: {required - set(ctx.keys())}"
```

- [ ] **Step 1.2：运行测试，确认 FAIL**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_dashboard_writer.py -v 2>&1 | head -15
```

- [ ] **Step 1.3：创建 agents/dashboard_writer.py**

```python
"""
Dashboard 写入模块 — dashboard_writer.py
读取所有 B 级 JSON，生成 reports/daily_dashboard_{date}.html。

用法: python3.12 agents/dashboard_writer.py
     或由 poll.py 每轮末尾调用 write_dashboard()
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE     = os.path.expanduser("~/stock_team")
FIND_DIR = os.path.join(BASE, "findings")
TPL_DIR  = os.path.join(BASE, "templates")
RPT_DIR  = os.path.join(BASE, "reports")


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _read_last_jsonl(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)
                except Exception:
                    pass
    return last


def _read_all_jsonl(path: str) -> list[dict]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


# ── 数据加载函数 ──────────────────────────────────────────────────────────────

def load_premarket_summaries(date: str, symbols: list[str],
                              find_dir: str = FIND_DIR) -> dict:
    """返回 {sym: premarket_summary_dict}"""
    result = {}
    for sym in symbols:
        path = os.path.join(find_dir, f"premarket_summary_{date}_{sym}.json")
        d = _load(path)
        if d:
            result[sym] = d
    return result


def load_intraday_latest(date: str, symbols: list[str],
                          find_dir: str = FIND_DIR) -> dict:
    """返回 {sym: 最新一条 JSONL 记录}"""
    result = {}
    for sym in symbols:
        path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym}.jsonl")
        last = _read_last_jsonl(path)
        if last:
            result[sym] = last
    return result


def load_intraday_events(date: str, symbols: list[str],
                          find_dir: str = FIND_DIR) -> list[dict]:
    """返回所有 llm_triggered=True 的 JSONL 记录（按时间排序）"""
    events = []
    for sym in symbols:
        path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym}.jsonl")
        for rec in _read_all_jsonl(path):
            if rec.get("meta", {}).get("llm_triggered"):
                events.append(rec)
    events.sort(key=lambda r: r.get("ts", ""))
    return events


def load_portfolio_snapshot(date: str, find_dir: str = FIND_DIR) -> dict:
    path = os.path.join(find_dir, f"portfolio_snapshot_{date}.json")
    return _load(path)


def load_postmarket_day(date: str, find_dir: str = FIND_DIR) -> dict:
    path = os.path.join(find_dir, f"postmarket_summary_{date}.json")
    return _load(path)


def load_session_state(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, "learning", f"session_state_{date}.json")
    return _load(path)


def load_daily_plan(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, f"daily_plan_{date}.json")
    return _load(path)


# ── 上下文构建 ────────────────────────────────────────────────────────────────

def build_dashboard_context(date: str, symbols: list[str] | None = None,
                             base_dir: str = BASE) -> dict:
    """构建 Jinja2 渲染上下文"""
    find_dir = os.path.join(base_dir, "findings")

    if symbols is None:
        pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
        excluded = set(pos_data.get("_excluded", []))
        symbols = [s for s in pos_data.get("positions", {}).keys() if s not in excluded]
        cfg = _load(os.path.join(base_dir, "config", "poll_config.json"))
        symbols = list(dict.fromkeys(symbols + cfg.get("default_symbols", [])))

    premarket    = load_premarket_summaries(date, symbols, find_dir)
    intraday     = load_intraday_latest(date, symbols, find_dir)
    events       = load_intraday_events(date, symbols, find_dir)
    portfolio    = load_portfolio_snapshot(date, find_dir)
    postmarket_d = load_postmarket_day(date, find_dir)
    session_st   = load_session_state(date, base_dir)
    daily_plan   = load_daily_plan(date, base_dir)

    return {
        "date":           date,
        "generated_at":   datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "symbols":        symbols,
        "premarket":      premarket,
        "intraday":       intraday,
        "events":         events,
        "portfolio":      portfolio,
        "postmarket_day": postmarket_d,
        "session_state":  session_st,
        "daily_plan":     daily_plan,
    }


# ── HTML 生成 ─────────────────────────────────────────────────────────────────

def write_dashboard(date: str, symbols: list[str] | None = None,
                    base_dir: str = BASE) -> str:
    """生成 daily_dashboard_{date}.html，返回路径"""
    try:
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(os.path.join(base_dir, "templates")),
                          autoescape=False)
        tmpl = env.get_template("daily_dashboard.html.j2")
    except Exception as e:
        return f"[dashboard_writer] Jinja2 加载失败: {e}"

    ctx  = build_dashboard_context(date, symbols, base_dir)
    html = tmpl.render(**ctx)

    os.makedirs(os.path.join(base_dir, "reports"), exist_ok=True)
    path = os.path.join(base_dir, "reports", f"daily_dashboard_{date}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main():
    date_str = _date.today().strftime("%Y-%m-%d")
    path = write_dashboard(date_str)
    print(f"Dashboard: {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 1.4：运行测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_dashboard_writer.py -v
```

预期：全部 PASS

- [ ] **Step 1.5：Commit**

```bash
git add agents/dashboard_writer.py tests/test_dashboard_writer.py
git commit -m "feat: add dashboard_writer.py — load all B-level JSON + build context"
```

---

## Task 2：HTML 模板

**Files:**
- Create: `templates/daily_dashboard.html.j2`

---

- [ ] **Step 2.1：创建 templates/daily_dashboard.html.j2**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<title>Trading Dashboard {{ date }}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Courier New', monospace; background: #0d1117; color: #c9d1d9;
         padding: 1em; font-size: 14px; }
  h1 { color: #58a6ff; margin-bottom: 0.5em; }
  .meta { color: #8b949e; font-size: 0.85em; margin-bottom: 1em; }

  /* Tabs */
  .tab-bar { display: flex; gap: 4px; margin-bottom: 1em; border-bottom: 1px solid #30363d; }
  .tab-btn { background: #161b22; border: 1px solid #30363d; border-bottom: none;
             color: #8b949e; padding: 6px 16px; cursor: pointer; border-radius: 4px 4px 0 0; }
  .tab-btn.active { background: #1f6feb; color: #fff; border-color: #1f6feb; }
  .tab-pane { display: none; }
  .tab-pane.active { display: block; }

  /* Cards */
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 6px;
          padding: 1em; margin-bottom: 1em; }
  .card h2 { color: #58a6ff; font-size: 1em; margin-bottom: 0.5em; }
  .card h3 { color: #8b949e; font-size: 0.9em; margin-bottom: 0.3em; }

  /* Grid */
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1em; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1em; }

  /* Status badges */
  .badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; }
  .badge-green  { background: #1a3a24; color: #3fb950; border: 1px solid #3fb950; }
  .badge-red    { background: #3a1a1a; color: #f85149; border: 1px solid #f85149; }
  .badge-yellow { background: #3a2f00; color: #e3b341; border: 1px solid #e3b341; }
  .badge-blue   { background: #1a2a3a; color: #58a6ff; border: 1px solid #58a6ff; }
  .badge-gray   { background: #1f2937; color: #8b949e; border: 1px solid #30363d; }

  /* Table */
  table { width: 100%; border-collapse: collapse; }
  th, td { border: 1px solid #30363d; padding: 6px 10px; text-align: left; }
  th { background: #1f2937; color: #8b949e; font-size: 0.85em; }
  tr:hover td { background: #1f2937; }

  /* Colors */
  .green  { color: #3fb950; }
  .red    { color: #f85149; }
  .yellow { color: #e3b341; }
  .blue   { color: #58a6ff; }
  .gray   { color: #8b949e; }

  /* Alerts */
  .alert-red    { border-left: 3px solid #f85149; background: #3a1a1a; padding: 8px; margin: 4px 0; }
  .alert-yellow { border-left: 3px solid #e3b341; background: #3a2f00; padding: 8px; margin: 4px 0; }
  .alert-info   { border-left: 3px solid #58a6ff; background: #1a2a3a; padding: 8px; margin: 4px 0; }

  /* Next action banner */
  .banner { padding: 10px 16px; border-radius: 6px; margin-bottom: 1em; font-weight: bold; }
  .banner-immediate { background: #3a1a1a; border: 1px solid #f85149; color: #f85149; }
  .banner-normal    { background: #1a2a3a; border: 1px solid #58a6ff; color: #58a6ff; }
</style>
</head>
<body>
<h1>📊 Trading Dashboard — {{ date }}</h1>
<div class="meta">生成于 {{ generated_at }} | 每30秒自动刷新</div>

<!-- ── Next Action Banner ── -->
{% set ns = session_state %}
{% if ns and ns.next_action %}
{% set na = ns.next_action %}
<div class="banner {{ 'banner-immediate' if na.priority == 'immediate' else 'banner-normal' }}">
  {{ '🔴 ' if na.priority == 'immediate' else '→ ' }}{{ na.instruction }}
</div>
{% endif %}

<!-- ── Tab Bar ── -->
<div class="tab-bar">
  <button class="tab-btn active" onclick="showTab('overview')">📋 总览</button>
  <button class="tab-btn" onclick="showTab('intraday')">📈 盘中</button>
  <button class="tab-btn" onclick="showTab('events')">⚡ 事件日志</button>
  <button class="tab-btn" onclick="showTab('postmarket')">🌙 盘后复盘</button>
</div>

<!-- ═══════════════ TAB: 总览 ═══════════════ -->
<div id="tab-overview" class="tab-pane active">

  <!-- 今日行动 -->
  <div class="card">
    <h2>今日行动</h2>
    <table>
      <tr><th>标的</th><th>行动</th><th>价格</th><th>止损距离</th><th>论点</th><th>GTC</th></tr>
      {% for sym in symbols %}
      {% set pm = premarket.get(sym, {}) %}
      {% set it = intraday.get(sym, {}) %}
      {% set dp = daily_plan.get('per_symbol', {}).get(sym, {}) if daily_plan else {} %}
      {% set action = dp.get('action_now', '—') %}
      {% set price = it.get('price_now', {}).get('price') %}
      {% set dist_stop = it.get('plan_vs_now', {}).get('dist_to_stop_pct') %}
      {% set thesis = it.get('plan_vs_now', {}).get('thesis_signal', '—') %}
      {% set gtc_ok = sym not in (session_state.get('gtc_status', {}).get('missing', []) if session_state else []) %}
      <tr>
        <td><b>{{ sym }}</b></td>
        <td>
          {% if action == 'exit' %}<span class="badge badge-red">🚨 exit</span>
          {% elif action == 'reduce' %}<span class="badge badge-yellow">⚠️ reduce</span>
          {% elif action == 'enter' %}<span class="badge badge-green">✅ enter</span>
          {% elif action == 'watch' %}<span class="badge badge-blue">👁️ watch</span>
          {% elif action == 'hold' %}<span class="badge badge-blue">🔵 hold</span>
          {% else %}<span class="badge badge-gray">{{ action }}</span>
          {% endif %}
        </td>
        <td>{{ '$%.2f' % price if price else '—' }}</td>
        <td>
          {% if dist_stop is not none %}
            <span class="{{ 'red' if dist_stop < 3 else 'yellow' if dist_stop < 5 else 'green' }}">
              {{ '%.1f' % dist_stop }}%
            </span>
          {% else %}—{% endif %}
        </td>
        <td>
          {% if thesis == 'breach' %}<span class="red">💀 breach</span>
          {% elif thesis == 'warning' %}<span class="yellow">⚠️ warning</span>
          {% elif thesis == 'intact' %}<span class="green">✅ intact</span>
          {% else %}—{% endif %}
        </td>
        <td>{{ '✅' if gtc_ok else '❌' }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <!-- 离线期间事件 -->
  {% if session_state and session_state.get('missed_alerts') %}
  <div class="card">
    <h2>📬 离线期间事件</h2>
    {% for alert in session_state.missed_alerts %}
    <div class="alert-{{ 'red' if alert.level == 'red' else 'yellow' }}">
      <b>{{ alert.time }}</b> {{ alert.sym }} — {{ alert.event }} | {{ alert.detail }}
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- 组合风险 -->
  {% if portfolio and portfolio.totals %}
  <div class="card">
    <h2>组合风险快照</h2>
    <div class="grid-3">
      <div>
        <div class="gray">总杠杆</div>
        <div class="{{ 'red' if portfolio.totals.leverage_ratio > 2.5 else 'yellow' if portfolio.totals.leverage_ratio > 2.0 else 'green' }}">
          {{ '%.2f' % portfolio.totals.leverage_ratio }}x
        </div>
      </div>
      <div>
        <div class="gray">VaR (SPY-5%)</div>
        <div>${{ '%.0f' % portfolio.totals.var_5pct_loss }}</div>
      </div>
      <div>
        <div class="gray">浮盈</div>
        <div class="{{ 'green' if (portfolio.totals.total_unrealized_pnl_pct or 0) >= 0 else 'red' }}">
          {{ '%+.1f' % (portfolio.totals.total_unrealized_pnl_pct or 0) }}%
        </div>
      </div>
    </div>
    {% if portfolio.warnings %}
    <div style="margin-top:0.5em;">
      {% for w in portfolio.warnings %}
      <div class="alert-{{ 'red' if w.level == 'high' else 'yellow' if w.level == 'medium' else 'info' }}">
        {{ w.msg }}
      </div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endif %}

  <!-- 节点进度 -->
  {% if daily_plan and daily_plan.get('schedule') %}
  <div class="card">
    <h2>日程进度</h2>
    <table>
      <tr><th>节点</th><th>名称</th><th>时间</th><th>状态</th></tr>
      {% for s in daily_plan.schedule %}
      <tr>
        <td>{{ s.node }}</td>
        <td>{{ s.name }}</td>
        <td>{{ s.window }}</td>
        <td>
          {% if s.status == 'done' %}<span class="green">✅ 完成</span>
          {% elif s.status == 'active' %}<span class="yellow">🔄 进行中</span>
          {% elif s.status == 'auto' %}<span class="gray">🤖 自动</span>
          {% else %}<span class="gray">⏳ 等待</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

</div><!-- end tab-overview -->

<!-- ═══════════════ TAB: 盘中 ═══════════════ -->
<div id="tab-intraday" class="tab-pane">
  {% for sym in symbols %}
  {% set pm = premarket.get(sym, {}) %}
  {% set it = intraday.get(sym, {}) %}
  {% set dp_sym = daily_plan.get('per_symbol', {}).get(sym, {}) if daily_plan else {} %}
  <div class="card">
    <h2>{{ sym }}
      {% set pr = it.get('price_now', {}).get('price') %}
      {% if pr %} — ${{ '%.2f' % pr }}{% endif %}
    </h2>
    <div class="grid-2">
      <!-- 左：价格状态 -->
      <div>
        <h3>实时状态</h3>
        {% set pn = it.get('price_now', {}) %}
        <table>
          <tr><td class="gray">涨跌幅</td>
              <td class="{{ 'green' if (pn.get('chg_pct') or 0) >= 0 else 'red' }}">
                {{ '%+.1f' % (pn.get('chg_pct') or 0) }}%</td></tr>
          <tr><td class="gray">Gate</td>
              <td>{{ pn.get('gate_status', '—') }}</td></tr>
          <tr><td class="gray">大师均分</td>
              <td>{{ '%.1f' % pn.get('master_avg', 0) if pn.get('master_avg') else '—' }}</td></tr>
          <tr><td class="gray">共识</td>
              <td>{{ pn.get('master_consensus', '—') }}</td></tr>
        </table>
      </div>
      <!-- 右：计划 vs 现实 -->
      <div>
        <h3>计划 vs 现实</h3>
        {% set pvn = it.get('plan_vs_now', {}) %}
        {% set kl = dp_sym.get('key_levels', {}) %}
        <table>
          <tr><td class="gray">入场价</td>
              <td>{{ '$%.2f' % kl.entry_base if kl.get('entry_base') else '—' }}</td></tr>
          <tr><td class="gray">止损</td>
              <td>{{ '$%.2f' % kl.hard_stop if kl.get('hard_stop') else '—' }}
                  <span class="{{ 'red' if (pvn.get('dist_to_stop_pct') or 99) < 3 else 'yellow' if (pvn.get('dist_to_stop_pct') or 99) < 5 else '' }}">
                    ({{ '%.1f' % pvn.dist_to_stop_pct if pvn.get('dist_to_stop_pct') is not none else '—' }}%)
                  </span></td></tr>
          <tr><td class="gray">目标</td>
              <td>{{ '$%.2f' % kl.target if kl.get('target') else '—' }}</td></tr>
          <tr><td class="gray">加仓</td>
              <td>{{ '$%.2f' % kl.flex_add if kl.get('flex_add') else '—' }}</td></tr>
          <tr><td class="gray">减仓</td>
              <td>{{ '$%.2f' % kl.flex_reduce if kl.get('flex_reduce') else '—' }}</td></tr>
          <tr><td class="gray">论点</td>
              <td class="{{ 'red' if pvn.get('thesis_signal') == 'breach' else 'yellow' if pvn.get('thesis_signal') == 'warning' else 'green' }}">
                {{ pvn.get('thesis_signal', '—') }}</td></tr>
          <tr><td class="gray">入场窗口</td>
              <td>{{ pvn.get('entry_go_status', '—') }}</td></tr>
        </table>
      </div>
    </div>
    {% if it.get('action_now') %}
    <div style="margin-top:0.5em;" class="alert-info">
      <b>action_now:</b> {{ it.action_now.get('conclusion', '—') }}
      — {{ it.action_now.get('note', '') }}
    </div>
    {% endif %}
  </div>
  {% endfor %}
</div><!-- end tab-intraday -->

<!-- ═══════════════ TAB: 事件日志 ═══════════════ -->
<div id="tab-events" class="tab-pane">
  <div class="card">
    <h2>今日 LLM 触发事件</h2>
    {% if events %}
    <table>
      <tr><th>时间</th><th>标的</th><th>事件</th><th>行动结论</th><th>说明</th></tr>
      {% for ev in events %}
      {% set meta = ev.get('meta', {}) %}
      {% set ac = ev.get('action_now') or {} %}
      <tr>
        <td>{{ ev.get('ts', '—') }}</td>
        <td><b>{{ meta.get('sym', '—') }}</b></td>
        <td>
          {% set trigger = meta.get('llm_trigger', '—') %}
          <span class="badge {{ 'badge-red' if trigger in ['hard_stop_breach','vix_spike'] else 'badge-yellow' }}">
            {{ trigger }}
          </span>
        </td>
        <td>{{ ac.get('conclusion', '—') }}</td>
        <td class="gray">{{ ac.get('note', '—') }}</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <div class="gray">今日暂无 LLM 触发事件</div>
    {% endif %}
  </div>
</div><!-- end tab-events -->

<!-- ═══════════════ TAB: 盘后复盘 ═══════════════ -->
<div id="tab-postmarket" class="tab-pane">
  {% if postmarket_day and postmarket_day.get('portfolio') %}
  {% set port = postmarket_day.portfolio %}
  <div class="card">
    <h2>今日组合表现</h2>
    <div class="grid-3">
      <div>
        <div class="gray">加权日收益</div>
        <div class="{{ 'green' if (port.total_day_ret_pct or 0) >= 0 else 'red' }}">
          {{ '%+.2f' % port.total_day_ret_pct if port.total_day_ret_pct is not none else '—' }}%
        </div>
      </div>
      <div>
        <div class="gray">最佳</div>
        <div class="green">{{ port.best_performer or '—' }}</div>
      </div>
      <div>
        <div class="gray">最差</div>
        <div class="red">{{ port.worst_performer or '—' }}</div>
      </div>
    </div>
  </div>
  {% endif %}

  {% if postmarket_day and postmarket_day.get('llm_review') %}
  <div class="card">
    <h2>LLM 复盘</h2>
    <p style="white-space:pre-wrap;">{{ postmarket_day.llm_review }}</p>
  </div>
  {% endif %}

  <!-- 待确认建议 -->
  {% set has_suggestions = false %}
  {% for sym in symbols %}
  {% set pm_sym_path = 'findings/postmarket_summary_' + date + '_' + sym + '.json' %}
  {% endfor %}
  {% if postmarket_day and postmarket_day.get('pending_suggestions_count', 0) > 0 %}
  <div class="card">
    <h2>⏳ 待确认建议 ({{ postmarket_day.pending_suggestions_count }} 条)</h2>
    <div class="gray">请在次日盘前运行时逐条确认</div>
  </div>
  {% endif %}

  {% if postmarket_day and postmarket_day.get('tomorrow_risk_calendar') %}
  <div class="card">
    <h2>📅 明日风险日历</h2>
    {% for ev in postmarket_day.tomorrow_risk_calendar %}
    <div class="alert-yellow">{{ ev }}</div>
    {% endfor %}
  </div>
  {% endif %}
</div><!-- end tab-postmarket -->

<script>
function showTab(name) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}
</script>
</body>
</html>
```

- [ ] **Step 2.2：冒烟测试（用现有数据）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 agents/dashboard_writer.py
ls reports/daily_dashboard_*.html 2>/dev/null | tail -1
```

预期：生成 HTML 文件，无报错。

- [ ] **Step 2.3：Commit**

```bash
git add templates/daily_dashboard.html.j2 agents/dashboard_writer.py
git commit -m "feat: add daily_dashboard.html.j2 — 4-tab trading dashboard with auto-refresh"
```

---

## Task 3：poll.py 集成 + CHANGELOG

**Files:**
- Modify: `agents/poll.py`（在 session_state updater 钩子后追加 3 行）

---

- [ ] **Step 3.1：在 session_state 钩子之后追加**

在 poll.py 中找到 `# ── session_state missed_alerts 更新` 块的最后一个 `except Exception: pass`，追加：

```python
    # ── daily_dashboard HTML 生成 ────────────────────────────────────────────
    try:
        from agents.dashboard_writer import write_dashboard
        write_dashboard(_snap_date)
    except Exception:
        pass
```

- [ ] **Step 3.2：冒烟测试**

```bash
/tool/pandora/bin/python3.12 -c "from agents.dashboard_writer import write_dashboard; print('import OK')"
```

- [ ] **Step 3.3：更新 CHANGELOG.md**

顶部追加：

```
## 2026-05-20 daily_dashboard 实施完成

### 新建文件
- `agents/dashboard_writer.py` — 读取所有 B 级 JSON，构建 Jinja2 上下文
- `templates/daily_dashboard.html.j2` — 4-Tab 交易 Dashboard（总览/盘中/事件/盘后），meta-refresh 30s
- `tests/test_dashboard_writer.py` — 4个单元测试

### 修改文件
- `agents/poll.py` — 每轮末尾调用 write_dashboard()

---
```

- [ ] **Step 3.4：Commit**

```bash
git add agents/poll.py CHANGELOG.md
git commit -m "feat: integrate dashboard_writer into poll.py + CHANGELOG"
```
