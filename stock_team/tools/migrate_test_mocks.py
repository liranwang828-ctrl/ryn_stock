import os
import re

# Destination map for modules after workspace restructuring
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
    "suggestion_applier": "agents",
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

    # agents/
    "tech_agent": "agents",
    "risk_agent": "agents",
    "macro_agent": "agents",
    "sentiment_agent": "agents",
    "fund_agent": "agents",
    "verifier_agent": "agents",
    "sector_agent": "agents",
    "community_agent": "agents",
    "debate_engine": "agents",
    "harvest_agent": "agents",
    "learning_agent": "agents",
    "persona_engine": "agents",
    "report_agent": "agents",
    "strategy_agent": "agents"
}

root_dir = r"D:\gemini\lianghua\stock_team\tests"

def migrate_test_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    modified = False
    
    # Replace mock patch strings: "agents.module" -> "stock_team.subdir.module"
    # Also handles "stock_team.agents.module" -> "stock_team.subdir.module"
    def repl_mock_str(match):
        nonlocal modified
        module_name = match.group(1)
        if module_name in module_destinations:
            sub_dir = module_destinations[module_name]
            modified = True
            return f"stock_team.{sub_dir}.{module_name}"
        return match.group(0)
        
    # Match strings starting with agents. or stock_team.agents.
    content, count = re.subn(r"(?:stock_team\.)?agents\.([a-zA-Z0-9_]+)", repl_mock_str, content)
    
    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[REPLACED MOCKS] {file_path} ({count} changes)")

# Run across all python files in tests directory
for dirpath, _, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith(".py"):
            migrate_test_file(os.path.join(dirpath, filename))
