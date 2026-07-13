# Premarket Tape Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an observation-only cross-asset premarket tape that shows futures, ETF premarket quotes, BTC and macro proxies with explicit timestamps, comparison semantics, freshness and conflict checks.

**Architecture:** Keep the existing observation Stage 0 daily-close snapshot unchanged. Add a focused `premarket_tape.py` producer with injectable loaders, publish its JSON as a separate runtime artifact, optionally wire it into `start_stage0_observation`, and expose a compact read-only payload to the operating console. All trade permission and Stage transitions remain unchanged.

**Tech Stack:** Python 3, yfinance, pytest, existing orchestration adapter and dashboard server, vanilla HTML/JavaScript operating console.

---

## File map

- Create `stock_team/data_ingest/premarket_tape.py`: asset configuration, normalization, freshness, cross-asset checks, atomic JSON producer and CLI.
- Create `stock_team/tests/unit/data_ingest/test_premarket_tape.py`: pure unit and producer tests with injected loaders.
- Modify `stock_team/orchestration/adapters.py`: optionally invoke the independent tape producer when `tape_out` is supplied.
- Modify `stock_team/tests/unit/orchestration/test_adapters.py`: adapter wiring and backward compatibility tests.
- Modify `stock_team/server/dashboard_server.py`: read the canonical tape artifact and expose a compact read-only summary.
- Modify `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`: manifest parsing and missing/degraded behavior tests.
- Modify `investing-os/dashboards/operating-console.html`: show one compact Premarket Tape block without adding workflow logic or POST actions.

### Task 1: Normalize records and freshness

**Files:**
- Create: `stock_team/data_ingest/premarket_tape.py`
- Test: `stock_team/tests/unit/data_ingest/test_premarket_tape.py`

- [ ] **Step 1: Write failing tests for record semantics**

Add tests that call the wished-for API:

```python
from datetime import datetime
from stock_team.data_ingest.premarket_tape import normalize_record

def test_etf_record_uses_prior_regular_close_and_intraday_last_bar():
    record = normalize_record(
        symbol="QQQ",
        asset_class="etf_premarket",
        last=717.62,
        comparison_value=725.51,
        comparison_kind="prior_regular_close",
        as_of_et="2026-07-13T08:21:46-04:00",
        source="yfinance_1m_prepost",
        now_et=datetime.fromisoformat("2026-07-13T08:25:00-04:00"),
        reported_volume=0,
    )
    assert record["change_pct"] == -1.09
    assert record["freshness"] == "fresh"
    assert record["quality"] == "degraded"
    assert record["issues"] == ["zero_reported_volume"]

def test_unknown_comparison_kind_is_not_usable():
    record = normalize_record(
        symbol="NQ=F", asset_class="index_future", last=29728.5,
        comparison_value=29695.25, comparison_kind="provider_defined_unknown",
        as_of_et="2026-07-13T08:11:00-04:00", source="yfinance_fast_info",
        now_et=datetime.fromisoformat("2026-07-13T08:12:00-04:00"),
    )
    assert record["quality"] == "degraded"
    assert "comparison_semantics_unknown" in record["issues"]
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest stock_team/tests/unit/data_ingest/test_premarket_tape.py -q
```

Expected: collection fails because `stock_team.data_ingest.premarket_tape` does not exist.

- [ ] **Step 3: Implement minimal normalization**

Implement constants and functions:

```python
FRESH_MINUTES = 10
AGING_MINUTES = 30
KNOWN_COMPARISON_KINDS = {
    "prior_regular_close",
    "prior_futures_settlement_or_provider_previous_close",
    "prior_24h_reference",
}

def classify_freshness(as_of_et: str, now_et: datetime) -> str: ...
def normalize_record(*, symbol: str, asset_class: str, last: float,
                     comparison_value: float | None, comparison_kind: str,
                     as_of_et: str, source: str, now_et: datetime,
                     reported_volume: int | None = None) -> dict: ...
```

Calculate percentage changes to two decimals. Mark zero-volume ETF records degraded, unknown comparison semantics degraded, and stale records `stale_unverified`.

- [ ] **Step 4: Add and verify freshness boundary tests**

Test exactly 10 minutes as fresh, more than 10 through 30 as aging, more than 30 as stale, and a future timestamp as degraded with `timestamp_in_future`.

- [ ] **Step 5: Run Task 1 tests GREEN**

Run the focused test file. Expected: all Task 1 tests pass.

### Task 2: Cross-asset reconciliation

**Files:**
- Modify: `stock_team/data_ingest/premarket_tape.py`
- Modify: `stock_team/tests/unit/data_ingest/test_premarket_tape.py`

- [ ] **Step 1: Write failing reconciliation tests**

```python
from stock_team.data_ingest.premarket_tape import compare_pair

def test_qqq_nq_opposite_directions_are_conflicted():
    result = compare_pair(
        "QQQ_NQ",
        {"change_pct": -1.09, "quality": "degraded", "freshness": "fresh"},
        {"change_pct": 0.30, "quality": "usable_observation", "freshness": "fresh"},
    )
    assert result["status"] == "conflicted"

def test_stale_member_makes_pair_insufficient_quality():
    result = compare_pair(
        "QQQ_NQ",
        {"change_pct": -0.2, "quality": "stale_unverified", "freshness": "stale"},
        {"change_pct": -0.1, "quality": "usable_observation", "freshness": "fresh"},
    )
    assert result["status"] == "insufficient_quality"
```

- [ ] **Step 2: Run the new tests RED**

Expected: import or attribute failure for `compare_pair`.

- [ ] **Step 3: Implement reconciliation**

Implement `compare_pair(name, left, right)` with these rules:

- stale/missing record -> `insufficient_quality`;
- absolute change difference greater than 0.50 percentage points -> `conflicted`;
- opposite signs with both absolute changes greater than 0.20 -> `conflicted`;
- otherwise -> `aligned`.

Implement `build_cross_asset_checks(records)` for `QQQ_NQ`, `SPY_ES`, and `IWM_RTY`, plus a non-directional macro descriptor.

- [ ] **Step 4: Run focused tests GREEN**

Expected: normalization and reconciliation tests all pass.

### Task 3: Producer, yfinance loader and atomic output

**Files:**
- Modify: `stock_team/data_ingest/premarket_tape.py`
- Modify: `stock_team/tests/unit/data_ingest/test_premarket_tape.py`

- [ ] **Step 1: Write failing producer tests**

Use an injected `record_loader(symbol, asset_class, now_et)` returning deterministic rows. Assert:

```python
payload = build_premarket_tape(
    trading_date="2026-07-13",
    session_id="observation-2026-07-13",
    now_et=datetime.fromisoformat("2026-07-13T08:25:00-04:00"),
    output_path=tmp_path / "tape.json",
    focus_symbols=["AMAT", "TSM"],
    record_loader=fake_loader,
)
assert payload["evidence_level"] == "observation_only"
assert payload["permission"] == "no_trading_permission"
assert payload["cross_asset_checks"]["QQQ_NQ"]["status"] == "conflicted"
assert json.loads((tmp_path / "tape.json").read_text())["session_id"] == "observation-2026-07-13"
```

Also test one missing non-core symbol yields `status: partial`; all core symbols missing raises `RuntimeError` and leaves no final output.

- [ ] **Step 2: Run producer tests RED**

Expected: missing `build_premarket_tape`.

- [ ] **Step 3: Implement producer and loaders**

Implement:

- static asset map from the approved design;
- `_load_yfinance_record()` using ETF pre/post last valid bar rather than `fast_info.last_price`;
- futures and macro records with explicit provider-derived comparison kind;
- BTC timestamp validation;
- focus symbols loaded as `focus_equity_premarket`;
- per-symbol exception capture;
- temporary JSON followed by `Path.replace()`.

Add CLI arguments:

```text
--date --session-id --as-of --out [--universe]
```

If `--universe` exists, read `primary_focus` and `cognition_watchlist`; otherwise use no focus equities.

- [ ] **Step 4: Run producer tests GREEN**

Expected: all data-ingest tests pass without network access.

- [ ] **Step 5: Run a real isolated producer smoke test**

Write output beneath a temporary directory, inspect timestamps and quality fields, then delete the temporary directory using native PowerShell after verifying its resolved path is within the workspace temp location.

### Task 4: Optional orchestration wiring

**Files:**
- Modify: `stock_team/orchestration/adapters.py`
- Modify: `stock_team/tests/unit/orchestration/test_adapters.py`

- [ ] **Step 1: Write failing adapter tests**

Extend `test_start_stage0_observation_builds_only_observation_producer_command` with a new test supplying:

```python
"tape_out": str(tape_path),
"universe": str(universe_path),
```

Assert two commands run in order: existing observation producer, then `python -m stock_team.data_ingest.premarket_tape`; assert all three artifacts are returned. Add a regression test without `tape_out` asserting the original single command remains unchanged.

- [ ] **Step 2: Run adapter tests RED**

Expected: only one command is built when tape parameters are supplied.

- [ ] **Step 3: Implement minimal optional wiring**

In the `start_stage0_observation` branch, append the tape command only when `parameters.get("tape_out")` is non-empty. Pass date, session ID, as-of, output and universe. Add `tape_out` to artifact paths.

- [ ] **Step 4: Run adapter and orchestration regression tests GREEN**

Run:

```powershell
python -m pytest stock_team/tests/unit/orchestration/test_adapters.py stock_team/tests/unit/orchestration/test_coordinator.py stock_team/tests/integration/test_daily_e2e.py -q
```

Expected: all pass; existing Stage 0 paths remain unchanged.

### Task 5: Read-only dashboard exposure

**Files:**
- Modify: `stock_team/server/dashboard_server.py`
- Modify: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`
- Modify: `investing-os/dashboards/operating-console.html`

- [ ] **Step 1: Write failing server payload tests**

Create a canonical tape JSON under the test runtime and assert coordinator summary includes:

```python
assert payload["premarket_tape"]["status"] == "partial"
assert payload["premarket_tape"]["groups"]["index_futures"][0]["symbol"] == "NQ=F"
assert payload["premarket_tape"]["cross_asset_checks"]["QQQ_NQ"]["status"] == "conflicted"
```

Add a missing-file test returning `{"status": "missing", "groups": {}, "cross_asset_checks": {}}` without blocking DAILY.

- [ ] **Step 2: Run server tests RED**

Expected: `premarket_tape` absent.

- [ ] **Step 3: Implement read-only summary builder**

Add a small helper that loads `{session_id}-premarket-tape.json`, groups selected display fields by asset class, and never mutates coordinator state. Include it in the dashboard manifest/summary payload.

- [ ] **Step 4: Add compact HTML rendering**

Add a single Premarket Tape section showing last update, four groups, freshness badges and cross-asset statuses. Use only manifest data. Add no POST, buttons or workflow transitions.

- [ ] **Step 5: Run dashboard tests GREEN**

Run the focused dashboard unit tests and the existing dashboard experience-loop integration test.

### Task 6: Real DAILY verification and documentation

**Files:**
- Modify: `investing-os/handoff/2026-07-13-premarket-analysis.zh.md`
- Runtime output: `investing-os/system/runtime/inputs/observation-2026-07-13-premarket-tape.json`

- [ ] **Step 1: Generate the real tape**

Run the producer for `observation-2026-07-13` using the canonical universe and current ET timestamp.

- [ ] **Step 2: Verify artifact semantics**

Confirm QQQ uses its actual pre/post bar, NQ is shown separately, stale BTC is downgraded, and QQQ/NQ disagreement is visible.

- [ ] **Step 3: Run full relevant verification**

```powershell
python -m pytest stock_team/tests/unit/data_ingest/ stock_team/tests/unit/orchestration/ stock_team/tests/unit/core/test_dashboard_refresh_prices.py stock_team/tests/integration/test_daily_e2e.py stock_team/tests/integration/test_dashboard_experience_loop.py -q
```

Expected: zero failures.

- [ ] **Step 4: Record the corrected premarket interpretation**

Update the handoff to distinguish daily baseline, ETF premarket and futures, and include data-quality limitations.

- [ ] **Step 5: Commit and push scoped files**

Stage only files in this plan. Preserve unrelated dirty investing-os wiki/framework changes.

