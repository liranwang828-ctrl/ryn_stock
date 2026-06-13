# 2026-06-04 SNXX Contextual Review

## Metadata

```yaml
symbol: SNXX
date: 2026-06-04
review_created: 2026-06-05
status: reviewed_with_interview
related_fill_review: wiki/journals/2026-06-04-snxx-fill-review.md
related_case: wiki/historical-cases/CASE-004-snxx-attention-capture.md
```

## Purpose

Upgrade the SNXX review from a fill review into a contextual review.

This review should combine:

- fill path
- SNXX price path
- underlying / product context
- broader market context
- trader interview

## Known Product Context

SNXX is a leveraged daily ETF tied to SNDK exposure.

Important note:

- Public search indicates SNXX had an 8-for-1 stock split announced around 2026-06-03.
- This can make recent price history and chart comparison harder to interpret.
- Any historical chart should be checked for split-adjustment behavior.

Sources to verify during final review:

- OCC information memo for SNXX 8-for-1 split.
- ETF provider or broker product page for SNXX leverage/objective.

## Known Fill Context

From screenshot-visible fills:

```yaml
total_buy_quantity: 650
total_sell_quantity: 650
estimated_average_buy_price: 30.66
estimated_average_sell_price: 29.90
visible_realized_pnl: -508.63
```

Pattern already identified:

```text
signal entry
|
averaging down
|
partial profitable exits
|
re-risking
|
forced exit
```

## Market Context Needed

Reconstructed from read-only `stock_team` Polygon API query for 2026-06-04 1-minute bars.

Data source:

- Polygon aggregates API via `stock_team/.env`
- queried symbols: SNXX, SNDK, QQQ, SPY
- regular session only: 09:30-16:00 ET

### Daily Session Summary

| Symbol | Open | High | High Time ET | Low | Low Time ET | Close | Day Change | Approx VWAP | Last 30m Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SNXX | 28.82 | 31.81 | 12:47 | 28.30 | 09:30 | 29.66 | +2.92% | 30.56 | -3.19% |
| SNDK | 1741.31 | 1825.90 | 12:44 | 1725.08 | 09:30 | 1762.00 | +1.19% | 1788.65 | -1.78% |
| QQQ | 735.48 | 743.50 | 15:30 | 732.62 | 10:07 | 740.55 | +0.69% | 739.03 | -0.39% |
| SPY | 752.10 | 758.31 | 15:33 | 751.47 | 09:30 | 757.01 | +0.65% | 756.07 | -0.16% |

### Interpretation

The broad market was not a full-day collapse.

QQQ and SPY closed positive.

But the final 30 minutes weakened:

- QQQ fell about 0.39% from 15:30 to close.
- SPY fell about 0.16% from 15:30 to close.
- SNXX fell about 3.19% from 15:30 to close.
- SNDK fell about 1.78% from 15:30 to close.

This means the late SNXX damage was more symbol/underlying-specific than broad-market-only.

Market context did not force the trade to fail from the open, but it made late-session re-risking especially dangerous.

### Key Contextual Finding

SNXX and SNDK both peaked around mid-day:

- SNXX high: 12:47 ET
- SNDK high: 12:44 ET

After that, the trade was no longer chasing a fresh high.

It was increasingly fighting a fading underlying structure.

## Fill Context Against Market

| Time ET | Side | Qty | Fill | SNXX Bar Close | SNDK Bar Close | QQQ Bar Close | SPY Bar Close | Context |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 10:28:37 | Buy | 100 | 31.44 | 31.50 | 1816.01 | 737.10 | 754.15 | Early strength after open; SNXX already well above open. |
| 10:37:27 | Buy | 50 | 30.64 | 30.60 | 1791.56 | 736.69 | 753.81 | Sharp pullback from first entry zone. |
| 10:42:15 | Buy | 50 | 30.10 | 29.94 | 1772.42 | 736.61 | 754.01 | Averaging into continued weakness. |
| 13:27:25 | Buy | 100 | 31.14 | 31.15 | 1806.75 | 741.39 | 757.01 | Recovery phase after mid-day strength; still below eventual high. |
| 14:03:43 | Sell | 100 | 31.40 | 31.44 | 1815.00 | 742.88 | 757.72 | Valid chance to reduce exposure. |
| 14:12:13 | Sell | 50 | 31.65 | 31.73 | 1823.05 | 743.35 | 757.73 | Best visible exit area; near strong recovery. |
| 14:26:34 | Buy | 100 | 31.11 | 31.09 | 1805.15 | 743.35 | 757.92 | Re-risk after partial profitable exits. |
| 14:40:24 | Buy | 50 | 30.60 | 30.58 | 1790.50 | 742.45 | 757.71 | Underlying fading again. |
| 15:00:11 | Buy | 100 | 30.19 | 30.43 | 1786.00 | 742.72 | 757.80 | Late-day weakness; SNXX below VWAP estimate. |
| 15:54:01 | Buy | 100 | 29.77 | 29.58 | 1761.46 | 741.41 | 757.55 | Very late add during tail-end selloff. |
| 15:55:03 | Sell | 150 | 29.33 | 29.48 | 1758.65 | 740.82 | 757.12 | Forced exit starts as SNXX/SNDK slide. |
| 15:56:22 | Sell | 250 | 29.50 | 29.39 | 1756.93 | 740.73 | 757.07 | Exit during final minutes. |
| 15:56:56 | Sell | 100 | 29.40 | 29.39 | 1756.93 | 740.73 | 757.07 | Final visible exit. |

## Contextual Audit

### What Market Context Adds

The broad market was constructive for much of the day.

This makes the first idea more understandable.

However:

- SNXX and SNDK peaked around 12:44-12:47 ET.
- The 14:26 re-entry occurred after partial profitable exits and after the underlying had already failed to sustain the high area.
- The 15:54 add occurred during the final minutes, with SNXX below approximate VWAP and SNDK sliding.
- QQQ/SPY were also fading into the close, but less severely than SNXX/SNDK.

### Revised Failure Structure

```text
early strength
|
first pullback add
|
midday recovery
|
partial profitable exits
|
re-risk after underlying failed to sustain high
|
late add below VWAP / into final selloff
|
forced exit
```

### Stronger System Lesson

The most dangerous action was not the first entry.

The most dangerous action was re-risking after the market had already offered a risk-reduction window.

Especially:

- buy at 14:26 after profitable exits
- buy at 15:54 during late-session selloff

## Remaining Market Questions

- Was there a specific SNDK catalyst or news item driving the morning move?
- Was the 8-for-1 split affecting displayed price perception or volatility interpretation?
- Did the trader know SNXX was leveraged SNDK exposure at the time?

Optional additional inputs:

- broker chart screenshot
- SNDK news/catalyst screenshot
- stock_team intraday snapshot if it exists

## Trader Interview

Status: completed first pass.

### 1. First Entry

Before the first SNXX buy at 22:28:37 local time / around the U.S. session, what exactly did you expect?

Was it:

- VWAP reclaim continuation
- quick scalp
- trend day continuation
- sympathy / sector move
- other

User answer:

The first entry had several inputs:

- SNXX had shown decent relative strength over the prior two to three days.
- Each break above VWAP had tended to attack upward and hold.
- This breakout looked supported by strong volume.
- The broad market was rebounding.
- Semiconductors were broadly attacking upward.
- The user already had optical-module exposure and wanted additional storage exposure.
- The user's current cycle view was that optical modules plus storage are, and may remain for a long time, the main line.

Interpretation:

The first entry was not pure random FOMO.

It had a thesis seed:

```text
relative strength
|
VWAP behavior
|
volume
|
market rebound
|
semiconductor strength
|
storage exposure as part of AI cycle thesis
```

But the thesis seed was not converted into a complete trade plan.

Missing:

- explicit invalidation
- position-size boundary
- add rule
- re-entry rule
- attention budget

### 2. Thesis

At first entry, did SNXX have a thesis beyond price/VWAP movement?

If yes, what was it?

User answer:

Yes, but it was implicit rather than written.

The thesis was:

- storage exposure should matter in the current AI cycle
- the user already had optical-module exposure and wanted storage exposure
- semiconductors were acting strong
- SNXX/SNDK strength appeared to fit the cycle theme

Interpretation:

This was a theme-expression trade.

The problem was not absence of all cognition.

The problem was incomplete translation from cognition to execution.

The trade needed to answer:

- why SNXX rather than SNDK or another storage name?
- how much exposure is appropriate for a leveraged ETF?
- what invalidates the setup?
- what proves the storage thesis is still intact during the trade?
- what is the maximum attention budget?

### 3. Invalidation

At first entry, what would have told you "this trade is wrong"?

If there was no condition, write "none".

User answer:

No explicit invalidation was written.

Interpretation:

The thesis seed existed, but the trade had no falsification boundary.

That allowed the trade to mutate when price moved against it.

### 4. Adds

For each add cluster, what was the reason?

- 30.64 / 30.10 area:
- 31.14 / 31.11 area:
- 30.60 / 30.19 area:
- 29.77 final buy:

Classify each as:

- thesis strengthened
- cost reduction
- rebound expectation
- emotional repair
- unclear

User answer:

The later add behavior increasingly became:

- not wanting to accept that prior profit was too small
- wanting to reproduce the earlier profitable operation
- trying to make a bit more
- later, not wanting to accept the loss
- lowering cost
- emotional repair

Interpretation by cluster:

- 30.64 / 30.10 area: likely pullback add mixed with cost-basis management.
- 31.14 / 31.11 area: re-risking after recovery; confidence/relief rather than fully new thesis.
- 30.60 / 30.19 area: increasingly recovery-oriented.
- 29.77 final buy: not thesis strengthening; user classifies it as unwillingness, cost averaging, and complete loss of control.

### 5. Partial Profitable Exits

After selling 100 at 31.40 and 50 at 31.65, why did the trade continue?

Did you feel:

- risk reduced
- confidence restored
- opportunity still valid
- regret about not holding more
- desire to recover earlier stress

User answer:

The user felt the earlier profitable sells were too small.

The user did not want to give up the possible additional profit and wanted to replicate the earlier operation to make a bit more.

Interpretation:

This is the key transition point.

The trade shifted from:

```text
theme-expression / momentum setup
```

to:

```text
profit regret
|
operation replication
|
re-risking
```

The partial profitable exits should have reduced the cognitive load.

Instead, they created a new emotional anchor:

```text
I sold too little / I can do it again
```

That anchor pulled the user back into risk.

### 6. Attention

At what point did SNXX start occupying too much attention?

Approximate timestamp or trade is enough.

User answer:

Attention and control started to break during the 30.60 / 30.19 add area.

At that point, the user had already noticed SNXX was weakening.

The user also noticed that MU, a related storage/semiconductor name, was weaker.

Despite that, the user still hoped for a miracle rebound.

Interpretation:

This is the cleanest loss-of-control timestamp zone:

```text
14:40 ET buy at 30.60
|
15:00 ET buy at 30.19
```

The issue was not lack of market perception.

The issue was overriding perceived weakness with hope.

By 15:54, the final 29.77 buy was no longer a decision problem only; it was already a control problem.

### 7. Market Context

Did you notice broad market weakness during the SNXX trade?

If yes, did it change your sizing or exit plan?

User answer:

The user did notice weakness.

The user noticed SNXX was weakening and also noticed related storage/semiconductor context, including MU, was weaker.

But the user hoped SNXX would reverse and outperform again.

Interpretation:

The failure was not:

```text
I did not see weakness.
```

The failure was:

```text
I saw weakness but hoped it would reverse.
```

This matters because the system should not only improve information intake.

It must create a hard stop when known adverse evidence is being overridden by hope.

### 8. Spillover

Did SNXX affect the later COHR / ORCL / INTC exits?

Answer one:

- no
- maybe
- yes
- unsure

Then explain briefly.

User answer:

There was obvious influence.

If the SNXX trade had not happened, the user likely would not have sold as much COHR / ORCL / INTC.

The user may even have been reluctant to sell during the later selloff.

However, the emotional spillover may have accidentally helped reduce risk and avoid some post-market or overnight losses.

Interpretation:

This is mixed-quality behavior.

The process was polluted by SNXX emotional spillover.

The outcome may still have been protective.

Classification:

```yaml
process_quality: compromised
outcome_quality: partially_protective
decision_type: emotional_spillover_triggered_risk_reduction
```

System lesson:

Do not evaluate exits only by outcome.

Separate:

- whether the exit reduced risk
- whether the exit was thesis-based
- whether the exit was emotionally triggered
- whether the same action would have been taken under a clean state

### 9. Pause Point

If the system could force one pause, which moment should trigger it?

Examples:

- first add
- second add
- after partial profitable exit
- before final 29.77 buy
- before final sell cluster

Preliminary interpretation:

The strongest forced-pause candidates are:

1. after the profitable exits at 14:03 and 14:12 ET
2. before the 14:26 re-entry
3. during the 30.60 / 30.19 add zone
4. before the 15:54 final buy

The system should ask:

```text
Am I re-entering because thesis improved, or because I regret selling too little?
```

Final pause rule:

If the user notices symbol or peer weakness but continues because of hope, the system should force a pause.

The required pause question:

```text
What evidence would make this trade stop now?
```

### 10. Better Rule

What rule would have stopped the worst part of this trade without blocking valid trades?

Candidate rule:

After partial profitable exits in a thesis-incomplete trade, no re-entry is allowed unless a fresh plan is written.

Fresh plan must include:

- thesis
- trigger
- invalidation
- add rule
- attention budget
- market/underlying confirmation

If the reason is "I sold too little" or "I want to do it again", re-entry is forbidden.

## Pending Conclusion

Interview first pass is complete.

CASE-004 should be revised from "no thesis" to a more precise lesson:

```text
An implicit theme thesis is not enough.
If it is not converted into invalidation, size, add, re-entry, and attention rules, the trade can mutate into profit regret and bailout behavior.
```

Final contextual conclusion:

The SNXX trade had a real theme seed.

The failure was the inability to convert that theme seed into execution constraints and then obey adverse evidence.

The deepest failure point was:

```text
seeing weakness
|
still hoping for reversal
|
adding anyway
```

The COHR / ORCL / INTC exits were affected by emotional spillover, but the outcome may have been risk-protective.

This creates a nuanced rule:

Emotional spillover can accidentally reduce risk, but it should not be relied on as a risk-management system.
