# Trade Idea Review Protocol

Date: 2026-06-02

Purpose: make the combined master + quant + portfolio review the default workflow for any candidate ticker, watchlist, entry idea, exit idea, or sector rotation question.

## Default Rule

When the user asks about a ticker, candidate pool, sector, entry, exit, add, reduce, or next-session focus list, do not answer from price action alone.

Use the full stack:

1. Market assumption
2. Portfolio constraint
3. Quant screen
4. Master lens
5. Action tier
6. Risk and invalidation

Fast answers are allowed only for pure recordkeeping, not for trade judgment.

## Postmarket Review Data Requirement

Before reviewing any completed trade, always pull or load market data first.

Minimum data for each traded symbol:

- current trade date intraday bars, preferably 1-minute bars
- same-day open, high, low, close, VWAP, day range position
- recent daily bars, at least 5-day and 10-day returns
- QQQ same-day and recent returns
- relevant sector ETF or peer basket where available
- after-hours or premarket drift if relevant

Do not evaluate whether a buy or sell was good until these are available or explicitly marked unavailable.

For user-reported free trading days without a premarket plan, the review must use:

- actual fill price versus day low/high/VWAP
- actual fill price versus close
- actual symbol return versus QQQ
- actual symbol return versus sector or closest peer group
- recent trend state before the trade

If exact intraday fill time is missing, estimate quality from fill price location inside the day range and explicitly say that time-based precision is unavailable.

## Step 1: Market Assumption

State the working market regime before ranking tickers.

Required checks:

- QQQ / SPY direction
- Relevant sector ETF direction, such as IGV, HACK, SOXX, SMH, XLC
- After-hours or premarket drift if available
- User's stated bias, such as defensive, neutral, or offensive

Output:

- `market_bias`: defensive / neutral / offensive
- `implication`: chase_allowed / pullback_only / observe_only

## Step 2: Portfolio Constraint

Before discussing new candidates, check whether the idea fits the current portfolio.

Required checks:

- Current positions and concentration
- Existing exposure to the same theme
- Cash and buying power if available
- Whether an existing position is already consuming emotional bandwidth
- Whether the new idea reduces or increases portfolio complexity

Output:

- `portfolio_fit`: good / acceptable / poor
- `constraint_note`

## Step 3: Quant Screen

Use the paid data source first when available. Prefer Polygon/Massive over yfinance.

Required metrics where available:

- 1-day return
- 5-day return
- 10-day return
- 20-day return
- 20-day volume ratio
- close position inside intraday range
- relative strength vs QQQ
- relative strength vs relevant sector ETF
- after-hours or premarket drift
- distance from recent high and low

Minimum comparison set:

- Candidate ticker
- QQQ
- Relevant sector ETF
- 2-5 peer tickers
- Existing portfolio names in the same theme

Output:

- `trend_score`
- `relative_strength`
- `volume_confirmation`
- `extension_risk`
- `pullback_quality`

## Step 4: Master Lens

Apply the masters as filters, not as decoration.

Use at least these lenses:

- Minervini: clean trend, buy point quality, extension risk
- Druckenmiller: macro/sector leadership, concentration of best idea
- Marks: safety margin and cycle risk
- Taleb: tail risk, gap risk, fragile setup
- Soros: reflexivity and narrative reinforcement
- Livermore: price confirms thesis, do not average weakness blindly
- Lynch: business logic and whether the story is understandable

Output:

- `master_consensus`: bullish / neutral / cautious / avoid
- `best_master_argument`
- `main_master_objection`

## Step 5: Action Tier

Every candidate must be assigned one tier.

Allowed tiers:

- `A`: actionable candidate today or next session, with clear conditions
- `B`: pullback candidate only
- `C`: sector gauge or watch-only confirmation name
- `D`: observe only, no trade
- `E`: remove from active watchlist

Do not use vague labels like "worth watching" without assigning a tier.

## Step 6: Risk and Invalidation

Every actionable or pullback candidate must include:

- entry condition
- no-chase condition
- invalidation level or condition
- position size class: core / tactical / satellite / no-trade
- what would upgrade or downgrade the idea

## Required Response Shape

For a single ticker:

```text
Verdict: <tier> - <role>
Market fit:
Portfolio fit:
Quant:
Master view:
Action plan:
Invalidation:
```

For a basket:

```text
Market assumption:
Portfolio constraint:
Tier table:
Master consensus:
Quant ranking:
Action plan:
What not to do:
```

## Low Model Boundary

Low-tier agents may collect data tables and draft inventories only.

They must not:

- assign final action tiers
- recommend entries or exits
- modify trading rules
- modify positions
- modify trade history
- change core JSON artifacts

High-tier model must review and approve any trade-related interpretation.

## Current Default Bias

As of the 2026-06-01 postmarket review:

- User bias for next session is defensive.
- Do not chase software or high-beta names after large up days.
- COHR is a position management object, not a new-capital candidate.
- New ideas must prove relative strength during QQQ pullback.

This default bias should be refreshed at the next premarket run.
