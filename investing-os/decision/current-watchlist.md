# Current Watchlist

## Purpose

Track symbols under attention and define what kind of action is allowed.

Watchlist does not mean permission to trade.

## States

- `research_only`
- `watch_for_trigger`
- `plan_required`
- `allowed_if_plan_matches`
- `no_trade`
- `blocked_pending_review`

## Current Items

| Symbol | State | Allowed Next Step | Blocker |
|---|---|---|---|
| MSFT | allowed_if_plan_matches | Hold or schedule company dossier | No intraday thesis drift |
| NVDA | allowed_if_plan_matches | Hold or schedule company dossier | No intraday thesis drift |
| GOOGL | allowed_if_plan_matches | Hold or schedule company dossier | No intraday thesis drift |
| COHR | plan_required | Review conditional swing plan candidate before any action | No chase near highs; no add while lagging LITE/AAOI/SOXX |
| ORCL | plan_required | Run company research lifecycle, then build swing plan only if thesis candidate survives | No re-entry from rebound impulse |
| INTC | plan_required | Run company research lifecycle, then build short-term tactical plan only if setup survives | Cannot be treated as core; no trade without trigger and time stop |
| SNXX | blocked_pending_review | Review fills and create case candidate | No new trade without full written plan |

## Stage 1 Research Universe

Source:

- `D:\gemini\lianghua\stock_team\findings\cycle_factor_search_findings_v1.md`

Purpose:

Use this universe to prioritize cognition and evidence requests. It is not trade permission.

| Tier | Symbols | Use | Constraint |
|---|---|---|---|
| leader_subset_under_research | RKLB, NVDA, TSLA, LITE, NET, AVGO, PANW, MDB, DDOG, PLTR | First-pass Stage 1 focus pool for catalyst/thesis verification | No action without fresh Stage 0 + Stage 1 packet and written plan |
| growth_ai_semis_software_universe | NVDA, AMD, AVGO, TSM, MU, ARM, LITE, COHR, QCOM, AMAT, KLAC, MRVL, ASML, PLTR, CRWD, PANW, NET, DDOG, SNOW, MDB, VST, GE, RKLB, TSLA, META, MSFT, GOOGL, AMZN, NFLX, ORCL, CRM, ADBE | Wider research universe | Mixed technical filters alone are insufficient |

Current research implication:

- Mixed candidate50 is too diluted for bull-market alpha.
- Growth / AI / semis / software pool has better historical Stage 1 quality.
- Transition-market exposure should be downgraded unless a stronger catalyst packet exists.

## Daily Watchlist Rule

Before market:

1. Remove symbols with no role.
2. Mark each symbol as `allowed_if_plan_matches`, `plan_required`, `research_only`, or `blocked_pending_review`.
3. Write the exact condition that would allow action.
4. If the condition is not written, action is not allowed.

## Stock Team Input Rule

`stock_team` can add context or alerts.

It cannot upgrade a watchlist state by itself.

Any upgrade requires a reviewed packet and human decision.
