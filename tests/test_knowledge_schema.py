import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.knowledge_schema import (
    normalize_decision,
    normalize_knowledge_node,
    normalize_lesson,
    normalize_observation,
    normalize_outcome,
)
from agents.knowledge_store import append_knowledge_event, load_recent_events


def test_normalize_observation_preserves_fields():
    raw = {
        "id": "obs-1",
        "ts": "2026-05-24T09:30:00-04:00",
        "date": "2026-05-24",
        "topic": "NVDA",
        "source": "manual",
        "facts": {"headline": "AI demand stays strong"},
        "context": {"regime": "risk_on"},
        "tags": ["semis", "macro"],
        "priority": 2,
    }

    obs = normalize_observation(raw)

    assert obs["kind"] == "observation"
    assert obs["id"] == "obs-1"
    assert obs["topic"] == "NVDA"
    assert obs["priority"] == 2
    assert obs["tags"] == ["semis", "macro"]


def test_normalize_decision_preserves_fields():
    raw = {
        "id": "dec-1",
        "ts": "2026-05-24T09:31:00-04:00",
        "date": "2026-05-24",
        "symbol": "NVDA",
        "action": "buy",
        "rationale": "Breakout with volume",
        "confidence": 0.78,
        "tags": ["entry"],
    }

    decision = normalize_decision(raw)

    assert decision["kind"] == "decision"
    assert decision["symbol"] == "NVDA"
    assert decision["action"] == "buy"
    assert decision["confidence"] == 0.78


def test_normalize_outcome_preserves_fields():
    raw = {
        "id": "out-1",
        "ts": "2026-05-24T16:00:00-04:00",
        "date": "2026-05-24",
        "symbol": "NVDA",
        "result": "win",
        "pnl_pct": 3.4,
        "notes": "Held trend into close",
    }

    outcome = normalize_outcome(raw)

    assert outcome["kind"] == "outcome"
    assert outcome["symbol"] == "NVDA"
    assert outcome["result"] == "win"
    assert outcome["pnl_pct"] == 3.4


def test_normalize_lesson_preserves_fields():
    raw = {
        "id": "les-1",
        "ts": "2026-05-24T18:00:00-04:00",
        "date": "2026-05-24",
        "summary": "Wait for confirmation after opening range",
        "what_worked": ["Patience"],
        "what_failed": ["Chasing strength"],
        "bias": "impulsive",
        "rule_change": "Require opening range confirmation",
        "tags": ["execution"],
    }

    lesson = normalize_lesson(raw)

    assert lesson["kind"] == "lesson"
    assert lesson["summary"] == "Wait for confirmation after opening range"
    assert lesson["bias"] == "impulsive"
    assert lesson["rule_change"] == "Require opening range confirmation"


def test_normalize_knowledge_node_preserves_fields():
    raw = {
        "id": "node-1",
        "ts": "2026-05-24T18:05:00-04:00",
        "date": "2026-05-24",
        "theme": "semis demand",
        "statement": "Demand remained resilient",
        "supporting_cases": ["les-1", "les-2"],
        "tags": ["NVDA", "AI"],
        "confidence": 0.9,
    }

    node = normalize_knowledge_node(raw)

    assert node["kind"] == "knowledge_node"
    assert node["theme"] == "semis demand"
    assert node["supporting_cases"] == ["les-1", "les-2"]
    assert node["confidence"] == 0.9


def test_append_and_load_events_round_trip(tmp_path):
    events = [
        normalize_observation(
            {
                "id": "obs-1",
                "ts": "2026-05-24T09:30:00-04:00",
                "date": "2026-05-24",
                "topic": "NVDA",
                "source": "manual",
                "facts": {"headline": "AI demand stays strong"},
            }
        ),
        normalize_lesson(
            {
                "id": "les-1",
                "ts": "2026-05-24T18:00:00-04:00",
                "date": "2026-05-24",
                "summary": "Wait for confirmation after opening range",
                "what_worked": ["Patience"],
                "what_failed": ["Chasing strength"],
                "bias": "impulsive",
                "rule_change": "Require opening range confirmation",
            }
        ),
        normalize_decision(
            {
                "id": "dec-1",
                "ts": "2026-05-24T09:31:00-04:00",
                "date": "2026-05-24",
                "symbol": "NVDA",
                "action": "buy",
                "rationale": "Breakout with volume",
            }
        ),
        normalize_outcome(
            {
                "id": "out-1",
                "ts": "2026-05-24T16:00:00-04:00",
                "date": "2026-05-24",
                "symbol": "NVDA",
                "result": "win",
                "pnl_pct": 3.4,
            }
        ),
        normalize_knowledge_node(
            {
                "id": "node-1",
                "ts": "2026-05-24T18:05:00-04:00",
                "date": "2026-05-24",
                "theme": "semis demand",
                "statement": "Demand remained resilient",
                "supporting_cases": ["les-1"],
            }
        ),
    ]

    for event in events:
        path = append_knowledge_event(str(tmp_path), event)

    assert path.endswith(os.path.join("learning", "knowledge_journal.jsonl"))
    assert os.path.exists(path)

    rows = load_recent_events(str(tmp_path), limit=10)
    assert [row["id"] for row in rows] == ["obs-1", "les-1", "dec-1", "out-1", "node-1"]
    assert rows[0]["kind"] == "observation"
    assert rows[1]["kind"] == "lesson"
    assert rows[2]["kind"] == "decision"
    assert rows[3]["kind"] == "outcome"
    assert rows[4]["kind"] == "knowledge_node"


def test_load_recent_events_skips_malformed_trailing_line(tmp_path):
    path = os.path.join(str(tmp_path), "learning", "knowledge_journal.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "observation", "id": "obs-1"}, ensure_ascii=False) + "\n")
        f.write('{"kind": "lesson", "id": "les-1"}\n')
        f.write('{"kind": "knowledge_node", "id": "node-1"}\n')
        f.write('{"kind": "outcome", "id": "out-1"}\n')
        f.write('{"kind": "decision", "id": "dec-1"}\n')
        f.write('{"kind": "lesson", "id": "bad-1"\n')

    rows = load_recent_events(str(tmp_path), limit=10)
    assert [row["id"] for row in rows] == ["obs-1", "les-1", "node-1", "out-1", "dec-1"]


def test_load_recent_events_skips_non_dict_json_values(tmp_path):
    path = os.path.join(str(tmp_path), "learning", "knowledge_journal.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "observation", "id": "obs-1"}, ensure_ascii=False) + "\n")
        f.write("null\n")
        f.write("[]\n")
        f.write(json.dumps({"kind": "lesson", "id": "les-1"}, ensure_ascii=False) + "\n")

    rows = load_recent_events(str(tmp_path), limit=10)
    assert [row["id"] for row in rows] == ["obs-1", "les-1"]


def test_load_recent_events_skips_middle_malformed_line_and_keeps_later_rows(tmp_path):
    path = os.path.join(str(tmp_path), "learning", "knowledge_journal.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "observation", "id": "obs-1"}, ensure_ascii=False) + "\n")
        f.write('{"kind": "lesson", "id": "les-1"}\n')
        f.write('{"kind": "knowledge_node", "id": "bad-1"\n')
        f.write(json.dumps({"kind": "decision", "id": "dec-1"}, ensure_ascii=False) + "\n")
        f.write(json.dumps({"kind": "outcome", "id": "out-1"}, ensure_ascii=False) + "\n")

    rows = load_recent_events(str(tmp_path), limit=10)
    assert [row["id"] for row in rows] == ["obs-1", "les-1", "dec-1", "out-1"]


def test_load_recent_events_empty_journal_returns_empty_list(tmp_path):
    path = os.path.join(str(tmp_path), "learning", "knowledge_journal.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").close()

    assert load_recent_events(str(tmp_path), limit=10) == []


def test_load_recent_events_limit_zero_or_negative_returns_empty_list(tmp_path):
    append_knowledge_event(
        str(tmp_path),
        {
            "kind": "observation",
            "id": "obs-1",
            "ts": "2026-05-24T09:30:00-04:00",
            "date": "2026-05-24",
            "topic": "NVDA",
        },
    )

    assert load_recent_events(str(tmp_path), limit=0) == []
    assert load_recent_events(str(tmp_path), limit=-3) == []


def test_load_recent_events_honors_limit(tmp_path):
    for idx in range(3):
        append_knowledge_event(
            str(tmp_path),
            {
                "kind": "observation",
                "id": f"obs-{idx}",
                "ts": f"2026-05-24T09:3{idx}:00-04:00",
                "date": "2026-05-24",
                "topic": "NVDA",
            },
        )

    rows = load_recent_events(str(tmp_path), limit=2)
    assert [row["id"] for row in rows] == ["obs-1", "obs-2"]
