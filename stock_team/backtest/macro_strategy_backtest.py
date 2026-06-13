"""
Macro-driven Stock Entry Strategy Backtesting Framework
宏观驱动的股票入场策略回测脚手架

本脚本实现了一个“自上而下”（Top-Down）的宏观+技术面双因子股票入场策略回测系统。
您可以直接运行此脚本进行测试，并根据需要修改因子参数和入场逻辑。

策略逻辑：
1. 宏观过滤（自上而下）：监测宏观指标（如PMI、利率）。当宏观环境处于扩张或宽松期（如PMI > 50 且无风险利率未暴涨）时，允许入场；否则保持空仓或低仓位。
2. 技术入场（时点选择）：在宏观环境允许的前提下，当个股出现技术突破（如价格突破均线）时触发买入。
3. 风控出场：个股跌破止损线（如ATR追踪止损）或宏观环境急剧恶化时离场。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体（解决Matplotlib画图中文乱码问题）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# ==============================================================================
# 1. 模拟数据生成模块 (Mock Data Generator)
# ==============================================================================
def generate_mock_data(days=1000):
    """
    生成模拟的宏观数据与股票量价数据，便于框架直接运行
    """
    np.random.seed(42)
    start_date = datetime.now() - timedelta(days=days)
    date_range = pd.date_range(start=start_date, periods=days, freq='D')
    
    # 1. 模拟宏观数据
    # PMI: 在45-55之间波动的周期曲线
    pmi = 50 + 4 * np.sin(np.linspace(0, 4 * np.pi, days)) + np.random.normal(0, 0.5, days)
    # 10年期国债收益率 (%): 在2.0 - 4.5 之间波动
    interest_rate = 3.0 - 0.8 * np.sin(np.linspace(0, 3 * np.pi, days)) + np.random.normal(0, 0.1, days)
    
    macro_df = pd.DataFrame({
        'PMI': pmi,
        'InterestRate': interest_rate
    }, index=date_range)
    
    # 2. 模拟股票量价数据 (以某种正相关的宏观贝塔为主)
    # 基础股票指数（基准）
    benchmark_returns = np.random.normal(0.0003, 0.012, days)
    # 让宏观PMI对收益率产生一点正向拉动，模拟宏观环境对股市的影响
    benchmark_returns += (pmi - 50) * 0.00015
    benchmark_price = 100 * np.exp(np.cumsum(benchmark_returns))
    
    # 目标个股数据 (带有Alpha的个股，波动更大)
    stock_returns = benchmark_returns * 1.2 + np.random.normal(0.0002, 0.018, days)
    stock_price_close = 10 * np.exp(np.cumsum(stock_returns))
    
    # 生成高开低收和成交量
    stock_df = pd.DataFrame(index=date_range)
    stock_df['Close'] = stock_price_close
    stock_df['High'] = stock_df['Close'] * (1 + np.abs(np.random.normal(0.01, 0.005, days)))
    stock_df['Low'] = stock_df['Close'] * (1 - np.abs(np.random.normal(0.01, 0.005, days)))
    stock_df['Open'] = (stock_df['High'] + stock_df['Low']) / 2 + np.random.normal(0, 0.01, days)
    stock_df['Volume'] = np.random.randint(10000, 100000, days) * (stock_df['Close'] / 10)
    
    return macro_df, stock_df

# ==============================================================================
# 2. 因子计算与因子库定义 (Factor Engine)
# ==============================================================================
def calculate_factors(macro_df, stock_df):
    """
    计算宏观过滤因子与股票微观入场因子
    """
    df = stock_df.copy()
    
    # 合并宏观数据到个股数据中
    df = df.join(macro_df, how='left')
    
    # ------------------ A. 宏观因子 (Macro Factors) ------------------
    # 1. PMI因子：PMI > 50 代表经济扩张 (1为扩张期，0为收缩期)
    df['Macro_PMI_Trend'] = (df['PMI'] > 50).astype(int)
    
    # 2. 利率变化趋势因子：10天利率均值是否下行（利率下行代表流动性宽松）
    df['Rate_MA10'] = df['InterestRate'].rolling(window=10).mean()
    df['Macro_Liquidity_Friendly'] = (df['InterestRate'] < df['Rate_MA10']).astype(int)
    
    # 综合宏观打分：满足任一偏暖信号即认为宏观可入场 (这里可以自定义权重或逻辑)
    df['Macro_Filter'] = ((df['Macro_PMI_Trend'] == 1) | (df['Macro_Liquidity_Friendly'] == 1)).astype(int)
    
    # ------------------ B. 技术面/量价选股因子 (Technical Factors) ------------------
    # 1. 均线系统 (EMA/MA)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # 均线多头排列因子
    df['Tech_MA_Trend'] = (df['MA20'] > df['MA60']).astype(int)
    
    # 2. 动量突破因子 (唐奇安通道突破)
    # 过去20天的最高价和最低价
    df['Donchian_High'] = df['Close'].shift(1).rolling(window=20).max()
    df['Donchian_Low'] = df['Close'].shift(1).rolling(window=20).min()
    
    # 价格突破20天高点
    df['Tech_Breakout'] = (df['Close'] > df['Donchian_High']).astype(int)
    
    # 3. 波动率指标 ATR (Average True Range) - 用于动态风控/止损
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift(1))
    low_close = np.abs(df['Low'] - df['Close'].shift(1))
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    # 填充空值
    df = df.bfill()
    
    return df

# ==============================================================================
# 3. 入场点信号生成器 (Signal Generator)
# ==============================================================================
def generate_entry_signals(df):
    """
    生成买入和卖出信号
    
    入场策略：
    - 宏观过滤器为真 (Macro_Filter == 1)
    - 并且技术面出现金叉突破 (Tech_Breakout == 1 或 Tech_MA_Trend金叉)
    
    出场策略：
    - 跌破止损线（如：买入价 - 2 * ATR）或均线死叉 (MA20 < MA60)
    """
    signals = df.copy()
    signals['Signal'] = 0  # 1: 买入信号, -1: 卖出信号, 0: 持币/维持持仓
    
    in_position = False
    buy_price = 0.0
    stop_loss = 0.0
    
    # 迭代生成交易信号
    for i in range(1, len(df)):
        current_date = df.index[i]
        
        # 提取因子值
        macro_ok = df['Macro_Filter'].iloc[i] == 1
        tech_breakout = df['Tech_Breakout'].iloc[i] == 1
        ma_golden_cross = (df['MA20'].iloc[i] > df['MA60'].iloc[i]) and (df['MA20'].iloc[i-1] <= df['MA60'].iloc[i-1])
        ma_death_cross = (df['MA20'].iloc[i] < df['MA60'].iloc[i]) and (df['MA20'].iloc[i-1] >= df['MA60'].iloc[i-1])
        
        atr = df['ATR'].iloc[i]
        close_price = df['Close'].iloc[i]
        
        if not in_position:
            # 基础入场逻辑：宏观向好 + (价格创20日新高 或 发生均线金叉)
            if macro_ok and (tech_breakout or ma_golden_cross):
                signals.loc[current_date, 'Signal'] = 1
                in_position = True
                buy_price = close_price
                stop_loss = buy_price - 2 * atr  # ATR追踪止损
        else:
            # 更新移动止损线（只升不降，保护利润）
            current_stop = close_price - 2 * atr
            if current_stop > stop_loss:
                stop_loss = current_stop
                
            # 基础离场逻辑：跌破移动止损线 或 均线发生死叉 或 宏观极度恶化
            # 这里让宏观彻底转弱(如PMI和利率均变差)也作为离场信号之一
            macro_bad = df['Macro_Filter'].iloc[i] == 0
            
            if (close_price < stop_loss) or ma_death_cross or macro_bad:
                signals.loc[current_date, 'Signal'] = -1
                in_position = False
                buy_price = 0.0
                stop_loss = 0.0
                
    return signals

# ==============================================================================
# 4. 向量化回测引擎 (Backtest Engine)
# ==============================================================================
def run_backtest(signals_df, initial_capital=100000.0, transaction_fee=0.0003):
    """
    运行策略回测并计算业绩指标
    """
    backtest = signals_df.copy()
    
    # 计算每日收益率
    backtest['Market_Return'] = backtest['Close'].pct_change()
    
    # 模拟持仓状态：1表示持有，0表示空仓
    backtest['Position'] = 0
    
    current_pos = 0
    for i in range(len(backtest)):
        sig = backtest['Signal'].iloc[i]
        if sig == 1:
            current_pos = 1
        elif sig == -1:
            current_pos = 0
        backtest.iloc[i, backtest.columns.get_loc('Position')] = current_pos
        
    # 我们要在信号产生的下一天（T+1日）执行交易，以避免前瞻偏差 (Look-ahead bias)
    backtest['Signal_Delayed'] = backtest['Signal'].shift(1)
    backtest['Position_Delayed'] = backtest['Position'].shift(1)
    backtest['Position_Delayed'] = backtest['Position_Delayed'].fillna(0)
    
    # 交易费用计算：当Position_Delayed发生变化时产生佣金
    backtest['Trades'] = backtest['Position_Delayed'].diff().abs()
    backtest.loc[backtest.index[0], 'Trades'] = backtest['Position_Delayed'].iloc[0]  # 第一天建仓记录
    backtest['Fees'] = backtest['Trades'] * transaction_fee
    
    # 策略每日收益：持仓状态下的市场收益 - 交易手续费
    backtest['Strategy_Return'] = backtest['Position_Delayed'] * backtest['Market_Return'] - backtest['Fees']
    
    # 计算累计收益率
    backtest['Benchmark_CumProd'] = (1 + backtest['Market_Return'].fillna(0)).cumprod()
    backtest['Strategy_CumProd'] = (1 + backtest['Strategy_Return'].fillna(0)).cumprod()
    
    # 计算资金曲线
    backtest['Portfolio_Value'] = backtest['Strategy_CumProd'] * initial_capital
    
    # ================= 业绩评价指标 =================
    total_days = len(backtest)
    years = total_days / 365.25
    
    # 1. 年化收益率 (CAGR)
    cum_return = backtest['Strategy_CumProd'].iloc[-1] - 1
    annual_return = (backtest['Strategy_CumProd'].iloc[-1]) ** (1 / years) - 1
    benchmark_annual = (backtest['Benchmark_CumProd'].iloc[-1]) ** (1 / years) - 1
    
    # 2. 年化波动率
    annual_vol = backtest['Strategy_Return'].std() * np.sqrt(252)
    
    # 3. 夏普比率 (Sharpe Ratio, 假设无风险利率为 2%)
    rf = 0.02
    sharpe_ratio = (annual_return - rf) / annual_vol if annual_vol > 0 else 0
    
    # 4. 最大回撤 (Max Drawdown)
    roll_max = backtest['Portfolio_Value'].cummax()
    drawdown = (backtest['Portfolio_Value'] - roll_max) / roll_max
    max_drawdown = drawdown.min()
    
    # 5. 交易次数与胜率
    trade_signals = backtest[backtest['Signal'] != 0]['Signal']
    num_trades = len(backtest[backtest['Trades'] == 1]) // 2  # 一买一卖算一次完整交易
    
    # 输出业绩报告
    print("\n" + "="*50)
    print("       策略回测业绩报告 (Backtest Performance)")
    print("="*50)
    print(f"回测周期: {backtest.index[0].strftime('%Y-%m-%d')} 至 {backtest.index[-1].strftime('%Y-%m-%d')} (约 {years:.2f} 年)")
    print(f"初始资金: {initial_capital:,.2f} 元")
    print(f"最终资金: {backtest['Portfolio_Value'].iloc[-1]:,.2f} 元")
    print(f"策略累计收益率: {cum_return * 100:.2f}%")
    print(f"基准累计收益率: {(backtest['Benchmark_CumProd'].iloc[-1] - 1) * 100:.2f}%")
    print(f"策略年化收益率: {annual_return * 100:.2f}%")
    print(f"基准年化收益率: {benchmark_annual * 100:.2f}%")
    print(f"年化波动率: {annual_vol * 100:.2f}%")
    print(f"夏普比率 (Sharpe Ratio): {sharpe_ratio:.2f}")
    print(f"最大回撤 (Max Drawdown): {max_drawdown * 100:.2f}%")
    print(f"完整交易次数: {num_trades} 次")
    print("="*50)
    
    return backtest, {
        'Total Return': cum_return,
        'Annual Return': annual_return,
        'Sharpe Ratio': sharpe_ratio,
        'Max Drawdown': max_drawdown
    }

# ==============================================================================
# 5. 可视化模块 (Visualization)
# ==============================================================================
def plot_results(backtest_df):
    """
    绘制资金曲线、宏观指标与交易信号对比图
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # 图1：资金曲线对比
    axes[0].plot(backtest_df.index, backtest_df['Strategy_CumProd'], label='宏观驱动入场策略', color='crimson', linewidth=2)
    axes[0].plot(backtest_df.index, backtest_df['Benchmark_CumProd'], label='基准(持有不动)', color='gray', linestyle='--', alpha=0.7)
    axes[0].set_title('策略累计净值 VS 基准累计净值', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('累计净值 (Net Value)')
    axes[0].grid(True, linestyle=':', alpha=0.6)
    axes[0].legend(loc='upper left')
    
    # 标记买卖点
    buy_signals = backtest_df[backtest_df['Signal'] == 1]
    sell_signals = backtest_df[backtest_df['Signal'] == -1]
    
    # 在净值图上映射买入卖出时刻的基准点，作为参考
    axes[0].scatter(buy_signals.index, backtest_df.loc[buy_signals.index, 'Strategy_CumProd'], 
                    marker='^', color='green', s=100, label='买入 (Buy)')
    axes[0].scatter(sell_signals.index, backtest_df.loc[sell_signals.index, 'Strategy_CumProd'], 
                    marker='v', color='orange', s=100, label='卖出 (Sell)')
    axes[0].legend(loc='upper left')

    # 图2：宏观指标与过滤器状态
    axes[1].plot(backtest_df.index, backtest_df['PMI'], label='PMI (左轴)', color='royalblue', alpha=0.8)
    axes[1].axhline(50, color='red', linestyle='--', alpha=0.5, label='PMI荣枯线(50)')
    axes[1].set_ylabel('PMI 指数')
    
    # 双轴绘制利率
    ax2_twin = axes[1].twinx()
    ax2_twin.plot(backtest_df.index, backtest_df['InterestRate'], label='10年期国债利率 (右轴)', color='purple', alpha=0.6)
    ax2_twin.set_ylabel('利率 (%)')
    
    # 合并图例
    lines, labels = axes[1].get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    axes[1].legend(lines + lines2, labels + labels2, loc='upper left')
    axes[1].set_title('宏观指标监测 (PMI & 无风险利率)', fontsize=12)
    axes[1].grid(True, linestyle=':', alpha=0.6)
    
    # 图3：持仓区间与宏观过滤器
    axes[2].fill_between(backtest_df.index, 0, backtest_df['Position_Delayed'], 
                         facecolor='green', alpha=0.2, label='持仓区间 (Position)')
    axes[2].plot(backtest_df.index, backtest_df['Macro_Filter'], label='宏观过滤器 (1=偏暖, 0=偏冷)', 
                 color='teal', linestyle='-.', alpha=0.8)
    axes[2].set_title('策略持仓区间与宏观过滤器状态', fontsize=12)
    axes[2].set_ylabel('状态值')
    axes[2].set_xlabel('日期 (Date)')
    axes[2].grid(True, linestyle=':', alpha=0.6)
    axes[2].legend(loc='upper left')
    
    plt.tight_layout()
    plt.savefig('strategy_performance.png', dpi=300)
    print("\n[成功] 业绩图表已保存至: strategy_performance.png")
    try:
        plt.show()
    except Exception:
        print("[提示] 处于非交互式环境，跳过显示图表窗口，请直接查看 strategy_performance.png")

# ==============================================================================
# 主入口 (Main Execution)
# ==============================================================================
if __name__ == '__main__':
    print("正在启动宏观股票入场策略回测系统...")
    
    # 1. 模拟生成1000天（约3年）的数据
    macro_data, stock_data = generate_mock_data(days=1000)
    
    # 2. 计算因子
    print("正在计算宏观因子与技术因子...")
    factored_df = calculate_factors(macro_data, stock_data)
    
    # 3. 生成买卖信号
    print("正在生成交易信号...")
    signals_df = generate_entry_signals(factored_df)
    
    # 4. 执行回测并评估业绩
    print("正在运行策略回测评估...")
    backtest_result, metrics = run_backtest(signals_df)
    
    # 5. 可视化
    print("正在生成分析图表...")
    plot_results(backtest_result)
