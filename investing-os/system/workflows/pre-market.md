# Pre-Market Workflow

## Goal

Prepare the day without creating unnecessary emotional attachment.

## Steps

0. Run file growth health check: `./tools/check-file-growth.ps1`.
1. Load the latest broker snapshot using US/Eastern trading-date boundaries, not local Beijing calendar dates.
2. Load the prior post-market review and cognition state before building any universe.
3. Build the allowed universe from current positions, active watchlist, and researched or explicitly approved candidates.
4. Include `source_inputs.positions`, `source_inputs.prior_review`, `source_inputs.cognition_state`, `permission_state_before_open`, and `forbidden_actions` in the Stage 0 universe artifact.
5. Request Stage 0 market context from stock_team for broad market state, sector heat, catalysts, and universe relevance.
6. Discuss permission state and focus pool with the user.
7. Create the Stage 1 decision sheet only for the confirmed focus pool.
8. Request symbol-level plan evidence from stock_team.
9. Write planned actions, key levels, forbidden actions, and no-trade conditions.
10. If any symbol may have intraday action, define pre-authorized actions, fast consistency checks, and exception rules.
11. Stop adding new intraday narratives.

## Output

Use `templates/pre-market-plan.md`.

If the plan does not define `pre_authorized_actions`, then intraday guidance must default to observe-only or reduce-risk-only.
