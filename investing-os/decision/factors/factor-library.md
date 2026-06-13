# Factor Library

Purpose:

Maintain a shared vocabulary of measurable factors used by pre-market planning, intraday monitoring, backtesting, and post-market review.

Core rule:

```text
Factors are facts.
Tactics interpret factor combinations.
The brain activates tactics.
The muscle calculates factors.
```

## Factor Status

| Status | Meaning | Trading Use |
|---|---|---|
| context | useful background only | Cannot drive pass/fail |
| candidate | plausible but not validated | Paper review only |
| validating | being backtested or paper-tested | Limited monitoring |
| active | validated enough for tactic conditions | May drive pass/fail |
| disabled | known unreliable or not currently usable | Do not use |

## Market Regime Factors

| Factor ID | Description | Pre-Market | Intraday | Backtest Split | Status |
|---|---|---:|---:|---:|---|
| qqq_trend_5d_20d | QQQ short/intermediate trend context | yes | no | yes | candidate |
| qqq_high_volume_risk_off | QQQ downside move with elevated volume | yes | yes | yes | validating |
| qqq_vwap_state | QQQ price relative to VWAP | no | yes | yes | candidate |
| qqq_opening_range_state | QQQ relative to opening range high/low | no | yes | yes | candidate |
| vix_direction | Volatility proxy direction | yes | yes | yes | validating |
| market_catalyst_risk | Macro/news/event risk context | yes | yes | yes | candidate |
| qqq_cycle_regime | QQQ slow-cycle regime: bull_market / bear_market / transition_market | yes | no | yes | validating |

## Sector / Theme Factors

| Factor ID | Description | Pre-Market | Intraday | Backtest Split | Status |
|---|---|---:|---:|---:|---|
| sector_rs_vs_qqq | Sector/theme proxy relative strength vs QQQ | yes | yes | yes | validating |
| sector_vwap_state | Sector proxy price relative to VWAP | no | yes | yes | candidate |
| sector_high_volume_breakdown | Sector proxy high-volume downside break | yes | yes | yes | validating |
| peer_confirmation | Relevant peers confirm or diverge from symbol move | yes | yes | yes | candidate |
| stage1_universe_quality | Whether the candidate pool belongs to a historically stronger theme/universe instead of a diluted mixed list | yes | no | yes | validating |
| transition_market_filter | Avoid or downgrade action during transition_market unless a stronger catalyst packet exists | yes | yes | yes | validating |

## Symbol Factors

| Factor ID | Description | Pre-Market | Intraday | Backtest Split | Status |
|---|---|---:|---:|---:|---|
| symbol_rs_vs_market | Symbol relative strength vs QQQ/SPY | yes | yes | yes | validating |
| symbol_rs_vs_sector | Symbol relative strength vs sector proxy | yes | yes | yes | validating |
| symbol_vwap_reclaim | Symbol reclaims VWAP after pullback | no | yes | yes | candidate |
| symbol_opening_range_reclaim | Symbol reclaims opening range after pullback | no | yes | yes | candidate |
| volume_confirmation | Rebound volume is stronger than local baseline | no | yes | yes | candidate |
| atr_risk_distance | Distance to invalidation expressed in ATR or percent | yes | yes | yes | validating |
| ma20_distance | Price distance from MA20 | yes | yes | yes | candidate |
| ma50_distance | Price distance from MA50 | yes | yes | yes | candidate |
| prior_day_high_low | Prior day high/low reference | yes | yes | yes | candidate |
| leader_subset_membership | Symbol belongs to a train/test validated leader subset for current research cycle | yes | no | yes | validating |

## Current Validation Evidence

### stage1_universe_quality / leader_subset_membership

Source:

- `D:\gemini\lianghua\stock_team\findings\cycle_factor_search_findings_v1.md`
- `D:\gemini\lianghua\stock_team\findings\cycle_factor_search_growth_ai_semis_v1.md`

Evidence summary:

- Mixed candidate50 was weak versus QQQ in bull windows.
- Growth / AI / semis / software universe showed 10D alpha_vs_QQQ of `+0.787%` and OOS alpha of `+0.627%`.
- Train-selected leader subset excluding META outlier showed test-period 10D alpha_vs_QQQ of `+1.350%` and Sharpe proxy of `2.112`.

Initial leader subset under research:

```text
RKLB, NVDA, TSLA, LITE, NET, AVGO, PANW, MDB, DDOG, PLTR
```

Use:

- Stage 1 research prioritization.
- Candidate-pool quality scoring.
- Not an entry signal.
- Not a buy/sell/hold rule.

Known caveats:

- VIX historical cache was incomplete before 2024-05-29.
- META was excluded from the first leader subset because its training-period alpha looked outlier-like and requires audit.
- Current max drawdown evidence is an event-sequence metric, not a portfolio equity curve drawdown.

## Portfolio / Risk Factors

| Factor ID | Description | Pre-Market | Intraday | Backtest Split | Status |
|---|---|---:|---:|---:|---|
| permission_state | Brain-owned Green/Yellow/Red/No-Trade state | yes | yes | yes | active |
| daily_loss_state | Current day loss state and risk budget use | yes | yes | yes | candidate |
| linked_leveraged_exposure | Related leveraged product exposure exists | yes | yes | yes | validating |
| attention_budget_state | Time/attention spent on symbol or tactic | yes | yes | no | candidate |
| same_symbol_stopout_today | Same symbol/tactic already stopped out today | no | yes | yes | validating |

## Validation Rule

Any factor promoted from `candidate` to `active` needs:

- definition
- data source
- formula or calculation method
- missing-data behavior
- at least one validation record
- known failure modes
