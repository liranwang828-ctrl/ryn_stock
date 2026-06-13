# CASE-004: SNXX Attention Capture And Re-Risking

## Metadata

- ID: CASE-004
- Title: SNXX Attention Capture And Re-Risking
- Date: 2026-06-04
- Asset: SNXX
- Source:
  - `wiki/journals/2026-06-04-daily-review.md`
  - `wiki/journals/2026-06-04-snxx-fill-review.md`
- Related principles:
  - `wiki/principles/PRIN-005-vwap-volume-rules.md`
  - `wiki/principles/PRIN-006-cognitive-attention-budget.md`

## Basic Data

Visible screenshot-based summary:

```yaml
total_buy_quantity: 650
total_sell_quantity: 650
estimated_average_buy_price: 30.66
estimated_average_sell_price: 29.90
visible_realized_pnl: -508.63
round_trip_notional: 39368.85
```

Context from read-only Polygon API query:

```yaml
SNXX_day_change: "+2.92%"
SNXX_high: 31.81
SNXX_high_time_et: "12:47"
SNXX_close: 29.66
SNXX_approx_vwap: 30.56
SNXX_last_30m_change: "-3.19%"
SNDK_high_time_et: "12:44"
SNDK_last_30m_change: "-1.78%"
QQQ_day_change: "+0.69%"
QQQ_last_30m_change: "-0.39%"
SPY_day_change: "+0.65%"
SPY_last_30m_change: "-0.16%"
```

## Facts

The trade began after SNXX showed an intraday signal that was interpreted as an opportunity.

The first visible buys were:

- 100 shares at 31.44
- 50 shares at 30.64
- 50 shares around 30.10

Later, the position was rebuilt or increased through additional buys:

- 100 shares at 31.14
- 100 shares at 31.11
- 50 shares at 30.60
- 100 shares at 30.19
- 100 shares at 29.77

There were partial profitable sells:

- 100 shares at 31.40
- 50 shares at 31.65

The final exit cluster occurred near the close:

- 150 shares at 29.33
- 250 shares at 29.50
- 100 shares at 29.40

Market context:

- SNXX and SNDK both peaked around mid-day.
- QQQ and SPY closed positive but faded in the final 30 minutes.
- SNXX and SNDK faded much more sharply than the broad market near the close.

## Decision Context

The trade had an implicit thesis seed, but not a written trade plan.

The initial idea combined:

- recent relative strength
- repeated VWAP reclaim behavior
- perceived strong volume
- broad market rebound
- semiconductor strength
- desire to add storage exposure to an AI-cycle portfolio
- the user's view that optical modules plus storage may be the main cycle line

The failure was not that there was no cognition at all.

The failure was that the cognition did not become execution constraints.

Missing:

- explicit invalidation
- position-size boundary
- add rule
- re-entry rule after partial exit
- attention budget

After partial profitable exits, the trade began to behave less like theme expression and more like profit regret, operation replication, cost-basis management, and recovery trading.

## Subjective Psychology

Likely psychological sequence:

```text
theme confidence / FOMO
|
early pullback pressure
|
partial recovery
|
regret about selling too little
|
re-risking to reproduce the prior operation
|
loss aversion
|
cost averaging
|
loss of control
|
forced exit near close
```

The trade became cognitively larger than its intended role.

Later interview clarified the loss-of-control zone:

- by the 30.60 / 30.19 add area, the user had noticed SNXX was weakening
- the user also noticed related storage/semiconductor context, including MU, was weaker
- the add continued because the user hoped for a miracle rebound
- the 15:54 buy was later classified as unwillingness, cost averaging, and complete loss of control

## Objective Audit

The final loss was not caused by a single entry.

It came from a sequence:

- entering with an implicit thesis but no explicit plan
- adding without prewritten add rule
- rebuilding exposure after partial recovery because the prior sell felt too small
- re-risking after SNXX/SNDK had failed to sustain mid-day highs
- adding very late in the session during a symbol-specific selloff
- allowing attention to remain attached to a low-conviction trade
- exiting under time and risk pressure

## What Went Right

- The trade was eventually closed.
- Partial sells showed that exposure could have been reduced earlier.
- The loss was contained before becoming a larger open-ended hold.

## What Went Wrong

- Theme cognition was not translated into trade constraints.
- No written invalidation existed.
- Adds occurred after adverse movement.
- Partial profitable sells did not end the trade.
- Re-risking after partial recovery was driven by "sold too little / want to do it again" thinking.
- The user noticed weakness around the 30.60 / 30.19 add zone but continued because of hope.
- The 15:54 buy was later classified by the user as unwillingness, cost averaging, and complete loss of control.
- The trade consumed attention and may have affected other decisions.

## Falsification Or Missed Signals

There was no written trade-level thesis to falsify.

This is the core problem.

There was an implicit theme thesis:

- storage exposure in the AI cycle
- semiconductor strength
- SNXX/SNDK relative strength

But the trade-level falsification was missing.

Future invalidation should exist before entry:

- if signal fails within defined time window, exit
- if VWAP/context fails, no add
- if attention budget is exceeded, pause
- if no add rule exists, adding is forbidden

## Principle Updates

This case reinforces:

- `PRIN-005`: VWAP and volume are context, not commands.
- `PRIN-006`: attention is a risk budget.

Candidate addition:

Partial recovery does not reset trade quality.

If a trade began without thesis, profitable partial exits should reduce or end risk, not justify re-risking.

Refined candidate:

An implicit theme thesis is not an executable plan.

Before action, theme must be converted into:

- symbol choice
- time horizon
- position size
- invalidation
- add rule
- re-entry rule
- attention budget

## System Updates

Current system state:

- SNXX remains `blocked_pending_review`.
- Short-term trades require thesis, trigger, maximum loss, invalidation, add rule, and attention budget.
- Re-entry after partial exit requires a new plan, not emotional continuation.

Potential checklist addition:

- Did I already get a chance to reduce risk?
- Am I re-entering because thesis improved, or because I want to recover the trade?
- Has this trade changed identity since entry?
- Am I seeing weakness but hoping for a reversal anyway?
- Would I make this same portfolio exit if the stressful trade did not exist?

## Contextual Review Pending

The current case now includes:

- fill evidence
- first-pass market context from Polygon 1-minute bars
- user interview

Before treating it as final, complete:

- catalyst/news review if available

Draft:

- `wiki/journals/2026-06-04-snxx-contextual-review.md`

## One Sentence Lesson

An implicit theme thesis is not enough; if adverse evidence is visible but hope overrides it, the trade has moved from judgment to control failure.
