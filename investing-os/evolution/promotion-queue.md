# Promotion Queue

## Purpose

Hold candidate lessons before they become durable personal cognition, principles, checklist rules, or risk constraints.

This queue exists to prevent the system from silently turning one review into permanent identity.

## Status Values

- `pending_user_approval`
- `evidence_received_pending_review`
- `adopted`
- `revised`
- `rejected`
- `keep_observing`

## Candidates

```yaml
id: CAND-2026-06-05-001
source: wiki/journals/2026-06-04-snxx-contextual-review.md
area: cognition
candidate: Seeing weakness but hoping for reversal is a distinct mistake pattern.
current_usage: drafted into cognition/mistake-patterns.md as a candidate-level pattern
status: pending_user_approval
decision_needed: adopt / revise / reject / keep_observing
```

```yaml
id: CAND-2026-06-05-002
source: wiki/journals/2026-06-04-snxx-contextual-review.md
area: execution
candidate: No adding when adverse evidence is visible and the reason is hope for reversal.
current_usage: drafted into execution/intraday.md and system/checks/short-term-trade-checklist.md as a candidate guard
status: pending_user_approval
decision_needed: adopt / revise / reject / keep_observing
```

```yaml
id: CAND-2026-06-05-003
source: wiki/journals/2026-06-04-snxx-contextual-review.md
area: cognition
candidate: Partial recovery can create re-risking through regret about selling too little.
current_usage: drafted into cognition/mistake-patterns.md as a candidate-level pattern
status: pending_user_approval
decision_needed: adopt / revise / reject / keep_observing
```

```yaml
id: CAND-2026-06-05-004
source: wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md
area: post_market_review
candidate: Mixed-quality exits should separate process quality from outcome quality.
current_usage: drafted into execution/post-market.md and decision/decision-log.md as a review classifier
status: pending_user_approval
decision_needed: adopt / revise / reject / keep_observing
```

```yaml
id: CAND-2026-06-05-005
source: wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md
area: decision
candidate: COHR / ORCL / INTC should stay plan_required until individual theses are rebuilt.
current_usage: applied conservatively to prevent rebound-driven re-entry
status: pending_user_approval
decision_needed: adopt / revise / reject / keep_observing
```

```yaml
id: CAND-2026-06-05-006
source: wiki/companies/COHR.md
area: company_thesis
candidate: COHR as AI optical infrastructure / photonics platform exposure.
current_usage: role confirmed as swing-oriented; fast draft exists, full company research lifecycle still pending
status: adopted_as_thesis_candidate
decision_needed: define swing plan / reject thesis / keep observing
```

```yaml
id: CAND-2026-06-05-007
source: wiki/companies/ORCL.md
area: company_thesis
candidate: ORCL as AI cloud infrastructure capacity / RPO conversion thesis.
current_usage: role confirmed as swing-oriented; fast draft exists, full company research lifecycle still pending
status: revised
decision_needed: run company research packet / define swing plan only after packet absorption / reject thesis / keep observing
```

```yaml
id: CAND-2026-06-05-008
source: wiki/companies/INTC.md
area: company_thesis
candidate: INTC as high-uncertainty AI CPU / foundry / advanced packaging turnaround optionality.
current_usage: role confirmed as short-term tactical or swing; fast draft exists, full company research lifecycle still pending
status: revised
decision_needed: run company research packet / define short-term or swing plan only after packet absorption / reject thesis / keep observing
```

```yaml
id: CAND-2026-06-06-001
source: wiki/journals/2026-06-05-major-drawdown-review.md
area: cognition
candidate: Recent profits can inflate confidence when profits are not decomposed into skill, beta, luck, and one-large-winner effects.
current_usage: adopted into cognition maps and short-term/trade-plan checks as profit-streak decomposition guard
status: adopted
decision_needed: review effectiveness after next profit streak
```

```yaml
id: CAND-2026-06-06-002
source: wiki/journals/2026-06-05-major-drawdown-review.md
area: execution
candidate: After any failed short-term trade and stop-loss, block new short-term trades for the rest of the session unless acting on a prewritten swing plan or reducing risk.
current_usage: adopted into execution/intraday.md and system/checks/short-term-trade-checklist.md
status: adopted
decision_needed: review after next short-term stop-loss event
```

```yaml
id: CAND-2026-06-06-003
source: wiki/journals/2026-06-05-major-drawdown-review.md
area: risk
candidate: Major drawdown should move the system into Red permission state until open risk, emotional state, and next-session plan are reviewed.
current_usage: adopted into execution/intraday.md as permission-state model
status: adopted
decision_needed: review thresholds after recovery from current Red state
```

```yaml
id: CAND-2026-06-06-004
source: wiki/journals/2026-06-05-major-drawdown-review.md
area: risk
candidate: Separate theme thesis validity, underlying relative strength, and leveraged-instrument suitability before deciding whether to hold a trapped leveraged position.
current_usage: adopted into templates/risk-checklist.md and templates/trade-plan.md as instrument-fit guard
status: adopted
decision_needed: review after next leveraged/instrument-substitution decision
```

```yaml
id: CAND-2026-06-06-005
source: wiki/journals/2026-06-05-major-drawdown-review.md
area: tactics
candidate: RS pullback rebound tactic may be retained only as a restricted, market-regime-dependent tactic pending stock_team historical validation.
current_usage: stock_team backtest evidence received; kept as restricted research candidate, not promoted to live rule
status: evidence_received_pending_review
decision_needed: adopt restricted paper/live rules / revise boundaries / reject / keep research-only
evidence:
  - wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md
```
