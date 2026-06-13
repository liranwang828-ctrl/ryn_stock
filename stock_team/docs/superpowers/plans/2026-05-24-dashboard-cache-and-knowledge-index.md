# Dashboard Cache and Full Knowledge Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the dashboard useful when polling is idle by reading a local cache of the last successful operational snapshot, and make learning summaries reflect the full knowledge journal through a derived all-time index.

**Architecture:** Add a small cache file in `learning/dashboard_cache.json` that `poll.py` writes after each successful tick and `dashboard_writer.py` reads first when assembling the page. Keep `learning/knowledge_journal.jsonl` as the source of truth for all learning records, and maintain a derived `learning/knowledge_index.json` so dashboard summaries can show all-time counts and recent highlights without rescanning the journal on every render. The dashboard remains read-heavy; cache and index maintenance happen on the write path.

**Tech Stack:** Python stdlib, JSON/JSONL, existing `agents/*` patterns, existing Jinja2 dashboard templates, pytest.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `agents/dashboard_cache.py` | Create | Read/write `learning/dashboard_cache.json` and provide a compact API for the latest operational snapshot. |
| `agents/knowledge_index.py` | Create | Build and load the all-time learning index from `learning/knowledge_journal.jsonl`. |
| `agents/poll.py` | Modify | Write dashboard cache after a successful poll tick. |
| `agents/dashboard_writer.py` | Modify | Read dashboard cache first for operational state and read the knowledge index for learning state. |
| `agents/knowledge_store.py` | Modify | Add a full-journal read helper and update the knowledge index when appending a new record. |
| `templates/daily_dashboard.html.j2` | Modify | Show the compact cache-driven operational state and label the learning panel as all-time. |
| `tests/test_dashboard_cache.py` | Create | Verify cache round-trip and dashboard fallback when poll has not run. |
| `tests/test_knowledge_index.py` | Create | Verify full index rebuild and incremental index updates. |
| `tests/test_dashboard_writer.py` | Modify | Verify the dashboard consumes cache state and all-time learning counts. |

---

### Task 1: Add the dashboard cache layer

**Files:**
- Create: `agents/dashboard_cache.py`
- Modify: `agents/poll.py`
- Modify: `agents/dashboard_writer.py`
- Create: `tests/test_dashboard_cache.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dashboard_cache.py` with one test for the cache file and one test for dashboard fallback when findings files are absent:

```python
import os

def test_dashboard_cache_round_trip(tmp_path):
    from agents.dashboard_cache import load_dashboard_cache, write_dashboard_cache

    payload = {
        "date": "2026-05-24",
        "generated_at": "2026-05-24T10:00:00-04:00",
        "market_clock": {"phase": "rest_day", "phase_label": "休息日"},
        "intraday": {"NVDA": {"price_now": {"price": 220.0, "gate_status": "通过"}}},
        "sector_snaps": {"SOXX": 3.0},
    }

    path = write_dashboard_cache(str(tmp_path), payload)
    loaded = load_dashboard_cache(str(tmp_path))

    assert path.endswith(os.path.join("learning", "dashboard_cache.json"))
    assert loaded["market_clock"]["phase"] == "rest_day"
    assert loaded["intraday"]["NVDA"]["price_now"]["price"] == 220.0
    assert loaded["sector_snaps"]["SOXX"] == 3.0


def test_dashboard_context_uses_cache_when_findings_are_missing(tmp_path):
    from agents.dashboard_cache import write_dashboard_cache
    from agents.dashboard_writer import build_dashboard_context

    (tmp_path / "learning").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "positions.json").write_text("{\"positions\": {}, \"_excluded\": []}", encoding="utf-8")
    (tmp_path / "config" / "poll_config.json").write_text("{\"default_symbols\": []}", encoding="utf-8")

    write_dashboard_cache(str(tmp_path), {
        "date": "2026-05-24",
        "generated_at": "2026-05-24T10:00:00-04:00",
        "market_clock": {"phase": "rest_day", "phase_label": "休息日"},
        "intraday": {
            "NVDA": {
                "price_now": {"price": 220.0, "gate_status": "通过", "master_avg": 6.0, "master_consensus": "buy"},
                "plan_vs_now": {"entry_go_status": "pending"},
            }
        },
        "sector_snaps": {"SOXX": 3.0},
    })

    ctx = build_dashboard_context("2026-05-24", symbols=["NVDA"], base_dir=str(tmp_path))

    assert ctx["intraday"]["NVDA"]["price_now"]["price"] == 220.0
    assert ctx["intraday"]["NVDA"]["plan_vs_now"]["entry_go_status"] == "pending"
    assert ctx["market_clock"]["phase"] == "rest_day"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_dashboard_cache.py -v
```

Expected: failure because the cache module and fallback wiring do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Add a small cache module and wire it into poll/render:

```python
def write_dashboard_cache(base_dir: str, payload: dict) -> str:
    path = os.path.join(base_dir, "learning", "dashboard_cache.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def load_dashboard_cache(base_dir: str) -> dict:
    path = os.path.join(base_dir, "learning", "dashboard_cache.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
```

In `agents/poll.py`, write the cache after the tick finishes:

```python
from agents.dashboard_cache import write_dashboard_cache

write_dashboard_cache(BASE, {
    "date": _snap_date,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "market_clock": _market_clock_dict,
    "intraday": snap_data,
    "sector_snaps": sector_snaps,
    "focus_symbols": list(stocks.keys()),
})
```

In `agents/dashboard_writer.py`, read the cache before assembling the final context and use it to backfill missing `market_clock`, `intraday`, and `sector_snaps` when current findings are absent.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_dashboard_cache.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/dashboard_cache.py agents/poll.py agents/dashboard_writer.py tests/test_dashboard_cache.py
git commit -m "feat: add dashboard cache for last successful poll state"
```

---

### Task 2: Build the full knowledge index

**Files:**
- Create: `agents/knowledge_index.py`
- Modify: `agents/knowledge_store.py`
- Modify: `agents/dashboard_writer.py`
- Create: `tests/test_knowledge_index.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_knowledge_index.py` with two tests: one for full rebuild from the journal and one for incremental update after append.

```python
def test_rebuild_knowledge_index_counts_all_records(tmp_path):
    from agents.knowledge_index import rebuild_knowledge_index

    journal = tmp_path / "learning" / "knowledge_journal.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    with open(journal, "w", encoding="utf-8") as f:
        for i in range(60):
            f.write(f'{{"kind":"observation","id":"obs-{i}","ts":"2026-05-24T09:{i:02d}:00-04:00","date":"2026-05-24","topic":"NVDA"}}\n')
        f.write('{"kind":"lesson","id":"les-1","ts":"2026-05-24T18:00:00-04:00","date":"2026-05-24","summary":"Keep requiring confirmation before committing."}\n')

    index = rebuild_knowledge_index(str(tmp_path))

    assert index["source_coverage"]["observation"] == 60
    assert index["source_coverage"]["lesson"] == 1
    assert index["scope"] == "all_time"


def test_append_knowledge_event_updates_index(tmp_path):
    from agents.knowledge_store import append_knowledge_event
    from agents.knowledge_index import load_knowledge_index

    append_knowledge_event(str(tmp_path), {
        "kind": "lesson",
        "id": "les-2",
        "ts": "2026-05-24T18:05:00-04:00",
        "date": "2026-05-24",
        "summary": "Confirmation and patience improved the result.",
        "what_worked": ["Confirmation"],
        "what_failed": ["Impulsive entries"],
    })

    index = load_knowledge_index(str(tmp_path))

    assert index["source_coverage"]["lesson"] == 1
    assert index["latest_lessons"][0]["id"] == "les-2"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_knowledge_index.py -v
```

Expected: failure because the index module and update path do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Add a full-journal indexer and keep it in sync when new records are appended:

```python
def load_all_events(base_dir: str) -> list[dict[str, Any]]:
    path = os.path.join(base_dir, "learning", "knowledge_journal.jsonl")
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows
```

```python
def rebuild_knowledge_index(base_dir: str) -> dict:
    rows = load_all_events(base_dir)
    # aggregate counts, latest items, and open questions across the full journal
```

```python
def load_knowledge_index(base_dir: str) -> dict:
    path = os.path.join(base_dir, "learning", "knowledge_index.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return rebuild_knowledge_index(base_dir)
```

In `agents/knowledge_store.py`, update `append_knowledge_event()` so that each append also updates the derived index file by calling `update_knowledge_index_from_event(base_dir, event)` in `agents.knowledge_index`.

In `agents/dashboard_writer.py`, stop using the 50-row learning window for the panel and read the all-time index instead.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_knowledge_index.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/knowledge_index.py agents/knowledge_store.py agents/dashboard_writer.py tests/test_knowledge_index.py
git commit -m "feat: add all-time knowledge index"
```

---

### Task 3: Surface the cached operational state and all-time learning view in the dashboard

**Files:**
- Modify: `agents/dashboard_writer.py`
- Modify: `templates/daily_dashboard.html.j2`
- Modify: `tests/test_dashboard_writer.py`

- [ ] **Step 1: Write the failing test**

Add a dashboard regression test that proves the learning panel reads the all-time index rather than just a recent window:

```python
def test_build_dashboard_context_uses_all_time_knowledge_index(tmp_path):
    from agents.dashboard_writer import build_dashboard_context
    from agents.knowledge_index import rebuild_knowledge_index

    (tmp_path / "learning").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "positions.json").write_text("{\"positions\": {}, \"_excluded\": []}", encoding="utf-8")
    (tmp_path / "config" / "poll_config.json").write_text("{\"default_symbols\": []}", encoding="utf-8")

    journal = tmp_path / "learning" / "knowledge_journal.jsonl"
    with open(journal, "w", encoding="utf-8") as f:
        for i in range(60):
            f.write(f'{{"kind":"observation","id":"obs-{i}","ts":"2026-05-24T09:{i:02d}:00-04:00","date":"2026-05-24","topic":"NVDA"}}\n')
    rebuild_knowledge_index(str(tmp_path))

    ctx = build_dashboard_context("2026-05-24", symbols=["NVDA"], base_dir=str(tmp_path))

    assert ctx["learning"]["scope"] == "all_time"
    assert ctx["learning"]["source_coverage"]["observation"] == 60
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_dashboard_writer.py -v
```

Expected: the new learning scope and all-time counts are missing until the index wiring is in place.

- [ ] **Step 3: Add the minimal dashboard wiring**

Update `build_dashboard_context()` so it merges the cache and index into the existing context:

```python
dashboard_cache = load_dashboard_cache(base_dir)
learning_index = load_knowledge_index(base_dir)

market_clock = market_clock or dashboard_cache.get("market_clock", {})
for sym, rec in (dashboard_cache.get("intraday") or {}).items():
    intraday.setdefault(sym, rec)

learning_state = dict(learning_index)
learning_state["scope"] = "all_time"
learning_state["cache_updated_at"] = dashboard_cache.get("generated_at")
```

In `templates/daily_dashboard.html.j2`, show a compact label that makes the learning panel explicit about scope:

```jinja2
<span class="badge badge-blue" style="font-size:0.72rem; padding:2px 8px;">全量知识库</span>
```

Keep the rest of the panel small and operational: latest lesson summary, all-time source coverage, and the top open question.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_dashboard_writer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/dashboard_writer.py templates/daily_dashboard.html.j2 tests/test_dashboard_writer.py
git commit -m "feat: make dashboard read cache and all-time knowledge index"
```

---

## Verification Notes

- Prefer `python -m pytest tests/test_dashboard_cache.py tests/test_knowledge_index.py tests/test_dashboard_writer.py -v` for the new coverage.
- Run `python -m py_compile agents/dashboard_cache.py agents/knowledge_index.py agents/knowledge_store.py agents/dashboard_writer.py agents/poll.py` before handoff.
- After the dashboard task, open `http://localhost:8080/` and confirm the dashboard still renders when no fresh poll has happened, and the learning panel shows all-time counts instead of a 50-row window.

