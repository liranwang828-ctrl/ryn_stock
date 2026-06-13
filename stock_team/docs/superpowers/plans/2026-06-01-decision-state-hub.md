# Decision State Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily per-symbol Decision State Hub that normalizes thesis, factor evidence, backtest evidence, execution state, and controller judgment into `findings/decision_state_{date}.json`.

**Architecture:** Add one new pure-data builder module, `agents/decision_state_hub.py`, that reads existing artifacts and emits a stable JSON contract. Keep the first version additive: no backtest engine changes, no trading rule changes, and no dashboard visual redesign. Then teach `dashboard_writer.py` to load the hub output into its context without requiring templates to consume it yet.

**Tech Stack:** Python standard library, existing JSON artifact patterns, pytest, existing repo hygiene guard.

---

## 中文实施摘要

本计划只做第一阶段：先把系统的决策状态统一起来，不改交易逻辑，不碰同事的回测引擎，也不先做 dashboard 视觉重构。

落地结果有三个：

1. 新增 `agents/decision_state_hub.py`，读取已有的 `premarket_summary`、`entry_decision`、因子 IC 报告、周度样本外回测报告等文件。
2. 生成 `findings/decision_state_{date}.json`，每只股票统一包含 thesis、factor、backtest、execution、controller、visual_notes 六层。
3. `dashboard_writer.py` 先只加载这个文件进 context，给后续 dashboard 可视化优化 agent 用，不改变现有页面显示。

边界：

- 不修改 `agents/backtest_*`、`scripts/*backtest*`、`scripts/weekly_*` 的回测计算逻辑。
- 如果实施过程中发现回测引擎、因子验证或交易规则存在问题，只记录到 `docs/TODO.md` 或本计划的后续优化备注，不在本阶段顺手修改。
- 不新增网络抓取。
- 不自动下单。
- 不把所有证据压成一个黑箱总分。

## File Structure

| 文件 | 类型 | 职责 |
| --- | --- | --- |
| `agents/decision_state_hub.py` | 新建 | 读取现有 artifacts，构建并写出 `decision_state_{date}.json` |
| `tests/test_decision_state_hub.py` | 新建 | 覆盖完整数据、缺失数据、冲突降级、CLI 写文件、dashboard-safe 字段 |
| `agents/dashboard_writer.py` | 修改 | 新增 `load_decision_state()`，在 `build_dashboard_context()` 中放入 `decision_state` |
| `tests/test_dashboard_writer.py` | 修改 | 验证 dashboard context 能加载 decision state，缺失时安全降级 |
| `docs/superpowers/specs/2026-05-31-decision-state-hub-design.md` | 已有 | 作为实施约束，不再扩写大段英文 |

## Target JSON Shape

`findings/decision_state_{date}.json` 第一版结构固定为：

```json
{
  "date": "2026-06-01",
  "generated_at": "2026-06-01T09:20:00+08:00",
  "symbols": {
    "NVDA": {
      "identity": {
        "symbol": "NVDA",
        "date": "2026-06-01",
        "market_phase": "premarket",
        "track": "swing",
        "source_freshness": {
          "premarket_summary": {"status": "fresh", "path": "findings/premarket_summary_2026-06-01_NVDA.json"},
          "entry_decision": {"status": "fresh", "path": "findings/entry_decision_2026-06-01.json"},
          "factor_ic_report": {"status": "available", "path": "findings/factor_ic_report.json"},
          "weekly_oos": {"status": "available", "path": "findings/weekly_oos_validation_results.json"}
        }
      },
      "thesis": {
        "base_thesis": "等待盘前确认",
        "key_catalysts": [],
        "main_risks": [],
        "contradictions": [],
        "llm_confidence": null,
        "llm_confidence_reason": "未找到可用 thesis 字段",
        "verdict": "insufficient"
      },
      "factor_evidence": {
        "factor_scores": {},
        "factor_direction": "neutral",
        "factor_quality": "unavailable",
        "factor_notes": ["未找到因子 IC 报告"]
      },
      "backtest_evidence": {
        "strategy_family": "weekly_rebalance",
        "matched_signal_set": "default",
        "in_sample_summary": {},
        "out_of_sample_summary": {},
        "drawdown_profile": {},
        "parameter_stability": "unknown",
        "backtest_verdict": "unavailable",
        "backtest_notes": ["未找到周度样本外验证报告"]
      },
      "execution": {
        "current_price": null,
        "entry_zone": null,
        "stop_level": null,
        "target_zone": null,
        "wait_conditions": [],
        "action_state": "monitor",
        "action_reason": "等待更多证据",
        "position_context": "no_position"
      },
      "controller": {
        "controller_verdict": "monitor",
        "controller_confidence": 35,
        "evidence_alignment": "insufficient",
        "required_human_check": ["确认 thesis 和交易节点是否已刷新"],
        "blocked_by": ["missing_thesis", "missing_backtest"],
        "summary_for_dashboard": "证据不足，先观察"
      },
      "visual_notes": {
        "primary_action": "观察",
        "why_now": ["证据不足"],
        "risk_flag": "caution",
        "evidence_alignment": "insufficient",
        "missing_inputs": ["thesis", "backtest"],
        "level_map": {"entry": null, "stop": null, "target": null, "wait": []},
        "review_questions": ["今天的 thesis、节点、回测证据是否都已刷新？"]
      }
    }
  }
}
```

### Task 1: 新建 hub 测试骨架和完整样例

**Files:**
- Create: `tests/test_decision_state_hub.py`

- [ ] **Step 1: 写入失败测试文件**

Create `tests/test_decision_state_hub.py` with this content:

```python
import json
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_symbol_state_uses_existing_artifacts(tmp_path):
    from agents.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(findings / f"premarket_summary_{date}_NVDA.json", {
        "symbol": "NVDA",
        "date": date,
        "track": "swing",
        "thesis": {
            "base_thesis": "AI demand remains strong",
            "key_catalysts": ["earnings follow-through"],
            "main_risks": ["valuation compression"],
            "today_falsification": "breaks premarket support"
        },
        "entry": {
            "entry_base": 100.0,
            "target_price": 112.0,
            "stop_loss": 94.0,
            "sizing": "normal"
        },
        "exit": {
            "hard_stop": 94.0,
            "target_price": 112.0
        },
        "market_context": {
            "phase": "premarket"
        }
    })
    _write_json(findings / f"entry_decision_{date}.json", {
        "date": date,
        "decisions": {
            "NVDA": {
                "decision": "可入场",
                "confidence": "高",
                "hard_vetoes": [],
                "soft_vetoes": []
            }
        }
    })
    _write_json(findings / "factor_ic_report.json", {
        "factors": {
            "volatility_20d": {
                "mean_ic": 0.0553,
                "ir": 0.2088,
                "t_stat": 2.18,
                "positive_weeks_pct": 61.5,
                "sample_weeks": 26
            },
            "sentiment_catalyst": {
                "mean_ic": 0.09,
                "sample_weeks": 2
            }
        }
    })
    _write_json(findings / "weekly_oos_validation_results.json", {
        "time_oos": {"return_pct": 57.18, "max_drawdown_pct": -5.78, "alpha_pct": 15.94},
        "style_oos": {"return_pct": 98.25, "alpha_pct": -23.64},
        "full_lifecycle": {"return_pct": 129.87, "max_drawdown_pct": -26.95}
    })

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert state["date"] == date
    assert nvda["identity"]["symbol"] == "NVDA"
    assert nvda["thesis"]["verdict"] == "supportive"
    assert nvda["factor_evidence"]["factor_quality"] == "usable"
    assert nvda["backtest_evidence"]["backtest_verdict"] == "supportive"
    assert nvda["execution"]["action_state"] == "act"
    assert nvda["controller"]["evidence_alignment"] == "aligned"
    assert nvda["visual_notes"]["primary_action"] == "可入场"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_build_symbol_state_uses_existing_artifacts -q
```

Expected: fails with `ModuleNotFoundError: No module named 'agents.decision_state_hub'`.

### Task 2: 实现 Decision State Hub 纯构建器

**Files:**
- Create: `agents/decision_state_hub.py`
- Test: `tests/test_decision_state_hub.py`

- [ ] **Step 1: 新建最小实现**

Create `agents/decision_state_hub.py` with this content:

```python
import argparse
import glob
import json
import os
from datetime import datetime, timezone
from typing import Any


_POSSIBLE_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = _POSSIBLE_BASE if os.path.exists(os.path.join(_POSSIBLE_BASE, "templates")) else os.path.expanduser("~/stock_team")


def _load_json(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _source_status(path: str, expected_date: str | None = None) -> dict[str, Any]:
    if not os.path.exists(path):
        return {"status": "missing", "path": _rel(path)}
    status = "available"
    if expected_date and expected_date not in os.path.basename(path):
        status = "stale"
    else:
        status = "fresh" if expected_date else "available"
    return {"status": status, "path": _rel(path)}


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path, BASE).replace("\\", "/")
    except Exception:
        return path.replace("\\", "/")


def _premarket_path(find_dir: str, date: str, sym: str) -> str:
    return os.path.join(find_dir, f"premarket_summary_{date}_{sym.upper()}.json")


def _entry_decision_path(find_dir: str, date: str) -> str:
    return os.path.join(find_dir, f"entry_decision_{date}.json")


def _extract_thesis(premarket: dict[str, Any]) -> dict[str, Any]:
    thesis = premarket.get("thesis") if isinstance(premarket.get("thesis"), dict) else {}
    strategic = premarket.get("strategic_context") if isinstance(premarket.get("strategic_context"), dict) else {}
    base = (
        thesis.get("base_thesis")
        or thesis.get("summary")
        or strategic.get("base_thesis")
        or strategic.get("strategic_stance")
    )
    catalysts = thesis.get("key_catalysts") or strategic.get("key_catalysts") or []
    risks = thesis.get("main_risks") or strategic.get("main_risks") or []
    contradictions = []
    falsification = thesis.get("today_falsification") or strategic.get("falsification")
    if falsification:
        contradictions.append(str(falsification))
    verdict = "supportive" if base else "insufficient"
    return {
        "base_thesis": base or "未找到可用 thesis 字段",
        "key_catalysts": catalysts if isinstance(catalysts, list) else [str(catalysts)],
        "main_risks": risks if isinstance(risks, list) else [str(risks)],
        "contradictions": contradictions,
        "llm_confidence": strategic.get("unified_confidence"),
        "llm_confidence_reason": "来自 premarket_summary/strategic_context" if base else "未找到可用 thesis 字段",
        "verdict": verdict,
    }


def _factor_quality(report: dict[str, Any]) -> tuple[dict[str, Any], str, str, list[str]]:
    factors = report.get("factors") if isinstance(report.get("factors"), dict) else {}
    if not factors:
        return {}, "neutral", "unavailable", ["未找到因子 IC 报告"]

    notes: list[str] = []
    usable_count = 0
    strong_count = 0
    for name, data in factors.items():
        if not isinstance(data, dict):
            continue
        sample_weeks = int(data.get("sample_weeks") or data.get("weeks") or 0)
        mean_ic = float(data.get("mean_ic") or 0)
        t_stat = float(data.get("t_stat") or 0)
        if sample_weeks and sample_weeks < 8:
            notes.append(f"{name} 样本周数不足: {sample_weeks}")
        if abs(mean_ic) >= 0.03 and sample_weeks >= 8:
            usable_count += 1
        if abs(mean_ic) >= 0.05 and abs(t_stat) >= 2 and sample_weeks >= 12:
            strong_count += 1

    if strong_count:
        quality = "strong"
        direction = "supportive"
    elif usable_count:
        quality = "usable"
        direction = "supportive"
    else:
        quality = "weak"
        direction = "neutral"
    if not notes:
        notes.append("因子报告可用，未发现低样本提示")
    return factors, direction, quality, notes


def _extract_factor_evidence(find_dir: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = os.path.join(find_dir, "factor_ic_report.json")
    report = _load_json(path)
    scores, direction, quality, notes = _factor_quality(report)
    return {
        "factor_scores": scores,
        "factor_direction": direction,
        "factor_quality": quality,
        "factor_notes": notes,
    }, _source_status(path)


def _extract_backtest_evidence(find_dir: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = os.path.join(find_dir, "weekly_oos_validation_results.json")
    report = _load_json(path)
    if not report:
        return {
            "strategy_family": "weekly_rebalance",
            "matched_signal_set": "default",
            "in_sample_summary": {},
            "out_of_sample_summary": {},
            "drawdown_profile": {},
            "parameter_stability": "unknown",
            "backtest_verdict": "unavailable",
            "backtest_notes": ["未找到周度样本外验证报告"],
        }, _source_status(path)

    time_oos = report.get("time_oos") or report.get("time_oos_validation") or {}
    style_oos = report.get("style_oos") or report.get("style_oos_validation") or {}
    full = report.get("full_lifecycle") or report.get("full_period") or {}
    alpha = float(time_oos.get("alpha_pct") or 0) if isinstance(time_oos, dict) else 0.0
    style_alpha = float(style_oos.get("alpha_pct") or 0) if isinstance(style_oos, dict) else 0.0
    verdict = "supportive" if alpha > 0 else "caution"
    notes = ["time-OOS alpha 为正"] if alpha > 0 else ["time-OOS alpha 不占优"]
    if style_alpha < 0:
        notes.append("style-OOS alpha 为负，需要在 dashboard 中保持可见")
    return {
        "strategy_family": "weekly_rebalance",
        "matched_signal_set": "default",
        "in_sample_summary": full if isinstance(full, dict) else {},
        "out_of_sample_summary": {
            "time_oos": time_oos if isinstance(time_oos, dict) else {},
            "style_oos": style_oos if isinstance(style_oos, dict) else {},
        },
        "drawdown_profile": {
            "full_lifecycle_max_drawdown_pct": full.get("max_drawdown_pct") if isinstance(full, dict) else None,
            "time_oos_max_drawdown_pct": time_oos.get("max_drawdown_pct") if isinstance(time_oos, dict) else None,
        },
        "parameter_stability": "unknown",
        "backtest_verdict": verdict,
        "backtest_notes": notes,
    }, _source_status(path)


def _extract_execution(sym: str, premarket: dict[str, Any], entry_file: dict[str, Any]) -> dict[str, Any]:
    entry = premarket.get("entry") if isinstance(premarket.get("entry"), dict) else {}
    exit_data = premarket.get("exit") if isinstance(premarket.get("exit"), dict) else {}
    decisions = entry_file.get("decisions") if isinstance(entry_file.get("decisions"), dict) else {}
    dec = decisions.get(sym.upper()) if isinstance(decisions.get(sym.upper()), dict) else {}
    decision_text = str(dec.get("decision") or "").strip()

    if decision_text == "可入场":
        action_state = "act"
        action_reason = "entry_decision 标记为可入场"
    elif decision_text == "不入场":
        action_state = "avoid"
        action_reason = "entry_decision 标记为不入场"
    elif decision_text:
        action_state = "wait"
        action_reason = f"entry_decision 标记为{decision_text}"
    else:
        action_state = "monitor"
        action_reason = "未找到 entry_decision"

    return {
        "current_price": premarket.get("current_price"),
        "entry_zone": entry.get("entry_base") or entry.get("entry_base_adj"),
        "stop_level": exit_data.get("hard_stop") or entry.get("stop_loss"),
        "target_zone": exit_data.get("target_price") or entry.get("target_price"),
        "wait_conditions": dec.get("soft_vetoes") or [],
        "action_state": action_state,
        "action_reason": action_reason,
        "position_context": premarket.get("position_context") or "no_position",
    }


def _controller(thesis: dict[str, Any], factor: dict[str, Any], backtest: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    blocked_by: list[str] = []
    required: list[str] = []
    if thesis.get("verdict") == "insufficient":
        blocked_by.append("missing_thesis")
        required.append("确认 thesis 是否已刷新")
    if factor.get("factor_quality") in {"unavailable", "weak"}:
        blocked_by.append("weak_or_missing_factor")
        required.append("确认因子证据是否足够")
    if backtest.get("backtest_verdict") in {"unavailable", "reject"}:
        blocked_by.append("missing_or_rejected_backtest")
        required.append("确认回测证据是否可用")

    if blocked_by:
        alignment = "insufficient"
        confidence = 35
    elif backtest.get("backtest_verdict") == "caution" or factor.get("factor_quality") == "usable":
        alignment = "mixed"
        confidence = 55
    else:
        alignment = "aligned"
        confidence = 70

    verdict = execution.get("action_state") or "monitor"
    if blocked_by and verdict == "act":
        verdict = "wait"
    summary = {
        "act": "证据对齐，可按计划执行",
        "wait": "等待条件确认",
        "monitor": "证据不足，先观察",
        "avoid": "风险或门控不允许，避免交易",
    }.get(verdict, "等待人工确认")
    return {
        "controller_verdict": verdict,
        "controller_confidence": confidence,
        "evidence_alignment": alignment,
        "required_human_check": required,
        "blocked_by": blocked_by,
        "summary_for_dashboard": summary,
    }


def _visual_notes(controller: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    action_label = {
        "act": "可入场",
        "wait": "等待",
        "monitor": "观察",
        "avoid": "不入场",
    }.get(controller.get("controller_verdict"), "观察")
    risk_flag = "blocked" if controller.get("blocked_by") else ("caution" if controller.get("evidence_alignment") != "aligned" else "none")
    return {
        "primary_action": action_label,
        "why_now": [controller.get("summary_for_dashboard")],
        "risk_flag": risk_flag,
        "evidence_alignment": controller.get("evidence_alignment"),
        "missing_inputs": controller.get("blocked_by", []),
        "level_map": {
            "entry": execution.get("entry_zone"),
            "stop": execution.get("stop_level"),
            "target": execution.get("target_zone"),
            "wait": execution.get("wait_conditions", []),
        },
        "review_questions": controller.get("required_human_check", []),
    }


def build_symbol_state(date: str, sym: str, base_dir: str = BASE) -> dict[str, Any]:
    find_dir = os.path.join(base_dir, "findings")
    pm_path = _premarket_path(find_dir, date, sym)
    entry_path = _entry_decision_path(find_dir, date)
    premarket = _load_json(pm_path)
    entry_file = _load_json(entry_path)
    factor, factor_src = _extract_factor_evidence(find_dir)
    backtest, backtest_src = _extract_backtest_evidence(find_dir)
    thesis = _extract_thesis(premarket)
    execution = _extract_execution(sym, premarket, entry_file)
    controller = _controller(thesis, factor, backtest, execution)
    visual = _visual_notes(controller, execution)
    market_context = premarket.get("market_context") if isinstance(premarket.get("market_context"), dict) else {}
    return {
        "identity": {
            "symbol": sym.upper(),
            "date": date,
            "market_phase": market_context.get("phase") or premarket.get("market_phase") or "unknown",
            "track": premarket.get("track") or "swing",
            "source_freshness": {
                "premarket_summary": _source_status(pm_path, date),
                "entry_decision": _source_status(entry_path, date),
                "factor_ic_report": factor_src,
                "weekly_oos": backtest_src,
            },
        },
        "thesis": thesis,
        "factor_evidence": factor,
        "backtest_evidence": backtest,
        "execution": execution,
        "controller": controller,
        "visual_notes": visual,
    }


def _discover_symbols(date: str, base_dir: str = BASE) -> list[str]:
    find_dir = os.path.join(base_dir, "findings")
    symbols: set[str] = set()
    for path in glob.glob(os.path.join(find_dir, f"premarket_summary_{date}_*.json")):
        name = os.path.basename(path)
        sym = name.removeprefix(f"premarket_summary_{date}_").removesuffix(".json")
        if sym:
            symbols.add(sym.upper())
    entry = _load_json(_entry_decision_path(find_dir, date))
    decisions = entry.get("decisions") if isinstance(entry.get("decisions"), dict) else {}
    symbols.update(str(s).upper() for s in decisions)
    return sorted(symbols)


def build_decision_state(date: str, symbols: list[str] | None = None, base_dir: str = BASE) -> dict[str, Any]:
    chosen = [s.upper() for s in symbols] if symbols else _discover_symbols(date, base_dir)
    return {
        "date": date,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "symbols": {sym: build_symbol_state(date, sym, base_dir=base_dir) for sym in chosen},
    }


def write_decision_state(date: str, symbols: list[str] | None = None, base_dir: str = BASE) -> str:
    payload = build_decision_state(date=date, symbols=symbols, base_dir=base_dir)
    out_dir = os.path.join(base_dir, "findings")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"decision_state_{date}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build daily per-symbol decision state.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--base-dir", default=BASE)
    parser.add_argument("symbols", nargs="*")
    args = parser.parse_args(argv)
    out_path = write_decision_state(args.date, args.symbols or None, base_dir=args.base_dir)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 运行完整样例测试**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py::test_build_symbol_state_uses_existing_artifacts -q
```

Expected: `1 passed`.

- [ ] **Step 3: 提交 Task 1-2**

Run:

```powershell
git add agents\decision_state_hub.py tests\test_decision_state_hub.py
git commit -m "feat: add decision state hub builder"
```

### Task 3: 补齐缺失数据、冲突降级和 CLI 写文件测试

**Files:**
- Modify: `tests/test_decision_state_hub.py`
- Modify: `agents/decision_state_hub.py`

- [ ] **Step 1: 添加缺失数据和 CLI 测试**

Append these tests to `tests/test_decision_state_hub.py`:

```python

def test_missing_sources_emit_valid_monitor_state(tmp_path):
    from agents.decision_state_hub import build_decision_state

    state = build_decision_state(date="2026-06-01", symbols=["MRVL"], base_dir=str(tmp_path))
    mrvl = state["symbols"]["MRVL"]

    assert mrvl["identity"]["source_freshness"]["premarket_summary"]["status"] == "missing"
    assert mrvl["thesis"]["verdict"] == "insufficient"
    assert mrvl["factor_evidence"]["factor_quality"] == "unavailable"
    assert mrvl["backtest_evidence"]["backtest_verdict"] == "unavailable"
    assert mrvl["execution"]["action_state"] == "monitor"
    assert mrvl["controller"]["controller_verdict"] == "monitor"
    assert mrvl["visual_notes"]["risk_flag"] == "blocked"


def test_controller_downgrades_action_when_evidence_missing(tmp_path):
    from agents.decision_state_hub import build_decision_state

    date = "2026-06-01"
    findings = tmp_path / "findings"
    _write_json(findings / f"entry_decision_{date}.json", {
        "decisions": {"NVDA": {"decision": "可入场", "confidence": "高"}}
    })

    state = build_decision_state(date=date, symbols=["NVDA"], base_dir=str(tmp_path))
    nvda = state["symbols"]["NVDA"]

    assert nvda["execution"]["action_state"] == "act"
    assert nvda["controller"]["controller_verdict"] == "wait"
    assert "missing_thesis" in nvda["controller"]["blocked_by"]
    assert nvda["visual_notes"]["primary_action"] == "等待"


def test_write_decision_state_creates_json_file(tmp_path):
    from agents.decision_state_hub import write_decision_state

    out = write_decision_state("2026-06-01", ["NVDA"], base_dir=str(tmp_path))
    payload = json.loads(Path(out).read_text(encoding="utf-8"))

    assert Path(out).name == "decision_state_2026-06-01.json"
    assert payload["symbols"]["NVDA"]["identity"]["symbol"] == "NVDA"
```

- [ ] **Step 2: 运行新增测试**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py -q
```

Expected: all tests pass.

- [ ] **Step 3: 如有失败，修正实现**

If `test_controller_downgrades_action_when_evidence_missing` fails because `visual_notes.primary_action` is still `可入场`, update `_visual_notes()` in `agents/decision_state_hub.py` to derive its label from `controller.controller_verdict`, not from `execution.action_state`. The implementation in Task 2 already does this:

```python
action_label = {
    "act": "可入场",
    "wait": "等待",
    "monitor": "观察",
    "avoid": "不入场",
}.get(controller.get("controller_verdict"), "观察")
```

- [ ] **Step 4: 提交 Task 3**

Run:

```powershell
git add agents\decision_state_hub.py tests\test_decision_state_hub.py
git commit -m "test: cover decision state missing evidence"
```

### Task 4: dashboard_writer 加载 Decision State 但不改 UI

**Files:**
- Modify: `agents/dashboard_writer.py`
- Modify: `tests/test_dashboard_writer.py`

- [ ] **Step 1: 先写 dashboard context 测试**

Append this test to `tests/test_dashboard_writer.py`:

```python

def test_dashboard_context_loads_decision_state_when_present(tmp_path):
    import json
    from pathlib import Path

    from agents.dashboard_writer import build_dashboard_context

    base = tmp_path
    findings = base / "findings"
    findings.mkdir(parents=True)
    date = "2026-06-01"
    (findings / f"decision_state_{date}.json").write_text(json.dumps({
        "date": date,
        "symbols": {
            "NVDA": {
                "controller": {
                    "controller_verdict": "wait",
                    "evidence_alignment": "insufficient"
                },
                "visual_notes": {
                    "primary_action": "等待",
                    "risk_flag": "blocked"
                }
            }
        }
    }, ensure_ascii=False), encoding="utf-8")

    ctx = build_dashboard_context(date, symbols=["NVDA"], base_dir=str(base))

    assert ctx["decision_state"]["date"] == date
    assert ctx["decision_state"]["symbols"]["NVDA"]["visual_notes"]["primary_action"] == "等待"


def test_dashboard_context_uses_empty_decision_state_when_missing(tmp_path):
    from agents.dashboard_writer import build_dashboard_context

    ctx = build_dashboard_context("2026-06-01", symbols=["NVDA"], base_dir=str(tmp_path))

    assert ctx["decision_state"] == {"date": "2026-06-01", "symbols": {}}
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests\test_dashboard_writer.py -k "decision_state" -q
```

Expected: fails because `decision_state` is not in dashboard context.

- [ ] **Step 3: 在 dashboard_writer.py 增加加载函数**

Add this function near the other load helpers in `agents/dashboard_writer.py`:

```python
def load_decision_state(date: str, base_dir: str = BASE) -> dict:
    path = os.path.join(base_dir, "findings", f"decision_state_{date}.json")
    data = _load(path)
    if isinstance(data, dict) and isinstance(data.get("symbols"), dict):
        return data
    return {"date": date, "symbols": {}}
```

- [ ] **Step 4: 在 build_dashboard_context() 返回值中加入字段**

Find the final dashboard context dictionary in `build_dashboard_context()` and add:

```python
"decision_state": load_decision_state(date, base_dir=base_dir),
```

If `build_dashboard_context()` uses an intermediate `ctx` dictionary, set it before return:

```python
ctx["decision_state"] = load_decision_state(date, base_dir=base_dir)
```

- [ ] **Step 5: 运行 dashboard decision state 测试**

Run:

```powershell
python -m pytest tests\test_dashboard_writer.py -k "decision_state" -q
```

Expected: both tests pass.

- [ ] **Step 6: 运行 dashboard writer smoke 测试**

Run:

```powershell
python -m pytest tests\test_dashboard_writer.py -q
```

Expected: all dashboard writer tests pass.

- [ ] **Step 7: 提交 Task 4**

Run:

```powershell
git add agents\dashboard_writer.py tests\test_dashboard_writer.py
git commit -m "feat: expose decision state to dashboard context"
```

### Task 5: CLI 烟测、文档备注和最终验证

**Files:**
- Modify: `docs/superpowers/specs/2026-05-31-decision-state-hub-design.md`
- No change: backtest engine files

- [ ] **Step 1: 运行 py_compile**

Run:

```powershell
python -m py_compile agents\decision_state_hub.py agents\dashboard_writer.py
```

Expected: command exits with code 0.

- [ ] **Step 2: 运行 hub 测试和 dashboard 关联测试**

Run:

```powershell
python -m pytest tests\test_decision_state_hub.py tests\test_dashboard_writer.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: 用临时目录烟测 CLI 写文件**

Run:

```powershell
$tmp = New-Item -ItemType Directory -Path ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "decision-state-hub-smoke-" + [System.Guid]::NewGuid().ToString()))
New-Item -ItemType Directory -Path (Join-Path $tmp.FullName "findings") | Out-Null
python agents\decision_state_hub.py --date 2026-06-01 --base-dir $tmp.FullName NVDA
Get-ChildItem (Join-Path $tmp.FullName "findings") -Filter "decision_state_2026-06-01.json"
```

Expected: output includes `decision_state_2026-06-01.json`.

- [ ] **Step 4: 确认没有误碰回测实现文件**

Run:

```powershell
git diff --name-only HEAD
```

Expected changed files are limited to:

```text
agents/decision_state_hub.py
agents/dashboard_writer.py
tests/test_decision_state_hub.py
tests/test_dashboard_writer.py
docs/superpowers/specs/2026-05-31-decision-state-hub-design.md
```

If `agents/backtest_*`, `scripts/*backtest*`, or `scripts/weekly_*` appears, stop and inspect before committing.

- [ ] **Step 5: 在 spec 顶部追加实施状态**

Add this short Chinese note under the existing Chinese summary in `docs/superpowers/specs/2026-05-31-decision-state-hub-design.md`:

```markdown
### 实施状态

第一版实现范围：新增 `agents/decision_state_hub.py` 生成 `findings/decision_state_{date}.json`，并让 `dashboard_writer.py` 加载该状态进 dashboard context。此阶段不改回测计算、不改 dashboard UI、不改变交易规则。
```

- [ ] **Step 6: 运行 repo hygiene**

Run:

```powershell
python scripts\check_repo_hygiene.py
git status --short
```

Expected: hygiene passes. `git status --short` only shows intentional source, test, or doc files before the final commit.

- [ ] **Step 7: 提交最终文档状态**

Run:

```powershell
git add docs\superpowers\specs\2026-05-31-decision-state-hub-design.md
git commit -m "docs: record decision state hub implementation scope"
```

## Final Verification

After all tasks are implemented, run:

```powershell
python -m py_compile agents\decision_state_hub.py agents\dashboard_writer.py
python -m pytest tests\test_decision_state_hub.py tests\test_dashboard_writer.py -q
python scripts\check_repo_hygiene.py
git status --short
```

Expected:

- `py_compile` exits 0.
- selected pytest suite passes.
- repo hygiene passes.
- worktree is clean after commits.

## Completion Handoff

Status: complete as of 2026-06-01.

Implemented commits:

- `d2cea54 feat: add decision state hub builder`
- `bc7f5ae fix: make decision state evidence status honest`
- `54f04e3 test: cover decision state missing evidence`
- `db6d563 feat: expose decision state to dashboard context`
- `cc3eec0 docs: record decision state hub implementation scope`
- `f4f593b fix: support capsule and stale decision sources`

Final delivered behavior:

- `agents/decision_state_hub.py` builds `findings/decision_state_{date}.json`.
- The hub reads flat and capsule `premarket_summary` paths.
- Malformed JSON is reported through `source_freshness` as `parse_error` or `invalid`.
- Stale premarket summaries are marked `stale` and block/downgrade the controller.
- Backtest `caution` no longer produces dashboard copy that says evidence is aligned.
- `dashboard_writer.py` loads `decision_state` into dashboard context without changing UI/templates.

Final verification:

- `python -m py_compile agents\decision_state_hub.py agents\dashboard_writer.py` passed.
- `python -m pytest tests\test_decision_state_hub.py tests\test_dashboard_writer.py -q` passed with 47 tests.
- CLI smoke wrote `decision_state_2026-06-01.json` in a temp `findings` directory.
- `python scripts\check_repo_hygiene.py` passed after deleting generated test/compile caches.
- Final code review approved the implementation and confirmed the previous capsule/stale findings were closed.

Non-blocking follow-ups:

- Decide later whether symbol auto-discovery should include stale symbols even when at least one current-date symbol exists.
- Decide later whether `backtest_verdict = caution` plus `entry_decision = 可入场` should remain actionable or always require human confirmation.

## Self-Review Notes

- Spec coverage: thesis, factor, backtest, execution, controller, visual notes, missing data, and dashboard data foundation are covered.
- Backtest boundary: this plan only reads existing backtest summary files and does not modify backtest engines or weekly validation scripts.
- Backtest/rule issues discovered during implementation should become TODO entries, not opportunistic logic changes.
- Visualization boundary: this plan produces `visual_notes` for the future dashboard optimization agent, but does not redesign UI.
- Type consistency: the plan consistently uses `build_decision_state()`, `build_symbol_state()`, `write_decision_state()`, `load_decision_state()`, and `decision_state_{date}.json`.
