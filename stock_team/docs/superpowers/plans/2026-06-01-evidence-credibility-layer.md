# Evidence Credibility Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增只读的证据可信度摘要层，生成 `findings/evidence_credibility_report.json`，并让 Decision State Hub 优先读取它。

**Architecture:** 新增 `scripts/evidence_credibility_report.py` 作为纯解释层，只读取现有因子、回测、参数、盘中随机搜索产物，不重跑回测、不写回参数。`agents/decision_state_hub.py` 保持兼容：优先消费新报告，缺失时继续使用旧的 `factor_ic_report.json` 和 `weekly_oos_validation_results.json`。

**Tech Stack:** Python standard library, pytest, existing JSON artifact conventions.

---

## 中文实施摘要

这一阶段完整做“回测 / 因子可信度强化”的第一版，但范围限定为 **摘要已有证据**：

- 不改 `agents/backtest_*`
- 不改 `scripts/weekly_*`
- 不重跑完整回测
- 不改交易规则
- 不自动写回参数
- 不做 dashboard UI

最终产物：

1. `scripts/evidence_credibility_report.py`
2. `tests/test_evidence_credibility_report.py`
3. `agents/decision_state_hub.py` 优先读取 `evidence_credibility_report.json`
4. `tests/test_decision_state_hub.py` 增加集成测试
5. spec/plan 记录完成状态

长期目标已经写入 spec：后续要做到完整研究系统级别，包括滚动 IC、分市场状态 IC、分行业/风格 IC、参数曲面、walk-forward、bootstrap/Monte Carlo、slippage/latency 压力测试和统一研究档案。本计划只做第一阶段摘要层。

## File Structure

| 文件 | 类型 | 职责 |
| --- | --- | --- |
| `scripts/evidence_credibility_report.py` | 新建 | 读取已有 JSON，生成可信度摘要报告 |
| `tests/test_evidence_credibility_report.py` | 新建 | 覆盖因子分级、回测分级、参数稳定性、盘中精确层分级、写文件 |
| `agents/decision_state_hub.py` | 修改 | 优先读取 `evidence_credibility_report.json`，缺失时回退旧逻辑 |
| `tests/test_decision_state_hub.py` | 修改 | 验证 hub 消费可信度报告、warning 进入 controller |
| `docs/superpowers/specs/2026-06-01-evidence-credibility-layer-design.md` | 修改 | 追加实施状态 |

## Target Contract

`findings/evidence_credibility_report.json` 的第一版必须包含：

```json
{
  "date": "2026-06-01",
  "generated_at": "2026-06-01T10:00:00+08:00",
  "factor_credibility": {
    "overall_verdict": "usable",
    "factors": {}
  },
  "backtest_credibility": {
    "overall_verdict": "caution",
    "time_oos": {},
    "style_oos": {},
    "full_lifecycle": {},
    "parameter_stability": {},
    "notes": []
  },
  "intraday_precision_credibility": {
    "tier": "exploratory",
    "notes": []
  },
  "decision_state_overrides": {
    "factor_quality": "usable",
    "backtest_verdict": "caution",
    "required_warnings": []
  }
}
```

### 分级规则

因子：

- `robust`: weeks >= 52, abs(mean_ic) >= 0.04, t_stat >= 2, positive_weeks_pct >= 58
- `usable`: weeks >= 52, abs(mean_ic) >= 0.02, ir > 0, positive_weeks_pct >= 52
- `exploratory`: weeks >= 8，但不满足 usable
- `insufficient`: weeks < 8 或关键字段缺失

回测：

- 子项 `supportive`: alpha > 0 且 mdd > -30
- 子项 `caution`: alpha <= 0 或 mdd <= -30
- 整体 `caution`: 任一关键 OOS 子项 caution，尤其 style-OOS alpha 为负
- 整体 `supportive`: time-OOS、style-OOS、full lifecycle 都 supportive
- `unavailable`: 报告缺失或解析失败

参数稳定性：

- `usable`: best_sortino 存在，neighborhood_avg_sortino / best_sortino >= 0.85
- `fragile`: 比例 < 0.85
- `unknown`: 字段缺失或 best_sortino <= 0

盘中精确层：

- `exploratory`: best_pf > 1 但 best_return 明显低于 benchmark_return
- `usable`: best_pf >= 1.3 且 best_return >= benchmark_return
- `insufficient`: 缺失报告

### Task 1: 新增 Evidence Credibility 纯函数测试

**Files:**
- Create: `tests/test_evidence_credibility_report.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_evidence_credibility_report.py`:

```python
import json
from pathlib import Path


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_report_classifies_factor_and_backtest_evidence(tmp_path):
    from scripts.evidence_credibility_report import build_evidence_credibility_report

    findings = tmp_path / "findings"
    config = tmp_path / "config"
    _write_json(findings / "factor_ic_report.json", [
        {
            "Factor": "5. Volatility (20d)",
            "Mean IC": 0.0553,
            "IC Std": 0.2649,
            "IR (Info Ratio)": 0.2088,
            "t-statistic": 2.18,
            "Positive Weeks %": "61.5%",
            "Weeks Count": 109
        },
        {
            "Factor": "6. Sentiment Catalyst",
            "Mean IC": -0.1564,
            "IC Std": 0.1666,
            "IR (Info Ratio)": -0.9387,
            "t-statistic": -1.33,
            "Positive Weeks %": "50.0%",
            "Weeks Count": 2
        }
    ])
    _write_json(findings / "weekly_oos_validation_results.json", {
        "full_lifecycle": {"return": 129.87, "mdd": -26.95, "sortino": 0.8522, "alpha": 7.98},
        "time_oos": {"return": 57.18, "mdd": -5.78, "sortino": 3.4882, "alpha": 15.94},
        "style_oos": {"return": 98.25, "mdd": -18.19, "sortino": 1.0065, "alpha": -23.64}
    })
    _write_json(config / "best_weekly_params.json", {
        "optimized_metrics": {
            "sortino": 0.8522,
            "neighborhood_avg_sortino": 0.8508
        }
    })
    _write_json(findings / "random_search_v2_summary.json", {
        "best_pf": 1.2819,
        "best_return": 1.7871,
        "top_results": [{"qqq_return": 21.2192}]
    })

    report = build_evidence_credibility_report("2026-06-01", base_dir=str(tmp_path))

    factors = report["factor_credibility"]["factors"]
    assert factors["5. Volatility (20d)"]["tier"] == "robust"
    assert factors["6. Sentiment Catalyst"]["tier"] == "insufficient"
    assert "样本只有 2 周" in " ".join(factors["6. Sentiment Catalyst"]["notes"])
    assert report["backtest_credibility"]["overall_verdict"] == "caution"
    assert report["backtest_credibility"]["style_oos"]["verdict"] == "caution"
    assert report["backtest_credibility"]["parameter_stability"]["tier"] == "usable"
    assert report["intraday_precision_credibility"]["tier"] == "exploratory"
    assert report["decision_state_overrides"]["factor_quality"] == "usable"
    assert report["decision_state_overrides"]["backtest_verdict"] == "caution"
    assert any("Style-OOS alpha 为负" in w for w in report["decision_state_overrides"]["required_warnings"])
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests\test_evidence_credibility_report.py::test_build_report_classifies_factor_and_backtest_evidence -q
```

Expected: fails with `ModuleNotFoundError` or missing function.

### Task 2: 实现 Evidence Credibility 报告生成器

**Files:**
- Create: `scripts/evidence_credibility_report.py`
- Test: `tests/test_evidence_credibility_report.py`

- [ ] **Step 1: 写最小实现**

Create `scripts/evidence_credibility_report.py`:

```python
import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, str) and value.endswith("%"):
            return float(value[:-1])
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalise_factor_rows(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("factors"), dict):
        rows = []
        for name, data in raw["factors"].items():
            if isinstance(data, dict):
                rows.append({
                    "Factor": name,
                    "Mean IC": data.get("mean_ic"),
                    "IR (Info Ratio)": data.get("ir"),
                    "t-statistic": data.get("t_stat"),
                    "Positive Weeks %": data.get("positive_weeks_pct"),
                    "Weeks Count": data.get("sample_weeks") or data.get("weeks"),
                })
        return rows
    return []


def classify_factor(row: dict[str, Any]) -> dict[str, Any]:
    name = str(row.get("Factor") or "unknown")
    mean_ic = _to_float(row.get("Mean IC"))
    ir = _to_float(row.get("IR (Info Ratio)"))
    t_stat = _to_float(row.get("t-statistic"))
    positive_weeks_pct = _to_float(row.get("Positive Weeks %"))
    weeks = _to_int(row.get("Weeks Count"))
    notes: list[str] = []

    if weeks < 8:
        tier = "insufficient"
        sample_label = "too_small"
        notes.append(f"样本只有 {weeks} 周，禁止作为强证据")
    elif weeks >= 52 and abs(mean_ic) >= 0.04 and t_stat >= 2 and positive_weeks_pct >= 58:
        tier = "robust"
        sample_label = "sufficient"
        notes.append("统计表现较强，但仍应作为排序证据而非独立交易结论")
    elif weeks >= 52 and abs(mean_ic) >= 0.02 and ir > 0 and positive_weeks_pct >= 52:
        tier = "usable"
        sample_label = "sufficient"
        notes.append("可作为辅助排序证据")
    else:
        tier = "exploratory"
        sample_label = "limited" if weeks < 52 else "sufficient"
        notes.append("统计显著性不足，暂作探索性证据")

    return {
        "tier": tier,
        "mean_ic": mean_ic,
        "ir": ir,
        "t_stat": t_stat,
        "positive_weeks_pct": positive_weeks_pct,
        "weeks_count": weeks,
        "sample_label": sample_label,
        "notes": notes,
    }


def _rank_factor_overall(factors: dict[str, dict[str, Any]]) -> str:
    tiers = [v.get("tier") for v in factors.values()]
    if "robust" in tiers or "usable" in tiers:
        return "usable"
    if "exploratory" in tiers:
        return "exploratory"
    return "insufficient"


def _scenario_metrics(data: dict[str, Any]) -> dict[str, Any]:
    alpha = _to_float(data.get("alpha") if "alpha" in data else data.get("alpha_pct"))
    mdd = _to_float(data.get("mdd") if "mdd" in data else data.get("max_drawdown_pct"))
    total_return = _to_float(data.get("return") if "return" in data else data.get("return_pct"))
    verdict = "supportive" if alpha > 0 and mdd > -30 else "caution"
    return {"return": total_return, "alpha": alpha, "mdd": mdd, "verdict": verdict}


def _parameter_stability(best_params: Any) -> dict[str, Any]:
    metrics = best_params.get("optimized_metrics", {}) if isinstance(best_params, dict) else {}
    best_sortino = _to_float(metrics.get("sortino"))
    neighborhood = _to_float(metrics.get("neighborhood_avg_sortino"))
    if best_sortino <= 0 or neighborhood <= 0:
        return {"tier": "unknown", "best_sortino": best_sortino, "neighborhood_avg_sortino": neighborhood, "notes": ["缺少可用邻域稳定性数据"]}
    ratio = neighborhood / best_sortino
    tier = "usable" if ratio >= 0.85 else "fragile"
    note = "邻域表现接近最优，初步说明参数不是孤点" if tier == "usable" else "邻域表现显著弱于最优，参数可能脆弱"
    return {"tier": tier, "best_sortino": best_sortino, "neighborhood_avg_sortino": neighborhood, "ratio": ratio, "notes": [note]}


def _intraday_precision(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"tier": "insufficient", "notes": ["未找到盘中随机搜索摘要"]}
    best_pf = _to_float(raw.get("best_pf"))
    best_return = _to_float(raw.get("best_return"))
    top_results = raw.get("top_results") if isinstance(raw.get("top_results"), list) else []
    benchmark_return = _to_float(top_results[0].get("qqq_return")) if top_results and isinstance(top_results[0], dict) else 0.0
    if best_pf >= 1.3 and best_return >= benchmark_return:
        tier = "usable"
        notes = ["盘中精确层初步可用，但仍需样本外验证"]
    elif best_pf > 1:
        tier = "exploratory"
        notes = ["盘中随机搜索 PF 略高于 1，但收益显著低于 QQQ，不能作为强 alpha 层"]
    else:
        tier = "insufficient"
        notes = ["盘中精确层尚未显示稳定优势"]
    return {"tier": tier, "best_pf": best_pf, "best_return": best_return, "benchmark_return": benchmark_return, "notes": notes}


def build_evidence_credibility_report(date: str, base_dir: str = BASE) -> dict[str, Any]:
    findings_dir = os.path.join(base_dir, "findings")
    config_dir = os.path.join(base_dir, "config")
    factor_rows = _normalise_factor_rows(_load_json(os.path.join(findings_dir, "factor_ic_report.json")))
    factors = {str(row.get("Factor")): classify_factor(row) for row in factor_rows}

    weekly = _load_json(os.path.join(findings_dir, "weekly_oos_validation_results.json"))
    weekly = weekly if isinstance(weekly, dict) else {}
    full = _scenario_metrics(weekly.get("full_lifecycle", {}))
    time_oos = _scenario_metrics(weekly.get("time_oos", {}))
    style_oos = _scenario_metrics(weekly.get("style_oos", {}))
    parameter_stability = _parameter_stability(_load_json(os.path.join(config_dir, "best_weekly_params.json")))
    backtest_notes: list[str] = []
    backtest_verdict = "supportive"
    if style_oos["verdict"] == "caution" and style_oos["alpha"] < 0:
        backtest_verdict = "caution"
        backtest_notes.append("style-OOS alpha 为负，LLM 和 dashboard 必须显式提示")
    if time_oos["verdict"] == "caution" or full["verdict"] == "caution":
        backtest_verdict = "caution"
    if not weekly:
        backtest_verdict = "unavailable"
        backtest_notes.append("未找到 weekly OOS 验证报告")

    intraday = _intraday_precision(_load_json(os.path.join(findings_dir, "random_search_v2_summary.json")))
    warnings = []
    for name, data in factors.items():
        if data["tier"] == "insufficient":
            warnings.append(f"{name} 样本不足")
    if style_oos["alpha"] < 0:
        warnings.append("Style-OOS alpha 为负")
    if intraday["tier"] == "exploratory":
        warnings.append("盘中精确点位层仍属探索性")

    return {
        "date": date,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "factor_credibility": {
            "overall_verdict": _rank_factor_overall(factors),
            "factors": factors,
        },
        "backtest_credibility": {
            "overall_verdict": backtest_verdict,
            "time_oos": time_oos,
            "style_oos": style_oos,
            "full_lifecycle": full,
            "parameter_stability": parameter_stability,
            "notes": backtest_notes,
        },
        "intraday_precision_credibility": intraday,
        "decision_state_overrides": {
            "factor_quality": _rank_factor_overall(factors),
            "backtest_verdict": backtest_verdict,
            "required_warnings": warnings,
        },
    }


def write_evidence_credibility_report(date: str, base_dir: str = BASE) -> str:
    payload = build_evidence_credibility_report(date, base_dir=base_dir)
    out_dir = os.path.join(base_dir, "findings")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "evidence_credibility_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build evidence credibility summary.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--base-dir", default=BASE)
    args = parser.parse_args(argv)
    print(write_evidence_credibility_report(args.date, base_dir=args.base_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 运行测试**

Run:

```powershell
python -m pytest tests\test_evidence_credibility_report.py -q
python -m py_compile scripts\evidence_credibility_report.py
```

Expected: test passes and compile exits 0.

- [ ] **Step 3: 提交 Task 1-2**

Run:

```powershell
git add scripts\evidence_credibility_report.py tests\test_evidence_credibility_report.py
git commit -m "feat: add evidence credibility report"
```

### Task 3: 写文件和缺失输入测试

**Files:**
- Modify: `tests/test_evidence_credibility_report.py`
- Modify: `scripts/evidence_credibility_report.py`

- [ ] **Step 1: 添加写文件与缺失输入测试**

Append to `tests/test_evidence_credibility_report.py`:

```python

def test_write_report_creates_findings_artifact(tmp_path):
    from scripts.evidence_credibility_report import write_evidence_credibility_report

    out = write_evidence_credibility_report("2026-06-01", base_dir=str(tmp_path))
    payload = json.loads(Path(out).read_text(encoding="utf-8"))

    assert Path(out).name == "evidence_credibility_report.json"
    assert payload["date"] == "2026-06-01"
    assert "decision_state_overrides" in payload


def test_missing_inputs_are_unavailable_not_crashing(tmp_path):
    from scripts.evidence_credibility_report import build_evidence_credibility_report

    report = build_evidence_credibility_report("2026-06-01", base_dir=str(tmp_path))

    assert report["factor_credibility"]["overall_verdict"] == "insufficient"
    assert report["backtest_credibility"]["overall_verdict"] == "unavailable"
    assert report["intraday_precision_credibility"]["tier"] == "insufficient"
```

- [ ] **Step 2: 运行测试**

Run:

```powershell
python -m pytest tests\test_evidence_credibility_report.py -q
```

Expected: all evidence credibility tests pass. If missing-input behavior fails, update `build_evidence_credibility_report()` so empty inputs produce `insufficient` / `unavailable` labels.

- [ ] **Step 3: 提交 Task 3**

Run:

```powershell
git add scripts\evidence_credibility_report.py tests\test_evidence_credibility_report.py
git commit -m "test: cover evidence credibility report edge cases"
```

### Task 4: Decision State Hub 优先读取可信度报告

**Files:**
- Modify: `agents/decision_state_hub.py`
- Modify: `tests/test_decision_state_hub.py`

- [ ] **Step 1: 添加 hub 集成测试**

Append to `tests/test_decision_state_hub.py`:

```python

def test_decision_state_prefers_evidence_credibility_report(tmp_path):
    from agents.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(findings / f"premarket_summary_{date}_NVDA.json", {
        "symbol": "NVDA",
        "date": date,
        "thesis": {"base_thesis": "AI demand remains strong"},
    })
    _write_json(findings / f"entry_decision_{date}.json", {
        "decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}
    })
    _write_json(findings / "evidence_credibility_report.json", {
        "factor_credibility": {
            "overall_verdict": "usable",
            "factors": {
                "5. Volatility (20d)": {"tier": "robust", "weeks_count": 109}
            }
        },
        "backtest_credibility": {
            "overall_verdict": "caution",
            "time_oos": {"verdict": "supportive", "alpha": 15.94},
            "style_oos": {"verdict": "caution", "alpha": -23.64},
            "full_lifecycle": {"verdict": "supportive"},
            "parameter_stability": {"tier": "usable"},
            "notes": ["style-OOS alpha 为负，LLM 和 dashboard 必须显式提示"]
        },
        "decision_state_overrides": {
            "factor_quality": "usable",
            "backtest_verdict": "caution",
            "required_warnings": ["Style-OOS alpha 为负"]
        }
    })

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert nvda["factor_evidence"]["factor_quality"] == "usable"
    assert nvda["factor_evidence"]["factor_scores"]["5. Volatility (20d)"]["tier"] == "robust"
    assert nvda["backtest_evidence"]["backtest_verdict"] == "caution"
    assert "Style-OOS alpha 为负" in nvda["controller"]["required_human_check"]
    assert nvda["controller"]["evidence_alignment"] == "mixed"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_decision_state_prefers_evidence_credibility_report -q
```

Expected: fails because hub does not yet read `evidence_credibility_report.json`.

- [ ] **Step 3: 修改 hub 实现**

In `agents/decision_state_hub.py`, add helper:

```python
def _load_evidence_credibility(find_dir: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = os.path.join(find_dir, "evidence_credibility_report.json")
    report, load_status = _load_json_with_status(path)
    return report, _source_status(path, os.path.dirname(find_dir), load_status=load_status)
```

Update `build_symbol_state()` flow:

```python
credibility, credibility_src = _load_evidence_credibility(find_dir)
if credibility:
    factor = _factor_from_credibility(credibility)
    backtest = _backtest_from_credibility(credibility)
else:
    factor, factor_src = _extract_factor_evidence(find_dir, base_dir)
    backtest, backtest_src = _extract_backtest_evidence(find_dir, base_dir)
```

Add pure helpers:

```python
def _factor_from_credibility(report: dict[str, Any]) -> dict[str, Any]:
    fc = report.get("factor_credibility") if isinstance(report.get("factor_credibility"), dict) else {}
    overrides = report.get("decision_state_overrides") if isinstance(report.get("decision_state_overrides"), dict) else {}
    return {
        "factor_scores": fc.get("factors") if isinstance(fc.get("factors"), dict) else {},
        "factor_direction": "supportive" if overrides.get("factor_quality") in {"robust", "usable"} else "neutral",
        "factor_quality": overrides.get("factor_quality") or fc.get("overall_verdict") or "unavailable",
        "factor_notes": list(overrides.get("required_warnings") or []),
    }


def _backtest_from_credibility(report: dict[str, Any]) -> dict[str, Any]:
    bc = report.get("backtest_credibility") if isinstance(report.get("backtest_credibility"), dict) else {}
    overrides = report.get("decision_state_overrides") if isinstance(report.get("decision_state_overrides"), dict) else {}
    return {
        "strategy_family": "weekly_rebalance",
        "matched_signal_set": "credibility_report",
        "in_sample_summary": bc.get("full_lifecycle") if isinstance(bc.get("full_lifecycle"), dict) else {},
        "out_of_sample_summary": {
            "time_oos": bc.get("time_oos") if isinstance(bc.get("time_oos"), dict) else {},
            "style_oos": bc.get("style_oos") if isinstance(bc.get("style_oos"), dict) else {},
        },
        "drawdown_profile": {},
        "parameter_stability": bc.get("parameter_stability") if isinstance(bc.get("parameter_stability"), dict) else {"tier": "unknown"},
        "backtest_verdict": overrides.get("backtest_verdict") or bc.get("overall_verdict") or "unavailable",
        "backtest_notes": list(bc.get("notes") or []) + list(overrides.get("required_warnings") or []),
    }
```

Update controller call to include required warnings as human checks. One direct approach:

```python
credibility_warnings = []
if credibility:
    overrides = credibility.get("decision_state_overrides") if isinstance(credibility.get("decision_state_overrides"), dict) else {}
    credibility_warnings = list(overrides.get("required_warnings") or [])
controller = _controller(..., warnings=credibility_warnings)
```

Update `_controller()` signature:

```python
warnings: list[str] | None = None
```

Inside `_controller()`, before return:

```python
for warning in warnings or []:
    if warning not in required:
        required.append(warning)
```

Also include `evidence_credibility_report` in `source_freshness`.

- [ ] **Step 4: 运行 hub 测试**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py -q
```

Expected: all hub tests pass.

- [ ] **Step 5: 提交 Task 4**

Run:

```powershell
git add agents\decision_state_hub.py tests\test_decision_state_hub.py
git commit -m "feat: use evidence credibility in decision state"
```

### Task 5: 最终文档状态与验证

**Files:**
- Modify: `docs/superpowers/specs/2026-06-01-evidence-credibility-layer-design.md`
- Modify: `docs/superpowers/plans/2026-06-01-evidence-credibility-layer.md`

- [ ] **Step 1: 运行完整验证**

Run:

```powershell
python -m py_compile scripts\evidence_credibility_report.py agents\decision_state_hub.py
python -m pytest tests\test_evidence_credibility_report.py tests\test_decision_state_hub.py -q
python scripts\evidence_credibility_report.py --date 2026-06-01 --base-dir .
python scripts\check_repo_hygiene.py
git status --short
```

Expected:

- compile passes
- selected tests pass
- CLI writes `findings/evidence_credibility_report.json`
- hygiene may flag the generated findings artifact if untracked; do not commit generated findings unless explicitly intended. Delete or leave ignored according to hygiene result.

- [ ] **Step 2: 如果 CLI 生成 artifact 导致 hygiene 失败**

If `findings/evidence_credibility_report.json` is untracked and not ignored, remove it after confirming the CLI smoke output:

```powershell
Remove-Item -LiteralPath findings\evidence_credibility_report.json -Force
python scripts\check_repo_hygiene.py
```

- [ ] **Step 3: 追加 spec 实施状态**

Append to `docs/superpowers/specs/2026-06-01-evidence-credibility-layer-design.md`:

```markdown
## 实施状态

第一版实现范围：新增 `scripts/evidence_credibility_report.py` 生成 `findings/evidence_credibility_report.json`，并让 `agents/decision_state_hub.py` 优先读取该报告。此阶段没有修改回测引擎、weekly 回测脚本、交易规则或 dashboard UI。
```

- [ ] **Step 4: 追加计划交接状态**

Append to this plan:

```markdown
## Completion Handoff

Status: complete as of 2026-06-01.

Implemented behavior:

- `scripts/evidence_credibility_report.py` builds the evidence credibility report.
- Decision State Hub prefers the credibility report and falls back to legacy factor/backtest files.
- Style-OOS negative alpha becomes a required warning.
- Sentiment catalyst with tiny samples is marked insufficient.
- Intraday precision random search is marked exploratory when PF is positive but return trails QQQ.

Final verification:

- `python -m py_compile scripts\evidence_credibility_report.py agents\decision_state_hub.py`
- `python -m pytest tests\test_evidence_credibility_report.py tests\test_decision_state_hub.py -q`
- `python scripts\check_repo_hygiene.py`
```

- [ ] **Step 5: 提交文档状态**

Run:

```powershell
git add docs\superpowers\specs\2026-06-01-evidence-credibility-layer-design.md docs\superpowers\plans\2026-06-01-evidence-credibility-layer.md
git commit -m "docs: record evidence credibility handoff"
```

## Final Verification

Before reporting completion, run:

```powershell
python -m py_compile scripts\evidence_credibility_report.py agents\decision_state_hub.py
python -m pytest tests\test_evidence_credibility_report.py tests\test_decision_state_hub.py -q
python scripts\check_repo_hygiene.py
git status --short
```

Expected:

- compile exits 0
- selected tests pass
- hygiene passes
- worktree clean after commits and cache cleanup

## Self-Review Notes

- Spec coverage: report generation, factor tiers, backtest tiers, parameter stability, intraday precision, Decision State Hub integration, no backtest changes, no UI changes.
- Long-term goal coverage: complete research-system optimization is documented in the spec, but deliberately excluded from this implementation plan.
- Boundary check: implementation must not modify `agents/backtest_*`, `scripts/weekly_*`, `scripts/*backtest*`, or trading-rule logic.

## Completion Handoff

Status: complete as of 2026-06-01.

Implemented behavior:

- `scripts/evidence_credibility_report.py` builds the evidence credibility report.
- Decision State Hub prefers the credibility report and falls back to legacy factor/backtest files.
- Style-OOS negative alpha becomes a required warning.
- Sentiment catalyst with tiny samples is marked insufficient.
- Intraday precision random search is marked exploratory when PF is positive but return trails QQQ.

Final verification:

- `python -m py_compile scripts\evidence_credibility_report.py agents\decision_state_hub.py` passed.
- `python -m pytest tests\test_evidence_credibility_report.py tests\test_decision_state_hub.py -q` passed with 12 tests.
- `python scripts\evidence_credibility_report.py --date 2026-06-01 --base-dir .` wrote `findings/evidence_credibility_report.json`.
- `python scripts\check_repo_hygiene.py` passed after deleting generated test/compile caches.
