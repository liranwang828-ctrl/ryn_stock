# tests/unit/agents/test_evidence_credibility_report.py
import json
from pathlib import Path


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_report_classifies_factor_and_backtest_evidence(tmp_path):
    from scripts.legacy.evidence_credibility_report import build_evidence_credibility_report

    findings = tmp_path / "findings"
    config = tmp_path / "config"
    _write_json(
        findings / "factor_ic_report.json",
        [
            {
                "Factor": "5. Volatility (20d)",
                "Mean IC": 0.0553,
                "IC Std": 0.2649,
                "IR (Info Ratio)": 0.2088,
                "t-statistic": 2.18,
                "Positive Weeks %": "61.5%",
                "Weeks Count": 109,
            },
            {
                "Factor": "6. Sentiment Catalyst",
                "Mean IC": -0.1564,
                "IC Std": 0.1666,
                "IR (Info Ratio)": -0.9387,
                "t-statistic": -1.33,
                "Positive Weeks %": "50.0%",
                "Weeks Count": 2,
            },
        ],
    )
    _write_json(
        findings / "weekly_oos_validation_results.json",
        {
            "full_lifecycle": {
                "return": 129.87,
                "mdd": -26.95,
                "sortino": 0.8522,
                "alpha": 7.98,
            },
            "time_oos": {
                "return": 57.18,
                "mdd": -5.78,
                "sortino": 3.4882,
                "alpha": 15.94,
            },
            "style_oos": {
                "return": 98.25,
                "mdd": -18.19,
                "sortino": 1.0065,
                "alpha": -23.64,
            },
        },
    )
    _write_json(
        config / "best_weekly_params.json",
        {
            "optimized_metrics": {
                "sortino": 0.8522,
                "neighborhood_avg_sortino": 0.8508,
            }
        },
    )
    _write_json(
        findings / "random_search_v2_summary.json",
        {
            "best_pf": 1.2819,
            "best_return": 1.7871,
            "top_results": [{"qqq_return": 21.2192}],
        },
    )

    report = build_evidence_credibility_report("2026-06-01", base_dir=str(tmp_path))

    factors = report["factor_credibility"]["factors"]
    assert factors["5. Volatility (20d)"]["tier"] == "robust"
    assert factors["6. Sentiment Catalyst"]["tier"] == "insufficient"
    assert "样本只有 2 周" in " ".join(factors["6. Sentiment Catalyst"]["notes"])
    assert report["backtest_credibility"]["overall_verdict"] == "caution"
    assert report["backtest_credibility"]["style_oos"]["verdict"] == "caution"
    assert report["backtest_credibility"]["parameter_stability"]["tier"] == "usable"
    assert report["intraday_precision_credibility"]["tier"] == "exploratory"
    assert report["decision_state_overrides"]["factor_quality"] == "usable"
    assert report["decision_state_overrides"]["backtest_verdict"] == "caution"
    assert any(
        "Style-OOS alpha 为负" in w
        for w in report["decision_state_overrides"]["required_warnings"]
    )


def test_write_report_creates_findings_artifact(tmp_path):
    from scripts.legacy.evidence_credibility_report import write_evidence_credibility_report

    out = write_evidence_credibility_report("2026-06-01", base_dir=str(tmp_path))
    payload = json.loads(Path(out).read_text(encoding="utf-8"))

    assert Path(out).name == "evidence_credibility_report.json"
    assert payload["date"] == "2026-06-01"
    assert "decision_state_overrides" in payload


def test_missing_inputs_are_unavailable_not_crashing(tmp_path):
    from scripts.legacy.evidence_credibility_report import build_evidence_credibility_report

    report = build_evidence_credibility_report("2026-06-01", base_dir=str(tmp_path))

    assert report["factor_credibility"]["overall_verdict"] == "insufficient"
    assert report["backtest_credibility"]["overall_verdict"] == "unavailable"
    assert report["intraday_precision_credibility"]["tier"] == "insufficient"
