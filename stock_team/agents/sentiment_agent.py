import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from stock_team.utils.protocol import (BASE, VERIFIED_PATH, BOARD_PATH, FINDINGS_DIR,
                              make_finding, make_revision, compute_phase2_response)

BULLISH_WORDS = {"beat", "surge", "rally", "upgrade", "buy", "bullish", "record",
                 "growth", "profit", "strong", "raised", "outperform", "upside"}
BEARISH_WORDS = {"miss", "decline", "downgrade", "sell", "bearish", "loss",
                 "weak", "cut", "lowered", "underperform", "concern", "risk", "fall"}

def analyze_news(headlines):
    """Return (news_points, news_score) from raw headline list."""
    news_points, score = [], 0
    for h in (headlines or [])[:6]:
        title = h.get("title", "").lower()
        pub   = h.get("publisher", "")
        time_ = h.get("time", "")
        bull  = sum(1 for w in BULLISH_WORDS if w in title)
        bear  = sum(1 for w in BEARISH_WORDS if w in title)
        tag   = "📈" if bull > bear else "📉" if bear > bull else "📰"
        news_points.append(f"{tag} [{time_} {pub}] {h.get('title','')[:70]}")
        score += (bull - bear) * 5
    return news_points, score

def analyze(symbol, fields):
    rec_val  = fields.get("analyst_rec",  {}).get("value")
    rec_v    = fields.get("analyst_rec",  {}).get("verified", False)
    tgt_val  = fields.get("target_price", {}).get("value")
    close    = fields.get("close",        {}).get("value", 0)
    headlines= fields.get("news_headlines",{}).get("value") or []

    points, score = [], 0

    # 分析师评级
    if rec_val:
        if rec_val <= 1.5:   points.append(f"分析师强烈看多(评级{rec_val:.1f})"); score += 30
        elif rec_val <= 2.5: points.append(f"分析师看多(评级{rec_val:.1f})");     score += 15
        elif rec_val <= 3.5: points.append(f"分析师中性(评级{rec_val:.1f})");     score += 0
        else:                points.append(f"分析师看空(评级{rec_val:.1f})");     score -= 20

    # 目标价 + 新鲜度检测
    if tgt_val and close:
        upside = (tgt_val - close) / close
        # 新鲜度：估算目标价是否已过时（通过近30日价格变动判断）
        price_chg_30d = fields.get("price_chg_3m", {}).get("value") or 0  # 实际是3个月
        stale_flag = ""
        stale_weight = 1.0
        if abs(price_chg_30d) > 0.20:
            stale_flag = f" ⚠️ 目标价可能过时（近期涨跌{price_chg_30d:+.0%}）"
            stale_weight = 0.3  # 大幅波动后目标价权重降为30%
        elif abs(price_chg_30d) > 0.10:
            stale_flag = f" (近期波动{price_chg_30d:+.0%}，目标价仅供参考)"
            stale_weight = 0.6

        if upside > 0.1:
            points.append(f"目标价${tgt_val:.0f}，上行空间{upside:.0%}{stale_flag}")
            score += int(20 * stale_weight)
        elif upside < -0.05:
            points.append(f"目标价${tgt_val:.0f}，下行风险{upside:.0%}{stale_flag}")
            score -= int(15 * stale_weight)
        else:
            points.append(f"目标价${tgt_val:.0f}，空间有限({upside:.0%}){stale_flag}")

    # 新闻情绪
    news_pts, news_score = analyze_news(headlines)
    if news_pts:
        points.append("── 近期新闻 ──")
        points += news_pts
        score += news_score

    signal     = "bullish" if score >= 25 else "bearish" if score <= -15 else "neutral"
    confidence = min(85, 50 + abs(score))
    refs       = [{"field": "analyst_rec",    "verified": rec_v,  "source": "yfinance"},
                  {"field": "news_headlines", "verified": False,  "source": "yfinance"}]

    # ── Layer 2: 推理链 ──────────────────────────────────────────
    analysis = []
    analyst_rec = fields.get("analyst_rec", {}).get("value")
    target_price = fields.get("target_price", {}).get("value")
    cur_price = fields.get("close", {}).get("value")

    if analyst_rec:
        if analyst_rec <= 2:
            analysis.append(f"分析师评级{analyst_rec:.1f}（强烈买入），但需注意分析师通常滞后于市场")
        elif analyst_rec >= 4:
            analysis.append(f"分析师评级{analyst_rec:.1f}（偏空），机构普遍悲观时反而可能是底部信号")
    if target_price and cur_price:
        upside = (target_price - cur_price) / cur_price * 100
        if upside > 20:
            analysis.append(f"分析师目标价{upside:.0f}%上行空间，但目标价通常有6-12个月滞后，需判断时效性")
        elif upside < 0:
            analysis.append(f"当前价已超过分析师目标价{abs(upside):.0f}%，说明上涨已超出机构预期")

    # ── Layer 3: 专业结论 ────────────────────────────────────────
    if signal == "bullish":
        judgment = "市场情绪偏多：分析师看多+新闻正面，情绪助力"
        boundary = "若分析师开始集体下调目标价或负面新闻增多，情绪反转"
        challenge = "Marks会问：情绪是否已经过度乐观？钟摆是否在极端位置？"
    elif signal == "bearish":
        judgment = "市场情绪偏空：分析师悲观+负面新闻主导"
        boundary = "若出现正面催化剂且情绪开始改善，空头依据减弱"
        challenge = "Burry会反问：极度悲观是否反而是买入信号？"
    else:
        judgment = "市场情绪中性：多空信号均衡"
        boundary = "等待情绪明确方向的催化剂"
        challenge = "Druckenmiller会问：情绪中性时哪个方向的动量更强？"

    conclusion = {
        "judgment": judgment,
        "boundary": boundary,
        "anticipated_challenge": challenge
    }

    return signal, confidence, points or ["机构数据不足"], refs, analysis, conclusion

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()

    data   = json.load(open(VERIFIED_PATH, encoding="utf-8"))
    fields = data["fields"]
    _data  = {k: v.get("value") if isinstance(v, dict) else v for k, v in fields.items()}
    signal, conf, points, refs, analysis, conclusion = analyze(args.symbol, fields)
    os.makedirs(FINDINGS_DIR, exist_ok=True)

    if args.round is None:
        msg = make_finding("SentimentAgent", args.symbol, signal, conf, points, refs, analysis=analysis, conclusion=conclusion)
        board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        from stock_team.utils.protocol import apply_persona
        msg = apply_persona(msg, _data, "SentimentAgent", board)
        json.dump(msg, open(os.path.join(FINDINGS_DIR, "SentimentAgent.json"), "w", encoding="utf-8"), indent=2)
    else:
        board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = compute_phase2_response("SentimentAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            json.dump({}, open(os.path.join(FINDINGS_DIR, f"SentimentAgent_r{args.round}.json"), "w", encoding="utf-8"))
            return
        json.dump(msg, open(os.path.join(FINDINGS_DIR, f"SentimentAgent_r{args.round}.json"), "w", encoding="utf-8"), indent=2)

if __name__ == "__main__":
    main()
