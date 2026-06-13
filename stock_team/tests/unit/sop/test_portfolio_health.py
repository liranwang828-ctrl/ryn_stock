import sys, os, json, datetime

from unittest.mock import patch


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _mock_risk_result():
    """compute_portfolio_risk() 的最小合法返回值"""
    return {
        "positions_detail": [
            {
                "sym": "NVDA", "underlying": "NVDA", "leverage": 1,
                "shares": 10, "cost": 180.0,
                "cur_price": 200.0, "market_value": 2000.0, "net_exposure": 2000.0,
                "beta": 1.2, "var_5pct_loss": 120.0,
            }
        ],
        "total_value": 2000.0, "total_exposure": 2000.0, "leverage_ratio": 1.0,
        "var_5pct_loss": 120.0, "var_5pct_pct": 6.0,
        "sector_pct": {"Tech": 100.0},
        "sector_exposure": {"Tech": 2000.0},
        "top_corr_pair": ("NVDA", "AAPL"),
        "top_corr_value": 0.7,
        "corr_matrix": {"NVDA": {"AAPL": 0.7}},
        "warnings": [],
    }


def test_build_warnings_leverage_excess():
    """leverage_ratio > 2.5 → high warning"""
    from stock_team.core.portfolio_snapshot import build_warnings
    totals = {"leverage_ratio": 2.8, "var_5pct_pct": 10.0}
    sector = {"top_sector_pct": 50.0, "top_sector": "Tech", "hhi": 0.2}
    correlation = {"top_pair_value": 0.7, "top_pair": ["A", "B"], "high_corr_count": 0}
    positions = []
    strategic = {"memo_expiry_alerts": [], "stance_misalign": []}
    warns = build_warnings(totals, sector, correlation, positions, strategic)
    codes = [w["code"] for w in warns]
    assert "leverage_excess" in codes
    assert any(w["level"] == "high" for w in warns if w["code"] == "leverage_excess")


def test_build_warnings_approaching_stop():
    """dist_to_stop_pct < 3 → high approaching_stop warning"""
    from stock_team.core.portfolio_snapshot import build_warnings
    totals = {"leverage_ratio": 1.0, "var_5pct_pct": 5.0}
    sector = {"top_sector_pct": 40.0, "top_sector": "Tech", "hhi": 0.15}
    correlation = {"top_pair_value": 0.5, "top_pair": ["A", "B"], "high_corr_count": 0}
    positions = [{"sym": "NVDA", "dist_to_stop_pct": 1.5}]
    strategic = {"memo_expiry_alerts": [], "stance_misalign": []}
    warns = build_warnings(totals, sector, correlation, positions, strategic)
    codes = [w["code"] for w in warns]
    assert "approaching_stop" in codes


def test_build_warnings_no_warning():
    """一切正常 → 空警告列表"""
    from stock_team.core.portfolio_snapshot import build_warnings
    totals = {"leverage_ratio": 1.0, "var_5pct_pct": 5.0}
    sector = {"top_sector_pct": 40.0, "top_sector": "Tech", "hhi": 0.15}
    correlation = {"top_pair_value": 0.5, "top_pair": ["A", "B"], "high_corr_count": 0}
    positions = [{"sym": "NVDA", "dist_to_stop_pct": 10.0}]
    strategic = {"memo_expiry_alerts": [], "stance_misalign": []}
    warns = build_warnings(totals, sector, correlation, positions, strategic)
    assert warns == []


def test_build_portfolio_snapshot_schema(tmp_path):
    """build_portfolio_snapshot 返回所有顶层 key"""
    from stock_team.core.portfolio_snapshot import build_portfolio_snapshot
    # 写入 positions.json（只需最小结构）
    pos_file = tmp_path / "config" / "positions.json"
    _write(str(pos_file), {
        "positions": {"NVDA": {
            "cost": 180.0, "shares": 10, "date": "2026-05-12",
            "thesis_status": "intact",
        }},
        "_excluded": [],
    })

    mock_result = _mock_risk_result()
    with patch("stock_team.core.portfolio_snapshot.compute_portfolio_risk",
               return_value=mock_result):
        snapshot = build_portfolio_snapshot(
            date="2026-05-20", trigger="on_demand", base_dir=str(tmp_path))

    required = {"date", "generated_at", "trigger", "positions_detail",
                "totals", "sector", "correlation", "strategic_alignment", "warnings"}
    assert required == set(snapshot.keys()), f"缺少: {required - set(snapshot.keys())}"
    assert snapshot["trigger"] == "on_demand"
    assert isinstance(snapshot["positions_detail"], list)
    assert isinstance(snapshot["warnings"], list)


def test_write_portfolio_snapshot_creates_file(tmp_path):
    """write_portfolio_snapshot 生成 JSON 文件"""
    from stock_team.core.portfolio_snapshot import build_portfolio_snapshot, write_portfolio_snapshot
    pos_file = tmp_path / "config" / "positions.json"
    _write(str(pos_file), {
        "positions": {"NVDA": {"cost": 180.0, "shares": 10, "date": "2026-05-12",
                                "thesis_status": "intact"}},
        "_excluded": [],
    })
    import pathlib
    mock_result = _mock_risk_result()
    with patch("stock_team.core.portfolio_snapshot.compute_portfolio_risk",
               return_value=mock_result):
        data = build_portfolio_snapshot("2026-05-20", "on_demand", base_dir=str(tmp_path))
    path = write_portfolio_snapshot("2026-05-20", data, base_dir=str(tmp_path))
    assert pathlib.Path(path).exists()
    d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    assert d["trigger"] == "on_demand"
    current_path = tmp_path / "findings" / "portfolio_snapshot_current.json"
    assert current_path.exists()
    current = json.loads(current_path.read_text(encoding="utf-8"))
    assert current["trigger"] == "on_demand"


def test_generate_rebalancing_suggestions_high_leverage():
    """leverage_ratio > 2.5 → reduce_leverage high"""
    from stock_team.core.portfolio_weekly import generate_rebalancing_suggestions
    snapshot = {
        "totals": {"leverage_ratio": 2.8, "total_exposure": 50000.0},
        "sector": {"top_sector_pct": 50.0, "top_sector": "Tech"},
        "correlation": {"top_pair": ["NVDA", "AAPL"], "top_pair_value": 0.7},
        "positions_detail": [{"sym": "NVDA", "dist_to_stop_pct": 10.0}],
        "strategic_alignment": {"memo_expiry_alerts": [], "stance_misalign": []},
    }
    suggs = generate_rebalancing_suggestions(snapshot)
    types = [s["type"] for s in suggs]
    assert "reduce_leverage" in types
    assert any(s["priority"] == "high" for s in suggs if s["type"] == "reduce_leverage")


def test_generate_rebalancing_suggestions_clean():
    """一切正常 → 空建议列表"""
    from stock_team.core.portfolio_weekly import generate_rebalancing_suggestions
    snapshot = {
        "totals": {"leverage_ratio": 1.2, "total_exposure": 10000.0},
        "sector": {"top_sector_pct": 40.0, "top_sector": "Tech"},
        "correlation": {"top_pair": ["NVDA", "AAPL"], "top_pair_value": 0.5},
        "positions_detail": [{"sym": "NVDA", "dist_to_stop_pct": 10.0}],
        "strategic_alignment": {"memo_expiry_alerts": [], "stance_misalign": []},
    }
    suggs = generate_rebalancing_suggestions(snapshot)
    assert suggs == []


def test_build_exposure_trend_first_week(tmp_path):
    """首周无上周文件 → null 字段，不报错"""
    from stock_team.core.portfolio_weekly import build_exposure_trend
    totals = {"leverage_ratio": 1.5, "total_exposure": 20000.0}
    trend = build_exposure_trend(2026, 21, totals, base_dir=str(tmp_path))
    assert trend["leverage_ratio_prev"] is None
    assert trend["exposure_chg_pct"] is None
    assert trend["leverage_ratio_curr"] == 1.5


def test_build_portfolio_weekly_schema(tmp_path):
    """build_portfolio_weekly 返回 snapshot + 额外字段"""
    from stock_team.core.portfolio_weekly import build_portfolio_weekly
    # 写入 portfolio_snapshot_today.json
    date = "2026-05-20"
    snapshot = {
        "date": date, "generated_at": "2026-05-20T16:00:00Z",
        "trigger": "weekly_sub",
        "positions_detail": [{"sym": "NVDA", "dist_to_stop_pct": 10.0,
                               "cur_price": 200.0}],
        "totals": {"leverage_ratio": 1.2, "total_exposure": 10000.0},
        "sector": {"top_sector_pct": 60.0, "top_sector": "Tech"},
        "correlation": {"top_pair": ["NVDA", "A"], "top_pair_value": 0.5},
        "strategic_alignment": {"memo_expiry_alerts": [], "stance_misalign": []},
        "warnings": [],
    }
    snap_path = tmp_path / "findings" / f"portfolio_snapshot_{date}.json"
    snap_path.parent.mkdir(parents=True)
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False))

    # 写入 positions.json
    pos_file = tmp_path / "config" / "positions.json"
    pos_file.parent.mkdir(parents=True)
    pos_file.write_text(json.dumps({
        "positions": {"NVDA": {"cost": 180.0, "shares": 10, "date": "2026-05-12",
                                "thesis_status": "intact"}},
        "_excluded": [],
    }))

    weekly = build_portfolio_weekly(date, year=2026, week=21, base_dir=str(tmp_path))
    # 应包含 snapshot 所有字段 + 额外字段
    assert "week_performance" in weekly
    assert "thesis_changes" in weekly
    assert "signal_accuracy_week" in weekly
    assert "exposure_trend" in weekly
    assert "rebalancing_suggestions" in weekly
    assert "llm_summary" in weekly
