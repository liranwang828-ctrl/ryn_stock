# CAND-2026-06-06-002 Short-Term Stop No-Trade

```yaml
lesson_id: CAND-2026-06-06-002
title: Short-Term Stop No-Trade / 短线止损后禁止新短线
status: adopted
source_report: wiki/journals/2026-06-05-major-drawdown-review.md
area: execution
severity: high
```

## Lesson

After a failed short-term trade and stop-loss, hand-feel is impaired and the next short-term trade is presumed contaminated by repair desire.

## Recommended Landing

| Target File | Update Type | Reason |
|---|---|---|
| execution/intraday.md | permission_rule | Add no-new-short-term-trade guard after stop-loss. |
| system/checks/short-term-trade-checklist.md | checklist_rule | Make stop-loss cooldown explicit before new short-term trades. |

## Adoption Record

```yaml
adopted_files:
  - execution/intraday.md
  - system/checks/short-term-trade-checklist.md
adopted_date: 2026-06-06
review_due: 2026-06-13
```
