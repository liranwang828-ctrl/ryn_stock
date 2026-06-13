# 2026-06-04 COHR / ORCL / INTC Exit Review

## Metadata

```yaml
date: 2026-06-04
review_created: 2026-06-05
symbols: [COHR, ORCL, INTC]
status: first_pass_reviewed
related_review: wiki/journals/2026-06-04-snxx-contextual-review.md
decision_area: swing_exit_review
```

## Purpose

Separate two questions that can easily get mixed together:

1. Did the exits reduce real portfolio risk?
2. Were the exits made from a clean decision state?

The answer can be mixed.

An exit can be outcome-protective while still being process-contaminated.

## Visible Broker Fills

From user-provided broker screenshots:

| Symbol | Side | Qty | Fill | Local Time | ET Time | Visible P/L |
|---|---:|---:|---:|---:|---:|---:|
| COHR | Sell | 20 | 422.89 | 2026-06-05 03:58:21 | 2026-06-04 15:58:21 | +1236.01 |
| INTC | Sell | 15 | 111.80 | 2026-06-05 03:58:42 | 2026-06-04 15:58:42 | +47.96 |
| ORCL | Sell | 10 | 236.54 | 2026-06-05 03:59:19 | 2026-06-04 15:59:19 | +53.35 |

Known limitation:

- The screenshots show visible fills and P/L, but not the full original thesis, cost basis history, or complete position history.
- INTC had a visible same-day buy of 10 shares at 108.00, while the exit sold 15 shares, implying part of the position existed before the visible screenshot window.

## Market Context

Reconstructed from read-only `stock_team` Polygon API query for 2026-06-04 1-minute bars.

Regular session summary:

| Symbol | Open | High | High Time ET | Low | Low Time ET | Close | Day Change | Approx VWAP | Last 30m Change | After-Hours Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| COHR | 398.70 | 432.51 | 13:54 | 380.20 | 10:08 | 421.90 | +5.82% | 409.45 | -1.16% | -2.11% |
| ORCL | 227.00 | 238.95 | 15:24 | 224.00 | 09:45 | 236.18 | +4.04% | 233.79 | -1.06% | -0.91% |
| INTC | 108.40 | 113.14 | 14:06 | 107.48 | 10:06 | 111.59 | +2.94% | 110.47 | -0.77% | -1.74% |
| QQQ | 735.48 | 743.50 | 15:30 | 732.62 | 10:07 | 740.55 | +0.69% | 739.03 | -0.37% | -0.70% |
| SPY | 752.10 | 758.31 | 15:33 | 751.47 | 09:30 | 757.01 | +0.65% | 756.07 | -0.17% | -0.33% |

Around exit window:

| Symbol | 15:55 | 15:56 | 15:57 | 15:58 | 15:59 | 16:00 | 19:59 |
|---|---:|---:|---:|---:|---:|---:|---:|
| COHR | 424.19 | 422.95 | 422.88 | 422.54 | 421.75 | 421.90 | 413.00 |
| ORCL | 236.42 | 236.52 | 236.44 | 236.46 | 236.34 | 236.18 | n/a |
| INTC | 111.64 | 111.86 | 111.71 | 111.86 | 111.79 | 111.59 | 109.83 |
| QQQ | 740.82 | 740.73 | 740.83 | 740.89 | 740.50 | 740.55 | 735.38 |
| SPY | 757.12 | 757.07 | 757.25 | 757.40 | 757.06 | 757.01 | 754.56 |

## Objective Finding

The exits were not made into a collapsing regular session.

All three names closed positive on the day.

However:

- each name had already faded from its intraday high
- all three weakened in the final 30 minutes
- COHR and INTC continued to weaken after hours
- the broad market also faded after hours, though less severely than COHR / INTC

This supports a mixed conclusion:

```yaml
risk_reduction_result: useful
regular_session_exit_quality: acceptable_price_area
after_hours_avoidance: helpful_for_COHR_and_INTC
thesis_falsification: not_proven
decision_state_quality: compromised_by_SNXX_spillover
```

## User Interview Input

User clarified:

- SNXX obviously influenced the COHR / ORCL / INTC exits.
- Without the SNXX trade, the user likely would not have sold this much.
- The user may even have been reluctant to sell during the visible late selloff.
- Therefore the exits may have accidentally helped avoid post-market or overnight losses.

Interpretation:

The action may have been helpful, but the trigger was not clean.

The system must not mark this as either:

- pure disciplined risk control
- pure mistake

It should be marked as:

```yaml
process_quality: compromised
outcome_quality: partially_protective
decision_type: emotional_spillover_triggered_risk_reduction
```

## Symbol-Level Notes

### COHR

Role before exit:

- AI infrastructure / optical module trend exposure
- swing / trend holding

Facts:

- sold 20 at 422.89 near the final minutes
- intraday high was 432.51 at 13:54
- regular close was 421.90
- after-hours 19:59 price was 413.00

Interpretation:

- Exit price was below intraday high but still strong relative to open and VWAP.
- The action reduced overnight risk effectively.
- No evidence in this review proves the COHR thesis was falsified.

Decision state:

```yaml
symbol: COHR
state: plan_required
reason: exit may have reduced risk, but thesis status remains unresolved
next_step: rebuild swing thesis before re-entry
```

### ORCL

Role before exit:

- AI infrastructure / cloud infrastructure trend exposure
- swing / trend holding

Facts:

- sold 10 at 236.54
- intraday high was 238.95 at 15:24
- regular close was 236.18
- exit was close to regular-session close

Interpretation:

- Exit was not obviously poor on price.
- After-hours evidence is incomplete from this query.
- No evidence in this review proves the ORCL thesis was falsified.

Decision state:

```yaml
symbol: ORCL
state: plan_required
reason: exit cause must be separated from thesis change
next_step: rebuild swing thesis before re-entry
```

### INTC

Role before exit:

- semiconductor / possible AI infrastructure trend exposure
- role less mature than COHR / ORCL

Facts:

- visible same-day buy: 10 at 108.00
- sold 15 at 111.80
- intraday high was 113.14 at 14:06
- regular close was 111.59
- after-hours 19:59 price was 109.83

Interpretation:

- Exit protected against after-hours weakness.
- But the role itself needs more work; INTC cannot be treated as core or high-conviction swing without a clearer thesis.

Decision state:

```yaml
symbol: INTC
state: plan_required
reason: role and thesis are underdefined
next_step: decide whether INTC is swing candidate, research-only, or no-trade
```

## Cognitive Lesson

This event shows a subtle pattern:

```text
bad short-term trade
|
emotional pressure rises
|
portfolio risk is reduced
|
outcome looks helpful
|
process quality remains unclear
```

This is dangerous because the user may learn the wrong lesson.

The correct lesson is not:

```text
Emotional pressure helped me sell, so emotional pressure is useful.
```

The correct lesson is:

```text
I need a clean risk-reduction protocol that can do the useful part without relying on emotional contamination.
```

## System Rule

When a short-term trade emotionally contaminates portfolio decisions:

1. Risk reduction is allowed.
2. Re-entry is not allowed.
3. Thesis status must be marked unresolved.
4. Outcome quality and process quality must be recorded separately.
5. The next action must be a written plan, not a rebound chase.

## Decision Update

COHR / ORCL / INTC remain `plan_required`.

Reason:

- exits may have been outcome-protective
- exits were not clean evidence of thesis falsification
- re-entry requires independent thesis rebuild

## Follow-Up

1. Rebuild COHR thesis.
2. Rebuild ORCL thesis.
3. Decide INTC role.
4. Add a clean portfolio-risk-reduction protocol for late-session stress.
5. Compare future exits against this classification:

```yaml
process_quality:
outcome_quality:
thesis_status:
risk_reduction_status:
reentry_allowed:
```
