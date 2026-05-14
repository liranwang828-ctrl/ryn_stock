import sys, os, json, argparse, requests, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.protocol import (BASE, BOARD_PATH, FINDINGS_DIR, VERIFIED_PATH,
                              make_finding, make_revision, compute_phase2_response)
from utils import get_logger, fetch_with_retry, atomic_write_json

log = get_logger(__name__)

SUBREDDITS = ["wallstreetbets", "stocks", "investing"]

def _get_praw():
    """Initialize praw if credentials are available."""
    client_id = os.environ.get("REDDIT_CLIENT_ID", "")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "stock-agent/1.0")
    if not client_id or not client_secret:
        return None
    try:
        import praw
        return praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
    except ImportError:
        log.warning("praw not installed, falling back to raw Reddit search")
        return None
    except Exception as e:
        log.warning("praw init failed: %s, falling back to raw search", e)
        return None

def fetch_reddit_sentiment(symbol):
    """Fetch Reddit sentiment via praw (OAuth) with fallback to raw search."""
    bullish_words = {"buy", "long", "bull", "moon", "calls", "undervalued", "green"}
    bearish_words = {"sell", "short", "bear", "puts", "overvalued", "dump", "crash"}

    reddit = _get_praw()
    if reddit:
        return _fetch_reddit_praw(symbol, reddit, bullish_words, bearish_words)
    return _fetch_reddit_raw(symbol, bullish_words, bearish_words)

def _fetch_reddit_praw(symbol, reddit, bullish_words, bearish_words):
    posts, bullish, bearish = [], 0, 0
    for sub in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub)
            for submission in subreddit.search(symbol, sort="hot", limit=15):
                content = (submission.title + " " + submission.selftext).lower()
                upvotes = submission.score
                bull_hits = sum(1 for w in bullish_words if w in content)
                bear_hits = sum(1 for w in bearish_words if w in content)
                if bull_hits > bear_hits:
                    bullish += upvotes
                    posts.append(f"r/{sub}: {submission.title[:60]}... (+{upvotes}看多)")
                elif bear_hits > bull_hits:
                    bearish += upvotes
                    posts.append(f"r/{sub}: {submission.title[:60]}... (+{upvotes}看空)")
        except Exception as e:
            log.debug("Reddit praw error r/%s: %s", sub, e)
            continue
    return bullish, bearish, posts[:5]

def _fetch_reddit_raw(symbol, bullish_words, bearish_words):
    posts, bullish, bearish = [], 0, 0
    for sub in SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={symbol}&sort=hot&limit=15&t=day"
            headers = {"User-Agent": os.environ.get("REDDIT_USER_AGENT", "stock-agent/1.0")}
            resp = fetch_with_retry(lambda: requests.get(url, headers=headers, timeout=10))
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "60")
                log.warning("Reddit rate limited r/%s, retry-after=%s", sub, retry_after)
                continue
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
        except Exception as e:
            log.debug("Reddit raw error r/%s: %s", sub, e)
            continue
    return bullish, bearish, posts[:5]

def fetch_stocktwits_sentiment(symbol):
    try:
        url  = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
        resp = fetch_with_retry(lambda: requests.get(url, timeout=10))
        if resp.status_code != 200:
            return 0, 0
        msgs = resp.json().get("messages", [])
        bull = sum(1 for m in msgs if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish")
        bear = sum(1 for m in msgs if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish")
        return bull, bear
    except Exception as e:
        log.debug("StockTwits error: %s", e)
        return 0, 0

_CHINESE_BULLISH = [
    '看涨', '做多', '满仓', '加仓', '抄底', '起飞', '暴涨', '涨停',
    '利好', '突破', '新高', '强势', '坚定持有', '价值投资', '低估',
    '回购', '分红', '龙头', '吃肉', '翻倍', '稳了', '冲', '梭哈',
    '格局', '长线', '低吸', '埋伏', '起飞了', '大肉'
]
_CHINESE_BEARISH = [
    '看跌', '做空', '清仓', '减仓', '暴跌', '跌停', '割肉', '套牢',
    '利空', '破位', '新低', '弱势', '止损', '出货', '高估', '雷',
    '暴雷', '退市', '停牌', '腰斩', '韭菜', '接盘', '跑路', '跳水',
    '崩盘', '亏', '砸盘', '诱多', '出货了'
]
_BULLISH_EN = ['bull', 'long', 'buy', 'call', 'moon', '10x', '100x']
_BEARISH_EN = ['bear', 'short', 'sell', 'put', 'dump', 'rug', 'dead']


def _chinese_sentiment_score(text: str) -> float:
    text_l = text.lower()
    score, total = 0.0, 0
    for kw in _CHINESE_BULLISH:
        if kw in text_l:
            score += 1; total += 1
    for kw in _CHINESE_BEARISH:
        if kw in text_l:
            score -= 1; total += 1
    for kw in _BULLISH_EN:
        if kw in text_l:
            score += 0.5; total += 1
    for kw in _BEARISH_EN:
        if kw in text_l:
            score -= 0.5; total += 1
    if total == 0:
        return 0.0
    return max(-0.7, min(0.7, score / max(total, 1)))


def fetch_xueqiu(symbol: str):
    """Fetch sentiment from Xueqiu (雪球) Chinese retail investor platform. No API key needed."""
    try:
        url = 'https://xueqiu.com/query/v1/search/status.json'
        params = {'q': symbol, 'count': 20, 'type': '11', 'source': 'all'}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://xueqiu.com/',
            'Accept': 'application/json'
        }
        session = requests.Session()
        fetch_with_retry(lambda: session.get('https://xueqiu.com/', headers={'User-Agent': headers['User-Agent']}, timeout=10))
        resp = fetch_with_retry(lambda: session.get(url, params=params, headers=headers, timeout=10))
        if resp.status_code != 200:
            return 0, 0, []
        data = resp.json()
        items = data.get('list', [])
        if not items:
            return 0, 0, []
        bull, bear = 0, 0
        posts = []
        for item in items[:20]:
            text = (item.get('text', '') or item.get('title', ''))
            if not text:
                continue
            text = re.sub(r'<[^>]+>', '', text)
            s = _chinese_sentiment_score(text)
            if s > 0.1:
                bull += 1
                posts.append(f"雪球: {text[:60]}... (看多)")
            elif s < -0.1:
                bear += 1
                posts.append(f"雪球: {text[:60]}... (看空)")
        return bull, bear, posts[:3]
    except Exception:
        return 0, 0, []


def analyze(symbol):
    r_bull, r_bear, posts = fetch_reddit_sentiment(symbol)
    st_bull, st_bear      = fetch_stocktwits_sentiment(symbol)
    xq_bull, xq_bear, xq_posts = fetch_xueqiu(symbol)

    total_bull = r_bull + st_bull * 100 + xq_bull * 50
    total_bear = r_bear + st_bear * 100 + xq_bear * 50
    total      = total_bull + total_bear or 1
    bull_pct   = total_bull / total
    points     = [f"社群看多比例 {bull_pct:.0%} (Reddit+StockTwits+雪球)"]
    if posts:
        points.append("Reddit: " + posts[0])
    if xq_posts:
        points.append("雪球: " + xq_posts[0])
    if bull_pct >= 0.6:   signal, score = "bullish", int(bull_pct * 80)
    elif bull_pct <= 0.4: signal, score = "bearish", int((1 - bull_pct) * 80)
    else:                 signal, score = "neutral",  55
    refs = [{"field": "community_sentiment", "verified": False, "source": "reddit+stocktwits+xueqiu"}]
    return signal, score, points, refs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()
    signal, conf, points, refs = analyze(args.symbol)
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    from agents.protocol import apply_persona
    _raw = json.load(open(VERIFIED_PATH)).get("fields", {}) if os.path.exists(VERIFIED_PATH) else {}
    _data = {k: v.get("value") if isinstance(v, dict) else v for k, v in _raw.items()}
    if args.round is None:
        msg = make_finding("CommunityAgent", args.symbol, signal, conf, points, refs)
        _board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = apply_persona(msg, _data, "CommunityAgent", _board)
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, "CommunityAgent.json"), indent=2)
    else:
        board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = compute_phase2_response("CommunityAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            atomic_write_json({}, os.path.join(FINDINGS_DIR, f"CommunityAgent_r{args.round}.json"))
            return
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, f"CommunityAgent_r{args.round}.json"), indent=2)

if __name__ == "__main__":
    main()
