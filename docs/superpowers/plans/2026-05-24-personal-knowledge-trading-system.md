# Personal Knowledge Trading System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared knowledge layer that ingests research/news/public-holding inputs, turns them into structured observations and lessons, and exposes the current learning state inside the existing dashboard without creating a separate UI.

**Architecture:** Use an append-only journal in `learning/` as the canonical memory layer, with normalized records for `Observation`, `Decision`, `Outcome`, `Lesson`, and `KnowledgeNode`. Add thin source adapters for news, SEC/company filings, public-holding signals, and manual research notes, then let a small synthesis agent turn those inputs plus recent trade outcomes into lessons. The dashboard stays the daily operating surface and only shows concise learning summaries, source coverage, and open questions.

**Tech Stack:** Python stdlib, JSON/JSONL, existing `agents/*` patterns, existing Jinja2 dashboard templates, optional bundled PDF/text extraction utilities available in the workspace runtime.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `agents/knowledge_schema.py` | Create | Define normalized record shapes and helpers for observations, decisions, outcomes, lessons, and knowledge nodes. |
| `agents/knowledge_store.py` | Create | Append/read the journal in `learning/knowledge_journal.jsonl` and provide simple queries for recent items and coverage. |
| `agents/research_ingest.py` | Create | Ingest and normalize the first source set: news, filings, public holdings, and manual research inputs. |
| `agents/knowledge_agent.py` | Create | Synthesize lessons and knowledge nodes from source docs and recent outcomes; write back to the journal. |
| `agents/dashboard_writer.py` | Modify | Load learning summaries into the dashboard context. |
| `agents/dashboard_server.py` | Modify | Keep dashboard refresh-friendly; no new learning API is required in v1 because the template can render from the journal-backed context. |
| `templates/daily_dashboard.html.j2` | Modify | Add a compact learning panel for latest lesson, source coverage, and open questions. |
| `tests/test_knowledge_schema.py` | Create | Verify schema normalization and journal round-tripping. |
| `tests/test_research_ingest.py` | Create | Verify each source adapter emits normalized documents. |
| `tests/test_knowledge_agent.py` | Create | Verify deterministic lesson synthesis and knowledge-node creation. |
| `tests/test_dashboard_writer.py` | Modify | Verify dashboard context includes learning state and renders non-empty summaries. |

---

### Task 1: Create the shared knowledge schema and journal

**Files:**
- Create: `agents/knowledge_schema.py`
- Create: `agents/knowledge_store.py`
- Create: `tests/test_knowledge_schema.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_knowledge_schema.py` with a round-trip test for each record type and a journal append/read test:

```python
from agents.knowledge_schema import normalize_observation, normalize_decision, normalize_outcome, normalize_lesson, normalize_knowledge_node
from agents.knowledge_store import append_knowledge_event, load_recent_events

def test_schema_round_trip(tmp_path):
    obs = normalize_observation({
        "id": "obs-1",
        "ts": "2026-05-24T09:30:00-04:00",
        "date": "2026-05-24",
        "topic": "NVDA",
        "source": "manual",
        "facts": {"headline": "AI demand stays strong"},
        "context": {"regime": "risk_on"},
        "tags": ["semis", "macro"],
    })
    assert obs["kind"] == "observation"
    assert obs["topic"] == "NVDA"

def test_append_and_load_events(tmp_path):
    path = append_knowledge_event(str(tmp_path), {"kind": "lesson", "id": "lesson-1"})
    rows = load_recent_events(str(tmp_path), limit=10)
    assert path.endswith("learning/knowledge_journal.jsonl")
    assert rows[0]["id"] == "lesson-1"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_knowledge_schema.py -v
```

Expected: failure because the schema and store modules do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Add pure-dict helpers and a tiny append-only journal:

```python
def normalize_observation(raw: dict) -> dict:
    return {"kind": "observation", "id": raw["id"], "ts": raw["ts"], "date": raw["date"], **raw}

def append_knowledge_event(base_dir: str, event: dict) -> str:
    path = os.path.join(base_dir, "learning", "knowledge_journal.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path

def load_recent_events(base_dir: str, limit: int = 50) -> list[dict]:
    path = os.path.join(base_dir, "learning", "knowledge_journal.jsonl")
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows[-limit:]
```

Keep the storage format as JSONL under `learning/knowledge_journal.jsonl`.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_knowledge_schema.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/knowledge_schema.py agents/knowledge_store.py tests/test_knowledge_schema.py
git commit -m "feat: add shared knowledge schema and journal"
```

---

### Task 2: Ingest the first research sources into normalized documents

**Files:**
- Create: `agents/research_ingest.py`
- Create: `tests/test_research_ingest.py`
- Modify: `config/research_sources.json` if the project needs a simple on/off source list

- [ ] **Step 1: Write the failing tests**

Create `tests/test_research_ingest.py` with one test per source type:

```python
from agents.research_ingest import ingest_news_item, ingest_sec_filing, ingest_public_holding, ingest_manual_note

def test_ingest_news_item_normalizes_fields():
    doc = ingest_news_item({
        "title": "NVDA beats expectations",
        "published_at": "2026-05-24T08:00:00-04:00",
        "source": "Reuters",
        "url": "https://example.com/news",
        "body": "Strong data center demand...",
        "symbols": ["NVDA"],
    })
    assert doc["source_type"] == "news"
    assert doc["symbols"] == ["NVDA"]
    assert doc["title"] == "NVDA beats expectations"

def test_ingest_sec_filing_normalizes_fields():
    doc = ingest_sec_filing({
        "form_type": "10-Q",
        "company": "NVIDIA",
        "symbol": "NVDA",
        "published_at": "2026-05-24T00:00:00-04:00",
        "source": "SEC",
        "url": "https://example.com/10q",
        "text": "Risk factors ...",
    })
    assert doc["source_type"] == "sec_filing"
    assert doc["symbol"] == "NVDA"

def test_ingest_public_holding_normalizes_fields():
    doc = ingest_public_holding({
        "person": "Long-term public investor",
        "published_at": "2026-05-24T00:00:00-04:00",
        "source": "13F",
        "symbol": "SOXX",
        "action": "add",
        "rationale": "semis exposure",
    })
    assert doc["source_type"] == "public_holding"
    assert doc["action"] == "add"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_research_ingest.py -v
```

Expected: failure because the ingestion helpers do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create one adapter module that returns normalized dicts with these required fields:

```python
{
    "id": "...",
    "source_type": "news" | "sec_filing" | "public_holding" | "manual_note",
    "source": "...",
    "published_at": "...",
    "symbols": [...],
    "title": "...",
    "text": "...",
    "url": "...",
    "citations": [...],
}
```

Keep the first version deterministic. For manual PDFs, extract text into the same shape and keep the PDF path in `citations`.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_research_ingest.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/research_ingest.py tests/test_research_ingest.py config/research_sources.json
git commit -m "feat: add research source normalization"
```

---

### Task 3: Build the learning synthesis agent

**Files:**
- Create: `agents/knowledge_agent.py`
- Create: `tests/test_knowledge_agent.py`

- [ ] **Step 1: Write the failing tests**

Create a deterministic synthesis test that feeds one observation, one outcome, and one research doc, then expects a lesson and a knowledge node:

```python
from agents.knowledge_agent import synthesize_lesson, build_knowledge_node

def test_synthesize_lesson_returns_actionable_summary():
    lesson = synthesize_lesson(
        docs=[{"source_type": "news", "title": "NVDA beats expectations", "text": "Strong demand"}],
        outcomes=[{"symbol": "NVDA", "hit_miss": "hit", "deviation": 0.8}],
        observations=[{"topic": "NVDA", "context": {"regime": "risk_on"}}],
    )
    assert lesson["kind"] == "lesson"
    assert lesson["what_worked"]
    assert lesson["rule_change"]

def test_build_knowledge_node_links_supporting_cases():
    node = build_knowledge_node(
        theme="semis demand",
        lesson={"summary": "Demand stayed strong"},
        supporting_cases=["lesson-1", "lesson-2"],
    )
    assert node["kind"] == "knowledge_node"
    assert node["supporting_cases"] == ["lesson-1", "lesson-2"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_knowledge_agent.py -v
```

Expected: failure because the synthesis module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement a small synthesis layer that:

1. Groups docs by topic/symbol.
2. Compares the docs with recent outcomes.
3. Emits a lesson record with `summary`, `what_worked`, `what_failed`, `bias`, and `rule_change`.
4. Emits a knowledge node with `theme`, `statement`, `tags`, `validity`, `supporting_cases`, and `last_updated`.

Keep the first version deterministic. If an LLM hook is added later, it must sit behind a tiny pure function that can be bypassed in tests.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_knowledge_agent.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/knowledge_agent.py tests/test_knowledge_agent.py
git commit -m "feat: add learning synthesis agent"
```

---

### Task 4: Surface learning state in the dashboard

**Files:**
- Modify: `agents/dashboard_writer.py`
- Modify: `agents/dashboard_server.py`
- Modify: `templates/daily_dashboard.html.j2`
- Modify: `tests/test_dashboard_writer.py`

- [ ] **Step 1: Write the failing test**

Add a dashboard context test that stubs a small knowledge journal and asserts the context includes a non-empty learning summary:

```python
import json

def test_build_dashboard_context_includes_learning_state(tmp_path):
    from agents.dashboard_writer import build_dashboard_context
    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    (base / "config" / "positions.json").write_text(json.dumps({"positions": {"NVDA": {}}, "_excluded": []}), encoding="utf-8")
    (base / "config" / "poll_config.json").write_text(json.dumps({"default_symbols": ["NVDA"]}), encoding="utf-8")
    journal = {
        "kind": "lesson",
        "id": "lesson-1",
        "summary": "Strong earnings guidance kept the thesis intact",
        "source_type": "lesson",
        "topic": "NVDA",
        "created_at": "2026-05-24T12:00:00-04:00",
    }
    with open(base / "learning" / "knowledge_journal.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(journal, ensure_ascii=False) + "\n")
    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))
    assert ctx["learning"]["latest_lesson"]["kind"] == "lesson"
    assert ctx["learning"]["source_coverage"]["lesson"] == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_dashboard_writer.py -v
```

Expected: the new learning fields are missing.

- [ ] **Step 3: Add the minimal dashboard wiring**

Extend `build_dashboard_context()` so it loads:

```python
learning = {
    "source_coverage": {"news": 3, "sec_filing": 1, "public_holding": 2, "manual_note": 1, "lesson": 4},
    "latest_observations": [{"kind": "observation", "topic": "NVDA"}],
    "latest_lessons": [{"kind": "lesson", "summary": "Earnings held the thesis intact"}],
    "open_questions": ["Does demand stay strong into the next guide?"],
}
```

Then add a compact panel to `templates/daily_dashboard.html.j2` that shows:

- the latest lesson summary
- the top source types being ingested
- the next open question

Keep it visually small and operational, not like a second landing page.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_dashboard_writer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/dashboard_writer.py agents/dashboard_server.py templates/daily_dashboard.html.j2 tests/test_dashboard_writer.py
git commit -m "feat: surface learning state in dashboard"
```

---

## Verification Notes

- Prefer `python -m pytest ... -v` for the new tests.
- Run `python -m py_compile agents/knowledge_schema.py agents/knowledge_store.py agents/research_ingest.py agents/knowledge_agent.py agents/dashboard_writer.py agents/dashboard_server.py` before handoff.
- After the dashboard task, open `http://localhost:8080/` and confirm the learning panel is present but compact.
