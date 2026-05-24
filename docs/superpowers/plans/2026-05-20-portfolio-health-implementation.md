# portfolio-health 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/portfolio_snapshot.py` 和 `agents/portfolio_weekly.py`，将 `portfolio_risk_agent.py` 的计算结果包装为标准化 JSON 输出（portfolio_snapshot_{date}.json + portfolio_weekly_{year}W{week}.json），包含 warnings 规则引擎和再平衡建议。

**Architecture:** `portfolio_snapshot.py` 调用现有 `compute_portfolio_risk()`，追加 per-position 增强字段（stop/target/thesis_status/days_held）、strategic_alignment、warnings；`portfolio_weekly.py` 在 snapshot 基础上聚合周数据和建议。两个文件均为纯函数 + 文件 I/O，可单元测试（yfinance 调用通过 mock 绕过）。

**Tech Stack:** Python 3.12, json, yfinance（通过现有 portfolio_risk_agent 间接使用，测试中 mock）

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/portfolio_snapshot.py` | 新建 | 日快照：包装 compute_portfolio_risk + 规则引擎 |
| `agents/portfolio_weekly.py` | 新建 | 周报：聚合周数据 + 再平衡建议 |
| `tests/test_portfolio_health.py` | 新建 | 单元测试，mock yfinance |

---

## Task 1：portfolio_snapshot.py — 日快照

**Files:**
- Create: `agents/portfolio_snapshot.py`
- Create: `tests/test_portfolio_health.py`

---

- [ ] **Step 1.1：写测试**

```python
# tests/test_portfolio_health.py
import sys, os, json, datetime
sys.path.insert(0, os.path.expanduser("~/stock_team"))
from unittest.mock import patch


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _mock_risk_result():
    """compute_portfolio_risk() 的最小合法返回值"""
    return {
        "positions_detail": [
            {
                "sym": "NVDA", "underlying": "NVDA", "leverage": 1,
                "shares": 10, "cost": 180.0,
                "cur_price": 200.0, "market_value": 2000.0, "net_exposure": 2000.0,
                "beta": 1.2, "var_5pct_loss": 120.0,
            }
        ],
        "total_value": 2000.0, "total_exposure": 2000.0, "leverage_ratio": 1.0,
        "var_5pct_loss": 120.0, "var_5pct_pct": 6.0,
        "sector_pct": {"Tech": 100.0},
        "sector_exposure": {"Tech": 2000.0},
        "top_corr_pair": ("NVDA", "AAPL"),
        "top_corr_value": 0.7,
        "corr_matrix": {"NVDA": {"AAPL": 0.7}},
        "warnings": [],
    }


def test_build_warnings_leverage_excess():
    """leverage_ratio > 2.5 → high warning"""
    from agents.portfolio_snapshot import build_warnings
    totals = {"leverage_ratio": 2.8, "var_5pct_pct": 10.0}
    sector = {"top_sector_pct": 50.0, "top_sector": "Tech", "hhi": 0.2}
    correlation = {"top_pair_value": 0.7, "top_pair": ["A", "B"], "high_corr_count": 0}
    positions = []
    strategic = {"memo_expiry_alerts": [], "stance_misalign": []}
    warns = build_warnings(totals, sector, correlation, positions, strategic)
    codes = [w["code"] for w in warns]
    assert "leverage_excess" in codes
    assert any(w["level"] == "high" for w in warns if w["code"] == "leverage_excess")


def test_build_warnings_approaching_stop():
    """dist_to_stop_pct < 3 → high approaching_stop warning"""
    from agents.portfolio_snapshot import build_warnings
    totals = {"leverage_ratio": 1.0, "var_5pct_pct": 5.0}
    sector = {"top_sector_pct": 40.0, "top_sector": "Tech", "hhi": 0.15}
    correlation = {"top_pair_value": 0.5, "top_pair": ["A", "B"], "high_corr_count": 0}
    positions = [{"sym": "NVDA", "dist_to_stop_pct": 1.5}]
    strategic = {"memo_expiry_alerts": [], "stance_misalign": []}
    warns = build_warnings(totals, sector, correlation, positions, strategic)
    codes = [w["code"] for w in warns]
    assert "approaching_stop" in codes


def test_build_warnings_no_warning():
    """一切正常 → 空警告列表"""
    from agents.portfolio_snapshot import build_warnings
    totals = {"leverage_ratio": 1.0, "var_5pct_pct": 5.0}
    sector = {"top_sector_pct": 40.0, "top_sector": "Tech", "hhi": 0.15}
    correlation = {"top_pair_value": 0.5, "top_pair": ["A", "B"], "high_corr_count": 0}
    positions = [{"sym": "NVDA", "dist_to_stop_pct": 10.0}]
    strategic = {"memo_expiry_alerts": [], "stance_misalign": []}
    warns = build_warnings(totals, sector, correlation, positions, strategic)
    assert warns == []


def test_build_portfolio_snapshot_schema(tmp_path):
    """build_portfolio_snapshot 返回所有顶层 key"""
    from agents.portfolio_snapshot import build_portfolio_snapshot
    # 写入 positions.json（只需最小结构）
    pos_file = tmp_path / "config" / "positions.json"
    _write(str(pos_file), {
        "positions": {"NVDA": {
            "cost": 180.0, "shares": 10, "date": "2026-05-12",
            "thesis_status": "intact",
        }},
        "_excluded": [],
    })

    mock_result = _mock_risk_result()
    with patch("agents.portfolio_snapshot.compute_portfolio_risk",
               return_value=mock_result):
        snapshot = build_portfolio_snapshot(
            date="2026-05-20", trigger="on_demand", base_dir=str(tmp_path))

    required = {"date", "generated_at", "trigger", "positions_detail",
                "totals", "sector", "correlation", "strategic_alignment", "warnings"}
    assert required == set(snapshot.keys()), f"缺少: {required - set(snapshot.keys())}"
    assert snapshot["trigger"] == "on_demand"
    assert isinstance(snapshot["positions_detail"], list)
    assert isinstance(snapshot["warnings"], list)


def test_write_portfolio_snapshot_creates_file(tmp_path):
    """write_portfolio_snapshot 生成 JSON 文件"""
    from agents.portfolio_snapshot import build_portfolio_snapshot, write_portfolio_snapshot
    pos_file = tmp_path / "config" / "positions.json"
    _write(str(pos_file), {
        "positions": {"NVDA": {"cost": 180.0, "shares": 10, "date": "2026-05-12",
                                "thesis_status": "intact"}},
        "_excluded": [],
    })
    import pathlib
    mock_result = _mock_risk_result()
    with patch("agents.portfolio_snapshot.compute_portfolio_risk",
               return_value=mock_result):
        data = build_portfolio_snapshot("2026-05-20", "on_demand", base_dir=str(tmp_path))
    path = write_portfolio_snapshot("2026-05-20", data, base_dir=str(tmp_path))
    assert pathlib.Path(path).exists()
    d = json.loads(pathlib.Path(path).read_text())
    assert d["trigger"] == "on_demand"
```

- [ ] **Step 1.2：运行测试，确认 FAIL（ImportError）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_portfolio_health.py -v 2>&1 | head -15
```

- [ ] **Step 1.3：创建 agents/portfolio_snapshot.py**

```python
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

BASE     = os.path.expanduser("~/stock_team")
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

        result.append({
            **d,
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
    print(f"  ✅ {os.path.basename(path)}")


if __name__ == "__main__":
    trigger_arg = sys.argv[1] if len(sys.argv) > 1 else "on_demand"
    main(trigger_arg)
```

- [ ] **Step 1.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_portfolio_health.py -v
```

预期：全部 PASS

- [ ] **Step 1.5：Commit**

```bash
git add agents/portfolio_snapshot.py tests/test_portfolio_health.py
git commit -m "feat: add portfolio_snapshot.py — daily health snapshot with warnings"
```

---

## Task 2：portfolio_weekly.py — 周报

**Files:**
- Create: `agents/portfolio_weekly.py`
- Test: `tests/test_portfolio_health.py`（追加）

---

- [ ] **Step 2.1：追加测试**

```python
def test_generate_rebalancing_suggestions_high_leverage():
    """leverage_ratio > 2.5 → reduce_leverage high"""
    from agents.portfolio_weekly import generate_rebalancing_suggestions
    snapshot = {
        "totals": {"leverage_ratio": 2.8, "total_exposure": 50000.0},
        "sector": {"top_sector_pct": 50.0, "top_sector": "Tech"},
        "correlation": {"top_pair": ["NVDA", "AAPL"], "top_pair_value": 0.7},
        "positions_detail": [{"sym": "NVDA", "dist_to_stop_pct": 10.0}],
        "strategic_alignment": {"memo_expiry_alerts": [], "stance_misalign": []},
    }
    suggs = generate_rebalancing_suggestions(snapshot)
    types = [s["type"] for s in suggs]
    assert "reduce_leverage" in types
    assert any(s["priority"] == "high" for s in suggs if s["type"] == "reduce_leverage")


def test_generate_rebalancing_suggestions_clean():
    """一切正常 → 空建议列表"""
    from agents.portfolio_weekly import generate_rebalancing_suggestions
    snapshot = {
        "totals": {"leverage_ratio": 1.2, "total_exposure": 10000.0},
        "sector": {"top_sector_pct": 40.0, "top_sector": "Tech"},
        "correlation": {"top_pair": ["NVDA", "AAPL"], "top_pair_value": 0.5},
        "positions_detail": [{"sym": "NVDA", "dist_to_stop_pct": 10.0}],
        "strategic_alignment": {"memo_expiry_alerts": [], "stance_misalign": []},
    }
    suggs = generate_rebalancing_suggestions(snapshot)
    assert suggs == []


def test_build_exposure_trend_first_week(tmp_path):
    """首周无上周文件 → null 字段，不报错"""
    from agents.portfolio_weekly import build_exposure_trend
    totals = {"leverage_ratio": 1.5, "total_exposure": 20000.0}
    trend = build_exposure_trend(2026, 21, totals, base_dir=str(tmp_path))
    assert trend["leverage_ratio_prev"] is None
    assert trend["exposure_chg_pct"] is None
    assert trend["leverage_ratio_curr"] == 1.5


def test_build_portfolio_weekly_schema(tmp_path):
    """build_portfolio_weekly 返回 snapshot + 额外字段"""
    from agents.portfolio_weekly import build_portfolio_weekly
    # 写入 portfolio_snapshot_today.json
    date = "2026-05-20"
    snapshot = {
        "date": date, "generated_at": "2026-05-20T16:00:00Z",
        "trigger": "weekly_sub",
        "positions_detail": [{"sym": "NVDA", "dist_to_stop_pct": 10.0,
                               "cur_price": 200.0}],
        "totals": {"leverage_ratio": 1.2, "total_exposure": 10000.0},
        "sector": {"top_sector_pct": 60.0, "top_sector": "Tech"},
        "correlation": {"top_pair": ["NVDA", "A"], "top_pair_value": 0.5},
        "strategic_alignment": {"memo_expiry_alerts": [], "stance_misalign": []},
        "warnings": [],
    }
    snap_path = tmp_path / "findings" / f"portfolio_snapshot_{date}.json"
    snap_path.parent.mkdir(parents=True)
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False))

    # 写入 positions.json
    pos_file = tmp_path / "config" / "positions.json"
    pos_file.parent.mkdir(parents=True)
    pos_file.write_text(json.dumps({
        "positions": {"NVDA": {"cost": 180.0, "shares": 10, "date": "2026-05-12",
                                "thesis_status": "intact"}},
        "_excluded": [],
    }))

    weekly = build_portfolio_weekly(date, year=2026, week=21, base_dir=str(tmp_path))
    # 应包含 snapshot 所有字段 + 额外字段
    assert "week_performance" in weekly
    assert "thesis_changes" in weekly
    assert "signal_accuracy_week" in weekly
    assert "exposure_trend" in weekly
    assert "rebalancing_suggestions" in weekly
    assert "llm_summary" in weekly
```

- [ ] **Step 2.2：运行，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_portfolio_health.py -k "rebalancing or exposure or weekly" -v
```

- [ ] **Step 2.3：创建 agents/portfolio_weekly.py**

```python
"""
组合健康周报模块 — portfolio_weekly.py
在 portfolio_snapshot 基础上追加周度数据和再平衡建议。

输出: findings/portfolio_weekly_{year}W{week:02d}.json

用法: python3.12 agents/portfolio_weekly.py [YYYY] [WW]
"""
import json, os, sys
from datetime import datetime, timezone, date as _date, timedelta

BASE     = os.path.expanduser("~/stock_team")
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

        # 本周开/收盘：用当前价格近似（真实值需 yfinance，此处做简单近似）
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
        print(f"  ✅ {os.path.basename(path)}")
        suggs = data.get("rebalancing_suggestions", [])
        print(f"  再平衡建议: {len(suggs)} 条")
    else:
        print("  ❌ 无 portfolio_snapshot，请先运行 portfolio_snapshot.py")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_portfolio_health.py -v
```

预期：全部 PASS

- [ ] **Step 2.5：Commit**

```bash
git add agents/portfolio_weekly.py tests/test_portfolio_health.py
git commit -m "feat: add portfolio_weekly.py — weekly report with rebalancing suggestions"
```

---

## Task 3：CHANGELOG 更新

- [ ] **Step 3.1：更新 CHANGELOG.md**

顶部追加：

```
## 2026-05-20 portfolio-health 实施完成

### 新建文件
- `agents/portfolio_snapshot.py` — 日快照：warnings 规则引擎 + strategic_alignment + 增强 position detail
- `agents/portfolio_weekly.py` — 周报：信号准确率聚合 + 再平衡建议 + exposure trend
- `tests/test_portfolio_health.py` — 9个单元测试，mock yfinance

---
```

- [ ] **Step 3.2：Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for portfolio-health implementation"
```
