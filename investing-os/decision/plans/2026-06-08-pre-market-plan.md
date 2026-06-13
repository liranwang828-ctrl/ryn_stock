# 2026-06-08 Pre-Market Plan

Superseded: this draft was created before the Stage 0 discussion had a user-confirmed Stage 1 focus pool. It is preserved only as a historical draft. The valid plan for today's first operating pass is `decision/plans/2026-06-08-pre-market-plan.INTC-MU-COHR.v2.md`, using only `INTC + MU + COHR`.

Task type: pre-market planning

Status: cognition-system first operating pass after Stage 0 + Stage 1 evidence

This is a plan draft, not a trading instruction.

## System Basis

- WHY / constitution: AI assists; user decides.
- Framework: Stage 0 sets risk context; Stage 1 selects worthy candidates; intraday executes only written plans.
- Factor source: `D:\gemini\lianghua\stock_team\findings\cycle_factor_search_findings_v1.md`
- Stage 0 packet: `system/data/packets/pre-market-context-packet.2026-06-08.cognition-v1.md`
- Stage 1 packet: `system/data/packets/plan-evidence-packet.2026-06-08.cognition-v1.md`
- Fresh data status: Stage 0 exists; Stage 1 exists but is `fallback_data` because Polygon failed and yfinance sandbox data was used.
- Permission implication: no new pre-authorized entries today.

## Overnight Information

Known from local research evidence:

- Mixed candidate50 did not show strong bull-market alpha versus QQQ.
- Growth / AI / semis / software universe showed stronger Stage 1 quality.
- Train-selected leader subset excluding META outlier retained positive test-period 10D alpha_vs_QQQ.
- Transition-market exposure should be downgraded unless a stronger catalyst packet exists.

Missing:

- Current account / position snapshot.
- Current catalyst/news check for leader subset symbols.
- Production-grade Polygon / IBKR symbol evidence.

## Market Context

Market assumption: Yellow / risk-off pressure.

Stage 0 facts:

- QQQ yesterday `-4.80%`, 5D `-4.50%`, 20D `+1.46%`, volume ratio `2.4x`.
- SPY yesterday `-2.58%`, 5D `-2.50%`, 20D `+0.82%`, volume ratio `1.9x`.
- VIXY yesterday `+7.23%`, 5D `+4.38%`, 20D `-9.46%`, volume ratio `2.0x`.
- SMH 5D `-4.88%`, 20D `+5.48%`.
- SOXX 5D `-5.15%`, 20D `+9.63%`.

Interpretation boundary:

- This is factual context, not trade permission.
- Broad growth risk is under short-term pressure.
- Semiconductor theme remains stronger on 20D than on 5D.
- Do not upgrade any symbol because it belongs to the leader subset.
- If transition_market is confirmed, downgrade new-risk plans unless catalyst evidence is unusually strong.

Required Stage 0 evidence:

| Evidence | Purpose | Status |
|---|---|---|
| QQQ | market cycle and broad risk state | ready |
| SPY | broad confirmation | ready |
| VIXY | volatility proxy | ready |
| SMH / SOXX | semiconductor theme confirmation | ready |
| account / positions | permission and exposure check | missing fresh packet |

## Watchlist

### Existing System Watchlist

| Symbol | Role | Today State | Allowed Next Step |
|---|---|---|---|
| NVDA | existing watchlist + leader subset | observe / evidence request | Build Stage 1 packet; no new action without plan |
| COHR | plan_required | observe / thesis review | Review swing candidate; no chase or add |
| ORCL | plan_required | research lifecycle | No rebound impulse re-entry |
| INTC | plan_required | research lifecycle | No trade without trigger and time stop |
| SNXX | blocked_pending_review | blocked | No new trade |

### Stage 1 Leader Subset Under Research

| Tier | Symbols | Today Use | Constraint |
|---|---|---|---|
| first focus | RKLB, NVDA, AVGO, PLTR, NET | Request Stage 1 evidence first | Observe-only until packet exists |
| secondary focus | TSLA, LITE, PANW, MDB, DDOG | Keep in research queue | Do not expand intraday attention |

Rationale:

- First focus includes symbols from the train/test leader subset with enough strategic relevance to cognition.
- This is a research priority list, not a trade list.

## Key Levels Or Events

Not available yet.

Required from stock_team Stage 1 packet:

- symbol daily position versus MA20 / MA50
- RS20 / RS50 versus QQQ
- sector / theme confirmation versus SMH, SOXX, or relevant proxy
- 10D / 20D forward evidence classification from research system
- fresh catalyst check
- current risk distance and invalidation reference

Stage 1 packet facts:

| Symbol | 1D % | 5D % | 20D % | MA20 Distance | MA50 Distance | Plan Mode |
|---|---:|---:|---:|---:|---:|---|
| RKLB | -8.23% | -23.28% | +40.09% | -10.04% | +19.36% | observe |
| NVDA | -6.20% | -2.86% | -3.03% | -3.82% | +3.58% | observe |
| AVGO | -7.92% | -13.66% | -6.50% | -7.16% | -0.03% | observe |
| PLTR | -4.35% | -13.42% | -1.11% | -2.13% | -3.04% | observe |
| NET | -6.90% | +3.43% | -2.60% | +13.91% | +18.33% | observe |

Stage 1 warning:

- `polygon_api_key_missing_or_failed; fell back to yfinance sandbox data which is not production grade`

## Planned Actions

1. Keep permission state Yellow / observe-only because Stage 1 is fallback data.
2. Keep first focus pool as RKLB, NVDA, AVGO, PLTR, NET for cognition and evidence review only.
3. Do not create intraday entries from this packet.
4. Request production-grade runtime evidence before any future upgrade.
5. Treat today's broad-market weakness as a reason to avoid new unplanned risk.

## Pre-Authorized Actions

None.

These are not orders. They define what may be considered intraday if every condition remains true.

| Symbol | Scope | Tactic | Max Loss | Position Cap | Trigger Window | Stale Data Limit | Slippage Limit | Manual Confirm |
|---|---|---|---:|---:|---:|---:|---:|---|
| ALL | evidence_only | none | 0 | 0 | n/a | 0s | n/a | yes |

## Fast Consistency Check

- data_fresh: Stage 0 yes; Stage 1 fallback only
- same_permission_state: unknown until account snapshot
- no_exception_triggered: unknown
- position_cap_not_exceeded: unknown
- daily_loss_limit_not_exceeded: unknown
- not_repair_trading: required

## Intraday Exception Rules

| Exception | Trigger | Effect |
|---|---|---|
| market_context_missing | Stage 0 packet missing or stale | observe-only |
| stage1_evidence_missing | Symbol packet missing | no new action |
| transition_market_confirmed | QQQ cycle is transition_market and no strong catalyst packet | no new risk |
| data_stale | runtime data stale beyond packet limit | pause_for_brain_review |
| account_mismatch | positions / orders unavailable or inconsistent | pause_for_brain_review |
| repair_motive | desire to recover prior loss or missed move | no_trade |

## No-Trade Conditions

- No fresh Stage 0 packet.
- No fresh Stage 1 packet for the symbol.
- User has not confirmed focus pool.
- Intraday narrative invents a symbol not in today's plan.
- Action would be based only on leader-subset membership.
- Action would increase attention burden before evidence is ready.
- Current position / account data is missing.

## Discipline Reminder

Today is the first cognition-system operating pass.

The job is to make the system smarter before the market creates pressure.

Leader subset is a research edge, not permission.
