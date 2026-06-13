# 2026-06-08 Pre-Market Plan: INTC + MU + COHR

Task type: pre-market planning

Status: workflow practice draft. The user later identified that the Stage 0 evidence is not a valid pre-market packet because it lacks true pre-market data and can include post-open / stale cache leakage.

This is a plan draft, not a trading instruction.

## System Basis

- WHY / constitution: AI assists; user decides.
- Framework: Stage 0 sets risk context; brain/user confirms Stage 1 focus pool; stock_team calculates evidence; intraday executes only written plans.
- Stage 0 packet: `system/data/packets/pre-market-context-packet.2026-06-08.INTC-MU-COHR.v2.md`
- Stage 1 packet: `system/data/packets/plan-evidence-packet.2026-06-08.INTC-MU-COHR.v2.md`
- Permission state: not valid for real planning from this artifact.
- Data caveat: Stage 0 is invalid for real pre-market use; Stage 1 is `fallback_data` because Polygon failed and yfinance sandbox data was used.

## Validity Correction

This file is kept only as a process rehearsal.

It must not be treated as a valid 2026-06-08 pre-market plan because:

- Stage 0 did not contain a true pre-market snapshot.
- Later verification showed the market-context cache could reuse stale / prior-session figures.
- Post-open or post-close data must not be used to reconstruct a pre-market decision state.
- The focus pool was user-specified for practice, not produced by the full cognition discussion process.

## Stage 0 Discussion Result

Stage 0 facts:

- QQQ yesterday `-4.80%`, 5D `-4.50%`, 20D `+1.46%`, volume ratio `2.4x`.
- SPY yesterday `-2.58%`, 5D `-2.50%`, 20D `+0.82%`, volume ratio `1.9x`.
- VIXY yesterday `+7.23%`, 5D `+4.38%`, 20D `-9.46%`, volume ratio `2.0x`.
- SMH 5D `-4.88%`, 20D `+5.48%`.
- SOXX 5D `-5.15%`, 20D `+9.63%`.

Brain/user discussion outcome:

- Do not use the leader-subset research pool for today's Stage 1.
- Today's focus pool is only `INTC + MU + COHR`.
- Broad market pressure makes new-risk permission inappropriate without a separate plan.

## Stage 1 Evidence

Packet status: `fallback_data`.

| Symbol | 1D % | 5D % | 20D % | Volume Ratio | Plan Mode | Boundary |
|---|---:|---:|---:|---:|---|---|
| INTC | +11.82% | +1.43% | -11.23% | 0.11x | observe | turnaround narrative cannot become thesis intraday |
| MU | -13.25% | -11.02% | +33.62% | 1.37x | observe | memory-cycle excitement cannot become entry signal |
| COHR | -10.64% | +4.29% | +18.11% | 1.04x | observe | no chase; no add while lagging peers |

Evidence warning:

- `polygon_api_key_missing_or_failed; fell back to yfinance sandbox data which is not production grade`

## Planned Actions

1. Keep INTC, MU, and COHR as observe-only today.
2. Do not create intraday entry authorization from fallback data.
3. Use the packet to guide cognition: what needs research, what not to chase, and what would falsify interest.
4. If production-grade runtime evidence becomes available later, discuss again before writing any symbol-level plan.

## Pre-Authorized Actions

None.

| Symbol | Scope | Tactic | Max Loss | Position Cap | Trigger Window | Stale Data Limit | Slippage Limit | Manual Confirm |
|---|---|---|---:|---:|---:|---:|---:|---|
| INTC | evidence_only | none | 0 | 0 | n/a | 0s | n/a | yes |
| MU | evidence_only | none | 0 | 0 | n/a | 0s | n/a | yes |
| COHR | evidence_only | none | 0 | 0 | n/a | 0s | n/a | yes |

## No-Trade Conditions

- Stage 1 remains fallback_data.
- Current account / position snapshot is missing.
- Action would be based on a one-day move.
- Action would be based on theme excitement without fresh catalyst confirmation.
- Action would convert observe-only evidence into an entry plan.
- Repair motive, regret, or urgency appears.

## Intraday Exception Rules

| Exception | Trigger | Effect |
|---|---|---|
| fallback_data_only | Stage 1 uses sandbox/fallback data | observe-only |
| market_pressure | QQQ / SPY remain under short-term pressure | no new unplanned risk |
| account_mismatch | positions / orders unavailable or inconsistent | pause_for_brain_review |
| repair_motive | desire to recover loss or missed move | no_trade |

## Discipline Reminder

Today's correct win is following the sequence:

Stage 0 -> discussion -> Stage 1 focus pool -> evidence -> observe-only unless a real plan is written.
