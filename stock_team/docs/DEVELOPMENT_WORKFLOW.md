# Stock Team Development Workflow

> Updated: 2026-05-24

This file defines the practical development flow for the current phase of `stock_team`, with extra emphasis on keeping the worktree clean while multiple models or sessions hand work off to each other.

For repo-agnostic rules, see [GENERAL_DEVELOPER_RULES.md](D:\gemini\lianghua\stock_team\docs\GENERAL_DEVELOPER_RULES.md).

For high/low capability model collaboration, see [agent_collaboration_protocol_zh.md](D:\gemini\lianghua\stock_team\docs\agent_collaboration_protocol_zh.md).

---

## 1. Start-of-session checklist

Every development session should begin with:

1. Read [ANTIGRAVITY_HANDOFF.md](D:\gemini\lianghua\stock_team\ANTIGRAVITY_HANDOFF.md).
2. Run `git status --short`.
3. Run `git diff --stat`.
4. Decide which lane the session belongs to:
   - `dashboard stabilization`
   - `core trading flow`
   - `research/report enrichment`
   - `backtest/parameter work`
   - `cleanup/documentation`
5. Before changing code, identify whether the current dirty files are:
   - product code worth preserving
   - generated runtime data
   - temporary or redundant files
6. For trading-flow sessions, search for `premarket_sandbox_{date}.md` and any handoff note that says the user pasted a premarket sandbox discussion. Treat that discussion as the day's highest-priority source of truth before reading `daily_plan_{date}.json`.

Do not start by re-exploring the whole repo unless the handoff is clearly stale.

---

## 2. Current priority order

For the next stretch of development, use this order:

1. Stabilize the explicit trading conversation flow first.
   Goal: in盘前/盘中/盘后 conversations, the Agent must clearly confirm focus symbols, actions, trigger prices, and whether files are synced or the user should rely on chat-only execution.
2. Treat `premarket_sandbox_{date}.md` or the user's pasted sandbox discussion as the day's highest-priority source of truth.
   Goal: never infer the real strategy only from auto-generated pass-only files such as `daily_plan_{date}.json`.
3. Keep Dashboard work paused unless the user explicitly asks to resume it.
   Goal: avoid spending scarce model budget on Dashboard polishing while trading coordination is handled through conversation.
4. Then move to report enrichment or backtest work only when the user asks.
5. Defer broad refactors until a user-visible pain point forces them.

This repo already has enough moving parts. The fastest progress will come from narrowing scope, not from opening a second front.

---

## 3. Session workflow

### A. Triage

- Inspect current diffs.
- Separate code changes from generated data.
- Decide whether the session is:
  - finishing existing work
  - fixing regressions
  - adding one scoped feature
  - cleanup only

### B. Minimal verification

Use the lightest checks that can catch the likely breakage:

- Python code changes:
  - `python -m py_compile agents/dashboard_server.py agents/dashboard_writer.py`
- Dashboard changes:
  - `python agents/dashboard_server.py`
  - open `/api/status`
  - open `/`
- Focused tests when available:
  - `python -m pytest tests/test_dashboard_writer.py tests/test_premarket_summary.py -q`

If `pytest` is unavailable in the current interpreter, record that explicitly in the handoff only when the work will be handed off or paused. Do not claim full verification.

### C. Implementation

- Keep edits in the active lane only.
- Prefer small, reviewable patches.
- Do not mix feature work with unrelated cleanup unless the cleanup is obviously safe.

### D. Closeout

Before ending a session:

1. Re-run the narrow verification that matches the edits.
2. Update `ANTIGRAVITY_HANDOFF.md` only if the work is being handed off, paused, or left in a state where the next session needs context.
3. Prepare commit groups, but do not mix runtime outputs into code commits.

---

## 4. Commit hygiene

Use separate commits for separate intent.

### Commit together

- `agents/*.py`
- `templates/*.j2`
- `docs/*.md`
- `.gitignore`

### Usually do not commit

- `data_raw_primary.json`
- `data_raw_secondary.json`
- `data_verified.json`
- `discussion_board.jsonl`
- `strategy_result.json`
- `persona_stances.jsonl`
- `findings/*.json` unless deliberately preserving a fixture or reference output
- `learning/intraday_data.db`
- generated `reports/daily_dashboard_*.html`

### Runtime files that should stay untracked or ignored

- `run.lock`
- `logs/*`
- `.bak` backups

If a commit contains both code and runtime artifacts, split it before submitting.

---

## 5. Current assessment of the dirty worktree

### Worth preserving and likely commitable

- `agents/dashboard_writer.py`
- `templates/daily_dashboard.html.j2`
- `templates/scripts.js.j2`
- `templates/styles.css.j2`
- `ANTIGRAVITY_HANDOFF.md`
- `docs/DEVELOPMENT_WORKFLOW.md`

### Likely generated and should stay out of normal commits

- `data_raw_primary.json`
- `data_raw_secondary.json`
- `data_verified.json`
- `discussion_board.jsonl`
- `strategy_result.json`
- `persona_stances.jsonl`
- `findings/CommunityAgent.json`
- `findings/FundAgent.json`
- `findings/MacroAgent.json`
- `findings/RiskAgent.json`
- `findings/SectorAgent.json`
- `findings/SentimentAgent.json`
- `findings/TechAgent.json`
- `findings/company_profile_AMD.json`
- `findings/fundamentals_AMD.json`
- `findings/macro.json`
- `learning/intraday_data.db`

### Cleanup candidates

- `run.lock`
- `templates/daily_dashboard.html.j2.bak`

---

## 6. Handoff discipline

Only sessions that are interrupted, handed off, or intentionally paused must append to `ANTIGRAVITY_HANDOFF.md`:

- session goal
- files changed
- commands run
- verification result
- remaining risks
- the exact next recommended step

The next session should be able to continue within five minutes without digging through the entire repository history.
