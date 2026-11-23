# data.py - downloads free share price data from Yahoo Finance (using yfinance)
# NOTE: this data is free, delayed and unofficial. Do not trust it for real money decisions.
import pandas as pd  # pandas holds tables of data
import yfinance as yf  # yfinance downloads free data from Yahoo Finance

# Names shown in the sidebar and the Yahoo code for each one
STOCKS = {
    "NIFTY 50": "^NSEI",  # the Nifty 50 index
    "RELIANCE": "RELIANCE.NS",  # .NS means NSE India
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
}


class DataError(Exception):
    """A simple error with a friendly message we can show on screen."""


def download_prices(symbol, start, end):
    """Download daily prices (Open, High, Low, Close, Volume) between two dates."""
    try:
        # Download daily data. auto_adjust=True fixes prices for splits and dividends
        df = yf.download(symbol, start=str(start), end=str((pd.Timestamp(end) + pd.Timedelta(days=1)).date()),
                         progress=False, auto_adjust=True)
    except Exception as e:  # internet problem, Yahoo busy, etc.
        raise DataError(f"Could not download data. Check your internet and try again in a minute. ({e})")
    if df is None or df.empty:  # nothing came back
        raise DataError("Yahoo Finance returned no data. It may be busy (rate limit) or the dates are wrong. "
                        "Wait one minute and try again.")
    if isinstance(df.columns, pd.MultiIndex):  # newer yfinance gives two-level column names
        df.columns = df.columns.get_level_values(0)  # keep only the first level
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()  # keep needed columns, drop empty rows
    df.index = pd.to_datetime(df.index).tz_localize(None)  # remove time zone so dates are simple
    return df


def latest_price(symbol):
    """Get the latest (delayed) price. Returns (price, time_text)."""
    try:
        df = yf.download(symbol, period="5d", interval="1d", progress=False, auto_adjust=True)
    except Exception as e:
        raise DataError(f"Could not fetch the latest price. ({e})")
    if df is None or df.empty:
        raise DataError("Could not fetch the latest price. Yahoo may be busy. Try again in a minute.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    last = df.dropna().iloc[-1]  # the newest row
    return float(last["Close"]), str(df.dropna().index[-1].date())
