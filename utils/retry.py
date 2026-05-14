"""
Retry wrapper for yfinance and other network calls.
Usage: from utils.retry import fetch_with_retry
       data = fetch_with_retry(lambda: yf.Ticker(sym).history(period='2y'))
"""
import time
import random
import logging

log = logging.getLogger(__name__)

RETRYABLE = (ConnectionError, TimeoutError, OSError)


def fetch_with_retry(func, max_retries=3, base_delay=1.0, backoff=2.0, jitter=True):
    """Call func() with exponential backoff retry."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func()
        except RETRYABLE as e:
            last_exc = e
            if attempt < max_retries - 1:
                delay = base_delay * (backoff ** attempt)
                if jitter:
                    delay *= 0.5 + random.random() * 0.5
                log.warning("Network error (attempt %d/%d): %s. Retrying in %.1fs",
                           attempt + 1, max_retries, e, delay)
                time.sleep(delay)
        except Exception:
            raise

    log.error("All %d attempts failed. Last error: %s", max_retries, last_exc)
    raise last_exc


def yf_history(ticker, **kwargs):
    """
    Fetch yfinance history with retry.
    Usage: df = yf_history('AAPL', period='2y')
    """
    import yfinance as yf
    t = yf.Ticker(ticker)
    return fetch_with_retry(lambda: t.history(**kwargs))


def yf_info(ticker):
    """Fetch yfinance info dict with retry."""
    import yfinance as yf
    t = yf.Ticker(ticker)
    return fetch_with_retry(lambda: t.info)


def yf_news(ticker):
    """Fetch yfinance news with retry."""
    import yfinance as yf
    t = yf.Ticker(ticker)
    return fetch_with_retry(lambda: t.news or [])
