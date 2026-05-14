import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, fetch_with_retry, atomic_write_json
log = get_logger(__name__)
from agents.protocol import (BASE, VERIFIED_PATH, BOARD_PATH, FINDINGS_DIR,
                              make_finding, make_revision, compute_phase2_response)

def get_field(fields, name, default=None):
    entry = fields.get(name, {})
    return entry.get("value", default), entry.get("verified", False)

def analyze(symbol, fields):
    close, _       = get_field(fields, "close")
    prev, _        = get_field(fields, "prev_close", close)
    volume, _      = get_field(fields, "volume")
    vol_ma20, _    = get_field(fields, "vol_ma20")
    macd, _        = get_field(fields, "macd")
    rsi14, _       = get_field(fields, "rsi14")
    hi52, _        = get_field(fields, "52w_high")
    lo52, _        = get_field(fields, "52w_low")
    overnight, _   = get_field(fields, "overnight_chg", 0.0)
    ext_session, _ = get_field(fields, "extended_session", "none")

    points = []
    bullish_score = 0

    # 盘前/盘后价格方向（最直接的当日信号）
    if overnight and ext_session != "none":
        label = "盘前" if ext_session == "pre" else "盘后"
        if overnight > 0.01:
            points.append(f"{label}涨{overnight:.2%}，开盘动能正面")
            bullish_score += 20
        elif overnight < -0.01:
            points.append(f"{label}跌{overnight:.2%}，开盘压力存在")
            bullish_score -= 20
        elif overnight < -0.005:
            points.append(f"{label}微跌{overnight:.2%}，注意开盘方向")
            bullish_score -= 8

    if macd and macd > 0:
        points.append(f"MACD金叉({macd:.1f})，多头动能扩大")
        bullish_score += 25
    elif macd and macd < 0:
        points.append(f"MACD死叉({macd:.1f})，空头占优")
        bullish_score -= 25

    if rsi14:
        if rsi14 > 75:
            points.append(f"RSI-14={rsi14:.1f} 超买，短期回调风险")
            bullish_score += 10
        elif rsi14 < 25:
            points.append(f"RSI-14={rsi14:.1f} 超卖，反弹机会")
            bullish_score += 15
        else:
            points.append(f"RSI-14={rsi14:.1f} 中性区间")
            bullish_score += 15

    if volume and vol_ma20:
        ratio = volume / vol_ma20
        price_chg = (close - prev) / prev if prev else 0
        if ratio > 1.5 and price_chg > 0:
            points.append(f"放量上涨(量比{ratio:.1f}x)，主力推升")
            bullish_score += 20
        elif ratio > 1.5 and price_chg < 0:
            points.append(f"放量下跌(量比{ratio:.1f}x)，主力出货")
            bullish_score -= 20
        else:
            points.append(f"成交量温和(量比{ratio:.1f}x)")
            bullish_score += 5

    if hi52 and lo52 and close:
        pos = (close - lo52) / (hi52 - lo52) if hi52 != lo52 else 0.5
        if pos > 0.9:
            points.append(f"接近52周高点({pos:.0%})，注意压力")
        elif pos < 0.1:
            points.append(f"接近52周低点({pos:.0%})，关注支撑")

    if bullish_score >= 40:
        signal, confidence = "bullish", min(90, 50 + bullish_score)
    elif bullish_score <= 0:
        signal, confidence = "bearish", min(90, 50 - bullish_score)
    else:
        signal, confidence = "neutral", 60

    data_refs = [
        {"field": "macd",   "verified": fields.get("macd",  {}).get("verified", False), "source": "yfinance"},
        {"field": "rsi14",  "verified": fields.get("rsi14", {}).get("verified", False), "source": "yfinance"},
        {"field": "volume", "verified": fields.get("volume",{}).get("verified", False), "source": "yfinance"},
    ]

    # ── Layer 2: 推理链 ──────────────────────────────────────────
    analysis = []
    macd_v = fields.get("macd", {}).get("value")
    rsi14_v = fields.get("rsi14", {}).get("value")
    volume_v = fields.get("volume", {}).get("value")
    vol_ma20_v = fields.get("vol_ma20", {}).get("value")
    close_v = fields.get("close", {}).get("value")
    prev_v = fields.get("prev_close", {}).get("value")

    if macd_v and macd_v > 0:
        analysis.append(f"MACD正值({macd_v:.2f})说明短期均线高于长期均线，动能方向向上——需量能配合才构成有效信号")
    elif macd_v and macd_v < 0:
        analysis.append(f"MACD负值({macd_v:.2f})空头动能仍占主导，技术上不宜追多，等待MACD柱收窄转正")
    if rsi14_v:
        if rsi14_v > 75:
            analysis.append(f"RSI-14={rsi14_v:.1f}超买区，短期面临获利盘出货压力，但强势股可维持更久")
        elif rsi14_v < 35:
            analysis.append(f"RSI-14={rsi14_v:.1f}超卖区，有均值回归动力，但需排除趋势性下跌")
        else:
            analysis.append(f"RSI-14={rsi14_v:.1f}健康区间，上行空间未耗尽")
    if volume_v and vol_ma20_v and close_v and prev_v:
        ratio = volume_v / vol_ma20_v
        price_chg = (close_v - prev_v) / prev_v
        if ratio > 1.5 and price_chg > 0:
            analysis.append(f"量比{ratio:.1f}x配合上涨，有真实买盘支撑")
        elif ratio < 0.7:
            analysis.append(f"量比{ratio:.1f}x萎缩，需关注后续量能是否恢复")

    # ── Layer 3: 专业结论 ────────────────────────────────────────
    if signal == "bullish":
        judgment = "技术结构看多：动能向上+量价配合"
        boundary = "若MACD柱收窄或跌破VWAP，看多减弱"
        challenge = "Minervini会问：Stage 2是否确认？量比是否>1.5x？"
    elif signal == "bearish":
        judgment = "技术结构看空：动能转弱+量价背离"
        boundary = "若价格站上MA20且量能扩张，空头失效"
        challenge = "Soros会问：下跌是否在创造反身性反弹机会？"
    else:
        judgment = "技术信号混合，等待方向确认"
        boundary = "需放量突破关键价位才能确认方向"
        challenge = "Livermore会问：这不是最强的股票，为什么选它？"

    conclusion = {
        "judgment": judgment,
        "boundary": boundary,
        "anticipated_challenge": challenge
    }

    return signal, min(confidence, 95), points, data_refs, analysis, conclusion

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()

    data   = json.load(open(VERIFIED_PATH))
    fields = data["fields"]
    signal, conf, points, refs, analysis, conclusion = analyze(args.symbol, fields)
    _data  = {k: v.get("value") if isinstance(v, dict) else v for k, v in fields.items()}
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    board  = [json.loads(l) for l in open(BOARD_PATH) if l.strip()] if os.path.exists(BOARD_PATH) else []

    if args.round is None:
        from agents.protocol import apply_persona
        msg = make_finding("TechAgent", args.symbol, signal, conf, points, refs, analysis=analysis, conclusion=conclusion)
        msg = apply_persona(msg, _data, "TechAgent", board)
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, "TechAgent.json"), indent=2)
    else:
        msg = compute_phase2_response("TechAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            atomic_write_json({}, os.path.join(FINDINGS_DIR, f"TechAgent_r{args.round}.json"))
            return
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, f"TechAgent_r{args.round}.json"), indent=2)

if __name__ == "__main__":
    main()
