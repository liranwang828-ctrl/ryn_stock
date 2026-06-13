import json
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_symbol_state_uses_existing_artifacts(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "track": "swing",
            "thesis": {
                "base_thesis": "AI demand remains strong",
                "key_catalysts": ["earnings follow-through"],
                "main_risks": ["valuation compression"],
                "today_falsification": "breaks premarket support",
            },
            "entry": {
                "entry_base": 100.0,
                "target_price": 112.0,
                "stop_loss": 94.0,
                "sizing": "normal",
            },
            "exit": {
                "hard_stop": 94.0,
                "target_price": 112.0,
            },
            "market_context": {
                "phase": "premarket",
            },
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {
            "date": date,
            "decisions": {
                "NVDA": {
                    "decision": "可入场",
                    "confidence": "高",
                    "hard_vetoes": [],
                    "soft_vetoes": [],
                }
            },
        },
    )
    _write_json(
        findings / "factor_ic_report.json",
        {
            "factors": {
                "volatility_20d": {
                    "mean_ic": 0.0553,
                    "ir": 0.2088,
                    "t_stat": 2.18,
                    "positive_weeks_pct": 61.5,
                    "sample_weeks": 26,
                },
                "sentiment_catalyst": {
                    "mean_ic": 0.09,
                    "sample_weeks": 2,
                },
            }
        },
    )
    _write_json(
        findings / "weekly_oos_validation_results.json",
        {
            "time_oos": {
                "return_pct": 57.18,
                "max_drawdown_pct": -5.78,
                "alpha_pct": 15.94,
            },
            "style_oos": {"return_pct": 98.25, "alpha_pct": -23.64},
            "full_lifecycle": {"return_pct": 129.87, "max_drawdown_pct": -26.95},
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert state["date"] == date
    assert nvda["identity"]["symbol"] == "NVDA"
    assert nvda["thesis"]["verdict"] == "supportive"
    assert nvda["factor_evidence"]["factor_quality"] == "usable"
    assert nvda["backtest_evidence"]["backtest_verdict"] == "supportive"
    assert nvda["execution"]["action_state"] == "act"
    assert nvda["controller"]["evidence_alignment"] == "aligned"
    assert nvda["visual_notes"]["primary_action"] == "可入场"


def test_malformed_premarket_summary_marks_source_invalid(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    findings.mkdir(parents=True)
    (findings / f"premarket_summary_{date}_NVDA.json").write_text(
        '{"symbol": "NVDA", "thesis": ',
        encoding="utf-8",
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {
            "date": date,
            "decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}},
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert nvda["identity"]["source_freshness"]["premarket_summary"]["status"] in {
        "invalid",
        "parse_error",
    }
    unavailable_text = " ".join(
        nvda["controller"]["blocked_by"]
        + nvda["controller"]["required_human_check"]
    )
    assert "premarket" in unavailable_text or "输入" in unavailable_text


def test_backtest_caution_summary_does_not_claim_aligned_evidence(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "track": "swing",
            "thesis": {"base_thesis": "AI demand remains strong"},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {
            "date": date,
            "decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}},
        },
    )
    _write_json(
        findings / "factor_ic_report.json",
        {
            "factors": {
                "volatility_20d": {
                    "mean_ic": 0.0553,
                    "sample_weeks": 26,
                }
            }
        },
    )
    _write_json(
        findings / "weekly_oos_validation_results.json",
        {
            "time_oos": {"return_pct": 1.0, "max_drawdown_pct": -5.0, "alpha_pct": 0},
            "full_lifecycle": {"return_pct": 10.0, "max_drawdown_pct": -12.0},
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert nvda["controller"]["evidence_alignment"] == "mixed"
    assert "证据对齐" not in nvda["controller"]["summary_for_dashboard"]
    assert all("证据对齐" not in note for note in nvda["visual_notes"]["why_now"])


def test_controller_audit_allows_act_when_evidence_aligned(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
            "entry": {"entry_base": 100.0},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )
    _write_json(
        findings / "evidence_credibility_report.json",
        {
            "factor_credibility": {
                "overall_verdict": "usable",
                "factors": {
                    "5. Volatility (20d)": {"tier": "robust", "weeks_count": 109}
                },
            },
            "backtest_credibility": {
                "overall_verdict": "supportive",
                "time_oos": {"verdict": "supportive", "alpha": 15.94},
                "style_oos": {"verdict": "supportive", "alpha": 4.2},
                "full_lifecycle": {"verdict": "supportive"},
                "parameter_stability": {"tier": "usable"},
                "notes": [],
            },
            "decision_state_overrides": {
                "factor_quality": "usable",
                "backtest_verdict": "supportive",
                "required_warnings": [],
            },
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    audit = state["symbols"]["NVDA"]["controller"]["audit"]

    assert "act" in audit["allowed_actions"]
    assert audit["llm_output_contract"]["final_action_must_be_one_of"] == audit["allowed_actions"]
    assert audit["llm_output_contract"]["confidence_ceiling"] == 70
    assert not any("不能建议立即入场" in claim for claim in audit["forbidden_claims"])
    assert any(item["source"] == "thesis" for item in audit["evidence_for"])
    assert any(item["source"] == "factor" for item in audit["evidence_for"])
    assert any(item["source"] == "backtest" for item in audit["evidence_for"])

def test_missing_sources_emit_valid_monitor_state(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    state = build_decision_state(date="2026-06-01", symbols=["MRVL"], base_dir=str(tmp_path))
    mrvl = state["symbols"]["MRVL"]

    assert mrvl["identity"]["source_freshness"]["premarket_summary"]["status"] == "missing"
    assert mrvl["thesis"]["verdict"] == "insufficient"
    assert mrvl["factor_evidence"]["factor_quality"] == "unavailable"
    assert mrvl["backtest_evidence"]["backtest_verdict"] == "unavailable"
    assert mrvl["execution"]["action_state"] == "monitor"
    assert mrvl["controller"]["controller_verdict"] == "monitor"
    assert mrvl["visual_notes"]["risk_flag"] == "blocked"


def test_controller_downgrades_action_when_evidence_missing(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert nvda["execution"]["action_state"] == "act"
    assert nvda["controller"]["controller_verdict"] == "wait"
    assert "missing_thesis" in nvda["controller"]["blocked_by"]
    assert nvda["visual_notes"]["primary_action"] == "等待"


def test_write_decision_state_creates_json_file(tmp_path):
    from stock_team.utils.decision_state_hub import write_decision_state

    out = write_decision_state("2026-06-01", ["NVDA"], base_dir=str(tmp_path))
    payload = json.loads(Path(out).read_text(encoding="utf-8"))

    assert Path(out).name == "decision_state_2026-06-01.json"
    assert payload["symbols"]["NVDA"]["identity"]["symbol"] == "NVDA"


def test_uses_capsule_premarket_summary_and_discovers_symbol(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / "symbols" / "NVDA" / "plans" / f"premarket_summary_{date}.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "Capsule thesis is current"},
            "entry": {"entry_base": 100.0},
            "market_context": {"phase": "premarket"},
        },
    )

    state = build_decision_state(date=date, base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert nvda["thesis"]["base_thesis"] == "Capsule thesis is current"
    assert nvda["identity"]["source_freshness"]["premarket_summary"]["status"] == "fresh"
    assert nvda["identity"]["source_freshness"]["premarket_summary"]["path"] == (
        "findings/symbols/NVDA/plans/premarket_summary_2026-06-01.json"
    )


def test_stale_premarket_summary_is_marked_and_downgraded(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    findings = tmp_path / "findings"
    _write_json(
        findings / "symbols" / "NVDA" / "plans" / "premarket_summary_2026-05-31.json",
        {
            "symbol": "NVDA",
            "date": "2026-05-31",
            "thesis": {"base_thesis": "Yesterday thesis should not look fresh"},
            "entry": {"entry_base": 100.0},
        },
    )

    state = build_decision_state(date="2026-06-01", symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert nvda["identity"]["source_freshness"]["premarket_summary"]["status"] == "stale"
    assert "stale_premarket_summary" in nvda["controller"]["blocked_by"]
    assert nvda["controller"]["controller_confidence"] <= 35
    assert nvda["visual_notes"]["risk_flag"] == "blocked"


def test_decision_state_prefers_evidence_credibility_report(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )
    _write_json(
        findings / "evidence_credibility_report.json",
        {
            "factor_credibility": {
                "overall_verdict": "usable",
                "factors": {
                    "5. Volatility (20d)": {"tier": "robust", "weeks_count": 109}
                },
            },
            "backtest_credibility": {
                "overall_verdict": "caution",
                "time_oos": {"verdict": "supportive", "alpha": 15.94},
                "style_oos": {"verdict": "caution", "alpha": -23.64},
                "full_lifecycle": {"verdict": "supportive"},
                "parameter_stability": {"tier": "usable"},
                "notes": ["style-OOS alpha 为负，LLM 和 dashboard 必须显式提示"],
            },
            "decision_state_overrides": {
                "factor_quality": "usable",
                "backtest_verdict": "caution",
                "required_warnings": ["Style-OOS alpha 为负"],
            },
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert nvda["factor_evidence"]["factor_quality"] == "usable"
    assert nvda["factor_evidence"]["factor_scores"]["5. Volatility (20d)"]["tier"] == "robust"
    assert nvda["backtest_evidence"]["backtest_verdict"] == "caution"
    assert "Style-OOS alpha 为负" in nvda["controller"]["required_human_check"]
    assert nvda["controller"]["evidence_alignment"] == "mixed"


def test_controller_audit_blocks_act_when_backtest_is_caution(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )
    _write_json(
        findings / "evidence_credibility_report.json",
        {
            "factor_credibility": {
                "overall_verdict": "usable",
                "factors": {
                    "5. Volatility (20d)": {"tier": "robust", "weeks_count": 109}
                },
            },
            "backtest_credibility": {
                "overall_verdict": "caution",
                "time_oos": {"verdict": "supportive", "alpha": 15.94},
                "style_oos": {"verdict": "caution", "alpha": -23.64},
                "full_lifecycle": {"verdict": "supportive"},
                "parameter_stability": {"tier": "usable"},
                "notes": ["style-OOS alpha 为负，LLM 和 dashboard 必须显式提示"],
            },
            "decision_state_overrides": {
                "factor_quality": "usable",
                "backtest_verdict": "caution",
                "required_warnings": ["Style-OOS alpha 为负"],
            },
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    controller = state["symbols"]["NVDA"]["controller"]
    audit = controller["audit"]

    assert controller["evidence_alignment"] == "mixed"
    assert "act" not in audit["allowed_actions"]
    assert audit["llm_output_contract"]["final_action_must_be_one_of"] == audit["allowed_actions"]
    assert audit["llm_output_contract"]["confidence_ceiling"] == controller["controller_confidence"]
    assert any(item["source"] == "backtest" and item["status"] == "caution" for item in audit["evidence_against"])
    assert any("caution" in reason for reason in audit["downgrade_reasons"])
    assert any("fully validated" in claim for claim in audit["forbidden_claims"])
    assert any("证据完全对齐" in claim for claim in audit["forbidden_claims"])


def test_controller_audit_records_stale_input_discipline(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    findings = tmp_path / "findings"
    _write_json(
        findings / "symbols" / "NVDA" / "plans" / "premarket_summary_2026-05-31.json",
        {
            "symbol": "NVDA",
            "date": "2026-05-31",
            "thesis": {"base_thesis": "Yesterday thesis should not look fresh"},
        },
    )
    _write_json(
        findings / "entry_decision_2026-06-01.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )

    state = build_decision_state(date="2026-06-01", symbols=["NVDA"], base_dir=str(tmp_path))
    controller = state["symbols"]["NVDA"]["controller"]
    audit = controller["audit"]

    assert "stale_premarket_summary" in controller["blocked_by"]
    assert "act" not in audit["allowed_actions"]
    assert any(item["source"] == "source_freshness" for item in audit["evidence_against"])
    assert any("刷新 premarket_summary" in reason for reason in audit["downgrade_reasons"])
    assert any("不能建议立即入场" in claim for claim in audit["forbidden_claims"])
    assert any("输入完整且新鲜" in claim for claim in audit["forbidden_claims"])


def test_controller_audit_records_insufficient_factor_samples(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )
    _write_json(
        findings / "evidence_credibility_report.json",
        {
            "factor_credibility": {
                "overall_verdict": "insufficient",
                "factors": {
                    "6. Sentiment Catalyst": {
                        "tier": "insufficient",
                        "weeks_count": 2,
                        "notes": ["样本只有 2 周，禁止作为强证据"],
                    }
                },
            },
            "backtest_credibility": {
                "overall_verdict": "supportive",
                "time_oos": {"verdict": "supportive", "alpha": 15.94},
                "style_oos": {"verdict": "supportive", "alpha": 4.2},
                "full_lifecycle": {"verdict": "supportive"},
                "parameter_stability": {"tier": "usable"},
                "notes": [],
            },
            "decision_state_overrides": {
                "factor_quality": "insufficient",
                "backtest_verdict": "supportive",
                "required_warnings": ["6. Sentiment Catalyst 样本不足"],
            },
        },
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    audit = state["symbols"]["NVDA"]["controller"]["audit"]

    assert "act" not in audit["allowed_actions"]
    assert any(item["source"] == "factor" and item["status"] == "insufficient" for item in audit["evidence_against"])
    assert any("样本不足" in reason for reason in audit["downgrade_reasons"])
    assert any("样本不足因子" in claim for claim in audit["forbidden_claims"])
    assert audit["llm_output_contract"]["narrative_only_upgrade_allowed"] is False


def test_visual_notes_remain_dashboard_safe_with_audit(tmp_path):
    from stock_team.utils.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(
        findings / f"premarket_summary_{date}_NVDA.json",
        {
            "symbol": "NVDA",
            "date": date,
            "thesis": {"base_thesis": "AI demand remains strong"},
            "entry": {"entry_base": 100.0},
            "exit": {"hard_stop": 94.0, "target_price": 112.0},
        },
    )
    _write_json(
        findings / f"entry_decision_{date}.json",
        {"decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}},
    )

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert "audit" in nvda["controller"]
    assert "audit" not in nvda["visual_notes"]
    assert set(nvda["visual_notes"]) >= {
        "primary_action",
        "why_now",
        "risk_flag",
        "evidence_alignment",
        "missing_inputs",
        "level_map",
        "review_questions",
    }
    assert isinstance(nvda["visual_notes"]["why_now"], list)
    assert nvda["visual_notes"]["why_now"]
    assert all(isinstance(item, str) for item in nvda["visual_notes"]["why_now"])
