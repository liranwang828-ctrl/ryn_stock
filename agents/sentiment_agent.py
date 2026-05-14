import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, fetch_with_retry, atomic_write_json
log = get_logger(__name__)
from agents.protocol import (BASE, VERIFIED_PATH, BOARD_PATH, FINDINGS_DIR,
                              make_finding, make_revision, compute_phase2_response)


class VADERSentiment:
    """Compact VADER sentiment analyzer. Falls back to financial lexicon if NLTK unavailable."""

    def __init__(self):
        """Initialize with VADER from NLTK if available, otherwise use fallback."""
        self._analyzer = None
        try:
            from nltk.sentiment import SentimentIntensityAnalyzer
            import nltk
            try:
                nltk.data.find('sentiment/vader_lexicon.zip')
            except LookupError:
                nltk.download('vader_lexicon', quiet=True)
            self._analyzer = SentimentIntensityAnalyzer()
        except ImportError:
            pass

    def compound(self, text):
        """Return VADER compound score for text, falling back to financial lexicon."""
        if not text or not isinstance(text, str):
            return 0.0
        if self._analyzer:
            return self._analyzer.polarity_scores(text)['compound']
        return self._fallback(text)

    def _fallback(self, text):
        """Score text using hardcoded financial bullish/bearish word lists."""
        text_l = text.lower()
        pos = {'beat', 'raise', 'upgrade', 'growth', 'profit', 'record', 'strong',
               'positive', 'outperform', 'buyback', 'dividend', 'bull', 'long',
               'calls', 'moon', 'rocket', 'green', 'pump', 'squeeze', 'yolo',
               'undervalued', 'breakout', 'momentum', 'rally', 'raised guidance',
               'upgraded', 'accumulate', 'oversold', 'support', 'bounce', 'dip buy'}
        neg = {'miss', 'cut', 'downgrade', 'loss', 'decline', 'weak', 'negative',
               'underperform', 'lawsuit', 'layoff', 'warning', 'bear', 'short',
               'puts', 'dump', 'red', 'crash', 'rug', 'scam', 'overvalued',
               'top', 'sell', 'breakdown', 'resistance', 'drop', 'plunge',
               'bankrupt', 'probe', 'investigation', 'default', 'delist', 'halt'}
        negations = {'not', "n't", 'never', 'no', 'neither', 'nor', 'hardly'}
        words = text_l.split()
        score, negate, total = 0.0, False, 0
        for w in words:
            w = w.strip('.,!?;:\'"()[]{}').lower()
            if w in negations:
                negate = True; continue
            if w in pos:
                score += -1 if negate else 1; total += 1
            elif w in neg:
                score += 1 if negate else -1; total += 1
        return score / max(total, 1)


_vader = None


def _get_vader():
    """Return cached VADERSentiment singleton."""
    global _vader
    if _vader is None:
        _vader = VADERSentiment()
    return _vader


def analyze_news(headlines):
    """VADER-based news sentiment. Returns (news_points, news_score)."""
    vader = _get_vader()
    news_points, score = [], 0.0
    for h in (headlines or [])[:8]:
        title = h.get("title", "")
        pub = h.get("publisher", "")
        time_ = h.get("time", "")
        compound = vader.compound(title)
        if compound > 0.1:
            tag = "📈"
        elif compound < -0.1:
            tag = "📉"
        else:
            tag = "📰"
        news_points.append(f"{tag} [{time_} {pub}] {title[:70]}")
        score += compound * 30
    return news_points, int(score)

def analyze(symbol, fields):
    """Score analyst ratings, target price, and news sentiment into a signal with confidence."""
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
                  {"field": "news_headlines", "verified": False,  "source": "yfinance+vader"}]

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
    """Parse args, run sentiment analysis, and write finding JSON."""
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
        from agents.protocol import apply_persona
        msg = apply_persona(msg, _data, "SentimentAgent", board)
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, "SentimentAgent.json"), indent=2)
    else:
        board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = compute_phase2_response("SentimentAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            atomic_write_json({}, os.path.join(FINDINGS_DIR, f"SentimentAgent_r{args.round}.json"))
            return
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, f"SentimentAgent_r{args.round}.json"), indent=2)

if __name__ == "__main__":
    main()
