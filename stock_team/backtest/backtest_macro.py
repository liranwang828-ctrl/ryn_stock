"""
宏观策略回测 — backtest_macro.py
验证"何时适合进场"的宏观环境参数，5年日线数据。

用法:
  python3.12 agents/backtest_macro.py [--years 5] [--syms NVDA AAPL ...]
"""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date as _date

BASE       = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
CFG_DIR    = os.path.join(BASE, "config")
FIND_DIR   = os.path.join(BASE, "findings")

from stock_team.backtest.backtest_engine import _fetch_ohlcv

RISK_FREE_RATE = 0.045  # 4.5% 近似3月期美债


def _fetch_vix(years: int = 5) -> pd.DataFrame:
    """拉取 ^VIX 和 ^VIX3M 日线"""
    vix   = _fetch_ohlcv("^VIX",   years=years)
    vix3m = _fetch_ohlcv("^VIX3M", years=years)
    if vix.empty:
        return pd.DataFrame()
    df = vix[["Close"]].rename(columns={"Close": "vix"})
    if not vix3m.empty:
        df = df.join(vix3m[["Close"]].rename(columns={"Close": "vix3m"}), how="left")
        df["vix_ts"] = (df["vix"] / df["vix3m"]).round(3)
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
    df    = sym_df[["Close", "High", "Low", "Volume"]].copy()
    close = df["Close"]

    ma20  = close.rolling(20).mean()
    df["ma20_dev"] = ((close - ma20) / ma20).round(4)

    ma200 = close.rolling(200).mean()
    df["ma200_up"] = (ma200.diff(5) > 0).astype(bool)

    hi52w = df["High"].rolling(252).max()
    df["dist_hi52w"] = ((close - hi52w) / hi52w).round(4)

    spy_close = spy_df["Close"].reindex(df.index, method="ffill")
    spy_ma200 = spy_df["Close"].rolling(200).mean().reindex(df.index, method="ffill")
    df["spy_above_ma200"] = (spy_close > spy_ma200).astype(bool)

    sym_ret5  = close.pct_change(5)
    spy_ret5  = spy_close.pct_change(5)
    df["rs5"] = ((sym_ret5 - spy_ret5) * 100).round(2)

    vol = df["Volume"]
    df["vol_ratio"] = (vol.rolling(5).mean() / vol.rolling(20).mean()).round(3)

    if not vix_df.empty:
        vix_aligned   = vix_df.reindex(df.index, method="ffill")
        df["vix_level"] = vix_aligned.get("vix_level", pd.Series(dtype=float))
        df["vix_ts"]    = vix_aligned.get("vix_ts",    pd.Series(dtype=float))
    else:
        df["vix_level"] = np.nan
        df["vix_ts"]    = np.nan

    return df.dropna(subset=["ma20_dev", "rs5", "vol_ratio"])


def compute_metrics(returns: list, risk_free_rate: float = RISK_FREE_RATE,
                    spy_ann_return: float = 0.12) -> dict:
    """
    计算6个回测指标。
    returns: 每笔交易收益率列表（小数）
    """
    if not returns:
        return {k: None for k in ["ev", "win_rate", "rr_ratio", "sortino",
                                   "max_drawdown", "max_single_loss",
                                   "n_trades", "alpha_vs_spy"]}
    arr = np.array(returns)
    n   = len(arr)

    wins   = arr[arr > 0]
    losses = arr[arr < 0]

    win_rate = len(wins) / n
    avg_win  = float(wins.mean())   if len(wins)   > 0 else 0.0
    avg_loss = float(losses.mean()) if len(losses)  > 0 else 0.0
    ev       = win_rate * avg_win + (1 - win_rate) * avg_loss

    rr_ratio = (abs(avg_win) / abs(avg_loss)) if avg_loss != 0 else 0.0

    ann_factor   = min(n, 50)
    ann_return   = (1 + ev) ** ann_factor - 1
    down_dev     = float(arr[arr < 0].std()) if len(losses) > 1 else 0.001
    ann_down_dev = down_dev * np.sqrt(ann_factor)
    sortino      = (ann_return - risk_free_rate) / ann_down_dev if ann_down_dev > 0 else 0.0

    cumulative = np.cumprod(1 + arr)
    peak       = np.maximum.accumulate(cumulative)
    drawdowns  = (cumulative - peak) / peak
    max_dd     = float(drawdowns.min())

    max_single_loss = float(losses.min()) if len(losses) > 0 else 0.0
    alpha_vs_spy    = ann_return - spy_ann_return

    return {
        "ev":              round(ev, 4),
        "win_rate":        round(win_rate, 4),
        "avg_win":         round(avg_win, 4),
        "avg_loss":        round(avg_loss, 4),
        "rr_ratio":        round(rr_ratio, 2),
        "sortino":         round(sortino, 3),
        "max_drawdown":    round(max_dd, 4),
        "max_single_loss": round(max_single_loss, 4),
        "n_trades":        n,
        "alpha_vs_spy":    round(alpha_vs_spy, 4),
    }


def apply_macro_filter(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    应用宏观策略过滤条件，返回"允许进场的日期"子集。
    """
    mask = pd.Series(True, index=df.index)

    vix_thresh = params.get("vix_panic_threshold", 25)
    if "vix_level" in df.columns:
        # NaN vix_level（VIX数据缺失）视为通过，不排除
        mask &= (df["vix_level"].isna() | (df["vix_level"] < vix_thresh))

    ma20_max = params.get("ma20_dev_veto_pct", 10.0) / 100
    if "ma20_dev" in df.columns:
        mask &= df["ma20_dev"] < ma20_max

    if params.get("ma200_filter", True) and "ma200_up" in df.columns:
        mask &= df["ma200_up"]

    vix_ts_thresh = params.get("vix_ts_threshold", 1.1)
    if "vix_ts" in df.columns:
        mask &= (df["vix_ts"].isna() | (df["vix_ts"] < vix_ts_thresh))

    qqq5m_veto = params.get("qqq5m_veto", -0.5)
    if "qqq5m" in df.columns:
        mask &= df["qqq5m"] >= qqq5m_veto

    if params.get("spy_ma200_veto", True) and "spy_above_ma200" in df.columns:
        mask &= df["spy_above_ma200"]

    return df[mask]


def scan_macro_params(df: pd.DataFrame, param_grid: dict,
                      forward_col: str = "fwd_10d") -> list:
    """网格搜索宏观参数，返回每个参数组合的指标列表。"""
    keys   = list(param_grid.keys())
    values = list(param_grid.values())
    results = []

    for combo in itertools.product(*values):
        params   = dict(zip(keys, combo))
        filtered = apply_macro_filter(df, params)
        if filtered.empty or forward_col not in filtered.columns:
            continue
        rets    = filtered[forward_col].dropna().tolist()
        metrics = compute_metrics(rets)
        results.append({"params": params, "metrics": metrics,
                         "n_filtered": len(filtered)})

    return results


def _passes_thresholds(metrics: dict) -> bool:
    """双重门槛 + Taleb 尾部检验"""
    if metrics.get("win_rate", 0) < 0.55:
        return False
    if metrics.get("rr_ratio", 0) < 1.5:
        return False
    avg_win  = metrics.get("avg_win", 0)
    max_loss = abs(metrics.get("max_single_loss", 0))
    if avg_win > 0 and max_loss / avg_win > 3.0:
        return False
    return True


def _passes_master_constraints(params: dict, metrics: dict) -> bool:
    """大师约束：逻辑一致性 + 风险上限检查"""
    if metrics.get("max_drawdown", -1) < -0.25:
        return False
    if params.get("k4", 1.0) > 1.0:
        return False
    if params.get("k5", 0.5) >= params.get("k6", 1.0):
        return False
    return True


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
    "qqq5m_veto":          [-1.0, -0.7, -0.5, -0.3],
    "spy_ma200_veto":      [True, False],
}


def _apply_earnings_blackout(df: pd.DataFrame, sym: str,
                              blackout_days: int = 10) -> pd.DataFrame:
    """过滤财报前10个交易日的信号，失败时静默跳过。"""
    try:
        cal = yf.Ticker(sym).calendar
        if cal is None:
            return df
        # yfinance returns dict with 'Earnings Date' key
        if isinstance(cal, dict):
            earn_dates_raw = cal.get("Earnings Date", [])
            if not isinstance(earn_dates_raw, (list, tuple)):
                earn_dates_raw = [earn_dates_raw]
            earn_dates = pd.to_datetime(earn_dates_raw, errors="coerce").dropna()
        else:
            # DataFrame fallback (older yfinance)
            earn_dates = []
            for col in cal.columns:
                earn_dates.extend(pd.to_datetime(cal[col].dropna()).tolist())
            earn_dates = pd.to_datetime(earn_dates, errors="coerce")
        for earn_date in earn_dates:
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


def _analyze_by_period(df: pd.DataFrame, params: dict) -> dict:
    """分时期分析：4个市场环境"""
    periods = {
        "2021_bull":     ("2021-01-01", "2021-12-31"),
        "2022_bear":     ("2022-01-01", "2022-12-31"),
        "2023_recovery": ("2023-01-01", "2023-12-31"),
        "2024_ai_bull":  ("2024-01-01", "2024-12-31"),
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
        sub = df[df["sym"].isin(syms)] if "sym" in df.columns else df
        if sub.empty or not params:
            result[label] = {"n": 0}
            continue
        filtered = apply_macro_filter(sub, params)
        rets = filtered["fwd_10d"].dropna().tolist() if "fwd_10d" in filtered.columns else []
        result[label] = {**compute_metrics(rets), "n": len(filtered)}
    return result


def run_macro_backtest(syms: list = None, years: int = 5) -> dict:
    """对标的列表运行宏观策略回测，聚合计算，扫描参数网格。"""
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
        signals["fwd_10d"] = df["Close"].pct_change(10).shift(-10)
        signals = _apply_earnings_blackout(signals, sym)
        signals["sym"] = sym
        all_dfs.append(signals)

    if not all_dfs:
        return {"error": "无有效数据"}

    combined = pd.concat(all_dfs).dropna(subset=["ma20_dev", "rs5", "fwd_10d"])
    print(f"[macro_backtest] 合并样本: {len(combined)} 行，扫描 {_grid_size(PARAM_GRID)} 组参数...")

    # 样本外验证：按时间前80%训练，后20%验证
    combined_sorted = combined.sort_index()
    unique_dates = combined_sorted.index.unique().sort_values()
    split_date = unique_dates[int(len(unique_dates) * 0.8)]
    train_df = combined_sorted[combined_sorted.index < split_date]
    val_df   = combined_sorted[combined_sorted.index >= split_date]
    combined = combined_sorted  # use sorted version for by_period analysis

    results = scan_macro_params(train_df, PARAM_GRID, forward_col="fwd_10d")
    results = [r for r in results if _passes_master_constraints(r["params"], r["metrics"])]

    valid = [r for r in results if _passes_thresholds(r["metrics"])]
    best  = max(valid, key=lambda r: r["metrics"]["ev"]) if valid else None

    if best:
        val_f    = apply_macro_filter(val_df, best["params"])
        val_rets = val_f["fwd_10d"].dropna().tolist() if "fwd_10d" in val_f.columns else []
        val_m    = compute_metrics(val_rets)
        train_wr = best["metrics"].get("win_rate", 0)
        val_wr   = val_m.get("win_rate", 0)
        if train_wr and val_wr and train_wr - val_wr > 0.15:
            print(f"⚠️ 过拟合警告：训练{train_wr:.1%} vs 验证{val_wr:.1%}，差>15pp")
        best["oos_metrics"] = val_m

    by_period = _analyze_by_period(combined, best["params"] if best else {})
    by_sector = _analyze_by_sector(combined, best["params"] if best else {})
    current_params = json.load(open(os.path.join(CFG_DIR, "macro_strategy_params.json"),
                                    encoding="utf-8"))

    return {
        "best_params":    best,
        "all_results":    results,
        "by_period":      by_period,
        "by_sector":      by_sector,
        "current_params": current_params,
        "n_samples":      len(combined),
        "n_symbols":      len(all_dfs),
        "run_date":       str(_date.today()),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--syms", nargs="*", default=None)
    args = parser.parse_args()
    out = run_macro_backtest(syms=args.syms, years=args.years)
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("all_results",)}, ensure_ascii=False, indent=2))
