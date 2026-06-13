# Stock Team Import Destination Map

Date: 2026-06-05  
Source inventory: `handoff/inventory/stock_team-inventory-manifest.json`

## Purpose

Map the 20 Phase 0 candidate cognition assets from `stock_team` to safe inbox locations and likely permanent destinations in `investing-os`.

This document does not authorize copying yet.

It is a planning map for user review.

## Rules

- Source files remain untouched.
- No file is copied until the user approves Phase 2.
- Every file enters `wiki/inbox/` first.
- Permanent destination is provisional until content is read and rewritten.
- Broad system docs should not be forced into `wiki/principles/README.md`.
- Runtime parameters should not be hardcoded into principles.

## Destination Map

| # | Source file | Inbox destination | Likely permanent destination | Treatment | Notes |
|---:|---|---|---|---|---|
| 1 | `docs/wiki/00_system_overview_zh.md` | `wiki/inbox/system/00_system_overview_zh.md` | `system/architecture.md` or `PROJECT.md` update | Split / summarize | System overview may contain architecture or governance content. Do not import wholesale. |
| 2 | `docs/wiki/01_ai_usage_protocol_zh.md` | `wiki/inbox/ai/01_ai_usage_protocol_zh.md` | `AGENTS.md`, `agents/`, or `system/checks/` | Split | AI usage rules belong to agent boundaries and checklists, not principles by default. |
| 3 | `docs/wiki/02_portfolio_framework_zh.md` | `wiki/inbox/system/02_portfolio_framework_zh.md` | `framework.md` and `templates/risk-checklist.md` | Split | Portfolio logic should update framework and risk templates after review. |
| 4 | `docs/wiki/03_daily_workflow_zh.md` | `wiki/inbox/system/03_daily_workflow_zh.md` | `system/workflows/trading-day.md` and `templates/trading-day-plan.md` | Merge / revise | Must be adapted to the user's timezone-offset workflow. |
| 5 | `docs/wiki/04_company_research_method_zh.md` | `wiki/inbox/system/04_company_research_method_zh.md` | `wiki/methodologies/` and `templates/company-research.md` | Split | Research method should become methodology plus template improvements. |
| 6 | `docs/wiki/05_market_sector_map_zh.md` | `wiki/inbox/reports/05_market_sector_map_zh.md` | `wiki/industries/` | Rewrite | Treat as industry map, not principle. |
| 7 | `docs/wiki/README_zh.md` | `wiki/inbox/system/README_zh.md` | `README.md`, `PROJECT.md`, or no import | Compare / dedupe | May duplicate current `investing-os` docs. Import only unique content. |
| 8 | `docs/wiki/ai/answer_checklist_zh.md` | `wiki/inbox/ai/answer_checklist_zh.md` | `system/checks/` or `AGENTS.md` | Convert to checklist | Useful if it improves AI output discipline. |
| 9 | `docs/wiki/ai/llm_controller_discipline_zh.md` | `wiki/inbox/ai/llm_controller_discipline_zh.md` | `AGENTS.md`, `agents/`, `system/checks/` | Split | Keep as AI boundary and controller discipline, not trading advice. |
| 10 | `docs/wiki/ai/low_model_boundary_zh.md` | `wiki/inbox/ai/low_model_boundary_zh.md` | `AGENTS.md` or `agents/` | Extract guardrails | Use only durable model-boundary rules. |
| 11 | `docs/wiki/cases/2026-06-02_cohr_profit_taking_zh.md` | `wiki/inbox/cases/2026-06-02_cohr_profit_taking_zh.md` | `wiki/historical-cases/CASE-001-cohr-profit-taking.md` | Rewrite as case | Link to profit-taking and regret-loop principles. |
| 12 | `docs/wiki/cases/2026-06-02_crdu_fomo_pullback_zh.md` | `wiki/inbox/cases/2026-06-02_crdu_fomo_pullback_zh.md` | `wiki/historical-cases/CASE-002-crdu-fomo-pullback.md` | Rewrite as case | Link to FOMO, entry discipline, and pullback rules. |
| 13 | `docs/wiki/cases/2026-06-02_pltr_trend_switch_exit_zh.md` | `wiki/inbox/cases/2026-06-02_pltr_trend_switch_exit_zh.md` | `wiki/historical-cases/CASE-003-pltr-trend-switch-exit.md` | Rewrite as case | Link to exit discipline and trend-change detection. |
| 14 | `docs/wiki/principles/hand_feel_trade_zh.md` | `wiki/inbox/principles/hand_feel_trade_zh.md` | `wiki/principles/PRIN-002-hand-feel-trade-limit.md` | Rewrite as principle | Separate discipline intent from any numeric limit. |
| 15 | `docs/wiki/principles/leveraged_tool_rules_zh.md` | `wiki/inbox/principles/leveraged_tool_rules_zh.md` | `wiki/principles/PRIN-001-leveraged-tool-discipline.md` | Rewrite as principle | Any OCO or leverage thresholds should become runtime parameters if needed. |
| 16 | `docs/wiki/principles/profit_taking_regret_loop_zh.md` | `wiki/inbox/principles/profit_taking_regret_loop_zh.md` | `wiki/principles/PRIN-003-profit-taking-cooling-period.md` | Rewrite as principle | Cooling time should be parameterized, not treated as eternal truth. |
| 17 | `docs/wiki/principles/sector_sympathy_catalyst_zh.md` | `wiki/inbox/principles/sector_sympathy_catalyst_zh.md` | `wiki/principles/PRIN-004-sector-sympathy-rules.md` and `wiki/methodologies/` | Split | May contain both principle and method. |
| 18 | `docs/wiki/principles/vwap_volume_confirmation_zh.md` | `wiki/inbox/principles/vwap_volume_confirmation_zh.md` | `wiki/principles/PRIN-005-vwap-volume-rules.md` and runtime snapshot parameters | Split | Keep qualitative confirmation rule separate from VWAP thresholds. |
| 19 | `findings/AI_GPU_compute_industry_2026-05-26.md` | `wiki/inbox/reports/AI_GPU_compute_industry_2026-05-26.md` | `wiki/industries/ai-gpu-compute.md` | Rewrite as industry note | Preserve source metadata and open questions. |
| 20 | `findings/Physical_AI_industry_2026-05-26.md` | `wiki/inbox/reports/Physical_AI_industry_2026-05-26.md` | `wiki/industries/physical-ai.md` | Rewrite as industry note | Preserve source metadata and thesis/falsification. |

## Grouped Import Plan

### System And Workflow Docs

Source files:

- `docs/wiki/00_system_overview_zh.md`
- `docs/wiki/02_portfolio_framework_zh.md`
- `docs/wiki/03_daily_workflow_zh.md`
- `docs/wiki/README_zh.md`

Inbox:

- `wiki/inbox/system/`

Likely output:

- `PROJECT.md`
- `framework.md`
- `system/workflows/`
- `templates/`

### AI Boundary Docs

Source files:

- `docs/wiki/01_ai_usage_protocol_zh.md`
- `docs/wiki/ai/answer_checklist_zh.md`
- `docs/wiki/ai/llm_controller_discipline_zh.md`
- `docs/wiki/ai/low_model_boundary_zh.md`

Inbox:

- `wiki/inbox/ai/`

Likely output:

- `AGENTS.md`
- `agents/`
- `system/checks/`

### Principles

Source files:

- `docs/wiki/principles/hand_feel_trade_zh.md`
- `docs/wiki/principles/leveraged_tool_rules_zh.md`
- `docs/wiki/principles/profit_taking_regret_loop_zh.md`
- `docs/wiki/principles/sector_sympathy_catalyst_zh.md`
- `docs/wiki/principles/vwap_volume_confirmation_zh.md`

Inbox:

- `wiki/inbox/principles/`

Likely output:

- `wiki/principles/PRIN-*`
- runtime snapshot parameters where numeric thresholds exist

### Cases

Source files:

- `docs/wiki/cases/2026-06-02_cohr_profit_taking_zh.md`
- `docs/wiki/cases/2026-06-02_crdu_fomo_pullback_zh.md`
- `docs/wiki/cases/2026-06-02_pltr_trend_switch_exit_zh.md`

Inbox:

- `wiki/inbox/cases/`

Likely output:

- `wiki/historical-cases/CASE-*`

### Research Reports

Source files:

- `findings/AI_GPU_compute_industry_2026-05-26.md`
- `findings/Physical_AI_industry_2026-05-26.md`
- `docs/wiki/05_market_sector_map_zh.md`

Inbox:

- `wiki/inbox/reports/`

Likely output:

- `wiki/industries/`

## Review Needed

Before copying files into inbox, confirm:

1. Whether all 20 candidate files should be copied.
2. Whether broad system docs should be imported or only used as reference.
3. Whether the two industry reports are still strategically important.
4. Whether any private trading reflection should be excluded from permanent wiki.

