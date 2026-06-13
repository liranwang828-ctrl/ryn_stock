# Decision Log

## Purpose

Record important judgment changes.

This is not a trade blotter.

Use it when a thesis, position role, risk budget, or allowed action changes.

## Entry Template

```yaml
date:
symbol:
decision_area:
previous_state:
new_state:
reason:
evidence:
emotion_check:
related_journal:
related_principle:
next_review:
```

## Entries

```yaml
date: 2026-06-05
symbol: SNXX
decision_area: watchlist_state
previous_state: undefined
new_state: blocked_pending_review
reason: 2026-06-04 trade lacked thesis, invalidation, add rule, and attention budget control.
evidence: wiki/journals/2026-06-04-daily-review.md
emotion_check: FOMO, loss aversion, attention capture, possible emotional spillover
related_journal: wiki/journals/2026-06-04-daily-review.md
related_principle: wiki/principles/PRIN-006-cognitive-attention-budget.md
next_review: after full SNXX fill review
```

```yaml
date: 2026-06-05
symbol: SNXX
decision_area: case_promotion
previous_state: journal_only
new_state: historical_case
reason: Fill review showed a repeatable structure: signal entry, averaging down, partial recovery, re-risking, and forced exit.
evidence: wiki/journals/2026-06-04-snxx-fill-review.md
emotion_check: relief after partial profitable exits may have enabled re-risking
related_case: wiki/historical-cases/CASE-004-snxx-attention-capture.md
related_principle: wiki/principles/PRIN-006-cognitive-attention-budget.md
next_review: compare against last 20 short-term trades
```

```yaml
date: 2026-06-05
symbol: COHR/ORCL/INTC
decision_area: swing_role_review
previous_state: swing
new_state: plan_required
reason: 2026-06-04 exits may have been risk management or emotional spillover; decision cause is not yet classified.
evidence: wiki/journals/2026-06-04-daily-review.md
emotion_check: possible spillover from SNXX
related_journal: wiki/journals/2026-06-04-daily-review.md
related_principle: wiki/principles/PRIN-006-cognitive-attention-budget.md
next_review: next weekend review or before any re-entry
```

```yaml
date: 2026-06-05
symbol: COHR/ORCL/INTC
decision_area: exit_quality_classification
previous_state: plan_required_pending_review
new_state: plan_required_thesis_unresolved
reason: Exit review showed useful risk reduction but compromised decision-state quality due to SNXX emotional spillover.
evidence: wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md
emotion_check: emotional spillover likely increased willingness to sell; outcome was partially protective, especially for COHR and INTC after hours
related_journal: wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md
related_principle: wiki/principles/PRIN-006-cognitive-attention-budget.md
next_review: rebuild individual thesis before any re-entry
```

```yaml
date: 2026-06-05
symbol: COHR
decision_area: company_thesis_candidate
previous_state: quick_role_draft_research_lifecycle_pending
new_state: thesis_candidate_plan_required
reason: Full company research packet supports COHR as a swing thesis candidate, but valuation and peer-leadership constraints prevent automatic trade permission.
evidence: system/data/packets/drafts/company-research-COHR-2026-06-05.md
emotion_check: prior COHR regret loop requires prewritten partial profit and no regret-driven re-entry
related_journal: wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md
related_dossier: wiki/companies/COHR.md
next_review: create swing plan candidate or keep observing
```

```yaml
date: 2026-06-05
symbol: COHR
decision_area: user_review_update
previous_state: thesis_candidate_pending_user_review
new_state: thesis_candidate_pending_valuation_and_sizing_confirmation
reason: User confirmed COHR is swing-only, not core; confirmed peer-leadership requirement; raised need for AI overheated-narrative valuation framework and clarified tentative max size as 30% of swing sleeve.
evidence: wiki/companies/COHR.zh.md
emotion_check: prior regret loop remains relevant; no trade permission
related_dossier: wiki/companies/COHR.zh.md
next_review: build AI swing valuation framework and confirm sizing interpretation
```

```yaml
date: 2026-06-05
symbol: COHR
decision_area: role_refinement
previous_state: swing_candidate_role_open
new_state: mainline_carrier_plus_resilient_swing
reason: User clarified COHR should serve as AI optical mainline exposure with relatively better resilience, not as the highest-beta attack tool.
evidence: user review discussion
emotion_check: role clarity should reduce chasing AAOI/LITE-style beta with COHR
related_dossier: wiki/companies/COHR.zh.md
next_review: build AI swing valuation framework around this role
```

```yaml
date: 2026-06-05
symbol: COHR
decision_area: ai_swing_valuation
previous_state: thesis_candidate_pending_valuation_and_sizing_confirmation
new_state: valuation_temperature_orange_pending_user_review
reason: COHR is a mainline/resilient swing candidate, but AI optical narrative is hot, price is elevated, valuation is demanding, and peer signals are mixed.
evidence: wiki/companies/COHR-valuation-temperature.zh.md
emotion_check: no regret re-entry; no chase near highs
related_dossier: wiki/companies/COHR.zh.md
next_review: user review of valuation temperature and sizing map
```

```yaml
date: 2026-06-05
symbol: COHR
decision_area: conditional_swing_plan
previous_state: valuation_temperature_orange_pending_user_review
new_state: swing_plan_candidate_pending_user_review
reason: Conditional swing plan created from COHR thesis candidate and orange valuation temperature; no trade permission granted.
evidence: decision/trade-plans/COHR-swing-plan-candidate-2026-06-05.zh.md
emotion_check: plan forbids regret re-entry and cost-reduction adds
related_dossier: wiki/companies/COHR.zh.md
next_review: user review of trigger, sizing, risk limit, and exit rules
```
