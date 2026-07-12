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
    assert "--as-of" in calls[0][0]
    assert "--as-of" in calls[1][0]
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


def test_adapter_supports_intraday_snapshot(tmp_path, monkeypatch):
    calls = []
    snapshot_out = tmp_path / "snapshot.md"

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        snapshot_out.write_text("ok", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    result = adapter.run(
        "refresh_market_observation",
        {"symbols": "MSFT,NVDA", "out": str(snapshot_out)},
    )
    assert calls[0][0][:4] == ["python", "-m", "stock_team.cli", "intraday-snapshot"]
    assert "--symbols" in calls[0][0]
    assert "MSFT,NVDA" in calls[0][0]
    assert "--out" in calls[0][0]
    assert result.artifact_paths == [str(snapshot_out)]


def test_adapter_supports_intraday_snapshot_with_refresh(tmp_path, monkeypatch):
    calls = []
    snapshot_out = tmp_path / "snapshot.md"

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        snapshot_out.write_text("ok", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    adapter.run(
        "refresh_market_observation",
        {"symbols": "MSFT,NVDA", "refresh": True, "out": str(snapshot_out)},
    )
    assert "--refresh" in calls[0][0]


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


# ---------------------------------------------------------------------------
# L1: start_stage0_from_snapshot adapter — market-context only, no premarket-snapshot
# ---------------------------------------------------------------------------


def test_start_stage0_from_snapshot_builds_only_market_context(tmp_path, monkeypatch):
    calls = []
    snapshot_path = tmp_path / "existing_snapshot.json"
    snapshot_path.write_text('{"source_kind": "formal_provider_snapshot"}', encoding="utf-8")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    output_path = tmp_path / "stage0.md"
    output_path.write_text("ok", encoding="utf-8")
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    adapter.run(
        "start_stage0_from_snapshot",
        {
            "date": "2026-06-15",
            "as_of": "2026-06-15T09:20:00-04:00",
            "universe": "universe.json",
            "pre_market_snapshot": str(snapshot_path),
            "out": str(output_path),
        },
    )
    assert len(calls) == 1
    assert calls[0][0][:4] == ["python", "-m", "stock_team.cli", "market-context"]
    assert "--as-of" in calls[0][0]
    assert "2026-06-15T09:20:00-04:00" in calls[0][0]
    assert "--pre-market-snapshot" in calls[0][0]
    assert str(snapshot_path) in calls[0][0]


def test_existing_start_stage0_still_builds_both_commands(tmp_path, monkeypatch):
    """Existing start_stage0 must still build premarket-snapshot + market-context."""
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
            "focus_symbols": "AAOX",
            "themes": "ai",
            "catalysts": "none",
            "notes": "test",
            "out": str(output_path),
        },
    )
    assert len(calls) == 2
    assert calls[0][0][:4] == ["python", "-m", "stock_team.cli", "premarket-snapshot"]
    assert calls[1][0][:4] == ["python", "-m", "stock_team.cli", "market-context"]
    assert "--as-of" in calls[0][0]
    assert "--as-of" in calls[1][0]


def test_start_stage0_observation_builds_only_observation_producer_command(tmp_path, monkeypatch):
    calls = []
    snapshot_path = tmp_path / "snapshot.json"
    output_path = tmp_path / "context.md"

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        snapshot_path.write_text("{}", encoding="utf-8")
        output_path.write_text("# observation", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = ExistingCliAdapter(workspace_root=tmp_path, python_executable="python")
    result = adapter.run("start_stage0_observation", {
        "date": "2026-07-10",
        "as_of": "2026-07-10T08:30:00-04:00",
        "snapshot_out": str(snapshot_path),
        "out": str(output_path),
    })

    assert len(calls) == 1
    assert calls[0][0][:3] == ["python", "-m", "stock_team.data_ingest.observation_market_context"]
    assert result.artifact_paths == [str(snapshot_path), str(output_path)]
