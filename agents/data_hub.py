"""
异步/高并发 SQLite WAL 数据总线模块 — data_hub.py
负责统一存储和高效率检索盘中快照与交易记录，支持 WAL 模式，彻底杜绝高并发文件锁冲突。
"""
import os
import sqlite3
import json
import time
from datetime import datetime, timezone

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
DB_DIR = os.path.join(BASE, "learning")
DB_PATH = os.path.join(DB_DIR, "intraday_data.db")

def retry_sqlite(max_retries=5, delay=0.1):
    """SQLite 锁重试装饰器，保障在高并发写时的绝对稳定性"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_err = None
            for _ in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower():
                        last_err = e
                        time.sleep(delay)
                        continue
                    raise e
            raise last_err
        return wrapper
    return decorator

@retry_sqlite()
def init_db():
    """初始化数据库架构，启用 WAL 模式"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    
    # 启用 WAL 模式，大幅提升多读一写的并发吞吐量
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    
    cursor = conn.cursor()
    
    # 1. 盘中快照表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        sym TEXT NOT NULL,
        ts TEXT NOT NULL,
        price REAL,
        chg_pct REAL,
        vwap_dist_pct REAL,
        rsi14_5m REAL,
        vol_ratio REAL,
        gate_status TEXT,
        master_avg REAL,
        master_consensus TEXT,
        plan_vs_now TEXT,    -- JSON string
        node_snapshot TEXT,  -- JSON string
        action_now TEXT,     -- JSON string
        llm_triggered INTEGER DEFAULT 0,
        llm_trigger TEXT,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. 大师评分表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS master_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        sym TEXT NOT NULL,
        price REAL,
        rs REAL,
        score REAL,
        consensus TEXT,
        persona_scores TEXT, -- JSON string
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 3. 创建极速查询索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snap_date_sym ON snapshots(date, sym);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_date ON master_scores(date);")
    
    conn.commit()
    conn.close()

@retry_sqlite()
def write_snapshot_db(record: dict) -> None:
    """写入单条快照记录到 SQLite"""
    init_db()  # 确保库已初始化
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    
    meta = record.get("meta", {})
    price_now = record.get("price_now", {})
    pvn = record.get("plan_vs_now", {})
    nodes = record.get("node_snapshot", {})
    action = record.get("action_now")
    
    date = meta.get("date", datetime.now().strftime("%Y-%m-%d"))
    sym = meta.get("sym", "").upper()
    ts = record.get("ts", "")
    
    price = float(price_now.get("price", 0.0) or 0.0)
    chg_pct = float(price_now.get("chg_pct", 0.0) or 0.0)
    vwap_dist_pct = float(price_now.get("vwap_dist_pct", 0.0) or 0.0)
    rsi14_5m = float(price_now.get("rsi14_5m", 50.0) or 50.0)
    vol_ratio = float(price_now.get("vol_ratio", 1.0) or 1.0)
    gate_status = price_now.get("gate_status", "未通过")
    
    master_avg = price_now.get("master_avg")
    if master_avg is not None:
        master_avg = float(master_avg)
    master_consensus = price_now.get("master_consensus")
    
    llm_triggered = 1 if meta.get("llm_triggered") else 0
    llm_trigger = meta.get("llm_trigger")
    
    conn.execute("""
    INSERT INTO snapshots (
        date, sym, ts, price, chg_pct, vwap_dist_pct, rsi14_5m, vol_ratio,
        gate_status, master_avg, master_consensus, plan_vs_now, node_snapshot,
        action_now, llm_triggered, llm_trigger
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        date, sym, ts, price, chg_pct, vwap_dist_pct, rsi14_5m, vol_ratio,
        gate_status, master_avg, master_consensus,
        json.dumps(pvn, ensure_ascii=False),
        json.dumps(nodes, ensure_ascii=False),
        json.dumps(action, ensure_ascii=False) if action else None,
        llm_triggered, llm_trigger
    ))
    
    conn.commit()
    conn.close()

@retry_sqlite()
def write_master_score_db(date: str, time_str: str, entry: dict) -> None:
    """写入大师评分日志到 SQLite"""
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    
    scores = entry.get("scores", {})
    for sym, s_data in scores.items():
        price = float(s_data.get("price", 0.0) or 0.0)
        rs = float(s_data.get("rs", 0.0) or 0.0)
        master = s_data.get("master", {})
        score = float(master.get("avg", 0.0) or 0.0)
        consensus = master.get("consensus", "观望")
        
        conn.execute("""
        INSERT INTO master_scores (
            date, time, sym, price, rs, score, consensus, persona_scores
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            date, time_str, sym.upper(), price, rs, score, consensus,
            json.dumps(master, ensure_ascii=False)
        ))
        
    conn.commit()
    conn.close()

@retry_sqlite()
def query_latest_snapshots(date: str, symbols: list[str]) -> dict:
    """批量查询今日最新的快照数据，返回 {sym: record_dict}"""
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    result = {}
    for sym in symbols:
        cursor.execute("""
        SELECT ts, price_now_fields, plan_vs_now, node_snapshot, action_now, llm_triggered, llm_trigger, price, chg_pct, vwap_dist_pct, rsi14_5m, vol_ratio, gate_status, master_avg, master_consensus
        FROM snapshots
        WHERE date = ? AND sym = ?
        ORDER BY id DESC LIMIT 1;
        """, (date, sym.upper()))
        
        row = cursor.fetchone()
        if row:
            # 还原为 poll.py / intraday_snapshot 所需的字典格式
            pvn = json.loads(row[2]) if row[2] else {}
            nodes = json.loads(row[3]) if row[3] else {}
            action = json.loads(row[4]) if row[4] else None
            
            result[sym.upper()] = {
                "ts": row[0],
                "meta": {
                    "date": date,
                    "sym": sym.upper(),
                    "llm_triggered": bool(row[5]),
                    "llm_trigger": row[6]
                },
                "price_now": {
                    "price": row[7],
                    "chg_pct": row[8],
                    "vwap_dist_pct": row[9],
                    "rsi14_5m": row[10],
                    "vol_ratio": row[11],
                    "gate_status": row[12],
                    "master_avg": row[13],
                    "master_consensus": row[14]
                },
                "plan_vs_now": pvn,
                "node_snapshot": nodes,
                "action_now": action
            }
            
    conn.close()
    return result

@retry_sqlite()
def query_llm_events(date: str, symbols: list[str]) -> list[dict]:
    """批量查询今日触发的所有 LLM 决策事件列表，按时间升序"""
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    events = []
    # 如果 symbols 为空，查询全部今日股票
    if not symbols:
        cursor.execute("""
        SELECT sym, ts, price, chg_pct, vwap_dist_pct, rsi14_5m, vol_ratio, gate_status, master_avg, master_consensus, plan_vs_now, node_snapshot, action_now, llm_trigger
        FROM snapshots
        WHERE date = ? AND llm_triggered = 1
        ORDER BY id ASC;
        """, (date,))
    else:
        placeholders = ",".join("?" for _ in symbols)
        query_syms = [sym.upper() for sym in symbols]
        cursor.execute(f"""
        SELECT sym, ts, price, chg_pct, vwap_dist_pct, rsi14_5m, vol_ratio, gate_status, master_avg, master_consensus, plan_vs_now, node_snapshot, action_now, llm_trigger
        FROM snapshots
        WHERE date = ? AND llm_triggered = 1 AND sym IN ({placeholders})
        ORDER BY id ASC;
        """, [date] + query_syms)
        
    for row in cursor.fetchall():
        sym = row[0]
        ts = row[1]
        pvn = json.loads(row[10]) if row[10] else {}
        nodes = json.loads(row[11]) if row[11] else {}
        action = json.loads(row[12]) if row[12] else None
        
        events.append({
            "ts": ts,
            "meta": {
                "date": date,
                "sym": sym,
                "llm_triggered": True,
                "llm_trigger": row[13]
            },
            "price_now": {
                "price": row[2],
                "chg_pct": row[3],
                "vwap_dist_pct": row[4],
                "rsi14_5m": row[5],
                "vol_ratio": row[6],
                "gate_status": row[7],
                "master_avg": row[8],
                "master_consensus": row[9]
            },
            "plan_vs_now": pvn,
            "node_snapshot": nodes,
            "action_now": action
        })
        
    conn.close()
    return events
