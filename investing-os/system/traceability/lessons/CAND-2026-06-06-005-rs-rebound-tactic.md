# CAND-2026-06-06-005 RS Pullback Rebound Tactic

```yaml
lesson_id: CAND-2026-06-06-005
title: RS Pullback Rebound Tactic / RS Strong Pullback Rebound Tactic
status: evidence_received_pending_review
source_report: wiki/journals/2026-06-05-major-drawdown-review.md
evidence_report: wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md
area: tactic
severity: medium
```

## Lesson

The RS pullback rebound tactic may have value, but only as a restricted, market-regime-dependent tactic. Stock Team historical evidence has been received, but it does not justify unrestricted live use.

## Recommended Landing

| Target File | Update Type | Reason |
|---|---|---|
| decision/tactics/rs-pullback-rebound-candidate.md | tactic_candidate | Document allowed/disabled conditions. |
| wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md | evidence_source | Preserve evidence without turning it into a rule. |
| evolution/promotion-queue.md | evidence_review | Require user review before promotion. |

## Evidence Received

```yaml
received_date: 2026-06-06
total_trades: 213
win_rate: 62.91%
profit_factor: 1.33
average_win: 7.11%
average_loss: -9.05%
disable_condition_confirmed:
  - QQQ high-volume risk-off
leveraged_product_warning:
  - lower win rate
  - larger MAE
live_rule_status: not_promoted
```

## Adoption Record

```yaml
adopted_files:
  - decision/tactics/rs-pullback-rebound-candidate.md
adopted_date: 2026-06-06
review_due: user_evidence_review
```
