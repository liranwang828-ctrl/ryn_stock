import sys
import os
import json
import pandas as pd
import numpy as np

# Ensure UTF-8 Console Printing
sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to sys.path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.joint_backtest_engine import run_joint_backtest

def main():
    tickers = ["ARM", "NVDA", "SNOW", "AMD", "COHR", "VST", "SYM", "AVGO", "MRVL", "ANET", "CSCO", "LITE", "MU", "TSM", "VRT"]
    
    print("==================================================")
    print("🔮 联合策略20轮网格自主寻优扫描器启动")
    print(f"   • 标的池 (15只AI龙头): {tickers}")
    print("   • 非参数化原则（Barbell, Sizing, Slippage）将严格保持硬编码")
    print("==================================================")
    
    # 20-Round Grid Sweep Ranges (5 VC levels x 4 ATR stop multipliers = 20 rounds)
    vc_list = [15.0, 20.0, 25.0, 30.0, 35.0]
    atr_list = [1.2, 1.5, 1.8, 2.1]
    
    sweep_results = []
    round_count = 1
    total_rounds = len(vc_list) * len(atr_list)
    
    print(f"⏱️ 开始遍历 {total_rounds} 组参数网络进行深度多标的模拟...\n")
    
    for vc in vc_list:
        for atr in atr_list:
            print(f"🌀 [第 {round_count}/{total_rounds} 轮] 正在跑测：VC = {vc:.1f}%, ATR = {atr:.1f} ...")
            
            # Construct dynamic rules injection dictionary
            temp_rules = {
                "methodology_14_high_beta_gap": {
                    "vc_threshold_pct": vc,
                    "bracket_stop_loss_pct": 1.5,
                    "t1_size_pct": 30.0,
                    "t2_t3_size_pct": 70.0
                },
                "methodology_15_low_catalyst_rs": {
                    "vc_threshold_pct": vc,
                    "bracket_stop_loss_pct": 0.5,
                    "atr_stop_multiplier": atr,
                    "t1_size_pct": 30.0,
                    "t2_t3_size_pct": 70.0,
                    "nvda_exit_trigger": True
                }
            }
            
            # Run the actual high-frequency joint backtest engine in silent mode (verbose=False)
            try:
                metrics = run_joint_backtest(tickers, days=90, custom_rules=temp_rules, verbose=False)
                
                sweep_results.append({
                    "Round": round_count,
                    "VC_Threshold%": vc,
                    "ATR_Multiplier": atr,
                    "Total_Return%": metrics["total_return_pct"],
                    "Max_Drawdown%": metrics["max_drawdown_pct"],
                    "Sharpe": metrics["sharpe_ratio"],
                    "Sortino": metrics["sortino_ratio"],
                    "Calmar": metrics["calmar_ratio"],
                    "Win_Rate%": metrics["win_rate_pct"],
                    "Profit_Factor": metrics["profit_factor"],
                    "Payoff_Ratio": metrics["payoff_ratio"],
                    "Trades": metrics["trades_count"]
                })
                
                print(f"   ↳ ✅ PnL: {metrics['total_return_pct']:+.2f}% | MDD: {metrics['max_drawdown_pct']:.2f}% | Sortino: {metrics['sortino_ratio']:.2f} | WinRate: {metrics['win_rate_pct']:.1f}% | PF: {metrics['profit_factor']:.2f}")
            except Exception as e:
                print(f"   ↳ 🔴 运行失败: {e}")
                
            round_count += 1
            
    if not sweep_results:
        print("🔴 所有寻优轮次均失败，无法进行参数更新。")
        sys.exit(1)
        
    # Convert results to DataFrame for analysis and sorting
    results_df = pd.DataFrame(sweep_results)
    
    # Locate the best parameter combination based on Sortino Ratio
    # If Sortino is comparable, sort by Profit Factor and Win Rate
    sorted_df = results_df.sort_values(by=["Sortino", "Profit_Factor", "Win_Rate%"], ascending=[False, False, False])
    best_row = sorted_df.iloc[0]
    
    # Load current tactical rules to preserve other static configs
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "tactical_rules.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            current_rules = json.load(f)
    else:
        current_rules = {}
        
    # Update only the parameterized optimization values
    if "methodology_14_high_beta_gap" not in current_rules:
        current_rules["methodology_14_high_beta_gap"] = {}
    if "methodology_15_low_catalyst_rs" not in current_rules:
        current_rules["methodology_15_low_catalyst_rs"] = {}
        
    current_rules["methodology_14_high_beta_gap"]["vc_threshold_pct"] = float(best_row["VC_Threshold%"])
    current_rules["methodology_15_low_catalyst_rs"]["vc_threshold_pct"] = float(best_row["VC_Threshold%"])
    current_rules["methodology_15_low_catalyst_rs"]["atr_stop_multiplier"] = float(best_row["ATR_Multiplier"])
    
    # Save the optimized rules back to JSON config
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(current_rules, f, indent=2, ensure_ascii=False)
        
    # Generate Breathtaking ASCII Matrix Report
    print(f"\n==========================================================================================")
    print(f"                   🎯 15只AI龙头高频量化网格寻优矩阵 (Sorted by Sortino Ratio)")
    print(f"==========================================================================================")
    print(sorted_df.to_string(index=False, formatters={
        "VC_Threshold%": "{:.1f}%".format,
        "ATR_Multiplier": "{:.1f}".format,
        "Total_Return%": "{:+.2f}%".format,
        "Max_Drawdown%": "{:.2f}%".format,
        "Sharpe": "{:.2f}".format,
        "Sortino": "{:.2f}".format,
        "Calmar": "{:.2f}".format,
        "Win_Rate%": "{:.1f}%".format,
        "Profit_Factor": "{:.2f}".format,
        "Payoff_Ratio": "{:.2f}".format
    }))
    print(f"==========================================================================================")
    
    print(f"\n[🏆 寻优决断：全球下行风险最优解 (Global Downside-Risk Optimum)]")
    print(f"   • 最优 Volume Contraction 阈值 : {best_row['VC_Threshold%']:.1f}%")
    print(f"   • 最优 ATR 动态止损系数         : {best_row['ATR_Multiplier']:.1f}")
    print(f"   • 对应策略累计收益率           : {best_row['Total_Return%']:+.2f}%")
    print(f"   • 对应策略最大回撤             : {best_row['Max_Drawdown%']:.2f}%")
    print(f"   • 对应年化夏普比率 (Sharpe)    : {best_row['Sharpe']:.2f}")
    print(f"   • 对应下行索提诺比率 (Sortino)   : {best_row['Sortino']:.2f} (最优性能指标)")
    print(f"   • 最终期望获利因子 (PF)        : {best_row['Profit_Factor']:.2f}")
    print(f"   • 最终期望胜率 (Win Rate)      : {best_row['Win_Rate%']:.1f}%")
    
    print(f"\n💡 [系统自动集成成功] 最优寻优参数已成功写入配置文件: config/tactical_rules.json")
    print(f"   >>> 量化收缩阈值 (VC) 已锁定为: {best_row['VC_Threshold%']:.1f}%")
    print(f"   >>> 动态止损系数 (ATR) 已锁定为: {best_row['ATR_Multiplier']:.1f}")
    print(f"   >>> 即日起单兵狙击 .\\sniper 进行实战将全自动运用这套黄金调优参数！")
    print(f"==========================================================================================\n")
    
    # Save the optimization matrix to findings
    findings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "findings")
    os.makedirs(findings_dir, exist_ok=True)
    sweep_path = os.path.join(findings_dir, "parameter_sweep_matrix.json")
    sorted_df.to_json(sweep_path, orient="records", indent=2)
    print(f"💾 完整调优网格矩阵已安全归档至: findings/parameter_sweep_matrix.json\n")

if __name__ == "__main__":
    main()
