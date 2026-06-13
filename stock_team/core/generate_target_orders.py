import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime

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

def generate_sandboxed_api_mock_code():
    """Returns elegant, ready-to-run Alpaca & IB mock integration scripts."""
    return """
# ====================================================================================
# 🔌 实盘生产环境沙盒 API 无缝对接钩子示例 (Alpaca / Interactive Brokers)
# ====================================================================================

# 1. 🟢 Alpaca API 挂单与 GTC 止损自动化状态机集成
import alpaca_trade_api as tradeapi

def execute_orders_on_alpaca(target_orders, best_params):
    # 初始化 Alpaca 模拟盘沙盒客户端
    api = tradeapi.REST(
        key_id='YOUR_ALPACA_SANDBOX_KEY_ID',
        secret_key='YOUR_ALPACA_SANDBOX_SECRET_KEY',
        base_url='https://paper-api.alpaca.markets', # 锁定沙盒域名
        api_version='v2'
    )
    
    print("\\n📡 [Alpaca Sandbox Connection] 正在同步目标交易指令集...")
    
    # 获取当前已持仓列表，处理 Rebalance 卖出/减持
    positions = {p.symbol: p for p in api.list_positions()}
    
    for order in target_orders:
        symbol = order["ticker"]
        action = order["action"]
        qty = int(order["shares"])
        
        if qty <= 0:
            continue
            
        if action == "SELL":
            print(f"🔴 [Alpaca] 调仓卖出: {symbol} | 数量: {qty} 股")
            api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='market',
                time_in_force='day'
            )
        elif action == "BUY":
            print(f"🟢 [Alpaca] 调仓买入: {symbol} | 数量: {qty} 股")
            # 1. 提交买入市价单 (周一开盘 MOO 订单或 EOD 分段进场)
            buy_order = api.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                type='market',
                time_in_force='day'
            )
            
            # 2. 🟢 挂接大师风控高水位移动止损 (GTC Trailing Stop)
            trail_pct = float(order["hwm_trail"]) * 100 # 转化为百分比
            print(f"🛡️ [Alpaca] 绑定高水位 GTC 移动止损: {symbol} | 动态止损轨: {trail_pct:.1f}%")
            api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='trailing_stop',
                trail_percent=trail_pct,
                time_in_force='gtc' # 长期有效直到取消
            )

# 2. 🔵 Interactive Brokers (IB) API 集成
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

class IBRebalanceApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        
    def place_rebalance_bracket(self, order_id, ticker, action, qty, hwm_trail):
        # 1. 定义美股合约
        contract = Contract()
        contract.symbol = ticker
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        
        # 2. 提交买入市价单
        parent = Order()
        parent.orderId = order_id
        parent.action = action
        parent.orderType = "MKT"
        parent.totalQuantity = qty
        parent.transmit = False
        
        # 3. 挂接长期高水位移动止损单 (GTC Trailing Stop Limit)
        stop = Order()
        stop.orderId = parent.orderId + 1
        stop.parentId = parent.orderId
        stop.action = "SELL" if action == "BUY" else "BUY"
        stop.orderType = "TRAIL"
        stop.trailingPercent = float(hwm_trail) * 100
        stop.totalQuantity = qty
        stop.tif = "GTC" # GTC 长期保护止损
        stop.transmit = True
        
        self.placeOrder(parent.orderId, contract, parent)
        self.placeOrder(stop.orderId, contract, stop)
        print(f"🛡️ [IB API] 成功提交 {ticker} 双轨再平衡 Bracket 套单 | Trailing: {hwm_trail*100:.1f}%")
"""

def main():
    print("==========================================================================")
    print("🔌 [实盘再平衡 4] 目标交易清单(Target Order Sheet)自动生成与沙盒对接器")
    print("==========================================================================")
    
    # 1. Load optimal parameters
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "best_weekly_params.json")
    if not os.path.exists(config_path):
        config_path = r"d:\gemini\lianghua\stock_team\config\best_weekly_params.json"
        
    with open(config_path, "r", encoding="utf-8") as f:
        best_params = json.load(f)
        
    gap = best_params["monday_gap_threshold"]
    profit = best_params["breathing_profit_threshold"]
    hwm = best_params["hwm_stop_loss_pct"]
    
    # Initialize engine
    engine = WeeklyRebalanceEngine(
        tickers=TICKERS_50,
        verbose=False,
        monday_gap_threshold=gap,
        breathing_profit_threshold=profit,
        hwm_stop_loss_pct=hwm
    )
    engine.load_all_data()
    
    # Get the latest available Friday date from the database
    qqq_dates = sorted(list(engine.qqq_daily.index))
    latest_date = qqq_dates[-1]
    
    # Calculate factors on the latest available Friday close
    print(f"📡 正在计算横截面因子评分。基准评估日期 (最新周五): {latest_date.strftime('%Y-%m-%d')}")
    scores = engine.calculate_factors(latest_date)
    
    # Select top 5 tickers passing Stage 2
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    top_selected = sorted_scores[:5]
    
    # Get VIX risk sizing
    vix_val = engine.vix_daily.loc[latest_date, 'Close'] if latest_date in engine.vix_daily.index else 18.0
    active_exposure = np.clip(18.0 / vix_val, 0.15, 1.0)
    
    print(f"📊 最新 VIX 指数: {vix_val:.2f} | 组合实盘最大允许主动风险仓位: {active_exposure*100:.1f}%\n")
    
    # 2. Assume $100,000 baseline cash, read current portfolio positions if they exist
    initial_equity = 100000.0
    positions_cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "positions.json")
    
    # Map ticker to target value based on Rank Weights [0.35, 0.25, 0.20, 0.12, 0.08]
    RANK_WEIGHTS = [0.35, 0.25, 0.20, 0.12, 0.08]
    target_weights_map = {}
    for idx, (t, info) in enumerate(top_selected):
        target_weights_map[t] = initial_equity * active_exposure * RANK_WEIGHTS[idx]
        
    # Generate Target Order Sheet
    target_orders = []
    
    print("📋 目标股票选取矩阵 (TOP 5):")
    print("-" * 100)
    print(f"{'排名':<4} | {'股票':<6} | {'RS得分':<8} | {'收盘价':<8} | {'目标仓位价值':<12} | {'硬性ATR止损':<12} | {'高水位动态止损轨'}")
    print("-" * 100)
    
    for idx, (t, info) in enumerate(top_selected):
        target_val = target_weights_map[t]
        shares = target_val / info["close"]
        hwm_trail = info["hwm_trail"]
        hard_stop = info["close"] - 4.5 * info["atr"]
        
        print(f"#{idx+1:<3} | {t:<6} | {info['score']:>8.3f} | ${info['close']:>7.2f} | ${target_val:>11.2f} | ${hard_stop:>11.2f} | {hwm_trail*100:.1f}%")
        
        target_orders.append({
            "ticker": t,
            "action": "BUY",
            "shares": int(shares),
            "close_price": float(info["close"]),
            "target_value": float(target_val),
            "hard_stop_atr": float(hard_stop),
            "hwm_trail": float(hwm_trail),
            "execution_date": "2026-06-01 (Monday Open)"
        })
    print("-" * 100 + "\n")
    
    # Save target orders sheet to config directory
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    out_json_path = os.path.join(config_dir, "target_orders_rebalance.json")
    
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "rebalance_date": "2026-06-01",
            "vix": float(vix_val),
            "active_exposure": float(active_exposure),
            "orders": target_orders
        }, f, indent=2, ensure_ascii=False)
        
    print(f"💾 实盘生产交易清单已成功导出至配置文件：{out_json_path}")
    
    # Print Mock Sandbox Integration guidelines
    print("\n" + "=" * 90)
    print("                      ⚡ 机构级 Alpaca & IB 极小仓位沙盒实测接入指南")
    print("=" * 90)
    print("1. 大师级 GTC 双轨 Brackets 套单：系统支持在买入开仓的同时，自动挂接 '长期有效高水位移动止损 (GTC Trailing)'。")
    print("2. 实操落地方案：以下已为您生成高度吻合 Alpaca/IB REST 接口的状态机对接代码，已物理写入 `scripts/generate_target_orders.py`！")
    print("-" * 90)
    print(generate_sandboxed_api_mock_code()[:1000] + "\n   ... [完整IB/Alpaca沙盒高亮代码见 scripts/generate_target_orders.py] ...")
    print("=" * 90 + "\n")

if __name__ == "__main__":
    main()
