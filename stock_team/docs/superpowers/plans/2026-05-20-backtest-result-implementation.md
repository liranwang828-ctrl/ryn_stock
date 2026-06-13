# backtest_result 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/backtest_result.py`，包装现有 `backtest_engine.py` 的输出为标准化 JSON（backtest_result_{date}.json），追加历次运行到 backtest_log.jsonl，实现三种触发模式和自动阈值更新记录。

**Architecture:** `backtest_result.py` 调用 backtest_engine 的 `run_portfolio_scan` 和内部函数，构建 spec 格式的 scan_results/simulate_results/threshold_update，写出新文件。两套文件并存（旧 backtest_results_{date}.json 保留）。

**Tech Stack:** Python 3.12, json, pandas, yfinance（通过 backtest_engine 间接使用，测试中 mock）

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/backtest_result.py` | 新建 | 包装引擎，输出标准化 JSON + log 追加 |
| `tests/test_backtest_result.py` | 新建 | 单元测试，mock 网络调用 |

---

## Task 1：核心纯函数

**Files:**
- Create: `agents/backtest_result.py`（第一部分）
- Create: `tests/test_backtest_result.py`

---

- [ ] **Step 1.1：写测试**

```python
# tests/test_backtest_result.py
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/stock_team"))


# ── 测试 build_scan_results ──────────────────────────────────────────────

def test_build_scan_results_computes_improvement():
    """build_scan_results 正确计算 improvement_pp 和 win_rate_at_current"""
    from agents.backtest_result import build_scan_results
    # run_portfolio_scan 的模拟返回值
    raw_scan = {
        "ma20_dev_max": {
            "optimal": 0.03, "win_rate": 0.65, "n_samples": 150, "mean_ret": 0.02,
            "scan": [
                {"threshold": 0.03, "win_rate": 0.65, "n": 150, "mean_ret": 0.02},
                {"threshold": 0.05, "win_rate": 0.58, "n": 300, "mean_ret": 0.01},
                {"threshold": 0.08, "win_rate": 0.52, "n": 400, "mean_ret": 0.005},
            ],
        },
        "rs5_min": {
            "optimal": 1.0, "win_rate": 0.62, "n_samples": 80, "mean_ret": 0.015,
            "scan": [
                {"threshold": 0.0, "win_rate": 0.57, "n": 200, "mean_ret": 0.01},
                {"threshold": 1.0, "win_rate": 0.62, "n": 80, "mean_ret": 0.015},
            ],
        },
    }
    # 当前阈值（decision_thresholds.json 的 soft_vetoes）
    current_thresholds = {"ma20_dev_max": 0.05, "rs5_min": 0.0}

    result = build_scan_results(raw_scan, current_thresholds)

    assert "ma20_dev_max" in result
    assert "rs5_min" in result
    ma = result["ma20_dev_max"]
    assert ma["optimal"] == 0.03
    assert ma["current"] == 0.05
    assert ma["win_rate_at_optimal"] == 0.65
    assert abs(ma["win_rate_at_current"] - 0.58) < 0.01  # threshold=0.05 → win_rate=0.58
    assert abs(ma["improvement_pp"] - 7.0) < 0.1  # 65 - 58 = 7pp
    assert ma["sample_size"] == 150


def test_build_scan_results_fallback_to_nearest():
    """当前阈值不在候选列表中时，取最近邻"""
    from agents.backtest_result import build_scan_results
    raw_scan = {
        "ma20_dev_max": {
            "optimal": 0.03, "win_rate": 0.62, "n_samples": 100, "mean_ret": 0.01,
            "scan": [
                {"threshold": 0.03, "win_rate": 0.62, "n": 100, "mean_ret": 0.01},
                {"threshold": 0.06, "win_rate": 0.55, "n": 200, "mean_ret": 0.005},
            ],
        },
    }
    # current = 0.04 不在 [0.03, 0.06] 中，取最近邻 0.03
    result = build_scan_results(raw_scan, {"ma20_dev_max": 0.04})
    assert result["ma20_dev_max"]["win_rate_at_current"] is not None


# ── 测试 should_update_thresholds ─────────────────────────────────────────

def test_should_update_thresholds_triggers():
    """improvement > 5pp AND sample ≥ 20 AND win_rate > 0.55 → triggered"""
    from agents.backtest_result import should_update_thresholds
    scan_results = {
        "ma20_dev_max": {
            "optimal": 0.03, "current": 0.05,
            "win_rate_at_optimal": 0.63, "win_rate_at_current": 0.57,
            "improvement_pp": 6.0, "sample_size": 150,
        },
    }
    updates = should_update_thresholds(scan_results, run_type="full")
    assert len(updates) > 0
    assert updates[0]["param"] == "ma20_dev_max"


def test_should_update_thresholds_not_triggered_small_improvement():
    """improvement < 5pp → 不触发"""
    from agents.backtest_result import should_update_thresholds
    scan_results = {
        "ma20_dev_max": {
            "optimal": 0.04, "current": 0.05,
            "win_rate_at_optimal": 0.59, "win_rate_at_current": 0.57,
            "improvement_pp": 2.0, "sample_size": 150,
        },
    }
    updates = should_update_thresholds(scan_results, run_type="full")
    assert updates == []


def test_should_update_thresholds_incremental_never_updates():
    """incremental 模式永远不更新"""
    from agents.backtest_result import should_update_thresholds
    scan_results = {
        "ma20_dev_max": {
            "optimal": 0.03, "current": 0.05,
            "win_rate_at_optimal": 0.70, "win_rate_at_current": 0.57,
            "improvement_pp": 13.0, "sample_size": 500,
        },
    }
    updates = should_update_thresholds(scan_results, run_type="incremental")
    assert updates == []


# ── 测试 compute_consecutive_low_weeks ────────────────────────────────────

def test_consecutive_low_weeks_counts_correctly(tmp_path):
    """连续 incremental 低于 0.55 的次数计数正确"""
    from agents.backtest_result import compute_consecutive_low_weeks
    log_file = tmp_path / "backtest_log.jsonl"
    # 写入：1 次 full（重置）+ 3 次 incremental low + 1 次 incremental high
    entries = [
        {"run_type": "full",        "win_rate": 0.60, "consecutive_low_weeks": 0},
        {"run_type": "incremental", "win_rate": 0.50, "consecutive_low_weeks": 1},
        {"run_type": "incremental", "win_rate": 0.52, "consecutive_low_weeks": 2},
        {"run_type": "incremental", "win_rate": 0.48, "consecutive_low_weeks": 3},
    ]
    with open(str(log_file), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    count = compute_consecutive_low_weeks(find_dir=str(tmp_path))
    assert count == 3


def test_consecutive_low_weeks_resets_on_full(tmp_path):
    """full 运行后重置为 0"""
    from agents.backtest_result import compute_consecutive_low_weeks
    log_file = tmp_path / "backtest_log.jsonl"
    entries = [
        {"run_type": "incremental", "win_rate": 0.48, "consecutive_low_weeks": 3},
        {"run_type": "full",        "win_rate": 0.60, "consecutive_low_weeks": 0},
    ]
    with open(str(log_file), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    count = compute_consecutive_low_weeks(find_dir=str(tmp_path))
    assert count == 0


# ── 测试 append_backtest_log ──────────────────────────────────────────────

def test_append_backtest_log_creates_and_appends(tmp_path):
    """append_backtest_log 追加不覆盖"""
    from agents.backtest_result import append_backtest_log
    log_path = tmp_path / "backtest_log.jsonl"

    entry1 = {"date": "2026-05-20", "run_type": "full", "win_rate": 0.60,
               "n_entries": 100, "mean_ret_pct": 1.5, "vs_baseline_pp": 8.0,
               "threshold_updated": False, "consecutive_low_weeks": 0,
               "params_snapshot": {"ma20_dev_max": 0.05, "rs5_min": 0.0, "vol_ratio_max": 1.0}}
    entry2 = {**entry1, "date": "2026-05-27", "run_type": "incremental", "win_rate": 0.52}

    append_backtest_log(entry1, find_dir=str(tmp_path))
    append_backtest_log(entry2, find_dir=str(tmp_path))

    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 2
    d1 = json.loads(lines[0])
    assert d1["run_type"] == "full"
    d2 = json.loads(lines[1])
    assert d2["run_type"] == "incremental"
```

- [ ] **Step 1.2：运行测试，确认 FAIL（ImportError）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_backtest_result.py -v 2>&1 | head -15
```

- [ ] **Step 1.3：创建 agents/backtest_result.py（第一部分：纯函数）**

```python
"""
回测结果标准化模块 — backtest_result.py
包装 backtest_engine.py，输出 spec 格式的 JSON。

新文件（与旧文件并存）：
  findings/backtest_result_{date}.json   单次运行结果
  findings/backtest_log.jsonl           历史追加日志

用法: python3.12 agents/backtest_result.py [full|incremental|bootstrap] [SYM1 SYM2 ...]
"""
import json, os, sys
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE     = os.path.expanduser("~/stock_team")
FIND_DIR = os.path.join(BASE, "findings")
CFG_DIR  = os.path.join(BASE, "config")
_MIN_SAMPLES   = 20
_MIN_IMPROVE   = 5.0   # pp
_MIN_WIN_RATE  = 0.55


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_current_thresholds() -> dict:
    """读取 decision_thresholds.json 的 soft_vetoes"""
    data = _load(os.path.join(CFG_DIR, "decision_thresholds.json"))
    return data.get("soft_vetoes", {"ma20_dev_max": 0.05, "rs5_min": 0.0})


def _find_nearest_win_rate(scan_list: list, target: float) -> float | None:
    """在 scan 列表中找与 target 最近邻的 win_rate"""
    if not scan_list:
        return None
    valid = [(s["threshold"], s["win_rate"]) for s in scan_list
             if s.get("win_rate") is not None]
    if not valid:
        return None
    # 精确匹配
    for thr, wr in valid:
        if abs(thr - target) < 1e-6:
            return wr
    # 最近邻
    nearest = min(valid, key=lambda x: abs(x[0] - target))
    return nearest[1]


def build_scan_results(raw_scan: dict, current_thresholds: dict) -> dict:
    """
    将 run_portfolio_scan() 的返回值映射为 spec 格式的 scan_results。
    """
    result = {}
    for signal, data in raw_scan.items():
        cur_val = current_thresholds.get(signal)
        win_at_opt = data.get("win_rate")
        win_at_cur = _find_nearest_win_rate(data.get("scan", []), cur_val) \
                     if cur_val is not None else None
        improvement = None
        if win_at_opt is not None and win_at_cur is not None:
            improvement = round((win_at_opt - win_at_cur) * 100, 2)

        result[signal] = {
            "optimal":             data.get("optimal"),
            "current":             cur_val,
            "win_rate_at_optimal": win_at_opt,
            "win_rate_at_current": win_at_cur,
            "improvement_pp":      improvement,
            "sample_size":         data.get("n_samples", 0),
        }
    return result


def should_update_thresholds(scan_results: dict, run_type: str) -> list[dict]:
    """
    评估哪些信号阈值满足自动更新条件。
    incremental 模式永不更新。
    返回需更新的列表，空列表 = 不触发。
    """
    if run_type == "incremental":
        return []
    updates = []
    for param, data in scan_results.items():
        improvement = data.get("improvement_pp") or 0.0
        sample_size = data.get("sample_size") or 0
        win_opt     = data.get("win_rate_at_optimal") or 0.0
        if improvement > _MIN_IMPROVE and sample_size >= _MIN_SAMPLES and win_opt > _MIN_WIN_RATE:
            updates.append({
                "param":          param,
                "old_value":      data.get("current"),
                "new_value":      data.get("optimal"),
                "improvement_pp": improvement,
                "sample_size":    sample_size,
            })
    return updates


def apply_threshold_updates(updates: list[dict]) -> str:
    """将更新写入 decision_thresholds.json，返回 applied_at ISO 字符串"""
    cfg_path = os.path.join(CFG_DIR, "decision_thresholds.json")
    data = _load(cfg_path)
    for u in updates:
        param = u.get("param")
        new_v = u.get("new_value")
        if param and new_v is not None:
            data.setdefault("soft_vetoes", {})[param] = new_v
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return datetime.now(timezone.utc).isoformat()


def compute_consecutive_low_weeks(find_dir: str = FIND_DIR) -> int:
    """
    读取 backtest_log.jsonl，统计最近连续 incremental win_rate < 0.55 的次数。
    full/bootstrap 运行后重置为 0。
    """
    log_path = os.path.join(find_dir, "backtest_log.jsonl")
    if not os.path.exists(log_path):
        return 0
    entries = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    # 从最新往前数连续 incremental low
    count = 0
    for entry in reversed(entries):
        rt = entry.get("run_type", "")
        if rt in ("full", "bootstrap"):
            break
        if rt == "incremental":
            if (entry.get("win_rate") or 1.0) < 0.55:
                count += 1
            else:
                break   # 非连续，停止
    return count


def append_backtest_log(entry: dict, find_dir: str = FIND_DIR):
    """追加一条记录到 backtest_log.jsonl"""
    os.makedirs(find_dir, exist_ok=True)
    log_path = os.path.join(find_dir, "backtest_log.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

- [ ] **Step 1.4：运行测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_backtest_result.py -v
```

预期：全部 PASS

- [ ] **Step 1.5：Commit**

```bash
git add agents/backtest_result.py tests/test_backtest_result.py
git commit -m "feat: add backtest_result core functions — scan_results, threshold_update, log"
```

---

## Task 2：run_backtest 主函数 + 文件写入

**Files:**
- Modify: `agents/backtest_result.py`（追加）
- Test: `tests/test_backtest_result.py`（追加）

---

- [ ] **Step 2.1：追加测试**

```python
def test_run_backtest_incremental_schema(tmp_path):
    """run_backtest incremental 返回所有顶层字段，scan_results=null"""
    from unittest.mock import patch
    from agents.backtest_result import run_backtest

    mock_sim = {
        "win_rate": 0.58, "n_entries": 45, "mean_ret_pct": 1.2,
        "symbols": ["NVDA"], "years": 0,
        "thresholds_used": {"ma20_dev_max": 0.05, "rs5_min": 0.0},
        "note": "ok",
    }
    with patch("agents.backtest_result.simulate_decision_framework",
               return_value=mock_sim):
        result = run_backtest(
            symbols=["NVDA"], run_type="incremental",
            years=0, find_dir=str(tmp_path), cfg_dir=str(tmp_path / "config"),
        )

    assert set(result.keys()) == {"meta", "scan_results", "simulate_results",
                                   "threshold_update", "llm_summary"}
    assert result["scan_results"] is None          # incremental = no scan
    assert result["meta"]["run_type"] == "incremental"
    assert result["simulate_results"]["win_rate"] == 0.58


def test_write_backtest_result_creates_file(tmp_path):
    """write_backtest_result 生成 JSON 文件"""
    from agents.backtest_result import write_backtest_result
    import pathlib
    data = {"meta": {"date": "2026-05-20", "run_type": "full"},
            "scan_results": None, "simulate_results": {}, "threshold_update": {},
            "llm_summary": ""}
    path = write_backtest_result("2026-05-20", data, find_dir=str(tmp_path))
    assert pathlib.Path(path).exists()
    d = json.loads(pathlib.Path(path).read_text())
    assert d["meta"]["run_type"] == "full"
```

- [ ] **Step 2.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_backtest_result.py -k "run_backtest or write_backtest" -v
```

- [ ] **Step 2.3：追加主函数到 agents/backtest_result.py**

```python
# ── 需要从 backtest_engine 导入 ──────────────────────────────────────────────
try:
    from agents.backtest_engine import (
        run_portfolio_scan,
        simulate_decision_framework,
    )
except Exception:
    run_portfolio_scan = None
    simulate_decision_framework = None


def _build_simulate_results(sim_output: dict, params: dict) -> dict:
    """将 simulate_decision_framework 输出映射为 spec 格式"""
    win_rate = sim_output.get("win_rate")
    n        = sim_output.get("n_entries", 0)
    mean_ret = sim_output.get("mean_ret_pct")

    return {
        "n_entries":        n,
        "win_rate":         win_rate,
        "mean_ret_pct":     mean_ret,
        "median_ret_pct":   None,    # 需要原始 DataFrame，当前版本不可用
        "max_drawdown_pct": None,    # 同上
        "sharpe_proxy":     None,    # 同上
        "hold_days":        5,
        "vs_baseline": {
            "baseline_win_rate":       None,   # 需要无筛选基线，当前版本不可用
            "baseline_mean_ret":       None,
            "win_rate_improvement_pp": None,
        },
        "params_used": params,
    }


def run_backtest(
    symbols: list[str],
    run_type: str = "full",
    years: int = 2,
    find_dir: str = FIND_DIR,
    cfg_dir: str = CFG_DIR,
) -> dict:
    """
    主函数：执行回测并返回标准化 result dict。
    run_type: "bootstrap" | "full" | "incremental"
    """
    date_str = _date.today().strftime("%Y-%m-%d")
    current_thresholds = _get_current_thresholds()

    # ── scan（full/bootstrap 才执行）────────────────────────────────────────
    scan_results = None
    if run_type in ("full", "bootstrap") and run_portfolio_scan:
        raw_scan = run_portfolio_scan(symbols, years=years, write_output=False)
        scan_results = build_scan_results(raw_scan, current_thresholds)
    elif run_type in ("full", "bootstrap") and not run_portfolio_scan:
        scan_results = {}   # engine 不可用时返回空

    # ── simulate ────────────────────────────────────────────────────────────
    # 使用最优参数（scan 完成后）或当前参数（incremental）
    sim_params = dict(current_thresholds)
    if scan_results:
        for sig, data in scan_results.items():
            if data.get("optimal") is not None:
                sim_params[sig] = data["optimal"]

    thresholds_for_sim = {"soft_vetoes": sim_params}
    sim_output = {}
    if simulate_decision_framework:
        sim_years = max(years, 1) if years > 0 else 1
        sim_output = simulate_decision_framework(
            symbols=symbols,
            thresholds=thresholds_for_sim,
            years=sim_years,
            write_output=False,
        ) or {}

    simulate_results = _build_simulate_results(sim_output, sim_params)

    # ── threshold_update ─────────────────────────────────────────────────────
    updates = []
    if scan_results:
        updates = should_update_thresholds(scan_results, run_type)
    applied_at = None
    if updates:
        applied_at = apply_threshold_updates(updates)

    threshold_update = {
        "triggered":       len(updates) > 0,
        "reason":          "自动更新" if updates else
                           ("incremental 模式不更新" if run_type == "incremental"
                            else "改善幅度不足或样本量不足"),
        "updates_applied": updates,
        "applied_at":      applied_at,
    }

    # ── meta ─────────────────────────────────────────────────────────────────
    meta = {
        "date":          date_str,
        "run_type":      run_type,
        "symbols":       symbols,
        "data_years":    years if run_type != "incremental" else None,
        "data_from":     None,
        "data_to":       date_str,
        "sample_source": "yfinance_historical",
        "generated_at":  datetime.now(timezone.utc).isoformat(),
    }

    result = {
        "meta":             meta,
        "scan_results":     scan_results,
        "simulate_results": simulate_results,
        "threshold_update": threshold_update,
        "llm_summary":      "",   # 存根
    }

    # ── 追加 log ─────────────────────────────────────────────────────────────
    win_rate   = simulate_results.get("win_rate")
    consec     = compute_consecutive_low_weeks(find_dir=find_dir)
    if run_type == "incremental" and win_rate is not None and win_rate < 0.55:
        consec += 1
    elif run_type in ("full", "bootstrap"):
        consec = 0

    log_entry = {
        "date":                  date_str,
        "run_type":              run_type,
        "win_rate":              win_rate,
        "n_entries":             simulate_results.get("n_entries"),
        "mean_ret_pct":          simulate_results.get("mean_ret_pct"),
        "vs_baseline_pp":        None,
        "threshold_updated":     len(updates) > 0,
        "consecutive_low_weeks": consec,
        "params_snapshot":       sim_params,
    }
    append_backtest_log(log_entry, find_dir=find_dir)

    return result


def write_backtest_result(date: str, data: dict, find_dir: str = FIND_DIR) -> str:
    """写出 backtest_result_{date}.json（注意：单数 result，与旧文件 results 并存）"""
    os.makedirs(find_dir, exist_ok=True)
    path = os.path.join(find_dir, f"backtest_result_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="回测结果标准化")
    parser.add_argument("run_type", choices=["full", "incremental", "bootstrap"],
                        default="full", nargs="?")
    parser.add_argument("symbols", nargs="*")
    parser.add_argument("--years", type=int, default=None)
    args = parser.parse_args()

    years_map = {"bootstrap": 10, "full": 2, "incremental": 0}
    years = args.years if args.years is not None else years_map[args.run_type]

    cfg  = _load(os.path.join(CFG_DIR, "poll_config.json"))
    syms = args.symbols or cfg.get("default_symbols", [])

    print(f"\n回测 {args.run_type}  symbols={syms}  years={years}\n")
    result = run_backtest(syms, run_type=args.run_type, years=years)
    date_str = result["meta"]["date"]
    path = write_backtest_result(date_str, result)
    wr = result["simulate_results"].get("win_rate")
    print(f"  win_rate: {wr}")
    print(f"  ✅ {os.path.basename(path)}")
    if result["threshold_update"]["triggered"]:
        for u in result["threshold_update"]["updates_applied"]:
            print(f"  📈 {u['param']}: {u['old_value']} → {u['new_value']}"
                  f" (+{u['improvement_pp']:.1f}pp)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_backtest_result.py -v
```

预期：全部 PASS（simulate_decision_framework 通过 mock 绕过）

- [ ] **Step 2.5：Commit**

```bash
git add agents/backtest_result.py tests/test_backtest_result.py
git commit -m "feat: complete backtest_result — run_backtest + write + CLI"
```

---

## Task 3：CHANGELOG 更新

- [ ] **Step 3.1：更新 CHANGELOG.md**

顶部追加：

```
## 2026-05-20 backtest_result 实施完成

### 新建文件
- `agents/backtest_result.py` — 标准化回测输出：build_scan_results / should_update_thresholds / run_backtest / backtest_log 追加
- `tests/test_backtest_result.py` — 9个单元测试，mock yfinance/backtest_engine

### 说明
- 新文件 backtest_result_{date}.json（单数）与旧文件 backtest_results_{date}.json（复数）并存
- median/sharpe/vs_baseline 字段当前为 null 存根（需原始 DataFrame，待后续重构）

---
```

- [ ] **Step 3.2：Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for backtest_result implementation"
```
