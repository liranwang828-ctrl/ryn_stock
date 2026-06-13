# postmarket_summary 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/postmarket_data_collector.py` 和 `agents/postmarket_summary.py`，在 16:00 ET 后自动生成结构化复盘文件（execution/performance/signal_accuracy + 12 类建议），同时新建 `agents/suggestion_applier.py` 支持用户确认建议后写回源文件。

**Architecture:** 分三层：`postmarket_data_collector.py`（纯规则计算，可单元测试）→ `postmarket_summary.py`（组合数据 + 写文件 + 触发 harvest_agent）→ `suggestion_applier.py`（确认建议写回）。LLM 生成部分（learning_notes/llm_review）在初始版本中为存根（空字符串），后续单独接入 Claude API。

**Tech Stack:** Python 3.12, json, yfinance（获取当日开收盘价）

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/postmarket_data_collector.py` | 新建 | 纯规则计算：execution/performance/signal_accuracy/suggestions |
| `agents/postmarket_summary.py` | 新建 | 组合写文件：per-stock + per-day JSON |
| `agents/suggestion_applier.py` | 新建 | 建议确认写回：positions.json/config 等 |
| `tests/test_postmarket_summary.py` | 新建 | 单元测试，全用 tmp_path，无网络 |

---

## Task 1：postmarket_data_collector — 核心计算函数

**Files:**
- Create: `agents/postmarket_data_collector.py`
- Create: `tests/test_postmarket_summary.py`

---

- [ ] **Step 1.1：写测试**

```python
# tests/test_postmarket_summary.py
import sys, os, json, datetime
sys.path.insert(0, os.path.expanduser("~/stock_team"))


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _make_premarket(tmp_path, sym, date, entry_go=True, scene="B"):
    """构造最小合法 premarket_summary"""
    path = str(tmp_path / "findings" / f"premarket_summary_{date}_{sym}.json")
    _write_json(path, {
        "date": date, "sym": sym,
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0,
                  "entry_conditions": ["A"], "cancel_conditions": []},
        "exit": {"hard_stop": 95.0, "target_price": 110.0,
                 "flex_add_level": 93.0, "flex_reduce_level": 108.0},
        "thesis": {"status": "intact", "today_falsification": []},
        "stock_snapshot": {"pred_scene": scene, "catalyst_strength": 1},
        "post_open_adj": {"entry_go": entry_go, "scene_confirmed": scene,
                          "entry_base_adj": None, "hard_stop_adj": None},
        "strategic_context": {"source": "premarket_inferred",
                              "strategic_stance": "hold", "unified_confidence": 3},
    })
    return path


def _make_intraday(tmp_path, sym, date, thesis_signal="intact"):
    """构造最小合法 intraday_snapshot（最后一条 JSONL）"""
    path = str(tmp_path / "findings" / f"intraday_snapshot_{date}_{sym}.jsonl")
    record = {
        "ts": "15:58:00",
        "meta": {"date": date, "sym": sym, "session_min": 388,
                 "llm_triggered": False, "llm_trigger": None,
                 "cooldown_until": None, "post_open_calibrated": True},
        "price_now": {"price": 105.0, "gate_status": "通过",
                      "master_avg": 6.5, "master_consensus": "buy"},
        "plan_vs_now": {"thesis_signal": thesis_signal, "entry_go_status": "go"},
        "node_snapshot": {}, "action_now": None,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _make_positions(tmp_path, sym, shares=10, cost=100.0, date="2026-05-12"):
    path = str(tmp_path / "config" / "positions.json")
    _write_json(path, {
        "positions": {sym: {
            "cost": cost, "shares": shares, "date": date,
            "thesis_status": "intact", "thesis_updated": date,
        }},
        "_excluded": [],
    })
    return path


# ── 测试 build_execution ──────────────────────────────────────────────────

def test_build_execution_entry_triggered(tmp_path):
    """entry_go=True → plan_entry_triggered=True"""
    from agents.postmarket_data_collector import build_execution
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date, entry_go=True)
    _make_intraday(tmp_path, "TEST", date)
    result = build_execution("TEST", date, base_dir=str(tmp_path))
    assert result["plan_entry_triggered"] is True


def test_build_execution_no_intraday(tmp_path):
    """无 intraday 文件 → plan_exit_triggered=None"""
    from agents.postmarket_data_collector import build_execution
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date)
    # 不创建 intraday 文件
    result = build_execution("TEST", date, base_dir=str(tmp_path))
    assert result["plan_exit_triggered"] is None


# ── 测试 build_signal_accuracy ─────────────────────────────────────────────

def test_signal_accuracy_consensus_correct(tmp_path):
    """master_consensus=buy + day_ret > 0 → master_consensus_correct=True"""
    from agents.postmarket_data_collector import build_signal_accuracy
    date = "2026-05-20"
    pm_path = _make_premarket(tmp_path, "TEST", date, scene="B")
    it_path = _make_intraday(tmp_path, "TEST", date)
    result = build_signal_accuracy(
        sym="TEST", date=date,
        day_ret_pct=1.5,
        base_dir=str(tmp_path),
    )
    assert result["master_consensus_correct"] is True  # consensus=buy, ret>0


def test_signal_accuracy_pred_scene_match(tmp_path):
    """pred_scene == actual_scene → pred_scene_correct=True"""
    from agents.postmarket_data_collector import build_signal_accuracy
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date, scene="B")
    _make_intraday(tmp_path, "TEST", date)
    result = build_signal_accuracy("TEST", date, day_ret_pct=0.5,
                                   base_dir=str(tmp_path))
    assert result["pred_scene_correct"] is True
    assert result["actual_scene"] == "B"


# ── 测试 generate_suggestions ──────────────────────────────────────────────

def test_generate_suggestions_lesson_always_present():
    """lesson_record 每日必有"""
    from agents.postmarket_data_collector import generate_suggestions
    suggs = generate_suggestions(
        sym="TEST", date="2026-05-20",
        execution={"followed_plan": "yes"},
        performance={"day_ret_pct": 0.5, "thesis_days": 5, "vs_stop_pct": 5.0},
        signal_accuracy={},
    )
    types = [s["type"] for s in suggs]
    assert "lesson_record" in types


def test_generate_suggestions_thesis_status_on_breach():
    """thesis_signal=breach 终盘 → thesis_status 建议"""
    from agents.postmarket_data_collector import generate_suggestions
    suggs = generate_suggestions(
        sym="TEST", date="2026-05-20",
        execution={"followed_plan": "no"},
        performance={"day_ret_pct": -3.5, "thesis_days": 5, "vs_stop_pct": -1.0},
        signal_accuracy={"thesis_signal_correct": True},
    )
    types = [s["type"] for s in suggs]
    assert "thesis_status" in types
```

- [ ] **Step 1.2：运行测试，确认 FAIL（ImportError）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_postmarket_summary.py -v 2>&1 | head -15
```

- [ ] **Step 1.3：创建 agents/postmarket_data_collector.py**

```python
"""
盘后数据收集模块 — postmarket_data_collector.py
纯规则计算 execution / performance / signal_accuracy / suggestions。
无 LLM 调用，全部可单元测试。

用法：由 postmarket_summary.py 调用，不直接运行。
"""
import json, os
from datetime import datetime, date as _date, timezone

BASE     = os.path.expanduser("~/stock_team")
FIND_DIR = os.path.join(BASE, "findings")
CFG_DIR  = os.path.join(BASE, "config")


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _read_last_jsonl(path: str) -> dict | None:
    """读取 JSONL 文件最后一条，文件不存在或为空时返回 None"""
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


# ── build_execution ────────────────────────────────────────────────────────

def build_execution(sym: str, date: str, base_dir: str = BASE) -> dict:
    """
    读取 premarket_summary + intraday_snapshot，计算今日执行情况。
    """
    find_dir = os.path.join(base_dir, "findings")
    pm = _load(os.path.join(find_dir, f"premarket_summary_{date}_{sym.upper()}.json"))
    adj = pm.get("post_open_adj") or {}

    # plan_entry_triggered：来自 post_open_adj.entry_go
    entry_go = adj.get("entry_go")
    plan_entry_triggered = bool(entry_go) if entry_go is not None else None

    # plan_exit_triggered：读 intraday_snapshot 末条的 thesis_signal
    snap_path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym.upper()}.jsonl")
    snap_last = _read_last_jsonl(snap_path)
    plan_exit_triggered = None
    if snap_last:
        ts = snap_last.get("plan_vs_now", {}).get("thesis_signal")
        plan_exit_triggered = ts == "breach"

    return {
        "plan_entry_triggered": plan_entry_triggered,
        "actual_entry":         None,    # 由 translator.py 记录，此处暂为 null
        "plan_exit_triggered":  plan_exit_triggered,
        "actual_exit":          None,
        "followed_plan":        "na",
        "deviation_note":       "",
    }


# ── build_performance ──────────────────────────────────────────────────────

def build_performance(sym: str, date: str, base_dir: str = BASE) -> dict:
    """
    计算今日损益和持仓天数。
    open_price / close_price 从 yfinance 获取（若失败则返回 null）。
    """
    find_dir = os.path.join(base_dir, "findings")
    pm   = _load(os.path.join(find_dir, f"premarket_summary_{date}_{sym.upper()}.json"))
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    pos  = pos_data.get("positions", {}).get(sym.upper(), {})

    hard_stop  = (pm.get("exit") or {}).get("hard_stop")
    target     = (pm.get("exit") or {}).get("target_price") or \
                 (pm.get("entry") or {}).get("target_price")

    entry_date_str = pos.get("date", date)
    try:
        entry_date = _date.fromisoformat(entry_date_str)
        today_date = _date.fromisoformat(date)
        days_held  = (today_date - entry_date).days
    except Exception:
        days_held  = 0

    thesis_updated_str = pos.get("thesis_updated", date)
    try:
        thesis_date = _date.fromisoformat(thesis_updated_str)
        today_date2 = _date.fromisoformat(date)
        thesis_days = (today_date2 - thesis_date).days
    except Exception:
        thesis_days = 0

    # 尝试获取 yfinance 价格（失败时返回 null）
    open_price = close_price = day_ret_pct = None
    try:
        import yfinance as yf
        ticker = yf.Ticker(sym.upper())
        hist   = ticker.history(period="2d")
        if not hist.empty and len(hist) >= 1:
            row        = hist.iloc[-1]
            open_price = round(float(row["Open"]), 2)
            close_price= round(float(row["Close"]), 2)
            if open_price and open_price > 0:
                day_ret_pct = round((close_price - open_price) / open_price * 100, 2)
    except Exception:
        pass

    vs_target_pct = None
    if close_price is not None and target:
        vs_target_pct = round((close_price - target) / target * 100, 2)

    vs_stop_pct = None
    if close_price is not None and hard_stop:
        vs_stop_pct = round((close_price - hard_stop) / close_price * 100, 2)

    return {
        "open_price":   open_price,
        "close_price":  close_price,
        "day_ret_pct":  day_ret_pct,
        "vs_target_pct": vs_target_pct,
        "vs_stop_pct":   vs_stop_pct,
        "days_held":    days_held,
        "thesis_days":  thesis_days,
    }


# ── build_signal_accuracy ──────────────────────────────────────────────────

def build_signal_accuracy(sym: str, date: str, day_ret_pct: float | None,
                           base_dir: str = BASE) -> dict:
    """
    纯规则推导今日各信号准确性（全部 B 级，无 LLM）。
    """
    find_dir = os.path.join(base_dir, "findings")
    pm  = _load(os.path.join(find_dir, f"premarket_summary_{date}_{sym.upper()}.json"))
    adj = pm.get("post_open_adj") or {}

    # pred_scene / actual_scene
    pred_scene   = (pm.get("stock_snapshot") or {}).get("pred_scene")
    actual_scene = adj.get("scene_confirmed")
    pred_scene_correct = (pred_scene == actual_scene) if (pred_scene and actual_scene) else None

    # intraday 末条
    snap_path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym.upper()}.jsonl")
    snap_last = _read_last_jsonl(snap_path)
    master_consensus = None
    if snap_last:
        master_consensus = snap_last.get("price_now", {}).get("master_consensus")

    # master_consensus_correct
    master_correct = None
    if master_consensus and day_ret_pct is not None:
        if master_consensus == "buy":
            master_correct = day_ret_pct > 0
        elif master_consensus == "no_buy":
            master_correct = day_ret_pct < 0

    # gate_correct：gate 通过且 entry_go=True → day_ret > 0
    gate_correct = None
    entry_go_status = (snap_last.get("plan_vs_now", {}).get("entry_go_status")
                       if snap_last else None)
    gate_status = (snap_last.get("price_now", {}).get("gate_status")
                   if snap_last else None)
    if gate_status == "通过" and entry_go_status == "go" and day_ret_pct is not None:
        gate_correct = day_ret_pct > 0

    # thesis_signal_correct：breach 是否真的对应大跌（< -2%）
    thesis_signal = (snap_last.get("plan_vs_now", {}).get("thesis_signal")
                     if snap_last else None)
    thesis_sig_correct = None
    if thesis_signal == "breach" and day_ret_pct is not None:
        thesis_sig_correct = day_ret_pct < -2.0

    # entry_go_outcome
    entry_go_outcome = None
    if adj.get("entry_go") is True and day_ret_pct is not None:
        if day_ret_pct > 1.0:
            entry_go_outcome = "profitable"
        elif day_ret_pct >= -1.0:
            entry_go_outcome = "break_even"
        else:
            entry_go_outcome = "loss"
    elif adj.get("entry_go") is False:
        entry_go_outcome = "not_triggered"

    return {
        "pred_scene_correct":       pred_scene_correct,
        "actual_scene":             actual_scene,
        "master_consensus_correct": master_correct,
        "gate_correct":             gate_correct,
        "thesis_signal_correct":    thesis_sig_correct,
        "entry_go_outcome":         entry_go_outcome,
    }


# ── generate_suggestions ───────────────────────────────────────────────────

def generate_suggestions(
    sym: str, date: str,
    execution: dict,
    performance: dict,
    signal_accuracy: dict,
) -> list[dict]:
    """
    规则驱动生成 12 类建议草稿（不依赖 LLM）。
    优先级：breach > warning > low。
    """
    suggs = []

    day_ret     = performance.get("day_ret_pct", 0.0) or 0.0
    thesis_days = performance.get("thesis_days", 0) or 0
    vs_stop     = performance.get("vs_stop_pct")
    followed    = execution.get("followed_plan", "na")
    ts_correct  = signal_accuracy.get("thesis_signal_correct")

    # 1. thesis_status：今日大跌（< -3%）或论点破裂信号
    if day_ret < -3.0 or ts_correct is True:
        suggs.append({
            "type": "thesis_status",
            "priority": "high",
            "description": f"{sym} 今日跌幅 {day_ret:.1f}%，建议重新评估论点状态",
            "proposed_value": {"new_status": "weakening"},
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 2. stop_move：今日明显上涨（> 3%）且利润充足
    if day_ret > 3.0 and vs_stop is not None and vs_stop > 8.0:
        suggs.append({
            "type": "stop_move",
            "priority": "medium",
            "description": f"{sym} 今日涨幅 {day_ret:.1f}%，考虑上移止损锁定利润",
            "proposed_value": {"new_stop": None},  # 由用户填写具体价位
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 3. time_stop_eval：thesis_days 超过 14 天
    if thesis_days > 14:
        suggs.append({
            "type": "time_stop_eval",
            "priority": "medium",
            "description": f"{sym} 持仓 {thesis_days} 天，建议评估时间止损",
            "proposed_value": {"thesis_days": thesis_days, "expected_days": 14},
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 4. trigger_deep_research：亏损连续或跌幅 > 5%
    if day_ret < -5.0:
        suggs.append({
            "type": "trigger_deep_research",
            "priority": "high",
            "description": f"{sym} 今日跌 {day_ret:.1f}%，建议重新做深度研究",
            "proposed_value": {"reason": f"单日跌幅 {day_ret:.1f}%"},
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 5. thesis_confirmation：今日大涨 + gate 通过
    if day_ret > 3.0 and signal_accuracy.get("gate_correct") is True:
        suggs.append({
            "type": "thesis_confirmation",
            "priority": "low",
            "description": f"{sym} 今日涨 {day_ret:.1f}%，gate 通过，论点积极确认",
            "proposed_value": {"signal": "gate_pass_positive_day", "add_opportunity": True},
            "confirmed": None, "applied_at": None, "applied_to": None,
        })

    # 6. lesson_record：每日必有
    lesson = f"{sym} {date}: " + (
        f"计划执行{'良好' if followed == 'yes' else '偏差'}，"
        f"今日{'+' if day_ret >= 0 else ''}{day_ret:.1f}%"
    )
    suggs.append({
        "type": "lesson_record",
        "priority": "low",
        "description": lesson[:80],
        "proposed_value": {"lesson": lesson[:100]},
        "confirmed": None, "applied_at": None, "applied_to": None,
    })

    return suggs
```

- [ ] **Step 1.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_postmarket_summary.py -v
```

预期：全部 PASS（yfinance 相关的 build_performance 测试不在此 task，不需要网络）

- [ ] **Step 1.5：Commit**

```bash
git add agents/postmarket_data_collector.py tests/test_postmarket_summary.py
git commit -m "feat: add postmarket_data_collector — execution/performance/signal_accuracy/suggestions"
```

---

## Task 2：postmarket_summary.py（组合 + 写文件）

**Files:**
- Create: `agents/postmarket_summary.py`
- Test: `tests/test_postmarket_summary.py`（追加）

---

- [ ] **Step 2.1：追加测试**

```python
def test_build_per_stock_summary_schema(tmp_path):
    """build_per_stock_summary 返回所有顶层字段"""
    from agents.postmarket_summary import build_per_stock_summary
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date)
    _make_intraday(tmp_path, "TEST", date)
    _make_positions(tmp_path, "TEST", shares=10, cost=100.0)

    result = build_per_stock_summary("TEST", date, base_dir=str(tmp_path),
                                      day_ret_pct=1.5)
    required = {"date", "sym", "generated_at", "execution", "performance",
                "signal_accuracy", "snapshot_thesis_status",
                "learning_notes", "next_day"}
    assert required == set(result.keys()), f"缺少: {required - set(result.keys())}"
    assert result["sym"] == "TEST"
    assert isinstance(result["next_day"]["suggestions"], list)
    assert result["snapshot_thesis_status"] == "intact"


def test_write_per_stock_summary_creates_file(tmp_path):
    """write_per_stock_summary 生成 JSON 文件"""
    from agents.postmarket_summary import build_per_stock_summary, write_per_stock_summary
    date = "2026-05-20"
    _make_premarket(tmp_path, "TEST", date)
    _make_intraday(tmp_path, "TEST", date)
    _make_positions(tmp_path, "TEST")

    data = build_per_stock_summary("TEST", date, base_dir=str(tmp_path), day_ret_pct=1.5)
    path = write_per_stock_summary("TEST", date, data, base_dir=str(tmp_path))

    import pathlib
    assert pathlib.Path(path).exists()
    d = json.loads(pathlib.Path(path).read_text())
    assert d["sym"] == "TEST"
```

- [ ] **Step 2.2：运行，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_postmarket_summary.py -k "per_stock" -v
```

- [ ] **Step 2.3：创建 agents/postmarket_summary.py**

```python
"""
盘后汇总模块 — postmarket_summary.py
组合 postmarket_data_collector 的结构化数据，写出：
  postmarket_summary_{date}_{sym}.json  per-stock
  postmarket_summary_{date}.json        per-day

用法: python3.12 agents/postmarket_summary.py [SYM1 SYM2 ...]
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.postmarket_data_collector import (
    build_execution, build_performance, build_signal_accuracy, generate_suggestions,
)

BASE     = os.path.expanduser("~/stock_team")
FIND_DIR = os.path.join(BASE, "findings")
CFG_DIR  = os.path.join(BASE, "config")


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def build_per_stock_summary(
    sym: str, date: str,
    day_ret_pct: float | None = None,
    base_dir: str = BASE,
) -> dict:
    """构建 per-stock postmarket_summary dict"""
    find_dir = os.path.join(base_dir, "findings")
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    pos = pos_data.get("positions", {}).get(sym.upper(), {})

    execution      = build_execution(sym, date, base_dir=base_dir)
    performance    = build_performance(sym, date, base_dir=base_dir)
    if day_ret_pct is not None:
        performance["day_ret_pct"] = day_ret_pct   # 外部注入（测试用）
    actual_ret     = performance.get("day_ret_pct")
    signal_acc     = build_signal_accuracy(sym, date, day_ret_pct=actual_ret,
                                           base_dir=base_dir)
    suggestions    = generate_suggestions(
        sym=sym, date=date,
        execution=execution,
        performance=performance,
        signal_accuracy=signal_acc,
    )

    return {
        "date":          date,
        "sym":           sym.upper(),
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "execution":     execution,
        "performance":   performance,
        "signal_accuracy": signal_acc,
        "snapshot_thesis_status": pos.get("thesis_status"),  # 收盘快照
        "learning_notes": "",      # 待 LLM 生成（存根）
        "next_day": {
            "suggestions":  suggestions,
            "summary_note": "",    # 待 LLM 生成（存根）
        },
    }


def write_per_stock_summary(sym: str, date: str, data: dict,
                             base_dir: str = BASE) -> str:
    """写出 per-stock JSON，返回路径"""
    find_dir = os.path.join(base_dir, "findings")
    os.makedirs(find_dir, exist_ok=True)
    fname = f"postmarket_summary_{date}_{sym.upper()}.json"
    path  = os.path.join(find_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def build_per_day_summary(date: str, per_stock: list[dict],
                           base_dir: str = BASE) -> dict:
    """构建 per-day postmarket_summary dict（简化，不含相关性矩阵）"""
    syms = [d["sym"] for d in per_stock]
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    positions = pos_data.get("positions", {})

    # 加权平均日收益
    total_val = total_ret = 0.0
    best = worst = None
    for d in per_stock:
        sym = d["sym"]
        pos = positions.get(sym, {})
        shares = float(pos.get("shares", 0) or 0)
        open_p = d.get("performance", {}).get("open_price") or 0.0
        ret    = d.get("performance", {}).get("day_ret_pct") or 0.0
        w      = shares * open_p
        total_val += w
        total_ret += w * ret
        if best is None or ret > (per_stock[[d["sym"] for d in per_stock].index(sym)].get(
                "performance", {}).get("day_ret_pct", 0) or 0):
            best = sym
        if worst is None:
            worst = sym

    total_day_ret = round(total_ret / total_val, 2) if total_val > 0 else None

    # 汇总明日风险
    tomorrow_risks = []
    for d in per_stock:
        for s in d.get("next_day", {}).get("suggestions", []):
            if s["type"] == "tomorrow_risk_calendar":
                tomorrow_risks.extend(s.get("proposed_value", {}).get("events", []))

    pending = sum(
        1 for d in per_stock
        for s in d.get("next_day", {}).get("suggestions", [])
        if s.get("confirmed") is None
    )

    return {
        "date":            date,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "symbols":         syms,
        "portfolio": {
            "total_day_ret_pct":    total_day_ret,
            "best_performer":       best,
            "worst_performer":      worst,
            "correlation_matrix":   {},   # 需要 yfinance 历史数据，后续实现
            "max_correlation_pair": [],
            "max_correlation_value": None,
            "concentration_risk":   "medium",
        },
        "tomorrow_risk_calendar":  list(set(tomorrow_risks)),
        "pending_suggestions_count": pending,
        "llm_review": "",    # 待 LLM 生成（存根）
    }


def write_per_day_summary(date: str, data: dict, base_dir: str = BASE) -> str:
    """写出 per-day JSON，返回路径"""
    find_dir = os.path.join(base_dir, "findings")
    os.makedirs(find_dir, exist_ok=True)
    path = os.path.join(find_dir, f"postmarket_summary_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def main(syms: list[str] | None = None):
    date_str = _date.today().strftime("%Y-%m-%d")
    if not syms:
        cfg  = _load(os.path.join(CFG_DIR, "poll_config.json"))
        syms = cfg.get("default_symbols", [])

    print(f"\n{'='*60}")
    print(f"  盘后复盘 {date_str}  （{len(syms)} 只标的）")
    print(f"{'='*60}\n")

    per_stock_data = []
    for sym in syms:
        try:
            data = build_per_stock_summary(sym, date_str)
            path = write_per_stock_summary(sym, date_str, data)
            per_stock_data.append(data)
            ret = data.get("performance", {}).get("day_ret_pct")
            ret_str = f"{ret:+.1f}%" if ret is not None else "N/A"
            print(f"  {sym}: {ret_str}  ✅ {os.path.basename(path)}")
        except Exception as e:
            print(f"  {sym}: ❌ {e}")

    if per_stock_data:
        day_data = build_per_day_summary(date_str, per_stock_data)
        day_path = write_per_day_summary(date_str, day_data)
        pending  = day_data.get("pending_suggestions_count", 0)
        print(f"\n  per-day: ✅ {os.path.basename(day_path)}  （{pending} 条待确认建议）")


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
```

- [ ] **Step 2.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_postmarket_summary.py -v
```

预期：全部 PASS

- [ ] **Step 2.5：冒烟测试（用现有数据手动跑）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -c "
from agents.postmarket_summary import build_per_stock_summary, write_per_stock_summary
d = build_per_stock_summary('NVDA', '2026-05-19')
print('Keys:', sorted(d.keys()))
print('Suggestions:', len(d['next_day']['suggestions']))
" 2>/dev/null
```

- [ ] **Step 2.6：Commit**

```bash
git add agents/postmarket_summary.py tests/test_postmarket_summary.py
git commit -m "feat: add postmarket_summary.py — per-stock + per-day JSON writer"
```

---

## Task 3：suggestion_applier.py

**Files:**
- Create: `agents/suggestion_applier.py`
- Test: `tests/test_postmarket_summary.py`（追加）

---

- [ ] **Step 3.1：追加测试**

```python
def test_apply_suggestion_thesis_status(tmp_path):
    """apply_suggestion 写回 positions.json 的 thesis_status"""
    from agents.suggestion_applier import apply_suggestion
    pos_file = tmp_path / "config" / "positions.json"
    pos_file.parent.mkdir(parents=True)
    pos_file.write_text(json.dumps({
        "positions": {"NVDA": {"thesis_status": "intact", "cost": 100.0}},
        "_excluded": [],
    }), encoding="utf-8")

    suggestion = {
        "type": "thesis_status",
        "priority": "high",
        "description": "论点动摇",
        "proposed_value": {"new_status": "weakening"},
        "confirmed": True,
        "applied_at": None, "applied_to": None,
    }
    result = apply_suggestion("NVDA", suggestion, base_dir=str(tmp_path))

    pos_data = json.loads(pos_file.read_text())
    assert pos_data["positions"]["NVDA"]["thesis_status"] == "weakening"
    assert result["applied_to"]["old_value"]["thesis_status"] == "intact"


def test_apply_suggestion_lesson_record(tmp_path):
    """lesson_record 追加到 trading_lessons.json"""
    from agents.suggestion_applier import apply_suggestion
    lessons_file = tmp_path / "trading_lessons.json"
    lessons_file.write_text(json.dumps([]), encoding="utf-8")

    suggestion = {
        "type": "lesson_record",
        "proposed_value": {"lesson": "测试教训"},
        "confirmed": True, "applied_at": None, "applied_to": None,
    }
    apply_suggestion("TEST", suggestion, base_dir=str(tmp_path))

    data = json.loads(lessons_file.read_text())
    assert any("测试教训" in str(item) for item in data)


def test_apply_suggestion_display_only(tmp_path):
    """展示型建议（correlation_warning）applied_to 为 null，不写文件"""
    from agents.suggestion_applier import apply_suggestion
    suggestion = {
        "type": "correlation_warning",
        "proposed_value": {"pair": ["NVDA", "NBIL"], "corr": 0.91},
        "confirmed": True, "applied_at": None, "applied_to": None,
    }
    result = apply_suggestion("TEST", suggestion, base_dir=str(tmp_path))
    assert result["applied_to"] is None
```

- [ ] **Step 3.2：运行，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_postmarket_summary.py -k "apply" -v
```

- [ ] **Step 3.3：创建 agents/suggestion_applier.py**

```python
"""
建议应用模块 — suggestion_applier.py
将用户确认的 next_day.suggestions 写回对应源文件。

用法（由 Claude skill 调用，不直接运行）:
  from agents.suggestion_applier import apply_suggestion
  result = apply_suggestion(sym, suggestion, base_dir=BASE)
"""
import json, os
from datetime import datetime, timezone

BASE    = os.path.expanduser("~/stock_team")
CFG_DIR = os.path.join(BASE, "config")

# 展示型建议：confirmed=True 表示"已知晓"，不写任何文件
DISPLAY_ONLY_TYPES = {"correlation_warning", "thesis_confirmation", "time_stop_eval"}


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def apply_suggestion(sym: str, suggestion: dict,
                     base_dir: str = BASE) -> dict:
    """
    应用一条已确认的建议。
    返回更新后的 suggestion dict（含 applied_at + applied_to）。
    """
    stype  = suggestion.get("type", "")
    pvalue = suggestion.get("proposed_value", {}) or {}

    if stype in DISPLAY_ONLY_TYPES:
        suggestion["applied_at"] = datetime.now(timezone.utc).isoformat()
        suggestion["applied_to"] = None
        return suggestion

    applied_to = None
    sym_upper  = sym.upper()

    if stype == "thesis_status":
        pos_path = os.path.join(base_dir, "config", "positions.json")
        data = _load(pos_path)
        old_val = data.get("positions", {}).get(sym_upper, {}).get("thesis_status")
        new_val = pvalue.get("new_status", "weakening")
        data.setdefault("positions", {}).setdefault(sym_upper, {})["thesis_status"] = new_val
        _save(pos_path, data)
        applied_to = {"file": "positions.json",
                      "field": f"positions.{sym_upper}.thesis_status",
                      "old_value": {"thesis_status": old_val},
                      "new_value": {"thesis_status": new_val}}

    elif stype == "stop_move":
        pos_path = os.path.join(base_dir, "config", "positions.json")
        data = _load(pos_path)
        old_val = data.get("positions", {}).get(sym_upper, {}).get("t1_stop_snapshot")
        new_val = pvalue.get("new_stop")
        if new_val is not None:
            data.setdefault("positions", {}).setdefault(sym_upper, {})["t1_stop_snapshot"] = new_val
            _save(pos_path, data)
        applied_to = {"file": "positions.json",
                      "field": f"positions.{sym_upper}.t1_stop_snapshot",
                      "old_value": {"t1_stop_snapshot": old_val},
                      "new_value": {"t1_stop_snapshot": new_val}}

    elif stype == "lesson_record":
        lessons_path = os.path.join(base_dir, "trading_lessons.json")
        try:
            with open(lessons_path, encoding="utf-8") as f:
                lessons = json.load(f)
            if not isinstance(lessons, list):
                lessons = []
        except Exception:
            lessons = []
        lesson = pvalue.get("lesson", "")
        lessons.append({"date": datetime.now().strftime("%Y-%m-%d"), "sym": sym_upper,
                        "lesson": lesson})
        _save(lessons_path, lessons)
        applied_to = {"file": "trading_lessons.json", "field": "[]",
                      "old_value": None, "new_value": {"lesson": lesson}}

    elif stype == "trigger_deep_research":
        queue_path = os.path.join(base_dir, "config", "rerun_queue.json")
        try:
            with open(queue_path, encoding="utf-8") as f:
                queue = json.load(f)
            if not isinstance(queue, list):
                queue = []
        except Exception:
            queue = []
        queue.append({"sym": sym_upper, "reason": pvalue.get("reason", ""),
                      "requested_at": datetime.now().strftime("%Y-%m-%d")})
        _save(queue_path, queue)
        applied_to = {"file": "config/rerun_queue.json", "field": "[]",
                      "old_value": None, "new_value": pvalue}

    elif stype == "tomorrow_risk_calendar":
        cal_path = os.path.join(base_dir, "config", "macro_events_tomorrow.json")
        events = pvalue.get("events", [])
        _save(cal_path, {"date": datetime.now().strftime("%Y-%m-%d"), "events": events})
        applied_to = {"file": "config/macro_events_tomorrow.json",
                      "field": "events",
                      "old_value": None, "new_value": {"events": events}}

    # 其他类型暂不实施（master_weight / scene_calibration / node_reset / stage_alert）

    suggestion["applied_at"] = datetime.now(timezone.utc).isoformat()
    suggestion["applied_to"] = applied_to
    return suggestion
```

- [ ] **Step 3.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_postmarket_summary.py -v
```

预期：全部 PASS

- [ ] **Step 3.5：Commit**

```bash
git add agents/suggestion_applier.py tests/test_postmarket_summary.py
git commit -m "feat: add suggestion_applier.py — confirmed suggestions write-back to source files"
```

---

## Task 4：CHANGELOG 更新

- [ ] **Step 4.1：更新 CHANGELOG.md**

在顶部追加：

```
## 2026-05-20 postmarket_summary 实施完成

### 新建文件
- `agents/postmarket_data_collector.py` — 纯规则计算 execution/performance/signal_accuracy/12类建议
- `agents/postmarket_summary.py` — per-stock + per-day JSON 写文件，CLI 入口
- `agents/suggestion_applier.py` — 建议确认写回：thesis_status/stop_move/lesson_record/risk_calendar
- `tests/test_postmarket_summary.py` — 12个单元测试

---
```

- [ ] **Step 4.2：Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for postmarket_summary implementation"
```
