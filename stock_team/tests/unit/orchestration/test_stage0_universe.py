import json


def test_build_stage0_universe_writes_canonical_brain_preconditions(tmp_path, monkeypatch):
    from stock_team.orchestration.stage0_universe import build_stage0_universe_document

    stock_team_home = tmp_path / "stock_team"
    investing_os_home = tmp_path / "investing-os"
    runtime_root = investing_os_home / "system" / "runtime"
    (stock_team_home / "config").mkdir(parents=True)
    (runtime_root / "inputs").mkdir(parents=True)
    (investing_os_home / "wiki" / "journals").mkdir(parents=True)
    monkeypatch.setenv("INVESTING_OS_HOME", str(investing_os_home))

    (stock_team_home / "config" / "positions.json").write_text(
        json.dumps({
            "positions": {
                "MSFT": {
                    "position_type": "cloud core",
                    "thesis_status": "researched",
                }
            }
        }),
        encoding="utf-8",
    )
    (runtime_root / "inputs" / "observation-2026-08-13-pre-market-snapshot.json").write_text(
        json.dumps({"focus_symbols": ["NBIS"], "themes": ["ai_infrastructure"]}),
        encoding="utf-8",
    )
    journal = investing_os_home / "wiki" / "journals" / "2026-08-12-review.md"
    journal.write_text("# Review", encoding="utf-8")

    universe_path, journal_path = build_stage0_universe_document(
        base_dir=stock_team_home,
        runtime_root=runtime_root,
        market_date="2026-08-13",
        session_id="observation-2026-08-13",
    )

    expected = runtime_root / "inputs" / "observation-2026-08-13-stage0-universe.json"
    assert universe_path == expected
    assert journal_path == str(journal)
    payload = json.loads(expected.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "pre_market_universe"
    assert payload["date"] == "2026-08-13"
    assert set(payload["source_inputs"]) == {"positions", "prior_review", "cognition_state"}
    assert payload["permission_state_before_open"] == "Yellow"
    assert payload["forbidden_actions"]
    assert {row["symbol"] for row in payload["universe"]} == {"MSFT", "NBIS"}
