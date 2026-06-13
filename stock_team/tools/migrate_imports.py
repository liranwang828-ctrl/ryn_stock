import os
import re

# 映射关系表：旧的文件名/模块名映射到其新的二级目录
# 例如：data_agent -> data_ingest
module_destinations = {
    # utils/
    "protocol": "utils",
    "llm_client": "utils",
    "error_logger": "utils",
    "decision_state_hub": "utils",
    "capsule_utils": "utils",
    "translator": "utils",
    "unified_confidence": "utils",
    "market_calendar": "utils",
    "market_clock": "utils",
    "health_check": "utils",
    "question_router": "utils",
    "archive_housekeeping": "utils",
    "check_repo_hygiene": "utils",

    # server/
    "dashboard_server": "server",
    "dashboard_writer": "server",
    "dashboard_cache": "server",
    "report_viewer": "server",
    "dashboard_experience_loop": "server",
    "dashboard_experience_paths": "server",
    "generate_watchlist_ui": "server",

    # core/
    "premarket": "core",
    "poll": "core",
    "entry_guard": "core",
    "paper_trader": "core",
    "ibkr_monitor": "core",
    "ibkr_test_connection": "core",
    "session_manager": "core",
    "session_recorder": "core",
    "premarket_decision": "core",
    "premarket_exit_sheet": "core",
    "premarket_order_sheet": "core",
    "premarket_summary": "core",
    "premarket_watchlist_score": "core",
    "premarket_checklist": "core",
    "premarket_consensus_lock": "core",
    "rebalance_auditor": "core",
    "suggestion_applier.py": "core",
    "portfolio_snapshot": "core",
    "portfolio_macro_guard": "core",
    "position_builder": "core",
    "portfolio_weekly": "core",
    "portfolio_risk_agent": "core",
    "cio": "core",
    "daily_plan": "core",
    "daily_plan_writer": "core",
    "daily_script": "core",
    "generate_report_index": "core",
    "export_trade_evidence": "core",
    "generate_target_orders": "core",
    "tactical_sniper": "core",

    # data_ingest/
    "data_agent": "data_ingest",
    "data_hub": "data_ingest",
    "company_profile_fetcher": "data_ingest",
    "fundamentals_tracker": "data_ingest",
    "intraday_snapshot": "data_ingest",
    "postmarket_data_collector": "data_ingest",
    "postmarket_decision_audit": "data_ingest",
    "postmarket_master_eval": "data_ingest",
    "postmarket_review": "data_ingest",
    "postmarket_sandbox": "data_ingest",
    "postmarket_summary": "data_ingest",
    "postmarket_trade_review": "data_ingest",
    "quick_fundamentals": "data_ingest",
    "research_ingest": "data_ingest",
    "download_1min_stars": "data_ingest",
    "download_massive_intraday": "data_ingest",
    "download_splits_dividends": "data_ingest",
    "download_tickers_meta": "data_ingest",
    "download_tiingo_intraday": "data_ingest",
    "refresh_prices": "data_ingest",
    "delta_sync": "data_ingest",
    "check_vix_regime": "data_ingest",
    "harvest_300_universe": "data_ingest",

    # backtest/
    "backtest_engine": "backtest",
    "backtest_macro": "backtest",
    "backtest_micro": "backtest",
    "backtest_result": "backtest",
    "backtest_runner": "backtest",
    "bootstrap_agent": "backtest",
    "joint_backtest_engine": "backtest",
    "extreme_scenario_stress_tester": "backtest",
    "weekly_rebalance_engine": "backtest",
    "run_tactic_backtest": "backtest",
    "compare_engines": "backtest",
    "run_parameter_sweep": "backtest",
    "run_random_search": "backtest",
    "random_search_v2": "backtest",
    "weekly_engine_parameter_sweep": "backtest",
    "weekly_oos_validator": "backtest",
    "ablation_study": "backtest",
    "ablation_weekly_guards": "backtest",
    "monte_carlo_bootstrap": "backtest",
    "walk_forward_analysis": "backtest",
    "macro_strategy_backtest": "backtest",
    "causal_verification_test": "backtest",
    "debate_bbai_zs": "backtest",
    "factor_ic_analyzer": "backtest",
    "slippage_latency_sweeper": "backtest",

    # agents/ (纯 Agent)
    "tech_agent": "agents",
    "risk_agent": "agents",
    "macro_agent": "agents",
    "sentiment_agent": "agents",
    "fund_agent": "agents",
    "verifier_agent": "agents",
    "sector_agent": "agents",
    "community_agent": "agents",
    "debate_engine": "agents",
    "suggestion_applier": "agents",
    "harvest_agent": "agents",
    "learning_agent": "agents",
    "persona_engine": "agents",
    "report_agent": "agents",
    "strategy_agent": "agents"
}

root_dir = r"D:\gemini\lianghua\stock_team"

def fix_imports_in_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    modified = False

    # 1. 替换 `from agents import XXX` 为 `from stock_team.SUB_DIR import XXX`
    # 2. 替换 `from agents.XXX import YYY` 为 `from stock_team.SUB_DIR.XXX import YYY`
    # 3. 替换 `import agents.XXX` 为 `import stock_team.SUB_DIR.XXX`
    
    # 匹配 `from agents.module import ...` 或 `from agents import module`
    def repl_from_agents(match):
        nonlocal modified
        module_name = match.group(1)
        if module_name in module_destinations:
            sub_dir = module_destinations[module_name]
            modified = True
            return f"from stock_team.{sub_dir}.{module_name}"
        return match.group(0)

    content, count1 = re.subn(r"from\s+agents\.([a-zA-Z0-9_]+)", repl_from_agents, content)
    if count1 > 0:
        modified = True

    # 针对 `import agents.module`
    def repl_import_agents(match):
        nonlocal modified
        module_name = match.group(1)
        if module_name in module_destinations:
            sub_dir = module_destinations[module_name]
            modified = True
            return f"import stock_team.{sub_dir}.{module_name}"
        return match.group(0)

    content, count2 = re.subn(r"import\s+agents\.([a-zA-Z0-9_]+)", repl_import_agents, content)
    if count2 > 0:
        modified = True

    # 针对从 `scripts` 目录里直接导入模块的情况（比如 `import refresh_prices`）
    for mod_name, sub_dir in module_destinations.items():
        # 匹配 `from mod_name import ...` 或 `import mod_name`
        # 确保只匹配独立的单词，避免子串冲突
        def repl_direct_import(match):
            nonlocal modified
            modified = True
            return f"from stock_team.{sub_dir}.{mod_name}"

        content, count3 = re.subn(rf"from\s+{mod_name}(?=\s+import)", repl_direct_import, content)
        
        def repl_direct_import_sys(match):
            nonlocal modified
            modified = True
            return f"import stock_team.{sub_dir}.{mod_name}"
        content, count4 = re.subn(rf"import\s+{mod_name}(?=\s|$)", repl_direct_import_sys, content)
        
        if count3 > 0 or count4 > 0:
            modified = True

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[已修正] {file_path}")

# 递归遍历所有 Python 文件并修正
for dirpath, _, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith(".py"):
            fix_imports_in_file(os.path.join(dirpath, filename))
