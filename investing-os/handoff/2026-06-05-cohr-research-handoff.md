# COHR Research Handoff

Date: 2026-06-05

Owner so far: Codex + user  
Target repo: `C:\Users\rriww\Documents\investing-os`  
Related external repo: `D:\gemini\lianghua\stock_team`

## Current Status

COHR research has started using the full `investing-os` company research lifecycle.

Important correction:

- The first fast COHR dossier was too unilateral.
- User asked for Chinese review and direct participation.
- Current status is not final adoption.

Current COHR status:

```yaml
status: thesis_candidate_pending_user_review
role: swing
cohr_role_in_system: mainline_carrier_plus_resilient_swing
trade_permission: no
```

## Confirmed By User

1. COHR is a swing candidate, not a core holding.

Reason:

- optical module / optical networking has strong peer competition
- COHR moat is narrower than NVDA / GOOGL
- do not treat it as a default long-term compounder

2. COHR must not lag peers.

Peer basket:

- LITE
- AAOI
- SOXX

3. COHR role is:

```text
mainline carrier + relatively resilient swing exposure
```

It is not the highest-beta optical attack tool.

4. User wants an AI-overheated swing valuation framework.

Key phrase:

```text
估值不是买卖开关，估值是风险温度计
```

5. Candidate sizing:

```yaml
max_position_candidate: 30% of swing sleeve
portfolio_equivalent_if_swing_sleeve_60pct: about 18% total portfolio
status: pending_user_confirmation
```

## Files Created / Updated

Research:

- `wiki/companies/COHR.md`
- `wiki/companies/COHR.zh.md`
- `system/data/packets/drafts/company-research-COHR-2026-06-05.md`
- `wiki/sources/packet-review-COHR-2026-06-05.md`
- `wiki/sources/packet-review-COHR-2026-06-05.zh.md`

Valuation:

- `wiki/methodologies/ai-swing-valuation-temperature.zh.md`
- `wiki/companies/COHR-valuation-temperature.zh.md`

Current valuation candidate:

```yaml
valuation_temperature: orange
entry_permission: no_chase
preferred_entry: pullback_or_reclaim
starter_if_triggered: 10% to 15% of swing sleeve
full_size_limit: 30% of swing sleeve only after confirmation
trade_permission: no
```

Conditional plan:

- `decision/trade-plans/COHR-swing-plan-candidate-2026-06-05.zh.md`

Current plan status:

```yaml
status: plan_candidate_pending_user_review
trade_permission: no
current_decision: not_approved_for_trade
```

Temporary reclaim levels discussed:

```yaml
starter_zone: 423-425 hold
confirmation_zone: 432-433 reclaim
strong_confirmation: above 440
```

These levels require peer and market confirmation.

## Important Boundaries

- Do not mark COHR as trade-approved.
- Do not convert the plan into an active trade plan without user review.
- Do not treat `30% of swing sleeve` as initial position size.
- Do not use COHR as core holding by default.

## Next Steps For Codex

1. Review COHR conditional swing plan with the user in Chinese.
2. Confirm sizing interpretation.
3. Refine reclaim / pullback levels using fresh market data before any trading day.
4. Turn accepted parts into reviewed plan / watchlist metadata candidate / pre-market input only after user approval.

## Next Steps For ORCL

ORCL has only a fast draft.

Do not jump directly to trade plan.

Run:

```text
company research packet
|
packet review
|
user discussion
|
dossier absorption
|
valuation temperature
|
conditional swing plan candidate
```

## Antigravity Independence Boundary

Antigravity should not edit `investing-os`.

Antigravity may work independently inside `stock_team` on data evidence and exporter tasks:

- COHR/LITE/AAOI/SOXX peer evidence packet
- ORCL company research evidence packet
- command interface that Codex can call and log

Facts only. No thesis adoption. No trading recommendation.
