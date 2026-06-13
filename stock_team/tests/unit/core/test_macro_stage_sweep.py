import json
from datetime import date, timedelta
from pathlib import Path


def _write_daily(path: Path, closes: list[float], volumes: list[int] | None = None) -> None:
    volumes = volumes or [1000] * len(closes)
    rows = ["Date,Open,High,Low,Close,Volume"]
    for i, (close, volume) in enumerate(zip(closes, volumes), start=1):
        rows.append(f"2024-01-{i:02d},{close},{close + 1},{close - 1},{close},{volume}")
    path.write_text("\n".join(rows), encoding="utf-8")


def _write_daily_from(path: Path, closes: list[float], start: date, volumes: list[int] | None = None) -> None:
    volumes = volumes or [1000] * len(closes)
    rows = ["Date,Open,High,Low,Close,Volume"]
    for offset, (close, volume) in enumerate(zip(closes, volumes)):
        day = start + timedelta(days=offset)
        rows.append(f"{day.isoformat()},{close},{close + 1},{close - 1},{close},{volume}")
    path.write_text("\n".join(rows), encoding="utf-8")


def test_macro_stage_sweep_uses_forward_returns_not_intraday_exits(tmp_path):
    from stock_team.backtest.macro_stage_sweep import run_daily_macro_stage_sweep

    cache = tmp_path / "learning"
    cache.mkdir()
    qqq_closes = [100 + i for i in range(30)]
    _write_daily(cache / "daily_cache_QQQ.csv", qqq_closes)
    _write_daily(cache / "daily_cache_^VIX.csv", [16 - min(i * 0.1, 3) for i in range(30)])
    _write_daily(cache / "daily_cache_SPY.csv", qqq_closes)
    _write_daily(cache / "daily_cache_MU.csv", [50 + i * 1.5 for i in range(30)])

    result = run_daily_macro_stage_sweep(
        cache_dir=cache,
        symbols=["MU"],
        date_range={"start": "2024-01-01", "end": "2024-01-30"},
        gates=[{
            "gate_id": "macro_uptrend_rs_v1",
            "conditions": {
                "qqq_regime": ["qqq_uptrend"],
                "vix_regime": ["vix_low_falling"],
                "min_symbol_rs20": -10.0,
            },
        }],
    )

    gate = result["gates"][0]
    assert result["packet_type"] == "macro_stage_sweep_evidence_packet"
    assert result["outcome_horizons"] == ["fwd_3d", "fwd_5d", "fwd_10d", "fwd_20d"]
    assert gate["metrics"]["fwd_3d"]["n_events"] > 0
    assert gate["boundaries"]["uses_intraday_exit"] is False
    assert gate["boundaries"]["uses_fixed_take_profit_stop_loss"] is False
    assert gate["boundaries"]["forces_same_day_exit"] is False
    assert "stop_loss_pct" not in json.dumps(result)
    assert "take_profit_pct" not in json.dumps(result)


def test_candidate_pool_prefers_watchlist_then_liquid_cache(tmp_path):
    from stock_team.backtest.macro_stage_sweep import load_candidate_pool

    cache = tmp_path / "learning"
    cache.mkdir()
    for symbol in ["A", "B", "C", "D"]:
        (cache / f"daily_cache_{symbol}.csv").write_text("Date,Open,High,Low,Close,Volume\n", encoding="utf-8")
    (cache / "daily_cache_QQQ.csv").write_text("Date,Open,High,Low,Close,Volume\n", encoding="utf-8")
    watchlist = tmp_path / "master_watchlist.json"
    watchlist.write_text(json.dumps({"watchlist": {"C": {}, "A": {}}}), encoding="utf-8")

    pool = load_candidate_pool(cache_dir=cache, watchlist_path=watchlist, limit=3)

    assert pool == ["C", "A", "B"]


def test_candidate_pool_reads_nested_watchlist_sections(tmp_path):
    from stock_team.backtest.macro_stage_sweep import load_candidate_pool

    cache = tmp_path / "learning"
    cache.mkdir()
    for symbol in ["NVDA", "MU", "AAPL", "B"]:
        (cache / f"daily_cache_{symbol}.csv").write_text("Date,Open,High,Low,Close,Volume\n", encoding="utf-8")
    watchlist = tmp_path / "watchlist_permanent.json"
    watchlist.write_text(
        json.dumps({
            "quality_stable": {"NVDA": {}, "MU": {}},
            "pending_review": {"AAPL": {}},
        }),
        encoding="utf-8",
    )

    pool = load_candidate_pool(cache_dir=cache, watchlist_path=watchlist, limit=4)

    assert pool[:3] == ["NVDA", "MU", "AAPL"]


def test_daily_reader_handles_mixed_timezone_dates(tmp_path):
    from stock_team.backtest.macro_stage_sweep import _read_daily

    path = tmp_path / "daily_cache_MIX.csv"
    path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2024-11-01 00:00:00-04:00,100,101,99,100,1000\n"
        "2024-11-04 00:00:00-05:00,101,102,100,101,1100\n",
        encoding="utf-8",
    )

    frame = _read_daily(path, {"start": "2024-11-01", "end": "2024-11-04"})

    assert frame["date"].tolist() == ["2024-11-01", "2024-11-04"]


def test_macro_stage_sweep_falls_back_to_qqq_volume_when_spy_cache_missing(tmp_path):
    from stock_team.backtest.macro_stage_sweep import render_markdown, run_daily_macro_stage_sweep

    cache = tmp_path / "learning"
    cache.mkdir()
    qqq_closes = [100 + i for i in range(30)]
    _write_daily(cache / "daily_cache_QQQ.csv", qqq_closes, volumes=[1000 + i * 20 for i in range(30)])
    _write_daily(cache / "daily_cache_^VIX.csv", [15] * 30)
    _write_daily(cache / "daily_cache_MU.csv", [50 + i for i in range(30)])

    result = run_daily_macro_stage_sweep(
        cache_dir=cache,
        symbols=["MU"],
        date_range={"start": "2024-01-01", "end": "2024-01-30"},
        gates=[{"gate_id": "macro_any_v1", "conditions": {"qqq_regime": ["qqq_uptrend"]}}],
    )

    assert result["data_warnings"] == ["volume_proxy_fallback_to_qqq"]
    assert "volume_proxy_fallback_to_qqq" in render_markdown(result)
    assert result["gates"][0]["metrics"]["fwd_3d"]["n_events"] > 0


def test_macro_stage_sweep_reports_forward_mae_mfe(tmp_path):
    from stock_team.backtest.macro_stage_sweep import run_daily_macro_stage_sweep

    cache = tmp_path / "learning"
    cache.mkdir()
    qqq_closes = [100 + i for i in range(30)]
    _write_daily(cache / "daily_cache_QQQ.csv", qqq_closes)
    _write_daily(cache / "daily_cache_^VIX.csv", [15] * 30)
    _write_daily(cache / "daily_cache_MU.csv", [50 + i * 2 for i in range(30)])

    result = run_daily_macro_stage_sweep(
        cache_dir=cache,
        symbols=["MU"],
        date_range={"start": "2024-01-01", "end": "2024-01-30"},
        gates=[{"gate_id": "macro_any_v1", "conditions": {"qqq_regime": ["qqq_uptrend"]}}],
    )

    metrics = result["gates"][0]["metrics"]["fwd_5d"]
    assert metrics["avg_mae_pct"] is not None
    assert metrics["avg_mfe_pct"] is not None


def test_macro_stage_sweep_reuses_legacy_macro_metrics_and_benchmark_alpha(tmp_path):
    from stock_team.backtest.macro_stage_sweep import run_daily_macro_stage_sweep

    cache = tmp_path / "learning"
    cache.mkdir()
    qqq_closes = [100 + i * 0.5 for i in range(80)]
    _write_daily_from(cache / "daily_cache_QQQ.csv", qqq_closes, date(2024, 1, 1))
    _write_daily_from(cache / "daily_cache_^VIX.csv", [15] * 80, date(2024, 1, 1))
    _write_daily_from(cache / "daily_cache_MU.csv", [50 + i * 1.0 for i in range(80)], date(2024, 1, 1))

    result = run_daily_macro_stage_sweep(
        cache_dir=cache,
        symbols=["MU"],
        date_range={"start": "2024-01-01", "end": "2024-03-20"},
        gates=[{"gate_id": "macro_any_v1", "conditions": {"qqq_regime": ["qqq_uptrend"]}}],
    )

    metrics = result["gates"][0]["metrics"]["fwd_10d"]
    assert metrics["metric_source"] == "backtest_macro.compute_metrics"
    assert metrics["sortino"] is not None
    assert metrics["sharpe_proxy"] is not None
    assert metrics["max_drawdown"] is not None
    assert metrics["max_drawdown_basis"] == "legacy_event_sequence_not_portfolio_equity"
    assert metrics["alpha_vs_qqq_pct"] > 0


def test_macro_stage_sweep_reports_windows_oos_and_overfit_diagnostics(tmp_path):
    from stock_team.backtest.macro_stage_sweep import run_daily_macro_stage_sweep

    cache = tmp_path / "learning"
    cache.mkdir()
    dates = [f"2023-01-{i:02d}" for i in range(1, 29)] + [f"2024-01-{i:02d}" for i in range(1, 29)]

    def write_with_dates(path: Path, closes: list[float]) -> None:
        rows = ["Date,Open,High,Low,Close,Volume"]
        for date, close in zip(dates, closes):
            rows.append(f"{date},{close},{close + 1},{close - 1},{close},1000")
        path.write_text("\n".join(rows), encoding="utf-8")

    write_with_dates(cache / "daily_cache_QQQ.csv", [100 + i for i in range(len(dates))])
    write_with_dates(cache / "daily_cache_^VIX.csv", [15] * len(dates))
    write_with_dates(cache / "daily_cache_MU.csv", [50 + i * 1.5 for i in range(len(dates))])

    result = run_daily_macro_stage_sweep(
        cache_dir=cache,
        symbols=["MU"],
        date_range={"start": "2023-01-01", "end": "2024-01-28"},
        gates=[{"gate_id": "macro_any_v1", "conditions": {"min_symbol_rs20": -10.0}}],
    )

    diagnostics = result["gates"][0]["diagnostics"]
    assert "yearly_windows" in diagnostics
    assert "2023" in diagnostics["yearly_windows"]
    assert "2024" in diagnostics["yearly_windows"]
    assert diagnostics["walk_forward_oos"]["method"] == "anchored_time_split"
    assert diagnostics["walk_forward_oos"]["test"]["n_events"] > 0
    assert diagnostics["overfit_risk"]["sample_size_ok"] is not None
    assert diagnostics["overfit_risk"]["oos_degradation_pct"] is not None


def test_macro_stage_markdown_renders_research_grade_fields(tmp_path):
    from stock_team.backtest.macro_stage_sweep import render_markdown, run_daily_macro_stage_sweep

    cache = tmp_path / "learning"
    cache.mkdir()
    _write_daily_from(cache / "daily_cache_QQQ.csv", [100 + i for i in range(80)], date(2024, 1, 1))
    _write_daily_from(cache / "daily_cache_^VIX.csv", [15] * 80, date(2024, 1, 1))
    _write_daily_from(cache / "daily_cache_MU.csv", [50 + i * 1.5 for i in range(80)], date(2024, 1, 1))
    result = run_daily_macro_stage_sweep(
        cache_dir=cache,
        symbols=["MU"],
        date_range={"start": "2024-01-01", "end": "2024-03-20"},
        gates=[{"gate_id": "macro_any_v1", "conditions": {"qqq_regime": ["qqq_uptrend"]}}],
    )

    markdown = render_markdown(result)

    assert "alpha_vs_qqq_pct" in markdown
    assert "sortino" in markdown
    assert "sharpe_proxy" in markdown
    assert "max_drawdown" in markdown
    assert "walk_forward_oos" in markdown
    assert "overfit_risk" in markdown


def test_benchmark_forward_returns_use_qqq_calendar_not_symbol_rows(tmp_path):
    from stock_team.backtest.macro_stage_sweep import _build_market_context, _build_symbol_context, _read_daily

    cache = tmp_path / "learning"
    cache.mkdir()
    (cache / "daily_cache_QQQ.csv").write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2024-01-01,100,101,99,100,1000\n"
        "2024-01-03,110,111,109,110,1000\n"
        "2024-01-05,121,122,120,121,1000\n"
        "2024-01-07,133.1,134,132,133.1,1000\n",
        encoding="utf-8",
    )
    (cache / "daily_cache_^VIX.csv").write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2024-01-01,15,15,15,15,1000\n"
        "2024-01-03,15,15,15,15,1000\n"
        "2024-01-05,15,15,15,15,1000\n"
        "2024-01-07,15,15,15,15,1000\n",
        encoding="utf-8",
    )
    _write_daily_from(cache / "daily_cache_MU.csv", [50 + i for i in range(10)], date(2024, 1, 1))
    date_range = {"start": "2024-01-01", "end": "2024-01-10"}
    qqq = _read_daily(cache / "daily_cache_QQQ.csv", date_range)
    vix = _read_daily(cache / "daily_cache_^VIX.csv", date_range)
    market = _build_market_context(qqq, vix, qqq)

    frame = _build_symbol_context("MU", _read_daily(cache / "daily_cache_MU.csv", date_range), qqq, market)

    first = frame[frame["date"] == "2024-01-01"].iloc[0]
    assert round(first["qqq_fwd_3d"], 3) == 33.1


def test_macro_stage_sweep_reports_bull_bear_market_cycle_windows(tmp_path):
    from stock_team.backtest.macro_stage_sweep import render_markdown, run_daily_macro_stage_sweep

    cache = tmp_path / "learning"
    cache.mkdir()
    qqq_closes = [160 - i * 0.5 for i in range(90)] + [115 + i * 0.7 for i in range(90)]
    symbol_closes = [80 - i * 0.3 for i in range(90)] + [53 + i * 1.0 for i in range(90)]
    _write_daily_from(cache / "daily_cache_QQQ.csv", qqq_closes, date(2023, 1, 1))
    _write_daily_from(cache / "daily_cache_^VIX.csv", [24] * 80 + [16] * 100, date(2023, 1, 1))
    _write_daily_from(cache / "daily_cache_MU.csv", symbol_closes, date(2023, 1, 1))

    result = run_daily_macro_stage_sweep(
        cache_dir=cache,
        symbols=["MU"],
        date_range={"start": "2023-01-01", "end": "2023-06-29"},
        gates=[{"gate_id": "macro_any_v1", "conditions": {"min_symbol_rs20": -100.0}}],
    )

    cycle_windows = result["gates"][0]["diagnostics"]["market_cycle_windows"]
    assert "bear_market" in cycle_windows
    assert "bull_market" in cycle_windows
    assert cycle_windows["bear_market"]["n_events"] > 0
    assert cycle_windows["bull_market"]["n_events"] > 0
    markdown = render_markdown(result)
    assert "market_cycle_windows" in markdown
    assert "bull_market" in markdown
    assert "bear_market" in markdown


def test_cycle_factor_search_ranks_candidates_by_cycle_alpha_and_oos(tmp_path):
    from stock_team.backtest.macro_stage_sweep import run_cycle_factor_search

    cache = tmp_path / "learning"
    cache.mkdir()
    qqq_closes = [160 - i * 0.4 for i in range(100)] + [120 + i * 0.8 for i in range(120)]
    strong = [80 - i * 0.1 for i in range(100)] + [70 + i * 1.4 for i in range(120)]
    weak = [80 - i * 0.8 for i in range(100)] + [30 + i * 0.3 for i in range(120)]
    _write_daily_from(cache / "daily_cache_QQQ.csv", qqq_closes, date(2022, 1, 1))
    _write_daily_from(cache / "daily_cache_^VIX.csv", [24] * 100 + [15] * 120, date(2022, 1, 1))
    _write_daily_from(cache / "daily_cache_STRONG.csv", strong, date(2022, 1, 1))
    _write_daily_from(cache / "daily_cache_WEAK.csv", weak, date(2022, 1, 1))

    result = run_cycle_factor_search(
        cache_dir=cache,
        symbols=["STRONG", "WEAK"],
        date_range={"start": "2022-01-01", "end": "2022-08-08"},
        max_candidates=5,
    )

    assert result["packet_type"] == "cycle_factor_search_evidence_packet"
    assert result["ranked_candidates"]
    top = result["ranked_candidates"][0]
    assert top["grade"] in {"A", "B"}
    assert top["score"] > 0
    assert top["diagnostics"]["market_cycle_windows"]
    assert top["diagnostics"]["overfit_risk"]["risk_level"] in {"low", "medium", "high"}
    assert top["boundaries"]["contains_permission_decision"] is False
