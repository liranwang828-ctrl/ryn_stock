"""
Dashboard 写入模块 — dashboard_writer.py
读取所有 B 级 JSON，生成 reports/daily_dashboard_{date}.html。

用法: python3.12 agents/dashboard_writer.py
     或由 poll.py 每轮末尾调用 write_dashboard()
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")
TPL_DIR  = os.path.join(BASE, "templates")
RPT_DIR  = os.path.join(BASE, "reports")


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _read_last_jsonl(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)
                except Exception:
                    pass
    return last


def _read_all_jsonl(path: str) -> list[dict]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


# ── 数据加载函数 ──────────────────────────────────────────────────────────────

def load_premarket_summaries(date: str, symbols: list[str],
                              find_dir: str = FIND_DIR) -> dict:
    """返回 {sym: premarket_summary_dict}"""
    result = {}
    for sym in symbols:
        path = os.path.join(find_dir, f"premarket_summary_{date}_{sym}.json")
        d = _load(path)
        if d:
            result[sym] = d
    return result


def load_intraday_latest(date: str, symbols: list[str],
                          find_dir: str = FIND_DIR) -> dict:
    """返回 {sym: 最新一条 JSONL 记录}"""
    result = {}
    for sym in symbols:
        path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym}.jsonl")
        last = _read_last_jsonl(path)
        if last:
            result[sym] = last
    return result


def load_intraday_events(date: str, symbols: list[str],
                          find_dir: str = FIND_DIR) -> list[dict]:
    """返回所有 llm_triggered=True 的 JSONL 记录（按时间排序）"""
    events = []
    for sym in symbols:
        path = os.path.join(find_dir, f"intraday_snapshot_{date}_{sym}.jsonl")
        for rec in _read_all_jsonl(path):
            if rec.get("meta", {}).get("llm_triggered"):
                events.append(rec)
    events.sort(key=lambda r: r.get("ts", ""))
    return events


def load_portfolio_snapshot(date: str, find_dir: str = FIND_DIR) -> dict:
    path = os.path.join(find_dir, f"portfolio_snapshot_{date}.json")
    if not os.path.exists(path):
        try:
            from agents.portfolio_snapshot import build_portfolio_snapshot, write_portfolio_snapshot
            base_dir = os.path.dirname(find_dir)
            data = build_portfolio_snapshot(date, trigger="on_demand", base_dir=base_dir)
            if data and data.get("totals", {}).get("total_value", 0.0) > 0.0:
                write_portfolio_snapshot(date, data, base_dir=base_dir)
                return data
        except Exception as e:
            print(f"[dashboard_writer] Dynamic portfolio snapshot build failed for {date}: {e}")
    return _load(path)


def load_postmarket_day(date: str, find_dir: str = FIND_DIR) -> dict:
    path = os.path.join(find_dir, f"postmarket_summary_{date}.json")
    return _load(path)


def load_session_state(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, "learning", f"session_state_{date}.json")
    return _load(path)


def load_daily_plan(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, f"daily_plan_{date}.json")
    return _load(path)


# ── 上下文构建 ────────────────────────────────────────────────────────────────

def build_dashboard_context(date: str, symbols: list[str] | None = None,
                             base_dir: str = BASE) -> dict:
    """构建 Jinja2 渲染上下文"""
    find_dir = os.path.join(base_dir, "findings")

    if symbols is None:
        pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
        excluded = set(pos_data.get("_excluded", []))
        all_syms = [s for s in pos_data.get("positions", {}).keys() if s not in excluded]
        cfg = _load(os.path.join(base_dir, "config", "poll_config.json"))
        all_syms = list(dict.fromkeys(all_syms + cfg.get("default_symbols", [])))
        
        # 自动感应今日生成的 CIO 报告中包含的自定义股票
        dynamic_syms = []
        rpt_dir = os.path.join(base_dir, "reports")
        if os.path.exists(rpt_dir):
            for f in os.listdir(rpt_dir):
                if f.startswith(f"{date}_") and f.endswith(".html"):
                    sym = f[len(date)+1:-5]
                    # 排除 daily_dashboard 开头的报告
                    if sym and not sym.startswith("daily_dashboard") and sym not in dynamic_syms:
                        dynamic_syms.append(sym.upper())
                        
        all_syms = list(dict.fromkeys(all_syms + dynamic_syms))
        
        # 显示今日有盘前汇总、盘中快照或今日动态生成了报告的标的
        symbols = [s for s in all_syms if
                   os.path.exists(os.path.join(find_dir, f"premarket_summary_{date}_{s}.json")) or
                   os.path.exists(os.path.join(find_dir, f"intraday_snapshot_{date}_{s}.jsonl")) or
                   s in dynamic_syms]
        if not symbols:   # fallback：若无任何数据文件，显示全部
            symbols = all_syms

    premarket    = load_premarket_summaries(date, symbols, find_dir)
    intraday     = load_intraday_latest(date, symbols, find_dir)
    events       = load_intraday_events(date, symbols, find_dir)
    portfolio    = load_portfolio_snapshot(date, find_dir)
    postmarket_d = load_postmarket_day(date, find_dir)
    session_st   = load_session_state(date, base_dir)
    daily_plan   = load_daily_plan(date, base_dir)

    # 检查哪些标的有今日 CIO 报告（按股票号命名）
    rpt_dir = os.path.join(base_dir, "reports")
    cio_reports = {s for s in symbols
                   if os.path.exists(os.path.join(rpt_dir, f"{date}_{s}.html"))}

    # 检查哪些标的有 strategic_memo（直接检查文件存在，不依赖 premarket_summary）
    has_memo_syms = {s for s in symbols
                     if os.path.exists(os.path.join(base_dir, f"strategic_memo_{s}.json"))}

    # 检查哪些标的有今日可读研究报告（report_viewer 生成）
    research_reports = {s for s in symbols
                        if os.path.exists(os.path.join(rpt_dir, f"research_{s}.html"))}

    # 动态扫描所有可用的历史日期以提供延续性支持
    available_dates = set()
    if os.path.exists(find_dir):
        for f in os.listdir(find_dir):
            if f.startswith("portfolio_snapshot_") and f.endswith(".json"):
                d_str = f[len("portfolio_snapshot_"):-5]
                if len(d_str) == 10:
                    available_dates.add(d_str)
            elif f.startswith("premarket_summary_") and f.endswith(".json"):
                parts = f.split("_")
                if len(parts) >= 3:
                    d_str = parts[2]
                    if len(d_str) == 10:
                        available_dates.add(d_str)
    if os.path.exists(base_dir):
        for f in os.listdir(base_dir):
            if f.startswith("daily_plan_") and f.endswith(".json"):
                d_str = f[len("daily_plan_"):-5]
                if len(d_str) == 10:
                    available_dates.add(d_str)
    available_dates.add(date)
    sorted_dates = sorted(list(available_dates), reverse=True)

    # 加载自选股列表
    wl_path = os.path.join(base_dir, "watchlist.json")
    watchlist_list = []
    if os.path.exists(wl_path):
        try:
            with open(wl_path, encoding="utf-8") as f:
                wl_data = json.load(f)
                watchlist_list = wl_data.get("watchlist", [])
        except Exception:
            pass

    # 1. 构建历史净值组合走势 timeline
    portfolio_history = []
    for d_str in sorted(list(available_dates)):
        snap = load_portfolio_snapshot(d_str, find_dir)
        if snap and snap.get("totals"):
            totals = snap["totals"]
            portfolio_history.append({
                "date": d_str,
                "total_value": totals.get("total_value", 0.0),
                "total_exposure": totals.get("total_exposure", 0.0),
                "leverage_ratio": totals.get("leverage_ratio", 1.0),
                "unrealized_pnl_pct": totals.get("total_unrealized_pnl_pct", 0.0)
            })
    if not portfolio_history:
        portfolio_history.append({
            "date": date,
            "total_value": 100000.0,
            "total_exposure": 0.0,
            "leverage_ratio": 1.0,
            "unrealized_pnl_pct": 0.0
        })
    portfolio_history.sort(key=lambda x: x["date"])

    # 2. 扫描 reports/ 目录下所有 CIO 深度辩论及长期研究报告
    all_cio_reports = []
    all_research_reports = []
    rpt_dir = os.path.join(base_dir, "reports")
    if os.path.exists(rpt_dir):
        for f in os.listdir(rpt_dir):
            if f.endswith(".html"):
                if f.startswith("research_"):
                    sym = f[len("research_"):-5].upper()
                    all_research_reports.append({
                        "symbol": sym,
                        "filename": f,
                        "path": f"/reports/{f}"
                    })
                elif len(f) >= 16 and f[4] == '-' and f[7] == '-' and f[10] == '_':
                    parts = f.split("_")
                    d_str = parts[0]
                    sym = "_".join(parts[1:])[:-5].upper()
                    if not sym.startswith("DAILY_DASHBOARD"):
                        all_cio_reports.append({
                            "date": d_str,
                            "symbol": sym,
                            "filename": f,
                            "path": f"/reports/{f}"
                        })
    all_cio_reports.sort(key=lambda x: (x["date"], x["symbol"]), reverse=True)
    all_research_reports.sort(key=lambda x: x["symbol"])

    # 3. 读取 paper_trading 组合的历史交易台账 (仅用于模拟交易台账)
    trades_history_list = []
    trades_path = os.path.join(base_dir, "paper_trading", "trades.jsonl")
    if os.path.exists(trades_path):
        trades_history_list = _read_all_jsonl(trades_path)
        
    loose_trades_path = os.path.join(base_dir, "paper_trading", "loose", "trades.jsonl")
    loose_trades = []
    if os.path.exists(loose_trades_path):
        loose_trades = _read_all_jsonl(loose_trades_path)
        
    combined_trades = []
    for t in trades_history_list:
        t["acct_label"] = "基准/主账户"
        combined_trades.append(t)
    for t in loose_trades:
        t["acct_label"] = "模拟/宽松"
        combined_trades.append(t)
    combined_trades.sort(key=lambda x: x.get("time", ""), reverse=True)

    # 4. 加载今日关注列表 config/daily_focus.json
    focus_path = os.path.join(base_dir, "config", "daily_focus.json")
    focus_data = _load(focus_path)
    focus_list = [s.upper() for s in focus_data.get("focus_stocks", [])]

    # 5. 加载今日盘前扫描自动推荐 candidates_{date}.json
    candidates_path = os.path.join(base_dir, f"candidates_{date}.json")
    candidates_data = _load(candidates_path)
    candidates_list = candidates_data.get("candidates", [])

    # 6. 读取实盘真实成交台账 knowledge/trading_history.jsonl
    real_trades = []
    th_path = os.path.join(base_dir, "knowledge", "trading_history.jsonl")
    if os.path.exists(th_path):
        with open(th_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        if rec.get("type") in ["buy", "sell", "stop_hit"]:
                            real_trades.append(rec)
                    except Exception:
                        pass
    real_trades.reverse()  # 倒序，最新在最上

    # 7. 加载可用现金并动态计算 NAV (总净资产) 与组合权重
    pos_path = os.path.join(base_dir, "config", "positions.json")
    pos_data = _load(pos_path)
    cash_val = float(pos_data.get("cash", 7034.90))

    holdings_value = 0.0
    if portfolio and "positions_detail" in portfolio:
        for d in portfolio["positions_detail"]:
            holdings_value += float(d.get("market_value", 0.0))
    nav_val = holdings_value + cash_val

    if portfolio and "totals" in portfolio:
        portfolio["totals"]["total_value"] = nav_val
        portfolio["totals"]["cash"] = cash_val
        portfolio["totals"]["holdings_value"] = holdings_value
        # 杠杆计算 = 总敞口 / NAV
        tot_exp = float(portfolio["totals"].get("total_exposure", 0.0))
        portfolio["totals"]["leverage_ratio"] = round(tot_exp / nav_val, 2) if nav_val > 0 else 0.0
        # VaR 百分比计算
        var_loss = float(portfolio["totals"].get("var_5pct_loss", 0.0))
        portfolio["totals"]["var_5pct_pct"] = round(var_loss / nav_val * 100, 1) if nav_val > 0 else 0.0

    # 8. 加载模拟盘账户数据
    loose_portfolio = _load(os.path.join(base_dir, "paper_trading", "loose", "portfolio.json"))
    benchmark_portfolio = _load(os.path.join(base_dir, "paper_trading", "portfolio.json"))

    # 9. 加载 yfinance 数据健康状态
    yf_status_path = os.path.join(base_dir, "logs", "yfinance_status.json")
    data_health = {"status": "stable", "errors": []}
    if os.path.exists(yf_status_path):
        try:
            with open(yf_status_path, "r", encoding="utf-8") as f:
                data_health = json.load(f)
        except Exception:
            pass

    # 读取服务器实际运行的端口
    server_port = 8080
    try:
        port_path = os.path.join(base_dir, "config", "server_port.json")
        if os.path.exists(port_path):
            with open(port_path, "r", encoding="utf-8") as pf:
                port_data = json.load(pf)
                server_port = port_data.get("port", 8080)
    except Exception:
        pass

    # 10. 构建每只标的的三态报告状态 + macro_strategy 节点 + premarket 详情
    report_status = {}
    macro_nodes_all = {}
    premarket_details = {}
    rpt_d = os.path.join(base_dir, "reports")
    for s in symbols:
        sym_upper = s.upper()
        memo_path = os.path.join(base_dir, f"strategic_memo_{sym_upper}.json")
        macro_path = os.path.join(base_dir, f"macro_strategy_{sym_upper}.json")
        prem_path = os.path.join(find_dir, f"premarket_summary_{date}_{sym_upper}.json")
        cio_rpt = os.path.join(rpt_d, f"{date}_{sym_upper}.html") if os.path.exists(rpt_d) else ""

        status = {
            "has_cio": os.path.exists(cio_rpt) if cio_rpt else False,
            "has_memo": os.path.exists(memo_path),
            "has_macro_nodes": os.path.exists(macro_path),
            "has_premarket_summary": os.path.exists(prem_path),
        }
        report_status[sym_upper] = status

        if os.path.exists(macro_path):
            try:
                with open(macro_path, encoding="utf-8") as f:
                    ms = json.load(f)
                    macro_nodes_all[sym_upper] = ms.get("nodes", {})
            except Exception:
                pass

        if os.path.exists(prem_path):
            try:
                with open(prem_path, encoding="utf-8") as f:
                    premarket_details[sym_upper] = json.load(f)
            except Exception:
                pass

    # 补充流入中心：将已有 premarket_summary 但不在候选列表的标的注入
    for sym_upper, status in report_status.items():
        if status.get("has_premarket_summary") and sym_upper not in [c.get("sym","") for c in candidates_list]:
            candidates_list.append({"sym": sym_upper, "score": 0, "recent_2d": 0, "reasons": ["已有盘前分析"]})

    return {
        "report_status":          report_status,
        "macro_nodes":            macro_nodes_all,
        "premarket_details":      premarket_details,
        "date":                   date,
        "generated_at":           datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "data_health":            data_health,
        "symbols":                symbols,
        "premarket":              premarket,
        "intraday":               intraday,
        "events":                 events,
        "portfolio":              portfolio,
        "postmarket_day":         postmarket_d,
        "session_state":          session_st,
        "daily_plan":             daily_plan,
        "cio_reports":            cio_reports,
        "has_memo_syms":          has_memo_syms,
        "research_reports":       research_reports,
        "available_dates":        sorted_dates,
        "watchlist":              watchlist_list,
        "portfolio_history_json": json.dumps(portfolio_history),
        "all_cio_reports":        all_cio_reports,
        "all_research_reports":   all_research_reports,
        "trades_history":         combined_trades, # 模拟盘台账
        "focus_list":             focus_list,      # 今日关注列表
        "candidates_list":        candidates_list,  # 盘前扫描候选股
        "real_trades":            real_trades,     # 实盘真实交易台账
        "cash":                   cash_val,
        "nav":                    nav_val,
        "positions_config":       pos_data,        # 实盘持仓配置元数据
        "loose_portfolio":        loose_portfolio,  # 模拟宽松组合
        "benchmark_portfolio":    benchmark_portfolio, # 模拟基准组合
        "server_port":            server_port,     # 仪表盘后端运行端口
    }


# ── HTML 生成 ─────────────────────────────────────────────────────────────────

def write_dashboard(date: str, symbols: list[str] | None = None,
                    base_dir: str = BASE) -> str:
    """生成 daily_dashboard_{date}.html，返回路径"""
    try:
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(os.path.join(base_dir, "templates")),
                          autoescape=False,
                          auto_reload=True, cache_size=0)
        tmpl = env.get_template("daily_dashboard.html.j2")
    except Exception as e:
        return f"[dashboard_writer] Jinja2 加载失败: {e}"

    ctx  = build_dashboard_context(date, symbols, base_dir)
    html = tmpl.render(**ctx)

    os.makedirs(os.path.join(base_dir, "reports"), exist_ok=True)
    path = os.path.join(base_dir, "reports", f"daily_dashboard_{date}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main():
    date_str = _date.today().strftime("%Y-%m-%d")
    path = write_dashboard(date_str)
    print(f"Dashboard: {path}")


if __name__ == "__main__":
    main()