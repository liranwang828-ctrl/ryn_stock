# AI Trading Response Checklist

Use this checklist before any AI response involving:

- buy
- sell
- add
- reduce
- stop loss
- take profit
- candidate stocks
- sector rotation
- position management

## 1. Task Type

Classify the task first:

- pre-market planning
- intraday monitoring
- post-market review
- company research
- candidate screening
- position record
- learning / methodology discussion
- pure journal entry

Do not produce action-oriented conclusions before the task type is clear.

## 2. Data Freshness

Check whether fresh data is required.

If fresh data is missing, state the missing data clearly.

Do not infer current price, current market state, or current position state from memory.

For any post-market review, contextual trade review, exit review, or major drawdown review:

- Do not start from fills alone.
- Build or request an external market context packet first.
- Required context includes traded-symbol intraday K-line, recent daily K-line, volume, SPY / QQQ, VIX, sector ETF, peers / underlying symbols, and key trade-time market state.
- If market context is missing, mark the review as `blocked_market_context_missing`.
- User narrative may be preserved, but mistake classification and permanent lesson extraction are not allowed until context is present.

## 3. Position Role

Identify the asset role:

- long-term core
- swing
- intraday
- hand-feel trade
- leveraged / options
- watchlist only
- research only

## 4. System Fit

Check:

- Does this match the written framework?
- Does it violate a principle?
- Does it increase attention burden?
- Does it trigger known error patterns?
- Is there a written thesis?
- Is there falsification?
- Is there position sizing?

## 5. Known Error Patterns

Watch for:

- a single position occupying all attention
- regret loop after first profit-taking
- opening new trades after large same-day profit
- FOMO after strong open far from VWAP
- low-quality hand-feel trades late in session
- mechanical sector sympathy transfer
- signal treated as thesis
- losing trade turned into cost-reduction project

## 6. Required Output Structure

For single-asset review:

```text
Task type:
Facts:
Position role:
Market context packet:
Market / sector context:
Signal:
Thesis:
Risk:
Falsification:
System fit:
Missing data:
Allowed next steps:
Human decision required:
```

For post-market / major drawdown review:

```text
Task type:
Review status:
Market context packet:
External market facts:
Fills / actions:
Position roles:
Account damage:
Plan vs action:
Emotion:
System failure candidates:
Missing data:
Allowed next steps:
Human decision required:
```

For candidate-pool review:

```text
Market assumption:
Position constraints:
Candidate tiers:
Quant / signal notes:
Mainline judgment:
What not to do:
Allowed next steps:
Missing data:
Human decision required:
```

## 7. Forbidden Output

AI must not:

- issue final buy / sell / hold commands
- encourage breaking position limits
- bypass risk checks
- turn missing data into certainty
- convert one-day noise into permanent principles
- treat a signal as a trade command

## 8. System Basis

For important trading responses, include:

```text
System basis:
- WHY / constitution:
- framework:
- principles:
- data:
- position role:
- missing:
```
