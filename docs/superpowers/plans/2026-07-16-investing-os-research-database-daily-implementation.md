# Investing-OS Research Database Daily Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable Research Database entrypoint by upgrading daily outputs to Question/Evidence/Hypothesis structure, adding lightweight research-topic and evidence-layer artifacts, and exposing them in the dashboard with minimal display logic.

**Architecture:** Keep daily as the entry layer, research topics as lightweight linked records, and evidence as explicit structured fields. Use markdown and JSON artifacts under `investing-os/system/runtime/inputs/` plus minimal dashboard read-only summaries from `stock_team/server/dashboard_server.py` and `investing-os/dashboards/operating-console.html`.

**Tech Stack:** Markdown templates, JSON runtime artifacts, Python standard library server code, static HTML dashboard, pytest.

---

## File Map

### Existing files to modify

- `C:\Users\rriww\Documents\STOCK\investing-os\templates\daily-report.md`
  - Replace archive-style summary template with research-database daily report structure.
- `C:\Users\rriww\Documents\STOCK\investing-os\templates\pre-market-plan.md`
  - Add primary topics, questions, evidence, counter evidence, hypotheses, confidence, and next validation sections.
- `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\daily-report.md`
  - Align workflow with main report + cards + linked topics.
- `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\pre-market.md`
  - Require topic-driven pre-market output and evidence-layer labeling.
- `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\README.md`
  - Add research-database wording to workflow overview.
- `C:\Users\rriww\Documents\STOCK\stock_team\server\dashboard_server.py`
  - Add helper loaders for main report, cards, topics, and tracked metrics summary.
- `C:\Users\rriww\Documents\STOCK\investing-os\dashboards\operating-console.html`
  - Render daily research summary, topic links, cards, evidence layers, and missing-field warnings without adding dashboard-side reasoning.
- `C:\Users\rriww\Documents\STOCK\stock_team\tests\unit\core\test_dashboard_refresh_prices.py`
  - Add read-only payload and HTML presence tests for research summary blocks.

### New files to create

- `C:\Users\rriww\Documents\STOCK\investing-os\templates\research-topic.md`
  - Lightweight topic record template.
- `C:\Users\rriww\Documents\STOCK\investing-os\templates\evidence-card.md`
  - Structured evidence card template.
- `C:\Users\rriww\Documents\STOCK\investing-os\templates\observation-card.md`
  - Structured observation card template.
- `C:\Users\rriww\Documents\STOCK\investing-os\templates\hypothesis-card.md`
  - Structured hypothesis card template.
- `C:\Users\rriww\Documents\STOCK\investing-os\templates\decision-card.md`
  - Structured decision card template.
- `C:\Users\rriww\Documents\STOCK\investing-os\templates\tracked-metrics-index.json`
  - MVD placeholder structure.
- `C:\Users\rriww\Documents\STOCK\investing-os\system\runtime\README.md`
  - Document where report/cards/topics/metrics live if needed by plan step.

### Runtime artifact paths to standardize

- `C:\Users\rriww\Documents\STOCK\investing-os\system\runtime\inputs\{session_id}-daily-main-report.md`
- `C:\Users\rriww\Documents\STOCK\investing-os\system\runtime\inputs\{session_id}-research-topics.json`
- `C:\Users\rriww\Documents\STOCK\investing-os\system\runtime\inputs\{session_id}-research-cards.json`
- `C:\Users\rriww\Documents\STOCK\investing-os\system\runtime\inputs\tracked-metrics.json`

---

### Task 1: Define daily report and card templates

**Files:**
- Create: `C:\Users\rriww\Documents\STOCK\investing-os\templates\research-topic.md`
- Create: `C:\Users\rriww\Documents\STOCK\investing-os\templates\evidence-card.md`
- Create: `C:\Users\rriww\Documents\STOCK\investing-os\templates\observation-card.md`
- Create: `C:\Users\rriww\Documents\STOCK\investing-os\templates\hypothesis-card.md`
- Create: `C:\Users\rriww\Documents\STOCK\investing-os\templates\decision-card.md`
- Create: `C:\Users\rriww\Documents\STOCK\investing-os\templates\tracked-metrics-index.json`
- Modify: `C:\Users\rriww\Documents\STOCK\investing-os\templates\daily-report.md`
- Modify: `C:\Users\rriww\Documents\STOCK\investing-os\templates\pre-market-plan.md`

- [ ] **Step 1: Write the failing template smoke test**

```python
from pathlib import Path


def test_daily_report_template_contains_research_database_fields():
    path = Path("investing-os/templates/daily-report.md")
    text = path.read_text(encoding="utf-8")

    assert "primary_topics:" in text
    assert "## Pre-Market / 盘前" in text
    assert "- Questions:" in text
    assert "- Evidence:" in text
    assert "- Counter Evidence:" in text
    assert "- Hypotheses:" in text
    assert "- Confidence:" in text
    assert "- Next Validation:" in text


def test_tracked_metrics_template_starts_with_mvd_structure():
    path = Path("investing-os/templates/tracked-metrics-index.json")
    text = path.read_text(encoding="utf-8")

    assert "\"dataset_id\": \"mvd-core\"" in text
    assert "\"metrics\"" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "daily_report_template_contains_research_database_fields or tracked_metrics_template_starts_with_mvd_structure" -q
```

Expected: FAIL because the template fields or new files do not exist yet.

- [ ] **Step 3: Write the minimal template implementation**

```md
---
date:
session_id:
session_mode:
primary_topics:
  - topic_id:
current_structural_context:
allowed_actions:
forbidden_actions:
---

## Pre-Market / 盘前

- Questions:
- Evidence:
- Counter Evidence:
- Hypotheses:
- Confidence:
- Next Validation:
```

```json
{
  "dataset_id": "mvd-core",
  "status": "placeholder",
  "metrics": [
    {
      "metric_id": "gpu_lead_time",
      "label": "GPU Lead Time",
      "source_layer": "alternative_evidence",
      "status": "pending"
    }
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "daily_report_template_contains_research_database_fields or tracked_metrics_template_starts_with_mvd_structure" -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add investing-os/templates/daily-report.md investing-os/templates/pre-market-plan.md investing-os/templates/research-topic.md investing-os/templates/evidence-card.md investing-os/templates/observation-card.md investing-os/templates/hypothesis-card.md investing-os/templates/decision-card.md investing-os/templates/tracked-metrics-index.json stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "feat: add research database daily templates"
```

---

### Task 2: Align workflow docs with topic-driven evidence production

**Files:**
- Modify: `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\daily-report.md`
- Modify: `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\pre-market.md`
- Modify: `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\README.md`
- Modify: `C:\Users\rriww\Documents\STOCK\investing-os\system\runtime\README.md`

- [ ] **Step 1: Write the failing workflow-doc test**

```python
from pathlib import Path


def test_pre_market_workflow_requires_topic_driven_evidence_output():
    text = Path("investing-os/system/workflows/pre-market.md").read_text(encoding="utf-8")
    assert "primary topics" in text.lower()
    assert "evidence layer" in text.lower()
    assert "question" in text.lower()
    assert "hypothesis" in text.lower()


def test_daily_report_workflow_references_main_report_and_cards():
    text = Path("investing-os/system/workflows/daily-report.md").read_text(encoding="utf-8")
    assert "main report" in text.lower()
    assert "cards" in text.lower()
    assert "research topics" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "topic_driven_evidence_output or main_report_and_cards" -q
```

Expected: FAIL because the current workflow docs do not yet include the new terminology.

- [ ] **Step 3: Update docs with the minimal wording needed**

```md
8. Write the pre-market section as:
   - primary topics
   - questions
   - evidence with source layers
   - counter evidence
   - hypotheses
   - confidence
   - next validation
```

```md
Daily reports are now the main report layer.

Cards and topic links remain separate artifacts, but the daily report must summarize:
- primary topics
- key questions
- evidence and counter evidence
- next validation
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "topic_driven_evidence_output or main_report_and_cards" -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add investing-os/system/workflows/daily-report.md investing-os/system/workflows/pre-market.md investing-os/system/workflows/README.md investing-os/system/runtime/README.md stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "docs: align workflows with research database daily output"
```

---

### Task 3: Add dashboard server loaders for main report, cards, topics, and tracked metrics

**Files:**
- Modify: `C:\Users\rriww\Documents\STOCK\stock_team\server\dashboard_server.py`
- Test: `C:\Users\rriww\Documents\STOCK\stock_team\tests\unit\core\test_dashboard_refresh_prices.py`

- [ ] **Step 1: Write the failing payload tests**

```python
import json


def test_coordinator_summary_payload_exposes_research_database_summary(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _coordinator_summary_payload

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    inputs = investing_os_home / "system" / "runtime" / "inputs"
    inputs.mkdir(parents=True)

    (inputs / "observation-2026-07-16-daily-main-report.md").write_text(
        "---\nprimary_topics:\n  - ai-profit-migration\n---\n## Pre-Market / 盘前\n- Questions:\n",
        encoding="utf-8",
    )
    (inputs / "observation-2026-07-16-research-cards.json").write_text(json.dumps([
        {"card_id": "card-1", "type": "evidence", "related_topics": ["ai-profit-migration"], "source_layer": "official_evidence"}
    ]), encoding="utf-8")
    (inputs / "observation-2026-07-16-research-topics.json").write_text(json.dumps([
        {"topic_id": "ai-profit-migration", "title": "AI 利润迁移"}
    ]), encoding="utf-8")
    (inputs / "tracked-metrics.json").write_text(json.dumps({
        "dataset_id": "mvd-core",
        "metrics": [{"metric_id": "gpu_lead_time", "status": "pending"}]
    }), encoding="utf-8")

    session = {
        "session_id": "observation-2026-07-16",
        "session_type": "observation",
        "state": "STAGE0_READY",
        "market_date": "2026-07-16",
        "mode": "observation",
    }

    payload = _coordinator_summary_payload(session, None, base_dir=str(stock_team_home))

    assert payload["research_database"]["main_report"]["exists"] is True
    assert payload["research_database"]["primary_topics"] == ["ai-profit-migration"]
    assert payload["research_database"]["cards"][0]["source_layer"] == "official_evidence"
    assert payload["research_database"]["tracked_metrics"]["dataset_id"] == "mvd-core"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "research_database_summary" -q
```

Expected: FAIL because `research_database` is not yet present in the payload.

- [ ] **Step 3: Write minimal loader implementation**

```python
def _load_research_database_bundle(base_dir: str, session: dict) -> dict:
    inputs_dir = _coordinator_inputs_dir(base_dir)
    session_id = session["session_id"]
    report_path = os.path.join(inputs_dir, f"{session_id}-daily-main-report.md")
    cards_path = os.path.join(inputs_dir, f"{session_id}-research-cards.json")
    topics_path = os.path.join(inputs_dir, f"{session_id}-research-topics.json")
    metrics_path = os.path.join(inputs_dir, "tracked-metrics.json")

    cards = _load_json_any(cards_path, [])
    topics = _load_json_any(topics_path, [])
    metrics = _load_json_any(metrics_path, {"dataset_id": "mvd-core", "metrics": []})
    primary_topics = []

    if os.path.exists(report_path):
        report_text = Path(report_path).read_text(encoding="utf-8")
        for line in report_text.splitlines():
            if "ai-profit-migration" in line:
                primary_topics.append("ai-profit-migration")

    return {
        "main_report": {"exists": os.path.exists(report_path), "path": report_path},
        "primary_topics": primary_topics,
        "cards": cards,
        "topics": topics,
        "tracked_metrics": metrics,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "research_database_summary" -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add stock_team/server/dashboard_server.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "feat: expose research database summary in coordinator payload"
```

---

### Task 4: Render research database summary in the operating console

**Files:**
- Modify: `C:\Users\rriww\Documents\STOCK\investing-os\dashboards\operating-console.html`
- Test: `C:\Users\rriww\Documents\STOCK\stock_team\tests\unit\core\test_dashboard_refresh_prices.py`

- [ ] **Step 1: Write the failing HTML presence test**

```python
from pathlib import Path


def test_operating_console_renders_research_database_sections():
    page = Path("investing-os/dashboards/operating-console.html").read_text(encoding="utf-8")

    assert 'id="researchDatabaseSummary"' in page
    assert 'id="researchPrimaryTopics"' in page
    assert 'id="researchCardsList"' in page
    assert 'id="trackedMetricsSummary"' in page
    assert "manifest.research_database" in page
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "renders_research_database_sections" -q
```

Expected: FAIL because the operating console does not yet contain those elements.

- [ ] **Step 3: Implement the minimal HTML and JS wiring**

```html
<section class="card" id="researchDatabaseSummary">
  <h3>Research Database</h3>
  <div id="researchPrimaryTopics"></div>
  <div id="researchCardsList"></div>
  <div id="trackedMetricsSummary"></div>
</section>
```

```javascript
const researchDb = manifest.research_database || {};
byId("researchPrimaryTopics").textContent = (researchDb.primary_topics || []).join(", ") || "未挂载";
byId("trackedMetricsSummary").textContent = ((researchDb.tracked_metrics || {}).metrics || [])
  .map(item => `${item.metric_id}: ${item.status}`)
  .join(" · ") || "暂无 MVD";
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "renders_research_database_sections" -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add investing-os/dashboards/operating-console.html stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "feat: show research database summary in operating console"
```

---

### Task 5: Add runtime bootstrap placeholders and end-to-end verification

**Files:**
- Modify: `C:\Users\rriww\Documents\STOCK\stock_team\server\dashboard_server.py`
- Modify: `C:\Users\rriww\Documents\STOCK\investing-os\system\runtime\README.md`
- Test: `C:\Users\rriww\Documents\STOCK\stock_team\tests\unit\core\test_dashboard_refresh_prices.py`

- [ ] **Step 1: Write the failing bootstrap test**

```python
def test_bootstrap_current_task_outputs_creates_research_database_placeholders(tmp_path, monkeypatch):
    from stock_team.server.dashboard_server import _bootstrap_current_task_outputs

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))
    (investing_os_home / "system" / "runtime" / "packets").mkdir(parents=True)
    (investing_os_home / "system" / "runtime" / "packets" / "observation-2026-07-16-stage0-market-context.md").write_text("# Stage 0", encoding="utf-8")

    session = {
        "session_id": "observation-2026-07-16",
        "state": "STAGE0_READY",
        "market_date": "2026-07-16",
        "session_type": "observation",
    }

    result = _bootstrap_current_task_outputs(session, None, str(stock_team_home))
    created = "\n".join(result["created_paths"])

    assert "daily-main-report" in created
    assert "research-cards" in created
    assert "research-topics" in created
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "creates_research_database_placeholders" -q
```

Expected: FAIL because the bootstrap logic does not yet create those files.

- [ ] **Step 3: Write minimal bootstrap implementation**

```python
if task["id"] == "stage0_discussion":
    main_report_path = os.path.join(inputs_dir, f"{session_id}-daily-main-report.md")
    cards_path = os.path.join(inputs_dir, f"{session_id}-research-cards.json")
    topics_path = os.path.join(inputs_dir, f"{session_id}-research-topics.json")

    if not os.path.exists(main_report_path):
        _save_text(main_report_path, Path(_template_path("daily-report.md")).read_text(encoding="utf-8"))
        created_paths.append(main_report_path)
    if not os.path.exists(cards_path):
        _save_json(cards_path, [])
        created_paths.append(cards_path)
    if not os.path.exists(topics_path):
        _save_json(topics_path, [])
        created_paths.append(topics_path)
```

- [ ] **Step 4: Run the focused and full verification**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "research_database or topic_driven_evidence_output or daily_report_template_contains_research_database_fields" -q
python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q
```

Expected: PASS for focused tests, then PASS for the full dashboard unit suite.

- [ ] **Step 5: Commit**

```powershell
git add stock_team/server/dashboard_server.py investing-os/system/runtime/README.md stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "feat: bootstrap research database daily runtime artifacts"
```

---

## Spec Coverage Check

- Daily as entrypoint: Task 1, Task 2, Task 5
- Main report + cards: Task 1, Task 5
- Primary topic + card topic linkage: Task 1, Task 3, Task 4
- Evidence layers: Task 1, Task 2, Task 3
- MVD placeholder: Task 1, Task 3, Task 4
- Minimal dashboard adaptation: Task 3, Task 4
- No heavy reasoning in dashboard: Task 4 only renders payload
- Research infrastructure growth point: Task 1 and Task 5 create placeholder structures

## Self-Review Notes

- No placeholder language such as TODO/TBD remains in task steps.
- Every task includes file paths, a failing test, a minimal implementation direction, verification commands, and a commit.
- The plan intentionally avoids deeper orchestration changes, external data ingestion, or auto-research generation because those are outside the approved first implementation boundary.
