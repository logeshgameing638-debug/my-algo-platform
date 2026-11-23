# app.py - the main dashboard. Run it with:  streamlit run app.py
from datetime import date, timedelta  # dates
import pandas as pd
import streamlit as st  # makes the web page
import data, strategy, backtest, paper_trade  # our own files

st.set_page_config(page_title="Logesh Algo Platform", layout="wide")  # page settings
st.title("Logesh - Personal Algo Platform | PAPER TRADING ONLY")  # big title
st.warning("PAPER TRADING ONLY. No real money, no broker. Prices come from free, delayed, unofficial Yahoo "
           "Finance data. Backtests do NOT guarantee future results. This is not advice.")

# ---------- Sidebar: choices ----------
st.sidebar.header("Settings")
stock_name = st.sidebar.selectbox("Stock", list(data.STOCKS.keys()))  # which stock
symbol = data.STOCKS[stock_name]  # Yahoo code
start = st.sidebar.date_input("Start date", date.today() - timedelta(days=3 * 365))  # first day
end = st.sidebar.date_input("End date", date.today())  # last day
capital = st.sidebar.number_input("Capital (Rs)", min_value=1000, value=100000, step=1000)  # backtest money
strat = st.sidebar.selectbox("Strategy", strategy.STRATEGIES)  # which rules
risk = st.sidebar.number_input("Max risk per trade (% of capital)", 0.1, 5.0, backtest.RISK_PCT, 0.1)  # 0.5% rule
st.sidebar.caption(f"Every trade: Stop-loss {strategy.STOP_LOSS_PCT}% and Target {strategy.TARGET_PCT}%.")


@st.cache_data(ttl=600, show_spinner="Downloading prices...")  # remember data for 10 minutes
def load(sym, s, e):
    return data.download_prices(sym, s, e)


def get_data():
    """Load prices, or show a friendly error and return None."""
    if start >= end:
        st.error("Start date must be before End date.")
        return None
    try:
        return load(symbol, start, end)
    except data.DataError as e:
        st.error(str(e))
        return None


tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard", "Backtest", "Paper Trade", "Trade Diary", "Arena"])

# ---------- Tab 1: Dashboard ----------
with tab1:
    df = get_data()
    if df is not None:
        sig, why = strategy.explain_today(df, strat)  # today's signal
        last, prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"{stock_name} last price", f"Rs {last:,.2f}", f"{(last / prev - 1) * 100:.2f}%")
        c2.metric("Today's signal", sig)
        c3.metric("Virtual wallet cash", f"Rs {paper_trade.cash_balance():,.0f}")
        c4.metric("Paper P&L (closed)", f"Rs {paper_trade.total_pnl():,.0f}")
        st.info(f"Why {sig}? {why}  (data up to {df.index[-1].date()})")
        d = strategy.add_indicators(df)
        st.pyplot(backtest.price_chart(d, stock_name))  # price chart
        st.caption("Free Yahoo Finance data. Delayed and unofficial.")

# ---------- Tab 2: Backtest ----------
with tab2:
    st.write("Test the strategy on OLD data. Past results do not promise future results.")
    cost = st.number_input("Cost per buy and per sell (%)", 0.0, 1.0, backtest.COST_PCT, 0.01)
    if st.button("Run Backtest", type="primary"):
        df = get_data()
        if df is not None:
            if len(df) < 60:
                st.error("Not enough days of data. Pick a longer date range.")
            else:
                trades, equity, d = backtest.run_backtest(df, strat, capital, cost, risk)
                st.session_state["bt"] = (trades, equity, d, backtest.summarize(trades, equity, capital),
                                          f"{stock_name} - {strat}")
    if "bt" in st.session_state:
        trades, equity, d, summ, label = st.session_state["bt"]
        st.subheader(label)
        cols = st.columns(6)
        for col, (k, v) in zip(cols, summ.items()):
            col.metric(k, v)
        st.pyplot(backtest.make_chart(d, trades, equity, label))
        st.subheader("All trades")
        if len(trades):
            st.dataframe(trades, width="stretch", hide_index=True)
        else:
            st.info("This strategy made no trades in this date range.")

# ---------- Tab 3: Paper Trade ----------
with tab3:
    st.write("Virtual trades only. The buttons below just write a line in a local file. No broker is used.")
    try:
        price, when = data.latest_price(symbol)
    except data.DataError as e:
        price = None
        st.error(str(e))
    df = get_data()
    if price is not None:
        st.metric(f"{stock_name} latest price (delayed, free, unofficial)", f"Rs {price:,.2f}", f"as of {when}")
        if df is not None:
            sig, why = strategy.explain_today(df, strat)
            st.info(f"Today's signal ({strat}): {sig}. {why}")
        else:
            sig, why = "HOLD", "No data"
        stop, target = strategy.stop_and_target(price)
        st.write(f"Virtual cash: Rs {paper_trade.cash_balance():,.2f} | Stop-loss would be Rs {stop:,.2f} | "
                 f"Target would be Rs {target:,.2f}")
        max_qty = int(paper_trade.cash_balance() * (risk / strategy.STOP_LOSS_PCT) // price)  # size so a stop-loss costs only the risk %
        st.caption(f"Risk rule: max {risk}% of wallet lost per trade. With a {strategy.STOP_LOSS_PCT}% stop-loss, "
                   f"that is about {max_qty} unit(s) at this price. (A guide, not forced.)")
        qty = st.number_input("Quantity", min_value=1, value=max(1, min(max_qty, 1)), step=1)
        note = st.text_input("Your reason (saved in the diary)", value=f"{sig}: {why}")
        b1, b2 = st.columns(2)
        if b1.button("Virtual BUY"):
            ok, msg = paper_trade.buy(stock_name, strat, price, int(qty), note)
            (st.success if ok else st.error)(msg)
        if b2.button("Check stop-loss / target for this stock"):
            msgs = paper_trade.check_stops(stock_name, price)
            st.info("\n".join(msgs) if msgs else "No open trade hit its stop-loss or target.")
    st.subheader("Open positions")
    opens = paper_trade.open_positions()
    if not opens:
        st.write("No open positions.")
    for t in opens:
        c1, c2 = st.columns([4, 1])
        c1.write(f"#{t['id']} {t['stock']} x{t['qty']} bought at Rs {t['entry_price']:.2f} "
                 f"(stop {t['stop_loss']:.2f}, target {t['target']:.2f})")
        if c2.button("Virtual SELL", key=f"sell{t['id']}"):
            try:  # sell at the latest price of THAT stock
                p, _ = data.latest_price(data.STOCKS[t["stock"]])
                ok, msg = paper_trade.sell(t["id"], p, "Manual sell")
                (st.success if ok else st.error)(msg)
                st.rerun()
            except data.DataError as e:
                st.error(str(e))
    st.subheader("Closed trades")
    closed = paper_trade.closed_trades()
    if closed:
        st.dataframe(pd.DataFrame(closed)[["id", "stock", "qty", "entry_price", "exit_price", "exit_reason", "pnl"]],
                     hide_index=True, width="stretch")
    else:
        st.write("No closed trades yet.")
    st.metric("Total paper profit/loss", f"Rs {paper_trade.total_pnl():,.2f}")

# ---------- Tab 4: Trade Diary ----------
with tab4:
    st.write("Every paper trade is saved here automatically.")
    rows = paper_trade.all_trades()
    if not rows:
        st.info("Your diary is empty. Make a virtual trade in the Paper Trade tab.")
    else:
        t = pd.DataFrame(rows)
        diary = t[["entry_time", "stock", "strategy", "qty", "entry_price", "status", "reason",
                   "exit_time", "exit_price", "exit_reason", "pnl"]]
        diary.columns = ["Date", "Stock", "Strategy", "Qty", "Buy Price", "Status", "Reason",
                         "Exit Date", "Exit Price", "Exit Reason", "Profit/Loss (Rs)"]
        st.dataframe(diary, hide_index=True, width="stretch")
        done = t[t["status"] == "CLOSED"]
        a, b, c, e = st.columns(4)
        a.metric("Trades made", len(t))
        b.metric("Closed trades", len(done))
        c.metric("Winning trades", int((done["pnl"] > 0).sum()))
        e.metric("Total P&L (Rs)", f"{done['pnl'].sum():,.2f}")
        st.download_button("Download diary as CSV", diary.to_csv(index=False), "trade_diary.csv")
    with st.expander("Danger zone"):
        if st.button("Delete all paper trades and reset wallet"):
            paper_trade.reset_all()
            st.rerun()


# ---------- Tab 5: Arena (all strategies ranked) ----------
with tab5:
    st.write(f"Run ALL {len(strategy.STRATEGIES)} strategies on the selected stock and dates, then rank them by return.")
    st.warning("A high rank on OLD data does NOT mean future profit. Strategies with few trades (under 20) can look "
               "good by luck. More trades or a positive backtest is not proof of an edge. Compare with Buy & Hold below.")
    arena_cost = st.number_input("Cost per buy and per sell (%) for the arena", 0.0, 1.0, backtest.COST_PCT, 0.01,
                                 key="arena_cost")
    if st.button("Run Arena", type="primary"):
        df = get_data()
        if df is not None:
            if len(df) < 60:
                st.error("Not enough days of data. Pick a longer date range.")
            else:
                with st.spinner("Testing all strategies..."):
                    arena, bh = backtest.run_arena(df, capital, arena_cost, risk)
                arena["Note"] = arena["Total Trades"].apply(lambda n: "Too few trades to trust" if n < 20 else "")
                st.session_state["arena"] = (arena, bh, f"{stock_name}, {start} to {end}")
    if "arena" in st.session_state:
        arena, bh, label = st.session_state["arena"]
        st.subheader(f"Arena results: {label}")
        winners = int((arena["Total Return %"] > 0).sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Buy & Hold return % (just hold, no trading)", bh)
        c2.metric("Strategies with positive return", f"{winners} of {len(arena)}")
        c3.metric("Strategies that beat Buy & Hold", int((arena["Total Return %"] > bh).sum()))
        st.dataframe(arena, hide_index=True, width="stretch", height=38 * (len(arena) + 1))
        st.caption("Every trade used a 1% stop-loss and 2% target. Costs included. Paper results only.")
        st.download_button("Download arena table as CSV", arena.to_csv(index=False), "arena.csv")
