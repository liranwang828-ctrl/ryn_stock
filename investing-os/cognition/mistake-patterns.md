# Mistake Patterns

## Purpose

Track repeated mistake structures so the system can design against them.

## Current Patterns

### Planless Short-Term Entry

Trigger:

- strong intraday signal
- fear of missing a move
- VWAP or momentum breakout appears urgent

Failure:

- no thesis
- no invalidation
- no add rule
- signal becomes substitute for judgment

Countermeasure:

- short-term trade checklist
- signal-to-action checklist
- no-trade if thesis cannot be stated before entry

### Averaging Down Without Thesis Strengthening

Trigger:

- price moves against position
- loss feels reversible
- desire to lower cost basis

Failure:

- add decision comes from price pain, not thesis improvement
- opportunity trade turns into bailout trade

Countermeasure:

- prewritten add rule
- no add if thesis is missing
- pause after first unplanned add impulse

### Low Financial Risk, High Cognitive Risk

Trigger:

- position size looks small
- attention cost is ignored
- user believes the trade is not financially large enough to matter

Failure:

- small trade hijacks the day
- sleep and unrelated portfolio decisions become affected

Countermeasure:

- cognitive attention budget
- 30-minute continuous-monitoring pause
- fact / thesis / risk restart

## 2026-06-04 SNXX Pattern Extraction

Source:

- `wiki/journals/2026-06-04-daily-review.md`
- `wiki/journals/2026-06-04-snxx-fill-review.md`
- `wiki/historical-cases/CASE-004-snxx-attention-capture.md`

Pattern chain:

```text
VWAP breakout
|
FOMO entry
|
loss aversion
|
unplanned add
|
attention capture
|
sleep risk
|
possible emotional spillover
```

Core mistake:

The trade was not large enough to dominate the account, but it became large enough to dominate cognition.

System response:

- SNXX moved to `blocked_pending_review`
- short-term trades require thesis, trigger, risk, invalidation, add rule, and attention budget
- low-conviction trades cannot receive high-conviction attention

### Partial Recovery Re-Risking

Status:

- candidate pending user approval

Trigger:

- a losing or unstable trade gets a partial profitable exit
- emotional relief appears
- user re-enters or rebuilds exposure before thesis quality improves

Failure:

- partial recovery is mistaken for validation
- risk is re-added without a fresh plan
- the trade survives by changing identity

Countermeasure:

- partial profitable exit should reduce or end risk when original thesis was missing
- re-entry after partial exit requires a new written thesis, trigger, invalidation, add rule, and attention budget
- do not let relief become permission

### Implicit Thesis Without Execution Constraints

Status:

- candidate pending user approval

Trigger:

- user has a real theme view
- symbol appears to express that theme
- market and sector confirm in the moment

Failure:

- thesis remains implicit
- no invalidation, add rule, re-entry rule, or attention budget exists
- trade can mutate after price feedback

Countermeasure:

- convert theme thesis into execution constraints before entry
- if the thesis cannot be translated into falsification and sizing, trade remains research/watchlist only

### Seeing Weakness But Hoping For Reversal

Status:

- candidate pending user approval

Trigger:

- symbol starts weakening
- peer or related theme also weakens
- user still believes the original theme can reassert

Failure:

- adverse evidence is perceived but not obeyed
- hope replaces invalidation
- add behavior continues after the setup has degraded

Countermeasure:

- if weakness is noticed, write the stop condition immediately
- no add is allowed while the reason is "hope it reverses"
- ask: what evidence would make this trade stop now?

## 2026-06-05 Major Drawdown Pattern Extraction

Source:

- `wiki/journals/2026-06-05-major-drawdown-review.md`

Status:

- candidate pending user approval

Pattern chain:

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

Core mistake:

Profits earned in a supportive regime were treated as permission to use leveraged short-term tactics in a hostile regime.

Sub-patterns:

- recent-profit overconfidence
- failure to separate skill / beta / luck / one-large-winner
- short-term stop-loss followed by continued opportunity seeking
- repair desire disguised as rebound trading
- theme thesis used to support an unsuitable leveraged instrument
- market-regime change not used as a hard veto

Countermeasures:

- decompose profit streak before increasing leverage or short-term size
- after short-term stop-loss, enter no-new-short-term-trade mode
- treat major drawdown as Red permission state
- separate thesis validity, underlying strength, and instrument suitability
- require market-context packet before trade review conclusions
- backtest RS pullback rebound tactic before active use

## Update Rule

Every repeated mistake should eventually create one of:

- principle candidate
- checklist update
- historical case
- workflow change
