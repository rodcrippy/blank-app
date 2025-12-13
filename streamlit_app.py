import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import numpy as np 

# Set page configuration
st.set_page_config(page_title="ANALYTICA LabZ", layout="wide", page_icon="📈")

# Fetching stock data from Yahoo Finance with caching
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_stock_data(symbol, time_range="max"):
    stock = yf.Ticker(symbol)
    stock_data = stock.history(period=time_range)

    if stock_data.empty:
        st.error("Error: Unable to fetch stock data.")
        return None

    stock_data = stock_data[['Open', 'High', 'Low', 'Close', 'Volume']]
    return stock_data

# Calculate price differences based on days
def calculate_price_differences(stock_data):
    if len(stock_data) < 30:
        st.error("Insufficient historical data for price difference calculations.")
        return None, None, None, None, None
    
    daily_diff = stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[-2]
    weekly_diff = stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[-6]
    monthly_diff = stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[-22]
    days_90_diff = stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[-90]
    months_6_diff = stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[-132]
    return daily_diff, weekly_diff, monthly_diff, days_90_diff, months_6_diff

# Calculate a regression curve for the data and bands with stable historical zones
@st.cache_data(ttl=86400)  # Cache for 24 hours to maintain consistency
def calculate_regression_curve(symbol, _x_values, _y_values, degree=2, num_bands=4):
    """
    Calculate regression curve with fixed historical zones.
    Uses all historical data to establish consistent reference points.
    Note: _x_values and _y_values are unhashed parameters (pandas objects)
    """
    x_numeric = np.arange(len(_y_values))
    y_numeric = _y_values.values
    
    # Limit polynomial degree to max of (data length - 1)
    if degree > len(y_numeric) - 1:
        degree = len(y_numeric) - 1
    
    # Improved normalization to avoid polyfit conditioning warnings
    # Use mean centering and scaling for better numerical stability
    x_mean = np.mean(x_numeric)
    x_std = np.std(x_numeric)
    if x_std == 0:
        x_std = 1
    x_transformed = (x_numeric - x_mean) / x_std
    
    # Scale y values for better conditioning
    y_mean = np.mean(y_numeric)
    y_std = np.std(y_numeric)
    if y_std == 0:
        y_std = 1
    y_scaled = (y_numeric - y_mean) / y_std
    
    # Apply polynomial fit with improved conditioning
    with np.errstate(all='ignore'):  # Suppress numpy warnings
        try:
            coefficients = np.polyfit(x_transformed, y_scaled, degree, rcond=None)
            polynomial = np.poly1d(coefficients)
            
            # Calculate regression values in scaled space
            regression_scaled = polynomial(x_transformed)
            
            # Transform back to original scale
            regression_values = regression_scaled * y_std + y_mean
            
        except np.RankWarning:
            # Fallback to lower degree if poorly conditioned
            degree = max(1, degree // 2)
            coefficients = np.polyfit(x_transformed, y_scaled, degree, rcond=None)
            polynomial = np.poly1d(coefficients)
            regression_scaled = polynomial(x_transformed)
            regression_values = regression_scaled * y_std + y_mean
    
    # Calculate residuals for determining standard deviation bands
    residuals = y_numeric - regression_values
    std_residuals = np.std(residuals)
    
    bands = []
    colors = ['green', 'blue', 'red', 'purple']
    band_annotations = [
        ('Take Profit Level 1', 'black', 'DCA Buy Level 1', 'green'),
        ('Take Profit Level 2', 'blue', 'DCA Buy Level 2', 'blue'),
        ('Take Profit Level 3', 'red', 'DCA Buy Level 3', 'red'),
        ('Take Profit Level 4', 'purple', 'DCA Buy Level 4', 'purple')
    ]

    for i in range(1, num_bands + 1):
        lower_band = regression_values - i * 1.5 * std_residuals
        upper_band = regression_values + i * 1.5 * std_residuals
        bands.append((lower_band, upper_band, colors[i - 1], band_annotations[i - 1]))

    return regression_values, bands, degree

# Function to center the DataFrame headers
def centered_dataframe(df):
    styled_df = df.style.set_table_attributes('style="width:100%; border-collapse:collapse;"') \
                         .set_table_styles(
                             [{'selector': 'th', 'props': [('text-align', 'center')]}]
                         )
    return styled_df.to_html(escape=False)

# Main app function
def app():
    # Add Google Analytics tracking
    st.markdown('''
        <!-- Google tag (gtag.js) -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-EQ0NXTHK2E"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());

          gtag('config', 'G-EQ0NXTHK2E');
        </script>
    ''', unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; font-size: 64px;'>📉 DCA NAVIGATOR 📈</h1>", unsafe_allow_html=True)

    st.sidebar.markdown("<h2 style='text-align: center; font-size: 40px;'>ANALYTICA Labs</h2>", unsafe_allow_html=True)

    st.sidebar.markdown(
        "<h5 style='text-align: center;'>Powered by <a href='https://finance.yahoo.com' style='color: blue;'>Yahoo Finance</a></h5>",
        unsafe_allow_html=True
    )

    # Initialize session state for storing ticker-specific settings
    if 'ticker_settings' not in st.session_state:
        st.session_state.ticker_settings = {}
    
    # Get query parameters to preserve state across browser refreshes
    query_params = st.query_params
    
    # Initialize values from query parameters or defaults
    default_symbol = query_params.get("symbol", "AAPL")
    default_chart = query_params.get("chart", "Candlestick Chart")

    symbol = st.sidebar.text_input(
        "Enter a stock ticker (e.g., AAPL, TSLA):",
        value=default_symbol,
        help="Enter the stock symbol you wish to look up. All valid tickers can be found on Yahoo Finance. Examples include 'AAPL' for Apple Inc. and 'TSLA' for Tesla Inc."
    ).upper()

    chart_types = ["Candlestick Chart", "Line Chart"]
    # Safely get the index, default to 0 if not found
    try:
        chart_index = chart_types.index(default_chart)
    except ValueError:
        chart_index = 0
    
    chart_type = st.sidebar.radio(
        "Select Chart Type:", 
        chart_types, 
        index=chart_index,
        help="To identify price action events for DCA entry use the Line Chart"
    )

    # Get the saved degree for this specific ticker, or use default
    if symbol in st.session_state.ticker_settings:
        saved_degree = st.session_state.ticker_settings[symbol].get('degree', 2)
    else:
        # Try to get from query params, otherwise default to 2
        saved_degree = int(query_params.get("degree", "2"))

    # Initialize temp degree in session state if not present
    if 'temp_degree' not in st.session_state:
        st.session_state.temp_degree = saved_degree
    
    # Update temp_degree when switching tickers
    if 'last_symbol' not in st.session_state or st.session_state.last_symbol != symbol:
        st.session_state.temp_degree = saved_degree
        st.session_state.last_symbol = symbol

    # Custom CSS for smaller +/- buttons
    st.sidebar.markdown("""
        <style>
        div[data-testid="column"] button {
            height: 28px;
            padding: 0px 8px;
            font-size: 14px;
            min-width: 28px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("**Polynomial Degree for Regression Curve**")
    
    # Create columns for -/+ buttons and slider with tighter spacing
    col_minus, col_slider, col_plus = st.sidebar.columns([0.5, 7, 0.5])
    
    with col_minus:
        if st.button("➖", key="degree_minus", help="Decrease degree by 1"):
            st.session_state.temp_degree = max(1, st.session_state.temp_degree - 1)
    
    with col_plus:
        if st.button("➕", key="degree_plus", help="Increase degree by 1"):
            st.session_state.temp_degree = min(100, st.session_state.temp_degree + 1)
    
    with col_slider:
        degree = st.slider(
            "Degree", 
            min_value=1, 
            max_value=100, 
            value=st.session_state.temp_degree, 
            step=1,
            format="%d",
            label_visibility="collapsed",
            help="## Effect of Polynomial Degree on Stock Price Chart\n\n"
                 "* **High Polynomial Degree:**\n"
                 "  - You will see price action events more frequently, resulting in more DCA buying opportunities with smaller price changes. This allows you to invest smaller amounts more often, potentially diversifying your investments but may also lead to higher transaction fees.\n"
                 "\n"
                 "* **Low Polynomial Degree:**\n"
                 "  - You will encounter price action events less often, resulting in fewer DCA opportunities with larger price changes. This means you'll invest larger amounts less frequently, which can simplify your investment strategy but might cause you to miss out on some opportunities.\n"
                 "\n"
                 "## Summary:\n"
                 "It's important to decide how often you want to DCA buy, how much to consistently invest each time a DCA price action event occurs, and how this choice affects your overall investment strategy. Each stock/cryptocurrency is subjective to working best with its own specific value. THERE IS NO ONE SET VALUE THAT IS THE HOLY GRAIL. It all depends on your budget and desired frequency of investing."
        )
    
    # Update temp_degree to match slider if user dragged it
    st.session_state.temp_degree = degree
    
    # Display current degree value
    st.sidebar.markdown(f"<p style='text-align: center; font-size: 16px; margin-top: -10px;'>Current Degree: <b>{degree}</b></p>", unsafe_allow_html=True)
    
    # Save the degree setting for this specific ticker
    if symbol not in st.session_state.ticker_settings:
        st.session_state.ticker_settings[symbol] = {}
    st.session_state.ticker_settings[symbol]['degree'] = degree
    
    # Update query parameters to preserve state across browser refreshes
    st.query_params.update({
        "symbol": symbol,
        "chart": chart_type,
        "degree": str(degree)
    })

    if symbol:
        stock_data = get_stock_data(symbol)

        if stock_data is not None:
            if len(stock_data) < 30:
                st.error("Insufficient historical data for price difference calculations.")
                return
            
            @st.cache_data(ttl=3600)  # Cache for 1 hour
            def get_stock_info(symbol):
                return yf.Ticker(symbol).info
            
            stock_info = get_stock_info(symbol)
            stock_name = stock_info.get('longName', stock_info.get('shortName', symbol))

            st.markdown(f"<p style='font-size:40px; text-align: center; font-weight:bold;'>{stock_name}</p>", unsafe_allow_html=True)

            daily_diff, weekly_diff, monthly_diff, days_90_diff, months_6_diff = calculate_price_differences(stock_data)

            if daily_diff is None: 
                return

            percentage_difference_daily = (daily_diff / stock_data['Close'].iloc[-2]) * 100
            percentage_difference_weekly = (weekly_diff / stock_data['Close'].iloc[-6]) * 100
            percentage_difference_monthly = (monthly_diff / stock_data['Close'].iloc[-22]) * 100
            percentage_difference_days_90 = (days_90_diff / stock_data['Close'].iloc[-90]) * 100
            percentage_difference_months_6 = (months_6_diff / stock_data['Close'].iloc[-132]) * 100

            latest_close_price = stock_data['Close'].iloc[-1]
            max_52_week_high = stock_data['Close'].rolling(window=252).max().iloc[-1]
            min_52_week_low = stock_data['Close'].rolling(window=252).min().iloc[-1]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Close Price", f"${latest_close_price:,.4f}")
            with col2:
                st.metric("Daily Price Difference", f"${daily_diff:,.4f}", f"{percentage_difference_daily:+.2f}%")
            with col3:
                st.metric("Weekly Price Difference", f"${weekly_diff:,.4f}", f"{percentage_difference_weekly:+.2f}%")
            with col4:
                st.metric("Monthly Price Difference", f"${monthly_diff:,.4f}", f"{percentage_difference_monthly:+.2f}%")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("90 Days Price Difference", f"${days_90_diff:,.4f}", f"{percentage_difference_days_90:+.2f}%")
            with col2:
                st.metric("6 Months Price Difference", f"${months_6_diff:,.4f}", f"{percentage_difference_months_6:+.2f}%")
            with col3:
                st.metric("52-Week High", f"${max_52_week_high:,.4f}")
            with col4:
                st.metric("52-Week Low", f"${min_52_week_low:,.4f}")



            st.subheader(chart_type)
            chart_data = go.Figure()

            if chart_type == "Candlestick Chart":
                chart_data.add_trace(go.Candlestick(
                    x=stock_data.index,
                    open=stock_data['Open'],
                    high=stock_data['High'],
                    low=stock_data['Low'],
                    close=stock_data['Close'],
                    showlegend=False  # Hide the legend for the candlestick chart
                ))

            regression_values, bands, degree = calculate_regression_curve(symbol, stock_data.index, stock_data['Close'], degree)
            chart_data.add_trace(go.Scatter(
                x=stock_data.index,
                y=regression_values,
                mode='lines',
                name='Regression Curve',
                line=dict(color='orange', width=2),
                showlegend=False
            ))

            for i, (lower_band, upper_band, color, (upper_text, upper_color, lower_text, lower_color)) in enumerate(bands):
                chart_data.add_trace(go.Scatter(
                    x=stock_data.index,
                    y=upper_band,
                    mode='lines',
                    name='Take Profit Zones',
                    line=dict(color=color, width=1),
                    showlegend=False
                ))

                chart_data.add_trace(go.Scatter(
                    x=stock_data.index,
                    y=lower_band,
                    mode='lines',
                    name='DCA Buy Zones',
                    line=dict(color=color, width=1),
                    showlegend=False
                ))

                # Add annotations for each band
                annotation_offset = 0.10 * len(stock_data)
                annotation_x = stock_data.index[-1] + pd.DateOffset(days=annotation_offset)

                chart_data.add_annotation(
                    x=annotation_x,
                    y=upper_band[-1],
                    text=upper_text,
                    font=dict(color=upper_color, size=12),
                    showarrow=False
                )

                chart_data.add_annotation(
                    x=annotation_x,
                    y=lower_band[-1],
                    text=lower_text,
                    font=dict(color=lower_color, size=12),
                    showarrow=False
                )

            if chart_type == "Line Chart":
                chart_data.add_trace(go.Scatter(
                    x=stock_data.index,
                    y=stock_data['Close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color='blue', width=1), 
                    showlegend=False
                ))

            chart_data.update_layout(title=f"{symbol} - {chart_type}",
                                      xaxis_rangeslider_visible=False,
                                      yaxis=dict(title="Price", tickprefix="$"),
                                      xaxis_title="")
            st.plotly_chart(chart_data, use_container_width=True)

            st.subheader("Summary")
            last_30_days = stock_data.tail(30).reset_index()  # Convert the index to a column
            last_30_days.rename(columns={'index': 'Date'}, inplace=True)  # Rename the index column to 'Date'
            
            # Display the DataFrame in a scrollable format
            st.dataframe(last_30_days, height=300)  # Display the DataFrame, set height to control initial view
            
            # Add manual refresh button
            if st.sidebar.button("🔄 Refresh Data"):
                st.cache_data.clear()
                st.rerun()

if __name__ == "__main__":
    app()
