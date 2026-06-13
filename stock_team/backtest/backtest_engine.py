"""
backtest_engine.py — 历史信号参数扫描 + 框架模拟

用法:
    python3.12 agents/backtest_engine.py scan MRVL RKLB   # 信号扫描
    python3.12 agents/backtest_engine.py simulate MRVL    # 框架模拟
    python3.12 agents/backtest_engine.py update           # 用扫描结果更新阈值配置

范围限制:
    回测仅覆盖可从历史 OHLCV + 宏观代理数据重建的信号:
    - 技术信号: MA20乖离、RS5日超额、量比
    watchlist_score 和 analyst_target 不可历史回测（需实时数据）。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

_BASE          = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
_FINDINGS      = os.path.join(_BASE, "findings")
_THRESHOLDS    = os.path.join(_BASE, "config", "decision_thresholds.json")
_OPT_OUT       = os.path.join(_FINDINGS, "signal_thresholds_optimized.json")
_MIN_SAMPLES   = 20    # 阈值候选需有至少这么多样本才被考虑
_UPDATE_MIN_PP = 0.05  # 只有胜率超过 0.5+0.05=0.55 才写入配置


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
    df["rs5"] = ((sym_ret5 - spy_close.pct_change(5)) * 100).round(3)

    # 量比（当日量 / 前20日均量，用 shift(1) 避免 look-ahead）
    vol_ma20      = df["Volume"].rolling(20).mean().shift(1)
    df["vol_ratio"] = (df["Volume"] / vol_ma20).round(3)

    return df


def _add_forward_returns(df: pd.DataFrame, days: int = 5) -> pd.DataFrame:
    """追加 fwd_{days}d 列：days 日后的涨跌幅（用于胜率计算）"""
    df = df.copy()
    df[f"fwd_{days}d"] = df["Close"].shift(-days) / df["Close"] - 1
    return df


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
    assert direction in ("below", "above"), f"direction 须为 'below' 或 'above'，收到 {direction!r}"
    rows = df[[signal_col, fwd_col]].dropna()
    if len(rows) < min_samples:
        return {"optimal": None, "win_rate": None, "n_samples": 0, "mean_ret": None, "scan": []}

    scan = []
    for thr in thresholds:
        mask   = rows[signal_col] <= thr if direction == "below" else rows[signal_col] >= thr
        subset = rows[mask]
        n      = len(subset)
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


def run_portfolio_scan(symbols: list, years: int = 2,
                       write_output: bool = True) -> dict:
    """
    对标的列表运行信号扫描，聚合得到统一最优阈值。
    统一阈值的统计力量更大（更多样本）。

    write_output=True 时写入 findings/signal_thresholds_optimized.json。
    """
    spy_df = _fetch_spy(years=years)
    if spy_df.empty:
        return {"error": "SPY 数据获取失败", "symbols_scanned": []}

    all_dfs = []
    scanned = []
    for sym in symbols:
        sym_df = _fetch_ohlcv(sym, years=years)
        if sym_df.empty:
            continue
        df = _compute_daily_signals(sym_df, spy_df)
        df = _add_forward_returns(df, days=5)
        df = df.dropna(subset=["ma20_dev", "rs5", "vol_ratio"])
        all_dfs.append(df)
        scanned.append(sym)

    if not all_dfs:
        return {"error": "无有效数据", "symbols_scanned": []}

    combined = pd.concat(all_dfs, ignore_index=True)

    output = {
        "scan_date":       datetime.now().strftime("%Y-%m-%d"),
        "symbols_scanned": scanned,
        "n_total_samples": len(combined),
        "ma20_dev_max": _scan_signal(combined, "ma20_dev",
                                      [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10],
                                      direction="below"),
        "rs5_min":      _scan_signal(combined, "rs5",
                                      [-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0],
                                      direction="above"),
        "vol_ratio_max":_scan_signal(combined, "vol_ratio",
                                      [0.6, 0.7, 0.8, 0.9, 1.0, 1.2],
                                      direction="below"),
        "_note": (
            "watchlist_score 不可历史回测（需实时分析师数据）。"
            "macro_score、RR 的历史阈值建议从 observation_outcomes.jsonl 实盘数据验证。"
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
    """
    if not os.path.exists(_THRESHOLDS):
        return False

    with open(_THRESHOLDS, encoding="utf-8") as f:
        current = json.load(f)

    updated  = False
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
        current["_updated"]        = datetime.now().strftime("%Y-%m-%d")
        current["_update_source"]  = "backtest_engine"
        current["_update_baseline"] = baseline
        with open(_THRESHOLDS, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)

    return updated


def simulate_decision_framework(symbols: list, thresholds: dict,
                                 years: int = 2,
                                 write_output: bool = True) -> dict:
    """
    简化框架历史回测：用可回测的技术信号模拟"可入场"决策。

    使用的信号（可历史重建）：
      - MA20乖离 ≤ ma20_dev_max（软否决1）
      - RS5 ≥ rs5_min（软否决2）
      软否决 ≤ 1 → 模拟入场，统计 5日后收益率。

    不可重建（不纳入）：RR、watchlist_score、thesis_status。
    """
    sv       = thresholds.get("soft_vetoes", {})
    ma20_max = sv.get("ma20_dev_max", 0.05)
    rs5_min  = sv.get("rs5_min", 0.0)

    spy_df   = _fetch_spy(years=years)
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
        return {"error": "无有效数据", "n_entries": 0, "win_rate": None,
                "mean_ret_pct": None, "note": "无有效数据"}

    combined = pd.concat(all_rows)
    combined = combined.dropna(subset=["ma20_dev", "rs5", "fwd_5d"])

    combined["soft_veto_count"] = (
        (combined["ma20_dev"] > ma20_max).astype(int) +
        (combined["rs5"] < rs5_min).astype(int)
    )
    entries = combined[combined["soft_veto_count"] <= 1]
    n       = len(entries)

    if n == 0:
        summary = {"win_rate": None, "n_entries": 0, "mean_ret_pct": None}
    else:
        summary = {
            "win_rate":    round(float((entries["fwd_5d"] > 0).mean()), 4),
            "n_entries":   n,
            "mean_ret_pct": round(float(entries["fwd_5d"].mean() * 100), 2),
        }

    output = {
        **summary,
        "symbols":        symbols,
        "years":          years,
        "thresholds_used": {"ma20_dev_max": ma20_max, "rs5_min": rs5_min},
        "note": (
            "简化框架回测：仅使用 MA20乖离 + RS5 两条软否决（可历史重建）。"
            "硬否决（RR/宏观/watchlist_score）因需实时数据未纳入。"
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
    import argparse

    parser = argparse.ArgumentParser(description="历史信号回测引擎")
    sub    = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="运行信号参数扫描")
    p_scan.add_argument("symbols", nargs="*")
    p_scan.add_argument("--years", type=int, default=2)

    p_sim = sub.add_parser("simulate", help="运行框架简化回测")
    p_sim.add_argument("symbols", nargs="*")
    p_sim.add_argument("--years", type=int, default=2)

    sub.add_parser("update", help="将扫描结果写入 decision_thresholds.json")

    args = parser.parse_args()

    cfg_path = os.path.join(_BASE, "config", "poll_config.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    default_syms = cfg.get("watchlist", [])[:10]

    if args.cmd == "scan":
        symbols = getattr(args, "symbols", None) or default_syms
        result  = run_portfolio_scan(symbols, years=getattr(args, "years", 2))
        print(f"扫描完成: {result.get('symbols_scanned')}")
        for k in ["ma20_dev_max", "rs5_min", "vol_ratio_max"]:
            r = result.get(k, {})
            print(f"  {k}: optimal={r.get('optimal')}, win_rate={r.get('win_rate')}, n={r.get('n_samples')}")

    elif args.cmd == "simulate":
        symbols = getattr(args, "symbols", None) or default_syms
        if not os.path.exists(_THRESHOLDS):
            print(f"阈值配置不存在: {_THRESHOLDS}，请先运行 update 或确认文件存在")
            return
        with open(_THRESHOLDS, encoding="utf-8") as f:
            thresholds = json.load(f)
        result = simulate_decision_framework(symbols, thresholds, years=getattr(args, "years", 2))
        print(f"框架回测: {result.get('n_entries')}次入场, 胜率={result.get('win_rate')}, 均收益={result.get('mean_ret_pct')}%")

    elif args.cmd == "update":
        if not os.path.exists(_OPT_OUT):
            print("请先运行 scan 命令生成扫描结果")
            return
        with open(_OPT_OUT, encoding="utf-8") as f:
            scan = json.load(f)
        updated = _try_update_thresholds(scan)
        print("✅ 阈值已更新" if updated else "ℹ️ 无需更新（胜率未超过 55% 基线）")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
