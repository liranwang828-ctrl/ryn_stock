import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import (BASE, VERIFIED_PATH, BOARD_PATH, FINDINGS_DIR,
                              make_finding, make_revision, compute_phase2_response)

def _recent_2d_change(symbol):
    """计算近2日收盘涨跌幅，用于判断超卖状态"""
    try:
        import yfinance as yf
        h = yf.Ticker(symbol).history(period="5d")
        if len(h) >= 3:
            return float((h["Close"].iloc[-1] - h["Close"].iloc[-3]) / h["Close"].iloc[-3] * 100)
    except Exception:
        pass
    return 0.0

def analyze(symbol, fields):
    close = fields.get("close", {}).get("value", 0)
    beta  = fields.get("beta",  {}).get("value")
    lo52  = fields.get("52w_low",  {}).get("value")
    hi52  = fields.get("52w_high", {}).get("value")
    rsi14 = fields.get("rsi14", {}).get("value", 50)
    atr14 = fields.get("atr14", {}).get("value")
    short_pct = fields.get("short_pct", {}).get("value", 0)
    catalyst  = fields.get("catalyst_strength", {}).get("value", 1)
    recent_2d = _recent_2d_change(symbol)
    points, score = [], 0

    # ── 轧空设置检测 ─────────────────────────────────────────────
    # 高空头 + 近期超卖 + 正向催化剂 = 轧空设置（看涨），而非单纯风险
    squeeze_setup = short_pct and short_pct > 10 and recent_2d < -2.5 and catalyst >= 1
    if squeeze_setup:
        points.append(f"空头比例{short_pct:.0f}%+近2日{recent_2d:+.1f}%超卖+有催化剂→轧空设置，空头被迫回补")
        score += 25
    if beta:
        if beta > 2.0:   points.append(f"Beta={beta:.1f} 高波动，需控制仓位"); score -= 20
        elif beta > 1.5: points.append(f"Beta={beta:.1f} 中高波动");           score -= 10
        else:            points.append(f"Beta={beta:.1f} 波动适中");            score += 5
    stop_loss = round(close * 0.93, 2) if close else None
    if lo52 and close and lo52 > close * 0.85:
        stop_loss = round(max(stop_loss or 0, lo52 * 1.01), 2)
    if stop_loss:
        points.append(f"建议止损位 ${stop_loss}（当前价-7% 或52周低点保护）")
    if beta and beta > 1.5:
        points.append("建议仓位 ≤ 5%（高Beta股）")
    else:
        points.append("建议仓位 ≤ 10%")
    if rsi14 and rsi14 > 75:
        points.append(f"RSI={rsi14:.1f} 超买，短期回调可能性高，止损纪律尤重要")
        score -= 10
    if squeeze_setup:
        signal = "bullish"
    elif score >= -10:
        signal = "neutral"
    else:
        signal = "bearish"
    confidence = min(85, 55 + abs(score))
    refs = [{"field": "beta",  "verified": fields.get("beta",  {}).get("verified", False), "source": "yfinance"},
            {"field": "close", "verified": fields.get("close", {}).get("verified", False), "source": "yfinance"}]

    # ── Layer 2: 推理链 ──────────────────────────────────────────
    analysis = []
    cur_price = close or 100
    if beta:
        if beta > 2:
            analysis.append(f"Beta={beta:.1f}，大盘涨1%该股可能涨{beta:.1f}%，但大盘跌时放大幅度相同，杠杆效应明显")
        elif beta < 0.5:
            analysis.append(f"Beta={beta:.1f}，低波动防御型，大盘剧烈波动时相对稳定")
        else:
            analysis.append(f"Beta={beta:.1f}，波动适中，与大盘较为同步")
    if atr14 and cur_price:
        atr_pct = atr14 / cur_price * 100
        analysis.append(f"ATR={atr14:.2f}(日均波幅{atr_pct:.1f}%)，合理止损应至少{atr_pct*1.5:.1f}%以上，否则容易被噪音触发")
    if squeeze_setup:
        analysis.append(f"空头比例{short_pct:.0f}%+近2日{recent_2d:+.1f}%+有催化剂 = 轧空设置：空头面临回补压力，是助推而非抑制上涨的结构")
    elif short_pct and short_pct > 10:
        analysis.append(f"空头比例{short_pct:.0f}%偏高，若无催化剂，空头持续压制价格；若出现催化剂则可能触发轧空")
    elif short_pct and short_pct < 3:
        analysis.append(f"空头比例{short_pct:.0f}%极低，下跌时缺乏空头回补保护")

    # ── Layer 3: 专业结论 ────────────────────────────────────────
    risk_level = "偏高" if beta and beta > 2 else "适中" if beta and beta > 1 else "偏低"
    atr_str = f"{atr14:.1f}" if atr14 else "N/A"
    beta_str = f"{beta:.1f}" if beta else "N/A"
    judgment = f"风险水平{risk_level}：Beta={beta_str}，ATR={atr_str}"
    boundary = "若持仓比例超过账户的10%或同时有2个以上高Beta仓位，总风险超标"
    challenge = "Taleb会问：最坏情景（5σ事件）下这个仓位的最大损失是多少？你能承受吗？"

    conclusion = {
        "judgment": judgment,
        "boundary": boundary,
        "anticipated_challenge": challenge
    }

    return signal, confidence, points, refs, analysis, conclusion, stop_loss

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()
    data = json.load(open(VERIFIED_PATH, encoding="utf-8"))
    signal, conf, points, refs, analysis, conclusion, stop_loss = analyze(args.symbol, data["fields"])
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    from agents.protocol import apply_persona
    _data = {k: v.get("value") if isinstance(v, dict) else v for k, v in data["fields"].items()}
    if args.round is None:
        _board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = make_finding("RiskAgent", args.symbol, signal, conf, points, refs, analysis=analysis, conclusion=conclusion)
        msg["stop_loss"] = stop_loss
        msg = apply_persona(msg, _data, "RiskAgent", _board)
        json.dump(msg, open(os.path.join(FINDINGS_DIR, "RiskAgent.json"), "w", encoding="utf-8"), indent=2)
    else:
        board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = compute_phase2_response("RiskAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            json.dump({}, open(os.path.join(FINDINGS_DIR, f"RiskAgent_r{args.round}.json"), "w", encoding="utf-8"))
            return
        json.dump(msg, open(os.path.join(FINDINGS_DIR, f"RiskAgent_r{args.round}.json"), "w", encoding="utf-8"), indent=2)

if __name__ == "__main__":
    main()
