import os
import sys
import pandas as pd
from datetime import datetime
import pytz

# Force UTF-8 printing
sys.stdout.reconfigure(encoding='utf-8')

try:
    import yfinance as yf
except ImportError:
    print("🔴 错误: 本地未安装 yfinance，无法进行免费增量同步。")
    print("💡 请先在终端运行: pip install yfinance")
    sys.exit(1)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning")

def delta_sync_ticker(ticker):
    cache_path = os.path.join(CACHE_DIR, f"intraday_cache_{ticker}.csv")
    if not os.path.exists(cache_path):
        print(f"🟡 {ticker} 在本地未检测到基础 5-Min 历史缓存，跳过增量同步。")
        return False
        
    print(f"\n📡 启动 {ticker} 免费增量增益拼接同步 (yfinance)...")
    
    # 1. Read existing local cache
    try:
        df_local = pd.read_csv(cache_path)
        # Parse datetime and handle UTC index
        if 'Datetime' in df_local.columns:
            df_local['Datetime'] = pd.to_datetime(df_local['Datetime'], utc=True)
            df_local = df_local.set_index('Datetime')
        elif 'Unnamed: 0' in df_local.columns:
            df_local = df_local.rename(columns={'Unnamed: 0': 'Datetime'})
            df_local['Datetime'] = pd.to_datetime(df_local['Datetime'], utc=True)
            df_local = df_local.set_index('Datetime')
        else:
            # Assumes index is already Datetime
            df_local.index = pd.to_datetime(df_local.index, utc=True)
    except Exception as e:
        print(f"   ❌ 读取或解析本地缓存失败: {e}")
        return False
        
    if df_local.empty:
        print(f"   ❌ 本地缓存数据为空！")
        return False
        
    # Get last timestamp in local data
    last_timestamp = df_local.index[-1]
    last_timestamp_ny = last_timestamp.tz_convert('America/New_York')
    print(f"   📅 本地缓存最新数据时间: {last_timestamp_ny.strftime('%Y-%m-%d %H:%M:%S')} (纽约时间)")
    
    now_utc = datetime.now(pytz.utc)
    now_ny = now_utc.tz_convert('America/New_York')
    
    # Calculate time delta in hours
    time_delta = now_utc - last_timestamp
    hours_behind = time_delta.total_seconds() / 3600.0
    
    # If we are behind by less than 2 hours or it's a weekend and we've already synced Friday, skip
    if hours_behind < 2.0:
        print(f"   🟢 本地数据已是最新 (仅落后 {hours_behind:.1f} 小时)，无需同步。")
        return True
        
    # 2. Fetch incremental data from yfinance
    # yfinance only allows retrieving 5m data for the last 60 days
    # If the local data is behind by more than 50 days, warning
    if hours_behind > 24 * 55:
        print(f"   ⚠️ 警告: 本地数据落后了 {hours_behind/24:.1f} 天，yfinance 5分钟级别限制最大回溯60天！")
        
    print(f"   📥 正在从 yfinance 拉取 {ticker} 自 {last_timestamp_ny.strftime('%Y-%m-%d')} 至今的 5m 增量 K线...")
    
    try:
        ticker_yf = yf.Ticker(ticker)
        # Fetch 5m data. yfinance returns datetime index in localized form (usually US/Eastern)
        df_new = ticker_yf.history(start=last_timestamp_ny.strftime('%Y-%m-%d'), interval="5m")
        
        if df_new.empty:
            print("   🟡 yfinance 未返回任何新数据，可能当前是非交易时间或已是最新。")
            return True
            
        # Standardize index to UTC for seamless merging
        df_new.index = pd.to_datetime(df_new.index, utc=True)
        
        # Rename columns to match local cache layout (Open, High, Low, Close, Volume, Dividends, Stock Splits)
        df_new = df_new.rename(columns={
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume',
            'Dividends': 'Dividends',
            'Stock Splits': 'Stock Splits'
        })
        # Keep only matching columns
        cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
        df_new = df_new[cols]
        
        # Filter new data to strictly contain only elements AFTER last_timestamp
        df_new_filtered = df_new[df_new.index > last_timestamp]
        
        if df_new_filtered.empty:
            print("   🟢 过滤后无更新的高频K线，本地数据已保持最新。")
            return True
            
        print(f"   ✅ 成功拉取到 {len(df_new_filtered)} 条新高频K线")
        
        # 3. Merge, Deduplicate and Save
        df_merged = pd.concat([df_local, df_new_filtered])
        # Deduplicate on index
        df_merged = df_merged[~df_merged.index.duplicated(keep='last')]
        df_merged = df_merged.sort_index()
        
        # Save back to CSV
        df_merged.to_csv(cache_path)
        print(f"   💾 增量拼接保存成功！当前本地总条数: {len(df_merged)}")
        print(f"   🔔 数据最新时间已更新为: {df_merged.index[-1].tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"   ❌ yfinance 同步拼接发生异常: {e}")
        return False

def main():
    print("============================================================")
    print("🚀 yfinance 零成本“平替续航”本地数仓增量拼接同步器")
    print("============================================================")
    
    # Get all tickers that have local intraday_cache in learning/
    if not os.path.exists(CACHE_DIR):
        print(f"🔴 错误: 本地未发现 cache 目录: {CACHE_DIR}")
        return
        
    local_files = os.listdir(CACHE_DIR)
    tickers = []
    for f in local_files:
        if f.startswith("intraday_cache_") and f.endswith(".csv"):
            ticker = f.replace("intraday_cache_", "").replace(".csv", "")
            if ticker != "QQQ": # QQQ benchmark is handled separately
                tickers.append(ticker)
                
    tickers = sorted(list(set(tickers)))
    # Add QQQ to sync
    if os.path.exists(os.path.join(CACHE_DIR, "intraday_cache_QQQ.csv")):
        tickers.append("QQQ")
        
    if not tickers:
        print("🟡 本地 learning 文件夹下未检测到任何以 'intraday_cache_*.csv' 命名的股票历史数据库。")
        print("💡 请确保您已先通过 Polygon 数据下载器同步了基础历史数据！")
        return
        
    print(f"✅ 检测到本地已存在 {len(tickers)} 支股票的基础数据库，启动免费增量同步...")
    
    success_count = 0
    for ticker in tickers:
        try:
            if delta_sync_ticker(ticker):
                success_count += 1
        except Exception as e:
            print(f"🔴 同步 {ticker} 发生未捕获异常: {e}")
            
    print("\n" + "="*60)
    print(f"✨ 增量拼接同步完成：成功同步并拼接更新 {success_count}/{len(tickers)} 个标的历史数据库！")
    print("💡 提示：此同步器完全基于免费的 yfinance API，不需要您拥有任何付费订阅即可永久运行。")
    print("="*60)

if __name__ == "__main__":
    main()
