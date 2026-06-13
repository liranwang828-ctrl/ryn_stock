# 出场决策模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/premarket_exit_sheet.py`，为每只持仓盘前生成三态出场建议（应出场/考虑减仓/继续持有）和今日止损价位，写入 `findings/exit_decision_{date}.json`，集成进 node 0。

**Architecture:** `evaluate_exit()` 内部从 yfinance 获取实时价，按优先级计算硬止损（manual_gtc > node1 > auto_atr），检查硬触发（价格/thesis/时间到期）和软触发（weakening/浮亏区/临近止损/RR低）输出三态。`generate_exit_sheet()` 批量调用，结果写入 JSON 并集成进 session_manager node 0。

**Tech Stack:** Python 3.12, yfinance, json, re（时间条件解析）, unittest.mock（测试）

---

## File Map

| 状态 | 路径 | 职责 |
|------|------|------|
| 新建 | `agents/premarket_exit_sheet.py` | 出场评估逻辑 + CLI |
| 新建 | `tests/test_premarket_exit_sheet.py` | 单元测试（10项）|
| 修改 | `agents/session_manager.py` | 加 Step 3.7 |
| 修改 | `agents/premarket_decision.py` | main() 末尾调用 |

---

## Task 1: 工具函数层（常量 + 解析 + 止损计算）

**Files:**
- Create: `agents/premarket_exit_sheet.py`
- Create: `tests/test_premarket_exit_sheet.py`

- [ ] **Step 1: 写失败测试（4个）**

```python
# tests/test_premarket_exit_sheet.py
import sys, os
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import date, timedelta


def test_parse_time_deadline_finds_date():
    """_parse_time_deadline 从中文文本解析截止日期"""
    from agents.premarket_exit_sheet import _parse_time_deadline
    text = "【路径/时间成本】MRVL 两周内（截止 2099-12-31）无法收复"
    days, date_str = _parse_time_deadline(text)
    assert date_str == "2099-12-31"
    assert days > 0


def test_parse_time_deadline_no_date():
    """无日期文本返回 (None, None)"""
    from agents.premarket_exit_sheet import _parse_time_deadline
    days, ds = _parse_time_deadline("【基本面/论点失效】大客户减单")
    assert days is None
    assert ds is None


def test_compute_stop_levels_uses_manual_gtc():
    """t1_stop_snapshot 非空时 stop_source=manual_gtc"""
    from agents.premarket_exit_sheet import _compute_stop_levels
    pos_cfg = {"t1_stop_snapshot": 76.0, "t1_cost": 102.5}
    with patch("agents.premarket_exit_sheet._fetch_price_and_atr",
               return_value={"cur": 88.4, "atr14": 5.0, "lo5": 80.0}):
        hs, ss, src, tech = _compute_stop_levels("MRVU", pos_cfg)
    assert hs == 76.0
    assert src == "manual_gtc"
    assert ss == 102.5  # soft_stop = cost


def test_compute_stop_levels_uses_auto_atr():
    """无手工止损时 stop_source=auto_atr，值为 lo5 - atr*0.3"""
    from agents.premarket_exit_sheet import _compute_stop_levels
    pos_cfg = {"t1_stop_snapshot": None, "node1": None, "t1_cost": 141.0}
    with patch("agents.premarket_exit_sheet._fetch_price_and_atr",
               return_value={"cur": 141.0, "atr14": 10.0, "lo5": 130.0}):
        hs, ss, src, tech = _compute_stop_levels("BABA", pos_cfg)
    assert src == "auto_atr"
    assert abs(hs - (130.0 - 10.0 * 0.3)) < 0.01  # lo5 - atr*0.3 = 127.0
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_exit_sheet.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 创建 agents/premarket_exit_sheet.py（工具函数层）**

```python
"""
premarket_exit_sheet.py — 持仓出场评估模块

与 premarket_decision.py 对称，为每只持仓盘前生成三态出场建议。

用法:
    python3.12 agents/premarket_exit_sheet.py            # 评估所有持仓
    python3.12 agents/premarket_exit_sheet.py MRVU BABA  # 指定持仓
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf
from datetime import datetime, date as _date

_BASE      = os.path.expanduser("~/stock_team")
_POS_PATH  = os.path.join(_BASE, "config", "positions.json")
_MACRO_PATH = os.path.join(_BASE, "findings", "macro.json")
_FINDINGS  = os.path.join(_BASE, "findings")


def _load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default or {}


def _parse_time_deadline(text: str):
    """
    从证伪条件文本中提取"截止 YYYY-MM-DD"日期。
    返回 (days_remaining, date_str)，无日期时返回 (None, None)。
    days_remaining < 0 表示已过期。
    """
    m = re.search(r'截止\s*(\d{4}-\d{2}-\d{2})', text)
    if not m:
        return None, None
    date_str = m.group(1)
    try:
        deadline = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (deadline - _date.today()).days, date_str
    except Exception:
        return None, None


def _fetch_price_and_atr(sym: str) -> dict | None:
    """获取当前价、ATR14、近5日低点。失败返回 None。"""
    try:
        h = yf.Ticker(sym).history(period="30d")
        if h.empty or len(h) < 5:
            return None
        cur   = float(h["Close"].iloc[-1])
        atr14 = float((h["High"] - h["Low"]).tail(14).mean()) if len(h) >= 14 \
                else float((h["High"] - h["Low"]).mean())
        lo5   = float(h["Low"].tail(5).min())
        return {"cur": cur, "atr14": round(atr14, 2), "lo5": round(lo5, 2)}
    except Exception:
        return None


def _compute_stop_levels(sym: str, pos_cfg: dict):
    """
    计算硬止损和软止损。

    返回 (hard_stop, soft_stop, stop_source, tech_data)
    stop_source: "manual_gtc" | "node1" | "auto_atr"
    tech_data: {"cur", "atr14", "lo5"} 或 None

    优先级：
      t1_stop_snapshot not in (None, 0) → manual_gtc
      node1 not in (None, 0)            → node1
      否则                               → auto_atr（lo5 - atr14×0.3）
    """
    t1_stop   = pos_cfg.get("t1_stop_snapshot")
    node1_val = pos_cfg.get("node1")
    cost      = float(pos_cfg.get("t1_cost") or pos_cfg.get("cost") or 0)
    soft_stop = cost

    tech = _fetch_price_and_atr(sym)

    if t1_stop not in (None, 0):
        return float(t1_stop), soft_stop, "manual_gtc", tech

    if node1_val not in (None, 0):
        return float(node1_val), soft_stop, "node1", tech

    # auto ATR
    if tech:
        auto_stop = round(tech["lo5"] - tech["atr14"] * 0.3, 2)
        return auto_stop, soft_stop, "auto_atr", tech

    return None, soft_stop, "auto_atr", None
```

- [ ] **Step 4: 跑 4 个测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_exit_sheet.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/premarket_exit_sheet.py tests/test_premarket_exit_sheet.py
git commit -m "feat(exit): add utility layer - _parse_time_deadline, _compute_stop_levels"
```

---

## Task 2: evaluate_exit() 核心决策逻辑

**Files:**
- Modify: `agents/premarket_exit_sheet.py`
- Modify: `tests/test_premarket_exit_sheet.py`

- [ ] **Step 1: 追加 6 个失败测试**

```python
# 追加到 tests/test_premarket_exit_sheet.py

def _make_pos(thesis_status="intact", t1_stop=None, node1=None, cost=100.0,
              falsification_conditions=None):
    return {
        "thesis_status": thesis_status,
        "t1_stop_snapshot": t1_stop,
        "node1": node1,
        "t1_cost": cost,
        "falsification_conditions": falsification_conditions or [],
    }

def _mock_tech(cur=120.0, atr14=5.0, lo5=110.0):
    return {"cur": cur, "atr14": atr14, "lo5": lo5}


def test_evaluate_exit_price_below_hard_stop():
    """价格 < 硬止损 → 应出场"""
    from agents.premarket_exit_sheet import evaluate_exit
    pos = _make_pos(t1_stop=100.0, cost=120.0)
    with patch("agents.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=95.0, lo5=90.0)):
        r = evaluate_exit("LITE", pos, {})
    assert r["decision"] == "应出场"
    assert "price < hard_stop" in r["hard_triggers"]
    assert r["hard_dist_pct"] < 0  # 负数表示跌破


def test_evaluate_exit_thesis_broken():
    """thesis_status=broken → 应出场"""
    from agents.premarket_exit_sheet import evaluate_exit
    pos = _make_pos(thesis_status="broken", t1_stop=80.0, cost=100.0)
    with patch("agents.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=85.0)):
        r = evaluate_exit("BABA", pos, {})
    assert r["decision"] == "应出场"
    assert "thesis_status=broken" in r["hard_triggers"]


def test_evaluate_exit_time_expired():
    """过期时间证伪条件 → 应出场"""
    from agents.premarket_exit_sheet import evaluate_exit
    past = (date.today() - __import__("datetime").timedelta(days=2)).strftime("%Y-%m-%d")
    cond = f"【路径/时间成本】截止 {past} 未完成"
    pos = _make_pos(t1_stop=80.0, cost=100.0, falsification_conditions=[cond])
    with patch("agents.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=90.0)):
        r = evaluate_exit("TEST", pos, {})
    assert r["decision"] == "应出场"
    assert any("expired" in t for t in r["hard_triggers"])


def test_evaluate_exit_weakening():
    """thesis=weakening → 考虑减仓"""
    from agents.premarket_exit_sheet import evaluate_exit
    pos = _make_pos(thesis_status="weakening", t1_stop=80.0, cost=100.0)
    with patch("agents.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=110.0)):
        r = evaluate_exit("NVDA", pos, {})
    assert r["decision"] == "考虑减仓"
    assert "thesis_status=weakening" in r["soft_triggers"]


def test_evaluate_exit_time_soft_trigger():
    """时间证伪条件 ≤3天 → 考虑减仓"""
    from agents.premarket_exit_sheet import evaluate_exit
    soon = (date.today() + __import__("datetime").timedelta(days=2)).strftime("%Y-%m-%d")
    cond = f"【路径/时间成本】截止 {soon} 条件"
    pos = _make_pos(t1_stop=80.0, cost=100.0, falsification_conditions=[cond])
    with patch("agents.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=110.0)):
        r = evaluate_exit("TEST", pos, {})
    assert r["decision"] == "考虑减仓"
    assert any("time_condition_expiring" in t for t in r["soft_triggers"])


def test_evaluate_exit_hold():
    """无触发条件 → 继续持有"""
    from agents.premarket_exit_sheet import evaluate_exit
    pos = _make_pos(t1_stop=80.0, cost=100.0)
    with patch("agents.premarket_exit_sheet._fetch_price_and_atr",
               return_value=_mock_tech(cur=120.0)):
        r = evaluate_exit("IAU", pos, {})
    assert r["decision"] == "继续持有"
    assert r["hard_triggers"] == []
    assert r["soft_triggers"] == []
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_exit_sheet.py::test_evaluate_exit_price_below_hard_stop -v 2>&1 | head -10
```
Expected: `AttributeError` (evaluate_exit not found)

- [ ] **Step 3: 实现 evaluate_exit()**

追加到 `agents/premarket_exit_sheet.py`：

```python
def evaluate_exit(sym: str, pos_cfg: dict, macro: dict) -> dict:
    """
    对单只持仓进行出场评估。在函数内部通过 yfinance 获取实时价格和技术数据。
    返回完整评估 dict。
    """
    sym = sym.upper()
    hard_stop, soft_stop, stop_source, tech = _compute_stop_levels(sym, pos_cfg)
    cur   = tech["cur"]   if tech else None
    atr14 = tech["atr14"] if tech else None

    hard_triggers        = []
    soft_triggers        = []
    falsification_check  = []  # 需人工确认的基本面条件

    # ── 硬触发 ──────────────────────────────────────────────────
    # H1: 价格 < 硬止损
    hard_dist_pct = None
    if cur is not None and hard_stop is not None:
        hard_dist_pct = round((cur - hard_stop) / cur * 100, 1)
        if cur < hard_stop:
            hard_triggers.append("price < hard_stop")

    # H2: thesis_status = broken
    if pos_cfg.get("thesis_status") == "broken":
        hard_triggers.append("thesis_status=broken")

    # H3/S3: 解析 falsification_conditions 中的时间条件
    for cond in (pos_cfg.get("falsification_conditions") or []):
        days, date_str = _parse_time_deadline(cond)
        if days is not None:
            if days <= 0:
                hard_triggers.append(f"time_condition_expired ({date_str})")
            elif days <= 3:
                soft_triggers.append(f"time_condition_expiring_{days}d")
                falsification_check.append(cond[:80])
            else:
                falsification_check.append(cond[:80])
        else:
            # 非时间条件：展示给用户确认
            falsification_check.append(cond[:80])

    # ── 软触发 ──────────────────────────────────────────────────
    # S1: thesis_status = weakening
    if pos_cfg.get("thesis_status") == "weakening":
        soft_triggers.append("thesis_status=weakening")

    # S2: 价格在浮亏区（soft_stop > cur > hard_stop）
    if cur is not None and hard_stop is not None and soft_stop is not None:
        if hard_stop < cur < soft_stop:
            soft_triggers.append("price_in_loss_zone")

    # S3: 接近硬止损（0% < hard_dist_pct < 3%）
    if hard_dist_pct is not None and 0 < hard_dist_pct < 3:
        soft_triggers.append("approaching_hard_stop")

    # S4: RR 剩余 < 1.0
    rr = None
    cost      = float(pos_cfg.get("t1_cost") or pos_cfg.get("cost") or 0)
    target_pct = pos_cfg.get("target_pct")
    if target_pct and cost > 0 and cur and hard_stop and cur > hard_stop:
        target = cost * (1 + float(target_pct) / 100)
        denom  = cur - hard_stop
        if denom > 0:
            rr = round((target - cur) / denom, 1)
            if rr < 1.0:
                soft_triggers.append("rr_remaining_low")

    # ── 决策 ────────────────────────────────────────────────────
    if hard_triggers:
        decision = "应出场"
        reason   = hard_triggers[0]
    elif soft_triggers:
        decision = "考虑减仓"
        reason   = " + ".join(soft_triggers[:2])
    else:
        decision = "继续持有"
        reason   = "无触发条件"

    return {
        "sym":                sym,
        "decision":           decision,
        "hard_stop":          hard_stop,
        "soft_stop":          soft_stop,
        "stop_source":        stop_source,
        "cur":                cur,
        "hard_dist_pct":      hard_dist_pct,
        "hard_triggers":      hard_triggers,
        "soft_triggers":      soft_triggers,
        "falsification_check": falsification_check,
        "rr_remaining":       rr,
        "reason":             reason,
    }
```

- [ ] **Step 4: 跑全部 10 个测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_exit_sheet.py -v
```
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/premarket_exit_sheet.py tests/test_premarket_exit_sheet.py
git commit -m "feat(exit): add evaluate_exit() with hard/soft trigger logic"
```

---

## Task 3: generate_exit_sheet() + write_exit_decision() + fmt_exit_sheet() + main()

**Files:**
- Modify: `agents/premarket_exit_sheet.py`

- [ ] **Step 1: 追加写文件测试**

```python
# 追加到 tests/test_premarket_exit_sheet.py

def test_write_exit_decision_creates_json(tmp_path, monkeypatch):
    """write_exit_decision 生成 exit_decision_{date}.json"""
    from agents.premarket_exit_sheet import write_exit_decision
    import agents.premarket_exit_sheet as mod
    monkeypatch.setattr(mod, "_FINDINGS", str(tmp_path))

    decisions = {
        "MRVU": {
            "decision": "考虑减仓", "hard_stop": 76.0, "soft_stop": 102.5,
            "stop_source": "manual_gtc", "cur": 88.4, "hard_dist_pct": 14.0,
            "hard_triggers": [], "soft_triggers": ["price_in_loss_zone"],
            "falsification_check": [], "rr_remaining": None, "reason": "浮亏区",
        }
    }
    write_exit_decision(decisions, findings_dir=str(tmp_path))

    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    out = tmp_path / f"exit_decision_{date_str}.json"
    assert out.exists()
    import json
    data = json.loads(out.read_text())
    assert "date" in data
    assert "positions" in data
    assert "MRVU" in data["positions"]
    assert data["positions"]["MRVU"]["decision"] == "考虑减仓"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_exit_sheet.py::test_write_exit_decision_creates_json -v 2>&1 | head -10
```

- [ ] **Step 3: 实现三个函数 + main()**

追加到 `agents/premarket_exit_sheet.py`：

```python
def generate_exit_sheet(pos_syms: list) -> dict:
    """
    批量评估持仓列表，返回 {sym: evaluate_exit() 结果}。
    从 positions.json 读取持仓配置，evaluate_exit 内部获取实时价格。
    """
    pos_data = _load_json(_POS_PATH).get("positions", {})
    macro    = _load_json(_MACRO_PATH)
    results  = {}
    for sym in pos_syms:
        sym     = sym.upper()
        pos_cfg = pos_data.get(sym, {})
        if not pos_cfg:
            continue
        results[sym] = evaluate_exit(sym, pos_cfg, macro)
    return results


def write_exit_decision(decisions: dict, findings_dir: str = None) -> None:
    """写入 findings/exit_decision_{date}.json"""
    _fdir = findings_dir or _FINDINGS
    os.makedirs(_fdir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output   = {"date": date_str, "positions": decisions}
    path     = os.path.join(_fdir, f"exit_decision_{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def fmt_exit_sheet(decisions: dict) -> str:
    """格式化为人类可读输出，含 ❌/⚠️/✅ 标记"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines    = [f"\n【今日持仓出场评估】{date_str}\n"]
    _icons   = {"应出场": "❌", "考虑减仓": "⚠️", "继续持有": "✅"}
    _src_label = {
        "manual_gtc": "GTC 已挂",
        "node1":      "node1",
        "auto_atr":   "⚠️ ATR估算，建议设 GTC",
    }
    for sym, d in decisions.items():
        icon = _icons.get(d.get("decision", ""), "?")
        lines.append(f"{sym}  {icon} {d.get('decision','?')}")

        hs   = d.get("hard_stop")
        ss   = d.get("soft_stop")
        cur  = d.get("cur")
        dist = d.get("hard_dist_pct")
        src  = _src_label.get(d.get("stop_source", ""), d.get("stop_source", ""))

        if hs is not None and cur is not None:
            dist_str = f"  距硬线 {dist:+.1f}%" if dist is not None else ""
            lines.append(f"  硬止损 ${hs:.2f}（{src}）  现价 ${cur:.2f}{dist_str}")
        if ss is not None:
            lines.append(f"  软止损（成本）${ss:.2f}")
        for t in d.get("hard_triggers", []):
            lines.append(f"  触发（硬）: {t}")
        for t in d.get("soft_triggers", []):
            lines.append(f"  触发（软）: {t}")
        for fc in d.get("falsification_check", []):
            lines.append(f"  ⚠️ 请确认证伪条件: {fc[:70]}")
        rr = d.get("rr_remaining")
        if rr is not None:
            lines.append(f"  RR剩余 {rr:.1f}x")
        lines.append("")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="持仓出场评估")
    parser.add_argument("symbols", nargs="*", help="持仓代码（空则评估所有持仓）")
    args = parser.parse_args()

    pos_data = _load_json(_POS_PATH).get("positions", {})
    if args.symbols:
        pos_syms = [s.upper() for s in args.symbols]
    else:
        pos_syms = [s for s, d in pos_data.items()
                    if (d.get("shares") or d.get("t1_shares") or 0) > 0]

    results = generate_exit_sheet(pos_syms)
    print(fmt_exit_sheet(results))
    write_exit_decision(results)
    print(f"✅ 出场评估写入 findings/exit_decision_{datetime.now().strftime('%Y-%m-%d')}.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑全部 11 个测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_exit_sheet.py -v
```
Expected: 11 passed

- [ ] **Step 5: CLI 冒烟测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_exit_sheet.py MRVU 2>&1 | tail -15
```
Expected: 含"MRVU  ⚠️ 考虑减仓"或"❌ 应出场"、止损价位、决策理由

- [ ] **Step 6: Commit**

```bash
cd ~/stock_team
git add agents/premarket_exit_sheet.py tests/test_premarket_exit_sheet.py
git commit -m "feat(exit): add generate_exit_sheet, write_exit_decision, fmt_exit_sheet, main CLI"
```

---

## Task 4: 集成 session_manager.py 和 premarket_decision.py

**Files:**
- Modify: `agents/session_manager.py` (Step 3.7)
- Modify: `agents/premarket_decision.py` (main() 末尾)

- [ ] **Step 1: 在 session_manager.py 加 Step 3.7**

在 Step 3.5（CIO 持仓健康，`elif cio_syms:` 块结束后）、Step 4（leader-pair，`# Step 4: leader-pair 快速触发检查`）之前，插入 Step 3.7。先确认位置：

```bash
grep -n "Step 3.5\|Step 4\|leader-pair\|elif cio_syms" agents/session_manager.py | head -10
```

插入 Step 3.7：

```python
        # Step 3.7: 持仓出场评估（与入场决策对称）
        lines.append("\n【Step 3.7】持仓出场评估")
        if pos_syms:
            try:
                from agents.premarket_exit_sheet import (
                    generate_exit_sheet, fmt_exit_sheet, write_exit_decision
                )
                _exit_decisions = generate_exit_sheet(pos_syms)
                lines.append(fmt_exit_sheet(_exit_decisions))
                write_exit_decision(_exit_decisions)
            except Exception as _e:
                lines.append(f"  出场评估失败: {_e}")
        else:
            lines.append("  无当前持仓，跳过")
```

注：`pos_syms` 在 Step 3（portfolio_risk）前已定义（来自 positions.json）。

- [ ] **Step 2: 在 premarket_decision.py main() 末尾调用出场评估**

找到 `premarket_decision.py` 的 `main()` 函数末尾（`write_entry_decision` 调用之后），追加：

```python
    # 同步生成持仓出场评估（与入场决策并列）
    try:
        from agents.premarket_exit_sheet import generate_exit_sheet, fmt_exit_sheet, write_exit_decision
        _exit_syms = [s for s in pos if (pos[s].get("shares") or pos[s].get("t1_shares") or 0) > 0]
        if _exit_syms:
            _exit_results = generate_exit_sheet(_exit_syms)
            print(fmt_exit_sheet(_exit_results))
            write_exit_decision(_exit_results)
    except Exception as _e:
        print(f"出场评估失败: {_e}")
```

- [ ] **Step 3: 验证 session_manager 和 premarket_decision 仍可 import**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "
from agents.session_manager import run_node
from agents.premarket_decision import main
print('all imports OK')
"
```
Expected: `all imports OK`

- [ ] **Step 4: 运行全部测试确认无回归**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_exit_sheet.py tests/test_output_files.py tests/test_premarket_decision.py -v --tb=no -q 2>&1 | tail -5
```
Expected: 所有测试通过，无回归

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/session_manager.py agents/premarket_decision.py
git commit -m "feat(exit): integrate exit sheet into node 0 Step 3.7 and premarket_decision main()"
```

---

## Task 5: CHANGELOG 更新

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: 在 CHANGELOG.md 顶部追加**

```
## 2026-05-20 出场决策模块（premarket_exit_sheet.py）

### 新建文件

- **新建** `agents/premarket_exit_sheet.py` — 持仓出场评估，与入场决策对称：
  - `_parse_time_deadline(text)` — 解析证伪条件中的"截止 YYYY-MM-DD"日期，计算剩余天数
  - `_fetch_price_and_atr(sym)` — yfinance 获取实时价格、ATR14、近5日低点
  - `_compute_stop_levels(sym, pos_cfg)` — 两层止损计算（manual_gtc > node1 > auto_atr）
  - `evaluate_exit(sym, pos_cfg, macro)` — 三态出场判断：应出场 / 考虑减仓 / 继续持有
  - `generate_exit_sheet(pos_syms)` — 批量评估，返回 {sym: result}
  - `write_exit_decision(decisions)` — 写 findings/exit_decision_{date}.json
  - `fmt_exit_sheet(decisions)` — 格式化输出（❌/⚠️/✅）
  - CLI: `python3.12 agents/premarket_exit_sheet.py [SYMS...]`

### 修改文件

- **修改** `agents/session_manager.py` — node 0 加 Step 3.7（持仓出场评估，在持仓健康之后）
- **修改** `agents/premarket_decision.py` — main() 末尾同步调用出场评估

### 测试

- `tests/test_premarket_exit_sheet.py` — 11项，覆盖止损计算、三态决策、时间条件解析、JSON写入
```

- [ ] **Step 2: Commit**

```bash
cd ~/stock_team
git add CHANGELOG.md
git commit -m "docs: CHANGELOG for exit decision module"
```

---

## 验收检查

| 验收点 | 验证方式 | 期望结果 |
|--------|---------|---------|
| 价格触发应出场 | `evaluate_exit` 测试 | price < hard_stop → hard_triggers 含 "price < hard_stop" |
| ATR 自动估算 | `evaluate_exit("BABA", pos_no_stop, {})` | stop_source="auto_atr"，输出含 ⚠️ |
| 时间条件解析 | `_parse_time_deadline` 测试 | 2天→软触发，过期→硬触发，>3天→仅展示 |
| JSON 输出 | `write_exit_decision` 测试 | exit_decision_{date}.json 含 date + positions |
| Node 0 集成 | `python3.12 morning.py` | Step 3.7 显示各持仓出场评估 |
| CLI 运行 | `python3.12 agents/premarket_exit_sheet.py` | 打印各持仓评估 + 写 JSON |
