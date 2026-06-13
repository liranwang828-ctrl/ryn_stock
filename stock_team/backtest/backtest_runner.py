"""
回测统一入口 — backtest_runner.py
串行调用：backtest_macro → backtest_micro structural → backtest_micro intraday
生成对比报告，用户确认后 --apply 写回参数文件。

用法:
  python3.12 agents/backtest_runner.py --years 5
  python3.12 agents/backtest_runner.py --intraday-only --window-days 60
  python3.12 agents/backtest_runner.py --apply findings/backtest_report_YYYY-MM-DD.json
  python3.12 agents/backtest_runner.py --restore findings/params_backup_YYYY-MM-DD.json
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date as _date

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
CFG_DIR  = os.path.join(BASE, "config")
FIND_DIR = os.path.join(BASE, "findings")


def _load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _backup_params(date_str: str) -> str:
    """写回前备份当前所有参数"""
    backup = {
        "macro_strategy_params": _load_json(os.path.join(CFG_DIR, "macro_strategy_params.json")),
        "micro_strategy_params": _load_json(os.path.join(CFG_DIR, "micro_strategy_params.json")),
        "evolution_per_sym":     {},
    }
    for path in glob.glob(os.path.join(BASE, "macro_strategy_*.json")):
        sym = os.path.basename(path).replace("macro_strategy_", "").replace(".json", "")
        if "_prev" not in sym:
            d = _load_json(path)
            backup["evolution_per_sym"][sym] = d.get("evolution", {})

    bak_path = os.path.join(FIND_DIR, f"params_backup_{date_str}.json")
    _save_json(bak_path, backup)
    print(f"[runner] 参数已备份至 {bak_path}")
    return bak_path


def apply_results(report_path: str):
    """将回测报告中的推荐参数写回配置文件"""
    report   = _load_json(report_path)
    date_str = str(_date.today())
    _backup_params(date_str)

    macro_recs = (report.get("macro_backtest", {})
                  .get("best_params", {})
                  .get("params", {}))
    if macro_recs:
        macro_cfg = _load_json(os.path.join(CFG_DIR, "macro_strategy_params.json"))
        mr = macro_cfg.setdefault("market_regime", {})
        for k in ["vix_panic_threshold", "ma20_dev_veto_pct",
                  "qqq5m_veto", "vix_ts_threshold"]:
            if k in macro_recs:
                mr[k] = macro_recs[k]
        _save_json(os.path.join(CFG_DIR, "macro_strategy_params.json"), macro_cfg)
        print("[runner] ✅ macro_strategy_params.json 已更新")

    structural = report.get("micro_structural", {}).get("structural", {})
    for sym, sym_data in structural.items():
        best = sym_data.get("best_params")
        if not best:
            continue
        path = os.path.join(BASE, f"macro_strategy_{sym.upper()}.json")
        if not os.path.exists(path):
            continue
        macro = _load_json(path)
        ev = macro.setdefault("evolution", {})
        ev.update({k: v for k, v in best["params"].items()
                   if k in ("k1", "k2", "k3", "k4", "k5", "k6")})
        ev["last_backtest_date"] = date_str
        _save_json(path, macro)
        print(f"[runner] ✅ macro_strategy_{sym}.json evolution 已更新")

    intraday_recs = report.get("micro_intraday", {}).get("best_global_params", {})
    if intraday_recs:
        micro_cfg = _load_json(os.path.join(CFG_DIR, "micro_strategy_params.json"))
        fs = micro_cfg.setdefault("flex_signals", {})
        for k in ["rsi14_5m_oversold", "vwap_add_threshold",
                  "vol_ratio_shrink", "min_signals_required"]:
            if k in intraday_recs:
                fs[k] = intraday_recs[k]
        _save_json(os.path.join(CFG_DIR, "micro_strategy_params.json"), micro_cfg)
        print("[runner] ✅ micro_strategy_params.json 已更新")

    print(f"\n[runner] 如需恢复: python3.12 agents/backtest_runner.py --restore findings/params_backup_{date_str}.json")


def restore_params(backup_path: str):
    """从备份恢复参数"""
    backup = _load_json(backup_path)
    _save_json(os.path.join(CFG_DIR, "macro_strategy_params.json"),
               backup.get("macro_strategy_params", {}))
    _save_json(os.path.join(CFG_DIR, "micro_strategy_params.json"),
               backup.get("micro_strategy_params", {}))
    for sym, ev in backup.get("evolution_per_sym", {}).items():
        path = os.path.join(BASE, f"macro_strategy_{sym.upper()}.json")
        if os.path.exists(path):
            macro = _load_json(path)
            macro["evolution"] = ev
            _save_json(path, macro)
    print(f"[runner] ✅ 参数已从 {backup_path} 恢复")


def _print_summary(report: dict):
    """打印人类可读摘要"""
    print("\n" + "═" * 60)
    print("  回测结果摘要")
    print("═" * 60)

    best_m = report.get("macro_backtest", {}).get("best_params", {})
    if best_m:
        m = best_m.get("metrics", {})
        print(f"\n【宏观策略最优参数】")
        print(f"  参数: {best_m.get('params', {})}")
        print(f"  EV={m.get('ev')} 胜率={m.get('win_rate'):.1%} "
              f"Sortino={m.get('sortino'):.2f} 最大回撤={m.get('max_drawdown'):.1%}")

    structural = report.get("micro_structural", {}).get("structural", {})
    if structural:
        print(f"\n【微观结构位最优参数（各标的）】")
        for sym, d in structural.items():
            best = d.get("best_params")
            if best:
                from stock_team.backtest.backtest_micro import _get_leverage_factor
                lev = _get_leverage_factor(sym)
                lev_str = f" ({lev}x杠杆)" if lev > 1 else ""
                print(f"  {sym}{lev_str}: k1={best['params'].get('k1')} "
                      f"k_tp={best['params'].get('k_tp', 2.5)} "
                      f"EV={best['metrics'].get('ev', 0):.4f}")

    intraday = report.get("micro_intraday", {})
    if intraday.get("best_global_params"):
        print(f"\n【盘中信号最优参数】")
        print(f"  参数: {intraday['best_global_params']}")
        print(f"  EV={intraday.get('best_ev', 0):.4f}")

    print("═" * 60)


def run_full_backtest(years: int = 5, window_days: int = 60,
                      intraday_only: bool = False) -> str:
    """串行运行三层回测，保存报告，返回报告路径。"""
    from stock_team.backtest.backtest_macro import run_macro_backtest
    from stock_team.backtest.backtest_micro import run_micro_backtest, run_intraday_backtest

    date_str = str(_date.today())
    report   = {"run_date": date_str, "years": years}

    if not intraday_only:
        print("\n[runner] === Step 1: 宏观策略回测 ===")
        report["macro_backtest"] = run_macro_backtest(years=years)

        print("\n[runner] === Step 2: 微观结构位回测 ===")
        report["micro_structural"] = run_micro_backtest(years=years)

    print(f"\n[runner] === Step 3: 盘中信号回测（{window_days}天）===")
    report["micro_intraday"] = run_intraday_backtest(window_days=window_days)

    report_path = os.path.join(FIND_DIR, f"backtest_report_{date_str}.json")
    os.makedirs(FIND_DIR, exist_ok=True)
    _save_json(report_path, report)

    _print_summary(report)
    print(f"\n[runner] 报告已保存: {report_path}")
    print(f"[runner] 确认写回: python3.12 agents/backtest_runner.py --apply {report_path}")

    return report_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="回测统一入口")
    parser.add_argument("--years",         type=int, default=5)
    parser.add_argument("--window-days",   type=int, default=60, dest="window_days")
    parser.add_argument("--intraday-only", action="store_true", dest="intraday_only")
    parser.add_argument("--apply",         type=str, default=None)
    parser.add_argument("--restore",       type=str, default=None)
    args = parser.parse_args()

    if args.apply:
        apply_results(args.apply)
    elif args.restore:
        restore_params(args.restore)
    else:
        run_full_backtest(years=args.years,
                          window_days=args.window_days,
                          intraday_only=args.intraday_only)
