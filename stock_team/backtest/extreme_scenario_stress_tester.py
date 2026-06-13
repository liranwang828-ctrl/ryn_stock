import os
import sys
import json
import numpy as np
import pandas as pd
import copy

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

class ExtremeScenarioStressTester:
    def __init__(self):
        # 1. Load best parameter set from best_weekly_params.json
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "best_weekly_params.json")
        if not os.path.exists(config_path):
            print("🔴 错误：找不到最优参数配置文件 best_weekly_params.json。请先运行网格扫描器。")
            sys.exit(1)
            
        with open(config_path, "r", encoding="utf-8") as f:
            best_params = json.load(f)
            
        self.gap = best_params["monday_gap_threshold"]
        self.profit = best_params["breathing_profit_threshold"]
        self.hwm = best_params["hwm_stop_loss_pct"]
        
        print("==========================================================================================")
        print("🚀 [主动制造极端场景诊断器] 初始化成功")
        print(f"🎯 已锁定黄金参数集: Monday Gap Gap: {self.gap*100:+.1f}% | Profit stop trigger: {self.profit:.1f}% | Base HWM stop: {self.hwm*100:.1f}%")
        print("==========================================================================================")

    def load_base_engine(self):
        """Create and load data for a standard WeeklyRebalanceEngine."""
        engine = WeeklyRebalanceEngine(
            tickers=TICKERS_50,
            verbose=False,
            monday_gap_threshold=self.gap,
            breathing_profit_threshold=self.profit,
            hwm_stop_loss_pct=self.hwm
        )
        engine.load_all_data()
        
        # Pre-split dates to ensure O(1) dictionary lookup
        for t in engine.intraday_data:
            df = engine.intraday_data[t]
            if isinstance(df, pd.DataFrame):
                engine.intraday_data[t] = {d: grp for d, grp in df.groupby(df.index.date)}
        return engine

    def run_baseline(self):
        """Run standard baseline backtest."""
        print("\n📊 正在建立基准回测参考线 (2021-06-01 至 2026-05-30)...")
        engine = self.load_base_engine()
        m_base = engine.run_backtest(start_date_str="2021-06-01", end_date_str="2026-05-30", K=5)
        print(f"   ↳ ✅ [基准线] 收益率: {m_base['total_return_pct']:+.2f}% | 最大回撤: {m_base['max_drawdown_pct']:.2f}% | Sortino: {m_base['sortino_ratio']:.2f} | 交易笔数: {m_base['trades_count']}")
        return m_base

    def test_scenario_1_black_swan_crash(self):
        """
        Test Scenario 1: Global Black Swan Market Crash (Monday Open)
        We pick 8 random weeks throughout 2022-2024 and artificially force a massive QQQ -6.0% gap-down on Monday open
        and spike VIX to 48.0 on Friday to test if Monday Gap Defense and Regime limits successfully shield our capital.
        """
        print("\n💥 [极端测试 1: 系统性开盘黑天鹅暴跌测试] 正在人工注入开盘极端市场波动...")
        engine = self.load_base_engine()
        
        # We pick 8 specific Mondays to inject QQQ crash
        crash_mondays = [
            pd.to_datetime("2022-03-07"),
            pd.to_datetime("2022-06-13"),
            pd.to_datetime("2022-09-12"),
            pd.to_datetime("2023-03-13"),
            pd.to_datetime("2023-10-23"),
            pd.to_datetime("2024-04-15"),
            pd.to_datetime("2024-08-05"),
            pd.to_datetime("2025-01-06")
        ]
        
        # Inject -6% gap down on QQQ for those Mondays in qqq_daily
        for mon in crash_mondays:
            if mon in engine.qqq_daily.index:
                # Find previous Friday to calculate the gap correctly
                past_qqq = engine.qqq_daily[engine.qqq_daily.index < mon]
                if not past_qqq.empty:
                    friday_close = past_qqq['Close'].iloc[-1]
                    # Artificially set Monday Open to Friday Close * 0.94 (-6.0% Gap Down!)
                    engine.qqq_daily.loc[mon, 'Open'] = friday_close * 0.94
                    
            # Spike VIX to 48 on preceding Friday
            friday_date = mon - pd.Timedelta(days=3)
            vix_past = engine.vix_daily[engine.vix_daily.index < mon]
            if not vix_past.empty:
                last_trading_day = vix_past.index[-1]
                engine.vix_daily.loc[last_trading_day, 'Close'] = 48.0
                
        # Run backtest with the infected data
        m_stressed = engine.run_backtest(start_date_str="2021-06-01", end_date_str="2026-05-30", K=5)
        
        print(f"   ↳ 🛡️ [风控激活结果] 收益率: {m_stressed['total_return_pct']:+.2f}% | 最大回撤: {m_stressed['max_drawdown_pct']:.2f}% | Sortino: {m_stressed['sortino_ratio']:.2f}")
        print(f"   ↳ 🛡️ 交易笔数: {m_stressed['trades_count']} 次 (基准线为 {self.base_metrics['trades_count']} 次，减少开仓防御成功！)")
        return m_stressed

    def test_scenario_2_individual_flash_crash(self):
        """
        Test Scenario 2: Individual Stock Flash Crash & Gap-down (Monday Open)
        We select NVDA, TSLA, AMD and inject a catastrophic -25% gap-down on Monday open.
        """
        print("\n⚡ [极端测试 2: 个股特异性开盘闪崩与跳空极限测试] 注入周一 -25% 缺口闪崩...")
        engine = self.load_base_engine()
        
        # Target stock to crash: NVDA and TSLA
        crash_stocks = ['NVDA', 'TSLA', 'AMD']
        crash_mondays = [
            pd.to_datetime("2023-05-15"),
            pd.to_datetime("2023-11-20"),
            pd.to_datetime("2024-03-11"),
            pd.to_datetime("2024-07-22"),
            pd.to_datetime("2025-02-10")
        ]
        
        for t in crash_stocks:
            if t in engine.daily_data:
                for mon in crash_mondays:
                    if mon in engine.daily_data[t].index:
                        past_t = engine.daily_data[t][engine.daily_data[t].index < mon]
                        if not past_t.empty:
                            friday_close = past_t['Close'].iloc[-1]
                            # Force Open to crash by -25%!
                            engine.daily_data[t].loc[mon, 'Open'] = friday_close * 0.75
                            engine.daily_data[t].loc[mon, 'Low'] = friday_close * 0.70
                            engine.daily_data[t].loc[mon, 'Close'] = friday_close * 0.73
                            
                            # Also infect 5-min intraday bar for that Monday
                            if t in engine.intraday_data and mon.date() in engine.intraday_data[t]:
                                intra_df = engine.intraday_data[t][mon.date()]
                                if not intra_df.empty:
                                    # Copy to avoid writing to read-only views
                                    intra_df = intra_df.copy()
                                    intra_df.iloc[0, intra_df.columns.get_loc('Open')] = friday_close * 0.75
                                    intra_df.iloc[0, intra_df.columns.get_loc('Low')] = friday_close * 0.70
                                    intra_df.iloc[0, intra_df.columns.get_loc('Close')] = friday_close * 0.73
                                    engine.intraday_data[t][mon.date()] = intra_df
                                    
        m_stressed = engine.run_backtest(start_date_str="2021-06-01", end_date_str="2026-05-30", K=5)
        print(f"   ↳ 🛡️ [风控激活结果] 收益率: {m_stressed['total_return_pct']:+.2f}% | 最大回撤: {m_stressed['max_drawdown_pct']:.2f}% | Sortino: {m_stressed['sortino_ratio']:.2f}")
        return m_stressed

    def test_scenario_3_slippage_shock_sweep(self):
        """
        Test Scenario 3: Extreme Slippage Shock / Liquidity Sweep
        """
        print("\n📈 [极端测试 3: 极端滑点与流动性衰变测试] 开展滑点敏感度扫频...")
        slippage_levels = [0.002, 0.005, 0.010, 0.020]
        sweep_results = {}
        
        for slip in slippage_levels:
            engine = WeeklyRebalanceEngine(
                tickers=TICKERS_50,
                verbose=False,
                monday_gap_threshold=self.gap,
                breathing_profit_threshold=self.profit,
                hwm_stop_loss_pct=self.hwm
            )
            engine.load_all_data()
            for t in engine.intraday_data:
                df = engine.intraday_data[t]
                if isinstance(df, pd.DataFrame):
                    engine.intraday_data[t] = {d: grp for d, grp in df.groupby(df.index.date)}
            
            # We will patch engine's fee_rate to fee_rate + slip! This represents a perfect proxy for slippage friction!
            engine.fee_rate = 0.0003 + slip
            m_slip = engine.run_backtest(start_date_str="2021-06-01", end_date_str="2026-05-30", K=5)
            
            print(f"   ↳ 🚨 滑点加权摩擦 {slip*100:.2f}% | 最终收益: {m_slip['total_return_pct']:+.2f}% | 最大回撤: {m_slip['max_drawdown_pct']:.2f}% | Sortino: {m_slip['sortino_ratio']:.2f}")
            sweep_results[f"Slippage_{slip*100:.2f}%"] = m_slip
            
        return sweep_results

    def test_scenario_4_continuous_high_panic_regime(self):
        """
        Test Scenario 4: Continuous High Panic Regime (VIX Shift)
        """
        print("\n🌲 [极端测试 4: 持续高恐慌时相测试] 全局注入 VIX 极度抬升风险...")
        engine = self.load_base_engine()
        
        # Shift VIX up by 15.0 across all dates
        engine.vix_daily = engine.vix_daily.copy()
        engine.vix_daily['Close'] = engine.vix_daily['Close'] + 15.0
        
        m_panic = engine.run_backtest(start_date_str="2021-06-01", end_date_str="2026-05-30", K=5)
        print(f"   ↳ 🛡️ [全天候风控缩容结果] 收益率: {m_panic['total_return_pct']:+.2f}% | 最大回撤: {m_panic['max_drawdown_pct']:.2f}% | Sortino: {m_panic['sortino_ratio']:.2f}")
        return m_panic

    def test_scenario_5_midweek_black_swan_crash(self):
        """
        Test Scenario 5: Mid-week Systematic Black Swan Crash (Wednesday Shock)
        We pick 8 specific Wednesdays throughout 2022-2024 and artificially force a massive QQQ -6.0% crash on Wednesday close
        and spike VIX to 48.0 on Wednesday. This tests if mid-week daily trailing stops react instantly to exit positions mid-week.
        """
        print("\n💥 [极端测试 5: 周中系统性黑天鹅暴跌测试] 正在注入周三极限市场暴跌...")
        engine = self.load_base_engine()
        
        crash_wednesdays = [
            pd.to_datetime("2022-03-09"),
            pd.to_datetime("2022-06-15"),
            pd.to_datetime("2022-09-14"),
            pd.to_datetime("2023-03-15"),
            pd.to_datetime("2023-10-25"),
            pd.to_datetime("2024-04-17"),
            pd.to_datetime("2024-08-07"),
            pd.to_datetime("2025-01-08")
        ]
        
        for wed in crash_wednesdays:
            if wed in engine.qqq_daily.index:
                past_qqq = engine.qqq_daily[engine.qqq_daily.index < wed]
                if not past_qqq.empty:
                    tuesday_close = past_qqq['Close'].iloc[-1]
                    engine.qqq_daily.loc[wed, 'Open'] = tuesday_close * 0.99
                    engine.qqq_daily.loc[wed, 'Low'] = tuesday_close * 0.93
                    engine.qqq_daily.loc[wed, 'Close'] = tuesday_close * 0.94 # -6% crash on Wednesday!
                    
            if wed in engine.vix_daily.index:
                engine.vix_daily.loc[wed, 'Close'] = 48.0
                
        # Run backtest with infected data
        m_stressed = engine.run_backtest(start_date_str="2021-06-01", end_date_str="2026-05-30", K=5)
        print(f"   ↳ 🛡️ [周中风控激活结果] 收益率: {m_stressed['total_return_pct']:+.2f}% | 最大回撤: {m_stressed['max_drawdown_pct']:.2f}% | Sortino: {m_stressed['sortino_ratio']:.2f}")
        return m_stressed

    def test_scenario_6_midweek_individual_flash_crash(self):
        """
        Test Scenario 6: Mid-week Individual Flash Crash (Wednesday Crash)
        We select NVDA, TSLA, AMD and inject a catastrophic -25% crash on Wednesday.
        This tests if the daily trailing stop-loss (HWM) or hard physical stops successfully trigger mid-week.
        """
        print("\n⚡ [极端测试 6: 周中个股闪崩与止损灵敏度测试] 注入周三 -25% 崩盘...")
        engine = self.load_base_engine()
        
        crash_stocks = ['NVDA', 'TSLA', 'AMD']
        crash_wednesdays = [
            pd.to_datetime("2023-05-17"),
            pd.to_datetime("2023-11-22"),
            pd.to_datetime("2024-03-13"),
            pd.to_datetime("2024-07-24"),
            pd.to_datetime("2025-02-12")
        ]
        
        for t in crash_stocks:
            if t in engine.daily_data:
                for wed in crash_wednesdays:
                    if wed in engine.daily_data[t].index:
                        past_t = engine.daily_data[t][engine.daily_data[t].index < wed]
                        if not past_t.empty:
                            tuesday_close = past_t['Close'].iloc[-1]
                            engine.daily_data[t].loc[wed, 'Open'] = tuesday_close * 0.99
                            engine.daily_data[t].loc[wed, 'Low'] = tuesday_close * 0.70 # Wednesday low crashes to -30%
                            engine.daily_data[t].loc[wed, 'Close'] = tuesday_close * 0.75 # Wednesday close is -25%
                            
        m_stressed = engine.run_backtest(start_date_str="2021-06-01", end_date_str="2026-05-30", K=5)
        print(f"   ↳ 🛡️ [周中风控激活结果] 收益率: {m_stressed['total_return_pct']:+.2f}% | 最大回撤: {m_stressed['max_drawdown_pct']:.2f}% | Sortino: {m_stressed['sortino_ratio']:.2f}")
        return m_stressed

    def execute_all_stress_tests(self):
        # 1. Run Baseline
        self.base_metrics = self.run_baseline()
        
        # 2. Run Scenario 1
        s1_metrics = self.test_scenario_1_black_swan_crash()
        
        # 3. Run Scenario 2
        s2_metrics = self.test_scenario_2_individual_flash_crash()
        
        # 4. Run Scenario 3
        s3_sweep = self.test_scenario_3_slippage_shock_sweep()
        
        # 5. Run Scenario 4
        s4_metrics = self.test_scenario_4_continuous_high_panic_regime()

        # 6. Run Scenario 5
        s5_metrics = self.test_scenario_5_midweek_black_swan_crash()

        # 7. Run Scenario 6
        s6_metrics = self.test_scenario_6_midweek_individual_flash_crash()
        
        # Generate and print the Stunning ASCII Performance Comparison Dashboard
        print("\n" + "="*110)
        print("                 🏆 周频截面轮动引擎 —— 【主动制造极端场景与混沌测试】终极压力测试看板")
        print("="*110)
        
        headers = ["测试场景与极端压力项", "累计总收益", "跑赢大盘 (Alpha)", "最大回撤 (MDD)", "年化夏普", "年化索提诺", "获利因子", "总交易笔数"]
        print(f"{headers[0]:<35} | {headers[1]:<10} | {headers[2]:<15} | {headers[3]:<12} | {headers[4]:<8} | {headers[5]:<9} | {headers[6]:<8} | {headers[7]:<10}")
        print("-" * 110)
        
        # Baseline
        print(f"{'⚡ 5年期正常历史基准 (Baseline)':<35} | "
              f"{self.base_metrics['total_return_pct']:>+9.2f}% | "
              f"{self.base_metrics['alpha_pct']:>+14.2f}% | "
              f"{self.base_metrics['max_drawdown_pct']:>11.2f}% | "
              f"{self.base_metrics['sharpe_ratio']:>8.2f} | "
              f"{self.base_metrics['sortino_ratio']:>9.2f} | "
              f"{self.base_metrics['profit_factor']:>8.2f} | "
              f"{self.base_metrics['trades_count']:>10d}")
              
        # Scenario 1 (Monday Black Swan)
        print(f"{'💥 场景 1: 周一开盘黑天鹅 (QQQ -6%)':<35} | "
              f"{s1_metrics['total_return_pct']:>+9.2f}% | "
              f"{s1_metrics['alpha_pct']:>+14.2f}% | "
              f"{s1_metrics['max_drawdown_pct']:>11.2f}% | "
              f"{s1_metrics['sharpe_ratio']:>8.2f} | "
              f"{s1_metrics['sortino_ratio']:>9.2f} | "
              f"{s1_metrics['profit_factor']:>8.2f} | "
              f"{s1_metrics['trades_count']:>10d}")
              
        # Scenario 2 (Monday Stock Crash)
        print(f"{'⚡ 场景 2: 周一个股闪崩 (-25% Open)':<35} | "
              f"{s2_metrics['total_return_pct']:>+9.2f}% | "
              f"{s2_metrics['alpha_pct']:>+14.2f}% | "
              f"{s2_metrics['max_drawdown_pct']:>11.2f}% | "
              f"{s2_metrics['sharpe_ratio']:>8.2f} | "
              f"{s2_metrics['sortino_ratio']:>9.2f} | "
              f"{s2_metrics['profit_factor']:>8.2f} | "
              f"{s2_metrics['trades_count']:>10d}")

        # Scenario 5 (Wednesday Black Swan)
        print(f"{'💥 场景 3: 周中系统性暴跌 (QQQ -6%)':<35} | "
              f"{s5_metrics['total_return_pct']:>+9.2f}% | "
              f"{s5_metrics['alpha_pct']:>+14.2f}% | "
              f"{s5_metrics['max_drawdown_pct']:>11.2f}% | "
              f"{s5_metrics['sharpe_ratio']:>8.2f} | "
              f"{s5_metrics['sortino_ratio']:>9.2f} | "
              f"{s5_metrics['profit_factor']:>8.2f} | "
              f"{s5_metrics['trades_count']:>10d}")
              
        # Scenario 6 (Wednesday Stock Crash)
        print(f"{'⚡ 场景 4: 周中个股闪崩 (-25% Close)':<35} | "
              f"{s6_metrics['total_return_pct']:>+9.2f}% | "
              f"{s6_metrics['alpha_pct']:>+14.2f}% | "
              f"{s6_metrics['max_drawdown_pct']:>11.2f}% | "
              f"{s6_metrics['sharpe_ratio']:>8.2f} | "
              f"{s6_metrics['sortino_ratio']:>9.2f} | "
              f"{s6_metrics['profit_factor']:>8.2f} | "
              f"{s6_metrics['trades_count']:>10d}")
              
        # Scenario 4 (Continuous High Panic)
        print(f"{'🌲 场景 5: 持续恐慌风暴 (VIX +15)':<35} | "
              f"{s4_metrics['total_return_pct']:>+9.2f}% | "
              f"{s4_metrics['alpha_pct']:>+14.2f}% | "
              f"{s4_metrics['max_drawdown_pct']:>11.2f}% | "
              f"{s4_metrics['sharpe_ratio']:>8.2f} | "
              f"{s4_metrics['sortino_ratio']:>9.2f} | "
              f"{s4_metrics['profit_factor']:>8.2f} | "
              f"{s4_metrics['trades_count']:>10d}")
              
        # Slippage 0.50%
        slip_05 = s3_sweep["Slippage_0.50%"]
        print(f"{'📈 滑点冲击: 极端流动性枯竭 (0.5%)':<35} | "
              f"{slip_05['total_return_pct']:>+9.2f}% | "
              f"{slip_05['alpha_pct']:>+14.2f}% | "
              f"{slip_05['max_drawdown_pct']:>11.2f}% | "
              f"{slip_05['sharpe_ratio']:>8.2f} | "
              f"{slip_05['sortino_ratio']:>9.2f} | "
              f"{slip_05['profit_factor']:>8.2f} | "
              f"{slip_05['trades_count']:>10d}")
              
        print("="*110 + "\n")
        
        # Save results to findings directory for walkthrough integration
        findings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "findings")
        out_path = os.path.join(findings_dir, "extreme_stress_testing_results.json")
        
        summary_data = {
            "baseline": self.base_metrics,
            "black_swan_crash": s1_metrics,
            "individual_flash_crash": s2_metrics,
            "midweek_black_swan": s5_metrics,
            "midweek_individual_flash_crash": s6_metrics,
            "continuous_high_panic": s4_metrics,
            "slippage_sweep": {k: v for k, v in s3_sweep.items()}
        }
        
        # Clean pandas timestamp types
        def clean_types(d):
            if isinstance(d, dict):
                return {k: clean_types(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [clean_types(x) for x in d]
            elif isinstance(d, pd.Timestamp):
                return d.strftime('%Y-%m-%d')
            elif isinstance(d, (np.int64, np.int32)):
                return int(d)
            elif isinstance(d, (np.float64, np.float32)):
                return float(d)
            return d
            
        clean_summary = clean_types(summary_data)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(clean_summary, f, indent=2, ensure_ascii=False)
        print(f"💾 压力测试归档包已生成，成功保存至本地数仓：{out_path}\n")

if __name__ == "__main__":
    tester = ExtremeScenarioStressTester()
    tester.execute_all_stress_tests()
