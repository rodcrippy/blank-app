"""
Login and User Authentication System for DCA Navigator
Separate module for testing before integration with main app
"""

import streamlit as st
import json
import hashlib
import os
from datetime import datetime
import pandas as pd

# User database file
USER_DB_FILE = "users_db.json"

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

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
    
    users[username] = {
        'password': hash_password(password),
        'email': email,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_login': None,
        'access_level': 'standard',  # 'standard' or 'premium'
        'login_count': 0
    }
    
    save_users(users)
    return True, "Account created successfully"

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

def update_user_access(username, access_level):
    """Update user access level (admin function)"""
    users = load_users()
    if username in users:
        users[username]['access_level'] = access_level
        save_users(users)
        return True
    return False

def delete_user(username):
    """Delete a user account (admin function)"""
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        return True
    return False

def initialize_session_state():
    """Initialize session state variables"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'access_level' not in st.session_state:
        st.session_state.access_level = None

def logout():
    """Logout current user"""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.access_level = None

def login_page():
    """Display login page"""
    st.title("🔐 DCA Navigator - Login")
    
    tab1, tab2, tab3 = st.tabs(["Login", "Sign Up", "Admin"])
    
    # Login Tab
    with tab1:
        st.markdown("### Welcome Back!")
        
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login")
            
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
    
    # Sign Up Tab
    with tab2:
        st.markdown("### Create New Account")
        
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="signup_username")
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
            submit_signup = st.form_submit_button("Create Account")
            
            if submit_signup:
                if not new_username or not new_email or not new_password:
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    success, message = create_user(new_username, new_password, new_email)
                    if success:
                        st.success(message)
                        st.info("You can now login with your credentials")
                    else:
                        st.error(message)
    
    # Admin Tab
    with tab3:
        st.markdown("### Admin Panel")
        st.warning("⚠️ Admin access required")
        
        admin_password = st.text_input("Admin Password", type="password", key="admin_pass")
        
        # Simple admin password (you should change this!)
        if admin_password == "admin123":
            st.success("✅ Admin access granted")
            
            users = load_users()
            
            if users:
                st.markdown("#### User Management")
                
                # Display users table
                user_data = []
                for username, info in users.items():
                    user_data.append({
                        'Username': username,
                        'Email': info['email'],
                        'Access Level': info['access_level'],
                        'Created': info['created_at'],
                        'Last Login': info['last_login'] or 'Never',
                        'Login Count': info.get('login_count', 0)
                    })
                
                df = pd.DataFrame(user_data)
                st.dataframe(df, use_container_width=True)
                
                # User management actions
                st.markdown("#### Modify User Access")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    selected_user = st.selectbox("Select User", list(users.keys()))
                
                with col2:
                    new_access = st.selectbox("Access Level", ["standard", "premium"])
                
                with col3:
                    if st.button("Update Access"):
                        if update_user_access(selected_user, new_access):
                            st.success(f"Updated {selected_user} to {new_access}")
                            st.rerun()
                
                # Delete user
                st.markdown("#### Delete User")
                col1, col2 = st.columns([3, 1])
                with col1:
                    delete_username = st.selectbox("Select User to Delete", list(users.keys()), key="delete_user")
                with col2:
                    if st.button("Delete User", type="primary"):
                        if delete_user(delete_username):
                            st.success(f"Deleted user: {delete_username}")
                            st.rerun()
            else:
                st.info("No users registered yet")
        elif admin_password:
            st.error("Incorrect admin password")

def main():
    """Main function to test login system"""
    st.set_page_config(page_title="DCA Navigator Login", page_icon="🔐", layout="wide")
    
    initialize_session_state()
    
    # Check if user is logged in
    if st.session_state.logged_in:
        # Display logged-in user dashboard
        st.title("🎯 DCA Navigator - Dashboard")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.markdown(f"### Welcome, {st.session_state.username}!")
        
        with col2:
            user_info = get_user_info(st.session_state.username)
            if user_info['access_level'] == 'premium':
                st.success("🌟 Premium Access")
            else:
                st.info("📊 Standard Access")
        
        with col3:
            if st.button("Logout"):
                logout()
                st.rerun()
        
        st.markdown("---")
        
        # Display user information
        user_info = get_user_info(st.session_state.username)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Account Created", user_info['created_at'].split()[0])
        
        with col2:
            st.metric("Total Logins", user_info.get('login_count', 0))
        
        with col3:
            st.metric("Last Login", user_info['last_login'].split()[0] if user_info['last_login'] else 'N/A')
        
        with col4:
            st.metric("Access Level", user_info['access_level'].upper())
        
        st.markdown("---")
        
        # Feature access based on user level
        st.markdown("### 🚀 Available Features")
        
        if user_info['access_level'] == 'premium':
            st.success("✅ Full access to all DCA Navigator features:")
            st.markdown("""
            - ✅ Advanced backtesting with all stocks/crypto
            - ✅ Custom intensity optimizer
            - ✅ Portfolio performance tracking
            - ✅ Bitcoin ATH forecasting
            - ✅ Market position analysis
            - ✅ Unlimited simulations
            - ✅ Export trade history
            - ✅ Priority support
            """)
        else:
            st.info("📊 Standard access features:")
            st.markdown("""
            - ✅ Basic backtesting (limited symbols)
            - ✅ Standard DCA strategies
            - ✅ Performance summary
            - ⚠️ Limited to 5 simulations per day
            
            **Upgrade to Premium for:**
            - 🔒 Advanced optimizer
            - 🔒 Bitcoin ATH forecasting
            - 🔒 Unlimited simulations
            - 🔒 Priority support
            """)
            
            if st.button("🌟 Upgrade to Premium", type="primary"):
                st.info("Contact admin to upgrade your account")
        
        st.markdown("---")
        st.markdown("### 📈 Ready to use DCA Navigator?")
        st.info("Your login session is active. You can now integrate this with the main app.")
        
    else:
        # Show login page
        login_page()

if __name__ == "__main__":
    main()
