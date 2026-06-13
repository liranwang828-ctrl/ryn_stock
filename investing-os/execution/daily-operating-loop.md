# Daily Operating Loop

## After Work: Pre-Market

Inputs:

- market context
- holdings
- watchlist
- stock_team pre-market packet if available
- `decision/current-watchlist.md`
- `decision/position-roles.md`
- `decision/risk-budget.md`

Required outputs:

- allowed actions
- no-trade conditions
- alerts
- sleep risk awareness
- blocked symbols confirmed
- plan-required symbols either planned or left untouched

## Before Sleep: Risk Lock

Ask:

- Are open orders reviewed?
- Can every position be held while sleeping?
- Is any low-conviction trade capturing attention?
- Is there any action pressure not covered by plan?
- Did any trade become a sleep risk?
- Did any non-core position become emotionally oversized?

If yes:

- reduce
- close
- cancel unnecessary orders
- or write explicit risk acceptance

## During Market: Low Intervention

Rules:

- execute only prewritten plan
- respond only to predefined alerts
- do not invent new trades from price alone
- signals create review tasks, not commands
- blocked symbols cannot be traded
- plan-required symbols cannot be traded until plan exists

## Morning / Daytime: Review

If available:

- compare plan vs action
- record emotions
- update journal
- mark follow-up tasks
- update decision state if thesis, role, risk, or watchlist status changed

If missed:

- complete catch-up review before writing the next plan if material events occurred

## Daily Minimum

If time is limited, complete only:

1. watchlist state check
2. no-trade conditions
3. sleep risk lock
4. one-sentence review
