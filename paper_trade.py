# paper_trade.py - VIRTUAL trading. No broker, no real money. Everything is saved in a local SQLite file.
import sqlite3  # small database stored in one file
from datetime import datetime
from pathlib import Path
from strategy import stop_and_target  # stop-loss and target rules

DB_FILE = Path(__file__).parent / "paper_trades.db"  # the database file next to this code
START_CASH = 100000.0  # virtual wallet: Rs 1,00,000


def _conn():
    """Open the database and make the table if it is missing."""
    c = sqlite3.connect(DB_FILE)
    c.row_factory = sqlite3.Row  # lets us read columns by name
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, stock TEXT, strategy TEXT, qty INTEGER,
        entry_time TEXT, entry_price REAL, stop_loss REAL, target REAL, reason TEXT,
        status TEXT, exit_time TEXT, exit_price REAL, exit_reason TEXT, pnl REAL)""")
    return c


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # current date and time as text


def buy(stock, strategy, price, qty, reason):
    """Open a virtual BUY. Stop-loss and target are always added. Returns (ok, message)."""
    if qty <= 0:
        return False, "Quantity must be at least 1."
    if price * qty > cash_balance():  # cannot spend more than the wallet
        return False, "Not enough virtual cash for this order."
    stop, target = stop_and_target(price)  # no trade without stop-loss
    with _conn() as c:
        c.execute("INSERT INTO trades (stock,strategy,qty,entry_time,entry_price,stop_loss,target,reason,status) "
                  "VALUES (?,?,?,?,?,?,?,?, 'OPEN')",
                  (stock, strategy, qty, _now(), price, stop, target, reason))
    return True, f"Virtual BUY saved: {qty} x {stock} at Rs {price:.2f}. Stop-loss {stop:.2f}, target {target:.2f}."


def sell(trade_id, price, why="Manual sell"):
    """Close an open virtual trade at the given price."""
    with _conn() as c:
        row = c.execute("SELECT * FROM trades WHERE id=? AND status='OPEN'", (trade_id,)).fetchone()
        if row is None:
            return False, "That trade is not open."
        pnl = (price - row["entry_price"]) * row["qty"]  # profit or loss in Rs
        c.execute("UPDATE trades SET status='CLOSED', exit_time=?, exit_price=?, exit_reason=?, pnl=? WHERE id=?",
                  (_now(), price, why, pnl, trade_id))
    return True, f"Virtual SELL saved at Rs {price:.2f}. Profit/Loss: Rs {pnl:.2f}."


def check_stops(stock, price):
    """Close open trades of this stock if the price is at/below stop-loss or at/above target."""
    msgs = []
    for t in open_positions():
        if t["stock"] != stock:
            continue
        if price <= t["stop_loss"]:
            msgs.append(sell(t["id"], price, "Stop-loss hit")[1])
        elif price >= t["target"]:
            msgs.append(sell(t["id"], price, "Target hit")[1])
    return msgs


def open_positions():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM trades WHERE status='OPEN' ORDER BY id DESC")]


def closed_trades():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM trades WHERE status='CLOSED' ORDER BY id DESC")]


def all_trades():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM trades ORDER BY id DESC")]


def total_pnl():
    """Total profit or loss of closed trades."""
    with _conn() as c:
        return c.execute("SELECT COALESCE(SUM(pnl),0) FROM trades WHERE status='CLOSED'").fetchone()[0]


def cash_balance():
    """Wallet cash = start cash - money in open trades + closed profit/loss."""
    with _conn() as c:
        invested = c.execute("SELECT COALESCE(SUM(entry_price*qty),0) FROM trades WHERE status='OPEN'").fetchone()[0]
    return START_CASH - invested + total_pnl()


def reset_all():
    """Delete every paper trade and start again with Rs 1,00,000."""
    with _conn() as c:
        c.execute("DELETE FROM trades")
