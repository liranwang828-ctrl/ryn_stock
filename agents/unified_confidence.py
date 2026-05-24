"""
统一置信度引擎 — 把所有信号整合为一个数字
输入: ML分数 + CIO大师置信度 + 历史胜率 + 宏观状态 + 组合VaR
输出: 0-100 的统一置信度 + 推荐仓位比例

用法:
  from agents.unified_confidence import compute
  result = compute("NVDA")
"""
import os, json
_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
LRN  = os.path.join(BASE, "learning")

def compute(sym: str, track: str = "swing", strategy_data: dict = None) -> dict:
    """
    整合所有置信度来源，返回统一结论
    """
    scores = {}
    weights = {}

    # ── 1. ML 模型历史胜率 (weight: 0.25) ──────────────────────
    try:
        from agents.intuition_agent import get_intuition_for_premarket, score_symbol
        import yfinance as yf
        from learning.features import extract_intraday_features, extract_swing_features
        h = yf.Ticker(sym).history(period="60d")
        if not h.empty:
            fi = extract_intraday_features(h)
            fs = extract_swing_features(h)
            result = score_symbol(sym, {**fi, **fs})
            if result:
                ml_score = result.get(track, 0.5)
                scores["ml_model"] = ml_score * 100
                weights["ml_model"] = 0.25
    except Exception:
        pass

    # ── 2. CIO 大师置信度 (weight: 0.35) ───────────────────────
    try:
        # 优先使用传入的 strategy_data（来自并行 CIO rundir）
        if strategy_data and strategy_data.get("symbol") == sym:
            strategy = strategy_data
        else:
            from agents.protocol import STRATEGY_PATH
            strategy = json.load(open(STRATEGY_PATH, encoding="utf-8")) if os.path.exists(STRATEGY_PATH) else {}
        if strategy.get("symbol") == sym:
                cio_conf = strategy.get("confidence", 50)
                cio_sig  = strategy.get("signal", "neutral")
                # 转换为0-100 (bullish=高, bearish=低, neutral=50)
                if cio_sig == "bullish":
                    cio_score = 50 + cio_conf / 2
                elif cio_sig == "bearish":
                    cio_score = 50 - cio_conf / 2
                else:
                    cio_score = 50
                scores["cio"] = cio_score
                weights["cio"] = 0.35
    except Exception:
        pass

    # ── 3. 宏观状态调整 (weight: 0.20) ─────────────────────────
    try:
        import yfinance as yf
        from learning.features import get_macro_regime
        spy_h = yf.Ticker("SPY").history(period="1y")
        macro = get_macro_regime(spy_h, len(spy_h)-1)
        macro_score = {"ai_bull": 70, "recovery": 60, "normal": 50, "bear": 35}.get(macro, 50)
        scores["macro"] = macro_score
        weights["macro"] = 0.20
    except Exception:
        pass

    # ── 4. 组合风险惩罚 (weight: 0.10) ─────────────────────────
    portfolio_score = 60  # default neutral-positive
    try:
        import subprocess, re
        r = subprocess.run(
            [sys.executable,
             os.path.join(BASE, "agents", "portfolio_risk_agent.py"), "--summary-only"],
            cwd=BASE, capture_output=True, text=True, timeout=30
        )
        m = re.search(r'\((-[\d.]+)%\)', r.stdout)
        if m:
            var_pct = float(m.group(1))
            # 亏损越大，越扣分
            portfolio_score = max(20, 60 + var_pct * 2)  # -8% → 44分
    except Exception:
        pass
    scores["portfolio_risk"] = portfolio_score
    weights["portfolio_risk"] = 0.10

    # ── 5. 时间感知因子 (weight: 0.10) ─────────────────────────
    try:
        from agents.market_calendar import get_time_factor
        time_score = get_time_factor()
    except Exception:
        time_score = 60
    scores["time_factor"] = time_score
    weights["time_factor"] = 0.10

    # ── 加权平均 ─────────────────────────────────────────────────
    if not scores:
        return {"unified": 50, "sources": {}, "recommendation": "数据不足"}

    total_w = sum(weights.get(k, 0) for k in scores)
    if total_w == 0:
        unified = 50.0
    else:
        unified = sum(scores[k] * weights.get(k, 0) for k in scores) / total_w

    # 推荐仓位比例
    if unified >= 70:
        position_pct = "正常×1.5"
    elif unified >= 55:
        position_pct = "正常"
    elif unified >= 45:
        position_pct = "半仓"
    else:
        position_pct = "观望/极小仓"

    return {
        "sym": sym, "track": track,
        "unified": round(unified, 1),
        "sources": {k: round(v, 1) for k, v in scores.items()},
        "weights": weights,
        "recommendation": position_pct,
    }

def format_output(result: dict) -> str:
    lines = [f"【统一置信度】{result['sym']} {result['track']}"]
    lines.append(f"  综合: {result['unified']:.0f}/100  → 仓位建议: {result['recommendation']}")
    for src, score in result.get("sources", {}).items():
        w = result.get("weights", {}).get(src, 0)
        lines.append(f"  {src:18} {score:5.1f}分  权重{w:.0%}")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    track = sys.argv[2] if len(sys.argv) > 2 else "swing"
    result = compute(sym, track)
    print(format_output(result))
