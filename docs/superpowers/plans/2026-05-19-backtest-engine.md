# 历史回测引擎 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/backtest_engine.py`，实现技术信号参数扫描（Track A）和简化框架回测，为 `decision_thresholds.json` 提供数据驱动的阈值依据；修改 `harvest_agent.py` 添加 `has_catalyst` 字段启动 Track C 前向验证。

**Architecture:** `backtest_engine.py` 分三层：(1) 数据获取层（yfinance OHLCV + 宏观代理），(2) 信号计算层（每日信号值计算），(3) 分析层（单信号扫描 / 组合扫描 / 框架模拟）。输出写入 `findings/` 并可选更新 `config/decision_thresholds.json`（仅在胜率提升 > 5pp 时）。

**Tech Stack:** Python 3.12, yfinance, pandas, json

**范围限制（必读）：** 技术信号（MA20乖离、RS5、量比）可全量历史回测。宏观代理（VIX、DXY）可部分回测。watchlist_score 不可回测（需实时分析师数据）。结论明确标注"仅适用于技术信号"。

---

## File Map

| 状态 | 路径 | 职责 |
|------|------|------|
| 新建 | `agents/backtest_engine.py` | 数据获取、信号计算、参数扫描、框架模拟 |
| 修改 | `agents/harvest_agent.py` | 追加 `has_catalyst` 字段到 outcomes |
| 新建 | `tests/test_backtest_engine.py` | 单元测试 |
| 运行时生成 | `findings/signal_thresholds_optimized.json` | 信号扫描最优阈值 |
| 运行时生成 | `findings/backtest_results_{date}.json` | 框架模拟结果 |

---

## Task 1: 数据获取 + 信号计算工具函数

**Files:**
- Create: `agents/backtest_engine.py`
- Create: `tests/test_backtest_engine.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_backtest_engine.py
import sys, os
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


def _make_ohlcv(n=300, start_price=100.0, trend=0.0002):
    """生成模拟日线 OHLCV 数据"""
    import numpy as np
    np.random.seed(42)
    closes = [start_price]
    for i in range(n - 1):
        closes.append(closes[-1] * (1 + trend + np.random.normal(0, 0.015)))
    closes = [round(c, 2) for c in closes]
    return pd.DataFrame({
        "Open":   [c * 0.995 for c in closes],
        "High":   [c * 1.015 for c in closes],
        "Low":    [c * 0.985 for c in closes],
        "Close":  closes,
        "Volume": [1_000_000 + int(np.random.normal(0, 200_000)) for _ in closes],
    })


def test_compute_daily_signals_has_required_columns():
    """_compute_daily_signals 返回含 ma20_dev / rs5 / vol_ratio 的 DataFrame"""
    from agents.backtest_engine import _compute_daily_signals
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start_price=400.0)
    result = _compute_daily_signals(sym_df, spy_df)
    assert "ma20_dev"  in result.columns
    assert "rs5"       in result.columns
    assert "vol_ratio" in result.columns
    assert len(result) == len(sym_df)


def test_compute_daily_signals_ma20_dev_correct():
    """MA20乖离率计算正确：(close - MA20) / MA20"""
    from agents.backtest_engine import _compute_daily_signals
    # 构造 close 全为 100，MA20=100 → dev=0
    df = pd.DataFrame({
        "Close":  [100.0] * 250,
        "High":   [101.0] * 250,
        "Low":    [99.0]  * 250,
        "Open":   [100.0] * 250,
        "Volume": [1_000_000] * 250,
    })
    spy_df = _make_ohlcv(250, start_price=400.0)
    result = _compute_daily_signals(df, spy_df)
    # 第20行之后 ma20_dev 应接近0
    assert abs(result["ma20_dev"].iloc[30]) < 0.001


def test_forward_return_5d():
    """_add_forward_returns 添加 5日后涨跌幅列"""
    from agents.backtest_engine import _add_forward_returns
    df = pd.DataFrame({"Close": [100, 102, 104, 103, 105, 107, 106, 108, 110, 112]})
    result = _add_forward_returns(df, days=5)
    assert "fwd_5d" in result.columns
    # 第0行 5日后是第5行(107)：(107-100)/100 = 7%
    assert abs(result["fwd_5d"].iloc[0] - 0.07) < 0.001
    # 最后5行 fwd_5d 应为 NaN
    assert pd.isna(result["fwd_5d"].iloc[-1])
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_engine.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 agents/backtest_engine.py（工具函数层）**

```python
"""
backtest_engine.py — 历史信号参数扫描 + 框架模拟

用法:
    python3.12 agents/backtest_engine.py scan MRVL RKLB   # 信号扫描
    python3.12 agents/backtest_engine.py simulate MRVL    # 框架模拟
    python3.12 agents/backtest_engine.py update           # 用扫描结果更新阈值配置

范围限制:
    回测仅覆盖可从历史 OHLCV + 宏观代理数据重建的信号:
    - 技术信号: MA20乖离、RS5日超额、量比
    - 宏观代理: VIX（macro_score 代理）、DXY
    watchlist_score 和 analyst_target 不可历史回测（需实时数据）。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

_BASE          = os.path.expanduser("~/stock_team")
_FINDINGS      = os.path.join(_BASE, "findings")
_THRESHOLDS    = os.path.join(_BASE, "config", "decision_thresholds.json")
_OPT_OUT       = os.path.join(_FINDINGS, "signal_thresholds_optimized.json")
_MIN_SAMPLES   = 20    # 阈值候选需有至少这么多样本才被考虑
_UPDATE_MIN_PP = 0.05  # 只有胜率提升超过5pp才写入配置


def _fetch_ohlcv(sym: str, years: int = 2) -> pd.DataFrame:
    """获取标的历史日线 OHLCV，失败时返回空 DataFrame"""
    try:
        period = f"{years * 365 + 60}d"
        df = yf.Ticker(sym).history(period=period)
        if df.empty:
            return pd.DataFrame()
        return df[["Open", "High", "Low", "Close", "Volume"]].copy()
    except Exception:
        return pd.DataFrame()


def _fetch_spy(years: int = 2) -> pd.DataFrame:
    """获取 SPY 历史日线，用于计算 RS5"""
    return _fetch_ohlcv("SPY", years=years)


def _compute_daily_signals(sym_df: pd.DataFrame, spy_df: pd.DataFrame) -> pd.DataFrame:
    """
    对日线数据逐行计算技术信号，返回含信号列的 DataFrame。

    新增列:
      ma20_dev   — (close - MA20) / MA20，正=高于均线
      rs5        — 标的5日收益率 - SPY5日收益率（%）
      vol_ratio  — 当日量 / 前20日均量
    """
    df = sym_df.copy()
    close = df["Close"]

    # MA20 乖离率
    ma20 = close.rolling(20).mean()
    df["ma20_dev"] = ((close - ma20) / ma20).round(4)

    # RS5 超额
    sym_ret5  = close.pct_change(5)
    spy_close = spy_df["Close"].reindex(df.index, method="ffill")
    spy_ret5  = spy_close.pct_change(5)
    df["rs5"] = ((sym_ret5 - spy_ret5) * 100).round(3)

    # 量比（当日量 / 前20日均量）
    vol_ma20      = df["Volume"].rolling(20).mean().shift(1)
    df["vol_ratio"] = (df["Volume"] / vol_ma20).round(3)

    return df


def _add_forward_returns(df: pd.DataFrame, days: int = 5) -> pd.DataFrame:
    """追加 fwd_{days}d 列：days 日后的涨跌幅（用于胜率计算）"""
    df = df.copy()
    df[f"fwd_{days}d"] = df["Close"].shift(-days) / df["Close"] - 1
    return df
```

- [ ] **Step 4: 跑 3 个测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_engine.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/backtest_engine.py tests/test_backtest_engine.py
git commit -m "feat(backtest): add data fetch + signal computation utilities"
```

---

## Task 2: _scan_signal() + run_signal_scan()

**Files:**
- Modify: `agents/backtest_engine.py`
- Modify: `tests/test_backtest_engine.py`

- [ ] **Step 1: 追加失败测试**

```python
# 追加到 tests/test_backtest_engine.py

def test_scan_signal_returns_scan_result():
    """_scan_signal 对 ma20_dev 扫描，返回含 optimal / win_rate / n_samples 的 dict"""
    from agents.backtest_engine import _scan_signal
    # 构造：ma20_dev < 0.03 时 5日后上涨；否则下跌
    n = 100
    ma20_devs = [0.02] * 50 + [0.08] * 50
    fwd_5d    = [0.02] * 50 + [-0.01] * 50   # 前50个看涨，后50个看跌
    df = pd.DataFrame({"ma20_dev": ma20_devs, "fwd_5d": fwd_5d})

    result = _scan_signal(
        df, signal_col="ma20_dev", thresholds=[0.01, 0.03, 0.05, 0.10],
        direction="below",   # signal <= threshold 时触发
        fwd_col="fwd_5d",
    )
    assert "optimal" in result
    assert "win_rate" in result
    assert "scan" in result          # 完整扫描表
    # 在这个数据集里，threshold=0.03 捕获前50行（全涨），win_rate=1.0
    assert result["optimal"] == 0.03


def test_run_signal_scan_structure():
    """run_signal_scan 对单个标的返回含全部信号键的 dict"""
    from agents.backtest_engine import run_signal_scan
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start_price=400.0)

    with patch("agents.backtest_engine._fetch_ohlcv") as mock_ohlcv, \
         patch("agents.backtest_engine._fetch_spy") as mock_spy:
        mock_ohlcv.return_value = sym_df
        mock_spy.return_value   = spy_df
        result = run_signal_scan("MRVL", years=1)

    assert "ma20_dev_max"  in result   # 软否决：MA20乖离上限
    assert "rs5_min"       in result   # 软否决：RS5下限
    assert "vol_ratio_max" in result   # 量比阈值
    for key in result:
        assert "optimal" in result[key]
        assert "win_rate" in result[key]
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_engine.py::test_scan_signal_returns_scan_result -v 2>&1 | head -10
```

- [ ] **Step 3: 实现 _scan_signal() + run_signal_scan()**

追加到 `agents/backtest_engine.py`：

```python
def _scan_signal(df: pd.DataFrame, signal_col: str,
                 thresholds: list, direction: str,
                 fwd_col: str = "fwd_5d",
                 min_samples: int = _MIN_SAMPLES) -> dict:
    """
    单信号参数扫描。

    direction="below": 信号 <= threshold 时视为"触发入场条件"
    direction="above": 信号 >= threshold 时视为"触发入场条件"

    返回:
      {optimal, win_rate, n_samples, mean_ret, scan: [{threshold, win_rate, n, mean_ret}]}
    """
    rows = df[[signal_col, fwd_col]].dropna()
    if len(rows) < min_samples:
        return {"optimal": None, "win_rate": None, "n_samples": 0, "mean_ret": None, "scan": []}

    scan = []
    for thr in thresholds:
        if direction == "below":
            mask = rows[signal_col] <= thr
        else:
            mask = rows[signal_col] >= thr
        subset = rows[mask]
        n = len(subset)
        if n < min_samples:
            scan.append({"threshold": thr, "win_rate": None, "n": n, "mean_ret": None})
            continue
        win_rate = float((subset[fwd_col] > 0).mean())
        mean_ret = float(subset[fwd_col].mean())
        scan.append({"threshold": thr, "win_rate": round(win_rate, 4),
                     "n": n, "mean_ret": round(mean_ret, 4)})

    valid = [s for s in scan if s["win_rate"] is not None]
    if not valid:
        return {"optimal": None, "win_rate": None, "n_samples": 0, "mean_ret": None, "scan": scan}

    best = max(valid, key=lambda s: s["win_rate"])
    return {
        "optimal":   best["threshold"],
        "win_rate":  best["win_rate"],
        "n_samples": best["n"],
        "mean_ret":  best["mean_ret"],
        "scan":      scan,
    }


def run_signal_scan(sym: str, years: int = 2) -> dict:
    """
    对单只标的运行所有可回测信号的参数扫描。
    返回 {signal_key: {optimal, win_rate, n_samples, mean_ret, scan}}。

    注: watchlist_score 不可历史回测（需实时分析师数据），已排除。
    """
    sym_df = _fetch_ohlcv(sym, years=years)
    spy_df = _fetch_spy(years=years)
    if sym_df.empty or spy_df.empty:
        return {}

    df = _compute_daily_signals(sym_df, spy_df)
    df = _add_forward_returns(df, days=5)
    df = df.dropna(subset=["ma20_dev", "rs5", "vol_ratio"])

    results = {}

    # MA20乖离上限（软否决）：低乖离率时入场更好
    results["ma20_dev_max"] = _scan_signal(
        df, "ma20_dev",
        thresholds=[0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10],
        direction="below",
    )

    # RS5日超额下限（软否决）：相对强势时入场更好
    results["rs5_min"] = _scan_signal(
        df, "rs5",
        thresholds=[-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0],
        direction="above",
    )

    # 量比（缩量入场）：量比小时入场更好
    results["vol_ratio_max"] = _scan_signal(
        df, "vol_ratio",
        thresholds=[0.6, 0.7, 0.8, 0.9, 1.0, 1.2],
        direction="below",
    )

    return results
```

- [ ] **Step 4: 跑所有 5 个测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_engine.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/backtest_engine.py tests/test_backtest_engine.py
git commit -m "feat(backtest): add _scan_signal() + run_signal_scan() - parameter sweep"
```

---

## Task 3: run_portfolio_scan() + simulate_decision_framework() + CLI

**Files:**
- Modify: `agents/backtest_engine.py`
- Modify: `tests/test_backtest_engine.py`

- [ ] **Step 1: 追加失败测试**

```python
# 追加到 tests/test_backtest_engine.py

def test_run_portfolio_scan_aggregates_symbols():
    """run_portfolio_scan 对多个标的聚合结果，返回统一最优阈值"""
    from agents.backtest_engine import run_portfolio_scan
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start_price=400.0)

    with patch("agents.backtest_engine._fetch_ohlcv") as mock_ohlcv, \
         patch("agents.backtest_engine._fetch_spy") as mock_spy:
        mock_ohlcv.return_value = sym_df
        mock_spy.return_value   = spy_df
        result = run_portfolio_scan(["MRVL", "RKLB"], years=1)

    assert "ma20_dev_max"  in result
    assert "rs5_min"       in result
    # 必须有 symbols_scanned 记录
    assert "symbols_scanned" in result
    assert len(result["symbols_scanned"]) == 2


def test_simulate_decision_framework_returns_summary():
    """simulate_decision_framework 只使用 soft_vetoes 中的技术信号（hard_vetoes 不可历史重建）"""
    from agents.backtest_engine import simulate_decision_framework
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start_price=400.0)
    # 只传 soft_vetoes：simulate 只读 ma20_dev_max / rs5_min
    # hard_vetoes 不传，因为 RR/watchlist_score 不可历史重建
    thresholds = {
        "soft_vetoes": {"ma20_dev_max": 0.05, "rs5_min": 0.0, "max_headwinds": 2},
    }
    with patch("agents.backtest_engine._fetch_ohlcv") as mock_ohlcv, \
         patch("agents.backtest_engine._fetch_spy") as mock_spy:
        mock_ohlcv.return_value = sym_df
        mock_spy.return_value   = spy_df
        result = simulate_decision_framework(["MRVL"], thresholds, years=1,
                                              write_output=False)

    assert "win_rate"     in result
    assert "n_entries"    in result
    assert "mean_ret_pct" in result
    assert "note"         in result
    # note 必须声明不使用 hard_vetoes
    assert "hard" not in result.get("thresholds_used", {})
    assert result["n_entries"] > 0  # 有效模拟产生了入场记录
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_engine.py::test_run_portfolio_scan_aggregates_symbols -v 2>&1 | head -10
```

- [ ] **Step 3: 实现 run_portfolio_scan() + simulate_decision_framework() + main()**

追加到 `agents/backtest_engine.py`：

```python
def run_portfolio_scan(symbols: list, years: int = 2,
                       write_output: bool = True) -> dict:
    """
    对标的列表运行信号扫描，聚合得到统一最优阈值。
    统一阈值的统计力量更大（更多样本）。

    write_output=True 时写入 findings/signal_thresholds_optimized.json。
    返回聚合结果 dict，含 symbols_scanned 和各信号最优阈值。
    """
    all_results = {}
    scanned = []

    spy_df = _fetch_spy(years=years)
    if spy_df.empty:
        return {"error": "SPY 数据获取失败", "symbols_scanned": []}

    for sym in symbols:
        sym_df = _fetch_ohlcv(sym, years=years)
        if sym_df.empty:
            continue
        df = _compute_daily_signals(sym_df, spy_df)
        df = _add_forward_returns(df, days=5)
        df = df.dropna(subset=["ma20_dev", "rs5", "vol_ratio"])
        all_results[sym] = df
        scanned.append(sym)

    if not all_results:
        return {"error": "无有效数据", "symbols_scanned": []}

    # 合并所有标的的信号数据
    combined = pd.concat(all_results.values(), ignore_index=True)

    ma20_scan = _scan_signal(combined, "ma20_dev",
                             [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10],
                             direction="below")
    rs5_scan  = _scan_signal(combined, "rs5",
                             [-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0],
                             direction="above")
    vol_scan  = _scan_signal(combined, "vol_ratio",
                             [0.6, 0.7, 0.8, 0.9, 1.0, 1.2],
                             direction="below")

    output = {
        "scan_date":       datetime.now().strftime("%Y-%m-%d"),
        "symbols_scanned": scanned,
        "n_total_samples": len(combined),
        "ma20_dev_max":    ma20_scan,
        "rs5_min":         rs5_scan,
        "vol_ratio_max":   vol_scan,
        "_note": (
            "watchlist_score 不可历史回测（需实时分析师数据）。"
            "macro_score、RR 的历史阈值建议从 observation_outcomes.jsonl 的实盘数据验证。"
        ),
    }

    if write_output:
        os.makedirs(_FINDINGS, exist_ok=True)
        with open(_OPT_OUT, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"信号扫描结果写入 {_OPT_OUT}")

    return output


def _try_update_thresholds(scan_result: dict) -> bool:
    """
    若扫描结果胜率超过基线（0.5）+5pp（即 win_rate >= 0.55），
    更新 decision_thresholds.json。返回 True 表示有更新。

    更新规则：
    - 基线 = 0.5（随机猜测的期望胜率）
    - 5pp 改善门槛 = _UPDATE_MIN_PP = 0.05
    - 条件：new_win_rate >= 0.5 + _UPDATE_MIN_PP = 0.55
    - 首次扫描（无历史基线）也适用同一规则
    """
    if not os.path.exists(_THRESHOLDS):
        return False

    with open(_THRESHOLDS, encoding="utf-8") as f:
        current = json.load(f)

    updated = False
    baseline = 0.5 + _UPDATE_MIN_PP   # = 0.55

    # MA20乖离上限
    ma20 = scan_result.get("ma20_dev_max", {})
    if ma20.get("optimal") is not None and (ma20.get("win_rate") or 0) >= baseline:
        current.setdefault("soft_vetoes", {})["ma20_dev_max"] = ma20["optimal"]
        updated = True

    # RS5下限
    rs5 = scan_result.get("rs5_min", {})
    if rs5.get("optimal") is not None and (rs5.get("win_rate") or 0) >= baseline:
        current.setdefault("soft_vetoes", {})["rs5_min"] = rs5["optimal"]
        updated = True

    if updated:
        current["_updated"] = datetime.now().strftime("%Y-%m-%d")
        current["_update_source"] = "backtest_engine"
        current["_update_baseline"] = baseline
        with open(_THRESHOLDS, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)

    return updated


def simulate_decision_framework(symbols: list, thresholds: dict,
                                 years: int = 2,
                                 write_output: bool = True) -> dict:
    """
    简化框架历史回测：用可回测的技术信号模拟"可入场"决策，
    统计实际 5日后收益率。

    使用的信号（可历史重建）：
      - MA20乖离 ≤ ma20_dev_max（软否决1，不触发才入场）
      - RS5 ≥ rs5_min（软否决2，不触发才入场）
      决策：软否决 ≤ 1 → 模拟入场

    不可重建的信号（不纳入）：
      - RR比（需历史止损价，过于复杂）
      - watchlist_score（需实时分析师数据）
      - thesis_status（主观判断）
    """
    sv          = thresholds.get("soft_vetoes", {})
    ma20_max    = sv.get("ma20_dev_max", 0.05)
    rs5_min     = sv.get("rs5_min", 0.0)

    spy_df = _fetch_spy(years=years)
    all_rows = []

    for sym in symbols:
        sym_df = _fetch_ohlcv(sym, years=years)
        if sym_df.empty or spy_df.empty:
            continue
        df = _compute_daily_signals(sym_df, spy_df)
        df = _add_forward_returns(df, days=5)
        df["sym"] = sym
        all_rows.append(df)

    if not all_rows:
        return {"error": "无有效数据", "n_entries": 0, "win_rate": None}

    combined = pd.concat(all_rows)
    combined = combined.dropna(subset=["ma20_dev", "rs5", "fwd_5d"])

    # 软否决计数（仅计算可回测的两条）
    combined["soft_veto_count"] = (
        (combined["ma20_dev"] > ma20_max).astype(int) +
        (combined["rs5"] < rs5_min).astype(int)
    )

    # 模拟入场：软否决 ≤ 1
    entries = combined[combined["soft_veto_count"] <= 1]
    n       = len(entries)

    if n == 0:
        summary = {"win_rate": None, "n_entries": 0, "mean_ret_pct": None}
    else:
        win_rate = float((entries["fwd_5d"] > 0).mean())
        mean_ret = float(entries["fwd_5d"].mean() * 100)
        summary  = {
            "win_rate":    round(win_rate, 4),
            "n_entries":   n,
            "mean_ret_pct": round(mean_ret, 2),
        }

    output = {
        **summary,
        "symbols": symbols,
        "years":   years,
        "thresholds_used": {"ma20_dev_max": ma20_max, "rs5_min": rs5_min},
        "note": (
            "简化框架回测：仅使用 MA20乖离 + RS5 两条软否决（可历史重建）。"
            "硬否决（RR/宏观/watchlist_score）因需实时数据未纳入。"
            "结论仅适用于技术信号维度。"
        ),
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
    }

    if write_output:
        os.makedirs(_FINDINGS, exist_ok=True)
        out_path = os.path.join(_FINDINGS,
                                f"backtest_results_{datetime.now().strftime('%Y-%m-%d')}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"框架回测结果写入 {out_path}")

    return output


def main():
    import argparse, json as _json

    parser = argparse.ArgumentParser(description="历史信号回测引擎")
    sub    = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="运行信号参数扫描")
    p_scan.add_argument("symbols", nargs="+")
    p_scan.add_argument("--years", type=int, default=2)

    p_sim = sub.add_parser("simulate", help="运行框架简化回测")
    p_sim.add_argument("symbols", nargs="+")
    p_sim.add_argument("--years", type=int, default=2)

    p_upd = sub.add_parser("update", help="将扫描结果写入 decision_thresholds.json")

    args = parser.parse_args()

    cfg_path = os.path.join(_BASE, "config", "poll_config.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg      = json.load(f)
    watchlist = cfg.get("watchlist", [])[:20]   # 最多20只

    if args.cmd == "scan":
        result = run_portfolio_scan(args.symbols or watchlist, years=args.years)
        print(f"扫描完成: {result['symbols_scanned']}")
        for k in ["ma20_dev_max", "rs5_min", "vol_ratio_max"]:
            r = result.get(k, {})
            print(f"  {k}: optimal={r.get('optimal')}, win_rate={r.get('win_rate')}, n={r.get('n_samples')}")

    elif args.cmd == "simulate":
        with open(_THRESHOLDS, encoding="utf-8") as f:
            thresholds = json.load(f)
        result = simulate_decision_framework(args.symbols or watchlist, thresholds, years=args.years)
        print(f"框架回测: {result.get('n_entries')}次入场, 胜率={result.get('win_rate')}, 均收益={result.get('mean_ret_pct')}%")

    elif args.cmd == "update":
        if not os.path.exists(_OPT_OUT):
            print("请先运行 scan 命令生成扫描结果")
            return
        with open(_OPT_OUT, encoding="utf-8") as f:
            scan = json.load(f)
        updated = _try_update_thresholds(scan)
        print("✅ 阈值已更新" if updated else "ℹ️ 无需更新（改善幅度未超过阈值）")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑所有 7 个测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_engine.py -v
```
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
cd ~/stock_team
git add agents/backtest_engine.py tests/test_backtest_engine.py
git commit -m "feat(backtest): add run_portfolio_scan, simulate_decision_framework, CLI"
```

---

## Task 4: harvest_agent.py — 追加 has_catalyst 字段

**Files:**
- Modify: `agents/harvest_agent.py`
- Create: `tests/test_harvest_has_catalyst.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_harvest_has_catalyst.py
import sys, os, json, tempfile
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch, MagicMock
import pandas as pd


def _fake_obs_record(catalyst_strength=0):
    return {
        "date": "2026-05-19", "time": "10:00", "session": "morning",
        "sym": "LITE", "is_position": True, "price": 870.0,
        "rsi3": 45, "macd": 0.5, "rs_pct": 2.3,
        "gate_pass": True, "gate_block": "",
        "gate_detail": {}, "key_obs": "", "key_levels": {},
        "spy_chg": 0.005, "qqq5m": 0.003, "vix": 18.5,
        "vix_dir": "下降", "macro": "normal",
        "catalyst_strength": catalyst_strength,
        "vol_ratio": 0.75,
    }


def test_outcome_has_catalyst_true_when_strength_positive(tmp_path, monkeypatch):
    """catalyst_strength > 0 时 has_catalyst=True"""
    import agents.harvest_agent as ha
    monkeypatch.setattr(ha, "OBS_LOG",  str(tmp_path / "obs.jsonl"))
    monkeypatch.setattr(ha, "OBS_OUT",  str(tmp_path / "outcomes.jsonl"))

    # 写一条有催化剂的观察记录
    obs = _fake_obs_record(catalyst_strength=3)
    with open(ha.OBS_LOG, "w") as f:
        f.write(json.dumps(obs) + "\n")

    # mock yfinance 返回价格数据
    fake_hist = pd.DataFrame({
        "Open":  [868.0, 875.0],
        "High":  [880.0, 882.0],
        "Low":   [860.0, 865.0],
        "Close": [870.0, 878.0],
    })
    with patch("yfinance.Ticker") as MockTicker:
        m = MagicMock()
        m.history.return_value = fake_hist
        MockTicker.return_value = m
        ha.process_observation_log()

    outcomes = [json.loads(l) for l in open(ha.OBS_OUT)]
    assert len(outcomes) == 1
    assert outcomes[0]["has_catalyst"] is True


def test_outcome_has_catalyst_false_when_strength_zero(tmp_path, monkeypatch):
    """catalyst_strength == 0 时 has_catalyst=False"""
    import agents.harvest_agent as ha
    monkeypatch.setattr(ha, "OBS_LOG",  str(tmp_path / "obs.jsonl"))
    monkeypatch.setattr(ha, "OBS_OUT",  str(tmp_path / "outcomes.jsonl"))

    obs = _fake_obs_record(catalyst_strength=0)
    with open(ha.OBS_LOG, "w") as f:
        f.write(json.dumps(obs) + "\n")

    fake_hist = pd.DataFrame({
        "Open":  [868.0, 875.0], "High":  [880.0, 882.0],
        "Low":   [860.0, 865.0], "Close": [870.0, 878.0],
    })
    with patch("yfinance.Ticker") as MockTicker:
        m = MagicMock()
        m.history.return_value = fake_hist
        MockTicker.return_value = m
        ha.process_observation_log()

    outcomes = [json.loads(l) for l in open(ha.OBS_OUT)]
    assert len(outcomes) == 1
    assert outcomes[0]["has_catalyst"] is False
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_harvest_has_catalyst.py -v 2>&1 | head -15
```
Expected: `KeyError` 或 `AssertionError`（has_catalyst 字段不存在时测试失败）

- [ ] **Step 3: 修改 harvest_agent.py**

在 `process_observation_log()` 函数的 `outcomes.append({...})` 块中，追加 `has_catalyst` 字段。

找到这个位置（大约在第173-189行）：

```python
                outcomes.append({
                    "date": today, "obs_time": r.get("time"), ...
                    "rsi3_at_obs": r.get("rsi3"), "macd_at_obs": r.get("macd"),
                    "rs_at_obs": r.get("rs_pct"),
                })
```

在 `"rs_at_obs"` 那行之后，`})` 之前追加：

```python
                    "has_catalyst": bool((r.get("catalyst_strength") or 0) > 0),
```

- [ ] **Step 4: 跑测试**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_harvest_has_catalyst.py -v
```
Expected: 2 passed

- [ ] **Step 5: 确认现有 harvest 测试没有回归**

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/ -q --tb=no 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
cd ~/stock_team
git add agents/harvest_agent.py tests/test_harvest_has_catalyst.py
git commit -m "feat(harvest): add has_catalyst field to observation_outcomes - enables Track C"
```

---

## Task 5: CHANGELOG 更新

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: 在 CHANGELOG.md 顶部追加**

```
## 2026-05-19 历史回测引擎（backtest_engine.py）

### 新建文件

- **新建** `agents/backtest_engine.py` — 历史信号参数扫描 + 框架模拟：
  - `_fetch_ohlcv / _fetch_spy / _compute_daily_signals / _add_forward_returns` — 数据获取和信号计算
  - `_scan_signal(df, signal_col, thresholds, direction)` — 单信号参数扫描，输出最优阈值和胜率
  - `run_signal_scan(sym, years=2)` — 对单标的扫描 MA20乖离/RS5/量比三个信号
  - `run_portfolio_scan(symbols, years=2)` — 多标的聚合扫描，写入 `findings/signal_thresholds_optimized.json`
  - `simulate_decision_framework(symbols, thresholds, years=2)` — 简化框架模拟（使用可历史重建的信号），写入 `findings/backtest_results_{date}.json`
  - `_try_update_thresholds(scan_result)` — 扫描结果改善>5pp时更新 decision_thresholds.json
  - CLI: scan / simulate / update 三个子命令
- **明确局限**: watchlist_score / analyst_target 不可历史回测，结论仅适用于技术+宏观代理信号

### 修改文件

- **修改** `agents/harvest_agent.py` — `process_observation_log()` 追加 `has_catalyst` 字段（`catalyst_strength > 0`），启动 Track C 前向催化剂验证

### 测试

- `tests/test_backtest_engine.py` — 7项
- `tests/test_harvest_has_catalyst.py` — 2项
```

- [ ] **Step 2: Commit**

```bash
cd ~/stock_team
git add CHANGELOG.md
git commit -m "docs: CHANGELOG for backtest engine + harvest has_catalyst"
```

---

## 验收检查（对应 spec Validation）

| 验收点 | 验证命令 | 期望结果 |
|--------|---------|---------|
| V6: run_signal_scan | `python3.12 agents/backtest_engine.py scan MRVL --years 2` | 输出 ma20_dev_max/rs5_min/vol_ratio_max 最优阈值 |
| V7: simulate_framework | `python3.12 agents/backtest_engine.py simulate MRVL RKLB`（前提：`config/decision_thresholds.json` 存在）| 输出 n_entries/win_rate/mean_ret_pct |
| V8: has_catalyst | `pytest tests/test_harvest_has_catalyst.py -v` | 2 passed |
