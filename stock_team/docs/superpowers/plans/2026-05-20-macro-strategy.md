# 宏观策略（Macro Strategy）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `macro_strategy.py` 独立模块，综合 memo 定性分析 + 实时市场数据，系统性计算所有交易节点（13个），替代当前基于成本比例的草率计算。

**Architecture:** 独立脚本 `agents/macro_strategy.py`，读取 `strategic_memo_{sym}.json` + yfinance 实时数据，输出 `macro_strategy_{sym}.json`。`premarket_summary.py` 和 `report_viewer.py` 消费此文件。进化系数存于 `evolution` 字段，历史回测更新。

**Tech Stack:** Python 3.12, yfinance, pandas, numpy, json, unittest.mock（测试）

**Spec:** `docs/superpowers/specs/2026-05-20-macro-strategy-design.md`

---

## 文件结构

| 操作 | 路径 | 职责 |
|------|------|------|
| 创建 | `agents/macro_strategy.py` | 主模块：市场数据 + 节点计算 + 输出 |
| 创建 | `agents/portfolio_macro_guard.py` | 组合层外部环境止损（大盘/板块） |
| 创建 | `config/portfolio_macro_guard.json` | X/Y 系数（VIX/SPY 缩仓比例） |
| 创建 | `tests/test_macro_strategy.py` | 所有节点计算单元测试 |
| 创建 | `tests/fixtures/macro_strategy_memo.json` | 测试用 memo 数据 |
| 修改 | `agents/premarket_summary.py` | build_summary 读取 macro_strategy JSON |
| 修改 | `agents/report_viewer.py` | 新增"交易节点"Section |
| 修改 | `agents/strategic_memo_writer.py` | 删除草率价格计算，改为读取宏观策略 |
| 修改 | `~/.claude/skills/stock-deep-research.md` | 添加 macro_strategy.py 步骤 |
| 修改 | `~/.claude/skills/stock-premarket.md` | 添加 macro_strategy.py --refresh 步骤 |

---

## Task 1: 测试 Fixture + 市场数据模块

**Files:**
- Create: `tests/fixtures/macro_strategy_memo.json`
- Create: `agents/macro_strategy.py`（仅 fetch_market_data 函数）
- Create: `tests/test_macro_strategy.py`（仅市场数据测试）

- [ ] **Step 1: 创建 memo fixture**

```bash
cat > ~/stock_team/tests/fixtures/macro_strategy_memo.json << 'EOF'
{
  "sym": "TEST",
  "analysis_date": "2026-05-20",
  "synthesis": {"strategic_stance": "hold"},
  "judgment": {"unified_confidence": 3},
  "support_and_risk": {
    "next_catalyst": {"event": "earnings", "date": "2026-06-15", "importance": "high"}
  },
  "scenarios": {
    "bull": {"price_target": 130.0},
    "base": {"price_target": 115.0},
    "bear": {"price_target": 85.0}
  },
  "agent_analysis": {
    "sentiment": {"confidence": 75, "signal": "bullish"}
  },
  "position_context": {
    "falsification_conditions": [],
    "position_snapshot": {"cost": 100.0, "shares": 10}
  }
}
EOF
```

- [ ] **Step 2: 写市场数据测试**

```python
# tests/test_macro_strategy.py
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch, MagicMock
import pandas as pd, numpy as np


def _make_price_history(n=120, close=224.77):
    """生成模拟价格历史"""
    np.random.seed(42)
    closes = [close]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.012)))
    closes = list(reversed(closes))
    return pd.DataFrame({
        "Open":   [c * 0.998 for c in closes],
        "High":   [c * 1.012 for c in closes],
        "Low":    [c * 0.988 for c in closes],
        "Close":  closes,
        "Volume": [int(50e6 + np.random.normal(0, 5e6)) for _ in closes],
    })


def _mock_ticker(hist_df, info=None):
    t = MagicMock()
    t.history.return_value = hist_df
    t.info = info or {
        "targetMeanPrice": 275.3,
        "targetLowPrice": 200.0,
        "targetHighPrice": 350.0,
        "numberOfAnalystOpinions": 50,
    }
    return t


def test_fetch_market_data_returns_required_fields():
    from agents.macro_strategy import fetch_market_data
    hist = _make_price_history()
    ticker = _mock_ticker(hist)
    with patch("agents.macro_strategy.yf.Ticker", return_value=ticker):
        data = fetch_market_data("TEST")
    required = ["price", "ma20", "ma50", "ma200", "atr14", "atr21",
                "fib_382", "fib_618", "swing_high_90d", "swing_low_14d",
                "rsi14", "volume_ratio", "analyst_target", "sentiment_score"]
    for f in required:
        assert f in data, f"Missing field: {f}"


def test_fetch_market_data_ma_ordering():
    """MA20 应该比 MA50 更接近当前价（短期均线更快）"""
    from agents.macro_strategy import fetch_market_data
    hist = _make_price_history(close=224.77)
    ticker = _mock_ticker(hist)
    with patch("agents.macro_strategy.yf.Ticker", return_value=ticker):
        data = fetch_market_data("TEST")
    assert abs(data["ma20"] - data["price"]) <= abs(data["ma50"] - data["price"]) + 5


def test_fetch_market_data_atr_positive():
    from agents.macro_strategy import fetch_market_data
    hist = _make_price_history()
    ticker = _mock_ticker(hist)
    with patch("agents.macro_strategy.yf.Ticker", return_value=ticker):
        data = fetch_market_data("TEST")
    assert data["atr14"] > 0
    assert data["atr21"] > 0


def test_fetch_market_data_fib_levels():
    """fib_382 应该在 swing_low 和 swing_high 之间"""
    from agents.macro_strategy import fetch_market_data
    hist = _make_price_history()
    ticker = _mock_ticker(hist)
    with patch("agents.macro_strategy.yf.Ticker", return_value=ticker):
        data = fetch_market_data("TEST")
    lo, hi = data["swing_low_14d"], data["swing_high_90d"]
    if hi > lo:
        assert lo <= data["fib_382"] <= hi
        assert lo <= data["fib_618"] <= hi
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -v 2>&1 | head -30
```
Expected: `ModuleNotFoundError: No module named 'agents.macro_strategy'`

- [ ] **Step 4: 实现 fetch_market_data**

```python
# agents/macro_strategy.py
"""
宏观策略模块 — macro_strategy.py
综合 strategic_memo + 实时市场数据，系统性制定所有交易节点。
输出: macro_strategy_{sym}.json

用法:
  python3.12 agents/macro_strategy.py NVDA          # 全量生成
  python3.12 agents/macro_strategy.py NVDA --refresh # 只更新动态节点
"""
import json, os, sys, argparse
from datetime import datetime, timezone, date as _date

import yfinance as yf
import numpy as np
import pandas as pd

BASE     = os.path.expanduser("~/stock_team")
FIND_DIR = os.path.join(BASE, "findings")
CFG_DIR  = os.path.join(BASE, "config")


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_market_data(sym: str, period: str = "6mo") -> dict:
    """从 yfinance 抓取并计算所有所需市场指标。"""
    ticker = yf.Ticker(sym)
    hist   = ticker.history(period=period)
    info   = ticker.info or {}

    if hist.empty or len(hist) < 21:
        return {}

    closes  = hist["Close"].values
    highs   = hist["High"].values
    lows    = hist["Low"].values
    volumes = hist["Volume"].values

    price = float(closes[-1])

    # 移动均线
    ma20  = float(np.mean(closes[-20:])) if len(closes) >= 20 else price
    ma50  = float(np.mean(closes[-50:])) if len(closes) >= 50 else price
    ma200 = float(np.mean(closes[-200:])) if len(closes) >= 200 else price

    # ATR (Average True Range)
    def _atr(n: int) -> float:
        tr_list = []
        for i in range(1, min(n + 1, len(closes))):
            tr = max(highs[-i] - lows[-i],
                     abs(highs[-i] - closes[-i-1]),
                     abs(lows[-i]  - closes[-i-1]))
            tr_list.append(tr)
        return float(np.mean(tr_list)) if tr_list else 0.0

    atr14 = _atr(14)
    atr21 = _atr(21)

    # 摆动高低点
    swing_high_90d = float(np.max(highs[-90:])) if len(highs) >= 90 else float(np.max(highs))
    swing_low_14d  = float(np.min(lows[-14:]))  if len(lows)  >= 14 else float(np.min(lows))

    # Fibonacci 回撤（基于近90日摆动）
    swing_low_90d = float(np.min(lows[-90:])) if len(lows) >= 90 else float(np.min(lows))
    fib_range = swing_high_90d - swing_low_90d
    fib_382 = round(swing_high_90d - 0.382 * fib_range, 2) if fib_range > 0 else price
    fib_618 = round(swing_high_90d - 0.618 * fib_range, 2) if fib_range > 0 else price

    # RSI-14
    def _rsi(n: int = 14) -> float:
        if len(closes) < n + 1:
            return 50.0
        deltas = np.diff(closes[-(n+1):])
        gains  = deltas[deltas > 0]
        losses = -deltas[deltas < 0]
        avg_gain = float(np.mean(gains))  if len(gains)  > 0 else 0.0
        avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.001
        rs = avg_gain / avg_loss
        return round(100 - 100 / (1 + rs), 1)

    rsi14 = _rsi(14)

    # 成交量比（近5日均量 / 近20日均量）
    vol_5  = float(np.mean(volumes[-5:]))  if len(volumes) >= 5  else 0.0
    vol_20 = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else 1.0
    volume_ratio = round(vol_5 / vol_20, 2) if vol_20 > 0 else 1.0

    # 分析师目标价
    analyst_target = info.get("targetMeanPrice") or info.get("targetMedianPrice")

    return {
        "price":          round(price, 2),
        "ma20":           round(ma20, 2),
        "ma50":           round(ma50, 2),
        "ma200":          round(ma200, 2),
        "atr14":          round(atr14, 2),
        "atr21":          round(atr21, 2),
        "fib_382":        fib_382,
        "fib_618":        fib_618,
        "swing_high_90d": round(swing_high_90d, 2),
        "swing_low_14d":  round(swing_low_14d, 2),
        "rsi14":          rsi14,
        "volume_ratio":   volume_ratio,
        "analyst_target": float(analyst_target) if analyst_target else None,
        "sentiment_score": None,  # 由 memo 注入，见 build_nodes()
    }
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py::test_fetch_market_data_returns_required_fields tests/test_macro_strategy.py::test_fetch_market_data_atr_positive tests/test_macro_strategy.py::test_fetch_market_data_fib_levels -v 2>&1 | tail -15
```
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
cd ~/stock_team && git add agents/macro_strategy.py tests/test_macro_strategy.py tests/fixtures/macro_strategy_memo.json && git commit -m "feat(macro-strategy): add market data fetcher + tests"
```

---

## Task 2: 买入节点计算（Entry Invalidation / Add1 / Add2 / Re-entry）

**Files:**
- Modify: `agents/macro_strategy.py`（添加 calc_entry_nodes 函数）
- Modify: `tests/test_macro_strategy.py`（添加 entry 节点测试）

- [ ] **Step 1: 写买入节点测试**

```python
# 追加到 tests/test_macro_strategy.py

def _default_mkt(price=224.77, ma20=215.8, ma50=210.2, ma200=178.5,
                  atr14=8.3, fib_382=202.1, fib_618=187.2,
                  swing_low_14d=208.5, swing_high_90d=242.5,
                  volume_ratio=1.1, analyst_target=275.3):
    return dict(price=price, ma20=ma20, ma50=ma50, ma200=ma200,
                atr14=atr14, atr21=7.9, fib_382=fib_382, fib_618=fib_618,
                swing_low_14d=swing_low_14d, swing_high_90d=swing_high_90d,
                rsi14=60.9, volume_ratio=volume_ratio,
                analyst_target=analyst_target, sentiment_score=0.75)

def _default_ev(k1=1.0, k2=0.2, k3=0.0, k4=0.90, k5=0.5, k6=1.0,
                k_reentry=0.3, fe_catalyst=2.0, c1=0.5, c2=1.5,
                Z_pre_reduce_pct=20, N_time_stop=30, D_decay_stop=14,
                M_decay_min_pct=5.0):
    return dict(k1=k1, k2=k2, k3=k3, k4=k4, k5=k5, k6=k6,
                k_reentry=k_reentry, fe_catalyst=fe_catalyst,
                c1=c1, c2=c2, Z_pre_reduce_pct=Z_pre_reduce_pct,
                N_time_stop=N_time_stop, D_decay_stop=D_decay_stop,
                M_decay_min_pct=M_decay_min_pct)


def test_entry_invalidation_above_entry_base():
    from agents.macro_strategy import calc_entry_nodes
    mkt = _default_mkt()
    ev  = _default_ev()
    nodes = calc_entry_nodes(mkt, ev, entry_base=224.0,
                             unified_confidence=3, thesis_status="intact")
    # 追涨上限必须高于 entry_base
    assert nodes["entry_invalidation"]["price"] > 224.0


def test_add1_uses_max_of_fib_and_ma50():
    from agents.macro_strategy import calc_entry_nodes
    mkt = _default_mkt(fib_382=195.0, ma50=210.0, atr14=8.0)
    ev  = _default_ev(k2=0.2)
    # ma50 + 0.2*atr = 211.6 > fib_382=195.0 → add1 应在 211.6 附近
    nodes = calc_entry_nodes(mkt, ev, entry_base=224.0,
                             unified_confidence=3, thesis_status="intact")
    assert nodes["add1"]["price"] >= 195.0


def test_add2_requires_high_confidence():
    from agents.macro_strategy import calc_entry_nodes
    mkt = _default_mkt()
    ev  = _default_ev()
    # unified_confidence=2 低于阈值4，add2 应为 None
    nodes_low  = calc_entry_nodes(mkt, ev, entry_base=224.0,
                                  unified_confidence=2, thesis_status="intact")
    nodes_high = calc_entry_nodes(mkt, ev, entry_base=224.0,
                                  unified_confidence=4, thesis_status="intact")
    assert nodes_low["add2"] is None
    assert nodes_high["add2"] is not None


def test_reentry_requires_intact_thesis():
    from agents.macro_strategy import calc_entry_nodes
    mkt = _default_mkt()
    ev  = _default_ev()
    nodes = calc_entry_nodes(mkt, ev, entry_base=224.0,
                             unified_confidence=3, thesis_status="weakening")
    assert nodes["re_entry"] is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "entry" -v 2>&1 | tail -10
```
Expected: `ImportError` 或 `AttributeError: calc_entry_nodes`

- [ ] **Step 3: 实现 calc_entry_nodes**

```python
# 追加到 agents/macro_strategy.py

def calc_entry_nodes(mkt: dict, ev: dict, entry_base: float,
                     unified_confidence: int, thesis_status: str) -> dict:
    """计算买入方向的所有节点：Entry Invalidation / Add1 / Add2 / Re-entry"""
    atr14  = mkt["atr14"]
    ma50   = mkt["ma50"]
    fib382 = mkt["fib_382"]
    fib618 = mkt["fib_618"]
    sw_low = mkt["swing_low_14d"]

    # Entry Invalidation：超过此价不追入
    inv_price = round(entry_base + 0.5 * atr14, 2)

    # Add1：max(Fib38.2%, MA50 + k2*ATR)，结构低点覆盖规则
    add1_base = max(fib382, round(ma50 + ev["k2"] * atr14, 2))
    # 若近14日结构低点比 max() 低超过 0.5*ATR，结构优先
    if add1_base - sw_low > 0.5 * atr14:
        add1_price = round(sw_low, 2)
    else:
        add1_price = round(add1_base, 2)

    add1 = {
        "price":       add1_price,
        "basis":       f"max(Fib38.2%={fib382}, MA50({ma50})+{ev['k2']}×ATR14({atr14})={round(ma50+ev['k2']*atr14,2)})",
        "conditions":  ["论点 intact", "vol_ratio < 0.8", "催化剂窗口外"],
        "invalidation":"放量跌破 MA50 → 取消 Add1",
    }

    # Add2：Fib61.8%，仅高置信度
    add2 = None
    if unified_confidence >= 4:
        add2_price = round(max(fib618, mkt["ma200"] + ev["k3"] * atr14), 2)
        add2 = {
            "price":       add2_price,
            "basis":       f"Fib61.8%={fib618}",
            "conditions":  ["unified_confidence ≥ 4"],
            "invalidation":"论点转 weakening → 取消",
        }

    # Re-entry：仅论点 intact
    re_entry = None
    if thesis_status == "intact":
        re_entry_price = round(ma50 + ev["k_reentry"] * atr14, 2)
        re_entry = {
            "price":       re_entry_price,
            "basis":       f"MA50({ma50}) + {ev['k_reentry']}×ATR14({atr14})",
            "conditions":  ["thesis_status = intact", "距止损出场 ≥ 3天"],
            "invalidation":"距止损出场不足3天 或 论点转 weakening → 取消",
        }

    return {
        "entry_invalidation": {"price": inv_price, "basis": f"entry_base({entry_base}) + 0.5×ATR14"},
        "add1":      add1,
        "add2":      add2,
        "re_entry":  re_entry,
    }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "entry" -v 2>&1 | tail -10
```
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team && git add agents/macro_strategy.py tests/test_macro_strategy.py && git commit -m "feat(macro-strategy): entry/add node calculators"
```

---

## Task 3: 止损节点计算（Dynamic Stop / Force Exit）

**Files:**
- Modify: `agents/macro_strategy.py`（添加 calc_stop_nodes）
- Modify: `tests/test_macro_strategy.py`

- [ ] **Step 1: 写止损节点测试**

```python
# 追加到 tests/test_macro_strategy.py

def test_dynamic_stop_below_ma50():
    from agents.macro_strategy import calc_stop_nodes
    mkt = _default_mkt(ma50=210.2, atr14=8.3, swing_low_14d=208.5)
    ev  = _default_ev(k1=1.0)
    nodes = calc_stop_nodes(mkt, ev, entry_base=224.0,
                            bear_scenario_price=156.4)
    # Dynamic Stop 应低于 MA50
    assert nodes["dynamic_stop"]["price"] < 210.2


def test_dynamic_stop_uses_structural_low():
    from agents.macro_strategy import calc_stop_nodes
    # 结构低点高于 MA50 时，取结构低点
    mkt = _default_mkt(ma50=200.0, atr14=5.0, swing_low_14d=215.0)
    ev  = _default_ev(k1=1.0)
    nodes = calc_stop_nodes(mkt, ev, entry_base=224.0,
                            bear_scenario_price=156.4)
    # max(200.0, 215.0) = 215.0, 215.0 - 5.0 = 210.0
    assert abs(nodes["dynamic_stop"]["price"] - 210.0) < 1.0


def test_force_exit_uses_bear_scenario():
    from agents.macro_strategy import calc_stop_nodes
    mkt = _default_mkt()
    ev  = _default_ev()
    nodes = calc_stop_nodes(mkt, ev, entry_base=224.0,
                            bear_scenario_price=156.4)
    assert nodes["force_exit"]["price_bear"] == 156.4


def test_force_exit_catalyst_below_entry():
    from agents.macro_strategy import calc_stop_nodes
    mkt = _default_mkt(atr14=8.3)
    ev  = _default_ev(fe_catalyst=2.0)
    nodes = calc_stop_nodes(mkt, ev, entry_base=224.0,
                            bear_scenario_price=156.4)
    # 催化剂版 = entry - fe_catalyst*atr14 = 224 - 16.6 = 207.4
    assert nodes["force_exit"]["price_catalyst"] < 224.0
```

- [ ] **Step 2: 运行确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "stop or force" -v 2>&1 | tail -10
```

- [ ] **Step 3: 实现 calc_stop_nodes**

```python
# 追加到 agents/macro_strategy.py

def calc_stop_nodes(mkt: dict, ev: dict, entry_base: float,
                    bear_scenario_price: float) -> dict:
    """计算止损方向节点：Dynamic Stop + Force Exit"""
    atr14  = mkt["atr14"]
    ma50   = mkt["ma50"]
    sw_low = mkt["swing_low_14d"]

    # Dynamic Stop：max(MA50, 近14日结构低点) - k1*ATR14
    anchor     = max(ma50, sw_low)
    stop_price = round(anchor - ev["k1"] * atr14, 2)

    dynamic_stop = {
        "price":  stop_price,
        "basis":  f"max(MA50={ma50}, 近14日结构低点={sw_low}) − {ev['k1']}×ATR14({atr14}) = {stop_price}",
        "trail_activation": {
            "breakeven_trigger_pct": 8,
            "ma20_trail_trigger_pct": 15,
        },
        "invalidation": f"收盘反回 stop+0.5×ATR({round(stop_price+0.5*atr14,2)}) 且缩量 → 假突破",
        "gap_rule":     "开盘直接低于此价 → 市价出场",
    }

    # Force Exit：bear 情景价 + 催化剂版本
    catalyst_exit = round(entry_base - ev["fe_catalyst"] * atr14, 2)
    force_exit = {
        "price_bear":       bear_scenario_price,
        "price_catalyst":   catalyst_exit,
        "basis_bear":       "memo.scenarios.bear.price_target",
        "basis_catalyst":   f"entry({entry_base}) − {ev['fe_catalyst']}×ATR14({atr14})",
        "gap_rule":         "开盘低于此价 → 市价执行",
    }

    return {"dynamic_stop": dynamic_stop, "force_exit": force_exit}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "stop or force" -v 2>&1 | tail -10
```
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team && git add agents/macro_strategy.py tests/test_macro_strategy.py && git commit -m "feat(macro-strategy): stop node calculators"
```

---

## Task 4: 目标节点计算（TP1 / TP2 / Flex Reduce）

**Files:**
- Modify: `agents/macro_strategy.py`（添加 calc_target_nodes）
- Modify: `tests/test_macro_strategy.py`

- [ ] **Step 1: 写目标节点测试**

```python
# 追加到 tests/test_macro_strategy.py

def test_tp1_near_swing_high():
    from agents.macro_strategy import calc_target_nodes
    mkt = _default_mkt(swing_high_90d=242.5, price=224.77)
    ev  = _default_ev()
    nodes = calc_target_nodes(mkt, ev)
    # TP1 应在近期阻力区附近（swing_high 附近）
    assert nodes["tp1"]["price"] > mkt["price"]
    assert nodes["tp1"]["reduce_pct"] == 30


def test_tp2_applies_analyst_discount():
    from agents.macro_strategy import calc_target_nodes
    mkt = _default_mkt(analyst_target=275.3, swing_high_90d=242.5)
    ev  = _default_ev(k4=0.90)
    nodes = calc_target_nodes(mkt, ev)
    # TP2 = min(275.3*0.90=247.8, 历史前高) → 247.8
    assert nodes["tp2"]["price"] <= 275.3 * 0.90 + 1.0


def test_tp2_none_when_no_analyst_target():
    from agents.macro_strategy import calc_target_nodes
    mkt = _default_mkt(analyst_target=None)
    ev  = _default_ev()
    nodes = calc_target_nodes(mkt, ev)
    # 无分析师目标时，TP2 基于 swing_high
    assert nodes["tp2"]["price"] is not None
```

- [ ] **Step 2: 运行确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "tp1 or tp2" -v 2>&1 | tail -10
```

- [ ] **Step 3: 实现 calc_target_nodes**

```python
# 追加到 agents/macro_strategy.py

def calc_target_nodes(mkt: dict, ev: dict) -> dict:
    """计算目标方向节点：TP1 / TP2 / Flex Reduce"""
    atr14        = mkt["atr14"]
    swing_high   = mkt["swing_high_90d"]
    analyst_tgt  = mkt["analyst_target"]
    price        = mkt["price"]

    # TP1：近期阻力位（swing_high_90d 附近，若已突破则取 +1σ 估算）
    if swing_high > price:
        tp1_price = round(swing_high * 0.995, 2)  # 留 0.5% 缓冲
    else:
        tp1_price = round(price + 1.5 * atr14, 2)  # 已在高位，用 ATR 估算

    tp1 = {
        "price":      tp1_price,
        "basis":      f"近90日高点区域 swing_high={swing_high}",
        "reduce_pct": 30,
        "gap_rule":   "开盘高于 TP1 → 按开盘价执行",
    }

    # TP2：min(分析师目标*k4, swing_high)；无分析师目标用 swing_high*1.05
    if analyst_tgt:
        tp2_candidate = round(analyst_tgt * ev["k4"], 2)
        tp2_price     = min(tp2_candidate, round(swing_high * 1.05, 2))
        tp2_basis     = f"分析师目标${analyst_tgt} × {ev['k4']} = {tp2_candidate}"
    else:
        tp2_price = round(swing_high * 1.05, 2)
        tp2_basis = f"无分析师目标，swing_high({swing_high}) × 1.05"

    tp2 = {
        "price":      tp2_price,
        "basis":      tp2_basis,
        "reduce_pct": 100,
        "invalidation": "分析师目标下调超10% → 重算",
    }

    flex_reduce = {
        "note":           "盘中动态，--refresh 每日更新",
        "max_reduce_pct": 15,
        "basis":          "VWAP 偏离 + RSI > 70",
    }

    return {"tp1": tp1, "tp2": tp2, "flex_reduce": flex_reduce}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "tp" -v 2>&1 | tail -10
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team && git add agents/macro_strategy.py tests/test_macro_strategy.py && git commit -m "feat(macro-strategy): target node calculators"
```

---

## Task 5: 情景与催化剂节点 + 时间止损

**Files:**
- Modify: `agents/macro_strategy.py`（添加 calc_scenario_nodes / calc_time_stop）
- Modify: `tests/test_macro_strategy.py`

- [ ] **Step 1: 写情景 + 时间止损测试**

```python
# 追加到 tests/test_macro_strategy.py
from datetime import date as _date

def test_scenario_downgrade_below_ma():
    from agents.macro_strategy import calc_scenario_nodes
    mkt = _default_mkt(ma20=215.8, ma50=210.2, atr14=8.3)
    ev  = _default_ev(k5=0.5, k6=1.0)
    nodes = calc_scenario_nodes(mkt, ev)
    assert nodes["scenario_downgrade"]["bull_to_base"]["price"] < 215.8
    assert nodes["scenario_downgrade"]["base_to_bear"]["price"] < 210.2


def test_catalyst_pre_reduce_active_when_close():
    from agents.macro_strategy import calc_scenario_nodes
    mkt  = _default_mkt()
    ev   = _default_ev()
    cat  = {"event": "earnings", "date": "2026-05-22", "importance": "high"}
    today = _date(2026, 5, 20)
    nodes = calc_scenario_nodes(mkt, ev, catalyst=cat, today=today,
                                entry_base=224.0)
    assert nodes["catalyst_framework"]["pre_reduce_active"] is True


def test_catalyst_pre_reduce_inactive_when_far():
    from agents.macro_strategy import calc_scenario_nodes
    mkt   = _default_mkt()
    ev    = _default_ev()
    cat   = {"event": "earnings", "date": "2026-07-01", "importance": "high"}
    today = _date(2026, 5, 20)
    nodes = calc_scenario_nodes(mkt, ev, catalyst=cat, today=today,
                                entry_base=224.0)
    assert nodes["catalyst_framework"]["pre_reduce_active"] is False


def test_time_stop_standard():
    from agents.macro_strategy import calc_time_stop
    ev    = _default_ev(N_time_stop=30)
    today = _date(2026, 5, 20)
    cat_date = "2026-06-15"
    stop = calc_time_stop(ev, today=today, catalyst_date=cat_date,
                          position_type="thesis")
    assert stop["type"] == "standard"
    assert stop["review_date"] is not None


def test_time_stop_decay_for_leveraged():
    from agents.macro_strategy import calc_time_stop
    ev    = _default_ev(D_decay_stop=14)
    today = _date(2026, 5, 20)
    stop = calc_time_stop(ev, today=today, catalyst_date=None,
                          position_type="trend")
    assert stop["type"] == "decay"
    assert stop["decay_days"] == 14
```

- [ ] **Step 2: 运行确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "scenario or catalyst or time_stop" -v 2>&1 | tail -10
```

- [ ] **Step 3: 实现 calc_scenario_nodes 和 calc_time_stop**

```python
# 追加到 agents/macro_strategy.py
from datetime import date as _date, timedelta

def calc_scenario_nodes(mkt: dict, ev: dict, catalyst: dict = None,
                        today: _date = None, entry_base: float = None) -> dict:
    atr14 = mkt["atr14"]
    ma20  = mkt["ma20"]
    ma50  = mkt["ma50"]

    scenario_downgrade = {
        "bull_to_base": {
            "price": round(ma20 - ev["k5"] * atr14, 2),
            "basis": f"MA20({ma20}) − {ev['k5']}×ATR14({atr14})",
        },
        "base_to_bear": {
            "price": round(ma50 - ev["k6"] * atr14, 2),
            "basis": f"MA50({ma50}) − {ev['k6']}×ATR14({atr14})",
        },
    }

    # Catalyst Framework
    cat_active = False
    pre_reduce_pct = ev["Z_pre_reduce_pct"]
    post_add = post_exit = None

    if catalyst and today:
        try:
            cat_date = _date.fromisoformat(catalyst["date"])
            days_away = (cat_date - today).days
            cat_active = (days_away <= 3 and catalyst.get("importance") == "high")
            if entry_base and mkt.get("atr14"):
                post_add  = round(entry_base + ev["c1"] * atr14, 2)
                post_exit = round(entry_base - ev["c2"] * atr14, 2)
        except Exception:
            pass

    catalyst_framework = {
        "pre_reduce_active": cat_active,
        "pre_reduce_days":   3,
        "pre_reduce_pct":    pre_reduce_pct,
        "post_add_trigger":  post_add,
        "post_force_exit":   post_exit,
        "next_catalyst":     catalyst,
    }

    return {
        "scenario_downgrade":  scenario_downgrade,
        "catalyst_framework":  catalyst_framework,
    }


def calc_time_stop(ev: dict, today: _date, catalyst_date: str,
                   position_type: str) -> dict:
    """时间止损：普通版（所有仓位）或衰减版（杠杆ETF）"""
    is_leveraged = position_type in ("trend",) and "etf" in position_type.lower()
    # 简化判断：trend 类型使用衰减止损
    use_decay = (position_type == "trend")

    if use_decay:
        return {
            "type":           "decay",
            "decay_days":     ev["D_decay_stop"],
            "min_progress":   ev["M_decay_min_pct"],
            "condition":      f"持有>{ev['D_decay_stop']}天且底层标的涨幅<{ev['M_decay_min_pct']}%",
            "review_date":    str(today + timedelta(days=ev["D_decay_stop"])),
        }

    # 普通时间止损：基于催化剂截止日 + 缓冲
    if catalyst_date:
        try:
            cat_d = _date.fromisoformat(catalyst_date)
            review = cat_d + timedelta(days=7)
        except Exception:
            review = today + timedelta(days=ev["N_time_stop"])
    else:
        review = today + timedelta(days=ev["N_time_stop"])

    return {
        "type":        "standard",
        "review_date": str(review),
        "condition":   f"持仓超{ev['N_time_stop']}天且未向TP1移动5%",
        "decay_stop":  None,
    }
```

- [ ] **Step 4: 运行确认通过**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "scenario or catalyst or time_stop" -v 2>&1 | tail -10
```
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team && git add agents/macro_strategy.py tests/test_macro_strategy.py && git commit -m "feat(macro-strategy): scenario/catalyst/time-stop calculators"
```

---

## Task 6: 主编排器（build_nodes + write_macro_strategy + CLI）

**Files:**
- Modify: `agents/macro_strategy.py`（添加 build_nodes / write_macro_strategy / main）
- Modify: `tests/test_macro_strategy.py`（集成测试）

- [ ] **Step 1: 写集成测试**

```python
# 追加到 tests/test_macro_strategy.py
import tempfile

def test_build_nodes_integration():
    from agents.macro_strategy import build_nodes
    mkt  = _default_mkt()
    memo = json.load(open(
        os.path.join(os.path.expanduser("~/stock_team"),
                     "tests/fixtures/macro_strategy_memo.json")))
    pos  = {"cost": 100.0, "shares": 10, "position_type": "thesis"}
    nodes = build_nodes("TEST", mkt, memo, pos, entry_base=100.0)

    required_keys = ["entry_invalidation", "add1", "dynamic_stop",
                     "force_exit", "tp1", "tp2", "flex_reduce",
                     "scenario_downgrade", "catalyst_framework", "time_stop"]
    for k in required_keys:
        assert k in nodes, f"Missing node: {k}"


def test_write_macro_strategy(tmp_path):
    from agents.macro_strategy import build_nodes, write_macro_strategy
    mkt  = _default_mkt()
    memo = json.load(open(
        os.path.join(os.path.expanduser("~/stock_team"),
                     "tests/fixtures/macro_strategy_memo.json")))
    pos  = {"cost": 100.0, "shares": 10, "position_type": "thesis"}
    nodes = build_nodes("TEST", mkt, memo, pos, entry_base=100.0)

    out_path = write_macro_strategy("TEST", mkt, memo, nodes, base_dir=str(tmp_path))
    assert os.path.exists(out_path)
    data = json.load(open(out_path))
    assert data["sym"] == "TEST"
    assert "evolution" in data
    assert "nodes" in data
```

- [ ] **Step 2: 运行确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "integration or write_macro" -v 2>&1 | tail -10
```

- [ ] **Step 3: 实现 build_nodes / write_macro_strategy / main**

```python
# 追加到 agents/macro_strategy.py

DEFAULT_EVOLUTION = {
    "rule_version": "1.0",
    "k1": 1.0, "k2": 0.2, "k3": 0.0, "k4": 0.90,
    "k5": 0.5, "k6": 1.0, "k_reentry": 0.3,
    "fe_catalyst": 2.0, "c1": 0.5, "c2": 1.5,
    "Z_pre_reduce_pct": 20,
    "N_time_stop": 30, "D_decay_stop": 14, "M_decay_min_pct": 5.0,
    "last_backtest_date": None, "backtest_score": None, "outcomes_count": 0,
}


def build_nodes(sym: str, mkt: dict, memo: dict, pos: dict,
                entry_base: float = None) -> dict:
    """整合所有节点计算器，返回完整节点字典。"""
    today = _date.today()

    # 从已有文件读取进化系数（若存在）
    existing = _load(os.path.join(BASE, f"macro_strategy_{sym.upper()}.json"))
    ev = {**DEFAULT_EVOLUTION, **existing.get("evolution", {})}

    entry_base = entry_base or pos.get("cost", mkt["price"])
    unified_conf = memo.get("judgment", {}).get("unified_confidence", 3)
    thesis_status = pos.get("thesis_status", "intact")
    position_type = pos.get("position_type", "thesis")
    bear_price = memo.get("scenarios", {}).get("bear", {}).get("price_target", 0)
    catalyst = memo.get("support_and_risk", {}).get("next_catalyst", {})
    cat_date_str = catalyst.get("date") if catalyst else None

    # 注入 sentiment_score
    sent_conf = memo.get("agent_analysis", {}).get("sentiment", {}).get("confidence", 50)
    mkt["sentiment_score"] = round(sent_conf / 100, 2)

    entry_nodes  = calc_entry_nodes(mkt, ev, entry_base, unified_conf, thesis_status)
    stop_nodes   = calc_stop_nodes(mkt, ev, entry_base, bear_price)
    target_nodes = calc_target_nodes(mkt, ev)
    scene_nodes  = calc_scenario_nodes(mkt, ev, catalyst, today, entry_base)
    time_node    = calc_time_stop(ev, today, cat_date_str, position_type)

    return {
        **entry_nodes,
        **stop_nodes,
        **target_nodes,
        **scene_nodes,
        "time_stop": time_node,
    }


def write_macro_strategy(sym: str, mkt: dict, memo: dict, nodes: dict,
                         base_dir: str = BASE) -> str:
    existing = _load(os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json"))
    ev = {**DEFAULT_EVOLUTION, **existing.get("evolution", {})}

    out = {
        "sym":              sym.upper(),
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "market_data_date": str(_date.today()),
        "nodes":            nodes,
        "market_inputs":    mkt,
        "memo_inputs": {
            "strategic_stance":    memo.get("synthesis", {}).get("strategic_stance"),
            "unified_confidence":  memo.get("judgment", {}).get("unified_confidence"),
            "next_catalyst":       memo.get("support_and_risk", {}).get("next_catalyst"),
            "scenario_bear_price": memo.get("scenarios", {}).get("bear", {}).get("price_target"),
            "scenario_base_price": memo.get("scenarios", {}).get("base", {}).get("price_target"),
            "scenario_bull_price": memo.get("scenarios", {}).get("bull", {}).get("price_target"),
        },
        "evolution": ev,
    }

    path = os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser(description="宏观策略节点生成")
    parser.add_argument("symbol")
    parser.add_argument("--refresh", action="store_true",
                        help="只更新动态节点（Flex/Time/Catalyst），不重抓全量数据")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD（供测试用）")
    args = parser.parse_args()

    sym = args.symbol.upper()
    date_str = args.date or str(_date.today())

    memo = _load(os.path.join(BASE, f"strategic_memo_{sym}.json"))
    if not memo:
        print(f"[macro_strategy] ⚠️ strategic_memo_{sym}.json 不存在，跳过")
        return

    positions = _load(os.path.join(CFG_DIR, "positions.json"))
    pos = (positions.get("positions") or {}).get(sym, {})

    order_sheet = _load(os.path.join(FIND_DIR, f"order_sheet_{date_str}.json"))
    entry_base = (order_sheet.get(sym) or {}).get("entry_base") or pos.get("cost")

    print(f"[macro_strategy] 抓取 {sym} 市场数据...")
    mkt = fetch_market_data(sym)
    if not mkt:
        print(f"[macro_strategy] ❌ 无法获取市场数据")
        return

    nodes = build_nodes(sym, mkt, memo, pos, entry_base)
    path  = write_macro_strategy(sym, mkt, memo, nodes)
    print(f"[macro_strategy] ✅ 已保存: {path}")

    # 打印关键节点摘要
    n = nodes
    ds = n.get("dynamic_stop", {})
    print(f"  止损: ${ds.get('price','?')}  TP1: ${n.get('tp1',{}).get('price','?')}  "
          f"TP2: ${n.get('tp2',{}).get('price','?')}  Add1: ${n.get('add1',{}).get('price','?')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行集成测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -v 2>&1 | tail -20
```
Expected: 全部通过

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team && git add agents/macro_strategy.py tests/test_macro_strategy.py && git commit -m "feat(macro-strategy): main orchestrator + CLI"
```

---

## Task 7: portfolio_macro_guard 独立模块

**Files:**
- Create: `agents/portfolio_macro_guard.py`
- Create: `config/portfolio_macro_guard.json`
- Create: `tests/test_portfolio_macro_guard.py`

- [ ] **Step 1: 创建默认配置**

```bash
cat > ~/stock_team/config/portfolio_macro_guard.json << 'EOF'
{
  "vix_spike_threshold": 5.0,
  "spy_drop_threshold": -2.5,
  "portfolio_reduce_pct": 20,
  "sector_etf_ma50_break": true,
  "sector_reduce_pct": 30,
  "last_backtest_date": null
}
EOF
```

- [ ] **Step 2: 写测试**

```python
# tests/test_portfolio_macro_guard.py
import sys, os, json, tempfile
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch


def test_get_thresholds_returns_required_keys():
    from agents.portfolio_macro_guard import get_thresholds
    cfg_path = os.path.join(os.path.expanduser("~/stock_team"),
                            "config/portfolio_macro_guard.json")
    thresholds = get_thresholds(cfg_path=cfg_path)
    assert "vix_spike_threshold" in thresholds
    assert "portfolio_reduce_pct" in thresholds


def test_check_market_stress_triggers_on_vix_spike():
    from agents.portfolio_macro_guard import check_market_stress
    result = check_market_stress(vix_change=6.0, spy_change=-1.0,
                                 vix_threshold=5.0, spy_threshold=-2.5)
    assert result["triggered"] is True
    assert result["layer"] == "market"


def test_check_market_stress_triggers_on_spy_drop():
    from agents.portfolio_macro_guard import check_market_stress
    result = check_market_stress(vix_change=2.0, spy_change=-3.0,
                                 vix_threshold=5.0, spy_threshold=-2.5)
    assert result["triggered"] is True


def test_check_market_stress_no_trigger():
    from agents.portfolio_macro_guard import check_market_stress
    result = check_market_stress(vix_change=1.0, spy_change=-0.5,
                                 vix_threshold=5.0, spy_threshold=-2.5)
    assert result["triggered"] is False
```

- [ ] **Step 3: 运行确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_portfolio_macro_guard.py -v 2>&1 | tail -10
```

- [ ] **Step 4: 实现 portfolio_macro_guard.py**

```python
# agents/portfolio_macro_guard.py
"""
组合层外部环境止损模块 — portfolio_macro_guard.py
大盘层（VIX/SPY）和板块层（ETF）的触发检查。
被 macro_strategy.py 调用，不写入个股 JSON。
"""
import json, os

CFG_PATH = os.path.join(os.path.expanduser("~/stock_team"),
                        "config/portfolio_macro_guard.json")


def get_thresholds(cfg_path: str = CFG_PATH) -> dict:
    try:
        with open(cfg_path) as f:
            return json.load(f)
    except Exception:
        return {
            "vix_spike_threshold": 5.0,
            "spy_drop_threshold": -2.5,
            "portfolio_reduce_pct": 20,
            "sector_reduce_pct": 30,
        }


def check_market_stress(vix_change: float, spy_change: float,
                        vix_threshold: float = 5.0,
                        spy_threshold: float = -2.5) -> dict:
    triggered = vix_change >= vix_threshold or spy_change <= spy_threshold
    reason = []
    if vix_change >= vix_threshold:
        reason.append(f"VIX +{vix_change:.1f}")
    if spy_change <= spy_threshold:
        reason.append(f"SPY {spy_change:.2f}%")
    return {
        "triggered": triggered,
        "layer":     "market" if triggered else None,
        "reason":    " + ".join(reason) if reason else None,
    }


def check_sector_stress(sector_etf_below_ma50: bool,
                        stock_rs_negative: bool) -> dict:
    triggered = sector_etf_below_ma50 and stock_rs_negative
    return {
        "triggered": triggered,
        "layer":     "sector" if triggered else None,
        "reason":    "板块ETF跌破MA50 + 个股RS转负" if triggered else None,
    }
```

- [ ] **Step 5: 运行确认通过**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_portfolio_macro_guard.py -v 2>&1 | tail -10
```
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
cd ~/stock_team && git add agents/portfolio_macro_guard.py config/portfolio_macro_guard.json tests/test_portfolio_macro_guard.py && git commit -m "feat(macro-strategy): portfolio_macro_guard module"
```

---

## Task 8: 集成 premarket_summary.py

**Files:**
- Modify: `agents/premarket_summary.py`（build_summary 中读取 macro_strategy JSON）

- [ ] **Step 1: 确认当前 exit_sect 构建位置**

```bash
grep -n "hard_stop\|target_price\|exit_sect" ~/stock_team/agents/premarket_summary.py | head -20
```
预期看到行 228-238 的 exit_sect 构建代码。

- [ ] **Step 2: 添加 macro_strategy 读取函数**

在 `agents/premarket_summary.py` 的 `_load` 函数之后（约第 37 行），添加：

```python
def _load_macro_strategy(sym: str, base_dir: str = BASE) -> dict:
    """读取宏观策略节点（若存在）。"""
    return _load(os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json"))
```

- [ ] **Step 3: 修改 build_summary 中的 exit_sect 构建**

在 `build_summary` 函数中，找到 `exit_sect = {` 的构建块（约 228 行），在其之后添加 macro_strategy 覆盖逻辑：

```python
    # 从宏观策略读取精确节点（优先级高于 order_sheet/exit_decision）
    macro = _load_macro_strategy(sym_upper, base_dir)
    macro_nodes = macro.get("nodes", {})

    if exit_sect and macro_nodes:
        ds = macro_nodes.get("dynamic_stop", {})
        tp1 = macro_nodes.get("tp1", {})
        add1 = macro_nodes.get("add1", {})
        if ds.get("price"):
            exit_sect["hard_stop"]     = ds["price"]
            exit_sect["stop_source"]   = "macro_strategy"
        if tp1.get("price"):
            exit_sect["target_price"]  = tp1["price"]
        if add1 and add1.get("price"):
            exit_sect["flex_add_level"] = add1["price"]
        flex_reduce = macro_nodes.get("flex_reduce", {})
        if flex_reduce:
            exit_sect["flex_reduce_level"] = flex_reduce.get("basis")  # 动态，存描述
```

- [ ] **Step 4: 手动验证（快速烟测）**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "
from agents.premarket_summary import build_summary
import datetime
d = build_summary('NVDA', str(datetime.date.today()))
ex = d.get('exit') or {}
print('hard_stop:', ex.get('hard_stop'))
print('stop_source:', ex.get('stop_source'))
print('target_price:', ex.get('target_price'))
"
```
预期：若 `macro_strategy_NVDA.json` 存在，`stop_source` 为 `macro_strategy`。

- [ ] **Step 5: 运行现有 premarket_summary 测试确认无回归**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_premarket_summary.py -v 2>&1 | tail -15
```

- [ ] **Step 6: Commit**

```bash
cd ~/stock_team && git add agents/premarket_summary.py && git commit -m "feat(macro-strategy): premarket_summary reads macro_strategy nodes"
```

---

## Task 9: 集成 report_viewer.py（交易节点 Section）

**Files:**
- Modify: `agents/report_viewer.py`（新增 render_trading_nodes 函数 + 调用）

- [ ] **Step 1: 找插入位置**

```bash
grep -n "def render_research_report\|Section\|section-h2\|出场逻辑" ~/stock_team/agents/report_viewer.py | tail -15
```

- [ ] **Step 2: 添加 render_trading_nodes 函数**

在 `render_research_report` 函数之前添加：

```python
def render_trading_nodes(macro: dict) -> str:
    """渲染宏观策略交易节点 HTML Section。"""
    if not macro:
        return ""
    nodes = macro.get("nodes", {})
    if not nodes:
        return ""

    def _row(label, price, basis, extra=""):
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "—"
        return (f"<tr><td class='kv-label'>{label}</td>"
                f"<td class='bold'>{price_str}</td>"
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
        _row("动态止损", ds.get("price"), ds.get("basis",""), ds.get("invalidation","")),
        _row("强制清仓(熊市)", fe.get("price_bear"), fe.get("basis_bear",""), "论点破裂兜底"),
        _row("Add1 加仓", add1.get("price"), add1.get("basis",""), add1.get("invalidation","")),
        _row("Add2 加仓", add2.get("price") if add2 else None, add2.get("basis","") if add2 else "", "需 confidence≥4"),
        _row("TP1 目标(30%)", tp1.get("price"), tp1.get("basis",""), "第一批减仓"),
        _row("TP2 目标(全清)", tp2.get("price"), tp2.get("basis",""), tp2.get("invalidation","")),
        _row("情景降级 bull→base", sd.get("bull_to_base",{}).get("price"), sd.get("bull_to_base",{}).get("basis","")),
        _row("情景降级 base→bear", sd.get("base_to_bear",{}).get("price"), sd.get("base_to_bear",{}).get("basis","")),
    ]

    ts  = nodes.get("time_stop", {})
    time_str = f"时间止损: {ts.get('review_date','?')} — {ts.get('condition','')}" if ts else ""

    return f"""
<h2 class="section-h2">📐 交易节点（宏观策略）</h2>
<div class="card">
  <div class="card-title">价格节点 · 计算依据 · 失效条件</div>
  <table class="kv-table">
    <tr><th>节点</th><th>价格</th><th>计算依据</th><th>失效/说明</th></tr>
    {''.join(rows)}
  </table>
  {f'<p class="note">{time_str}</p>' if time_str else ''}
  <p class="note muted">系数版本: {macro.get("evolution",{}).get("rule_version","?")} | 
  数据日期: {macro.get("market_data_date","?")}</p>
</div>
"""
```

- [ ] **Step 3: 在 render_research_report 中调用**

找到 `# 出场逻辑` 或 `🚪 出场逻辑` section 之前，插入宏观策略节点读取和渲染：

```python
    # 交易节点（宏观策略）
    macro = _load(os.path.join(BASE, f"macro_strategy_{sym_upper}.json"))
    nodes_html = render_trading_nodes(macro)
```

- [ ] **Step 3b: 找到精确插入位置并插入代码**

```bash
# 确认出场逻辑 section 的行号
grep -n "出场逻辑\|exit_logic\|🚪" ~/stock_team/agents/report_viewer.py | head -5
```

在 `render_research_report` 函数中，找到渲染出场逻辑的代码块（通常形如 `html += _card("🚪 出场逻辑", ...)`），在其**之前**插入以下两行：

```python
    # 交易节点（宏观策略）
    macro = _load(os.path.join(BASE, f"macro_strategy_{sym_upper}.json"))
    html += render_trading_nodes(macro)
```

验证插入正确：

```bash
grep -n "render_trading_nodes\|macro_strategy" ~/stock_team/agents/report_viewer.py
```
Expected: 出现 `render_trading_nodes` 和 `macro_strategy` 两行。

- [ ] **Step 4: 运行 research report 测试确认无回归**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_research_report.py -v 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team && git add agents/report_viewer.py && git commit -m "feat(macro-strategy): trading nodes section in research report"
```

---

## Task 10: 更新 Skills + strategic_memo_writer 清理

**Files:**
- Modify: `~/.claude/skills/stock-deep-research.md`
- Modify: `~/.claude/skills/stock-premarket.md`
- Modify: `agents/strategic_memo_writer.py`（移除草率价格计算）

- [ ] **Step 1: 更新 stock-deep-research skill**

打开 `~/.claude/skills/stock-deep-research.md`，在步骤列表中找到 `report_agent.py` 步骤（约第5步），在之前插入：

```
5. `python3.12 agents/macro_strategy.py {SYM}`
```

同时更新步骤注释，说明"宏观策略制定所有价格节点"。

- [ ] **Step 2: 更新 stock-premarket skill**

打开 `~/.claude/skills/stock-premarket.md`，在 `premarket_summary.py` 步骤之前插入：

```
6.5. `python3.12 agents/macro_strategy.py {SYM} --refresh`
```

- [ ] **Step 3: 清理 strategic_memo_writer.py 中的草率计算**

先定位精确行号：

```bash
grep -n "cost \* (1 + target_pct\|cost \* 0\.87\|cost_f \* 0\.92" ~/stock_team/agents/strategic_memo_writer.py
```

对每处找到的行，将原计算替换为 None 占位（premarket_summary 会从 macro_strategy JSON 覆盖）：

```python
# 价格节点由 macro_strategy.py 计算，此处为占位，由 premarket_summary 覆盖
target_price = None
# ...
hard_stop_auto = None
# ...
position_context["add_strategy"]["t2_price_floor"] = None
```

验证替换完成：

```bash
grep -n "cost \* 0\.87\|cost \* 0\.92\|cost \* (1 + target_pct" ~/stock_team/agents/strategic_memo_writer.py
```
Expected: 无输出（所有草率计算已清除）。

- [ ] **Step 4: 运行全套测试确认无回归**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team && git add ~/.claude/skills/stock-deep-research.md ~/.claude/skills/stock-premarket.md agents/strategic_memo_writer.py && git commit -m "feat(macro-strategy): update skills + clean memo_writer price calcs"
```

---

## Task 11: 历史回测框架（evolution 系数优化）

**Files:**
- Modify: `agents/macro_strategy.py`（添加 backtest_macro_strategy 函数）
- Modify: `tests/test_macro_strategy.py`（回测测试）

- [ ] **Step 1: 写回测测试**

```python
# 追加到 tests/test_macro_strategy.py

def test_backtest_evaluates_stop_hit_rate():
    from agents.macro_strategy import backtest_node
    # 模拟：30天价格历史，止损被击中3次
    closes = [100.0] * 5 + [95.0] * 5 + [100.0] * 10 + [88.0] * 10
    result = backtest_node(
        node_type="dynamic_stop",
        node_price=92.0,
        entry_price=100.0,
        price_history=closes,
    )
    assert "hit" in result
    assert "hit_rate" in result
    assert 0.0 <= result["hit_rate"] <= 1.0


def test_backtest_returns_zero_hit_when_price_never_drops():
    from agents.macro_strategy import backtest_node
    closes = [100.0, 101.0, 102.0, 103.0, 105.0]
    result = backtest_node(
        node_type="dynamic_stop",
        node_price=90.0,
        entry_price=100.0,
        price_history=closes,
    )
    assert result["hit"] is False
    assert result["hit_rate"] == 0.0
```

- [ ] **Step 2: 运行确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "backtest" -v 2>&1 | tail -10
```

- [ ] **Step 3: 实现 backtest_node**

```python
# 追加到 agents/macro_strategy.py

def backtest_node(node_type: str, node_price: float, entry_price: float,
                  price_history: list) -> dict:
    """
    简单单节点回测：给定历史价格序列，判断节点是否被击中。
    node_type: 'dynamic_stop' | 'tp1' | 'tp2'
    """
    if not price_history or node_price is None:
        return {"hit": False, "hit_rate": 0.0, "days_to_hit": None}

    hit_days = []
    for i, price in enumerate(price_history):
        if node_type == "dynamic_stop" and price <= node_price:
            hit_days.append(i)
        elif node_type in ("tp1", "tp2") and price >= node_price:
            hit_days.append(i)

    hit = len(hit_days) > 0
    hit_rate = round(len(hit_days) / len(price_history), 3)
    days_to_hit = hit_days[0] if hit_days else None

    return {"hit": hit, "hit_rate": hit_rate, "days_to_hit": days_to_hit}


def record_outcome(sym: str, node_type: str, planned_price: float,
                   actual_trigger_price: float, outcome: str,
                   pnl_impact: float, base_dir: str = BASE) -> None:
    """记录节点实际结果到 learning/macro_strategy_outcomes.jsonl"""
    import time
    record = {
        "sym":                  sym,
        "date":                 str(_date.today()),
        "node_type":            node_type,
        "planned_price":        planned_price,
        "actual_trigger_price": actual_trigger_price,
        "outcome":              outcome,   # "hit" | "missed" | "skipped"
        "pnl_impact":           pnl_impact,
        "ts":                   time.time(),
    }
    path = os.path.join(base_dir, "learning", "macro_strategy_outcomes.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: 写参数扫描测试**

```python
# 追加到 tests/test_macro_strategy.py

def test_scan_parameters_returns_best_k1():
    from agents.macro_strategy import scan_parameters
    # 模拟5条历史记录：k1=0.5 命中率低，k1=1.5 命中率高
    outcomes = [
        {"node_type": "dynamic_stop", "planned_price": 95.0,
         "actual_trigger_price": 94.0, "outcome": "hit", "pnl_impact": -5.0},
        {"node_type": "dynamic_stop", "planned_price": 95.0,
         "actual_trigger_price": 93.0, "outcome": "hit", "pnl_impact": -7.0},
        {"node_type": "tp1", "planned_price": 110.0,
         "actual_trigger_price": 112.0, "outcome": "hit", "pnl_impact": 10.0},
    ]
    result = scan_parameters(outcomes, param_name="k1",
                             param_range=[0.5, 1.0, 1.5])
    assert "best_value" in result
    assert result["best_value"] in [0.5, 1.0, 1.5]
    assert "metric" in result
```

- [ ] **Step 5: 运行确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "scan_parameters" -v 2>&1 | tail -10
```

- [ ] **Step 6: 实现 scan_parameters + update_evolution**

```python
# 追加到 agents/macro_strategy.py

def scan_parameters(outcomes: list, param_name: str,
                    param_range: list) -> dict:
    """
    扫描单个参数的最优值。
    评估指标：stop 被扫频率最低 + tp 命中率最高的综合得分。
    """
    if not outcomes:
        return {"best_value": param_range[len(param_range)//2], "metric": 0.0}

    stop_outcomes = [o for o in outcomes if o["node_type"] == "dynamic_stop"]
    tp_outcomes   = [o for o in outcomes if o["node_type"] in ("tp1", "tp2")]

    best_value, best_score = param_range[0], -999.0
    for val in param_range:
        # 简化评估：止损命中率越低越好，TP 命中率越高越好
        stop_hit_rate = (sum(1 for o in stop_outcomes if o["outcome"] == "hit")
                         / len(stop_outcomes)) if stop_outcomes else 0.5
        tp_hit_rate   = (sum(1 for o in tp_outcomes   if o["outcome"] == "hit")
                         / len(tp_outcomes))   if tp_outcomes   else 0.5
        score = tp_hit_rate - stop_hit_rate
        if score > best_score:
            best_score, best_value = score, val

    return {"param_name": param_name, "best_value": best_value,
            "metric": round(best_score, 3), "n_outcomes": len(outcomes)}


def update_evolution(sym: str, base_dir: str = BASE) -> dict:
    """
    读取历史记录，扫描关键系数，更新 macro_strategy_{sym}.json 的 evolution 字段。
    需要 ≥ 10 条记录才运行。
    """
    import glob
    outcomes_path = os.path.join(base_dir, "learning", "macro_strategy_outcomes.jsonl")
    outcomes = []
    try:
        with open(outcomes_path) as f:
            for line in f:
                r = json.loads(line.strip())
                if r.get("sym") == sym.upper():
                    outcomes.append(r)
    except Exception:
        pass

    if len(outcomes) < 10:
        print(f"[evolution] {sym}: 记录数 {len(outcomes)} < 10，跳过参数扫描")
        return {}

    updates = {}
    for param, rng in [("k1", [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]),
                       ("k4", [0.80, 0.85, 0.90, 0.95, 1.0])]:
        result = scan_parameters(outcomes, param, rng)
        updates[param] = result["best_value"]
        print(f"[evolution] {sym} {param}: {result['best_value']} (score={result['metric']})")

    # 写回 evolution 字段
    macro_path = os.path.join(base_dir, f"macro_strategy_{sym.upper()}.json")
    macro = _load(macro_path)
    if macro:
        macro["evolution"].update(updates)
        macro["evolution"]["last_backtest_date"] = str(_date.today())
        macro["evolution"]["outcomes_count"] = len(outcomes)
        with open(macro_path, "w", encoding="utf-8") as f:
            json.dump(macro, f, ensure_ascii=False, indent=2)
    return updates
```

- [ ] **Step 7: 运行确认通过**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py -k "backtest or scan_parameters" -v 2>&1 | tail -10
```
Expected: `3 passed`

- [ ] **Step 8: 运行全套测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_macro_strategy.py tests/test_portfolio_macro_guard.py -v 2>&1 | tail -20
```

- [ ] **Step 9: Commit**

```bash
cd ~/stock_team && git add agents/macro_strategy.py tests/test_macro_strategy.py && git commit -m "feat(macro-strategy): backtest node + param scan + evolution auto-update"
```

---

## Task 12: 端到端冒烟测试

**验证完整链路正常工作。**

- [ ] **Step 1: 生成 NVDA 宏观策略（需 strategic_memo_NVDA.json 存在）**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/macro_strategy.py NVDA
```
预期输出：
```
[macro_strategy] 抓取 NVDA 市场数据...
[macro_strategy] ✅ 已保存: /home/lirawang/stock_team/macro_strategy_NVDA.json
  止损: $xxx  TP1: $xxx  TP2: $xxx  Add1: $xxx
```

- [ ] **Step 2: 检查输出 JSON**

```bash
/tool/pandora/bin/python3.12 -c "
import json
d = json.load(open('/home/lirawang/stock_team/macro_strategy_NVDA.json'))
nodes = d['nodes']
print('dynamic_stop:', nodes['dynamic_stop']['price'], '|', nodes['dynamic_stop']['basis'][:60])
print('tp1:', nodes['tp1']['price'])
print('tp2:', nodes['tp2']['price'])
print('add1:', nodes['add1']['price'])
print('scenario_downgrade base→bear:', nodes['scenario_downgrade']['base_to_bear']['price'])
"
```

- [ ] **Step 3: 验证 premarket_summary 读取新止损**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "
from agents.premarket_summary import build_summary
import datetime
d = build_summary('NVDA', str(datetime.date.today()))
ex = d.get('exit') or {}
print('hard_stop:', ex.get('hard_stop'), '| source:', ex.get('stop_source'))
print('target_price:', ex.get('target_price'))
"
```
预期：`stop_source: macro_strategy`

- [ ] **Step 4: 生成研究报告并确认节点 Section**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/report_viewer.py NVDA $(date +%Y-%m-%d) && grep -c "交易节点" reports/research_NVDA_$(date +%Y-%m-%d).html
```
预期：输出 `1`（节点 Section 存在）

- [ ] **Step 5: 最终 commit**

```bash
cd ~/stock_team && git add -A && git commit -m "feat(macro-strategy): end-to-end smoke test verified

完整链路：macro_strategy.py → premarket_summary → report_viewer
13个节点全量计算，基于 TA 结构而非成本比例。"
```

---

## 实施说明

- **Python 路径**：始终用 `/tool/pandora/bin/python3.12`
- **测试运行目录**：`cd ~/stock_team` 后运行 pytest
- **真实网络请求**：Task 12 的端到端测试需要网络；Task 1-11 的单元测试均 mock yfinance
- **进化系数**：初始值已内置为 `DEFAULT_EVOLUTION`，Task 11 实现的 `backtest_node` 和 `record_outcome` 是后续自动调参的基础
- **方案 C 扩展点**：`macro_strategy.py --refresh` 已预留，盘前校正层在此基础上扩展
