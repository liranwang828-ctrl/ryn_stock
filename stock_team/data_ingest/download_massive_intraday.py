import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta

# Force UTF-8 printing
sys.stdout.reconfigure(encoding='utf-8')

# 1. Read API Key from .env file
def get_api_key():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        return None
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("POLYGON_API_KEY="):
                key = line.strip().split("=")[1].strip()
                if "your_actual_api_key_here" in key or not key:
                    return None
                return key
    return None

API_KEY = get_api_key()

TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX', 
    'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'JPM', 'BAC', 'MS', 'GS', 'V', 
    'MA', 'AXP', 'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'TSLA', 
    'HD', 'MCD', 'NKE', 'SBUX', 'WMT', 'COST', 'KO', 'PEP', 'PG', 'GE', 
    'CAT', 'HON', 'LMT', 'BA', 'XOM', 'CVX', 'COP', 'FCX', 'NEE', 'AMT'
]
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning")
os.makedirs(CACHE_DIR, exist_ok=True)

# Fetch 5 years of history to cover multiple market cycles (including the brutal 2022 bear market)
DAYS_TO_FETCH = 1825  

def download_ticker_history(ticker, api_key):
    cache_path = os.path.join(CACHE_DIR, f"intraday_cache_{ticker}.csv")
    # Check if a comprehensive 5-year cache exists (usually > 7.5 MB)
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 7.5 * 1024 * 1024:
        print(f"🟢 {ticker} 5年高频缓存已存在于本地，自动跳过下载。")
        return True
        
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DAYS_TO_FETCH)
    
    print(f"\n📡 正在从 Massive.com 获取 {ticker} 过去 5 年的 5分钟 综合高频数据...")
    print(f"   时间跨度: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    
    # Chunk downloads into 6-month blocks to guarantee we never hit Polygon's 50,000 limit per call
    chunk_size_days = 180
    current_start = start_date
    all_dfs = []
    
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_size_days), end_date)
        start_str = current_start.strftime("%Y-%m-%d")
        end_str = current_end.strftime("%Y-%m-%d")
        
        # Massive.com (Polygon.io) Aggregates API Endpoint
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/5/minute/{start_str}/{end_str}?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
        
        try:
            r = requests.get(url)
            if r.status_code != 200:
                print(f"   ❌ 获取分片 [{start_str} 至 {end_str}] 失败: {r.status_code}")
                current_start = current_end
                continue
                
            res = r.json()
            results = res.get("results", [])
            
            if results:
                df_chunk = pd.DataFrame(results)
                # Map Polygon keys: t=timestamp, o=open, h=high, l=low, c=close, v=volume
                df_chunk = df_chunk.rename(columns={
                    't': 'Datetime',
                    'o': 'Open',
                    'h': 'High',
                    'l': 'Low',
                    'c': 'Close',
                    'v': 'Volume'
                })
                # Convert unix millisecond timestamp to datetime
                df_chunk['Datetime'] = pd.to_datetime(df_chunk['Datetime'], unit='ms', utc=True)
                df_chunk = df_chunk.set_index('Datetime')
                
                # Keep only core trading columns
                df_chunk = df_chunk[['Open', 'High', 'Low', 'Close', 'Volume']]
                all_dfs.append(df_chunk)
                print(f"   ✅ 分片 [{start_str} 至 {end_str}] 下载成功 | 包含 {len(df_chunk)} 条数据")
            else:
                print(f"   🟡 分片 [{start_str} 至 {end_str}] 无数据")
                
        except Exception as e:
            print(f"   ❌ 分片 [{start_str} 至 {end_str}] 处理异常: {e}")
            
        current_start = current_end
        
    if not all_dfs:
        print(f"🔴 {ticker} 没有下载到任何数据。")
        return False
        
    # Combine and deduplicate
    df_combined = pd.concat(all_dfs)
    df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
    df_combined = df_combined.sort_index()
    
    # Align with the yfinance formatting (Add Dividends and Stock Splits as 0.0)
    df_combined['Dividends'] = 0.0
    df_combined['Stock Splits'] = 0.0
    
    # Save to local CSV
    df_combined.to_csv(cache_path)
    # Touch modification time
    os.utime(cache_path, None)
    
    print(f"🟢 成功写入 {ticker}: 本地已永久保存 {len(df_combined)} 条 5分钟 K线")
    print(f"   实际时间范围: {df_combined.index[0].tz_convert('America/New_York')} 至 {df_combined.index[-1].tz_convert('America/New_York')}")
    return True

def main():
    print("============================================================")
    print("🚀 Massive.com (原 Polygon) 2年历史高频 5分钟数据 永续收割同步器")
    print("============================================================")
    
    if not API_KEY:
        print("🔴 错误: 未能在 .env 文件中检测到有效 POLYGON_API_KEY。")
        print("💡 请先将您的 API Key 粘贴进 stock_team/.env 中的 POLYGON_API_KEY 字段！")
        print("============================================================")
        return
        
    print(f"✅ 已检测到 API Key | 启动 15 支 AI 龙头 + QQQ 的 2年数据下载计划...")
    
    # Add QQQ benchmark to download list
    download_tickers = TICKERS + ["QQQ"]
    success_count = 0
    
    for ticker in download_tickers:
        if download_ticker_history(ticker, API_KEY):
            success_count += 1
            
    print("\n" + "="*60)
    print(f"✨ 永续同步大告捷：成功永久同步并缓存 {success_count}/{len(download_tickers)} 个标的历史高频数据库！")
    print("💡 提示：这批数据已安全保存在本地 learning/ 文件夹下，您可以随时取消订阅，本地数据可永久免费使用！")
    print("="*60)

if __name__ == "__main__":
    main()
