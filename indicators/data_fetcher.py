"""
Data Fetcher — Multi-Source OHLCV Provider
==========================================
Priority: Cloud DB → Yahoo Finance fallback → Empty (alert)

Usage:
    fetcher = DataFetcher(cloud_db_config={...})
    df = fetcher.get_ohlcv('NVDA', period='6mo', interval='1d')
    # → DataFrame with [open, high, low, close, volume], datetime index
"""

from typing import Optional, Dict
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class DataFetcher:
    """Multi-source data fetcher with automatic fallback (cloud DB, then Yahoo Finance)."""

    def __init__(self, cloud_db_config: Optional[Dict] = None,
                 yfinance_enabled: bool = True):
        """Initialize with optional cloud DB config and Yahoo Finance toggle."""
        self.cloud_config = cloud_db_config
        self.yf_enabled = yfinance_enabled
        self._cloud_conn = None
        if cloud_db_config:
            self._init_cloud_db()

    # ── Cloud DB ───────────────────────────────────────────

    def _init_cloud_db(self):
        """Initialize cloud database connection via SQLAlchemy."""
        try:
            # Uncomment and configure based on your cloud DB type:
            # from sqlalchemy import create_engine
            # conn_str = (
            #     f"mysql+pymysql://{self.cloud_config['user']}:{self.cloud_config['password']}"
            #     f"@{self.cloud_config['host']}:{self.cloud_config['port']}/{self.cloud_config['db']}"
            # )
            # self._cloud_conn = create_engine(conn_str)
            #
            # Or for PostgreSQL:
            # conn_str = (
            #     f"postgresql+psycopg2://{self.cloud_config['user']}:{self.cloud_config['password']}"
            #     f"@{self.cloud_config['host']}:{self.cloud_config['port']}/{self.cloud_config['db']}"
            # )
            # self._cloud_conn = create_engine(conn_str)
            pass
        except Exception as e:
            print(f"[DataFetcher] Cloud DB init failed: {e}. Will use Yahoo Finance only.")
            self.cloud_config = None

    def _fetch_from_cloud(self, ticker: str, start_date: str,
                          end_date: str, interval: str = '1d') -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from cloud database."""
        # Expected schema: ohlcv(ticker, date, open, high, low, close, volume)
        if not self._cloud_conn or not self.cloud_config:
            return None

        try:
            table = self.cloud_config.get('table', 'ohlcv')
            query = f"""
                SELECT date, open, high, low, close, volume
                FROM {table}
                WHERE ticker = %(ticker)s
                  AND date BETWEEN %(start)s AND %(end)s
                ORDER BY date ASC
            """
            params = {'ticker': ticker.upper(), 'start': start_date, 'end': end_date}
            df = pd.read_sql(query, self._cloud_conn, params=params, index_col='date')
            if not df.empty:
                return df
        except Exception as e:
            print(f"[DataFetcher] Cloud DB query failed for {ticker}: {e}")
        return None

    # ── Yahoo Finance fallback ─────────────────────────────

    def _fetch_from_yfinance(self, ticker: str, period: str = '6mo',
                             interval: str = '1d') -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Yahoo Finance."""
        if not self.yf_enabled:
            return None

        try:
            import yfinance as yf

            # yf.download handles delisted/empty tickers more gracefully
            df = yf.download(ticker, period=period, interval=interval,
                           progress=False, auto_adjust=True)

            if df is None or df.empty:
                print(f"[DataFetcher] Yahoo Finance returned empty data for {ticker}")
                return None

            # Handle MultiIndex columns from download()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Standardize to lowercase
            rename_map = {
                'Open': 'open', 'High': 'high', 'Low': 'low',
                'Close': 'close', 'Volume': 'volume',
                'Adj Close': 'adj_close'
            }
            df = df.rename(columns=rename_map)

            # Keep only OHLCV
            keep_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[[c for c in keep_cols if c in df.columns]]
            return df

        except Exception as e:
            print(f"[DataFetcher] Yahoo Finance failed for {ticker}: {e}")
        return None

    # ── Main API ───────────────────────────────────────────

    def get_ohlcv(self, ticker: str, period: str = '6mo',
                  interval: str = '1d') -> pd.DataFrame:
        """Get OHLCV data with automatic source fallback (cloud DB then Yahoo Finance)."""
        end_date = datetime.now()
        start_date = self._period_to_start(end_date, period)

        # 1. Historical: try cloud DB first (yesterday and earlier)
        df_hist = self._fetch_from_cloud(ticker,
                                          start_date.strftime('%Y-%m-%d'),
                                          (end_date - timedelta(days=1)).strftime('%Y-%m-%d'),
                                          interval)
        source_hist = 'cloud_db' if df_hist is not None and not df_hist.empty else None

        # 2. If no cloud DB or cloud DB empty, fallback to Yahoo Finance for full history
        if source_hist is None:
            df_full = self._fetch_from_yfinance(ticker, period, interval)
            if df_full is None or df_full.empty:
                raise ValueError(
                    f"All data sources failed for {ticker}. "
                    f"Cloud DB: {'configured' if self.cloud_config else 'not configured'}, "
                    f"Yahoo Finance: {'enabled' if self.yf_enabled else 'disabled'}."
                )
            df_full = df_full.sort_index()
            df_full = df_full[~df_full.index.duplicated(keep='last')]
            return df_full

        # 3. Today's data: always from Yahoo Finance (cloud DB doesn't have it)
        today_df = None
        if self.yf_enabled:
            today_df = self._fetch_from_yfinance(ticker, '1d', interval)
            if today_df is not None:
                today_start = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                today_df = today_df[today_df.index >= today_start]

        # 4. Merge: cloud history + yfinance today
        if today_df is not None and not today_df.empty:
            df = pd.concat([df_hist, today_df])
        else:
            df = df_hist

        df = df.sort_index()
        df = df[~df.index.duplicated(keep='last')]
        return df

    def _fill_recent_from_yfinance(self, ticker: str,
                                    cloud_df: pd.DataFrame,
                                    interval: str = '1d') -> pd.DataFrame:
        """Fill recent missing bars from Yahoo Finance when cloud DB lags."""
        if interval in ('1m', '2m', '5m', '15m', '30m', '60m', '1h', '90m'):
            yf_period = '5d'
        else:
            yf_period = '5d'  # Last 5 trading days covers any DB lag

        yf_df = self._fetch_from_yfinance(ticker, yf_period, interval)
        if yf_df is None or yf_df.empty:
            return cloud_df

        # Only take bars newer than cloud's latest bar
        latest_cloud_ts = cloud_df.index.max()
        new_bars = yf_df[yf_df.index > latest_cloud_ts]

        if not new_bars.empty:
            return pd.concat([cloud_df, new_bars])

        return cloud_df

    def _period_to_start(self, end: datetime, period: str) -> datetime:
        """Convert Yahoo Finance period string to absolute start date."""
        period_map = {
            '1d':  timedelta(days=1),
            '5d':  timedelta(days=7),    # 5 trading days ≈ 7 calendar days
            '1mo': timedelta(days=35),
            '3mo': timedelta(days=95),
            '6mo': timedelta(days=185),
            '1y':  timedelta(days=370),
            '2y':  timedelta(days=740),
            '5y':  timedelta(days=1830),
            '10y': timedelta(days=3650),
            'max': timedelta(days=7300),  # 20 years
        }
        delta = period_map.get(period, timedelta(days=185))
        return end - delta


# ============================================================
# Quick integration helper
# ============================================================

def fetch_and_compute(ticker: str, fetcher: DataFetcher,
                      period: str = '6mo', interval: str = '1d',
                      timestamp: Optional[str] = None) -> list:
    """Fetch OHLCV data and compute all indicators, returning table-ready rows."""
    from indicators.compute_indicators import compute_all_indicators, to_table_rows

    df = fetcher.get_ohlcv(ticker, period, interval)
    indicators = compute_all_indicators(df)
    ts = timestamp or datetime.now().isoformat()
    return to_table_rows(ticker, indicators, ts)
