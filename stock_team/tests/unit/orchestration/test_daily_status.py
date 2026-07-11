import json
from datetime import datetime
from pathlib import Path

from stock_team.orchestration.models import new_trading_session
from stock_team.orchestration.daily_status import build_daily_status


def _session(mode="observation"):
    session = new_trading_session(
        "trading-2026-07-11",
        "2026-07-11",
        "2026-07-11T08:00:00-04:00",
        session_type=mode,
    )
    session["daily0_confirmation"] = {
        "confirmed_at": "2026-07-11T08:01:00-04:00",
        "activity_mode": mode,
        "account_fact_status": "stale_unverified" if mode == "observation" else "verified",
        "account_snapshot_ref": "runtime/inputs/account.json",
        "analysis_scope_ref": "runtime/inputs/universe.json",
        "user_confirmed": True,
    }
    return session


def test_confirmed_observation_waits_for_stage0_data(tmp_path):
    manifest = build_daily_status(
        session=_session(),
        runtime_root=tmp_path,
        now=datetime.fromisoformat("2026-07-11T08:05:00-04:00"),
    )

    assert manifest["current_node"] == "DAILY-1"
    assert manifest["current_step"] == "DAILY-1A"
    assert manifest["overall_status"] == "waiting_data"
    assert manifest["observation_available"] is True
    assert manifest["next_conversation_prompt"] == "请等待或刷新当日正式盘前数据。"


def test_missing_daily0_confirmation_waits_for_user(tmp_path):
    session = _session()
    session.pop("daily0_confirmation")

    manifest = build_daily_status(session=session, runtime_root=tmp_path)

    assert manifest["current_node"] == "DAILY-0"
    assert manifest["overall_status"] == "waiting_user"
    assert manifest["missing_items"][0]["code"] == "daily0_confirmation_missing"


def test_confirmed_focus_advances_to_stage1_evidence(tmp_path):
    inputs = tmp_path / "inputs"
    packets = tmp_path / "packets"
    inputs.mkdir()
    packets.mkdir()
    sid = "trading-2026-07-11"
    universe = {
        "date": "2026-07-11",
        "source_inputs": {"positions": [], "prior_review": {}, "cognition_state": {}},
        "permission_state_before_open": "Yellow",
        "forbidden_actions": [],
    }
    snapshot = {
        "markets": {
            symbol: {"price": 1, "prev_close": 1, "source": "polygon_premarket_snapshot"}
            for symbol in ("QQQ", "SPY", "IWM", "VIXY")
        }
    }
    (inputs / f"{sid}-stage0-universe.json").write_text(json.dumps(universe), encoding="utf-8")
    (inputs / f"{sid}-pre-market-snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    (packets / f"{sid}-stage0-market-context.md").write_text("# Stage 0\n", encoding="utf-8")
    (inputs / f"{sid}-stage0-discussion-notes.md").write_text("# Discussion\n## Market Context\n## Risk\n", encoding="utf-8")
    (inputs / f"{sid}-stage1-decision-sheet.json").write_text(json.dumps({
        "date": "2026-07-11", "focus_symbols": ["NVDA"], "user_confirmed": True
    }), encoding="utf-8")

    manifest = build_daily_status(session=_session(), runtime_root=tmp_path)

    assert manifest["current_step"] == "DAILY-1C"
    assert manifest["overall_status"] == "waiting_data"
    assert manifest["next_conversation_prompt"] == "请等待焦点标的证据生成。"
    assert manifest["state_sync"]["needed"] is True


def test_manifest_exposes_five_nodes_and_daily1_substeps(tmp_path):
    manifest = build_daily_status(session=_session(), runtime_root=tmp_path)

    assert [node["node"] for node in manifest["nodes"]] == [
        "DAILY-0", "DAILY-1", "DAILY-2", "DAILY-3", "DAILY-4"
    ]
    daily1 = manifest["nodes"][1]
    assert [step["step"] for step in daily1["substeps"]] == [
        "DAILY-1A", "DAILY-1B", "DAILY-1C", "DAILY-1D"
    ]


def test_daily_status_schema_declares_required_contract():
    schema_path = Path(__file__).parents[4] / "investing-os" / "system" / "data" / "schemas" / "daily-status.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "schema_version", "trading_date", "generated_at", "current_node",
        "current_step", "overall_status", "observation_available",
        "next_conversation_prompt", "nodes", "artifacts", "missing_items",
        "warnings", "state_sync", "cognition_links",
    }


def test_offline_daily0_daily1_artifacts_reach_open_observation(tmp_path):
    inputs = tmp_path / "inputs"
    packets = tmp_path / "packets"
    inputs.mkdir()
    packets.mkdir()
    sid = "trading-2026-07-11"
    (inputs / f"{sid}-stage0-universe.json").write_text(json.dumps({
        "date": "2026-07-11",
        "source_inputs": {"positions": [], "prior_review": {}, "cognition_state": {}},
        "permission_state_before_open": "Yellow",
        "forbidden_actions": ["loss_repair_reentry"],
    }), encoding="utf-8")
    (inputs / f"{sid}-pre-market-snapshot.json").write_text(json.dumps({
        "markets": {
            symbol: {"price": 1, "prev_close": 1, "source": "polygon_premarket_snapshot"}
            for symbol in ("QQQ", "SPY", "IWM", "VIXY")
        }
    }), encoding="utf-8")
    (packets / f"{sid}-stage0-market-context.md").write_text("# Stage 0\n", encoding="utf-8")
    (inputs / f"{sid}-stage0-discussion-notes.md").write_text("# Discussion\n## Market Context\n## Risk\n", encoding="utf-8")
    (inputs / f"{sid}-stage1-decision-sheet.json").write_text(json.dumps({
        "date": "2026-07-11", "focus_symbols": ["NVDA"], "user_confirmed": True
    }), encoding="utf-8")
    (packets / f"{sid}-stage1-plan-evidence.md").write_text("# Stage 1\nNVDA\n", encoding="utf-8")
    (inputs / f"{sid}-trading-plan.json").write_text(json.dumps({
        "risk_mode": "observe_only",
        "allowed_actions": [],
        "forbidden_actions": ["new_risk"],
        "user_confirmation": {"confirmed": True, "confirmed_version": "v1"},
    }), encoding="utf-8")
    (inputs / f"{sid}-intraday-guidance.json").write_text(json.dumps({
        "risk_mode": "observe_only", "allowed_actions": [], "forbidden_actions": ["new_risk"]
    }), encoding="utf-8")

    manifest = build_daily_status(session=_session(), runtime_root=tmp_path)

    assert manifest["current_node"] == "DAILY-2"
    assert manifest["current_step"] == "DAILY-2"
    assert manifest["overall_status"] == "active"
    assert manifest["observation_available"] is True
    assert manifest["missing_items"] == []
