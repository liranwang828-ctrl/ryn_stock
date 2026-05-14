"""
日志清理工具 — 轻量级，按需运行（无需定时，空间基本不是问题）

策略：
  - premarket_analysis / opening_scenarios：保留60天，更早的删除
  - session_*.md：保留90天，更早的压缩到 archive/
  - paper_trading/*/evolution.jsonl：超过10MB时保留最近5000条
  - trading_history.jsonl：永久保留（增速极慢）
  - reports/*.html：保留30天

用法：python3.12 agents/cleanup.py [--dry-run]
"""
import os, sys, gzip, json, shutil
from datetime import datetime, timedelta, timezone

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY_RUN = "--dry-run" in sys.argv

def log(msg):
    print(f"  {'[DRY]' if DRY_RUN else '[DEL]'} {msg}")

def rm(path):
    if not DRY_RUN:
        os.remove(path)

def cutoff(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

freed = 0

# ── 1. 日期型文件（premarket / opening_scenarios）─────────────
for pattern, keep_days in [("premarket_analysis_", 60), ("opening_scenarios_", 60)]:
    cut = cutoff(keep_days)
    for f in os.listdir(BASE):
        if f.startswith(pattern) and f.endswith(".json"):
            date_str = f.replace(pattern,"").replace(".json","")
            if date_str < cut:
                path = os.path.join(BASE, f)
                size = os.path.getsize(path)
                log(f"{f}  ({size//1024}KB)")
                rm(path)
                freed += size

# ── 2. session 日志（90天后压缩归档）─────────────────────────
knowledge_dir = os.path.join(BASE, "knowledge")
archive_dir   = os.path.join(BASE, "knowledge", "archive")
os.makedirs(archive_dir, exist_ok=True)
cut90 = cutoff(90)
for f in os.listdir(knowledge_dir):
    if f.startswith("session_") and f.endswith(".md"):
        date_str = f.replace("session_","").replace(".md","")
        if date_str < cut90:
            src  = os.path.join(knowledge_dir, f)
            dst  = os.path.join(archive_dir, f + ".gz")
            size = os.path.getsize(src)
            log(f"{f} → archive/ ({size//1024}KB)")
            if not DRY_RUN:
                with open(src,'rb') as fi, gzip.open(dst,'wb') as fo:
                    fo.write(fi.read())
                os.remove(src)
            freed += size

# ── 3. reports/*.html（30天）──────────────────────────────────
reports_dir = os.path.join(BASE, "reports")
if os.path.exists(reports_dir):
    cut30 = cutoff(30)
    for f in os.listdir(reports_dir):
        if f.endswith(".html"):
            date_str = f[:10]  # YYYY-MM-DD
            if date_str < cut30:
                path = os.path.join(reports_dir, f)
                size = os.path.getsize(path)
                log(f"reports/{f}  ({size//1024}KB)")
                rm(path)
                freed += size

# ── 4. paper_trading evolution.jsonl 轮转（>10MB保留最近5000条）
PT_DIR = os.path.join(BASE, "paper_trading")
MAX_EVO_MB = 10
KEEP_LINES = 5000
for acct in ["strict","base","loose"]:
    evo = os.path.join(PT_DIR, acct, "evolution.jsonl")
    if not os.path.exists(evo):
        continue
    size = os.path.getsize(evo)
    if size > MAX_EVO_MB * 1024 * 1024:
        with open(evo) as f:
            lines = f.readlines()
        keep = lines[-KEEP_LINES:]
        log(f"paper_trading/{acct}/evolution.jsonl 轮转  "
            f"({size//1024//1024}MB → 保留{KEEP_LINES}条)")
        if not DRY_RUN:
            with open(evo, "w") as f:
                f.writelines(keep)
        freed += size - sum(len(l) for l in keep)

# ── 汇总 ─────────────────────────────────────────────────────
print(f"\n{'预计' if DRY_RUN else '已'}释放: {freed/1024/1024:.1f}MB")

# 当前使用量
total = sum(
    os.path.getsize(os.path.join(r,f))
    for r,_,files in os.walk(BASE)
    for f in files
)
print(f"当前总占用: {total/1024/1024:.1f}MB")
