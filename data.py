# data.py - downloads free share price data from Yahoo Finance (using yfinance)
# NOTE: this data is free, delayed and unofficial. Do not trust it for real money decisions.
import pandas as pd  # pandas holds tables of data
import yfinance as yf  # yfinance downloads free data from Yahoo Finance

# Instruments are grouped for the sidebar. Every friendly name maps to a Yahoo code.
# INDICES are practice-only: you cannot buy an index itself, but you CAN test
# strategies on its price. COMMODITY FUTURES are priced in US dollars (USD),
# not rupees. Yahoo does not carry Indian index futures or MCX commodities,
# so the futures here are the big world ones (gold, silver, oil, gas, copper).
STOCK_GROUPS = {
    "Index (India)": {
        "NIFTY 50": "^NSEI",  # the Nifty 50 index
        "NIFTY NEXT 50": "^NSMIDCP",  # the next 50 companies after the Nifty 50
        "NIFTY 100": "^CNX100",
        "NIFTY 200": "^CNX200",
        "NIFTY MIDCAP 50": "^NSEMDCP50",
        "BANK NIFTY": "^NSEBANK",  # banking sector index
        "SENSEX": "^BSESN",  # the BSE Sensex
        "NIFTY IT": "^CNXIT",
        "NIFTY AUTO": "^CNXAUTO",
        "NIFTY PHARMA": "^CNXPHARMA",
        "NIFTY FMCG": "^CNXFMCG",
        "NIFTY METAL": "^CNXMETAL",
        "NIFTY ENERGY": "^CNXENERGY",
        "NIFTY REALTY": "^CNXREALTY",
        "NIFTY PSU BANK": "^CNXPSUBANK",
        "NIFTY PSE": "^CNXPSE",  # public sector companies
        "NIFTY INFRA": "^CNXINFRA",
        "INDIA VIX": "^INDIAVIX",  # fear index: high means the market is nervous
    },
    "Stock (India)": {
        "RELIANCE": "RELIANCE.NS",  # .NS means NSE India
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
        "HDFCBANK": "HDFCBANK.NS",
    },
    "Commodity Future (USD)": {
        "GOLD FUTURE": "GC=F",  # gold futures, priced in US dollars
        "SILVER FUTURE": "SI=F",
        "CRUDE OIL FUTURE": "CL=F",
        "NATURAL GAS FUTURE": "NG=F",
        "COPPER FUTURE": "HG=F",
    },
}

# Flat lookup: friendly name -> Yahoo code. Used everywhere in the app.
STOCKS = {name: code for group in STOCK_GROUPS.values() for name, code in group.items()}

# Currency mark for display only: "Rs" for Indian things, "$" for USD futures.
CURRENCY = {}
for _group_name, _group in STOCK_GROUPS.items():
    for _name in _group:
        CURRENCY[_name] = "$" if _group_name.endswith("(USD)") else "Rs"


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
