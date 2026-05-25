import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.research_ingest import (
    ingest_manual_note,
    ingest_news_item,
    ingest_public_holding,
    ingest_sec_filing,
)


def test_ingest_news_item_normalizes_fields():
    raw = {
        "title": "NVDA beats expectations",
        "source": "Reuters",
        "url": "https://example.com/news",
        "published_at": "2026-05-24T08:00:00-04:00",
        "body": "Strong data center demand...",
        "symbols": ["nvda", "NVDA"],
        "citations": ["https://example.com/source-note"],
        "category": "earnings",
    }

    doc = ingest_news_item(raw)

    assert doc["id"].startswith("news-")
    assert doc["source_type"] == "news"
    assert doc["symbols"] == ["NVDA"]
    assert doc["title"] == "NVDA beats expectations"
    assert doc["source"] == "Reuters"
    assert doc["url"] == "https://example.com/news"
    assert doc["published_at"] == "2026-05-24T08:00:00-04:00"
    assert doc["text"] == "Strong data center demand..."
    assert doc["body"] == "Strong data center demand..."
    assert doc["citations"] == ["https://example.com/source-note", "https://example.com/news"]
    assert doc["category"] == "earnings"
    assert ingest_news_item(raw)["id"] == doc["id"]


def test_ingest_news_item_falls_back_from_empty_symbols_and_citations():
    raw = {
        "title": "NVDA beats expectations",
        "source": "Reuters",
        "url": "https://example.com/news",
        "published_at": "2026-05-24T08:00:00-04:00",
        "text": "  ",
        "body": "Strong data center demand...",
        "symbols": [],
        "symbol": "nvda",
        "citations": [],
        "citation": "https://example.com/source-note",
    }

    doc = ingest_news_item(raw)

    assert doc["symbols"] == ["NVDA"]
    assert doc["text"] == "Strong data center demand..."
    assert doc["body"] == "Strong data center demand..."
    assert doc["citations"] == ["https://example.com/source-note", "https://example.com/news"]


def test_ingest_sec_filing_normalizes_fields():
    raw = {
        "symbol": "nvda",
        "form_type": "10-Q",
        "source": "SEC",
        "url": "https://example.com/10q",
        "published_at": "2026-05-24T00:00:00-04:00",
        "text": "Risk factors ...",
        "filing_date": "2026-05-23",
        "citations": ["https://example.com/sec-citation"],
    }

    doc = ingest_sec_filing(raw)

    assert doc["id"].startswith("sec_filing-")
    assert doc["source_type"] == "sec_filing"
    assert doc["symbol"] == "NVDA"
    assert doc["form_type"] == "10-Q"
    assert doc["source"] == "SEC"
    assert doc["url"] == "https://example.com/10q"
    assert doc["published_at"] == "2026-05-24T00:00:00-04:00"
    assert doc["text"] == "Risk factors ..."
    assert doc["citations"] == ["https://example.com/sec-citation", "https://example.com/10q"]
    assert doc["filing_date"] == "2026-05-23"
    assert ingest_sec_filing(raw)["id"] == doc["id"]


def test_ingest_public_holding_uses_text_when_rationale_is_blank():
    raw = {
        "person": "Warren Buffett",
        "symbol": "brk.b",
        "action": "add",
        "source": "13F",
        "published_at": "2026-05-24T00:00:00-04:00",
        "rationale": "   ",
        "text": "Trims cash into quality compounders",
        "citations": ["https://example.com/13f-filing"],
    }

    doc = ingest_public_holding(raw)

    assert doc["rationale"] == "Trims cash into quality compounders"
    assert doc["text"] == "Trims cash into quality compounders"


def test_ingest_public_holding_normalizes_fields():
    raw = {
        "person": "Warren Buffett",
        "symbol": "brk.b",
        "action": "add",
        "source": "13F",
        "published_at": "2026-05-24T00:00:00-04:00",
        "rationale": "Trims cash into quality compounders",
        "citations": ["https://example.com/13f-filing"],
        "manager": "Berkshire Hathaway",
    }

    doc = ingest_public_holding(raw)

    assert doc["id"].startswith("public_holding-")
    assert doc["source_type"] == "public_holding"
    assert doc["person"] == "Warren Buffett"
    assert doc["symbol"] == "BRK.B"
    assert doc["action"] == "add"
    assert doc["source"] == "13F"
    assert doc["published_at"] == "2026-05-24T00:00:00-04:00"
    assert doc["rationale"] == "Trims cash into quality compounders"
    assert doc["text"] == "Trims cash into quality compounders"
    assert doc["citations"] == ["https://example.com/13f-filing"]
    assert doc["manager"] == "Berkshire Hathaway"
    assert ingest_public_holding(raw)["id"] == doc["id"]


def test_ingest_manual_note_normalizes_fields():
    raw = {
        "source": "research desk",
        "published_at": "2026-05-24T09:15:00-04:00",
        "title": "Follow up on AI optics",
        "text": "Check supplier cadence and margin mix.",
        "symbols": ["lite", "MRVL"],
        "citations": ["/tmp/notes/ai-optics.pdf"],
        "author": "Analyst",
    }

    doc = ingest_manual_note(raw)

    assert doc["id"].startswith("manual_note-")
    assert doc["source_type"] == "manual_note"
    assert doc["source"] == "research desk"
    assert doc["published_at"] == "2026-05-24T09:15:00-04:00"
    assert doc["title"] == "Follow up on AI optics"
    assert doc["text"] == "Check supplier cadence and margin mix."
    assert doc["symbols"] == ["LITE", "MRVL"]
    assert doc["citations"] == ["/tmp/notes/ai-optics.pdf"]
    assert doc["author"] == "Analyst"
    assert ingest_manual_note(raw)["id"] == doc["id"]


def test_ingest_news_item_id_is_stable_across_collection_order():
    raw_a = {
        "title": "NVDA beats expectations",
        "source": "Reuters",
        "url": "https://example.com/news",
        "published_at": "2026-05-24T08:00:00-04:00",
        "text": "Strong data center demand...",
        "symbols": ["nvda", "amd"],
        "citations": ["https://example.com/b", "https://example.com/a"],
    }
    raw_b = {
        "title": "NVDA beats expectations",
        "source": "Reuters",
        "url": "https://example.com/news",
        "published_at": "2026-05-24T08:00:00-04:00",
        "text": "Strong data center demand...",
        "symbols": ["amd", "nvda"],
        "citations": ["https://example.com/a", "https://example.com/b"],
    }

    doc_a = ingest_news_item(raw_a)
    doc_b = ingest_news_item(raw_b)

    assert doc_a["symbols"] == ["NVDA", "AMD"]
    assert doc_b["symbols"] == ["AMD", "NVDA"]
    assert doc_a["id"] == doc_b["id"]
