import os
import sys
import pandas as pd
import numpy as np

# Ensure Parent Directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from stock_team.backtest.weekly_rebalance_engine import WeeklyRebalanceEngine

TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX', 
    'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'JPM', 'BAC', 'MS', 'GS', 'V', 
    'MA', 'AXP', 'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'TSLA', 
    'HD', 'MCD', 'NKE', 'SBUX', 'WMT', 'COST', 'KO', 'PEP', 'PG', 'GE', 
    'CAT', 'HON', 'LMT', 'BA', 'XOM', 'CVX', 'COP', 'FCX', 'NEE', 'AMT'
]

def main():
    print("=" * 80)
    print("🔬 启动周频轮动引擎『大风控开关消融实验 (Risk Guard Ablation study)』")
    print("=" * 80)
    print("我们将对比以下 4 种风险开关组合，判定『收益/胜率提升 vs 回撤降低』的边际比重：")
    print("  1. 基准全开组 (A): 宽止损回归保护(MA50/VIX) + 周一黑天鹅跳空防御")
    print("  2. 宽止损裸奔组 (B): 废除宽止损回归保护 (利润>20%无脑放宽止损，无大盘与VIX安全网)")
    print("  3. 黑天鹅裸奔组 (C): 废除周一黑天鹅跳空防御")
    print("  4. 双重裸奔组 (D): 废除全部两项风险卫士")
    print("=" * 80 + "\n")
    
    configs = [
        {"name": "A. 基准全开组 (Full Guards)", "stop_guard": True, "gap_guard": True},
        {"name": "B. 宽止损无保护组 (No Stop Guard)", "stop_guard": False, "gap_guard": True},
        {"name": "C. 黑天鹅无保护组 (No Gap Guard)", "stop_guard": True, "gap_guard": False},
        {"name": "D. 双重无保护裸奔组 (No Guards)", "stop_guard": False, "gap_guard": False}
    ]
    
    results = []
    
    for c in configs:
        print(f"📡 正在跑测: {c['name']} (请稍候)...")
        engine = WeeklyRebalanceEngine(
            TICKERS, 
            verbose=False,
            use_breathing_stop_guard=c["stop_guard"],
            use_monday_gap_guard=c["gap_guard"]
        )
        try:
            m = engine.run_backtest(K=5)
            results.append({
                "Configuration": c["name"],
                "Total Return": f"+{m['total_return_pct']:.2f}%",
                "Max Drawdown": f"{m['max_drawdown_pct']:.2f}%",
                "Win Rate": f"{m['win_rate_pct']:.1f}%",
                "Trades": m["trades_count"],
                "Sharpe": f"{m['sharpe_ratio']:.2f}",
                "Sortino": f"{m['sortino_ratio']:.2f}",
                "Calmar": f"{m['calmar_ratio']:.2f}"
            })
            print(f"   ✅ 完成！收益率: {m['total_return_pct']:+.2f}% | 最大回撤: {m['max_drawdown_pct']:.2f}% | 交易: {m['trades_count']}次")
        except Exception as e:
            print(f"   ❌ 跑测失败: {e}")
            
    df = pd.DataFrame(results)
    
    print("\n" + "=" * 100)
    print("                  🏆 周频截面轮动引擎大风控开关消融实验对比看板")
    print("=" * 100)
    print(df.to_string(index=False))
    print("=" * 100 + "\n")
    
    print("💡 决策大诊断指引：")
    print("1. 对比 A 组 与 B 组：检查『宽止损回归保护』是否成功在 2022 熊市或高位剧震中锁住了利润。")
    print("2. 对比 A 组 与 C 组：检查『周一跳空开盘防御』是否有效规避了周末黑天鹅『建仓即吃暴跌』的损失。")
    print("3. 若某项无保护组相比基准组，回撤仅变差 1-2%，但收益/胜率出现大幅萎缩，则代表该项保护为『过度约束』，应予以舍弃；反之，若回撤大幅改善，则证明其高价值，应当正式纳入。")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()
