"""
个股太空舱数据迁移工具 — migrate_to_capsule.py
一键扫描 findings/ 目录下的所有历史平铺数据，自动归档至 findings/symbols/{SYM}/ 对应的个股隔离太空舱中，
并自动提取最新一天的交易计划参数以初始化其专属 strategy.json 策略存档文件。
"""
import os
import re
import shutil
import json
import argparse
from datetime import datetime, timezone

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive", "tools"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive", "tools"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))

# List of agents who generate per-stock files
AGENT_NAMES = ["FundAgent", "MacroAgent", "TechAgent", "RiskAgent", "SectorAgent", "SentimentAgent", "CommunityAgent"]

def migrate(dry_run=False):
    find_dir = os.path.join(BASE, "findings")
    if not os.path.exists(find_dir):
        print(f"Error: Findings directory does not exist at {find_dir}")
        return

    print(f"Starting data migration to Stock Capsule under: {find_dir}")
    if dry_run:
        print("=== RUNNING IN DRY-RUN MODE (NO FILES WILL BE MOVED) ===")

    # Keep track of all discovered tickers and their file modifications
    symbols_found = set()
    files_moved_count = 0

    # 1. Migrate root-level strategic memo files
    print("\n--- 1. Migrating root-level strategic memo files ---")
    for fname in os.listdir(BASE):
        m = re.match(r"^strategic_memo_([A-Z0-9]+)\.json$", fname)
        if m:
            sym = m.group(1)
            symbols_found.add(sym)
            src_path = os.path.join(BASE, fname)
            capsule_dir = os.path.join(find_dir, "symbols", sym)
            dst_path = os.path.join(capsule_dir, f"strategic_memo.json")

            print(f"Memo: {fname} -> symbols/{sym}/strategic_memo.json")
            if not dry_run:
                os.makedirs(capsule_dir, exist_ok=True)
                shutil.move(src_path, dst_path)
            files_moved_count += 1

    # 2. Migrate files inside findings/
    print("\n--- 2. Migrating flat files in findings/ ---")
    for fname in os.listdir(find_dir):
        src_path = os.path.join(find_dir, fname)
        if not os.path.isfile(src_path):
            continue

        # Case A: premarket_summary_{date}_{sym}.json
        m_pm = re.match(r"^premarket_summary_(\d{4}-\d{2}-\d{2})_([A-Z0-9]+)\.json$", fname)
        if m_pm:
            date, sym = m_pm.group(1), m_pm.group(2)
            symbols_found.add(sym)
            dst_dir = os.path.join(find_dir, "symbols", sym, "plans")
            dst_path = os.path.join(dst_dir, f"premarket_summary_{date}.json")
            
            print(f"Plan: {fname} -> symbols/{sym}/plans/premarket_summary_{date}.json")
            if not dry_run:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src_path, dst_path)
            files_moved_count += 1
            continue

        # Case B: intraday_snapshot_{date}_{sym}.jsonl
        m_snap = re.match(r"^intraday_snapshot_(\d{4}-\d{2}-\d{2})_([A-Z0-9]+)\.jsonl$", fname)
        if m_snap:
            date, sym = m_snap.group(1), m_snap.group(2)
            symbols_found.add(sym)
            dst_dir = os.path.join(find_dir, "symbols", sym, "snapshots")
            dst_path = os.path.join(dst_dir, f"intraday_snapshot_{date}.jsonl")
            
            print(f"Snapshot: {fname} -> symbols/{sym}/snapshots/intraday_snapshot_{date}.jsonl")
            if not dry_run:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src_path, dst_path)
            files_moved_count += 1
            continue

        # Case C: debate_{sym}_{date}.jsonl
        m_deb = re.match(r"^debate_([A-Z0-9]+)_(\d{4}-\d{2}-\d{2})\.jsonl$", fname)
        if m_deb:
            sym, date = m_deb.group(1), m_deb.group(2)
            symbols_found.add(sym)
            dst_dir = os.path.join(find_dir, "symbols", sym, "debates")
            dst_path = os.path.join(dst_dir, f"debate_{date}.jsonl")
            
            print(f"Debate: {fname} -> symbols/{sym}/debates/debate_{date}.jsonl")
            if not dry_run:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src_path, dst_path)
            files_moved_count += 1
            continue

        # Case D: narrative_{sym}_{date}.json
        m_nar = re.match(r"^narrative_([A-Z0-9]+)_(\d{4}-\d{2}-\d{2})\.json$", fname)
        if m_nar:
            sym, date = m_nar.group(1), m_nar.group(2)
            symbols_found.add(sym)
            dst_dir = os.path.join(find_dir, "symbols", sym, "debates")
            dst_path = os.path.join(dst_dir, f"narrative_{date}.json")
            
            print(f"Narrative: {fname} -> symbols/{sym}/debates/narrative_{date}.json")
            if not dry_run:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src_path, dst_path)
            files_moved_count += 1
            continue

        # Case E: {AgentName}_{sym}_{date}.json
        moved_agent = False
        for agent in AGENT_NAMES:
            pattern = rf"^{agent}_([A-Z0-9]+)_(\d{{4}}-\d{{2}}-\d{{2}})\.json$"
            m_agt = re.match(pattern, fname)
            if m_agt:
                sym, date = m_agt.group(1), m_agt.group(2)
                symbols_found.add(sym)
                dst_dir = os.path.join(find_dir, "symbols", sym, "debates")
                dst_path = os.path.join(dst_dir, f"{agent}_{date}.json")
                
                print(f"Agent opinion: {fname} -> symbols/{sym}/debates/{agent}_{date}.json")
                if not dry_run:
                    os.makedirs(dst_dir, exist_ok=True)
                    shutil.move(src_path, dst_path)
                files_moved_count += 1
                moved_agent = True
                break
        
        if moved_agent:
            continue

    # 3. Initialize Capsule strategy.json for each discovered symbol
    print("\n--- 3. Initializing capsule strategy.json fallbacks ---")
    for sym in symbols_found:
        capsule_dir = os.path.join(find_dir, "symbols", sym)
        strat_path = os.path.join(capsule_dir, "strategy.json")
        
        # Look for the latest premarket summary we just moved
        plans_dir = os.path.join(capsule_dir, "plans")
        latest_plan = None
        if os.path.exists(plans_dir):
            plans = sorted([f for f in os.listdir(plans_dir) if f.startswith("premarket_summary_")])
            if plans:
                latest_plan = os.path.join(plans_dir, plans[-1])

        # Default fallback structure
        strategy_data = {
            "symbol": sym,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "key_levels": {
                "entry_low": None,
                "entry_high": None,
                "stop_loss": None,
                "target_price": None
            },
            "exit_plan": {
                "flex_add_level": None,
                "flex_reduce_level": None
            },
            "thesis": {
                "status": "intact",
                "today_falsification": []
            }
        }

        # Parse levels from latest plan if found
        if latest_plan and os.path.exists(latest_plan):
            try:
                with open(latest_plan, encoding="utf-8") as f:
                    plan_data = json.load(f)
                
                # Extract premarket entry/exit fields
                entry = plan_data.get("entry", {})
                exit = plan_data.get("exit", {})
                thesis = plan_data.get("thesis", {})
                
                strategy_data["key_levels"] = {
                    "entry_low": entry.get("entry_low") or entry.get("entry_base"),
                    "entry_high": entry.get("entry_high"),
                    "stop_loss": entry.get("stop_loss"),
                    "target_price": entry.get("target_price")
                }
                strategy_data["exit_plan"] = {
                    "flex_add_level": exit.get("flex_add_level"),
                    "flex_reduce_level": exit.get("flex_reduce_level")
                }
                strategy_data["thesis"] = {
                    "status": thesis.get("status", "intact"),
                    "today_falsification": thesis.get("today_falsification") or []
                }
                print(f"Parsed latest parameters for {sym} from {os.path.basename(latest_plan)}")
            except Exception as ex:
                print(f"Warning: Failed to parse parameters for {sym}: {ex}")

        # Save strategy.json
        if not dry_run:
            os.makedirs(capsule_dir, exist_ok=True)
            with open(strat_path, "w", encoding="utf-8") as f:
                json.dump(strategy_data, f, indent=2, ensure_ascii=False)
            print(f"Created permanent strategy: symbols/{sym}/strategy.json")
        else:
            print(f"Would create permanent strategy: symbols/{sym}/strategy.json")

    print("\n=======================================================")
    if dry_run:
        print(f"Dry-run finished. Would reorganize {files_moved_count} files across {len(symbols_found)} stock capsules.")
    else:
        print(f"Migration completed successfully! Reorganized {files_moved_count} files across {len(symbols_found)} stock capsules.")
    print("=======================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate stock files to capsule folders.")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry-run simulation.")
    args = parser.parse_args()
    
    migrate(dry_run=args.dry_run)
