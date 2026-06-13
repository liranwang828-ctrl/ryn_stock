import os
import sys
import json
import numpy as np
import pandas as pd

# Ensure UTF-8 Console Printing on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to sys.path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.weekly_rebalance_engine import WeeklyRebalanceEngine

# Out-of-sample Ticker Pools (Core 50 tickers)
TICKERS_50 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX', 
    'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'JPM', 'BAC', 'MS', 'GS', 'V', 
    'MA', 'AXP', 'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'TSLA', 
    'HD', 'MCD', 'NKE', 'SBUX', 'WMT', 'COST', 'KO', 'PEP', 'PG', 'GE', 
    'CAT', 'HON', 'LMT', 'BA', 'XOM', 'CVX', 'COP', 'FCX', 'NEE', 'AMT'
]

def main():
    print("==========================================================================")
    print("🧪 [机构级压力测试 1 & 2] 交易滑点摩擦与执行延迟时间窗多维联合扫频")
    print("==========================================================================")

    # Load best parameter set from best_weekly_params.json
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "best_weekly_params.json")
    if not os.path.exists(config_path):
        config_path = r"d:\gemini\lianghua\stock_team\config\best_weekly_params.json"
        
    if not os.path.exists(config_path):
        print("🔴 错误：找不到最优参数配置文件 best_weekly_params.json。")
        sys.exit(1)
        
    with open(config_path, "r", encoding="utf-8") as f:
        best_params = json.load(f)
        
    gap = best_params["monday_gap_threshold"]
    profit = best_params["breathing_profit_threshold"]
    hwm = best_params["hwm_stop_loss_pct"]
    
    # 1. Load data once to avoid repeated disk I/O in loop
    print("📡 正在预载 5年全生命周期 50只标的数据...")
    base_engine = WeeklyRebalanceEngine(
        tickers=TICKERS_50,
        verbose=False,
        monday_gap_threshold=gap,
        breathing_profit_threshold=profit,
        hwm_stop_loss_pct=hwm
    )
    base_engine.load_all_data()
    
    # Pre-split dates
    for t in base_engine.intraday_data:
        df = base_engine.intraday_data[t]
        if isinstance(df, pd.DataFrame):
            base_engine.intraday_data[t] = {d: grp for d, grp in df.groupby(df.index.date)}

    # Sweep parameters
    # Slippages: 0.05% (baseline), 0.10%, 0.20%, 0.50%
    # Waterfall decay on stops: HWM stop slippage (0.5% standard to 1.5% extreme), Waterfall stop slippage (1.5% to 3.0% extreme)
    slippage_scenarios = [
        {"name": "基准滑点 (0.05%)", "slip": 0.0005, "hwm_slip": 0.005, "waterfall_slip": 0.015},
        {"name": "温和滑点 (0.10%)", "slip": 0.0010, "hwm_slip": 0.008, "waterfall_slip": 0.018},
        {"name": "恶劣滑点 (0.20%)", "slip": 0.0020, "hwm_slip": 0.012, "waterfall_slip": 0.022},
        {"name": "流动性冰封 (0.50%)", "slip": 0.0050, "hwm_slip": 0.020, "waterfall_slip": 0.040}
    ]
    
    # Latencies: 0m, 5m, 15m, 30m, 60m
    latency_scenarios = [0, 5, 15, 30, 60]
    
    results = []

    print("\n🚀 开始联合扫描...")
    for slip_scen in slippage_scenarios:
        for lat in latency_scenarios:
            # Instantiate engine with preloaded data
            engine = WeeklyRebalanceEngine(
                tickers=TICKERS_50,
                verbose=False,
                monday_gap_threshold=gap,
                breathing_profit_threshold=profit,
                hwm_stop_loss_pct=hwm,
                custom_slippage_rate=slip_scen["slip"],
                hwm_slippage_rate=slip_scen["hwm_slip"],
                waterfall_slippage_rate=slip_scen["waterfall_slip"],
                latency_minutes=lat
            )
            
            # Share loaded datasets
            engine.daily_data = base_engine.daily_data
            engine.intraday_data = base_engine.intraday_data
            engine.qqq_daily = base_engine.qqq_daily
            engine.vix_daily = base_engine.vix_daily
            
            m = engine.run_backtest(start_date_str="2021-06-01", end_date_str="2026-05-30", K=5)
            
            results.append({
                "scenario_name": slip_scen["name"],
                "slippage": slip_scen["slip"],
                "latency_minutes": lat,
                "total_return": m["total_return_pct"],
                "mdd": m["max_drawdown_pct"],
                "sharpe": m["sharpe_ratio"],
                "sortino": m["sortino_ratio"],
                "profit_factor": m["profit_factor"],
                "trades_count": m["trades_count"]
            })
            
            print(f"   ↳ ✅ [Slippage: {slip_scen['slip']*100:.2f}% | Latency: {lat:2d}m] -> 收益: {m['total_return_pct']:>+7.2f}% | 回撤: {m['max_drawdown_pct']:.2f}% | Sortino: {m['sortino_ratio']:.2f}")

    # Display breathtaking Sweep Matrix Dashboard
    print("\n" + "=" * 120)
    print("               🏆 周频截面轮动引擎 —— 交易滑点摩擦与执行延迟时间窗多维联合扫频看板")
    print("=" * 120)
    print(f"{'交易滑点测试场景':<22} | {'延迟执行':<8} | {'累计总收益':<10} | {'最大回撤':<9} | {'年化夏普':<8} | {'年化索提诺':<9} | {'获利因子':<8} | {'总交易笔数'}")
    print("-" * 120)
    
    for r in results:
        print(f"{r['scenario_name']:<22} | "
              f"{r['latency_minutes']:>6d}m | "
              f"{r['total_return']:>+9.2f}% | "
              f"{r['mdd']:>8.2f}% | "
              f"{r['sharpe']:>8.2f} | "
              f"{r['sortino']:>9.2f} | "
              f"{r['profit_factor']:>8.2f} | "
              f"{r['trades_count']:>10d}")
    print("=" * 120 + "\n")

    # Deep Quant Insights
    print("💡 联合扫频深度投研报告与衰变判定：")
    
    # Analyze Latency damage at standard slippage
    lat_0 = [x for x in results if x["slippage"] == 0.0005 and x["latency_minutes"] == 0][0]
    lat_30 = [x for x in results if x["slippage"] == 0.0005 and x["latency_minutes"] == 30][0]
    lat_60 = [x for x in results if x["slippage"] == 0.0005 and x["latency_minutes"] == 60][0]
    
    loss_30m = lat_0["total_return"] - lat_30["total_return"]
    loss_60m = lat_0["total_return"] - lat_60["total_return"]
    
    print(f"   1. ⏰ 【延迟建仓敏感度】：")
    print(f"      - 顶格秒级建仓 (0m 延迟) 累计收益为 {lat_0['total_return']:+.2f}%。")
    print(f"      - 延迟 30分钟 建仓 (9:45 进场) 累计收益为 {lat_30['total_return']:+.2f}% (衰退损耗: {loss_30m:+.2f}%)。")
    print(f"      - 延迟 1小时 建仓 (10:00 进场) 累计收益为 {lat_60['total_return']:+.2f}% (衰退损耗: {loss_60m:+.2f}%)。")
    if abs(loss_30m) < 8.0:
        print(f"      - 【判定】：延迟30分钟建仓收益损耗极其轻微，表明策略对“瞬时执行精度”高度脱敏，容错率极强，具备完美的实盘承载力！")
    else:
        print(f"      - 【判定】：延迟建仓产生明显阿法衰退，实盘需严控下单响应。")

    # Analyze Slippage breakdown point at 0m latency
    slip_05 = [x for x in results if x["slippage"] == 0.0005 and x["latency_minutes"] == 0][0]
    slip_20 = [x for x in results if x["slippage"] == 0.0020 and x["latency_minutes"] == 0][0]
    slip_50 = [x for x in results if x["slippage"] == 0.0050 and x["latency_minutes"] == 0][0]
    
    print(f"   2. 🚨 【滑点摩擦耐受极限】：")
    print(f"      - 正常基准滑点 (0.05%) 累计收益为 {slip_05['total_return']:+.2f}%，Sortino: {slip_05['sortino']:.2f}。")
    print(f"      - 恶劣重度滑点 (0.20% + 止损罚金) 累计收益为 {slip_20['total_return']:+.2f}%，Sortino: {slip_20['sortino']:.2f}。")
    print(f"      - 极端枯竭滑点 (0.50% + 瀑布扣减) 累计收益为 {slip_50['total_return']:+.2f}%，Sortino: {slip_50['sortino']:.2f}。")
    
    if slip_20["sortino"] > 1.0:
        print(f"      - 【判定】：策略在 0.20% 恶劣滑点摩擦下 Sortino 仍大于 1.0 (录得 {slip_20['sortino']:.2f})，完美通过机构级滑点大测，具备极强的实盘防爆抗性！")
    else:
        print(f"      - 【判定】：策略在重度摩擦下收益衰退较快，需使用高阶限价单或 MOO 订单控制执行。")

    # Save to findings for walkthrough integration
    findings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "findings")
    out_path = os.path.join(findings_dir, "slippage_latency_sweep_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 联合扫频数据分析包已归档入库：{out_path}\n")

if __name__ == "__main__":
    main()
