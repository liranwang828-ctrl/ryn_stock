# Pre-Market Workflow

## Goal

Prepare the day without creating unnecessary emotional attachment.

Stage 0 is not a pure market-data action.

Before requesting Stage 0 market context, the workflow must load the current brain-owned state that already exists before the market opens:

- current positions context
- prior review state
- cognition state
- permission state before open
- forbidden actions

If these inputs are missing, the system may still collect or display partial facts, but Stage 0 must not be treated as formally ready to continue the pre-market workflow.

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
9. Write the pre-market section around the confirmed primary topics.
10. For each primary topic, record:
   - key questions
   - evidence with source layers in the evidence layer
   - counter evidence
   - hypotheses, including the current lead hypothesis
   - confidence
   - next validation
11. Write planned actions, key levels, forbidden actions, and no-trade conditions only after the topic-driven evidence view is clear.
12. If any symbol may have intraday action, define pre-authorized actions, fast consistency checks, and exception rules.
13. Stop adding new intraday narratives.

## Output

Use `templates/pre-market-plan.md`.

The output should also make the evidence layer legible by topic so later daily reports can reuse the same questions, evidence, counter evidence, hypotheses, and next validation items without rewriting them from scratch.

If the plan does not define `pre_authorized_actions`, then intraday guidance must default to observe-only or reduce-risk-only.
