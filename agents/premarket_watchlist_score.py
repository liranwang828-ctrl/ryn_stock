"""
premarket_watchlist_score.py
盘前关注列表 6 维评分模块（Task 1: score_stock）

6 维合计 100 分：
  Dim1  rs5       5日RS超额 vs SPY       20分
  Dim2  ma20_dev  MA20乖离率合理性       15分
  Dim3  analyst   分析师目标上行空间     20分
  Dim4  macro     宏观适配度             20分
  Dim5  narrative 今晚叙事命中           15分
  Dim6  vol       缩量下跌质量           10分
"""

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Optional

import yfinance as yf

# 项目根目录
_ROOT = Path(((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
_FUNDAMENTALS_DIR = _ROOT / "findings"
_BASE = _ROOT

# 常用配置文件路径
_CFG_PATH    = _ROOT / "config" / "daily_focus.json"
_MACRO_PATH  = _ROOT / "findings" / "macro.json"
_REGIME_PATH = _ROOT / "config" / "market_regime.json"
_POS_PATH    = _ROOT / "config" / "positions.json"

def _load_json(path: Path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

# 全局懒加载 —— 仅在需要时读取
_CFG    = None
_MACRO  = None
_REGIME = None
_POS    = None

def _get_cfg():
    global _CFG
    if _CFG is None:
        _CFG = _load_json(_CFG_PATH, {})
    return _CFG

def _get_macro():
    global _MACRO
    if _MACRO is None:
        _MACRO = _load_json(_MACRO_PATH, {})
    return _MACRO

def _get_regime():
    global _REGIME
    if _REGIME is None:
        _REGIME = _load_json(_REGIME_PATH, {})
    return _REGIME

def _get_pos():
    global _POS
    if _POS is None:
        raw = _load_json(_POS_PATH, {})
        # positions.json 结构: {"positions": {"SYM": {...}}}
        _POS = raw.get("positions", raw)
    return _POS


# ---------------------------------------------------------------------------
# Dim 1: 5日RS超额 vs SPY (20分)
# ---------------------------------------------------------------------------

def _rs5(sym: str) -> tuple[float, Optional[float]]:
    """返回 (sym_5d_return_pct, spy_5d_return_pct)，数据不足时返回 None。"""
    try:
        hist_sym = yf.Ticker(sym).history(period="10d")
        hist_spy = yf.Ticker("SPY").history(period="10d")
        if len(hist_sym) < 6 or len(hist_spy) < 6:
            return None, None
        sym_ret = (hist_sym["Close"].iloc[-1] - hist_sym["Close"].iloc[-6]) / hist_sym["Close"].iloc[-6] * 100
        spy_ret = (hist_spy["Close"].iloc[-1] - hist_spy["Close"].iloc[-6]) / hist_spy["Close"].iloc[-6] * 100
        return float(sym_ret), float(spy_ret)
    except Exception:
        return None, None


def _score_rs5(sym: str) -> tuple[int, float]:
    """返回 (score, rs5_value)；数据不足时 score=5 (中性), rs5=0.0。"""
    sym_ret, spy_ret = _rs5(sym)
    if sym_ret is None or spy_ret is None:
        return 5, 0.0
    rs5 = sym_ret - spy_ret
    if rs5 > 5:
        score = 20
    elif rs5 > 2:
        score = 15
    elif rs5 > 0:
        score = 10
    elif rs5 > -2:
        score = 5
    else:
        score = 0
    return score, rs5


# ---------------------------------------------------------------------------
# Dim 2: MA20乖离率合理性 (15分)
# ---------------------------------------------------------------------------

def _score_ma20_dev(sym: str) -> tuple[int, Optional[float]]:
    """返回 (score, dev_pct)；数据不足时 score=7 (中性), dev=None。"""
    try:
        hist = yf.Ticker(sym).history(period="30d")
        if len(hist) < 20:
            return 7, None
        ma20 = hist["Close"].iloc[-20:].mean()
        cur = hist["Close"].iloc[-1]
        dev = (cur - ma20) / ma20 * 100
        dev = float(dev)
        if -5 <= dev <= 5:
            score = 15
        elif -8 <= dev <= 8:
            score = 10
        elif -12 <= dev <= 0:
            score = 5
        else:
            score = 0
        return score, dev
    except Exception:
        return 7, None


# ---------------------------------------------------------------------------
# Dim 3: 分析师目标上行空间 (20分)
# ---------------------------------------------------------------------------

def _score_analyst(sym: str) -> tuple[int, Optional[float]]:
    """返回 (score, upside_pct)；数据不足时 score=8 (中性), upside=None。
    target_price 来自 JSON；当前价格用 yfinance 实时获取，避免使用陈旧的 JSON cur 字段。
    """
    try:
        fpath = _FUNDAMENTALS_DIR / f"fundamentals_{sym.upper()}.json"
        if not fpath.exists():
            return 8, None
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        target = data.get("target_price")
        if target is None:
            return 8, None
        # 实时价格，不用 JSON 中的 cur（可能是旧数据）
        try:
            h = yf.Ticker(sym).history(period="3d")["Close"]
            cur = float(h.iloc[-1]) if not h.empty else None
        except Exception:
            cur = None
        if cur is None or cur <= 0:
            return 8, None
        upside = (float(target) - cur) / cur * 100
        if upside > 20:
            score = 20
        elif upside > 10:
            score = 15
        elif upside > 0:
            score = 8
        else:
            score = 0
        return score, upside
    except Exception:
        return 8, None


# ---------------------------------------------------------------------------
# Dim 4: 宏观适配度 (20分)
# ---------------------------------------------------------------------------

def _parse_cpi(cpi_str) -> float:
    """将 '2.5%' 解析为 2.5；解析失败返回 0.0。"""
    try:
        return float(str(cpi_str).replace("%", "").strip())
    except Exception:
        return 0.0


def _score_macro(macro: dict, pos_cfg: Optional[dict]) -> tuple[int, int]:
    """返回 (score, headwind_count)。"""
    if pos_cfg is None or "macro_sensitivity" not in pos_cfg:
        return 20, 0

    sens = pos_cfg["macro_sensitivity"]
    headwinds = 0

    yield_curve = macro.get("yield_curve", "正常")
    dxy = float(macro.get("dxy", 100))
    cpi = _parse_cpi(macro.get("cpi_latest", "0%"))
    macro_score = float(macro.get("macro_score", 5))

    if sens.get("rate_up") == "负" and yield_curve == "倒挂":
        headwinds += 1
    if sens.get("dollar_strong") == "负" and dxy > 103:
        headwinds += 1
    if sens.get("inflation") == "负" and cpi > 3.5:
        headwinds += 1
    if sens.get("recession") == "负" and macro_score <= 3:
        headwinds += 1

    if headwinds == 0:
        score = 20
    elif headwinds == 1:
        score = 12
    elif headwinds == 2:
        score = 5
    else:
        score = 0

    return score, headwinds


# ---------------------------------------------------------------------------
# Dim 5: 今晚叙事命中 (15分)
# ---------------------------------------------------------------------------

def _score_narrative(sym: str, regime: dict) -> int:
    """返回 score：叙事命中得 15 分，否则 0 分。"""
    overnight = regime.get("overnight_signal", "")
    if sym.upper() in overnight.upper():
        return 15
    return 0


# ---------------------------------------------------------------------------
# Dim 6: 缩量下跌质量 (10分)
# ---------------------------------------------------------------------------

def _score_vol(sym: str) -> tuple[int, float]:
    """返回 (score, vol_ratio)；数据不足时 score=4 (中性), vol_ratio=1.0。"""
    try:
        hist = yf.Ticker(sym).history(period="15d")
        if len(hist) < 12:
            return 4, 1.0
        today_vol = float(hist["Volume"].iloc[-1])
        avg_vol = float(hist["Volume"].iloc[-11:-1].mean())
        if avg_vol <= 0:
            return 4, 1.0
        vol_ratio = today_vol / avg_vol
        today_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        price_down = today_close < prev_close

        if price_down and vol_ratio < 0.8:
            score = 10
        elif vol_ratio < 0.8:
            score = 6
        elif vol_ratio < 1.0:
            score = 3
        else:
            score = 0

        return score, float(vol_ratio)
    except Exception:
        return 4, 1.0


# ---------------------------------------------------------------------------
# 主接口
# ---------------------------------------------------------------------------

def score_stock(
    sym: str,
    macro: dict,
    regime: dict,
    pos_cfg: Optional[dict] = None,
) -> dict:
    """对单支股票进行 6 维评分。

    Parameters
    ----------
    sym      : 股票代码（如 'RKLB'）
    macro    : 宏观数据字典，来自 findings/macro.json
    regime   : 市场状态字典，来自 config/market_regime.json
    pos_cfg  : 个股配置（含 macro_sensitivity），可选

    Returns
    -------
    dict with keys:
        sym, score, breakdown, summary, macro_note,
        rs5, ma20_dev, upside, vol_ratio, narrative_hit
    """
    # --- Dim 1
    rs5_score, rs5_val = _score_rs5(sym)

    # --- Dim 2
    ma20_score, ma20_dev_val = _score_ma20_dev(sym)

    # --- Dim 3
    analyst_score, upside_val = _score_analyst(sym)

    # --- Dim 4
    macro_score_val, headwinds = _score_macro(macro, pos_cfg)

    # --- Dim 5
    narrative_score = _score_narrative(sym, regime)
    narrative_hit = narrative_score > 0

    # --- Dim 6
    vol_score, vol_ratio_val = _score_vol(sym)

    total = rs5_score + ma20_score + analyst_score + macro_score_val + narrative_score + vol_score

    breakdown = {
        "rs5":      rs5_score,
        "ma20_dev": ma20_score,
        "analyst":  analyst_score,
        "macro":    macro_score_val,
        "narrative": narrative_score,
        "vol":      vol_score,
    }

    # 摘要文字
    facts = []
    if narrative_hit:
        facts.append(f"叙事命中({regime.get('overnight_signal', '')[:30]})")
    if rs5_val > 2:
        facts.append(f"RS5超额{rs5_val:.1f}%")
    if upside_val is not None and upside_val > 10:
        facts.append(f"目标上行{upside_val:.1f}%")
    if headwinds >= 2:
        facts.append(f"宏观逆风{headwinds}项")
    if vol_ratio_val < 0.8:
        facts.append(f"缩量({vol_ratio_val:.2f}x)")
    summary = " | ".join(facts) if facts else "无特殊信号"

    macro_note = f"逆风{headwinds}项 | regime={regime.get('regime', 'unknown')}"

    return {
        "sym":          sym.upper(),
        "score":        total,
        "breakdown":    breakdown,
        "summary":      summary,
        "macro_note":   macro_note,
        "rs5":          rs5_val,
        "ma20_dev":     ma20_dev_val,
        "upside":       upside_val,
        "vol_ratio":    vol_ratio_val,
        "narrative_hit": narrative_hit,
    }


# ---------------------------------------------------------------------------
# rank_watchlist
# ---------------------------------------------------------------------------

def rank_watchlist(
    symbols: list,
    macro: dict,
    regime: dict,
    n_top: int = 2,
    positions: Optional[dict] = None,
) -> list:
    """对 symbols 列表进行评分并按 score 降序排列，前 n_top 个标记 recommended=True。

    Parameters
    ----------
    symbols   : 股票代码列表
    macro     : 宏观数据字典
    regime    : 市场状态字典
    n_top     : 推荐标记数量（默认 2）
    positions : 个股配置字典 {SYM: pos_cfg}，None 时从 _POS_PATH 加载

    Returns
    -------
    list of score dicts，按 score 降序，每项含 recommended 字段
    """
    if positions is None:
        positions = _get_pos()

    results = []
    for sym in symbols:
        pos_cfg = positions.get(sym.upper()) if positions else None
        result = score_stock(sym, macro, regime, pos_cfg=pos_cfg)
        result["recommended"] = False
        results.append(result)

    results.sort(key=lambda r: r["score"], reverse=True)

    for i in range(min(n_top, len(results))):
        results[i]["recommended"] = True

    return results


# ---------------------------------------------------------------------------
# _fmt_ranked
# ---------------------------------------------------------------------------

def _fmt_ranked(ranked: list) -> str:
    """生成关注推荐格式化文本并返回，不产生打印副作用。"""
    today = date.today().strftime("%Y-%m-%d")
    lines = [f"\n【今日关注推荐】{today}\n"]

    rec_idx = 1
    candidates = []

    for item in ranked:
        sym   = item["sym"]
        score = item["score"]
        summary    = item.get("summary", "") or ""
        macro_note = item.get("macro_note", "") or ""

        if item.get("recommended"):
            lines.append(f"⭐ 推荐{rec_idx}: {sym}  {score}分")
            if summary:
                lines.append(f"   {summary}")
            if macro_note:
                lines.append(f"   {macro_note}")
            lines.append("")
            rec_idx += 1
        else:
            candidates.append(f"{sym} {score}分")

    if candidates:
        lines.append(f"候补: {' | '.join(candidates)}")

    lines.append("\n[确认推荐] 直接回车 / [覆盖] 输入代码如: LITE RKLB")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# interactive_select
# ---------------------------------------------------------------------------

def interactive_select(ranked: list) -> list:
    """交互式选择关注标的。

    打印 _fmt_ranked，等待用户输入：
    - 直接回车 → 返回 recommended=True 的标的
    - 输入代码（空格分隔）→ 返回用户指定顺序的标的

    Parameters
    ----------
    ranked : rank_watchlist 的输出

    Returns
    -------
    list of selected dicts
    """
    print(_fmt_ranked(ranked))
    user_input = input("> ").strip().upper()

    if not user_input:
        return [r for r in ranked if r.get("recommended")]

    # 构建 sym → dict 映射
    sym_map = {r["sym"]: r for r in ranked}

    selected = []
    for sym in user_input.split():
        if sym in sym_map:
            selected.append(sym_map[sym])
        else:
            # 用户指定了不在 ranked 中的代码，创建占位项
            selected.append({
                "sym":         sym,
                "score":       0,
                "recommended": True,
                "summary":     "用户覆盖选择",
                "macro_note":  "",
            })

    return selected


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="盘前关注列表评分与筛选")
    parser.add_argument("symbols", nargs="*", help="股票代码列表（空时用配置默认值）")
    parser.add_argument("--output", default="", help="输出 JSON 路径（相对 _BASE 或绝对路径）")
    parser.add_argument("--top", type=int, default=2, help="推荐数量（默认 2）")
    parser.add_argument("--no-interactive", action="store_true", help="跳过交互，直接输出")
    args = parser.parse_args()

    cfg    = _get_cfg()
    macro  = _get_macro()
    regime = _get_regime()

    symbols = args.symbols if args.symbols else cfg.get("default_symbols", [])
    if not symbols:
        # 回退：从 daily_focus 的 focus_stocks 取
        symbols = cfg.get("focus_stocks", [])

    ranked = rank_watchlist(symbols, macro, regime, n_top=args.top)

    if args.no_interactive:
        print(_fmt_ranked(ranked))
        selected = [r for r in ranked if r.get("recommended")]
    else:
        selected = interactive_select(ranked)

    print(f"\n✅ 今日关注: {' / '.join(r['sym'] for r in selected)}")

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = _BASE / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "date":       str(date.today()),
            "selected":   selected,
            "all_ranked": ranked,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"📄 已写入: {out_path}")


if __name__ == "__main__":
    main()
