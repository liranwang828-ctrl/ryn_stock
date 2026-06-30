# Repository Audit - 2026-06-30

## Scope

This audit covers the shared Git repository at:

```text
C:\Users\rriww\Documents\STOCK
```

`investing-os` and `stock_team` are directories in the same repository.

No existing source, runtime state, or user data was deleted during the audit.

## Repository State

- Review branch: `codex/repository-cleanup-20260630`
- Main branch at audit start: `master`
- Starting commit: `b95a820`
- Remote: not configured
- Existing linked worktree:
  - branch: `codex/phase1-coordinator-foundation`
  - path: `.worktrees/phase1-coordinator-foundation`
- Main worktree and coordinator worktree both contain uncommitted changes.

## Keep And Commit

### Coordinator Foundation

The eight commits on `codex/phase1-coordinator-foundation` are a coherent,
tested foundation and should be preserved:

```text
c67993c define coordinator session contracts
d429c47 validate coordinator state models
de7ad2e persist coordinator sessions atomically
2ee8c3a encode coordinator state transitions
e63cceb adapt coordinator to existing cli
b075ec1 coordinate workflow actions idempotently
de5ffad expose workflow coordinator cli
aee24b1 document coordinator workflow entry points
```

The committed branch tests passed:

```text
29 passed
```

The branch's former uncommitted UI/server changes were preserved in:

```text
stash@{0}: archive phase1 coordinator post-foundation ui experiments 2026-06-30
```

They had a failing server test and overlap with newer main-worktree
implementations. The worktree is now clean. Do not merge or apply that stash
without a contract comparison.

### Current Main-Worktree Source Changes

The following are real source changes, not generated artifacts:

- Stage 0 paid-provider and timestamp-proven pre-market collection in
  `stock_team/cli.py`, with focused tests.
- IBKR-only account and position provenance in
  `stock_team/core/ibkr_monitor.py`, with focused tests.
- Shared underlying/leveraged-symbol capsule resolution in
  `stock_team/utils/capsule_utils.py`.
- Capsule path integration in
  `stock_team/core/premarket_consensus_lock.py`.
- Durable leveraged mappings in `stock_team/config/leveraged_pairs.json`.
- Dashboard price-refresh behavior and tests.
- The investing-os workflow agents.
- The operating console and coordinator-facing server implementation.

Observed focused verification:

```text
current orchestration: 23 passed
IBKR and capsule utilities: 3 passed
new Stage 0 pre-market tests: 10 passed
dashboard refresh tests: 10 passed
```

These changes must be committed in separate intent groups. The coordinator,
server, console, agents, and schemas require one integration review because
the main worktree versions differ substantially from both the committed and
uncommitted coordinator-worktree versions.

## Keep Local, Do Not Commit

The following are local runtime or private operational artifacts:

- `investing-os/system/runtime/coordinator-decisions/`
- `investing-os/system/runtime/inputs/`
- `investing-os/system/runtime/packets/`
- `investing-os/system/runtime/sessions/*.json`
- `investing-os/system/runtime/trade-history/`
- `dashboard-*.out.log`
- `dashboard-*.err.log`

The runtime trade-history files may contain account identifiers or execution
records. They must remain local and must not be pushed.

`investing-os/system/runtime/README.md` and
`investing-os/system/runtime/sessions/.gitkeep` are source-level structure
files, but the current main-worktree README conflicts with the newer packet
layout and should not be committed without revision.

## Generated Artifact

`stock_team/reports/dashboard.html` is a generated snapshot containing dated
portfolio values, focus symbols, and the local server port. It has been removed
from the Git index and added to `.gitignore`. The existing local file was
preserved so the current dashboard can continue to run.

## Local Configuration That Needs Separation

### `stock_team/config/server_port.json`

The port changed from `8080` to `58862`. The server writes this file whenever
it binds a port, so the file has been removed from the Git index and added to
`.gitignore`. The local file was preserved.

### `stock_team/config/poll_config.json`

This file mixes durable polling configuration with portfolio and daily focus
fallbacks. It remains tracked because many tools require the static polling,
watchlist, threshold, and sector-map fields. `portfolio_symbols` and
`default_symbols` were reset to empty arrays so Git does not preserve stale
holdings or a dated focus list. Live holdings remain IBKR-owned.

## Coordinator Conflict

There are three relevant coordinator states:

1. Eight committed foundation commits in
   `codex/phase1-coordinator-foundation`.
2. Additional uncommitted UI/server work in that linked worktree.
3. Newer, substantially different uncommitted coordinator/UI/server files in
   the main worktree.

The main-worktree coordinator tests pass, but they cover fewer cases than the
committed branch tests. The linked worktree's added server tests currently
report:

```text
1 passed, 1 failed
```

The failing assertion is a Chinese `start_here` label mismatch. This does not
justify discarding either implementation. Integration must compare behavior
and contracts, not choose solely by modification time.

## Existing Tracked Large Data

The only currently checked-out tracked file above 500 KB is:

```text
investing-os/handoff/inventory/stock_team-inventory-manifest.json
```

It is a historical inventory artifact, approximately 1.08 MB. It is not a
current dirty-worktree problem. Keep it unless repository history is later
split into an archive.

## Proposed Commit Groups

1. Repository hygiene:
   - `.gitignore`
   - this audit report
2. Leveraged-symbol capsule mapping:
   - `stock_team/config/leveraged_pairs.json`
   - `stock_team/utils/capsule_utils.py`
   - `stock_team/core/premarket_consensus_lock.py`
   - capsule tests
3. IBKR source-of-truth cleanup:
   - `stock_team/core/ibkr_monitor.py`
   - IBKR tests
4. Stage 0 true pre-market acquisition:
   - `stock_team/cli.py`
   - focused CLI tests
5. Dashboard and operating console integration:
   - coordinator-facing dashboard server
   - operating console
   - focused dashboard tests
6. Coordinator comparison:
   - preserve the committed coordinator foundation
   - review newer main-worktree schemas, orchestration, agents, server, and
     console as one contract-aware integration

The current coordinator and UI changes were preserved as separate commits.
The older coordinator worktree remains available for contract comparison.

## Do Not Do

- Do not run `git clean`, hard reset, or recursive deletion.
- Do not commit current runtime packets or IBKR trade history.
- Do not commit generated `stock_team/reports/dashboard.html`.
- Do not let a low-tier model resolve the coordinator conflict.
- Do not merge the dirty coordinator worktree wholesale.
- Do not claim push/upload until a Git remote is configured.
