"""
News, Sentiment, and Macro Data Pipeline
========================================
Fetches from: Finnhub (news, sentiment), Reddit (WSB mentions),
Yahoo Finance (macro: VIX, DXY, yields).

Each source is optional — degrades gracefully if API keys are missing.
Results are formatted to match data_catalog.yaml table schemas.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pandas as pd
import numpy as np


class NewsPipeline:
    """
    Multi-source news and sentiment data pipeline.
    Populates: market_news, social_sentiment, wsb_mentions, macro_indicators.

    API keys are read from environment variables:
        FINNHUB_API_KEY
        REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET
    """

    def __init__(self, finnhub_key: Optional[str] = None,
                 reddit_id: Optional[str] = None,
                 reddit_secret: Optional[str] = None):
        self.finnhub_key = finnhub_key or os.getenv('FINNHUB_API_KEY')
        self.reddit_id = reddit_id or os.getenv('REDDIT_CLIENT_ID')
        self.reddit_secret = reddit_secret or os.getenv('REDDIT_CLIENT_SECRET')
        self._reddit_token = None
        self._reddit_token_expiry = None

    # ── Finnhub: Market News ─────────────────────────────────

    def fetch_finnhub_news(self, ticker: str, days_back: int = 1) -> List[Dict]:
        """
        Fetch news for a ticker from Finnhub.
        Returns list of dicts matching market_news table schema.
        """
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
            for art in articles[:20]:  # cap at 20 per ticker
                results.append({
                    'news_id': f"finnhub_{art.get('id', hash(art['headline']))}",
                    'headline': art.get('headline', ''),
                    'source': art.get('source', 'Finnhub'),
                    'severity': self._classify_severity(art),
                    'timestamp': datetime.fromtimestamp(art['datetime']).isoformat(),
                    'related_tickers': self._extract_related(art, ticker),
                    'sentiment_polarity': self._compute_sentiment(art.get('summary', '') or art.get('headline', ''))
                })
            return results
        except Exception as e:
            print(f"[NewsPipeline] Finnhub news failed for {ticker}: {e}")
            return []

    def fetch_finnhub_sentiment(self, ticker: str) -> Optional[Dict]:
        """Fetch Finnhub social sentiment data."""
        if not self.finnhub_key:
            return None
        try:
            import requests
            url = 'https://finnhub.io/api/v1/stock/social-sentiment'
            resp = requests.get(url, params={'symbol': ticker, 'token': self.finnhub_key}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data:
                return {
                    'ticker': ticker,
                    'source': 'twitter',
                    'score': self._normalize_score(data.get('twitter', {}).get('sentiment', 0)),
                    'volume': data.get('twitter', {}).get('mention', 0),
                    'sample_timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"[NewsPipeline] Finnhub sentiment failed for {ticker}: {e}")
        return None

    # ── Reddit: WSB Mentions ─────────────────────────────────

    def _get_reddit_token(self) -> Optional[str]:
        """Get Reddit API access token. Cached until expiry."""
        if self._reddit_token and self._reddit_token_expiry > datetime.now():
            return self._reddit_token
        if not self.reddit_id or not self.reddit_secret:
            return None

        try:
            import requests
            auth = requests.auth.HTTPBasicAuth(self.reddit_id, self.reddit_secret)
            headers = {'User-Agent': 'AgentTeam/2.0'}
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
        """
        Fetch WSB mention counts and sentiment.
        Scrapes r/wallstreetbets top posts and comments for ticker mentions.
        Returns list of dicts matching wsb_mentions table schema.
        """
        token = self._get_reddit_token()
        if not token:
            return []

        results = []
        try:
            import requests
            headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'AgentTeam/2.0'}

            for ticker in tickers:
                # Search WSB for ticker mentions in last 24h
                url = 'https://oauth.reddit.com/r/wallstreetbets/search'
                params = {'q': f'${ticker}', 'sort': 'new', 'limit': 25,
                         't': 'day', 'type': 'link'}
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                if resp.status_code != 200:
                    continue

                posts = resp.json().get('data', {}).get('children', [])
                mention_count = len(posts)

                # Simple sentiment: count bullish/bearish keywords in titles
                sentiment_score = 0.0
                for post in posts:
                    title = post['data'].get('title', '')
                    sentiment_score += self._keyword_sentiment(title)

                sentiment_polarity = np.clip(
                    sentiment_score / max(mention_count, 1) * 0.3,
                    -0.8, 0.8
                )

                results.append({
                    'ticker': ticker,
                    'mention_count': mention_count,
                    'sentiment_polarity': round(float(sentiment_polarity), 4),
                    'timestamp': datetime.now().isoformat()
                })
            return results
        except Exception as e:
            print(f"[NewsPipeline] WSB fetch failed: {e}")
            return results

    def fetch_reddit_sentiment(self, ticker: str, subreddits: List[str] = None) -> List[Dict]:
        """
        Fetch sentiment from multiple subreddits.
        Returns list of dicts matching social_sentiment table schema.
        """
        if subreddits is None:
            subreddits = ['wallstreetbets', 'stocks', 'investing']

        token = self._get_reddit_token()
        if not token:
            return []

        results = []
        try:
            import requests
            headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'AgentTeam/2.0'}

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

                sentiment_sum = 0.0
                for c in comments:
                    body = c['data'].get('body', '')
                    sentiment_sum += self._keyword_sentiment(body)

                score = np.clip(sentiment_sum / max(len(comments), 1) * 0.25, -0.7, 0.7)
                results.append({
                    'ticker': ticker,
                    'source': sub,
                    'score': round(float(score), 4),
                    'volume': len(comments),
                    'sample_timestamp': datetime.now().isoformat()
                })
            return results
        except Exception as e:
            print(f"[NewsPipeline] Reddit sentiment failed for {ticker}: {e}")
            return results

    # ── Yahoo Finance: Macro Indicators ──────────────────────

    def fetch_macro_indicators(self) -> List[Dict]:
        """
        Fetch VIX, DXY, 10Y/2Y spread from Yahoo Finance.
        Returns list of dicts matching macro_indicators table schema.
        """
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

            # Compute 10Y-2Y spread if both are available
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

    # ── Bulk Fetch ───────────────────────────────────────────

    def fetch_all(self, tickers: List[str], days_back: int = 1) -> Dict[str, List]:
        """
        Fetch all data for a list of tickers.
        Returns dict keyed by table name with list of row dicts.
        """
        return {
            'market_news': self._flat_fetch(self.fetch_finnhub_news, tickers, days_back),
            'social_sentiment': self._flat_fetch(self.fetch_finnhub_sentiment, tickers),
            'wsb_mentions': self.fetch_wsb_mentions(tickers),
            'macro_indicators': self.fetch_macro_indicators()
        }

    def _flat_fetch(self, fn, tickers, *args):
        results = []
        for t in tickers:
            res = fn(t, *args)
            if isinstance(res, list):
                results.extend(res)
            elif res is not None:
                results.append(res)
        return results

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _classify_severity(article: Dict) -> str:
        """Classify news severity based on headline keywords and source."""
        headline = (article.get('headline', '') + ' ' + article.get('summary', '')).lower()
        high_keywords = ['crash', 'plunge', 'surge', 'shock', 'warns', 'probe', 'lawsuit',
                        'bankrupt', 'recall', 'investigation', 'downgrade', 'cut guidance']
        medium_keywords = ['earnings', 'revenue', 'guidance', 'outlook', 'upgrade',
                          'acquisition', 'merger', 'layoff', 'restructuring']

        for kw in high_keywords:
            if kw in headline:
                return 'HIGH'
        for kw in medium_keywords:
            if kw in headline:
                return 'MEDIUM'
        return 'LOW'

    @staticmethod
    def _extract_related(article: Dict, primary: str) -> List[str]:
        """Extract related tickers from article text."""
        related = article.get('related', '')
        tickers = [primary]
        if isinstance(related, str) and related:
            tickers.extend([t.strip() for t in related.split(',') if t.strip()])
        return tickers

    @staticmethod
    def _compute_sentiment(text: str) -> float:
        """Simple keyword-based sentiment score for news text."""
        if not text:
            return 0.0
        text = text.lower()
        bullish = ['beat', 'raise', 'upgrade', 'growth', 'profit', 'record', 'strong',
                   'positive', 'outperform', 'buyback', 'dividend', 'expansion']
        bearish = ['miss', 'cut', 'downgrade', 'loss', 'decline', 'weak', 'negative',
                   'underperform', 'probe', 'lawsuit', 'layoff', 'warning']

        score = sum(1 for w in bullish if w in text)
        score -= sum(1 for w in bearish if w in text)
        return round(np.clip(score / 5, -0.8, 0.8), 4)

    @staticmethod
    def _keyword_sentiment(text: str) -> float:
        """Keyword sentiment for social media text (more informal)."""
        if not text:
            return 0.0
        text = text.lower()
        bullish = ['moon', 'rocket', 'bull', 'long', 'calls', 'buy', 'dip',
                   'green', 'pump', 'squeeze', 'yolo', 'gem', 'undervalued']
        bearish = ['dump', 'bear', 'short', 'puts', 'sell', 'bag', 'red',
                   'crash', 'rug', 'scam', 'overvalued', 'top']

        score = sum(1 for w in bullish if w in text)
        score -= sum(1 for w in bearish if w in text)
        return score

    @staticmethod
    def _normalize_score(raw_score: float) -> float:
        """Normalize Finnhub sentiment to [-1, 1] range."""
        return round(np.clip(raw_score, -1.0, 1.0), 4)


# ── Standalone fetch ─────────────────────────────────────────

def run_news_pipeline(tickers: List[str], days_back: int = 1) -> Dict[str, List]:
    """Convenience function: fetch all news/sentiment/macro data."""
    pipeline = NewsPipeline()
    return pipeline.fetch_all(tickers, days_back)
