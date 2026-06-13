# Stock Team Asset Inventory Summary

Date: 2026-06-05 03:47:39
Total Files Counted: 1965
Total Size: 1304200148 bytes

## Asset Categories Breakdown

| Category | Files Count |
| :--- | :--- |
| legacy_artifact | 1142 |
| generated_output | 583 |
| code | 200 |
| runtime_config | 20 |
| cognition | 15 |
| reflection | 3 |
| research | 2 |

## Migration Action Summary

| Action | Files Count | Description |
| :--- | :--- | :--- |
| candidate_archive_later | 1137 | Archive to legacy folders after review. |
| keep | 5 | Keep in stock_team as is. |
| ignore_generated | 583 | Directly ignored runtime caches and logs. |
| candidate_code_refactor | 200 | Reorganize in tests/ scripts/ or agents/. |
| candidate_runtime_config | 20 | Keep in config/ for runtime parameter loading. |
| candidate_copy_to_inbox | 20 | Copy to investing-os/wiki/inbox/ for safety before restructure. |

## Major Cognition / Research / Reflection Files to Migrate

The following files represent the core intellectual asset to be transferred into the `wiki/` of `investing-os`:

### 🧠 Principles (Cognition)
- **docs/wiki/00_system_overview_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/01_ai_usage_protocol_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/02_portfolio_framework_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/03_daily_workflow_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/04_company_research_method_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/05_market_sector_map_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/README_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/ai/answer_checklist_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/ai/llm_controller_discipline_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/ai/low_model_boundary_zh.md** -> Suggested: `wiki/principles/README.md`
- **docs/wiki/principles/hand_feel_trade_zh.md** -> Suggested: `wiki/principles/PRIN-002-hand-feel-trade-limit.md`
- **docs/wiki/principles/leveraged_tool_rules_zh.md** -> Suggested: `wiki/principles/PRIN-001-leveraged-tool-discipline.md`
- **docs/wiki/principles/profit_taking_regret_loop_zh.md** -> Suggested: `wiki/principles/PRIN-003-profit-taking-cooling-period.md`
- **docs/wiki/principles/sector_sympathy_catalyst_zh.md** -> Suggested: `wiki/principles/PRIN-004-sector-sympathy-rules.md`
- **docs/wiki/principles/vwap_volume_confirmation_zh.md** -> Suggested: `wiki/principles/PRIN-005-vwap-volume-rules.md`

### 🎬 Historical Cases (Reflection)
- **docs/wiki/cases/2026-06-02_cohr_profit_taking_zh.md** -> Suggested: `wiki/historical-cases/CASE-001-cohr-profit-taking.md`
- **docs/wiki/cases/2026-06-02_crdu_fomo_pullback_zh.md** -> Suggested: `wiki/historical-cases/CASE-002-crdu-fomo-pullback.md`
- **docs/wiki/cases/2026-06-02_pltr_trend_switch_exit_zh.md** -> Suggested: `wiki/historical-cases/CASE-003-pltr-trend-switch-exit.md`

### 🔍 Deep Research (Research)
- **findings/AI_GPU_compute_industry_2026-05-26.md** -> Suggested: `wiki/industries/`
- **findings/Physical_AI_industry_2026-05-26.md** -> Suggested: `wiki/industries/`

---
*Note: This summary is generated as part of Phase 0. No files were modified, moved or deleted.*
