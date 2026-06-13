import os
import sys
import requests
import sqlite3
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

# 300 highly liquid, representative US stocks (S&P 500 constituents)
TICKERS_300 = [
    # --- Technology (70) ---
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'TSM', 'AMD', 'NFLX',
    'ADBE', 'CRM', 'QCOM', 'ORCL', 'CSCO', 'TXN', 'INTC', 'MU', 'AMAT', 'LRCX',
    'PANW', 'SNPS', 'CDNS', 'ASML', 'KLAC', 'FTNT', 'NOW', 'IBM', 'INTU', 'APH',
    'MSI', 'TEL', 'HPQ', 'DELL', 'ANET', 'ANSS', 'KEYS', 'FISV', 'FIS', 'JKHY',
    'PAYX', 'CTSH', 'IT', 'TYL', 'LDOS', 'EPAM', 'GLW', 'STX', 'WDC', 'QRVO',
    'SWKS', 'MPWR', 'ON', 'MCHP', 'ADI', 'NXPI', 'FSLR', 'ENPH', 'SEDG', 'DDOG',
    'NET', 'OKTA', 'CRWD', 'WDAY', 'TEAM', 'PLTR', 'SNOW', 'MDB', 'ZS', 'SPLK',
    
    # --- Finance & Payments (50) ---
    'JPM', 'BAC', 'MS', 'GS', 'V', 'MA', 'AXP', 'DFS', 'COF', 'SYF',
    'BLK', 'SPGI', 'MCO', 'C', 'WFC', 'PNC', 'USB', 'TFC', 'SCHW', 'BK',
    'STT', 'AMP', 'TROW', 'BEN', 'IVZ', 'AMG', 'FITB', 'HBAN', 'KEY', 'RF',
    'CMA', 'ZION', 'SBNY', 'MKTX', 'CBOE', 'NDAQ', 'CME', 'ICE', 'MSCI', 'AON',
    'MMC', 'WTW', 'AJG', 'BRO', 'PGR', 'ALL', 'TRV', 'CB', 'AIG', 'MET',
    
    # --- Healthcare & Biotech (50) ---
    'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'TMO', 'DHR', 'ABT', 'MDT',
    'ISRG', 'SYK', 'BSX', 'BDX', 'GILD', 'REGN', 'AMGN', 'VRTX', 'BIIB', 'mRNA',
    'IQV', 'A', 'WST', 'RVTY', 'MTD', 'WAT', 'ZTS', 'IDXX', 'ALGN', 'XRAY',
    'DXCM', 'PODD', 'EW', 'STE', 'RMD', 'MCK', 'CAH', 'ABC', 'HUM', 'CI',
    'CNC', 'ELV', 'HCA', 'UHS', 'THC', 'BXP', 'VTR', 'WELL', 'PEAK', 'DOC',
    
    # --- Consumer Discretionary (40) ---
    'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'ORLY', 'AZO', 'ULTA',
    'TGT', 'DG', 'DLTR', 'WMT', 'COST', 'BBY', 'TSCO', 'ROST', 'LVS', 'WYNN',
    'MGM', 'RCL', 'CCL', 'NCLH', 'MAR', 'HLT', 'H', 'YUM', 'DRI', 'CMG',
    'DPZ', 'WEN', 'MCD', 'LEN', 'DHI', 'PHM', 'TOL', 'NVR', 'GRMN', 'HAS',
    
    # --- Consumer Staples & Services (30) ---
    'KO', 'PEP', 'PG', 'CL', 'KMB', 'EL', 'COTY', 'REV', 'CHD', 'HRB',
    'GIS', 'K', 'HNZ', 'MDLZ', 'HSY', 'CAG', 'CPB', 'SJM', 'ADM', 'BG',
    'WBA', 'CVS', 'SYY', 'USFD', 'PFG', 'STZ', 'BF.B', 'TAP', 'MNST', 'CLX',
    
    # --- Energy & Industrials (40) ---
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'BKR', 'OXY', 'DVN', 'HES',
    'GE', 'CAT', 'HON', 'LMT', 'BA', 'RTX', 'NOC', 'GD', 'HWM', 'TXT',
    'DE', 'UNP', 'CSX', 'NSC', 'FDX', 'UPS', 'EMR', 'ETN', 'ITW', 'PH',
    'AME', 'ROK', 'FAST', 'GWW', 'ODFL', 'JBHT', 'CHRW', 'EXPD', 'LUV', 'DAL',
    
    # --- Materials, Utilities & Real Estate (20) ---
    'FCX', 'NEM', 'APD', 'SHW', 'ECL', 'DD', 'DOW', 'CTVA', 'CF', 'MOS',
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'ED', 'PEG', 'AMT', 'CCI'
]

# Ensure uniqueness and sort
TICKERS_300 = sorted(list(set(TICKERS_300)))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning", "corporate_actions.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create splits table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS splits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        execution_date TEXT NOT NULL,
        split_from REAL NOT NULL,
        split_to REAL NOT NULL,
        declared_date TEXT,
        ratio TEXT,
        UNIQUE(ticker, execution_date)
    )
    """)
    
    # Create dividends table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dividends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        ex_dividend_date TEXT NOT NULL,
        payment_date TEXT,
        record_date TEXT,
        declaration_date TEXT,
        amount REAL NOT NULL,
        frequency INTEGER,
        dividend_type TEXT,
        cash_amount REAL,
        currency TEXT,
        UNIQUE(ticker, ex_dividend_date)
    )
    """)
    
    conn.commit()
    conn.close()

def save_splits(ticker, splits_list):
    if not splits_list:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted = 0
    for split in splits_list:
        exec_date = split.get("execution_date")
        if not exec_date:
            continue
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO splits 
            (ticker, execution_date, split_from, split_to, declared_date, ratio)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                exec_date,
                split.get("split_from", 1.0),
                split.get("split_to", 1.0),
                split.get("declared_date"),
                f"{split.get('split_to')}:{split.get('split_from')}"
            ))
            inserted += 1
        except Exception as e:
            pass
            
    conn.commit()
    conn.close()
    if inserted > 0:
        print(f"   📊 成功保存 {inserted} 条拆股记录。")

def save_dividends(ticker, dividends_list):
    if not dividends_list:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted = 0
    for div in dividends_list:
        ex_date = div.get("ex_dividend_date")
        if not ex_date:
            continue
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO dividends 
            (ticker, ex_dividend_date, payment_date, record_date, declaration_date, amount, frequency, dividend_type, cash_amount, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                ex_date,
                div.get("payment_date"),
                div.get("record_date"),
                div.get("declaration_date"),
                div.get("amount", 0.0),
                div.get("frequency", 4),
                div.get("dividend_type", "CD"),
                div.get("cash_amount", 0.0),
                div.get("currency", "USD")
            ))
            inserted += 1
        except Exception as e:
            pass
            
    conn.commit()
    conn.close()
    if inserted > 0:
        print(f"   💰 成功保存 {inserted} 条分红记录。")

def fetch_corporate_actions(ticker, api_key):
    session = requests.Session()
    
    # 1. Fetch Splits
    splits = []
    splits_url = f"https://api.polygon.io/v3/reference/splits?ticker={ticker}&limit=1000&apiKey={api_key}"
    try:
        r = session.get(splits_url, timeout=10)
        if r.status_code == 200:
            res = r.json()
            splits = res.get("results", [])
            save_splits(ticker, splits)
        else:
            print(f"   ⚠️ 获取拆股失败: {r.status_code}")
    except Exception as e:
        print(f"   ❌ 获取拆股异常: {e}")
        
    # 2. Fetch Dividends
    dividends = []
    div_url = f"https://api.polygon.io/v3/reference/dividends?ticker={ticker}&limit=1000&apiKey={api_key}"
    try:
        r = session.get(div_url, timeout=10)
        if r.status_code == 200:
            res = r.json()
            dividends = res.get("results", [])
            save_dividends(ticker, dividends)
        else:
            print(f"   ⚠️ 获取分红失败: {r.status_code}")
    except Exception as e:
        print(f"   ❌ 获取分红异常: {e}")

def main():
    print("============================================================")
    print("🚀 Polygon.io 历史拆股分红数据库极限收割同步器")
    print("============================================================")
    
    if not API_KEY:
        print("🔴 错误: 未能在 .env 文件中检测到有效 POLYGON_API_KEY。")
        print("============================================================")
        return
        
    init_db()
    print(f"✅ SQLite 本地数据库已初始化: {DB_PATH}")
    print(f"✅ 开始同步 {len(TICKERS_300)} 支核心资产的完整公司行为数据...")
    
    success_count = 0
    for idx, ticker in enumerate(TICKERS_300, 1):
        print(f"📡 [{idx}/{len(TICKERS_300)}] 正在获取 {ticker} 的拆股与分红历史...")
        try:
            # Sleep slightly to avoid throttling
            time.sleep(0.05)
            fetch_corporate_actions(ticker, API_KEY)
            success_count += 1
        except KeyboardInterrupt:
            print("\n👋 收到中断信号，退出同步。")
            break
        except Exception as e:
            print(f"🔴 {ticker} 处理失败: {e}")
            
    print("\n" + "="*60)
    print(f"✨ 收割大告捷：成功同步并离线缓存 {success_count}/{len(TICKERS_300)} 个标的完整的拆分分红元数据库！")
    print(f"💡 本地SQLite数仓路径: {DB_PATH}")
    print("="*60)

if __name__ == "__main__":
    main()
