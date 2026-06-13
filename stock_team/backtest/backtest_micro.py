"""
微观策略回测 — backtest_micro.py
- 结构位回测（5年日线）：Add1/TP1/DynamicStop 节点模拟
- 盘中信号回测（60天5分钟）：RSI/VWAP/量比 Flex 信号

用法:
  python3.12 agents/backtest_micro.py --structural [--years 5] [--sym NVDA]
  python3.12 agents/backtest_micro.py --intraday [--window-days 60] [--sym NVDA]
"""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date as _date

BASE    = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
CFG_DIR = os.path.join(BASE, "config")

from stock_team.backtest.backtest_engine import _fetch_ohlcv
from stock_team.backtest.backtest_macro  import compute_metrics, _passes_thresholds, _passes_master_constraints

RISK_FREE_RATE = 0.045

STRUCTURAL_PARAM_GRID = {
    "k1":  [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],   # 止损 ATR 倍数
    "k_tp":[1.5, 2.0, 2.5, 3.0, 3.5],                 # TP1 ATR 倍数（新）
    "k5":  [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], # 情景降级 ATR 倍数
}

INTRADAY_PARAM_GRID = {
    "rsi14_5m_oversold":  [25, 30, 35, 40, 45],
    "vwap_add_threshold": [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5],
    "vol_ratio_shrink":   [0.5, 0.6, 0.7, 0.8, 0.9],
    "min_signals_required": [2, 3, 4],
}

HOLDINGS = ["NVDA", "BABA", "MSFT", "IAU", "MRVL", "LITE"]


LEVERAGED_CFG_PATH = os.path.join(CFG_DIR, "leveraged_pairs.json")

def _get_leverage_factor(sym: str) -> int:
    """获取标的的杠杆倍数。如果标的本身是杠杆ETF，或者其底层映射存在杠杆，则返回相应杠杆倍数。"""
    if not sym:
        return 1
    if not os.path.exists(LEVERAGED_CFG_PATH):
        return 1
    try:
        with open(LEVERAGED_CFG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 1. 检查 sym 是否是底层标的并被配置了杠杆
        if sym in cfg:
            return cfg[sym].get("leverage", 1)
        # 2. 检查 sym 是否是配置里的杠杆 ETF 符号本身
        for k, v in cfg.items():
            if v.get("sym") == sym:
                return v.get("leverage", 1)
    except Exception:
        pass
    return 1


def compute_dynamic_slippage(sym: str, close: float, atr14: float, gap_pct: float, leverage: int = 1) -> float:
    """
    计算复合动态滑点与交易损耗。
    - 基础费率: 0.05% (滑点) + 0.02% (规费/印花税等交易损耗) = 0.07%
    - 波动率惩罚: (ATR14 / Close) * 0.1 (高波动标的买卖价差更宽)
    - 开盘缺口惩罚: abs(gap_pct) * 0.15 (大跳空代表市场情绪剧烈，冲击成本上升)
    - 杠杆损耗惩罚: 按杠杆倍数乘积放大
    """
    base_friction = 0.0007  # 0.07%
    
    # 波动率惩罚
    vol_ratio = (atr14 / close) if (close > 0 and atr14 > 0) else 0.02
    vol_penalty = vol_ratio * 0.1
    
    # 缺口惩罚
    gap_penalty = abs(gap_pct) * 0.15 if gap_pct > 0 else 0.0
    
    total_slip = (base_friction + vol_penalty + gap_penalty) * leverage
    
    # 设定上下界限，保护数值合理性
    return min(max(total_slip, 0.0005), 0.015)


def compute_leverage_decay(leverage: int, hold_days: int) -> float:
    """
    计算杠杆 ETF 的每日复利波动率衰减（Volatility Drag）。
    - 2x 杠杆: 每日衰减约 0.03% (0.0003)
    - 3x 杠杆: 每日衰减约 0.08% (0.0008)
    """
    if leverage <= 1:
        return 0.0
    daily_decay = 0.0003 if leverage == 2 else 0.0008 if leverage == 3 else 0.0004 * (leverage - 1)
    return daily_decay * hold_days


def compute_structural_nodes(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """每日滚动计算宏观策略节点（Add1/DynamicStop/TP1/情景降级）。
    TP1 = ma50 + k4 * ATR14 (兼容模式下，供旧系统和测试使用)
    在 simulate 里默认使用动态自适应的 TP1 (entry_price + k_tp * ATR14)。
    """
    k1 = params.get("k1", 1.0)
    k2 = params.get("k2", 0.2)
    k4 = params.get("k4", params.get("k_tp", 2.5))  # 兼容以前的 k4 与新的 k_tp 参数
    k5 = params.get("k5", 0.5)

    close = df["Close"]
    high  = df["High"]

    ma50  = close.rolling(50).mean().shift(1)
    tr    = pd.concat([
        high - df["Low"],
        (high - close.shift(1)).abs(),
        (df["Low"] - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean().shift(1)

    result = df[["Close", "High", "Low", "Volume"]].copy()
    result["add1"]         = (ma50 + k2 * atr14).round(2)
    result["dynamic_stop"] = (ma50 - k1 * atr14).round(2)
    result["atr14"]        = atr14.round(2)          # 供 simulate 计算动态 TP1
    result["tp1"]          = (ma50 + k4 * atr14).round(2) # 满足 test_compute_structural_nodes_has_required_columns 等测试要求
    result["scenario_b2b"] = (ma50 - k5 * atr14).round(2)
    result["ma50"]         = ma50

    return result



def simulate_structural_trades(df: pd.DataFrame, nodes: pd.DataFrame,
                                slippage: float = 0.001,
                                max_hold_days: int = 60,
                                k_tp: float = 2.5,
                                sym: str = "NVDA") -> list:
    """
    5年日线结构位交易模拟。
    TP1 = 入场价 + k_tp × ATR14（VWAP风格：随波动率自适应的目标距离）
    k_tp 默认 2.5，即盈亏比 = k_tp / k1（k1=1.0时为2.5:1）
    """
    leverage = _get_leverage_factor(sym)
    trades      = []
    in_trade    = False
    entry_price = 0.0
    entry_tp1   = 0.0
    entry_date  = ""
    hold_days   = 0

    for i in range(len(df)):
        row  = df.iloc[i]
        node = nodes.iloc[i]

        if pd.isna(node.get("add1")) or pd.isna(node.get("dynamic_stop")):
            continue

        if in_trade:
            hold_days += 1
            cur_stop = float(node["dynamic_stop"])
            stop_reason = "initial_stop"
            if entry_price > 0:
                pnl_pct = (row["Close"] - entry_price) / entry_price
                if pnl_pct >= 0.15 and not pd.isna(node.get("ma50")):
                    cur_stop = max(cur_stop, float(node["ma50"]))
                    stop_reason = "trail_ma50"
                elif pnl_pct >= 0.08:
                    cur_stop = max(cur_stop, entry_price)
                    stop_reason = "breakeven"

            exit_date = str(df.index[i].date()) if hasattr(df.index[i], 'date') else str(df.index[i])

            # Helper to calculate dynamic costs & decay when trade exits
            def get_final_return(exit_p: float) -> float:
                # Entry Day Gap
                entry_idx = i - hold_days
                entry_row = df.iloc[entry_idx] if entry_idx >= 0 else row
                entry_prev_close = df["Close"].iloc[entry_idx - 1] if entry_idx > 0 else entry_row["Open"]
                entry_gap = abs(entry_row["Open"] - entry_prev_close) / entry_prev_close if entry_prev_close > 0 else 0.0
                
                # Exit Day Gap
                exit_prev_close = df["Close"].iloc[i - 1] if i > 0 else row["Open"]
                exit_gap = abs(row["Open"] - exit_prev_close) / exit_prev_close if exit_prev_close > 0 else 0.0
                
                atr_val = float(node.get("atr14", 0))
                
                entry_slip = compute_dynamic_slippage(sym, entry_price, atr_val, entry_gap, leverage)
                exit_slip = compute_dynamic_slippage(sym, exit_p, atr_val, exit_gap, leverage)
                
                total_slip = entry_slip + exit_slip
                decay = compute_leverage_decay(leverage, hold_days)
                
                raw_ret = (exit_p - entry_price) / entry_price
                return round(raw_ret - total_slip - decay, 4)

            if row["High"] >= entry_tp1:
                ret = get_final_return(entry_tp1)
                trades.append({"return": ret, "outcome": "tp1",
                                "hold_days": hold_days, "entry_price": entry_price,
                                "exit_price": entry_tp1, "exit_date": exit_date,
                                "entry_date": entry_date})
                in_trade = False
            elif row["Low"] <= cur_stop:
                ret = get_final_return(cur_stop)
                trades.append({"return": ret, "outcome": "stop",
                                "hold_days": hold_days, "entry_price": entry_price,
                                "exit_price": cur_stop, "exit_date": exit_date,
                                "stop_reason": stop_reason, "entry_date": entry_date})
                in_trade = False
            elif hold_days >= max_hold_days:
                ret = get_final_return(row["Close"])
                trades.append({"return": ret, "outcome": "time_stop",
                                "hold_days": hold_days, "entry_price": entry_price,
                                "exit_price": row["Close"], "exit_date": exit_date,
                                "entry_date": entry_date})
                in_trade = False
        else:
            add1 = float(node["add1"])
            if row["Low"] <= add1 and add1 > 0:
                # For entry, calculate dynamic slippage to adjust initial entry price
                atr_val = float(node.get("atr14", 0))
                prev_close = df["Close"].iloc[i - 1] if i > 0 else row["Open"]
                gap_pct = abs(row["Open"] - prev_close) / prev_close if prev_close > 0 else 0.0
                entry_slip = compute_dynamic_slippage(sym, add1, atr_val, gap_pct, leverage)
                
                entry_price = add1 * (1 + entry_slip)
                atr14_val  = float(node.get("atr14", 0))
                entry_tp1  = entry_price + k_tp * atr14_val if atr14_val > 0 else entry_price * 1.05
                entry_date = str(df.index[i].date()) if hasattr(df.index[i], 'date') else str(df.index[i])
                hold_days  = 0
                in_trade   = True

    return trades


def scan_structural_params(df: pd.DataFrame,
                            param_grid: dict = None,
                            slippage: float = 0.001,
                            sym: str = "NVDA") -> list:
    """对单只标的日线数据扫描结构位参数。"""
    grid   = param_grid or STRUCTURAL_PARAM_GRID
    keys   = list(grid.keys())
    values = list(grid.values())
    results = []

    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        if params.get("k1", 1.0) < 0.2:
            continue
        if params.get("k4", 1.0) > 1.0:
            continue
        nodes  = compute_structural_nodes(df, params)
        k_tp   = params.get("k_tp", 2.5)
        trades = simulate_structural_trades(df, nodes, slippage=slippage, k_tp=k_tp, sym=sym)
        if not trades:
            continue
        rets    = [t["return"] for t in trades]
        metrics = compute_metrics(rets)
        results.append({"params": params, "metrics": metrics, "n_trades": len(trades)})

    return results


def compute_intraday_signals(df: pd.DataFrame) -> pd.DataFrame:
    """计算5分钟K线的盘中信号：RSI14、VWAP偏离、量比、EMA均线趋势。"""
    result = df.copy()
    close  = df["Close"]
    volume = df["Volume"]

    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    result["rsi14_5m"] = (100 - 100 / (1 + gain / loss.replace(0, 0.001))).round(1)

    try:
        dates = pd.to_datetime(df.index).date
    except Exception:
        dates = df.index.date

    vwap_list = []
    for dt in pd.unique(dates):
        mask    = pd.to_datetime(df.index).date == dt
        sub     = df[mask]
        cum_vol = sub["Volume"].cumsum()
        cum_pv  = (sub["Close"] * sub["Volume"]).cumsum()
        vwap    = cum_pv / cum_vol.replace(0, 1)
        vwap_list.extend(vwap.tolist())

    result["vwap"]     = vwap_list
    result["vwap_dev"] = ((close - result["vwap"]) / result["vwap"] * 100).round(2)
    result["vol_ratio_5m"] = (volume / volume.rolling(20).mean()).round(3)

    # 4. EMA 5分钟日内均线趋势金叉因子 (EMA9 > EMA21)
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    result["ema_trend"] = (ema9 > ema21).astype(int)

    return result


def _in_action_window(ts) -> bool:
    """判断时间戳是否在 10:00-10:30 ET"""
    try:
        et = ts.tz_convert("America/New_York") if hasattr(ts, "tz_convert") else ts
        h, m = et.hour, et.minute
        return h == 10 and 0 <= m < 30
    except Exception:
        return False


def scan_intraday_params(signals: pd.DataFrame, param_grid: dict,
                          add1_price: float, stop_price: float,
                          tp1_price: float, slippage: float = 0.001,
                          sym: str = "NVDA") -> list:
    """60天5分钟数据的盘中信号参数扫描，只检查10:00-10:30 ET窗口。"""
    window_mask = signals.index.map(_in_action_window)
    window_df   = signals[window_mask].copy()

    keys   = list(param_grid.keys())
    values = list(param_grid.values())
    results = []
    
    leverage = _get_leverage_factor(sym)

    for combo in itertools.product(*values):
        params     = dict(zip(keys, combo))
        rsi_thresh = params.get("rsi14_5m_oversold", 35)
        vwap_thr   = params.get("vwap_add_threshold", -1.5)
        vol_thr    = params.get("vol_ratio_shrink", 0.7)
        min_sig    = params.get("min_signals_required", 3)

        trades = []
        for ts, row in window_df.iterrows():
            sigs = sum([
                row.get("rsi14_5m", 50) < rsi_thresh,
                row.get("vwap_dev", 0) < vwap_thr,
                row.get("vol_ratio_5m", 1.0) < vol_thr,
                row.get("ema_trend", 0) == 1,
            ])
            if sigs >= min_sig:
                bar_vol = (row["High"] - row["Low"]) / row["Close"] if row["Close"] > 0 else 0.005
                entry_slip = min(max(0.0005, (0.0003 + bar_vol * 0.1) * leverage), 0.01)
                
                ep = row["Close"] * (1 + entry_slip)
                
                # Find subsequent bars in same day to determine actual outcome
                ts_date = pd.to_datetime(ts).date()
                same_day = signals[pd.to_datetime(signals.index).date == ts_date]
                # Only look at bars AFTER the signal bar
                future_bars = same_day[same_day.index > ts]

                outcome = "hold"
                ret = 0.0
                for _, fb in future_bars.iterrows():
                    fb_vol = (fb["High"] - fb["Low"]) / fb["Close"] if fb["Close"] > 0 else 0.005
                    exit_slip = min(max(0.0005, (0.0003 + fb_vol * 0.1) * leverage), 0.01)
                    
                    if fb.get("High", 0) >= tp1_price:
                        ret = (tp1_price * (1 - exit_slip) - ep) / ep
                        outcome = "tp1"
                        break
                    elif fb.get("Low", 0) <= stop_price:
                        ret = (stop_price * (1 - exit_slip) - ep) / ep
                        outcome = "stop"
                        break
                else:
                    # End of day without hitting tp1 or stop - use closing price
                    if not future_bars.empty:
                        last_bar = future_bars.iloc[-1]
                        last_vol = (last_bar["High"] - last_bar["Low"]) / last_bar["Close"] if last_bar["Close"] > 0 else 0.005
                        exit_slip = min(max(0.0005, (0.0003 + last_vol * 0.1) * leverage), 0.01)
                        ret = (last_bar["Close"] * (1 - exit_slip) - ep) / ep
                        outcome = "eod"

                trades.append({"return": round(ret, 4), "outcome": outcome})

        rets    = [t["return"] for t in trades] if trades else []
        metrics = compute_metrics(rets)
        results.append({"params": params, "metrics": metrics, "n_trades": len(trades)})

    return results


def run_micro_backtest(syms: list = None, years: int = 5) -> dict:
    """运行结构位回测（5年日线，所有持仓各自优化k值）。
    每只标的的完整交易记录单独保存到 findings/backtest_trades_{sym}.json。
    """
    syms = syms or HOLDINGS
    out  = {}
    for sym in syms:
        print(f"[micro_backtest] 结构位回测: {sym}...")
        df = _fetch_ohlcv(sym, years=years)
        if df.empty:
            continue

        split    = int(len(df) * 0.8)
        train_df = df.iloc[:split]
        val_df   = df.iloc[split:]

        results = scan_structural_params(train_df, sym=sym)
        valid   = [r for r in results
                   if _passes_thresholds(r["metrics"]) and
                      _passes_master_constraints(r["params"], r["metrics"])]
        best = max(valid, key=lambda r: r["metrics"]["ev"]) if valid else None

        if best:
            k_tp       = best["params"].get("k_tp", 2.5)
            val_nodes  = compute_structural_nodes(val_df, best["params"])
            val_trades = simulate_structural_trades(val_df, val_nodes, k_tp=k_tp, sym=sym)
            val_m      = compute_metrics([t["return"] for t in val_trades])
            train_wr   = best["metrics"].get("win_rate", 0)
            val_wr     = val_m.get("win_rate", 0)
            if train_wr and val_wr and train_wr - val_wr > 0.15:
                print(f"  ⚠️ {sym} 过拟合：训练{train_wr:.1%} vs 验证{val_wr:.1%}")
            best["oos_metrics"] = val_m

            # 保存完整交易记录（按标的独立文件，方便 review 和 debug）
            trades_path = os.path.join(BASE, "findings", f"backtest_trades_{sym}.json")
            trade_log = {
                "sym":          sym,
                "run_date":     str(_date.today()),
                "best_params":  best["params"],
                "train_metrics": best["metrics"],
                "oos_metrics":  val_m,
                "oos_trades":   val_trades,      # 验证集完整逐笔记录
            }
            os.makedirs(os.path.join(BASE, "findings"), exist_ok=True)
            with open(trades_path, "w", encoding="utf-8") as f:
                json.dump(trade_log, f, ensure_ascii=False, indent=2)
            print(f"  → {sym}: k1={best['params'].get('k1')} k_tp={k_tp} EV={best['metrics'].get('ev')} | 交易记录: {trades_path}")
        else:
            print(f"  → {sym}: 无满足门槛的参数组合")

        out[sym] = {"best_params": best, "n_candidates": len(results),
                    "n_valid": len(valid)}

    return {"structural": out, "run_date": str(_date.today())}


def run_intraday_backtest(syms: list = None, window_days: int = 60) -> dict:
    """运行盘中信号回测（60天5分钟数据，全局参数优化）。"""
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

        macro_path = os.path.join(BASE, f"macro_strategy_{sym.upper()}.json")
        macro = {}
        if os.path.exists(macro_path):
            try:
                macro = json.load(open(macro_path, encoding="utf-8"))
            except Exception:
                pass

        add1_p = (macro.get("nodes", {}).get("add1") or {}).get("price", 0)
        stop_p = (macro.get("nodes", {}).get("dynamic_stop") or {}).get("price", 0)
        tp1_p  = (macro.get("nodes", {}).get("tp1") or {}).get("price", 0)
        if not (add1_p and stop_p and tp1_p):
            print(f"  → {sym}: 无节点数据，跳过")
            continue

        signals = compute_intraday_signals(df5m)
        results = scan_intraday_params(signals, INTRADAY_PARAM_GRID,
                                       add1_price=add1_p, stop_price=stop_p,
                                       tp1_price=tp1_p, sym=sym)
        all_results.extend(results)

    from collections import defaultdict
    grouped = defaultdict(list)
    for r in all_results:
        key = tuple(sorted(r["params"].items()))
        grouped[key].append(r["metrics"])

    best_global = None
    best_ev     = -999.0
    for key, metrics_list in grouped.items():
        valid_evs = [m["ev"] for m in metrics_list if m.get("ev") is not None]
        if not valid_evs:
            continue
        avg_ev = sum(valid_evs) / len(valid_evs)
        if avg_ev > best_ev:
            best_ev     = avg_ev
            best_global = dict(key)

    return {"best_global_params": best_global, "best_ev": best_ev,
            "run_date": str(_date.today()), "window_days": window_days}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--structural",  action="store_true")
    parser.add_argument("--intraday",    action="store_true")
    parser.add_argument("--years",       type=int, default=5)
    parser.add_argument("--window-days", type=int, default=60, dest="window_days")
    parser.add_argument("--sym",         nargs="*", default=None)
    args = parser.parse_args()

    if args.structural or not args.intraday:
        out = run_micro_backtest(syms=args.sym, years=args.years)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.intraday:
        out = run_intraday_backtest(syms=args.sym, window_days=args.window_days)
        print(json.dumps(out, ensure_ascii=False, indent=2))
