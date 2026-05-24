# trading-day 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/daily_plan_writer.py`，实现 spec 格式的 `daily_plan_{date}.json`（Node 0 生成）和 session_state 的 missed_alerts/gtc_status/next_action 扩展字段更新（每轮 poll 调用）。

**Architecture:** `daily_plan_writer.py` 提供两类函数：(1) Node 0 生成 daily_plan（读取 premarket_summary + positions + postmarket）; (2) session_state 实时更新（读 alert_queue → missed_alerts、gtc_status、next_action）。poll.py 在现有 intraday_snapshot 钩子后再加一个轻量调用。旧 `daily_plan.py` 保留不动。

**Tech Stack:** Python 3.12, json

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/daily_plan_writer.py` | 新建 | Node 0 生成 + session_state 更新函数 |
| `agents/poll.py` | 修改（intraday 钩子后追加 3 行）| 每轮调用 update_session_state_from_alerts |
| `tests/test_daily_plan_writer.py` | 新建 | 单元测试 |

---

## Task 1：daily_plan_writer — 核心纯函数

**Files:**
- Create: `agents/daily_plan_writer.py`
- Create: `tests/test_daily_plan_writer.py`

---

- [ ] **Step 1.1：写测试**

```python
# tests/test_daily_plan_writer.py
import sys, os, json, datetime
sys.path.insert(0, os.path.expanduser("~/stock_team"))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _make_premarket(tmp_path, sym, date, action_dec="enter", exit_dec=None):
    path = str(tmp_path / "findings" / f"premarket_summary_{date}_{sym}.json")
    entry = {"decision": action_dec, "entry_base": 100.0, "stop_loss": 95.0,
             "target_price": 110.0}
    exit_ = {"decision": exit_dec, "hard_stop": 95.0, "target_price": 110.0,
              "flex_add_level": 93.0, "flex_reduce_level": 108.0} if exit_dec else None
    _write(path, {
        "date": date, "sym": sym,
        "market_context": {"env": "顺风", "vix_level": 18.5, "macro_events_today": []},
        "entry": entry,
        "exit": exit_,
        "thesis": {"status": "intact"} if exit_ else None,
        "strategic_context": {"source": "premarket_inferred"},
        "post_open_adj": None,
    })
    return path


def _make_positions(tmp_path, sym, gtc_placed=True):
    path = str(tmp_path / "config" / "positions.json")
    _write(path, {
        "positions": {sym: {
            "cost": 100.0, "shares": 10, "date": "2026-05-12",
            "thesis_status": "intact",
            "gtc_stop_placed": gtc_placed, "gtc_stop_date": "2026-05-12",
        }},
        "_excluded": [],
    })
    return path


# ── action_now 规则 ──────────────────────────────────────────────────────

def test_action_now_exit_beats_entry():
    """exit=exit 优先于 entry=enter"""
    from agents.daily_plan_writer import compute_action_now
    result = compute_action_now(
        entry_decision="enter", exit_decision="exit",
        thesis_status="intact", is_held=True,
    )
    assert result == "exit"


def test_action_now_reduce_beats_enter():
    """exit=reduce 优先于 entry=enter"""
    from agents.daily_plan_writer import compute_action_now
    result = compute_action_now(
        entry_decision="enter", exit_decision="reduce",
        thesis_status="intact", is_held=True,
    )
    assert result == "reduce"


def test_action_now_no_position_pass():
    """无仓位 + entry=pass → pass"""
    from agents.daily_plan_writer import compute_action_now
    result = compute_action_now(
        entry_decision="pass", exit_decision=None,
        thesis_status=None, is_held=False,
    )
    assert result == "pass"


def test_action_now_held_intact_hold():
    """有仓 + entry=pass + thesis=intact → hold"""
    from agents.daily_plan_writer import compute_action_now
    result = compute_action_now(
        entry_decision="pass", exit_decision=None,
        thesis_status="intact", is_held=True,
    )
    assert result == "hold"


# ── gtc_status 规则 ──────────────────────────────────────────────────────

def test_compute_gtc_status_missing(tmp_path):
    """gtc_stop_placed=False → 在 missing 列表中"""
    from agents.daily_plan_writer import compute_gtc_status
    _make_positions(tmp_path, "NVDA", gtc_placed=False)
    status = compute_gtc_status(base_dir=str(tmp_path))
    assert "NVDA" in status["missing"]
    assert "NVDA" not in status["placed"]


def test_compute_gtc_status_placed(tmp_path):
    """gtc_stop_placed=True → 在 placed 列表中"""
    from agents.daily_plan_writer import compute_gtc_status
    _make_positions(tmp_path, "NVDA", gtc_placed=True)
    status = compute_gtc_status(base_dir=str(tmp_path))
    assert "NVDA" in status["placed"]
    assert "NVDA" not in status["missing"]


# ── compute_next_action ──────────────────────────────────────────────────

def test_next_action_red_alert_is_immediate():
    """missed_alerts 有 red → immediate"""
    from agents.daily_plan_writer import compute_next_action
    session_state = {
        "missed_alerts": [{"level": "red", "sym": "NVDA", "event": "hard_stop_breach",
                           "detail": "破止损"}],
        "gtc_status": {"missing": [], "placed": ["NVDA"]},
    }
    daily_plan = {"pending_suggestions_total": 0, "per_symbol": {}}
    result = compute_next_action(session_state, daily_plan, session_min=40)
    assert result["priority"] == "immediate"


def test_next_action_gtc_missing_is_immediate(tmp_path):
    """gtc_status.missing 非空 → immediate"""
    from agents.daily_plan_writer import compute_next_action
    session_state = {
        "missed_alerts": [],
        "gtc_status": {"missing": ["NVDA"], "placed": []},
    }
    daily_plan = {"pending_suggestions_total": 0, "per_symbol": {}}
    result = compute_next_action(session_state, daily_plan, session_min=40)
    assert result["priority"] == "immediate"


def test_next_action_normal_fallback():
    """无紧急情况 → normal"""
    from agents.daily_plan_writer import compute_next_action
    session_state = {
        "missed_alerts": [],
        "gtc_status": {"missing": [], "placed": ["NVDA"]},
    }
    daily_plan = {"pending_suggestions_total": 0, "per_symbol": {}}
    result = compute_next_action(session_state, daily_plan, session_min=40)
    assert result["priority"] == "normal"


# ── build_daily_plan ─────────────────────────────────────────────────────

def test_build_daily_plan_schema(tmp_path):
    """build_daily_plan 返回所有顶层字段"""
    from agents.daily_plan_writer import build_daily_plan
    date = "2026-05-20"
    _make_premarket(tmp_path, "NVDA", date, action_dec="enter")
    _make_positions(tmp_path, "NVDA")

    plan = build_daily_plan(date, symbols=["NVDA"], base_dir=str(tmp_path))
    required = {"date", "generated_at", "market_context", "symbols_today",
                "per_symbol", "schedule", "gtc_required", "pending_suggestions_total"}
    assert required == set(plan.keys()), f"缺少: {required - set(plan.keys())}"
    assert "NVDA" in plan["per_symbol"]
    assert plan["per_symbol"]["NVDA"]["action_now"] == "enter"
```

- [ ] **Step 1.2：运行测试，确认 FAIL**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_daily_plan_writer.py -v 2>&1 | head -15
```

- [ ] **Step 1.3：创建 agents/daily_plan_writer.py**

```python
"""
日计划写入模块 — daily_plan_writer.py
Node 0 生成 daily_plan_{date}.json（spec 格式）。
提供 session_state 实时更新函数（每轮 poll 调用）。

后台零 LLM 调用。

用法（Node 0）:
  python3.12 agents/daily_plan_writer.py [SYM1 SYM2 ...]
"""
import json, os, sys
from datetime import datetime, timezone, date as _date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE     = os.path.expanduser("~/stock_team")
FIND_DIR = os.path.join(BASE, "findings")
CFG_DIR  = os.path.join(BASE, "config")

NODE_NAMES = {
    0: "晨间准备",  1: "盘前",     2: "开盘观察",
    3: "盘中主动期", 4: "入场执行", 5: "持仓管理", 6: "收盘复盘",
}
NODE_WINDOWS = {
    0: "08:00-09:00", 1: "09:00-09:25", 2: "09:30-10:00",
    3: "10:00-10:30", 4: "10:30-16:00", 5: "16:00-16:30", 6: "16:30+",
}


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── 纯计算函数 ─────────────────────────────────────────────────────────────

def compute_action_now(
    entry_decision: str | None,
    exit_decision: str | None,
    thesis_status: str | None,
    is_held: bool,
) -> str:
    """
    规则推导今日行动（exit 优先于 entry）。
    返回: "exit|reduce|enter|watch|hold|pass"
    """
    if is_held and exit_decision == "exit":
        return "exit"
    if is_held and exit_decision == "reduce":
        return "reduce"
    if entry_decision == "enter":
        return "enter"
    if entry_decision == "watch":
        return "watch"
    if is_held and thesis_status == "intact":
        return "hold"
    return "pass"


def compute_gtc_status(base_dir: str = BASE) -> dict:
    """读 positions.json，返回 GTC 挂单状态（_excluded 标的跳过）"""
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    excluded = set(pos_data.get("_excluded", []))
    placed, missing = [], []
    for sym, pos in pos_data.get("positions", {}).items():
        if sym in excluded:
            continue
        if pos.get("gtc_stop_placed"):
            placed.append(sym)
        else:
            missing.append(sym)
    return {"placed": placed, "missing": missing}


def compute_next_action(
    session_state: dict, daily_plan: dict, session_min: int
) -> dict:
    """
    规则推导用户上线时的第一件事（优先级从高到低）。
    返回 {"priority": "immediate|normal", "instruction": "string"}
    """
    missed = session_state.get("missed_alerts", [])
    gtc    = session_state.get("gtc_status", {})
    ps_total = daily_plan.get("pending_suggestions_total", 0)

    if any(a.get("level") == "red" for a in missed):
        return {"priority": "immediate",
                "instruction": "有 🔴 紧急事件待处理，先看 missed_alerts"}

    missing_gtc = gtc.get("missing", [])
    if missing_gtc:
        sym = missing_gtc[0]
        return {"priority": "immediate",
                "instruction": f"{sym} GTC 止损单未挂，请立即处理"}

    # entry_go 触发（10:00-10:30）
    if 30 <= session_min <= 60:
        per_sym = daily_plan.get("per_symbol", {})
        for sym, data in per_sym.items():
            if data.get("entry_go_status") == "go":
                return {"priority": "immediate",
                        "instruction": f"{sym} entry_go 已触发，确认是否入场"}

    if ps_total > 0:
        return {"priority": "normal",
                "instruction": f"有 {ps_total} 条昨日建议待确认"}

    node = session_state.get("node", 0)
    node_name = NODE_NAMES.get(node, str(node))
    return {"priority": "normal",
            "instruction": f"当前节点 {node_name}，按计划继续"}


# ── daily_plan 构建 ─────────────────────────────────────────────────────────

def _get_key_levels(pm: dict) -> dict:
    """从 premarket_summary 提取关键价位节点"""
    entry = pm.get("entry") or {}
    exit_ = pm.get("exit") or {}
    adj   = pm.get("post_open_adj") or {}

    def _pick(adj_key, *fallbacks):
        v = adj.get(adj_key)
        if v is not None:
            return v
        for k in fallbacks:
            val = exit_.get(k) or entry.get(k)
            if val is not None:
                return val
        return None

    return {
        "entry_base":  _pick("entry_base_adj",  "entry_base"),
        "hard_stop":   _pick("hard_stop_adj",   "hard_stop",    "stop_loss"),
        "flex_add":    _pick("flex_add_adj",     "flex_add_level"),
        "flex_reduce": _pick("flex_reduce_adj",  "flex_reduce_level"),
        "target":      _pick("target_adj",       "target_price"),
    }


def _count_pending_suggestions(sym: str, date: str, find_dir: str) -> int:
    """读昨日 postmarket_summary，统计 confirmed=null 的建议数"""
    try:
        yesterday = (_date.fromisoformat(date) - timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        return 0
    pm_path = os.path.join(find_dir, f"postmarket_summary_{yesterday}_{sym}.json")
    data = _load(pm_path)
    return sum(1 for s in data.get("next_day", {}).get("suggestions", [])
               if s.get("confirmed") is None)


def _check_memo_valid(sym: str, base_dir: str) -> bool:
    """检查 strategic_memo 是否未过期"""
    memo = _load(os.path.join(base_dir, f"strategic_memo_{sym}.json"))
    if not memo:
        return True   # 无 memo 视为有效（不产生过期警告）
    valid_until = memo.get("outlook", {}).get("valid_until", "")
    if not valid_until or valid_until in ("next_earnings", "next_catalyst_event"):
        return True
    try:
        return _date.fromisoformat(valid_until) >= _date.today()
    except Exception:
        return True


def build_daily_plan(date: str, symbols: list[str] | None = None,
                     base_dir: str = BASE) -> dict:
    """构建 spec 格式的 daily_plan dict（Node 0 调用）"""
    find_dir = os.path.join(base_dir, "findings")
    cfg_dir  = os.path.join(base_dir, "config")

    if symbols is None:
        cfg = _load(os.path.join(cfg_dir, "poll_config.json"))
        pos_data = _load(os.path.join(cfg_dir, "positions.json"))
        symbols = list({
            *cfg.get("default_symbols", []),
            *[s for s in pos_data.get("positions", {}) if not s.startswith("_")]
        })

    # 读取第一个 premarket_summary 获取 market_context（所有标的共用同一大盘）
    market_context = {"env": "中性", "vix_level": None, "macro_events": [],
                      "tomorrow_risk": []}
    for sym in symbols:
        pm_path = os.path.join(find_dir, f"premarket_summary_{date}_{sym}.json")
        pm = _load(pm_path)
        if pm:
            mc = pm.get("market_context", {})
            market_context["env"]         = mc.get("env", "中性")
            market_context["vix_level"]   = mc.get("vix_level")
            market_context["macro_events"] = mc.get("macro_events_today", [])
            break

    # 读昨日 postmarket per-day 获取 tomorrow_risk
    try:
        yesterday = (_date.fromisoformat(date) - timedelta(days=1)).strftime("%Y-%m-%d")
        pm_day = _load(os.path.join(find_dir, f"postmarket_summary_{yesterday}.json"))
        market_context["tomorrow_risk"] = pm_day.get("tomorrow_risk_calendar", [])
    except Exception:
        pass

    # per_symbol
    per_symbol = {}
    gtc_required = []
    pending_total = 0

    pos_data = _load(os.path.join(cfg_dir, "positions.json"))
    positions = pos_data.get("positions", {})
    excluded  = set(pos_data.get("_excluded", []))

    for sym in symbols:
        pm_path = os.path.join(find_dir, f"premarket_summary_{date}_{sym}.json")
        pm = _load(pm_path)

        entry  = pm.get("entry") or {}
        exit_  = pm.get("exit") or {}
        thesis = pm.get("thesis") or {}
        adj    = pm.get("post_open_adj") or {}
        sc     = pm.get("strategic_context") or {}

        is_held = exit_ is not None and bool(exit_)
        entry_dec = entry.get("decision", "pass")
        exit_dec  = exit_.get("decision") if is_held else None
        th_status = thesis.get("status") if is_held else None

        action = compute_action_now(entry_dec, exit_dec, th_status, is_held)
        levels = _get_key_levels(pm) if pm else {"entry_base": None, "hard_stop": None,
                                                   "flex_add": None, "flex_reduce": None,
                                                   "target": None}

        entry_go = adj.get("entry_go")
        if entry_go is True:
            ego_status = "go"
        elif entry_go is False:
            ego_status = "abort"
        elif adj:
            ego_status = "pending"
        else:
            ego_status = None

        pending = _count_pending_suggestions(sym, date, find_dir)
        pending_total += pending

        memo_valid = _check_memo_valid(sym, base_dir)

        per_symbol[sym] = {
            "premarket_summary_path": f"findings/premarket_summary_{date}_{sym}.json",
            "action_now":             action,
            "key_levels":             levels,
            "entry_go_status":        ego_status,
            "pending_suggestions":    pending,
            "memo_valid":             memo_valid,
        }

        # GTC 警示
        pos = positions.get(sym, {})
        if sym not in excluded and not pos.get("gtc_stop_placed"):
            gtc_required.append(sym)

    # schedule
    schedule = []
    for node in range(7):
        name   = NODE_NAMES.get(node, str(node))
        window = NODE_WINDOWS.get(node, "")
        status = "auto" if node >= 4 else "pending"
        schedule.append({"node": node, "name": name, "window": window,
                          "status": status, "summary": None})

    return {
        "date":                   date,
        "generated_at":           datetime.now(timezone.utc).isoformat(),
        "market_context":         market_context,
        "symbols_today":          symbols,
        "per_symbol":             per_symbol,
        "schedule":               schedule,
        "gtc_required":           gtc_required,
        "pending_suggestions_total": pending_total,
    }


def write_daily_plan(date: str, data: dict, base_dir: str = BASE) -> str:
    path = os.path.join(base_dir, f"daily_plan_{date}.json")
    _save(path, data)
    return path


# ── session_state 更新函数（每轮 poll 调用）──────────────────────────────────

def update_session_state_from_alerts(date: str, base_dir: str = BASE):
    """
    从 alert_queue 过滤 time > last_online_at 的条目写入 missed_alerts。
    保留全量 alert_queue，missed_alerts 是只读视图。
    """
    state_path = os.path.join(base_dir, "learning", f"session_state_{date}.json")
    state = _load(state_path)
    if not state:
        return

    last_online = state.get("last_online_at", "00:00")
    alert_queue = state.get("alert_queue", [])

    # 过滤：只取 last_online_at 之后的 🔴🟡 事件
    new_missed = []
    for alert in alert_queue:
        t = alert.get("time", "00:00")
        if t > last_online:
            level = "red" if alert.get("type", "").endswith("broken") else "yellow"
            new_missed.append({
                "time":   t,
                "level":  level,
                "sym":    alert.get("symbol", ""),
                "event":  alert.get("type", ""),
                "detail": alert.get("message", "")[:60],
            })

    # 只追加新的（避免重复）
    existing_times = {m["time"] + m.get("sym", "") for m in state.get("missed_alerts", [])}
    to_add = [m for m in new_missed
              if m["time"] + m.get("sym", "") not in existing_times]
    if to_add:
        state.setdefault("missed_alerts", []).extend(to_add)
        _save(state_path, state)


def mark_user_online(date: str, base_dir: str = BASE):
    """用户上线时调用：记录 last_online_at，清空 missed_alerts"""
    state_path = os.path.join(base_dir, "learning", f"session_state_{date}.json")
    state = _load(state_path) or {}
    now = datetime.now().strftime("%H:%M")
    state["last_online_at"] = now
    state["missed_alerts"]  = []   # 上线后清空
    # 更新 gtc_status
    state["gtc_status"] = compute_gtc_status(base_dir=base_dir)
    _save(state_path, state)


def main():
    date_str = _date.today().strftime("%Y-%m-%d")
    syms = sys.argv[1:] if len(sys.argv) > 1 else None
    print(f"\n生成日计划 {date_str}\n")
    plan = build_daily_plan(date_str, symbols=syms)
    path = write_daily_plan(date_str, plan)
    print(f"  ✅ {os.path.basename(path)}")
    print(f"  today symbols: {plan['symbols_today']}")
    gtc = plan.get("gtc_required", [])
    if gtc:
        print(f"  ⚠️ GTC 未挂: {gtc}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 1.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_daily_plan_writer.py -v
```

预期：全部 PASS

- [ ] **Step 1.5：Commit**

```bash
git add agents/daily_plan_writer.py tests/test_daily_plan_writer.py
git commit -m "feat: add daily_plan_writer.py — daily_plan schema + session_state updater"
```

---

## Task 2：poll.py 集成（每轮末尾追加 3 行）

**Files:**
- Modify: `agents/poll.py`（在 intraday_snapshot 钩子块之后）

---

- [ ] **Step 2.1：找到插入位置**

在 poll.py 中搜索 `# ── intraday_snapshot`，找到该块的最后一个 `except Exception: pass`，紧接其后追加：

```python
    # ── session_state missed_alerts 更新（每轮同步，纯脚本）──────────────────
    try:
        from agents.daily_plan_writer import update_session_state_from_alerts
        update_session_state_from_alerts(_snap_date)
    except Exception:
        pass
```

- [ ] **Step 2.2：冒烟测试**

```bash
/tool/pandora/bin/python3.12 -c "
from agents.daily_plan_writer import (
    compute_action_now, compute_gtc_status, compute_next_action,
    build_daily_plan, update_session_state_from_alerts
)
print('import OK')
"
```

- [ ] **Step 2.3：运行回归测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_daily_plan_writer.py tests/test_session_manager.py -v --tb=short 2>&1 | tail -10
```

预期：全部 PASS，session_manager 无回归

- [ ] **Step 2.4：Commit**

```bash
git add agents/poll.py
git commit -m "feat: add session_state missed_alerts update hook to poll.py"
```

---

## Task 3：CHANGELOG 更新

- [ ] **Step 3.1：更新 CHANGELOG.md**

顶部追加：

```
## 2026-05-20 trading-day daily_plan_writer 实施完成

### 新建文件
- `agents/daily_plan_writer.py` — spec 格式 daily_plan 生成 + session_state missed_alerts 更新
- `tests/test_daily_plan_writer.py` — 12个单元测试

### 修改文件
- `agents/poll.py` — 每轮末尾调用 update_session_state_from_alerts()

---
```

- [ ] **Step 3.2：Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for trading-day implementation"
```
