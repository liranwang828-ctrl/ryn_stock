# PRIN-005: VWAP And Volume Confirmation Rules

## Metadata

- ID: PRIN-005
- Title: VWAP And Volume Confirmation Rules
- Version: 1.0
- Status: active
- Created: 2026-06-05
- Updated: 2026-06-05
- Source: `wiki/inbox/principles/vwap_volume_confirmation_zh.md`

## Core Assertion

VWAP is a useful intraday structure reference, but it must not be used alone.

Volume and context decide whether VWAP matters.

## Why It Exists

VWAP often reflects institutional cost and intraday structure, but treating it as a standalone signal creates false precision.

This principle keeps VWAP as context, not command.

## Trigger Conditions

Apply this principle when using VWAP or volume to evaluate:

- intraday entries
- pullbacks
- reclaim setups
- trend continuation
- exit warnings
- leveraged product trades

## Execution Constraints

VWAP is most useful when:

- price reclaims VWAP after losing it
- price pulls back to VWAP and holds
- a second VWAP breakout supports trend following
- volume contracts near VWAP support

VWAP is weaker when:

- price stays far above VWAP after open
- price stays below VWAP after open
- a strong catalyst creates vertical movement
- the product is leveraged or illiquid
- opening a new position late in the session

Volume confirmation principles:

- breakouts should expand volume
- pullbacks should contract volume
- second breakouts should show renewed volume

For leveraged products, check the underlying asset's VWAP first.

## What This Principle Forbids

- Treating VWAP alone as a buy or sell command
- Going long below VWAP without reclaim and volume confirmation
- Ignoring catalyst context
- Using leveraged product VWAP while ignoring the underlying asset
- Opening late-session trades only because of VWAP proximity

## Falsification Or Revision Conditions

Revise VWAP and volume parameters only after reviewing enough trades by setup type.

Do not treat one successful VWAP bounce as universal evidence.

## Drift Audit

- Was VWAP used as context or command?
- Was volume confirming or contradicting?
- Was the setup a reclaim, hold, breakout, or late chase?
- Was the product leveraged or illiquid?
- Did the user ignore broader market or sector structure?

## Related Cases

- `wiki/historical-cases/CASE-002-crdu-fomo-pullback.md`
- `wiki/historical-cases/CASE-003-pltr-trend-switch-exit.md`

## Related Workflows

- `templates/signal-review.md`
- `templates/trade-plan.md`
- `system/workflows/signal-processing.md`

## Runtime Parameters

Candidate parameters from source material:

- daily relative volume activity threshold
- breakout volume multiple
- strong confirmation volume multiple
- pullback volume contraction range
- VWAP break warning condition

These are tactical parameters. They should be exported through runtime snapshots after validation and should not be treated as timeless principles.
