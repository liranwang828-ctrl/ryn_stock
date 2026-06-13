# 2026-06-05 Major Drawdown Review

## Metadata

```yaml
local_review_date: 2026-06-06
market_date: 2026-06-05
status: intake_started
severity: major_drawdown
trade_permission_during_review: no
market_context_packet: complete
facts_status: partial
```

## Purpose

This is not a normal post-market review.

This review is for a major drawdown event that:

- created the largest single-day drawdown so far
- caused emotional breakdown
- affected principal capital
- may require changes to risk, execution, and recovery rules

The goal is not to judge the user.

The goal is to reconstruct:

```text
facts
|
position and risk exposure
|
decision chain
|
emotional state
|
system failures
|
recovery protocol
```

## Review Rule

No lesson is promoted to permanent personal cognition until user review.

Candidate lessons must go through:

- `evolution/promotion-queue.md`

## Phase 0: Stabilization

Before analysis, answer:

- Is the account still exposed to unmanaged risk?
- Is there any position that can still cause forced or emotional action?
- Is there any margin / leverage / options / leveraged ETF risk?
- Is sleep and basic recovery possible tonight?
- Is the user emotionally stable enough to analyze, or should the system only preserve facts first?

Current status:

```yaml
stabilization_status: active_unmanaged_risk_confirmed
open_risk_status: confirmed_open_high_risk_position
emotional_capacity: impaired
analysis_depth_allowed: gradual
```

Screenshot-based stabilization notes:

- The latest visible fill is `MUU buy 30 @ 731.73`, not followed by a visible sell in the provided screenshots.
- User confirmed the `MUU` position is still open and already down about `$2,000`.
- Polygon snapshot check showed `MUU` day close around `661.33` and latest minute around `649.99`; against the visible `731.73` entry, the estimated unrealized loss range is roughly `$2,112` to `$2,452` for 30 shares, depending on reference price.
- This is now a confirmed open high-risk position, not merely a possible leftover position.
- Several traded instruments appear to be leveraged / single-stock trading tools, including `MULL`, `MUU`, `LITX`, and `COHX`.
- No options fills are visible in the screenshots.
- Margin usage is not visible from the screenshots.

## Phase 1: Account Damage

To fill:

```yaml
starting_net_liquidation:
ending_net_liquidation:
day_pnl:
realized_pnl: -2666.55 visible_local_2026-06-06_bucket
unrealized_pnl: MUU about -2000 user_reported; estimated -2112 to -2452 from visible entry and snapshot references
principal_affected: yes_reported_by_user
max_intraday_drawdown:
margin_used:
leverage_used: likely_leveraged_products_visible
largest_position: MUU buy 30 @ 731.73 visible_notional 21951.90 confirmed_still_open
largest_loss_source: MULL visible_realized_loss_about -2048.86
```

Visible account damage facts:

- Broker 7-day realized P/L header shows `+$506.19` for `May 31, 2026 - Jun 06, 2026`.
- Local `June 05, 2026` bucket shows `+$1,086.28`.
- Local `June 06, 2026` bucket shows `-$2,666.55`.
- User confirmed `MUU` is still open and down about `$2,000`.
- Using visible entry `MUU buy 30 @ 731.73`, the open position had visible notional exposure of about `$21,951.90`.
- Polygon snapshot reference: `MUU` day close around `661.33`; latest minute around `649.99`.
- The screenshot does not show account net liquidation, intraday low, unrealized P/L, buying power, or margin status.
- Therefore realized loss is visible and open risk is confirmed, but true maximum account drawdown is still not measurable without account net liquidation / margin data.

Questions:

1. How much was the account down at the worst point?
2. How much was realized versus unrealized?
3. Did the drawdown come from one position, several positions, or portfolio-wide exposure?
4. Was leverage involved?
5. Did any loss exceed the originally acceptable risk?

## Phase 2: Position Inventory

For each important symbol:

| Symbol | Role Before Day | Size | Action | P/L | Thesis Status | Process Quality |
|---|---|---:|---|---:|---|---|
| MUU | leveraged tool / high-risk exposure | 30 visible latest buy | buy @ 731.73 | unrealized unknown | no documented thesis yet | unresolved risk |
| MULL | leveraged tool / short-term | multiple 10/40 share trades | buy / sell / re-buy / sell | about -2048.86 visible realized | no documented thesis yet | major loss source |
| COHX | leveraged tool / short-term | 10/20/30/40 share trades | rapid in-out | about +33.84 visible realized | no documented thesis yet | repeated short-term trading |
| LITX | leveraged tool / short-term | 100 visible buy, partial exits | buy / sell | about +67.89 visible realized | no documented thesis yet | rapid short-term trading |
| COHR | swing candidate | 5 visible | buy then sell | -76.54 visible realized | thesis not invalidated by screenshot | possibly affected by risk event |
| PLTR | existing position / unclear | 10 visible sell | sell | -88.73 visible realized | unknown | possibly affected by risk event |
| VRT | existing position / unclear | 10 visible sell | sell | -296.55 visible realized | unknown | possibly affected by risk event |

Role options:

- core
- swing
- short-term
- leveraged tool
- emotional repair trade
- unclear

## Phase 3: Timeline Reconstruction

Use exact timestamps when possible.

External market data must be reviewed before interpreting user behavior.

Market context packet:

- `system/data/market-context/2026-06-05-major-drawdown/market-context-summary.md`
- Raw 5-minute and daily aggregate files are stored in `system/data/market-context/2026-06-05-major-drawdown/`.

Data sources:

- Polygon / Massive 5-minute and daily aggregates for stocks and ETFs.
- Yahoo chart `^VIX` for VIX, because the Polygon index endpoint was unavailable under the current API permission.

Regular-session market facts:

| Symbol | Regular Return | Volume vs 20D Avg | Interpretation |
|---|---:|---:|---|
| QQQ | -3.74% | 2.56x | broad Nasdaq risk-off, high-volume selloff |
| SPY | -2.26% | 2.00x | broad market weakness |
| SOXX | -6.90% | 2.53x | semiconductor sector under heavier pressure than QQQ |
| SMH | -6.05% | 2.16x | semiconductor weakness confirmed |
| MU | -8.62% | 1.40x | memory exposure materially weaker than QQQ |
| MULL | -18.05% | 1.48x | leveraged memory tool amplified the move |
| MUU | -18.40% | 1.60x | leveraged memory tool amplified the move |
| COHR | -7.47% | 0.99x | optical / AI infra swing candidate also weakened |
| NVDA | -4.61% | 1.25x | AI leader weaker than QQQ, but far less severe than memory leveraged tools |

VIX:

- `^VIX` regular-session open: `16.04`
- `^VIX` regular-session close: `21.01`
- Change: `+4.97 points`, about `+30.99%`
- Interpretation: volatility regime moved from calm to elevated during the session.

Initial market-context conclusion:

- This was not a normal single-name mistake day.
- It was a broad high-volume risk-off session.
- Semiconductor / AI beta was weaker than QQQ.
- Memory-linked leveraged tools were much weaker than the market and much weaker than the underlying broad AI basket.
- The trading damage must be analyzed as `systemic risk-off + leveraged instrument amplification + repeated re-entry after loss`, not just as bad entries.

| Time | Market Context | Position / Action | Reason At The Time | Emotion | Rule Status |
|---|---|---|---|---|---|
| | | | | | |

Important timestamps:

- first decision that increased risk
- first moment the plan stopped matching reality
- first moment emotional control broke
- largest loss point
- action taken during breakdown
- final risk state

Visible screenshot timeline:

| Local Time | Position / Action | Visible Notional | Visible P/L | Notes |
|---|---|---:|---:|---|
| 20:54:24 | COHR buy 5 @ 406.9 | 2034.50 | | swing candidate exposure opened |
| 22:01:26 | COHX buy 10 @ 59.53 | 595.30 | | short-term / leveraged tool candidate |
| 22:04:51 | COHX sell 10 @ 61.65 | 616.45 | +19.14 | quick profit |
| 22:12:25 | COHX buy 20 @ 63.9 | 1278.00 | | re-entry |
| 22:14:03 | COHX buy 20 @ 64.52 | 1290.40 | | add |
| 22:19:29 | COHX sell 40 @ 65.5 | 2620.00 | +48.54 | exit |
| 22:21:30 | MULL buy 10 @ 700.3 | 7003.00 | | high-notional leveraged tool candidate |
| 22:24:30 | LITX buy 100 @ 43.4 | 4340.00 | | short-term exposure |
| 22:26:49 | MULL buy 10 @ 686.87 | 6868.65 | | add after lower price |
| 22:39:09 | MULL sell 10 @ 706 | 7060.00 | +122.03 | partial realized profit |
| 22:59:22 | LITX sell 50 @ 45.92 | 2296.00 | +124.44 | partial profit |
| 23:06:33 | MULL buy 10 @ 691 | 6910.00 | | re-entry |
| 23:21:49 | LITX sell 50 @ 42.3 | 2115.00 | -56.55 | loss on remaining LITX |
| 23:25:20 | MULL buy 10 @ 674 | 6740.00 | | add after lower price |
| 23:49:05 | COHX buy 30 @ 64 | 1920.00 | | new COHX exposure |
| 00:07:46 | MULL buy 10 @ 667 | 6670.00 | | further MULL add |
| 00:20:45 | COHX sell 30 @ 62.94 | 1888.20 | -33.84 | loss exit |
| 00:32:12 | MULL sell 40 @ 642 | 25680.00 | -1581.36 | major realized loss |
| 00:55:04 | MULL buy 40 @ 642.67 | 25707.00 | | re-entry after major loss |
| 01:08:40 | MULL sell 40 @ 628 | 25120.00 | -589.53 | second major MULL loss |
| 01:10:43 | COHR sell 5 @ 392 | 1960.00 | -76.54 | swing candidate sold during event |
| 01:11:02 | PLTR sell 10 @ 136.78 | 1367.80 | -88.73 | existing position sold |
| 01:15:55 | VRT sell 10 @ 302.7 | 3027.01 | -296.55 | existing position sold |
| 01:29:27 | MUU buy 30 @ 731.73 | 21951.90 | | latest visible action; open status unknown |

Key market-state timestamps:

| Local Time | Event | QQQ From Open | SOXX From Open | MU From Open | MULL From Open | MUU From Open | VIX |
|---|---|---:|---:|---:|---:|---:|---:|
| 20:54 | COHR first buy | +0.11% | +0.62% | +0.65% | +3.00% | +1.25% | unavailable |
| 22:21 | MULL first buy | -0.54% | -0.68% | -0.36% | -0.92% | -1.08% | 16.42 |
| 00:32 | MULL major loss sell | -1.76% | -3.45% | -4.03% | -8.57% | -8.70% | 18.51 |
| 00:55 | MULL re-entry after loss | -1.81% | -3.50% | -4.15% | -8.72% | -8.82% | 18.55 |
| 01:08 | MULL second loss sell | -2.05% | -4.16% | -4.77% | -10.36% | -10.07% | 18.60 |
| 01:29 | MUU latest visible buy | -1.97% | -3.72% | -4.16% | -9.24% | -8.72% | 18.40 |

## Phase 4: Plan vs Action

For each major action:

```yaml
planned_action:
actual_action:
deviation:
reason_given_at_time:
real_reason_after_review:
was_thesis_explicit:
was_risk_predefined:
was_add_rule_predefined:
was_exit_rule_predefined:
```

Initial plan-vs-action reconstruction:

| Area | Planned / Required By System | Actual From Evidence | Deviation |
|---|---|---|---|
| Market context | Review QQQ / VIX / sector before interpreting opportunity | Initial behavior occurred during broad risk-off and semiconductor weakness | Market context was not treated as a hard veto |
| Instrument role | Leveraged / single-stock tools require explicit risk budget and exit plan | `MULL`, `MUU`, `LITX`, `COHX` were traded rapidly | Instrument risk outran written plan |
| Position sizing | Non-core / short-term exposure should not threaten principal or emotional stability | `MUU` latest visible notional about `$21,951.90`; open loss about `$2,000+` | Size became too large for an unresolved short-term trade |
| Loss response | Stop, pause, review; do not re-risk to repair pain | After `MULL` realized major loss, there was a `MULL buy 40 @ 642.67` re-entry | Loss was followed by renewed exposure |
| Portfolio impact | Existing positions should be evaluated by thesis and risk separately | `COHR`, `PLTR`, `VRT` sold during the event | Possible spillover from leveraged-tool damage into unrelated holdings |
| End state | Major drawdown should end with risk contained | `MUU` remained open and down about `$2,000` | Review begins with unresolved risk |

Important distinction:

- Some sells may have reduced further damage.
- But the reason for each sell still needs review.
- A good outcome on one action does not erase process failure in the surrounding chain.

Thesis / instrument mismatch:

The user still has a plausible high-level thesis:

- AI remains a major market theme.
- Memory may remain an important part of the AI infrastructure cycle.
- Storage / memory exposure may still deserve research and portfolio representation.

But the trade under review was not simply `memory thesis exposure`.

It became:

```text
AI / memory macro thesis
used to justify
leveraged short-term tool exposure
after realized loss
inside a broad risk-off session
without predefined max loss, add rule, or holding horizon
```

This mismatch is central.

The review should not ask only:

- Is memory still a good theme?

It must also ask:

- Is `MUU` the correct instrument for this thesis?
- Is this position size compatible with the user's emotional and capital constraints?
- Is the current holding a planned thesis position or a trapped repair position?
- If the thesis needs months, can a leveraged tool survive the path?
- If the trade was short-term, why is it being evaluated by long-term thesis logic?

## Open MUU Risk Decision Review

This section is for risk framing only.

It does not decide for the user.

Current known facts:

```yaml
symbol: MUU
underlying: MU
product_type: daily_2x_single_stock_leveraged_etf
visible_entry: 30 @ 731.73
visible_notional: 21951.90
user_reported_unrealized_loss: about -2000
position_classification_by_user: trapped_position_after_loss_repair
emotional_status: hijacking_decision_and_attention
```

Product-mechanics note:

- `MUU` is a daily 2x leveraged product tied to Micron (`MU`).
- Daily leveraged products are designed around daily percentage changes, not clean long-term 2x thesis expression.
- Path matters: a volatile down-then-up path can damage the leveraged product even if the underlying later improves.
- This is especially important when the user thesis may require weeks or months.

Risk questions before any action:

1. If this were a fresh trade today, would the user choose `MUU`, this size, and this holding horizon?
2. Is the position being held because the thesis is strong, or because realizing the loss is painful?
3. What account-level loss would make this position unacceptable even if the thesis remains plausible?
4. What underlying `MU` behavior would prove the relative-strength idea is failing?
5. What market condition would make any memory exposure temporarily invalid, even if the long-term theme remains intact?

Leveraged survival assessment framework:

```text
underlying thesis
|
expected holding period
|
expected path volatility
|
instrument leverage and daily reset
|
account-level loss tolerance
|
attention / sleep cost
|
decision: same instrument / smaller size / different instrument / no exposure
```

The current issue is not only price loss.

The current issue is that `MUU` has become:

```text
thesis exposure
+ loss repair object
+ emotional burden
+ capital lock risk
+ path-dependent leveraged instrument
```

### MUU Risk Decision Table

This table is not an instruction.

It is a decision aid for the user.

| Option | What It Means | When It Makes Sense | Main Cost | Main Risk | What It Tests |
|---|---|---|---|---|---|
| Hold full `MUU` | Keep current trapped position unchanged | Only if user can define max acceptable loss, time horizon, and invalidation before next session | Continued emotional burden and capital lock | Further gap-down / volatility decay / panic selling later | Whether this is truly planned thesis exposure |
| Reduce `MUU` | Cut part of the position to reduce emotional and account pressure | If position size is the main reason the user cannot think clearly | Realizes part of loss and may feel like admitting failure | Remaining position may still hijack attention if no plan exists | Whether lower size restores cognition |
| Exit `MUU` | Close the trapped leveraged position | If the position is primarily loss repair, not planned thesis exposure | Locks in loss and creates regret risk if rebound happens | Emotional pain may trigger revenge trade unless blocked | Whether protecting cognition matters more than repair |
| Convert to `MU` | Replace leveraged product with underlying exposure | If memory thesis remains valid but leveraged path risk is unsuitable | May realize `MUU` loss and reduce upside speed | Still exposed to MU downside, but without 2x daily reset | Whether the thesis is about MU, not leverage |
| Wait for structured rebound to reassess | Define a short window and key levels before deciding | If immediate action is too emotional and a plan can be written | Risk continues during waiting period | Waiting can become passive hope if no invalidation exists | Whether user can wait with rules, not hope |
| Do nothing emotionally | Avoid deciding and keep watching | Never a deliberate plan; this is the default failure mode | Sleep, attention, future decisions | Position continues controlling the user | Confirms the trade remains in control |

### Required Decision Inputs Before Next Session

Before any new trade idea is allowed, the user must answer:

```yaml
current_MUU_size:
current_MUU_unrealized_pnl:
account_net_liquidation:
max_additional_loss_user_can_accept:
margin_used:
must_sleep_before_next_session: yes/no
chosen_option:
if_hold_or_wait:
  max_loss:
  time_limit:
  invalidation:
  reassessment_trigger:
if_reduce_or_exit:
  revenge_trade_block:
  next_trade_allowed_after:
```

### Falsification Should Be Split

The current confusion comes from using one falsification question for three different things.

They must be split:

| Layer | Question | Possible Falsification |
|---|---|---|
| Memory thesis | Is memory still part of AI infrastructure mainline? | Broad evidence that AI capex / memory demand narrative is breaking, not just one market selloff |
| MU relative strength | Is MU still the right expression? | After market stabilization, MU fails to repair, loses RS vs QQQ / SOXX / SMH, or breaks key structure on weak demand |
| MUU instrument | Is daily 2x MUU suitable for this exposure? | If holding period is uncertain, path volatility is high, or position hijacks emotion / capital, MUU is invalid even if MU thesis remains plausible |

Current working classification:

```yaml
memory_thesis_status: not_falsified_by_one_broad_risk_off_day
MU_relative_strength_status: needs_recheck_after_market_stabilizes
MUU_instrument_status: invalid_for_current_emotional_and_process_state
current_position_status: trapped_position_pending_user_decision
```

### User Risk Inputs

User provided:

```yaml
current_MUU_size: 30
account_net_liquidation: 37000
max_additional_loss_user_can_accept: 2000
margin_used: no
```

Derived risk facts:

```yaml
visible_MUU_entry_notional: 21951.90
entry_notional_as_account_pct: 59.33
current_loss_reported: about -2000
current_loss_as_account_pct: about -5.41
max_additional_loss_as_account_pct: 5.41
total_tolerated_MUU_loss_from_entry: about -4000
total_tolerated_MUU_loss_as_account_pct: about -10.81
additional_price_drop_allowed_per_share: about 66.67
```

Interpretation:

- This is not a small tactical trade.
- `MUU` entry notional was about `59%` of account net liquidation.
- The user has already experienced about a `5.4%` account hit from this open position.
- The stated additional tolerance of `$2,000` would bring this single trapped position's total loss to about `$4,000`, or roughly `10.8%` of account net liquidation.
- Because no margin is used, forced liquidation risk is lower than with margin, but emotional and capital-lock risk remain high.

Risk boundary:

```yaml
if_MUU_additional_loss_reaches: -2000
then:
  - position has exceeded user-stated tolerance
  - no new bullish interpretation should override this without explicit user re-approval
  - review must treat continued holding as a new decision, not continuation of old trade
```

User recovery insight:

```text
This loss made the user feel the importance of firmly trusting system decisions.
The user wants decisions made in a fully rational state to govern later execution.
The key is not never losing money, but not letting emotional states override prior rational system decisions.
```

Candidate recovery principle:

```yaml
status: candidate_only_pending_user_review
principle: Trust the decision made by the system in a rational state; do not let a later emotional state rewrite it.
scope:
  - risk exits
  - stop-trading decisions
  - max-loss boundaries
  - leveraged-product handling
not_scope:
  - blind faith in any prior idea
  - refusing to update when new evidence invalidates the plan
guardrail:
  - rational decisions must be written before emotional stress
  - later changes require new evidence, not pain relief
```

### MUU Rational-State Handling Plan

Status:

```yaml
status: draft_pending_user_review
purpose: contain_existing_trapped_position
not_purpose:
  - recover all losses quickly
  - prove the memory thesis
  - create a new bullish trade
  - add exposure
```

Position:

```yaml
symbol: MUU
size: 30
entry_reference: 731.73
entry_notional: 21951.90
account_net_liquidation_reference: 37000
current_loss_reference: about -2000
max_additional_loss_allowed: 2000
margin_used: no
```

Hard rules:

1. No adding to `MUU`.
2. No new leveraged product trade until this review is completed.
3. No new unrelated trade while `MUU` remains emotionally dominant.
4. If a decision is made before market open in a calm state, do not rewrite it during panic or relief.
5. Any plan change requires objective new evidence, not desire to repair loss.

Decision branches:

| Branch | Condition | Action Type | What It Protects |
|---|---|---|---|
| Further breakdown | Additional `MUU` loss approaches `$2,000` | Execute predefined risk containment; do not reinterpret | Account and cognition |
| Weak bounce | Price rebounds but MU / SOXX / QQQ remain weak | Use bounce to reduce trapped risk or reassess; never add | Prevent relief from becoming re-risking |
| Rebound risk-reduction | `MUU` rebounds enough to reduce loss, but position is still emotionally dominant | Reduce part of the position according to a prewritten amount | Convert rebound into lower risk, not renewed hope |
| Strong structured rebound | MU outperforms QQQ / SOXX, market stabilizes, VIX cools | Decide whether to reduce, hold smaller, or convert exposure | Separate thesis from trapped position |
| Market stabilizes but MU fails | QQQ / SOXX stabilize while MU / MUU fail to repair | Treat MU relative-strength thesis as deteriorating | Prevent thesis attachment |
| Emotional overload | User cannot stop watching or sleep / work is affected | Prioritize reducing cognitive burden | Protect decision quality |

Rebound reduction rule candidate:

```yaml
status: candidate_pending_user_review
principle: For a trapped leveraged position, rebound is first a risk-reduction opportunity, not proof that the original trade was right.
allowed_rebound_actions:
  - reduce position size
  - convert part of leveraged exposure into underlying exposure
  - define a smaller hold with explicit max loss
forbidden_rebound_actions:
  - add because price bounced
  - cancel max-loss boundary because relief appears
  - reinterpret trapped position as clean thesis exposure without writing a new plan
```

Pre-market checklist before next session:

```yaml
QQQ_state:
SOXX_state:
SMH_state:
MU_state:
MU_relative_strength_vs_QQQ:
MU_relative_strength_vs_SOXX:
VIX_state:
MUU_unrealized_pnl:
can_user_execute_without_revenge_trade: yes/no
chosen_branch:
```

Execution standard:

- The goal is not to be perfectly right.
- The goal is to make the next action from the rational system, not from fear or repair desire.
- If the user chooses to hold, it must be a new written decision with loss limit and time limit.
- If the user chooses to reduce or exit, it is a risk decision, not proof that the memory thesis is false.

### Tactical Origin Of The Breakdown

User narrative:

- The original plan was ultra-short-term profit capture.
- Early execution appeared successful:
  - `COHX` produced profit.
  - `LITX` produced profit.
  - first `MULL` trade produced profit.
- User believed a high-win-rate tactic had been found:
  - identify relative strength during a selloff
  - find a balance / stabilization point
  - enter for rebound
  - take half profit near disagreement / resistance
  - let the remaining position run
- The method resembled the prior `SNXX` pattern:
  - after locking profit on part of the position
  - the remaining part failed to reach expectation
  - user tried to reuse the method and add
  - the add sequence grew larger and became uncontrolled
- User chose leveraged products because the tactic appeared high win-rate and leverage made the feedback fast.
- User also recognized overconfidence:
  - recent overall P/L had been positive
  - `COHR` contributed a large part of the profits
  - some profit had luck and favorable-market components
  - the recent successful short-term trades also worked partly because the market had been trending upward
  - when the market switched to a broad decline, the same tactic became much less controllable
  - tactic failure then combined with emotional instability

Candidate mechanism:

```text
early short-term wins
|
recent overall profitability
|
overconfidence / inflated trust in hand-feel
|
belief that a high-win-rate tactic was found
|
leverage chosen because feedback was fast
|
market regime changed from supportive/uptrend to broad selloff
|
market selloff exceeded user's expected range
|
waiting for rebound
|
loss made rebound feel more valuable
|
same tactic reused to repair loss
|
adds increased
|
loss of control
```

Important distinction:

- The initial tactic was not necessarily invalid.
- The failure came from using a short-term tactic without hard stop, max re-entry count, leverage cap, market-context veto, and post-loss no-trade rule.
- A tactic can have edge in some regimes but still become dangerous when the trader starts using it to repair the previous failed attempt.
- Recent profits should not automatically be interpreted as evidence that the tactic itself has durable edge.
- Separate skill, market beta, luck, and one large winner before increasing size or leverage.

Overconfidence diagnosis candidate:

```yaml
status: candidate_pending_user_review
pattern: recent_profit_overconfidence
description: Recent profits, especially from a large winner and favorable market trend, increased confidence in short-term tactics and reduced discipline when regime changed.
components:
  - COHR contributed large profit
  - luck / favorable trend contributed to recent results
  - short-term wins reinforced hand-feel
  - leverage was chosen because the tactic felt high-win-rate
  - broad market decline invalidated the environment for the tactic
failure_mode:
  - edge inferred too quickly
  - market regime ignored
  - size and leverage increased before evidence was durable
  - loss repaired with same tactic after regime changed
```

Candidate rule:

```yaml
status: candidate_pending_user_review
rule: After a strong profit streak, do not increase leverage or short-term size until profits are decomposed into skill, beta, and luck.
required_review:
  - how much profit came from one large winner
  - how much came from market trend
  - how much came from repeatable process
  - whether the tactic works in down-market conditions
  - whether recent wins created permission to ignore checklists
```

### Tactic Retention Decision

User does not want to discard the tactic completely.

Current stance:

```yaml
tactic_name: RS pullback balance-point rebound tactic
status: retain_as_restricted_candidate
not_status: active_unrestricted_tactic
requires_backtest: yes
requires_market_regime_filter: yes
requires_size_limit: yes
requires_post_loss_cooldown: yes
```

Tactic description:

```text
During a pullback or selloff:
identify symbols with strong relative strength
|
wait for balance / stabilization point
|
enter for rebound
|
take partial profit near disagreement / resistance
|
let remaining position run only if structure remains valid
```

Allowed only when:

- Broad market is in a confirmed supportive or improving state.
- QQQ / SPY are not in broad high-volume risk-off.
- VIX level and direction are favorable or at least not deteriorating.
- Relevant sector ETF is not breaking down.
- The symbol shows real relative strength versus QQQ and sector.
- Entry, stop, partial-take-profit, and no-add rules are written before entry.
- Position size is small enough that failure cannot trigger repair trading.

Forbidden when:

- QQQ / SOXX / SMH are in broad high-volume selloff.
- VIX is rising sharply.
- The tactic is being used after a prior short-term stop-loss.
- The purpose is to recover earlier losses.
- Leveraged products are used without a separate leveraged-product plan.
- The user cannot define max dollar loss before entry.

Backtest / evidence questions:

```yaml
questions:
  - What is the tactic win rate in QQQ uptrend days?
  - What is the tactic win rate in QQQ downtrend / high-volume selloff days?
  - How does VIX rising vs falling affect expectancy?
  - Does partial profit-taking improve expectancy or only reduce stress?
  - What happens after first failed attempt if re-entry is allowed?
  - Does the tactic still work after adding leveraged products?
  - What is max adverse excursion before successful rebound?
  - What stop size preserves positive expectancy?
```

Candidate rule:

```yaml
status: candidate_pending_backtest_and_user_review
rule: RS pullback rebound tactic is allowed only as a restricted, market-regime-dependent tactic; it is disabled during broad risk-off or after any short-term stop-loss.
```

### Stock Team Experiment Boundary

User asked whether this tactic should be tested by `stock_team`.

Decision:

```yaml
stock_team_experiment_allowed: yes
allowed_mode:
  - historical_backtest
  - paper_simulation
  - read_only_data_analysis
forbidden_mode:
  - live_trade
  - auto_order
  - discretionary intraday experiment with real capital
reason:
  - current MUU risk remains unresolved
  - user is recovering from a major drawdown
  - tactic is not yet validated across market regimes
  - recent wins may contain beta / luck / one-large-winner effects
```

Experiment objective:

```yaml
tactic: RS pullback balance-point rebound tactic
goal: Determine whether the tactic has positive expectancy only under specific market regimes.
not_goal:
  - justify current MUU position
  - recover losses
  - prove the user was right
  - produce a same-day live trade
```

Required experiment splits:

```yaml
market_regime:
  - QQQ_uptrend_low_vix
  - QQQ_flat_low_vix
  - QQQ_downtrend_vix_rising
  - high_volume_risk_off
sector_state:
  - sector_outperforming_QQQ
  - sector_inline
  - sector_underperforming_QQQ
instrument_type:
  - underlying_stock
  - leveraged_product
entry_type:
  - first_attempt_only
  - re_entry_after_partial_profit
  - re_entry_after_stop_loss
```

Minimum output required from `stock_team`:

```yaml
win_rate:
average_win:
average_loss:
profit_factor:
max_drawdown:
max_adverse_excursion:
expectancy_by_regime:
effect_of_VIX_direction:
effect_of_QQQ_direction:
effect_of_re_entry:
leveraged_vs_underlying_comparison:
recommended_disable_conditions:
```

Decision rule after experiment:

- If the tactic only works in supportive regimes, it becomes a restricted tactic.
- If re-entry after stop-loss destroys expectancy, it must be hard-disabled.
- If leveraged products make drawdown unacceptable, leverage must be disabled or capped.
- If results are inconclusive, the tactic remains research-only.

### Post-Loss Permission Management

This event suggests that the system needs trading permissions, not only trade checklists.

Candidate permission states:

| State | Trigger | Allowed | Blocked |
|---|---|---|---|
| Normal | No active emotional or risk breach | Planned trades, research, reviews | Planless trades |
| Yellow | Small short-term loss or attention capture | Existing plan execution, risk reduction | New hand-feel trades |
| Orange | Any short-term stop-loss, leveraged loss, or repeated checking | Risk reduction, pre-planned swing actions only | New short-term trades, re-entry attempts |
| Red | Major drawdown, principal affected, emotional breakdown, or unresolved high-risk position | Reduce unmanaged risk, journal, research | All new risk-taking |
| Recovery | After Red, before user-approved reset | Research, review, planned position repair | Leverage, revenge trades, new tactics |

Current event state:

```yaml
permission_state: red
reason:
  - major_drawdown
  - principal_affected
  - emotional_breakdown
  - unresolved_MUU_high_risk_position
allowed:
  - assess_current_open_risk
  - reduce_or_define_unmanaged_risk
  - journal_and_review
  - research
blocked:
  - new_short_term_trades
  - new_leveraged_product_trades
  - re_entry_to_recover_loss
  - live_experiment_of_RS_rebound_tactic
reset_requires:
  - MUU risk plan
  - sleep / emotional stabilization
  - written next-session plan
  - user review
```

Candidate rule:

```yaml
status: candidate_pending_user_review
rule: Major drawdown automatically moves the system into Red permission state until open risk, emotions, and next-session plan are reviewed.
```

Important:

- Red state is not punishment.
- Red state exists because the user has already identified that emotional state can rewrite rational decisions.
- The purpose is to protect future cognition and capital from the recovery impulse.

## Phase 5: Emotional Breakdown

This section should be written carefully and without self-attack.

Questions:

1. When did anxiety become panic?
2. When did the trade start affecting identity / self-worth?
3. When did the goal shift from making a good decision to escaping pain?
4. Did shame, anger, regret, or revenge appear?
5. Did the loss affect sleep, body state, or ability to think?
6. Did any action happen mainly to make the feeling stop?

User interview notes:

1. After `00:32` MULL realized loss of about `-$1,581`:
   - User felt some relief.
   - User also felt unwilling to accept the loss.
   - User continued watching the market.
   - Interpretation candidate: the position was closed, but the psychological trade was not closed.

2. At `00:55` MULL re-entry:
   - User believed there was a clear rebound signal.
   - User also wanted to make back the loss.
   - Interpretation candidate: signal reading and loss repair became mixed.

3. Loss of control point:
   - User believes the system was already fully out of control from the second MULL add.
   - This is earlier than the final `MUU` open position.
   - Interpretation candidate: the visible final position is the result of the breakdown, not the beginning of it.

4. Current feeling toward open `MUU`:
   - User still believes the high-level AI mainline and memory-cycle thesis may remain valid.
   - User is afraid of a stampede / forced selling dynamic.
   - User is afraid of geopolitical and external-event shocks.
   - User is afraid that even if the thesis recovers, repair may take too long and lock capital.
   - Emotional state includes fear, unwillingness, thesis attachment, and concern about opportunity cost.

5. Current review capacity:
   - User explicitly stated that even the review itself is still affected by emotion.
   - This means the system should avoid forcing a final decision frame too early.
   - Current priority is to separate thesis, instrument, size, and emotional burden.

6. Current classification of `MUU`:
   - User agrees it is a trapped position left after loss-repair behavior.
   - User agrees it has clearly hijacked emotion and decision-making.
   - User does not yet know how to evaluate leveraged-instrument path risk.

7. Current falsification uncertainty:
   - User is not sure what it means for the idea to be wrong.
   - User initially frames falsification around the memory thesis:
     - if the broader market stabilizes
     - and MU still breaks key levels or fails to repair
     - then the memory thesis / relative strength thesis becomes more questionable.
   - User notes that broad market collapse alone may not prove the memory thesis wrong.
   - User's prior reason for attention to MU was strong relative strength and evidence of demand / support.

Emotional sequence candidate:

```text
relief after realizing loss
|
unwillingness to accept finality
|
continued watching
|
rebound signal interpreted through repair desire
|
second add / re-risking
|
loss of control
|
open MUU becomes both thesis object and emotional burden
```

Key distinction:

- Believing in the long-term AI / memory thesis is not the same as having a valid plan for a leveraged short-term instrument.
- A macro thesis can be directionally right while the instrument, size, timing, and holding period are wrong.
- The current open `MUU` risk is emotionally hard because it combines thesis attachment with realized-loss repair pressure.
- The open question is not only "is the memory thesis wrong?"
- The immediate question is "can this instrument and size survive the path required for the thesis to work?"

## Phase 6: System Failure Analysis

Possible failure categories:

- position size too large
- leverage / instrument risk
- unclear role
- no maximum daily loss
- no per-trade loss cap
- no stop-trading rule
- averaging down
- hope override
- attention capture
- sleep risk
- revenge / repair trading
- ignoring market context
- ignoring peer weakness
- portfolio concentration
- no forced cooldown
- no principal protection rule

To fill:

```yaml
primary_failure: candidate_uncontained_leveraged_repair_loop
secondary_failures:
  - market_context_not_used_as_hard_gate
  - oversized_non_core_instrument_exposure
  - re_entry_after_major_realized_loss
  - unresolved_open_risk_after_breakdown
  - emotional_spillover_to_existing_positions
system_rule_missing:
  - maximum_daily_loss_stop
  - leveraged_product_max_notional
  - post_loss_re_entry_cooldown
  - mandatory_market_context_gate_before_review
system_rule_ignored:
  - risk_control_before_return
  - no_plan_no_trade
  - signal_is_not_command
data_needed:
  - account_net_liquidation_before_and_after
  - intraday_low_account_value
  - margin_usage
  - current_open_positions
  - user's emotional timeline
```

Candidate failure chain:

```text
broad risk-off session
|
semiconductor / memory sector sells off harder than QQQ
|
leveraged memory tools amplify downside
|
first large loss realized
|
re-entry / repair attempt
|
second large loss realized
|
unrelated positions sold during stress
|
new larger open MUU risk remains unresolved
```

This is still a candidate analysis.

It must be reviewed with the user's narrative before becoming a case, checklist update, or principle candidate.

User-proposed rule candidate:

```yaml
status: candidate_pending_user_review
rule: After any short-term trade failure and stop-loss, enter no-new-short-term-trade mode for the rest of the session.
reason:
  - short-term loss distorts hand-feel
  - repair desire rises immediately after stop-loss
  - the next trade is likely to be contaminated by the previous loss
  - the system should protect cognition before protecting the chance to catch the next setup
exceptions:
  - pre-market planned swing action reaches predefined level
  - risk reduction of existing position
  - closing or reducing unmanaged risk
not_allowed_as_exception:
  - revenge trade
  - same tactic re-entry to make back loss
  - larger size because the rebound looks stronger
```

Potential enforcement:

```yaml
trigger:
  - any short_term_trade stopped_out
  - any leveraged_product_trade stopped_out
  - any planless short_term_trade loss
effect:
  - block new short-term trades for rest of session
  - allow only planned swing execution or risk reduction
  - require journal note before next active trade
```

## Phase 7: Principal Protection Review

Because principal was affected, this review must create a candidate principal-protection protocol.

Candidate questions:

1. What loss level should trigger stop-trading for the day?
2. What drawdown should force risk reduction?
3. What maximum single-symbol exposure is allowed for non-core positions?
4. What maximum exposure is allowed in leveraged instruments?
5. What rule protects sleep and next-day cognition?
6. What must happen before trading resumes after a major drawdown?

No rule is adopted until user review.

User reflection on principal damage:

- User felt significant pain from the drawdown.
- User also recognizes a possible learning value:
  - after the previous failure, there was still some luck / survivorship feeling because recent profits remained
  - the prior mistake felt like giving back part of profits, not a true system-level warning
  - this event affected principal and therefore made the weakness more concrete
- User hopes this pain helps reveal lack of discipline more clearly and supports future correction.

System interpretation:

- Prior smaller failures did not fully break the illusion of recoverability.
- This event created a stronger emotional memory because it crossed from profit giveback into principal damage.
- The system should use this pain as evidence for guardrails, not as a source of shame.

Candidate principal-protection upgrade:

```yaml
status: candidate_pending_user_review
principle: A strategy that can affect principal must have written risk limits before execution.
applies_to:
  - short-term leveraged products
  - high beta single-stock tools
  - any trade whose notional exceeds 20% of account
  - any trade after a short-term stop-loss
required_before_trade:
  - max dollar loss
  - max position notional
  - no-add condition
  - market-context veto
  - stop-trading trigger
```

## Phase 8: Recovery Protocol

Immediate recovery candidate:

```yaml
trading_status_next_session: restricted_due_to_confirmed_open_high_risk_position
allowed_actions:
  - assess_current_open_risk
  - reduce_or_define_unmanaged_risk_only_after_human_decision
  - journal facts
  - review existing positions
  - research only
forbidden_actions:
  - revenge trade
  - size up to recover
  - trade without written plan
  - trade leveraged products without explicit approval
  - open new unrelated positions before MUU risk is reviewed
```

Open question:

- Should the next trading session be research-only unless a written recovery plan is approved?

Additional recovery constraint:

- Because `MUU` remains open and has an unrealized loss around `$2,000+`, the system should treat all new trading ideas as blocked until open risk is reviewed.
- The review may discuss possible actions, but final action remains the user's decision.

## Evidence Needed

Please provide any available:

- account P/L screenshot
- trade fills
- open positions
- symbols involved
- realized/unrealized P/L
- margin/leverage status
- market context notes
- your narrative of what happened

## Preliminary Answers From Screenshots

These are screenshot-level answers only.

1. Open high-risk position:
   - Likely yes.
   - The latest visible action is `MUU buy 30 @ 731.73`, not followed by a visible sell.
   - If still open, it is the highest-priority unmanaged risk item.

2. Realized damage:
   - Visible local `June 06, 2026` realized P/L is `-$2,666.55`.
   - The 7-day realized P/L header still shows `+$506.19`, but this does not measure intraday drawdown or principal stress.
   - Maximum account drawdown is still unknown because net liquidation / unrealized P/L is not visible.

3. Main loss source:
   - Main visible realized loss source is `MULL`, about `-$2,048.86` net visible realized P/L.
   - Other visible losses: `VRT -296.55`, `PLTR -88.73`, `COHR -76.54`, `COHX -33.84`.

4. Leverage / instrument risk:
   - The screenshots show repeated trading in instruments that appear to be leveraged / single-stock trading tools: `MULL`, `MUU`, `LITX`, `COHX`.
   - No options trades are visible.
   - Margin use is unknown from screenshots.

## Current Review State

```yaml
review_started: true
facts_complete: false
emotional_review_complete: false
system_update_allowed: candidate_only
trade_permission: no
```

## Closing Summary

This review is ready to pause after initial intake, market context, emotional reconstruction, and system diagnosis.

The event chain:

```text
recent profits and COHR large winner
|
short-term tactic gets several early wins
|
confidence rises faster than evidence quality
|
leverage chosen because feedback is fast
|
market regime shifts into broad risk-off
|
tactic loses reliability
|
loss creates unwillingness and repair desire
|
same tactic reused after failure
|
adds increase
|
control breaks
|
principal is affected
|
MUU remains as trapped leveraged position
```

One-sentence lesson candidate:

```text
Do not let profits earned in a supportive regime authorize leveraged short-term tactics in a hostile regime.
```

Alternative wording:

```text
When a short-term tactic fails, the next trade is usually not opportunity; it is often the previous loss asking to be repaired.
```

## Candidate System Updates

These are not adopted yet.

They require user review before promotion.

```yaml
candidates:
  - id: post_market_context_gate
    rule: Trading review must not begin from fills alone; market context packet is required before classification.
    destination_candidate:
      - system/workflows/post-market.md
      - system/checks/ai-trading-response-checklist.md
    status: already_added_as_process_gate

  - id: short_term_stop_no_trade
    rule: After any failed short-term trade and stop-loss, block new short-term trades for the rest of the session.
    destination_candidate:
      - system/checks/short-term-trade-checklist.md
      - execution/intraday.md
      - system/data/snapshots/risk-limits
    status: pending_user_review

  - id: major_drawdown_red_permission
    rule: Major drawdown moves the system into Red permission state until open risk, emotion, and next-session plan are reviewed.
    destination_candidate:
      - execution/intraday.md
      - execution/post-market.md
      - system/data/snapshots/risk-limits
    status: pending_user_review

  - id: profit_streak_decomposition
    rule: After a strong profit streak, decompose profit into skill, beta, luck, and one-large-winner before increasing size or leverage.
    destination_candidate:
      - cognition/biases.md
      - evolution/promotion-queue.md
      - templates/post-market-review.md
    status: pending_user_review

  - id: rs_rebound_tactic_restricted
    rule: RS pullback rebound tactic may be retained only as a restricted, regime-dependent tactic pending backtest.
    destination_candidate:
      - decision/tactics/
      - system/checks/short-term-trade-checklist.md
      - stock_team experiment task
    status: pending_backtest

  - id: leveraged_product_thesis_split
    rule: Separate thesis validity, underlying strength, and leveraged instrument suitability.
    destination_candidate:
      - system/checks/risk-checklist.md
      - templates/trade-plan.md
      - wiki/principles
    status: pending_user_review
```

## Open Tasks

```yaml
before_next_premarket:
  - build MUU premarket context:
      - QQQ
      - SPY
      - SOXX
      - SMH
      - MU
      - MUU
      - VIX
  - fill MUU rational-state handling plan
  - choose branch:
      - hold_with_limits
      - rebound_reduce
      - reduce_now
      - exit
      - convert_to_MU
      - structured_wait_with_failure_condition
  - confirm no-add rule
  - confirm max additional loss boundary

stock_team:
  - run read-only / historical experiment for RS pullback rebound tactic
  - split by QQQ regime, VIX direction, sector state, instrument type, and re-entry behavior
  - produce expectancy, drawdown, MAE, and disable-condition summary

investing_os:
  - decide which candidate rules enter promotion queue
  - create or update permission-state model
  - create restricted tactic page after stock_team evidence
  - update short-term checklist after user review
```

## Recovery Plan

Next 24-72 hours:

```yaml
trading_permission: red
allowed:
  - review
  - research
  - risk containment
  - premarket plan
  - stock_team historical experiment
blocked:
  - new short-term trades
  - new leveraged product trades
  - revenge trades
  - live experiments
  - adding to MUU
reset_conditions:
  - MUU plan written
  - next-session plan written before market
  - user confirms emotional stability
  - no open unmanaged high-risk position
```

Personal recovery note:

```text
The goal after a major drawdown is not to earn it back quickly.
The goal is to restore decision quality.
```

## Review Pause State

```yaml
review_pause_state: pre_premarket_decision_pending
MUU_status: open_trapped_position
system_permission_state: red
next_required_action: premarket_MUU_decision_packet
permanent_principle_updates: none_yet
candidate_updates_recorded: yes
```

## Absorption Status

This review is not complete until lessons are routed into the operating system.

Current absorption status:

```yaml
review_event_recorded: yes
market_context_gate_added: yes
promotion_queue_updated: yes
cognition_patterns_updated: yes
emotional_patterns_updated: yes
bias_map_updated: yes
strengths_weaknesses_updated: yes
system_update_log_updated: pending
checklist_updates:
  market_context_gate: applied
  short_term_stop_no_trade: adopted
  red_permission_state: adopted
  profit_streak_decomposition: adopted
  leveraged_product_thesis_split: adopted
  rs_rebound_tactic: pending_backtest
permanent_principle_updates: none_yet
```

Absorption map:

| Lesson | Current Location | Status | Next Decision |
|---|---|---|---|
| Review must not start from fills alone | `system/workflows/post-market.md`, `templates/post-market-review.md`, `system/checks/ai-trading-response-checklist.md` | applied as process gate | keep |
| Profit streak overconfidence | `evolution/promotion-queue.md`, `cognition/mistake-patterns.md`, `cognition/emotional-patterns.md`, `cognition/bias-map.md`, `system/checks/short-term-trade-checklist.md`, `templates/trade-plan.md` | adopted | review after next profit streak |
| Short-term stop-loss no-trade | `evolution/promotion-queue.md`, `execution/intraday.md`, `system/checks/short-term-trade-checklist.md` | adopted | review after next short-term stop-loss event |
| Major drawdown Red permission | `evolution/promotion-queue.md`, `execution/intraday.md` | adopted | define thresholds after current recovery |
| Thesis / underlying / leveraged instrument split | `evolution/promotion-queue.md`, `cognition/bias-map.md`, `templates/risk-checklist.md`, `templates/trade-plan.md` | adopted | review after next leveraged/instrument decision |
| RS pullback rebound tactic | review candidate section, stock_team experiment boundary | pending backtest | test before adoption |

Definition of done for this review:

```yaml
done_when:
  - MUU premarket decision packet completed
  - adopted items are tested in real review flow
  - stock_team experiment either completed or scheduled
```
