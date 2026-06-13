import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# Force UTF-8 printing
sys.stdout.reconfigure(encoding='utf-8')

# Read API Key from .env file
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

# 50 Highly traded, high-beta/momentum stars
TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX', 
    'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'JPM', 'BAC', 'MS', 'GS', 'V', 
    'MA', 'AXP', 'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'TSLA', 
    'HD', 'MCD', 'NKE', 'SBUX', 'WMT', 'COST', 'KO', 'PEP', 'PG', 'GE', 
    'CAT', 'HON', 'LMT', 'BA', 'XOM', 'CVX', 'COP', 'FCX', 'NEE', 'AMT'
]

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning")
os.makedirs(CACHE_DIR, exist_ok=True)

# Default to 2 years (730 days) of 1-minute historical data
# Users can request up to 5 years (1825 days) via sys.argv
DAYS_TO_FETCH = int(sys.argv[1]) if len(sys.argv) > 1 else 730

def download_ticker_1min_history(ticker, api_key):
    parquet_path = os.path.join(CACHE_DIR, f"intraday_1min_{ticker}.parquet")
    csv_path = os.path.join(CACHE_DIR, f"intraday_1min_{ticker}.csv")
    
    # Check if a comprehensive cache exists
    if os.path.exists(parquet_path) and os.path.getsize(parquet_path) > 5 * 1024 * 1024:
        print(f"🟢 {ticker} 1分钟高频Parquet缓存已存在，自动跳过。")
        return True
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 25 * 1024 * 1024:
        print(f"🟢 {ticker} 1分钟高频CSV缓存已存在，自动跳过。")
        return True
        
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DAYS_TO_FETCH)
    
    print(f"\n📡 正在从 Polygon 获取 {ticker} 过去 {DAYS_TO_FETCH} 天的 1分钟 极致高频K线...")
    print(f"   时间跨度: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    
    # Chunk downloads into 30-day blocks to stay well under the 50,000 aggregates limit per call
    # 30 days * 390 min/day = ~11,700 rows, very safe!
    chunk_size_days = 30
    current_start = start_date
    all_dfs = []
    
    session = requests.Session()
    
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_size_days), end_date)
        start_str = current_start.strftime("%Y-%m-%d")
        end_str = current_end.strftime("%Y-%m-%d")
        
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{start_str}/{end_str}?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
        
        try:
            # Respect rate limit, sleep briefly
            time.sleep(0.05)
            r = session.get(url, timeout=15)
            if r.status_code != 200:
                print(f"   ❌ 获取分片 [{start_str} 至 {end_str}] 失败: HTTP {r.status_code}")
                current_start = current_end
                continue
                
            res = r.json()
            results = res.get("results", [])
            
            if results:
                df_chunk = pd.DataFrame(results)
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
                df_chunk = df_chunk[['Open', 'High', 'Low', 'Close', 'Volume']]
                all_dfs.append(df_chunk)
                print(f"   ✅ 分片 [{start_str} 至 {end_str}] 下载成功 | {len(df_chunk)} 条")
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
    
    # Save the data
    try:
        df_combined.to_parquet(parquet_path)
        print(f"🟢 成功写入并压缩 {ticker} Parquet 文件 | 共 {len(df_combined)} 条 1分钟 K线")
        # Clean up CSV if exists
        if os.path.exists(csv_path):
            os.remove(csv_path)
    except ImportError:
        df_combined.to_csv(csv_path)
        print(f"🟢 成功写入 {ticker} CSV 文件 (未安装 pyarrow) | 共 {len(df_combined)} 条 1分钟 K线")
        
    return True

def main():
    print("============================================================")
    # Translation: "Massive.com (Polygon.io) 1-Minute Hyper-Frequency 'Star Stock' Harvest Syncer"
    print("🚀 Polygon.io 1分钟极致高频“明星股”历史数据永续收割同步器")
    print("============================================================")
    
    if not API_KEY:
        print("🔴 错误: 未能在 .env 文件中检测到有效 POLYGON_API_KEY。")
        print("============================================================")
        return
        
    print(f"✅ 已检测到 API Key | 启动 {len(TICKERS)} 支明星成份股的 {DAYS_TO_FETCH} 天 1分钟 高频同步...")
    
    success_count = 0
    for ticker in TICKERS:
        try:
            if download_ticker_1min_history(ticker, API_KEY):
                success_count += 1
        except KeyboardInterrupt:
            print("\n👋 收到中断信号，正在退出主流程...")
            break
        except Exception as e:
            print(f"🔴 {ticker} 下载发生严重错误: {e}")
            
    print("\n" + "="*60)
    print(f"✨ 收割大告捷：成功永久同步并压缩 {success_count}/{len(TICKERS)} 个标的历史高频 1分钟 数据库！")
    print("💡 提示：这批数据已安全保存在本地 learning/ 文件夹下，可随时用于盘中高频 ORB 突破和 morning washouts 离线研究！")
    print("="*60)

if __name__ == "__main__":
    main()
