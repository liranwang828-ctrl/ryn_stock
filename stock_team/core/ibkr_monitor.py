import os
import sys
import json
import time
import asyncio
import logging
import subprocess
from datetime import datetime, timezone
from ib_insync import IB, Stock
from stock_team.utils.workspace_paths import investing_os_home

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IBKR_Monitor")

# Base paths calculation
BASE = (os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
        if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) 
        else os.path.dirname(os.path.abspath(__file__)))
POS_PATH = os.path.join(BASE, "config", "positions.json")
RULES_PATH = os.path.join(BASE, "config", "tactical_rules.json")

# investing-os paths
BRAIN_BASE = investing_os_home(BASE)
WATCHLIST_PATH = os.path.join(BRAIN_BASE, "decision", "current-watchlist.md")
SNAPSHOT_JSON = os.path.join(BRAIN_BASE, "system", "data", "packets", "intraday_snapshot.json")
SNAPSHOT_MD = os.path.join(BRAIN_BASE, "system", "data", "packets", "intraday_snapshot.md")
EVENT_LOG_PATH = os.path.join(BRAIN_BASE, "system", "data", "packets", "ib_event_log.json")

def parse_watchlist_symbols(file_path):
    """
    Parses current-watchlist.md and extracts active uppercase ticker symbols.
    """
    symbols = set()
    if not os.path.exists(file_path):
        logger.warning(f"Watchlist file not found: {file_path}")
        return symbols
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2:
                        sym = parts[1]
                        # Verify it is a valid uppercase ticker symbol (1-5 chars)
                        if sym.isupper() and sym.isalpha() and 1 <= len(sym) <= 5:
                            symbols.add(sym)
    except Exception as e:
        logger.error(f"Error parsing watchlist: {e}")
    return symbols

def get_positions_symbols(file_path):
    """
    Loads symbols from config/positions.json.
    """
    symbols = set()
    if not os.path.exists(file_path):
        return symbols
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            positions = data.get("positions", {})
            for sym in positions.keys():
                if sym.isupper() and sym.isalpha() and 1 <= len(sym) <= 5:
                    symbols.add(sym)
    except Exception as e:
        logger.error(f"Error loading positions: {e}")
    return symbols

def load_tactical_rules(file_path):
    """
    Loads thresholds from config/tactical_rules.json.
    """
    rules = {
        "hard_stop_near_warn_pct": 3.0,
        "vwap_add_threshold": -1.5,
        "vwap_reduce_threshold": 1.5
    }
    if not os.path.exists(file_path):
        return rules
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Fetch from micro_strategy_params if present
            micro = data.get("micro_strategy_params", {})
            health = micro.get("thesis_health", {})
            flex = micro.get("flex_signals", {})
            if "hard_stop_near_warn_pct" in health:
                rules["hard_stop_near_warn_pct"] = float(health["hard_stop_near_warn_pct"])
            if "vwap_add_threshold" in flex:
                rules["vwap_add_threshold"] = float(flex["vwap_add_threshold"])
            if "vwap_reduce_threshold" in flex:
                rules["vwap_reduce_threshold"] = float(flex["vwap_reduce_threshold"])
    except Exception as e:
        logger.error(f"Error loading tactical rules: {e}")
    return rules

def log_ib_event(event_type, details):
    """
    Appends an event to the rolling event list in ib_event_log.json.
    """
    try:
        events = []
        if os.path.exists(EVENT_LOG_PATH):
            try:
                with open(EVENT_LOG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        events = data
                    elif isinstance(data, dict):
                        events = [data]
            except Exception:
                pass
                
        event_record = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **details
        }
        events.append(event_record)
        
        # Keep last 100 events
        if len(events) > 100:
            events = events[-100:]
            
        os.makedirs(os.path.dirname(EVENT_LOG_PATH), exist_ok=True)
        with open(EVENT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to log IB event: {e}")

def update_positions_file(ib):
    """
    Reads active portfolio from IB and syncs config/positions.json automatically.
    """
    try:
        ib_positions = ib.positions()
        cash = 0.0
        net_liq = 0.0
        for v in ib.accountValues():
            if v.tag == 'TotalCashValue' and v.currency == 'USD':
                cash = float(v.value)
            elif v.tag == 'NetLiquidation' and v.currency == 'USD':
                net_liq = float(v.value)
        
        if not os.path.exists(POS_PATH):
            logger.error(f"positions.json not found at {POS_PATH}")
            return
            
        with open(POS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        data["cash"] = cash
        data["cash_updated"] = datetime.now().strftime("%Y-%m-%d")
        
        current_pos_dict = {}
        for p in ib_positions:
            sym = p.contract.symbol
            current_pos_dict[sym] = p
            
        # Update cost and shares for active positions
        for sym, pos_obj in current_pos_dict.items():
            shares = int(pos_obj.position)
            cost = float(pos_obj.avgCost)
            if shares == 0:
                if sym in data.get("positions", {}):
                    del data["positions"][sym]
                continue
                
            if "positions" not in data:
                data["positions"] = {}
                
            if sym not in data["positions"]:
                # Initialize new position
                data["positions"][sym] = {
                    "cost": cost,
                    "shares": shares,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "note": "Auto-added by IBKR Monitor",
                    "tranche": "tactical",
                    "thesis_status": "needs_review",
                    "falsification_conditions": []
                }
            else:
                data["positions"][sym]["shares"] = shares
                data["positions"][sym]["cost"] = cost
                
        # Remove closed positions
        for sym in list(data.get("positions", {}).keys()):
            if sym not in current_pos_dict:
                del data["positions"][sym]
                
        data["positions_updated"] = datetime.now().strftime("%Y-%m-%d")
        data["local_record_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save positions.json
        with open(POS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info("[IBKR Sync] Positions synchronized successfully.")
        
        # Write to ib_event_log.json
        log_ib_event("positions_synchronized", {
            "cash": cash,
            "net_liquidation": net_liq,
            "positions_count": len(ib_positions)
        })
            
    except Exception as e:
        logger.error(f"Failed to synchronize positions file: {e}")

def run_offline_fallback(symbols):
    """
    Subprocess fallback calling poll.py --once to query yfinance.
    Parses results and outputs standard JSON snapshot.
    """
    logger.warning("Starting yfinance offline fallback execution...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Execute poll.py as subprocess
    script_path = os.path.join(BASE, "agents", "poll.py")
    cmd = [sys.executable, script_path, "--once"] + list(symbols)
    
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=BASE, encoding="utf-8")
        if res.returncode != 0:
            logger.error(f"Fallback subprocess failed with return code {res.returncode}: {res.stderr}")
    except Exception as e:
        logger.error(f"Failed to launch fallback subprocess: {e}")
        
    # Read the latest generated poll_state_{date}.json
    poll_state_path = os.path.join(BASE, "learning", f"poll_state_{date_str}.json")
    if not os.path.exists(poll_state_path):
        logger.error(f"Fallback poll state file not found: {poll_state_path}")
        write_error_snapshot("Fallback state not found.")
        return
        
    try:
        with open(poll_state_path, "r", encoding="utf-8") as f:
            poll_state = json.load(f)
            
        # Read positions.json for static fallback portfolio cash
        static_cash = 10000.0
        static_net_liq = 10000.0
        if os.path.exists(POS_PATH):
            with open(POS_PATH, "r", encoding="utf-8") as pf:
                pd = json.load(pf)
                static_cash = pd.get("cash", 10000.0)
                
        mc = poll_state.get("market_context", {})
        
        # Ingest symbols and positions
        positions_out = {}
        alerts_out = []
        
        symbols_data = poll_state.get("symbols", {})
        positions_data = poll_state.get("positions_summary", {})
        
        # Sum portfolio values
        total_market_value = 0.0
        total_unrealized_pnl = 0.0
        
        # Read positions.json to match shares
        pos_shares_map = {}
        if os.path.exists(POS_PATH):
            with open(POS_PATH, "r", encoding="utf-8") as pf:
                pd = json.load(pf)
                for sym, p_val in pd.get("positions", {}).items():
                    pos_shares_map[sym] = p_val.get("shares", 0)
                    
        for sym, p_val in positions_data.items():
            shares = pos_shares_map.get(sym, 0)
            cost = p_val.get("cost", 0.0)
            curr = p_val.get("current", 0.0)
            mval = shares * curr
            upnl = shares * (curr - cost)
            total_market_value += mval
            total_unrealized_pnl += upnl
            
            positions_out[sym] = {
                "cost": cost,
                "shares": shares,
                "current_price": curr,
                "market_value": round(mval, 2),
                "unrealized_pnl": round(upnl, 2),
                "pct_of_portfolio": 0.0  # Will calculate below
            }
            
        static_net_liq = static_cash + total_market_value
        
        for sym in positions_out.keys():
            mval = positions_out[sym]["market_value"]
            positions_out[sym]["pct_of_portfolio"] = round((mval / static_net_liq * 100) if static_net_liq else 0.0, 2)
            
        # Parse Alerts
        for sym, s_val in symbols_data.items():
            pvn = s_val.get("plan_vs_now", {})
            thesis_sig = pvn.get("thesis_signal", "intact")
            last_price = s_val.get("last_price", 0.0)
            
            # Load premarket stop loss
            pm_path = os.path.join(BASE, "findings", f"premarket_summary_{date_str}_{sym}.json")
            hard_stop = None
            if os.path.exists(pm_path):
                try:
                    with open(pm_path, encoding='utf-8') as pmf:
                        pm_d = json.load(pmf)
                        hard_stop = pm_d.get('exit', {}).get('hard_stop') or pm_d.get('exit', {}).get('stop_loss')
                except Exception:
                    pass
            
            if thesis_sig == "breach" or (hard_stop and last_price <= hard_stop):
                alerts_out.append({
                    "symbol": sym,
                    "level": "RED",
                    "alert_type": "hard_stop_breach",
                    "message": f"Price ${last_price} is at or below Stop Loss level ${hard_stop} (Thesis Breach)."
                })
            elif thesis_sig == "warning" or (hard_stop and last_price <= hard_stop * 1.03):
                alerts_out.append({
                    "symbol": sym,
                    "level": "YELLOW",
                    "alert_type": "thesis_warning",
                    "message": f"Price ${last_price} approaching Stop Loss level ${hard_stop}."
                })
                
        snapshot_data = {
            "timestamp": datetime.now().isoformat(),
            "source": "offline_fallback",
            "account": {
                "cash": round(static_cash, 2),
                "net_liquidation": round(static_net_liq, 2),
                "unrealized_pnl": round(total_unrealized_pnl, 2),
                "day_pnl": 0.0
            },
            "positions": positions_out,
            "alerts": alerts_out
        }
        
        write_snapshot_packets(snapshot_data)
        logger.info("[Fallback] Successfully exported yfinance fallback snapshot.")
    except Exception as e:
        logger.error(f"Error compiling fallback snapshot: {e}")
        write_error_snapshot(str(e))

def write_error_snapshot(err_msg):
    """Writes a degraded error snapshot to prevent brain crashes."""
    snapshot_data = {
        "timestamp": datetime.now().isoformat(),
        "source": "offline_fallback",
        "account": { "cash": 0.0, "net_liquidation": 0.0, "unrealized_pnl": 0.0, "day_pnl": 0.0 },
        "positions": {},
        "alerts": [{
            "symbol": "SYSTEM",
            "level": "RED",
            "alert_type": "system_offline",
            "message": f"TWS client offline. Offline fallback failed: {err_msg}"
        }]
    }
    write_snapshot_packets(snapshot_data)

def write_snapshot_packets(data):
    """Writes JSON and Markdown snapshots to the investing-os folders."""
    try:
        os.makedirs(os.path.dirname(SNAPSHOT_JSON), exist_ok=True)
        
        # 1. Write JSON
        with open(SNAPSHOT_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        # 2. Write Markdown
        md_lines = []
        md_lines.append("# Intraday Snapshot Status")
        md_lines.append(f"**Last Sync time**: `{data['timestamp']}`")
        md_lines.append(f"**Data Source**: `{data['source']}`")
        md_lines.append("")
        md_lines.append("## Account Summary")
        md_lines.append(f"- **Net Liquidation**: `${data['account']['net_liquidation']:,.2f}`")
        md_lines.append(f"- **Available Cash**: `${data['account']['cash']:,.2f}`")
        md_lines.append(f"- **Total Unrealized PnL**: `${data['account']['unrealized_pnl']:,.2f}`")
        md_lines.append(f"- **Day PnL**: `${data['account']['day_pnl']:,.2f}`")
        md_lines.append("")
        md_lines.append("## Active Positions")
        md_lines.append("| Symbol | Cost | Shares | Price | Market Value | PnL | Portfolio % |")
        md_lines.append("|---|---|---|---|---|---|---|")
        if not data["positions"]:
            md_lines.append("| - | - | - | - | - | - | - |")
        for sym, p in data["positions"].items():
            md_lines.append(f"| {sym} | ${p['cost']:.2f} | {p['shares']} | ${p['current_price']:.2f} | ${p['market_value']:,.2f} | ${p['unrealized_pnl']:+,.2f} | {p['pct_of_portfolio']:.2f}% |")
            
        md_lines.append("")
        md_lines.append("## Triggered Alert Notifications")
        if not data["alerts"]:
            md_lines.append("*No active alerts. System healthy.*")
        else:
            for alert in data["alerts"]:
                lvl = "🔴" if alert["level"] == "RED" else ("🟡" if alert["level"] == "YELLOW" else "ℹ️")
                md_lines.append(f"- {lvl} **[{alert['symbol']}]** ({alert['alert_type']}): {alert['message']}")
                
        with open(SNAPSHOT_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
            
    except Exception as e:
        logger.error(f"Failed to write snapshot files: {e}")

def load_cached_fallback_prices():
    """
    Looks for the latest poll_state_*.json or loads from positions.json
    to provide fallback prices for symbols when TWS returns NaN.
    """
    fallback_prices = {}
    
    # 1. Try positions.json first
    if os.path.exists(POS_PATH):
        try:
            with open(POS_PATH, "r", encoding="utf-8") as f:
                pd = json.load(f)
                # Read broker_last_price if present
                for sym, pos_data in pd.get("positions", {}).items():
                    if "broker_last_price" in pos_data:
                        price = float(pos_data["broker_last_price"])
                        if price > 0:
                            fallback_prices[sym] = price
        except Exception as e:
            logger.warning(f"Error reading positions.json for fallback prices: {e}")
            
    # 2. Try latest poll_state_*.json in learning directory
    learning_dir = os.path.join(BASE, "learning")
    if os.path.exists(learning_dir):
        try:
            files = [f for f in os.listdir(learning_dir) if f.startswith("poll_state_") and f.endswith(".json")]
            if files:
                # Sort files to get the latest one
                files.sort(reverse=True)
                latest_file = os.path.join(learning_dir, files[0])
                with open(latest_file, "r", encoding="utf-8") as f:
                    poll_data = json.load(f)
                    
                    # Read from positions_summary
                    for sym, val in poll_data.get("positions_summary", {}).items():
                        price = val.get("current") or val.get("cost")
                        if price:
                            fallback_prices[sym] = float(price)
                            
                    # Read from symbols
                    for sym, val in poll_data.get("symbols", {}).items():
                        price = val.get("last_price")
                        if price:
                            fallback_prices[sym] = float(price)
        except Exception as e:
            logger.warning(f"Error reading poll_state for fallback prices: {e}")
            
    return fallback_prices

async def run_monitor_loop(ib, symbols, rules):
    """
    Subscribes to live tickers from TWS and prints/writes snapshots periodically.
    """
    logger.info(f"Connected. Subscribing to market data for: {list(symbols)}")
    
    # Update positions.json initially
    update_positions_file(ib)
    
    # Set up position update listener
    ib.positionEvent += lambda p: update_positions_file(ib)
    
    tickers = []
    for sym in symbols:
        # Skip placeholder or invalid symbols
        if sym in ["SNXX", "SYSTEM"]:
            continue
        contract = Stock(sym, 'SMART', 'USD')
        tickers.append(ib.reqMktData(contract, '', False, False))
        
    logger.info("Subscriptions created. Commencing event-driven stream check...")
    
    # Load fallback prices from cache files
    fallback_prices = load_cached_fallback_prices()
    logger.info(f"Loaded {len(fallback_prices)} cached fallback prices: {fallback_prices}")
    
    last_alert_state = {}
    
    while True:
        try:
            # Refresh account summary values from local memory cache
            cash = 0.0
            net_liq = 0.0
            unrealized_pnl = 0.0
            day_pnl = 0.0
            
            for v in ib.accountValues():
                if v.tag == 'TotalCashValue' and v.currency == 'USD':
                    cash = float(v.value)
                elif v.tag == 'NetLiquidation' and v.currency == 'USD':
                    net_liq = float(v.value)
                elif v.tag == 'UnrealizedPnL' and v.currency == 'USD':
                    unrealized_pnl = float(v.value)
                elif v.tag == 'DailyPnL' and v.currency == 'USD':
                    day_pnl = float(v.value)
            
            # Get latest portfolio prices from TWS memory
            portfolio_prices = {}
            for item in ib.portfolio():
                if item.marketPrice and item.marketPrice == item.marketPrice:  # check not NaN
                    portfolio_prices[item.contract.symbol] = item.marketPrice
                    
            # Load active positions from positions.json (to get exact shares)
            pos_shares_map = {}
            pos_cost_map = {}
            if os.path.exists(POS_PATH):
                with open(POS_PATH, "r", encoding="utf-8") as pf:
                    pd = json.load(pf)
                    for sym, p_val in pd.get("positions", {}).items():
                        pos_shares_map[sym] = p_val.get("shares", 0)
                        pos_cost_map[sym] = p_val.get("cost", 0.0)
                        
            positions_out = {}
            alerts_out = []
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # Map ticker prices and calculate indicators
            current_alert_keys = set()
            
            for ticker in tickers:
                sym = ticker.contract.symbol
                # Use last price, falling back to marketPrice or close
                price = ticker.last if (ticker.last and not ticker.last != ticker.last) else ticker.marketPrice()
                if not price or price != price: # handle NaN or None
                    price = ticker.close if (ticker.close and not ticker.close != ticker.close) else 0.0
                    
                # Fallback to portfolio market price if still 0.0/NaN
                if (not price or price <= 0.0) and sym in portfolio_prices:
                    price = portfolio_prices[sym]
                    
                # Fallback to cached yfinance/positions price if still 0.0/NaN
                if (not price or price <= 0.0) and sym in fallback_prices:
                    price = fallback_prices[sym]
                    
                if price <= 0.0:
                    continue
                    
                shares = pos_shares_map.get(sym, 0)
                cost = pos_cost_map.get(sym, 0.0)
                mval = shares * price
                upnl = shares * (price - cost)
                
                # Check if held
                if shares > 0:
                    positions_out[sym] = {
                        "cost": cost,
                        "shares": shares,
                        "current_price": price,
                        "market_value": round(mval, 2),
                        "unrealized_pnl": round(upnl, 2),
                        "pct_of_portfolio": round((mval / net_liq * 100) if net_liq else 0.0, 2)
                    }
                    
                # Load premarket rules stops
                pm_path = os.path.join(BASE, "findings", f"premarket_summary_{today_str}_{sym}.json")
                hard_stop = None
                target = None
                if os.path.exists(pm_path):
                    try:
                        with open(pm_path, encoding='utf-8') as pmf:
                            pm_d = json.load(pmf)
                            exit_n = pm_d.get('exit', {})
                            hard_stop = exit_n.get('hard_stop') or exit_n.get('stop_loss')
                            target = exit_n.get('target') or exit_n.get('target_price')
                    except Exception:
                        pass
                
                # Calculate stop-loss alert
                dist_to_stop_pct = None
                if hard_stop and price:
                    dist_to_stop_pct = round((price - hard_stop) / price * 100, 2)
                    
                    if price <= hard_stop:
                        alerts_out.append({
                            "symbol": sym,
                            "level": "RED",
                            "alert_type": "hard_stop_breach",
                            "message": f"Price ${price:.2f} is at or below Stop Loss level ${hard_stop:.2f}!"
                        })
                        current_alert_keys.add(f"{sym}_RED_stop")
                    elif dist_to_stop_pct < rules["hard_stop_near_warn_pct"]:
                        alerts_out.append({
                            "symbol": sym,
                            "level": "YELLOW",
                            "alert_type": "hard_stop_approach",
                            "message": f"Price ${price:.2f} is approaching Stop Loss (${hard_stop:.2f}) | Distance: {dist_to_stop_pct}%."
                        })
                        current_alert_keys.add(f"{sym}_YELLOW_stop")
                        
                # Calculate VWAP alert
                vwap = ticker.vwap
                if vwap and vwap > 0.0:
                    vwap_dist_pct = round((price - vwap) / vwap * 100, 2)
                    if vwap_dist_pct <= rules["vwap_add_threshold"]:
                        alerts_out.append({
                            "symbol": sym,
                            "level": "YELLOW",
                            "alert_type": "vwap_add_deviation",
                            "message": f"Price ${price:.2f} is below daily VWAP (${vwap:.2f}) by {vwap_dist_pct}% (Limit: {rules['vwap_add_threshold']}%)."
                        })
                        current_alert_keys.add(f"{sym}_YELLOW_vwap_add")
                    elif vwap_dist_pct >= rules["vwap_reduce_threshold"]:
                        alerts_out.append({
                            "symbol": sym,
                            "level": "YELLOW",
                            "alert_type": "vwap_reduce_deviation",
                            "message": f"Price ${price:.2f} is above daily VWAP (${vwap:.2f}) by {vwap_dist_pct}% (Limit: {rules['vwap_reduce_threshold']}%)."
                        })
                        current_alert_keys.add(f"{sym}_YELLOW_vwap_reduce")

            # Calculate sum of unrealized PnL from positions as fallback for overall PnL
            calc_unrealized_pnl = sum(pos["unrealized_pnl"] for pos in positions_out.values())
            if unrealized_pnl == 0.0 and calc_unrealized_pnl != 0.0:
                unrealized_pnl = calc_unrealized_pnl

            snapshot_data = {
                "timestamp": datetime.now().isoformat(),
                "source": "ibkr_stream",
                "account": {
                    "cash": round(cash, 2),
                    "net_liquidation": round(net_liq, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "day_pnl": round(day_pnl, 2)
                },
                "positions": positions_out,
                "alerts": alerts_out
            }
            
            # Check if alert status changed. If so, print to console instantly.
            alert_states_str = ",".join(sorted(list(current_alert_keys)))
            if last_alert_state.get("states") != alert_states_str:
                logger.info(f"Alert state changed: {alert_states_str if alert_states_str else 'All Clear'}")
                
                # Log alert changes to timeline
                old_keys = set(last_alert_state.get("keys_set", []))
                added_alerts = current_alert_keys - old_keys
                cleared_alerts = old_keys - current_alert_keys
                
                for key in added_alerts:
                    # Find matching alert details
                    matching_alerts = [a for a in alerts_out if key.startswith(a["symbol"])]
                    alert_detail = matching_alerts[0] if matching_alerts else {"symbol": key.split("_")[0]}
                    log_ib_event("alert_triggered", {
                        "symbol": alert_detail.get("symbol"),
                        "level": alert_detail.get("level", "YELLOW"),
                        "alert_type": alert_detail.get("alert_type", "deviation"),
                        "message": alert_detail.get("message", f"Alert triggered: {key}")
                    })
                    
                for key in cleared_alerts:
                    log_ib_event("alert_cleared", {
                        "symbol": key.split("_")[0],
                        "alert_key": key
                    })
                
                last_alert_state["states"] = alert_states_str
                last_alert_state["keys_set"] = list(current_alert_keys)
                # Instantly write
                write_snapshot_packets(snapshot_data)
            else:
                # Periodic write every 10 seconds
                last_write = last_alert_state.get("last_write", 0)
                if time.time() - last_write >= 10:
                    write_snapshot_packets(snapshot_data)
                    last_alert_state["last_write"] = time.time()
                    
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in monitor loop iteration: {e}")
            await asyncio.sleep(5)

def main():
    # Load targets
    watchlist_symbols = parse_watchlist_symbols(WATCHLIST_PATH)
    position_symbols = get_positions_symbols(POS_PATH)
    all_symbols = watchlist_symbols.union(position_symbols)
    
    if not all_symbols:
        logger.warning("No symbols found to monitor. Defaulting to standard SPY/QQQ/NVDA watchlist.")
        all_symbols = {"SPY", "QQQ", "NVDA"}
        
    rules = load_tactical_rules(RULES_PATH)
    
    logger.info(f"Target Watchlist Symbols: {watchlist_symbols}")
    logger.info(f"Target Position Symbols: {position_symbols}")
    logger.info(f"Combined Monitoring Set ({len(all_symbols)}): {list(all_symbols)}")
    
    # Try connecting to TWS/Gateway
    ports = [7497, 7496, 4002, 4001]
    connected = False
    ib = IB()
    
    for port in ports:
        logger.info(f"Connecting to TWS port {port}...")
        try:
            ib.connect('127.0.0.1', port, clientId=10, timeout=5)
            connected = True
            logger.info(f"Successfully connected to port {port}!")
            break
        except Exception as e:
            logger.info(f"Failed to connect on port {port}.")
            
    if connected:
        try:
            asyncio.run(run_monitor_loop(ib, all_symbols, rules))
        except KeyboardInterrupt:
            logger.info("Termination request received. Disconnecting...")
        finally:
            ib.disconnect()
    else:
        logger.warning("Could not connect to TWS. Commencing offline fallback mode.")
        run_offline_fallback(all_symbols)
        
if __name__ == '__main__':
    main()
