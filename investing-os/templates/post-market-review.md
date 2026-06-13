# Post-Market Review Template

## Date

## Review Status

```yaml
market_context_packet: missing/complete/partial
fills_collected: yes/no
user_narrative_collected: yes/no
analysis_allowed: no/limited/full
```

If `market_context_packet` is `missing`, stop here and collect market data first.

## External Market Context

Required before interpreting mistakes:

- traded-symbol intraday K-line
- traded-symbol recent daily K-line
- traded-symbol volume and volume ratio
- SPY / QQQ intraday and daily behavior
- VIX level and direction, or documented unavailable reason
- relevant sector ETF behavior
- relevant peers / underlying symbols
- market state at key trade timestamps

Evidence location:

- `system/data/market-context/{date}-{review-id}/`

## What Happened

## What I Did

## What I Felt

## What Was Planned

## What Deviated

## Was The Thesis Changed?

## Mistakes

## Lessons

## Wiki Updates Needed

## Tomorrow's Focus
