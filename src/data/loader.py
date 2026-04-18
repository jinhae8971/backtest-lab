"""Data loading for Backtrader backtests — yfinance primary."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

import pandas as pd


def load_yfinance_data(
    ticker: str,
    *,
    period: str | None = None,
    start: str | None = None,
    end: str | None = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """Load OHLCV data from yfinance.

    Returns DataFrame with columns: open, high, low, close, volume
    Index: DatetimeIndex
    """
    import yfinance as yf

    kwargs = {"interval": interval, "progress": False, "auto_adjust": False}
    if start or end:
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end
    else:
        kwargs["period"] = period or "5y"

    df = yf.download(ticker, **kwargs)
    if df is None or len(df) == 0:
        raise ValueError(f"No data for {ticker}")

    # Flatten multi-level columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    # Lowercase
    df.columns = [c.lower() for c in df.columns]
    # Standardize column names
    df = df.rename(columns={"adj close": "adj_close"})

    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Got: {list(df.columns)}")

    return df[["open", "high", "low", "close", "volume"]]


def load_backtrader_feed(
    ticker: str,
    *,
    period: str | None = None,
    start: str | None = None,
    end: str | None = None,
    interval: str = "1d",
):
    """Load data directly as a Backtrader data feed.

    Returns:
        bt.feeds.PandasData object ready to add to Cerebro.
    """
    import backtrader as bt

    df = load_yfinance_data(
        ticker, period=period, start=start, end=end, interval=interval,
    )
    # Backtrader expects specific column names
    df = df.rename(columns={
        "open": "open", "high": "high", "low": "low",
        "close": "close", "volume": "volume",
    })
    return bt.feeds.PandasData(
        dataname=df,
        name=ticker,
        timeframe=bt.TimeFrame.Days,
    )
