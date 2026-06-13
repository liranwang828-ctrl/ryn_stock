"""
组合健康周报模块 — portfolio_weekly.py
在 portfolio_snapshot 基础上追加周度数据和再平衡建议。

输出: findings/portfolio_weekly_{year}W{week:02d}.json

用法: python3.12 agents/portfolio_weekly.py [YYYY] [WW]
"""
import json, os, sys
from datetime import datetime, timezone, date as _date, timedelta

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ── 周数据聚合 ──────────────────────────────────────────────────────────────

def _week_dates(year: int, week: int) -> list[str]:
    """返回该周一到周五的日期字符串列表"""
    monday = _date.fromisocalendar(year, week, 1)
    return [(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]


def _aggregate_signal_accuracy(dates: list[str], syms: list[str],
                                base_dir: str = BASE) -> dict | None:
    """聚合本周各日 postmarket_summary 的 signal_accuracy 字段"""
    find_dir = os.path.join(base_dir, "findings")
    master_correct = []
    gate_correct   = []
    scene_correct  = {}
    sample = 0

    for date in dates:
        for sym in syms:
            path = os.path.join(find_dir, f"postmarket_summary_{date}_{sym}.json")
            d = _load(path)
            if not d:
                continue
            sa = d.get("signal_accuracy", {})
            sample += 1
            if sa.get("master_consensus_correct") is not None:
                master_correct.append(sa["master_consensus_correct"])
            if sa.get("gate_correct") is not None:
                gate_correct.append(sa["gate_correct"])
            scene = sa.get("actual_scene")
            correct = sa.get("pred_scene_correct")
            if scene and correct is not None:
                scene_correct.setdefault(scene, []).append(correct)

    if sample == 0:
        return None

    return {
        "master_accuracy": round(sum(master_correct) / len(master_correct), 2)
                           if master_correct else None,
        "scene_accuracy":  {s: round(sum(v) / len(v), 2) for s, v in scene_correct.items()},
        "gate_accuracy":   round(sum(gate_correct) / len(gate_correct), 2)
                           if gate_correct else None,
        "sample_size": sample,
    }


def _find_thesis_changes(dates: list[str], syms: list[str],
                          base_dir: str = BASE) -> list[dict]:
    """读 postmarket_summary snapshot_thesis_status，发现论点状态变化"""
    find_dir = os.path.join(base_dir, "findings")
    changes = []
    for sym in syms:
        prev_status = None
        for date in dates:
            path = os.path.join(find_dir, f"postmarket_summary_{date}_{sym}.json")
            d = _load(path)
            if not d:
                continue
            status = d.get("snapshot_thesis_status")
            if status and prev_status and status != prev_status:
                changes.append({"sym": sym, "from": prev_status, "to": status, "date": date})
            if status:
                prev_status = status
    return changes


def _build_week_performance(snapshot: dict, dates: list[str],
                             base_dir: str = BASE) -> list[dict]:
    """构建 week_performance（基于 position 当前价格和本周首尾日）"""
    find_dir = os.path.join(base_dir, "findings")
    result = []
    for pos in snapshot.get("positions_detail", []):
        sym = pos.get("sym", "")
        cur = pos.get("cur_price")
        dist_stop = pos.get("dist_to_stop_pct")
        dist_tgt  = pos.get("dist_to_target_pct")

        # 本周开/收盘：用当前价格近似（真实值需 yfinance 历史，此处做简单近似）
        week_ret_pct = None   # 需要 yfinance 历史，保留 null

        vs_target = "below"
        if dist_tgt is not None:
            if dist_tgt > 2:
                vs_target = "below"
            elif dist_tgt < -2:
                vs_target = "above"
            else:
                vs_target = "at"

        vs_stop = "safe"
        if dist_stop is not None:
            if dist_stop < 0:
                vs_stop = "breached"
            elif dist_stop < 5:
                vs_stop = "warning"

        result.append({
            "sym": sym,
            "week_open": None,   # yfinance 依赖，暂 null
            "week_close": cur,
            "week_ret_pct": week_ret_pct,
            "vs_target": vs_target,
            "vs_stop": vs_stop,
            "plan_followed": "na",
        })
    return result


def build_exposure_trend(year: int, week: int, totals: dict,
                          base_dir: str = BASE) -> dict:
    """读取上周 portfolio_weekly，构建 exposure_trend"""
    find_dir = os.path.join(base_dir, "findings")
    prev_week = week - 1
    prev_year = year
    if prev_week == 0:
        prev_week = 52
        prev_year = year - 1
    prev_path = os.path.join(find_dir, f"portfolio_weekly_{prev_year}W{prev_week:02d}.json")
    prev = _load(prev_path) if os.path.exists(prev_path) else {}

    curr_lev = totals.get("leverage_ratio")
    curr_exp = totals.get("total_exposure")
    prev_lev = (prev.get("totals") or {}).get("leverage_ratio") if prev else None
    prev_exp = (prev.get("totals") or {}).get("total_exposure") if prev else None

    chg = None
    if curr_exp is not None and prev_exp and prev_exp > 0:
        chg = round((curr_exp - prev_exp) / prev_exp * 100, 2)

    return {
        "leverage_ratio_prev": prev_lev,
        "leverage_ratio_curr": curr_lev,
        "total_exposure_prev": prev_exp,
        "total_exposure_curr": curr_exp,
        "exposure_chg_pct":   chg,
    }


def generate_rebalancing_suggestions(snapshot: dict) -> list[dict]:
    """规则驱动生成再平衡建议"""
    suggs = []
    totals = snapshot.get("totals", {})
    sector = snapshot.get("sector", {})
    corr   = snapshot.get("correlation", {})
    positions = snapshot.get("positions_detail", [])
    strategic = snapshot.get("strategic_alignment", {})

    lev    = totals.get("leverage_ratio", 0.0) or 0.0
    top_s  = sector.get("top_sector_pct", 0.0) or 0.0
    top_c  = corr.get("top_pair_value", 0.0) or 0.0
    pair   = corr.get("top_pair", [])

    if lev > 2.5:
        suggs.append({"type": "reduce_leverage", "priority": "high",
                      "description": f"总杠杆 {lev:.1f}x 超过安全线，建议降至 2.0x 以下",
                      "proposed_value": {"target_ratio": 2.0, "note": "降杠杆"},
                      "confirmed": None, "applied_at": None, "applied_to": None})
    if top_s > 70:
        suggs.append({"type": "diversify_sector", "priority": "high",
                      "description": f"{sector.get('top_sector','?')} 占比 {top_s:.0f}%，建议分散",
                      "proposed_value": {"overweight_sector": sector.get("top_sector",""),
                                         "overweight_pct": top_s},
                      "confirmed": None, "applied_at": None, "applied_to": None})
    for pos in positions:
        dist = pos.get("dist_to_stop_pct")
        if dist is not None and dist < 3:
            suggs.append({"type": "reduce_position", "priority": "high",
                          "description": f"{pos['sym']} 距止损 {dist:.1f}%，建议减仓",
                          "proposed_value": {"sym": pos["sym"], "reduce_pct": 30},
                          "confirmed": None, "applied_at": None, "applied_to": None})
    if top_c > 0.85 and pair:
        suggs.append({"type": "reduce_position", "priority": "medium",
                      "description": f"{pair[0]}/{pair[1]} 相关性 {top_c:.2f}，建议减少一方",
                      "proposed_value": {"sym": pair[0], "reduce_pct": 20},
                      "confirmed": None, "applied_at": None, "applied_to": None})
    for alert in strategic.get("memo_expiry_alerts", []):
        suggs.append({"type": "memo_refresh", "priority": "medium",
                      "description": f"{alert['sym']} memo 还剩 {alert.get('days_left','?')} 天",
                      "proposed_value": {"sym": alert["sym"],
                                         "days_left": alert.get("days_left")},
                      "confirmed": None, "applied_at": None, "applied_to": None})
    for mis in strategic.get("stance_misalign", []):
        suggs.append({"type": "reduce_position", "priority": "medium",
                      "description": f"{mis['sym']} 战略={mis['strategic_stance']}，建议减仓",
                      "proposed_value": {"sym": mis["sym"], "reduce_pct": 30},
                      "confirmed": None, "applied_at": None, "applied_to": None})
    if 2.0 < lev <= 2.5:
        suggs.append({"type": "reduce_leverage", "priority": "low",
                      "description": f"总杠杆 {lev:.1f}x，建议关注",
                      "proposed_value": {"target_ratio": 2.0, "note": "关注杠杆"},
                      "confirmed": None, "applied_at": None, "applied_to": None})
    return suggs


# ── 主函数 ──────────────────────────────────────────────────────────────────

def build_portfolio_weekly(date: str, year: int | None = None,
                            week: int | None = None,
                            base_dir: str = BASE) -> dict:
    """在 portfolio_snapshot 基础上追加周度字段"""
    if year is None or week is None:
        d = _date.fromisoformat(date)
        year, week = d.isocalendar()[:2]

    find_dir = os.path.join(base_dir, "findings")

    # 读取当日 snapshot（基础）
    snap_path = os.path.join(find_dir, f"portfolio_snapshot_{date}.json")
    snapshot  = _load(snap_path)
    if not snapshot:
        return {}

    pos_data = _load(os.path.join(base_dir, "config", "positions.json"))
    excluded = set(pos_data.get("_excluded", []))
    all_syms = [s for s in pos_data.get("positions", {}).keys() if s not in excluded]

    dates = _week_dates(year, week)

    week_perf    = _build_week_performance(snapshot, dates, base_dir)
    thesis_chg   = _find_thesis_changes(dates, all_syms, base_dir)
    sig_acc_week = _aggregate_signal_accuracy(dates, all_syms, base_dir)
    exp_trend    = build_exposure_trend(year, week, snapshot.get("totals", {}), base_dir)
    rebalancing  = generate_rebalancing_suggestions(snapshot)

    return {
        **snapshot,
        "trigger": "weekly",
        "week_performance":     week_perf,
        "thesis_changes":       thesis_chg,
        "signal_accuracy_week": sig_acc_week,
        "exposure_trend":       exp_trend,
        "rebalancing_suggestions": rebalancing,
        "llm_summary": "",   # 存根，待 LLM 接入
    }


def write_portfolio_weekly(year: int, week: int, data: dict,
                            base_dir: str = BASE) -> str:
    find_dir = os.path.join(base_dir, "findings")
    os.makedirs(find_dir, exist_ok=True)
    path = os.path.join(find_dir, f"portfolio_weekly_{year}W{week:02d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def main():
    today = _date.today()
    year, week, _ = today.isocalendar()
    date_str = today.strftime("%Y-%m-%d")
    print(f"\n组合健康周报 {year}W{week:02d}\n")
    data = build_portfolio_weekly(date_str, year, week)
    if data:
        path = write_portfolio_weekly(year, week, data)
        print(f"  输出: {os.path.basename(path)}")
        suggs = data.get("rebalancing_suggestions", [])
        print(f"  再平衡建议: {len(suggs)} 条")
    else:
        print("  无 portfolio_snapshot，请先运行 portfolio_snapshot.py")


if __name__ == "__main__":
    main()
