import os
import sys

from agents.knowledge_agent import build_knowledge_node, synthesize_lesson


def test_synthesize_lesson_returns_actionable_lesson():
    docs = [
        {
            "title": "Confirm before committing",
            "text": "The setup worked best when the entry waited for confirmation at support.",
        }
    ]
    outcomes = [
        {
            "result": "win",
            "pnl_pct": 2.4,
            "notes": "The trade held after the confirmation trigger fired.",
        }
    ]
    observations = [
        {
            "summary": "Patience reduced churn.",
            "note": "The impulsive entry was avoided.",
        }
    ]

    lesson = synthesize_lesson(docs, outcomes, observations)

    assert lesson["kind"] == "lesson"
    assert lesson["summary"]
    assert lesson["what_worked"]
    assert lesson["what_failed"]
    assert lesson["rule_change"]


def test_build_knowledge_node_preserves_theme_and_supporting_cases():
    lesson = {
        "summary": "Wait for confirmation before committing.",
        "what_worked": ["Confirmation reduced churn."],
        "what_failed": ["Impulsive entries were weaker."],
        "bias": "impulsiveness",
        "rule_change": "Require a confirmation trigger at support.",
    }

    node = build_knowledge_node(
        "entry discipline",
        lesson,
        ["case-1", "case-2"],
    )

    assert node["kind"] == "knowledge_node"
    assert node["theme"] == "entry discipline"
    assert node["supporting_cases"] == ["case-1", "case-2"]
    assert node["statement"]
    assert node["tags"]
    assert node["validity"]
    assert node["last_updated"]


def test_synthesis_is_deterministic_for_repeat_input():
    docs = [
        {
            "title": "Confirm before committing",
            "text": "The setup worked best when the entry waited for confirmation at support.",
        }
    ]
    outcomes = [
        {
            "result": "win",
            "pnl_pct": 2.4,
            "notes": "The trade held after the confirmation trigger fired.",
        }
    ]
    observations = [
        {
            "summary": "Patience reduced churn.",
            "note": "The impulsive entry was avoided.",
        }
    ]

    lesson_a = synthesize_lesson(docs, outcomes, observations)
    lesson_b = synthesize_lesson(docs, outcomes, observations)
    node_a = build_knowledge_node("entry discipline", lesson_a, ["case-1", "case-2"])
    node_b = build_knowledge_node("entry discipline", lesson_b, ["case-1", "case-2"])

    assert lesson_a == lesson_b
    assert node_a == node_b
