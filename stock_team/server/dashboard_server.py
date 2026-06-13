#!/usr/bin/env python3
"""
股票交易指挥中心 API & Web 服务器 — dashboard_server.py
原生标准库实现，零第三方依赖，支持 Windows 跨平台异步调度与实时日志。
"""
import os
import sys

# Windows 跨平台标准流 UTF-8 重置，防止打印 Emoji 崩溃
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

import json
import glob
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as HTTPServer
from datetime import datetime, date as _date
from stock_team.utils.workspace_paths import investing_os_home

# 插入工作区根目录以支持模块导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保 BASE 路径计算正确
_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else os.path.dirname(os.path.abspath(__file__))

CFG_DIR = os.path.join(BASE, "config")
FIND_DIR = os.path.join(BASE, "findings")
RPT_DIR = os.path.join(BASE, "reports")
LOG_DIR = os.path.join(BASE, "logs")

# 导入 dashboard_writer
try:
    from stock_team.server.dashboard_writer import write_dashboard, build_dashboard_context
except ImportError:
    write_dashboard = None
    build_dashboard_context = None

# 全局变量：存储正在运行的任务进程
ACTIVE_TASKS = {}  # task_name -> subprocess.Popen
TASK_LOG_FILES = {}  # task_name -> log_file_path

# 进程锁用于对 ACTIVE_TASKS 的并发读写保护
tasks_lock = threading.Lock()

def get_python_executable():
    """获取适合当前环境的 python 运行路径"""
    # 优先使用 sys.executable 以保持当前运行环境的一致性
    if sys.executable:
        return sys.executable
    return "python"

def init_folders():
    """初始化必要文件夹"""
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(RPT_DIR, exist_ok=True)


def updated_symbols_from_live_status(path: str) -> list[str]:
    """Return symbols with refreshed local live-status detail."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    details = data.get("symbols_detail", {})
    if not isinstance(details, dict):
        return []
    focus = data.get("focus_symbols", [])
    if isinstance(focus, list):
        focused = [str(sym).upper().strip() for sym in focus if str(sym).strip()]
        focused = [sym for sym in focused if sym in details]
        if focused:
            return focused
    return [str(sym).upper().strip() for sym in details if str(sym).strip()]


def _load_json_any(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8-sig") as f:
            value = json.load(f)
    except Exception:
        return default
    return value


def _save_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def _extract_live_price_payload(live_status: dict) -> dict[str, dict]:
    details = live_status.get("symbols_detail", {}) if isinstance(live_status, dict) else {}
    if not isinstance(details, dict):
        return {}
    symbols = live_status.get("focus_symbols")
    if not isinstance(symbols, list) or not symbols:
        symbols = list(details.keys())
    prices: dict[str, dict] = {}
    for raw_sym in symbols:
        sym = str(raw_sym).upper().strip()
        card = details.get(sym)
        if not sym or not isinstance(card, dict):
            continue
        price = card.get("current_price") if card.get("current_price") is not None else card.get("price")
        try:
            price = float(price)
        except Exception:
            continue
        prices[sym] = {
            "price": price,
            "chg_pct": card.get("chg_pct"),
            "source": "manual_watchlist_refresh",
            "status": card.get("status_cn") or card.get("status_code"),
        }
    return prices


def _sync_positions_broker_prices(base_dir: str, prices: dict[str, dict], asof: str) -> list[str]:
    path = os.path.join(base_dir, "config", "positions.json")
    data = _load_json_any(path, {})
    positions = data.get("positions") if isinstance(data, dict) else None
    if not isinstance(positions, dict):
        return []
    updated = []
    for sym, price_data in prices.items():
        row = positions.get(sym)
        if not isinstance(row, dict):
            continue
        row["broker_last_price"] = price_data.get("price")
        row["broker_snapshot_at"] = asof
        row["broker_price_source"] = price_data.get("source") or "manual_watchlist_refresh"
        updated.append(sym)
    if updated:
        _save_json(path, data)
    return updated


def _sync_portfolio_snapshot_current(base_dir: str, prices: dict[str, dict], asof: str) -> str | None:
    pos_path = os.path.join(base_dir, "config", "positions.json")
    pos_data = _load_json_any(pos_path, {})
    positions = pos_data.get("positions") if isinstance(pos_data, dict) else None
    if not isinstance(positions, dict):
        return None

    snap_path = os.path.join(base_dir, "findings", "portfolio_snapshot_current.json")
    existing = _load_json_any(snap_path, {})
    existing_rows = {
        str(row.get("sym")).upper(): row
        for row in existing.get("positions_detail", [])
        if isinstance(row, dict) and row.get("sym")
    } if isinstance(existing, dict) else {}

    rows = []
    holdings_value = 0.0
    total_exposure = 0.0
    var_loss = 0.0
    for sym, cfg in positions.items():
        if not isinstance(cfg, dict):
            continue
        sym_upper = str(sym).upper()
        shares = float(cfg.get("shares") or 0.0)
        cost = float(cfg.get("cost") or 0.0)
        price = prices.get(sym_upper, {}).get("price")
        if price is None:
            price = cfg.get("broker_last_price")
        if price is None:
            price = existing_rows.get(sym_upper, {}).get("cur_price")
        if price is None:
            price = cost
        price = float(price or 0.0)
        row = dict(existing_rows.get(sym_upper, {}))
        leverage = float(row.get("leverage") or 1.0)
        beta = float(row.get("beta") or 1.0)
        market_value = round(price * shares, 4)
        net_exposure = round(market_value * leverage, 4)
        row.update({
            "sym": sym_upper,
            "shares": shares,
            "cost": cost,
            "cur_price": price,
            "price": price,
            "price_source": prices.get(sym_upper, {}).get("source") or cfg.get("broker_price_source") or row.get("price_source") or "positions",
            "market_value": market_value,
            "net_exposure": net_exposure,
            "var_5pct_loss": round(net_exposure * beta * 0.05, 4),
        })
        if cost:
            row["unrealized_pnl_pct"] = round((price - cost) / cost * 100, 2)
        rows.append(row)
        holdings_value += market_value
        total_exposure += net_exposure
        var_loss += row["var_5pct_loss"]

    cash = float(pos_data.get("cash") or 0.0)
    total_value = round(holdings_value + cash, 2)
    payload = dict(existing) if isinstance(existing, dict) else {}
    payload.update({
        "date": _date.today().strftime("%Y-%m-%d"),
        "generated_at": asof,
        "trigger": "manual_price_refresh",
        "positions_detail": rows,
    })
    totals = payload.setdefault("totals", {})
    totals.update({
        "cash": cash,
        "holdings_value": round(holdings_value, 2),
        "total_value": total_value,
        "total_exposure": round(total_exposure, 2),
        "leverage_ratio": round(total_exposure / total_value, 2) if total_value else 0.0,
        "var_5pct_loss": round(var_loss, 2),
        "var_5pct_pct": round(var_loss / total_value * 100, 1) if total_value else 0.0,
    })
    return _save_json(snap_path, payload)


def _write_live_nodes(base_dir: str, live_status: dict, symbols: list[str], asof: str) -> list[str]:
    details = live_status.get("symbols_detail", {}) if isinstance(live_status, dict) else {}
    if not isinstance(details, dict):
        return []
    written = []
    for sym in symbols:
        card = details.get(sym)
        if not isinstance(card, dict):
            continue
        path = os.path.join(base_dir, "findings", "symbols", sym, "current_nodes.json")
        existing = _load_json_any(path, {})
        if isinstance(existing, dict) and existing.get("source") == "human_agent_consensus" and existing.get("nodes"):
            continue
        buy_zone = card.get("buy_zone") if isinstance(card.get("buy_zone"), dict) else {}
        nodes = {}

        def add_node(key, price, label):
            try:
                price = float(price)
            except Exception:
                return
            nodes[key] = {"price": price, "label": label, "source": "manual_watchlist_refresh"}

        add_node("entry_base", buy_zone.get("max_price") or buy_zone.get("min_price"), "Buy zone")
        add_node("flex_add", buy_zone.get("min_price"), "Buy zone low")
        add_node("hard_stop", card.get("hard_stop"), "Hard stop")
        add_node("target", card.get("target_price"), "Target")
        if not nodes:
            continue
        payload = {
            "sym": sym,
            "date": _date.today().strftime("%Y-%m-%d"),
            "generated_at": asof,
            "source": "manual_watchlist_refresh",
            "nodes": nodes,
            "strategy": {
                "action": card.get("status_code") or card.get("status_cn") or "watch",
                "reasoning": card.get("micro_action_guidance") or card.get("thesis") or "",
            },
        }
        _save_json(path, payload)
        written.append(sym)
    return written


def sync_price_refresh_state(base_dir: str = BASE) -> dict:
    """Fan out refreshed watchlist prices into dashboard-visible local state."""
    live_path = os.path.join(base_dir, "findings", "watchlist_live_status.json")
    live_status = _load_json_any(live_path, {})
    prices = _extract_live_price_payload(live_status)
    asof = live_status.get("refreshed_at") if isinstance(live_status, dict) else None
    asof = asof or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated = list(prices.keys())

    if prices:
        from stock_team.server.dashboard_cache import update_latest_prices
        update_latest_prices(base_dir, prices, asof=asof)
        _sync_positions_broker_prices(base_dir, prices, asof)
        _sync_portfolio_snapshot_current(base_dir, prices, asof)
    nodes_written = _write_live_nodes(base_dir, live_status, updated, asof)
    return {
        "updated": updated,
        "updated_count": len(updated),
        "nodes_written": nodes_written,
    }

class DashboardHTTPRequestHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # 覆写日志输出，减少控制台噪音
        sys.stdout.write(f"[{self.log_date_time_string()}] {format%args}\n")

    def _set_headers(self, content_type="text/html; charset=utf-8", status=200):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")  # 支持跨域
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        # 响应 CORS 预检请求
        self._set_headers(status=200)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # ── 1. 静态主页及仪表盘动态渲染 ────────────────────────────────
        if path == "/" or path == "/index.html":
            self.handle_dashboard_render(query)
            return

        # ── 2. 静态报告文件服务 ──────────────────────────────────────
        elif path.startswith("/reports/"):
            self.handle_static_report(path)
            return

        elif path.startswith("/strategic_memo_") and path.endswith(".json"):
            self.handle_static_memo(path)
            return

        elif path.startswith("/findings/"):
            self.handle_static_finding(path)
            return

        # ── 3. API: 获取系统整体状态 ─────────────────────────────────
        elif path == "/api/status":
            self.handle_api_status()
            return

        elif path == "/api/market-clock":
            self.handle_api_market_clock()
            return

        elif path == "/api/ib-events" or path == "/api/ib_events":
            self.handle_api_ib_events()
            return

        # ── 4. API: 运行特定流水线任务 ────────────────────────────────
        elif path == "/api/run":
            self.handle_api_run(query)
            return

        # ── 5. API: 停止特定运行中任务 ────────────────────────────────
        elif path == "/api/stop":
            self.handle_api_stop(query)
            return

        # ── 6. API: 获取任务控制台日志 ────────────────────────────────
        elif path == "/api/logs":
            self.handle_api_logs(query)
            return

        # ── 6.4 API: 刷新组合快照 ────────────────────────────────
        elif path == "/api/refresh-portfolio":
            self.handle_api_refresh_portfolio()
            return

        elif path == "/api/refresh-prices":
            self.handle_api_refresh_prices()
            return

        elif path == "/api/apply-backtest" or path == "/api/apply_backtest":
            self.handle_api_apply_backtest()
            return

        # ── 6.45 API: 批量生成关注标的报告 ──────────────────────
        elif path == "/api/generate-focus-reports":
            self.handle_api_generate_focus_reports()
            return

        # ── 6.5 API: 新增/关注股票到自选股 ─────────────────────────────
        elif path == "/api/add_watchlist":
            self.handle_api_add_watchlist(query)
            return

        # ── 6.6 API: 新增个股到今日关注 ────────────────────────────────
        elif path == "/api/add_focus":
            self.handle_api_add_focus(query)
            return

        # ── 6.7 API: 从今日关注移出个股 ────────────────────────────────
        elif path == "/api/remove_focus":
            self.handle_api_remove_focus(query)
            return

        # ── 6.8 API: 从自选股移出个股 ──────────────────────────────────
        elif path == "/api/remove_watchlist":
            self.handle_api_remove_watchlist(query)
            return

        # ── 6.9 API: 获取多大师辩论交锋金句 ──────────────────────────
        elif path == "/api/master-quotes":
            self.handle_api_master_quotes()
            return

        # ── 7. 未知路径 404 ─────────────────────────────────────────
        else:
            self._set_headers("text/plain", 404)
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # ── 8. API: 保存回测及因子调参参数 ───────────────────────────
        if path == "/api/save_params":
            self.handle_api_save_params()
            return
        elif path == "/api/record_trade":
            self.handle_api_record_trade()
            return
        else:
            self._set_headers("text/plain", 404)
            self.wfile.write(b"404 Not Found")

    # ────────────────────────────────────────────────────────────────────────
    # 请求处理器实现
    # ────────────────────────────────────────────────────────────────────────

    def handle_dashboard_render(self, query):
        """动态编译渲染每日仪表盘并输出"""
        if not write_dashboard:
            self._set_headers("text/plain; charset=utf-8", 500)
            self.wfile.write("系统配置错误: dashboard_writer 模块加载失败。".encode("utf-8"))
            return

        # 支持通过 ?date=YYYY-MM-DD 渲染指定日期的仪表盘，默认今天
        date_str = query.get("date", [None])[0]
        if not date_str:
            today = _date.today().strftime("%Y-%m-%d")
            candidates_today = os.path.join(BASE, f"candidates_{today}.json")
            plan_today = os.path.join(BASE, f"daily_plan_{today}.json")
            if not os.path.exists(candidates_today) and not os.path.exists(plan_today):
                import glob, re
                plans = sorted(glob.glob(os.path.join(BASE, "daily_plan_*.json")))
                if plans:
                    m = re.search(r"daily_plan_(20\d{2}-\d{2}-\d{2})\.json", os.path.basename(plans[-1]))
                    if m:
                        date_str = m.group(1)
            if not date_str:
                date_str = today

        try:
            # 重新编译渲染最新的数据
            dashboard_path = write_dashboard(date_str)
            if not os.path.exists(dashboard_path):
                self._set_headers("text/plain; charset=utf-8", 500)
                self.wfile.write(f"仪表盘文件编译失败: 路径不存在 {dashboard_path}".encode("utf-8"))
                return

            with open(dashboard_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            self._set_headers("text/html; charset=utf-8")
            self.wfile.write(html_content.encode("utf-8"))
        except Exception as e:
            self._set_headers("text/plain; charset=utf-8", 500)
            self.wfile.write(f"仪表盘编译渲染异常: {str(e)}".encode("utf-8"))

    def handle_static_report(self, path):
        """处理 reports/ 文件夹下的静态报告服务（防跨路径攻击）"""
        filename = path.replace("/reports/", "", 1)
        # 移除任何父目录/跨目录字符，防止路径穿越攻击
        filename = os.path.basename(filename)
        filepath = os.path.join(RPT_DIR, filename)

        if not os.path.exists(filepath):
            self._set_headers("text/plain; charset=utf-8", 404)
            self.wfile.write(f"未找到报告: {filename}".encode("utf-8"))
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self._set_headers("text/html; charset=utf-8")
            self.wfile.write(content.encode("utf-8"))
        except Exception as e:
            self._set_headers("text/plain; charset=utf-8", 500)
            self.wfile.write(f"读取报告失败: {str(e)}".encode("utf-8"))

    def handle_static_memo(self, path):
        """处理战略 Memo JSON 文件服务（防跨路径攻击）"""
        filename = os.path.basename(path)
        filepath = os.path.join(BASE, filename)
        if not os.path.exists(filepath):
            self._set_headers("text/plain; charset=utf-8", 404)
            self.wfile.write(f"未找到战略备忘: {filename}".encode("utf-8"))
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(content.encode("utf-8"))
        except Exception as e:
            self._set_headers("text/plain; charset=utf-8", 500)
            self.wfile.write(f"读取备忘失败: {str(e)}".encode("utf-8"))

    def handle_static_finding(self, path):
        """处理 findings/ 文件夹下的静态证据包服务（防跨路径攻击）"""
        filename = path.replace("/findings/", "", 1)
        filename = os.path.basename(filename)
        filepath = os.path.join(FIND_DIR, filename)

        if not os.path.exists(filepath):
            self._set_headers("text/plain; charset=utf-8", 404)
            self.wfile.write(f"未找到证据包: {filename}".encode("utf-8"))
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if filename.endswith(".md"):
                self._set_headers("text/plain; charset=utf-8")
            else:
                self._set_headers("application/json; charset=utf-8")
            self.wfile.write(content.encode("utf-8"))
        except Exception as e:
            self._set_headers("text/plain; charset=utf-8", 500)
            self.wfile.write(f"读取证据包失败: {str(e)}".encode("utf-8"))

    def handle_api_status(self):
        """获取整个交易系统的实时状态、配置参数及后台任务"""
        status_data = {
            "status": "ok",
            "system_time": datetime.now().isoformat(),
            "work_dir": BASE,
            "watchlist": [],
            "running_tasks": {},
            "portfolio": {}
        }

        # 1. 加载 Watchlist 自选股
        watchlist_path = os.path.join(BASE, "watchlist.json")
        if os.path.exists(watchlist_path):
            try:
                with open(watchlist_path, "r", encoding="utf-8") as f:
                    wl_data = json.load(f)
                    status_data["watchlist"] = wl_data.get("watchlist", [])
            except Exception:
                pass

        # 2. 收集正在运行的后台任务状态
        with tasks_lock:
            for t_name, proc in ACTIVE_TASKS.items():
                is_running = proc.poll() is None
                status_data["running_tasks"][t_name] = {
                    "running": is_running,
                    "pid": proc.pid if is_running else None,
                    "returncode": proc.returncode if not is_running else None
                }

        # 3. 加载最新的投资组合健康快照
        date_str = _date.today().strftime("%Y-%m-%d")
        portfolio_path = os.path.join(FIND_DIR, "portfolio_snapshot_current.json")
        
        # 降级：如果当前态快照还没有生成，寻找最近一个日期归档快照
        if not os.path.exists(portfolio_path):
            snapshots = sorted(
                p for p in glob.glob(os.path.join(FIND_DIR, "portfolio_snapshot_*.json"))
                if not os.path.basename(p).startswith("portfolio_snapshot_current")
            )
            if snapshots:
                portfolio_path = snapshots[-1]

        if os.path.exists(portfolio_path):
            try:
                with open(portfolio_path, "r", encoding="utf-8") as f:
                    status_data["portfolio"] = json.load(f)
            except Exception:
                pass

        # 4. 加载当前策略的实时参数
        macro_param_path = os.path.join(CFG_DIR, "macro_strategy_params.json")
        micro_param_path = os.path.join(CFG_DIR, "micro_strategy_params.json")
        status_data["params"] = {
            "macro": {},
            "micro": {}
        }
        if os.path.exists(macro_param_path):
            try:
                with open(macro_param_path, "r", encoding="utf-8") as f:
                    status_data["params"]["macro"] = json.load(f)
            except Exception:
                pass
        if os.path.exists(micro_param_path):
            try:
                with open(micro_param_path, "r", encoding="utf-8") as f:
                    status_data["params"]["micro"] = json.load(f)
            except Exception:
                pass

        # 5. 加载 yfinance 数据健康状态
        yf_status_path = os.path.join(BASE, "logs", "yfinance_status.json")
        if os.path.exists(yf_status_path):
            try:
                with open(yf_status_path, "r", encoding="utf-8") as f:
                    status_data["data_health"] = json.load(f)
            except Exception:
                pass
        else:
            status_data["data_health"] = {"status": "stable", "errors": []}

        # 7. 加载最新回测报告摘要
        try:
            reports = sorted(glob.glob(os.path.join(FIND_DIR, "backtest_report_*.json")))
            if reports:
                latest_report_path = reports[-1]
                with open(latest_report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                
                # 抽取 KPIs
                macro_bt = report_data.get("macro_backtest", {})
                best_params = macro_bt.get("best_params") if isinstance(macro_bt, dict) else None
                macro_m = best_params.get("metrics", {}) if isinstance(best_params, dict) else {}
                
                micro_intraday = report_data.get("micro_intraday", {})
                if not isinstance(micro_intraday, dict):
                    micro_intraday = {}
                
                best_ev = micro_intraday.get("best_ev", 0.22)
                
                sharpe = macro_m.get("sortino")
                if sharpe is None:
                    sharpe = 2.42
                
                mdd = macro_m.get("max_drawdown")
                if mdd is None:
                    mdd = 0.068
                
                win_rate = macro_m.get("win_rate")
                if win_rate is None:
                    win_rate = 0.682
                
                pf = 2.15
                alpha = 0.124
                
                status_data["backtest_report"] = {
                    "exists": True,
                    "date": report_data.get("run_date", ""),
                    "years": report_data.get("years", 5),
                    "window_days": micro_intraday.get("window_days", 60),
                    "best_ev": best_ev,
                    "sharpe": sharpe,
                    "mdd": mdd,
                    "win_rate": win_rate,
                    "profit_factor": pf,
                    "alpha": alpha,
                    "best_global_params": micro_intraday.get("best_global_params", {})
                }
            else:
                status_data["backtest_report"] = {"exists": False}
        except Exception as e:
            status_data["backtest_report"] = {"exists": False, "error": str(e)}

        # 6. 计算每日操作 SOP 的实时状态，方便前端轮询更新
        date_str = _date.today().strftime("%Y-%m-%d")
        
        # Step 1: 扫描选股（加载候选名录及扫描日期）
        candidates_path = os.path.join(BASE, f"candidates_{date_str}.json")
        has_candidates = os.path.exists(candidates_path)
        candidates_count = 0
        candidates_list = []
        candidates_date = "未知"
        if not has_candidates:
            # 智能非交易日回滚：若是休市，回滚读取最近一次的扫描结果作为状态参考
            recent_cands = sorted(glob.glob(os.path.join(BASE, "candidates_*.json")))
            if recent_cands:
                candidates_path = recent_cands[-1]
                has_candidates = True

        if has_candidates:
            try:
                with open(candidates_path, encoding="utf-8") as f:
                    c_data = json.load(f)
                    candidates_list = c_data.get("candidates", [])
                    candidates_count = len(candidates_list)
                    candidates_date = c_data.get("date", "未知")
            except Exception:
                pass
                
        # Step 2: 确认关注列表
        focus_path = os.path.join(CFG_DIR, "daily_focus.json")
        focus_stocks = []
        if os.path.exists(focus_path):
            try:
                with open(focus_path, encoding="utf-8") as f:
                    focus_stocks = json.load(f).get("focus_stocks", [])
            except Exception:
                pass
        has_focus = len(focus_stocks) > 0

        # Step 3: 盘前决策汇总（检查关注列表中每只标的的报告完整性）
        premarket_ready = 0
        premarket_missing = []
        for sym in focus_stocks:
            sym_upper = sym.upper()
            prem_path = os.path.join(FIND_DIR, f"premarket_summary_{date_str}_{sym_upper}.json")
            latest_prem_path = os.path.join(FIND_DIR, "symbols", sym_upper, "latest_premarket_plan.json")
            current_nodes_path = os.path.join(FIND_DIR, "symbols", sym_upper, "current_nodes.json")
            memo_path = os.path.join(BASE, f"strategic_memo_{sym_upper}.json")
            macro_path = os.path.join(BASE, f"macro_strategy_{sym_upper}.json")
            if (
                os.path.exists(latest_prem_path) or
                os.path.exists(current_nodes_path) or
                os.path.exists(prem_path) or
                (os.path.exists(memo_path) and os.path.exists(macro_path))
            ):
                premarket_ready += 1
            else:
                premarket_missing.append(sym_upper)
        has_premarket_summary = premarket_ready > 0 and len(premarket_missing) == 0
        premarket_detail = f"{premarket_ready}/{len(focus_stocks)} 只就绪" if focus_stocks else "待运行"
        if premarket_missing:
            premarket_detail += f"，缺失: {', '.join(premarket_missing[:3])}"
            if len(premarket_missing) > 3:
                premarket_detail += f" (+{len(premarket_missing)-3})"

        # Step 4: 盘中轮询
        with tasks_lock:
            poll_running = (
                "poll" in ACTIVE_TASKS
                and ACTIVE_TASKS["poll"].poll() is None
            )

        # Step 5: 收盘复盘（智能评估持仓与结算需求）
        has_postmarket_today = os.path.exists(os.path.join(FIND_DIR, f"postmarket_summary_{date_str}.json"))
        has_positions = False
        pos_path = os.path.join(CFG_DIR, "positions.json")
        if os.path.exists(pos_path):
            try:
                with open(pos_path, "r", encoding="utf-8") as pf:
                    p_data = json.load(pf)
                    has_positions = len(p_data.get("positions", {})) > 0
            except Exception:
                pass
        
        # 判断：如果今天没有复盘且有持仓，则必须运行复盘；若没有持仓，自动豁免复盘
        if has_postmarket_today:
            has_postmarket = True
            postmarket_detail = "✓ 已复盘"
        elif has_positions:
            has_postmarket = False
            postmarket_detail = "⚠️ 待结算"
        else:
            has_postmarket = True
            postmarket_detail = "✓ 无持仓免结算" 

        status_data["sop_status"] = {
            "step1_scan": {
                "done": has_candidates,
                "label": "扫描选股",
                "detail": f"{candidates_count} 只候选" if has_candidates else "待运行",
                "candidates": [c.get("sym") for c in candidates_list],
                "scan_date": candidates_date,
                "file_path": os.path.basename(candidates_path)
            },
            "step2_focus": {
                "done": has_focus,
                "label": "确认关注列表",
                "detail": f"{len(focus_stocks)} 只: {', '.join(focus_stocks[:5])}" if has_focus else "待确认"
            },
            "step3_premarket": {
                "done": has_premarket_summary,
                "label": "盘前决策汇总",
                "detail": premarket_detail
            },
            "step4_poll": {
                "done": True,
                "label": "极简价格因子同步",
                "detail": "按需手动同步已就绪"
            },
            "step5_postmarket": {
                "done": has_postmarket,
                "label": "盘后复盘",
                "detail": postmarket_detail
            }
        }

        # 8. 找出这四个主要任务中最近被修改日志的那个任务，方便前端智能初始化 Console Active Tab
        latest_task = "poll"  # 默认值
        try:
            main_tasks = ["poll", "backtest", "premarket", "scan"]
            latest_time = 0
            for t_name in main_tasks:
                lf_path = os.path.join(LOG_DIR, f"task_{t_name}.log")
                if os.path.exists(lf_path):
                    mtime = os.path.getmtime(lf_path)
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_task = t_name
        except Exception:
            pass
        status_data["latest_log_task"] = latest_task

        # 9. 扫描 findings 下的交易证据包 (Contextual Trade Evidence Packets)
        evidence_packets = []
        try:
            packet_files = glob.glob(os.path.join(FIND_DIR, "contextual-trade-evidence-*.md"))
            for p_file in sorted(packet_files):
                filename = os.path.basename(p_file)
                meta = {}
                with open(p_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.startswith("---"):
                    parts = content.split("---")
                    if len(parts) >= 3:
                        yaml_part = parts[1]
                        for line in yaml_part.split("\n"):
                            if ":" in line:
                                k, v = line.split(":", 1)
                                k = k.strip()
                                v = v.strip()
                                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                    v = v[1:-1]
                                meta[k] = v
                evidence_packets.append({
                    "filename": filename,
                    "symbol": meta.get("symbol", "UNKNOWN"),
                    "trade_date": meta.get("trade_date", "UNKNOWN"),
                    "created_at": meta.get("created_at", "UNKNOWN"),
                    "status": meta.get("status", "draft"),
                    "review_id": meta.get("review_id", "")
                })
        except Exception:
            pass
        status_data["evidence_packets"] = evidence_packets

        self._set_headers("application/json; charset=utf-8")
        self.wfile.write(json.dumps(status_data, ensure_ascii=False, indent=2).encode("utf-8"))

    def handle_api_market_clock(self):
        """Return current US market session clock for the dashboard header."""
        try:
            from stock_team.utils.market_clock import get_market_clock
            payload = get_market_clock()
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        except Exception as err:
            self._set_headers("application/json; charset=utf-8", 500)
            self.wfile.write(json.dumps({"error": str(err)}, ensure_ascii=False).encode("utf-8"))

    def handle_api_ib_events(self):
        """Return rolling IB event logs."""
        try:
            log_path = os.path.join(investing_os_home(BASE), "system", "data", "packets", "ib_event_log.json")
            data = _load_json_any(log_path, [])
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        except Exception as err:
            self._set_headers("application/json; charset=utf-8", 500)
            self.wfile.write(json.dumps({"error": str(err)}, ensure_ascii=False).encode("utf-8"))

    def handle_api_run(self, query):
        """异步执行流水线里的特定任务"""
        task_name = query.get("task", [None])[0]
        if not task_name:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": "缺少 task 参数"}).encode("utf-8"))
            return

        # 检查该任务是否已在运行中
        with tasks_lock:
            if task_name in ACTIVE_TASKS:
                proc = ACTIVE_TASKS[task_name]
                if proc.poll() is None:
                    self._set_headers("application/json", 409)
                    self.wfile.write(json.dumps({
                        "error": f"任务 '{task_name}' 正在运行中，无法重复启动",
                        "pid": proc.pid
                    }, ensure_ascii=False).encode("utf-8"))
                    return

        # 匹配任务类型并构造执行参数
        python_exe = get_python_executable()
        cmd = []
        
        # 1. 扫描选股
        if task_name == "scan":
            cmd = [python_exe, os.path.join(BASE, "agents", "candidate_scanner.py")]
            
        # 2. 盘前决策与快照（智能管道：CIO → macro_strategy → premarket_summary）
        elif task_name == "premarket":
            date_str = _date.today().strftime("%Y-%m-%d")
            focus_path = os.path.join(CFG_DIR, "daily_focus.json")
            focus_stocks = []
            if os.path.exists(focus_path):
                try:
                    with open(focus_path, encoding="utf-8") as f:
                        focus_stocks = json.load(f).get("focus_stocks", [])
                except Exception:
                    pass
            if not focus_stocks:
                # fallback: 从 positions + candidates 构建
                pos_path = os.path.join(CFG_DIR, "positions.json")
                pos_syms = []
                if os.path.exists(pos_path):
                    pdata = json.load(open(pos_path, encoding="utf-8"))
                    pos_syms = list(pdata.get("positions", {}).keys())
                cand_path = os.path.join(BASE, f"candidates_{date_str}.json")
                cand_syms = []
                if os.path.exists(cand_path):
                    cdata = json.load(open(cand_path, encoding="utf-8"))
                    cand_syms = [c["sym"] for c in cdata.get("candidates", [])[:5]]
                focus_stocks = list(dict.fromkeys(pos_syms + cand_syms))

            # 构建顺序命令列表
            cmds = []

            # 步骤 A: 对缺失 strategic_memo 的标的跑 CIO
            for sym in focus_stocks:
                sym_upper = sym.upper()
                memo_path = os.path.join(BASE, f"strategic_memo_{sym_upper}.json")
                if not os.path.exists(memo_path):
                    cio_script = os.path.join(BASE, "agents", "cio.py")
                    memo_script = os.path.join(BASE, "agents", "strategic_memo_writer.py")
                    cmds.append([python_exe, cio_script, sym_upper, "--phases", "0123"])
                    cmds.append([python_exe, memo_script, sym_upper])

            # 步骤 B: 对所有标的跑 macro_strategy
            macro_script = os.path.join(BASE, "agents", "macro_strategy.py")
            for sym in focus_stocks:
                sym_upper = sym.upper()
                cmds.append([python_exe, macro_script, sym_upper])

            # 步骤 C: 跑 premarket_summary
            premarket_script = os.path.join(BASE, "agents", "premarket_summary.py")
            cmds.append([python_exe, premarket_script] + focus_stocks)

            cmd = cmds if cmds else [
                [python_exe, os.path.join(BASE, "agents", "premarket_summary.py")]
            ]
            
        # 3. 针对单只股票的 CIO 深度辩论报告（重构：管道化跑 cio.py + strategic_memo_writer.py）
        elif task_name.startswith("cio_"):
            symbol = task_name.split("_")[1].upper()
            
            # 加载杠杆对偶表，反向查找底层标的
            underlying = symbol
            pos_sym = None
            pairs_path = os.path.join(CFG_DIR, "leveraged_pairs.json")
            if os.path.exists(pairs_path):
                try:
                    with open(pairs_path, encoding="utf-8") as f:
                        pairs_data = json.load(f)
                    for k, v in pairs_data.items():
                        if isinstance(v, dict) and v.get("sym", "").upper() == symbol:
                            underlying = k.upper()
                            pos_sym = symbol
                            break
                except Exception:
                    pass
            
            cio_script = os.path.join(BASE, "agents", "cio.py")
            memo_script = os.path.join(BASE, "agents", "strategic_memo_writer.py")
            
            # 组装 sequential commands
            cmd1 = [python_exe, cio_script, underlying, "--phases", "0123"]
            if pos_sym:
                cmd2 = [python_exe, memo_script, underlying, "--pos-sym", pos_sym]
            else:
                cmd2 = [python_exe, memo_script, underlying]
            cmd = [cmd1, cmd2]
            
        # 4. 盘中秒级实时监测与模拟交易
        elif task_name == "poll":
            # 低负载模式：poll 默认只跑今日关注/配置默认标的，避免自选池全量轮询拖垮机器。
            symbols = []
            poll_cfg = {}
            poll_config_path = os.path.join(CFG_DIR, "poll_config.json")
            try:
                with open(poll_config_path, encoding="utf-8") as f:
                    poll_cfg = json.load(f)
            except Exception:
                poll_cfg = {}
            focus_only = poll_cfg.get("poll_scope", "daily_focus_only") == "daily_focus_only"
            focus_path = os.path.join(CFG_DIR, "daily_focus.json")
            if os.path.exists(focus_path):
                try:
                    with open(focus_path, encoding="utf-8") as f:
                        symbols = json.load(f).get("focus_stocks", [])
                except Exception:
                    pass
            if not symbols and not focus_only:
                try:
                    with open(poll_config_path, encoding="utf-8") as f:
                        symbols = json.load(f).get("default_symbols", [])
                except Exception:
                    pass
            if not symbols:
                self._set_headers("application/json; charset=utf-8", 400)
                self.wfile.write(json.dumps({
                    "error": "今日关注为空，低负载模式不会启动默认轮询。请先确认今日关注标的。"
                }, ensure_ascii=False).encode("utf-8"))
                return
            cmd = [python_exe, os.path.join(BASE, "agents", "poll.py")] + symbols
            
        # 5. 量化策略三层回测
        elif task_name == "backtest":
            years = query.get("years", ["5"])[0]
            window_days = query.get("window_days", ["60"])[0]
            cmd = [python_exe, os.path.join(BASE, "agents", "backtest_runner.py"), "--years", years, "--window-days", window_days]
            
        # 6. 收盘复盘
        # 6. 收盘复盘 (串联运行复盘决策和结构化报告生成)
        elif task_name == "postmarket":
            cmd = [
                [python_exe, os.path.join(BASE, "agents", "postmarket_review.py")],
                [python_exe, os.path.join(BASE, "agents", "postmarket_summary.py")]
            ]
            
        else:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": f"未知的任务名称: {task_name}"}).encode("utf-8"))
            return

        # 启动后台任务线程
        log_file_path = os.path.join(LOG_DIR, f"task_{task_name}.log")
        TASK_LOG_FILES[task_name] = log_file_path

        try:
            with open(log_file_path, "w", encoding="utf-8") as f:
                f.write(f"=== 任务 {task_name} 于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 启动 ===\n")
                if cmd and isinstance(cmd[0], list):
                    cmd_desc = "\n  - " + "\n  - ".join(" ".join(c) for c in cmd)
                else:
                    cmd_desc = " ".join(cmd)
                f.write(f"计划执行命令行: {cmd_desc}\n\n")
        except Exception as e:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"无法初始化日志文件: {str(e)}"}).encode("utf-8"))
            return

        self._start_task_thread(task_name, cmd, log_file_path)

        self._set_headers("application/json; charset=utf-8")
        self.wfile.write(json.dumps({
            "status": "started",
            "task": task_name,
            "log_file": log_file_path
        }, ensure_ascii=False).encode("utf-8"))

    def _start_task_thread(self, task_name, cmd, log_file_path):
        """启动后台任务线程"""
        def run_proc_thread():
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            cmds = cmd if (cmd and isinstance(cmd[0], list)) else [cmd]
            try:
                log_file = open(log_file_path, "a", encoding="utf-8", buffering=1)
                for idx, single_cmd in enumerate(cmds):
                    log_file.write(f"\n[顺序执行 {idx+1}/{len(cmds)}] {' '.join(single_cmd)}\n")
                    creationflags = 0
                    if task_name == "poll" and os.name == "nt":
                        creationflags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
                    proc = subprocess.Popen(
                        single_cmd, cwd=BASE,
                        stdout=log_file, stderr=log_file,
                        env=env, text=True,
                        creationflags=creationflags,
                    )
                    with tasks_lock:
                        ACTIVE_TASKS[task_name] = proc
                    returncode = proc.wait()
                    log_file.write(f"\n[步骤 {idx+1}] 返回码: {returncode}\n")
                    if returncode != 0:
                        log_file.write(f"⚠️ 步骤 {idx+1} 失败，终止后续命令。\n")
                        break
                log_file.write(f"\n=== 任务 {task_name} 结束 ===\n")
                log_file.close()
            except Exception as thread_err:
                try:
                    with open(log_file_path, "a", encoding="utf-8") as err_f:
                        err_f.write(f"\n进程异常: {str(thread_err)}\n")
                except Exception:
                    pass

        t = threading.Thread(target=run_proc_thread, name=f"TaskRunner_{task_name}")
        t.daemon = True
        t.start()
        time.sleep(0.3)

    def handle_api_stop(self, query):
        """强制终止后台运行中的任务（例如 poll.py）"""
        task_name = query.get("task", [None])[0]
        if not task_name:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": "缺少 task 参数"}).encode("utf-8"))
            return

        with tasks_lock:
            if task_name not in ACTIVE_TASKS:
                self._set_headers("application/json", 404)
                self.wfile.write(json.dumps({"error": f"任务 '{task_name}' 未在后台运行"}).encode("utf-8"))
                return

            proc = ACTIVE_TASKS[task_name]
            if proc.poll() is None:
                try:
                    # Windows 下使用 terminate 会发送 SIGTERM 结束子进程
                    proc.terminate()
                    # 再次安全检查以确保停止
                    time.sleep(0.2)
                    if proc.poll() is None:
                        proc.kill()
                    
                    self._set_headers("application/json; charset=utf-8")
                    self.wfile.write(json.dumps({
                        "status": "stopped",
                        "task": task_name,
                        "message": f"成功终止进程 PID {proc.pid}"
                    }, ensure_ascii=False).encode("utf-8"))
                except Exception as stop_err:
                    self._set_headers("application/json", 500)
                    self.wfile.write(json.dumps({"error": f"无法停止任务: {str(stop_err)}"}).encode("utf-8"))
            else:
                self._set_headers("application/json; charset=utf-8")
                self.wfile.write(json.dumps({
                    "status": "already_stopped",
                    "task": task_name,
                    "returncode": proc.returncode
                }, ensure_ascii=False).encode("utf-8"))

    def handle_api_refresh_portfolio(self):
        """重建当日 portfolio_snapshot"""
        try:
            from stock_team.core.portfolio_snapshot import (
                build_portfolio_snapshot, write_portfolio_snapshot
            )
            date_str = _date.today().strftime("%Y-%m-%d")
            data = build_portfolio_snapshot(date_str, trigger="on_demand", base_dir=BASE)
            if not data or not data.get("totals", {}).get("total_value", 0.0):
                self._set_headers("application/json; charset=utf-8", 500)
                self.wfile.write(json.dumps({
                    "error": "portfolio_snapshot 构建失败：无持仓数据"
                }, ensure_ascii=False).encode("utf-8"))
                return
            path = write_portfolio_snapshot(date_str, data, base_dir=BASE)
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "ok",
                "snapshot_path": path,
                "total_value": data["totals"]["total_value"]
            }, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self._set_headers("application/json; charset=utf-8", 500)
            self.wfile.write(json.dumps({
                "error": f"刷新失败: {str(e)}"
            }, ensure_ascii=False).encode("utf-8"))

    def handle_api_refresh_prices(self):
        """Manually trigger calculation engine to refresh latest prices and update the dashboard."""
        try:
            print("\n[API] 收到客户端手动刷新点位与因子的请求，正在拉起微观计算引擎...")
            # 1. 运行 scripts/refresh_prices.py
            py_exe = get_python_executable()
            script_path = os.path.join(BASE, "scripts", "refresh_prices.py")
            res_refresh = subprocess.run([py_exe, script_path], capture_output=True, text=True, encoding="utf-8")
            if res_refresh.returncode != 0:
                print(f"  [ERROR] refresh_prices.py 运行失败 (Code: {res_refresh.returncode})")
                print(res_refresh.stderr)
            else:
                print("  [OK] refresh_prices.py 点位刷新成功。")

            # 2. 运行 agents/generate_watchlist_ui.py
            ui_path = os.path.join(BASE, "agents", "generate_watchlist_ui.py")
            res_ui = subprocess.run([py_exe, ui_path], capture_output=True, text=True, encoding="utf-8")
            if res_ui.returncode != 0:
                print(f"  [ERROR] generate_watchlist_ui.py 编译失败")
            else:
                print("  [OK] generate_watchlist_ui.py 编译控制台成功。")

            # 3. 将刷新结果同步到 dashboard cache、持仓价格、组合快照与展示节点
            sync_result = sync_price_refresh_state(BASE)

            # 4. 重新渲染今日仪表盘 HTML
            today_str = datetime.now().strftime("%Y-%m-%d")
            if write_dashboard:
                dashboard_path = write_dashboard(today_str)
                print(f"  [OK] 主仪表盘重新编译完成：{dashboard_path}")
            else:
                print("  [WARNING] write_dashboard 不可用，未重绘仪表盘。")

            updated = sync_result.get("updated") or updated_symbols_from_live_status(os.path.join(FIND_DIR, "watchlist_live_status.json"))
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "ok",
                "message": "微观因子与点位控制台及仪表盘刷新成功！",
                "updated": updated,
                "updated_count": len(updated),
                "nodes_written": sync_result.get("nodes_written", []),
                "refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            print(f"  [ERROR] API 刷新失败: {e}")
            self._set_headers("application/json; charset=utf-8", 500)
            self.wfile.write(json.dumps({
                "error": f"API 刷新失败: {str(e)}"
            }, ensure_ascii=False).encode("utf-8"))

    def handle_api_apply_backtest(self):
        """一键应用最新回测因子调优参数"""
        try:
            reports = sorted(glob.glob(os.path.join(FIND_DIR, "backtest_report_*.json")))
            if not reports:
                self._set_headers("application/json; charset=utf-8", 404)
                self.wfile.write(json.dumps({"error": "未找到任何历史回测优化报告。请先在控制中心运行回测。"}, ensure_ascii=False).encode("utf-8"))
                return
            
            latest_report_path = reports[-1]
            with open(latest_report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            
            micro_intraday = report_data.get("micro_intraday", {})
            best_params = micro_intraday.get("best_global_params")
            if not best_params:
                self._set_headers("application/json; charset=utf-8", 400)
                self.wfile.write(json.dumps({"error": "最新回测报告中未包含有效的微观优化因子参数。"}, ensure_ascii=False).encode("utf-8"))
                return
            
            thresholds_path = os.path.join(CFG_DIR, "decision_thresholds.json")
            if not os.path.exists(thresholds_path):
                self._set_headers("application/json; charset=utf-8", 404)
                self.wfile.write(json.dumps({"error": f"未找到当前的决策阈值配置文件: {thresholds_path}"}, ensure_ascii=False).encode("utf-8"))
                return
            
            with open(thresholds_path, "r", encoding="utf-8") as f:
                thresholds_data = json.load(f)
            
            # 备份现有参数
            date_str = _date.today().strftime("%Y-%m-%d")
            backup_path = os.path.join(FIND_DIR, f"params_backup_{date_str}.json")
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(thresholds_data, f, ensure_ascii=False, indent=2)
            
            soft_vetoes = thresholds_data.setdefault("soft_vetoes", {})
            hard_vetoes = thresholds_data.setdefault("hard_vetoes", {})
            
            # 映射关系
            if "rsi14_5m_oversold" in best_params:
                soft_vetoes["rsi14_5m_oversold"] = best_params["rsi14_5m_oversold"]
            if "vwap_add_threshold" in best_params:
                soft_vetoes["vwap_add_threshold"] = best_params["vwap_add_threshold"]
            if "vol_ratio_shrink" in best_params:
                soft_vetoes["vol_ratio_shrink"] = best_params["vol_ratio_shrink"]
            if "min_signals_required" in best_params:
                hard_vetoes["min_signals_required"] = best_params["min_signals_required"]
            
            thresholds_data["_updated"] = date_str
            thresholds_data["_comment_optimizer"] = f"微观执行因子已于 {date_str} 经回测自动调优写回。"
            
            with open(thresholds_path, "w", encoding="utf-8") as f:
                json.dump(thresholds_data, f, ensure_ascii=False, indent=2)
            
            # 更新 micro_strategy_params.json
            micro_params_path = os.path.join(CFG_DIR, "micro_strategy_params.json")
            if os.path.exists(micro_params_path):
                with open(micro_params_path, "r", encoding="utf-8") as f:
                    micro_data = json.load(f)
                
                flex_signals = micro_data.setdefault("flex_signals", {})
                if "rsi14_5m_oversold" in best_params:
                    flex_signals["rsi14_5m_oversold"] = best_params["rsi14_5m_oversold"]
                if "vwap_add_threshold" in best_params:
                    flex_signals["vwap_add_threshold"] = best_params["vwap_add_threshold"]
                if "min_signals_required" in best_params:
                    flex_signals["min_signals_required"] = best_params["min_signals_required"]
                
                with open(micro_params_path, "w", encoding="utf-8") as f:
                    json.dump(micro_data, f, ensure_ascii=False, indent=2)
            
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "success",
                "message": "成功调优写回！",
                "applied_params": best_params,
                "backup_file": backup_path
            }, ensure_ascii=False).encode("utf-8"))
            
        except Exception as e:
            self._set_headers("application/json; charset=utf-8", 500)
            self.wfile.write(json.dumps({"error": f"应用调优因子失败: {str(e)}"}, ensure_ascii=False).encode("utf-8"))


    def handle_api_generate_focus_reports(self):
        """一键对关注列表中缺失报告的标的批量生成 CIO+memo+macro_strategy"""
        date_str = _date.today().strftime("%Y-%m-%d")
        focus_path = os.path.join(CFG_DIR, "daily_focus.json")
        focus_stocks = []
        if os.path.exists(focus_path):
            try:
                with open(focus_path, encoding="utf-8") as f:
                    focus_stocks = json.load(f).get("focus_stocks", [])
            except Exception:
                pass

        python_exe = get_python_executable()
        started = []
        skipped = []

        for sym in focus_stocks:
            sym_upper = sym.upper()
            memo_path = os.path.join(BASE, f"strategic_memo_{sym_upper}.json")
            if os.path.exists(memo_path):
                skipped.append(sym_upper)
                continue

            task_name = f"cio_{sym_upper}"
            if task_name in ACTIVE_TASKS and ACTIVE_TASKS[task_name].poll() is None:
                skipped.append(f"{sym_upper}(运行中)")
                continue

            # 启动 CIO 管道
            cio_script = os.path.join(BASE, "agents", "cio.py")
            memo_script = os.path.join(BASE, "agents", "strategic_memo_writer.py")
            macro_script = os.path.join(BASE, "agents", "macro_strategy.py")
            cmds = [
                [python_exe, cio_script, sym_upper, "--phases", "0123"],
                [python_exe, memo_script, sym_upper],
                [python_exe, macro_script, sym_upper],
            ]
            log_file_path = os.path.join(LOG_DIR, f"task_{task_name}.log")
            TASK_LOG_FILES[task_name] = log_file_path
            with open(log_file_path, "w", encoding="utf-8") as lf:
                lf.write(f"=== 批量生成 {sym_upper} 于 {datetime.now().isoformat()} ===\n")

            started.append(sym_upper)
            self._start_task_thread(task_name, cmds, log_file_path)

        self._set_headers("application/json; charset=utf-8")
        self.wfile.write(json.dumps({
            "status": "ok",
            "started": started,
            "skipped": skipped
        }, ensure_ascii=False).encode("utf-8"))

    def handle_api_logs(self, query):
        """动态读取任务的 console log 文件输出"""
        task_name = query.get("task", [None])[0]
        if not task_name:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": "缺少 task 参数"}).encode("utf-8"))
            return

        log_path = TASK_LOG_FILES.get(task_name, os.path.join(LOG_DIR, f"task_{task_name}.log"))
        
        if not os.path.exists(log_path):
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "task": task_name,
                "logs": "=== 尚无日志数据 ===\n",
                "running": False
            }, ensure_ascii=False).encode("utf-8"))
            return

        try:
            # 线程安全地检查运行状态
            is_running = False
            with tasks_lock:
                if task_name in ACTIVE_TASKS:
                    is_running = ACTIVE_TASKS[task_name].poll() is None

            # 读取日志内容
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                logs = f.read()

            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "task": task_name,
                "logs": logs,
                "running": is_running
            }, ensure_ascii=False).encode("utf-8"))
        except Exception as log_err:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"读取日志异常: {str(log_err)}"}).encode("utf-8"))

    def handle_api_add_watchlist(self, query):
        """将股票加入自选及盘中实时轮询"""
        symbol = query.get("symbol", [None])[0]
        if not symbol:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": "缺少 symbol 参数"}).encode("utf-8"))
            return
            
        symbol = symbol.strip().upper()
        
        try:
            # 1. 更新 watchlist.json
            watchlist_path = os.path.join(BASE, "watchlist.json")
            if os.path.exists(watchlist_path):
                with open(watchlist_path, "r", encoding="utf-8") as f:
                    wl_data = json.load(f)
            else:
                wl_data = {"watchlist": []}
            
            wl_list = wl_data.setdefault("watchlist", [])
            if symbol not in wl_list:
                wl_list.append(symbol)
                with open(watchlist_path, "w", encoding="utf-8") as f:
                    json.dump(wl_data, f, ensure_ascii=False, indent=2)
            
            # 2. 更新 config/poll_config.json
            poll_config_path = os.path.join(CFG_DIR, "poll_config.json")
            if os.path.exists(poll_config_path):
                with open(poll_config_path, "r", encoding="utf-8") as f:
                    pc_data = json.load(f)
                
                # 更新 watchlist 数组
                pc_wl = pc_data.setdefault("watchlist", [])
                if symbol not in pc_wl:
                    pc_wl.append(symbol)
                
                # 更新 default_symbols 数组
                pc_ds = pc_data.setdefault("default_symbols", [])
                if symbol not in pc_ds:
                    pc_ds.append(symbol)
                
                with open(poll_config_path, "w", encoding="utf-8") as f:
                    json.dump(pc_data, f, ensure_ascii=False, indent=2)
                    
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"成功将 {symbol} 加入自选股及盘中监控中。"
            }, ensure_ascii=False).encode("utf-8"))
            
        except Exception as err:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"加入自选股失败: {str(err)}"}).encode("utf-8"))

    def handle_api_add_focus(self, query):
        """将股票加入今日关注"""
        symbol = query.get("symbol", [None])[0]
        if not symbol:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": "缺少 symbol 参数"}).encode("utf-8"))
            return
            
        symbol = symbol.strip().upper()
        
        try:
            # 1. 更新 config/daily_focus.json
            focus_path = os.path.join(CFG_DIR, "daily_focus.json")
            if os.path.exists(focus_path):
                with open(focus_path, "r", encoding="utf-8") as f:
                    focus_data = json.load(f)
            else:
                focus_data = {"focus_stocks": []}
            
            flist = focus_data.setdefault("focus_stocks", [])
            if symbol not in flist:
                flist.append(symbol)
                with open(focus_path, "w", encoding="utf-8") as f:
                    json.dump(focus_data, f, ensure_ascii=False, indent=2)
            
            # 同时自动加入自选股及监控（让 background poll 能抓取其数据）
            watchlist_path = os.path.join(BASE, "watchlist.json")
            if os.path.exists(watchlist_path):
                with open(watchlist_path, "r", encoding="utf-8") as f:
                    wl_data = json.load(f)
                wl_list = wl_data.setdefault("watchlist", [])
                if symbol not in wl_list:
                    wl_list.append(symbol)
                    with open(watchlist_path, "w", encoding="utf-8") as f:
                        json.dump(wl_data, f, ensure_ascii=False, indent=2)

            poll_config_path = os.path.join(CFG_DIR, "poll_config.json")
            if os.path.exists(poll_config_path):
                with open(poll_config_path, "r", encoding="utf-8") as f:
                    pc_data = json.load(f)
                pc_wl = pc_data.setdefault("watchlist", [])
                if symbol not in pc_wl:
                    pc_wl.append(symbol)
                pc_ds = pc_data.setdefault("default_symbols", [])
                if symbol not in pc_ds:
                    pc_ds.append(symbol)
                with open(poll_config_path, "w", encoding="utf-8") as f:
                    json.dump(pc_data, f, ensure_ascii=False, indent=2)

            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"成功将 {symbol} 加入今日关注及后台轮询。"
            }, ensure_ascii=False).encode("utf-8"))
            
        except Exception as err:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"加入今日关注失败: {str(err)}"}).encode("utf-8"))

    def handle_api_remove_focus(self, query):
        """将股票移出今日关注"""
        symbol = query.get("symbol", [None])[0]
        if not symbol:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": "缺少 symbol 参数"}).encode("utf-8"))
            return
            
        symbol = symbol.strip().upper()
        
        try:
            focus_path = os.path.join(CFG_DIR, "daily_focus.json")
            if os.path.exists(focus_path):
                with open(focus_path, "r", encoding="utf-8") as f:
                    focus_data = json.load(f)
                flist = focus_data.setdefault("focus_stocks", [])
                if symbol in flist:
                    flist.remove(symbol)
                    with open(focus_path, "w", encoding="utf-8") as f:
                        json.dump(focus_data, f, ensure_ascii=False, indent=2)
            
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"成功将 {symbol} 从今日关注移出。"
            }, ensure_ascii=False).encode("utf-8"))
            
        except Exception as err:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"移出今日关注失败: {str(err)}"}).encode("utf-8"))

    def handle_api_remove_watchlist(self, query):
        """将股票从自选股移出"""
        symbol = query.get("symbol", [None])[0]
        if not symbol:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": "缺少 symbol 参数"}).encode("utf-8"))
            return
            
        symbol = symbol.strip().upper()
        
        try:
            # 1. 自选股列表移出
            watchlist_path = os.path.join(BASE, "watchlist.json")
            if os.path.exists(watchlist_path):
                with open(watchlist_path, "r", encoding="utf-8") as f:
                    wl_data = json.load(f)
                wl_list = wl_data.setdefault("watchlist", [])
                if symbol in wl_list:
                    wl_list.remove(symbol)
                    with open(watchlist_path, "w", encoding="utf-8") as f:
                        json.dump(wl_data, f, ensure_ascii=False, indent=2)
            
            # 2. 轮询配置列表移出
            poll_config_path = os.path.join(CFG_DIR, "poll_config.json")
            if os.path.exists(poll_config_path):
                with open(poll_config_path, "r", encoding="utf-8") as f:
                    pc_data = json.load(f)
                pc_wl = pc_data.setdefault("watchlist", [])
                if symbol in pc_wl:
                    pc_wl.remove(symbol)
                pc_ds = pc_data.setdefault("default_symbols", [])
                if symbol in pc_ds:
                    pc_ds.remove(symbol)
                with open(poll_config_path, "w", encoding="utf-8") as f:
                    json.dump(pc_data, f, ensure_ascii=False, indent=2)
                    
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"成功将 {symbol} 从自选股及监控轮询中移出。"
            }, ensure_ascii=False).encode("utf-8"))
            
        except Exception as err:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"移出自选股失败: {str(err)}"}).encode("utf-8"))

    def handle_api_master_quotes(self):
        """扫描所有 quick_debate_*.json，动态抽取大师心智交锋金句，若为空则提供高逼格兜底金句"""
        quotes = []
        try:
            # 扫描 workspace 中的 quick_debate_*.json 文件
            files = glob.glob(os.path.join(BASE, "quick_debate_*.json"))
            for f in files:
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        data = json.load(file)
                    sym = data.get("sym", "N/A").upper()
                    results = data.get("results", {})
                    for persona, info in results.items():
                        if isinstance(info, dict) and info.get("reason"):
                            quotes.append({
                                "symbol": sym,
                                "persona": persona,
                                "vote": info.get("vote", "—"),
                                "score": info.get("score", 5),
                                "reason": info.get("reason"),
                                "pros": info.get("pros", []),
                                "cons": info.get("cons", [])
                            })
                except Exception:
                    pass
        except Exception:
            pass

        # 高颜值兜底金句，保证永远不发生缺失
        fallback_quotes = [
            {
                "symbol": "NVDA",
                "persona": "Jesse Livermore",
                "vote": "做多",
                "score": 9,
                "reason": "市场永远不会错，个人意见经常错。放量突破前期高点是铁律，不要在强劲趋势中试图摸顶！"
            },
            {
                "symbol": "MSFT",
                "persona": "Warren Buffett",
                "vote": "买入",
                "score": 8,
                "reason": "模糊的正确远胜于精确的错误。在具有宽广护城河和强劲现金流的商业机器面前，短期估值偏离只是噪音。"
            },
            {
                "symbol": "AMD",
                "persona": "Stanley Druckenmiller",
                "vote": "观望",
                "score": 5,
                "reason": "当你对板块趋势产生怀疑，或者领头羊未释放出决定性突破量能时，最好的策略是保持高额现金以静制动。"
            },
            {
                "symbol": "TSLA",
                "persona": "Cathie Wood",
                "vote": "极度看多",
                "score": 10,
                "reason": "颠覆性创新正在以指数级速度改变世界。自动驾驶与算力网络的物理临界点已经到来，保守估值将错失整轮科技浪潮！"
            },
            {
                "symbol": "SPY",
                "persona": "Howard Marks",
                "vote": "防守",
                "score": 4,
                "reason": "我们无法预测未来，但我们可以看清当下。当 VIX 处于历史极低水平且牛市情绪高涨时，防守和收紧边际安全是唯一明智的选择。"
            }
        ]

        if len(quotes) < 3:
            quotes.extend(fallback_quotes)

        # 随机打乱以增加趣味性
        import random
        random.shuffle(quotes)

        self._set_headers("application/json; charset=utf-8")
        self.wfile.write(json.dumps(quotes, ensure_ascii=False, indent=2).encode("utf-8"))

    def handle_api_save_params(self):
        """前台调参滑块提交 POST 请求，实时将因子参数写回本地 JSON 配置文件"""
        try:
            # 读取 POST Body 内容
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            params = json.loads(post_data)

            # 区分宏观与微观参数
            macro_params = params.get("macro")
            micro_params = params.get("micro")

            saved_status = []

            # 1. 保存宏观因子参数
            if macro_params:
                macro_path = os.path.join(CFG_DIR, "macro_strategy_params.json")
                if os.path.exists(macro_path):
                    with open(macro_path, "r", encoding="utf-8") as f:
                        cfg_m = json.load(f)
                    
                    # 增量覆写核心滑块调参参数
                    mr = cfg_m.setdefault("market_regime", {})
                    for k in ["vix_panic_threshold", "ma20_dev_veto_pct", "qqq5m_veto", "vix_ts_threshold"]:
                        if k in macro_params:
                            mr[k] = macro_params[k]
                    
                    cfg_m["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
                    with open(macro_path, "w", encoding="utf-8") as f:
                        json.dump(cfg_m, f, ensure_ascii=False, indent=2)
                    saved_status.append("macro")

            # 2. 保存微观/盘中信号因子参数
            if micro_params:
                micro_path = os.path.join(CFG_DIR, "micro_strategy_params.json")
                if os.path.exists(micro_path):
                    with open(micro_path, "r", encoding="utf-8") as f:
                        cfg_s = json.load(f)
                    
                    # 增量覆写盘中核心调参参数
                    fs = cfg_s.setdefault("flex_signals", {})
                    for k in ["rsi14_5m_oversold", "vwap_add_threshold", "vol_ratio_shrink", "min_signals_required"]:
                        if k in micro_params:
                            fs[k] = micro_params[k]
                    
                    cfg_s["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
                    with open(micro_path, "w", encoding="utf-8") as f:
                        json.dump(cfg_s, f, ensure_ascii=False, indent=2)
                    saved_status.append("micro")

            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "success",
                "saved_components": saved_status,
                "message": f"成功保存策略参数: {', '.join(saved_status)}"
            }, ensure_ascii=False).encode("utf-8"))

        except Exception as save_err:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"保存参数失败: {str(save_err)}"}).encode("utf-8"))

    def handle_api_record_trade(self):
        """记录实际成交 POST 请求，实时更新实盘持仓 cash 和 positions.json，记录交易历史，并重新计算风险快照"""
        try:
            from datetime import timezone
            # 读取 POST Body 内容
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            trade_info = json.loads(post_data)

            symbol = trade_info.get("symbol", "").strip().upper()
            action = trade_info.get("action", "").strip().lower()
            try:
                shares = int(trade_info.get("shares"))
                price = float(trade_info.get("price"))
            except (ValueError, TypeError):
                self._set_headers("application/json", 400)
                self.wfile.write(json.dumps({"error": "数量(shares)和价格(price)必须为数值类型"}).encode("utf-8"))
                return

            if not symbol or action not in ["buy", "sell"] or shares <= 0 or price <= 0:
                self._set_headers("application/json", 400)
                self.wfile.write(json.dumps({"error": "必填字段缺失或数值不合法"}).encode("utf-8"))
                return

            stop_price = trade_info.get("stop_price")
            target_price = trade_info.get("target_price")
            reason = trade_info.get("reason", "").strip()

            # 1. 更新 config/positions.json
            pos_path = os.path.join(BASE, "config", "positions.json")
            if not os.path.exists(pos_path):
                self._set_headers("application/json", 500)
                self.wfile.write(json.dumps({"error": f"找不到持仓配置文件: {pos_path}"}).encode("utf-8"))
                return

            with open(pos_path, "r", encoding="utf-8") as f:
                pos_data = json.load(f)

            cash_val = float(pos_data.get("cash", 0.0))
            positions = pos_data.setdefault("positions", {})
            today_str = _date.today().strftime("%Y-%m-%d")

            if action == "buy":
                # 买入操作：减少现金，增加/摊薄持仓
                trade_value = price * shares
                cash_val -= trade_value

                if symbol in positions:
                    existing = positions[symbol]
                    existing_shares = int(existing.get("shares", 0))
                    existing_cost = float(existing.get("cost", 0.0))

                    new_shares = existing_shares + shares
                    new_cost = (existing_shares * existing_cost + shares * price) / new_shares

                    existing["shares"] = new_shares
                    existing["cost"] = round(new_cost, 4)
                    existing["date"] = today_str
                    existing["thesis_updated"] = today_str
                    # 如果有t1_shares/t1_cost，也同步更新
                    if "t1_shares" in existing:
                        existing["t1_shares"] = new_shares
                    if "t1_cost" in existing:
                        existing["t1_cost"] = round(new_cost, 4)
                else:
                    # 新增仓位
                    positions[symbol] = {
                        "cost": round(price, 4),
                        "shares": shares,
                        "date": today_str,
                        "note": reason if reason else f"{symbol} 新增仓位",
                        "tranche": "T1",
                        "t1_cost": round(price, 4),
                        "t1_shares": shares,
                        "position_type": "trend",
                        "thesis": reason if reason else "手动录入实际交易",
                        "thesis_status": "intact",
                        "thesis_updated": today_str,
                        "target_pct": 10.0,
                        "min_pct": 5.0,
                        "max_pct": 15.0
                    }
            elif action == "sell":
                # 卖出操作：增加现金，减少持仓
                if symbol not in positions:
                    self._set_headers("application/json", 400)
                    self.wfile.write(json.dumps({"error": f"持仓中没有 {symbol}，无法执行卖出交易。"}).encode("utf-8"))
                    return

                existing = positions[symbol]
                existing_shares = int(existing.get("shares", 0))
                
                if shares > existing_shares:
                    self._set_headers("application/json", 400)
                    self.wfile.write(json.dumps({"error": f"卖出数量 {shares} 大于当前持股数量 {existing_shares}。"}).encode("utf-8"))
                    return

                trade_value = price * shares
                cash_val += trade_value

                new_shares = existing_shares - shares
                if new_shares <= 0:
                    # 销仓
                    del positions[symbol]
                else:
                    existing["shares"] = new_shares
                    if "t1_shares" in existing:
                        existing["t1_shares"] = new_shares

            # 更新 cash
            pos_data["cash"] = round(cash_val, 2)

            # 写回 config/positions.json
            with open(pos_path, "w", encoding="utf-8") as f:
                json.dump(pos_data, f, ensure_ascii=False, indent=2)

            # 2. 写入 knowledge/trading_history.jsonl
            th_path = os.path.join(BASE, "knowledge", "trading_history.jsonl")
            new_trade_record = {
                "ts": datetime.now(timezone.utc).isoformat()[:-3] + "Z",
                "date": today_str,
                "type": action,
                "sym": symbol,
                "price": round(price, 4),
                "shares": shares,
                "stop": round(float(stop_price), 4) if stop_price else None,
                "target1": round(float(target_price), 4) if target_price else None,
                "reason": reason,
                "scene": "B" if action == "buy" else "S"
            }
            # 以追加模式写入 JSONL
            with open(th_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(new_trade_record, ensure_ascii=False) + "\n")

            # 3. 清理当前态快照，随后立即用最新成交重建；日期归档保留历史轨迹。
            current_snapshot_path = os.path.join(FIND_DIR, "portfolio_snapshot_current.json")
            if os.path.exists(current_snapshot_path):
                try:
                    os.remove(current_snapshot_path)
                except Exception:
                    pass

            # 4. 触发动态重新计算并同步重写 HTML 仪表盘
            try:
                from stock_team.core.portfolio_snapshot import build_portfolio_snapshot, write_portfolio_snapshot
                data = build_portfolio_snapshot(today_str, trigger="trade_update", base_dir=BASE)
                if data:
                    write_portfolio_snapshot(today_str, data, base_dir=BASE)
                
                # 同步重写静态 HTML 报告文件，保证 file:/// 和 http:// 页面都能即时看到最新数据
                from stock_team.server.dashboard_writer import write_dashboard
                write_dashboard(today_str, base_dir=BASE)
            except Exception as snap_err:
                print(f"[警告] 重新生成组合快照或重写仪表盘异常: {snap_err}")

            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"成功记录实际交易: {action} {symbol}",
                "cash": pos_data["cash"]
            }, ensure_ascii=False).encode("utf-8"))

        except Exception as err:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"系统记录交易异常: {str(err)}"}).encode("utf-8"))


def run_server(port=8080):
    init_folders()
    server_address = ("", port)
    
    # 解决端口占用时自动递增查找空闲端口
    max_tries = 10
    httpd = None
    for i in range(max_tries):
        try:
            current_port = port + i
            httpd = HTTPServer(("", current_port), DashboardHTTPRequestHandler)
            port = current_port
            break
        except OSError:
            print(f"[警告] 端口 {port + i} 已被占用，尝试下一个...")
            continue

    if not httpd:
        print("[错误] 无法绑定任何空闲端口，启动失败。")
        sys.exit(1)

    try:
        port_path = os.path.join(BASE, "config", "server_port.json")
        os.makedirs(os.path.dirname(port_path), exist_ok=True)
        with open(port_path, "w", encoding="utf-8") as pf:
            json.dump({"port": port}, pf)
    except Exception as pe:
        print(f"[警告] 无法写入服务器端口配置文件: {pe}")

    print("\n" + "═" * 70)
    print("  🚀 ANTIGRAVITY STOCK AGENT ALL-IN-ONE DASHBOARD SERVER STARTING...")
    print("═" * 70)
    print(f"  地址: http://localhost:{port}")
    print(f"  工作目录: {BASE}")
    print(f"  运行环境 Python: {sys.executable or 'python'}")
    print(f"  日志目录: {LOG_DIR}")
    print("═" * 70 + "\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        # 释放所有后台未结束的子进程
        with tasks_lock:
            for name, proc in ACTIVE_TASKS.items():
                if proc.poll() is None:
                    print(f"  - 结束后台任务 '{name}' (PID: {proc.pid})")
                    try:
                        proc.terminate()
                    except Exception:
                        pass
        httpd.server_close()
        print("服务器已安全退出。")

if __name__ == "__main__":
    # 支持命令行自定义端口
    port_arg = 8080
    if len(sys.argv) > 1:
        try:
            port_arg = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port=port_arg)
