# position-builder 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `agents/position_builder.py`，在建仓时通过三种模式（规划/快速/补全）引导用户结构化填写 positions.json，确保 falsification_conditions 等关键字段不缺失。

**Architecture:** 新建 `position_builder.py` 实现三种模式的引导逻辑，通过标准化函数读写 `positions.json`；在 `translator.py` 添加买入意图规则触发快速模式；每次写入同步生成 `findings/position_entry_{date}_{sym}.json` 审计记录。

**Tech Stack:** Python 3.12, json, yfinance（仅读 strategic_memo 和 premarket_summary，不新增 API 调用）

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/position_builder.py` | 新建 | 三种模式的引导逻辑 + positions.json 写入 |
| `agents/translator.py` | 修改（~55行）| 添加买入意图规则（buy_quick 和 new_position）|
| `tests/test_position_builder.py` | 新建 | 单元测试：三种模式、schema 验证、审计记录 |

---

## Task 1：positions.json schema 验证函数

**Files:**
- Create: `agents/position_builder.py`（第一部分：schema 工具）
- Test: `tests/test_position_builder.py`

---

- [ ] **Step 1.1：写 schema 验证测试**

```python
# tests/test_position_builder.py
import sys, os, json, tempfile, datetime
sys.path.insert(0, os.path.expanduser("~/stock_team"))

def _minimal_pos():
    """最小合法持仓记录"""
    return {
        "cost": 100.0, "shares": 10, "date": "2026-05-20",
        "note": "test", "tranche": "T1",
        "t1_cost": 100.0, "t1_shares": 10, "t1_date": "2026-05-20",
        "t2_cost": None, "t2_shares": 0,
        "t2_conditions": {"note": "", "underlying_price_floor": None,
                          "etf_price_floor": None, "vol_ratio_min": None},
        "t3_cost": None, "t3_shares": 0,
        "position_type": "thesis",
        "thesis": "测试论点",
        "thesis_status": "intact", "thesis_updated": "2026-05-20",
        "falsification_conditions": ["价格跌破$90"],
        "falsification_updated": "2026-05-20",
        "catalyst_type": None, "catalyst_deadline": None,
        "catalyst_persistence": None,
        "daily_action": "B", "action_updated": "2026-05-20",
        "t1_stop_snapshot": 90.0,
        "stop_note": "GTC已挂", "gtc_stop_placed": True, "gtc_stop_date": "2026-05-20",
        "macro_type": "成长型",
        "macro_sensitivity": {"rate_up": "负", "inflation": "中",
                               "recession": "负", "dollar_strong": "负",
                               "credit_tight": "负"},
        "target_pct": 10.0, "min_pct": 5.0, "max_pct": 15.0,
        "_pending": False, "_pending_fields": [],
    }

def test_validate_valid_position():
    from agents.position_builder import validate_position
    pos = _minimal_pos()
    errors = validate_position(pos)
    assert errors == [], f"Valid position should have no errors, got: {errors}"

def test_validate_missing_required():
    from agents.position_builder import validate_position
    pos = _minimal_pos()
    del pos["thesis"]
    del pos["falsification_conditions"]
    errors = validate_position(pos)
    assert any("thesis" in e for e in errors)
    assert any("falsification_conditions" in e for e in errors)

def test_validate_pending_position():
    from agents.position_builder import validate_position
    pos = _minimal_pos()
    pos["_pending"] = True
    pos["falsification_conditions"] = []
    pos["t1_stop_snapshot"] = None
    errors = validate_position(pos)
    # _pending=True 时允许必填字段为空，validate 只报 warning 不报 error
    assert errors == []
```

- [ ] **Step 1.2：运行测试，确认 FAIL（ImportError）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -v 2>&1 | head -20
```

预期：`ImportError: cannot import name 'validate_position'`

- [ ] **Step 1.3：实现 position_builder.py 框架 + validate_position**

```python
# agents/position_builder.py
"""
建仓引导模块 — 三种模式：规划(planning) / 快速(quick) / 补全(catch_up)

用法（交互式，由 Claude skill 调用）:
  from agents.position_builder import (
      planning_mode, quick_mode, catch_up_mode,
      validate_position, list_pending
  )
"""
import json, os
from datetime import datetime, timezone

BASE      = os.path.expanduser("~/stock_team")
POS_PATH  = os.path.join(BASE, "config", "positions.json")
FIND_DIR  = os.path.join(BASE, "findings")
PYTHON    = "/tool/pandora/bin/python3.12"

# ── 必填字段（_pending=False 时检查）───────────────────────────
REQUIRED_FIELDS = [
    "cost", "shares", "date", "position_type", "thesis",
    "thesis_status", "falsification_conditions",
    "t1_stop_snapshot", "gtc_stop_placed",
]

# ── 待补全字段（quick 模式写入 _pending_fields）─────────────────
PENDING_FIELDS_DEFAULT = [
    "falsification_conditions", "t1_stop_snapshot",
    "gtc_stop_placed", "t2_conditions", "macro_sensitivity",
]

def _load_positions() -> dict:
    try:
        return json.load(open(POS_PATH, encoding="utf-8"))
    except Exception:
        return {"positions": {}, "_excluded": []}

def _save_positions(data: dict):
    json.dump(data, open(POS_PATH, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def _load_memo(sym: str) -> dict | None:
    path = os.path.join(BASE, f"strategic_memo_{sym.upper()}.json")
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    return None

def validate_position(pos: dict) -> list[str]:
    """
    验证持仓记录是否符合 schema。
    _pending=True 时跳过必填检查（快速模式允许缺失）。
    返回 error 字符串列表，空列表 = 合法。
    """
    errors = []
    if pos.get("_pending"):
        return []   # pending 模式下不强制验证
    for field in REQUIRED_FIELDS:
        val = pos.get(field)
        if val is None or val == "" or val == []:
            errors.append(f"缺少必填字段: {field}")
    # position_type 枚举检查
    valid_types = {"thesis", "catalyst", "trend", "flex"}
    if pos.get("position_type") not in valid_types:
        errors.append(f"position_type 必须是 {valid_types} 之一")
    # thesis_status 枚举检查
    valid_status = {"intact", "weakening", "broken"}
    if pos.get("thesis_status") not in valid_status:
        errors.append(f"thesis_status 必须是 {valid_status} 之一")
    return errors

def list_pending() -> list[str]:
    """返回所有 _pending=True 的标的列表"""
    data = _load_positions()
    excluded = set(data.get("_excluded", []))
    return [sym for sym, pos in data.get("positions", {}).items()
            if pos.get("_pending") and sym not in excluded]
```

- [ ] **Step 1.4：运行测试，确认 PASS**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -v 2>&1 | head -20
```

预期：3 个测试全部 PASS

- [ ] **Step 1.5：Commit**

```bash
cd ~/stock_team
git add agents/position_builder.py tests/test_position_builder.py
git commit -m "feat: add position_builder scaffold + validate_position + list_pending"
```

---

## Task 2：write_position + write_entry_audit 核心写入函数

**Files:**
- Modify: `agents/position_builder.py`（追加写入函数）
- Test: `tests/test_position_builder.py`（追加测试）

---

- [ ] **Step 2.1：写写入测试**

在 `tests/test_position_builder.py` 追加：

```python
def test_write_position_new(tmp_path):
    """write_position 新建持仓写入 positions.json"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))

    from agents.position_builder import write_position
    pos = _minimal_pos()
    write_position("TEST", pos, pos_path=str(pos_file))

    data = json.loads(pos_file.read_text())
    assert "TEST" in data["positions"]
    assert data["positions"]["TEST"]["thesis"] == "测试论点"

def test_write_position_excluded_preserved(tmp_path):
    """write_position 不覆盖 _excluded 列表"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": ["BABA"]}))

    from agents.position_builder import write_position
    write_position("TEST", _minimal_pos(), pos_path=str(pos_file))

    data = json.loads(pos_file.read_text())
    assert "BABA" in data["_excluded"]

def test_write_entry_audit(tmp_path):
    """write_entry_audit 生成 position_entry_{date}_{sym}.json"""
    from agents.position_builder import write_entry_audit
    date = "2026-05-20"
    audit = write_entry_audit(
        sym="TEST", date=date, mode="planning",
        fields_written=["cost", "thesis"],
        fields_pending=[],
        user_inputs={"thesis": "测试论点"},
        auto_filled={},
        find_dir=str(tmp_path),
    )
    # 文件应存在
    fname = f"position_entry_{date}_TEST.json"
    assert (tmp_path / fname).exists()
    d = json.loads((tmp_path / fname).read_text())
    assert d["mode"] == "planning"
    assert d["pending_count"] == 0
```

- [ ] **Step 2.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py::test_write_position_new -v
```

预期：`ImportError: cannot import name 'write_position'`

- [ ] **Step 2.3：实现 write_position 和 write_entry_audit**

在 `agents/position_builder.py` 追加：

```python
def write_position(sym: str, pos: dict, pos_path: str = POS_PATH):
    """将持仓记录写入 positions.json（新建或覆盖）"""
    try:
        data = json.load(open(pos_path, encoding="utf-8"))
    except Exception:
        data = {"positions": {}, "_excluded": []}
    data["positions"][sym.upper()] = pos
    json.dump(data, open(pos_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def write_entry_audit(
    sym: str, date: str, mode: str,
    fields_written: list, fields_pending: list,
    user_inputs: dict, auto_filled: dict,
    find_dir: str = FIND_DIR,
    positions_updated: bool = True,
    premarket_triggered: bool = False,
) -> str:
    """生成 position_entry_{date}_{sym}.json 审计记录，返回文件路径"""
    os.makedirs(find_dir, exist_ok=True)
    record = {
        "date": date,
        "sym": sym.upper(),
        "session_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "source": "manual",
        "fields_written": fields_written,
        "fields_pending": fields_pending,
        "pending_count": len(fields_pending),
        "positions_json_updated": positions_updated,
        "premarket_triggered": premarket_triggered,
        "user_inputs": user_inputs,
        "auto_filled": auto_filled,
    }
    fname = f"position_entry_{date}_{sym.upper()}.json"
    path = os.path.join(find_dir, fname)
    json.dump(record, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return path
```

- [ ] **Step 2.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -v
```

预期：全部 PASS

- [ ] **Step 2.5：Commit**

```bash
git add agents/position_builder.py tests/test_position_builder.py
git commit -m "feat: add write_position + write_entry_audit to position_builder"
```

---

## Task 3：quick_mode 实现

**Files:**
- Modify: `agents/position_builder.py`（追加 quick_mode）
- Test: `tests/test_position_builder.py`

---

- [ ] **Step 3.1：写 quick_mode 测试**

```python
def test_quick_mode_creates_pending_position(tmp_path):
    """quick_mode 写入 positions.json，_pending=True，缺失字段在 _pending_fields"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))

    from agents.position_builder import quick_mode
    result = quick_mode(
        sym="TEST",
        cost=100.0, shares=10, date="2026-05-20",
        position_type="thesis",
        thesis="AI算力垄断",
        pos_path=str(pos_file),
        find_dir=str(tmp_path),
    )

    data = json.loads(pos_file.read_text())
    pos = data["positions"]["TEST"]
    assert pos["_pending"] is True
    assert "falsification_conditions" in pos["_pending_fields"]
    assert pos["cost"] == 100.0
    assert pos["thesis"] == "AI算力垄断"
    assert result["mode"] == "quick"

def test_quick_mode_position_type_enum(tmp_path):
    """quick_mode 拒绝无效的 position_type，且不污染真实 positions.json"""
    import pytest
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))
    with pytest.raises(ValueError, match="position_type"):
        from agents.position_builder import quick_mode
        quick_mode("X", 100.0, 1, "2026-05-20", "invalid_type", "test",
                   pos_path=str(pos_file), find_dir=str(tmp_path))
```

- [ ] **Step 3.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -k "quick" -v
```

- [ ] **Step 3.3：实现 quick_mode**

在 `agents/position_builder.py` 追加：

```python
VALID_POSITION_TYPES = {"thesis", "catalyst", "trend", "flex"}

def quick_mode(
    sym: str, cost: float, shares: int, date: str,
    position_type: str, thesis: str,
    pos_path: str = POS_PATH, find_dir: str = FIND_DIR,
) -> dict:
    """
    快速建仓模式（盘中使用）：仅填写最小字段，其余标记 _pending。
    返回 {"mode": "quick", "pending_fields": [...], "audit_path": "..."}
    """
    if position_type not in VALID_POSITION_TYPES:
        raise ValueError(f"position_type 必须是 {VALID_POSITION_TYPES} 之一，得到: {position_type}")

    today = date
    pos = {
        "cost": cost, "shares": shares, "date": today,
        "note": f"{sym.upper()} 快速建仓",
        "tranche": "T1",
        "t1_cost": cost, "t1_shares": shares, "t1_date": today,
        "t2_cost": None, "t2_shares": 0,
        "t2_conditions": {"note": "", "underlying_price_floor": None,
                          "etf_price_floor": None, "vol_ratio_min": None},
        "t3_cost": None, "t3_shares": 0,
        "position_type": position_type,
        "thesis": thesis,
        "thesis_status": "intact", "thesis_updated": today,
        "falsification_conditions": [],   # 待补全
        "falsification_updated": None,
        "catalyst_type": None, "catalyst_deadline": None,
        "catalyst_persistence": None,
        "daily_action": "B", "action_updated": today,
        "t1_stop_snapshot": None,         # 待补全
        "stop_note": "", "gtc_stop_placed": False, "gtc_stop_date": None,
        "macro_type": "", "macro_sensitivity": {},  # 待补全
        "target_pct": None, "min_pct": None, "max_pct": None,
        "_pending": True,
        "_pending_fields": PENDING_FIELDS_DEFAULT.copy(),
    }

    write_position(sym, pos, pos_path=pos_path)
    audit_path = write_entry_audit(
        sym=sym, date=today, mode="quick",
        fields_written=["cost", "shares", "date", "position_type", "thesis"],
        fields_pending=PENDING_FIELDS_DEFAULT,
        user_inputs={"position_type": position_type, "thesis": thesis},
        auto_filled={},
        find_dir=find_dir,
    )
    return {"mode": "quick", "pending_fields": PENDING_FIELDS_DEFAULT, "audit_path": audit_path}
```

- [ ] **Step 3.4：运行测试，确认 PASS**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -k "quick" -v
```

- [ ] **Step 3.5：Commit**

```bash
git add agents/position_builder.py tests/test_position_builder.py
git commit -m "feat: implement quick_mode in position_builder"
```

---

## Task 4：planning_mode 实现（含 strategic_memo 快路径）

**Files:**
- Modify: `agents/position_builder.py`（追加 planning_mode）
- Test: `tests/test_position_builder.py`

---

- [ ] **Step 4.1：写 planning_mode 测试**

```python
def test_planning_mode_no_memo(tmp_path):
    """无 strategic_memo 时，planning_mode 返回引导问题列表"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))

    from agents.position_builder import planning_mode
    result = planning_mode(
        sym="NVDA", memo_dir=str(tmp_path),  # 无 memo 文件
        pos_path=str(pos_file), find_dir=str(tmp_path),
    )
    assert result["source"] == "manual"
    assert "prefilled" in result
    # 无 memo 时 prefilled 为空
    assert result["prefilled"].get("thesis") is None

def test_planning_mode_with_memo(tmp_path):
    """有 strategic_memo 时，prefilled 包含 thesis 和 macro_sensitivity"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))

    # 写入 mock strategic_memo
    memo = {
        "sym": "NVDA", "analysis_date": "2026-05-20",
        "synthesis": {"key_condition": "Blackwell出货节奏", "strategic_stance": "hold"},
        "support_and_risk": {
            "macro_fit": {"assessment": "favorable", "active_headwinds": [], "headwind_count": 0},
            "main_risks": ["竞争对手AMD追赶"],
        },
        "judgment": {"thesis_lifecycle_stage": {"stage": "mid"}},
        "outlook": {"valid_until": "2026-06-30"},
    }
    (tmp_path / "strategic_memo_NVDA.json").write_text(
        json.dumps(memo, ensure_ascii=False))

    from agents.position_builder import planning_mode
    result = planning_mode(
        sym="NVDA", memo_dir=str(tmp_path),
        pos_path=str(pos_file), find_dir=str(tmp_path),
    )
    assert result["source"] == "strategic_memo"
    assert result["prefilled"]["thesis"] == "Blackwell出货节奏"
    assert result["prefilled"]["macro_sensitivity"]["rate_up"] is not None

def test_planning_mode_write(tmp_path):
    """planning_mode write=True 时将记录写入 positions.json"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))

    from agents.position_builder import planning_mode
    user_answers = {
        "thesis": "AI算力垄断",
        "falsification_conditions": ["跌破$200且跑输SOXX"],
        "t1_stop_snapshot": 195.0,
        "gtc_stop_placed": True,
        "position_type": "thesis",
        "cost": 220.0, "shares": 10, "date": "2026-05-20",
    }
    planning_mode(
        sym="NVDA", memo_dir=str(tmp_path),
        pos_path=str(pos_file), find_dir=str(tmp_path),
        write=True, user_answers=user_answers,
    )
    data = json.loads(pos_file.read_text())
    assert "NVDA" in data["positions"]
    pos = data["positions"]["NVDA"]
    assert pos["_pending"] is False
    assert pos["falsification_conditions"] == ["跌破$200且跑输SOXX"]
```

- [ ] **Step 4.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -k "planning" -v
```

- [ ] **Step 4.3：实现 planning_mode**

在 `agents/position_builder.py` 追加：

```python
_MACRO_SENSITIVITY_TEMPLATE = {
    "rate_up": "负", "inflation": "中", "recession": "负",
    "dollar_strong": "负", "credit_tight": "负",
}

def _memo_to_prefilled(memo: dict) -> dict:
    """从 strategic_memo 提取可预填的字段"""
    prefilled = {}
    synth = memo.get("synthesis", {})
    prefilled["thesis"] = synth.get("key_condition", "")

    # macro_sensitivity 从 macro_fit 推导（简化：顺风全正，逆风全负，中性不变）
    mac = memo.get("support_and_risk", {}).get("macro_fit", {})
    assessment = mac.get("assessment", "neutral")
    headwinds = set(mac.get("active_headwinds", []))
    sens = _MACRO_SENSITIVITY_TEMPLATE.copy()
    for key in headwinds:
        if key in sens:
            sens[key] = "负"
    prefilled["macro_sensitivity"] = sens

    prefilled["main_risks"] = memo.get("support_and_risk", {}).get("main_risks", [])
    return prefilled

def planning_mode(
    sym: str,
    memo_dir: str = BASE,
    pos_path: str = POS_PATH,
    find_dir: str = FIND_DIR,
    write: bool = False,
    user_answers: dict | None = None,
) -> dict:
    """
    规划模式（建仓前使用）。
    write=False（默认）：仅返回引导信息（prefilled + questions），不写文件。
    write=True：user_answers 必须提供，写入 positions.json 并生成审计记录。
    """
    memo_path = os.path.join(memo_dir, f"strategic_memo_{sym.upper()}.json")
    memo = None
    if os.path.exists(memo_path):
        try:
            memo = json.load(open(memo_path, encoding="utf-8"))
        except Exception:
            pass

    source = "strategic_memo" if memo else "manual"
    prefilled = _memo_to_prefilled(memo) if memo else {
        "thesis": None, "macro_sensitivity": None, "main_risks": [],
    }

    if not write:
        return {
            "source": source,
            "prefilled": prefilled,
            "questions": [
                "Q1: position_type（thesis/catalyst/trend/flex）？",
                "Q2: 确认/修改 thesis（一句话，≤50字）？",
                "Q3: 证伪条件（什么情况下承认错了，具体可观测）？",
                "Q4: 硬止损价是多少？GTC 是否已挂好？",
            ],
        }

    # write=True：user_answers 必须提供所有必填字段
    a = user_answers or {}
    today = a.get("date", datetime.now().strftime("%Y-%m-%d"))
    pos = {
        "cost": a.get("cost", 0.0),
        "shares": a.get("shares", 0),
        "date": today, "note": f"{sym.upper()} 规划建仓",
        "tranche": "T1",
        "t1_cost": a.get("cost", 0.0),
        "t1_shares": a.get("shares", 0),
        "t1_date": today,
        "t2_cost": None, "t2_shares": 0,
        "t2_conditions": {"note": "", "underlying_price_floor": None,
                          "etf_price_floor": None, "vol_ratio_min": None},
        "t3_cost": None, "t3_shares": 0,
        "position_type": a.get("position_type", "thesis"),
        "thesis": a.get("thesis", prefilled.get("thesis", "")),
        "thesis_status": "intact", "thesis_updated": today,
        "falsification_conditions": a.get("falsification_conditions", []),
        "falsification_updated": today,
        "catalyst_type": a.get("catalyst_type"),
        "catalyst_deadline": a.get("catalyst_deadline"),
        "catalyst_persistence": a.get("catalyst_persistence"),
        "daily_action": "B", "action_updated": today,
        "t1_stop_snapshot": a.get("t1_stop_snapshot"),
        "stop_note": a.get("stop_note", ""),
        "gtc_stop_placed": a.get("gtc_stop_placed", False),
        "gtc_stop_date": today if a.get("gtc_stop_placed") else None,
        "macro_type": a.get("macro_type", ""),
        "macro_sensitivity": a.get("macro_sensitivity") or prefilled.get("macro_sensitivity") or {},
        "target_pct": a.get("target_pct"),
        "min_pct": a.get("min_pct"),
        "max_pct": a.get("max_pct"),
        "_pending": False,
        "_pending_fields": [],
    }

    write_position(sym, pos, pos_path=pos_path)
    auto_filled = {}
    if memo:
        auto_filled = {"thesis": prefilled.get("thesis"),
                       "macro_sensitivity": prefilled.get("macro_sensitivity")}
    audit_path = write_entry_audit(
        sym=sym, date=today, mode="planning",
        fields_written=list(a.keys()),
        fields_pending=[],
        user_inputs=a, auto_filled=auto_filled,
        find_dir=find_dir,
    )
    if memo:
        audit_path_data = json.load(open(audit_path, encoding="utf-8"))
        audit_path_data["source"] = "strategic_memo"
        json.dump(audit_path_data, open(audit_path, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)

    return {"source": source, "prefilled": prefilled, "audit_path": audit_path}
```

- [ ] **Step 4.4：运行测试，确认全部 PASS**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -v
```

- [ ] **Step 4.5：Commit**

```bash
git add agents/position_builder.py tests/test_position_builder.py
git commit -m "feat: implement planning_mode with strategic_memo fast-path"
```

---

## Task 5：catch_up_mode 实现

**Files:**
- Modify: `agents/position_builder.py`（追加 catch_up_mode）
- Test: `tests/test_position_builder.py`

---

- [ ] **Step 5.1：写 catch_up_mode 测试**

```python
def test_catch_up_mode_fills_pending(tmp_path):
    """catch_up_mode 填写 _pending=True 的持仓字段"""
    pos_file = tmp_path / "positions.json"
    # 先用 quick_mode 写入 pending 持仓
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))

    from agents.position_builder import quick_mode, catch_up_mode
    quick_mode("TEST", 100.0, 10, "2026-05-20", "thesis", "AI论点",
               pos_path=str(pos_file), find_dir=str(tmp_path))

    # 补全
    catch_up_mode(
        sym="TEST",
        updates={
            "falsification_conditions": ["跌破$90且跑输SPY"],
            "t1_stop_snapshot": 88.0,
            "gtc_stop_placed": True,
        },
        pos_path=str(pos_file), find_dir=str(tmp_path),
    )

    data = json.loads(pos_file.read_text())
    pos = data["positions"]["TEST"]
    assert pos["falsification_conditions"] == ["跌破$90且跑输SPY"]
    assert pos["t1_stop_snapshot"] == 88.0
    # _pending_fields 减少了已填字段
    assert "t1_stop_snapshot" not in pos["_pending_fields"]

def test_catch_up_sym_not_in_positions(tmp_path):
    """catch_up_mode 对不存在的 sym 抛 KeyError"""
    import pytest
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))
    from agents.position_builder import catch_up_mode
    with pytest.raises(KeyError):
        catch_up_mode("NONEXISTENT", {"thesis": "x"},
                      pos_path=str(pos_file), find_dir=str(tmp_path))

def test_catch_up_clears_pending_when_complete(tmp_path):
    """所有 _pending_fields 都填完后，_pending 变为 False"""
    pos_file = tmp_path / "positions.json"
    pos_file.write_text(json.dumps({"positions": {}, "_excluded": []}))

    from agents.position_builder import quick_mode, catch_up_mode, PENDING_FIELDS_DEFAULT
    quick_mode("TEST", 100.0, 10, "2026-05-20", "thesis", "AI论点",
               pos_path=str(pos_file), find_dir=str(tmp_path))

    # 一次性填完所有 pending 字段
    updates = {f: "dummy" for f in PENDING_FIELDS_DEFAULT}
    updates["falsification_conditions"] = ["条件1"]
    updates["t1_stop_snapshot"] = 88.0
    updates["gtc_stop_placed"] = True
    updates["t2_conditions"] = {"note": "test"}
    updates["macro_sensitivity"] = {"rate_up": "负", "inflation": "中",
                                    "recession": "负", "dollar_strong": "负",
                                    "credit_tight": "负"}

    catch_up_mode("TEST", updates, pos_path=str(pos_file), find_dir=str(tmp_path))

    data = json.loads(pos_file.read_text())
    pos = data["positions"]["TEST"]
    assert pos["_pending"] is False
    assert pos["_pending_fields"] == []
```

- [ ] **Step 5.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -k "catch_up" -v
```

- [ ] **Step 5.3：实现 catch_up_mode**

在 `agents/position_builder.py` 追加：

```python
def catch_up_mode(
    sym: str, updates: dict,
    pos_path: str = POS_PATH, find_dir: str = FIND_DIR,
) -> dict:
    """
    补全模式：填写 _pending=True 持仓的缺失字段。
    updates: {field: value} 要更新的字段。
    返回 {"mode": "catch_up", "remaining_pending": [...], "complete": bool}
    """
    data = _load_positions()
    sym_upper = sym.upper()
    if sym_upper not in data["positions"]:
        raise KeyError(f"{sym_upper} 不在 positions.json 中")

    pos = data["positions"][sym_upper]
    pending_fields = list(pos.get("_pending_fields", []))

    # 更新指定字段
    for field, value in updates.items():
        pos[field] = value
        if field in pending_fields:
            pending_fields.remove(field)

    # 更新 _pending 状态
    pos["_pending_fields"] = pending_fields
    pos["_pending"] = len(pending_fields) > 0

    data["positions"][sym_upper] = pos
    _save_positions(data)

    today = datetime.now().strftime("%Y-%m-%d")
    write_entry_audit(
        sym=sym, date=today, mode="catch_up",
        fields_written=list(updates.keys()),
        fields_pending=pending_fields,
        user_inputs=updates, auto_filled={},
        find_dir=find_dir,
        positions_updated=True,
        premarket_triggered=False,
    )

    return {
        "mode": "catch_up",
        "remaining_pending": pending_fields,
        "complete": not pos["_pending"],
    }
```

- [ ] **Step 5.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -v
```

预期：全部 PASS

- [ ] **Step 5.5：Commit**

```bash
git add agents/position_builder.py tests/test_position_builder.py
git commit -m "feat: implement catch_up_mode in position_builder"
```

---

## Task 6：translator.py 添加买入意图规则

**Files:**
- Modify: `agents/translator.py`（~55行，INTENT_RULES 中添加规则）
- Test: `tests/test_position_builder.py`

---

- [ ] **Step 6.1：写 translator 集成测试**

```python
def test_translator_detects_buy_intent():
    """translator 识别'买了NVDA'等买入意图（只测正则匹配，不执行子进程）"""
    import re
    from agents.translator import _COMPILED
    text = "刚买了NVDA"
    matched = [intent for pat, intent, fn in _COMPILED if pat.search(text)]
    assert "buy_quick" in matched, f"buy_quick 未匹配，命中: {matched}"

def test_translator_detects_new_position_intent():
    """translator 识别'建仓NVDA'等新建仓意图（只测正则匹配）"""
    import re
    from agents.translator import _COMPILED
    text = "新建仓位NVDA"
    matched = [intent for pat, intent, fn in _COMPILED if pat.search(text)]
    assert "new_position" in matched, f"new_position 未匹配，命中: {matched}"
```

- [ ] **Step 6.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -k "translator" -v
```

- [ ] **Step 6.3：修改 translator.py（两处修改）**

**修改 1**：在 `INTENT_RULES` 列表（约第 30 行）的 `# ── 收盘/收市` 规则前追加两条规则：

```python
    # ── 买入记录（触发 quick_mode）─────────────────────────────
    (r"(买了|买入了|成交了|入场了|刚买).{0,20}([A-Z]{2,5})",
     "buy_quick", lambda m, t: {"syms": _extract_syms(t)}),

    # ── 新建仓位（触发 planning_mode）──────────────────────────
    (r"(新建仓位|建仓|我要买|准备买|想买).{0,20}([A-Z]{2,5})",
     "new_position", lambda m, t: {"syms": _extract_syms(t)}),
```

**修改 2**：在 `translate()` 函数体内（约 `if intent == "morning":` 分支链中），追加两个 elif 分支。找到最后一个 `elif` 或 `else` 前插入：

```python
    elif intent == "buy_quick":
        syms = params.get("syms", [])
        sym_str = syms[0] if syms else "未知标的"
        return intent, f"检测到买入记录：{sym_str}。请告知成本价和股数，我来更新持仓记录。"

    elif intent == "new_position":
        syms = params.get("syms", [])
        sym_str = syms[0] if syms else "未知标的"
        return intent, f"准备为 {sym_str} 建仓。请确认：position_type（论点/催化剂/趋势/Flex）和一句话论点。"
```

- [ ] **Step 6.4：运行测试，确认 PASS**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -k "translator" -v
```

- [ ] **Step 6.5：运行全量测试确认无回归**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py tests/test_session_manager.py -v
```

- [ ] **Step 6.6：Commit**

```bash
git add agents/translator.py tests/test_position_builder.py
git commit -m "feat: add buy_quick and new_position intents to translator"
```

---

## Task 7：list_pending CLI + 更新 CHANGELOG

**Files:**
- Modify: `agents/position_builder.py`（追加 main() CLI）
- Modify: `CHANGELOG.md`

---

- [ ] **Step 7.1：实现 CLI 入口**

在 `agents/position_builder.py` 末尾追加：

```python
def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list_pending"
    if cmd == "list_pending":
        pending = list_pending()
        if pending:
            print(f"⚠️ 以下持仓有待补全字段：{', '.join(pending)}")
            for sym in pending:
                data = _load_positions()
                fields = data["positions"][sym].get("_pending_fields", [])
                print(f"  {sym}: {', '.join(fields)}")
        else:
            print("✅ 所有持仓记录完整，无待补全字段")

if __name__ == "__main__":
    main()
```

- [ ] **Step 7.2：冒烟测试 CLI**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 agents/position_builder.py list_pending
```

预期：显示当前 positions.json 中 _pending=true 的持仓（如有），或"✅ 所有持仓记录完整"

- [ ] **Step 7.3：更新 CHANGELOG**

在 `CHANGELOG.md` 顶部添加：

```
## 2026-05-20 position_builder.py 实施完成

### 新建文件
- `agents/position_builder.py` — 三种建仓模式：规划/快速/补全；validate_position；CLI list_pending
- `tests/test_position_builder.py` — 12个单元测试，覆盖三种模式和 schema 验证

### 修改文件
- `agents/translator.py` — 新增 buy_quick 和 new_position 意图规则
```

- [ ] **Step 7.4：最终全量测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_position_builder.py -v --tb=short
```

预期：全部 PASS

- [ ] **Step 7.5：最终 Commit**

```bash
git add agents/position_builder.py agents/translator.py CHANGELOG.md tests/test_position_builder.py
git commit -m "feat: complete position_builder with CLI + translator integration + CHANGELOG"
```
