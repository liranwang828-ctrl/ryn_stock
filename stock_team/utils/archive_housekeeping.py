# scripts/archive_housekeeping.py
"""
Archive Housekeeping Utility
Moves dated session files from findings/ and diagnostic scripts from scratch/ into archive vaults.
"""
import os
import shutil
import re

# Resolve base directory
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINDINGS_DIR = os.path.join(BASE, "findings")
SCRATCH_DIR = os.path.join(BASE, "scratch")
ARCHIVE_DIR = os.path.join(BASE, "archive")

# Define target vaults
FINDINGS_VAULT = os.path.join(ARCHIVE_DIR, "findings_history")
SCRATCH_VAULT = os.path.join(ARCHIVE_DIR, "scratch_history")
COG_VAULT = os.path.join(ARCHIVE_DIR, "cognitive_assets")

# Ensure target directories exist
os.makedirs(FINDINGS_VAULT, exist_ok=True)
os.makedirs(SCRATCH_VAULT, exist_ok=True)
os.makedirs(COG_VAULT, exist_ok=True)

# Date matching regex (YYYY-MM-DD or YYYYMMDD)
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})|(\d{8})")

def is_cognitive_industry_report(filename):
    """Identifies core qualitative research reports in findings/"""
    name_lower = filename.lower()
    return ("industry" in name_lower or "research" in name_lower or "方案" in name_lower) and filename.endswith(".md")

def clean_findings():
    """Archives dated findings and moves industry reports to cognitive vault"""
    print("[CLEANING] Cleaning findings/ directory...")
    if not os.path.exists(FINDINGS_DIR):
        print("   findings/ directory does not exist. Skipping.")
        return

    # Keep list for active current assets
    protected_findings = {
        "00_README.md", "01_methodology.md", "02_portfolio_strategy.md",
        "portfolio_snapshot_current.json", "watchlist_live_status.json",
        "contextual-trade-evidence-SNXX-2026-06-04.md" # SNXX Regression fixture
    }

    count = 0
    for filename in os.listdir(FINDINGS_DIR):
        filepath = os.path.join(FINDINGS_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        
        if filename in protected_findings:
            continue

        # Rule 1: Industry reports go to cognitive assets vault
        if is_cognitive_industry_report(filename):
            dest_path = os.path.join(COG_VAULT, filename)
            shutil.move(filepath, dest_path)
            print(f"   [MIGRATED COGNITION] {filename} -> archive/cognitive_assets/")
            count += 1
            continue

        # Rule 2: Files containing date patterns or session-prefix JSONs go to findings vault
        is_dated = DATE_PATTERN.search(filename) is not None
        is_session_output = any(filename.startswith(prefix) for prefix in [
            "CommunityAgent_", "FundAgent_", "MacroAgent_", "RiskAgent_", 
            "SectorAgent_", "SentimentAgent_", "TechAgent_", "debate_", 
            "narrative_", "intraday_snapshot_", "entry_decision_", 
            "exit_decision_", "order_sheet_", "portfolio_snapshot_", 
            "postmarket_", "premarket_", "watch_scan_", "opt_log_", 
            "backtest_", "best_search_", "parameter_", "random_", "factor_"
        ])

        if is_dated or is_session_output:
            dest_path = os.path.join(FINDINGS_VAULT, filename)
            shutil.move(filepath, dest_path)
            print(f"   [ARCHIVED FINDING] {filename} -> archive/findings_history/")
            count += 1

    print(f"[SUCCESS] Finished findings/ cleanup. Archived {count} files.\n")

def clean_scratch():
    """Archives all diagnostic scratch scripts and text reports to scratch vault"""
    print("[CLEANING] Cleaning scratch/ directory...")
    if not os.path.exists(SCRATCH_DIR):
        print("   scratch/ directory does not exist. Skipping.")
        return

    protected_scratch = {
        "AI_research_package" # Keep subdirectory
    }

    count = 0
    for filename in os.listdir(SCRATCH_DIR):
        filepath = os.path.join(SCRATCH_DIR, filename)
        if filename in protected_scratch:
            continue
        
        # We only move files
        if not os.path.isfile(filepath):
            continue

        dest_path = os.path.join(SCRATCH_VAULT, filename)
        shutil.move(filepath, dest_path)
        print(f"   [ARCHIVED SCRATCH] {filename} -> archive/scratch_history/")
        count += 1

    print(f"[SUCCESS] Finished scratch/ cleanup. Archived {count} files.\n")

def clean_root_temp_files():
    """Cleans up temporary data files from the repository root"""
    print("[CLEANING] Cleaning temporary root cache files...")
    root_temp_files = [
        "data_raw_primary.json",
        "data_raw_secondary.json",
        "sweep_progress.txt"
    ]
    
    count = 0
    for filename in root_temp_files:
        filepath = os.path.join(BASE, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"   [DELETED TEMP] {filename} from root")
            count += 1
            
    print(f"[SUCCESS] Finished root temp file cleanup. Deleted {count} files.\n")

def run():
    clean_findings()
    clean_scratch()
    clean_root_temp_files()
    print("[FINISHED] Archiving & Housekeeping successfully completed!")

if __name__ == "__main__":
    run()
