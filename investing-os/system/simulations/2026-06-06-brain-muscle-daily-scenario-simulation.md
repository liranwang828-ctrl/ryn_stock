# Brain-Muscle Daily Scenario Simulation

Date: 2026-06-06

Purpose:

Simulate normal daily usage scenarios to define practical input/output formats and discover current `stock_team` boundary or implementation issues.

## Boundary Rule

Every scenario must follow:

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

## Scenarios

| Scenario | Brain Input | Muscle Output | Status | Findings |
|---|---|---|---|---|
| Pre-market | pre-market decision sheet | plan evidence packet | in_progress |  |
| Intraday | intraday guidance request | runtime monitor packet | pending |  |
| Company research | company research request | company research packet | pending |  |
| Industry research | industry research request | industry research packet | pending |  |
| Trade review | trade review request | contextual trade evidence packet | pending |  |
| Post-market | post-market request | post-market packet | pending |  |
| Backtest | tactic backtest request | backtest evidence report | pending |  |

## Issues Found

| ID | Area | Severity | Finding | Owner | Status |
|---|---|---|---|---|---|
| SIM-001 | data source | medium | Earlier sandbox used yfinance for structure validation. Production packet must use Polygon / IBKR first or disclose fallback. | Antigravity | open |
| SIM-002 | language boundary | medium | Premarket CLI output contains action-like wording such as "should be applied" and "Restrict trade actions". Should be changed to neutral collision fields. | Antigravity | open |

## Pre-Market Simulation

### Stage 0: Market Context

Brain input:

- universe: `system/simulations/inputs/pre-market-decision-sheet.MU-NVDA-COHR-INTC.demo.json`
- themes: `semiconductors,ai_infrastructure,memory,cloud,optical`

Muscle command:

```powershell
python -m stock_team.cli market-context --date 2026-06-06 --themes semiconductors,ai_infrastructure,memory,cloud,optical --universe C:\Users\rriww\Documents\investing-os\system\simulations\inputs\pre-market-decision-sheet.MU-NVDA-COHR-INTC.demo.json --out D:\gemini\lianghua\stock_team\scratch\simulation_outputs\stage0_environment_MU-NVDA-COHR-INTC_2026-06-06.md
```

Brain interpretation simulation:

- Stage 0 is risk-off / unstable.
- Focus pool is narrowed to `MU` and `NVDA`.
- `MU` is for memory-theme evidence and loss-repair guard review.
- `NVDA` is for AI leadership / core context observation.
- Focus does not mean trade permission.

### Stage 1: Symbol Plan Evidence Request

Brain output to muscle:

- `system/simulations/inputs/stage1-pre-market-decision-sheet.MU-NVDA.demo.json`

Simulated muscle output back to brain:

- `system/simulations/outputs/stage1-plan-evidence-packet.MU-NVDA.demo.md`

Simulated brain intraday guidance to muscle:

- `system/simulations/inputs/intraday-guidance.NVDA-conditional.demo.json`
- Covers `NVDA` conditional short-term entry, `MU` conditional mid-term swing entry, `COHR` observe-only swing context, and `INTC` reduce-risk-only review.

Purpose:

- ask `stock_team` to calculate symbol-level facts and rule collisions
- preserve brain-owned role, permission state, risk budget, and forbidden actions
- prevent muscle from inventing entry, sizing, thesis adoption, or trade permission

Expected future muscle command shape:

```powershell
python -m stock_team.cli premarket --date 2026-06-06 --decision-sheet C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.MU-NVDA.demo.json --out D:\gemini\lianghua\stock_team\scratch\simulation_outputs\premarket_MU-NVDA_2026-06-06.md
```

The `--watchlist` argument should eventually become unnecessary when the decision sheet already contains the symbol list.

### Legacy COHR Sandbox

Brain input:

- `system/simulations/inputs/pre-market-decision-sheet.COHR.demo.json`

Muscle command:

```powershell
python -m stock_team.cli premarket --date 2026-06-06 --watchlist D:\gemini\lianghua\stock_team\watchlist_test.json --decision-sheet C:\Users\rriww\Documents\investing-os\system\simulations\inputs\pre-market-decision-sheet.COHR.demo.json --out D:\gemini\lianghua\stock_team\scratch\simulation_outputs\premarket_COHR_2026-06-06.md
```

Expected checks:

- packet references brain input artifact
- brain decision echo is present
- muscle candidate factors are present
- rule collision result is present
- no buy / sell / hold recommendation
- no permission state
- no psychological interpretation
- no invented entry / support / sizing outside decision sheet or formula contract
