# Constrained Mode 盘前系统重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将盘前流程从 Active Mode 架构迁移到 Constrained Mode——移除死代码（ML/社群 Agent）、标准化输出（每个脚本写 JSON）、让 poll.py 成为 entry_decision 的下游。

**Architecture:** 四个 Phase 顺序执行：B1（删死代码）→ A（输出标准化）→ C（poll 集成）→ D（node 0 重写）。B1 最安全，先做。D 依赖前三个完成。

**Tech Stack:** Python 3.12, json, subprocess, yfinance（已有依赖）

---

## File Map

| 状态 | 路径 | 变更内容 |
|------|------|---------|
| 修改 | `agents/cio.py` | 删 IntuitionAgent + CommunityAgent（B1）|
| 修改 | `agents/candidate_scanner.py` | 删 intuition_agent 加分块（B1）|
| 修改 | `agents/premarket_order_sheet.py` | 增加写 order_sheet + daily_plan compat（A）|
| 修改 | `agents/premarket_decision.py` | 增加写 entry_decision（A）|
| 修改 | `agents/poll.py` | 加 _load_entry_decision() + per-symbol 决策检查（C）|
| 修改 | `agents/session_manager.py` | node 0 重写（D）|
| 新建 | `tests/test_output_files.py` | A 的输出文件测试 |
| 新建 | `tests/test_poll_entry_decision.py` | C 的集成测试 |

---

## Phase B1：删除死代码

### Task 1: 从 cio.py 删除 IntuitionAgent + CommunityAgent

**Files:**
- Modify: `agents/cio.py` (lines 10-25, 165)

- [ ] **Step 1: 确认当前状态**

```bash
cd ~/stock_team && grep -n "intuition_agent\|community_agent\|CommunityAgent\|IntuitionAgent" agents/cio.py
```
Expected: 出现在 ANALYSIS_AGENTS 列表和 AGENT_CLASS_MAP 中

- [ ] **Step 2: 从 ANALYSIS_AGENTS 列表删除两个 agent**

找到 `agents/cio.py` 的 `ANALYSIS_AGENTS` 列表（第10-14行附近），将：
```python
ANALYSIS_AGENTS = [
    "tech_agent", "fund_agent", "macro_agent",
    "sentiment_agent", "community_agent", "risk_agent",
    "sector_agent", "intuition_agent",
]
```
改为：
```python
ANALYSIS_AGENTS = [
    "tech_agent", "fund_agent", "macro_agent",
    "sentiment_agent", "risk_agent",
    "sector_agent",
]
```

- [ ] **Step 3: 从 AGENT_CLASS_MAP 删除两个映射**

找到同文件的 `AGENT_CLASS_MAP` 字典，删除：
```python
"community_agent":  "CommunityAgent",
"intuition_agent":  "IntuitionAgent",
```

- [ ] **Step 4: 更新 check_consensus() 的 _AGENTS 列表和阈值**

在同文件约第164行的 `check_consensus()` 函数内（注意：不是 phase1_5），找到：
```python
def check_consensus(board):
    _AGENTS = ["TechAgent","FundAgent","MacroAgent","SentimentAgent","CommunityAgent","RiskAgent"]
    ...
    if len(signals) < 6: return False
```
改为（删除 CommunityAgent，同时更新两个阈值）：
```python
def check_consensus(board):
    _AGENTS = ["TechAgent","FundAgent","MacroAgent","SentimentAgent","RiskAgent","SectorAgent"]
    ...
    if len(signals) < 5: return False          # 阈值1: 6→5（agent 总数减1）
    majority = max(set(signals), key=signals.count)
    if signals.count(majority) < 4: return False  # 阈值2: 5→4（保持约83%多数票比例）
```
**必须同时改两个阈值**：阈值1从 `< 6` 改为 `< 5`；阈值2从 `< 5` 改为 `< 4`（维持原来约83%多数票比例，否则变成要求全票通过）。

- [ ] **Step 5: 验证**

```bash
cd ~/stock_team && grep -n "intuition_agent\|community_agent\|CommunityAgent\|IntuitionAgent" agents/cio.py
```
Expected: 无输出（已全部删除）

- [ ] **Step 6: Commit**

```bash
cd ~/stock_team
git add agents/cio.py
git commit -m "feat(B1): remove IntuitionAgent + CommunityAgent from CIO - ML never worked, community signal irrelevant"
```

---

### Task 2: 从 candidate_scanner.py 删除 intuition_agent 加分块

**Files:**
- Modify: `agents/candidate_scanner.py` (lines 138-157)

- [ ] **Step 1: 确认当前代码块**

```bash
cd ~/stock_team && sed -n '135,162p' agents/candidate_scanner.py
```
Expected: 看到 `# D. 历史直觉评分` + try/except 块

- [ ] **Step 2: 删除整个 intuition_agent 块**

找到并删除以下整段代码（`score_candidate()` 函数内，约 138-157 行）：

```python
    # D. 历史直觉评分（若模型存在）
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.expanduser("~/stock_team"))
        import yfinance as _yf
        from learning.features import extract_intraday_features, extract_swing_features
        from agents.intuition_agent import score_symbol
        _h = _yf.Ticker(snap["sym"]).history(period="60d")
        if not _h.empty:
            _fi = extract_intraday_features(_h, peer_chg=snap.get("gap_pct", 0))
            _fs = extract_swing_features(_h, short_pct=snap.get("short_pct", 0))
            _result = score_symbol(snap["sym"], {**_fi, **_fs})
            if _result:
                _swing = _result.get("swing", 0)
                if _swing > 0.65:
                    _bonus = int((_swing - 0.65) * 200)
                    score += _bonus
                    reasons.append(f"历史波段命中率{_swing*100:.0f}%")
    except Exception:
        pass
```

- [ ] **Step 3: 验证 score_candidate 函数仍可调用**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "
from agents.candidate_scanner import score_candidate, get_stock_snapshot
snap = {'sym': 'AAPL', 'gap_pct': 0, 'short_pct': 0}
print('score_candidate importable:', callable(score_candidate))
"
```
Expected: `score_candidate importable: True`（无 ImportError）

- [ ] **Step 4: Commit**

```bash
cd ~/stock_team
git add agents/candidate_scanner.py
git commit -m "feat(B1): remove intuition_agent bonus from candidate_scanner - ML dead code"
```

---

## Phase A：输出标准化

### Task 3: premarket_order_sheet.py 写 order_sheet + daily_plan compat

**Files:**
- Modify: `agents/premarket_order_sheet.py`
- Create: `tests/test_output_files.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_output_files.py
import sys, os, json, tempfile
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch, MagicMock
from datetime import datetime


def _mock_technicals():
    return {
        "cur": 870.0, "ma20": 920.0, "atr14": 50.0,
        "lo5": 857.0, "lo10": 840.0, "hi20": 960.0, "ma20_dev": -5.4,
    }


def test_order_sheet_writes_json_files(tmp_path, monkeypatch):
    """generate_order_sheet 运行后写入 order_sheet + daily_plan compat 两个文件"""
    import agents.premarket_order_sheet as mod
    monkeypatch.setattr(mod, "_FUND_DIR",     str(tmp_path))
    monkeypatch.setattr(mod, "_REGIME_PATH",  str(tmp_path / "regime.json"))
    monkeypatch.setattr(mod, "_POS_PATH",     str(tmp_path / "pos.json"))
    monkeypatch.setattr(mod, "_MACRO_PATH",   str(tmp_path / "macro.json"))

    # 写入假文件
    (tmp_path / "regime.json").write_text('{"regime":"trending_up","overnight_signal":""}')
    (tmp_path / "pos.json").write_text('{"positions":{}}')
    (tmp_path / "macro.json").write_text('{"macro_tone":"中性"}')

    with patch("agents.premarket_order_sheet._get_technicals") as mock_tech, \
         patch("agents.premarket_order_sheet._get_overnight_data") as mock_ov, \
         patch("agents.premarket_order_sheet._load_json") as mock_load:

        mock_tech.return_value = _mock_technicals()
        mock_ov.return_value = {"overnight_price": None, "overnight_chg": None, "already_in_zone": None}

        def _load_side(path, default=None):
            p = str(path)
            if "regime" in p: return {"regime": "trending_up", "overnight_signal": ""}
            if "pos" in p:    return {"positions": {}}
            if "macro" in p:  return {"macro_tone": "中性"}
            return default or {}
        mock_load.side_effect = _load_side

        # 调用并写文件
        date_str = datetime.now().strftime("%Y-%m-%d")
        d = mod.generate_order_sheet("LITE")
        mod.write_order_sheet_files({"LITE": d}, findings_dir=str(tmp_path), base_dir=str(tmp_path))

    # 验证 order_sheet_{date}.json
    order_file = tmp_path / f"order_sheet_{date_str}.json"
    assert order_file.exists(), f"order_sheet 文件未生成: {order_file}"
    order_data = json.loads(order_file.read_text())
    assert "LITE" in order_data
    assert "stop_loss" in order_data["LITE"]

    # 验证 daily_plan_{date}.json compat 格式
    plan_file = tmp_path / f"daily_plan_{date_str}.json"
    assert plan_file.exists(), f"daily_plan compat 文件未生成: {plan_file}"
    plan_data = json.loads(plan_file.read_text())
    assert "stocks" in plan_data
    lite = plan_data["stocks"].get("LITE", {})
    assert "stop" in lite
    assert "t1_target" in lite
    assert "t2_target" in lite
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_output_files.py::test_order_sheet_writes_json_files -v 2>&1 | head -15
```
Expected: `AttributeError`（write_order_sheet_files 不存在）

- [ ] **Step 3: 实现 write_order_sheet_files()**

在 `agents/premarket_order_sheet.py` 的 `fmt_order_sheet()` 之后添加：

```python
def write_order_sheet_files(sheets: dict, findings_dir: str = None,
                             base_dir: str = None) -> None:
    """
    将订单表字典写入两个文件：
    1. findings/order_sheet_{date}.json — 结构化订单表
    2. daily_plan_{date}.json — poll.py 兼容格式（stop/t1_target/t2_target）
    """
    import os as _os
    from datetime import datetime as _dt

    _base     = base_dir     or _BASE
    _findings = findings_dir or _FUND_DIR
    _os.makedirs(_findings, exist_ok=True)

    date_str = _dt.now().strftime("%Y-%m-%d")

    # 文件1：结构化订单表
    order_out = _os.path.join(_findings, f"order_sheet_{date_str}.json")
    with open(order_out, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_str,
            "symbols": {sym: {k: v for k, v in d.items()
                              if not isinstance(v, tuple)}
                        for sym, d in sheets.items()},
        }, f, ensure_ascii=False, indent=2)

    # 文件2：daily_plan compat（poll.py 读取 plan.get("stocks",{}).get(sym)）
    plan_stocks = {}
    for sym, d in sheets.items():
        tgt = d.get("target_price", 0)
        plan_stocks[sym] = {
            "stop":      d.get("stop_loss", 0),
            "t1_target": tgt,
            "t2_target": round(float(tgt) * 1.04, 2) if tgt else 0,
        }
    plan_out = _os.path.join(_base, f"daily_plan_{date_str}.json")
    existing = {}
    if _os.path.exists(plan_out):
        try:
            with open(plan_out, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.setdefault("stocks", {}).update(plan_stocks)
    with open(plan_out, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
```

同时在 `main()` 函数中，在打印输出后添加写文件调用：

```python
    # main() 末尾，在 if args.json: 之后添加：
    if not args.json:
        write_order_sheet_files(sheets)
```

- [ ] **Step 4: 跑测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_output_files.py -v
```
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/premarket_order_sheet.py tests/test_output_files.py
git commit -m "feat(A): premarket_order_sheet writes order_sheet + daily_plan compat JSON files"
```

---

### Task 4: premarket_decision.py 写 entry_decision_{date}.json

**Files:**
- Modify: `agents/premarket_decision.py`
- Modify: `tests/test_output_files.py`

- [ ] **Step 1: 追加失败测试**

```python
# 追加到 tests/test_output_files.py

def test_entry_decision_writes_json(tmp_path, monkeypatch):
    """premarket_decision main() 写入 entry_decision_{date}.json"""
    import agents.premarket_decision as mod
    monkeypatch.setattr(mod, "_THRESHOLDS_PATH", "/nonexistent")
    monkeypatch.setattr(mod, "_MACRO_PATH",      str(tmp_path / "macro.json"))
    monkeypatch.setattr(mod, "_REGIME_PATH",     str(tmp_path / "regime.json"))
    monkeypatch.setattr(mod, "_POS_PATH",        str(tmp_path / "pos.json"))
    monkeypatch.setattr(mod, "_FINDINGS",        str(tmp_path))

    (tmp_path / "macro.json").write_text('{"macro_score":6,"yield_curve":"正常","dxy":99}')
    (tmp_path / "regime.json").write_text('{"regime":"trending_up","overnight_signal":"LITE+3%"}')
    (tmp_path / "pos.json").write_text('{"positions":{"BABA":{"thesis_status":"intact","macro_type":"成长型+中概","macro_sensitivity":{}}}}')

    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")

    with patch("agents.premarket_decision._is_stage2_insufficient", return_value=False):
        # 直接调用 write_entry_decision（不需要 mock _load_entry_decision，该函数不在此模块）
        decisions = {
            "LITE": {"decision": "可入场", "hard_vetoes": [], "soft_vetoes": [],
                     "reason": "通过", "score": 75, "rr_ratio": 3.5}
        }
        pos_syms = ["BABA"]
        mod.write_entry_decision(decisions, pos_syms, findings_dir=str(tmp_path))

    out_file = tmp_path / f"entry_decision_{date_str}.json"
    assert out_file.exists(), f"entry_decision 文件未生成"
    data = json.loads(out_file.read_text())
    assert "decisions" in data
    assert "LITE" in data["decisions"]
    assert "poll_needed" in data
    assert "poll_symbols" in data
    # BABA（持仓）应在 poll_symbols 中
    assert "BABA" in data["poll_symbols"]
    # LITE（可入场）应在 poll_symbols 中
    assert "LITE" in data["poll_symbols"]
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_output_files.py::test_entry_decision_writes_json -v 2>&1 | head -15
```

- [ ] **Step 3: 实现 write_entry_decision() + _FINDINGS 常量**

在 `agents/premarket_decision.py` 中，在现有常量之后添加：

```python
_FINDINGS = os.path.join(_BASE, "findings")
```

在 `evaluate_entry()` 之后添加：

```python
def write_entry_decision(decisions: dict, pos_syms: list,
                          findings_dir: str = None) -> None:
    """
    将决策结果写入 findings/entry_decision_{date}.json。

    decisions: {sym: evaluate_entry() 返回值}
    pos_syms:  当前持仓股代码列表（不论决策如何，都需要监控）
    """
    from datetime import datetime as _dt
    _fdir = findings_dir or _FINDINGS
    os.makedirs(_fdir, exist_ok=True)

    date_str = _dt.now().strftime("%Y-%m-%d")

    # poll_symbols: 决策非"不入场"的焦点股 + 所有持仓
    entry_syms = [sym for sym, d in decisions.items()
                  if d.get("decision") != "不入场"]
    poll_syms  = list(dict.fromkeys(entry_syms + list(pos_syms)))
    poll_needed = bool(poll_syms)

    output = {
        "date":         date_str,
        "decisions":    decisions,
        "poll_needed":  poll_needed,
        "poll_symbols": poll_syms,
    }
    out_path = os.path.join(_fdir, f"entry_decision_{date_str}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
```

将整个 `main()` 函数替换为以下完整版本（在循环中收集 all_results，结束后写文件）：

```python
def main():
    import argparse
    import yfinance as yf
    from agents.premarket_order_sheet import generate_order_sheet
    from agents.premarket_watchlist_score import score_stock
    from datetime import datetime as _dt

    parser = argparse.ArgumentParser(description="盘前入场决策框架")
    parser.add_argument("symbols", nargs="+", help="股票代码，如 LITE RKLB")
    args = parser.parse_args()

    macro  = _load_json(os.path.join(_BASE, "findings", "macro.json"))
    regime = _load_json(_REGIME_PATH)
    pos    = _load_json(_POS_PATH).get("positions", {})

    try:
        info     = yf.Ticker("QQQ").info
        qqq_cur  = info.get("regularMarketPrice", 0)
        qqq_prev = info.get("regularMarketPreviousClose", qqq_cur)
        qqq_chg  = (qqq_cur - qqq_prev) / qqq_prev if qqq_prev else 0
    except Exception:
        qqq_chg = 0.0

    all_results = {}   # {sym: evaluate_entry() result}
    for sym in args.symbols:
        sym        = sym.upper()
        pos_cfg    = pos.get(sym, {})
        thresholds = load_thresholds(macro_type=pos_cfg.get("macro_type", ""))
        os_data    = generate_order_sheet(sym)
        wr         = score_stock(sym, macro, regime, pos_cfg=pos_cfg)

        result = evaluate_entry(
            sym=sym, order_sheet=os_data, watchlist_result=wr,
            macro=macro, pos_cfg=pos_cfg, regime=regime,
            qqq_premarket_chg=qqq_chg, thresholds=thresholds,
        )
        print(fmt_decision(result))
        all_results[sym] = result

    # 写 entry_decision_{date}.json
    _pos_syms = [s for s in pos if (pos[s].get("shares") or pos[s].get("t1_shares") or 0) > 0]
    write_entry_decision(all_results, _pos_syms)
    print(f"\n✅ 决策写入 findings/entry_decision_{_dt.now().strftime('%Y-%m-%d')}.json")
```

- [ ] **Step 4: 跑所有输出文件测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_output_files.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/premarket_decision.py tests/test_output_files.py
git commit -m "feat(A): premarket_decision writes entry_decision_{date}.json with poll_needed + poll_symbols"
```

---

## Phase C：poll.py 集成 entry_decision

### Task 5: poll.py 加 _load_entry_decision() + per-symbol 决策检查

**Files:**
- Modify: `agents/poll.py`
- Create: `tests/test_poll_entry_decision.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_poll_entry_decision.py
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch


def test_load_entry_decision_returns_dict(tmp_path, monkeypatch):
    """_load_entry_decision 正常读取文件时返回 decisions dict"""
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")

    data = {
        "date": date_str,
        "decisions": {
            "LITE": {"decision": "可入场", "soft_vetoes": []},
            "MRVU": {"decision": "不入场", "hard_vetoes": ["RR不足"]},
        },
        "poll_needed": True,
        "poll_symbols": ["LITE"],
    }
    f = tmp_path / f"entry_decision_{date_str}.json"
    f.write_text(json.dumps(data))

    import agents.poll as poll_mod
    with patch.object(poll_mod, "_STOCK_BASE", str(tmp_path)):
        result = poll_mod._load_entry_decision()

    assert result["LITE"]["decision"] == "可入场"
    assert result["MRVU"]["decision"] == "不入场"


def test_load_entry_decision_returns_empty_on_missing():
    """_load_entry_decision 文件不存在时返回空 dict（向后兼容）"""
    import agents.poll as poll_mod
    with patch.object(poll_mod, "_STOCK_BASE", "/nonexistent/path"):
        result = poll_mod._load_entry_decision()
    assert result == {}
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_poll_entry_decision.py -v 2>&1 | head -15
```
Expected: `AttributeError`（_load_entry_decision 不存在）

- [ ] **Step 3: 在 poll.py 中添加 _load_entry_decision()**

在 `agents/poll.py` 文件顶部的工具函数区域（`snap()` 附近），添加：

```python
def _load_entry_decision() -> dict:
    """
    读取今日 findings/entry_decision_{date}.json 的 decisions 字段。
    文件不存在或解析失败时返回 {} （向后兼容，所有标的按原逻辑处理）。
    """
    try:
        from datetime import datetime as _dt
        date_str  = _dt.now().strftime("%Y-%m-%d")
        findings  = os.path.join(_STOCK_BASE, "findings")
        path      = os.path.join(findings, f"entry_decision_{date_str}.json")
        if not os.path.exists(path):
            return {}
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("decisions", {})
    except Exception:
        return {}
```

- [ ] **Step 4: 在 run_poll() 中加载 entry_decision，在各标的详情循环中集成**

在 `run_poll()` 函数内，读取 trading config 之后（约 `_trading_mode = ...` 之后），添加：

```python
    # 读取今日盘前入场决策（Constrained Mode 下过滤信号）
    _entry_decisions = _load_entry_decision()
```

在 `# 各标的详情 + ATR止损` 的 for 循环（`for sym, rs, a in rs_list:`）内，在 `strategy_gate()` 调用之前插入：

```python
        # Constrained Mode: 盘前已决策"不入场"的焦点股 → 跳过 strategy_gate，只显示基础信息
        _sym_decision = _entry_decisions.get(sym)
        if _sym_decision and _sym_decision.get("decision") == "不入场" and _trading_mode == "constrained":
            _hard = _sym_decision.get("hard_vetoes", [])
            print(f"│ 盘前决策: ❌ 不入场 — {_hard[0] if _hard else _sym_decision.get('reason','')}")
            print(f"└{'─'*59}")
            continue   # 跳过 strategy_gate 和入场逻辑

        # Constrained Mode: 盘前"观察"状态 → 显示软否决提醒
        if _sym_decision and _sym_decision.get("decision") == "观察" and _trading_mode == "constrained":
            _soft = _sym_decision.get("soft_vetoes", [])
            if _soft:
                print(f"│ 盘前决策: ⚠️ 观察中 — 软否决: {', '.join(_soft[:2])}")
```

- [ ] **Step 5: 跑 poll 集成测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_poll_entry_decision.py -v
```
Expected: 2 passed

- [ ] **Step 6: 验证 poll.py 仍可正常 import**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "import agents.poll; print('poll import OK')"
```
Expected: `poll import OK`

- [ ] **Step 7: Commit**

```bash
cd ~/stock_team
git add agents/poll.py tests/test_poll_entry_decision.py
git commit -m "feat(C): poll.py reads entry_decision - suppresses buy signal for 不入场 stocks in constrained mode"
```

---

## Phase D：session_manager.py node 0 重写

### Task 6: 删除死步骤 + 重构 node 0

**Files:**
- Modify: `agents/session_manager.py` (node 0 section, ~lines 187-446)

这是最大的改动，分两步：先删，再重组。

- [ ] **Step 0: 了解现有代码状态（必读，避免误删）**

session_manager.py 已在本次改造早期添加了 Steps 6.6-6.8（premarket_watchlist_score + premarket_order_sheet + premarket_decision），这些步骤**必须保留**，不要删除。`_focus_syms` 变量在 Step 6.6 的 constrained mode 块中被赋值（读取 today_focus.json）。

```bash
cd ~/stock_team && grep -n "Step 6\.\|_focus_syms\|today_focus\|premarket_watchlist_score\|premarket_order_sheet\|premarket_decision" agents/session_manager.py | head -20
```

- [ ] **Step 1: 确认当前 node 0 步骤边界**

```bash
cd ~/stock_team && grep -n "Step.*7\]\|Step.*8\]\|model health\|watchlist_permanent\|daily_plan.*generate\|CIO全量" agents/session_manager.py | head -20
```

- [ ] **Step 2: 删除 model health check（node 0 Step 0 的模型退化检查）**

找到以下代码块（约 244-251 行）并删除：

```python
        # 模型退化检查
        harvest_path = os.path.join(BASE, "learning", "daily_harvest.jsonl")
        if os.path.exists(harvest_path):
            rows = [json.loads(l) for l in open(harvest_path) if l.strip()]
            recent = rows[-20:]
            if recent:
                pos_rate = sum(1 for r in recent if r.get("label") == 1) / len(recent)
                health = "✅ 正常" if 0.15 < pos_rate < 0.85 else "⚠️  可能退化"
                lines.append(f"  模型健康: {health}（近{len(recent)}条正例率{pos_rate:.0%}）")
```

- [ ] **Step 3: 删除 watchlist_permanent 晨检（Step 2）**

找到并删除以下代码块（约 270-281 行）：

```python
        # Step 2: 永久观察列表 pending_review 检查
        lines.append("\n【Step 2/7】永久观察列表更新")
        wl_path = os.path.join(BASE, "watchlist_permanent.json")
        if os.path.exists(wl_path):
            wl = json.load(open(wl_path))
            pending = list(wl.get("pending_review", {}).keys())
            if pending:
                lines.append(f"  待评估标的({len(pending)}只): {' '.join(pending[:8])}")
                lines.append("  → 提示: 说'评估[标的]'可以做基本面深度评估")
            else:
                lines.append("  永久列表无待评估标的")
```

- [ ] **Step 4: 替换 Step 4 候选池扫描为 leader-pair 快速触发**

找到以下代码块（约 290-296 行）：

```python
        # Step 4: 候选池扫描
        lines.append("\n【Step 4/7】候选池扫描（宏观+质量过滤+领头羊联动）")
        r1 = subprocess.run(
            [PYTHON, os.path.join(AGENTS_DIR, "candidate_scanner.py"), "--top", "8"],
            cwd=BASE, capture_output=True, text=True, timeout=180
        )
        lines.append(_get_out(r1, fallback="（无候选数据）", maxlen=2000))
```

替换为：

```python
        # Step 4: leader-pair 快速触发检查（不做全量扫描）
        lines.append("\n【Step 4】leader-pair 触发检查")
        try:
            from agents.candidate_scanner import check_leader_triggers
            _triggers = check_leader_triggers()
            if _triggers:
                for _sym, _leaders in _triggers.items():
                    lines.append(f"  ⚡ {_sym} 被触发（{', '.join(_leaders)}）→ 加入今日关注")
                    if _sym not in (active_syms or []):
                        active_syms = list(active_syms or []) + [_sym]
            else:
                lines.append("  无领头羊触发")
        except Exception as _e:
            lines.append(f"  leader-pair 检查失败: {_e}")
```

- [ ] **Step 5: 将 premarket.py 调用改为只跑焦点股+持仓**

找到 Step 6 的 premarket.py 调用（约 344 行）：

```python
        lines.append(f"\n【Step 6/7】盘前分析（{len(all_syms)}只: {' '.join(all_syms[:6])}...）")
        if all_syms:
            r2 = subprocess.run(
                [PYTHON, os.path.join(AGENTS_DIR, "premarket.py")] + all_syms,
```

改为只传焦点股和持仓（`_focus_syms` 在 Step 6.6 的 constrained mode 块中已被赋值；此处 `_focus_syms` 可能还未赋值，需安全处理）：

```python
        # 确定盘前分析标的：焦点股+持仓（不跑全量watchlist）
        # 注：_focus_syms 在 Step 6.6 中赋值，若未跑 Step 6.6 则为空
        _premarket_syms = list(dict.fromkeys(
            (locals().get("_focus_syms") or []) + pos_syms
        ))
        if not _premarket_syms:
            _premarket_syms = list(dict.fromkeys(cand_syms[:3] + pos_syms))
        lines.append(f"\n【Step 5】盘前分析（{len(_premarket_syms)}只: {' '.join(_premarket_syms)}）")
        if _premarket_syms:
            r2 = subprocess.run(
                [PYTHON, os.path.join(AGENTS_DIR, "premarket.py")] + _premarket_syms,
                cwd=BASE, capture_output=True, text=True, timeout=300
            )
            lines.append(_get_out(r2, fallback="（无盘前数据）", maxlen=4000))
```

- [ ] **Step 6: 改造 Step 7 CIO 为周一 Phase 1（6 agent，无辩论）**

找到 Step 7 CIO 全量分析（约 412-430 行）的条件判断，在 `if cio_syms:` 之前，加周一判断：

```python
        import calendar as _cal
        _is_monday = datetime.now().weekday() == 0   # 0 = Monday

        if cio_syms and _is_monday:
            lines.append(f"\n【Step 3.5】持仓健康周报（CIO Phase 1，周一例行，约2分钟）")
            lines.append(f"  标的: {' '.join(cio_syms)}")
            # Phase 1 only (no debate), 6 agents (Intuition+Community already removed)
            try:
                from agents.cio import run_parallel as _cio_parallel
                _cio_res, _ = _cio_parallel(cio_syms, phases="01", timeout=180)
                _review = {"date": datetime.now().strftime("%Y-%m-%d"), "symbols": {}}
                for _sym, _res in _cio_res.items():
                    _sig  = _res.get("master_signal", _res.get("signal", "neutral"))
                    _conf = _res.get("master_conf",   _res.get("confidence", 0))
                    _icon = "✅" if _sig == "bullish" else "🔴" if _sig == "bearish" else "⚠️"
                    lines.append(f"  {_icon} [{_sym}] {_sig}({_conf}%)")
                    _review["symbols"][_sym] = {
                        "signal": _sig, "confidence": _conf,
                        "recommendation": "hold" if _sig != "bearish" else "review_needed"
                    }
                # 写 holdings_review_{date}.json
                _rev_path = os.path.join(BASE, "findings",
                                          f"holdings_review_{datetime.now().strftime('%Y-%m-%d')}.json")
                import json as _json_mod
                with open(_rev_path, "w", encoding="utf-8") as _rf:
                    _json_mod.dump(_review, _rf, ensure_ascii=False, indent=2)
                lines.append(f"  周报写入: {_rev_path}")
            except Exception as _e:
                lines.append(f"  CIO Phase 1 失败: {_e}")
        elif cio_syms:
            lines.append(f"\n【Step 3.5】持仓健康：非周一，跳过 CIO 周报（上次：检查 findings/holdings_review_*.json）")
            # thesis=weakening 提示
            for _sym in cio_syms:
                _ts = positions.get(_sym, {}).get("thesis_status", "intact") if 'positions' in dir() else "intact"
                if _ts in ("weakening", "broken"):
                    lines.append(f"  ⚠️  {_sym} 论点{_ts} — 建议运行深度审查:")
                    lines.append(f"     python3.12 agents/cio.py {_sym} --phases 0123")
```

同时**删除**原有的每日全量 CIO 代码块（`if cio_syms: lines.append(f"\n【Step 7】CIO全量分析...")` 整块）。

- [ ] **Step 7: 删除 Step 8 daily_plan.py**

找到并删除以下代码块（约 432-441 行）：

```python
        # Step 8: 今日交易计划（入场价位 + 止损 + 目标价）
        lines.append(f"\n【Step 8】今日交易计划（价位预设）")
        if all_syms:
            r_dp = subprocess.run(
                [PYTHON, os.path.join(AGENTS_DIR, "daily_plan.py"), "generate"] + all_syms,
                cwd=BASE, capture_output=True, text=True, timeout=60
            )
            lines.append(_get_out(r_dp, fallback="（计划生成失败，premarket 文件可能未就绪）", maxlen=1500))
        else:
            lines.append("  无标的，跳过")
```

- [ ] **Step 8: 在 node 0 结语加 entry_decision 读取 + poll 建议**

将原有的结语（约 443-446 行）：

```python
        lines.append(f"\n{'═'*50}")
        lines.append(f"✅ 晨间准备完成  宏观:{macro if 'macro' in dir() else '?'}")
        lines.append(f"今日关注标的({len(all_syms)}只): {' '.join(all_syms)}")
        lines.append("→ 9:30 说'开盘了'进入盘中监控，或说'再看看XXX'做追加分析")
```

替换为：

```python
        lines.append(f"\n{'═'*50}")
        lines.append(f"✅ 晨间准备完成")

        # 读取 entry_decision 输出 poll 建议
        _ed_path = os.path.join(BASE, "findings",
                                 f"entry_decision_{datetime.now().strftime('%Y-%m-%d')}.json")
        try:
            with open(_ed_path, encoding="utf-8") as _edf:
                _ed = json.load(_edf)
            _poll_syms = _ed.get("poll_symbols", [])
            _poll_needed = _ed.get("poll_needed", False)
            _dec_summary = []
            for _s, _d in _ed.get("decisions", {}).items():
                _icon = {"可入场": "✅", "观察": "⚠️", "不入场": "❌"}.get(_d.get("decision",""), "?")
                _dec_summary.append(f"{_icon}{_s}")
            lines.append(f"盘前决策: {' | '.join(_dec_summary) or '无'}")
            if _poll_needed and _poll_syms:
                _sym_str = " ".join(_poll_syms)
                lines.append(f"\n📡 今日需要轮询（{len(_poll_syms)}只标的）")
                lines.append(f"启动命令：")
                lines.append(f"/loop 2m /tool/pandora/bin/python3.12 agents/poll.py {_sym_str} --session 2>&1 | tail -60")
            else:
                lines.append(f"\n✅ 今日无入场机会，GTC 单已接管，无需轮询")
                if pos_syms:
                    lines.append(f"若持仓有异常可手动：python3.12 agents/poll.py {' '.join(pos_syms)} --session")
        except Exception:
            _fs_safe = locals().get("_focus_syms") or []
            lines.append(f"今日关注标的({len(_fs_safe)}只): {' '.join(_fs_safe)}")
            lines.append("→ 9:30 说'开盘了'进入盘中监控")
```

- [ ] **Step 9: 验证 node 0 可以运行**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "
from agents.session_manager import run_node
print('session_manager importable OK')
" 2>&1
```
Expected: `session_manager importable OK`

- [ ] **Step 10: Commit**

```bash
cd ~/stock_team
git add agents/session_manager.py
git commit -m "feat(D): node 0 rewrite - remove dead steps, CIO weekly-only, poll suggested by entry_decision"
```

---

## Task 7: CHANGELOG 更新

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: 在 CHANGELOG 顶部追加**

```
## 2026-05-19 Constrained Mode 盘前系统重构

### 移除的死代码（B1）
- `agents/cio.py`: 删除 IntuitionAgent（ML 从未跑通）和 CommunityAgent（机构股无社群信号价值），ANALYSIS_AGENTS 从 8 → 6
- `agents/candidate_scanner.py`: 删除 intuition_agent 加分块（依赖已失效 ML 模型）

### 输出标准化（A）
- `agents/premarket_order_sheet.py`: 新增 `write_order_sheet_files()`，生成 `findings/order_sheet_{date}.json` + `daily_plan_{date}.json`（poll.py 兼容格式）
- `agents/premarket_decision.py`: 新增 `write_entry_decision()`，生成 `findings/entry_decision_{date}.json`（含 decisions/poll_needed/poll_symbols）

### poll.py 集成（C）
- `agents/poll.py`: 新增 `_load_entry_decision()`，在 Constrained Mode 下对"不入场"焦点股跳过 strategy_gate，对"观察"股显示软否决提醒

### node 0 重写（D）
- 删除：model health check、watchlist_permanent 晨检、candidate_scanner 全量扫描、CIO 每日全量、daily_plan.py Step 8
- 改造：Step 4 → leader-pair 快速触发；premarket.py → 只跑焦点股+持仓；CIO → 周一 Phase 1 + thesis=weakening 提示
- 新增：node 0 结语读取 entry_decision，自动输出今日 poll 启动命令或"无需轮询"提示
```

- [ ] **Step 2: Commit**

```bash
cd ~/stock_team
git add CHANGELOG.md
git commit -m "docs: CHANGELOG for constrained mode flow redesign"
```

---

## 验收检查

| 验收点 | 验证命令 | 期望结果 |
|--------|---------|---------|
| B1: 无 IntuitionAgent/CommunityAgent | `grep -n "IntuitionAgent\|CommunityAgent" agents/cio.py` | 无输出 |
| B1: candidate_scanner 无 intuition | `grep -n "intuition_agent" agents/candidate_scanner.py` | 无输出 |
| A: order_sheet 文件生成 | `python3.12 agents/premarket_order_sheet.py LITE` | findings/order_sheet_{date}.json 存在 |
| A: daily_plan compat 格式 | `python3.12 -c "import json; d=json.load(open('daily_plan_$(date +%Y-%m-%d).json')); print('stocks' in d)"` | True |
| A: entry_decision 文件生成 | `python3.12 agents/premarket_decision.py LITE` | findings/entry_decision_{date}.json 存在，含 poll_needed |
| C: poll 不跑死标的 | entry_decision 写"LITE不入场"，跑 poll.py LITE | 输出含"❌ 不入场"，无 strategy_gate 信号 |
| D: node 0 结语含 poll 建议 | `python3.12 morning.py` | 输出含"今日需要轮询"或"无需轮询" |
