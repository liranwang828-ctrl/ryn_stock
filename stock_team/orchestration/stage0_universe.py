from __future__ import annotations

import json
import os
from pathlib import Path

from stock_team.utils.workspace_paths import investing_os_home


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _parse_symbol_list(raw_value) -> list[str]:
    values = raw_value if isinstance(raw_value, list) else raw_value.split(",") if isinstance(raw_value, str) else []
    result = []
    seen = set()
    for item in values:
        symbol = str(item).upper().strip()
        if symbol and symbol not in seen:
            seen.add(symbol)
            result.append(symbol)
    return result


def _infer_position_theme(position: dict) -> str:
    text = " ".join(str(position.get(key) or "") for key in ("position_type", "note", "thesis")).lower()
    for token, theme in (
        ("ai_power", "power"),
        ("power", "power"),
        ("memory", "memory"),
        ("cloud", "cloud"),
        ("optical", "optical"),
        ("semiconductor", "semiconductors"),
        ("gpu", "semiconductors"),
        ("ai", "ai_infrastructure"),
    ):
        if token in text:
            return theme
    return "user_focus"


def _latest_journal_path(investing_root: Path) -> str:
    journals_dir = investing_root / "wiki" / "journals"
    if not journals_dir.is_dir():
        return ""
    candidates = sorted(journals_dir.glob("*.md"), reverse=True)
    return str(candidates[0]) if candidates else ""


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def build_stage0_universe_document(
    *,
    base_dir: str | Path,
    runtime_root: str | Path,
    market_date: str,
    session_id: str,
) -> tuple[Path, str]:
    base_dir = Path(base_dir)
    runtime_root = Path(runtime_root)
    investing_root = Path(investing_os_home(base_dir))
    inputs_dir = runtime_root / "inputs"
    universe_path = inputs_dir / f"{session_id}-stage0-universe.json"
    journal_path = _latest_journal_path(investing_root)
    snapshot = _load_json(inputs_dir / f"{session_id}-pre-market-snapshot.json", {})
    snapshot_symbols = _parse_symbol_list(snapshot.get("focus_symbols"))
    snapshot_themes = _parse_symbol_list(snapshot.get("themes"))
    positions_payload = _load_json(base_dir / "config" / "positions.json", {})
    current_positions = positions_payload.get("positions") if isinstance(positions_payload, dict) else {}
    if not isinstance(current_positions, dict):
        current_positions = {}

    universe_rows = []
    seen_symbols = set()
    for symbol in snapshot_symbols:
        position = current_positions.get(symbol) if isinstance(current_positions.get(symbol), dict) else {}
        is_position = bool(position)
        universe_rows.append({
            "symbol": symbol,
            "role": "current_position" if is_position else "watchlist",
            "theme": _infer_position_theme(position) if is_position else (snapshot_themes[0].lower() if snapshot_themes else "user_focus"),
            "research_status": str(position.get("thesis_status") or "pending").strip() if is_position else "pending",
            "source": "current_positions+snapshot_focus" if is_position else "snapshot_focus_symbols",
            "brain_note": "Imported from current holdings and explicit daily focus." if is_position else "Explicit daily focus symbol from pre-market snapshot.",
        })
        seen_symbols.add(symbol)

    for raw_symbol, position in current_positions.items():
        symbol = str(raw_symbol).upper().strip()
        if not symbol or symbol in seen_symbols or not isinstance(position, dict):
            continue
        universe_rows.append({
            "symbol": symbol,
            "role": "current_position",
            "theme": _infer_position_theme(position),
            "research_status": str(position.get("thesis_status") or "needs_review").strip(),
            "source": "current_positions",
            "brain_note": "Live IBKR position added to the daily observation universe.",
        })
        seen_symbols.add(symbol)

    universe_document = {
        "artifact_type": "pre_market_universe",
        "version": "1.0",
        "date": market_date,
        "created_by": "investing-os-dashboard",
        "purpose": "Dashboard-generated minimum Stage 0 universe. This is not a trading permission list.",
        "source_inputs": {
            "positions": [{
                "source": "ibkr_live_api" if current_positions else "dashboard_runtime_placeholder",
                "as_of_et": f"{market_date}T08:00:00-04:00",
                "symbols": sorted(seen_symbols),
                "notes": "Derived from local live-synced positions.json for Stage 0 dashboard bootstrap." if current_positions else "No live broker position snapshot was attached from the dashboard runtime.",
            }],
            "prior_review": {
                "path": os.path.relpath(journal_path, investing_root).replace("\\", "/") if journal_path else "",
                "status": "not_attached" if not journal_path else "reviewed_for_stage0_input",
                "key_risks": [],
            },
            "cognition_state": {"permission_basis": "normal", "active_risks": []},
        },
        "permission_state_before_open": "Yellow",
        "forbidden_actions": [
            "new_short_term_trade_without_plan",
            "new_leveraged_product_trade_without_explicit_brain_approval",
            "loss_repair_reentry",
        ],
        "selection_policy": {
            "allowed_sources": [
                "current_positions",
                "active_watchlist",
                "researched_or_explicitly_approved_candidates",
                "market_or_sector_proxies",
            ],
            "forbidden_interpretations": [
                "focus_pool",
                "trade_permission",
                "buy_sell_hold_recommendation",
                "symbol_selection_by_stock_team",
            ],
        },
        "themes": snapshot_themes or ["semiconductors", "ai_infrastructure", "memory", "cloud", "optical"],
        "universe": universe_rows,
        "proxies": [
            {
                "symbol": "QQQ",
                "role": "market_proxy",
                "theme": "market_context",
                "research_status": "proxy",
                "source": "proxy",
                "brain_note": "Nasdaq growth proxy for Stage 0 market context.",
            },
            {
                "symbol": "SPY",
                "role": "market_proxy",
                "theme": "market_context",
                "research_status": "proxy",
                "source": "proxy",
                "brain_note": "Broad market proxy for Stage 0 market context.",
            },
        ],
        "forbidden_sections_absent": [
            "buy_sell_hold_recommendation",
            "trading_permission_state",
            "symbol_selection_recommendation",
            "final_thesis_adoption",
            "psychological_interpretation",
        ],
    }
    _write_json_atomic(universe_path, universe_document)
    return universe_path, journal_path
