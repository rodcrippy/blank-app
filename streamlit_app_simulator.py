import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import numpy as np
from datetime import datetime, timedelta
import json
import hashlib
import os

# Set page configuration
st.set_page_config(page_title="ANALYTICA LabZ - DCA Simulator", layout="wide", page_icon="📈")

# ============================================================================
# LOGIN SYSTEM
# ============================================================================

USER_DB_FILE = "users_db.json"

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password):
    """Validate password meets security requirements"""
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least 1 uppercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least 1 number"
    
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        return False, "Password must contain at least 1 special character (!@#$%^&* etc.)"
    
    return True, "Password is valid"

def load_users():
    """Load users from JSON database"""
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON database"""
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def create_user(username, password, email):
    """Create a new user account"""
    users = load_users()
    
    if username in users:
        return False, "Username already exists"
    
    now = datetime.now()
    trial_end = now + timedelta(days=7)
    
    users[username] = {
        'password': hash_password(password),
        'email': email,
        'created_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'last_login': None,
        'access_level': 'trial',  # Start with trial
        'login_count': 0,
        'subscription_status': 'trial',  # 'trial', 'active', 'expired'
        'trial_start_date': now.strftime('%Y-%m-%d'),
        'trial_end_date': trial_end.strftime('%Y-%m-%d'),
        'subscription_end_date': None,  # Set when payment is made
        'daily_usage_count': 0,
        'last_usage_date': now.strftime('%Y-%m-%d'),
        'total_usage_count': 0
    }
    
    save_users(users)
    return True, "Account created successfully! Your 7-day trial has started."

def authenticate_user(username, password):
    """Authenticate user credentials"""
    users = load_users()
    
    if username not in users:
        return False, "Username not found"
    
    if users[username]['password'] != hash_password(password):
        return False, "Incorrect password"
    
    # Update last login
    users[username]['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    users[username]['login_count'] = users[username].get('login_count', 0) + 1
    save_users(users)
    
    return True, "Login successful"

def get_user_info(username):
    """Get user information"""
    users = load_users()
    return users.get(username, None)

def check_and_update_subscription_status(username):
    """Check if trial or subscription has expired and update status"""
    users = load_users()
    if username not in users:
        return None
    
    user = users[username]
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    
    # Reset daily usage counter if it's a new day
    if user.get('last_usage_date') != today:
        user['daily_usage_count'] = 0
        user['last_usage_date'] = today
    
    # Check trial expiration
    if user.get('subscription_status') == 'trial':
        trial_end = datetime.strptime(user.get('trial_end_date', today), '%Y-%m-%d')
        if now > trial_end:
            user['subscription_status'] = 'expired'
            user['access_level'] = 'free'
    
    # Check subscription expiration
    elif user.get('subscription_status') == 'active' and user.get('subscription_end_date'):
        sub_end = datetime.strptime(user['subscription_end_date'], '%Y-%m-%d')
        if now > sub_end:
            user['subscription_status'] = 'expired'
            user['access_level'] = 'free'
    
    save_users(users)
    return user

def check_usage_limit(username):
    """Check if user has exceeded daily usage limit"""
    user = check_and_update_subscription_status(username)
    if not user:
        return False, "User not found"
    
    # Premium and active subscribers get unlimited access
    if user.get('subscription_status') in ['active'] or user.get('access_level') == 'premium':
        return True, "unlimited"
    
    # Trial users get unlimited access during trial
    if user.get('subscription_status') == 'trial':
        trial_end = datetime.strptime(user.get('trial_end_date'), '%Y-%m-%d')
        days_remaining = (trial_end - datetime.now()).days + 1
        return True, f"trial:{days_remaining}"
    
    # Free/expired users get 3 per day
    daily_limit = 3
    current_usage = user.get('daily_usage_count', 0)
    
    if current_usage >= daily_limit:
        return False, f"Daily limit of {daily_limit} chart views reached. Upgrade to premium for unlimited access."
    
    return True, f"free:{daily_limit - current_usage}"

def increment_usage(username):
    """Increment user's daily usage counter"""
    users = load_users()
    if username not in users:
        return
    
    user = users[username]
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    
    # Reset counter if new day
    if user.get('last_usage_date') != today:
        user['daily_usage_count'] = 0
        user['last_usage_date'] = today
    
    user['daily_usage_count'] = user.get('daily_usage_count', 0) + 1
    user['total_usage_count'] = user.get('total_usage_count', 0) + 1
    
    save_users(users)

def upgrade_to_premium(username, months=1):
    """Upgrade user to premium subscription"""
    users = load_users()
    if username not in users:
        return False, "User not found"
    
    now = datetime.now()
    sub_end = now + timedelta(days=30 * months)
    
    users[username]['subscription_status'] = 'active'
    users[username]['access_level'] = 'premium'
    users[username]['subscription_end_date'] = sub_end.strftime('%Y-%m-%d')
    users[username]['daily_usage_count'] = 0  # Reset counter
    
    save_users(users)
    return True, f"Upgraded to premium! Subscription active until {sub_end.strftime('%B %d, %Y')}"

def get_subscription_info(username):
    """Get detailed subscription information for display"""
    user = check_and_update_subscription_status(username)
    if not user:
        return None
    
    info = {
        'status': user.get('subscription_status', 'unknown'),
        'access_level': user.get('access_level', 'free'),
        'daily_usage': user.get('daily_usage_count', 0),
        'total_usage': user.get('total_usage_count', 0)
    }
    
    # Calculate days remaining
    if user.get('subscription_status') == 'trial':
        trial_end = datetime.strptime(user.get('trial_end_date'), '%Y-%m-%d')
        info['days_remaining'] = max(0, (trial_end - datetime.now()).days + 1)
        info['end_date'] = user.get('trial_end_date')
    elif user.get('subscription_status') == 'active' and user.get('subscription_end_date'):
        sub_end = datetime.strptime(user.get('subscription_end_date'), '%Y-%m-%d')
        info['days_remaining'] = max(0, (sub_end - datetime.now()).days + 1)
        info['end_date'] = user.get('subscription_end_date')
    else:
        info['days_remaining'] = 0
        info['end_date'] = None
    
    return info

def reset_password(username, email, new_password):
    """Reset user password after verification"""
    users = load_users()
    
    if username not in users:
        return False, "Username not found"
    
    if users[username]['email'] != email:
        return False, "Email does not match our records"
    
    # Update password
    users[username]['password'] = hash_password(new_password)
    save_users(users)
    
    return True, "Password reset successful"

def initialize_session_state():
    """Initialize session state variables"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'access_level' not in st.session_state:
        st.session_state.access_level = None
    if 'show_reset_password' not in st.session_state:
        st.session_state.show_reset_password = False
    if 'intro_seen' not in st.session_state:
        st.session_state.intro_seen = False
    if 'dca_strategy' not in st.session_state:
        st.session_state.dca_strategy = 'Zone Multiplier DCA'  # Default to enhanced version
    if 'active_tp_zones' not in st.session_state:
        st.session_state.active_tp_zones = [1, 2, 3, 4]  # All zones active by default
    if 'usage_tracked' not in st.session_state:
        st.session_state.usage_tracked = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'DCA Navigator'

def logout():
    """Logout current user"""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.access_level = None
    st.session_state.intro_seen = False  # Reset intro when logging out

def show_intro_page():
    """Display introduction/marketing page after login"""
    st.title("🎯 Welcome to the DCA Navigator")
    st.markdown("### For the Crypto On Crack Community")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## After 4 Years, Here's Your Visual
        
        For over **4 years**, our community of **17,000+ members** in Crypto On Crack has been successfully using 
        the simplified DCA approach. You've seen the results. You've built wealth systematically. You've avoided the 
        emotional rollercoaster of trying to time the market.
        
        **Now, after years of strenuous testing and refinement, I've finally developed a visualization of our daily DCA efforts.**
        
        ### Why This Changes Everything
        
        Having this visual is **priceless**. It bridges the gap from concept to visual understanding—turning abstract 
        strategy into clear, actionable data you can see and trust.
        
        Instead of wondering "Should I DCA today?", you now **see exactly where price sits** relative to:
        - Historical accumulation zones
        - Take-profit levels
        - Mathematical fair value baseline
        
        The confusion is gone. The guesswork is eliminated. The strategy you've been following now has **visual confirmation**.
        
        ### Two Perspectives, One Tool
        
        This tool lets you compare both approaches side-by-side:
        
        **📊 Simplified DCA** - The foundational approach our community has used for years. Steady, consistent accumulation 
        below regression with standard position sizing. Perfect for hands-off wealth building.
        
        **⚡ Zone Multiplier DCA** - The enhanced strategy with 5x entry multipliers at key buy zones. Same core concept, 
        but with strategic position sizing based on zone depth. This is what I personally use daily.
        
        You can toggle between both perspectives to see how each approach would have performed on any asset, any timeframe.
        
        ### The Backtesting Simulator
        
        Test either strategy on historical data:
        
        ✅ **See exact entry/exit points** from past cycles  
        ✅ **Compare simplified DCA vs. zone multiplier DCA** side-by-side  
        ✅ **Adjust intensity levels** to match your risk tolerance  
        ✅ **Calculate total returns** vs. simply holding  
        ✅ **Validate the approach** across different market conditions
        
        This is how you gain confidence—by seeing it work repeatedly across real historical data.
        
        ---
        
        ### For Our Community
        
        You've already proven the strategy works by using it for years. Now you have the **visual framework** that makes 
        it even easier to execute consistently. See your daily DCA efforts in context. Understand where you are in the cycle. 
        Make decisions with clarity instead of emotion.
        
        This isn't a new strategy—it's a **visualization of what we've been doing all along**, refined through 4 years 
        of real-world testing with 17,000+ members.
        
        """)
        
        if st.button("🚀 Continue to App", type="primary", use_container_width=True):
            st.session_state.intro_seen = True
            st.rerun()
    
    with col2:
        st.markdown("### 📈 Community Stats")
        
        st.info("""
        **Crypto On Crack**  
        17,000+ Active Members
        
        **Strategy Age**  
        4+ Years of Testing
        
        **Proven Approach**  
        Simplified DCA
        
        **Time Commitment**  
        5 minutes per day
        """)
        
        st.success("""
        **🎯 What's New**
        
        ✨ Visual representation
        ✨ Historical zone mapping
        ✨ Real-time positioning
        ✨ Backtesting simulator
        ✨ Strategy comparison
        """)
        
        st.warning("""
        **⚠️ Two Approaches**
        
        **Simplified DCA**
        • What we've used for 4 years
        • Consistent position sizing
        • Hands-off approach
        
        **Zone Multiplier DCA**
        • Enhanced with 5x entries
        • Strategic position sizing
        • Active optimization
        """)
        
        st.markdown("""
        ---
        **Returning member?**
        """)
        if st.button("Skip Intro"):
            st.session_state.intro_seen = True
            st.rerun()

def show_login_page():
    """Display login/signup page"""
    # Create centered layout with 30% width
    col1, col2, col3 = st.columns([0.35, 0.30, 0.35])
    
    with col2:
        st.title("🔐 ANALYTICA LabZ")
        st.markdown("### DCA Navigator")
        st.markdown("---")
        
        # Check if showing password reset form
        if st.session_state.show_reset_password:
            st.markdown("### 🔒 Reset Password")
            st.info("For security, you must set a new password. Please provide your username and registered email to verify your identity.")
            
            with st.form("reset_password_form"):
                reset_username = st.text_input("Username")
                reset_email = st.text_input("Email (for verification)")
                reset_new_password = st.text_input("New Password", type="password")
                reset_confirm_password = st.text_input("Confirm New Password", type="password")
                
                submit_reset = st.form_submit_button("🔑 Reset Password", type="primary", use_container_width=True)
                cancel_reset = st.form_submit_button("Cancel", use_container_width=True)
                
                if cancel_reset:
                    st.session_state.show_reset_password = False
                    st.rerun()
                
                if submit_reset:
                    if not reset_username or not reset_email or not reset_new_password:
                        st.error("All fields are required")
                    elif reset_new_password != reset_confirm_password:
                        st.error("Passwords do not match")
                    else:
                        valid, msg = validate_password(reset_new_password)
                        if not valid:
                            st.error(msg)
                        else:
                            success, message = reset_password(reset_username, reset_email, reset_new_password)
                            if success:
                                st.success(message + " - You can now login with your new password!")
                                st.session_state.show_reset_password = False
                                st.balloons()
                            else:
                                st.error(message)
            
            return
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.markdown("#### Welcome Back!")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", type="primary", use_container_width=True)
                
                if submit:
                    if not username or not password:
                        st.error("Please enter both username and password")
                    else:
                        success, message = authenticate_user(username, password)
                        if success:
                            user_info = get_user_info(username)
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.access_level = user_info['access_level']
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            
            # Forgot password button
            if st.button("🔑 Forgot Password?", help="Reset your password securely", use_container_width=True):
                st.session_state.show_reset_password = True
                st.rerun()
        
        with tab2:
            st.markdown("#### Create New Account")
            with st.form("signup_form"):
                new_username = st.text_input("Username", key="signup_user")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password", key="signup_pass")
                confirm_password = st.text_input("Confirm Password", type="password")
                submit_signup = st.form_submit_button("Create Account", type="primary", use_container_width=True)
                
                if submit_signup:
                    if not new_username or not new_email or not new_password:
                        st.error("All fields are required")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        valid, msg = validate_password(new_password)
                        if not valid:
                            st.error(msg)
                        else:
                            success, message = create_user(new_username, new_password, new_email)
                            if success:
                                st.success(message + " - You can now login!")
                            else:
                                st.error(message)
            
            st.info("""💡 **Password Requirements:**
            - Minimum 12 characters
            - At least 1 uppercase letter
            - At least 1 number
            - At least 1 special character (!@#$%^&* etc.)
            
            **Tip:** Use a valid email - you'll need it to reset your password!""")

# ============================================================================
# END LOGIN SYSTEM
# ============================================================================

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

# Calculate a regression curve - ORIGINAL METHOD (Simple)
@st.cache_data(ttl=86400)
def calculate_regression_curve_original(symbol, _x_values, _y_values, degree=2, num_bands=4):
    """
    Original polynomial fitting method - simpler normalization
    """
    x_numeric = np.arange(len(_y_values))
    y_numeric = _y_values.values
    
    # Limit polynomial degree to max of (data length - 1)
    if degree > len(y_numeric) - 1:
        degree = len(y_numeric) - 1
    
    # Simple normalization to [0, 1]
    x_transformed = x_numeric / np.max(x_numeric)
    
    # Apply polynomial fit
    coefficients = np.polyfit(x_transformed, y_numeric, degree)
    polynomial = np.poly1d(coefficients)
    
    # Calculate regression values
    regression_values = polynomial(x_transformed)
    
    # Calculate residuals for bands
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

# Calculate a regression curve - ENHANCED METHOD (Advanced)
@st.cache_data(ttl=86400)  # Cache for 24 hours to maintain consistency
def calculate_regression_curve_enhanced(symbol, _x_values, _y_values, degree=2, num_bands=4):
    """
    Enhanced polynomial fitting with improved numerical stability
    """
    x_numeric = np.arange(len(_y_values))
    y_numeric = _y_values.values
    
    # Limit polynomial degree to max of (data length - 1)
    if degree > len(y_numeric) - 1:
        degree = len(y_numeric) - 1
    
    # Improved normalization - mean centering and scaling
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
    with np.errstate(all='ignore'):
        try:
            coefficients = np.polyfit(x_transformed, y_scaled, degree, rcond=None)
            polynomial = np.poly1d(coefficients)
            regression_scaled = polynomial(x_transformed)
            regression_values = regression_scaled * y_std + y_mean
            
        except np.RankWarning:
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

# Main wrapper function that routes to selected method
def calculate_regression_curve(symbol, _x_values, _y_values, degree=2, num_bands=4, use_original=False):
    """
    Main regression curve calculator - routes to original or enhanced method
    """
    if use_original:
        return calculate_regression_curve_original(symbol, _x_values, _y_values, degree, num_bands)
    else:
        return calculate_regression_curve_enhanced(symbol, _x_values, _y_values, degree, num_bands)

# Function to center the DataFrame headers
def centered_dataframe(df):
    styled_df = df.style.set_table_attributes('style="width:100%; border-collapse:collapse;"') \
                         .set_table_styles(
                             [{'selector': 'th', 'props': [('text-align', 'center')]}]
                         )
    return styled_df.to_html(escape=False)

def analyze_market_position(current_price, regression_values, bands, stock_data):
    """
    Analyze current market position relative to polynomial levels and provide trading signal.
    
    Returns: dict with signal, description, and recommendation
    """
    # Get current regression level and bands
    current_regression = regression_values[-1]
    
    # Calculate historical context
    lookback_period = min(252, len(stock_data))  # 1 year or available data
    historical_high = stock_data['High'].iloc[-lookback_period:].max()
    historical_low = stock_data['Low'].iloc[-lookback_period:].min()
    recent_high = stock_data['High'].iloc[-30:].max()  # Last 30 days
    recent_low = stock_data['Low'].iloc[-30:].min()    # Last 30 days
    
    # Price momentum analysis (last 5 days)
    recent_prices = stock_data['Close'].iloc[-5:]
    price_5d_ago = recent_prices.iloc[0] if len(recent_prices) >= 5 else current_price
    price_momentum = ((current_price - price_5d_ago) / price_5d_ago) * 100
    is_pushing_higher = price_momentum > 2  # More than 2% gain in 5 days
    is_rejecting = price_momentum < -2  # More than 2% loss in 5 days
    
    # Calculate position metrics
    distance_from_regression = ((current_price - current_regression) / current_regression) * 100
    distance_from_high = ((current_price - historical_high) / historical_high) * 100
    distance_from_low = ((current_price - historical_low) / historical_low) * 100
    
    # Determine which zone the price is in (considering active TP zones)
    current_zone_level = None
    zone_type = None  # 'buy' or 'sell'
    next_zone_level = None
    active_tp_zones = st.session_state.get('active_tp_zones', [1, 2, 3, 4])
    
    for level, (lower_band, upper_band, color, annotations) in enumerate(bands, 1):
        if current_price < lower_band[-1]:
            current_zone_level = level
            zone_type = 'buy'
            break
        elif current_price > upper_band[-1]:
            # Only consider this a sell zone if it's in the active TP zones list
            if level in active_tp_zones:
                current_zone_level = level
                zone_type = 'sell'
                # Check if there's a higher active zone
                for higher_level in range(level + 1, len(bands) + 1):
                    if higher_level in active_tp_zones:
                        next_zone_level = higher_level
                        break
            # Keep checking for higher zones
    
    # Determine market phase
    is_near_historical_high = (current_price / historical_high) > 0.95
    is_near_historical_low = (current_price / historical_low) < 1.05
    is_above_regression = current_price > current_regression
    is_below_regression = current_price < current_regression
    
    # Generate signal and recommendation
    signal = ""
    signal_color = ""
    description = ""
    recommendation = ""
    
    if zone_type == 'sell' and is_above_regression:
        signal = "🔴 SELL NOW"
        signal_color = "red"
        zone_text = f"Take Profit Zone {current_zone_level}" if current_zone_level else "Take Profit zone"
        
        # Determine price action context
        price_action_context = ""
        if is_pushing_higher and next_zone_level:
            price_action_context = f" Price momentum is **strong (+{price_momentum:.1f}% over 5 days)** and pushing toward **TP Zone {next_zone_level}**."
        elif is_pushing_higher:
            price_action_context = f" Price momentum is **strong (+{price_momentum:.1f}% over 5 days)** and may extend higher."
        elif is_rejecting:
            price_action_context = f" Price is **rejecting ({price_momentum:.1f}% over 5 days)** and showing weakness."
        else:
            price_action_context = f" Price is **consolidating** at this level."
        
        description = f"Price is **+{abs(distance_from_regression):.1f}%** above regression curve in **{zone_text}**.{price_action_context}"
        
        if is_near_historical_high:
            if is_pushing_higher and next_zone_level:
                recommendation = f"🎯 **Action:** Price is pushing through **{zone_text}** toward **TP Zone {next_zone_level}**. Consider taking 25-50% profits now and watching daily action. If momentum continues, wait for next zone. If rejection occurs, exit immediately. Near historical highs—risk of reversal is elevated."
            elif is_rejecting:
                recommendation = f"🎯 **Action:** **SELL IMMEDIATELY** at **{zone_text}**. Price is rejecting and near historical highs ({((current_price/historical_high)*100):.1f}% of peak). This is peak exit opportunity. Sell 75-100% of position to lock in gains before potential reversal."
            else:
                recommendation = f"🎯 **Action:** Take profits at **{zone_text}**. Price is near historical highs ({((current_price/historical_high)*100):.1f}% of peak). Consider selling 50-75% now. **Watch daily action:** if price breaks higher, hold remainder for next zone; if rejection, exit fully."
        else:
            distance_to_high = ((historical_high - current_price) / current_price) * 100
            if is_pushing_higher and next_zone_level:
                recommendation = f"🎯 **Action:** Strong momentum detected. Consider taking 25% profits at **{zone_text}** and holding remainder for **TP Zone {next_zone_level}**. **Monitor daily:** Sell more if rejection appears. Distance to historical high: {distance_to_high:.1f}%."
            elif is_rejecting:
                recommendation = f"🎯 **Action:** Price rejecting at **{zone_text}**. Take profits NOW—sell 50-75% of position. The strategy signals distribution phase. Set stop-loss for remainder at zone entry level."
            else:
                recommendation = f"🎯 **Action:** Take profits at **{zone_text}** levels. Price is {distance_to_high:.1f}% below historical high. Sell 25-50% now. **Watch daily candles:** Strong closes above = potential for higher zones; weak closes/wicks = exit signal."
    
    elif zone_type == 'buy' and is_below_regression:
        signal = "🟢 BUY NOW"
        signal_color = "green"
        zone_text = f"DCA Buy Zone {current_zone_level}" if current_zone_level else "DCA Buy zone"
        
        # Determine price action for buy zones
        price_action_context = ""
        if is_rejecting and next_zone_level:
            price_action_context = f" Price is **falling ({price_momentum:.1f}% over 5 days)** and may drop to **Buy Zone {next_zone_level}**."
        elif is_rejecting:
            price_action_context = f" Price is **declining ({price_momentum:.1f}% over 5 days)**—deeper entry possible."
        elif is_pushing_higher:
            price_action_context = f" Price is **bouncing (+{price_momentum:.1f}% over 5 days)**—support found."
        else:
            price_action_context = f" Price is **stabilizing** at this level."
        
        description = f"Price is **{distance_from_regression:.1f}%** below regression curve in **{zone_text}**.{price_action_context}"
        
        if is_near_historical_low:
            if is_rejecting and next_zone_level:
                recommendation = f"🎯 **Action:** At **{zone_text}** near historical lows. Price still falling—consider splitting buy: 2.5X now, 2.5X if **Buy Zone {next_zone_level}** reached. **Watch daily action** for capitulation signals. This is prime accumulation territory."
            elif is_pushing_higher:
                recommendation = f"🎯 **Action:** **BUY AGGRESSIVELY** at **{zone_text}**. Price bouncing from historical lows ({((current_price/historical_low)*100):.1f}% above bottom). Execute full 5X DCA immediately—bottom may be in. Maximum risk-reward zone."
            else:
                recommendation = f"🎯 **Action:** Aggressive accumulation at **{zone_text}**. Near historical lows. Execute 5X DCA buys. **Monitor daily:** if breakdown continues, DCA Zone {next_zone_level if next_zone_level else 'deeper'} is next opportunity."
        else:
            distance_to_low = ((current_price - historical_low) / current_price) * 100
            if is_rejecting and next_zone_level:
                recommendation = f"🎯 **Action:** At **{zone_text}** with downward momentum. Execute 3X DCA now, reserve 2X for **Buy Zone {next_zone_level}** if weakness continues. **Daily monitoring critical:** look for volume exhaustion signals."
            elif is_pushing_higher:
                recommendation = f"🎯 **Action:** **STRONG BUY** at **{zone_text}**. Price bouncing—support established. Execute full 5X DCA. Reversal likely forming. Distance to historical low: {distance_to_low:.1f}%."
            else:
                recommendation = f"🎯 **Action:** Execute 5X DCA buy orders at **{zone_text}**. Price is {distance_to_low:.1f}% above historical low. **Watch daily price action:** Further drops = better entries; stabilization = accumulation in progress."
    
    elif is_above_regression and not zone_type:
        signal = "🟡 WAIT (HOLD)"
        signal_color = "orange"
        description = f"Price is **+{abs(distance_from_regression):.1f}%** above regression but below TP zones."
        recommendation = f"🎯 **Action:** Hold current positions and wait for **Take Profit Zone 1** to sell. Price needs to rise {((bands[0][1][-1] - current_price) / current_price * 100):.1f}% to reach first TP zone. Continue daily DCA only—no zone buys recommended at current levels."
    
    elif is_below_regression and not zone_type:
        signal = "🟡 WAIT (MONITOR)"
        signal_color = "orange"
        description = f"Price is **{distance_from_regression:.1f}%** below regression but above buy zones."
        recommendation = f"🎯 **Action:** Monitor for deeper pullback to **DCA Buy Zone 1**. Price needs to fall {((current_price - bands[0][0][-1]) / current_price * 100):.1f}% to reach first buy zone. Execute daily DCA only—wait for zone entry signals before 5X buys."
    
    else:  # Near regression line
        signal = "⚪ NEUTRAL"
        signal_color = "gray"
        description = f"Price is trading near regression curve ({distance_from_regression:+.1f}%)."
        recommendation = f"🎯 **Action:** Execute standard daily DCA only. Price is in fair value range. Wait for clear zone entries: fall {((current_price - bands[0][0][-1]) / current_price * 100):.1f}% for buy signal or rise {((bands[0][1][-1] - current_price) / current_price * 100):.1f}% for sell signal."
    
    return {
        'signal': signal,
        'signal_color': signal_color,
        'description': description,
        'recommendation': recommendation,
        'metrics': {
            'distance_from_regression': distance_from_regression,
            'distance_from_high': distance_from_high,
            'distance_from_low': distance_from_low,
            'historical_high': historical_high,
            'historical_low': historical_low,
            'recent_high': recent_high,
            'recent_low': recent_low
        }
    }

def calculate_bitcoin_ath_forecast(current_price, stock_data):
    """
    Calculate Bitcoin ATH forecast using diminishing returns with institutional adjustment.
    Only applicable for Bitcoin.
    """
    # Known Bitcoin ATH history
    ath_history = [
        {'year': 2013, 'price': 1100, 'multiplier': None},
        {'year': 2017, 'price': 19665, 'multiplier': 17.9},
        {'year': 2021, 'price': 69000, 'multiplier': 3.5}
    ]
    
    # Calculate historical diminishing rate
    # 2017→2021: 3.5x / 17.9x = 0.196 (~20% retention in retail era)
    historical_retention = 0.20
    
    # Institutional era adjusted retention rates (2024-2026+)
    # Higher retention due to ETF inflows, sovereign buyers, institutional adoption
    conservative_retention = 0.55
    base_retention = 0.65
    optimistic_retention = 0.75
    
    # Last cycle multiplier
    last_multiplier = 3.5
    last_ath = 69000
    
    # Calculate projections
    conservative_multiplier = last_multiplier * conservative_retention
    base_multiplier = last_multiplier * base_retention
    optimistic_multiplier = last_multiplier * optimistic_retention
    
    conservative_ath = last_ath * conservative_multiplier
    base_ath = last_ath * base_multiplier
    optimistic_ath = last_ath * optimistic_multiplier
    
    # Calculate progress to base target
    progress_pct = (current_price / base_ath) * 100
    
    # Determine current cycle status
    all_time_high = stock_data['High'].max()
    days_since_ath = 0
    if all_time_high > last_ath:
        # New ATH achieved in current cycle
        ath_date = stock_data['High'].idxmax()
        days_since_ath = (stock_data.index[-1] - ath_date).days
    
    return {
        'ath_history': ath_history,
        'historical_retention': historical_retention,
        'conservative': {
            'price': conservative_ath,
            'multiplier': conservative_multiplier,
            'retention': conservative_retention
        },
        'base': {
            'price': base_ath,
            'multiplier': base_multiplier,
            'retention': base_retention
        },
        'optimistic': {
            'price': optimistic_ath,
            'multiplier': optimistic_multiplier,
            'retention': optimistic_retention
        },
        'progress_pct': progress_pct,
        'current_ath': all_time_high,
        'days_since_ath': days_since_ath
    }

# Detect if asset is Stock or Crypto
def detect_asset_type(symbol):
    """Detect if symbol is a stock or cryptocurrency"""
    crypto_suffixes = ['-USD', '-USDT', '-BUSD', 'BTC', 'ETH', 'USDT', 'USDC']
    symbol_upper = symbol.upper()
    
    if any(suffix in symbol_upper for suffix in crypto_suffixes):
        return "Crypto"
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        quote_type = info.get('quoteType', '')
        
        if quote_type in ['CRYPTOCURRENCY', 'CURRENCY']:
            return "Crypto"
        elif quote_type in ['EQUITY', 'ETF', 'MUTUALFUND']:
            return "Stock"
    except:
        pass
    
    return "Stock"

# Get dividend information for stocks
@st.cache_data(ttl=3600)
def get_dividend_info(symbol):
    """Get dividend information for stock symbols"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        dividend_data = {
            'pays_dividend': False,
            'dividend_yield': 0,
            'dividend_rate': 0,
            'payout_ratio': 0,
            'ex_dividend_date': None
        }
        
        if info.get('dividendYield') and info.get('dividendYield') > 0:
            dividend_data['pays_dividend'] = True
            # dividendYield from yfinance is already a decimal (0.02 = 2%)
            dividend_data['dividend_yield'] = info.get('dividendYield', 0)
            dividend_data['dividend_rate'] = info.get('dividendRate', 0)
            # payoutRatio is also a decimal (0.5 = 50%)
            dividend_data['payout_ratio'] = info.get('payoutRatio', 0) if info.get('payoutRatio') else 0
            dividend_data['ex_dividend_date'] = info.get('exDividendDate', None)
        
        return dividend_data
    except:
        return None

# Detect DCA Buy Signals
def detect_buy_signals(stock_data, bands):
    """
    Detect DCA buy signals: Yesterday touched zone + Today stayed above
    """
    buy_signals = []
    
    for i in range(1, len(stock_data)):
        today = stock_data.iloc[i]
        yesterday = stock_data.iloc[i-1]
        today_date = stock_data.index[i]
        
        for level, (lower_band, upper_band, color, annotations) in enumerate(bands, 1):
            buy_zone = lower_band[i]
            buy_zone_yesterday = lower_band[i-1]
            
            yesterday_touched = yesterday['High'] > buy_zone_yesterday and yesterday['Low'] <= buy_zone_yesterday
            today_above = today['Low'] > buy_zone and today['High'] > buy_zone
            
            if yesterday_touched and today_above:
                buy_signals.append({
                    'date': today_date,
                    'price': today['Close'],
                    'zone_level': level,
                    'zone_price': buy_zone
                })
    
    return buy_signals

# Detect Take Profit Signals
def detect_sell_signals(stock_data, bands):
    """
    Detect take profit signals: Yesterday touched zone + Today stayed below
    """
    sell_signals = []
    
    for i in range(1, len(stock_data)):
        today = stock_data.iloc[i]
        yesterday = stock_data.iloc[i-1]
        today_date = stock_data.index[i]
        
        for level, (lower_band, upper_band, color, annotations) in enumerate(bands, 1):
            tp_zone = upper_band[i]
            tp_zone_yesterday = upper_band[i-1]
            
            yesterday_touched = yesterday['Low'] < tp_zone_yesterday and yesterday['High'] >= tp_zone_yesterday
            today_below = today['High'] < tp_zone and today['Low'] < tp_zone
            
            if yesterday_touched and today_below:
                sell_signals.append({
                    'date': today_date,
                    'price': today['Close'],
                    'zone_level': level,
                    'zone_price': tp_zone
                })
    
    return sell_signals

# Run DCA Simulation
def run_dca_simulation(stock_data, bands, total_budget, investment_years, asset_type, dividend_info, regression_values):
    """
    Simulate DCA strategy:
    - Daily DCA when price < regression line
    - 5X DCA on zone signals
    - Compound all dividends back into investment
    - Sell entire bag on TP signals
    """
    # Use trading days (252 per year) for more accurate daily DCA calculation
    trading_days_in_period = len(stock_data)  # Use actual number of trading days in the data
    daily_dca_amount = total_budget / trading_days_in_period
    
    buy_signals = detect_buy_signals(stock_data, bands)
    
    # Track portfolio
    total_invested = 0
    total_shares = 0
    cash_from_sales = 0
    dividend_income = 0
    dividend_shares_bought = 0
    trades = []
    position_history = []
    daily_buy_count = 0
    zone_buy_count = 0
    sell_count = 0
    portfolio_history = []  # Track portfolio value over time
    sell_count = 0
    
    # Create signal lookup for faster processing
    zone_buy_dates = {sig['date']: sig for sig in buy_signals}
    sell_count = 0
    
    # Process each day
    for i in range(len(stock_data)):
        date = stock_data.index[i]
        price = stock_data['Close'].iloc[i]
        high_price = stock_data['High'].iloc[i]
        low_price = stock_data['Low'].iloc[i]
        regression_price = regression_values[i]
        
        # CHECK FOR TAKE PROFIT FIRST - if we have shares and hit a TP zone, sell entire bag
        if total_shares > 0 and i > 0:
            yesterday = stock_data.iloc[i-1]
            for level, (lower_band, upper_band, color, annotations) in enumerate(bands, 1):
                tp_zone = upper_band[i]
                tp_zone_yesterday = upper_band[i-1]
                
                # Detect TP crossing: yesterday was below/touching zone, today high reached/exceeded it
                # OR today's close is above the TP zone (breakthrough)
                yesterday_below = yesterday['High'] < tp_zone_yesterday
                today_touched_or_above = high_price >= tp_zone or price >= tp_zone
                
                if yesterday_below and today_touched_or_above:
                    # SELL ENTIRE BAG at TP zone
                    sale_amount = total_shares * price
                    cash_from_sales += sale_amount
                    sell_count += 1
                    
                    # Update all open positions with sell info
                    for pos in position_history:
                        if pos['sell_date'] is None:
                            pos['sell_date'] = date
                            pos['sell_price'] = price
                            pos['sell_level'] = level
                            pos['profit_loss'] = (price - pos['buy_price']) * pos['shares']
                            pos['roi'] = ((price - pos['buy_price']) / pos['buy_price']) * 100
                            pos['hold_days'] = (date - pos['buy_date']).days
                    
                    trades.append({
                        'date': date,
                        'type': 'SELL',
                        'level': level,
                        'price': price,
                        'shares': total_shares,
                        'amount': sale_amount
                    })
                    
                    total_shares = 0  # Sold entire bag
                    break  # Exit TP check loop after first sell
        
        # Check for dividend payment (quarterly for stocks)
        if asset_type == "Stock" and dividend_info and dividend_info['pays_dividend'] and total_shares > 0:
            if i > 0 and i % 90 == 0:  # Quarterly
                quarterly_dividend = (dividend_info['dividend_rate'] / 4) * total_shares
                dividend_income += quarterly_dividend
                # Reinvest dividend immediately
                div_shares = quarterly_dividend / price
                total_shares += div_shares
                dividend_shares_bought += div_shares
        
        # Check for zone buy signal (5X)
        if date in zone_buy_dates:
            signal = zone_buy_dates[date]
            amount_to_invest = daily_dca_amount * 5
            shares_bought = amount_to_invest / price
            total_invested += amount_to_invest
            total_shares += shares_bought
            zone_buy_count += 1
            
            buy_record = {
                'buy_date': date,
                'buy_price': price,
                'buy_level': signal['zone_level'],
                'buy_type': '5X Zone',
                'shares': shares_bought,
                'amount_invested': amount_to_invest,
                'sell_date': None,
                'sell_price': None,
                'sell_level': None,
                'profit_loss': None,
                'roi': None,
                'hold_days': None
            }
            position_history.append(buy_record)
            
            trades.append({
                'date': date,
                'type': 'BUY 5X',
                'level': signal['zone_level'],
                'price': price,
                'shares': shares_bought,
                'amount': amount_to_invest
            })
        # Daily DCA when price below regression line
        elif price < regression_price:
            amount_to_invest = daily_dca_amount
            shares_bought = amount_to_invest / price
            total_invested += amount_to_invest
            total_shares += shares_bought
            daily_buy_count += 1
            
            buy_record = {
                'buy_date': date,
                'buy_price': price,
                'buy_level': 0,  # Daily buy, not zone-based
                'buy_type': 'Daily DCA',
                'shares': shares_bought,
                'amount_invested': amount_to_invest,
                'sell_date': None,
                'sell_price': None,
                'sell_level': None,
                'profit_loss': None,
                'roi': None,
                'hold_days': None
            }
            position_history.append(buy_record)
            
            trades.append({
                'date': date,
                'type': 'BUY Daily',
                'level': 0,
                'price': price,
                'shares': shares_bought,
                'amount': amount_to_invest
            })
        
        # Track daily portfolio value
        current_portfolio_value = (total_shares * price) + cash_from_sales
        portfolio_history.append({
            'date': date,
            'total_invested': total_invested,
            'portfolio_value': current_portfolio_value,
            'shares': total_shares,
            'cash': cash_from_sales
        })
    
    # Final calculations
    current_price = stock_data['Close'].iloc[-1]
    current_value = total_shares * current_price
    total_return = cash_from_sales + current_value - total_invested  # Dividends already reinvested in shares
    roi_percentage = (total_return / total_invested * 100) if total_invested > 0 else 0
    
    # Calculate value of dividend shares
    dividend_shares_value = dividend_shares_bought * current_price
    
    # Find next TP target - the lowest TP zone above current price
    next_tp_level = None
    next_tp_price = None
    for level, (lower_band, upper_band, color, annotations) in enumerate(bands, 1):
        tp_zone = upper_band[-1]  # Last value in the band (current)
        if tp_zone > current_price:
            if next_tp_price is None or tp_zone < next_tp_price:
                next_tp_level = level
                next_tp_price = tp_zone
    
    return {
        'total_invested': total_invested,
        'total_shares': total_shares,
        'cash_from_sales': cash_from_sales,
        'current_value': current_value,
        'dividend_income': dividend_income,
        'dividend_shares_bought': dividend_shares_bought,
        'dividend_shares_value': dividend_shares_value,
        'total_return': total_return,
        'roi_percentage': roi_percentage,
        'next_tp_level': next_tp_level,
        'next_tp_price': next_tp_price,
        'trades': trades,
        'portfolio_history': portfolio_history,
        'daily_buy_count': daily_buy_count,
        'zone_buy_count': zone_buy_count,
        'sell_count': sell_count,
        'daily_dca_amount': daily_dca_amount,
        'position_history': position_history
    }

# Optimization function to find best polynomial degree
def optimize_degree(stock_data, total_budget, investment_years, asset_type, dividend_info, degree_range=(1, 20), step=2, use_original_method=False):
    """
    Test different polynomial degrees to find the most profitable one.
    Returns: dict with optimal_degree, best_roi, all_results
    """
    results = []
    best_roi = float('-inf')
    best_degree = degree_range[0]
    
    # Clear cache to ensure fresh calculations
    import time
    cache_buster = time.time()
    
    # Test degrees in the specified range (inclusive)
    for test_degree in range(degree_range[0], degree_range[1] + 1, step):
        try:
            # Calculate regression for this degree with unique cache key
            x_values = stock_data.index
            y_values = stock_data['Close']
            regression_values, bands, actual_degree = calculate_regression_curve(
                f"opt_{test_degree}_{cache_buster}",  # Unique cache key with timestamp
                x_values,
                y_values,
                degree=test_degree,
                num_bands=4,
                use_original=use_original_method
            )
            
            # Limit data to investment period using trading days
            trading_days_needed = int(252 * investment_years)
            if len(stock_data) > trading_days_needed:
                sim_stock_data = stock_data.iloc[-trading_days_needed:]
                sim_regression = regression_values[-trading_days_needed:]
                sim_bands = [(lb[-trading_days_needed:], ub[-trading_days_needed:], c, a) for lb, ub, c, a in bands]
            else:
                sim_stock_data = stock_data
                sim_regression = regression_values
                sim_bands = bands
            
            # Run simulation
            sim_results = run_dca_simulation(
                sim_stock_data,
                sim_bands,
                total_budget,
                investment_years,
                asset_type,
                dividend_info,
                sim_regression
            )
            
            roi = sim_results['roi_percentage']
            results.append({
                'degree': test_degree,
                'roi': roi,
                'total_return': sim_results['total_return'],
                'total_invested': sim_results['total_invested'],
                'daily_buys': sim_results['daily_buy_count'],
                'zone_buys': sim_results['zone_buy_count'],
                'sells': sim_results['sell_count']
            })
            
            if roi > best_roi:
                best_roi = roi
                best_degree = test_degree
                
        except Exception as e:
            # Skip degrees that cause errors
            continue
    
    return {
        'optimal_degree': best_degree,
        'best_roi': best_roi,
        'all_results': results
    }

def show_account_settings_page():
    """Display account settings and subscription management page"""
    st.title("⚙️ Account Settings")
    
    user_info = get_user_info(st.session_state.username)
    sub_info = get_subscription_info(st.session_state.username)
    
    if not user_info or not sub_info:
        st.error("Unable to load account information")
        return
    
    # Account Overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Username", st.session_state.username)
        st.metric("Member Since", user_info.get('created_at', 'N/A').split()[0])
    
    with col2:
        status_emoji = {"trial": "🎁", "active": "🌟", "expired": "⚠️"}
        st.metric("Subscription Status", f"{status_emoji.get(sub_info['status'], '')} {sub_info['status'].title()}")
        if sub_info['days_remaining'] > 0:
            st.metric("Days Remaining", sub_info['days_remaining'])
    
    with col3:
        st.metric("Total Logins", user_info.get('login_count', 0))
        st.metric("Total Chart Views", sub_info['total_usage'])
    
    st.markdown("---")
    
    # Subscription Details
    st.subheader("📊 Subscription Details")
    
    if sub_info['status'] == 'trial':
        st.info(f"""
        **🎁 Trial Period Active**
        
        You're currently in your 7-day trial period with full access to all features.
        
        - **Trial Ends:** {sub_info['end_date']}
        - **Days Remaining:** {sub_info['days_remaining']}
        - **Current Access:** Unlimited
        """)
    
    elif sub_info['status'] == 'active':
        st.success(f"""
        **🌟 Premium Subscription Active**
        
        You have unlimited access to all features.
        
        - **Subscription Ends:** {sub_info['end_date']}
        - **Days Remaining:** {sub_info['days_remaining']}
        - **Renewal:** Contact admin before expiration
        """)
    
    elif sub_info['status'] == 'expired':
        st.warning(f"""
        **⚠️ Free Tier Access**
        
        Your trial/subscription has expired. You're limited to 5 chart views per day.
        
        - **Today's Usage:** {sub_info['daily_usage']}/5
        - **Total Views:** {sub_info['total_usage']}
        
        Upgrade to premium for unlimited access!
        """)
        
        if st.button("⬆️ Upgrade to Premium", type="primary", use_container_width=True):
            st.info("""
            ### 💳 Upgrade to Premium
            
            Contact the Crypto On Crack admin team to upgrade your account:
            
            **Premium Benefits:**
            - ✅ Unlimited chart views
            - ✅ Full backtesting access
            - ✅ All DCA strategies
            - ✅ Priority support
            - ✅ Advanced features
            
            **Pricing:** Contact admin for current rates
            """)
    
    st.markdown("---")
    
    # Usage Statistics
    st.subheader("📈 Usage Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Today's Chart Views", sub_info['daily_usage'])
        if sub_info['status'] == 'expired':
            remaining = 5 - sub_info['daily_usage']
            st.progress(sub_info['daily_usage'] / 5, text=f"{remaining} remaining today")
    
    with col2:
        st.metric("Lifetime Chart Views", sub_info['total_usage'])
        st.caption("Total charts viewed since account creation")
    
    st.markdown("---")
    
    # Account Actions
    st.subheader("🔧 Account Actions")
    
    if st.button("🔑 Change Password"):
        st.info("Use the 'Forgot Password?' option on the login page to reset your password.")
    
    st.caption(f"**Email on file:** {user_info.get('email', 'N/A')}")
    st.caption(f"**Last login:** {user_info.get('last_login', 'N/A')}")

def show_about_help_page():
    """Display about and help information page"""
    st.title("📚 About & Help")
    
    # About Section
    st.header("About DCA Navigator")
    st.markdown("""
    The **DCA Navigator** is a visualization tool for the Dollar-Cost Averaging strategy used by 
    the **Crypto On Crack** community (17,000+ members, 4+ years proven).
    
    ### What We Provide
    
    This tool bridges the gap from concept to visual understanding, showing you:
    - 📊 **Real-time zone positioning** - Where price sits relative to historical patterns
    - 🎯 **DCA entry signals** - When to accumulate based on mathematical zones
    - 💰 **Take profit levels** - Strategic exit points based on historical resistance
    - 📈 **Backtesting simulator** - Test strategies on historical data
    - 🔮 **Bitcoin ATH forecasts** - Institutional-era projections with diminishing returns
    
    ### Our Approach
    
    **Simplified DCA** - The foundational approach our community has used for 4 years. Steady, 
    consistent accumulation below regression with standard position sizing.
    
    **Zone Multiplier DCA** - Enhanced strategy with 5x entry multipliers at key buy zones. 
    Strategic position sizing based on zone depth.
    """)
    
    st.markdown("---")
    
    # How to Use
    st.header("🎮 How to Use")
    
    tab1, tab2, tab3 = st.tabs(["Getting Started", "Understanding Signals", "Backtesting"])
    
    with tab1:
        st.markdown("""
        ### Getting Started
        
        1. **Enter a ticker symbol** (e.g., BTC-USD, AAPL, ETH-USD)
        2. **Select your DCA strategy** (Simplified or Zone Multiplier)
        3. **Choose active TP zones** (which take profit levels to use)
        4. **Adjust intensity** using the slider to match your risk tolerance
        5. **Read the market signal** for current action recommendation
        
        ### Daily Workflow
        
        - Check your assets each morning
        - Note the market signal (BUY/SELL/WAIT)
        - Execute DCA purchases when in buy zones
        - Take profits when TP zones are hit
        - Stay disciplined and unemotional
        """)
    
    with tab2:
        st.markdown("""
        ### Understanding Signals
        
        **🟢 BUY NOW** - Price is in a DCA buy zone below regression
        - Execute 5X DCA purchases (Zone Multiplier strategy)
        - Split buys if falling further into deeper zones
        - Maximum accumulation opportunity
        
        **🔴 SELL NOW** - Price is in a take profit zone above regression
        - Take profits on your position
        - 25-75% depending on momentum and zone level
        - Watch for rejection vs. push-through signals
        
        **🟡 WAIT** - Price is between zones
        - Hold current positions
        - Continue daily DCA only (no zone multipliers)
        - Monitor for zone entry signals
        
        **⚪ NEUTRAL** - Price near regression baseline
        - Market in equilibrium
        - Continue standard DCA approach
        - Wait for clear zone signals
        
        ### Zone Types
        
        **DCA Buy Zones (Green/Blue/Red/Purple bands below regression)**
        - Historical accumulation areas
        - Price trading at discount to mathematical baseline
        - Higher zone numbers = deeper discount
        
        **Take Profit Zones (Green/Blue/Red/Purple bands above regression)**
        - Historical resistance levels
        - Price trading at premium to baseline
        - Higher zone numbers = larger premium
        """)
    
    with tab3:
        st.markdown("""
        ### Using the Backtesting Simulator
        
        The simulator shows you how the strategy would have performed historically:
        
        1. **Select your asset** and timeframe
        2. **Set simulation parameters:**
           - Total budget for the period
           - Investment timeframe
           - Polynomial degree (intensity)
        3. **Run optimization** to find the best intensity level
        4. **Review results:**
           - Total return and ROI
           - Number of trades executed
           - Portfolio value over time
           - Individual trade history
        
        ### Key Metrics
        
        - **ROI %** - Return on investment percentage
        - **Total Return** - Dollar profit/loss
        - **Daily DCA Buys** - Standard accumulation trades
        - **Zone Buys** - 5X multiplier entries at key levels
        - **TP Sells** - Profit-taking exits
        - **Next TP Target** - Where to exit current positions
        """)
    
    st.markdown("---")
    
    # FAQ
    st.header("❓ Frequently Asked Questions")
    
    with st.expander("What happens when my trial ends?"):
        st.write("""
        After your 7-day trial, your account converts to free tier with 5 chart views per day. 
        The counter resets daily at midnight. Upgrade to premium for unlimited access.
        """)
    
    with st.expander("How do I upgrade to premium?"):
        st.write("""
        Contact the Crypto On Crack admin team through the community channels. Premium access 
        gives you unlimited chart views and full access to all features.
        """)
    
    with st.expander("What's the difference between Simplified and Zone Multiplier DCA?"):
        st.write("""
        **Simplified DCA** uses consistent position sizing - the approach our community has used for 4 years.
        
        **Zone Multiplier DCA** adds 5x entry multipliers when price enters specific buy zones, 
        allowing for strategic overweight positions at key levels.
        """)
    
    with st.expander("Can I change which TP zones are active?"):
        st.write("""
        Yes! Use the 'Active TP Zones' selector in the sidebar. You can enable/disable specific 
        take profit zones. Only selected zones will trigger sell signals, but all historical data 
        remains stored for analysis.
        """)
    
    with st.expander("How accurate is the backtesting?"):
        st.write("""
        Backtesting uses real historical data but past performance doesn't guarantee future results. 
        Use it to understand how the strategy behaves in different market conditions, not as a 
        prediction tool.
        """)
    
    with st.expander("What does 'intensity' mean?"):
        st.write("""
        Intensity controls the polynomial degree used for regression curve fitting. Higher intensity 
        creates tighter zones that react more to price movements. Lower intensity creates broader 
        zones that smooth out volatility. Optimize it using the backtester.
        """)
    
    st.markdown("---")
    
    # Contact
    st.header("💬 Contact & Support")
    st.info("""
    **Crypto On Crack Community**
    
    For support, questions, or premium upgrades, reach out through the official community channels.
    
    📊 **17,000+ Active Members**  
    🎯 **4+ Years Proven Strategy**  
    💎 **Community-Driven Development**
    """)

# Main app function
def app():
    # Check usage limits for non-premium users
    if st.session_state.logged_in and not st.session_state.get('usage_tracked', False):
        can_access, message = check_usage_limit(st.session_state.username)
        
        if not can_access:
            # Store limit reached status but don't stop the app
            st.session_state.chart_limit_reached = True
        else:
            # Increment usage counter
            increment_usage(st.session_state.username)
            st.session_state.usage_tracked = True
            st.session_state.chart_limit_reached = False
    
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

    # Show limit reached message if applicable (only on main chart page)
    if st.session_state.get('chart_limit_reached', False) and st.session_state.current_page == 'DCA Navigator':
        st.error("⛔ Daily limit of 3 chart views reached. Upgrade to premium for unlimited access.")
        st.info("""
        ### 🌟 Upgrade to Premium for:
        - ✅ Unlimited chart views
        - ✅ Zone Multiplier DCA strategy  
        - ✅ Full backtesting access
        - ✅ Bitcoin ATH forecasts
        - ✅ Priority support
        
        💡 **You can still access Account Settings and Help pages**
        """)
    
    st.markdown("<h1 style='text-align: center; font-size: 64px;'>📉 DCA NAVIGATOR 📈</h1>", unsafe_allow_html=True)

    st.sidebar.markdown("<h2 style='text-align: center; font-size: 40px;'>ANALYTICA Labs</h2>", unsafe_allow_html=True)
    
    # Page Navigation
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📱 Navigation")
    
    # Add Admin Panel for admin users
    nav_options = ["DCA Navigator", "Account Settings", "About & Help"]
    if st.session_state.username == "PaperChasn":
        nav_options.append("🔑 Admin Panel")
    
    # Ensure current_page is valid
    if st.session_state.current_page not in nav_options:
        st.session_state.current_page = "DCA Navigator"
    
    st.session_state.current_page = st.sidebar.radio(
        "Select Page:",
        options=nav_options,
        index=nav_options.index(st.session_state.current_page)
    )
    st.sidebar.markdown("---")
    
    # User info and logout in sidebar
    if st.session_state.logged_in:
        user_info = get_user_info(st.session_state.username)
        sub_info = get_subscription_info(st.session_state.username)
        
        st.sidebar.success(f"👤 **{st.session_state.username}**")
        
        # Display subscription status
        if sub_info:
            if sub_info['status'] == 'trial':
                st.sidebar.info(f"🎁 **Trial Active**\n{sub_info['days_remaining']} days remaining")
            elif sub_info['status'] == 'active':
                st.sidebar.success(f"🌟 **Premium Active**\n{sub_info['days_remaining']} days remaining")
            elif sub_info['status'] == 'expired':
                st.sidebar.warning(f"⚠️ **Free Access**\nUsage: {sub_info['daily_usage']}/3 today")
                if st.sidebar.button("⬆️ Upgrade to Premium", type="primary"):
                    st.sidebar.info("💳 Contact admin for premium access")
            
            # Show usage for non-premium
            if sub_info['status'] == 'expired':
                remaining = 3 - sub_info['daily_usage']
                if remaining > 0:
                    st.sidebar.metric("Charts Remaining Today", remaining)
                else:
                    st.sidebar.error("🚫 Daily chart limit reached")
        
        if st.sidebar.button("🚪 Logout", type="primary"):
            logout()
            st.rerun()
        
        st.sidebar.markdown("---")
    
    # DCA Strategy Selector
    st.sidebar.markdown("### 🎯 DCA Strategy")
    
    # Get user's subscription status
    user_sub_info = get_subscription_info(st.session_state.username)
    is_premium = user_sub_info['status'] in ['trial', 'active']
    
    if is_premium:
        st.session_state.dca_strategy = st.sidebar.radio(
            "Select your approach:",
            options=["Simplified DCA", "Zone Multiplier DCA"],
            index=1 if st.session_state.dca_strategy == "Zone Multiplier DCA" else 0,
            help="Simplified DCA: Standard position sizing (what our community has used for 4 years).\n\nZone Multiplier DCA: Enhanced with 5x entries at key buy zones."
        )
    else:
        st.session_state.dca_strategy = "Simplified DCA"
        st.sidebar.info("📊 **Free Tier**: Simplified DCA only\n\n🌟 Upgrade to Premium for Zone Multiplier DCA")
    
    if is_premium:
        if st.session_state.dca_strategy == "Simplified DCA":
            st.sidebar.info("📊 **Simplified DCA**: Consistent accumulation below regression with standard position sizing.")
        else:
            st.sidebar.success("⚡ **Zone Multiplier DCA**: Strategic 5x entries at key buy zones for optimized positioning.")
    
    st.sidebar.markdown("---")
    
    # Take Profit Zone Selector
    st.sidebar.markdown("### 🎯 Active TP Zones")
    st.session_state.active_tp_zones = st.sidebar.multiselect(
        "Select valid Take Profit zones:",
        options=[1, 2, 3, 4],
        default=st.session_state.active_tp_zones,
        help="Choose which Take Profit zones are active for your strategy. Only selected zones will trigger sell signals. Historical data for all zones remains stored."
    )
    
    if len(st.session_state.active_tp_zones) == 0:
        st.sidebar.warning("⚠️ No TP zones selected - sell signals disabled")
    elif len(st.session_state.active_tp_zones) < 4:
        st.sidebar.info(f"📊 Using TP Zones: {', '.join(map(str, sorted(st.session_state.active_tp_zones)))}")
    else:
        st.sidebar.success("✅ All TP zones active")
    
    st.sidebar.markdown("---")

    st.sidebar.markdown(
        "<h5 style='text-align: center;'>Powered by <a href='https://finance.yahoo.com' style='color: blue;'>Yahoo Finance</a></h5>",
        unsafe_allow_html=True
    )
    
    # Route to selected page
    if st.session_state.current_page == "Account Settings":
        show_account_settings_page()
        return
    elif st.session_state.current_page == "About & Help":
        show_about_help_page()
        return
    # else: continue with DCA Navigator (default)

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
        help="Enter the stock symbol you wish to look up. All valid tickers can be found on Yahoo Finance. Examples include 'AAPL' for Apple Inc. and 'TSLA' for Tesla Inc.",
        on_change=lambda: st.session_state.update({'usage_tracked': False})  # Reset tracking for new chart
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
    
    # Polynomial fitting method selector
    st.sidebar.markdown("---")
    fitting_method = st.sidebar.radio(
        "📊 Fitting Method:",
        options=["Enhanced (Current)", "Original (Simple)"],
        index=0,
        help="Enhanced: Mean-centering + scaling for numerical stability\nOriginal: Simple normalization to [0,1]"
    )
    use_original_method = (fitting_method == "Original (Simple)")
    st.sidebar.markdown("---")

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
        st.session_state.optimization_results = None  # Clear optimization when switching symbols

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
    
    st.sidebar.markdown("**Intensity**")
    
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
            help="## Effect of Intensity on Stock Price Chart\n\n"
                 "* **High Intensity:**\n"
                 "  - You will see price action events more frequently, resulting in more DCA buying opportunities with smaller price changes. This allows you to invest smaller amounts more often, potentially diversifying your investments but may also lead to higher transaction fees.\n"
                 "\n"
                 "* **Low Intensity:**\n"
                 "  - You will encounter price action events less often, resulting in fewer DCA opportunities with larger price changes. This means you'll invest larger amounts less frequently, which can simplify your investment strategy but might cause you to miss out on some opportunities.\n"
                 "\n"
                 "## Summary:\n"
                 "It's important to decide how often you want to DCA buy, how much to consistently invest each time a DCA price action event occurs, and how this choice affects your overall investment strategy. Each stock/cryptocurrency is subjective to working best with its own specific value. THERE IS NO ONE SET VALUE THAT IS THE HOLY GRAIL. It all depends on your budget and desired frequency of investing."
        )
    
    # Update temp_degree to match slider if user dragged it
    st.session_state.temp_degree = degree
    
    # Display current intensity value
    st.sidebar.markdown(f"<p style='text-align: center; font-size: 16px; margin-top: -10px;'>Current Intensity: <b>{degree}</b></p>", unsafe_allow_html=True)
    
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

    # DCA Simulator Inputs
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💰 DCA Simulator")
    
    total_budget = st.sidebar.number_input(
        "Total Investment ($)",
        min_value=100.0,
        max_value=1000000.0,
        value=10000.0,
        step=100.0,
        help="Total amount to invest over the period"
    )
    
    investment_years = st.sidebar.number_input(
        "Investment Period (Years)",
        min_value=1.0,
        max_value=30.0,
        value=5.0,
        step=0.5,
        help="How many years to DCA invest"
    )
    
    daily_dca = total_budget / (365 * investment_years)
    st.sidebar.markdown("**💰 Investment Strategy**")
    st.sidebar.info(f"""
    **Daily DCA:** ${daily_dca:.2f} *(below regression)*  
    **Zone Buy:** ${daily_dca * 5:.2f} *(5X multiplier)*
    """)
    
    # Check if user has premium access for backtesting
    backtest_sub_info = get_subscription_info(st.session_state.username)
    has_backtest_access = backtest_sub_info['status'] in ['trial', 'active']
    
    if has_backtest_access:
        run_sim = st.sidebar.button("🚀 Run Backtest")
    else:
        run_sim = False
        st.sidebar.button("🔒 Run Backtest (Premium Only)", disabled=True)
        st.sidebar.caption("⬆️ Upgrade to access backtesting")
    
    # Optimization section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 Strategy Optimizer")
    
    if has_backtest_access:
        st.sidebar.markdown("Find the most profitable intensity level for this asset.")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            opt_min = st.number_input("Min Intensity", 1, 100, 1, help="Starting intensity to test")
        with col2:
            opt_max = st.number_input("Max Intensity", 1, 100, 20, help="Ending intensity to test")
        
        opt_step = st.sidebar.selectbox(
            "Test Every N Levels",
            [1, 2, 3, 5],
            index=1,
            help="Step size for testing (smaller = more accurate but slower)"
        )
        
        run_optimization = st.sidebar.button("⚡ Optimize Intensity", help="Find the best intensity level for maximum profit")
    else:
        st.sidebar.info("🔒 **Premium Feature**\n\nOptimize intensity levels to maximize returns. Upgrade to unlock.")
        run_optimization = False
    
    # Store optimization results in session state
    if 'optimization_results' not in st.session_state:
        st.session_state.optimization_results = None
    if 'run_sim_after_apply' not in st.session_state:
        st.session_state.run_sim_after_apply = False

    if symbol:
        # Check if user hit chart limit
        if st.session_state.get('chart_limit_reached', False):
            st.warning("⚠️ Chart view limit reached for today. Please upgrade to premium or return tomorrow.")
            return
        
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
            
            # Detect asset type and get dividend info early
            asset_type = detect_asset_type(symbol)
            dividend_info = get_dividend_info(symbol) if asset_type == "Stock" else None
            
            # Handle optimization request
            if run_optimization:
                with st.spinner(f"🔍 Optimizing strategy... Testing degrees {opt_min} to {opt_max} (step {opt_step})..."):
                    st.session_state.optimization_results = optimize_degree(
                        stock_data,
                        total_budget,
                        investment_years,
                        asset_type,
                        dividend_info,
                        degree_range=(opt_min, opt_max),
                        step=opt_step,
                        use_original_method=use_original_method
                    )
            
            # Display optimization results if available
            if st.session_state.optimization_results:
                opt_results = st.session_state.optimization_results
                st.sidebar.markdown("---")
                st.sidebar.success(f"✨ **Optimal Intensity: {opt_results['optimal_degree']}**")
                st.sidebar.metric("Best ROI", f"{opt_results['best_roi']:.2f}%")
                
                if st.sidebar.button("📌 Apply Optimal Intensity"):
                    # Update the degree to the optimal one
                    st.session_state.temp_degree = opt_results['optimal_degree']
                    if symbol not in st.session_state.ticker_settings:
                        st.session_state.ticker_settings[symbol] = {}
                    st.session_state.ticker_settings[symbol]['degree'] = opt_results['optimal_degree']
                    st.session_state.run_sim_after_apply = True
                    st.rerun()
                
                with st.sidebar.expander("📊 View All Test Results"):
                    opt_df = pd.DataFrame(opt_results['all_results'])
                    opt_df = opt_df.sort_values('roi', ascending=False)
                    st.dataframe(
                        opt_df.style.format({
                            'roi': '{:.2f}%',
                            'total_return': '${:,.2f}',
                            'total_invested': '${:,.2f}'
                        }),
                        height=300
                    )

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

            # Display dividend info first (in professional format)
            if asset_type == "Stock" and dividend_info and dividend_info['pays_dividend']:
                # yfinance dividendYield: if < 0.01, treat as decimal (0.0037 = 0.37%), else already percentage (0.37 = 0.37%)
                display_yield = dividend_info['dividend_yield'] * 100 if dividend_info['dividend_yield'] < 0.01 else dividend_info['dividend_yield']
                display_payout = dividend_info['payout_ratio'] * 100 if dividend_info['payout_ratio'] < 0.01 else dividend_info['payout_ratio']
                
                div_col1, div_col2, div_col3 = st.columns(3)
                with div_col1:
                    st.metric("💰 Dividend Yield", f"{display_yield:.2f}%")
                with div_col2:
                    st.metric("📅 Annual Dividend", f"${dividend_info['dividend_rate']:.2f}")
                with div_col3:
                    st.metric("📊 Payout Ratio", f"{display_payout:.1f}%")
            
            # Analyze market position and generate signal (after price calculations)
            temp_regression_values, temp_bands, _ = calculate_regression_curve(symbol, stock_data.index, stock_data['Close'], degree, use_original=use_original_method)
            market_analysis = analyze_market_position(latest_close_price, temp_regression_values, temp_bands, stock_data)
            
            # Display trading signal with color-coded rectangle
            if market_analysis['signal_color'] == 'red':
                bg_color = '#ff4b4b'
                border_color = '#cc0000'
            elif market_analysis['signal_color'] == 'green':
                bg_color = '#00cc66'
                border_color = '#009944'
            elif market_analysis['signal_color'] == 'orange':
                bg_color = '#ffa500'
                border_color = '#cc8400'
            else:
                bg_color = '#0068c9'
                border_color = '#004c94'
            
            st.markdown(f"""
                <div style="
                    background-color: {bg_color};
                    border: 3px solid {border_color};
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    margin: 20px 0;
                ">
                    <h2 style="color: white; margin: 0; font-size: 32px;">{market_analysis['signal']}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            # Display market analysis
            st.markdown(f"**📊 Market Position:** {market_analysis['description']}")
            st.markdown(f"{market_analysis['recommendation']}")
            
            # Bitcoin ATH Forecast (only for BTC and premium users)
            if symbol in ['BTC-USD', 'BTC', 'BITCOIN']:
                # Check if user has premium access
                forecast_sub_info = get_subscription_info(st.session_state.username)
                has_forecast_access = forecast_sub_info['status'] in ['trial', 'active']
                
                if has_forecast_access:
                    btc_forecast = calculate_bitcoin_ath_forecast(latest_close_price, stock_data)
                    
                    st.markdown("---")
                    st.markdown("### 🚀 Bitcoin ATH Forecast (Institutional Era)")
                else:
                    st.markdown("---")
                    st.info("""
                    ### 🔒 Bitcoin ATH Forecast (Premium Only)
                    
                    Get data-driven projections for Bitcoin's next all-time high based on:
                    - Historical 4-year cycle patterns
                    - Diminishing returns analysis
                    - Institutional adoption impact
                    - Conservative, base, and optimistic scenarios
                    
                    ⬆️ **Upgrade to Premium** to unlock ATH forecasts
                    """)
                    btc_forecast = None
                
                if btc_forecast:  # Only show if forecast was generated
                    # Historical pattern
                    with st.expander("📚 Historical ATH Pattern", expanded=False):
                        st.markdown(f"""
                        **Retail Era (Pre-2024):**
                        - 2013 ATH: ${btc_forecast['ath_history'][0]['price']:,}
                        - 2017 ATH: ${btc_forecast['ath_history'][1]['price']:,} ({btc_forecast['ath_history'][1]['multiplier']}x gain)
                        - 2021 ATH: ${btc_forecast['ath_history'][2]['price']:,} ({btc_forecast['ath_history'][2]['multiplier']}x gain)
                        - **Diminishing Rate:** {btc_forecast['ath_history'][2]['multiplier']}x / {btc_forecast['ath_history'][1]['multiplier']}x = ~{btc_forecast['historical_retention']*100:.0f}% retention
                        
                        **🏦 Institutional Era (2024+):**
                        - Spot Bitcoin ETFs: $30B+ inflows (first year)
                        - Sovereign buyers entering market  
                        - Traditional finance integration
                        - **Expected Impact:** {btc_forecast['conservative']['retention']*100:.0f}-{btc_forecast['optimistic']['retention']*100:.0f}% gain retention
                        """)
                    
                    # Forecast metrics
                    st.markdown("**Next ATH Projections (2025-2026):**")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Conservative", 
                            f"${btc_forecast['conservative']['price']:,.0f}",
                            f"{btc_forecast['conservative']['multiplier']:.1f}x ({btc_forecast['conservative']['retention']*100:.0f}% retention)"
                        )
                    
                    with col2:
                        st.metric(
                            "Base Case", 
                            f"${btc_forecast['base']['price']:,.0f}",
                            f"{btc_forecast['base']['multiplier']:.1f}x ({btc_forecast['base']['retention']*100:.0f}% retention)"
                        )
                    
                    with col3:
                        st.metric(
                            "Optimistic", 
                            f"${btc_forecast['optimistic']['price']:,.0f}",
                            f"{btc_forecast['optimistic']['multiplier']:.1f}x ({btc_forecast['optimistic']['retention']*100:.0f}% retention)"
                        )
                    
                    # Progress indicator
                    st.progress(min(btc_forecast['progress_pct'] / 100, 1.0))
                    st.caption(f"**Progress to Base Target:** {btc_forecast['progress_pct']:.1f}% complete (${latest_close_price:,.0f} / ${btc_forecast['base']['price']:,.0f})")
                    
                    # Current cycle status
                    
                    st.warning("⚠️ **Note:** Post-2026 cycles will likely resume normal diminishing returns as institutional adoption matures.")

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

            regression_values, bands, degree = calculate_regression_curve(symbol, stock_data.index, stock_data['Close'], degree, use_original=use_original_method)
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
            
            # Display asset badge
            asset_badge = "🏦 Stock" if asset_type == "Stock" else "₿ Crypto"
            st.markdown(f"**Asset Type:** {asset_badge}")
            
            with st.expander("📊 View Last 30 Days Data", expanded=False):
                last_30_days = stock_data.tail(30).reset_index()
                last_30_days.rename(columns={'index': 'Date'}, inplace=True)
                st.dataframe(last_30_days, height=300)
            
            # DCA SIMULATOR RESULTS
            # Check if simulation should run (either button clicked or after applying optimal degree)
            should_run_sim = run_sim or st.session_state.run_sim_after_apply
            if st.session_state.run_sim_after_apply:
                st.session_state.run_sim_after_apply = False  # Reset flag after use
            
            if should_run_sim:
                st.markdown("---")
                st.markdown("## 🎯 DCA Backtest Results")
                
                with st.spinner("Running simulation..."):
                    # Limit data to investment period only using trading days (approx 252 per year)
                    trading_days_needed = int(252 * investment_years)
                    if len(stock_data) > trading_days_needed:
                        sim_stock_data = stock_data.iloc[-trading_days_needed:]
                        sim_regression = regression_values[-trading_days_needed:]
                        sim_bands = [(lb[-trading_days_needed:], ub[-trading_days_needed:], c, a) for lb, ub, c, a in bands]
                    else:
                        sim_stock_data = stock_data
                        sim_regression = regression_values
                        sim_bands = bands
                    
                    sim_results = run_dca_simulation(
                        sim_stock_data,
                        sim_bands,
                        total_budget,
                        investment_years,
                        asset_type,
                        dividend_info,
                        sim_regression
                    )
                
                # Main metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Invested", f"${sim_results['total_invested']:,.2f}")
                with col2:
                    st.metric("Current Value", f"${sim_results['current_value']:,.2f}")
                with col3:
                    st.metric("Total Return", 
                             f"${sim_results['total_return']:,.2f}",
                             f"{sim_results['roi_percentage']:+.2f}%")
                with col4:
                    st.metric("Cash Out", f"${sim_results['cash_from_sales']:,.2f}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Daily Buys", sim_results['daily_buy_count'])
                with col2:
                    st.metric("Zone Buys (5X)", sim_results['zone_buy_count'])
                with col3:
                    st.metric("Sell Signals", sim_results['sell_count'])
                with col4:
                    st.metric("Shares Held", f"{sim_results['total_shares']:.4f}")
                
                # Show dividend info if applicable
                if asset_type == "Stock" and sim_results['dividend_income'] > 0:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("💰 Dividend Cash", f"${sim_results['dividend_income']:,.2f}")
                    with col2:
                        st.metric("Dividend Shares", f"{sim_results['dividend_shares_bought']:.4f}")
                    with col3:
                        st.metric("Dividend Value", f"${sim_results['dividend_shares_value']:,.2f}")
                    with col4:
                        st.metric("Total Dividend Gain", f"${sim_results['dividend_income'] + sim_results['dividend_shares_value']:,.2f}")
                
                # Performance summary and growth chart side by side
                col_left, col_right = st.columns([1, 1])
                
                with col_left:
                    st.markdown("### 📋 Performance Summary")
                    
                    # Strategy box
                    st.markdown("**📊 Strategy Configuration**")
                    col_dca1, col_dca2 = st.columns(2)
                    with col_dca1:
                        st.metric("Daily DCA", f"${sim_results['daily_dca_amount']:.2f}", help="Executed when price is below regression")
                    with col_dca2:
                        st.metric("Zone Buy (5X)", f"${sim_results['daily_dca_amount'] * 5:.2f}", help="Executed at DCA buy zones")
                    
                    # Result box
                    roi_status = "✅ Profitable" if sim_results['roi_percentage'] > 0 else "❌ Loss"
                    result_color = "success" if sim_results['roi_percentage'] > 0 else "error"
                    st.markdown("**📈 Results**")
                    if result_color == "success":
                        st.success(f"""
                        **Status:** {roi_status}  
                        **ROI:** {sim_results['roi_percentage']:.2f}%  
                        **Net Profit:** ${sim_results['total_return']:,.2f}
                        """)
                    else:
                        st.error(f"""
                        **Status:** {roi_status}  
                        **ROI:** {sim_results['roi_percentage']:.2f}%  
                        **Net Loss:** ${sim_results['total_return']:,.2f}
                        """)
                    
                    # Trading activity
                    st.markdown("**📊 Trading Activity**")
                    trade_col1, trade_col2 = st.columns(2)
                    with trade_col1:
                        st.metric("Daily Buys", sim_results['daily_buy_count'])
                        st.metric("Zone Buys", sim_results['zone_buy_count'])
                    with trade_col2:
                        st.metric("Sells", sim_results['sell_count'])
                        st.metric("Shares Held", f"{sim_results['total_shares']:.4f}")
                    
                    # Dividend info if applicable
                    if sim_results['dividend_income'] > 0:
                        st.markdown("**💰 Dividends**")
                        st.info(f"Total Compounded: **${sim_results['dividend_income']:,.2f}**")
                    
                    # Next TP Target
                    st.markdown("**🎯 Next Take Profit Target**")
                    if sim_results['next_tp_level'] and sim_results['next_tp_price']:
                        current_price = stock_data['Close'].iloc[-1]
                        distance_to_tp = ((sim_results['next_tp_price'] - current_price) / current_price) * 100
                        st.warning(f"""
                        **TP Level {sim_results['next_tp_level']}:** ${sim_results['next_tp_price']:.2f}  
                        **Distance:** {distance_to_tp:+.2f}% from current price
                        """)
                    else:
                        st.success("✅ Price above all TP zones!")
                
                with col_right:
                    st.markdown("### 📈 Investment Growth")
                    # Create growth chart
                    if sim_results['portfolio_history']:
                        portfolio_df = pd.DataFrame(sim_results['portfolio_history'])
                        
                        growth_chart = go.Figure()
                        
                        # Portfolio value line
                        growth_chart.add_trace(go.Scatter(
                            x=portfolio_df['date'],
                            y=portfolio_df['portfolio_value'],
                            name='Portfolio Value',
                            line=dict(color='green', width=2),
                            fill='tonexty',
                            fillcolor='rgba(0, 255, 0, 0.1)'
                        ))
                        
                        # Total invested line
                        growth_chart.add_trace(go.Scatter(
                            x=portfolio_df['date'],
                            y=portfolio_df['total_invested'],
                            name='Total Invested',
                            line=dict(color='blue', width=2, dash='dash')
                        ))
                        
                        growth_chart.update_layout(
                            height=300,
                            margin=dict(l=0, r=0, t=20, b=0),
                            yaxis=dict(title="Value ($)", tickprefix="$"),
                            xaxis=dict(title=""),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(growth_chart, use_container_width=True)
                
                # DETAILED TRADE PERFORMANCE
                if sim_results['position_history']:
                    st.markdown("### 📊 Trade Performance by Entry")
                    
                    perf_data = []
                    for i, pos in enumerate(sim_results['position_history'], 1):
                        entry = {
                            'Entry #': i,
                            'Type': pos['buy_type'],
                            'Buy Date': pos['buy_date'].strftime('%Y-%m-%d'),
                            'Buy Price': f"${pos['buy_price']:.2f}",
                            'Buy Level': f"Zone {pos['buy_level']}" if pos['buy_level'] > 0 else "Daily",
                            'Shares': f"{pos['shares']:.4f}",
                            'Invested': f"${pos['amount_invested']:.2f}",
                        }
                        
                        if pos['sell_date']:
                            entry['Sell Date'] = pos['sell_date'].strftime('%Y-%m-%d')
                            entry['Sell Price'] = f"${pos['sell_price']:.2f}"
                            entry['Exit Level'] = f"⬆️ TP {pos['sell_level']}"
                            entry['Profit/Loss'] = f"${pos['profit_loss']:,.2f}"
                            entry['ROI'] = f"{pos['roi']:+.2f}%"
                            entry['Hold Days'] = pos['hold_days']
                        else:
                            entry['Sell Date'] = '👍 Holding'
                            entry['Sell Price'] = '-'
                            entry['Exit Level'] = '🔓 Open'
                            current_value = pos['shares'] * stock_data['Close'].iloc[-1]
                            unrealized = current_value - pos['amount_invested']
                            entry['Profit/Loss'] = f"${unrealized:,.2f}"
                            entry['ROI'] = f"{(unrealized/pos['amount_invested']*100):+.2f}%"
                            entry['Hold Days'] = (stock_data.index[-1] - pos['buy_date']).days
                        
                        perf_data.append(entry)
                    
                    perf_df = pd.DataFrame(perf_data)
                    
                    with st.expander("📋 View All Trades Details", expanded=False):
                        st.dataframe(perf_df, use_container_width=True, height=400)
                        
                        st.success("""
                        💡 **Reading the Table:**  
                        - Each row = one buy event at a DCA zone
                        - **Exit Level** shows which TP zone triggered the sale
                        - "👍 Holding" = position not yet sold
                        - Green ROI = profitable trade | Red ROI = loss
                        """)
                
                # Risk disclaimer
                st.warning("""
                ⚠️ **Important:** This is a backtest on historical data. Past performance does not guarantee future results.  
                Only invest what you can afford to lose. Adjust intensity level to optimize for your risk tolerance.
                """)
            
            # Add manual refresh button
            if st.sidebar.button("🔄 Refresh Data"):
                st.cache_data.clear()
                st.rerun()

if __name__ == "__main__":
    # Initialize session state
    initialize_session_state()
    
    # Check if user is logged in
    if not st.session_state.logged_in:
        show_login_page()
    elif not st.session_state.intro_seen:
        show_intro_page()
    else:
        app()
