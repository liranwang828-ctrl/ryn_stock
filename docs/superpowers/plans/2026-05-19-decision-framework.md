# 盘前分层否决决策框架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `premarket_decision.py`，将盘前入场决策从定性分析升级为6条硬否决+6条软否决的分层否决规则，输出"可入场/观察/不入场"三态，阈值从配置文件读取。

**Architecture:** `evaluate_entry()` 读取 `config/decision_thresholds.json` 的阈值，对 order_sheet + watchlist_score + macro + regime + positions 数据执行分层否决检查，返回结构化决策 dict。阈值配置文件支持按 `macro_type` 分组覆盖，使回测引擎（Plan 2）可以无代码更新阈值。

**Tech Stack:** Python 3.12, yfinance（Stage 2 MA20 斜率计算），json，unittest.mock（测试）

---

## File Map

| 状态 | 路径 | 职责 |
|------|------|------|
| 新建 | `config/decision_thresholds.json` | 存储当前阈值，回测引擎可更新 |
| 新建 | `agents/premarket_decision.py` | 分层否决逻辑 + CLI |
| 新建 | `tests/test_premarket_decision.py` | 单元测试（19项） |

---

## Task 1: decision_thresholds.json + load_thresholds()

**Files:**
- Create: `config/decision_thresholds.json`
- Create: `agents/premarket_decision.py` (skeleton + load_thresholds only)
- Test: `tests/test_premarket_decision.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_premarket_decision.py
import sys, os, json, tempfile
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch

def test_load_thresholds_returns_defaults_when_no_file():
    """无配置文件时返回内置默认值"""
    from agents.premarket_decision import load_thresholds
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent/path.json"):
        t = load_thresholds()
    assert t["hard_vetoes"]["rr_min"] == 2.0
    assert t["hard_vetoes"]["macro_score_min"] == 4
    assert t["hard_vetoes"]["watchlist_score_min"] == 50
    assert t["soft_vetoes"]["ma20_dev_max"] == 0.05


def test_load_thresholds_reads_file(tmp_path):
    """存在配置文件时从文件读取"""
    from agents.premarket_decision import load_thresholds
    cfg = {
        "hard_vetoes": {"rr_min": 2.5, "qqq_premarket_min": -0.02,
                        "macro_score_min": 5, "watchlist_score_min": 55},
        "soft_vetoes": {"ma20_dev_max": 0.03, "rs5_min": 0.01, "max_headwinds": 2},
        "macro_type_overrides": {},
    }
    p = tmp_path / "decision_thresholds.json"
    p.write_text(json.dumps(cfg))
    with patch("agents.premarket_decision._THRESHOLDS_PATH", str(p)):
        t = load_thresholds()
    assert t["hard_vetoes"]["rr_min"] == 2.5
    assert t["soft_vetoes"]["ma20_dev_max"] == 0.03


def test_load_thresholds_applies_macro_type_override(tmp_path):
    """macro_type 分组覆盖正确应用"""
    from agents.premarket_decision import load_thresholds
    cfg = {
        "hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                        "macro_score_min": 4, "watchlist_score_min": 50},
        "soft_vetoes": {"ma20_dev_max": 0.05, "rs5_min": 0.0, "max_headwinds": 2},
        "macro_type_overrides": {"防御型": {"macro_score_min": 3}},
    }
    p = tmp_path / "decision_thresholds.json"
    p.write_text(json.dumps(cfg))
    with patch("agents.premarket_decision._THRESHOLDS_PATH", str(p)):
        t_growth = load_thresholds(macro_type="成长型")
        t_defensive = load_thresholds(macro_type="防御型")
    assert t_growth["hard_vetoes"]["macro_score_min"] == 4      # 无覆盖
    assert t_defensive["hard_vetoes"]["macro_score_min"] == 3   # 覆盖生效
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_decision.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 创建 config/decision_thresholds.json**

```json
{
  "_comment": "premarket_decision.py 读取，backtest_engine.py 可更新。默认阈值基于设计 spec，回测验证后调整。",
  "_updated": "2026-05-19",
  "hard_vetoes": {
    "rr_min": 2.0,
    "qqq_premarket_min": -0.015,
    "macro_score_min": 4,
    "watchlist_score_min": 50
  },
  "soft_vetoes": {
    "ma20_dev_max": 0.05,
    "rs5_min": 0.0,
    "max_headwinds": 2
  },
  "macro_type_overrides": {
    "防御型": {"macro_score_min": 3},
    "大宗商品型": {"macro_score_min": 3}
  }
}
```

- [ ] **Step 4: 创建 agents/premarket_decision.py (skeleton + load_thresholds)**

```python
"""
premarket_decision.py — 盘前分层否决入场决策框架

用法:
    python3.12 agents/premarket_decision.py LITE  # 输出今日入场决策
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_BASE            = os.path.expanduser("~/stock_team")
_THRESHOLDS_PATH = os.path.join(_BASE, "config", "decision_thresholds.json")
_MACRO_PATH      = os.path.join(_BASE, "findings", "macro.json")
_REGIME_PATH     = os.path.join(_BASE, "config", "market_regime.json")
_POS_PATH        = os.path.join(_BASE, "config", "positions.json")

_DEFAULT_THRESHOLDS = {
    "hard_vetoes": {
        "rr_min":               2.0,
        "qqq_premarket_min":    -0.015,
        "macro_score_min":      4,
        "watchlist_score_min":  50,
    },
    "soft_vetoes": {
        "ma20_dev_max":  0.05,
        "rs5_min":       0.0,
        "max_headwinds": 2,
    },
    "macro_type_overrides": {},
}


def load_thresholds(macro_type: str = "") -> dict:
    """
    读取 config/decision_thresholds.json，不存在则返回默认值。
    若 macro_type 在 macro_type_overrides 中有条目，覆盖对应硬否决阈值。
    """
    import copy
    if os.path.exists(_THRESHOLDS_PATH):
        try:
            t = json.load(open(_THRESHOLDS_PATH, encoding="utf-8"))
        except Exception:
            t = copy.deepcopy(_DEFAULT_THRESHOLDS)
    else:
        t = copy.deepcopy(_DEFAULT_THRESHOLDS)

    overrides = t.get("macro_type_overrides", {}).get(macro_type, {})
    if overrides:
        t = copy.deepcopy(t)
        t["hard_vetoes"] = {**t.get("hard_vetoes", {}), **overrides}
    return t
```

- [ ] **Step 5: 跑 3 个测试确认通过**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_decision.py -v
```
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd ~/stock_team
git add config/decision_thresholds.json agents/premarket_decision.py tests/test_premarket_decision.py
git commit -m "feat(decision): add load_thresholds() + decision_thresholds.json"
```

---

## Task 2: _check_hard_vetoes()

**Files:**
- Modify: `agents/premarket_decision.py`
- Modify: `tests/test_premarket_decision.py`

- [ ] **Step 1: 追加失败测试**

```python
# 追加到 tests/test_premarket_decision.py

def _make_inputs(
    thesis_status="intact", rr_ratio=3.5, qqq_chg=-0.005,
    macro_score=6, score=75, overnight_note="已在目标区间",
):
    order_sheet = {"rr_ratio": rr_ratio, "overnight_note": overnight_note}
    macro       = {"macro_score": macro_score}
    pos_cfg     = {"thesis_status": thesis_status}
    return order_sheet, macro, pos_cfg, qqq_chg, score


def test_hard_veto_thesis_broken():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    os, macro, pos, qqq, score = _make_inputs(thesis_status="broken")
    vetoes = _check_hard_vetoes(os, macro, pos, qqq, score, t)
    assert any("thesis_status" in v for v in vetoes)


def test_hard_veto_thesis_weakening():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    os, macro, pos, qqq, score = _make_inputs(thesis_status="weakening")
    vetoes = _check_hard_vetoes(os, macro, pos, qqq, score, t)
    assert any("thesis_status" in v for v in vetoes)


def test_hard_veto_rr_low():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    os, macro, pos, qqq, score = _make_inputs(rr_ratio=0.6)
    vetoes = _check_hard_vetoes(os, macro, pos, qqq, score, t)
    assert any("RR" in v for v in vetoes)


def test_hard_veto_qqq_down():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    os, macro, pos, qqq, score = _make_inputs(qqq_chg=-0.02)
    vetoes = _check_hard_vetoes(os, macro, pos, qqq, score, t)
    assert any("QQQ" in v for v in vetoes)


def test_hard_veto_macro_score_low():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    os, macro, pos, qqq, score = _make_inputs(macro_score=3)
    vetoes = _check_hard_vetoes(os, macro, pos, qqq, score, t)
    assert any("macro_score" in v for v in vetoes)


def test_hard_veto_score_low():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    os, macro, pos, qqq, score = _make_inputs(score=40)
    vetoes = _check_hard_vetoes(os, macro, pos, qqq, score, t)
    assert any("watchlist_score" in v for v in vetoes)


def test_hard_veto_overnight_invalid():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    os, macro, pos, qqq, score = _make_inputs(overnight_note="区间失效（盘前$980 大幅高出）")
    vetoes = _check_hard_vetoes(os, macro, pos, qqq, score, t)
    assert any("区间失效" in v for v in vetoes)


def test_no_hard_vetoes_with_clean_inputs():
    from agents.premarket_decision import _check_hard_vetoes
    t = {"hard_vetoes": {"rr_min": 2.0, "qqq_premarket_min": -0.015,
                         "macro_score_min": 4, "watchlist_score_min": 50}}
    os, macro, pos, qqq, score = _make_inputs()
    vetoes = _check_hard_vetoes(os, macro, pos, qqq, score, t)
    assert vetoes == []
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_decision.py::test_hard_veto_rr_low -v 2>&1 | head -10
```
Expected: `AttributeError` (_check_hard_vetoes not found)

- [ ] **Step 3: 实现 _check_hard_vetoes()**

追加到 `agents/premarket_decision.py`（在 `load_thresholds` 之后）：

```python
def _check_hard_vetoes(order_sheet: dict, macro: dict, pos_cfg: dict,
                       qqq_premarket_chg: float, watchlist_score: int,
                       thresholds: dict) -> list:
    """
    检查6条硬否决，返回触发的否决描述列表。列表为空表示无硬否决。
    按优先级排序：thesis → RR → QQQ → macro_score → watchlist_score → overnight
    """
    hv   = thresholds.get("hard_vetoes", {})
    pos  = pos_cfg or {}
    vetoes = []

    # 1. thesis_status（最高优先级）
    status = pos.get("thesis_status", "intact")
    if status in ("weakening", "broken"):
        vetoes.append(f"thesis_status={status}（论点已{'弱化' if status=='weakening' else '破裂'}）")

    # 2. RR
    rr = float(order_sheet.get("rr_ratio") or 0)
    if rr < hv.get("rr_min", 2.0):
        vetoes.append(f"RR={rr:.1f}x < {hv.get('rr_min', 2.0):.1f}x（盈亏比不合格）")

    # 3. QQQ 盘前
    qqq_min = hv.get("qqq_premarket_min", -0.015)
    if qqq_premarket_chg < qqq_min:
        vetoes.append(f"QQQ盘前{qqq_premarket_chg:.1%}（逆风超过阈值{qqq_min:.1%}）")

    # 4. macro_score
    ms = macro.get("macro_score", 10)
    ms_min = hv.get("macro_score_min", 4)
    if ms < ms_min:
        vetoes.append(f"macro_score={ms} < {ms_min}（宏观环境不足）")

    # 5. watchlist_score
    s_min = hv.get("watchlist_score_min", 50)
    if watchlist_score < s_min:
        vetoes.append(f"watchlist_score={watchlist_score} < {s_min}（综合评分不足）")

    # 6. overnight_note 含"区间失效"
    on = order_sheet.get("overnight_note") or ""
    if "区间失效" in on:
        vetoes.append("overnight_note含'区间失效'（隔夜价大幅高出入场区间）")

    return vetoes
```

- [ ] **Step 4: 跑所有测试（3+7=10项）**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_decision.py -v
```
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/premarket_decision.py tests/test_premarket_decision.py
git commit -m "feat(decision): add _check_hard_vetoes() - 6 hard veto rules"
```

---

## Task 3: _check_soft_vetoes()

**Files:**
- Modify: `agents/premarket_decision.py`
- Modify: `tests/test_premarket_decision.py`

- [ ] **Step 1: 追加失败测试**

```python
# 追加到 tests/test_premarket_decision.py

def _default_soft_thresholds():
    return {"soft_vetoes": {"ma20_dev_max": 0.05, "rs5_min": 0.0, "max_headwinds": 2}}

def test_soft_veto_ma20_high():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.08, "rs5": 2.0},
        macro={"yield_curve": "正常", "dxy": 100, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "光模块"},
        regime={"regime": "trending_up", "overnight_signal": ""},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert any("MA20" in v for v in result)


def test_soft_veto_rs5_negative():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.01, "rs5": -1.5},
        macro={"yield_curve": "正常", "dxy": 100, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "光模块"},
        regime={"regime": "trending_up", "overnight_signal": ""},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert any("RS5" in v for v in result)


def test_soft_veto_headwinds():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.01, "rs5": 1.0},
        macro={"yield_curve": "倒挂", "dxy": 106, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {"rate_up": "负", "dollar_strong": "负"},
                 "macro_type": "光模块"},
        regime={"regime": "trending_up", "overnight_signal": ""},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert any("逆风" in v for v in result)


def test_soft_veto_regime_mismatch():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="LITE",
        watchlist_result={"ma20_dev": 0.01, "rs5": 1.0, "narrative_hit": False},
        macro={"yield_curve": "正常", "dxy": 100, "macro_score": 6},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "光模块"},
        regime={"regime": "sector_hot", "overnight_signal": "能源 XLE+5%"},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert any("Regime" in v for v in result)


def test_no_soft_vetoes_clean():
    from agents.premarket_decision import _check_soft_vetoes
    t = _default_soft_thresholds()
    result = _check_soft_vetoes(
        sym="RKLB",
        watchlist_result={"ma20_dev": -0.02, "rs5": 3.0, "narrative_hit": True},
        macro={"yield_curve": "正常", "dxy": 99, "macro_score": 7},
        pos_cfg={"macro_sensitivity": {}, "macro_type": "太空"},
        regime={"regime": "sector_hot", "overnight_signal": "太空 RKLB+6%"},
        master_confidence_all_low=False,
        thresholds=t,
    )
    assert result == []
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_decision.py::test_soft_veto_ma20_high -v 2>&1 | head -10
```

- [ ] **Step 3: 实现 _check_soft_vetoes()**

追加到 `agents/premarket_decision.py`：

```python
def _count_macro_headwinds(macro: dict, pos_cfg: dict) -> int:
    """活跃宏观逆风数量（对该标的为负向）"""
    ms = (pos_cfg or {}).get("macro_sensitivity", {})
    if not ms:
        return 0
    count = 0
    yc  = macro.get("yield_curve", "")
    dxy = float(macro.get("dxy") or 0)
    ms_val = macro.get("macro_score", 6)
    try:
        cpi = float(str(macro.get("cpi_latest", "0")).replace("%", ""))
    except Exception:
        cpi = 0
    if yc == "倒挂"   and ms.get("rate_up")       == "负": count += 1
    if dxy > 103      and ms.get("dollar_strong")  == "负": count += 1
    if cpi > 3.5      and ms.get("inflation")      == "负": count += 1
    if ms_val <= 3    and ms.get("recession")      == "负": count += 1
    return count


def _is_regime_mismatch(sym: str, pos_cfg: dict, regime: dict,
                         watchlist_result: dict) -> bool:
    """
    当前 regime 为 sector_hot 且叙事未命中该标的时，视为 regime 错位。
    trending_up/down/sideways/volatile 不触发此条件。
    """
    if regime.get("regime") != "sector_hot":
        return False
    narrative_hit = watchlist_result.get("narrative_hit", False)
    return not narrative_hit


def _is_stage2_insufficient(sym: str, watchlist_result: dict) -> bool:
    """
    Stage 2 结构不足：RS5日≤0 且 MA20不向上倾斜（两者同时成立）。
    MA20斜率：用 yfinance 10日数据判断 MA20[-1] > MA20[-6]。
    数据不可用时返回 False（保守，不触发否决）。
    """
    rs5 = watchlist_result.get("rs5")
    if rs5 is None or rs5 > 0:
        return False  # RS5日为正，Stage 2 条件之一未满足
    try:
        import yfinance as yf
        h = yf.Ticker(sym).history(period="15d")["Close"]
        if len(h) >= 11:
            ma20_today = float(h.tail(10).mean())
            ma20_5d_ago = float(h.iloc[-11:-1].mean())
            ma20_rising = ma20_today > ma20_5d_ago
            return not ma20_rising  # RS5≤0 AND MA20不上升
    except Exception:
        pass
    return False


def _check_soft_vetoes(sym: str, watchlist_result: dict, macro: dict,
                        pos_cfg: dict, regime: dict,
                        master_confidence_all_low: bool,
                        thresholds: dict) -> list:
    """
    检查6条软否决，返回触发的否决描述列表。
    ≥2条触发时 evaluate_entry() 将输出"观察"。
    """
    sv = thresholds.get("soft_vetoes", {})
    vetoes = []

    # 1. MA20乖离超阈值（追高）
    dev = watchlist_result.get("ma20_dev")
    dev_max = sv.get("ma20_dev_max", 0.05)
    if dev is not None and dev > dev_max:
        vetoes.append(f"MA20乖离+{dev:.1%}（超过阈值+{dev_max:.0%}，追高风险）")

    # 2. RS5日超额为负（相对弱势）
    rs5 = watchlist_result.get("rs5")
    rs5_min = sv.get("rs5_min", 0.0)
    if rs5 is not None and rs5 < rs5_min:
        vetoes.append(f"RS5日超额{rs5:+.1f}%（相对弱势，低于阈值{rs5_min:+.1f}%）")

    # 3. 活跃宏观逆风项数
    headwinds = _count_macro_headwinds(macro, pos_cfg)
    max_hw = sv.get("max_headwinds", 2)
    if headwinds >= max_hw:
        vetoes.append(f"活跃宏观逆风{headwinds}项（≥{max_hw}项阈值）")

    # 4. 大师置信度全部为"低"
    if master_confidence_all_low:
        vetoes.append("大师置信度全部为'低'（分析信心不足）")

    # 5. Regime 错位
    if _is_regime_mismatch(sym, pos_cfg, regime, watchlist_result):
        vetoes.append(f"Regime错位（当前sector_hot但{sym}叙事未命中）")

    # 6. Stage 2 结构不足
    if _is_stage2_insufficient(sym, watchlist_result):
        vetoes.append(f"{sym} Stage 2结构不足（RS5日≤0且MA20不向上倾斜）")

    return vetoes
```

- [ ] **Step 4: 跑所有测试（10+5=15项）**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_decision.py -v
```
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/premarket_decision.py tests/test_premarket_decision.py
git commit -m "feat(decision): add _check_soft_vetoes() - 6 soft veto rules"
```

---

## Task 4: evaluate_entry() + CLI

**Files:**
- Modify: `agents/premarket_decision.py`
- Modify: `tests/test_premarket_decision.py`

- [ ] **Step 1: 追加失败测试**

```python
# 追加到 tests/test_premarket_decision.py

def _clean_watchlist_result(score=75, ma20_dev=0.01, rs5=2.0, narrative_hit=True):
    return {"score": score, "ma20_dev": ma20_dev, "rs5": rs5,
            "narrative_hit": narrative_hit}

def _clean_order_sheet(rr_ratio=3.5, overnight_note="已在目标区间"):
    return {"rr_ratio": rr_ratio, "overnight_note": overnight_note}

_CLEAN_MACRO   = {"macro_score": 6, "yield_curve": "正常", "dxy": 99}
_CLEAN_POS_CFG = {"thesis_status": "intact", "macro_sensitivity": {}, "macro_type": "光模块"}
_CLEAN_REGIME  = {"regime": "trending_up", "overnight_signal": "LITE+3%"}


def test_evaluate_entry_ke_ruchang():
    """0个硬否决 + 0个软否决 → 可入场"""
    from agents.premarket_decision import evaluate_entry
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent"):
        result = evaluate_entry(
            sym="LITE",
            order_sheet=_clean_order_sheet(),
            watchlist_result=_clean_watchlist_result(),
            macro=_CLEAN_MACRO,
            pos_cfg=_CLEAN_POS_CFG,
            regime=_CLEAN_REGIME,
            qqq_premarket_chg=-0.003,
        )
    assert result["decision"] == "可入场"
    assert result["hard_vetoes"] == []


def test_evaluate_entry_bu_ruchang_hard_veto():
    """RR=0.6x → 不入场（硬否决）"""
    from agents.premarket_decision import evaluate_entry
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent"):
        result = evaluate_entry(
            sym="MRVU",
            order_sheet=_clean_order_sheet(rr_ratio=0.6),
            watchlist_result=_clean_watchlist_result(),
            macro=_CLEAN_MACRO,
            pos_cfg=_CLEAN_POS_CFG,
            regime=_CLEAN_REGIME,
            qqq_premarket_chg=-0.003,
        )
    assert result["decision"] == "不入场"
    assert len(result["hard_vetoes"]) >= 1


def test_evaluate_entry_guancha_two_soft():
    """0个硬否决 + 2个软否决 → 观察"""
    from agents.premarket_decision import evaluate_entry
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent"), \
         patch("agents.premarket_decision._is_stage2_insufficient", return_value=False):
        result = evaluate_entry(
            sym="LITE",
            order_sheet=_clean_order_sheet(),
            watchlist_result=_clean_watchlist_result(
                ma20_dev=0.08,   # 软否决1: MA20乖离>5%
                rs5=-1.5,        # 软否决2: RS5<0
            ),
            macro=_CLEAN_MACRO,
            pos_cfg=_CLEAN_POS_CFG,
            regime=_CLEAN_REGIME,
            qqq_premarket_chg=-0.003,
        )
    assert result["decision"] == "观察"
    assert len(result["soft_vetoes"]) >= 2


def test_evaluate_entry_one_soft_is_ke_ruchang():
    """0个硬否决 + 1个软否决 → 可入场（边界）"""
    from agents.premarket_decision import evaluate_entry
    with patch("agents.premarket_decision._THRESHOLDS_PATH", "/nonexistent"), \
         patch("agents.premarket_decision._is_stage2_insufficient", return_value=False):
        result = evaluate_entry(
            sym="LITE",
            order_sheet=_clean_order_sheet(),
            watchlist_result=_clean_watchlist_result(ma20_dev=0.08),  # 仅1个软否决
            macro=_CLEAN_MACRO,
            pos_cfg=_CLEAN_POS_CFG,
            regime=_CLEAN_REGIME,
            qqq_premarket_chg=-0.003,
        )
    assert result["decision"] == "可入场"
    assert len(result["soft_vetoes"]) == 1
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_decision.py::test_evaluate_entry_ke_ruchang -v 2>&1 | head -10
```

- [ ] **Step 3: 实现 evaluate_entry() 和 main()**

> **注意**：spec 中签名为 `evaluate_entry(sym, order_sheet, score: int, ...)`, 此处有意改为传入完整 `watchlist_result: dict`（内部提取 score），更灵活且 Plan 2 的 simulate_decision_framework 也应使用此签名。

追加到 `agents/premarket_decision.py`：

```python
def evaluate_entry(
    sym: str,
    order_sheet: dict,
    watchlist_result: dict,
    macro: dict,
    pos_cfg: dict,
    regime: dict,
    qqq_premarket_chg: float,
    thresholds: dict = None,
    master_confidence_all_low: bool = False,
) -> dict:
    """
    执行分层否决检查，返回入场决策 dict。

    返回结构:
      decision: "可入场" | "观察" | "不入场"
      hard_vetoes: list[str]   # 触发的硬否决
      soft_vetoes:  list[str]  # 触发的软否决
      reason: str              # 一句摘要
    """
    macro_type = (pos_cfg or {}).get("macro_type", "")
    if thresholds is None:
        thresholds = load_thresholds(macro_type=macro_type)

    score = watchlist_result.get("score", 0)

    hard = _check_hard_vetoes(order_sheet, macro, pos_cfg,
                              qqq_premarket_chg, score, thresholds)
    soft = _check_soft_vetoes(sym, watchlist_result, macro, pos_cfg,
                              regime, master_confidence_all_low, thresholds)

    if hard:
        decision = "不入场"
        reason   = f"硬否决触发（{hard[0]}）"
    elif len(soft) >= 2:
        decision = "观察"
        reason   = f"{len(soft)}个软否决，观察窗口30分钟内给出最终决定"
    else:
        decision = "可入场"
        reason   = "无硬否决" + (f"，1个软否决（{soft[0]}）" if soft else "，信号全部通过")

    return {
        "sym":         sym.upper(),
        "decision":    decision,
        "hard_vetoes": hard,
        "soft_vetoes": soft,
        "reason":      reason,
        "score":       score,
        "rr_ratio":    order_sheet.get("rr_ratio"),
    }


def fmt_decision(d: dict) -> str:
    """格式化决策输出"""
    icon = {"可入场": "✅", "观察": "⚠️", "不入场": "❌"}.get(d["decision"], "?")
    lines = [
        "",
        f"{'━'*48}",
        f"  {d['sym']} 盘前入场决策",
        f"{'━'*48}",
        f"  {icon} {d['decision']}",
        f"  {d['reason']}",
    ]
    if d["hard_vetoes"]:
        lines.append("  [硬否决]")
        for v in d["hard_vetoes"]:
            lines.append(f"    × {v}")
    if d["soft_vetoes"]:
        lines.append("  [软否决]")
        for v in d["soft_vetoes"]:
            lines.append(f"    ⚠ {v}")
    lines.append(f"{'━'*48}")
    return "\n".join(lines)


def _load_json(path, default=None):
    try:
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))
    except Exception:
        pass
    return default or {}


def main():
    import argparse
    import yfinance as yf
    from agents.premarket_order_sheet import generate_order_sheet
    from agents.premarket_watchlist_score import score_stock

    parser = argparse.ArgumentParser(description="盘前入场决策框架")
    parser.add_argument("symbols", nargs="+", help="股票代码，如 LITE RKLB")
    args = parser.parse_args()

    macro  = _load_json(os.path.join(_BASE, "findings", "macro.json"))
    regime = _load_json(_REGIME_PATH)
    pos    = _load_json(_POS_PATH).get("positions", {})

    # QQQ 盘前涨跌幅
    try:
        info = yf.Ticker("QQQ").info
        qqq_cur  = info.get("regularMarketPrice", 0)
        qqq_prev = info.get("regularMarketPreviousClose", qqq_cur)
        qqq_chg  = (qqq_cur - qqq_prev) / qqq_prev if qqq_prev else 0
    except Exception:
        qqq_chg = 0.0

    for sym in args.symbols:
        sym = sym.upper()
        pos_cfg   = pos.get(sym, {})
        thresholds = load_thresholds(macro_type=pos_cfg.get("macro_type", ""))
        os_data   = generate_order_sheet(sym)
        wr        = score_stock(sym, macro, regime, pos_cfg=pos_cfg)

        result = evaluate_entry(
            sym=sym, order_sheet=os_data, watchlist_result=wr,
            macro=macro, pos_cfg=pos_cfg, regime=regime,
            qqq_premarket_chg=qqq_chg, thresholds=thresholds,
        )
        print(fmt_decision(result))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑所有 20 个测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_decision.py -v
```
Expected: 20 passed

- [ ] **Step 5: CLI 冒烟测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_decision.py LITE 2>&1 | tail -20
```
Expected: 输出含"LITE 盘前入场决策"、✅/⚠️/❌ 标记、决策理由

- [ ] **Step 6: Commit**

```bash
cd ~/stock_team
git add agents/premarket_decision.py tests/test_premarket_decision.py
git commit -m "feat(decision): add evaluate_entry(), fmt_decision(), CLI - complete decision framework"
```

---

## Task 5: CHANGELOG 更新

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: 更新 CHANGELOG.md**

在 CHANGELOG.md 最顶部新增：

```
## 2026-05-19 盘前分层否决决策框架（premarket_decision.py）

### 新建文件

- **新建** `config/decision_thresholds.json` — 阈值配置，回测引擎（Plan 2）可更新；支持 macro_type 分组覆盖
- **新建** `agents/premarket_decision.py` — 分层否决入场决策：
  - `load_thresholds(macro_type)` — 读取配置，支持分组覆盖
  - `_check_hard_vetoes()` — 6条硬否决（thesis_status/RR/QQQ/macro_score/watchlist_score/overnight）
  - `_check_soft_vetoes()` — 6条软否决（MA20乖离/RS5/宏观逆风/大师置信/Regime错位/Stage2）
  - `evaluate_entry()` — 三态输出：可入场/观察/不入场
  - `fmt_decision()` — 格式化输出
  - CLI：`python3.12 agents/premarket_decision.py LITE RKLB`

### 测试

- `tests/test_premarket_decision.py` — 20项，覆盖三态输出、边界条件、配置文件读取
```

- [ ] **Step 2: Commit**

```bash
cd ~/stock_team
git add CHANGELOG.md
git commit -m "docs: CHANGELOG for premarket decision framework"
```

---

## 验收检查（对应 spec Validation）

| 验收点 | 验证命令 | 期望结果 |
|--------|---------|---------|
| V1（不入场/RR）| `pytest tests/test_premarket_decision.py::test_evaluate_entry_bu_ruchang_hard_veto` | PASS |
| V2（可入场）| `pytest tests/test_premarket_decision.py::test_evaluate_entry_ke_ruchang` | PASS |
| V3（观察）| `pytest tests/test_premarket_decision.py::test_evaluate_entry_guancha_two_soft` | PASS |
| V4（边界1软→可入场）| `pytest tests/test_premarket_decision.py::test_evaluate_entry_one_soft_is_ke_ruchang` | PASS |
| V5（配置文件驱动）| `pytest tests/test_premarket_decision.py::test_load_thresholds_reads_file` | PASS |
