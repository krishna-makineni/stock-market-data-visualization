📈 Real-Time Stock Market Dashboard
This interactive web application allows users to monitor and analyze real-time and historical stock market data with rich visualizations and technical indicators. Built using Streamlit, Plotly, and Yahoo Finance API (via yfinance), the dashboard offers a user-friendly interface and multiple analysis tools.

🔧 Key Features:
Live Stock Data Tracking
Add stock tickers (e.g., AAPL, MSFT) to track their latest prices, volume, highs/lows, and intraday trends.

Technical Indicators
Visualizations include:

Candlestick charts

Moving Averages (SMA 5 & SMA 20)

Relative Strength Index (RSI)

Volume bars

Real-Time Alerts
Set upper and lower price thresholds for each tracked stock. If the current price crosses your set boundaries, alerts are triggered and displayed prominently.

Historical vs Recent Performance Comparison
Analyze how a stock performed over the last few days versus longer historical periods using side-by-side charts.

Multiple Stock Comparison
Compare percentage changes of multiple stocks over a selected time frame using line plots.

Data Export
Download historical stock data in CSV format for offline analysis or archival.

🧠 Technologies Used:
Python

Streamlit – for frontend and web app deployment

Plotly – for interactive, responsive visualizations

yfinance – to fetch stock data from Yahoo Finance

Pandas & NumPy – for data manipulation

Base64 & BytesIO – for file export functionality

⚙ Customization & Settings:
Choose custom time frames (1d, 5d, 1mo, etc.) and data intervals (1m, 5m, 1h, etc.)

Set price alert thresholds individually for each stock

Monitor real-time changes with automated refreshes (cache interval set to 60 seconds)

