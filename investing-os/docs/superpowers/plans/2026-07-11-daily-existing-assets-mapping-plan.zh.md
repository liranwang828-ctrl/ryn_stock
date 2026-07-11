# DAILY Existing Assets Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a content-based map from the approved conversation-driven DAILY design to existing `investing-os` and `stock_team` files, identifying what can be reused immediately before any new runtime implementation.

**Architecture:** Inspect only the already identified DAILY workflow, runtime, packet, template, dashboard, and test files. Map each required DAILY capability to its current producer, canonical artifact, validator/state logic, display surface, and verified gap. Classify every inspected file as `reuse-now`, `merge-later`, `reference-only`, or `retire-later`; do not modify runtime code in this batch.

**Tech Stack:** Markdown contracts, JSON templates, Python orchestration/dashboard code, HTML/JavaScript dashboards, pytest tests, Git.

---

## File structure

### Create

- `investing-os/handoff/2026-07-11-daily-existing-assets-map.zh.md`
  - Capability-level map for DAILY-0 through DAILY-4.
- `investing-os/handoff/2026-07-11-daily-existing-file-ledger.zh.md`
  - Per-file content summary, dependencies, status tag, and recommended disposition.

### Modify

- `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`
  - Record mapping completion, confirmed reuse chain, and implementation order.

### Inspect only

- Approved design and canonical DAILY contracts.
- Identified `investing-os` workflow/template/packet files.
- Identified `stock_team` orchestration/dashboard files and focused tests.
- Existing operating, growth/cognition, intraday, and evidence dashboards plus their data generators.
- Existing old-system audit appendices as navigation evidence, not as a substitute for file-content inspection.

## Task 1: Map DAILY-0 and DAILY-1 runtime chain

**Inspect:**

- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- `investing-os/system/workflows/pre-market.md`
- `investing-os/templates/pre-market-universe.json`
- `investing-os/templates/pre-market-decision-sheet.json`
- `investing-os/system/data/packets/pre-market-context-packet.md`
- `stock_team/orchestration/models.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/orchestration/adapters.py`
- `stock_team/orchestration/coordinator.py`
- `stock_team/cli.py` only at `premarket-snapshot`, `market-context`, and `premarket` handlers
- focused orchestration, CLI, dashboard, and DAILY E2E tests that exercise these paths

- [ ] Extract for each capability: input, producer, output path, validation, confirmation owner, state effect, and failure behavior.
- [ ] Verify whether an existing file already represents `daily-start`, Stage 0 discussion, focus confirmation, Stage 1 evidence, plan, and intraday guidance.
- [ ] Record only content-supported gaps; do not infer absence from filenames.
- [ ] Add the DAILY-0/1 section to `2026-07-11-daily-existing-assets-map.zh.md`.

Verification:

```powershell
rg -n "DAILY-0|DAILY-1|daily-start|Stage 0|focus|decision sheet|plan|guidance" investing-os/handoff/2026-07-11-daily-existing-assets-map.zh.md
```

Expected: DAILY-0 and DAILY-1 each have a complete producer-to-display chain or an explicitly evidenced gap.

## Task 2: Map DAILY-2, DAILY-3, and DAILY-4

**Inspect:**

- `investing-os/system/workflows/intraday.md`
- `investing-os/system/workflows/intraday-guidance-protocol.md`
- `investing-os/system/workflows/post-market-trade-review.md`
- `investing-os/system/data/packets/intraday_snapshot.md`
- `investing-os/system/data/packets/intraday-dashboard-packet.md`
- relevant `stock_team/cli.py` intraday/review handlers
- `stock_team/orchestration/coordinator.py`
- `stock_team/server/dashboard_experience_loop.py`
- `stock_team/server/dashboard_experience_paths.py`
- focused intraday, review, experience-loop, and DAILY E2E tests

- [ ] Map existing snapshot, guidance, exception confirmation, review, archive, and cross-day recovery behavior.
- [ ] Locate any existing structure that can represent user-originated intraday observations and raw conversation references.
- [ ] Separate facts already produced from dialogue/confirmation capabilities that remain missing.
- [ ] Add the DAILY-2/3/4 section to the asset map.

Verification:

```powershell
rg -n "DAILY-2|DAILY-3|DAILY-4|intraday event|exception|review|archive|cross-day" investing-os/handoff/2026-07-11-daily-existing-assets-map.zh.md
```

Expected: opening observation, intraday management, and post-market review are separately mapped.

## Task 3: Map the two Dashboard surfaces and data generators

**Inspect:**

- `investing-os/dashboards/operating-console.html`
- `investing-os/dashboards/assets/operating-console-data.js`
- `investing-os/dashboards/growth-dashboard-draft.html`
- `investing-os/dashboards/assets/growth-dashboard-data.js`
- `investing-os/dashboards/assets/growth-dashboard-indexes.js`
- `investing-os/tools/generate-growth-dashboard-data.ps1`
- `investing-os/dashboards/intraday-dashboard.html`
- `investing-os/dashboards/latest_evidence_dashboard.html`
- `stock_team/server/dashboard_server.py`
- `stock_team/server/dashboard_writer.py`
- `stock_team/server/dashboard_cache.py`
- `stock_team/templates/daily_dashboard.html.j2` if referenced by the writer
- focused dashboard and dashboard-experience tests

- [ ] For each Dashboard, record sections actually rendered, data source, refresh mechanism, actions exposed, and whether it contains business logic.
- [ ] Identify which existing page is the daily trading surface and which is the cognition surface under the approved two-Dashboard decision.
- [ ] Identify reusable navigation, manifest, event-card, freshness, and evolution/promotion views.
- [ ] Record what must remain independent and what shared file contract can connect the two surfaces.

Verification:

```powershell
rg -n "每日交易 Dashboard|认知 Dashboard|data source|refresh|business logic|shared" investing-os/handoff/2026-07-11-daily-existing-assets-map.zh.md
```

Expected: both selected Dashboard roles and their current data pipelines are explicit.

## Task 4: Build the per-file ledger

- [ ] Add every file actually opened in Tasks 1-3 to `2026-07-11-daily-existing-file-ledger.zh.md`.
- [ ] For each file record: content-based responsibility, current consumers/producers, reusable elements, conflict or duplication, evidence lines/functions, and one disposition tag.
- [ ] Use only these tags:
  - `reuse-now`: required directly for the first runnable DAILY pass;
  - `merge-later`: valuable but should be consolidated after the pass works;
  - `reference-only`: examples, historical contracts, or tests useful for comparison;
  - `retire-later`: superseded or duplicative, but never delete without separate user approval.
- [ ] Mark uncertain classifications explicitly with the missing evidence needed; do not guess.

Verification:

```powershell
rg -n "reuse-now|merge-later|reference-only|retire-later" investing-os/handoff/2026-07-11-daily-existing-file-ledger.zh.md
```

Expected: all four tags are defined; only tags supported by inspected content are assigned.

## Task 5: Produce the reuse-first implementation sequence

- [ ] Cross-check the capability map against `2026-07-11-conversation-driven-daily-workflow-design.zh.md` section by section.
- [ ] Identify the smallest existing chain that can run DAILY-0 through DAILY-1 without new duplicate artifacts.
- [ ] List the exact existing commands, files, validators, and Dashboard surfaces for the first isolated pass.
- [ ] Separate tasks suitable for lower-tier models from decisions requiring user/high-level discussion.
- [ ] Update `WORKFLOW-STATUS.zh.md` with the mapping result and next implementation batch.

Verification:

```powershell
rg -n "first isolated pass|低阶|高阶|reuse-now|next implementation" investing-os/handoff/2026-07-11-daily-existing-assets-map.zh.md investing-os/system/workflows/WORKFLOW-STATUS.zh.md
git diff --check
```

Expected: implementation can start from an exact reuse chain rather than another repository scan.

## Final verification and commit

- [ ] Confirm no runtime Python, HTML, JavaScript, templates, or packet contracts changed.
- [ ] Confirm every recommendation cites an inspected file, symbol, section, command, or test.
- [ ] Run:

```powershell
git status --short
git diff --check
rg -n "TBD|TODO|implement later|待后续补充" investing-os/handoff/2026-07-11-daily-existing-assets-map.zh.md investing-os/handoff/2026-07-11-daily-existing-file-ledger.zh.md
```

- [ ] Commit:

```powershell
git add -- investing-os/handoff/2026-07-11-daily-existing-assets-map.zh.md investing-os/handoff/2026-07-11-daily-existing-file-ledger.zh.md investing-os/system/workflows/WORKFLOW-STATUS.zh.md
git commit -m "docs: map existing assets to conversation-driven DAILY"
```

## Self-review

- The plan maps existing implementation before authorizing new code.
- Scope is limited to files already identified by the approved design and prior content audit.
- Both Dashboard surfaces are inspected by content, not classified by filename.
- File disposition is non-destructive; no deletion or broad refactor is authorized.
- The output directly supports a runnable DAILY-0/1 implementation batch.
