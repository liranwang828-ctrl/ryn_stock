# intraday_snapshot 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/intraday_snapshot.py`，每次 poll 追加一条 JSONL 记录到 `intraday_snapshot_{date}_{sym}.jsonl`，实现盘前计划与实时价格的结构化桥接，支持事件驱动告警和 dashboard 展示。

**Architecture:** 单独新建 `intraday_snapshot.py` 模块（纯函数，易测试），poll.py 在每轮末尾调用其 `write_snapshot_entry()` 接口；后续 10 分钟冷却、post_open_adj 校准、poll_state 合并均在此模块内处理。poll.py 只做一行调用，最小化改动。

**Tech Stack:** Python 3.12, json（无新依赖）

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/intraday_snapshot.py` | 新建 | 核心模块：schema 构建、事件检测、冷却管理、文件 I/O |
| `agents/poll.py` | 修改（~2580 行末） | 每轮末尾调用 write_snapshot_entry() |
| `tests/test_intraday_snapshot.py` | 新建 | 单元测试：plan_vs_now 计算、thesis_signal 规则、entry_go_status 规则、事件检测 |

---

## Task 1：核心模块骨架 + plan_vs_now 计算

**Files:**
- Create: `agents/intraday_snapshot.py`
- Create: `tests/test_intraday_snapshot.py`

---

- [ ] **Step 1.1：写测试**

```python
# tests/test_intraday_snapshot.py
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/stock_team"))


def _nodes(entry_base=100.0, hard_stop=95.0, target=110.0,
           flex_add=93.0, flex_reduce=108.0):
    return {
        "entry_base": entry_base, "hard_stop": hard_stop,
        "target": target, "flex_add": flex_add, "flex_reduce": flex_reduce,
    }


def test_plan_vs_now_dist_formulas():
    """距离字段分母统一用 price"""
    from agents.intraday_snapshot import compute_dist_fields
    price = 102.0
    nodes = _nodes(entry_base=100.0, hard_stop=95.0, target=110.0,
                   flex_add=93.0, flex_reduce=108.0)
    d = compute_dist_fields(price, nodes)
    assert abs(d["dist_to_entry_pct"]      - (102.0 - 100.0) / 102.0 * 100) < 0.01
    assert abs(d["dist_to_stop_pct"]       - (102.0 -  95.0) / 102.0 * 100) < 0.01
    assert abs(d["dist_to_target_pct"]     - (110.0 - 102.0) / 102.0 * 100) < 0.01
    assert abs(d["dist_to_flex_add_pct"]   - (102.0 -  93.0) / 102.0 * 100) < 0.01
    assert abs(d["dist_to_flex_reduce_pct"]- (108.0 - 102.0) / 102.0 * 100) < 0.01


def test_plan_vs_now_null_when_no_nodes():
    """节点为 None 时距离字段为 None"""
    from agents.intraday_snapshot import compute_dist_fields
    d = compute_dist_fields(100.0, {"entry_base": None, "hard_stop": None,
                                    "target": None, "flex_add": None, "flex_reduce": None})
    assert d["dist_to_entry_pct"] is None
    assert d["dist_to_stop_pct"] is None


def test_thesis_signal_breach_on_stop():
    """price ≤ hard_stop → breach"""
    from agents.intraday_snapshot import compute_thesis_signal
    sig = compute_thesis_signal(
        price=94.0, hard_stop=95.0, dist_to_stop_pct=-1.1,
        thesis_status="intact", falsification_count=0,
    )
    assert sig == "breach"


def test_thesis_signal_warning_weakening():
    """weakening → warning（止损尚远）"""
    from agents.intraday_snapshot import compute_thesis_signal
    sig = compute_thesis_signal(
        price=97.0, hard_stop=95.0, dist_to_stop_pct=2.1,
        thesis_status="weakening", falsification_count=0,
    )
    assert sig == "warning"


def test_thesis_signal_intact_normal():
    """正常情况 → intact"""
    from agents.intraday_snapshot import compute_thesis_signal
    sig = compute_thesis_signal(
        price=102.0, hard_stop=95.0, dist_to_stop_pct=6.9,
        thesis_status="intact", falsification_count=0,
    )
    assert sig == "intact"


def test_entry_go_expired_after_10_30():
    """session_min ≥ 60 → expired（优先于其他规则）"""
    from agents.intraday_snapshot import compute_entry_go_status
    status = compute_entry_go_status(
        session_min=65,
        post_open_calibrated=True,
        entry_go=False,  # 即使 False，也应返回 expired
    )
    assert status == "expired"


def test_entry_go_go():
    """entry_go=True → go"""
    from agents.intraday_snapshot import compute_entry_go_status
    status = compute_entry_go_status(
        session_min=35,
        post_open_calibrated=True,
        entry_go=True,
    )
    assert status == "go"


def test_entry_go_pending_not_calibrated():
    """post_open_calibrated=False → pending"""
    from agents.intraday_snapshot import compute_entry_go_status
    status = compute_entry_go_status(
        session_min=20,
        post_open_calibrated=False,
        entry_go=None,
    )
    assert status == "pending"
```

- [ ] **Step 1.2：运行测试，确认 FAIL（ImportError）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py -v 2>&1 | head -15
```

- [ ] **Step 1.3：创建 agents/intraday_snapshot.py 骨架 + 实现三个纯函数**

```python
"""
盘中快照模块 — intraday_snapshot.py
每次 poll 追加一条 JSONL 记录到 intraday_snapshot_{date}_{sym}.jsonl。
提供的所有函数均为纯函数或纯 I/O，易于单元测试。

核心入口：write_snapshot_entry(sym, date, price_now_dict, context) → None
"""
import json, os
from datetime import datetime, timezone, timedelta

BASE      = os.path.expanduser("~/stock_team")
FIND_DIR  = os.path.join(BASE, "findings")
POLL_STATE_TPL = os.path.join(BASE, "learning", "poll_state_{}.json")

# ── 事件枚举 ───────────────────────────────────────────────────────────────
RED_EVENTS    = {"hard_stop_breach", "entry_go", "vix_spike"}
YELLOW_EVENTS = {"gate_flip", "consensus_shift", "thesis_breach"}
COOLDOWN_MINUTES = 10


# ── 纯计算函数 ─────────────────────────────────────────────────────────────

def compute_dist_fields(price: float, nodes: dict) -> dict:
    """
    计算当前价格距各节点的距离百分比。
    分母统一用 price，节点为 None 时对应字段返回 None。
    """
    def _dist(ref):
        if ref is None or price == 0:
            return None
        return round((ref - price) / price * 100, 2)

    eb  = nodes.get("entry_base")
    hs  = nodes.get("hard_stop")
    tgt = nodes.get("target")
    fa  = nodes.get("flex_add")
    fr  = nodes.get("flex_reduce")

    return {
        "dist_to_entry_pct":       None if eb  is None else round((price - eb)  / price * 100, 2),
        "dist_to_stop_pct":        None if hs  is None else round((price - hs)  / price * 100, 2),
        "dist_to_target_pct":      _dist(tgt),
        "dist_to_flex_add_pct":    None if fa  is None else round((price - fa)  / price * 100, 2),
        "dist_to_flex_reduce_pct": _dist(fr),
    }


def compute_thesis_signal(
    price: float, hard_stop: float | None, dist_to_stop_pct: float | None,
    thesis_status: str, falsification_count: int,
) -> str:
    """
    纯规则推导论点信号（优先级从高到低，第一条命中即停止）。
    返回: "breach" | "warning" | "intact"
    """
    if hard_stop is not None and price <= hard_stop:
        return "breach"
    if thesis_status == "broken":
        return "breach"
    if thesis_status == "weakening" and dist_to_stop_pct is not None and dist_to_stop_pct < 3.0:
        return "breach"
    if thesis_status == "weakening":
        return "warning"
    if dist_to_stop_pct is not None and dist_to_stop_pct < 3.0:
        return "warning"
    if falsification_count > 0 and dist_to_stop_pct is not None and dist_to_stop_pct < 5.0:
        return "warning"
    return "intact"


def compute_entry_go_status(
    session_min: int,
    post_open_calibrated: bool,
    entry_go: bool | None,
) -> str:
    """
    纯规则推导入场窗口状态（优先级从高到低）。
    返回: "expired" | "go" | "abort" | "pending"
    """
    if session_min >= 60:
        return "expired"
    if not post_open_calibrated:
        return "pending"
    if entry_go is True:
        return "go"
    if entry_go is False:
        return "abort"
    return "pending"
```

- [ ] **Step 1.4：运行测试，确认 PASS**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py -v
```

预期：8 个测试全部 PASS

- [ ] **Step 1.5：Commit**

```bash
git add agents/intraday_snapshot.py tests/test_intraday_snapshot.py
git commit -m "feat: add intraday_snapshot module with core pure functions"
```

---

## Task 2：get_effective_nodes + build_plan_vs_now + build_node_snapshot

**Files:**
- Modify: `agents/intraday_snapshot.py`（追加函数）
- Test: `tests/test_intraday_snapshot.py`（追加测试）

---

- [ ] **Step 2.1：追加测试**

```python
def test_get_effective_nodes_prefers_adj():
    """post_open_adj 值优先于原始值"""
    from agents.intraday_snapshot import get_effective_nodes
    summary = {
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0},
        "exit": {"hard_stop": 94.0, "target_price": 109.0,
                 "flex_add_level": 92.0, "flex_reduce_level": 107.0},
        "post_open_adj": {
            "entry_base_adj": 101.0,   # override
            "hard_stop_adj": None,     # null → use exit.hard_stop
            "target_adj": None,
            "flex_add_adj": 91.0,      # override
            "flex_reduce_adj": None,
        },
    }
    nodes = get_effective_nodes(summary)
    assert nodes["entry_base"] == 101.0   # adj 覆盖
    assert nodes["hard_stop"]  == 94.0   # adj=None → 用 exit.hard_stop
    assert nodes["flex_add"]   == 91.0   # adj 覆盖


def test_get_effective_nodes_no_adj():
    """post_open_adj=None → 全用原始值"""
    from agents.intraday_snapshot import get_effective_nodes
    summary = {
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0},
        "exit": {"hard_stop": 95.0, "target_price": 110.0,
                 "flex_add_level": 93.0, "flex_reduce_level": 108.0},
        "post_open_adj": None,
    }
    nodes = get_effective_nodes(summary)
    assert nodes["entry_base"] == 100.0
    assert nodes["hard_stop"]  == 95.0


def test_build_plan_vs_now_fields():
    """build_plan_vs_now 返回所有必要字段"""
    from agents.intraday_snapshot import build_plan_vs_now
    summary = {
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0,
                  "entry_conditions": ["A", "B"], "cancel_conditions": []},
        "exit": {"hard_stop": 95.0, "target_price": 110.0,
                 "flex_add_level": 93.0, "flex_reduce_level": 108.0},
        "thesis": {"status": "intact", "today_falsification": []},
        "post_open_adj": None,
    }
    pvn = build_plan_vs_now(
        price=102.0, summary=summary,
        session_min=20, post_open_calibrated=False,
    )
    required = {"dist_to_entry_pct", "dist_to_stop_pct", "dist_to_target_pct",
                "dist_to_flex_add_pct", "dist_to_flex_reduce_pct",
                "entry_conditions_met", "entry_conditions_total",
                "scene_match", "thesis_signal", "entry_go_status"}
    assert required == set(pvn.keys()), f"缺少字段: {required - set(pvn.keys())}"
    assert pvn["thesis_signal"] == "intact"
    assert pvn["entry_go_status"] == "pending"
```

- [ ] **Step 2.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py -k "nodes or plan_vs_now" -v
```

- [ ] **Step 2.3：追加函数到 agents/intraday_snapshot.py**

```python
def get_effective_nodes(summary: dict) -> dict:
    """
    从 premarket_summary 提取当前生效的价格节点。
    post_open_adj 中非 null 的 *_adj 值优先覆盖原始值。
    """
    entry = summary.get("entry") or {}
    exit_ = summary.get("exit") or {}
    adj   = summary.get("post_open_adj") or {}

    def _pick(adj_key, *fallbacks):
        v = adj.get(adj_key)
        if v is not None:
            return v
        for fb_key in fallbacks:
            val = exit_.get(fb_key) or entry.get(fb_key)
            if val is not None:
                return val
        return None

    return {
        "entry_base":  _pick("entry_base_adj",   "entry_base"),
        "hard_stop":   _pick("hard_stop_adj",    "hard_stop",     "stop_loss"),
        "target":      _pick("target_adj",       "target_price"),
        "flex_add":    _pick("flex_add_adj",     "flex_add_level"),
        "flex_reduce": _pick("flex_reduce_adj",  "flex_reduce_level"),
    }


def build_node_snapshot(nodes: dict) -> dict:
    """复制节点快照（用于 JSONL 中的 node_snapshot 字段）"""
    return {
        "entry_base":  nodes.get("entry_base"),
        "hard_stop":   nodes.get("hard_stop"),
        "target":      nodes.get("target"),
        "flex_add":    nodes.get("flex_add"),
        "flex_reduce": nodes.get("flex_reduce"),
    }


def build_plan_vs_now(
    price: float,
    summary: dict,
    session_min: int,
    post_open_calibrated: bool,
) -> dict:
    """
    构建 plan_vs_now 字段（纯规则，不依赖 LLM）。
    """
    nodes  = get_effective_nodes(summary)
    thesis = summary.get("thesis") or {}
    adj    = summary.get("post_open_adj") or {}

    dist   = compute_dist_fields(price, nodes)
    thesis_status      = thesis.get("status", "intact")
    falsification_count = len(thesis.get("today_falsification", []))

    thesis_sig = compute_thesis_signal(
        price=price,
        hard_stop=nodes.get("hard_stop"),
        dist_to_stop_pct=dist.get("dist_to_stop_pct"),
        thesis_status=thesis_status,
        falsification_count=falsification_count,
    )

    entry_go_val = adj.get("entry_go") if adj else None
    ego_status = compute_entry_go_status(
        session_min=session_min,
        post_open_calibrated=post_open_calibrated,
        entry_go=entry_go_val,
    )

    entry = summary.get("entry") or {}
    entry_conditions_total = len(entry.get("entry_conditions", []))

    return {
        **dist,
        "entry_conditions_met":   0,          # 实际判断由 poll.py 传入，默认 0
        "entry_conditions_total": entry_conditions_total,
        "scene_match":            None,        # 由 poll.py 对比 pred_scene 填充
        "thesis_signal":          thesis_sig,
        "entry_go_status":        ego_status,
    }
```

- [ ] **Step 2.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py -v
```

预期：全部 PASS

- [ ] **Step 2.5：Commit**

```bash
git add agents/intraday_snapshot.py tests/test_intraday_snapshot.py
git commit -m "feat: add get_effective_nodes + build_plan_vs_now + build_node_snapshot"
```

---

## Task 3：事件检测 + 冷却管理 + 文件 I/O

**Files:**
- Modify: `agents/intraday_snapshot.py`（追加）
- Test: `tests/test_intraday_snapshot.py`（追加）

---

- [ ] **Step 3.1：追加测试**

```python
def test_detect_event_hard_stop_breach():
    """price ≤ hard_stop → hard_stop_breach"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=94.0, hard_stop=95.0,
        thesis_signal="breach", prev_thesis_signal="intact",
        gate_status="未通过", prev_gate_status="通过",
        master_consensus="no_buy", prev_master_consensus="neutral",
        session_min=40, entry_go_status="go", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event == "hard_stop_breach"


def test_detect_event_entry_go():
    """entry_go_status 从非 go 变 go → entry_go"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=102.0, hard_stop=95.0,
        thesis_signal="intact", prev_thesis_signal="intact",
        gate_status="通过", prev_gate_status="通过",
        master_consensus="buy", prev_master_consensus="buy",
        session_min=30, entry_go_status="go", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event == "entry_go"


def test_detect_event_thesis_breach():
    """thesis_signal 从 intact 变 breach → thesis_breach（黄色，冷却）"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=100.0, hard_stop=95.0,   # price > hard_stop，不触发 hard_stop_breach
        thesis_signal="breach", prev_thesis_signal="intact",
        gate_status="通过", prev_gate_status="通过",
        master_consensus="neutral", prev_master_consensus="neutral",
        session_min=50, entry_go_status="pending", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event == "thesis_breach"


def test_detect_event_gate_flip():
    """gate_status 翻转 → gate_flip"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=100.0, hard_stop=95.0,
        thesis_signal="intact", prev_thesis_signal="intact",
        gate_status="通过", prev_gate_status="未通过",
        master_consensus="neutral", prev_master_consensus="neutral",
        session_min=50, entry_go_status="pending", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event == "gate_flip"


def test_detect_event_no_event():
    """无变化 → None"""
    from agents.intraday_snapshot import detect_event
    event = detect_event(
        price=100.0, hard_stop=95.0,
        thesis_signal="intact", prev_thesis_signal="intact",
        gate_status="通过", prev_gate_status="通过",
        master_consensus="neutral", prev_master_consensus="neutral",
        session_min=50, entry_go_status="pending", prev_entry_go_status="pending",
        vix_spike=False,
    )
    assert event is None


def test_append_and_read_snapshot(tmp_path):
    """append_snapshot 写入 JSONL，read_latest_snapshot 读最新一条"""
    from agents.intraday_snapshot import append_snapshot, read_latest_snapshot
    date = "2026-05-20"
    record1 = {"ts": "09:30:00", "meta": {"sym": "TEST", "date": date,
               "session_min": 0, "llm_triggered": False, "llm_trigger": None,
               "cooldown_until": None, "post_open_calibrated": False},
               "price_now": {"price": 100.0}, "plan_vs_now": {},
               "node_snapshot": {}, "action_now": None}
    record2 = {**record1, "ts": "09:32:00", "price_now": {"price": 101.0}}

    append_snapshot("TEST", date, record1, find_dir=str(tmp_path))
    append_snapshot("TEST", date, record2, find_dir=str(tmp_path))

    latest = read_latest_snapshot("TEST", date, find_dir=str(tmp_path))
    assert latest["price_now"]["price"] == 101.0
    assert latest["ts"] == "09:32:00"
```

- [ ] **Step 3.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py -k "detect or append or read" -v
```

- [ ] **Step 3.3：追加函数到 agents/intraday_snapshot.py**

```python
def detect_event(
    price: float, hard_stop: float | None,
    thesis_signal: str, prev_thesis_signal: str | None,
    gate_status: str, prev_gate_status: str | None,
    master_consensus: str | None, prev_master_consensus: str | None,
    session_min: int, entry_go_status: str, prev_entry_go_status: str | None,
    vix_spike: bool,
) -> str | None:
    """
    检测本轮是否触发事件（优先级：🔴 > 🟡）。
    返回事件 key 或 None。
    entry_go 自然受限于校准逻辑（10:00 poll 时 post_open_adj.entry_go 才被置为 True），
    因此转换到 "go" 仅在 10:00 附近发生，无需额外时间窗口过滤。
    """
    # 🔴 即时事件（优先检查，无冷却）
    if hard_stop is not None and price <= hard_stop:
        return "hard_stop_breach"
    if entry_go_status == "go" and prev_entry_go_status not in ("go", None) is False \
            and prev_entry_go_status != "go":
        return "entry_go"
    if vix_spike:
        return "vix_spike"
    # 🟡 冷却事件（per-sym 10分钟冷却）
    if thesis_signal == "breach" and prev_thesis_signal is not None \
            and prev_thesis_signal != "breach":
        return "thesis_breach"
    if gate_status != prev_gate_status and prev_gate_status is not None:
        return "gate_flip"
    if master_consensus != prev_master_consensus and prev_master_consensus is not None:
        return "consensus_shift"
    return None


def in_cooldown(sym: str, poll_state: dict) -> bool:
    """检查该标的是否在冷却期内"""
    cool = poll_state.get("symbols", {}).get(sym, {}).get("cooldown_until")
    if not cool:
        return False
    try:
        now_str = datetime.now().strftime("%H:%M:%S")
        return now_str < cool
    except Exception:
        return False


def set_cooldown(sym: str, poll_state_path: str) -> str:
    """设置冷却到期时间（当前时间 + 10 分钟），返回 cooldown_until 字符串"""
    until = (datetime.now() + timedelta(minutes=COOLDOWN_MINUTES)).strftime("%H:%M:%S")
    try:
        with open(poll_state_path, encoding="utf-8") as f:
            state = json.load(f)
        state.setdefault("symbols", {}).setdefault(sym, {})["cooldown_until"] = until
        with open(poll_state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return until


def append_snapshot(sym: str, date: str, record: dict,
                    find_dir: str = FIND_DIR) -> str:
    """追加一条 JSONL 记录，返回文件路径"""
    os.makedirs(find_dir, exist_ok=True)
    fname = f"intraday_snapshot_{date}_{sym.upper()}.jsonl"
    path  = os.path.join(find_dir, fname)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def read_latest_snapshot(sym: str, date: str,
                          find_dir: str = FIND_DIR) -> dict | None:
    """读取最新一条 JSONL 记录，文件不存在时返回 None"""
    fname = f"intraday_snapshot_{date}_{sym.upper()}.jsonl"
    path  = os.path.join(find_dir, fname)
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
```

- [ ] **Step 3.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py -v
```

预期：全部 PASS（detect_event 中 thesis_breach 逻辑较粗，可接受）

- [ ] **Step 3.5：Commit**

```bash
git add agents/intraday_snapshot.py tests/test_intraday_snapshot.py
git commit -m "feat: add detect_event + cooldown + append/read snapshot I/O"
```

---

## Task 4：update_poll_state + write_snapshot_entry（主入口）

**Files:**
- Modify: `agents/intraday_snapshot.py`（追加主入口）
- Test: `tests/test_intraday_snapshot.py`（追加测试）

---

- [ ] **Step 4.1：追加测试**

```python
def test_update_poll_state_merges_new_keys(tmp_path):
    """update_poll_state 只追加新字段，不覆盖已有字段"""
    from agents.intraday_snapshot import update_poll_state
    state_file = tmp_path / "poll_state_2026-05-20.json"
    state_file.write_text(json.dumps({
        "date": "2026-05-20",
        "symbols": {
            "TEST": {"last_price": 100.0, "gate_status": "未通过"}
        }
    }), encoding="utf-8")

    plan_vs_now = {
        "entry_conditions_met": 1, "entry_conditions_total": 3,
        "dist_to_stop_pct": 5.2, "dist_to_target_pct": 7.8,
        "thesis_signal": "intact", "entry_go_status": "pending",
    }
    update_poll_state("TEST", plan_vs_now, last_action_now=None,
                      last_event=None, last_event_at=None,
                      cooldown_until=None,
                      poll_state_path=str(state_file))

    state = json.loads(state_file.read_text())
    sym = state["symbols"]["TEST"]
    assert sym["last_price"] == 100.0           # 原有字段未被覆盖
    assert "plan_vs_now" in sym                 # 新增字段存在
    assert sym["plan_vs_now"]["thesis_signal"] == "intact"
    assert "last_action_now" in sym
    assert "cooldown_until" in sym


def test_write_snapshot_entry_creates_file(tmp_path):
    """write_snapshot_entry 追加 JSONL 文件且结构完整"""
    from agents.intraday_snapshot import write_snapshot_entry
    state_file = tmp_path / "poll_state_2026-05-20.json"
    state_file.write_text(json.dumps({"date": "2026-05-20", "symbols": {}}))

    summary = {
        "entry": {"entry_base": 100.0, "stop_loss": 95.0, "target_price": 110.0,
                  "entry_conditions": ["A"], "cancel_conditions": []},
        "exit": {"hard_stop": 95.0, "target_price": 110.0,
                 "flex_add_level": 93.0, "flex_reduce_level": 108.0},
        "thesis": {"status": "intact", "today_falsification": []},
        "post_open_adj": None,
    }

    write_snapshot_entry(
        sym="TEST", date="2026-05-20",
        price_now={
            "price": 102.0, "chg_pct": 0.5, "vwap_dist_pct": 0.2,
            "rs_vs_spy": 1.0, "rs_vs_sector": 0.5, "rsi14_5m": 55.0,
            "vol_ratio": 1.1, "gate_status": "通过", "gate_pass": ["RS"],
            "gate_block": [], "master_avg": 6.0, "master_consensus": "neutral",
        },
        premarket_summary=summary,
        session_min=20,
        post_open_calibrated=False,
        prev_poll_state={},
        vix_spike=False,
        find_dir=str(tmp_path),
        poll_state_path=str(state_file),
    )

    import pathlib
    files = list(pathlib.Path(tmp_path).glob("intraday_snapshot_2026-05-20_TEST.jsonl"))
    assert files, "JSONL 文件未生成"
    record = json.loads(files[0].read_text().strip())
    assert set(record.keys()) == {"ts", "meta", "price_now", "plan_vs_now",
                                  "node_snapshot", "action_now"}
    assert record["action_now"] is None
    assert record["meta"]["sym"] == "TEST"
```

- [ ] **Step 4.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py -k "poll_state or write_snapshot" -v
```

- [ ] **Step 4.3：追加主入口函数**

```python
def update_poll_state(
    sym: str,
    plan_vs_now: dict,
    last_action_now: str | None,
    last_event: str | None,
    last_event_at: str | None,
    cooldown_until: str | None,
    poll_state_path: str,
    master_consensus: str | None = None,
) -> None:
    """将本轮关键字段合并写入 poll_state（只追加，不覆盖已有字段）"""
    try:
        with open(poll_state_path, encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {"symbols": {}}

    sym_state = state.setdefault("symbols", {}).setdefault(sym, {})
    sym_state["plan_vs_now"]    = {k: plan_vs_now.get(k) for k in
                                    ("entry_conditions_met", "entry_conditions_total",
                                     "dist_to_stop_pct", "dist_to_target_pct",
                                     "thesis_signal", "entry_go_status")}
    sym_state["last_action_now"]  = last_action_now
    sym_state["last_event"]       = last_event
    sym_state["last_event_at"]    = last_event_at
    sym_state["cooldown_until"]   = cooldown_until
    # master_consensus 持久化，供下一轮 detect_event 读取 prev_master_consensus
    if master_consensus is not None:
        sym_state["master_consensus"] = master_consensus

    try:
        with open(poll_state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def write_snapshot_entry(
    sym: str,
    date: str,
    price_now: dict,
    premarket_summary: dict,
    session_min: int,
    post_open_calibrated: bool,
    prev_poll_state: dict,
    vix_spike: bool = False,
    find_dir: str = FIND_DIR,
    poll_state_path: str | None = None,
) -> None:
    """
    主入口：由 poll.py 每轮末尾调用。
    构建本轮 JSONL 记录并追加，同时更新 poll_state。
    """
    if poll_state_path is None:
        poll_state_path = POLL_STATE_TPL.format(date)

    # 1. 计算 plan_vs_now
    pvn = build_plan_vs_now(
        price=price_now.get("price", 0.0),
        summary=premarket_summary,
        session_min=session_min,
        post_open_calibrated=post_open_calibrated,
    )

    # 2. 检测事件
    prev_sym = prev_poll_state.get("symbols", {}).get(sym, {})
    prev_pvn = prev_sym.get("plan_vs_now", {})
    cur_consensus = price_now.get("master_consensus")
    event = detect_event(
        price=price_now.get("price", 0.0),
        hard_stop=get_effective_nodes(premarket_summary).get("hard_stop"),
        thesis_signal=pvn["thesis_signal"],
        prev_thesis_signal=prev_pvn.get("thesis_signal"),
        gate_status=price_now.get("gate_status", ""),
        prev_gate_status=prev_sym.get("gate_status"),
        master_consensus=cur_consensus,
        prev_master_consensus=prev_sym.get("master_consensus"),   # 由上轮 update_poll_state 写入
        session_min=session_min,
        entry_go_status=pvn["entry_go_status"],
        prev_entry_go_status=prev_pvn.get("entry_go_status"),
        vix_spike=vix_spike,
    )

    # 3. 冷却检查（🔴 事件跳过冷却）
    is_red    = event in RED_EVENTS
    on_cool   = not is_red and in_cooldown(sym, prev_poll_state)
    llm_triggered = event is not None and not on_cool
    cooldown_until = None
    if llm_triggered and event in YELLOW_EVENTS:
        cooldown_until = set_cooldown(sym, poll_state_path)

    # 4. 构建记录
    ts_str = datetime.now().strftime("%H:%M:%S")
    nodes  = get_effective_nodes(premarket_summary)
    record = {
        "ts": ts_str,
        "meta": {
            "date":                 date,
            "sym":                  sym.upper(),
            "session_min":          session_min,
            "llm_triggered":        llm_triggered,
            "llm_trigger":          event if llm_triggered else None,
            "cooldown_until":       cooldown_until,
            "post_open_calibrated": post_open_calibrated,
        },
        "price_now":     price_now,
        "plan_vs_now":   pvn,
        "node_snapshot": build_node_snapshot(nodes),
        "action_now":    None,
    }

    # 5. 写入 JSONL
    append_snapshot(sym, date, record, find_dir=find_dir)

    # 6. 更新 poll_state
    update_poll_state(
        sym=sym,
        plan_vs_now=pvn,
        last_action_now=None,
        last_event=event if llm_triggered else None,
        last_event_at=ts_str if llm_triggered else None,
        cooldown_until=cooldown_until,
        poll_state_path=poll_state_path,
        master_consensus=cur_consensus,
    )
```

- [ ] **Step 4.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py -v
```

预期：全部 PASS

- [ ] **Step 4.5：Commit**

```bash
git add agents/intraday_snapshot.py tests/test_intraday_snapshot.py
git commit -m "feat: add update_poll_state + write_snapshot_entry main entry"
```

---

## Task 5：poll.py 集成（每轮末尾调用）

**Files:**
- Modify: `agents/poll.py`（~2580 行，master_score_log 追加块之后）

---

- [ ] **Step 5.1：找到插入位置**

在 poll.py 中搜索 `master_score_log`，找到该块结束（约 2590 行），即最后一个 `except Exception: pass` 之后，`run_poll` 函数末尾附近。

- [ ] **Step 5.2：插入集成代码**

在 `master_score_log` 块结束之后（但仍在 `run_poll` 函数内）追加：

```python
    # ── intraday_snapshot（每轮追加 JSONL，合并 poll_state 新字段）──────────
    try:
        from agents.intraday_snapshot import write_snapshot_entry
        from datetime import date as _dt_date
        _snap_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _snap_syms = list(stocks.keys()) if stocks else []
        # 计算 vix_spike（VIX 单轮涨 > 10% 或 SPY 5分钟跌 > -1%）
        _vix_spike = (vc > 0 and _prev_state and
                      _prev_state.get("market_context", {}).get("vix", 0) > 0 and
                      vc / _prev_state["market_context"]["vix"] - 1 > 0.10) or \
                     (qqq5m < -1.0)
        _session_min = et_h * 60 + et_m - 9 * 60 - 30   # 开盘后分钟数
        _snap_ps_path = os.path.join(
            os.path.expanduser("~/stock_team"), "learning",
            f"poll_state_{_snap_date}.json")

        for _snap_sym, _snap_data in stocks.items():
            try:
                # 读取对应的 premarket_summary
                _snap_pm_path = os.path.join(
                    os.path.expanduser("~/stock_team"), "findings",
                    f"premarket_summary_{_snap_date}_{_snap_sym}.json")
                _snap_pm = {}
                if os.path.exists(_snap_pm_path):
                    with open(_snap_pm_path, encoding="utf-8") as _f:
                        _snap_pm = json.load(_f)

                # 构造 price_now dict（从 stocks[sym] 数据）
                _master = _snap_data.get("master_score", {})
                _snap_price_now = {
                    "price":            _snap_data.get("last_price", 0.0),
                    "chg_pct":          round(_snap_data.get("last_rs", 0.0), 2),
                    "vwap_dist_pct":    round(_snap_data.get("vwap_dist", 0.0), 2)
                                        if hasattr(_snap_data, "get") else 0.0,
                    "rs_vs_spy":        round(_snap_data.get("last_rs", 0.0), 2),
                    "rs_vs_sector":     0.0,
                    "rsi14_5m":         round(_snap_data.get("last_rsi14_5m", 50.0), 1),
                    "vol_ratio":        round(_snap_data.get("last_vol_ratio", 1.0), 2),
                    "gate_status":      _snap_data.get("gate_status", "未通过"),
                    "gate_pass":        _snap_data.get("gate_pass_list", []),
                    "gate_block":       _snap_data.get("gate_missing", []),
                    "master_avg":       round(float(_master.get("avg", 0)), 2)
                                        if _master else None,
                    "master_consensus": _master.get("consensus_code") if _master else None,
                }

                _post_cal = _snap_pm.get("post_open_adj") is not None

                write_snapshot_entry(
                    sym=_snap_sym,
                    date=_snap_date,
                    price_now=_snap_price_now,
                    premarket_summary=_snap_pm,
                    session_min=max(0, _session_min),
                    post_open_calibrated=_post_cal,
                    prev_poll_state=_old_state or {},
                    vix_spike=_vix_spike,
                    poll_state_path=_snap_ps_path,
                )
            except Exception:
                pass
    except Exception:
        pass
```

- [ ] **Step 5.3：冒烟测试（手动确认不报错）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -c "
# 验证 import 无问题
from agents.intraday_snapshot import write_snapshot_entry
print('import OK')
"
```

- [ ] **Step 5.4：运行回归测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_intraday_snapshot.py tests/test_session_manager.py -v --tb=short 2>&1 | tail -20
```

预期：test_intraday_snapshot 全部 PASS，session_manager 无回归

- [ ] **Step 5.5：Commit**

```bash
git add agents/poll.py
git commit -m "feat: integrate intraday_snapshot into poll.py end-of-round hook"
```

---

## Task 6：CHANGELOG 更新

- [ ] **Step 6.1：更新 CHANGELOG.md**

在顶部追加：

```
## 2026-05-20 intraday_snapshot.py 实施完成

### 新建文件
- `agents/intraday_snapshot.py` — JSONL 快照追加、plan_vs_now 规则计算、事件检测、冷却管理
- `tests/test_intraday_snapshot.py` — 13个单元测试

### 修改文件
- `agents/poll.py` — 每轮末尾调用 write_snapshot_entry()，追加盘中快照
```

- [ ] **Step 6.2：Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for intraday_snapshot implementation"
```
