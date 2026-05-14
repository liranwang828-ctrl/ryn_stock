import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, fetch_with_retry, atomic_write_json
log = get_logger(__name__)
from agents.protocol import (BASE, VERIFIED_PATH, BOARD_PATH, FINDINGS_DIR,
                              make_finding, make_revision, compute_phase2_response)

def analyze(symbol, fields):
    close = fields.get("close", {}).get("value", 0)
    beta  = fields.get("beta",  {}).get("value")
    lo52  = fields.get("52w_low",  {}).get("value")
    hi52  = fields.get("52w_high", {}).get("value")
    rsi14 = fields.get("rsi14", {}).get("value", 50)
    atr14 = fields.get("atr14", {}).get("value")
    short_pct = fields.get("short_pct", {}).get("value", 0)
    points, score = [], 0
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
    signal     = "neutral" if score >= -10 else "bearish"
    confidence = min(80, 55 + abs(score))
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
    if short_pct and short_pct > 10:
        analysis.append(f"空头比例{short_pct:.0f}%偏高，做空方一旦错了会产生逼空效应，助推上涨")
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
    data = json.load(open(VERIFIED_PATH))
    signal, conf, points, refs, analysis, conclusion, stop_loss = analyze(args.symbol, data["fields"])
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    from agents.protocol import apply_persona
    _data = {k: v.get("value") if isinstance(v, dict) else v for k, v in data["fields"].items()}
    if args.round is None:
        _board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = make_finding("RiskAgent", args.symbol, signal, conf, points, refs, analysis=analysis, conclusion=conclusion)
        msg["stop_loss"] = stop_loss
        msg = apply_persona(msg, _data, "RiskAgent", _board)
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, "RiskAgent.json"), indent=2)
    else:
        board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = compute_phase2_response("RiskAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            atomic_write_json({}, os.path.join(FINDINGS_DIR, f"RiskAgent_r{args.round}.json"))
            return
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, f"RiskAgent_r{args.round}.json"), indent=2)

if __name__ == "__main__":
    main()
