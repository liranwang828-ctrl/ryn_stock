# Brain-Muscle Handshake Protocol

Purpose:

Define one boundary protocol for every collaboration between `investing-os` and `stock_team`.

This avoids re-litigating the boundary for pre-market, intraday, research, review, and backtest workflows.

## Core Rule

```text
investing-os owns meaning, permission, thesis, role, and absorption.
stock_team owns facts, calculations, backtests, data quality, and packet production.
```

## Universal Flow

```text
Brain Request
|
Muscle Evidence
|
Brain Interpretation
|
User Confirmation
|
System Absorption
```

## Universal Boundary

`stock_team` may output:

- facts
- normalized data
- calculated indicators
- candidate factors
- rule collision results based on brain-provided rules
- backtest evidence
- missing data
- stale data
- source list

`stock_team` must not output:

- buy / sell / hold recommendation
- trading permission state
- final thesis adoption
- psychological interpretation
- action readiness such as "can trade" or "should enter"
- invented entry / support / sizing values not provided by the brain or formula contract
- live execution instruction

## Data Source Priority

Production evidence should prefer paid / broker-grade sources.

Priority:

1. Polygon for market prices, intraday bars, volume, VWAP, news, and historical aggregates when available.
2. IBKR for positions, orders, fills, account exposure, and broker-side execution records.
3. Local cache when it records the source, timestamp, and freshness.
4. yfinance only as fallback or sandbox convenience, never as the default production evidence source.

Every packet must disclose:

```yaml
data_sources:
  primary:
  fallback:
  cache_used:
  stale:
```

If fallback data is used, `missing_data` or `warnings` must explain why the preferred source was unavailable.

## Scenario Matrix

| Scenario | Brain Owns | Muscle Owns | Brain Input Artifact | Muscle Output Packet | Absorption Target |
|---|---|---|---|---|---|
| Pre-market stage 0 | question framing, permission state before open, whether new risk is even allowed, universe definition from positions / watchlist / researched names | broad market state, QQQ/SPY/VIX, futures, sector heat, catalyst facts, data freshness, environment-to-universe mapping | market context request + brain universe | pre-market context packet | focus pool discussion |
| Pre-market stage 1 | role, thesis, key level meaning, allowed tactics, forbidden actions, risk budget | symbol gap, ATR, RS, QQQ/SPY/VIX, rule collision | pre-market decision sheet | plan evidence packet | trading day plan + intraday guidance |
| Intraday | permission state, allowed / forbidden action categories, plan alignment | runtime price, VWAP, volume, QQQ/VIX, IBKR snapshot, stale data | intraday guidance request | runtime monitor packet | intraday guidance sheet |
| Company research | research question, thesis candidate criteria, decision use | financial facts, peer metrics, price RS, valuation facts | company research request | company research packet | company dossier + thesis candidate |
| Industry research | worldview question, industry map scope, bottleneck question | market size facts, supply chain facts, company list, historical metrics | industry research request | industry research packet | industry dossier + wiki |
| Trade review | original plan, emotional questions, rules to audit | fills, OHLCV, VWAP, QQQ/VIX, peer context, realized P/L | trade review request | contextual trade evidence packet | review report + lessons |
| Post-market | review frame, discipline checks, lesson promotion decision | closing data, daily P/L facts, packet summary, market context | post-market request | post-market packet | daily report + promotion queue |
| Backtest | tactic definition, allowed variables, disable conditions to test | historical data, metrics, splits, sensitivity, failure modes | backtest request | backtest evidence report | tactic review + factor evidence |

## Factor Boundary

There are three levels of trading factors.

### Candidate Factors

Computed by `stock_team`.

Examples:

- ATR
- VWAP
- gap percentage
- relative strength
- VIX direction
- volume confirmation
- prior high / low
- moving averages
- volume nodes

These are not trading instructions.

### Decision Rules

Defined by `investing-os`.

Examples:

- high-volume risk-off disables RS rebound tactic
- Red state blocks new short-term risk
- leveraged trapped position allows only risk review and pre-planned de-risk
- gap above configured threshold reduces allowed size by brain-defined factor

### Formula Overrides

Defined by `investing-os` when the brain wants fine control without writing a direct price.

Allowed:

```yaml
formula_overrides:
  tactic: rs_pullback_rebound
  entry_anchor: MA50
  stop_atr_multiplier: 1.0
  reason: tighter setup required after volatility expansion
```

Meaning:

- the brain may choose which approved formula variant to use
- the brain may adjust formula parameters when it can explain why
- the muscle calculates the physical price and share count from market data
- the muscle must echo the override and calculation, not treat it as a recommendation

Forbidden:

```yaml
formula_overrides:
  exact_entry_price: 333.53
  recommended_shares: 15
```

### Approved Plan Factors

Created during pre-market after user confirmation.

Examples:

- COHR 400 is observe support
- COHR 392 is invalidation review
- MUU is reduce-risk review only
- RS rebound tactic disabled today

Only approved plan factors may appear in intraday guidance as action boundaries.

## Pre-Market Two-Stage Flow

Pre-market should not jump directly into a symbol-level decision sheet.

Correct order:

```text
Stage 0: Market Context
|
stock_team returns broad market facts only
|
investing-os discusses permission and focus pool with user
|
Stage 1: Decision Sheet
|
stock_team returns symbol-level plan evidence packet
|
investing-os generates trading day plan and intraday guidance
```

Stage 0 muscle output should answer:

- QQQ / SPY / IWM direction
- VIX level and direction
- futures / pre-market index state if available
- sector heat, especially semiconductors / AI / cloud / storage when relevant
- yesterday / recent market behavior
- environment relevance to brain-provided positions, watchlist, and researched candidates
- major news / macro event calendar if available
- data freshness and missing data

Official Stage 0 output path:

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md
```

`stock_team` may keep an internal copy for diagnostics, but the brain reads this path as the canonical Stage 0 packet.

Stage 0 universe rule:

- The muscle must not scan the whole market for opportunities.
- The brain must provide a universe built from current positions, active watchlist, and researched or explicitly approved candidates.
- Symbols outside that universe are allowed only as market / sector / peer proxies.
- Each universe item should include `symbol`, `role`, `theme`, and `research_status`.

Stage 0 must not answer:

- which symbol to buy
- whether trading is allowed
- what position size to use

Stage 1 happens only after the brain and user choose the focus pool.

Stage 1 should derive market context from the canonical Stage 0 packet path unless the brain explicitly provides another path for a simulation:

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md
```

Stage 1 must include these fields before any intraday conditional action is possible:

- `pre_authorized_actions`
- `fast_consistency_check`
- `exception_rules`
- `risk_budget`
- `forbidden_actions`

If these fields are missing, the intraday mode defaults to `observe_only` or `reduce_risk_only`.

## Sandbox Finding

On 2026-06-06, a read-only COHR sandbox compared:

- default tactic parameters: `entry_anchor=MA20`, `stop_atr_multiplier=1.5`
- brain override parameters: `entry_anchor=MA50`, `stop_atr_multiplier=1.0`

Finding:

- passing only `allowed_tactics` is clean but may be too coarse
- allowing `formula_overrides` preserves brain precision without letting the muscle invent entry / support / sizing
- official schemas should keep `formula_overrides` as an optional brain-owned field
- the sandbox used `yfinance` only for quick structure validation; production packets should use Polygon / IBKR first and disclose any fallback source

## Rule Collision

`stock_team` may calculate rule collision results only when the rule comes from a brain-owned artifact.

Allowed:

```yaml
brain_rule:
  if_gap_above: 2.0
  size_multiplier: 0.5
muscle_fact:
  premarket_gap: 3.4
collision_result:
  triggered: true
  computed_multiplier: 0.5
```

Forbidden:

```yaml
recommended_size: 0.5
recommended_entry: 400
should_buy: true
```

## Required Packet Fields

Every muscle packet should include:

```yaml
packet_type:
generated_at:
command:
brain_input_artifact:
inputs:
data_sources:
missing_data:
warnings:
facts:
candidate_factors:
rule_collision_results:
forbidden_sections_absent:
  - buy_sell_hold_recommendation
  - trading_permission_state
  - final_thesis_adoption
  - psychological_interpretation
  - invented_entry_support_sizing
```

## Brain Interpretation

After receiving a packet, `investing-os` must decide:

- whether evidence is sufficient
- whether the plan remains aligned
- whether permission state tightens
- whether a report should be generated
- whether any lesson should enter promotion queue
- whether dashboard indexes should refresh

## Verification

For every new workflow integration:

- confirm brain input artifact exists
- confirm muscle packet references the input artifact
- confirm missing data is explicit
- confirm forbidden sections are absent
- confirm output is absorbed by an investing-os workflow
- confirm no stock_team dashboard or CLI becomes a competing user entrypoint
