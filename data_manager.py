import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _cache_path(ticker: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, f"{ticker}.csv")


def _download(ticker: str, start: str = None) -> pd.Series:
    kwargs = dict(auto_adjust=True, progress=False)
    if start:
        kwargs["start"] = start
    else:
        kwargs["period"] = "max"
    df = yf.download(ticker, **kwargs)
    if df.empty:
        return pd.Series(dtype=float, name=ticker)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.name = ticker
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.dropna()


def get_ticker_data(ticker: str) -> pd.Series:
    """Return adjusted close price series for ticker, using local cache + incremental update."""
    path = _cache_path(ticker)

    if os.path.exists(path):
        cached = pd.read_csv(path, index_col=0, parse_dates=True).squeeze("columns")
        cached.name = ticker
        cached.index = pd.to_datetime(cached.index).tz_localize(None)

        last_date = cached.index[-1].date()
        today = datetime.now().date()
        # No update needed if data is current (allow 1-day lag for weekends/holidays)
        if last_date >= today - timedelta(days=1):
            return cached

        start = (cached.index[-1] + timedelta(days=1)).strftime("%Y-%m-%d")
        new = _download(ticker, start=start)
        if not new.empty:
            combined = pd.concat([cached, new])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            combined.to_csv(path)
            return combined
        return cached
    else:
        data = _download(ticker)
        if not data.empty:
            data.to_csv(path)
        return data


def get_price_data(tickers: list[str]) -> pd.DataFrame:
    """Return DataFrame of adjusted close prices for all tickers, aligned on trading dates."""
    series = {t: get_ticker_data(t) for t in tickers}
    df = pd.DataFrame(series)
    df.sort_index(inplace=True)
    return df
