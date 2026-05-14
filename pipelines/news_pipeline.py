"""
News, Sentiment, and Macro Data Pipeline v2.0
==============================================
Multi-source sentiment engine with proper NLP scoring.

Sentiment Methods (priority order):
  1. VADER (Valence Aware Dictionary) — zero-dependency, handles negation/intensity
  2. FinBERT — financial-domain BERT, highest accuracy for earnings/news
  3. StockTwits — free API, real-time retail sentiment
  4. Finnhub social-sentiment — aggregated Twitter/X data
  5. Reddit — WSB + investing subreddits

Chinese sources:
  6. Xueqiu (雪球) — via unofficial API, Chinese retail sentiment

Sources: Finnhub (news), Reddit (WSB), StockTwits, Yahoo Finance (macro)
Each source degrades gracefully if API keys are missing.
"""

import os
import re
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


# ============================================================
# Sentiment Engines
# ============================================================

class VADERSentiment:
    """
    VADER sentiment analyzer — handles negation, capitalization, intensifiers.
    Uses NLTK's VADER implementation. Falls back to built-in lexicon if NLTK missing.

    VADER is specifically designed for social media text and outperforms
    keyword counting by ~30% on standard benchmarks.
    """

    def __init__(self):
        self._analyzer = None
        self._init_analyzer()

    def _init_analyzer(self):
        try:
            from nltk.sentiment import SentimentIntensityAnalyzer
            import nltk
            try:
                nltk.data.find('sentiment/vader_lexicon.zip')
            except LookupError:
                nltk.download('vader_lexicon', quiet=True)
            self._analyzer = SentimentIntensityAnalyzer()
        except ImportError:
            self._analyzer = None

    def score(self, text: str) -> Dict[str, float]:
        """Returns {'neg': float, 'neu': float, 'pos': float, 'compound': float}"""
        if not text or not isinstance(text, str):
            return {'neg': 0.0, 'neu': 1.0, 'pos': 0.0, 'compound': 0.0}

        if self._analyzer:
            return self._analyzer.polarity_scores(text)

        # Fallback: lightweight built-in lexicon
        return self._fallback_score(text)

    def compound(self, text: str) -> float:
        """Single compound score in [-1, 1]. >0.05=positive, <-0.05=negative."""
        return self.score(text)['compound']

    def _fallback_score(self, text: str) -> Dict[str, float]:
        """Minimal built-in lexicon fallback when NLTK unavailable."""
        text = text.lower()

        # Financial + social media combined lexicon
        pos_words = {
            'beat', 'raise', 'upgrade', 'growth', 'profit', 'record', 'strong',
            'positive', 'outperform', 'buyback', 'dividend', 'expansion', 'bull',
            'long', 'calls', 'moon', 'rocket', 'green', 'pump', 'squeeze',
            'yolo', 'gem', 'undervalued', 'breakout', 'momentum', 'rally',
            'beat estimates', 'raised guidance', 'upgraded', 'accumulate',
            'oversold', 'support', 'bounce', 'dip buy', 'diamond hands'
        }
        neg_words = {
            'miss', 'cut', 'downgrade', 'loss', 'decline', 'weak', 'negative',
            'underperform', 'lawsuit', 'layoff', 'warning', 'bear', 'short',
            'puts', 'dump', 'bag', 'red', 'crash', 'rug', 'scam',
            'overvalued', 'top', 'sell', 'breakdown', 'resistance', 'drop',
            'plunge', 'bankrupt', 'probe', 'investigation', 'default',
            'delist', 'halt', 'suspended', 'paper hands'
        }
        # Negation prefixes
        negations = {'not', "n't", 'never', 'no', 'neither', 'nor', 'hardly'}

        words = text.split()
        score = 0.0
        negate = False
        total = 0

        for i, w in enumerate(words):
            w = w.strip('.,!?;:"\'()[]{}')
            if w in negations:
                negate = True
                continue
            if w in pos_words:
                score += -1 if negate else 1
                total += 1
            elif w in neg_words:
                score += 1 if negate else -1
                total += 1
            # Reset negation after 3 words
            if i % 3 == 0:
                negate = False

        compound = np.clip(score / max(total, 1), -1.0, 1.0)
        # Estimate pos/neg/neu distribution from compound
        if compound > 0.05:
            pos, neg, neu = compound, 0.0, 1.0 - compound
        elif compound < -0.05:
            pos, neg, neu = 0.0, abs(compound), 1.0 - abs(compound)
        else:
            pos, neg, neu = 0.0, 0.0, 1.0

        return {'neg': round(neg, 4), 'neu': round(neu, 4),
                'pos': round(pos, 4), 'compound': round(compound, 4)}


class FinBERTSentiment:
    """
    Financial-domain BERT sentiment. Highest accuracy for financial text.
    Optional — requires transformers + torch. ~500MB model download on first use.
    """

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._available = False

    def _load(self):
        if self._model is not None:
            return
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            model_name = "ProsusAI/finbert"
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self._available = True
        except ImportError:
            print("[FinBERT] transformers/torch not installed. Using VADER only.")
        except Exception as e:
            print(f"[FinBERT] Failed to load model: {e}")

    def score(self, text: str) -> Optional[Dict[str, float]]:
        """Returns {positive, negative, neutral} probabilities."""
        self._load()
        if not self._available or not text:
            return None

        try:
            import torch
            inputs = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self._model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)[0]
            return {
                'positive': round(float(probs[0]), 4),
                'negative': round(float(probs[1]), 4),
                'neutral': round(float(probs[2]), 4),
                'compound': round(float(probs[0] - probs[1]), 4)
            }
        except Exception:
            return None


# ============================================================
# Sentiment Aggregator
# ============================================================

@dataclass
class SentimentSignal:
    """Aggregated sentiment result for a ticker."""
    ticker: str
    compound: float           # -1 to 1 overall sentiment
    confidence: float          # 0-1 how confident we are in this score
    source_count: int           # how many sources contributed
    sources: Dict[str, float] = field(default_factory=dict)  # per-source compound
    mention_volume: int = 0     # total mentions across sources
    trend: str = "stable"       # accelerating / stable / decelerating
    breakdown: str = ""         # human-readable summary


class SentimentAggregator:
    """
    Aggregates sentiment from multiple sources into a single signal.
    Handles source weighting, conflict resolution, and confidence scoring.
    """

    # Source weights — reflects historical accuracy vs benchmark
    SOURCE_WEIGHTS = {
        'finnhub_news': 0.20,
        'finnhub_social': 0.15,
        'stocktwits': 0.20,
        'reddit_wsb': 0.10,       # WSB is noisy, lower weight
        'reddit_investing': 0.15,
        'xueqiu': 0.10,
        'finbert': 0.25,          # highest weight when available
        'vader_news': 0.20,
    }

    def __init__(self):
        self.vader = VADERSentiment()
        self.finbert = FinBERTSentiment()
        self._history: Dict[str, List[float]] = {}  # ticker -> recent compounds for trend

    def aggregate(self, ticker: str, sources: Dict[str, Dict]) -> SentimentSignal:
        """
        Aggregate sentiment from multiple sources.

        Args:
            ticker: Stock symbol
            sources: {source_name: {'compound': float, 'volume': int, 'confidence': float}}
        """
        if not sources:
            return SentimentSignal(
                ticker=ticker, compound=0.0, confidence=0.0,
                source_count=0, breakdown="No sentiment data available"
            )

        weighted_sum = 0.0
        weight_total = 0.0
        volume_total = 0
        compounds = {}
        source_details = []

        for name, data in sources.items():
            weight = self.SOURCE_WEIGHTS.get(name, 0.10)
            compound = data.get('compound', 0)
            confidence = data.get('confidence', 0.5)
            volume = data.get('volume', 0)

            # Adjust weight by internal confidence
            effective_weight = weight * confidence
            weighted_sum += compound * effective_weight
            weight_total += effective_weight
            volume_total += volume
            compounds[name] = compound
            source_details.append(f"{name}={compound:.2f}")

        # Normalize
        compound = round(weighted_sum / max(weight_total, 0.001), 4)
        compound = np.clip(compound, -1.0, 1.0)

        # Confidence: higher when sources agree
        if len(compounds) >= 2:
            values = list(compounds.values())
            # Agreement = low variance
            variance = np.var(values) if len(values) > 1 else 1.0
            agreement_score = np.clip(1.0 / (1.0 + variance * 5), 0.1, 1.0)
            # Also weight by how many sources
            count_score = min(len(compounds) / 5, 1.0)
            confidence = round(0.5 * agreement_score + 0.3 * count_score + 0.2 * max(weight_total, 0.5), 4)
        else:
            confidence = 0.3

        # Trend analysis
        trend = self._compute_trend(ticker, compound)

        return SentimentSignal(
            ticker=ticker,
            compound=compound,
            confidence=confidence,
            source_count=len(compounds),
            sources=compounds,
            mention_volume=volume_total,
            trend=trend,
            breakdown=" | ".join(source_details)
        )

    def _compute_trend(self, ticker: str, current: float) -> str:
        """Track sentiment momentum over recent samples."""
        if ticker not in self._history:
            self._history[ticker] = []
        self._history[ticker].append(current)
        if len(self._history[ticker]) > 20:
            self._history[ticker] = self._history[ticker][-20:]

        history = self._history[ticker]
        if len(history) < 3:
            return "stable"

        recent_avg = np.mean(history[-3:])
        prior_avg = np.mean(history[:-3]) if len(history) > 3 else recent_avg

        if recent_avg - prior_avg > 0.1:
            return "accelerating_bullish"
        elif recent_avg - prior_avg < -0.1:
            return "accelerating_bearish"
        return "stable"


# ============================================================
# Main Pipeline
# ============================================================

class NewsPipeline:
    """
    Multi-source news and sentiment data pipeline.
    Populates: market_news, social_sentiment, wsb_mentions, macro_indicators.

    API keys are read from environment variables:
        FINNHUB_API_KEY
        REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET
        STOCKTWITS_ACCESS_TOKEN (optional)
    """

    def __init__(self, finnhub_key: Optional[str] = None,
                 reddit_id: Optional[str] = None,
                 reddit_secret: Optional[str] = None):
        self.finnhub_key = finnhub_key or os.getenv('FINNHUB_API_KEY')
        self.reddit_id = reddit_id or os.getenv('REDDIT_CLIENT_ID')
        self.reddit_secret = reddit_secret or os.getenv('REDDIT_CLIENT_SECRET')
        self._reddit_token = None
        self._reddit_token_expiry = None
        self.aggregator = SentimentAggregator()
        self.vader = self.aggregator.vader
        self.finbert = self.aggregator.finbert

    # ── Finnhub: Market News (VADER + FinBERT) ────────────────

    def fetch_finnhub_news(self, ticker: str, days_back: int = 1) -> List[Dict]:
        """Fetch news and score with VADER (and FinBERT for high-severity items)."""
        if not self.finnhub_key:
            return []

        try:
            import requests
            from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            to_date = datetime.now().strftime('%Y-%m-%d')

            url = 'https://finnhub.io/api/v1/company-news'
            params = {
                'symbol': ticker,
                'from': from_date,
                'to': to_date,
                'token': self.finnhub_key
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            articles = resp.json()

            results = []
            for art in articles[:30]:
                headline = art.get('headline', '')
                summary = art.get('summary', '')
                text = f"{headline}. {summary}" if summary else headline
                if not text.strip():
                    continue

                # VADER scoring (always available)
                vader_scores = self.vader.score(text)
                compound = vader_scores['compound']

                # FinBERT for high-severity or ambiguous (VADER near neutral)
                severity = self._classify_severity(art)
                if severity == 'HIGH' or abs(compound) < 0.15:
                    finbert_scores = self.finbert.score(text)
                    if finbert_scores:
                        compound = finbert_scores['compound']  # override with FinBERT

                results.append({
                    'news_id': f"finnhub_{art.get('id', abs(hash(headline)))}",
                    'headline': headline,
                    'source': art.get('source', 'Finnhub'),
                    'severity': severity,
                    'timestamp': datetime.fromtimestamp(art['datetime']).isoformat(),
                    'related_tickers': self._extract_related(art, ticker),
                    'sentiment_polarity': round(compound, 4)
                })
            return results
        except Exception as e:
            print(f"[NewsPipeline] Finnhub news failed for {ticker}: {e}")
            return []

    def fetch_finnhub_sentiment(self, ticker: str) -> Optional[Dict]:
        """Fetch Finnhub aggregated social sentiment (Twitter/X data)."""
        if not self.finnhub_key:
            return None
        try:
            import requests
            url = 'https://finnhub.io/api/v1/stock/social-sentiment'
            resp = requests.get(url, params={'symbol': ticker, 'token': self.finnhub_key}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data:
                twitter = data.get('twitter', {})
                reddit = data.get('reddit', {})
                # Combine Twitter + Reddit from Finnhub
                total_mentions = twitter.get('mention', 0) + reddit.get('mention', 0)
                twitter_score = self._normalize_finnhub(twitter.get('sentiment', 0))
                reddit_score = self._normalize_finnhub(reddit.get('sentiment', 0))
                # Weighted average
                if total_mentions > 0:
                    compound = (twitter_score * twitter.get('mention', 0) +
                               reddit_score * reddit.get('mention', 0)) / total_mentions
                else:
                    compound = twitter_score

                return {
                    'ticker': ticker,
                    'source': 'twitter',
                    'score': round(compound, 4),
                    'volume': total_mentions,
                    'sample_timestamp': datetime.now().isoformat(),
                    'raw_twitter': twitter,
                    'raw_reddit': reddit
                }
        except Exception as e:
            print(f"[NewsPipeline] Finnhub sentiment failed for {ticker}: {e}")
        return None

    # ── StockTwits ────────────────────────────────────────────

    def fetch_stocktwits(self, ticker: str) -> Optional[Dict]:
        """
        Fetch StockTwits messages and sentiment.
        StockTwits has a public API — no key needed for basic access.
        Rate limit: ~200 requests/hour without auth.

        Returns social_sentiment-compatible dict.
        """
        try:
            import requests
            url = f'https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json'
            headers = {'User-Agent': 'RynStockTeam/2.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            messages = data.get('messages', [])
            if not messages:
                return None

            compounds = []
            for msg in messages[:50]:  # Last 50 messages
                body = msg.get('body', '')
                # StockTwits sentiment label (if user tagged it)
                sentiment_label = msg.get('entities', {}).get('sentiment', {})
                if sentiment_label:
                    label = sentiment_label.get('basic', '')
                    if label == 'Bullish':
                        compounds.append(0.7)
                    elif label == 'Bearish':
                        compounds.append(-0.7)
                    else:
                        compounds.append(self.vader.compound(body))
                else:
                    compounds.append(self.vader.compound(body))

            if not compounds:
                return None

            compound = float(np.mean(compounds))
            # Confidence based on agreement
            bullish_pct = sum(1 for c in compounds if c > 0.05) / len(compounds)
            bearish_pct = sum(1 for c in compounds if c < -0.05) / len(compounds)
            # Higher confidence when consensus is clear
            confidence = max(bullish_pct, bearish_pct)

            return {
                'ticker': ticker,
                'source': 'stocktwits',
                'score': round(np.clip(compound, -1.0, 1.0), 4),
                'volume': len(messages),
                'sample_timestamp': datetime.now().isoformat(),
                'bullish_ratio': round(bullish_pct, 3),
                'bearish_ratio': round(bearish_pct, 3),
                'confidence': round(confidence, 4)
            }
        except Exception as e:
            print(f"[NewsPipeline] StockTwits failed for {ticker}: {e}")
            return None

    # ── Reddit: WSB + Multi-Subreddit ─────────────────────────

    def _get_reddit_token(self) -> Optional[str]:
        """Get Reddit API access token. Cached until expiry."""
        if self._reddit_token and self._reddit_token_expiry > datetime.now():
            return self._reddit_token
        if not self.reddit_id or not self.reddit_secret:
            return None

        try:
            import requests
            auth = requests.auth.HTTPBasicAuth(self.reddit_id, self.reddit_secret)
            headers = {'User-Agent': 'RynStockTeam/2.0'}
            data = {'grant_type': 'client_credentials'}
            resp = requests.post('https://www.reddit.com/api/v1/access_token',
                               auth=auth, headers=headers, data=data, timeout=15)
            resp.raise_for_status()
            token_data = resp.json()
            self._reddit_token = token_data['access_token']
            self._reddit_token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)
            return self._reddit_token
        except Exception as e:
            print(f"[NewsPipeline] Reddit auth failed: {e}")
            return None

    def fetch_wsb_mentions(self, tickers: List[str]) -> List[Dict]:
        """Fetch WSB mention counts with VADER sentiment."""
        token = self._get_reddit_token()
        if not token:
            return []

        results = []
        try:
            import requests
            headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'RynStockTeam/2.0'}

            for ticker in tickers:
                url = 'https://oauth.reddit.com/r/wallstreetbets/search'
                params = {'q': f'${ticker}', 'sort': 'new', 'limit': 25,
                         't': 'day', 'type': 'link'}
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                if resp.status_code != 200:
                    continue

                posts = resp.json().get('data', {}).get('children', [])
                mention_count = len(posts)

                # VADER sentiment on titles + selftext
                compounds = []
                for post in posts:
                    text = post['data'].get('title', '')
                    selftext = post['data'].get('selftext', '')
                    if selftext:
                        text += '. ' + selftext[:200]  # first 200 chars
                    compounds.append(self.vader.compound(text))

                if compounds:
                    sentiment_polarity = float(np.mean(compounds))
                else:
                    sentiment_polarity = 0.0

                results.append({
                    'ticker': ticker,
                    'mention_count': mention_count,
                    'sentiment_polarity': round(np.clip(sentiment_polarity, -0.8, 0.8), 4),
                    'timestamp': datetime.now().isoformat()
                })
            return results
        except Exception as e:
            print(f"[NewsPipeline] WSB fetch failed: {e}")
            return results

    def fetch_reddit_sentiment(self, ticker: str, subreddits: List[str] = None) -> List[Dict]:
        """Fetch Reddit sentiment from multiple subreddits with VADER."""
        if subreddits is None:
            subreddits = ['wallstreetbets', 'stocks', 'investing', 'StockMarket',
                         'options', 'trading', 'daytrading']

        token = self._get_reddit_token()
        if not token:
            return []

        results = []
        try:
            import requests
            headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'RynStockTeam/2.0'}

            for sub in subreddits:
                url = f'https://oauth.reddit.com/r/{sub}/search'
                params = {'q': f'${ticker} OR {ticker}', 'sort': 'new',
                         'limit': 30, 't': 'day', 'type': 'comment'}
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                if resp.status_code != 200:
                    continue

                comments = resp.json().get('data', {}).get('children', [])
                if not comments:
                    continue

                compounds = []
                for c in comments:
                    body = c['data'].get('body', '')
                    if body:
                        compounds.append(self.vader.compound(body))

                if compounds:
                    score = float(np.mean(compounds))
                    # Confidence: how much do the comments agree?
                    pos_ratio = sum(1 for c in compounds if c > 0.05) / len(compounds)
                    confidence = max(pos_ratio, 1 - pos_ratio)  # agreement strength
                else:
                    score = 0.0
                    confidence = 0.0

                results.append({
                    'ticker': ticker,
                    'source': f'reddit_{sub}',
                    'score': round(np.clip(score, -0.7, 0.7), 4),
                    'volume': len(comments),
                    'sample_timestamp': datetime.now().isoformat(),
                    'confidence': round(confidence, 4)
                })
            return results
        except Exception as e:
            print(f"[NewsPipeline] Reddit sentiment failed for {ticker}: {e}")
            return results

    # ── Xueqiu (雪球) Chinese Community ───────────────────────

    def fetch_xueqiu(self, ticker: str) -> Optional[Dict]:
        """
        Fetch sentiment from Xueqiu (雪球) — Chinese retail investor platform.
        Uses unofficial API endpoint. No API key required.

        Supports US stocks via ticker symbol. Chinese stocks use numeric code.
        """
        try:
            import requests
            # Xueqiu search API — public endpoint
            url = 'https://xueqiu.com/query/v1/search/status.json'
            params = {
                'q': ticker,
                'count': 20,
                'type': '11',  # all posts
                'source': 'all'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://xueqiu.com/',
                'Accept': 'application/json'
            }

            # Xueqiu requires a cookie — get one first
            session = requests.Session()
            session.get('https://xueqiu.com/', headers={'User-Agent': headers['User-Agent']}, timeout=10)

            resp = session.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            items = data.get('list', [])
            if not items:
                return None

            compounds = []
            for item in items[:30]:
                text = item.get('text', '') or item.get('title', '')
                if not text:
                    continue
                # Clean HTML
                text = re.sub(r'<[^>]+>', '', text)
                # Try to detect sentiment indicators in Chinese context
                compounds.append(self._chinese_sentiment_score(text))

            if not compounds:
                return None

            compound = float(np.mean(compounds))
            confidence = max(
                sum(1 for c in compounds if c > 0.05) / len(compounds),
                sum(1 for c in compounds if c < -0.05) / len(compounds)
            )

            return {
                'ticker': ticker,
                'source': 'xueqiu',
                'score': round(np.clip(compound, -0.7, 0.7), 4),
                'volume': len(compounds),
                'sample_timestamp': datetime.now().isoformat(),
                'confidence': round(confidence, 4)
            }
        except Exception as e:
            print(f"[NewsPipeline] Xueqiu failed for {ticker}: {e}")
            return None

    @staticmethod
    def _chinese_sentiment_score(text: str) -> float:
        """
        Chinese sentiment detection using keyword lexicon + VADER fallback.
        Covers common Chinese investment forum terminology.
        """
        text_lower = text.lower()

        # Chinese bullish keywords
        bullish_cn = [
            '看涨', '做多', '满仓', '加仓', '抄底', '起飞', '暴涨', '涨停',
            '利好', '突破', '新高', '强势', '坚定持有', '价值投资', '低估',
            '回购', '分红', '龙头', '吃肉', '翻倍', '稳了', '冲', '梭哈',
            '格局', '长线', '低吸', '埋伏', '起飞了', '大肉'
        ]
        # Chinese bearish keywords
        bearish_cn = [
            '看跌', '做空', '清仓', '减仓', '暴跌', '跌停', '割肉', '套牢',
            '利空', '破位', '新低', '弱势', '止损', '出货', '高估', '雷',
            '暴雷', '退市', '停牌', '腰斩', '韭菜', '接盘', '跑路', '跳水',
            '崩盘', '亏', '砸盘', '诱多', '出货了'
        ]
        # English financial terms mixed in Chinese posts
        bullish_en = ['bull', 'long', 'buy', 'call', 'moon', '10x', '100x']
        bearish_en = ['bear', 'short', 'sell', 'put', 'dump', 'rug', 'dead']

        score = 0.0
        total = 0

        for kw in bullish_cn:
            if kw in text_lower:
                score += 1
                total += 1
        for kw in bearish_cn:
            if kw in text_lower:
                score -= 1
                total += 1
        for kw in bullish_en:
            if kw in text_lower:
                score += 0.5
                total += 1
        for kw in bearish_en:
            if kw in text_lower:
                score -= 0.5
                total += 1

        if total == 0:
            # Fallback: try VADER on any English portions
            eng_text = re.sub(r'[一-鿿]+', ' ', text)
            if eng_text.strip():
                v = VADERSentiment()
                return v.compound(eng_text)
            return 0.0

        return float(np.clip(score / max(total, 1) * 0.7, -0.7, 0.7))

    # ── Yahoo Finance: Macro Indicators ──────────────────────

    def fetch_macro_indicators(self) -> List[Dict]:
        """Fetch VIX, DXY, 10Y/2Y spread, SPY from Yahoo Finance."""
        symbols = {
            'VIX': '^VIX',
            'DXY': 'DX-Y.NYB',
            '10Y_Yield': '^TNX',
            '2Y_Yield': '^IRX',
            'SPY': 'SPY'
        }

        results = []
        now = datetime.now().isoformat()

        try:
            import yfinance as yf

            for name, sym in symbols.items():
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period='2d')
                    if hist.empty:
                        continue
                    current = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[0])
                    change_pct = round((current - prev) / prev * 100, 2)

                    results.append({
                        'indicator_name': name,
                        'value': round(current, 2),
                        'change_pct': change_pct,
                        'timestamp': now,
                        'period': 'daily'
                    })
                except Exception:
                    continue

            # Compute 10Y-2Y spread
            y10 = next((r['value'] for r in results if r['indicator_name'] == '10Y_Yield'), None)
            y2 = next((r['value'] for r in results if r['indicator_name'] == '2Y_Yield'), None)
            if y10 is not None and y2 is not None:
                results.append({
                    'indicator_name': '10Y_2Y_spread',
                    'value': round(y10 - y2, 4),
                    'change_pct': 0,
                    'timestamp': now,
                    'period': 'daily'
                })
            return results
        except Exception as e:
            print(f"[NewsPipeline] Macro fetch failed: {e}")
            return results

    # ── Bulk Fetch & Aggregate ────────────────────────────────

    def fetch_all(self, tickers: List[str], days_back: int = 1) -> Dict:
        """Fetch ALL data sources for a list of tickers."""
        return {
            'market_news': self._flat_fetch(self.fetch_finnhub_news, tickers, days_back),
            'social_sentiment': self._flat_fetch(self.fetch_finnhub_sentiment, tickers),
            'wsb_mentions': self.fetch_wsb_mentions(tickers),
            'macro_indicators': self.fetch_macro_indicators()
        }

    def get_ticker_sentiment(self, ticker: str) -> SentimentSignal:
        """
        Get comprehensive sentiment for a single ticker.
        Aggregates ALL available sources into one signal.

        This is the main entry point for trading decisions.
        """
        sources = {}

        # 1. Finnhub news → VADER + FinBERT
        news_articles = self.fetch_finnhub_news(ticker)
        if news_articles:
            compounds = [a['sentiment_polarity'] for a in news_articles]
            sources['finnhub_news'] = {
                'compound': float(np.mean(compounds)),
                'volume': len(news_articles),
                'confidence': 1.0 / (1.0 + float(np.std(compounds)) * 3)  # lower when polarized
            }
            # High-severity articles → also run FinBERT
            high_sev = [a for a in news_articles if a['severity'] == 'HIGH']
            if high_sev:
                finbert_compounds = []
                for a in high_sev:
                    fb = self.finbert.score(a['headline'])
                    if fb:
                        finbert_compounds.append(fb['compound'])
                if finbert_compounds:
                    sources['finbert'] = {
                        'compound': float(np.mean(finbert_compounds)),
                        'volume': len(finbert_compounds),
                        'confidence': 0.85
                    }

        # 2. Finnhub social sentiment (Twitter/X aggregated)
        finnhub_social = self.fetch_finnhub_sentiment(ticker)
        if finnhub_social:
            sources['finnhub_social'] = {
                'compound': finnhub_social['score'],
                'volume': finnhub_social['volume'],
                'confidence': 0.6
            }

        # 3. StockTwits
        stocktwits = self.fetch_stocktwits(ticker)
        if stocktwits:
            sources['stocktwits'] = {
                'compound': stocktwits['score'],
                'volume': stocktwits['volume'],
                'confidence': stocktwits.get('confidence', 0.5)
            }

        # 4. Reddit multi-subreddit
        reddit_data = self.fetch_reddit_sentiment(ticker)
        for r in reddit_data:
            sources[r['source']] = {
                'compound': r['score'],
                'volume': r['volume'],
                'confidence': r.get('confidence', 0.4)
            }

        # 5. WSB mentions
        wsb = self.fetch_wsb_mentions([ticker])
        if wsb:
            sources['reddit_wsb'] = {
                'compound': wsb[0]['sentiment_polarity'],
                'volume': wsb[0]['mention_count'],
                'confidence': 0.35  # WSB is noisy
            }

        # 6. Xueqiu (Chinese)
        xueqiu = self.fetch_xueqiu(ticker)
        if xueqiu:
            sources['xueqiu'] = {
                'compound': xueqiu['score'],
                'volume': xueqiu['volume'],
                'confidence': xueqiu.get('confidence', 0.4)
            }

        return self.aggregator.aggregate(ticker, sources)

    def get_bulk_sentiment(self, tickers: List[str]) -> Dict[str, SentimentSignal]:
        """Get aggregated sentiment for multiple tickers."""
        return {t: self.get_ticker_sentiment(t) for t in tickers}

    # ── Helpers ──────────────────────────────────────────────

    def _flat_fetch(self, fn, tickers, *args):
        results = []
        for t in tickers:
            res = fn(t, *args)
            if isinstance(res, list):
                results.extend(res)
            elif res is not None:
                results.append(res)
        return results

    @staticmethod
    def _classify_severity(article: Dict) -> str:
        headline = (article.get('headline', '') + ' ' + article.get('summary', '')).lower()
        high_keywords = ['crash', 'plunge', 'surge', 'shock', 'warns', 'probe', 'lawsuit',
                        'bankrupt', 'recall', 'investigation', 'downgrade', 'cut guidance',
                        'fraud', 'halt', 'delist', 'default', 'bankruptcy']
        medium_keywords = ['earnings', 'revenue', 'guidance', 'outlook', 'upgrade',
                          'acquisition', 'merger', 'layoff', 'restructuring', 'ipo']

        for kw in high_keywords:
            if kw in headline:
                return 'HIGH'
        for kw in medium_keywords:
            if kw in headline:
                return 'MEDIUM'
        return 'LOW'

    @staticmethod
    def _extract_related(article: Dict, primary: str) -> List[str]:
        related = article.get('related', '')
        tickers = [primary]
        if isinstance(related, str) and related:
            tickers.extend([t.strip() for t in related.split(',') if t.strip()])
        return tickers

    @staticmethod
    def _normalize_finnhub(raw_score: float) -> float:
        """Normalize Finnhub sentiment from their scale to [-1, 1]."""
        return round(np.clip(raw_score, -1.0, 1.0), 4)


# ============================================================
# Standalone Functions
# ============================================================

def run_news_pipeline(tickers: List[str], days_back: int = 1) -> Dict[str, List]:
    """Convenience: fetch all raw data for database insertion."""
    pipeline = NewsPipeline()
    return pipeline.fetch_all(tickers, days_back)


def get_sentiment(ticker: str) -> SentimentSignal:
    """Convenience: get aggregated sentiment for one ticker."""
    pipeline = NewsPipeline()
    return pipeline.get_ticker_sentiment(ticker)


def get_bulk_sentiment(tickers: List[str]) -> Dict[str, SentimentSignal]:
    """Convenience: get aggregated sentiment for multiple tickers."""
    pipeline = NewsPipeline()
    return pipeline.get_bulk_sentiment(tickers)
