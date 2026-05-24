import sys, os, json, argparse, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import (BASE, BOARD_PATH, FINDINGS_DIR, VERIFIED_PATH,
                              make_finding, make_revision, compute_phase2_response)

SUBREDDITS = ["wallstreetbets", "stocks", "investing"]

def fetch_reddit_sentiment(symbol):
    posts, bullish, bearish = [], 0, 0
    bullish_words = {"buy", "long", "bull", "moon", "calls", "undervalued", "green"}
    bearish_words = {"sell", "short", "bear", "puts", "overvalued", "dump", "crash"}
    for sub in SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={symbol}&sort=hot&limit=15&t=day"
            headers = {"User-Agent": os.environ.get("REDDIT_USER_AGENT", "stock-agent/1.0")}
            resp = requests.get(url, headers=headers, timeout=10)
            # 处理限流或非200响应
            if resp.status_code != 200:
                continue
            data = resp.json()
            items = data.get("data", {}).get("children", [])
            for item in items:
                title = item["data"].get("title", "").lower()
                text  = item["data"].get("selftext", "").lower()
                content = title + " " + text
                upvotes = item["data"].get("score", 0)
                bull_hits = sum(1 for w in bullish_words if w in content)
                bear_hits = sum(1 for w in bearish_words if w in content)
                if bull_hits > bear_hits:
                    bullish += upvotes
                    posts.append(f"r/{sub}: {title[:60]}... (+{upvotes}看多)")
                elif bear_hits > bull_hits:
                    bearish += upvotes
                    posts.append(f"r/{sub}: {title[:60]}... (+{upvotes}看空)")
        except Exception:
            continue
    return bullish, bearish, posts[:5]

def fetch_stocktwits_sentiment(symbol):
    try:
        url  = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return 0, 0
        msgs = resp.json().get("messages", [])
        bull = sum(1 for m in msgs if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish")
        bear = sum(1 for m in msgs if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish")
        return bull, bear
    except Exception:
        return 0, 0

def analyze(symbol):
    r_bull, r_bear, posts = fetch_reddit_sentiment(symbol)
    st_bull, st_bear      = fetch_stocktwits_sentiment(symbol)
    total_bull = r_bull + st_bull * 100
    total_bear = r_bear + st_bear * 100
    total      = total_bull + total_bear or 1
    bull_pct   = total_bull / total
    points     = [f"Reddit/StockTwits 看多比例 {bull_pct:.0%}"]
    if posts:
        points.append("社群热点: " + posts[0])

    # ── 0%看多语义区分：待发现 vs 真看空 ────────────────────────
    # 读取股票基本面数据判断语义
    undiscovered = False
    if bull_pct == 0 and total_bear < 500:  # 几乎没有讨论
        try:
            _raw = json.load(open(VERIFIED_PATH, encoding="utf-8")).get("fields", {}) if os.path.exists(VERIFIED_PATH) else {}
            short_pct = _raw.get("short_pct", {}).get("value", 0) or 0
            import yfinance as yf
            h = yf.Ticker(symbol).history(period="5d")
            recent_2d = float((h["Close"].iloc[-1] - h["Close"].iloc[-3]) / h["Close"].iloc[-3] * 100) if len(h) >= 3 else 0
            # 高空头 + 近期超卖 + 社群沉默 = 待发现机会
            if short_pct > 10 and recent_2d < -2.0:
                undiscovered = True
                points.append(f"社群沉默（看多0%但讨论极少）+空头{short_pct:.0f}%+近2日{recent_2d:+.1f}% → 待发现，非真看空")
        except Exception:
            pass

    if undiscovered:
        signal, score = "neutral", 50
    elif bull_pct >= 0.6:   signal, score = "bullish", int(bull_pct * 80)
    elif bull_pct <= 0.4: signal, score = "bearish", int((1 - bull_pct) * 80)
    else:                 signal, score = "neutral",  55
    refs = [{"field": "community_sentiment", "verified": False, "source": "reddit+stocktwits"}]
    return signal, score, points, refs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()
    signal, conf, points, refs = analyze(args.symbol)
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    from agents.protocol import apply_persona
    _raw = json.load(open(VERIFIED_PATH, encoding="utf-8")).get("fields", {}) if os.path.exists(VERIFIED_PATH) else {}
    _data = {k: v.get("value") if isinstance(v, dict) else v for k, v in _raw.items()}
    if args.round is None:
        msg = make_finding("CommunityAgent", args.symbol, signal, conf, points, refs)
        _board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = apply_persona(msg, _data, "CommunityAgent", _board)
        with open(os.path.join(FINDINGS_DIR, "CommunityAgent.json"), "w", encoding="utf-8") as f:
            json.dump(msg, f, indent=2, ensure_ascii=False)
    else:
        board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = compute_phase2_response("CommunityAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            with open(os.path.join(FINDINGS_DIR, f"CommunityAgent_r{args.round}.json"), "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False)
            return
        with open(os.path.join(FINDINGS_DIR, f"CommunityAgent_r{args.round}.json"), "w", encoding="utf-8") as f:
            json.dump(msg, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
