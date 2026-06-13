# 回测系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建三层回测系统（宏观策略/微观结构位/盘中信号），6指标体系，55只标的宇宙，人工确认门控，替换旧的 backtest_engine 流程。

**Architecture:** 共享数据层（复用 backtest_engine._fetch_ohlcv）+ 独立的 backtest_macro.py / backtest_micro.py + 统一入口 backtest_runner.py。每个脚本独立可运行，runner 串行调用三者，生成对比报告后由用户手动执行 --apply 写回参数文件。

**Tech Stack:** Python 3.12, yfinance, pandas, numpy, unittest.mock（测试），json

**Spec:** `docs/superpowers/specs/2026-05-21-backtest-system-design.md`

---

## 文件结构

| 操作 | 路径 | 职责 |
|------|------|------|
| 创建 | `agents/backtest_macro.py` | 宏观策略回测：VIX/SPY/场景 × 5年日线 |
| 创建 | `agents/backtest_micro.py` | 微观结构位（5年）+ 盘中信号（60天）|
| 创建 | `agents/backtest_runner.py` | 统一入口，串行调用，生成报告，--apply 写回 |
| 创建 | `tests/test_backtest_macro.py` | 宏观回测单元测试 |
| 创建 | `tests/test_backtest_micro.py` | 微观回测单元测试 |
| 修改 | `~/.claude/skills/stock-backtest.md` | 更新触发步骤指向 backtest_runner.py |
| 不动 | `agents/backtest_engine.py` | 保留，_fetch_ohlcv 等基础函数被新脚本复用 |

---

## Task 1: 共享数据与指标工具层（backtest_macro.py 骨架）

**Files:**
- Create: `agents/backtest_macro.py`
- Create: `tests/test_backtest_macro.py`

- [ ] **Step 1: 写数据和指标计算的测试**

```python
# tests/test_backtest_macro.py
import sys, os
sys.path.insert(0, os.path.expanduser("~/stock_team"))
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock


def _make_ohlcv(n=300, start=100.0, vol_scale=1.0):
    """生成模拟日线 OHLCV"""
    np.random.seed(42)
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.012 * vol_scale)))
    closes = [max(1.0, c) for c in closes]
    return pd.DataFrame({
        "Open":   [c * 0.998 for c in closes],
        "High":   [c * 1.015 for c in closes],
        "Low":    [c * 0.985 for c in closes],
        "Close":  closes,
        "Volume": [int(1e7 + np.random.normal(0, 1e6)) for _ in closes],
    })


def test_compute_macro_signals_has_required_columns():
    from agents.backtest_macro import compute_macro_signals
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start=450.0)
    vix_df = _make_ohlcv(300, start=18.0, vol_scale=0.3)
    result = compute_macro_signals(sym_df, spy_df, vix_df)
    required = ["ma20_dev", "ma200_up", "rs5", "vol_ratio",
                "dist_hi52w", "vix_level", "vix_ts"]
    for col in required:
        assert col in result.columns, f"Missing column: {col}"


def test_compute_macro_signals_ma200_up_boolean():
    from agents.backtest_macro import compute_macro_signals
    sym_df = _make_ohlcv(300)
    spy_df = _make_ohlcv(300, start=450.0)
    vix_df = _make_ohlcv(300, start=18.0, vol_scale=0.3)
    result = compute_macro_signals(sym_df, spy_df, vix_df)
    assert result["ma200_up"].dtype == bool


def test_compute_metrics_ev_positive_when_mostly_wins():
    from agents.backtest_macro import compute_metrics
    # 7 wins of +5%, 3 losses of -2%
    returns = [0.05] * 7 + [-0.02] * 3
    metrics = compute_metrics(returns, risk_free_rate=0.045)
    assert metrics["ev"] > 0
    assert metrics["win_rate"] == 0.7
    assert metrics["max_drawdown"] <= 0  # 负数，表示回撤


def test_compute_metrics_returns_all_keys():
    from agents.backtest_macro import compute_metrics
    returns = [0.03, -0.01, 0.02, 0.04, -0.015]
    metrics = compute_metrics(returns, risk_free_rate=0.045)
    required = ["ev", "win_rate", "rr_ratio", "sortino", "max_drawdown",
                "max_single_loss", "n_trades", "alpha_vs_spy"]
    for k in required:
        assert k in metrics, f"Missing metric: {k}"
```

- [ ] **Step 2: 运行确认失败**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_macro.py -v 2>&1 | tail -10
```
Expected: `ModuleNotFoundError: No module named 'agents.backtest_macro'`

- [ ] **Step 3: 实现 compute_macro_signals 和 compute_metrics**

```python
# agents/backtest_macro.py
"""
宏观策略回测 — backtest_macro.py
验证"何时适合进场"的宏观环境参数，5年日线数据。

用法:
  python3.12 agents/backtest_macro.py [--years 5] [--syms NVDA AAPL ...]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date as _date

BASE       = os.path.expanduser("~/stock_team")
CFG_DIR    = os.path.join(BASE, "config")
FIND_DIR   = os.path.join(BASE, "findings")

# 复用 backtest_engine 的 OHLCV 拉取（避免重复）
from agents.backtest_engine import _fetch_ohlcv

RISK_FREE_RATE = 0.045  # 4.5% 近似3月期美债


def _fetch_vix(years: int = 5) -> pd.DataFrame:
    """拉取 ^VIX 和 ^VIX3M 日线"""
    vix  = _fetch_ohlcv("^VIX",  years=years)
    vix3m = _fetch_ohlcv("^VIX3M", years=years)
    if vix.empty:
        return pd.DataFrame()
    df = vix[["Close"]].rename(columns={"Close": "vix"})
    if not vix3m.empty:
        df = df.join(vix3m[["Close"]].rename(columns={"Close": "vix3m"}), how="left")
        df["vix_ts"] = (df["vix"] / df["vix3m"]).round(3)  # VIX 期限结构
    else:
        df["vix3m"] = np.nan
        df["vix_ts"] = np.nan
    df["vix_level"] = df["vix"]
    return df


def compute_macro_signals(sym_df: pd.DataFrame,
                           spy_df: pd.DataFrame,
                           vix_df: pd.DataFrame) -> pd.DataFrame:
    """
    计算宏观策略信号，每日滚动。
    所有指标只用截至 t-1 的数据（防数据泄露）。
    """
    df = sym_df[["Close", "High", "Low", "Volume"]].copy()
    close = df["Close"]

    # MA20 乖离率
    ma20 = close.rolling(20).mean()
    df["ma20_dev"] = ((close - ma20) / ma20).round(4)

    # MA200 趋势方向（向上=True）
    ma200 = close.rolling(200).mean()
    df["ma200_up"] = (ma200.diff(5) > 0).astype(bool)

    # 距52周高点距离
    hi52w = df["High"].rolling(252).max()
    df["dist_hi52w"] = ((close - hi52w) / hi52w).round(4)

    # RS5 日超额收益
    spy_close = spy_df["Close"].reindex(df.index, method="ffill")
    sym_ret5  = close.pct_change(5)
    spy_ret5  = spy_close.pct_change(5)
    df["rs5"] = ((sym_ret5 - spy_ret5) * 100).round(2)

    # 量比（近5日均量 / 近20日均量）
    vol = df["Volume"]
    df["vol_ratio"] = (vol.rolling(5).mean() / vol.rolling(20).mean()).round(3)

    # VIX 信号
    if not vix_df.empty:
        vix_aligned = vix_df.reindex(df.index, method="ffill")
        df["vix_level"] = vix_aligned.get("vix_level", np.nan)
        df["vix_ts"]    = vix_aligned.get("vix_ts", np.nan)
    else:
        df["vix_level"] = np.nan
        df["vix_ts"]    = np.nan

    return df.dropna(subset=["ma20_dev", "rs5", "vol_ratio"])


def compute_metrics(returns: list, risk_free_rate: float = RISK_FREE_RATE,
                    spy_ann_return: float = 0.12) -> dict:
    """
    计算6个回测指标。
    returns: 每笔交易的收益率列表（小数，如0.05表示+5%）
    spy_ann_return: SPY 同期年化收益（用于 Alpha 计算）
    """
    if not returns:
        return {k: None for k in ["ev", "win_rate", "rr_ratio", "sortino",
                                   "max_drawdown", "max_single_loss",
                                   "n_trades", "alpha_vs_spy"]}
    arr = np.array(returns)
    n   = len(arr)

    wins   = arr[arr > 0]
    losses = arr[arr < 0]

    win_rate  = len(wins) / n
    avg_win   = float(wins.mean())  if len(wins)  > 0 else 0.0
    avg_loss  = float(losses.mean()) if len(losses) > 0 else 0.0
    ev        = win_rate * avg_win + (1 - win_rate) * avg_loss

    rr_ratio  = (abs(avg_win) / abs(avg_loss)) if avg_loss != 0 else 0.0

    # Sortino: 年化收益率（假设每笔约5日，252/5≈50笔/年）
    ann_factor   = min(n, 50)  # 简化年化
    ann_return   = (1 + ev) ** ann_factor - 1
    down_dev     = float(arr[arr < 0].std()) if len(losses) > 1 else 0.001
    ann_down_dev = down_dev * np.sqrt(ann_factor)
    sortino      = (ann_return - risk_free_rate) / ann_down_dev if ann_down_dev > 0 else 0.0

    # 最大回撤（基于累积净值曲线）
    cumulative = np.cumprod(1 + arr)
    peak       = np.maximum.accumulate(cumulative)
    drawdowns  = (cumulative - peak) / peak
    max_dd     = float(drawdowns.min())

    # 最大单笔亏损 / 平均盈利
    max_single_loss = float(losses.min()) if len(losses) > 0 else 0.0

    # Alpha vs SPY
    alpha_vs_spy = ann_return - spy_ann_return

    return {
        "ev":              round(ev, 4),
        "win_rate":        round(win_rate, 4),
        "rr_ratio":        round(rr_ratio, 2),
        "sortino":         round(sortino, 3),
        "max_drawdown":    round(max_dd, 4),
        "max_single_loss": round(max_single_loss, 4),
        "n_trades":        n,
        "alpha_vs_spy":    round(alpha_vs_spy, 4),
    }
```

- [ ] **Step 4: 运行测试确认通过**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_macro.py -v 2>&1 | tail -10
```
Expected: `4 passed`

- [ ] **Step 5: Commit**
```bash
cd ~/stock_team && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git add agents/backtest_macro.py tests/test_backtest_macro.py && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git commit -m "feat(backtest): macro backtest data layer + metrics"
```

---

## Task 2: 宏观策略参数扫描逻辑

**Files:**
- Modify: `agents/backtest_macro.py`（添加 scan_macro_params + simulate_macro）
- Modify: `tests/test_backtest_macro.py`

- [ ] **Step 1: 写扫描逻辑测试**

```python
# 追加到 tests/test_backtest_macro.py

def _make_macro_df():
    """生成带所有宏观信号列的测试 DataFrame"""
    n = 300
    np.random.seed(42)
    dates = pd.date_range("2021-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "ma20_dev":  np.random.normal(0.02, 0.03, n),
        "ma200_up":  np.random.choice([True, False], n),
        "rs5":       np.random.normal(0.5, 2.0, n),
        "vol_ratio": np.random.uniform(0.5, 1.5, n),
        "dist_hi52w": np.random.uniform(-0.5, 0.05, n),
        "vix_level": np.random.uniform(15, 30, n),
        "vix_ts":    np.random.uniform(0.85, 1.2, n),
        "fwd_10d":   np.random.normal(0.01, 0.04, n),
        "Close":     np.cumsum(np.random.normal(0, 1, n)) + 200,
    }, index=dates)


def test_apply_macro_filter_reduces_rows():
    from agents.backtest_macro import apply_macro_filter
    df = _make_macro_df()
    params = {"vix_panic_threshold": 25, "ma20_dev_veto_pct": 8.0,
              "ma200_filter": True}
    filtered = apply_macro_filter(df, params)
    assert len(filtered) < len(df)


def test_scan_macro_params_returns_results():
    from agents.backtest_macro import scan_macro_params
    df = _make_macro_df()
    param_grid = {
        "vix_panic_threshold": [22, 25, 28],
        "ma20_dev_veto_pct":   [6.0, 8.0, 10.0],
    }
    results = scan_macro_params(df, param_grid)
    assert len(results) == 9  # 3 × 3
    assert all("ev" in r["metrics"] for r in results)
    assert all("params" in r for r in results)
```

- [ ] **Step 2: 运行确认失败**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_macro.py -k "filter or scan_macro" -v 2>&1 | tail -10
```

- [ ] **Step 3: 实现 apply_macro_filter 和 scan_macro_params**

```python
# 追加到 agents/backtest_macro.py

def apply_macro_filter(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    应用宏观策略过滤条件，返回"允许进场的日期"子集。
    params 对应 config/macro_strategy_params.json 的 market_regime 字段。
    """
    mask = pd.Series(True, index=df.index)

    vix_thresh = params.get("vix_panic_threshold", 25)
    if "vix_level" in df.columns:
        mask &= df["vix_level"] < vix_thresh

    ma20_max = params.get("ma20_dev_veto_pct", 10.0) / 100
    if "ma20_dev" in df.columns:
        mask &= df["ma20_dev"] < ma20_max

    if params.get("ma200_filter", True) and "ma200_up" in df.columns:
        mask &= df["ma200_up"]

    vix_ts_thresh = params.get("vix_ts_threshold", 1.1)
    if "vix_ts" in df.columns:
        mask &= (df["vix_ts"].isna() | (df["vix_ts"] < vix_ts_thresh))

    return df[mask]


def scan_macro_params(df: pd.DataFrame, param_grid: dict,
                      forward_col: str = "fwd_10d") -> list:
    """
    网格搜索宏观参数，返回每个参数组合的指标列表。
    param_grid: {param_name: [v1, v2, ...]}
    """
    import itertools
    keys   = list(param_grid.keys())
    values = list(param_grid.values())
    results = []

    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        filtered = apply_macro_filter(df, params)
        if filtered.empty or forward_col not in filtered.columns:
            continue
        rets    = filtered[forward_col].dropna().tolist()
        metrics = compute_metrics(rets)
        results.append({"params": params, "metrics": metrics,
                         "n_filtered": len(filtered)})

    return results
```

- [ ] **Step 4: 运行确认通过**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_macro.py -v 2>&1 | tail -10
```
Expected: `6 passed`

- [ ] **Step 5: 添加完整的 run_macro_backtest 主函数**

```python
# 追加到 agents/backtest_macro.py

MACRO_UNIVERSE = [
    "NVDA","AMD","AVGO","QCOM","MRVL","LITE","INTC","AMAT","KLAC",
    "MSFT","AAPL","GOOGL","META","AMZN","NFLX","CRM","ORCL",
    "NIKE","SBUX","MCD","HD","COST","WMT","TGT",
    "JPM","GS","V","MA","BAC",
    "JNJ","ABBV","UNH","LLY","PFE",
    "CAT","HON","RTX","BA",
    "XOM","CVX","OXY",
    "BABA","BIDU","JD",
    "IAU","GLD","GDX",
    "TSLA","COIN","ROKU","SNOW",
    "QQQ","SPY","TQQQ","SOXX","XLK","XLF",
]

PARAM_GRID = {
    "vix_panic_threshold": [20, 22, 25, 28, 30],
    "ma20_dev_veto_pct":   [5.0, 6.0, 8.0, 10.0, 12.0],
    "vix_ts_threshold":    [0.95, 1.0, 1.05, 1.1, 1.15],
    "qqq5m_veto":          [-1.0, -0.7, -0.5, -0.3],   # QQQ5m 急跌否决阈值
}


def run_macro_backtest(syms: list = None, years: int = 5) -> dict:
    """
    对标的列表运行宏观策略回测，聚合计算，扫描参数网格。
    返回 {best_params, all_results, by_period, current_params}
    """
    syms   = syms or MACRO_UNIVERSE
    spy_df = _fetch_ohlcv("SPY", years=years)
    vix_df = _fetch_vix(years=years)

    all_dfs = []
    print(f"[macro_backtest] 拉取 {len(syms)} 只标的数据...")
    for sym in syms:
        df = _fetch_ohlcv(sym, years=years)
        if df.empty or spy_df.empty:
            continue
        signals = compute_macro_signals(df, spy_df, vix_df)
        # 10日后收益率（近似结构位持有期）
        signals["fwd_10d"] = df["Close"].pct_change(10).shift(-10)
        # 财报黑窗期过滤（简化：用 yfinance calendar，失败时跳过）
        signals = _apply_earnings_blackout(signals, sym)
        signals["sym"] = sym
        all_dfs.append(signals)

    if not all_dfs:
        return {"error": "无有效数据"}

    combined = pd.concat(all_dfs).dropna(subset=["ma20_dev", "rs5", "fwd_10d"])
    print(f"[macro_backtest] 合并样本: {len(combined)} 行，开始扫描 {_grid_size(PARAM_GRID)} 组参数...")

    # 样本外验证：前80%训练，后20%验证（Spec 七章阶段3）
    split_idx = int(len(combined) * 0.8)
    train_df  = combined.iloc[:split_idx]
    val_df    = combined.iloc[split_idx:]

    results = scan_macro_params(train_df, PARAM_GRID, forward_col="fwd_10d")

    # 应用大师约束过滤
    results = [r for r in results if _passes_master_constraints(r["params"], r["metrics"])]

    # 找最优（训练集 EV 最大 且 满足门槛）
    valid = [r for r in results if _passes_thresholds(r["metrics"])]
    best  = max(valid, key=lambda r: r["metrics"]["ev"]) if valid else None

    # 样本外验证（防过拟合警告）
    if best:
        val_f   = apply_macro_filter(val_df, best["params"])
        val_rets = val_f["fwd_10d"].dropna().tolist() if "fwd_10d" in val_f.columns else []
        val_m   = compute_metrics(val_rets)
        train_wr = best["metrics"].get("win_rate", 0)
        val_wr   = val_m.get("win_rate", 0) if val_rets else 0
        if train_wr and val_wr and train_wr - val_wr > 0.15:
            print(f"⚠️ 过拟合警告：训练胜率{train_wr:.1%} vs 验证胜率{val_wr:.1%}，差>15pp")
        best["oos_metrics"] = val_m

    # 分时期 + 分板块分析
    by_period = _analyze_by_period(combined, best["params"] if best else {})
    by_sector = _analyze_by_sector(combined, best["params"] if best else {})

    # 当前参数
    current_params = json.load(open(os.path.join(CFG_DIR, "macro_strategy_params.json")))

    return {
        "best_params":     best,
        "all_results":     results,
        "by_period":       by_period,
        "by_sector":       by_sector,
        "current_params":  current_params,
        "n_samples":       len(combined),
        "n_symbols":       len(all_dfs),
        "run_date":        str(_date.today()),
    }


def _apply_earnings_blackout(df: pd.DataFrame, sym: str,
                              blackout_days: int = 10) -> pd.DataFrame:
    """过滤财报前10个交易日的信号。yfinance 失败时静默跳过。"""
    try:
        cal = yf.Ticker(sym).calendar
        if cal is None or cal.empty:
            return df
        for col in cal.columns:
            dates = pd.to_datetime(cal[col].dropna())
            for earn_date in dates:
                start = earn_date - pd.Timedelta(days=blackout_days * 1.5)
                mask  = (df.index >= start) & (df.index <= earn_date)
                df    = df[~mask]
    except Exception:
        pass
    return df


def _grid_size(grid: dict) -> int:
    n = 1
    for v in grid.values():
        n *= len(v)
    return n


def _passes_master_constraints(params: dict, metrics: dict) -> bool:
    """大师约束：逻辑一致性 + 风险上限检查（Spec 七章阶段1）"""
    if metrics.get("max_drawdown", -1) < -0.25:
        return False  # Marks：最大回撤上限 25%
    # k4 不能高于1（不能高于分析师目标价）
    if params.get("k4", 1.0) > 1.0:
        return False
    # k5 < k6（bull→base 警戒比 base→bear 宽松）；k6 固定为 1.0
    if params.get("k5", 0.5) >= params.get("k6", 1.0):
        return False
    return True


def _passes_thresholds(metrics: dict) -> bool:
    """双重门槛 + Taleb 尾部检验"""
    if metrics.get("win_rate", 0) < 0.55:
        return False
    if metrics.get("rr_ratio", 0) < 1.5:
        return False
    avg_win = metrics.get("ev", 0) / max(metrics.get("win_rate", 0.01), 0.01) if metrics.get("win_rate", 0) > 0 else 0
    max_loss = abs(metrics.get("max_single_loss", 0))
    if avg_win > 0 and max_loss / avg_win > 3.0:
        return False  # Taleb：最大单笔亏损不超过平均盈利3倍
    return True


def _analyze_by_period(df: pd.DataFrame, params: dict) -> dict:
    """分时期分析：4个市场环境"""
    periods = {
        "2021_bull":    ("2021-01-01", "2021-12-31"),
        "2022_bear":    ("2022-01-01", "2022-12-31"),
        "2023_recovery":("2023-01-01", "2023-12-31"),
        "2024_ai_bull": ("2024-01-01", "2024-12-31"),
    }
    result = {}
    for label, (start, end) in periods.items():
        sub = df[(df.index >= start) & (df.index <= end)]
        if sub.empty or not params:
            result[label] = {"n": 0}
            continue
        filtered = apply_macro_filter(sub, params)
        rets = filtered["fwd_10d"].dropna().tolist() if "fwd_10d" in filtered.columns else []
        result[label] = {**compute_metrics(rets), "n": len(filtered)}
    return result


def _analyze_by_sector(df: pd.DataFrame, params: dict) -> dict:
    """分板块分析：高波动 vs 低波动 vs 避险"""
    sector_map = {
        "high_vol":  ["NVDA","AMD","AVGO","MRVL","LITE","TSLA","COIN","TQQQ","QQQ"],
        "low_vol":   ["MSFT","AAPL","GOOGL","META","JNJ","ABBV","JPM","V","WMT","MCD"],
        "defensive": ["IAU","GLD","GDX","XOM","CVX"],
    }
    result = {}
    for label, syms in sector_map.items():
        sub = df[df.get("sym", pd.Series()).isin(syms)] if "sym" in df.columns else df
        if sub.empty or not params:
            result[label] = {"n": 0}
            continue
        filtered = apply_macro_filter(sub, params)
        rets = filtered["fwd_10d"].dropna().tolist() if "fwd_10d" in filtered.columns else []
        result[label] = {**compute_metrics(rets), "n": len(filtered)}
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--syms", nargs="*", default=None)
    args = parser.parse_args()
    out = run_macro_backtest(syms=args.syms, years=args.years)
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("all_results",)}, ensure_ascii=False, indent=2))
```

- [ ] **Step 6: Commit**
```bash
cd ~/stock_team && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git add agents/backtest_macro.py tests/test_backtest_macro.py && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git commit -m "feat(backtest): macro strategy scanner + grid search"
```

---

## Task 3: 微观结构位回测（backtest_micro.py）

**Files:**
- Create: `agents/backtest_micro.py`
- Create: `tests/test_backtest_micro.py`

- [ ] **Step 1: 写结构位回测测试**

```python
# tests/test_backtest_micro.py
import sys, os
sys.path.insert(0, os.path.expanduser("~/stock_team"))
import pandas as pd
import numpy as np


def _make_ohlcv(n=300, start=100.0):
    np.random.seed(42)
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.012)))
    closes = [max(1.0, c) for c in closes]
    return pd.DataFrame({
        "Open":  [c * 0.998 for c in closes],
        "High":  [c * 1.015 for c in closes],
        "Low":   [c * 0.985 for c in closes],
        "Close": closes,
        "Volume":[int(1e7) for _ in closes],
    })


def test_compute_structural_nodes_has_required_columns():
    from agents.backtest_micro import compute_structural_nodes
    df = _make_ohlcv(300)
    params = {"k1": 1.0, "k2": 0.2, "k4": 0.9, "k5": 0.5}
    result = compute_structural_nodes(df, params)
    required = ["add1", "dynamic_stop", "tp1", "scenario_b2b"]
    for col in required:
        assert col in result.columns, f"Missing: {col}"


def test_structural_nodes_stop_below_add1():
    from agents.backtest_micro import compute_structural_nodes
    df = _make_ohlcv(300)
    params = {"k1": 1.0, "k2": 0.2, "k4": 0.9, "k5": 0.5}
    result = compute_structural_nodes(df, params).dropna()
    # 止损必须低于 Add1（k1 > k2 约束）
    assert (result["dynamic_stop"] < result["add1"]).all()


def test_simulate_structural_trades_returns_list():
    from agents.backtest_micro import simulate_structural_trades
    df = _make_ohlcv(300)
    nodes = pd.DataFrame({
        "add1":         [df["Close"].iloc[i] * 0.97 for i in range(300)],
        "dynamic_stop": [df["Close"].iloc[i] * 0.90 for i in range(300)],
        "tp1":          [df["Close"].iloc[i] * 1.08 for i in range(300)],
        "scenario_b2b": [df["Close"].iloc[i] * 0.93 for i in range(300)],
    }, index=df.index)
    trades = simulate_structural_trades(df, nodes, slippage=0.001)
    assert isinstance(trades, list)
    assert all("return" in t and "outcome" in t for t in trades)
```

- [ ] **Step 2: 运行确认失败**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_micro.py -v 2>&1 | tail -10
```

- [ ] **Step 3: 实现结构位计算和模拟**

```python
# agents/backtest_micro.py
"""
微观策略回测 — backtest_micro.py
- 结构位回测（5年日线）：Add1/TP1/DynamicStop 节点模拟
- 盘中信号回测（60天5分钟）：RSI/VWAP/量比 Flex 信号

用法:
  python3.12 agents/backtest_micro.py --structural [--years 5] [--sym NVDA]
  python3.12 agents/backtest_micro.py --intraday [--window-days 60] [--sym NVDA]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date as _date

BASE    = os.path.expanduser("~/stock_team")
CFG_DIR = os.path.join(BASE, "config")

from agents.backtest_engine import _fetch_ohlcv
from agents.backtest_macro  import compute_metrics, _passes_thresholds, _passes_master_constraints

RISK_FREE_RATE = 0.045

# ── 结构位节点计算 ────────────────────────────────────────────────────────────

def compute_structural_nodes(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    每日滚动计算宏观策略节点（Add1/DynamicStop/TP1/情景降级）。
    只使用截至 t-1 的数据（防数据泄露）。
    params: 含 k1/k2/k4/k5 的 dict（对应 macro_strategy evolution 字段）
    """
    k1 = params.get("k1", 1.0)
    k2 = params.get("k2", 0.2)
    k4 = params.get("k4", 0.9)
    k5 = params.get("k5", 0.5)

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    # MA50 / ATR14（滚动，截至前日）
    ma50   = close.rolling(50).mean().shift(1)
    tr     = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr14  = tr.rolling(14).mean().shift(1)

    # 近90日高点（截至前日）
    swing_high_90d = high.rolling(90).max().shift(1)

    # 分析师目标价（从 fundamentals_{sym}.json 读，不可回溯，用固定近似）
    # 简化：TP2 = swing_high × 1.05（保守估计）

    result = df[["Close", "High", "Low", "Volume"]].copy()
    result["add1"]         = (ma50 + k2 * atr14).round(2)
    result["dynamic_stop"] = (ma50 - k1 * atr14).round(2)
    result["tp1"]          = (swing_high_90d * 0.995).round(2)
    result["tp2"]          = (swing_high_90d * 1.05 * k4).round(2)
    result["scenario_b2b"] = (ma50 - k5 * atr14).round(2)  # base→bear 降级线
    result["ma50"]         = ma50

    return result


def simulate_structural_trades(df: pd.DataFrame, nodes: pd.DataFrame,
                                slippage: float = 0.001,
                                max_hold_days: int = 60) -> list:
    """
    5年日线结构位交易模拟。
    入场：当日 Low ≤ add1 → 以 add1 × (1+slippage) 入场
    出场：High ≥ tp1 → 止盈；Low ≤ dynamic_stop → 止损；超过 max_hold_days → 强制出场
    返回每笔交易的 dict 列表
    """
    trades = []
    in_trade = False
    entry_price = 0.0
    entry_date  = None
    entry_stop  = 0.0
    entry_tp1   = 0.0
    hold_days   = 0

    for i in range(len(df)):
        row  = df.iloc[i]
        node = nodes.iloc[i]

        if pd.isna(node.get("add1")) or pd.isna(node.get("dynamic_stop")):
            continue

        if in_trade:
            hold_days += 1
            cur_stop = node["dynamic_stop"]

            # 移动止损：浮盈≥8%→保本；≥15%→跟随MA50
            if entry_price > 0:
                pnl_pct = (row["Close"] - entry_price) / entry_price
                if pnl_pct >= 0.15 and node.get("ma50"):
                    cur_stop = max(cur_stop, float(node["ma50"]))
                elif pnl_pct >= 0.08:
                    cur_stop = max(cur_stop, entry_price)

            # 出场判断
            if row["High"] >= entry_tp1:
                ret = (entry_tp1 - entry_price) / entry_price - slippage
                trades.append({"return": ret, "outcome": "tp1",
                                "hold_days": hold_days, "entry": entry_price,
                                "exit": entry_tp1})
                in_trade = False
            elif row["Low"] <= cur_stop:
                ret = (cur_stop - entry_price) / entry_price - slippage
                trades.append({"return": ret, "outcome": "stop",
                                "hold_days": hold_days, "entry": entry_price,
                                "exit": cur_stop})
                in_trade = False
            elif hold_days >= max_hold_days:
                ret = (row["Close"] - entry_price) / entry_price - slippage
                trades.append({"return": ret, "outcome": "time_stop",
                                "hold_days": hold_days, "entry": entry_price,
                                "exit": row["Close"]})
                in_trade = False
        else:
            # 入场判断：当日 Low ≤ add1
            add1 = float(node["add1"])
            if row["Low"] <= add1 and add1 > 0:
                entry_price = add1 * (1 + slippage)
                entry_stop  = float(node["dynamic_stop"])
                entry_tp1   = float(node["tp1"])
                entry_date  = df.index[i]
                hold_days   = 0
                in_trade    = True

    return trades
```

- [ ] **Step 4: 运行测试确认通过**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_micro.py -v 2>&1 | tail -10
```
Expected: `4 passed`

- [ ] **Step 5: Commit**
```bash
cd ~/stock_team && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git add agents/backtest_micro.py tests/test_backtest_micro.py && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git commit -m "feat(backtest): micro structural node simulation"
```

---

## Task 4: 微观结构位参数扫描 + 盘中信号回测

**Files:**
- Modify: `agents/backtest_micro.py`（添加 scan_structural_params + intraday backtest）
- Modify: `tests/test_backtest_micro.py`

- [ ] **Step 1: 写扫描和盘中测试**

```python
# 追加到 tests/test_backtest_micro.py

def test_scan_structural_params_finds_best():
    from agents.backtest_micro import compute_structural_nodes, scan_structural_params
    df = _make_ohlcv(400)
    param_grid = {"k1": [0.75, 1.0, 1.25], "k4": [0.85, 0.90, 0.95]}
    results = scan_structural_params(df, param_grid)
    assert len(results) == 9
    assert all("metrics" in r for r in results)


def _make_5min_df(n=500, start=200.0):
    np.random.seed(7)
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.003)))
    closes = [max(1.0, c) for c in closes]
    times = pd.date_range("2026-01-02 09:30", periods=n, freq="5min", tz="America/New_York")
    df = pd.DataFrame({
        "Open":  [c * 0.999 for c in closes],
        "High":  [c * 1.005 for c in closes],
        "Low":   [c * 0.995 for c in closes],
        "Close": closes,
        "Volume":[int(1e5) for _ in closes],
    }, index=times)
    return df


def test_compute_intraday_signals_has_required():
    from agents.backtest_micro import compute_intraday_signals
    df = _make_5min_df()
    result = compute_intraday_signals(df)
    for col in ["rsi14_5m", "vwap_dev", "vol_ratio_5m"]:
        assert col in result.columns


def test_scan_intraday_params_returns_results():
    from agents.backtest_micro import compute_intraday_signals, scan_intraday_params
    df = _make_5min_df(600)
    signals = compute_intraday_signals(df)
    param_grid = {"rsi14_5m_oversold": [30, 35, 40],
                  "vwap_add_threshold": [-2.0, -1.5, -1.0]}
    results = scan_intraday_params(signals, param_grid,
                                   add1_price=195.0, stop_price=185.0, tp1_price=210.0)
    assert len(results) == 9
    assert all("metrics" in r for r in results)
```

- [ ] **Step 2: 运行确认失败**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_micro.py -k "scan_structural or intraday" -v 2>&1 | tail -10
```

- [ ] **Step 3: 实现参数扫描和盘中回测**

```python
# 追加到 agents/backtest_micro.py
import itertools

STRUCTURAL_PARAM_GRID = {
    "k1": [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
    "k4": [0.80, 0.85, 0.90, 0.95, 1.0],
    "k5": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
}

INTRADAY_PARAM_GRID = {
    "rsi14_5m_oversold":  [25, 30, 35, 40, 45],
    "vwap_add_threshold": [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5],
    "vol_ratio_shrink":   [0.5, 0.6, 0.7, 0.8, 0.9],
    "min_signals_required": [2, 3, 4],
}


def scan_structural_params(df: pd.DataFrame,
                            param_grid: dict = None,
                            slippage: float = 0.001) -> list:
    """对单只标的日线数据扫描结构位参数"""
    grid   = param_grid or STRUCTURAL_PARAM_GRID
    keys   = list(grid.keys())
    values = list(grid.values())
    results = []

    for combo in itertools.product(*values):
        params  = dict(zip(keys, combo))
        # 大师约束：k1 ≥ k2（k2 固定为 0.2）
        if params.get("k1", 1.0) < 0.2:
            continue
        nodes  = compute_structural_nodes(df, params)
        trades = simulate_structural_trades(df, nodes, slippage=slippage)
        if not trades:
            continue
        rets    = [t["return"] for t in trades]
        metrics = compute_metrics(rets)
        results.append({"params": params, "metrics": metrics,
                         "n_trades": len(trades)})

    return results


# ── 盘中信号回测 ──────────────────────────────────────────────────────────────

def compute_intraday_signals(df: pd.DataFrame) -> pd.DataFrame:
    """计算5分钟K线的盘中信号：RSI14、VWAP偏离、量比"""
    result = df.copy()
    close  = df["Close"]
    volume = df["Volume"]

    # RSI14（5分钟）
    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    result["rsi14_5m"] = (100 - 100 / (1 + gain / loss.replace(0, 0.001))).round(1)

    # VWAP 偏离（当日累计）
    try:
        dates = df.index.date
    except AttributeError:
        dates = pd.to_datetime(df.index).date
    vwap_list = []
    for dt in pd.unique(dates):
        mask = pd.to_datetime(df.index).date == dt
        sub  = df[mask]
        cum_vol = sub["Volume"].cumsum()
        cum_pv  = (sub["Close"] * sub["Volume"]).cumsum()
        vwap    = cum_pv / cum_vol.replace(0, 1)
        vwap_list.extend(vwap.tolist())
    result["vwap"]     = vwap_list
    result["vwap_dev"] = ((close - result["vwap"]) / result["vwap"] * 100).round(2)

    # 量比（当前5分钟量 vs 前20根均量）
    result["vol_ratio_5m"] = (volume / volume.rolling(20).mean()).round(3)

    return result


def _in_action_window(ts) -> bool:
    """判断时间戳是否在 10:00-10:30 ET"""
    try:
        et = ts.tz_convert("America/New_York") if hasattr(ts, "tz_convert") else ts
        h, m = et.hour, et.minute
        return (h == 10 and 0 <= m < 30)
    except Exception:
        return False


def scan_intraday_params(signals: pd.DataFrame, param_grid: dict,
                          add1_price: float, stop_price: float,
                          tp1_price: float, slippage: float = 0.001) -> list:
    """
    60天5分钟数据的盘中信号参数扫描。
    只检查 10:00-10:30 ET 操作窗口内的信号。
    """
    # 只保留操作窗口内的行
    window_mask = signals.index.map(_in_action_window)
    window_df   = signals[window_mask].copy()

    keys   = list(param_grid.keys())
    values = list(param_grid.values())
    results = []

    for combo in itertools.product(*values):
        params      = dict(zip(keys, combo))
        rsi_thresh  = params.get("rsi14_5m_oversold", 35)
        vwap_thresh = params.get("vwap_add_threshold", -1.5)
        vol_thresh  = params.get("vol_ratio_shrink", 0.7)
        min_sig     = params.get("min_signals_required", 3)

        trades = []
        for i, (ts, row) in enumerate(window_df.iterrows()):
            sigs = sum([
                row.get("rsi14_5m", 50) < rsi_thresh,
                row.get("vwap_dev", 0) < vwap_thresh,
                row.get("vol_ratio_5m", 1.0) < vol_thresh,
            ])
            if sigs >= min_sig:
                ep  = row["Close"] * (1 + slippage)
                ret = (tp1_price - ep) / ep if row["Close"] < tp1_price else \
                      (stop_price - ep) / ep
                trades.append({"return": ret,
                                "outcome": "tp1" if ret > 0 else "stop"})

        if not trades:
            results.append({"params": params, "metrics": {"n_trades": 0},
                             "n_trades": 0})
            continue

        rets    = [t["return"] for t in trades]
        metrics = compute_metrics(rets)
        results.append({"params": params, "metrics": metrics,
                         "n_trades": len(trades)})

    return results
```

- [ ] **Step 4: 运行所有微观测试**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_micro.py -v 2>&1 | tail -15
```
Expected: `8 passed`

- [ ] **Step 5: 添加 run_micro_backtest 主函数**

```python
# 追加到 agents/backtest_micro.py

HOLDINGS = ["NVDA", "BABA", "MSFT", "IAU", "MRVL", "LITE"]


def run_micro_backtest(syms: list = None, years: int = 5,
                       window_days: int = 60) -> dict:
    """
    运行结构位回测（5年日线，所有持仓各自优化 k 值）。
    返回 {sym: {best_params, all_results}} 的字典。
    """
    syms = syms or HOLDINGS
    out  = {}
    for sym in syms:
        print(f"[micro_backtest] 结构位回测: {sym}...")
        df = _fetch_ohlcv(sym, years=years)
        if df.empty:
            continue
        # 样本外验证（前80%训练，后20%验证）
        split = int(len(df) * 0.8)
        train_df_s, val_df_s = df.iloc[:split], df.iloc[split:]

        results = scan_structural_params(train_df_s)
        valid   = [r for r in results
                   if _passes_thresholds(r["metrics"]) and
                      _passes_master_constraints(r["params"], r["metrics"])]
        best = max(valid, key=lambda r: r["metrics"]["ev"]) if valid else None

        if best:
            val_nodes  = compute_structural_nodes(val_df_s, best["params"])
            val_trades = simulate_structural_trades(val_df_s, val_nodes)
            val_m      = compute_metrics([t["return"] for t in val_trades])
            train_wr   = best["metrics"].get("win_rate", 0)
            val_wr     = val_m.get("win_rate", 0)
            if train_wr and val_wr and train_wr - val_wr > 0.15:
                print(f"  ⚠️ {sym} 过拟合：训练{train_wr:.1%} vs 验证{val_wr:.1%}")
            best["oos_metrics"] = val_m

        out[sym] = {"best_params": best, "n_candidates": len(results),
                    "n_valid": len(valid)}
        print(f"  → {sym}: best k1={best['params'].get('k1')} EV={best['metrics'].get('ev')}" if best else f"  → {sym}: 无有效参数")

    return {"structural": out, "run_date": str(_date.today())}


def run_intraday_backtest(syms: list = None, window_days: int = 60) -> dict:
    """
    运行盘中信号回测（60天5分钟数据，全局参数优化）。
    """
    syms = syms or HOLDINGS
    all_results = []

    for sym in syms:
        print(f"[micro_backtest] 盘中信号回测: {sym}...")
        try:
            t    = yf.Ticker(sym)
            df5m = t.history(period=f"{window_days}d", interval="5m")
            if df5m.empty:
                continue
        except Exception:
            continue

        # 从 macro_strategy_{sym}.json 读当前节点价位
        macro_path = os.path.join(BASE, f"macro_strategy_{sym.upper()}.json")
        macro = {}
        if os.path.exists(macro_path):
            macro = json.load(open(macro_path))
        add1_p  = (macro.get("nodes", {}).get("add1") or {}).get("price", 0)
        stop_p  = (macro.get("nodes", {}).get("dynamic_stop") or {}).get("price", 0)
        tp1_p   = (macro.get("nodes", {}).get("tp1") or {}).get("price", 0)
        if not (add1_p and stop_p and tp1_p):
            print(f"  → {sym}: 无节点数据，跳过")
            continue

        signals = compute_intraday_signals(df5m)
        results = scan_intraday_params(signals, INTRADAY_PARAM_GRID,
                                       add1_price=add1_p, stop_price=stop_p,
                                       tp1_price=tp1_p)
        all_results.extend(results)

    # 聚合所有标的，找全局最优盘中参数
    from collections import defaultdict
    grouped = defaultdict(list)
    for r in all_results:
        key = tuple(sorted(r["params"].items()))
        grouped[key].append(r["metrics"])

    best_global = None
    best_ev = -999
    for key, metrics_list in grouped.items():
        valid_evs = [m["ev"] for m in metrics_list if m.get("ev") is not None]
        if not valid_evs:
            continue
        avg_ev = sum(valid_evs) / len(valid_evs)
        if avg_ev > best_ev:
            best_ev = avg_ev
            best_global = dict(key)

    return {"best_global_params": best_global, "best_ev": best_ev,
            "run_date": str(_date.today()), "window_days": window_days}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--structural", action="store_true")
    parser.add_argument("--intraday",   action="store_true")
    parser.add_argument("--years",      type=int, default=5)
    parser.add_argument("--window-days",type=int, default=60, dest="window_days")
    parser.add_argument("--sym",        nargs="*", default=None)
    args = parser.parse_args()

    if args.structural or not args.intraday:
        out = run_micro_backtest(syms=args.sym, years=args.years)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.intraday:
        out = run_intraday_backtest(syms=args.sym, window_days=args.window_days)
        print(json.dumps(out, ensure_ascii=False, indent=2))
```

- [ ] **Step 6: Commit**
```bash
cd ~/stock_team && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git add agents/backtest_micro.py tests/test_backtest_micro.py && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git commit -m "feat(backtest): micro structural scan + intraday signal backtest"
```

---

## Task 5: 统一入口 backtest_runner.py + 报告 + --apply 写回

**Files:**
- Create: `agents/backtest_runner.py`

- [ ] **Step 1: 实现 backtest_runner.py**

```python
# agents/backtest_runner.py
"""
回测统一入口 — backtest_runner.py
串行调用：backtest_macro → backtest_micro structural → backtest_micro intraday
生成对比报告，用户确认后 --apply 写回参数文件。

用法:
  python3.12 agents/backtest_runner.py --years 5            # 全量回测
  python3.12 agents/backtest_runner.py --intraday-only --window-days 60
  python3.12 agents/backtest_runner.py --apply findings/backtest_report_YYYY-MM-DD.json
  python3.12 agents/backtest_runner.py --restore findings/params_backup_YYYY-MM-DD.json
"""
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date as _date

BASE     = os.path.expanduser("~/stock_team")
CFG_DIR  = os.path.join(BASE, "config")
FIND_DIR = os.path.join(BASE, "findings")


def _load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _backup_params(date_str: str):
    """写回前备份当前所有参数"""
    backup = {
        "macro_strategy_params": _load_json(os.path.join(CFG_DIR, "macro_strategy_params.json")),
        "micro_strategy_params": _load_json(os.path.join(CFG_DIR, "micro_strategy_params.json")),
        "evolution_per_sym":     {},
    }
    import glob
    for path in glob.glob(os.path.join(BASE, "macro_strategy_*.json")):
        sym = os.path.basename(path).replace("macro_strategy_","").replace(".json","")
        if "_prev" not in sym:
            d = _load_json(path)
            backup["evolution_per_sym"][sym] = d.get("evolution", {})

    bak_path = os.path.join(FIND_DIR, f"params_backup_{date_str}.json")
    _save_json(bak_path, backup)
    print(f"[runner] 参数已备份至 {bak_path}")
    return bak_path


def apply_results(report_path: str):
    """将回测报告中的推荐参数写回配置文件"""
    report   = _load_json(report_path)
    date_str = str(_date.today())
    bak_path = _backup_params(date_str)

    # 1. 写回全局宏观参数
    macro_recs = (report.get("macro_backtest", {})
                  .get("best_params", {}).get("params", {}))
    if macro_recs:
        macro_cfg = _load_json(os.path.join(CFG_DIR, "macro_strategy_params.json"))
        mr = macro_cfg.setdefault("market_regime", {})
        for k in ["vix_panic_threshold", "ma20_dev_veto_pct",
                  "qqq5m_veto", "vix_ts_threshold"]:
            if k in macro_recs:
                mr[k] = macro_recs[k]
        _save_json(os.path.join(CFG_DIR, "macro_strategy_params.json"), macro_cfg)
        print(f"[runner] ✅ macro_strategy_params.json 已更新")

    # 2. 写回个股 evolution 字段
    structural = report.get("micro_structural", {}).get("structural", {})
    for sym, sym_data in structural.items():
        best = sym_data.get("best_params")
        if not best:
            continue
        path = os.path.join(BASE, f"macro_strategy_{sym.upper()}.json")
        if not os.path.exists(path):
            continue
        macro = _load_json(path)
        ev = macro.setdefault("evolution", {})
        ev.update({k: v for k, v in best["params"].items()
                   if k in ("k1","k2","k3","k4","k5","k6")})
        ev["last_backtest_date"] = date_str
        _save_json(path, macro)
        print(f"[runner] ✅ macro_strategy_{sym}.json evolution 已更新")

    # 3. 写回全局微观参数（盘中信号）
    intraday_recs = report.get("micro_intraday", {}).get("best_global_params", {})
    if intraday_recs:
        micro_cfg = _load_json(os.path.join(CFG_DIR, "micro_strategy_params.json"))
        fs = micro_cfg.setdefault("flex_signals", {})
        for k in ["rsi14_5m_oversold", "vwap_add_threshold",
                  "vol_ratio_shrink", "min_signals_required"]:
            if k in intraday_recs:
                fs[k] = intraday_recs[k]
        _save_json(os.path.join(CFG_DIR, "micro_strategy_params.json"), micro_cfg)
        print(f"[runner] ✅ micro_strategy_params.json 已更新")

    print(f"\n[runner] 如需恢复旧参数: python3.12 agents/backtest_runner.py --restore {bak_path}")


def restore_params(backup_path: str):
    """从备份恢复参数"""
    backup = _load_json(backup_path)
    _save_json(os.path.join(CFG_DIR, "macro_strategy_params.json"),
               backup.get("macro_strategy_params", {}))
    _save_json(os.path.join(CFG_DIR, "micro_strategy_params.json"),
               backup.get("micro_strategy_params", {}))
    for sym, ev in backup.get("evolution_per_sym", {}).items():
        path = os.path.join(BASE, f"macro_strategy_{sym.upper()}.json")
        if os.path.exists(path):
            macro = _load_json(path)
            macro["evolution"] = ev
            _save_json(path, macro)
    print(f"[runner] ✅ 参数已从 {backup_path} 恢复")


def run_full_backtest(years: int = 5, window_days: int = 60,
                      intraday_only: bool = False) -> str:
    """
    串行运行三层回测，保存报告，返回报告路径。
    Step 1: 宏观 → Step 2: 微观结构位（用最优宏观参数为背景）→ Step 3: 盘中信号
    """
    from agents.backtest_macro import run_macro_backtest
    from agents.backtest_micro import run_micro_backtest, run_intraday_backtest

    date_str = str(_date.today())
    report   = {"run_date": date_str, "years": years}

    if not intraday_only:
        print("\n[runner] === Step 1: 宏观策略回测 ===")
        macro_out = run_macro_backtest(years=years)
        report["macro_backtest"] = macro_out

        print("\n[runner] === Step 2: 微观结构位回测 ===")
        micro_out = run_micro_backtest(years=years)
        report["micro_structural"] = micro_out

    print(f"\n[runner] === Step 3: 盘中信号回测（{window_days}天）===")
    intraday_out = run_intraday_backtest(window_days=window_days)
    report["micro_intraday"] = intraday_out

    # 保存机器可读报告
    report_path = os.path.join(FIND_DIR, f"backtest_report_{date_str}.json")
    _save_json(report_path, report)

    # 打印摘要
    _print_summary(report)
    print(f"\n[runner] 报告已保存: {report_path}")
    print(f"[runner] 确认后执行写回: python3.12 agents/backtest_runner.py --apply {report_path}")

    return report_path


def _print_summary(report: dict):
    """打印人类可读摘要"""
    print("\n" + "═" * 60)
    print("  回测结果摘要")
    print("═" * 60)

    macro = report.get("macro_backtest", {})
    best_m = macro.get("best_params", {})
    if best_m:
        m = best_m.get("metrics", {})
        print(f"\n【宏观策略最优参数】")
        print(f"  参数: {best_m.get('params', {})}")
        print(f"  EV={m.get('ev'):.4f} 胜率={m.get('win_rate'):.1%} "
              f"Sortino={m.get('sortino'):.2f} 最大回撤={m.get('max_drawdown'):.1%}")

    structural = report.get("micro_structural", {}).get("structural", {})
    if structural:
        print(f"\n【微观结构位最优参数（各标的）】")
        for sym, d in structural.items():
            best = d.get("best_params", {})
            if best:
                print(f"  {sym}: k1={best['params'].get('k1')} k4={best['params'].get('k4')} "
                      f"EV={best['metrics'].get('ev', 0):.4f}")

    intraday = report.get("micro_intraday", {})
    if intraday.get("best_global_params"):
        print(f"\n【盘中信号最优参数】")
        print(f"  参数: {intraday['best_global_params']}")
        print(f"  EV={intraday.get('best_ev', 0):.4f}")

    print("═" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="回测统一入口")
    parser.add_argument("--years",         type=int, default=5)
    parser.add_argument("--window-days",   type=int, default=60, dest="window_days")
    parser.add_argument("--intraday-only", action="store_true", dest="intraday_only")
    parser.add_argument("--apply",         type=str, default=None,
                        help="将报告写回参数文件")
    parser.add_argument("--restore",       type=str, default=None,
                        help="从备份恢复参数")
    args = parser.parse_args()

    if args.apply:
        apply_results(args.apply)
    elif args.restore:
        restore_params(args.restore)
    else:
        run_full_backtest(years=args.years,
                          window_days=args.window_days,
                          intraday_only=args.intraday_only)
```

- [ ] **Step 2: 语法验证**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "
import py_compile
py_compile.compile('agents/backtest_runner.py', doraise=True)
print('syntax OK')
from agents.backtest_runner import apply_results, restore_params, run_full_backtest
print('imports OK')
"
```

- [ ] **Step 3: Commit**
```bash
cd ~/stock_team && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git add agents/backtest_runner.py && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git commit -m "feat(backtest): unified runner + apply/restore mechanism"
```

---

## Task 6: 更新 stock-backtest skill

**Files:**
- Modify: `~/.claude/skills/stock-backtest.md`

- [ ] **Step 1: 替换 skill 内容**

```markdown
---
name: stock-backtest
description: 策略回测和参数优化。用户说"回测"、"信号扫描"、"找最优阈值"、"验证策略"、"跑回测"、"参数优化"时触发。运行三层回测（宏观/微观结构位/盘中信号），输出6指标评估结果，人工确认后写回参数文件。
user-invocable: true
---

# Stock Backtest Skill

## When to Invoke

Trigger when user says:
- "回测" / "跑回测" / "参数优化" / "验证策略"
- "信号扫描" / "找最优阈值" / "历史验证"
- "更新参数" / "优化阈值"

## Instructions

### 全量回测（宏观 + 微观结构位 + 盘中信号，约15-25分钟）

**Step 1: 运行三层回测**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/backtest_runner.py --years 5
```
Writes: `findings/backtest_report_{date}.json`

**Step 2: 用户查看报告摘要**
终端已打印摘要。询问用户："是否确认写回参数？"

**Step 3: 用户确认后写回**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/backtest_runner.py --apply findings/backtest_report_{date}.json
```

### 仅盘中信号回测（约3-5分钟，每2-4周重跑）

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/backtest_runner.py --intraday-only --window-days 60
```

### 恢复旧参数（若新参数表现变差）

```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/backtest_runner.py --restore findings/params_backup_{date}.json
```

## Output Template

```
══════════════════════════════════════════════════════════════
  回测结果摘要
══════════════════════════════════════════════════════════════
【宏观策略最优参数】
  参数: {best_params}
  EV={ev} 胜率={win_rate} Sortino={sortino} 最大回撤={max_drawdown}

【微观结构位最优参数（各标的）】
  NVDA: k1={k1} k4={k4} EV={ev}
  ...

【盘中信号最优参数】
  参数: {params}  EV={ev}
══════════════════════════════════════════════════════════════
报告已保存: findings/backtest_report_{date}.json
确认写回: python3.12 agents/backtest_runner.py --apply findings/backtest_report_{date}.json
```

## Error Handling

- yfinance 拉取失败：跳过该标的，继续其他标的
- 无有效参数（全部过拟合）：显示 "无满足门槛的参数组合，建议放宽门槛或增加样本"
- --apply 前自动备份：若写回失败，用 --restore 恢复
```

- [ ] **Step 2: 验证 skill 文件存在且语法正确**
```bash
head -5 ~/.claude/skills/stock-backtest.md
```
Expected: 显示新的 description 和 name 字段。

- [ ] **Step 3: Commit**
```bash
cd ~/stock_team && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git add ~/.claude/skills/stock-backtest.md CHANGELOG.md && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git commit -m "feat(backtest): update stock-backtest skill to new runner"
```

---

## Task 7: 端到端冒烟测试

- [ ] **Step 1: 语法验证全部脚本**
```bash
cd ~/stock_team && for f in agents/backtest_macro.py agents/backtest_micro.py agents/backtest_runner.py; do
  /tool/pandora/bin/python3.12 -c "import py_compile; py_compile.compile('$f', doraise=True)" && echo "$f OK"
done
```

- [ ] **Step 2: 单元测试全部通过**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/test_backtest_macro.py tests/test_backtest_micro.py -v 2>&1 | tail -20
```
Expected: `12 passed`（4 + 8）

- [ ] **Step 3: 快速冒烟（用少量数据验证链路）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "
from agents.backtest_macro import run_macro_backtest
from agents.backtest_micro import run_micro_backtest

# 只跑2只股票，1年数据，验证链路不报错
macro = run_macro_backtest(syms=['NVDA','MSFT'], years=1)
print('macro OK, n_samples:', macro.get('n_samples'))

micro = run_micro_backtest(syms=['NVDA'], years=1)
print('micro OK, syms:', list(micro.get('structural',{}).keys()))
" 2>&1 | tail -10
```
Expected: 无 Exception，打印 OK 信息。

- [ ] **Step 4: 最终 commit**
```bash
cd ~/stock_team && GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git commit --allow-empty -m "feat(backtest): smoke test verified, system ready"
```

---

## 实施说明

- **Python 路径**: `/tool/pandora/bin/python3.12`
- **Git 命令**: 必须加 `GIT_DISCOVERY_ACROSS_FILESYSTEM=1` 前缀
- **测试运行目录**: `cd ~/stock_team` 后运行 pytest
- **网络请求**: Task 7 冒烟测试需要真实网络拉取 yfinance 数据，建议在测试环境运行
- **运行时间**: 全量回测约 15-25 分钟，冒烟测试约 2-3 分钟（1年数据，2只股票）
- **旧 backtest_engine.py**: 保留不删，其 `_fetch_ohlcv` / `_compute_daily_signals` 等基础函数被新脚本 import 复用
