# backtest.py - tests a strategy on OLD data to see what would have happened.
# A backtest is NOT a promise. Past results do not guarantee future results.
import math  # for rounding down shares
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # draw charts without opening a window
import matplotlib.pyplot as plt
from strategy import get_signals, stop_and_target, STOP_LOSS_PCT  # our rules

COST_PCT = 0.05  # small cost on each buy and each sell (brokerage, taxes), in percent
RISK_PCT = 0.5  # max loss per trade as % of your money (0.5% rule). With a 1% stop-loss this means half the money per trade


def run_backtest(df, strategy, capital, cost_pct=COST_PCT, risk_pct=RISK_PCT):
    """Walk through old days one by one and make virtual trades. Returns (trades table, equity series, signals table)."""
    d = get_signals(df, strategy)  # prices + indicators + entry/exit columns
    cash = float(capital)  # money we have
    pos = None  # the open trade (None = no trade)
    trades = []  # list of finished trades
    equity = []  # account value for each day
    for date, row in d.iterrows():  # go day by day
        if pos is not None:  # we are in a trade: check exits
            exit_price, why = None, None
            if row["Low"] <= pos["stop"]:  # price touched stop-loss (checked first = safer assumption)
                exit_price, why = pos["stop"], "Stop-loss hit"
            elif row["High"] >= pos["target"]:  # price touched target
                exit_price, why = pos["target"], "Target hit"
            elif row["exit"]:  # strategy says SELL
                exit_price, why = row["Close"], "Strategy sell signal"
            if exit_price is not None:  # close the trade
                proceeds = pos["qty"] * exit_price * (1 - cost_pct / 100)  # money back after cost
                profit = proceeds - pos["cost"]  # profit = money back - money spent
                cash += proceeds
                trades.append({"Date": date.date(), "Action": "SELL", "Price": round(exit_price, 2),
                               "Profit": round(profit, 2), "Reason": why, "Entry Date": pos["date"].date(),
                               "Entry Price": round(pos["price"], 2)})
                pos = None
        if pos is None and row["entry"]:  # no trade and BUY signal: open one
            price = float(row["Close"])  # buy at today's close
            max_money = min(cash, cash * risk_pct / STOP_LOSS_PCT)  # money allowed in this trade so a stop-loss costs only risk_pct of cash
            qty = math.floor(max_money / (price * (1 + cost_pct / 100)))  # whole shares we can afford
            if qty > 0:
                cost = qty * price * (1 + cost_pct / 100)  # total money spent
                stop, target = stop_and_target(price)  # stop-loss and target are ALWAYS set
                cash -= cost
                pos = {"date": date, "price": price, "qty": qty, "cost": cost, "stop": stop, "target": target}
                trades.append({"Date": date.date(), "Action": "BUY", "Price": round(price, 2), "Profit": None,
                               "Reason": f"Signal. Stop {stop:.2f} / Target {target:.2f}",
                               "Entry Date": None, "Entry Price": None})
        value = cash + (pos["qty"] * row["Close"] if pos else 0)  # cash + value of shares held
        equity.append(value)
    return pd.DataFrame(trades), pd.Series(equity, index=d.index, name="Equity"), d


def summarize(trades, equity, capital):
    """Calculate the summary numbers."""
    sells = trades[trades["Action"] == "SELL"] if len(trades) else trades  # finished trades only
    n = len(sells)
    total_return = (equity.iloc[-1] / capital - 1) * 100  # % change of account
    wins = (sells["Profit"] > 0).sum() if n else 0  # trades that made money
    drawdown = (equity / equity.cummax() - 1) * 100  # how far below the previous peak
    return {
        "Total Return %": round(float(total_return), 2),
        "Win Rate %": round(wins / n * 100, 1) if n else 0.0,
        "Total Trades": int(n),
        "Max Drawdown %": round(float(drawdown.min()), 2),
        "Best Trade": round(float(sells["Profit"].max()), 2) if n else 0.0,
        "Worst Trade": round(float(sells["Profit"].min()), 2) if n else 0.0,
    }


def make_chart(d, trades, equity, name):
    """Draw price + MA20 + MA50 with buy/sell marks, and the equity curve below."""
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(d.index, d["Close"], label="Price", color="black", linewidth=1)  # price line
    a1.plot(d.index, d["MA20"], label="MA20", color="tab:blue", linewidth=1)  # fast average
    a1.plot(d.index, d["MA50"], label="MA50", color="tab:orange", linewidth=1)  # slow average
    if len(trades):  # mark trades on the chart
        for action, color, mark in (("BUY", "green", "^"), ("SELL", "red", "v")):
            t = trades[trades["Action"] == action]
            a1.scatter(pd.to_datetime(t["Date"]), t["Price"], color=color, marker=mark, s=60, label=action, zorder=5)
    a1.set_title(f"{name} - Price, MA20, MA50"); a1.legend(loc="upper left"); a1.grid(alpha=0.3)
    a2.plot(equity.index, equity.values, color="tab:green")  # account value over time
    a2.set_title("Equity Curve (account value, Rs)"); a2.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def price_chart(d, name):
    """Simple chart of price + MA20 + MA50 for the Dashboard tab."""
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(d.index, d["Close"], label="Price", color="black", linewidth=1)
    ax.plot(d.index, d["MA20"], label="MA20", color="tab:blue", linewidth=1)
    ax.plot(d.index, d["MA50"], label="MA50", color="tab:orange", linewidth=1)
    ax.set_title(f"{name} - Price, MA20, MA50"); ax.legend(loc="upper left"); ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def run_arena(df, capital, cost_pct=COST_PCT, risk_pct=RISK_PCT):
    """Run EVERY strategy on the same data and rank them. Also adds a simple Buy & Hold line to compare."""
    from strategy import STRATEGIES  # list of all strategy names
    rows = []
    for name in STRATEGIES:  # one by one
        trades, equity, _ = run_backtest(df, name, capital, cost_pct, risk_pct)
        s = summarize(trades, equity, capital)
        rows.append({"Strategy": name, **s})
    arena = pd.DataFrame(rows).sort_values("Total Return %", ascending=False).reset_index(drop=True)
    arena.insert(0, "Rank", arena.index + 1)  # 1 = best return
    bh = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100  # buy on first day, hold to the end
    return arena, round(float(bh), 2)
