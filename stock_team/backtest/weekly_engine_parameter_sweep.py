import os
import sys
import json
import numpy as np
import pandas as pd

# Ensure UTF-8 Console Printing
sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to sys.path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.weekly_rebalance_engine import WeeklyRebalanceEngine

# Default 50 Tickers for high-fidelity sweep
TICKERS_50 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX', 
    'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'JPM', 'BAC', 'MS', 'GS', 'V', 
    'MA', 'AXP', 'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'TSLA', 
    'HD', 'MCD', 'NKE', 'SBUX', 'WMT', 'COST', 'KO', 'PEP', 'PG', 'GE', 
    'CAT', 'HON', 'LMT', 'BA', 'XOM', 'CVX', 'COP', 'FCX', 'NEE', 'AMT'
]

def main():
    print("==================================================")
    print("🔮 周频截面轮动引擎参数敏感性与“参数高原”寻优器启动")
    print("==================================================")
    
    # 1. Preload all daily and intraday data to avoid massive I/O bottleneck
    print("📡 正在预载 50 只成分股行情与 5分钟日内数据至内存中...")
    
    # We initialize a mock engine to leverage its load_all_data logic
    preload_engine = WeeklyRebalanceEngine(TICKERS_50, verbose=True)
    preload_engine.load_all_data()
    
    # Extract preloaded datasets
    preloaded_daily = preload_engine.daily_data
    preloaded_intraday = preload_engine.intraday_data
    preloaded_qqq = preload_engine.qqq_daily
    preloaded_vix = preload_engine.vix_daily
    
    print(f"✅ 数据预载完成：{len(preloaded_daily)} 只股票日线数据，{len(preloaded_intraday)} 只股票日内数据已驻留内存。")
    
    # 2. Define Parameter Grid Ranges
    # monday_gap_threshold: [-2.0%, -2.5%, -3.0%, -3.5%, -4.0%]
    # breathing_profit_threshold: [10.0%, 15.0%, 20.0%, 25.0%]
    # hwm_stop_loss_pct: [8.0%, 10.0%, 12.0%, 15.0%]
    gap_grid = [-0.02, -0.025, -0.03, -0.035, -0.04]
    profit_grid = [10.0, 15.0, 20.0, 25.0]
    hwm_grid = [0.08, 0.10, 0.12, 0.15]
    
    sweep_results = []
    round_count = 1
    total_rounds = len(gap_grid) * len(profit_grid) * len(hwm_grid)
    
    print(f"\n⏱️ 开始网格扫描，总计 {total_rounds} 组参数组合...")
    
    # We will store results in a 3D grid layout to perform neighborhood analysis
    # Grid coordinates mapping
    results_grid = np.zeros((len(gap_grid), len(profit_grid), len(hwm_grid)), dtype=object)
    
    for g_idx, gap in enumerate(gap_grid):
        for p_idx, profit in enumerate(profit_grid):
            for h_idx, hwm in enumerate(hwm_grid):
                print(f"🌀 [第 {round_count}/{total_rounds} 轮] 正在跑测：Monday Gap = {gap*100:.1f}%, Profit Stop Trigger = {profit:.1f}%, HWM Stop = {hwm*100:.1f}%")
                
                # Initialize engine instance (verbose=False)
                engine = WeeklyRebalanceEngine(
                    tickers=TICKERS_50,
                    verbose=False,
                    monday_gap_threshold=gap,
                    breathing_profit_threshold=profit,
                    hwm_stop_loss_pct=hwm
                )
                
                # Assign preloaded data directly to avoid disk reading
                engine.daily_data = preloaded_daily
                engine.intraday_data = preloaded_intraday
                engine.qqq_daily = preloaded_qqq
                engine.vix_daily = preloaded_vix
                
                try:
                    # Run the backtest (K=5)
                    metrics = engine.run_backtest(K=5)
                    
                    res_dict = {
                        "gap_threshold": gap,
                        "profit_threshold": profit,
                        "hwm_stop": hwm,
                        "total_return": metrics["total_return_pct"],
                        "max_drawdown": metrics["max_drawdown_pct"],
                        "sharpe": metrics["sharpe_ratio"],
                        "sortino": metrics["sortino_ratio"],
                        "calmar": metrics["calmar_ratio"],
                        "win_rate": metrics["win_rate_pct"],
                        "profit_factor": metrics["profit_factor"],
                        "trades_count": metrics["trades_count"],
                        "g_idx": g_idx,
                        "p_idx": p_idx,
                        "h_idx": h_idx
                    }
                    
                    sweep_results.append(res_dict)
                    results_grid[g_idx, p_idx, h_idx] = res_dict
                    
                    print(f"   ↳ ✅ 收益率: {metrics['total_return_pct']:+.2f}% | 最大回撤: {metrics['max_drawdown_pct']:.2f}% | Sortino: {metrics['sortino_ratio']:.2f} | 交易次数: {metrics['trades_count']}")
                except Exception as e:
                    print(f"   ↳ 🔴 运行失败: {e}")
                
                round_count += 1
                
    if not sweep_results:
        print("🔴 所有参数寻优轮次均失败，无法进行参数更新。")
        sys.exit(1)
        
    df_results = pd.DataFrame(sweep_results)
    
    # 3. Parameter Plateau Center Location (Neighborhood Stability Analysis)
    # For each cell, we define its neighborhood as cells within index distance of 1.
    # We find the cell with the highest average neighborhood Sortino ratio.
    plateau_results = []
    
    for res in sweep_results:
        g = res["g_idx"]
        p = res["p_idx"]
        h = res["h_idx"]
        
        neighbor_sortinos = []
        neighbor_drawdowns = []
        
        # Look in the 3x3x3 cube around the cell
        for dg in [-1, 0, 1]:
            for dp in [-1, 0, 1]:
                for dh in [-1, 0, 1]:
                    ng = g + dg
                    np_val = p + dp
                    nh = h + dh
                    
                    # Boundary check
                    if 0 <= ng < len(gap_grid) and 0 <= np_val < len(profit_grid) and 0 <= nh < len(hwm_grid):
                        neighbor = results_grid[ng, np_val, nh]
                        if neighbor:
                            neighbor_sortinos.append(neighbor["sortino"])
                            neighbor_drawdowns.append(neighbor["max_drawdown"])
                            
        # Average neighborhood stats
        avg_n_sortino = np.mean(neighbor_sortinos)
        avg_n_drawdown = np.mean(neighbor_drawdowns)
        
        res["neighborhood_avg_sortino"] = avg_n_sortino
        res["neighborhood_avg_drawdown"] = avg_n_drawdown
        plateau_results.append(res)
        
    df_plateau = pd.DataFrame(plateau_results)
    
    # Sort primarily by neighborhood average Sortino, then by cell Sortino
    df_sorted = df_plateau.sort_values(
        by=["neighborhood_avg_sortino", "sortino", "max_drawdown"],
        ascending=[False, False, False]
    )
    
    best_row = df_sorted.iloc[0]
    
    # Output parameter plateau report
    print("\n" + "=" * 100)
    print("                  🏆 周频截面轮动引擎 —— 三维参数高原寻优前 20 强看板")
    print("=" * 100)
    print(df_sorted.head(20).to_string(index=False, columns=[
        "gap_threshold", "profit_threshold", "hwm_stop", "total_return", 
        "max_drawdown", "sortino", "sharpe", "neighborhood_avg_sortino", 
        "neighborhood_avg_drawdown", "trades_count"
    ], formatters={
        "gap_threshold": "{:+.1%}".format,
        "profit_threshold": "{:.1f}%".format,
        "hwm_stop": "{:.1%}".format,
        "total_return": "{:+.2f}%".format,
        "max_drawdown": "{:.2f}%".format,
        "sortino": "{:.2f}".format,
        "sharpe": "{:.2f}".format,
        "neighborhood_avg_sortino": "{:.2f}".format,
        "neighborhood_avg_drawdown": "{:.2f}%".format
    }))
    print("=" * 100 + "\n")
    
    print(f"🎯 [参数高原中心决策 (Plateau Center Resolution)]")
    print(f"   • 最优 Monday Gap 阈值      : {best_row['gap_threshold']*100:+.1f}%")
    print(f"   • 最优盈利止损松绑阈值       : {best_row['profit_threshold']:.1f}%")
    print(f"   • 最优基准 HWM 移动止损比例 : {best_row['hwm_stop']*100:.1f}%")
    print(f"   • 本身点位 Sortino / 收益   : {best_row['sortino']:.2f} / {best_row['total_return']:+.2f}%")
    print(f"   • 本身点位最大回撤           : {best_row['max_drawdown']:.2f}%")
    print(f"   • 高原邻域平均 Sortino      : {best_row['neighborhood_avg_sortino']:.2f} (极具泛化性的钝感钝角！)")
    print(f"   • 高原邻域平均最大回撤       : {best_row['neighborhood_avg_drawdown']:.2f}%")
    
    # 4. Save optimized params to best_weekly_params.json
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    os.makedirs(config_dir, exist_ok=True)
    best_config_path = os.path.join(config_dir, "best_weekly_params.json")
    
    config_data = {
        "monday_gap_threshold": float(best_row["gap_threshold"]),
        "breathing_profit_threshold": float(best_row["profit_threshold"]),
        "hwm_stop_loss_pct": float(best_row["hwm_stop"]),
        "optimized_metrics": {
            "total_return_pct": float(best_row["total_return"]),
            "max_drawdown_pct": float(best_row["max_drawdown"]),
            "sortino": float(best_row["sortino"]),
            "sharpe": float(best_row["sharpe"]),
            "neighborhood_avg_sortino": float(best_row["neighborhood_avg_sortino"])
        }
    }
    
    with open(best_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n💾 最优“参数高原”配置已成功写入物理磁盘：{best_config_path}")
    
    # 5. Archive full grid results
    findings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "findings")
    os.makedirs(findings_dir, exist_ok=True)
    matrix_path = os.path.join(findings_dir, "weekly_parameter_sweep_matrix.json")
    df_sorted.to_json(matrix_path, orient="records", indent=2)
    print(f"💾 全量网格寻优多维数据矩阵已安全归档：{matrix_path}\n")

if __name__ == "__main__":
    main()
