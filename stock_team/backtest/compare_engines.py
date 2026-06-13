import sys
import os
import json
import pandas as pd
import numpy as np
import builtins

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.dirname(__file__))

from stock_team.backtest.joint_backtest_engine import run_joint_backtest
from stock_team.backtest.weekly_rebalance_engine import WeeklyRebalanceEngine

TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX', 
    'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'JPM', 'BAC', 'MS', 'GS', 'V', 
    'MA', 'AXP', 'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'TSLA', 
    'HD', 'MCD', 'NKE', 'SBUX', 'WMT', 'COST', 'KO', 'PEP', 'PG', 'GE', 
    'CAT', 'HON', 'LMT', 'BA', 'XOM', 'CVX', 'COP', 'FCX', 'NEE', 'AMT'
]

# Original 5-minute state machine parameters
BREAKTHROUGH_PARAMS = {
    "vc_threshold_pct": 40.0,
    "atr_stop_multiplier": 3.0,
    "rs_strong_threshold": 2.0,
    "ml_score_threshold": 0.8,
    "ml_confirm_bars": 3,
    "t1_wait_bars": 5,
    "entry_cutoff_time": "11:00",
    "stop_freeze_bars": 6,
    "hwm_trail_pct": 0.95,
    "trailing_stop_type": "HighWaterMark",
    "stop_loss_type": "ATR",
    "use_noise_delay": True,
    "use_t2_confirm": False,
    "profit_lock_threshold": 1.03,
    "tightened_trailing_stop_pct": 0.985,
    "open_high_vol_multiplier": 1.5,
    "ma20_trail_atr_multiplier": 0.5,
    "bracket_stop_loss_pct": 0.8,
    "max_active_positions": 5,
    "position_sizing_factor": 0.20,
    "long_term_ma_buffer_pct": 2.0,
    "long_term_trail_pct": 12.0,
    "long_term_atr_multiplier": 4.5
}
orig_rules = {
    'use_barbell': False,
    'methodology_15_low_catalyst_rs': BREAKTHROUGH_PARAMS
}

print("=" * 76)
print("📊 策略同台竞技：原5分钟高频状态机 vs 新周频截面轮动引擎")
print("=" * 76)

# 1. Run Original 5-min Backtest Silently
print("📡 正在运行原 5分钟高频状态机 5年全量回测 (请稍候)...")
orig_print = builtins.print
builtins.print = lambda *args, **kwargs: None
try:
    m_orig = run_joint_backtest(TICKERS, days=1825, custom_rules=orig_rules, verbose=False)
finally:
    builtins.print = orig_print

if not m_orig:
    print("🔴 原 5分钟策略回测失败。")
    sys.exit(1)
print(f"✅ 原策略回测完成！完成交易: {m_orig['trades_count']} 次")

# 2. Run New Weekly Rebalance Backtest Silently
print("\n📡 正在运行新 周频截面轮动阿尔法引擎 5年全量回测 (包含日内 Tactical 选点)...")
engine = WeeklyRebalanceEngine(TICKERS, verbose=False)
m_new = engine.run_backtest(K=5)
print(f"✅ 新策略回测完成！完成交易: {m_new['trades_count']} 次")

# 3. Rebuild and Merge Daily Equity Curves
def extract_daily_df(m_res, col_name):
    curve = m_res['equity_curve']
    df_curve = pd.DataFrame(curve)
    df_curve['Date'] = pd.to_datetime(df_curve['Timestamp']).dt.date
    df_daily = df_curve.groupby('Date').last().reset_index()
    df_daily['Date'] = pd.to_datetime(df_daily['Date']).dt.tz_localize(None)
    df_daily = df_daily.set_index('Date')
    return df_daily[[col_name]]

df_orig = extract_daily_df(m_orig, 'Equity').rename(columns={'Equity': 'Orig_Equity'})
df_new = extract_daily_df(m_new, 'Equity').rename(columns={'Equity': 'New_Equity'})

# Load QQQ Benchmark
from stock_team.backtest.joint_backtest_engine import DataFeatureBroker
broker = DataFeatureBroker()
qqq_daily_df = broker.get_daily_indicators("QQQ")
qqq_daily_df.index = pd.to_datetime(qqq_daily_df.index).tz_localize(None)

# Merge everything
df_merged = pd.merge(df_orig, df_new, left_index=True, right_index=True, how='inner')
df_merged = pd.merge(df_merged, qqq_daily_df[['Close']], left_index=True, right_index=True, how='inner')
df_merged = df_merged.rename(columns={'Close': 'QQQ'})

periods = [
    {"name": "1. 2021年多头牛市 (2021-06-01 至 2021-12-31)", "start": "2021-06-01", "end": "2021-12-31"},
    {"name": "2. 2022年大通胀熊市 (2022-01-01 至 2022-12-31)", "start": "2022-01-01", "end": "2022-12-31"},
    {"name": "3. 2023-2025年科技主升浪 (2023-01-01 至 2025-12-31)", "start": "2023-01-01", "end": "2025-12-31"},
    {"name": "4. 2026年高位震荡 (2026-01-01 至 2026-05-30)", "start": "2026-01-01", "end": "2026-05-30"}
]

print("\n" + "="*80)
print("             🏆 两大核心引擎各子周期绩效多维度对比表")
print("="*80)

for p in periods:
    start_dt = pd.to_datetime(p["start"])
    end_dt = pd.to_datetime(p["end"])
    
    df_p = df_merged[(df_merged.index >= start_dt) & (df_merged.index <= end_dt)]
    if df_p.empty:
        continue
        
    # P1: Original 5m Strategy returns
    o_start = df_p['Orig_Equity'].iloc[0]
    o_end = df_p['Orig_Equity'].iloc[-1]
    o_ret = ((o_end - o_start) / o_start) * 100
    
    # P2: New Weekly Strategy returns
    n_start = df_p['New_Equity'].iloc[0]
    n_end = df_p['New_Equity'].iloc[-1]
    n_ret = ((n_end - n_start) / n_start) * 100
    
    # QQQ returns
    q_start = df_p['QQQ'].iloc[0]
    q_end = df_p['QQQ'].iloc[-1]
    q_ret = ((q_end - q_start) / q_start) * 100
    
    # Max Drawdowns in this sub-period
    df_p = df_p.copy()
    df_p['O_Roll'] = df_p['Orig_Equity'].cummax()
    df_p['O_DD'] = (df_p['Orig_Equity'] - df_p['O_Roll']) / df_p['O_Roll'] * 100
    o_mdd = df_p['O_DD'].min()
    
    df_p['N_Roll'] = df_p['New_Equity'].cummax()
    df_p['N_DD'] = (df_p['New_Equity'] - df_p['N_Roll']) / df_p['N_Roll'] * 100
    n_mdd = df_p['N_DD'].min()
    
    df_p['Q_Roll'] = df_p['QQQ'].cummax()
    df_p['Q_DD'] = (df_p['QQQ'] - df_p['Q_Roll']) / df_p['Q_Roll'] * 100
    q_mdd = df_p['Q_DD'].min()
    
    print(f"\n📅 {p['name']}:")
    print(f"   📈 QQQ 收益率  : {q_ret:+.2f}%  | 最大回撤: {q_mdd:.2f}%")
    print(f"   ⚡ 原5m状态机  : {o_ret:+.2f}%  | 最大回撤: {o_mdd:.2f}% | 相对 Alpha: {o_ret - q_ret:+.2f}%")
    print(f"   🚀 新周频截面  : {n_ret:+.2f}%  | 最大回撤: {n_mdd:.2f}% | 相对 Alpha: {n_ret - q_ret:+.2f}%")
    print("-" * 80)

# Full Period Dashboard Comparison
print("\n" + "="*80)
print("             🏆 5年全生命周期总绩效指标 PK")
print("="*80)
print(f"指标项目            |  原5分钟状态机         |  新周频截面轮动")
print("-" * 80)
# Format everything into strings first for perfect and robust alignment
o_tc = str(m_orig['trades_count'])
n_tc = str(m_new['trades_count'])
o_wr = f"{m_orig['win_rate_pct']:.1f}%"
n_wr = f"{m_new['win_rate_pct']:.1f}%"
o_tr = f"{m_orig['total_return_pct']:+.2f}%"
n_tr = f"{m_new['total_return_pct']:+.2f}%"
o_qr = f"{m_orig['qqq_return_pct']:+.2f}%"
n_qr = f"{m_new['qqq_return_pct']:+.2f}%"
o_al = f"{m_orig['alpha_pct']:+.2f}%"
n_al = f"{m_new['alpha_pct']:+.2f}%"
o_dd = f"{m_orig['max_drawdown_pct']:.2f}%"
n_dd = f"{m_new['max_drawdown_pct']:.2f}%"
o_sh = f"{m_orig['sharpe_ratio']:.2f}"
n_sh = f"{m_new['sharpe_ratio']:.2f}"
o_so = f"{m_orig['sortino_ratio']:.2f}"
n_so = f"{m_new['sortino_ratio']:.2f}"
o_ca = f"{m_orig['calmar_ratio']:.2f}"
n_ca = f"{m_new['calmar_ratio']:.2f}"

print(f"交易总笔数          |  {o_tc:<20} |  {n_tc:<20}")
print(f"胜率                |  {o_wr:<20} |  {n_wr:<20}")
print(f"累计总收益          |  {o_tr:<20} |  {n_tr:<20}")
print(f"同期 QQQ 收益       |  {o_qr:<20} |  {n_qr:<20}")
print(f"超额收益 Alpha      |  {o_al:<20} |  {n_al:<20}")
print(f"历史最大回撤        |  {o_dd:<20} |  {n_dd:<20}")
print(f"年化夏普比率        |  {o_sh:<20} |  {n_sh:<20}")
print(f"年化索提诺比率      |  {o_so:<20} |  {n_so:<20}")
print(f"年化卡玛比率        |  {o_ca:<20} |  {n_ca:<20}")
print("="*80 + "\n")
