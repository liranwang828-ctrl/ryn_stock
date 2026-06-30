import json
import subprocess

import pytest

from stock_team.orchestration.adapters import AdapterError, ExistingCliAdapter


def test_market_context_adapter_builds_snapshot_then_stage0_commands(tmp_path, monkeypatch):
    calls = []
    snapshot_path = tmp_path / "snapshot.json"

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[:4] == ["python", "-m", "stock_team.cli", "premarket-snapshot"]:
            snapshot_path.write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    output_path = tmp_path / "stage0.md"
    output_path.write_text("ok", encoding="utf-8")
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    adapter.run(
        "start_stage0",
        {
            "date": "2026-06-15",
            "as_of": "2026-06-15T09:20:00-04:00",
            "universe": "universe.json",
            "pre_market_snapshot": str(snapshot_path),
            "focus_symbols": "AAOX,MUU,COHR",
            "themes": "ai_infrastructure,semiconductors,cloud",
            "catalysts": "Manage AAOX and MUU exit timing.",
            "notes": "Formal stock_team snapshot required.",
            "out": str(output_path),
        },
    )
    assert calls[0][0][:4] == ["python", "-m", "stock_team.cli", "premarket-snapshot"]
    assert calls[1][0][:4] == ["python", "-m", "stock_team.cli", "market-context"]
    assert calls[0][1]["timeout"] >= 90
    assert calls[1][1]["timeout"] >= 60


def test_adapter_timeout_is_retryable(tmp_path, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    with pytest.raises(AdapterError) as caught:
        adapter.run(
            "start_stage0",
            {
                "date": "2026-06-15",
                "as_of": "x",
                "universe": "u",
                "out": "o",
            },
        )
    assert caught.value.retryable is True


def test_adapter_accepts_focus_confirmation_artifacts(tmp_path):
    notes = tmp_path / "stage0-discussion-notes.md"
    decision_sheet = tmp_path / "stage1-decision-sheet.json"
    notes.write_text("# notes", encoding="utf-8")
    decision_sheet.write_text(
        json.dumps({"focus_symbols": ["AAOX", "MUU"], "user_confirmed": True}),
        encoding="utf-8",
    )
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    result = adapter.run(
        "record_focus_confirmation",
        {
            "discussion_notes": str(notes),
            "decision_sheet": str(decision_sheet),
        },
    )

    assert result.command == []
    assert result.artifact_paths == [str(notes), str(decision_sheet)]


def test_record_focus_confirmation_validates_decision_sheet_exists(tmp_path):
    notes = tmp_path / "discussion-notes.md"
    notes.write_text("# notes", encoding="utf-8")
    decision_sheet = tmp_path / "nonexistent-decision-sheet.json"
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    with pytest.raises(AdapterError) as caught:
        adapter.run(
            "record_focus_confirmation",
            {"discussion_notes": str(notes), "decision_sheet": str(decision_sheet)},
        )
    assert "not found" in str(caught.value).lower()
    assert caught.value.retryable is False


def test_record_focus_confirmation_validates_required_fields(tmp_path):
    notes = tmp_path / "discussion-notes.md"
    decision_sheet = tmp_path / "decision-sheet.json"
    notes.write_text("# notes", encoding="utf-8")
    decision_sheet.write_text("{}", encoding="utf-8")
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    with pytest.raises(AdapterError) as caught:
        adapter.run(
            "record_focus_confirmation",
            {"discussion_notes": str(notes), "decision_sheet": str(decision_sheet)},
        )
    assert "focus_symbols" in str(caught.value)
    assert caught.value.retryable is False


def test_record_focus_confirmation_validates_user_confirmed_true(tmp_path):
    notes = tmp_path / "discussion-notes.md"
    decision_sheet = tmp_path / "decision-sheet.json"
    notes.write_text("# notes", encoding="utf-8")
    decision_sheet.write_text(
        json.dumps({"focus_symbols": ["AAPL"], "user_confirmed": False}),
        encoding="utf-8",
    )
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    with pytest.raises(AdapterError) as caught:
        adapter.run(
            "record_focus_confirmation",
            {"discussion_notes": str(notes), "decision_sheet": str(decision_sheet)},
        )
    assert "user_confirmed" in str(caught.value)
    assert caught.value.retryable is False


def test_record_focus_confirmation_accepts_valid_decision_sheet(tmp_path):
    notes = tmp_path / "discussion-notes.md"
    decision_sheet = tmp_path / "decision-sheet.json"
    notes.write_text("# notes", encoding="utf-8")
    decision_sheet.write_text(
        json.dumps({"focus_symbols": ["AAPL", "MSFT"], "user_confirmed": True}),
        encoding="utf-8",
    )
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    result = adapter.run(
        "record_focus_confirmation",
        {"discussion_notes": str(notes), "decision_sheet": str(decision_sheet)},
    )

    assert result.command == []
    assert str(notes) in result.artifact_paths
    assert str(decision_sheet) in result.artifact_paths


def test_record_plan_approval_validates_plan_files_exist(tmp_path):
    trading_plan = tmp_path / "trading-plan.json"
    intraday = tmp_path / "nonexistent-guidance.json"
    trading_plan.write_text(
        json.dumps({"risk_mode": "moderate", "allowed_actions": ["buy"], "forbidden_actions": ["short"]}),
        encoding="utf-8",
    )
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    with pytest.raises(AdapterError) as caught:
        adapter.run(
            "record_plan_approval",
            {"trading_plan": str(trading_plan), "intraday_guidance": str(intraday)},
        )
    assert "not found" in str(caught.value).lower()
    assert caught.value.retryable is False


def test_record_plan_approval_validates_required_fields(tmp_path):
    trading_plan = tmp_path / "trading-plan.json"
    intraday = tmp_path / "intraday-guidance.json"
    trading_plan.write_text("{}", encoding="utf-8")
    intraday.write_text("{}", encoding="utf-8")
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    with pytest.raises(AdapterError) as caught:
        adapter.run(
            "record_plan_approval",
            {"trading_plan": str(trading_plan), "intraday_guidance": str(intraday)},
        )
    assert "risk_mode" in str(caught.value)
    assert caught.value.retryable is False


def test_record_plan_approval_accepts_valid_plan_files(tmp_path):
    trading_plan = tmp_path / "trading-plan.json"
    intraday = tmp_path / "intraday-guidance.json"
    plan_data = {
        "risk_mode": "moderate",
        "allowed_actions": ["buy", "sell"],
        "forbidden_actions": ["short", "margin"],
    }
    trading_plan.write_text(json.dumps(plan_data), encoding="utf-8")
    intraday.write_text(json.dumps(plan_data), encoding="utf-8")
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")

    result = adapter.run(
        "record_plan_approval",
        {"trading_plan": str(trading_plan), "intraday_guidance": str(intraday)},
    )

    assert result.command == []
    assert str(trading_plan) in result.artifact_paths
    assert str(intraday) in result.artifact_paths
