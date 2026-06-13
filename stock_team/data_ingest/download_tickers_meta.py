import os
import sys
import requests
import json
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

# Same 300 high-liquidity stock list
TICKERS_300 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX',
    'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'TXN', 'INTC', 'MU', 'AMAT', 'LRCX',
    'PANW', 'SNPS', 'CDNS', 'ASML', 'KLAC', 'FTNT', 'NOW', 'IBM', 'INTU', 'APH',
    'MSI', 'TEL', 'HPQ', 'DELL', 'ANET', 'ANSS', 'KEYS', 'FISV', 'FIS', 'JKHY',
    'PAYX', 'CTSH', 'IT', 'TYL', 'LDOS', 'EPAM', 'GLW', 'STX', 'WDC', 'QRVO',
    'SWKS', 'MPWR', 'ON', 'MCHP', 'ADI', 'NXPI', 'FSLR', 'ENPH', 'SEDG', 'DDOG',
    'NET', 'OKTA', 'CRWD', 'WDAY', 'TEAM', 'PLTR', 'SNOW', 'MDB', 'ZS', 'SPLK',
    'JPM', 'BAC', 'MS', 'GS', 'V', 'MA', 'AXP', 'DFS', 'COF', 'SYF',
    'BLK', 'SPGI', 'MCO', 'C', 'WFC', 'PNC', 'USB', 'TFC', 'SCHW', 'BK',
    'STT', 'AMP', 'TROW', 'BEN', 'IVZ', 'AMG', 'FITB', 'HBAN', 'KEY', 'RF',
    'CMA', 'ZION', 'SBNY', 'MKTX', 'CBOE', 'NDAQ', 'CME', 'ICE', 'MSCI', 'AON',
    'MMC', 'WTW', 'AJG', 'BRO', 'PGR', 'ALL', 'TRV', 'CB', 'AIG', 'MET',
    'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'DHR', 'ABT', 'MDT',
    'ISRG', 'SYK', 'BSX', 'BDX', 'GILD', 'REGN', 'AMGN', 'VRTX', 'BIIB', 'mRNA',
    'IQV', 'A', 'WST', 'RVTY', 'MTD', 'WAT', 'ZTS', 'IDXX', 'ALGN', 'XRAY',
    'DXCM', 'PODD', 'EW', 'STE', 'RMD', 'MCK', 'CAH', 'ABC', 'HUM', 'CI',
    'CNC', 'ELV', 'HCA', 'UHS', 'THC', 'BXP', 'VTR', 'WELL', 'PEAK', 'DOC',
    'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'ORLY', 'AZO', 'ULTA',
    'TGT', 'DG', 'DLTR', 'WMT', 'COST', 'BBY', 'TSCO', 'ROST', 'LVS', 'WYNN',
    'MGM', 'RCL', 'CCL', 'NCLH', 'MAR', 'HLT', 'H', 'YUM', 'DRI', 'CMG',
    'DPZ', 'WEN', 'LEN', 'DHI', 'PHM', 'TOL', 'NVR', 'GRMN', 'HAS',
    'KO', 'PEP', 'PG', 'CL', 'KMB', 'EL', 'COTY', 'REV', 'CHD', 'HRB',
    'GIS', 'K', 'HNZ', 'MDLZ', 'HSY', 'CAG', 'CPB', 'SJM', 'ADM', 'BG',
    'WBA', 'CVS', 'SYY', 'USFD', 'PFG', 'STZ', 'BF.B', 'TAP', 'MNST', 'CLX',
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'BKR', 'OXY', 'DVN', 'HES',
    'GE', 'CAT', 'HON', 'LMT', 'BA', 'RTX', 'NOC', 'GD', 'HWM', 'TXT',
    'DE', 'UNP', 'CSX', 'NSC', 'FDX', 'UPS', 'EMR', 'ETN', 'ITW', 'PH',
    'AME', 'ROK', 'FAST', 'GWW', 'ODFL', 'JBHT', 'CHRW', 'EXPD', 'LUV', 'DAL',
    'FCX', 'NEM', 'APD', 'SHW', 'ECL', 'DD', 'DOW', 'CTVA', 'CF', 'MOS',
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'ED', 'PEG', 'AMT', 'CCI'
]

TICKERS_300 = sorted(list(set(TICKERS_300)))

META_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning", "ticker_metadata.json")

def load_existing_meta():
    if os.path.exists(META_FILE_PATH):
        try:
            with open(META_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_meta(meta_dict):
    with open(META_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(meta_dict, f, indent=2, ensure_ascii=False)

def fetch_ticker_details(ticker, api_key):
    # API details v3
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={api_key}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            res = r.json()
            results = res.get("results", {})
            return results
        else:
            print(f"   ❌ 获取 {ticker} 元数据失败: {r.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        return None

def main():
    print("============================================================")
    print("🚀 Polygon.io 行业画像与市值流通盘元数据库极限收割机")
    print("============================================================")
    
    if not API_KEY:
        print("🔴 错误: 未能在 .env 文件中检测到有效 POLYGON_API_KEY。")
        print("============================================================")
        return
        
    meta_db = load_existing_meta()
    print(f"✅ 已加载现有元数据，包含 {len(meta_db)} 个股票的记录。")
    print(f"✅ 启动同步并离线化 {len(TICKERS_300)} 支标的的元数据...")
    
    new_fetches = 0
    for idx, ticker in enumerate(TICKERS_300, 1):
        # Resume-on-failure optimization
        if ticker in meta_db and meta_db[ticker] and "market_cap" in meta_db[ticker]:
            print(f"   🟢 [{idx}/{len(TICKERS_300)}] {ticker} 元数据已存在本地且完整，跳过。")
            continue
            
        print(f"📡 [{idx}/{len(TICKERS_300)}] 正在从 Polygon 获取 {ticker} 完整画像与基本元数据...")
        time.sleep(0.05)
        details = fetch_ticker_details(ticker, API_KEY)
        
        if details:
            # Extract key fields we care about
            cleaned_details = {
                "name": details.get("name"),
                "sic_code": details.get("sic_code"),
                "sic_description": details.get("sic_description"),
                "market_cap": details.get("market_cap"),
                "share_class_shares_outstanding": details.get("share_class_shares_outstanding"),
                "weighted_shares_outstanding": details.get("weighted_shares_outstanding"),
                "list_date": details.get("list_date"),
                "description": details.get("description"),
                "homepage_url": details.get("homepage_url"),
                "total_employees": details.get("total_employees"),
                "locale": details.get("locale"),
                "primary_exchange": details.get("primary_exchange")
            }
            
            meta_db[ticker] = cleaned_details
            new_fetches += 1
            
            # Periodically save progress to survive crashes
            if new_fetches % 10 == 0:
                save_meta(meta_db)
                print(f"   💾 进度自动保存: 本地数据库当前已保存 {len(meta_db)} 个标的。")
                
    save_meta(meta_db)
    print("\n" + "="*60)
    print(f"✨ 永续元数据收割同步大成功！")
    print(f"   当前本地元数据库共包含: {len(meta_db)}/{len(TICKERS_300)} 个股票的详细信息。")
    print(f"   数据文件路径: {META_FILE_PATH}")
    print("============================================================")

if __name__ == "__main__":
    main()
