import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_rebuild_knowledge_index_counts_all_time_and_latest_questions(tmp_path):
    from agents.knowledge_index import rebuild_knowledge_index

    journal = tmp_path / "learning" / "knowledge_journal.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    with open(journal, "w", encoding="utf-8") as f:
        for idx in range(60):
            f.write(json.dumps({
                "kind": "observation",
                "id": f"obs-{idx}",
                "ts": f"2026-05-24T09:{idx:02d}:00-04:00",
                "date": "2026-05-24",
                "topic": "NVDA",
                "summary": f"Observation {idx}",
                "question": f"Question {idx}",
            }, ensure_ascii=False) + "\n")
        f.write(json.dumps({
            "kind": "lesson",
            "id": "les-1",
            "ts": "2026-05-24T18:00:00-04:00",
            "date": "2026-05-24",
            "summary": "Keep requiring confirmation before committing.",
            "what_worked": ["Confirmation and patience improved the result."],
            "what_failed": ["Impulsive or unconfirmed execution weakened the setup."],
            "open_questions": [
                "Does confirmation still help in high-VIX sessions?",
                "Should we size down after gap-ups?",
            ],
        }, ensure_ascii=False) + "\n")

    index = rebuild_knowledge_index(str(tmp_path))

    assert index["scope"] == "all_time"
    assert index["source_coverage"]["observation"] == 60
    assert index["source_coverage"]["lesson"] == 1
    assert index["latest_observations"][0]["id"] == "obs-59"
    assert index["latest_lessons"][0]["id"] == "les-1"
    assert index["open_questions"][:3] == [
        "Should we size down after gap-ups?",
        "Does confirmation still help in high-VIX sessions?",
        "Question 59",
    ]
    assert len(index["open_questions"]) == 5


def test_append_knowledge_event_updates_index_and_dashboard_reads_all_time(tmp_path):
    from agents.dashboard_writer import build_dashboard_context
    from agents.knowledge_index import load_knowledge_index
    from agents.knowledge_schema import normalize_lesson
    from agents.knowledge_store import append_knowledge_event

    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    _write(str(base / "config" / "positions.json"), {"positions": {}, "_excluded": []})
    _write(str(base / "config" / "poll_config.json"), {"default_symbols": []})

    for idx in range(55):
        append_knowledge_event(
            str(base),
            {
                "kind": "observation",
                "id": f"obs-{idx}",
                "ts": f"2026-05-24T09:{idx:02d}:00-04:00",
                "date": "2026-05-24",
                "topic": "NVDA",
                "summary": f"Observation {idx}",
            },
        )

    append_knowledge_event(
        str(base),
        normalize_lesson({
            "id": "les-2",
            "ts": "2026-05-24T18:05:00-04:00",
            "date": "2026-05-24",
            "summary": "Confirmation and patience improved the result.",
            "what_worked": ["Confirmation"],
            "what_failed": ["Impulsive entries"],
            "open_questions": ["Does confirmation still help in high-VIX sessions?"],
        }),
    )

    index = load_knowledge_index(str(base))
    ctx = build_dashboard_context("2026-05-24", symbols=["NVDA"], base_dir=str(base))

    assert index["source_coverage"]["observation"] == 55
    assert index["source_coverage"]["lesson"] == 1
    assert index["latest_lessons"][0]["id"] == "les-2"
    assert index["scope"] == "all_time"
    assert ctx["learning"]["scope"] == "all_time"
    assert ctx["learning"]["source_coverage"]["observation"] == 55
    assert ctx["learning"]["latest_lessons"][0]["id"] == "les-2"
