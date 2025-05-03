import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import base64
from io import BytesIO
import schedule
import threading
import os

# Page config
st.set_page_config(
    page_title="Real-Time Stock Market Dashboard",
    page_icon="📈",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'alert_messages' not in st.session_state:
    st.session_state.alert_messages = []
if 'tracked_stocks' not in st.session_state:
    st.session_state.tracked_stocks = []
if 'thresholds' not in st.session_state:
    st.session_state.thresholds = {}
if 'last_prices' not in st.session_state:
    st.session_state.last_prices = {}

# Function to fetch real-time stock data
@st.cache_data(ttl=60)  # Cache data for 60 seconds
def fetch_stock_data(ticker, period="1d", interval="1m"):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period, interval=interval)
        if data.empty:
            st.error(f"No data found for {ticker}. Please check the symbol.")
            return None
        # Add additional metrics
        if len(data) > 1:
            data['SMA_5'] = data['Close'].rolling(window=5).mean()
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['RSI'] = calculate_rsi(data['Close'])
        data.reset_index(inplace=True)
        return data
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return None

# Function to fetch historical stock data
def fetch_historical_data(ticker, period="1y", interval="1d"):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period, interval=interval)
        if data.empty:
            st.error(f"No historical data found for {ticker}.")
            return None
        data.reset_index(inplace=True)
        return data
    except Exception as e:
        st.error(f"Error fetching historical data for {ticker}: {e}")
        return None

# Function to calculate RSI (Relative Strength Index)
def calculate_rsi(price_series, period=14):
    delta = price_series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Function to create a line chart for stock data
def create_line_chart(data, ticker, metric='Close'):
    # Check if the column is 'Date' or 'Datetime'
    date_col = 'Date' if 'Date' in data.columns else 'Datetime'
    
    fig = px.line(data, x=date_col, y=metric, title=f'{ticker} - {metric} Price')
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title=f'{metric} Price (USD)',
        hovermode='x unified',
        legend_title='Legend',
        height=500
    )
    return fig

# Function to create a candlestick chart
def create_candlestick_chart(data, ticker):
    # Check if the column is 'Date' or 'Datetime'
    date_col = 'Date' if 'Date' in data.columns else 'Datetime'
    
    fig = go.Figure(data=[go.Candlestick(
        x=data[date_col],
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price'
    )])
    
    # Add moving averages if available
    if 'SMA_5' in data.columns and not data['SMA_5'].isnull().all():
        fig.add_trace(go.Scatter(x=data[date_col], y=data['SMA_5'], 
                                 mode='lines', name='SMA 5'))
    if 'SMA_20' in data.columns and not data['SMA_20'].isnull().all():
        fig.add_trace(go.Scatter(x=data[date_col], y=data['SMA_20'], 
                                 mode='lines', name='SMA 20'))
    
    fig.update_layout(
        title=f'{ticker} Candlestick Chart',
        xaxis_title='Time',
        yaxis_title='Price (USD)',
        height=600,
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    return fig

# Function to create a volume chart
def create_volume_chart(data, ticker):
    # Check if the column is 'Date' or 'Datetime'
    date_col = 'Date' if 'Date' in data.columns else 'Datetime'
    
    fig = px.bar(data, x=date_col, y='Volume', title=f'{ticker} Trading Volume')
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Volume',
        height=300
    )
    return fig

# Function to create RSI chart
def create_rsi_chart(data, ticker):
    if 'RSI' not in data.columns or data['RSI'].isnull().all():
        return None
    
    # Check if the column is 'Date' or 'Datetime'
    date_col = 'Date' if 'Date' in data.columns else 'Datetime'
    
    fig = px.line(data, x=date_col, y='RSI', title=f'{ticker} RSI')
    
    # Add horizontal lines at 30 and 70 (overbought/oversold levels)
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='RSI',
        height=300,
        yaxis=dict(range=[0, 100])
    )
    return fig

# Function to create comparison chart for multiple stocks
def create_comparison_chart(tickers, period="1d", interval="1m"):
    compare_data = pd.DataFrame()
    
    for ticker in tickers:
        data = fetch_stock_data(ticker, period, interval)
        if data is not None:
            # Determine the date column name
            date_col = 'Date' if 'Date' in data.columns else 'Datetime'
            
            # Normalize to percentage change from first price
            first_price = data['Close'].iloc[0]
            data[f'{ticker}_Change'] = (data['Close'] / first_price - 1) * 100
            if compare_data.empty:
                compare_data = data[[date_col, f'{ticker}_Change']]
            else:
                compare_data = compare_data.merge(data[[date_col, f'{ticker}_Change']], on=date_col, how='outer')
    
    if compare_data.empty:
        return None
    
    # Determine the date column name for the final dataframe
    date_col = 'Date' if 'Date' in compare_data.columns else 'Datetime'
    
    fig = go.Figure()
    for ticker in tickers:
        fig.add_trace(go.Scatter(
            x=compare_data[date_col],
            y=compare_data[f'{ticker}_Change'],
            mode='lines',
            name=ticker
        ))
    
    fig.update_layout(
        title='Percentage Change Comparison',
        xaxis_title='Time',
        yaxis_title='% Change',
        height=500,
        hovermode='x unified'
    )
    return fig

# Function to create a comparison of historical vs. recent performance
def create_historical_comparison(ticker, recent_period="5d", historical_period="1y"):
    recent_data = fetch_stock_data(ticker, period=recent_period, interval="1h")
    historical_data = fetch_historical_data(ticker, period=historical_period, interval="1d")
    
    if recent_data is None or historical_data is None:
        return None
    
    # Create separate figures
    recent_fig = create_line_chart(recent_data, ticker, 'Close')
    recent_fig.update_layout(title=f'{ticker} - Recent Performance ({recent_period})')
    
    hist_fig = create_line_chart(historical_data, ticker, 'Close')
    hist_fig.update_layout(title=f'{ticker} - Historical Performance ({historical_period})')
    
    return recent_fig, hist_fig

# Function to download dataframe as CSV
def download_csv(df, ticker):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{ticker}_stock_data.csv">Download CSV File</a>'
    return href

# Function to check alerts
def check_alerts():
    for ticker in st.session_state.tracked_stocks:
        if ticker in st.session_state.thresholds and ticker in st.session_state.last_prices:
            current_price = st.session_state.last_prices[ticker]
            upper_threshold = st.session_state.thresholds[ticker].get('upper')
            lower_threshold = st.session_state.thresholds[ticker].get('lower')
            
            if upper_threshold and current_price > upper_threshold:
                alert_msg = f"⚠ ALERT: {ticker} has crossed above your upper threshold of ${upper_threshold:.2f}. Current price: ${current_price:.2f}"
                if alert_msg not in st.session_state.alert_messages:
                    st.session_state.alert_messages.insert(0, alert_msg)
            
            if lower_threshold and current_price < lower_threshold:
                alert_msg = f"⚠ ALERT: {ticker} has crossed below your lower threshold of ${lower_threshold:.2f}. Current price: ${current_price:.2f}"
                if alert_msg not in st.session_state.alert_messages:
                    st.session_state.alert_messages.insert(0, alert_msg)

# Main app
def main():
    st.title("📈 Real-Time Stock Market Dashboard")
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("Stock Selection")
        
        # User input for stock symbols
        new_ticker = st.text_input("Enter Stock Symbol (e.g., AAPL, MSFT)", "").upper()
        add_btn = st.button("Add Stock")
        
        if add_btn and new_ticker:
            # Validate the ticker before adding
            test_data = fetch_stock_data(new_ticker, period="1d", interval="5m")
            if test_data is not None and not test_data.empty:
                if new_ticker not in st.session_state.tracked_stocks:
                    st.session_state.tracked_stocks.append(new_ticker)
                    st.success(f"Added {new_ticker} to tracked stocks")
        
        # Display and manage tracked stocks
        st.subheader("Tracked Stocks")
        for i, ticker in enumerate(st.session_state.tracked_stocks):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"{i+1}. {ticker}")
            with col2:
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state.tracked_stocks.pop(i)
                    if ticker in st.session_state.thresholds:
                        del st.session_state.thresholds[ticker]
                    if ticker in st.session_state.last_prices:
                        del st.session_state.last_prices[ticker]
                    st.rerun()
        
        # Time frame selection
        st.header("Settings")
        time_frame = st.selectbox(
            "Select Time Frame",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=0
        )
        
        interval = st.selectbox(
            "Select Interval",
            options=["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
            index=4  # Default to 30m
        )
        
        # Note on data availability
        st.info("Note: 1-minute data is only available for the last 7 days. For longer periods, use larger intervals.")
        
        # Add alert thresholds
        if st.session_state.tracked_stocks:
            st.header("Price Alerts")
            alert_ticker = st.selectbox("Select Stock for Alert", options=st.session_state.tracked_stocks)
            
            # Get current price for reference
            current_data = fetch_stock_data(alert_ticker, period="1d", interval="1m")
            if current_data is not None and not current_data.empty:
                current_price = current_data['Close'].iloc[-1]
                st.write(f"Current price: ${current_price:.2f}")
                st.session_state.last_prices[alert_ticker] = current_price
                
                col1, col2 = st.columns(2)
                with col1:
                    upper_threshold = st.number_input(
                        "Upper Threshold ($)",
                        min_value=0.0,
                        value=float(current_price * 1.05),  # Default 5% above current
                        step=0.01
                    )
                with col2:
                    lower_threshold = st.number_input(
                        "Lower Threshold ($)",
                        min_value=0.0,
                        value=float(current_price * 0.95),  # Default 5% below current
                        step=0.01
                    )
                
                if st.button("Set Alert"):
                    if alert_ticker not in st.session_state.thresholds:
                        st.session_state.thresholds[alert_ticker] = {}
                    
                    st.session_state.thresholds[alert_ticker]['upper'] = upper_threshold
                    st.session_state.thresholds[alert_ticker]['lower'] = lower_threshold
                    st.success(f"Alert set for {alert_ticker}: Upper ${upper_threshold:.2f}, Lower ${lower_threshold:.2f}")
    
    # Main content area
    if not st.session_state.tracked_stocks:
        st.info("Please add stock symbols in the sidebar to start tracking.")
    else:
        # Display alerts
        if st.session_state.alert_messages:
            with st.expander("⚠ Alerts", expanded=True):
                for msg in st.session_state.alert_messages[:10]:  # Show only the 10 most recent alerts
                    st.warning(msg)
                if st.button("Clear Alerts"):
                    st.session_state.alert_messages = []
                    st.rerun()
        
        # Tabs for different visualizations
        tab1, tab2, tab3, tab4 = st.tabs(["Individual Stocks", "Stock Comparison", "Historical Analysis", "Data Export"])
        
        # Tab 1: Individual Stock Analysis
        with tab1:
            for ticker in st.session_state.tracked_stocks:
                st.header(f"{ticker} Analysis")
                data = fetch_stock_data(ticker, period=time_frame, interval=interval)
                
                if data is not None and not data.empty:
                    # Update last known price for alerts
                    st.session_state.last_prices[ticker] = data['Close'].iloc[-1]
                    
                    # Display current stats
                    latest = data.iloc[-1]
                    prev_close = data.iloc[-2]['Close'] if len(data) > 1 else data.iloc[0]['Open']
                    change = latest['Close'] - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Current Price", f"${latest['Close']:.2f}", f"{change:.2f} ({change_pct:.2f}%)")
                    col2.metric("Day High", f"${latest['High']:.2f}")
                    col3.metric("Day Low", f"${latest['Low']:.2f}")
                    col4.metric("Volume", f"{int(latest['Volume']):,}")
                    
                    # Display candlestick chart
                    st.plotly_chart(create_candlestick_chart(data, ticker), use_container_width=True)
                    
                    # Display additional charts in columns
                    col1, col2 = st.columns(2)
                    with col1:
                        st.plotly_chart(create_volume_chart(data, ticker), use_container_width=True)
                    with col2:
                        rsi_chart = create_rsi_chart(data, ticker)
                        if rsi_chart:
                            st.plotly_chart(rsi_chart, use_container_width=True)
                else:
                    st.error(f"Failed to load data for {ticker}")
        
        # Tab 2: Stock Comparison
        with tab2:
            if len(st.session_state.tracked_stocks) > 1:
                comp_fig = create_comparison_chart(st.session_state.tracked_stocks, period=time_frame, interval=interval)
                if comp_fig:
                    st.plotly_chart(comp_fig, use_container_width=True)
                else:
                    st.error("Failed to create comparison chart. Please check your selected stocks.")
            else:
                st.info("Add at least two stocks to compare their performance.")
        
        # Tab 3: Historical Analysis
        with tab3:
            if st.session_state.tracked_stocks:
                hist_ticker = st.selectbox("Select Stock for Historical Analysis", options=st.session_state.tracked_stocks)
                
                col1, col2 = st.columns(2)
                with col1:
                    recent_period = st.selectbox(
                        "Recent Performance Period",
                        options=["1d", "5d", "1mo", "3mo"],
                        index=1  # Default to 5d
                    )
                with col2:
                    hist_period = st.selectbox(
                        "Historical Comparison Period",
                        options=["6mo", "1y", "2y", "5y", "max"],
                        index=1  # Default to 1y
                    )
                
                hist_charts = create_historical_comparison(hist_ticker, recent_period, hist_period)
                if hist_charts:
                    recent_fig, hist_fig = hist_charts
                    st.plotly_chart(recent_fig, use_container_width=True)
                    st.plotly_chart(hist_fig, use_container_width=True)
                    
                    # Add technical analysis info
                    data = fetch_historical_data(hist_ticker, period=hist_period)
                    if data is not None and not data.empty:
                        st.subheader("Summary Statistics")
                        
                        # Calculate some basic stats
                        max_price = data['Close'].max()
                        min_price = data['Close'].min()
                        avg_price = data['Close'].mean()
                        current = data['Close'].iloc[-1]
                        start = data['Close'].iloc[0]
                        total_return = ((current - start) / start) * 100
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Highest Price", f"${max_price:.2f}")
                        col2.metric("Lowest Price", f"${min_price:.2f}")
                        col3.metric("Average Price", f"${avg_price:.2f}")
                        col4.metric("Total Return", f"{total_return:.2f}%")
                        
                        # Calculate and display volatility
                        data['Daily Return'] = data['Close'].pct_change()
                        volatility = data['Daily Return'].std() * (252 ** 0.5) * 100  # Annualized volatility
                        
                        st.metric("Annualized Volatility", f"{volatility:.2f}%")
                else:
                    st.error("Failed to create historical comparison charts.")
        
        # Tab 4: Data Export
        with tab4:
            export_ticker = st.selectbox("Select Stock for Data Export", options=st.session_state.tracked_stocks)
            
            col1, col2 = st.columns(2)
            with col1:
                export_period = st.selectbox(
                    "Select Period",
                    options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
                    index=2  # Default to 1mo
                )
            with col2:
                export_interval = st.selectbox(
                    "Select Interval",
                    options=["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    index=8  # Default to 1d
                )
            
            if st.button("Generate CSV"):
                export_data = fetch_stock_data(export_ticker, period=export_period, interval=export_interval)
                if export_data is not None and not export_data.empty:
                    st.success(f"Data prepared for {export_ticker} ({export_period}, {export_interval})")
                    st.dataframe(export_data.head())
                    st.markdown(download_csv(export_data, export_ticker), unsafe_allow_html=True)
                else:
                    st.error(f"Failed to prepare export data for {export_ticker}")

    # Auto-refresh the data (will only run in Streamlit's main thread)
    if st.session_state.tracked_stocks:
        check_alerts()
        time.sleep(1)  # Small delay to prevent too frequent refreshes
        st.rerun()

if _name_ == "_main_":
    main()
