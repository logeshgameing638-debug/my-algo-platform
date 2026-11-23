# Logesh - Personal Algo Platform (PAPER TRADING ONLY)

This app is free. It uses no broker and no real money.
It only makes VIRTUAL trades with a pretend wallet of Rs 1,00,000.

## Important
- Backtests use old data. They do NOT promise future profit.
- Prices come from Yahoo Finance through yfinance. They are free, delayed and unofficial.
- Do not trade real money because of this app. It is for learning.

## Setup on Windows (one time)
1. Go to https://www.python.org/downloads/ and install Python.
   On the first screen, TICK the box "Add python.exe to PATH". Then click Install.
2. Unzip this folder (my-algo-platform).
3. Open the folder. Click the address bar at the top, type `cmd` and press Enter.
4. Type this and press Enter (wait until it finishes):
   `pip install -r requirements.txt`

## Run the app
In the same black window type:
`streamlit run app.py`
Your browser opens the dashboard. If it does not, open http://localhost:8501

To stop the app, press Ctrl + C in the black window.

## How to use
1. Left side: choose the instrument type (Index, Stock or Commodity Future), the instrument, dates, capital and strategy.
2. Dashboard tab: see the price chart and today's signal (BUY / SELL / HOLD).
3. Backtest tab: press "Run Backtest" to see how the rules did on old data.
4. Paper Trade tab: press "Virtual BUY" or "Virtual SELL". This only saves a line in a file.
5. Trade Diary tab: see every trade, the reason, and your profit or loss.
6. Arena tab: rank all strategies on one instrument.

## What you can test
- 18 Indian indices: Nifty 50, Nifty Next 50, Nifty 100, Nifty 200, Nifty Midcap 50, Bank Nifty, Sensex,
  Nifty IT, Auto, Pharma, FMCG, Metal, Energy, Realty, PSU Bank, PSE, Infra, and India VIX.
- 4 stocks: Reliance, TCS, Infosys, HDFC Bank.
- 5 commodity futures (priced in US dollars): Gold, Silver, Crude Oil, Natural Gas, Copper.
Indices cannot be bought in real life, and Yahoo does not carry Indian index futures or MCX commodities.
Everything here is practice-only: the app just counts the numbers in your virtual wallet.

## The files
- app.py - the dashboard page
- strategy.py - the 24 strategies and the stop-loss / target rules
- backtest.py - tests the strategy on old data
- paper_trade.py - virtual trades saved in SQLite (file: paper_trades.db)
- Logesh-Strategy-Guide-2nd-Edition-Advanced.pdf - the full guide: rules, examples, when to skip
- data.py - downloads free prices with yfinance
- requirements.txt - the list of free packages

## The 24 strategies
Buy and sell rules are written in strategy.py in plain English. Groups:
- Moving average crossovers: MA20/50, MA10/30, MA50/200
- EMA crossovers: 9/21, 12/26, 20/50
- RSI: 30/70, 25/75, RSI-2 pullback
- Breakouts: 20-day, 50-day
- MACD: signal cross, cross above zero
- Bollinger: mean reversion, breakout
- Momentum: 20-day, 60-day
- Price vs MA50, Stochastic 20/80
- ADVANCED (5): Supertrend, ADX + DI trend cross, Ichimoku cloud breakout, Bollinger squeeze breakout, Trend pullback (MA200 + RSI)

Every trade has a 1% stop-loss and a 2% target. There is no trade without a stop-loss.

## The Arena tab
Press "Run Arena" to test ALL strategies on the same stock and dates. It ranks them and also shows Buy & Hold
(just buy once and wait) to compare. Be careful: a top rank on old data is often luck, especially with few trades.
Most simple strategies do NOT beat Buy & Hold. That is normal and honest. Never trade real money because of a rank.

## Rules this app follows (and how they differ from "textbook")
- Backtest buys at the day's closing price. A small cost (0.05% each side) is included. You can change it.
- If both stop-loss and target could be hit in one day, the app assumes the stop-loss was hit first (safer).
- Only buying (long) trades. No short selling.
- Position size: each backtest trade uses a size so that hitting the 1% stop-loss loses only 0.5% of your money (the "max risk per trade" box in the sidebar). With a 1% stop-loss that means about half your money in each trade.
- Indices (Nifty, Sensex, Bank Nifty, etc.) cannot be bought directly. Here they are only practice numbers.
- Commodity futures are priced in US dollars. The virtual wallet treats every number the same, so do not
  compare a gold paper P&L with a Nifty paper P&L.

## If something goes wrong
- "Yahoo returned no data": Yahoo is busy or your 4G is weak. Wait a minute and try again.
- "streamlit is not recognized": run `python -m streamlit run app.py` instead.
- To start the paper wallet fresh: Trade Diary tab > Danger zone > Reset.
