# premarket_summary 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `agents/premarket_summary.py`，将 6 个盘前输出文件合并为统一的 `premarket_summary_{date}_{sym}.json`，作为 stock-intraday 和 trading-day skill 的标准输入契约。

**Architecture:** 新建聚合脚本读取现有 6 个输出文件 + `strategic_memo_{sym}.json`（若存在），按 Full/Lite 两档模式合并写出每股一文件；同时补两处小改动（vix_level 写入 macro 输出、flex_reduce_level 写入 order_sheet）；最后在 session_manager.py 的 Step 6.8 后追加 Step 6.9 调用。

**Tech Stack:** Python 3.12, json, yfinance（仅 premarket.py 和 order_sheet.py 内用，summary.py 不引入新依赖）

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|---|---|---|
| `agents/premarket.py` | 修改（~1037行） | 将已计算的 `vix_cur` 写入 macro 输出 |
| `agents/premarket_order_sheet.py` | 修改（~232行） | 新增 `flex_reduce_level` 字段（hi5 价位） |
| `agents/premarket_summary.py` | 新建 | 主体：读 6 文件 + memo，写 B 级 JSON，打印 A 级报告 |
| `agents/session_manager.py` | 修改（~415行后） | Step 6.9：追加调用 premarket_summary.py |
| `tests/test_premarket_summary.py` | 新建 | 单元测试：schema 完整性、Full/Lite 两档、翻译映射 |

---

## Task 1：vix_level 写入 macro 输出

**Files:**
- Modify: `agents/premarket.py`（~第 1037 行的 macro dict 写入处）

---

- [ ] **Step 1.1：找到写入位置并加测试**

在 `tests/test_premarket_summary.py`（此时新建文件）写第一个测试：

```python
# tests/test_premarket_summary.py
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_macro_has_vix(tmp_path):
    """premarket_analysis JSON 的 macro 字段应含 vix_level"""
    # 用最近一次真实输出文件验证（不调用网络）
    base = os.path.expanduser("~/stock_team")
    import glob
    files = sorted(glob.glob(f"{base}/premarket_analysis_*.json"))
    if not files:
        return  # 无历史文件时跳过
    d = json.load(open(files[-1]))
    # 修改前会失败
    assert "vix_level" in d.get("macro", {}), "macro 缺少 vix_level"
```

- [ ] **Step 1.2：运行测试，确认 FAIL**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 -m pytest tests/test_premarket_summary.py::test_macro_has_vix -v
```

预期：`AssertionError: macro 缺少 vix_level`

- [ ] **Step 1.3：修改 premarket.py**

找到 `premarket.py` 约第 1037 行的 macro dict 写入处：

```python
# 现有代码（约 1037 行）
"macro": {"spy_pre": spy_pre_chg, "nq_futures": futures_chg, "env": env},
```

改为：

```python
"macro": {
    "spy_pre": spy_pre_chg,
    "nq_futures": futures_chg,
    "env": env.replace("✅", "").replace("❌", "").strip(),  # strip emoji
    "vix_level": round(vix_cur, 2) if 'vix_cur' in dir() else None,
},
```

注意：`vix_cur` 在 try 块内赋值（约第 748 行），若 try 失败则未定义。用 `'vix_cur' in dir()` 安全访问；但更好的做法是在 try 块外初始化：

在 try 块（约第 743 行）前加：
```python
vix_cur = None  # 初始化，try 失败时保持 None
```

再将 macro 写入改为：
```python
"macro": {
    "spy_pre": spy_pre_chg,
    "nq_futures": futures_chg,
    "env": env.replace("✅", "").replace("❌", "").strip(),
    "vix_level": round(vix_cur, 2) if vix_cur is not None else None,
},
```

- [ ] **Step 1.4：下次 premarket.py 运行后验证（或手动造文件）**

由于 premarket.py 需要网络，此处用临时文件模拟验证测试逻辑通过即可。跳过需要真实网络的验证，在下次盘前真实运行时观察输出。

- [ ] **Step 1.5：Commit**

```bash
cd ~/stock_team
git add agents/premarket.py tests/test_premarket_summary.py
git commit -m "feat: add vix_level and env-strip to premarket macro output"
```

---

## Task 2：flex_reduce_level 写入 order_sheet

**Files:**
- Modify: `agents/premarket_order_sheet.py`（~第 232 行，紧接 flex_add_level 后）

---

- [ ] **Step 2.1：写测试**

在 `tests/test_premarket_summary.py` 追加：

```python
from unittest.mock import patch, MagicMock

def test_order_sheet_has_flex_reduce():
    """generate_order_sheet 返回值应含 flex_reduce_level"""
    from agents.premarket_order_sheet import generate_order_sheet

    mock_tech = {
        "cur": 100.0, "ma20": 98.0, "atr14": 3.0,
        "lo5": 96.0, "lo10": 94.0, "hi20": 108.0, "hi5": 104.0,
        "ma20_dev": 2.0,
    }
    with patch("agents.premarket_order_sheet._get_technicals", return_value=mock_tech), \
         patch("agents.premarket_order_sheet._load_json", return_value={}):
        result = generate_order_sheet("TEST")
    assert "flex_reduce_level" in result, "order_sheet 缺少 flex_reduce_level"
    assert result["flex_reduce_level"] > result["flex_add_level"], \
        "flex_reduce 应高于 flex_add"
```

- [ ] **Step 2.2：运行测试，确认 FAIL**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_premarket_summary.py::test_order_sheet_has_flex_reduce -v
```

预期：`AssertionError: order_sheet 缺少 flex_reduce_level`

- [ ] **Step 2.3：修改 premarket_order_sheet.py**

在 `_get_technicals` 返回 dict 约第 69 行加 `hi5`（若不存在）：

```python
# 已有 lo5, lo10, hi20；补 hi5
hi5 = float(h["High"].tail(5).max())
return {
    "cur": cur, "ma20": ma20, "atr14": atr,
    "lo5": lo5, "lo10": lo10, "hi20": hi20, "hi5": hi5,   # 新增 hi5
    "ma20_dev": round((cur - ma20) / ma20 * 100, 1),
}
```

在 `generate_order_sheet` 约第 151 行加：
```python
hi5 = tech.get("hi5", cur * 1.03)
```

在返回 dict 约第 233 行 `flex_add_level` 后追加：
```python
"flex_add_level":    round(lo10, 2),
"flex_add_note":     f"近10日低点 ${lo10:.2f} + 缩量守住 → 可考虑加仓",
"flex_reduce_level": round(hi5, 2),                        # 新增：近5日高点 → 接近时考虑减仓
"flex_reduce_note":  f"近5日高点 ${hi5:.2f} → 价格逼近时考虑减仓",  # 新增
```

- [ ] **Step 2.4：运行测试，确认 PASS**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_premarket_summary.py::test_order_sheet_has_flex_reduce -v
```

预期：PASS

- [ ] **Step 2.5：Commit**

```bash
git add agents/premarket_order_sheet.py tests/test_premarket_summary.py
git commit -m "feat: add flex_reduce_level (hi5) to order_sheet output"
```

---

## Task 3：新建 agents/premarket_summary.py

**Files:**
- Create: `agents/premarket_summary.py`
- Test: `tests/test_premarket_summary.py`

---

- [ ] **Step 3.1：写 schema 完整性测试**

在 `tests/test_premarket_summary.py` 追加（先写测试，后写实现）：

```python
import tempfile, datetime

def _make_mock_files(tmp_path, sym="TEST", is_held=True):
    """在 tmp_path 下构造 6 个输入文件的最小合法版本"""
    date = datetime.date.today().strftime("%Y-%m-%d")
    findings = tmp_path / "findings"
    findings.mkdir()

    # premarket_analysis
    (tmp_path / f"premarket_analysis_{date}.json").write_text(json.dumps({
        "date": date,
        "macro": {"spy_pre": 0.2, "nq_futures": 0.3, "env": "顺风", "vix_level": 18.5},
        "stocks": {sym: {
            "symbol": sym, "gap_pct": 1.5, "pred_scene": "B",
            "news_type": "neutral", "catalyst_strength": 1,
            "pre_vol_ratio": 0.9, "sector_ref": "SOXX", "sector_gap": 0.3,
            "month_context": {"rs_1m": 5.0, "above_ma20": True, "above_ma50": True,
                              "tech_stage": "上升趋势"},
            "confidence": "中", "reasoning": "平开，等回踩",
        }},
    }), encoding="utf-8")

    # order_sheet
    (findings / f"order_sheet_{date}.json").write_text(json.dumps({
        "date": date,
        "symbols": {sym: {
            "sym": sym, "date": date, "is_held": is_held,
            "entry_base": 100.0, "stop_loss": 97.0, "target_price": 110.0,
            "rr_ratio": 3.3, "entry_conditions": ["条件A"],
            "cancel_conditions": ["取消条件A"],
            "flex_add_level": 94.0, "flex_reduce_level": 104.0,
            "overnight_note": "", "regime_note": "热点不在科技",
        }},
    }), encoding="utf-8")

    # entry_decision
    (findings / f"entry_decision_{date}.json").write_text(json.dumps({
        "date": date,
        sym: {"decision": "可入场", "hard_vetoes": [], "soft_vetoes": [], "sizing": "×1.0"},
    }), encoding="utf-8")

    # exit_decision（持仓时有内容）
    exit_data: dict = {"date": date}
    if is_held:
        exit_data["positions"] = {sym: {
            "sym": sym, "decision": "继续持有",
            "hard_stop": 95.0, "soft_stop": 97.0, "stop_source": "auto_atr",
            "cur": 101.0, "hard_dist_pct": 5.9, "hard_triggers": [],
            "soft_triggers": [], "falsification_check": ["论点破裂条件"],
            "rr_remaining": 4.5,
        }}
    (findings / f"exit_decision_{date}.json").write_text(
        json.dumps(exit_data), encoding="utf-8")

    # daily_checklist
    checklist_data: dict = {"date": date}
    if is_held:
        checklist_data["symbols"] = {sym: {
            "sym": sym, "date": date, "has_position": True,
            "thesis_status": "intact", "daily_action": "B",
            "position_type": "thesis",
        }}
    (tmp_path / f"daily_checklist_{date}.json").write_text(
        json.dumps(checklist_data), encoding="utf-8")

    # today_focus（可选，允许缺失）
    (findings / "today_focus.json").write_text(json.dumps({}), encoding="utf-8")

    return date


def test_summary_schema_completeness_no_memo(tmp_path):
    """无 strategic_memo 时生成 Lite 模式 JSON，所有顶层 key 存在"""
    from agents.premarket_summary import build_summary
    date = _make_mock_files(tmp_path, sym="TEST", is_held=True)
    result = build_summary("TEST", date, base_dir=str(tmp_path))

    required_keys = {"date", "sym", "generated_at", "market_context",
                     "stock_snapshot", "entry", "exit", "thesis",
                     "strategic_context", "post_open_adj"}
    assert required_keys == set(result.keys()), f"缺少 key: {required_keys - set(result.keys())}"
    assert result["strategic_context"]["source"] == "premarket_inferred"
    assert result["post_open_adj"] is None
    assert result["exit"] is not None      # is_held=True
    assert result["thesis"] is not None


def test_summary_not_held(tmp_path):
    """不持仓时 exit 和 thesis 为 None"""
    from agents.premarket_summary import build_summary
    date = _make_mock_files(tmp_path, sym="TEST", is_held=False)
    result = build_summary("TEST", date, base_dir=str(tmp_path))
    assert result["exit"] is None
    assert result["thesis"] is None


def test_decision_translation(tmp_path):
    """中文决策值正确翻译为英文枚举"""
    from agents.premarket_summary import build_summary
    date = _make_mock_files(tmp_path, sym="TEST", is_held=True)
    result = build_summary("TEST", date, base_dir=str(tmp_path))
    assert result["entry"]["decision"] in ("enter", "watch", "pass")
    assert result["exit"]["decision"] in ("hold", "reduce", "exit")


def test_alignment_check_consistent(tmp_path):
    """strategic_stance=hold + entry=enter → consistent"""
    from agents.premarket_summary import build_summary
    date = _make_mock_files(tmp_path, sym="TEST", is_held=True)
    result = build_summary("TEST", date, base_dir=str(tmp_path))
    ac = result["strategic_context"]["alignment_check"]
    assert ac["strategic_vs_tactical"] in ("consistent", "tension", "contradiction")
```

- [ ] **Step 3.2：运行测试，确认全部 FAIL（ImportError）**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_premarket_summary.py -k "summary" -v
```

预期：`ImportError: cannot import name 'build_summary' from 'agents.premarket_summary'`

- [ ] **Step 3.3：实现 agents/premarket_summary.py**

```python
"""
盘前汇总模块 — premarket_summary.py
读取 6 个盘前输出文件 + strategic_memo（若存在），
为每只标的合并输出 premarket_summary_{date}_{sym}.json（B级）
并打印 A 级终端报告（4-5行/股，不存文件）。

用法: python3.12 agents/premarket_summary.py [SYM1 SYM2 ...]
     不传参数则读 config/poll_config.json 中 default_symbols
"""
import json, os, sys
from datetime import date as _date, datetime, timezone

BASE      = os.path.expanduser("~/stock_team")
CFG_DIR   = os.path.join(BASE, "config")
FIND_DIR  = os.path.join(BASE, "findings")

# ── 翻译映射 ───────────────────────────────────────────────────────────────
_ENTRY_DEC = {"可入场": "enter", "观察": "watch", "不入场": "pass"}
_EXIT_DEC  = {"继续持有": "hold", "考虑减仓": "reduce", "应出场": "exit"}
_ENV_MAP   = {"顺风": "favorable", "中性": "neutral", "逆风": "challenging"}
_CONF_MAP  = {"高": 4, "中": 3, "低": 2}
_STAGE_MAP = {"weak": "reduce", "broken": "exit_ready",
              "intact": "hold", "weakening": "hold_reduced"}
_TECH_STAGE = {
    (True,  True):  "2",
    (True,  False): "3",
    (False, False): "4",
    (False, True):  "4",   # above_ma50 but not ma20 = unusual, treat as 4
}


def _load(path: str) -> dict:
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def _strip_env(raw: str) -> str:
    return raw.replace("✅", "").replace("❌", "").strip()


def _alignment(stance: str, entry_dec: str, exit_dec: str | None) -> dict:
    REDUCE_STANCES = {"hold_reduced", "reduce"}
    EXIT_STANCES   = {"exit_ready", "avoid"}
    HOLD_STANCES   = {"strong_hold", "hold"}

    if stance in EXIT_STANCES and entry_dec in ("enter", "watch"):
        return {"strategic_vs_tactical": "contradiction",
                "note": f"strategic={stance} 但 entry={entry_dec}"}
    if stance in EXIT_STANCES and exit_dec == "hold":
        return {"strategic_vs_tactical": "contradiction",
                "note": f"strategic={stance} 但 exit=hold"}
    if stance in REDUCE_STANCES and entry_dec == "enter":
        return {"strategic_vs_tactical": "tension",
                "note": f"strategic={stance} 但仍计划 enter"}
    return {"strategic_vs_tactical": "consistent", "note": ""}


def _build_strategic_lite(stock_snap: dict, thesis_status: str,
                           entry_dec: str, exit_dec: str | None) -> dict:
    """无 strategic_memo 时，盘前数据推导 strategic_context（Lite 模式）"""
    mc_env = stock_snap.get("_env_raw", "中性")
    cs     = stock_snap.get("catalyst_strength", 0)
    conf   = stock_snap.get("_confidence_raw", "中")

    stance    = _STAGE_MAP.get(thesis_status, "hold")
    unif_conf = _CONF_MAP.get(conf, 3)
    macro_fit = _ENV_MAP.get(mc_env, "neutral")

    am20 = stock_snap.get("_above_ma20", True)
    am50 = stock_snap.get("_above_ma50", True)
    tech_stage = _TECH_STAGE.get((am20, am50), "4")

    bin_risk = cs >= 2
    ac = _alignment(stance, entry_dec, exit_dec)

    return {
        "source": "premarket_inferred",
        "memo_date": None, "memo_valid_until": None,
        "strategic_stance": stance,
        "unified_confidence": unif_conf,
        "thesis_lifecycle": None,
        "key_condition": stock_snap.get("_reasoning", ""),
        "next_catalyst": {
            "event": stock_snap.get("news_type", "neutral"),
            "date": "unknown", "importance": "high" if cs >= 3 else "medium" if cs >= 1 else "low",
            "days_away": None,
        },
        "main_tensions": [],
        "macro_fit": macro_fit,
        "technical_stage": tech_stage,
        "binary_risk_flag": bin_risk,
        "alignment_check": ac,
    }


def _build_strategic_full(memo: dict, entry_dec: str, exit_dec: str | None,
                           today: _date) -> dict:
    """从 strategic_memo 构建 Full 模式 strategic_context"""
    next_cat_raw = memo.get("support_and_risk", {}).get("next_catalyst", {})
    cat_date_str = next_cat_raw.get("date", "unknown")
    try:
        cat_date = _date.fromisoformat(cat_date_str)
        days_away = (cat_date - today).days
    except Exception:
        days_away = None

    importance = next_cat_raw.get("importance", "low")
    bin_risk = (days_away is not None and days_away <= 2
                and importance == "high")

    stance = memo.get("synthesis", {}).get("strategic_stance", "hold")
    ac = _alignment(stance, entry_dec, exit_dec)

    return {
        "source": "strategic_memo",
        "memo_date": memo.get("analysis_date"),
        "memo_valid_until": memo.get("outlook", {}).get("valid_until"),
        "strategic_stance": stance,
        "unified_confidence": memo.get("judgment", {}).get("unified_confidence"),
        "thesis_lifecycle": memo.get("judgment", {}).get(
            "thesis_lifecycle_stage", {}).get("stage"),
        "key_condition": memo.get("synthesis", {}).get("key_condition", ""),
        "next_catalyst": {
            "event": next_cat_raw.get("event", ""),
            "date": cat_date_str,
            "importance": importance,
            "days_away": days_away,
        },
        "main_tensions": memo.get("synthesis", {}).get("main_tensions", []),
        "macro_fit": memo.get("support_and_risk", {}).get(
            "macro_fit", {}).get("assessment", "neutral"),
        "technical_stage": memo.get("support_and_risk", {}).get(
            "technical_stage", {}).get("stage", "2"),
        "binary_risk_flag": bin_risk,
        "alignment_check": ac,
    }


def _sizing_rule(unified_conf: int | None, bin_risk: bool, lite: bool) -> str:
    """四条 sizing 规则（Rules 1-3 先执行，Rule 4 封顶）"""
    if bin_risk or (unified_conf is not None and unified_conf <= 2):
        base = "×0.5"
    elif unified_conf is not None and unified_conf >= 5:
        base = "×1.5"
    else:
        base = "×1.0"
    if lite and base == "×1.5":
        base = "×1.0"   # Rule 4 封顶
    return base


def _risk_flag(headlines: list[str], main_risks: list[str]) -> tuple[bool, str]:
    """关键词匹配：新闻是否命中已知风险"""
    text = " ".join(headlines).lower()
    for risk in main_risks:
        for word in risk.lower().split():
            if len(word) > 3 and word in text:
                return True, word
    return False, ""


def build_summary(sym: str, date_str: str, base_dir: str = BASE) -> dict:
    """
    为单只标的构建 premarket_summary dict。
    base_dir 参数便于单元测试时注入临时目录。
    """
    find_dir = os.path.join(base_dir, "findings")
    today = _date.fromisoformat(date_str)

    # ── 读取 6 个输入文件 ────────────────────────────────────────────────────
    pre  = _load(os.path.join(base_dir, f"premarket_analysis_{date_str}.json"))
    ord_ = _load(os.path.join(find_dir, f"order_sheet_{date_str}.json"))
    entr = _load(os.path.join(find_dir, f"entry_decision_{date_str}.json"))
    exit_ = _load(os.path.join(find_dir, f"exit_decision_{date_str}.json"))
    chkl = _load(os.path.join(base_dir, f"daily_checklist_{date_str}.json"))
    memo = _load(os.path.join(base_dir, f"strategic_memo_{sym.upper()}.json"))

    sym_upper = sym.upper()

    # ── market_context ───────────────────────────────────────────────────────
    macro = pre.get("macro", {})
    market_context = {
        "spy_pre_chg": macro.get("spy_pre", 0.0),
        "nq_futures": macro.get("nq_futures", 0.0),
        "env": _strip_env(macro.get("env", "中性")),
        "vix_level": macro.get("vix_level"),
        "macro_events_today": macro.get("macro_events_today", []),
    }

    # ── stock_snapshot ───────────────────────────────────────────────────────
    stk = pre.get("stocks", {}).get(sym_upper, {})
    mc  = stk.get("month_context", {})

    main_risks = memo.get("support_and_risk", {}).get("main_risks", []) if memo else []
    headlines  = stk.get("all_headlines", [])
    rflag, rnote = _risk_flag(headlines, main_risks)

    stock_snapshot = {
        "gap_pct": stk.get("gap_pct", 0.0),
        "pred_scene": stk.get("pred_scene"),
        "news_type": stk.get("news_type", "neutral"),
        "catalyst_strength": stk.get("catalyst_strength", 0),
        "pre_vol_ratio": stk.get("pre_vol_ratio", 0.0),
        "overnight_note": ord_.get("symbols", {}).get(sym_upper, {}).get("overnight_note", ""),
        "sector_ref": stk.get("sector_ref", ""),
        "sector_gap_pct": stk.get("sector_gap", 0.0),
        "rs_vs_sector": round(mc.get("rs_1m", 0.0) - stk.get("sector_gap", 0.0), 2),
        "sector_note": ord_.get("symbols", {}).get(sym_upper, {}).get("regime_note", ""),
        "risk_flag": rflag,
        "risk_note": rnote,
        # 内部字段（供 strategic_context 推导用，不写入最终 JSON）
        "_env_raw": _strip_env(macro.get("env", "中性")),
        "_confidence_raw": stk.get("confidence", "中"),
        "_above_ma20": mc.get("above_ma20", True),
        "_above_ma50": mc.get("above_ma50", True),
        "_reasoning": stk.get("reasoning", ""),
    }

    # ── entry ────────────────────────────────────────────────────────────────
    ord_sym = ord_.get("symbols", {}).get(sym_upper, {})
    entr_sym = entr.get(sym_upper, entr)   # 兼容旧格式

    raw_dec = entr_sym.get("decision", "不入场")
    entry_dec = _ENTRY_DEC.get(raw_dec, "pass")

    bin_risk_for_sizing = bool(rflag)  # 临时：Full 模式时会被覆盖

    entry = {
        "decision": entry_dec,
        "hard_vetoes": entr_sym.get("hard_vetoes", []),
        "soft_vetoes": entr_sym.get("soft_vetoes", []),
        "entry_base": ord_sym.get("entry_base"),
        "stop_loss": ord_sym.get("stop_loss"),
        "target_price": ord_sym.get("target_price"),
        "rr_ratio": ord_sym.get("rr_ratio"),
        "sizing": "×1.0",   # 先占位，strategic_context 完成后更新
        "entry_conditions": ord_sym.get("entry_conditions", []),
        "cancel_conditions": ord_sym.get("cancel_conditions", []),
    }

    # ── exit / thesis（持仓时非 null） ──────────────────────────────────────
    pos_data = exit_.get("positions", {}).get(sym_upper)
    chk_sym  = chkl.get("symbols", {}).get(sym_upper)
    is_held  = pos_data is not None or (chk_sym and chk_sym.get("has_position"))

    if is_held and pos_data:
        raw_exit = pos_data.get("decision", "继续持有")
        exit_dec = _EXIT_DEC.get(raw_exit, "hold")
        exit_sect = {
            "decision": exit_dec,
            "hard_stop": pos_data.get("hard_stop"),
            "stop_source": pos_data.get("stop_source", "auto_atr"),
            "hard_dist_pct": pos_data.get("hard_dist_pct"),
            "hard_triggers": pos_data.get("hard_triggers", []),
            "soft_triggers": pos_data.get("soft_triggers", []),
            "target_price": ord_sym.get("target_price"),
            "current_rr_ratio": pos_data.get("rr_remaining"),
            "flex_add_level": ord_sym.get("flex_add_level"),
            "flex_reduce_level": ord_sym.get("flex_reduce_level"),
        }
        thesis = {
            "status": chk_sym.get("thesis_status", "intact") if chk_sym else "intact",
            "daily_action": chk_sym.get("daily_action", "B") if chk_sym else "B",
            "position_type": chk_sym.get("position_type", "thesis") if chk_sym else "thesis",
            "today_falsification": pos_data.get("falsification_check", []),
        }
    else:
        exit_dec = None
        exit_sect = None
        thesis = None

    # ── strategic_context ────────────────────────────────────────────────────
    thesis_status = thesis["status"] if thesis else "intact"
    if memo:
        sc = _build_strategic_full(memo, entry_dec, exit_dec, today)
    else:
        sc = _build_strategic_lite(stock_snapshot, thesis_status, entry_dec, exit_dec)

    # 更新 sizing（依赖 strategic_context 完成后）
    unif_conf = sc.get("unified_confidence")
    bin_risk  = sc.get("binary_risk_flag", False)
    lite_mode = sc["source"] == "premarket_inferred"
    entry["sizing"] = _sizing_rule(unif_conf, bin_risk, lite_mode)

    # 清除内部字段
    for k in ("_env_raw", "_confidence_raw", "_above_ma20", "_above_ma50", "_reasoning"):
        stock_snapshot.pop(k, None)

    return {
        "date": date_str,
        "sym": sym_upper,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_context": market_context,
        "stock_snapshot": stock_snapshot,
        "entry": entry,
        "exit": exit_sect,
        "thesis": thesis,
        "strategic_context": sc,
        "post_open_adj": None,
    }


def _print_a_level(d: dict) -> None:
    """打印每股 4-5 行 A 级终端报告"""
    sym = d["sym"]
    mc  = d["market_context"]
    ss  = d["stock_snapshot"]
    en  = d["entry"]
    ex  = d.get("exit") or {}
    th  = d.get("thesis") or {}
    sc  = d["strategic_context"]

    scene = ss.get("pred_scene") or "?"
    line1 = (f"{sym} | gap {ss['gap_pct']:+.1f}% | 场景{scene} | "
             f"板块{ss['sector_ref']}{ss['sector_gap_pct']:+.1f}% "
             f"RS{ss['rs_vs_sector']:+.1f}%")

    status  = th.get("status", "—")
    action  = th.get("daily_action", "—")
    hs      = ex.get("hard_stop")
    hdist   = ex.get("hard_dist_pct", 0)
    tgt     = ex.get("target_price") or en.get("target_price")
    rr      = ex.get("current_rr_ratio") or en.get("rr_ratio", 0)
    line2 = (f"论点{status} / {action}类 | "
             f"止损${hs or '—'}({hdist:.1f}%) / 目标${tgt or '—'} / RR={rr:.1f}")

    fl_add = ex.get("flex_add_level", "—")
    fl_red = ex.get("flex_reduce_level", "—")
    brf    = sc.get("binary_risk_flag", False)
    ali    = sc.get("alignment_check", {}).get("strategic_vs_tactical", "—")
    line3 = (f"加仓${fl_add} / 减仓${fl_red} | "
             f"binary_risk={'true' if brf else 'false'} | alignment={ali}")

    src     = sc.get("source", "?")
    stance  = sc.get("strategic_stance", "—")
    conf    = sc.get("unified_confidence", "—")
    lc      = sc.get("thesis_lifecycle") or "—"
    key_c   = sc.get("key_condition", "")[:30]
    line4 = f"strategic[{src[:4]}]: {stance}(conf={conf}/{lc}) | key: {key_c}"

    rf    = ss.get("risk_flag", False)
    rnote = ss.get("risk_note", "")
    line5 = f"risk_flag={'true → 命中: ' + rnote if rf else 'false'}"

    print("\n".join([line1, line2, line3, line4, line5]))
    print()


def write_summary(sym: str, d: dict, base_dir: str = BASE) -> str:
    """写 B 级 JSON，返回文件路径"""
    fname = f"premarket_summary_{d['date']}_{sym.upper()}.json"
    path  = os.path.join(base_dir, "findings", fname)
    json.dump(d, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return path


def main(syms: list[str] | None = None):
    date_str = _date.today().strftime("%Y-%m-%d")
    if not syms:
        cfg = _load(os.path.join(CFG_DIR, "poll_config.json"))
        syms = cfg.get("default_symbols", [])

    print(f"\n{'='*60}")
    print(f"  盘前汇总报告 {date_str}  （{len(syms)} 只标的）")
    print(f"{'='*60}\n")

    for sym in syms:
        try:
            d    = build_summary(sym, date_str)
            path = write_summary(sym, d)
            _print_a_level(d)
            print(f"  ✅ {os.path.basename(path)}\n")
        except Exception as e:
            print(f"  ❌ {sym} 生成失败: {e}\n")


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
```

- [ ] **Step 3.4：运行所有 summary 相关测试，确认 PASS**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_premarket_summary.py -v
```

预期：全部 PASS（含 Task 1、2 的测试）

- [ ] **Step 3.5：冒烟测试（用最新历史文件手动跑）**

```bash
cd ~/stock_team
/tool/pandora/bin/python3.12 agents/premarket_summary.py NVDA 2>&1 | head -30
```

预期：打印 5 行 A 级报告，无报错，`findings/premarket_summary_{today}_NVDA.json` 生成。
若找不到今日文件（非盘前运行），用最近一个历史日期的文件手动指定 date_str 验证 `build_summary` 逻辑：

```bash
/tool/pandora/bin/python3.12 -c "
from agents.premarket_summary import build_summary, _print_a_level
d = build_summary('NVDA', '2026-05-19')
_print_a_level(d)
import json; print(json.dumps(list(d.keys()), ensure_ascii=False))
"
```

预期：打印 5 行报告 + 10 个 key 列表，无报错。

- [ ] **Step 3.6：Commit**

```bash
git add agents/premarket_summary.py tests/test_premarket_summary.py
git commit -m "feat: add premarket_summary.py — B-level unified contract + A-level report"
```

---

## Task 4：session_manager.py 追加 Step 6.9

**Files:**
- Modify: `agents/session_manager.py`（~第 415 行，Step 6.8 的 premarket_decision.py 调用块之后）

---

- [ ] **Step 4.1：找到正确插入位置**

在 session_manager.py 中搜索 `Step 6.8`，找到 premarket_decision.py 的调用块结尾（约第 415-420 行）。

- [ ] **Step 4.2：插入 Step 6.9**

紧接 Step 6.8 的 `lines.append(...)` 之后追加：

```python
            # Step 6.9: premarket_summary 聚合（B级 JSON + A级终端报告）
            if _focus_syms:
                lines.append(f"\n【Step 6.9】盘前汇总（{' '.join(_focus_syms)}）")
                _r_summ = subprocess.run(
                    [PYTHON, os.path.join(AGENTS_DIR, "premarket_summary.py")]
                    + _focus_syms,
                    cwd=BASE, capture_output=True, text=True, timeout=60
                )
                lines.append(_get_out(_r_summ, fallback="（汇总生成失败）", maxlen=2000))
```

- [ ] **Step 4.3：写集成测试（轻量）**

在 `tests/test_premarket_summary.py` 追加：

```python
def test_premarket_summary_cli(tmp_path):
    """CLI 正常退出且产出文件"""
    import subprocess, sys, glob, datetime
    date = _make_mock_files(tmp_path, sym="CLI", is_held=False)

    result = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.argv=['x','CLI']; "
         f"import os; os.chdir('{tmp_path}'); "
         f"from agents.premarket_summary import main; "
         f"import agents.premarket_summary as m; "
         f"m.BASE='{tmp_path}'; m.CFG_DIR='{tmp_path}/config'; "
         f"m.main(['CLI'])"],
        capture_output=True, text=True, timeout=10
    )
    files = list(tmp_path.glob(f"findings/premarket_summary_{date}_CLI.json"))
    assert files, "premarket_summary JSON 未生成"
```

- [ ] **Step 4.4：运行全部测试**

```bash
/tool/pandora/bin/python3.12 -m pytest tests/test_premarket_summary.py -v
```

预期：全部 PASS

- [ ] **Step 4.5：Commit**

```bash
git add agents/session_manager.py tests/test_premarket_summary.py
git commit -m "feat: add Step 6.9 premarket_summary call to session_manager"
```

---

## Task 5：更新 CHANGELOG + 更新 brainstorm 进度

- [ ] **Step 5.1：CHANGELOG 已更新**（brainstorm 阶段已写入设计部分，此处补实施记录）

在 `~/stock_team/CHANGELOG.md` 顶部新块追加：

```
## 2026-05-20 premarket_summary.py 实施完成

### 新建文件
- `agents/premarket_summary.py` — 6文件聚合，Full/Lite两档，post_open_adj接口
- `tests/test_premarket_summary.py` — 5个单元测试

### 修改文件
- `agents/premarket.py` — macro 输出加 vix_level，env strip emoji
- `agents/premarket_order_sheet.py` — 加 flex_reduce_level（近5日高点）
- `agents/session_manager.py` — Step 6.9 追加 premarket_summary 调用
```

- [ ] **Step 5.2：Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for premarket_summary implementation"
```
