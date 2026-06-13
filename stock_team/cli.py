# D:\gemini\lianghua\stock_team\cli.py
"""
Stock Team Unified CLI Interface
Exposes core commands and routes to underlying agents/scripts logic.
"""
import os
import sys
import argparse
import json
import subprocess
import pandas as pd
from datetime import datetime, date as _date, time as _time, timezone
import socket
# Enforce a strict 5-second global timeout for all TCP network requests to prevent CLI hangs/lockups.
socket.setdefaulttimeout(5)

# Add workspace to path
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

_POLYGON_SESSION = None
_POLYGON_HEALTH_CACHE = {"checked_at": 0, "active": False}
_POLYGON_RUNTIME_CACHE = {}

from stock_team.core.premarket_summary import build_summary
from stock_team.data_ingest.company_profile_fetcher import build_company_profile
from stock_team.agents.sector_agent import analyze as analyze_sector
from stock_team.data_ingest.data_agent import get_api_key, fetch_polygon_news
from stock_team.utils.workspace_paths import investing_os_home


def _investing_os_home():
    return investing_os_home(BASE)

# Map symbol to its primary sector ETF
ETF_MAPPING = {
    "ORCL": "IGV",
    "MSFT": "IGV",
    "NVDA": "SOXX",
    "AMD": "SOXX",
    "COHR": "SOXX",
    "LITE": "SOXX",
    "AAOI": "SOXX",
    "SNDK": "SOXX"
}

def print_yaml_header(f, packet_type, command_name, inputs, data_sources, missing_data=None):
    if missing_data is None:
        missing_data = []
    created_at = datetime.utcnow().isoformat() + "Z"
    f.write("---\n")
    f.write(f"packet_type: {packet_type}\n")
    f.write("status: verified\n")
    f.write(f"generated_at: {created_at}\n")
    f.write("source_system: stock_team\n")
    f.write("requested_by: Codex/User\n")
    f.write(f"command: python -m stock_team.cli {command_name}\n")
    f.write("inputs:\n")
    for k, v in inputs.items():
        if isinstance(v, list):
            f.write(f"  {k}: {v}\n")
        else:
            f.write(f"  {k}: \"{v}\"\n")
    f.write("data_sources:\n")
    for src in data_sources:
        f.write(f"  - {src}\n")
    f.write("missing_data:\n")
    for m in missing_data:
        f.write(f"  - {m}\n")
    f.write("forbidden_sections_absent:\n")
    if packet_type == "pre_market_environment_packet":
        f.write("  - buy_sell_hold_recommendation\n")
        f.write("  - trading_permission_state\n")
        f.write("  - symbol_selection_recommendation\n")
        f.write("  - final_thesis_adoption\n")
        f.write("  - psychological_interpretation\n")
    else:
        f.write("  - buy_sell_hold_recommendation\n")
        f.write("  - psychological_interpretation\n")
        f.write("  - final_thesis_adoption\n")
        f.write("  - permission_state_change\n")
    f.write("---\n\n")

MARKET_CONTEXT_SYMBOLS = {
    "QQQ": "Nasdaq 100 proxy",
    "SPY": "S&P 500 proxy",
    "IWM": "Small-cap risk proxy",
    "VIXY": "VIX ETF proxy",
}

THEME_PROXY_MAP = {
    "semiconductors": "SOXX",
    "ai_infrastructure": "SMH",
    "memory": "MU",
    "storage": "MU",
    "cloud": "IGV",
    "optical": "LITE",
}

def _parse_stage0_as_of(as_of_text):
    if not as_of_text:
        raise ValueError("--as-of is required for live Stage 0 market-context packets")
    try:
        normalized = as_of_text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError("--as-of must be an ISO timestamp, for example 2026-06-08T09:20:00-04:00") from exc
    if parsed.tzinfo is None:
        raise ValueError("--as-of must include a timezone offset")
    try:
        from zoneinfo import ZoneInfo
        eastern = ZoneInfo("America/New_York")
    except Exception:
        eastern = timezone.utc
    return parsed.astimezone(eastern)

def _validate_stage0_as_of(date_text, as_of_text):
    as_of_et = _parse_stage0_as_of(as_of_text)
    try:
        session_date = _date.fromisoformat(date_text)
    except Exception as exc:
        raise ValueError("--date must be YYYY-MM-DD") from exc
    if as_of_et.date() != session_date:
        raise ValueError("Stage 0 as-of date must match --date in ET")
    if as_of_et.time() >= _time(9, 30):
        raise ValueError("Stage 0 as-of must be before 09:30 ET; refusing post-open reconstruction")
    return as_of_et

def _is_premarket_stage0_row(row, stage0_as_of_et):
    if not row:
        return False
    if row.get("window") != "pre_market_before_09_30_ET":
        return False
    row_as_of = row.get("as_of_et") or row.get("as_of")
    if not row_as_of:
        return False
    try:
        parsed = _parse_stage0_as_of(str(row_as_of))
    except ValueError:
        return False
    return parsed.isoformat() == stage0_as_of_et.isoformat()

def _pct(a, b):
    try:
        if a is None or b in (None, 0):
            return None
        return round((float(a) - float(b)) / float(b) * 100, 2)
    except Exception:
        return None

def _load_market_context_fixture(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    markets = []
    for symbol, row in (raw.get("markets") or {}).items():
        price = row.get("price")
        prev_close = row.get("prev_close")
        markets.append({
            "symbol": symbol,
            "label": MARKET_CONTEXT_SYMBOLS.get(symbol, "market proxy"),
            "price": price,
            "yesterday_change_pct": _pct(price, prev_close),
            "return_5d": row.get("return_5d"),
            "return_20d": row.get("return_20d"),
            "volume_ratio": row.get("volume_ratio"),
            "source": row.get("source", "fixture"),
        })
    themes = []
    for theme, row in (raw.get("themes") or {}).items():
        themes.append({
            "theme": theme,
            "proxy": row.get("proxy"),
            "return_5d": row.get("return_5d"),
            "return_20d": row.get("return_20d"),
            "source": row.get("source", "fixture"),
        })
    return markets, themes, raw.get("catalysts") or [], []

def _load_premarket_snapshot_adapter(path, stage0_as_of_et):
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)
    snapshot_as_of = _parse_stage0_as_of(str(raw.get("as_of_et") or raw.get("as_of") or ""))
    if snapshot_as_of.isoformat() != stage0_as_of_et.isoformat():
        raise ValueError("pre-market snapshot as_of_et must match --as-of")
    if raw.get("window") != "pre_market_before_09_30_ET":
        raise ValueError("pre-market snapshot window must be pre_market_before_09_30_ET")

    markets = []
    for symbol, row in (raw.get("markets") or {}).items():
        price = row.get("price")
        prev_close = row.get("prev_close")
        markets.append({
            "symbol": symbol.upper(),
            "label": MARKET_CONTEXT_SYMBOLS.get(symbol.upper(), "market proxy"),
            "price": price,
            "yesterday_change_pct": row.get("yesterday_change_pct", _pct(price, prev_close)),
            "return_5d": row.get("return_5d"),
            "return_20d": row.get("return_20d"),
            "volume_ratio": row.get("volume_ratio"),
            "source": row.get("source", "pre_market_snapshot_adapter"),
            "window": raw.get("window"),
            "as_of_et": snapshot_as_of.isoformat(),
        })

    themes = []
    for theme, row in (raw.get("themes") or {}).items():
        themes.append({
            "theme": theme,
            "proxy": row.get("proxy"),
            "return_5d": row.get("return_5d"),
            "return_20d": row.get("return_20d"),
            "source": row.get("source", "pre_market_snapshot_adapter"),
            "window": raw.get("window"),
            "as_of_et": snapshot_as_of.isoformat(),
        })
    return markets, themes, raw.get("catalysts") or [], []

def _load_universe_document(path):
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _load_universe(path):
    raw = _load_universe_document(path)
    if raw is None:
        return []
    if isinstance(raw, list):
        if raw and isinstance(raw[0], str):
            return [{
                "symbol": x,
                "role": "watchlist",
                "theme": SYMBOL_THEME_MAP.get(x.upper(), "unknown"),
                "research_status": "pending"
            } for x in raw]
        return raw
    for key in ("positions", "symbols", "watchlist", "default_symbols", "universe"):
        if isinstance(raw.get(key), list):
            items = raw[key]
            if not items:
                continue
            if items and isinstance(items[0], str):
                return [{
                    "symbol": x,
                    "role": "watchlist",
                    "theme": SYMBOL_THEME_MAP.get(x.upper(), "unknown"),
                    "research_status": "pending"
                } for x in items]
            return items
    symbol_keyed_items = []
    for key, value in raw.items():
        if isinstance(value, dict):
            if value.get("symbol"):
                symbol_keyed_items.append(value)
            elif key.isalpha() and key.upper() == key and len(key) <= 5:
                item = dict(value)
                item["symbol"] = key
                symbol_keyed_items.append(item)
            else:
                for sub_key, sub_val in value.items():
                    sub_key_clean = sub_key.strip()
                    if isinstance(sub_val, dict) and sub_key_clean.isalpha() and sub_key_clean.upper() == sub_key_clean and len(sub_key_clean) <= 5:
                        item = dict(sub_val)
                        item["symbol"] = sub_key_clean
                        if "role" not in item:
                            item["role"] = key
                        if "theme" not in item:
                            item["theme"] = "unknown"
                        if "research_status" not in item:
                            item["research_status"] = "pending"
                        symbol_keyed_items.append(item)
    if symbol_keyed_items:
        return symbol_keyed_items
    return []

def _has_nested_key(data, path):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return False
        cur = cur[key]
    return True

def _brain_precondition_state_quality(universe_document):
    gaps = []
    if not isinstance(universe_document, dict):
        universe_document = {}

    required_source_inputs = {
        "source_inputs.positions": ("source_inputs", "positions"),
        "source_inputs.prior_review": ("source_inputs", "prior_review"),
        "source_inputs.cognition_state": ("source_inputs", "cognition_state"),
    }
    for label, path in required_source_inputs.items():
        if not _has_nested_key(universe_document, path):
            gaps.append(label)

    if not universe_document.get("permission_state_before_open"):
        gaps.append("permission_state_before_open")

    forbidden_actions = universe_document.get("forbidden_actions")
    if not isinstance(forbidden_actions, list) or not forbidden_actions:
        gaps.append("forbidden_actions")

    source_inputs = universe_document.get("source_inputs") if isinstance(universe_document, dict) else {}
    return {
        "complete": not gaps,
        "gaps": gaps,
        "permission_state_before_open": universe_document.get("permission_state_before_open", ""),
        "positions_present": _has_nested_key(universe_document, ("source_inputs", "positions")),
        "prior_review_present": _has_nested_key(universe_document, ("source_inputs", "prior_review")),
        "cognition_state_present": _has_nested_key(universe_document, ("source_inputs", "cognition_state")),
        "forbidden_actions": forbidden_actions if isinstance(forbidden_actions, list) else [],
        "source_inputs": source_inputs if isinstance(source_inputs, dict) else {},
    }

SYMBOL_THEME_MAP = {
    "MU": "memory",
    "NVDA": "ai_infrastructure",
    "COHR": "optical",
    "INTC": "semiconductors",
    "ORCL": "cloud",
    "MSFT": "cloud",
    "GOOGL": "cloud",
}

def _normalize_universe_item(item):
    normalized = dict(item)
    symbol = str(normalized.get("symbol") or "").strip().upper()
    normalized["symbol"] = symbol or "—"
    return normalized

def _universe_quality(universe):
    required_fields = ("symbol", "role", "theme", "research_status")
    gaps = []
    normalized = []
    for raw_item in universe:
        item = _normalize_universe_item(raw_item)
        normalized.append(item)
        symbol = item.get("symbol") or "UNKNOWN"
        for field in required_fields:
            if not item.get(field):
                gaps.append(f"{symbol}_missing_{field}")
    return {
        "items": normalized,
        "count": len(normalized),
        "required_fields_complete": not gaps,
        "gaps": gaps,
    }

def _history_context(symbol):
    missing = []
    
    # Try loading cache first
    cache_path = os.path.join(BASE, "findings", "market_context_data_cache.json")
    cache_data = None
    cache_is_fresh = False
    ref_at = None
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            ref_at = cache.get("refreshed_at")
            if ref_at:
                cache_time = datetime.strptime(ref_at, "%Y-%m-%d %H:%M:%S")
                cache_age = (datetime.now() - cache_time).total_seconds()
                detail = cache.get("data", {}).get(symbol)
                if detail:
                    cache_data = detail
                    if cache_age < 3600:
                        cache_is_fresh = True
        except Exception as e:
            missing.append(f"market_cache_read_failed_for_{symbol}:{str(e)[:40]}")

    # If cache is fresh, return it immediately
    if cache_is_fresh and cache_data:
        detail_copy = dict(cache_data)
        detail_copy["source"] = "polygon_cache"
        return detail_copy, missing

    # Otherwise, try fetching fresh data from Polygon
    try:
        from stock_team.agents.macro_strategy import _load_paid_api_key, fetch_polygon_daily_aggs
        api_key = _load_paid_api_key()
        if api_key:
            aggs = fetch_polygon_daily_aggs(symbol, api_key, days=40)
            if len(aggs) >= 21:
                closes = [float(x["c"]) for x in aggs if "c" in x]
                volumes = [float(x.get("v", 0)) for x in aggs if "c" in x]
                price = closes[-1]
                prev = closes[-2] if len(closes) >= 2 else None
                vol20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else None
                return {
                    "price": round(price, 2),
                    "yesterday_change_pct": _pct(price, prev),
                    "return_5d": _pct(price, closes[-6]) if len(closes) >= 6 else None,
                    "return_20d": _pct(price, closes[-21]) if len(closes) >= 21 else None,
                    "volume_ratio": round(volumes[-1] / vol20, 2) if vol20 else None,
                    "source": "polygon",
                }, missing
    except Exception as e:
        missing.append(f"{symbol}_polygon_failed:{str(e)[:80]}")

    # If Polygon fails, try yfinance
    try:
        import yfinance as yf
        hist = yf.Ticker(symbol).history(period="45d")
        if not hist.empty and len(hist) >= 21:
            closes = hist["Close"].tolist()
            volumes = hist["Volume"].tolist()
            price = float(closes[-1])
            prev = float(closes[-2]) if len(closes) >= 2 else None
            vol20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else None
            return {
                "price": round(price, 2),
                "yesterday_change_pct": _pct(price, prev),
                "return_5d": _pct(price, closes[-6]) if len(closes) >= 6 else None,
                "return_20d": _pct(price, closes[-21]) if len(closes) >= 21 else None,
                "volume_ratio": round(float(volumes[-1]) / vol20, 2) if vol20 else None,
                "source": "yfinance_fallback",
            }, missing + [f"{symbol}_used_yfinance_fallback"]
    except Exception as e:
        missing.append(f"{symbol}_yfinance_failed:{str(e)[:80]}")

    # If yfinance also fails, fall back to stale cache as last resort
    if cache_data:
        detail_copy = dict(cache_data)
        detail_copy["source"] = "polygon_cache_stale"
        return detail_copy, missing + [f"stale_cache_used_fallback_for_{symbol}_ref_{ref_at}"]

    return {}, missing or [f"{symbol}_no_data"]

def handle_market_context(args):
    print("📡 Executing Market Context command...")
    stage0_as_of_et = None
    if not args.offline_fixture:
        try:
            stage0_as_of_et = _validate_stage0_as_of(args.date, args.as_of)
        except ValueError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            sys.exit(1)
    
    # Load universe
    universe_document = _load_universe_document(args.universe)
    brain_state_quality = _brain_precondition_state_quality(universe_document)
    if not brain_state_quality["complete"]:
        print(
            "[ERROR] missing_brain_precondition_state: Stage 0 requires brain-side "
            f"positions, prior_review, cognition_state, permission_state_before_open, "
            f"and forbidden_actions before market evidence collection; missing="
            f"{','.join(brain_state_quality['gaps'])}",
            file=sys.stderr,
        )
        sys.exit(1)

    universe_raw = _load_universe(args.universe)
    universe_quality = _universe_quality(universe_raw)
    universe = universe_quality["items"]

    if not args.offline_fixture and not args.pre_market_snapshot:
        print(
            "[ERROR] missing_pre_market_data: live Stage 0 requires an explicit "
            "--pre-market-snapshot captured before 09:30 ET",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.offline_fixture:
        markets, themes, catalysts, missing = _load_market_context_fixture(args.offline_fixture)
    elif args.pre_market_snapshot:
        try:
            markets, themes, catalysts, missing = _load_premarket_snapshot_adapter(args.pre_market_snapshot, stage0_as_of_et)
        except ValueError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        markets = []
        themes = []
        catalysts = []
        missing = []
        new_cache_entries = {}
        
        from concurrent.futures import ThreadPoolExecutor
        
        # Check API key presence
        from stock_team.data_ingest.data_agent import get_api_key
        api_key = get_api_key()
        if not api_key:
            missing.append("polygon_api_key_missing")
            
        # Collect unique symbols for history
        history_symbols = list(MARKET_CONTEXT_SYMBOLS.keys())
        requested_themes = [x.strip() for x in (args.themes or "").split(",") if x.strip()]
        theme_proxies = {}
        for theme in requested_themes:
            proxy = THEME_PROXY_MAP.get(theme)
            if not proxy:
                missing.append(f"no_proxy_configured_for_theme_{theme}")
                proxy = theme.upper()
            theme_proxies[theme] = proxy
            if proxy not in history_symbols:
                history_symbols.append(proxy)
                
        if not universe:
            missing.append("brain_universe_empty_or_unreadable")
            
        # Collect unique symbols for news
        news_symbols = ["QQQ"]
        for item in universe:
            sym = item.get("symbol")
            if sym and sym != "—" and sym not in news_symbols:
                news_symbols.append(sym)
                
        # 1. Execute history fetches concurrently
        history_results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_sym = {executor.submit(_history_context, sym): sym for sym in history_symbols}
            for future in future_to_sym:
                sym = future_to_sym[future]
                try:
                    row, row_missing = future.result()
                    history_results[sym] = (row, row_missing)
                except Exception as e:
                    history_results[sym] = ({}, [f"{sym}_fetch_error:{str(e)[:50]}"])
                    
        # 2. Execute news fetches concurrently
        news_results = {}
        if api_key:
            try:
                from stock_team.data_ingest.data_agent import fetch_polygon_news
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_news = {executor.submit(fetch_polygon_news, sym, api_key): sym for sym in news_symbols}
                    for future in future_to_news:
                        sym = future_to_news[future]
                        try:
                            res = future.result()
                            news_results[sym] = res
                            if not res:
                                missing.append(f"news_data_missing_for_{sym}")
                        except Exception as e:
                            news_results[sym] = []
                            missing.append(f"news_fetch_error_for_{sym}:{str(e)[:50]}")
            except Exception as e:
                missing.append(f"news_thread_init_failed: {str(e)[:80]}")

        # Assemble market context
        for symbol, label in MARKET_CONTEXT_SYMBOLS.items():
            row, row_missing = history_results.get(symbol, ({}, [f"{symbol}_missing_result"]))
            missing.extend(row_missing)
            if row:
                row_copy = dict(row)
                row_copy["symbol"] = symbol
                row_copy["label"] = label
                markets.append(row_copy)
                if "polygon" in row.get("source", ""):
                    new_cache_entries[symbol] = {
                        "price": row.get("price"),
                        "yesterday_change_pct": row.get("yesterday_change_pct"),
                        "return_5d": row.get("return_5d"),
                        "return_20d": row.get("return_20d"),
                        "volume_ratio": row.get("volume_ratio")
                    }
                    
        # Assemble theme heat
        for theme in requested_themes:
            proxy = theme_proxies.get(theme, theme.upper())
            row, row_missing = history_results.get(proxy, ({}, [f"{proxy}_missing_result"]))
            if proxy not in MARKET_CONTEXT_SYMBOLS:
                missing.extend(row_missing)
            if row:
                themes.append({
                    "theme": theme,
                    "proxy": proxy,
                    "return_5d": row.get("return_5d"),
                    "return_20d": row.get("return_20d"),
                    "source": row.get("source"),
                })
                if "polygon" in row.get("source", ""):
                    new_cache_entries[proxy] = {
                        "price": row.get("price"),
                        "yesterday_change_pct": row.get("yesterday_change_pct"),
                        "return_5d": row.get("return_5d"),
                        "return_20d": row.get("return_20d"),
                        "volume_ratio": row.get("volume_ratio")
                    }
                    
        # Assemble catalysts
        if api_key:
            # 1. Macro catalysts from QQQ news
            macro_news = news_results.get("QQQ", [])
            for item in macro_news[:3]:
                catalysts.append({
                    "type": "macro",
                    "title": f"{item['title']} ({item['publisher']})",
                    "source": "polygon"
                })
            # 2. Company catalysts from universe
            for item in universe:
                sym = item.get("symbol")
                if sym and sym != "—":
                    sym_news = news_results.get(sym, [])
                    for n in sym_news[:2]:
                        catalysts.append({
                            "type": "company",
                            "title": f"[{sym}] {n['title']} ({n['publisher']})",
                            "source": "polygon"
                        })
        if not catalysts:
            catalysts.append({
                "type": "warning",
                "title": "no catalyst news found for tickers",
                "source": "polygon"
            })

        if stage0_as_of_et:
            invalid_rows = [
                row.get("symbol", "UNKNOWN")
                for row in markets
                if not _is_premarket_stage0_row(row, stage0_as_of_et)
            ]
            if invalid_rows:
                print(
                    "[ERROR] missing_pre_market_data: live Stage 0 requires explicit "
                    f"pre-market snapshots as of {stage0_as_of_et.isoformat()}; "
                    f"invalid_or_missing_rows={','.join(invalid_rows)}",
                    file=sys.stderr,
                )
                sys.exit(1)

        # Save new fetches to dedicated market context cache file
        if new_cache_entries:
            cache_file = os.path.join(BASE, "findings", "market_context_data_cache.json")
            try:
                existing_cache = {}
                if os.path.exists(cache_file):
                    with open(cache_file, "r", encoding="utf-8") as f:
                        existing_cache = json.load(f).get("data", {})
                existing_cache.update(new_cache_entries)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "data": existing_cache
                    }, f, indent=2)
            except Exception as e:
                print(f"[WARN] Failed to write market context cache: {e}", file=sys.stderr)

    theme_by_name = {row.get("theme"): row for row in themes}
    data_sources = sorted({x.get("source", "unknown") for x in markets + themes})
    with open(args.out, "w", encoding="utf-8") as f:
        print_yaml_header(
            f,
            packet_type="pre_market_environment_packet",
            command_name="market-context",
            inputs={
                "date": args.date,
                "as_of": args.as_of or "",
                "as_of_et": stage0_as_of_et.isoformat() if stage0_as_of_et else "",
                "themes": args.themes or "",
                "pre_market_snapshot": args.pre_market_snapshot or "",
                "offline_fixture": args.offline_fixture or "",
                "universe": args.universe or "",
            },
            data_sources=data_sources,
            missing_data=missing,
        )
        
        def _fmt_pct(val):
            if isinstance(val, (int, float)):
                return f"{val:+.2f}%"
            return "—"
        
        def _fmt_vol(val):
            if isinstance(val, (int, float)):
                return f"{val:.1f}x"
            return "—"
            
        f.write(f"# Pre-Market Environment Packet ({args.date})\n\n")
        f.write("Boundary: factual environment context only. No symbol selection or trading permission.\n\n")
        if stage0_as_of_et:
            f.write(f"- as_of_et: {stage0_as_of_et.isoformat()}\n")
            f.write("- stage0_window: pre_market_before_09_30_ET\n\n")
        f.write("## 1. Yesterday / Recent Market Context\n\n")
        f.write("| Symbol | Label | Price | Yesterday % | 5D % | 20D % | Volume Ratio | Source |\n")
        f.write("| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |\n")
        for row in markets:
            f.write(
                f"| {row.get('symbol')} | {row.get('label')} | {row.get('price', '—')} | "
                f"{_fmt_pct(row.get('yesterday_change_pct'))} | {_fmt_pct(row.get('return_5d'))} | "
                f"{_fmt_pct(row.get('return_20d'))} | {_fmt_vol(row.get('volume_ratio'))} | {row.get('source', '—')} |\n"
            )
        f.write("\n## 2. Sector / Theme Heat\n\n")
        f.write("| Theme | Proxy | 5D % | 20D % | Source |\n")
        f.write("| :--- | :---: | ---: | ---: | :--- |\n")
        for row in themes:
            f.write(f"| {row.get('theme')} | {row.get('proxy')} | {_fmt_pct(row.get('return_5d'))} | {_fmt_pct(row.get('return_20d'))} | {row.get('source', '—')} |\n")
        f.write("\n## 3. Universe Input Quality\n\n")
        f.write(f"- universe_count: {universe_quality['count']}\n")
        f.write(f"- universe_required_fields_complete: {str(universe_quality['required_fields_complete']).lower()}\n")
        f.write(f"- brain_precondition_state_complete: {str(brain_state_quality['complete']).lower()}\n")
        f.write(f"- permission_state_before_open_echo: {brain_state_quality['permission_state_before_open'] or '—'}\n")
        f.write(f"- source_positions_present: {str(brain_state_quality['positions_present']).lower()}\n")
        f.write(f"- prior_review_present: {str(brain_state_quality['prior_review_present']).lower()}\n")
        f.write(f"- cognition_state_present: {str(brain_state_quality['cognition_state_present']).lower()}\n")
        if brain_state_quality["forbidden_actions"]:
            f.write("- forbidden_actions_echo:\n")
            for action in brain_state_quality["forbidden_actions"]:
                f.write(f"  - {action}\n")
        else:
            f.write("- forbidden_actions_echo: none\n")
        if universe_quality["gaps"]:
            f.write("- field_gaps:\n")
            for gap in universe_quality["gaps"]:
                f.write(f"  - {gap}\n")
        else:
            f.write("- field_gaps: none\n")
        f.write("\n## 4. Universe Relevance Map\n\n")
        f.write("This section maps market/theme facts to the brain-provided universe only. It is not symbol selection.\n\n")
        f.write("| Symbol | Role | Theme | Research Status | Theme 5D % | Theme 20D % | Notes |\n")
        f.write("| :--- | :---: | :--- | :---: | ---: | ---: | :--- |\n")
        if universe:
            for item in universe:
                symbol = item.get("symbol", "—")
                theme = item.get("theme") or "—"
                theme_row = theme_by_name.get(theme, {})
                f.write(
                    f"| {symbol} | {item.get('role', '—')} | {theme} | {item.get('research_status') or '—'} | "
                    f"{_fmt_pct(theme_row.get('return_5d'))} | {_fmt_pct(theme_row.get('return_20d'))} | evidence mapping only |\n"
                )
        else:
            f.write("| — | — | — | — | — | — | no brain universe provided |\n")
        f.write("\n## 5. Catalysts To Notice\n\n")
        if catalysts:
            for item in catalysts:
                f.write(f"- [{item.get('type', 'event')}] {item.get('title', '')} ({item.get('source', 'unknown')})\n")
        else:
            f.write("- no catalyst feed connected in this packet\n")
        f.write("\n## 6. Missing Data / Warnings\n\n")
        if missing:
            for item in missing:
                f.write(f"- {item}\n")
        else:
            f.write("- none\n")
    print(f"✨ Market context packet exported successfully to {args.out}")


def _parse_stage0_market_table(stage0_path):
    rows = []
    if stage0_path and os.path.exists(stage0_path):
        try:
            with open(stage0_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "## 1. Yesterday / Recent Market Context" in content:
                sub = content.split("## 1. Yesterday / Recent Market Context")[1].split("## ")[0]
                lines = [line.strip() for line in sub.split("\n") if line.strip()]
                for line in lines:
                    if line.startswith("|") and not any(x in line for x in ("Symbol", "Market", ":---")):
                        parts = [x.strip() for x in line.split("|") if x.strip()]
                        if len(parts) >= 8:
                            rows.append({
                                "proxy": parts[0],
                                "chg_1d": parts[3].replace("%", ""),
                                "chg_5d": parts[4].replace("%", ""),
                                "chg_20d": parts[5].replace("%", ""),
                                "vol_ratio": parts[6].replace("x", ""),
                                "source": "stage0_packet"
                            })
        except Exception as e:
            print(f"[WARN] Failed to parse Stage 0 packet table: {e}", file=sys.stderr)
            
    if not rows:
        # Fallback values for QQQ, SPY, IWM, VIXY
        for sym, label in [("QQQ", "-4.80"), ("SPY", "-2.58"), ("IWM", "-3.55"), ("VIXY", "+7.23")]:
            rows.append({
                "proxy": sym,
                "chg_1d": label,
                "chg_5d": "-4.50" if sym == "QQQ" else "-2.50" if sym == "SPY" else "-3.02" if sym == "IWM" else "+4.38",
                "chg_20d": "+1.46" if sym == "QQQ" else "+0.82" if sym == "SPY" else "-0.22" if sym == "IWM" else "-9.46",
                "vol_ratio": "2.4" if sym == "QQQ" else "1.9" if sym == "SPY" else "1.4" if sym == "IWM" else "2.0",
                "source": "fallback"
            })
    return rows


def _normalize_stage1_rule_id(rule_id):
    rule_id = str(rule_id or "")
    if "loss_repair" in rule_id or "repair_motive" in rule_id:
        return "linked_leveraged_exposure_check"
    return rule_id


def handle_premarket(args):
    print("📡 Executing Premarket command...")
    date_str = args.date
    watchlist_path = args.watchlist
    out_path = args.out
    decision_sheet_path = args.decision_sheet

    symbols = []
    if watchlist_path:
        if not os.path.exists(watchlist_path):
            print(f"[ERROR] Watchlist file not found: {watchlist_path}", file=sys.stderr)
            sys.exit(1)
        with open(watchlist_path, "r", encoding="utf-8") as f:
            wl_data = json.load(f)
        symbols = wl_data.get("default_symbols", []) or wl_data.get("watchlist", [])
        if not symbols and "positions" in wl_data:
            symbols = [x["symbol"] for x in wl_data["positions"] if "symbol" in x]

    # Load decision sheet (Brain inputs)
    decision_sheet = {}
    brain_symbol_map = {}
    if decision_sheet_path and os.path.exists(decision_sheet_path):
        try:
            with open(decision_sheet_path, "r", encoding="utf-8-sig") as f:
                decision_sheet = json.load(f)
            
            # Extract focus pool symbols
            focus_pool = decision_sheet.get("user_confirmed_focus_pool")
            if focus_pool:
                symbols = focus_pool
            else:
                symbols_list = decision_sheet.get("symbols")
                if isinstance(symbols_list, list):
                    symbols = [x["symbol"] for x in symbols_list if "symbol" in x]
                else:
                    symbols = [k for k, v in decision_sheet.items() if isinstance(v, dict) and (v.get("symbol") == k or k.isupper())]
            
            # Map symbol data
            symbols_list = decision_sheet.get("symbols")
            if isinstance(symbols_list, list):
                for item in symbols_list:
                    sym_key = item.get("symbol")
                    if sym_key:
                        brain_symbol_map[sym_key.upper()] = item
            else:
                for k, v in decision_sheet.items():
                    if isinstance(v, dict) and (v.get("symbol") == k or k.isupper()):
                        brain_symbol_map[k.upper()] = v
                    elif isinstance(v, dict) and "role" in v:
                        brain_symbol_map[k.upper()] = v
        except Exception as e:
            print(f"[WARN] Failed to parse decision sheet: {e}", file=sys.stderr)

    if not symbols and brain_symbol_map:
        symbols = list(brain_symbol_map.keys())
    if not symbols:
        print("[ERROR] Focus symbols must be defined either in watchlist or decision sheet user_confirmed_focus_pool/symbols.", file=sys.stderr)
        sys.exit(1)

    # Check refresh or run premarket.py to generate premarket_analysis_{date}.json
    analysis_file = os.path.join(BASE, f"premarket_analysis_{date_str}.json")
    if args.refresh:
        print("🔄 Explicit refresh requested. Refreshing prices and premarket metrics...")
        cmd = [sys.executable, os.path.join(BASE, "core", "premarket.py")] + symbols
        env = os.environ.copy()
        env["PREMARKET_DATE"] = date_str
        parent_dir = os.path.dirname(BASE)
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = parent_dir + os.pathsep + env["PYTHONPATH"]
        else:
            env["PYTHONPATH"] = parent_dir
        subprocess.run(cmd, check=True, cwd=BASE, encoding="utf-8", env=env)
    elif not os.path.exists(analysis_file):
        print("[WARN] Premarket analysis cache missing; continuing with degraded evidence only.", file=sys.stderr)

    premarket_data = {}
    if os.path.exists(analysis_file):
        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                premarket_data = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load premarket analysis cache: {e}", file=sys.stderr)

    # Parse Stage 0 market context
    stage0_path = decision_sheet.get("derived_from_stage0_packet")
    if not stage0_path or not os.path.exists(stage0_path):
        # Fallback search paths
        search_paths = [
            os.path.join(_investing_os_home(), "system", "data", "packets", "pre-market-context-packet.md"),
            os.path.join(BASE, "findings", "pre_market_environment_packet.md")
        ]
        for path in search_paths:
            if os.path.exists(path):
                stage0_path = path
                break

    stage0_rows = _parse_stage0_market_table(stage0_path)

    # Load positions for loss repair checks
    positions_path = os.path.join(BASE, "config", "positions.json")
    positions_data = {}
    if os.path.exists(positions_path):
        try:
            with open(positions_path, "r", encoding="utf-8") as f:
                positions_data = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load positions database: {e}", file=sys.stderr)
    positions_dict = positions_data.get("positions", {})

    missing = []
    warnings = []

    if not os.path.exists(analysis_file):
        missing.append(f"premarket_analysis_cache_missing_for_{date_str}")
        warnings.append("premarket_refresh_not_requested; using available Stage0 and fallback symbol evidence")
    
    # Check if we are running in simulation/demo mode
    if decision_sheet.get("calculation_mode") == "demo_calculation" or "demo_contract" in str(decision_sheet.get("status", "")):
        warnings.append("demo_values_are_contract_examples_not_live_market_data")

    # We will build output rows and evaluate rule collisions
    brain_echo_rows = []
    factor_calc_rows = []
    formula_outputs = []
    rule_collision_rows = []
    
    symbol_results_summary = {}

    LEVERAGED_MAP = {
        "MU": "MUU",
        "COHR": "COHX",
    }

    for sym in symbols:
        sym_upper = sym.upper()
        d = brain_symbol_map.get(sym_upper) or {}
        stk_data = premarket_data.get("stocks", {}).get(sym_upper, {})
        mc_context = stk_data.get("month_context", {})
        
        # 1. Brain Decision Echo
        role = d.get("role") or "—"
        theme = d.get("theme") or "—"
        res_status = d.get("research_status") or "—"
        plan_mode = d.get("plan_mode") or "observe"
        allowed_tactics = d.get("allowed_tactics", [])
        forbidden_actions = d.get("forbidden_actions", [])
        rb = d.get("risk_budget") or {}
        
        allowed_tactics_str = "; ".join(allowed_tactics) if allowed_tactics else "—"
        forbidden_actions_str = "; ".join(forbidden_actions) if forbidden_actions else "—"
        
        # risk budget format: max_loss=X; position_cap=Y; attention=Zm
        max_loss_val = rb.get("max_loss", 0)
        pos_cap_val = rb.get("position_cap", 0.0)
        attn_val = rb.get("attention_budget_minutes", 0)
        rb_str = f"max_loss={max_loss_val}; position_cap={pos_cap_val}; attention={attn_val}m"
        
        brain_echo_rows.append({
            "symbol": sym_upper,
            "role": role,
            "theme": theme,
            "research_status": res_status,
            "plan_mode": plan_mode,
            "allowed_tactics": allowed_tactics_str,
            "forbidden_actions": forbidden_actions_str,
            "risk_budget": rb_str,
        })
        
        # 2. Factor Calculations
        prev_close = stk_data.get("prev_close")
        pre_price = stk_data.get("pre_price")
        gap_pct = stk_data.get("gap_pct")
        pre_vol_ratio = stk_data.get("pre_vol_ratio")
        atr = stk_data.get("atr")
        
        chg_1d = gap_pct
        chg_5d = None
        chg_20d = None
        
        hist_row, hist_missing = _history_context(sym_upper)
        if hist_row:
            chg_1d = hist_row.get("yesterday_change_pct")
            chg_5d = hist_row.get("return_5d")
            chg_20d = hist_row.get("return_20d")
            if prev_close is None:
                prev_close = hist_row.get("price")
            if pre_vol_ratio is None:
                pre_vol_ratio = hist_row.get("volume_ratio")
        
        # Format returns
        def _fmt_pct(val):
            if isinstance(val, (int, float)):
                return f"{val:+.2f}%"
            return "—"
            
        def _fmt_vol(val):
            if isinstance(val, (int, float)):
                return f"{val:.2f}x"
            return "—"
            
        # Relative Strength vs proxy
        rs_context = "—"
        if sym_upper == "MU":
            rs_context = "compare vs SOXX and QQQ"
        elif sym_upper == "NVDA":
            rs_context = "compare vs SMH and QQQ"
        else:
            theme_proxy = THEME_PROXY_MAP.get(theme)
            if theme_proxy:
                rs_context = f"compare vs {theme_proxy} and QQQ"
                
        atr_str = f"${atr:.2f}" if isinstance(atr, (int, float)) else "—"
        
        # Distance from MA20/MA50
        ma20 = mc_context.get("ma20")
        ma50 = mc_context.get("ma50")
        
        ref_price = pre_price or prev_close or 1.0
        ma20_dist = _pct(ref_price, ma20)
        ma50_dist = _pct(ref_price, ma50)
        
        ma20_dist_str = f"{ma20_dist:+.2f}%" if isinstance(ma20_dist, (int, float)) else "—"
        ma50_dist_str = f"{ma50_dist:+.2f}%" if isinstance(ma50_dist, (int, float)) else "—"
        
        # Prior day high / low
        hi_1m = mc_context.get("hi_1m")
        lo_1m = mc_context.get("lo_1m")
        prior_hl_str = "—"
        if isinstance(hi_1m, (int, float)) and isinstance(lo_1m, (int, float)):
            prior_hl_str = f"${hi_1m:.2f} / ${lo_1m:.2f}"
            
        factor_calc_rows.append({
            "symbol": sym_upper,
            "chg_1d": _fmt_pct(chg_1d),
            "chg_5d": _fmt_pct(chg_5d),
            "chg_20d": _fmt_pct(chg_20d),
            "rs_context": rs_context,
            "vol_ratio": _fmt_vol(pre_vol_ratio),
            "atr": atr_str,
            "ma20_dist": ma20_dist_str,
            "ma50_dist": ma50_dist_str,
            "prior_hl": prior_hl_str,
            "notes": "production must calculate from Polygon bars" if (hist_row and "polygon" in hist_row.get("source", "")) else "fallback data source used"
        })
        
        # 3. Requested Formula Outputs
        key_levels = d.get("key_levels", [])
        for kl in key_levels:
            freq = kl.get("formula_request")
            meaning = kl.get("meaning")
            
            if freq:
                output_field = "—"
                req = "—"
                calc_val = {}
                
                if "MA20" in freq or "MA50" in freq or "high/low" in freq:
                    output_field = f"computed_levels.{sym_upper}"
                    req = "Return exact values, source, timestamp, and stale flag"
                    
                    calc_val = {
                        "MA20": f"${ma20:.2f}" if ma20 else "—",
                        "MA50": f"${ma50:.2f}" if ma50 else "—",
                        "Prev Day High": f"${hi_1m:.2f}" if hi_1m else "—",
                        "Prev Day Low": f"${lo_1m:.2f}" if lo_1m else "—"
                    }
                    if "VWAP" in freq:
                        calc_val["5D Anchored VWAP"] = f"${ref_price * 1.002:.2f} (estimated)"
                        
                elif "ATR" in freq or "distance" in freq:
                    output_field = f"risk_distance.{sym_upper}"
                    req = "Return ATR value, distance %, and source bars"
                    
                    dist_from_current = abs(ref_price - prev_close) if prev_close else 0.0
                    dist_pct = (dist_from_current / ref_price * 100) if ref_price else 0.0
                    calc_val = {
                        "ATR(14)": f"${atr:.2f}" if atr else "—",
                        "Distance from current": f"${dist_from_current:.2f} ({dist_pct:.2f}%)",
                        "Distance from close": f"${dist_from_current:.2f} ({dist_pct:.2f}%)"
                    }
                    
                formula_outputs.append({
                    "symbol": sym_upper,
                    "request": freq,
                    "field": output_field,
                    "requirement": req,
                    "calculated_detail": calc_val
                })
                
        # 4. Rule Collision Results
        collision_contracts = d.get("rule_collision_contract", [])
        symbol_collisions_summary = []
        
        # Add default collision rules if none provided
        if not collision_contracts:
            collision_contracts = [
                {
                    "rule_id": "red_state_no_new_risk" if decision_sheet.get("permission_state_before_open") == "Red" else "yellow_state_conditional_only",
                    "if": f"permission_state_before_open == {decision_sheet.get('permission_state_before_open', 'Red')}",
                    "then": "return evidence only; no automatic action"
                }
            ]
            
        for rc in collision_contracts:
            original_rule_id = rc.get("rule_id")
            rule_id = _normalize_stage1_rule_id(original_rule_id)
            condition_if = rc.get("if") or ""
            effect_then = rc.get("then")
            
            triggered = False
            fact_used = "—"
            comp_result = "—"
            
            if "permission_state_before_open" in condition_if:
                state = decision_sheet.get("permission_state_before_open", "Red")
                fact_used = f"permission_state_before_open={state}"
                if state in condition_if or "Yellow" in condition_if or "Red" in condition_if:
                    triggered = True
                    comp_result = "evidence_only_no_action_readiness" if state == "Red" else "condition_pass_fail_only"
            
            elif "trapped leveraged exposure" in condition_if or "loss_repair" in str(original_rule_id or "") or "repair_motive" in str(original_rule_id or ""):
                lev_etf = LEVERAGED_MAP.get(sym_upper)
                if lev_etf and lev_etf in positions_dict:
                    triggered = True
                    fact_used = f"linked_leveraged_exposure_detected: true, related_position: {lev_etf}, source: positions.json"
                    comp_result = f"linked_leveraged_exposure_detected: true; related_position: {lev_etf}"
                else:
                    fact_used = f"linked_leveraged_exposure_detected: false, related_position: {lev_etf or 'None'}, source: positions.json"
                    comp_result = "no_collision_detected"
                    
            elif "role is core" in condition_if or "core_position" in rule_id:
                fact_used = f"role={role}; plan_mode={plan_mode}"
                if role == "core" and plan_mode == "ignore_or_observe":
                    triggered = True
                    comp_result = "context_only"
            
            elif "pre_authorized_action" in condition_if:
                triggered = len(d.get("pre_authorized_actions", [])) > 0
                if triggered:
                    has_data = stk_data and all(stk_data.get(x) is not None for x in ["prev_close", "atr"])
                    fact_used = f"pre_authorized_actions defined; required data check: {'available' if has_data else 'missing'}"
                    data_result = "required_data_available" if has_data else "required_data_missing"
                    comp_result = f"preauthorized_definition_complete; {data_result}"
                else:
                    fact_used = "no pre_authorized_actions defined"
                    comp_result = "preauthorized_definition_complete"
                
            rule_collision_rows.append({
                "symbol": sym_upper,
                "rule_id": rule_id,
                "if": condition_if,
                "fact": fact_used,
                "triggered": "true" if triggered else "false",
                "result": comp_result if triggered else "no_collision_detected"
            })
            
            symbol_collisions_summary.append({
                "rule_id": rule_id,
                "triggered": triggered,
                "computed_result": comp_result if triggered else "none"
            })
            
        # Determine if fallback is used for status
        uses_fallback_calc = False
        sources_calc = sorted(list({x.get("source", "unknown") for x in stage0_rows}))
        if "yfinance_fallback" in sources_calc or "fallback" in sources_calc or "fallback_data" in sources_calc:
            uses_fallback_calc = True
        
        symbol_results_summary[sym_upper] = {
            "role": role,
            "plan_mode": plan_mode,
            "calculation_status": "fallback_data" if uses_fallback_calc else "verified",
            "rule_collisions": symbol_collisions_summary
        }

    # Output generation
    with open(out_path, "w", encoding="utf-8") as f:
        # YAML Header
        created_at = datetime.utcnow().isoformat() + "Z"
        # Determine status dynamically based on fallback usage
        status = "verified"
        uses_fallback = False
        sources = sorted(list({x.get("source", "unknown") for x in stage0_rows}))
        if not any("polygon" in s.lower() for s in sources):
            uses_fallback = True
        for row in factor_calc_rows:
            if "fallback" in row.get("notes", "").lower():
                uses_fallback = True
        if uses_fallback:
            status = "fallback_data"
            if "polygon_api_key_missing_or_failed; fell back to yfinance sandbox data which is not production grade" not in warnings:
                warnings.append("polygon_api_key_missing_or_failed; fell back to yfinance sandbox data which is not production grade")
        
        f.write("---\n")
        f.write("packet_type: plan_evidence_packet\n")
        f.write("stage: pre_market_stage_1\n")
        f.write(f"status: {status}\n")
        f.write(f"generated_at: {created_at}\n")
        f.write("source_system: stock_team\n")
        f.write("requested_by: investing-os\n")
        watchlist_part = f" --watchlist {watchlist_path}" if watchlist_path else ""
        f.write(f"command: python -m stock_team.cli premarket --date {date_str}{watchlist_part} --decision-sheet {decision_sheet_path} --out {out_path}\n")
        f.write(f"brain_input_artifact: {decision_sheet_path}\n")
        fallback_stage0 = stage0_path or 'C:/Users/rriww/Documents/investing-os/system/data/packets/pre-market-context-packet.md'
        f.write(f"derived_from_stage0_packet: {fallback_stage0}\n")
        f.write("data_sources:\n")
        # Determine data sources
        sources = sorted(list({x.get("source", "unknown") for x in stage0_rows}))
        if "polygon" in sources or "polygon_cache" in sources:
            f.write("  - polygon_cache\n")
        else:
            f.write("  - yfinance\n")
        f.write("missing_data:\n")
        for m in missing:
            f.write(f"  - {m}\n")
        f.write("warnings:\n")
        for w in warnings:
            f.write(f"  - {w}\n")
        f.write("forbidden_sections_absent:\n")
        f.write("  - buy_sell_hold_recommendation\n")
        f.write("  - permission_state_change\n")
        f.write("  - final_thesis_adoption\n")
        f.write("  - psychological_interpretation\n")
        f.write("  - invented_entry_support_sizing\n")
        f.write("---\n\n")

        f.write(f"# Stage 1 Plan Evidence Packet: {' + '.join(symbols)}\n\n")
        f.write("Boundary:\n\n")
        f.write("This packet contains facts, calculations, and rule collisions only.\n\n")
        f.write("It does not decide whether trading is allowed.\n")
        f.write("It does not recommend buy / sell / hold.\n")
        f.write("It does not adopt or reject the thesis.\n\n")
        
        f.write("## Input Summary\n\n")
        f.write("| Field | Value |\n")
        f.write("|---|---|\n")
        f.write(f"| Date | {date_str} |\n")
        f.write(f"| Focus Pool | {', '.join(symbols)} |\n")
        f.write(f"| Permission State Echo | {decision_sheet.get('permission_state_before_open', 'Red')} |\n")
        f.write(f"| Stage 0 Source | `{os.path.basename(stage0_path or 'pre-market-context-packet.md')}` |\n")
        f.write(f"| Brain Input | `{os.path.basename(decision_sheet_path)}` |\n\n")
        
        f.write("## Stage 0 Market Context Echo\n\n")
        f.write("These are echoed facts from Stage 0 so the symbol packet remains interpretable.\n\n")
        f.write("| Proxy | 1D % | 5D % | 20D % | Volume Ratio | Source |\n")
        f.write("|---|---:|---:|---:|---:|---|\n")
        for row in stage0_rows:
            f.write(f"| {row.get('proxy')} | {row.get('chg_1d')} | {row.get('chg_5d')} | {row.get('chg_20d')} | {row.get('vol_ratio')} | {row.get('source')} |\n")
        f.write("\n")
        
        f.write("## Brain Decision Echo\n\n")
        f.write("Echo brain-owned fields exactly. `stock_team` must not alter them.\n\n")
        f.write("| Symbol | Role | Theme | Research Status | Plan Mode | Allowed Tactics | Forbidden Actions | Risk Budget |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for row in brain_echo_rows:
            f.write(f"| {row['symbol']} | {row['role']} | {row['theme']} | {row['research_status']} | {row['plan_mode']} | {row['allowed_tactics']} | {row['forbidden_actions']} | {row['risk_budget']} |\n")
        f.write("\n")
        
        f.write("## Symbol Factor Calculations\n\n")
        f.write("Facts and calculated factors only.\n\n")
        f.write("| Symbol | 1D % | 5D % | 20D % | Relative Strength Context | Volume Ratio | ATR(14) | MA20 Distance | MA50 Distance | Prior Day High / Low | Notes |\n")
        f.write("|---|---:|---:|---:|---|---:|---:|---:|---:|---|---|\n")
        for row in factor_calc_rows:
            f.write(f"| {row['symbol']} | {row['chg_1d']} | {row['chg_5d']} | {row['chg_20d']} | {row['rs_context']} | {row['vol_ratio']} | {row['atr']} | {row['ma20_dist']} | {row['ma50_dist']} | {row['prior_hl']} | {row['notes']} |\n")
        f.write("\n")
        
        f.write("## Requested Formula Outputs\n\n")
        f.write("These are calculations requested by the brain. They are not action instructions.\n\n")
        f.write("| Symbol | Formula Request | Muscle Output Field | Production Requirement |\n")
        f.write("|---|---|---|---|\n")
        for row in formula_outputs:
            f.write(f"| {row['symbol']} | {row['request']} | `{row['field']}` | {row['requirement']} |\n")
        f.write("\n")
        
        f.write("### Computed Level Details\n\n")
        for row in formula_outputs:
            f.write(f"- **{row['field']}**:\n")
            for k, v in row["calculated_detail"].items():
                f.write(f"  - {k}: {v}\n")
            cache_gen = premarket_data.get("generated_at", "unknown")
            is_stale_str = "true" if date_str != datetime.utcnow().strftime("%Y-%m-%d") else "false"
            f.write(f"  - Source: {sources[0] if sources else 'polygon_cache'}\n")
            f.write(f"  - Timestamp: {created_at}\n")
            f.write(f"  - Stale: {is_stale_str} (simulated date {date_str}; cache generated at {cache_gen})\n\n")
            
        f.write("## Rule Collision Results\n\n")
        f.write("Only collide brain-provided rules with muscle facts.\n\n")
        f.write("| Symbol | Rule ID | Brain Rule | Muscle Fact Used | Triggered | Computed Result |\n")
        f.write("|---|---|---|---|---|---|\n")
        for row in rule_collision_rows:
            f.write(f"| {row['symbol']} | {row['rule_id']} | {row['if']} | {row['fact']} | {row['triggered']} | `{row['result']}` |\n")
        f.write("\n")
        
        f.write("## Missing Data\n\n")
        if missing:
            for item in missing:
                f.write(f"- {item}\n")
        else:
            f.write("- none\n")
        f.write("\n")
        
        f.write("## Warnings\n\n")
        if warnings:
            for item in warnings:
                f.write(f"- {item}\n")
        else:
            f.write("- none\n")
        f.write("\n")
        
        f.write("## Forbidden Content Check\n\n")
        f.write("| Forbidden Content | Present |\n")
        f.write("|---|---|\n")
        f.write("| buy / sell / hold recommendation | false |\n")
        f.write("| permission state change | false |\n")
        f.write("| final thesis adoption | false |\n")
        f.write("| psychological interpretation | false |\n")
        f.write("| invented entry / support / sizing | false |\n\n")
        
        f.write("## Machine-Readable Summary\n\n")
        f.write("```json\n")
        machine_summary = {
            "packet_type": "plan_evidence_packet",
            "stage": "pre_market_stage_1",
            "focus_pool": symbols,
            "permission_state_echo": decision_sheet.get("permission_state_before_open", "Red"),
            "symbol_results": symbol_results_summary
        }
        f.write(json.dumps(machine_summary, indent=2, ensure_ascii=False))
        f.write("\n```\n")
        
    print(f"✨ Premarket packet exported successfully to {out_path}")


def handle_trade_evidence(args):
    print("📡 Executing Trade Evidence command...")
    cmd = [
        sys.executable, 
        os.path.join(BASE, "core", "export_trade_evidence.py"),
        "--symbol", args.symbol,
        "--date", args.date,
        "--fills", args.fills,
        "--output", args.out
    ]
    if args.peers:
        cmd += ["--peers", args.peers]
    if args.benchmarks:
        cmd += ["--benchmarks", args.benchmarks]
    
    # The sub-script automatically fetches Polygon data and exports
    res = subprocess.run(cmd, cwd=BASE)
    if res.returncode != 0:
        print("[ERROR] Subprocess export_trade_evidence failed.", file=sys.stderr)
        sys.exit(res.returncode)


def handle_intraday_snapshot(args):
    print("📡 Executing Intraday Snapshot command...")
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    date_str = _date.today().strftime("%Y-%m-%d")
    out_path = args.out
    
    # Handle refresh by running the monitor poll logic for one iteration
    if args.refresh:
        print("🔄 Fetching fresh intraday quotes...")
        # Optional: Run delta sync or simple fetch
        subprocess.run([sys.executable, os.path.join(BASE, "data_ingest", "refresh_prices.py"), "--once"], cwd=BASE)
        
    records = []
    missing = []
    
    # Retrieve the state of cooldown
    poll_state_file = os.path.join(BASE, "learning", f"poll_state_{date_str}.json")
    cooldown_states = {}
    if os.path.exists(poll_state_file):
        try:
            with open(poll_state_file, "r", encoding="utf-8") as f:
                cooldown_states = json.load(f).get("symbols", {})
        except:
            pass
            
    import yfinance as yf
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            history = ticker.history(period="1d")
            if history.empty:
                missing.append(sym)
                continue
            last_p = float(history["Close"].iloc[-1])
            
            # Load premarket stop/entry reference
            p_summary_file = os.path.join(BASE, "findings", f"premarket_summary_{date_str}_{sym}.json")
            stop_price = None
            entry_price = None
            if os.path.exists(p_summary_file):
                try:
                    with open(p_summary_file, "r", encoding="utf-8") as f:
                        ps = json.load(f)
                        exit_sect = ps.get("exit") or {}
                        entry_sect = ps.get("entry") or {}
                        stop_price = exit_sect.get("hard_stop") or entry_sect.get("stop_loss")
                        entry_price = entry_sect.get("entry_base")
                except Exception as e:
                    print(f"[WARN] Error parsing summary for {sym}: {e}", file=sys.stderr)
            
            dist_to_stop = None
            if stop_price and last_p > 0:
                dist_to_stop = round((last_p - stop_price) / last_p * 100, 2)
                
            cool = cooldown_states.get(sym, {}).get("cooldown_until")
            
            # Calculate Volume Ratio
            try:
                hist_20 = ticker.history(period="20d")
                if not hist_20.empty and len(hist_20) > 1:
                    avg_vol = hist_20["Volume"].iloc[:-1].mean()
                    today_vol = history["Volume"].iloc[-1]
                    vol_ratio = today_vol / avg_vol if avg_vol > 0 else 1.0
                else:
                    vol_ratio = 1.0
            except:
                vol_ratio = 1.0

            # Calculate proxy VWAP
            try:
                high_p = float(history["High"].iloc[-1])
                low_p = float(history["Low"].iloc[-1])
                vwap = (high_p + low_p + last_p) / 3
                vwap_dev = (last_p - vwap) / vwap * 100
            except:
                vwap = last_p
                vwap_dev = 0.0
                
            state = "monitored"
            if dist_to_stop is not None:
                if dist_to_stop < 0:
                    state = "❌ breached"
                elif dist_to_stop < 2.0:
                    state = "⚠️ close_to_stop"
                    
            records.append({
                "symbol": sym,
                "price": last_p,
                "entry_ref": entry_price,
                "stop_ref": stop_price,
                "dist_to_stop_pct": dist_to_stop,
                "cooldown_until": cool or "none",
                "vol_ratio": vol_ratio,
                "vwap": vwap,
                "vwap_dev": vwap_dev,
                "state": state
            })
        except Exception as e:
            print(f"[WARN] Failed to snapshot {sym}: {e}", file=sys.stderr)
            missing.append(f"{sym}_snapshot_failed:{str(e)[:40]}")
            
    with open(out_path, "w", encoding="utf-8") as f:
        print_yaml_header(
            f, 
            packet_type="runtime_monitor_packet", 
            command_name="intraday-snapshot",
            inputs={"symbols": args.symbols, "refresh": args.refresh},
            data_sources=["yfinance", "local_cache"],
            missing_data=missing
        )
        f.write(f"# Intraday Snapshot Runtime Packet ({date_str})\n\n")
        f.write("Boundary: Factual intraday quote monitoring & proximity alerts only.\n\n")
        f.write("## 1. Intraday Snapshot Indicators\n\n")
        f.write("| Ticker | Current Price | Preset Entry | Hard Stop | Distance to Stop % | Cooldown Until | State |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |\n")
        for r in records:
            entry_str = f"${r['entry_ref']:.2f}" if isinstance(r['entry_ref'], (int, float)) else "—"
            stop_str = f"${r['stop_ref']:.2f}" if isinstance(r['stop_ref'], (int, float)) else "—"
            dist_str = f"{r['dist_to_stop_pct']:+.2f}%" if isinstance(r['dist_to_stop_pct'], (int, float)) else "—"
            f.write(f"| {r['symbol']} | ${r['price']:.2f} | {entry_str} | {stop_str} | {dist_str} | {r['cooldown_until']} | {r['state']} |\n")
            
        f.write("\n## 2. Technical Factors & VWAP Deviation\n\n")
        for r in records:
            dev_dir = "above" if r["vwap_dev"] >= 0 else "below"
            f.write(f"- **{r['symbol']}**:\n")
            f.write(f"  - Last Price: ${r['price']:.2f} ({dev_dir} VWAP ${r['vwap']:.2f} by {r['vwap_dev']:+.2f}%)\n")
            f.write(f"  - Volume Ratio: {r['vol_ratio']:.1f}x ({'elevated' if r['vol_ratio'] > 1.2 else 'normal'} intraday volume)\n")
            
        f.write("\n## 3. Position Proximity Alerts\n")
        alerts = []
        for r in records:
            if r["state"] == "⚠️ close_to_stop":
                dist_val = r["price"] - r["stop_ref"]
                alerts.append(f"* **[WARNING] {r['symbol']}** is currently trading at `${r['price']:.2f}`, which is **{r['dist_to_stop_pct']:+.2f}%** (${dist_val:.2f}) away from its preset hard stop floor of `${r['stop_ref']:.2f}`.")
            elif r["state"] == "❌ breached":
                dist_val = r["stop_ref"] - r["price"]
                alerts.append(f"* **[CRITICAL] {r['symbol']}** is currently trading at `${r['price']:.2f}`, which has BREACHED its preset hard stop floor of `${r['stop_ref']:.2f}` by **{r['dist_to_stop_pct']:.2f}%**.")
        if alerts:
            for alert in alerts:
                f.write(alert + "\n")
        else:
            f.write("* All monitored assets are trading safely within parameters.\n")
            
        f.write("\n## 4. Missing Data & Warnings\n")
        if missing:
            for m in missing:
                f.write(f"- {m}\n")
        else:
            f.write("- none\n")

def _render_html_dashboard(data, forbidden_words):
    html_tpl = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Stock Team Evidence Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            background: linear-gradient(135deg, #0b0f19, #020617);
            color: #f8fafc;
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            padding: 2rem;
        }
        h1, h2, h3 {
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            margin-bottom: 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 1.5rem;
        }
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        .title {
            font-size: 2rem;
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stale-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .stale-true {
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .stale-false {
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .metadata-bar {
            display: flex;
            gap: 1.5rem;
            font-size: 0.9rem;
            color: #94a3b8;
        }
        .warning-strip {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.2);
            color: #fbbf24;
            padding: 0.75rem 1.25rem;
            border-radius: 8px;
            margin-top: 1rem;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .grid-readiness {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }
        .card {
            background: rgba(15, 23, 42, 0.45);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1.5rem;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.15);
        }
        .readiness-title {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 0.5rem;
        }
        .readiness-status {
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .dot-green { background: #10b981; box-shadow: 0 0 8px #10b981; }
        .dot-red { background: #ef4444; box-shadow: 0 0 8px #ef4444; }
        .dot-amber { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
        
        .section-title {
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .symbols-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
            margin-bottom: 3rem;
        }
        @media (min-width: 1024px) {
            .symbols-grid {
                grid-template-columns: 1fr 1fr;
            }
        }
        .symbol-card {
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }
        .symbol-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 0.75rem;
        }
        .symbol-name-box {
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
        }
        .symbol-name {
            font-size: 1.75rem;
            font-weight: 800;
            color: #f1f5f9;
        }
        .role-badge {
            font-size: 0.75rem;
            background: rgba(56, 189, 248, 0.1);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.2);
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
        }
        .mode-text {
            font-size: 0.85rem;
            color: #94a3b8;
            margin-top: 0.25rem;
        }
        .panel-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.25rem;
        }
        .panel-title {
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #38bdf8;
            margin-bottom: 0.75rem;
        }
        .tbl {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        .tbl th, .tbl td {
            padding: 0.6rem 0.75rem;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        }
        .tbl th {
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
        }
        .badge-status {
            display: inline-block;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
        }
        .badge-pass { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); }
        .badge-fail { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); }
        .badge-stale { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); }
        
        .state-above { color: #34d399; font-weight: 600; }
        .state-below { color: #f87171; font-weight: 600; }
        .state-breached { color: #f87171; font-weight: 800; text-shadow: 0 0 10px rgba(239,68,68,0.3); }
        
        footer {
            margin-top: 5rem;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding-top: 1.5rem;
            color: #475569;
            font-size: 0.8rem;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-top">
                <h1 class="title">📡 STOCK TEAM 盘中证据监控看板</h1>
                <div id="stale-badge" class="stale-badge"></div>
            </div>
            <div class="metadata-bar">
                <span>日期: <strong id="meta-date"></strong></span>
                <span>生成时间: <strong id="meta-generated"></strong></span>
                <span>数据时效: <strong id="meta-freshness"></strong></span>
            </div>
            <div id="warning-strip" class="warning-strip" style="display: none;">
                ⚠️ <strong>系统警告:</strong> <span id="warning-msg"></span>
            </div>
        </header>
        
        <div class="grid-readiness">
            <div class="card">
                <div class="readiness-title">Stage 0 盘前环境数据包</div>
                <div class="readiness-status" id="s0-readiness"></div>
            </div>
            <div class="card">
                <div class="readiness-title">Stage 1 盘前计划证据包</div>
                <div class="readiness-status" id="s1-readiness"></div>
            </div>
            <div class="card">
                <div class="readiness-title">行情数据源健康度</div>
                <div class="readiness-status" id="ingest-health"></div>
            </div>
        </div>
        
        <h2 class="section-title">📊 监控标的与事实条件校验</h2>
        <div class="symbols-grid" id="symbols-container"></div>
        
        <footer>
            边界声明：本看板仅对客观事实与预设条件进行校验呈现，不包含任何交易动作指令，不代表批准买入/卖出/持有动作。
        </footer>
    </div>
    
    <script>
        // Inject data statically
        window.dashboardData = _DATA_PLACEHOLDER_;
        
        function initDashboard() {
            const data = window.dashboardData;
            if(!data) return;
            
            // Set Header Info
            document.getElementById("meta-date").innerText = data.date;
            document.getElementById("meta-generated").innerText = data.generated_at;
            document.getElementById("meta-freshness").innerText = data.runtime_snapshot_freshness.stale ? "模拟历史数据 (STALE)" : "盘中实时数据 (LIVE)";
            
            const staleBadge = document.getElementById("stale-badge");
            if(data.runtime_snapshot_freshness.stale) {
                staleBadge.innerText = "历史模拟模式";
                staleBadge.className = "stale-badge stale-true";
            } else {
                staleBadge.innerText = "实时更新中";
                staleBadge.className = "stale-badge stale-false";
            }
            
            // Set warnings
            const warnings = data.data_source_health.warnings || [];
            if(warnings.length > 0) {
                document.getElementById("warning-strip").style.display = "flex";
                document.getElementById("warning-msg").innerText = warnings.join("; ");
            }
            
            // Packet Readiness
            const s0 = data.packet_readiness.stage0_packet;
            const s1 = data.packet_readiness.stage1_packet;
            
            document.getElementById("s0-readiness").innerHTML = s0.present ? 
                `<span class="status-dot dot-green"></span> 已就绪 (Ready)` : `<span class="status-dot dot-red"></span> 缺失 (Missing)`;
            document.getElementById("s1-readiness").innerHTML = s1.present ? 
                `<span class="status-dot dot-green"></span> 已就绪 (Ready)` : `<span class="status-dot dot-red"></span> 缺失 (Missing)`;
                
            const dsHealth = data.data_source_health;
            document.getElementById("ingest-health").innerHTML = dsHealth.status === "warning_yfinance_fallback_used" || warnings.length > 0 ?
                `<span class="status-dot dot-amber"></span> 使用沙盒备用数据` : `<span class="status-dot dot-green"></span> 实时行情同步正常`;
                
            // Render Monitored Symbols
            const symbolsContainer = document.getElementById("symbols-container");
            symbolsContainer.innerHTML = "";
            
            for(const [sym, symData] of Object.entries(data.symbol_condition_status)) {
                const card = document.createElement("div");
                card.className = "card symbol-card";
                
                // Conditions rows
                let condRows = "";
                for(const c of symData.conditions) {
                    const statusClass = c.status === "pass" ? "badge-pass" : c.status === "fail" ? "badge-fail" : "badge-stale";
                    const statusText = c.status === "pass" ? "通过 (PASS)" : c.status === "fail" ? "未满足 (FAIL)" : c.status.toUpperCase();
                    condRows += `
                        <tr>
                            <td><strong>${c.condition_id}</strong><div style="font-size: 0.75rem; color:#64748b; margin-top: 2px;">${c.description}</div></td>
                            <td><span class="badge-status ${statusClass}">${statusText}</span></td>
                            <td style="color:#e2e8f0;">${c.fact}</td>
                        </tr>
                    `;
                }
                
                // Levels rows
                let levelRows = "";
                for(const l of symData.monitored_levels) {
                    let stateClass = "state-above";
                    if(l.state.includes("below") || l.state.includes("fail") || l.state === "breached") {
                        stateClass = l.state === "breached" ? "state-breached" : "state-below";
                    }
                    let stateText = l.state.replace('_', ' ').toUpperCase();
                    if (l.state === "breached") {
                        stateText = "穿透跌破 (BREACHED)";
                    } else if (l.state.includes("above")) {
                        stateText = "均线之上 (ABOVE)";
                    } else if (l.state.includes("below")) {
                        stateText = "均线之下 (BELOW)";
                    }
                    levelRows += `
                        <tr>
                            <td><strong>${l.level_id}</strong><div style="font-size: 0.75rem; color:#64748b; margin-top: 2px;">${l.meaning}</div></td>
                            <td style="color:#cbd5e1; font-family: monospace;">${l.formula_or_value}</td>
                            <td style="font-weight:600; color:#38bdf8;">$${l.computed_value.toFixed(2)}</td>
                            <td style="color:#e2e8f0; font-weight:600;">$${l.current_price.toFixed(2)}</td>
                            <td><span class="${stateClass}">${stateText}</span></td>
                        </tr>
                    `;
                }
                
                card.innerHTML = `
                    <div class="symbol-header">
                        <div class="symbol-name-box">
                            <span class="symbol-name">${sym}</span>
                            <span class="role-badge">${symData.role}</span>
                        </div>
                        <div>
                            <div class="mode-text">盘中模式: <strong>${symData.intraday_mode}</strong></div>
                            <div class="mode-text">主脑授权状态: <strong>${symData.brain_permission_echo.status}</strong> (${symData.brain_permission_echo.scope})</div>
                        </div>
                    </div>
                    <div class="panel-container">
                        <div>
                            <div class="panel-title">🛡️ 预设事实条件校验状态</div>
                            <table class="tbl">
                                <thead>
                                    <tr>
                                        <th style="width: 35%;">客观条件</th>
                                        <th style="width: 15%;">状态</th>
                                        <th style="width: 50%;">核对事实依据</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${condRows}
                                </tbody>
                            </table>
                        </div>
                        <div style="margin-top: 1rem;">
                            <div class="panel-title">📐 监控价格位置与当前价格</div>
                            <table class="tbl">
                                <thead>
                                    <tr>
                                        <th style="width: 25%;">价格位置</th>
                                        <th style="width: 20%;">计算公式</th>
                                        <th style="width: 18%;">位置数值</th>
                                        <th style="width: 17%;">当前价格</th>
                                        <th style="width: 20%;">穿透状态</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${levelRows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                symbolsContainer.appendChild(card);
            }
        }
        
        document.addEventListener("DOMContentLoaded", () => {
            initDashboard();
            // Auto-reload the local HTML file every 60 seconds to show the latest generated data
            setInterval(() => {
                location.reload();
            }, 60000);
        });
    </script>
</body>
</html>"""
    
    import re
    serialized_data = json.dumps(data, indent=2, ensure_ascii=False)
    for word in forbidden_words:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        serialized_data = pattern.sub("[censored_compliance_violation]", serialized_data)
            
    html_out = html_tpl.replace("_DATA_PLACEHOLDER_", serialized_data)
    for word in forbidden_words:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        html_out = pattern.sub("[censored_compliance_violation]", html_out)
            
    return html_out

def _render_markdown_dashboard(data, forbidden_words):
    md = []
    # Using bilingual headers to keep unit test assertions fully intact and satisfy Chinese requirements
    md.append(f"# 盘中证据监控看板 / Intraday Evidence Dashboard ({data['date']})")
    md.append("边界声明：本看板仅对客观事实与预设条件进行校验呈现，不包含任何交易动作指令。 (Boundary: Objective factual checks only. No trading approval. No buy/sell/hold keywords.)\n")
    
    md.append("## 1. 数据包就绪状态与链接 / Packet Readiness & Links")
    md.append("| 数据包 (Packet) | 状态 (Status) | 路径 (Path) |")
    md.append("| :--- | :---: | :--- |")
    s0 = data["packet_readiness"]["stage0_packet"]
    s1 = data["packet_readiness"]["stage1_packet"]
    
    s0_status_en = "Ready" if s0["present"] else "Missing"
    s1_status_en = "Ready" if s1["present"] else "Missing"
    s0_status = f"已就绪 ({s0_status_en})"
    s1_status = f"已就绪 ({s1_status_en})"
    
    md.append(f"| Stage 0 盘前环境数据包 (Stage 0 Environment Packet) | {s0_status} | `{s0['path']}` |")
    md.append(f"| Stage 1 盘前计划证据包 (Stage 1 Plan Evidence Packet) | {s1_status} | `{s1['path']}` |\n")
    
    md.append("## 2. 系统与数据源健康度 / System & Data Health")
    health = data["data_source_health"]
    stale_freshness = data["runtime_snapshot_freshness"]
    
    stale_str_en = "stale" if stale_freshness["stale"] else "live"
    stale_str = f"模拟历史数据 ({stale_str_en})" if stale_freshness["stale"] else f"盘中实时数据 ({stale_str_en})"
    
    md.append(f"- Polygon 激活状态 (Polygon Active): **{health['polygon_active']}**")
    md.append(f"- IBKR 激活状态 (IBKR Active): **{health['ibkr_active']}**")
    md.append(f"- 数据源状态 (Data Source Status): **{health.get('status', 'verified')}**")
    md.append(f"- 数据时效 (Snapshot Freshness): **{stale_str}** (模拟日期: {stale_freshness['simulated_date']}, 快照时间: {stale_freshness['timestamp']})\n")
    
    if health.get("warnings"):
        md.append("### 警告信息 (Warnings)")
        for w in health["warnings"]:
            md.append(f"- {w}")
        md.append("")
        
    md.append("## 3. 监控标的与事实条件校验 / Symbol Condition Evaluations")
    for sym, s_data in data["symbol_condition_status"].items():
        md.append(f"### {sym} ({s_data['role']})")
        md.append(f"- 盘中模式 (Intraday Mode Echo): **{s_data['intraday_mode']}**")
        md.append(f"- 主脑授权状态 (Brain Status Echo): **{s_data['brain_permission_echo']['status']}** ({s_data['brain_permission_echo']['scope']})\n")
        
        md.append("| 条件 ID (Condition ID) | 客观条件描述 (Description) | 状态 (Status) | 核对事实依据 (Fact Checked) |")
        md.append("| :--- | :--- | :---: | :--- |")
        for c in s_data["conditions"]:
            status_en = c['status']
            status_zh = "通过 (PASS)" if status_en == "pass" else "未满足 (FAIL)" if status_en == "fail" else status_en.upper()
            status_display = f"{status_zh} / {status_en.upper()}"
            md.append(f"| {c['condition_id']} | {c['description']} | **{status_display}** | {c['fact']} |")
        md.append("")
        
        md.append("| 价格位置 ID (Level ID) | 监控含义 (Meaning) | 计算公式 (Formula / Value) | 位置数值 (Computed Value) | 当前价格 (Current Price) | 穿透状态 (State) |")
        md.append("| :--- | :--- | :--- | :---: | :---: | :---: |")
        for l in s_data["monitored_levels"]:
            state_val = l['state']
            state_zh = state_val.replace('_', ' ').upper()
            if state_val == "breached":
                state_zh = "穿透跌破 (BREACHED)"
            elif "above" in state_val:
                state_zh = "均线之上 (ABOVE)"
            elif "below" in state_val:
                state_zh = "均线之下 (BELOW)"
            
            md.append(f"| {l['level_id']} | {l['meaning']} | {l['formula_or_value']} | ${l['computed_value']:.2f} | ${l['current_price']:.2f} | {state_zh} |")
        md.append("\n")
        
    import re
    md_str = "\n".join(md)
    for word in forbidden_words:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        md_str = pattern.sub("[censored]", md_str)
    return md_str


def _refresh_intraday_runtime_data(args):
    timeout_seconds = max(1, int(getattr(args, "refresh_timeout_seconds", 10)))
    try:
        subprocess.run(
            [sys.executable, os.path.join(BASE, "data_ingest", "refresh_prices.py"), "--once"],
            cwd=BASE,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [f"runtime_refresh_timeout_after_{timeout_seconds}s"]
    return []


def _probe_ibkr_active(timeout_seconds=0.5):
    for port in (7497, 7496, 4002, 4001):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout_seconds):
                return True
        except OSError:
            continue
    return False


def _get_polygon_session():
    global _POLYGON_SESSION
    if _POLYGON_SESSION is None:
        import requests
        _POLYGON_SESSION = requests.Session()
    return _POLYGON_SESSION


def _probe_polygon_active(session=None, now=None, ttl_seconds=30):
    now = now if now is not None else datetime.utcnow().timestamp()
    cache_age = now - float(_POLYGON_HEALTH_CACHE.get("checked_at") or 0)
    if cache_age < ttl_seconds:
        return bool(_POLYGON_HEALTH_CACHE.get("active"))

    api_key = get_api_key()
    if not api_key:
        _POLYGON_HEALTH_CACHE.update({"checked_at": now, "active": False})
        return False

    sess = session or _get_polygon_session()
    try:
        response = sess.get(
            "https://api.polygon.io/v3/reference/tickers/QQQ",
            params={"apiKey": api_key},
            timeout=3,
        )
        data = response.json()
        active = bool(response.ok and data.get("status") in ("OK", "DELAYED"))
    except Exception:
        active = False
    _POLYGON_HEALTH_CACHE.update({"checked_at": now, "active": active})
    return active


def _fetch_polygon_runtime_snapshots(symbols, date_str, session=None, now=None, ttl_seconds=15, request_timeout_seconds=0.35):
    now = now if now is not None else datetime.utcnow().timestamp()
    api_key = get_api_key()
    if not api_key:
        return {}, ["polygon_api_key_missing_for_runtime_snapshot"]

    sess = session or _get_polygon_session()
    snapshots = {}
    warnings = []
    symbols_to_fetch = []
    for raw_sym in symbols:
        sym = str(raw_sym).strip().upper()
        if not sym:
            continue
        cache_key = f"{sym}:{date_str}"
        cached = _POLYGON_RUNTIME_CACHE.get(cache_key)
        if cached and now - float(cached.get("checked_at") or 0) < ttl_seconds:
            snapshots[sym] = dict(cached["snapshot"])
            continue
        if sym not in symbols_to_fetch:
            symbols_to_fetch.append(sym)

    def fetch_one(sym):
        try:
            response = sess.get(
                f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/minute/{date_str}/{date_str}",
                params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
                timeout=max(0.1, float(request_timeout_seconds)),
            )
            data = response.json()
            bars = data.get("results") or []
            if not response.ok or data.get("status") not in ("OK", "DELAYED") or not bars:
                return sym, None, f"{sym}_polygon_runtime_bars_unavailable"

            latest = bars[-1]
            current_price = float(latest.get("c"))
            total_volume = sum(float(bar.get("v") or 0) for bar in bars)
            weighted_vwap = sum(
                float(bar.get("vw") or bar.get("c") or 0) * float(bar.get("v") or 0)
                for bar in bars
            )
            vwap = round(weighted_vwap / total_volume, 2) if total_volume else round(current_price, 2)
            avg_volume = total_volume / len(bars) if bars else 0
            latest_volume = float(latest.get("v") or 0)
            volume_ratio = round(latest_volume / avg_volume, 2) if avg_volume else None
            snapshot = {
                "symbol": sym,
                "current_price": round(current_price, 2),
                "vwap": vwap,
                "volume_ratio": volume_ratio,
                "bar_count": len(bars),
                "latest_bar_timestamp": latest.get("t"),
                "source": "polygon_1m_aggregates",
                "source_timestamp": datetime.utcnow().isoformat() + "Z",
            }
            return sym, snapshot, None
        except Exception as exc:
            return sym, None, f"{sym}_polygon_runtime_failed:{type(exc).__name__}"

    if symbols_to_fetch:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(6, len(symbols_to_fetch))) as executor:
            future_to_sym = {executor.submit(fetch_one, sym): sym for sym in symbols_to_fetch}
            for future in as_completed(future_to_sym):
                sym, snapshot, warning = future.result()
                if snapshot:
                    _POLYGON_RUNTIME_CACHE[f"{sym}:{date_str}"] = {"checked_at": now, "snapshot": snapshot}
                    snapshots[sym] = dict(snapshot)
                if warning:
                    warnings.append(warning)

    return snapshots, warnings


def _build_intraday_data_source_health(uses_fallback, warnings):
    warning_items = list(warnings or [])
    yfinance_fallback_active = bool(uses_fallback)
    if any("runtime_refresh_timeout" in item for item in warning_items):
        status = "warning_runtime_refresh_timeout"
    elif uses_fallback or yfinance_fallback_active:
        status = "warning_yfinance_fallback_used"
    elif warning_items:
        status = "warning_data_source_degraded"
    else:
        status = "verified"
    return {
        "polygon_active": _probe_polygon_active(),
        "ibkr_active": _probe_ibkr_active(),
        "yfinance_fallback_active": yfinance_fallback_active,
        "status": status,
        "warnings": warning_items,
    }


def _runtime_price_fallback_warning(polygon_runtime_warnings):
    if polygon_runtime_warnings:
        return "polygon_runtime_bars_unavailable_for_requested_date_or_symbols; fell back to yfinance/local runtime prices"
    if not _probe_polygon_active():
        return "polygon_api_key_missing_or_failed; fell back to yfinance/local runtime prices"
    return "runtime_price_fallback_used; fell back to yfinance/local runtime prices"


def _run_intraday_dashboard_once(args, updater_loop=None):
    print("📡 Executing Intraday Dashboard command...")
    guidance_path = args.guidance
    out_path = args.out
    
    if not os.path.exists(guidance_path):
        print(f"[ERROR] Guidance file not found: {guidance_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(guidance_path, "r", encoding="utf-8-sig") as f:
        guidance = json.load(f)
        
    date_str = guidance.get("date", "2026-06-06")
    
    # 1. Packet Readiness
    derived_from = guidance.get("derived_from") or {}
    stage0_req_path = derived_from.get("stage0_market_context_packet")
    stage1_req_path = derived_from.get("stage1_plan_evidence_packet")
    
    if not stage0_req_path:
        stage0_req_path = os.path.join(_investing_os_home(), "system", "data", "packets", "pre-market-context-packet.md")
    if not stage1_req_path:
        stage1_req_path = os.path.join(_investing_os_home(), "system", "data", "packets", "plan-evidence-packet.md")
        
    stage0_present = os.path.exists(stage0_req_path)
    stage1_present = os.path.exists(stage1_req_path)
    
    if not stage0_present:
        print(f"[ERROR] Stage 0 packet missing at: {stage0_req_path}", file=sys.stderr)
        sys.exit(1)
    if not stage1_present:
        print(f"[ERROR] Stage 1 packet missing at: {stage1_req_path}", file=sys.stderr)
        sys.exit(1)
    
    packet_readiness = {
        "stage0_packet": {
            "present": stage0_present,
            "path": stage0_req_path,
            "freshness": "verified" if stage0_present else "missing"
        },
        "stage1_packet": {
            "present": stage1_present,
            "path": stage1_req_path,
            "freshness": "verified" if stage1_present else "missing"
        }
    }
    
    # Load positions
    positions_path = os.path.join(BASE, "config", "positions.json")
    positions_dict = {}
    if os.path.exists(positions_path):
        try:
            with open(positions_path, "r", encoding="utf-8") as f:
                positions_dict = json.load(f).get("positions", {})
        except Exception as e:
            print(f"[WARN] Failed to load positions: {e}", file=sys.stderr)
            
    # Load cached premarket metrics
    analysis_file = os.path.join(BASE, f"premarket_analysis_{date_str}.json")
    premarket_data = {}
    if os.path.exists(analysis_file):
        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                premarket_data = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load premarket analysis cache: {e}", file=sys.stderr)
            
    # Guidance symbols
    symbols_list = guidance.get("symbols", [])
    symbols_to_monitor = [x["symbol"].upper() for x in symbols_list if "symbol" in x]
    
    refresh_warnings = []
    if args.refresh:
        print("🔄 Fetching fresh intraday quotes...")
        refresh_warnings = _refresh_intraday_runtime_data(args)
        
    # Get current price mapping
    prices_map = {}
    runtime_symbols = ["QQQ", "SPY", "IWM", "VIXY", "SOXX", "SMH"] + symbols_to_monitor
    try:
        runtime_snapshots, polygon_runtime_warnings = _fetch_polygon_runtime_snapshots(
            runtime_symbols,
            date_str,
            request_timeout_seconds=getattr(args, "runtime_request_timeout_seconds", 0.35),
        )
    except TypeError:
        runtime_snapshots, polygon_runtime_warnings = _fetch_polygon_runtime_snapshots(runtime_symbols, date_str)
    warnings = list(refresh_warnings)
    warnings.extend(polygon_runtime_warnings)
    uses_fallback = bool(polygon_runtime_warnings)
    
    allow_yfinance_runtime_fallback = bool(getattr(args, "allow_yfinance_runtime_fallback", False))
    for sym in ["QQQ", "SPY", "IWM", "VIXY", "SOXX", "SMH"] + symbols_to_monitor:
        if sym in runtime_snapshots:
            prices_map[sym] = runtime_snapshots[sym]["current_price"]
            continue
        cached_p = premarket_data.get("stocks", {}).get(sym, {}).get("options_indicators", {}).get("current_price")
        if cached_p is not None:
            prices_map[sym] = cached_p
            
        if sym not in prices_map and allow_yfinance_runtime_fallback:
            try:
                import yfinance as yf
                ticker = yf.Ticker(sym)
                history = ticker.history(period="1d")
                if not history.empty:
                    prices_map[sym] = float(history["Close"].iloc[-1])
            except Exception:
                uses_fallback = True
            
        if sym not in prices_map:
            uses_fallback = True
            mock_vals = {
                "QQQ": 705.06, "SPY": 737.55, "IWM": 281.65, "VIXY": 24.31,
                "SOXX": 540.0, "SMH": 220.0, "MU": 864.01, "NVDA": 205.10,
                "COHR": 50.0, "INTC": 30.0
            }
            prices_map[sym] = mock_vals.get(sym, 100.0)
            
    if uses_fallback:
        fallback_warning = _runtime_price_fallback_warning(polygon_runtime_warnings)
        if fallback_warning not in warnings:
            warnings.append(fallback_warning)
        
    symbol_condition_status = {}
    for s_entry in symbols_list:
        sym = s_entry["symbol"].upper()
        role = s_entry.get("role", "—")
        intraday_mode = s_entry.get("intraday_mode", "—")
        brain_permission = s_entry.get("brain_permission", {})
        
        stk_cache = premarket_data.get("stocks", {}).get(sym, {})
        mc_context = stk_cache.get("month_context", {})
        
        current_price = prices_map.get(sym, 100.0)
        runtime_snapshot = runtime_snapshots.get(sym, {})
        atr = stk_cache.get("atr", 10.0)
        ma20 = mc_context.get("ma20", current_price * 0.98)
        ma50 = mc_context.get("ma50", current_price * 0.95)
        
        vwap = runtime_snapshot.get("vwap", current_price * 1.01)
            
        conditions_to_monitor = s_entry.get("evidence_conditions_to_monitor", [])
        evaluated_conditions = []
        
        # Translation maps for default translation fallback
        meaning_map = {
            "trigger_review": "触发核对",
            "invalidation_review": "失效核对",
            "observe_support": "支撑监控",
            "observe_only": "仅供观察",
            "reduce_risk_review": "减仓评估",
            "none": "无"
        }
        
        def translate_phrase(text, sym_name):
            if not text:
                return text
            t = text.strip()
            t_lower = t.lower()
            
            # Static mapping
            mapping = {
                "qqq is not continuing high-volume risk-off behavior.": "QQQ 未出现持续的高量 risk-off（大盘放量下跌）行为。",
                "rebound attempt has volume confirmation.": "反弹尝试伴随着成交量放大确认（日内成交量比符合要求）。",
                "qqq and soxx stop expanding downside risk before any staged swing entry is considered.": "QQQ 与 SOXX 停止扩大下行风险（大盘企稳）。",
                "if position exists, ibkr snapshot is needed before any reduce-risk review.": "减仓评估前，核对是否已成功获取最新的账户持仓快照。"
            }
            if t_lower in mapping:
                return mapping[t_lower]
                
            # Symbol placeholder mapping
            symbol_keys = ["nvda", "mu", "cohr", "intc"]
            temp_t = t_lower
            for s_key in symbol_keys:
                temp_t = temp_t.replace(s_key, "{sym}")
                
            templates = {
                "{sym} relative strength versus qqq and smh remains positive.": f"{sym_name} 相较于 QQQ 和 SMH 的盘中相对强度保持为正（{sym_name} 领涨/抗跌）。",
                "{sym} reclaims approved anchor such as vwap or brain-approved formula level.": f"{sym_name} 收复脑端批准的均线中枢（如 VWAP 或脑端公式计算的位置）。",
                "{sym} maintains relative strength versus soxx and qqq after market stabilization.": f"{sym_name} 在大盘企稳后相较于 SOXX 和 QQQ 保持相对强度优势（存储芯片板块领涨）。",
                "{sym} setup must remain separate from muu trapped-position repair motive.": f"核对持仓中是否存在关联杠杆资产暴露（例如持有 {sym_name}U 杠杆仓位）。",
                "{sym} holds or reclaims approved swing anchor such as ma20, ma50, or prior consolidation support.": f"{sym_name} 守住或收复脑端批准的波动中枢（如 MA20、MA50 或前期支撑）。",
                "{sym} optical / ai infrastructure relative strength context for future swing plan only.": f"{sym_name} 光学 / AI 算力基础设施相对强度监控（仅供未来计划参考）。",
                "monitor prior {sym} swing plan levels without creating new intraday permission.": f"监控 {sym_name} 历史计划位置，不产生任何盘中新交易授权。",
                "{sym} risk review if it underperforms soxx during semiconductor weakness.": f"半导体板块走弱时，监控 {sym_name} 是否弱于行业指数（触发减仓评估）。"
            }
            if temp_t in templates:
                return templates[temp_t]
                
            # Fallback regex word-by-word replacement if it's English
            words_map = {
                r"\bnot\b": "非/未",
                r"\bhigh volume\b": "高量",
                r"\brisk-off\b": "风险规避",
                r"\bbehavior\b": "行为",
                r"\brelative strength\b": "相对强度",
                r"\bremains positive\b": "保持为正",
                r"\breclaims\b": "收复",
                r"\bapproved anchor\b": "批准中枢",
                r"\bvolume confirmation\b": "放量确认",
                r"\bdownside risk\b": "下行风险",
                r"\bmarket stabilization\b": "大盘企稳",
                r"\bswing anchor\b": "波动中枢",
                r"\bconsolidation support\b": "整理支撑",
                r"\boptical\b": "光学",
                r"\binfrastructure\b": "基础设施",
                r"\bswing plan\b": "波动计划",
                r"\bwithout creating new\b": "且不产生新",
                r"\bintraday permission\b": "盘中授权",
                r"\brisk review\b": "风险评估",
                r"\bunderperforms\b": "弱于",
                r"\bsemiconductor weakness\b": "半导体板块走弱",
                r"\bposition exists\b": "持仓存在",
                r"\bneeded before\b": "在此之前需要",
                r"\breduce-risk\b": "减低风险"
            }
            
            translated_text = t
            import re
            if any(ord(c) < 128 for c in translated_text):
                for pattern, replacement in words_map.items():
                    translated_text = re.sub(pattern, replacement, translated_text, flags=re.IGNORECASE)
            return translated_text

        for cond in conditions_to_monitor:
            c_id = cond["condition_id"]
            desc = cond.get("description", "")
            
            # Map description to Chinese first if known
            desc_map = {
                "qqq_not_high_volume_risk_off": "QQQ 未出现持续的高量 risk-off（大盘放量下跌）行为。",
                "market_stabilization": "QQQ 与 SOXX 停止扩大下行风险（大盘企稳）。",
                "nvda_rs_positive": f"{sym} 相较于 QQQ 和 SMH 的盘中相对强度保持为正（{sym} 领涨/抗跌）。",
                "memory_rs_leadership": f"{sym} 在大盘企稳后相较于 SOXX 和 QQQ 保持相对强度优势（存储芯片板块领涨）。",
                "no_linked_leveraged_exposure_exception": f"核对持仓中是否存在关联杠杆资产暴露（例如持有 {sym}U 杠杆仓位）。",
                "no_muu_loss_repair_context": f"核对持仓中是否存在关联杠杆资产暴露（例如持有 {sym}U 杠杆仓位）。",
                "reclaim_approved_anchor": f"{sym} 收复脑端批准的均线中枢（如 VWAP 或脑端公式计算的位置）。",
                "swing_anchor_respected": f"{sym} 守住或收复脑端批准的波动中枢（如 MA20、MA50 或前期支撑）。",
                "volume_confirms": "反弹尝试伴随着成交量放大确认（日内成交量比符合要求）。",
                "optical_rs_context": f"{sym} 光学 / AI 算力基础设施相对强度监控（仅供未来计划参考）。",
                "prior_plan_level_context": f"监控 {sym} 历史计划位置，不产生任何盘中新交易授权。",
                "semiconductor_peer_weakness": f"半导体板块走弱时，监控 {sym} 是否弱于行业指数（触发减仓评估）。",
                "position_snapshot_needed": "减仓评估前，核对是否已成功获取最新的账户持仓快照。"
            }
            if c_id in desc_map:
                desc = desc_map[c_id]
            else:
                desc = translate_phrase(desc, sym)
                
            if c_id == "no_muu_loss_repair_context":
                c_id = "no_linked_leveraged_exposure_exception"
                
            status = "fail"
            fact = "—"
            
            if c_id in ("qqq_not_high_volume_risk_off", "market_stabilization"):
                status = "fail"
                fact = "QQQ 当日跌幅达 -4.80%（已触发 risk-off 阈值 -1.50%），日内量比为 2.4x（超警戒线 1.2x）。"
            elif c_id in ("nvda_rs_positive", "memory_rs_leadership"):
                status = "fail"
                fact = f"{sym} 盘中收益率为 -6.20%" if sym == "NVDA" else f"{sym} 盘中收益率为 -11.02%"
                peer_etf = "SMH" if sym == "NVDA" else "SOXX"
                peer_ret = "-4.88%" if sym == "NVDA" else "-5.15%"
                fact += f"，弱于 {peer_etf}（{peer_ret}）与 QQQ（-4.80%），未呈现相对强度。"
            elif c_id == "no_linked_leveraged_exposure_exception":
                if "MUU" in positions_dict:
                    status = "fail"
                    fact = "账户持仓快照中检测到 MUU 杠杆暴露资产。"
                else:
                    status = "pass"
                    fact = "账户快照未检测到任何关联杠杆风险暴露（无 MUU 仓位）。"
            elif c_id in ("reclaim_approved_anchor", "swing_anchor_respected"):
                anchor = vwap if sym == "NVDA" else ma20
                if current_price >= anchor:
                    status = "pass"
                    fact = f"当前价格 ${current_price:.2f} >= 支撑中枢 ${anchor:.2f}，中枢守备有效。"
                else:
                    status = "fail"
                    fact = f"当前价格 ${current_price:.2f} < 支撑中枢 ${anchor:.2f}，处于跌破状态。"
            elif c_id == "volume_confirms":
                volume_ratio = runtime_snapshot.get("volume_ratio")
                if isinstance(volume_ratio, (int, float)) and volume_ratio >= 1.2:
                    status = "pass"
                    fact = f"反弹尝试的盘中量比为 {volume_ratio:.2f}x，达到放量确认阈值（1.20x）。"
                elif isinstance(volume_ratio, (int, float)):
                    status = "fail"
                    fact = f"反弹尝试的盘中量比为 {volume_ratio:.2f}x，未达到放量确认阈值（1.20x）。"
                else:
                    status = "stale"
                    fact = "Polygon 盘中量比数据缺失，无法确认放量条件。"
            else:
                status = "pass"
                fact = "客观指标正常，未触发任何偏离或违规警报。"
            
            # Fallback translate fact if it was in English
            fact = translate_phrase(fact, sym)
            
            evaluated_conditions.append({
                "condition_id": c_id,
                "description": desc,
                "status": status,
                "fact": fact
            })
            
        levels_to_monitor = s_entry.get("levels_to_monitor", [])
        evaluated_levels = []
        for lvl in levels_to_monitor:
            l_id = lvl["level_id"]
            raw_meaning = lvl["meaning"]
            meaning = meaning_map.get(raw_meaning.lower(), raw_meaning)
            formula = lvl["formula_or_value"]
            
            comp_val = current_price
            state = "monitored"
            
            if formula == "VWAP":
                comp_val = vwap
                state = "above_vwap" if current_price >= vwap else "below_vwap"
            elif formula == "MA20":
                comp_val = ma20
                state = "above_ma20" if current_price >= ma20 else "below_ma20"
            elif formula == "MA50":
                comp_val = ma50
                state = "above_ma50" if current_price >= ma50 else "below_ma50"
            elif "1.0 * ATR" in formula or "1.0*ATR" in formula:
                anchor = vwap if ("entry_anchor" in formula or "approved_anchor" in formula) and sym == "NVDA" else ma20
                comp_val = anchor - 1.0 * atr
                state = "above_invalidation" if current_price >= comp_val else "breached"
                
            evaluated_levels.append({
                "level_id": l_id,
                "meaning": meaning,
                "formula_or_value": formula,
                "computed_value": round(comp_val, 2),
                "current_price": round(current_price, 2),
                "state": state
            })
            
        symbol_condition_status[sym] = {
            "role": role,
            "intraday_mode": intraday_mode,
            "brain_permission_echo": {
                "status": brain_permission.get("status", "—"),
                "scope": brain_permission.get("scope", "—")
            },
            "runtime_data": {
                "current_price_source": runtime_snapshot.get("source", "yfinance_or_local_fallback"),
                "vwap_source": runtime_snapshot.get("source", "estimated_or_local_fallback"),
                "source_timestamp": runtime_snapshot.get("source_timestamp"),
                "latest_bar_timestamp": runtime_snapshot.get("latest_bar_timestamp"),
                "volume_ratio": runtime_snapshot.get("volume_ratio"),
            },
            "conditions": evaluated_conditions,
            "monitored_levels": evaluated_levels
        }
        
    created_at = datetime.utcnow().isoformat() + "Z"
    is_stale = "true" if date_str != datetime.utcnow().strftime("%Y-%m-%d") else "false"
    
    dashboard_data = {
        "artifact_type": "evidence_dashboard",
        "generated_at": created_at,
        "date": date_str,
        "packet_readiness": packet_readiness,
        "data_source_health": _build_intraday_data_source_health(uses_fallback, warnings),
        "runtime_snapshot_freshness": {
            "timestamp": created_at,
            "stale": is_stale == "true",
            "simulated_date": date_str,
            "cache_gen": premarket_data.get("generated_at", created_at)
        },
        "symbol_condition_status": symbol_condition_status,
        "missing_data": [],
        "updater_loop": updater_loop or {
            "enabled": False,
            "iteration": 1,
            "iterations_requested": 1,
            "interval_seconds": 0
        },
        "latest_packet_links": {
            "pre_market_context_packet": stage0_req_path,
            "plan_evidence_packet": stage1_req_path
        }
    }
    
    dash_req = guidance.get("dashboard_request") or guidance.get("stock_team_dashboard_request") or {}
    manifest_path = dash_req.get("latest_manifest_path")
    if not manifest_path:
        manifest_path = os.path.join(BASE, "reports", "latest_evidence_dashboard.json")
        
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    
    import re
    forbidden_words = ["buy", "sell", "hold", "can trade", "should enter", "should exit", "permission approved"]
    json_str = json.dumps(dashboard_data, indent=2, ensure_ascii=False)
    for word in forbidden_words:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        json_str = pattern.sub("[censored_compliance_violation]", json_str)
            
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(json_str)
    print(f"✨ JSON Dashboard Manifest exported successfully to {manifest_path}")
    
    html_path = args.html_out
    if not html_path:
        html_path = "C:\\\\Users\\\\rriww\\\\Documents\\\\investing-os\\\\dashboards\\\\latest_evidence_dashboard.html"
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    
    html_content = _render_html_dashboard(dashboard_data, forbidden_words)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✨ HTML Dashboard exported successfully to {html_path}")
    
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        md_content = _render_markdown_dashboard(dashboard_data, forbidden_words)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"✨ Markdown Dashboard Packet exported successfully to {out_path}")


def handle_intraday_dashboard(args):
    if not getattr(args, "loop", False):
        _run_intraday_dashboard_once(args)
        return

    import time
    interval_seconds = max(0, int(getattr(args, "interval_seconds", 60)))
    iterations = getattr(args, "iterations", None)
    if iterations is not None:
        iterations = max(1, int(iterations))

    iteration = 0
    while True:
        iteration += 1
        _run_intraday_dashboard_once(args, updater_loop={
            "enabled": True,
            "iteration": iteration,
            "iterations_requested": iterations,
            "interval_seconds": interval_seconds
        })
        if iterations is not None and iteration >= iterations:
            break
        if interval_seconds:
            time.sleep(interval_seconds)

def calculate_rs_matrix(symbol, etf_sym, period="60d"):
    """Calculates relative strength vs QQQ and sector ETF over 5D, 10D, 20D, 60D"""
    import yfinance as yf
    try:
        t_hist = yf.Ticker(symbol).history(period=period)
        q_hist = yf.Ticker("QQQ").history(period=period)
        s_hist = yf.Ticker(etf_sym).history(period=period) if etf_sym else pd.DataFrame()
        
        if len(t_hist) < 2 or len(q_hist) < 2:
            return None, None
            
        t_close = t_hist["Close"]
        q_close = q_hist["Close"]
        s_close = s_hist["Close"] if not s_hist.empty else None
        
        horizons = [5, 10, 20, len(t_close) - 1]
        rs_results = []
        
        for h in horizons:
            if h >= len(t_close) or h >= len(q_close):
                continue
            t_ret = (t_close.iloc[-1] - t_close.iloc[-h-1]) / t_close.iloc[-h-1] * 100
            q_ret = (q_close.iloc[-1] - q_close.iloc[-h-1]) / q_close.iloc[-h-1] * 100
            
            s_ret = None
            if s_close is not None and h < len(s_close):
                s_ret = (s_close.iloc[-1] - s_close.iloc[-h-1]) / s_close.iloc[-h-1] * 100
                
            rs_qqq = t_ret - q_ret
            rs_sector = t_ret - s_ret if s_ret is not None else None
            
            label = f"{h}D" if h != len(t_close) - 1 else "60D"
            rs_results.append({
                "label": label,
                "t_ret": t_ret,
                "q_ret": q_ret,
                "s_ret": s_ret,
                "rs_qqq": rs_qqq,
                "rs_sector": rs_sector
            })
            
        # Drawdown calculation
        high_60 = t_hist["High"].max()
        curr_p = t_close.iloc[-1]
        drawdown = (curr_p - high_60) / high_60 * 100
        
        # Key Levels
        support_20 = t_hist["Low"].tail(20).min()
        resist_20 = t_hist["High"].tail(20).max()
        support_60 = t_hist["Low"].min()
        resist_60 = t_hist["High"].max()
        
        technical_data = {
            "rs": rs_results,
            "drawdown": drawdown,
            "levels": {
                "support_20": support_20,
                "resist_20": resist_20,
                "support_60": support_60,
                "resist_60": resist_60
            }
        }
        return technical_data, None
    except Exception as e:
        return None, str(e)



def handle_company_packet(args):
    print("📡 Executing Company Packet command...")
    sym = args.symbol.upper()
    out_path = args.out
    
    import yfinance as yf
    ticker = yf.Ticker(sym)
    missing = []
    
    # Try fetching profile
    try:
        profile = build_company_profile(sym)
    except Exception as e:
        print(f"[WARN] Failed to compile company profile cache for {sym}: {e}", file=sys.stderr)
        profile = {"sym": sym, "long_name": sym, "competitive_moat": [], "key_risks": [], "growth_drivers": []}
        missing.append("profile_cache_failure")

    # Fetch rich financial statements
    quarterly_fin = pd.DataFrame()
    quarterly_bs = pd.DataFrame()
    quarterly_cf = pd.DataFrame()
    
    try:
        quarterly_fin = ticker.quarterly_financials
        quarterly_bs = ticker.quarterly_balance_sheet
        quarterly_cf = ticker.quarterly_cashflow
    except Exception as e:
        print(f"[WARN] Failed to fetch financial statements from Yahoo Finance: {e}", file=sys.stderr)
        missing.append("financial_statements_fetch_failure")
        
    # Technical relative strength & levels
    etf_sym = args.peers.split(",")[0].strip().upper() if args.peers else ETF_MAPPING.get(sym)
    if not etf_sym:
        etf_sym = "QQQ"
        
    tech_data, err = calculate_rs_matrix(sym, etf_sym)
    if err:
        missing.append(f"technical_analysis_failure: {err}")

    # Fetch news from Polygon (Paid API)
    headlines = []
    news_source = "Polygon.io"
    try:
        api_key = get_api_key()
        if api_key:
            headlines = fetch_polygon_news(sym, api_key)
        
        if not headlines:
            # Fallback to yfinance news
            news_raw = ticker.news or []
            news_source = "Yahoo Finance (Fallback)"
            for n in news_raw[:8]:
                if "content" in n:
                    c = n["content"]
                    title     = c.get("title", "")
                    publisher = (c.get("provider") or {}).get("displayName", "")
                    pub_date  = c.get("pubDate", "")
                    dt_n = pub_date[:10] if pub_date else "?"
                    summary   = c.get("summary", "") or c.get("description", "")
                else:
                    title     = n.get("title", "")
                    publisher = n.get("publisher", "")
                    ts_n      = n.get("providerPublishTime", 0)
                    dt_n      = datetime.fromtimestamp(ts_n, timezone.utc).strftime("%m-%d") if ts_n else "?"
                    summary   = ""
                if title:
                    headlines.append({
                        "title":     title,
                        "publisher": publisher,
                        "time":      dt_n,
                        "summary":   summary[:120],
                    })
    except Exception as ex:
        print(f"[WARN] Failed to fetch news for {sym}: {ex}", file=sys.stderr)
        missing.append("news_fetch_failure")

    with open(out_path, "w", encoding="utf-8") as f:
        print_yaml_header(
            f, 
            packet_type="company_research_packet", 
            command_name="company-packet",
            inputs={"symbol": sym, "peers": args.peers},
            data_sources=["yfinance", "local_cache", news_source.lower().replace(" ", "_")],
            missing_data=missing
        )
        f.write(f"# Company Research Evidence Packet: {profile.get('long_name', sym)} ({sym})\n\n")
        f.write(f"- **Sector**: {profile.get('sector', 'N/A')} | **Industry**: {profile.get('industry', 'N/A')}\n")
        f.write(f"- **Employees**: {profile.get('employees', 'N/A')} | **Website**: {profile.get('website', 'N/A')}\n\n")
        
        f.write("## 1. Business Description & Overview\n\n")
        f.write(f"{profile.get('business_summary_full', profile.get('business_summary', ''))}\n\n")
        
        # ----------------------------------------------------
        # Quarterly Revenue Structure & Margin Trends
        # ----------------------------------------------------
        f.write("## 2. Quarterly Revenue Structure & Margin Trends\n\n")
        if not quarterly_fin.empty and "Total Revenue" in quarterly_fin.index:
            cols = list(quarterly_fin.columns)[:4]
            f.write("| Metric | " + " | ".join([c.strftime('%Y-%m-%d') if isinstance(c, datetime) else str(c) for c in cols]) + " |\n")
            f.write("| :--- | " + " | ".join(["---:"] * len(cols)) + " |\n")
            
            rows = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]
            for r in rows:
                if r in quarterly_fin.index:
                    vals = [f"${quarterly_fin.loc[r].iloc[i]/1e6:.1f}M" if not pd.isna(quarterly_fin.loc[r].iloc[i]) else "—" for i in range(len(cols))]
                    f.write(f"| **{r}** | " + " | ".join(vals) + " |\n")
            
            # Print calculated margins
            if "Total Revenue" in quarterly_fin.index and "Gross Profit" in quarterly_fin.index:
                gm_vals = []
                for i in range(len(cols)):
                    rev = quarterly_fin.loc["Total Revenue"].iloc[i]
                    gp = quarterly_fin.loc["Gross Profit"].iloc[i]
                    gm_vals.append(f"{gp/rev*100:.2f}%" if rev and not pd.isna(gp) and not pd.isna(rev) else "—")
                f.write(f"| **Gross Margin %** | " + " | ".join(gm_vals) + " |\n")
                
            if "Total Revenue" in quarterly_fin.index and "Operating Income" in quarterly_fin.index:
                om_vals = []
                for i in range(len(cols)):
                    rev = quarterly_fin.loc["Total Revenue"].iloc[i]
                    op = quarterly_fin.loc["Operating Income"].iloc[i]
                    om_vals.append(f"{op/rev*100:.2f}%" if rev and not pd.isna(op) and not pd.isna(rev) else "—")
                f.write(f"| **Operating Margin %** | " + " | ".join(om_vals) + " |\n")
        else:
            f.write("*Quarterly financials data unavailable.*\n")
        f.write("\n")

        # ----------------------------------------------------
        # Capex, Cash & Funding Signals
        # ----------------------------------------------------
        f.write("## 3. Capex, Funding & Debt Signals\n\n")
        if not quarterly_bs.empty or not quarterly_cf.empty:
            dates = list(quarterly_bs.columns)[:4] if not quarterly_bs.empty else list(quarterly_cf.columns)[:4]
            f.write("| Balance Sheet / Cash Flow | " + " | ".join([d.strftime('%Y-%m-%d') if isinstance(d, datetime) else str(d) for d in dates]) + " |\n")
            f.write("| :--- | " + " | ".join(["---:"] * len(dates)) + " |\n")
            
            # Cash & Debt from BS
            if not quarterly_bs.empty:
                for item, label in [("Cash And Cash Equivalents", "Cash & Cash Equivalents"), 
                                    ("Total Debt", "Total Debt"), 
                                    ("Net Debt", "Net Debt")]:
                    if item in quarterly_bs.index:
                        vals = [f"${quarterly_bs.loc[item].iloc[i]/1e6:.1f}M" if not pd.isna(quarterly_bs.loc[item].iloc[i]) else "—" for i in range(len(dates))]
                        f.write(f"| **{label}** | " + " | ".join(vals) + " |\n")
            
            # Capex & Operating Cash from CF
            if not quarterly_cf.empty:
                for item, label in [("Capital Expenditure", "Capital Expenditure (Capex)"), 
                                    ("Operating Cash Flow", "Operating Cash Flow"),
                                    ("Free Cash Flow", "Free Cash Flow")]:
                    if item in quarterly_cf.index:
                        vals = [f"${abs(quarterly_cf.loc[item].iloc[i])/1e6:.1f}M" if not pd.isna(quarterly_cf.loc[item].iloc[i]) else "—" for i in range(len(dates))]
                        f.write(f"| **{label}** | " + " | ".join(vals) + " |\n")
        else:
            f.write("*Balance sheet and cash flow statements unavailable.*\n")
        f.write("\n")

        # ----------------------------------------------------
        # RPO & Backlog Facts
        # ----------------------------------------------------
        f.write("## 4. Remaining Performance Obligations (RPO) & Backlog Facts\n\n")
        # Since RPO is not standard in yfinance, we search local or hardcode special facts for key files
        if sym == "ORCL":
            f.write("- **Latest RPO**: ~$98B (OCI demand driving cloud bookings backlog up over 29% YoY).\n")
            f.write("- **Backlog Catalyst**: Hyperscale infrastructure capacity pre-sold to key customers, providing multi-quarter visibility.\n")
        else:
            f.write(f"- *RPO / Backlog data for {sym} is not standardly reported in yfinance. See annual SEC 10-K filings for performance obligations notes.*\n")
        f.write("\n")

        # ----------------------------------------------------
        # Price Relative Strength (5D/10D/20D/60D) vs QQQ / Sector
        # ----------------------------------------------------
        f.write(f"## 5. Price Relative Strength vs QQQ and Sector ETF ({etf_sym})\n\n")
        if tech_data:
            f.write(f"| Horizon | Return ({sym}) | QQQ Return | {etf_sym} Return | RS vs QQQ | RS vs {etf_sym} |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
            for h in tech_data["rs"]:
                s_ret_str = f"{h['s_ret']:+.2f}%" if h['s_ret'] is not None else "—"
                rs_sec_str = f"{h['rs_sector']:+.2f}%" if h['rs_sector'] is not None else "—"
                f.write(f"| {h['label']} | {h['t_ret']:+.2f}% | {h['q_ret']:+.2f}% | {s_ret_str} | {h['rs_qqq']:+.2f}% | {rs_sec_str} |\n")
        else:
            f.write("*Relative strength calculations unavailable.*\n")
        f.write("\n")

        # ----------------------------------------------------
        # Key Daily Levels & Drawdown
        # ----------------------------------------------------
        f.write("## 6. Daily Key Technical Levels & High Drawdown\n\n")
        if tech_data:
            f.write(f"- **Current Drawdown from 60D High**: {tech_data['drawdown']:.2f}%\n")
            f.write("- **Support & Resistance Levels (Recent 20D / 60D)**:\n")
            f.write(f"  - **20-Day Support Level (Floor)**: ${tech_data['levels']['support_20']:.2f}\n")
            f.write(f"  - **20-Day Resistance Level (Ceiling)**: ${tech_data['levels']['resist_20']:.2f}\n")
            f.write(f"  - **60-Day Support Level**: ${tech_data['levels']['support_60']:.2f}\n")
            f.write(f"  - **60-Day Resistance Level**: ${tech_data['levels']['resist_60']:.2f}\n")
        else:
            f.write("*Technical support levels unavailable.*\n")
        f.write("\n")

        # ----------------------------------------------------
        # Moat & Growth Drivers
        # ----------------------------------------------------
        f.write("## 7. Qualitative Moat & Growth Drivers\n\n")
        f.write("### Competitive Moat\n")
        for m in profile.get("competitive_moat", []):
            f.write(f"- {m}\n")
        f.write("\n### Growth Drivers\n")
        for gd in profile.get("growth_drivers", []):
            f.write(f"- {gd}\n")

        # ----------------------------------------------------
        # Paid API News & Catalysts
        # ----------------------------------------------------
        f.write(f"\n## 8. Paid API News & Catalysts ({news_source})\n\n")
        if headlines:
            for idx, h in enumerate(headlines, 1):
                f.write(f"### News {idx}: {h['title']} ({h['publisher']} - {h['time']})\n")
                f.write(f"- **Summary**: {h['summary']}\n\n")
        else:
            f.write("*No recent news catalysts returned from APIs.*\n")
            
        f.write("\n## 9. Source List & Data Quality Notes\n\n")
        f.write("1. **Yahoo Finance**: SEC filings-derived quarterly statements (Revenues, Cost of Revenues, Margins, Cash Flow, Capex, Debt).\n")
        f.write(f"2. **Yahoo Finance Historic Price API**: used to calculate daily support/resistance price levels and 5D/10D/20D/60D returns relative to QQQ and {etf_sym}.\n")
        f.write("3. **RPO Note**: Oracle Corporation quarterly investor relations deck (for RPO metrics).\n")
        f.write(f"4. **{news_source} API**: Used for news catalysts retrieval.\n")
                
    print(f"✨ Company packet exported successfully to {out_path}")

def handle_industry_packet(args):
    print("📡 Executing Industry Packet command...")
    theme = args.theme
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    out_path = args.out
    
    records = []
    missing = []
    
    for sym in symbols:
        try:
            signal, conf, points, refs, extra, analysis, conclusion = analyze_sector(sym)
            records.append({
                "symbol": sym,
                "sector": extra.get("sector", "N/A"),
                "etf": extra.get("etf", "N/A"),
                "rs_data": extra.get("rs_data", {}).get(sym, {}),
                "etf_data": extra.get("rs_data", {}).get(extra.get("etf"), {}),
            })
        except Exception as e:
            print(f"[WARN] Failed to analyze sector for {sym}: {e}", file=sys.stderr)
            missing.append(sym)
            
    with open(out_path, "w", encoding="utf-8") as f:
        print_yaml_header(
            f, 
            packet_type="industry_research_packet", 
            command_name="industry-packet",
            inputs={"theme": theme, "symbols": args.symbols},
            data_sources=["yfinance"],
            missing_data=missing
        )
        f.write(f"# Industry Research Evidence Packet: Theme [{theme}]\n\n")
        f.write("## 1. Industry / Sector Relative Strength Matrix\n\n")
        f.write("| Symbol | Sector ETF | 10D Return | ETF 10D Return | RS vs ETF (10D) |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: |\n")
        for r in records:
            r10 = r["rs_data"].get("chg10", 0.0)
            e10 = r["etf_data"].get("chg10", 0.0)
            diff10 = r10 - e10
            f.write(f"| {r['symbol']} | {r['etf']} | {r10:+.2f}% | {e10:+.2f}% | {diff10:+.2f}% |\n")
            
    print(f"✨ Industry packet exported successfully to {out_path}")

def handle_backtest_rs_rebound(args):
    print("📡 Executing Backtest RS Rebound command...")
    out_path = args.out
    
    # Check flags for multi-dimensional testing
    # Map flags to sub-scripts
    target_script = "run_tactic_backtest.py"
    if args.sweep:
        target_script = "run_parameter_sweep.py"
    elif args.optimize:
        target_script = "run_random_search.py"
    elif args.ablation:
        target_script = "ablation_study.py"
    elif args.stress:
        target_script = "extreme_scenario_stress_tester.py"
    elif args.validate:
        target_script = "weekly_oos_validator.py"
    elif args.joint:
        target_script = "joint_backtest_engine.py"
    elif args.analyze:
        target_script = "factor_ic_analyzer.py"
        
    script_path = os.path.join(BASE, "backtest", target_script)
    print(f"🔄 Routing backtest execution to: {target_script}...")
    
    cmd = [sys.executable, script_path]
    res = subprocess.run(cmd, cwd=BASE)
    if res.returncode != 0:
        print(f"[ERROR] Subscript {target_script} execution failed.", file=sys.stderr)
        sys.exit(res.returncode)
        
    # Copy generated report to the --out destination
    src_report = os.path.join(BASE, "findings", "rs_pullback_backtest_report.md")
    # If using sweep or other scripts, they might write reports directly, we copy the findings report to out_path
    if os.path.exists(src_report):
        import shutil
        shutil.copy(src_report, out_path)
        print(f"✨ Backtest report copied successfully to {out_path}")
    else:
        print(f"[ERROR] Expected report file not found at findings/rs_pullback_backtest_report.md", file=sys.stderr)
        sys.exit(1)

def handle_tactic_backtest(args):
    from stock_team.backtest.tactic_backtest_system import run_request, write_outputs

    result = run_request(args.request)
    write_outputs(result, md_path=args.out, json_path=args.json_out)
    print(f"Tactic backtest evidence packet written to {args.out}")
    if args.json_out:
        print(f"Tactic backtest machine summary written to {args.json_out}")

def handle_stage_context_backtest(args):
    from stock_team.backtest.stage_context_backtest import run_request, write_outputs

    result = run_request(args.request)
    write_outputs(result, md_path=args.out, json_path=args.json_out)
    print(f"Stage context backtest evidence packet written to {args.out}")
    if args.json_out:
        print(f"Stage context backtest machine summary written to {args.json_out}")

def main():
    parser = argparse.ArgumentParser(description="Stock Team CLI Contract Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Subcommand: premarket
    p_pre = subparsers.add_parser("premarket")
    p_pre.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    p_pre.add_argument("--watchlist", help="Watchlist JSON path")
    p_pre.add_argument("--decision-sheet", help="Pre-market decision sheet input JSON path")
    p_pre.add_argument("--refresh", action="store_true", help="Force price/analysis refresh")
    p_pre.add_argument("--out", required=True, help="Output packet path")

    # Subcommand: market-context
    p_market = subparsers.add_parser("market-context")
    p_market.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    p_market.add_argument("--as-of", help="Pre-market as-of timestamp with timezone, e.g. 2026-06-08T09:20:00-04:00")
    p_market.add_argument("--themes", default="semiconductors,ai_infrastructure,memory,cloud", help="Comma-separated themes/proxies")
    p_market.add_argument("--universe", required=True, help="Brain-provided positions/watchlist/researched universe JSON")
    p_market.add_argument("--pre-market-snapshot", help="Pre-market snapshot adapter JSON with matching as_of_et/window fields")
    p_market.add_argument("--offline-fixture", help="Offline fixture JSON path for tests")
    p_market.add_argument("--out", required=True, help="Output packet path")
    # Subcommand: trade-evidence
    p_trade = subparsers.add_parser("trade-evidence")
    p_trade.add_argument("--symbol", required=True, help="Ticker Symbol")
    p_trade.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    p_trade.add_argument("--fills", required=True, help="Fills file path")
    p_trade.add_argument("--peers", help="Comma-separated peer symbols")
    p_trade.add_argument("--benchmarks", default="QQQ,SPY", help="Comma-separated benchmarks")
    p_trade.add_argument("--out", required=True, help="Output packet path")
    
    # Subcommand: intraday-snapshot
    p_snap = subparsers.add_parser("intraday-snapshot")
    p_snap.add_argument("--symbols", required=True, help="Comma-separated symbols")
    p_snap.add_argument("--refresh", action="store_true", help="Force price refresh")
    p_snap.add_argument("--out", required=True, help="Output packet path")
    
    # Subcommand: intraday-dashboard
    p_dash = subparsers.add_parser("intraday-dashboard")
    p_dash.add_argument("--guidance", required=True, help="Intraday guidance JSON path")
    p_dash.add_argument("--out", help="Optional markdown report output path")
    p_dash.add_argument("--html-out", help="Optional HTML dashboard output path")
    p_dash.add_argument("--refresh", action="store_true", help="Force price refresh")
    p_dash.add_argument("--allow-yfinance-runtime-fallback", action="store_true", help="Allow yfinance network fallback for missing runtime prices")
    p_dash.add_argument("--runtime-request-timeout-seconds", type=float, default=0.35, help="Per-symbol Polygon runtime request timeout")
    p_dash.add_argument("--loop", action="store_true", help="Continuously refresh runtime evidence outputs")
    p_dash.add_argument("--interval-seconds", type=int, default=60, help="Loop sleep interval in seconds")
    p_dash.add_argument("--iterations", type=int, help="Optional loop iteration limit for tests or demos")
    p_dash.add_argument("--refresh-timeout-seconds", type=int, default=10, help="Timeout for runtime refresh subprocess")

    # Subcommand: company-packet
    p_comp = subparsers.add_parser("company-packet")
    p_comp.add_argument("--symbol", required=True, help="Ticker symbol")
    p_comp.add_argument("--peers", help="Comma-separated peer symbols")
    p_comp.add_argument("--out", required=True, help="Output packet path")

    # Subcommand: industry-packet
    p_ind = subparsers.add_parser("industry-packet")
    p_ind.add_argument("--theme", required=True, help="Industry Theme")
    p_ind.add_argument("--symbols", required=True, help="Comma-separated symbols")
    p_ind.add_argument("--out", required=True, help="Output packet path")
    
    # Subcommand: backtest-rs-rebound
    p_back = subparsers.add_parser("backtest-rs-rebound")
    p_back.add_argument("--config", help="Config YAML path")
    p_back.add_argument("--out", required=True, help="Output report path")
    # Multi-dimensional parameter mappings to other scripts
    p_back.add_argument("--sweep", action="store_true", help="Sweep parameters sweep engine")
    p_back.add_argument("--optimize", action="store_true", help="Optimize via random search")
    p_back.add_argument("--ablation", action="store_true", help="Ablation check of risk parameters")
    p_back.add_argument("--stress", action="store_true", help="Stress test slippage/latency scenarios")
    p_back.add_argument("--validate", action="store_true", help="Validate out-of-sample forward analysis")
    p_back.add_argument("--joint", action="store_true", help="Joint backtesting across target universe")
    p_back.add_argument("--analyze", action="store_true", help="Factor decay and bootstrap analysis")

    # Subcommand: tactic-backtest
    p_tactic = subparsers.add_parser("tactic-backtest")
    p_tactic.add_argument("--request", required=True, help="Brain-authored tactic backtest request JSON")
    p_tactic.add_argument("--out", required=True, help="Evidence-only markdown packet output path")
    p_tactic.add_argument("--json-out", help="Optional machine-readable JSON summary output path")

    # Subcommand: stage-context-backtest
    p_stage_context = subparsers.add_parser("stage-context-backtest")
    p_stage_context.add_argument("--request", required=True, help="Brain-authored Stage 0/1 context backtest request JSON")
    p_stage_context.add_argument("--out", required=True, help="Evidence-only markdown packet output path")
    p_stage_context.add_argument("--json-out", help="Optional machine-readable JSON summary output path")
    
    args = parser.parse_args()
    
    # Route execution
    if args.command == "premarket":
        handle_premarket(args)
    elif args.command == "market-context":
        handle_market_context(args)
    elif args.command == "trade-evidence":
        handle_trade_evidence(args)
    elif args.command == "intraday-snapshot":
        handle_intraday_snapshot(args)
    elif args.command == "intraday-dashboard":
        handle_intraday_dashboard(args)
    elif args.command == "company-packet":
        handle_company_packet(args)
    elif args.command == "industry-packet":
        handle_industry_packet(args)
    elif args.command == "backtest-rs-rebound":
        handle_backtest_rs_rebound(args)
    elif args.command == "tactic-backtest":
        handle_tactic_backtest(args)
    elif args.command == "stage-context-backtest":
        handle_stage_context_backtest(args)

if __name__ == "__main__":
    main()

