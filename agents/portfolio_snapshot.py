"""
组合健康日快照模块 — portfolio_snapshot.py
包装 portfolio_risk_agent.compute_portfolio_risk()，输出标准化 JSON。

输出: findings/portfolio_snapshot_{date}.json

用法: python3.12 agents/portfolio_snapshot.py [on_demand|daily_auto|weekly_sub]
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.portfolio_risk_agent import compute_portfolio_risk

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")
CFG_DIR  = os.path.join(BASE, "config")


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ── 规则引擎 ────────────────────────────────────────────────────────────────

def build_warnings(
    totals: dict, sector: dict, correlation: dict,
    positions: list[dict], strategic: dict,
) -> list[dict]:
    """规则驱动生成 warnings（优先级从高到低，全量扫描不短路）"""
    warns = []
    lev   = totals.get("leverage_ratio", 0.0) or 0.0
    top_s = sector.get("top_sector_pct", 0.0) or 0.0
    hhi   = sector.get("hhi", 0.0) or 0.0
    top_c = correlation.get("top_pair_value", 0.0) or 0.0
    pair  = correlation.get("top_pair", ["?", "?"])

    # High
    if lev > 2.5:
        warns.append({"level": "high", "code": "leverage_excess",
                      "msg": f"总杠杆 {lev:.1f}x 超过 2.5x 安全线"})
    if top_s > 70:
        warns.append({"level": "high", "code": "sector_concentrated",
                      "msg": f"{sector.get('top_sector','?')} 板块占比 {top_s:.0f}%，集中度过高"})
    for pos in positions:
        dist = pos.get("dist_to_stop_pct")
        if dist is not None and dist < 3:
            warns.append({"level": "high", "code": "approaching_stop",
                          "msg": f"{pos['sym']} 距硬止损仅 {dist:.1f}%，需关注"})

    # Medium
    if top_c > 0.85:
        warns.append({"level": "medium", "code": "high_correlation",
                      "msg": f"{pair[0]}/{pair[1]} 相关性 {top_c:.2f}，实际敞口被低估"})
    for alert in strategic.get("memo_expiry_alerts", []):
        d = alert.get("days_left")
        if d is not None and d < 7:
            warns.append({"level": "medium", "code": "memo_expiring",
                          "msg": f"{alert['sym']} strategic_memo 还剩 {d} 天有效期"})
    for mis in strategic.get("stance_misalign", []):
        warns.append({"level": "medium", "code": "stance_mismatch",
                      "msg": f"{mis['sym']} 战略建议 {mis['strategic_stance']} 但仍持有"})

    # Low
    if 2.0 < lev <= 2.5:
        warns.append({"level": "low", "code": "leverage_warning",
                      "msg": f"总杠杆 {lev:.1f}x，建议关注"})
    if hhi > 0.25:
        warns.append({"level": "low", "code": "hhi_high",
                      "msg": f"HHI={hhi:.2f}，组合集中度偏高"})

    return warns


# ── 数据增强 ────────────────────────────────────────────────────────────────

def _enhance_positions(details: list[dict], date: str, base_dir: str) -> list[dict]:
    """为每个持仓补充 dist_to_stop/target/thesis_status/days_held"""
    find_dir = os.path.join(base_dir, "findings")
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    positions = pos_data.get("positions", {})
    excluded  = set(pos_data.get("_excluded", []))

    # 读 exit_decision 获取 hard_stop
    exit_dec = _load(os.path.join(find_dir, f"exit_decision_{date}.json"))
    exit_pos = exit_dec.get("positions", {})

    # 读 order_sheet 获取 target_price
    order_sh = _load(os.path.join(find_dir, f"order_sheet_{date}.json"))
    order_syms = order_sh.get("symbols", {})

    today = _date.fromisoformat(date)
    result = []
    for d in details:
        sym = d.get("sym", "")
        if sym in excluded:
            continue
        pos = positions.get(sym, {})
        cur = d.get("cur_price", 0.0) or 0.0

        hard_stop = exit_pos.get(sym, {}).get("hard_stop")
        target    = order_syms.get(sym, {}).get("target_price")

        dist_stop = None
        if hard_stop and cur > 0:
            dist_stop = round((cur - hard_stop) / cur * 100, 2)
        dist_tgt = None
        if target and cur > 0:
            dist_tgt = round((target - cur) / cur * 100, 2)

        entry_date_str = pos.get("date", date)
        try:
            days_held = (today - _date.fromisoformat(entry_date_str)).days
        except Exception:
            days_held = 0

        cost = d.get("cost", 0.0) or 0.0
        pnl_pct = round((cur - cost) / cost * 100, 2) if cost > 0 else 0.0

        result.append({
            **d,
            "unrealized_pnl_pct": pnl_pct,
            "dist_to_stop_pct":   dist_stop,
            "dist_to_target_pct": dist_tgt,
            "thesis_status":      pos.get("thesis_status"),
            "days_held":          days_held,
        })
    return result


def _build_strategic_alignment(base_dir: str, excluded: set) -> dict:
    """读 strategic_memo 文件，构建 strategic_alignment"""
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    positions = pos_data.get("positions", {})
    alerts, misaligns = [], []

    for sym, pos in positions.items():
        if sym in excluded:
            continue
        memo_path = os.path.join(base_dir, f"strategic_memo_{sym}.json")
        memo = _load(memo_path)
        if not memo:
            continue

        valid_until = memo.get("outlook", {}).get("valid_until")
        days_left = None
        if valid_until and valid_until not in ("next_earnings", "next_catalyst_event"):
            try:
                vu = _date.fromisoformat(valid_until)
                days_left = (vu - _date.today()).days
            except Exception:
                pass
        if days_left is not None and days_left < 7:
            alerts.append({"sym": sym, "valid_until": valid_until, "days_left": days_left})

        stance = memo.get("synthesis", {}).get("strategic_stance", "")
        thesis = pos.get("thesis_status", "intact")
        if stance in {"reduce", "exit_ready", "avoid"} and thesis in {"intact", "weakening"}:
            misaligns.append({"sym": sym, "strategic_stance": stance,
                               "current_situation": "still_holding",
                               "note": f"strategic={stance}, thesis={thesis}"})

    return {"memo_expiry_alerts": alerts, "stance_misalign": misaligns}


# ── 主函数 ──────────────────────────────────────────────────────────────────

def build_portfolio_snapshot(date: str, trigger: str = "on_demand",
                              base_dir: str = BASE) -> dict:
    """构建 portfolio_snapshot dict（主函数）"""
    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    excluded = set(pos_data.get("_excluded", []))

    risk = compute_portfolio_risk()   # 可能为 None

    if not risk:
        positions_detail = []
        totals = {"total_value": 0.0, "total_exposure": 0.0, "leverage_ratio": 0.0,
                  "var_5pct_loss": 0.0, "var_5pct_pct": 0.0, "total_unrealized_pnl_pct": 0.0}
        sector = {"concentration": {}, "top_sector": None, "top_sector_pct": 0.0, "hhi": 0.0}
        correlation = {"matrix": {}, "top_pair": [], "top_pair_value": 0.0, "high_corr_count": 0}
        strategic = {"memo_expiry_alerts": [], "stance_misalign": []}
        warnings = []
    else:
        raw_detail = risk.get("positions_detail", [])
        positions_detail = _enhance_positions(raw_detail, date, base_dir)

        total_value    = risk.get("total_value", 0.0) or 0.0
        total_exposure = risk.get("total_exposure", 0.0) or 0.0
        lev_ratio      = risk.get("leverage_ratio", 1.0) or 1.0
        var_loss       = risk.get("var_5pct_loss", 0.0) or 0.0
        var_pct        = round(var_loss / total_value * 100, 2) if total_value > 0 else 0.0

        # 加权 PnL
        pnl_sum = sum(
            d.get("unrealized_pnl_pct", 0.0) * d.get("market_value", 0.0)
            for d in positions_detail
        )
        total_pnl = round(pnl_sum / total_value, 2) if total_value > 0 else 0.0

        totals = {
            "total_value": round(total_value, 2),
            "total_exposure": round(total_exposure, 2),
            "leverage_ratio": round(lev_ratio, 2),
            "var_5pct_loss": round(var_loss, 2),
            "var_5pct_pct": var_pct,
            "total_unrealized_pnl_pct": total_pnl,
        }

        sector_pct = risk.get("sector_pct", {})
        top_sector = max(sector_pct, key=sector_pct.get) if sector_pct else None
        top_sector_pct = sector_pct.get(top_sector, 0.0) if top_sector else 0.0
        hhi = round(sum((v / 100) ** 2 for v in sector_pct.values()), 4)

        sector = {
            "concentration": sector_pct,
            "top_sector": top_sector,
            "top_sector_pct": top_sector_pct,
            "hhi": hhi,
        }

        corr_matrix = risk.get("corr_matrix", {})
        top_pair_raw = risk.get("top_corr_pair", ())
        top_pair_val = risk.get("top_corr_value", 0.0) or 0.0
        high_corr_count = sum(
            1 for syms in corr_matrix.values()
            for v in syms.values() if v is not None and abs(v) > 0.8
        ) // 2   # 对称矩阵除以 2

        correlation = {
            "matrix": corr_matrix,
            "top_pair": list(top_pair_raw) if top_pair_raw else [],
            "top_pair_value": round(top_pair_val, 3),
            "high_corr_count": high_corr_count,
        }

        strategic = _build_strategic_alignment(base_dir, excluded)
        warnings  = build_warnings(totals, sector, correlation, positions_detail, strategic)

    return {
        "date":               date,
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "trigger":            trigger,
        "positions_detail":   positions_detail,
        "totals":             totals,
        "sector":             sector,
        "correlation":        correlation,
        "strategic_alignment": strategic,
        "warnings":           warnings,
    }


def write_portfolio_snapshot(date: str, data: dict, base_dir: str = BASE) -> str:
    find_dir = os.path.join(base_dir, "findings")
    os.makedirs(find_dir, exist_ok=True)
    path = os.path.join(find_dir, f"portfolio_snapshot_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def main(trigger: str = "on_demand"):
    date_str = _date.today().strftime("%Y-%m-%d")
    print(f"\n组合健康快照 {date_str} （trigger={trigger}）\n")
    data = build_portfolio_snapshot(date_str, trigger)
    path = write_portfolio_snapshot(date_str, data)
    warns = [w for w in data["warnings"] if w["level"] == "high"]
    print(f"  杠杆: {data['totals']['leverage_ratio']:.1f}x")
    print(f"  高优先警告: {len(warns)} 条")
    print(f"  输出: {os.path.basename(path)}")


if __name__ == "__main__":
    trigger_arg = sys.argv[1] if len(sys.argv) > 1 else "on_demand"
    main(trigger_arg)
