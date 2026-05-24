# tests/test_backtest_result.py
import sys, os, json
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))


# ── 测试 build_scan_results ──────────────────────────────────────────────

def test_build_scan_results_computes_improvement():
    """build_scan_results 正确计算 improvement_pp 和 win_rate_at_current"""
    from agents.backtest_result import build_scan_results
    # run_portfolio_scan 的模拟返回值
    raw_scan = {
        "ma20_dev_max": {
            "optimal": 0.03, "win_rate": 0.65, "n_samples": 150, "mean_ret": 0.02,
            "scan": [
                {"threshold": 0.03, "win_rate": 0.65, "n": 150, "mean_ret": 0.02},
                {"threshold": 0.05, "win_rate": 0.58, "n": 300, "mean_ret": 0.01},
                {"threshold": 0.08, "win_rate": 0.52, "n": 400, "mean_ret": 0.005},
            ],
        },
        "rs5_min": {
            "optimal": 1.0, "win_rate": 0.62, "n_samples": 80, "mean_ret": 0.015,
            "scan": [
                {"threshold": 0.0, "win_rate": 0.57, "n": 200, "mean_ret": 0.01},
                {"threshold": 1.0, "win_rate": 0.62, "n": 80, "mean_ret": 0.015},
            ],
        },
    }
    # 当前阈值（decision_thresholds.json 的 soft_vetoes）
    current_thresholds = {"ma20_dev_max": 0.05, "rs5_min": 0.0}

    result = build_scan_results(raw_scan, current_thresholds)

    assert "ma20_dev_max" in result
    assert "rs5_min" in result
    ma = result["ma20_dev_max"]
    assert ma["optimal"] == 0.03
    assert ma["current"] == 0.05
    assert ma["win_rate_at_optimal"] == 0.65
    assert abs(ma["win_rate_at_current"] - 0.58) < 0.01  # threshold=0.05 → win_rate=0.58
    assert abs(ma["improvement_pp"] - 7.0) < 0.1  # 65 - 58 = 7pp
    assert ma["sample_size"] == 150


def test_build_scan_results_fallback_to_nearest():
    """当前阈值不在候选列表中时，取最近邻"""
    from agents.backtest_result import build_scan_results
    raw_scan = {
        "ma20_dev_max": {
            "optimal": 0.03, "win_rate": 0.62, "n_samples": 100, "mean_ret": 0.01,
            "scan": [
                {"threshold": 0.03, "win_rate": 0.62, "n": 100, "mean_ret": 0.01},
                {"threshold": 0.06, "win_rate": 0.55, "n": 200, "mean_ret": 0.005},
            ],
        },
    }
    # current = 0.04 不在 [0.03, 0.06] 中，取最近邻 0.03
    result = build_scan_results(raw_scan, {"ma20_dev_max": 0.04})
    assert result["ma20_dev_max"]["win_rate_at_current"] is not None


# ── 测试 should_update_thresholds ─────────────────────────────────────────

def test_should_update_thresholds_triggers():
    """improvement > 5pp AND sample ≥ 20 AND win_rate > 0.55 → triggered"""
    from agents.backtest_result import should_update_thresholds
    scan_results = {
        "ma20_dev_max": {
            "optimal": 0.03, "current": 0.05,
            "win_rate_at_optimal": 0.63, "win_rate_at_current": 0.57,
            "improvement_pp": 6.0, "sample_size": 150,
        },
    }
    updates = should_update_thresholds(scan_results, run_type="full")
    assert len(updates) > 0
    assert updates[0]["param"] == "ma20_dev_max"


def test_should_update_thresholds_not_triggered_small_improvement():
    """improvement < 5pp → 不触发"""
    from agents.backtest_result import should_update_thresholds
    scan_results = {
        "ma20_dev_max": {
            "optimal": 0.04, "current": 0.05,
            "win_rate_at_optimal": 0.59, "win_rate_at_current": 0.57,
            "improvement_pp": 2.0, "sample_size": 150,
        },
    }
    updates = should_update_thresholds(scan_results, run_type="full")
    assert updates == []


def test_should_update_thresholds_incremental_never_updates():
    """incremental 模式永远不更新"""
    from agents.backtest_result import should_update_thresholds
    scan_results = {
        "ma20_dev_max": {
            "optimal": 0.03, "current": 0.05,
            "win_rate_at_optimal": 0.70, "win_rate_at_current": 0.57,
            "improvement_pp": 13.0, "sample_size": 500,
        },
    }
    updates = should_update_thresholds(scan_results, run_type="incremental")
    assert updates == []


# ── 测试 compute_consecutive_low_weeks ────────────────────────────────────

def test_consecutive_low_weeks_counts_correctly(tmp_path):
    """连续 incremental 低于 0.55 的次数计数正确"""
    from agents.backtest_result import compute_consecutive_low_weeks
    log_file = tmp_path / "backtest_log.jsonl"
    # 写入：1 次 full（重置）+ 3 次 incremental low + 1 次 incremental high
    entries = [
        {"run_type": "full",        "win_rate": 0.60, "consecutive_low_weeks": 0},
        {"run_type": "incremental", "win_rate": 0.50, "consecutive_low_weeks": 1},
        {"run_type": "incremental", "win_rate": 0.52, "consecutive_low_weeks": 2},
        {"run_type": "incremental", "win_rate": 0.48, "consecutive_low_weeks": 3},
    ]
    with open(str(log_file), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    count = compute_consecutive_low_weeks(find_dir=str(tmp_path))
    assert count == 3


def test_consecutive_low_weeks_resets_on_full(tmp_path):
    """full 运行后重置为 0"""
    from agents.backtest_result import compute_consecutive_low_weeks
    log_file = tmp_path / "backtest_log.jsonl"
    entries = [
        {"run_type": "incremental", "win_rate": 0.48, "consecutive_low_weeks": 3},
        {"run_type": "full",        "win_rate": 0.60, "consecutive_low_weeks": 0},
    ]
    with open(str(log_file), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    count = compute_consecutive_low_weeks(find_dir=str(tmp_path))
    assert count == 0


# ── 测试 append_backtest_log ──────────────────────────────────────────────

def test_append_backtest_log_creates_and_appends(tmp_path):
    """append_backtest_log 追加不覆盖"""
    from agents.backtest_result import append_backtest_log
    log_path = tmp_path / "backtest_log.jsonl"

    entry1 = {"date": "2026-05-20", "run_type": "full", "win_rate": 0.60,
               "n_entries": 100, "mean_ret_pct": 1.5, "vs_baseline_pp": 8.0,
               "threshold_updated": False, "consecutive_low_weeks": 0,
               "params_snapshot": {"ma20_dev_max": 0.05, "rs5_min": 0.0, "vol_ratio_max": 1.0}}
    entry2 = {**entry1, "date": "2026-05-27", "run_type": "incremental", "win_rate": 0.52}

    append_backtest_log(entry1, find_dir=str(tmp_path))
    append_backtest_log(entry2, find_dir=str(tmp_path))

    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 2
    d1 = json.loads(lines[0])
    assert d1["run_type"] == "full"
    d2 = json.loads(lines[1])
    assert d2["run_type"] == "incremental"


# ── Task 2 测试 ───────────────────────────────────────────────────────────

def test_run_backtest_incremental_schema(tmp_path):
    """run_backtest incremental 返回所有顶层字段，scan_results=null"""
    from unittest.mock import patch
    from agents.backtest_result import run_backtest

    mock_sim = {
        "win_rate": 0.58, "n_entries": 45, "mean_ret_pct": 1.2,
        "symbols": ["NVDA"], "years": 0,
        "thresholds_used": {"ma20_dev_max": 0.05, "rs5_min": 0.0},
        "note": "ok",
    }
    with patch("agents.backtest_result.simulate_decision_framework",
               return_value=mock_sim):
        result = run_backtest(
            symbols=["NVDA"], run_type="incremental",
            years=0, find_dir=str(tmp_path), cfg_dir=str(tmp_path / "config"),
        )

    assert set(result.keys()) == {"meta", "scan_results", "simulate_results",
                                   "threshold_update", "llm_summary"}
    assert result["scan_results"] is None          # incremental = no scan
    assert result["meta"]["run_type"] == "incremental"
    assert result["simulate_results"]["win_rate"] == 0.58


def test_write_backtest_result_creates_file(tmp_path):
    """write_backtest_result 生成 JSON 文件"""
    from agents.backtest_result import write_backtest_result
    import pathlib
    data = {"meta": {"date": "2026-05-20", "run_type": "full"},
            "scan_results": None, "simulate_results": {}, "threshold_update": {},
            "llm_summary": ""}
    path = write_backtest_result("2026-05-20", data, find_dir=str(tmp_path))
    assert pathlib.Path(path).exists()
    d = json.loads(pathlib.Path(path).read_text())
    assert d["meta"]["run_type"] == "full"
