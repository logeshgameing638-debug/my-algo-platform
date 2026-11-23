# strategy.py - the trading rules. Each strategy says when to BUY (enter) and when to SELL (exit).
# All strategies are classic beginner ideas. None of them is a promise of profit.
import numpy as np  # numbers
import pandas as pd  # tables

STOP_LOSS_PCT = 1.0  # every trade risks at most 1% (stop-loss)
TARGET_PCT = 2.0  # every trade aims for 2% profit (target)


def stop_and_target(entry_price):
    """Return (stop_loss_price, target_price). Every trade MUST have both."""
    stop = entry_price * (1 - STOP_LOSS_PCT / 100)  # price 1% below entry
    target = entry_price * (1 + TARGET_PCT / 100)  # price 2% above entry
    return stop, target


# ---------- small helper tools used by the strategies ----------
def sma(s, n):
    return s.rolling(n).mean()  # simple moving average: plain average of last n closes


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()  # exponential average: newer days count more


def rsi(close, n=14):
    change = close.diff()  # today's close minus yesterday's close
    gain = change.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()  # average gain
    loss = (-change.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()  # average loss
    rs = gain / loss.replace(0, np.nan)  # gain divided by loss
    return 100 - 100 / (1 + rs)  # RSI goes from 0 to 100


def cross_up(a, b):
    """True on the day line a moves from below line b to above it."""
    above = a > b  # True when a is above b
    return above & ~above.shift(1, fill_value=False)  # above today but not yesterday


def cross_down(a, b):
    """True on the day line a moves from above line b to below it."""
    return cross_up(b, a)  # same idea, flipped


def add_indicators(df):
    """Add MA20, MA50, RSI and breakout levels to the price table (used by charts too)."""
    df = df.copy()  # do not change the original table
    df["MA20"] = sma(df["Close"], 20)
    df["MA50"] = sma(df["Close"], 50)
    df["RSI"] = rsi(df["Close"], 14)
    df["High20"] = df["High"].rolling(20).max().shift(1)  # highest high of the PREVIOUS 20 days
    df["Low10"] = df["Low"].rolling(10).min().shift(1)  # lowest low of the PREVIOUS 10 days
    return df


# ---------- the strategies: each returns (entry, exit) True/False columns ----------
def ma_cross(fast, slow):
    def f(d):
        a, b = sma(d["Close"], fast), sma(d["Close"], slow)  # fast and slow averages
        return cross_up(a, b) & b.notna(), cross_down(a, b)  # BUY on cross up, SELL on cross down
    return f


def ema_cross(fast, slow):
    def f(d):
        a, b = ema(d["Close"], fast), ema(d["Close"], slow)  # fast and slow exponential averages
        return cross_up(a, b) & (d["Close"].expanding().count() > slow), cross_down(a, b)
    return f


def rsi_level(n, low, high):
    def f(d):
        r = rsi(d["Close"], n)  # RSI over n days
        return r < low, r > high  # BUY when oversold, SELL when overbought
    return f


def breakout(n_in, n_out):
    def f(d):
        hi = d["High"].rolling(n_in).max().shift(1)  # highest high of the previous n_in days
        lo = d["Low"].rolling(n_out).min().shift(1)  # lowest low of the previous n_out days
        return d["Close"] > hi, d["Close"] < lo  # BUY on breakout up, SELL on breakdown
    return f


def macd_cross(d):
    line = ema(d["Close"], 12) - ema(d["Close"], 26)  # MACD line
    signal = ema(line, 9)  # signal line
    return cross_up(line, signal), cross_down(line, signal)


def macd_zero(d):
    line = ema(d["Close"], 12) - ema(d["Close"], 26)  # MACD line
    signal = ema(line, 9)
    return cross_up(line, signal) & (line > 0), cross_down(line, signal)  # only buy when MACD is above zero


def boll_revert(d):
    mid = sma(d["Close"], 20)  # middle band
    sd = d["Close"].rolling(20).std()  # how much price moves around
    return d["Close"] < mid - 2 * sd, d["Close"] > mid  # BUY at lower band, SELL back at middle


def boll_break(d):
    mid = sma(d["Close"], 20)
    sd = d["Close"].rolling(20).std()
    return cross_up(d["Close"], mid + 2 * sd), d["Close"] < mid  # BUY on break above upper band


def momentum(n, level):
    def f(d):
        roc = (d["Close"] / d["Close"].shift(n) - 1) * 100  # % change over n days
        return cross_up(roc, pd.Series(level, index=d.index)), cross_down(roc, pd.Series(0, index=d.index))
    return f


def price_vs_ma(n):
    def f(d):
        m = sma(d["Close"], n)
        return cross_up(d["Close"], m) & m.notna(), cross_down(d["Close"], m)  # price crosses its average
    return f


def stochastic(d):
    lo = d["Low"].rolling(14).min()
    hi = d["High"].rolling(14).max()
    k = 100 * (d["Close"] - lo) / (hi - lo).replace(0, np.nan)  # where the close sits in the 14-day range
    return k < 20, k > 80


def rsi2_pullback(d):
    r = rsi(d["Close"], 2)  # very fast RSI
    up = d["Close"] > sma(d["Close"], 200)  # only buy dips in a long-term uptrend
    return (r < 10) & up, r > 70


# ---------- ADVANCED strategies (still long-only, same 1% stop-loss and 2% target) ----------
def atr(d, n=10):
    prev = d["Close"].shift(1)  # yesterday's close
    tr = pd.concat([d["High"] - d["Low"], (d["High"] - prev).abs(), (d["Low"] - prev).abs()], axis=1).max(axis=1)  # true range: biggest daily swing
    return tr.ewm(alpha=1 / n, adjust=False).mean()  # smoothed average of that swing


def supertrend(d):
    a = atr(d, 10)  # how much price normally swings
    mid = (d["High"] + d["Low"]) / 2  # middle of the day's range
    upper = (mid + 3 * a).values  # line above price
    lower = (mid - 3 * a).values  # line below price
    close = d["Close"].values
    n = len(d)
    fu, fl = upper.copy(), lower.copy()  # "final" lines that only tighten
    up = np.ones(n, dtype=bool)  # True = uptrend
    for i in range(1, n):  # walk day by day
        fu[i] = upper[i] if (upper[i] < fu[i - 1] or close[i - 1] > fu[i - 1]) else fu[i - 1]  # upper line may only move down
        fl[i] = lower[i] if (lower[i] > fl[i - 1] or close[i - 1] < fl[i - 1]) else fl[i - 1]  # lower line may only move up
        if up[i - 1] and close[i] < fl[i]:
            up[i] = False  # price broke the lower line: trend turns down
        elif (not up[i - 1]) and close[i] > fu[i]:
            up[i] = True  # price broke the upper line: trend turns up
        else:
            up[i] = up[i - 1]  # trend stays the same
    trend = pd.Series(up, index=d.index)
    ready = pd.Series(np.arange(n) > 15, index=d.index)  # skip the first days (not enough data)
    return (trend & ~trend.shift(1, fill_value=True)) & ready, (~trend & trend.shift(1, fill_value=False)) & ready


def adx_di(d):
    up_move = d["High"].diff()  # today's high minus yesterday's high
    down_move = -d["Low"].diff()  # yesterday's low minus today's low
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=d.index)  # upward push
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=d.index)  # downward push
    a = atr(d, 14)
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False).mean() / a  # strength of buyers
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False).mean() / a  # strength of sellers
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / 14, adjust=False).mean()  # how strong the trend is (any direction)
    ready = pd.Series(np.arange(len(d)) > 30, index=d.index)
    return cross_up(plus_di, minus_di) & (adx > 20) & ready, cross_down(plus_di, minus_di) & ready  # buy only when the trend is strong


def ichimoku(d):
    tenkan = (d["High"].rolling(9).max() + d["Low"].rolling(9).min()) / 2  # fast middle line
    kijun = (d["High"].rolling(26).max() + d["Low"].rolling(26).min()) / 2  # slow middle line
    span_a = ((tenkan + kijun) / 2).shift(26)  # cloud edge A (drawn 26 days ahead, so use the old value)
    span_b = ((d["High"].rolling(52).max() + d["Low"].rolling(52).min()) / 2).shift(26)  # cloud edge B
    top = pd.concat([span_a, span_b], axis=1).max(axis=1)  # top of the cloud
    ok = span_a.notna() & span_b.notna()
    return cross_up(d["Close"], top) & ok & (tenkan > kijun), cross_down(d["Close"], kijun)  # buy: close leaves the cloud upward


def bb_squeeze(d):
    mid = sma(d["Close"], 20)
    sd = d["Close"].rolling(20).std()
    width = (4 * sd) / mid  # how wide the bands are
    tight = width <= width.rolling(120).quantile(0.2)  # bands are among the narrowest 20% of the last 120 days
    recent_squeeze = tight.rolling(5).max().fillna(0).astype(bool)  # a squeeze happened in the last 5 days
    return (d["Close"] > mid + 2 * sd) & recent_squeeze, d["Close"] < mid  # buy: price breaks up out of a squeeze


def trend_pullback(d):
    r = rsi(d["Close"], 14)
    uptrend = d["Close"] > sma(d["Close"], 200)  # long-term uptrend
    dipped = (r.shift(1) < 40) & (r >= 40)  # RSI was below 40 and is back above it: dip is over
    return dipped & uptrend, (r > 70) | cross_down(d["Close"], sma(d["Close"], 50))  # sell: overbought or price loses MA50


# name -> (function, buy rule in words, sell rule in words)
STRATEGY_DEFS = {
    "MA Crossover (MA20 vs MA50)": (ma_cross(20, 50), "MA20 crosses above MA50", "MA20 crosses below MA50"),
    "MA Crossover (MA10 vs MA30)": (ma_cross(10, 30), "MA10 crosses above MA30", "MA10 crosses below MA30"),
    "MA Golden Cross (MA50 vs MA200)": (ma_cross(50, 200), "MA50 crosses above MA200", "MA50 crosses below MA200"),
    "EMA Crossover (9 vs 21)": (ema_cross(9, 21), "EMA9 crosses above EMA21", "EMA9 crosses below EMA21"),
    "EMA Crossover (12 vs 26)": (ema_cross(12, 26), "EMA12 crosses above EMA26", "EMA12 crosses below EMA26"),
    "EMA Crossover (20 vs 50)": (ema_cross(20, 50), "EMA20 crosses above EMA50", "EMA20 crosses below EMA50"),
    "RSI (30 / 70)": (rsi_level(14, 30, 70), "RSI is below 30 (oversold)", "RSI is above 70 (overbought)"),
    "RSI (25 / 75)": (rsi_level(14, 25, 75), "RSI is below 25 (very oversold)", "RSI is above 75 (very overbought)"),
    "RSI-2 Pullback (above MA200)": (rsi2_pullback, "2-day RSI below 10 while price is above MA200", "2-day RSI above 70"),
    "20-Day Breakout": (breakout(20, 10), "Close is above the previous 20-day high", "Close is below the previous 10-day low"),
    "50-Day Breakout": (breakout(50, 20), "Close is above the previous 50-day high", "Close is below the previous 20-day low"),
    "MACD Signal Cross": (macd_cross, "MACD line crosses above its signal line", "MACD line crosses below its signal line"),
    "MACD Cross above Zero": (macd_zero, "MACD crosses above signal while MACD is above zero", "MACD crosses below signal"),
    "Bollinger Mean Reversion": (boll_revert, "Close is below the lower Bollinger band", "Close is back above the middle band"),
    "Bollinger Breakout": (boll_break, "Close breaks above the upper Bollinger band", "Close falls below the middle band"),
    "Momentum (20-day, above 0%)": (momentum(20, 0), "20-day change turns positive", "20-day change turns negative"),
    "Momentum (60-day, above 5%)": (momentum(60, 5), "60-day change climbs above +5%", "60-day change turns negative"),
    "Price vs MA50 Trend": (price_vs_ma(50), "Close crosses above MA50", "Close crosses below MA50"),
    "Stochastic (20 / 80)": (stochastic, "Stochastic is below 20 (oversold)", "Stochastic is above 80 (overbought)"),
    "ADVANCED: Supertrend (ATR 10, x3)": (supertrend, "Supertrend flips from down to up (price closes above the upper line)", "Supertrend flips from up to down (price closes below the lower line)"),
    "ADVANCED: ADX + DI Trend Cross": (adx_di, "+DI crosses above -DI while ADX is above 20 (strong trend)", "+DI crosses below -DI"),
    "ADVANCED: Ichimoku Cloud Breakout": (ichimoku, "Close moves above the Ichimoku cloud while the fast line (Tenkan) is above the slow line (Kijun)", "Close crosses below the Kijun line"),
    "ADVANCED: Bollinger Squeeze Breakout": (bb_squeeze, "Close breaks above the upper band within 5 days of a squeeze (very narrow bands)", "Close falls below the middle band"),
    "ADVANCED: Trend Pullback (MA200 + RSI)": (trend_pullback, "In an uptrend (above MA200), RSI climbs back above 40 after dipping below it", "RSI above 70, or close crosses below MA50"),
}
STRATEGIES = list(STRATEGY_DEFS.keys())  # names shown in the sidebar


def get_signals(df, strategy):
    """Return the price table with two True/False columns: 'entry' (BUY today) and 'exit' (SELL today)."""
    d = add_indicators(df)  # prices + MA20 + MA50 + RSI
    entry, exit_ = STRATEGY_DEFS[strategy][0](d)  # run the chosen strategy
    d["entry"] = entry.fillna(False).astype(bool)  # missing means False
    d["exit"] = exit_.fillna(False).astype(bool)
    return d


def explain_today(df, strategy):
    """Return (signal, reason) for the LAST day: BUY, SELL or HOLD, with a plain English reason."""
    if len(df) < 60:  # not enough history
        return "HOLD", "Not enough data yet. Choose an earlier start date."
    d = get_signals(df, strategy)
    last = d.iloc[-1]  # the newest day
    _, buy_rule, sell_rule = STRATEGY_DEFS[strategy]
    if last["entry"]:
        return "BUY", f"Buy rule met today: {buy_rule}."
    if last["exit"]:
        return "SELL", f"Sell rule met today: {sell_rule}."
    return "HOLD", f"No rule met today. Buy when: {buy_rule}. Sell when: {sell_rule}."
