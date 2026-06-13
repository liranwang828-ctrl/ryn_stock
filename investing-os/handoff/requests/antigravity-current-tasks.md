# Antigravity Current Tasks

Date: 2026-06-07

Owner: Antigravity
Requested by: Codex / user
Target repo: `D:\gemini\lianghua\stock_team`
Mode: independent implementation inside `stock_team`; do not edit `investing-os`

## Operating Boundary

Read first:

- `C:\Users\rriww\Documents\investing-os\system\closed-loop-operating-architecture.md`
- `C:\Users\rriww\Documents\investing-os\system\workflows\brain-muscle-handshake-protocol.md`
- `C:\Users\rriww\Documents\investing-os\handoff\2026-06-07-system-overview-for-next-agent.md`
- `C:\Users\rriww\Documents\investing-os\handoff\2026-06-07-backtest-system-session-record.md`
- `C:\Users\rriww\Documents\investing-os\handoff\2026-06-08-INTC-MU-COHR-operating-pass.md`
- `C:\Users\rriww\Documents\investing-os\wiki\journals\2026-06-08-market-rebound-cognition-review.md`
- `D:\gemini\lianghua\stock_team\docs\ACTIVE_WORKSPACE.md`

All user-facing trading workflow starts from `investing-os`.

`stock_team` is the evidence engine. It may produce:

- factual evidence packets
- Polygon / IBKR / cache data
- calculations
- condition pass / fail
- data freshness and missing-data notes
- evidence dashboard and manifest

`stock_team` must not produce:

- buy / sell / hold recommendations
- trading permission approval
- final thesis adoption
- psychological interpretation
- principle updates
- live execution controls
- a competing user workflow that bypasses `investing-os`

## Data Source Priority

1. Polygon for prices, intraday bars, aggregates, volume, VWAP, and news.
2. IBKR for broker positions, orders, fills, account exposure, and realized / unrealized P&L.
3. Local cache only with source, generated timestamp, and freshness metadata.
4. yfinance only as fallback or sandbox convenience, never as the default production source.

Every packet must disclose source and freshness. If fallback data is used, explain why in `missing_data` or `warnings`.

## Current Execution Order

### Codex-Owned Backtest Contract - Completed Second Slice

Status:

- Codex has added a unified `tactic-backtest` entry in `stock_team`.
- Codex has added `fixture_events` and `intraday_ohlcv_fixture` data modes.
- `intraday_ohlcv_fixture` can generate candidate events from OHLCV bars using VWAP reclaim plus volume confirmation, then exits by stop / take-profit / end of day.
- Do not create a separate competing backtest CLI or dashboard workflow.
- Anti may later add Polygon production data loading behind this same contract, but should not change the request / output boundary without Codex review.

Canonical stock_team command shape:

```powershell
python -m stock_team.cli tactic-backtest --request "<brain request json>" --out "<evidence packet md>" --json-out "<machine summary json>"
```

Reference files in `stock_team`:

- `backtest/tactic_backtest_system.py`
- `docs/tactic-backtest-contract.md`
- `config/tactic_backtest_request.example.json`
- `config/tactic_backtest_intraday_ohlcv_request.example.json`
- `tests/unit/core/test_tactic_backtest_system.py`

Boundary:

- Output is evidence only.
- No tactic approval, config mutation, portfolio action, or trading permission.
- Any future adapter must preserve train / test windows, regime segmentation, MAE / MFE, profit factor, data-source freshness, and forbidden-decision checks.

Verification:

- Targeted tactic-backtest tests passed: `7 passed`.
- Example packet generated:
  - `D:\gemini\lianghua\stock_team\findings\tactic_backtest_ohlcv_example.md`
  - `D:\gemini\lianghua\stock_team\findings\tactic_backtest_ohlcv_example.json`

Next allowed extension:

- Polygon-first historical adapter that converts Polygon 1m / 5m aggregates into the same normalized OHLCV shape used by `intraday_ohlcv_fixture`.
- It must expose source, freshness, missing-data, and cache metadata.
- It must not add a second tactic-backtest command.

### 0. Stage 0 Pre-Market Context Packet - Contract Guard And Adapter Input Added

Status:

- `market-context` exists.
- `--universe` is required.
- `--as-of` is now required for live Stage 0 runs.
- `--as-of` must be before 09:30 ET on the requested session date.
- Live Stage 0 now fails with `missing_pre_market_data` unless market rows carry explicit `window=pre_market_before_09_30_ET` and matching `as_of_et`.
- Polygon cache / daily bars / yfinance / post-open data must not be used to reconstruct pre-market decision state.
- `--pre-market-snapshot` now accepts an explicit pre-market snapshot adapter JSON and can produce a valid Stage 0 packet if its `as_of_et` and `window` match the live Stage 0 contract.
- Stage 0 now rejects a naked ticker universe before market evidence collection.
- The brain universe must include `source_inputs.positions`, `source_inputs.prior_review`, `source_inputs.cognition_state`, `permission_state_before_open`, and `forbidden_actions`.
- Missing those brain-owned preconditions exits with `missing_brain_precondition_state` and writes no packet.
- The packet echoes brain-owned state only as input completeness facts: `brain_precondition_state_complete`, `permission_state_before_open_echo`, `source_positions_present`, `prior_review_present`, `cognition_state_present`, and `forbidden_actions_echo`.
- `stock_team` must not interpret cognition, change permission state, or approve trading.
- Broker and trade dates must use US/Eastern market-session boundaries. Beijing local date `2026-06-09` maps to US trading date `2026-06-08`; the prior US trading day is `2026-06-05`.
- Read-only IBKR broker report from the 2026-06-09 handoff:
  - `C:\Users\rriww\Documents\investing-os\system\data\snapshots\broker\ibkr-readonly-broker-report-local-2026-06-09-us-2026-06-08.md`
- Prior US trading day supplement:
  - `C:\Users\rriww\Documents\investing-os\system\data\snapshots\broker\ibkr-readonly-broker-supplement-us-2026-06-05.md`
  - IBKR Gateway did not return 2026-06-05 executions through `reqExecutions`; reconstructing that major drawdown still requires IBKR Activity Statement / Flex Query / Client Portal export or screenshots/logs.
- A real Polygon / IBKR collector is still needed to generate that adapter JSON automatically before the open.
- Offline fixtures remain allowed for tests and demos.
- Codex verification: `tests\unit\core\test_cli.py` passed with `31 passed`.

Codex replay flow run on 2026-06-09:

- User did not connect IBKR; replay used the latest saved read-only IBKR report above.
- Stage 0 replay fixture:
  - `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-market-context-fixture.2026-06-08.INTC-MU-COHR.replay.json`
- Stage 0 brain universe:
  - `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-pre-market-universe.2026-06-08.INTC-MU-COHR.v2.json`
- Canonical Stage 0 output written:
  - `C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`
- Stage 0 output confirmed:
  - `brain_precondition_state_complete: true`
  - `permission_state_before_open_echo: Red`
  - `source_positions_present: true`
  - `prior_review_present: true`
  - `cognition_state_present: true`
  - `forbidden_actions_echo` includes no new short-term risk, no new leveraged product trade, no loss-repair re-entry.
- This was a replay / structural flow test, not a live pre-market production packet.

Canonical output path when called by `investing-os`:

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md
```

Rules:

- `stock_team` may save internal diagnostic copies.
- Stage 1 and the brain read only the canonical path unless a simulation explicitly overrides it.
- Do not regress output fields: market context, sector/theme heat, universe input quality, universe relevance map, catalysts, missing data, forbidden sections absent.

Brain input artifact for Stage 0:

- Template:
  - `C:\Users\rriww\Documents\investing-os\templates\pre-market-universe.json`
- Demo universe for validation:
  - `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-pre-market-universe.MU-NVDA-COHR-INTC.demo.json`

Required Stage 0 validation command:

```powershell
python -m stock_team.cli market-context --date 2026-06-06 --as-of "2026-06-06T09:20:00-04:00" --themes "semiconductors,ai_infrastructure,memory,cloud,optical" --universe "C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-pre-market-universe.MU-NVDA-COHR-INTC.demo.json" --out "C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md"
```

Expected current behavior until the adapter exists:

- Without `--pre-market-snapshot`, the command must fail with `missing_pre_market_data`.
- It must not write a packet.
- This is correct; a fake Stage 0 is worse than a blocked Stage 0.

Valid adapter shape:

```json
{
  "as_of_et": "2026-06-08T09:20:00-04:00",
  "window": "pre_market_before_09_30_ET",
  "markets": {
    "QQQ": {"price": 719.2, "prev_close": 705.06, "return_5d": -1.2, "return_20d": 1.4, "volume_ratio": 0.3, "source": "polygon_premarket_snapshot"}
  },
  "themes": {
    "memory": {"proxy": "MU", "return_5d": -2.5, "return_20d": 12.0, "source": "polygon_premarket_snapshot"}
  },
  "catalysts": []
}
```

Valid adapter command:

```powershell
python -m stock_team.cli market-context --date 2026-06-06 --as-of "2026-06-06T09:20:00-04:00" --pre-market-snapshot "<adapter-json>" --themes "memory,optical" --universe "<brain-universe-json>" --out "C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md"
```

Remaining maintenance only:

- Keep cache freshness metadata visible.
- Keep factual catalysts evidence-only.
- Add regression tests if changing Stage 0 internals.

### 1. Stage 1 Pre-Market Plan Evidence Packet - Current Priority

Purpose:

After `investing-os` and the user choose the focus pool, `stock_team` reads the brain-owned pre-market decision sheet, calculates evidence, checks brain-provided rules, and writes the plan evidence packet.

Current status:

- Implementation exists.
- Codex verification: `tests\unit\core\test_cli.py` passed with `9 passed`.
- Output exists at the canonical path.
- Codex replay flow run on 2026-06-09 wrote a Red / observe-only Stage 1 decision sheet:
  - `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.2026-06-08.INTC-MU-COHR.replay-red.json`
- Canonical Stage 1 output written:
  - `C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.md`
- Stage 1 output confirmed:
  - Focus pool: INTC, MU, COHR
  - Permission echo: Red
  - Plan mode: observe_only
  - Rule collision result: `evidence_only_no_action_readiness`
  - Data status: `fallback_data`; yfinance fallback warning is present, so this is not production-grade market data.
- Contract review is not yet accepted. Fix the issues below before moving to the intraday dashboard.
- End-to-end route is not yet accepted because the canonical Stage 0 packet currently remains an empty template in `investing-os`; Stage 1 must be tested against a populated canonical Stage 0 packet, not a stale simulation or internal `findings` copy.

Brain input:

- `pre_market_decision_sheet` JSON from `investing-os`
- canonical Stage 0 packet:
  - `C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`

Stage 1 demo input:

- `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.MU-NVDA.demo.json`

Canonical output:

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.md
```

Required Stage 1 validation command:

```powershell
python -m stock_team.cli premarket --date 2026-06-06 --decision-sheet "C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.MU-NVDA.demo.json" --out "C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.md"
```

If `stock_team` still requires `--watchlist`, it may pass the same Stage 0 universe file, but the decision sheet remains the source of the Stage 1 focus pool.

Required output sections:

- YAML header with `packet_type: plan_evidence_packet`
- `brain_input_artifact`
- `derived_from_stage0_packet`
- data sources and freshness
- missing data / warnings
- Stage 0 market context echo
- Brain Decision Echo
- Symbol Candidate Factor Calculations
- Requested Formula Outputs
- Rule Collision Results
- Machine-Readable Summary JSON block
- Forbidden Sections Absent

Allowed calculations:

- 1D / 5D / 20D return
- relative strength versus benchmark / theme proxy
- volume ratio
- ATR(14)
- MA20 / MA50 distance
- prior day high / low
- VWAP or anchored VWAP when data supports it
- premarket gap when available
- linked leveraged exposure facts from IBKR or fallback positions

Required naming:

- Use `computed_reference_levels`, not `recommended_entry`.
- Use `risk_distance_facts`, not `stop_loss`.
- Use `formula_output_echo`, not `support recommendation`.

Rule collision boundaries:

- Only collide facts against rules provided by `investing-os`.
- Yellow / Red state may be echoed and checked, but `stock_team` must not change permission state.
- `preauthorized_action_fast_check` in Stage 1 only validates whether the rule definition is complete and data is available. Runtime pass/fail belongs to the intraday dashboard.
- If MU is in focus and MUU exposure exists, output linked exposure facts only, for example:
  - `linked_leveraged_exposure_detected: true`
  - `related_position: MUU`
  - `source: IBKR | cached_ibkr | positions_fixture`
  Do not label the user motive as loss repair.

Forbidden:

- buy / sell / hold
- can trade / should enter / should exit
- permission approved
- invented entry / stop / sizing
- psychological motive classification

Required tests:

- decision sheet parsing with missing optional fields
- canonical Stage 0 packet path handling
- YAML and JSON summary validity
- MU + MUU linked leveraged exposure fixture
- Yellow / Red rule collision echo without permission mutation
- forbidden language scan

Required fixes from Codex review:

0. Prove the formal Stage 0 -> Stage 1 path, not only internal outputs.
   - Run Stage 0 with `--out C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`.
   - Confirm that this canonical file contains real market context, data sources, catalyst facts, universe quality, and forbidden sections absent.
   - Then run Stage 1 reading that exact file through `derived_from_stage0_packet`.
   - Return both commands and output paths.
1. Do not mark Stage 1 runtime conditions as met.
   - Current output says `preauthorized_conditions_met`.
   - Stage 1 may only output `preauthorized_definition_complete`, `required_data_available`, or `required_data_missing`.
   - Runtime trigger pass/fail belongs to the intraday dashboard.
2. Do not imply psychological motive.
   - Current output uses `loss_repair_guard` and `risk_context_for_brain_review`, which is acceptable only if the fact is phrased as linked exposure.
   - Replace motive language with `linked_leveraged_exposure_detected`.
   - Include `related_position: MUU` and the source freshness.
3. Do not claim production verification when using fallback / yfinance.
   - Current output declares `status: verified` while `data_sources` is `yfinance` and computed levels say `Source: fallback`.
   - Either use Polygon/IBKR production sources or downgrade status to `verified_fixture` / `fallback_data`.
   - `warnings` must explain why Polygon / IBKR were unavailable.
4. Stale metadata must be truthful.
   - If using prior-day / weekend / fallback bars for a simulated date, do not set `Stale: false` without freshness reasoning.
5. Forbidden-language scan should distinguish boundary disclaimers from recommendations.
   - It is okay to list forbidden phrases in `Forbidden Sections Absent`.
   - The scan should fail only if those phrases appear as recommendations, readiness labels, or permission approvals.
6. Use a structured Stage 0 universe for formal validation.
   - The current demo watchlist contains only `default_symbols`.
   - That is acceptable as a loose smoke test, but formal Stage 0 validation should use a brain universe with `symbol`, `role`, `theme`, and `research_status`.
   - Missing fields should be audited, not silently guessed.
7. Clean up motive language in the Stage 1 brain demo before using it as a contract fixture.
   - Replace `MUU_repair_motive` with a neutral exposure rule such as `MUU_linked_leveraged_exposure`.
   - Replace conditions like `not_repair_trading` with measurable checks such as `no_linked_leveraged_exposure_exception`.

### 2. Intraday Evidence Dashboard Producer - Next

Purpose:

Use the brain-generated intraday guidance artifact to build a `stock_team` evidence dashboard and latest manifest.

Current Codex status on 2026-06-07:

- The HTML evidence dashboard has been generated and opened at:
  - `C:\Users\rriww\Documents\investing-os\dashboards\latest_evidence_dashboard.html`
- Stage 0 and Stage 1 packet readiness checks are implemented.
- Runtime refresh loop exists and is bounded by iteration and subprocess timeout controls.
- Polygon runtime 1m aggregate data is preferred when bars exist; yfinance/local fallback is explicitly warned.
- Polygon runtime 1m bars were slow because each dashboard iteration requested full-day 1m aggregate bars for each ticker sequentially. Codex changed `_fetch_polygon_runtime_snapshots` to de-duplicate symbols, fetch missing symbols concurrently, keep the short runtime cache, and preserve bounded per-symbol timeouts.
- `--allow-yfinance-runtime-fallback` is now explicit opt-in for dashboard runtime prices so yfinance cannot silently slow the loop.
- `--runtime-request-timeout-seconds` controls per-symbol Polygon runtime timeout; default is short so a degraded data source surfaces warnings instead of freezing the loop.
- The dashboard should be revisited after Stage 0 / Stage 1 backtest design is in place.
- Remaining dashboard work:
  - integrate this evidence view more cleanly into the investing-os operating dashboard;
  - make non-trading-day / no-bar warnings more readable;
  - preserve the boundary that the dashboard shows facts only, not trading permission.

Codex replay dashboard run on 2026-06-09:

- Observe-only guidance artifact:
  - `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\intraday-guidance.2026-06-08.INTC-MU-COHR.replay-red.minimal.json`
- Canonical dashboard outputs:
  - HTML: `C:\Users\rriww\Documents\investing-os\dashboards\latest_evidence_dashboard.html`
  - Markdown: `C:\Users\rriww\Documents\investing-os\system\data\packets\intraday-dashboard-packet.md`
  - Manifest: `D:\gemini\lianghua\stock_team\reports\latest_evidence_dashboard.json`
- Dashboard confirmed:
  - Stage 0 packet: Ready
  - Stage 1 packet: Ready
  - INTC / MU / COHR: `observe_only`
  - Brain permission echo: `not_allowed`, `evidence_only`
  - IBKR active: false because user did not connect IBKR for this replay.
  - Runtime status: `warning_yfinance_fallback_used`
  - Snapshot freshness: stale / simulated date 2026-06-08.
- A richer condition-monitor guidance was also created, but minimal guidance was used for the visible dashboard because some stock_team Chinese condition translation strings currently produce mojibake in JSON/HTML.
- Next dashboard fix should address translation encoding before reintroducing detailed condition rows.

New Stage backtest split:

- `stage-context-backtest` validates Stage 0 / Stage 1 environment and plan gate quality.
- `tactic-backtest` validates concrete intraday triggers and exit models.
- Do not merge these two into one optimizer.

Backtest runtime boundary:

- Backtests are research/review only.
- Do not run `stage-context-backtest` or `tactic-backtest` inside the intraday dashboard refresh loop.
- Do not run parameter sweeps, rule optimization, or context optimization during live trading runtime.
- Use backtests only when explicitly validating a strategy for possible adoption, investigating a post-market problem, or doing weekend/research strategy evolution.
- Historical intraday bars may be used by `tactic-backtest`, but that means historical intraday-style evidence, not live intraday execution.
- The dashboard remains a facts console: frozen packet readiness, runtime prices, levels, conditions, exposure, data health, warnings, latest manifest, and HTML output.

Research entry rule for next agent:

- If the user asks about Stage 0, Stage 1, macro factors, broad market permission, 50-stock candidate-pool selection, or whether a tactic/factor should enter the system, do not start with intraday ORB/VWAP/EMA trigger tests.
- Start with daily/multi-day macro/stage evidence: QQQ regime, VIX regime, market volume regime, sector/theme relative strength, candidate symbol relative strength, catalyst overlays when available, and forward 3D / 5D / 10D / 20D outcomes.
- Macro/stage research must not use fixed 1%-2% take-profit or stop-loss assumptions and must not force same-day exit.
- Use `tactic-backtest` only after the macro/stage gate is defined and the explicit research question is intraday trigger execution.
- Current correction from Codex: the prior ORB/VWAP/EMA intraday sweeps were the wrong entry for the user’s macro-factor question. Treat those outputs as diagnostic/anti-pattern evidence, not as macro-factor conclusions.

Stage 0 / Stage 1 refresh boundary:

- Treat Stage 0 and Stage 1 as pre-market anchors for the trading day.
- Do not auto-refresh or regenerate Stage 0 / Stage 1 during the intraday dashboard loop.
- The intraday dashboard may verify that the canonical Stage 0 / Stage 1 packets exist and expose their freshness, but it must not mutate them.
- Intraday refresh belongs to factual runtime snapshots only: prices, VWAP/level position, condition pass/fail/stale/missing, IBKR positions/orders/fills/account exposure, data-source health, and latest manifest/HTML output.
- Regenerate Stage 0 intraday only after explicit user/brain request for a major market-context reset.
- Regenerate Stage 1 intraday only after explicit user/brain change to plan, permission state, focus pool, risk budget, allowed tactics, or forbidden actions.

Brain artifact examples:

- `C:\Users\rriww\Documents\investing-os\templates\intraday-guidance-to-stock-team.json`
- `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\intraday-guidance.NVDA-conditional.demo.json`

Canonical latest manifest:

```text
D:\gemini\lianghua\stock_team\reports\latest_evidence_dashboard.json
```

Dashboard should show:

- packet readiness
- data source health
- runtime snapshot freshness
- symbol condition pass / fail / partial / stale / missing
- missing data
- latest packet links

Allowed updater loop:

```powershell
python -m stock_team.cli intraday-dashboard --guidance "<intraday guidance json>" --out "<dashboard packet md>" --html-out "<dashboard html>" --loop --interval-seconds 60
```

For tests or controlled demos, pass `--iterations <n>`.

Loop rules:

- Each iteration may rewrite the latest manifest, dashboard HTML, and optional Markdown dashboard packet.
- Each iteration must keep Stage 0 / Stage 1 packets read-only.
- The manifest should expose updater metadata such as whether loop mode is enabled, current iteration, requested iteration limit, and interval seconds.
- Tests and controlled demos must use `--iterations` plus a subprocess timeout so loop regressions cannot hang the test runner.
- Runtime refresh subprocesses must have bounded timeouts and surface timeout warnings rather than blocking an updater iteration indefinitely.

Dashboard must not show:

- buy / sell / hold
- permission approved
- can trade / should enter / should exit
- live execution controls

### 3. Post-Market Trade Evidence Packet

Purpose:

Before `investing-os` starts cognitive review, `stock_team` produces a factual post-market trade evidence packet.

Input contract:

- `C:\Users\rriww\Documents\investing-os\templates\post-market-trade-evidence-request.json`

Output contracts:

- `C:\Users\rriww\Documents\investing-os\system\data\packets\post-market-trade-evidence-packet.md`
- `C:\Users\rriww\Documents\investing-os\system\data\packets\contextual-trade-evidence-packet.md`

Required facts:

- IBKR orders, fills, positions, account P/L, commissions, exposure when connected
- full-day QQQ / SPY / IWM / VIX proxy tape
- full-day symbol and reviewed-symbol tape
- relevant sector / theme / peer proxy tape
- VWAP, volume ratio, price-vs-VWAP state
- opening 30-minute structure split into 0-5m, 5-15m, 15-30m
- key intraday nodes
- fill-against-context table
- data quality and missing-data notes

Forbidden:

- psychological interpretation
- final trading judgment
- principle update
- buy / sell / hold recommendation

### 4. Event Reconstruction And Periodic Tactic Summary

Purpose:

Provide evidence for missed opportunities, false positives, rule triggers without trade, and weekly/monthly tactic review.

Input / output contracts:

- `C:\Users\rriww\Documents\investing-os\templates\event-reconstruction-request.json`
- `C:\Users\rriww\Documents\investing-os\system\data\packets\event-reconstruction-packet.md`
- `C:\Users\rriww\Documents\investing-os\templates\tactic-event-summary-request.json`
- `C:\Users\rriww\Documents\investing-os\system\data\packets\tactic-event-summary-packet.md`

Must remain evidence-only:

- no final lesson
- no strategy adoption decision
- no psychological interpretation
- no principle update
- no recommendation

### 5. Research Evidence Packets

Purpose:

Support company / industry research with factual evidence, not conclusions.

Company packet contract:

- `C:\Users\rriww\Documents\investing-os\system\data\packets\company-research-packet.md`

Industry packet contract:

- `C:\Users\rriww\Documents\investing-os\system\data\packets\industry-research-packet.md`

Useful first examples:

- COHR peer evidence: COHR, LITE, AAOI, SOXX, QQQ
- ORCL company evidence: ORCL, MSFT, AMZN, GOOGL, IGV, QQQ

### 6. Packet Producer Map And CLI Contract Docs

Purpose:

Make it obvious which `stock_team` command produces which packet.

Create or update inside `stock_team`:

- `docs/CLI_CONTRACT.md`
- `docs/PACKET_PRODUCER_MAP.md`

Each producer map entry should include:

- command
- input artifact
- output artifact
- data sources
- tests
- known gaps
- forbidden behavior check

## Acceptance Report Format

When reporting back, return:

```yaml
implemented_commands:
  - command:
    status:
    smoke_test:
    example_output:
    canonical_output_path:
known_gaps:
  - gap:
    reason:
    proposed_next_step:
forbidden_behavior_check:
  buy_sell_hold_recommendations_present: false
  permission_approval_present: false
  psychological_interpretation_present: false
  live_execution_controls_present: false
  direct_user_entrypoints_created: false
```

## Cleared Or Not Active

Removed from the current active queue:

- old broad CLI checklist that mixed completed and future work
- old `scratch` and `findings` paths as canonical Stage 0 outputs
- runtime consumer implementation request
- direct polling / live workflow until `investing-os` authorizes the intraday contract
- duplicate SNXX / COHR / ORCL examples as top-level current tasks; they are now examples under post-market or research packets

Archive reference:

- `C:\Users\rriww\Documents\investing-os\handoff\inventory\antigravity-completed-and-cleared-2026-06-06.md`
