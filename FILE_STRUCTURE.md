# DCA Navigator File Structure Guide

## Main Application Files

### **streamlit_app_with_login.py** ✅ PRODUCTION VERSION
**This is your complete app with login integrated**
- Full DCA Navigator functionality
- Secure login/signup system
- Password reset feature
- User authentication required
- All latest features and improvements
- **USE THIS FILE FOR DEPLOYMENT**

### **streamlit_app_simulator.py** ✅ DEVELOPMENT VERSION
**Same as streamlit_app_with_login.py - both have login integrated**
- Originally your working file
- Currently identical to streamlit_app_with_login.py
- Has all login features integrated
- Keep for development/testing

### **streamlit_app.py**
**Basic version without simulator features**
- Simple stock charting
- No backtesting
- No login system
- Good reference for basic functionality

### **login.py** 
**Standalone login system for testing**
- Test login features independently
- User management dashboard
- Admin panel
- Not needed for main app (login is integrated)

---

## What Each File Contains

| File | Login? | Backtesting? | BTC Forecast? | Market Analysis? | Use Case |
|------|--------|--------------|---------------|------------------|----------|
| **streamlit_app_with_login.py** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **Production** |
| **streamlit_app_simulator.py** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **Development** |
| streamlit_app.py | ❌ No | ❌ No | ❌ No | ❌ No | Reference |
| login.py | ✅ Yes | ❌ No | ❌ No | ❌ No | Testing Only |

---

## To Run the App

### With Login (Production):
```bash
streamlit run streamlit_app_with_login.py
```

### Development Version:
```bash
streamlit run streamlit_app_simulator.py
```

### Test Login System Only:
```bash
streamlit run login.py
```

---

## Latest Features (in production files)

✅ **Authentication System**
- Secure login/signup
- Password hashing (SHA256)
- Password reset with email verification
- Session management

✅ **Password Requirements**
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 number
- At least 1 special character

✅ **DCA Strategy**
- Daily DCA when below regression
- 5X zone buys at support levels
- Take profit zones for exits
- Market position analysis

✅ **Bitcoin Forecasting**
- ATH predictions with diminishing returns
- Institutional era adjustments
- Conservative/Base/Optimistic scenarios

✅ **Market Intelligence**
- Price momentum analysis (5-day)
- Zone progression tracking
- Rejection/continuation signals
- Daily action recommendations

✅ **Professional UI**
- Color-coded signals
- Performance metrics
- Trade history dataframes
- Portfolio growth charts

---

## User Database

- **users_db.json** - Stores all user accounts
- Created automatically on first signup
- Contains: username, password hash, email, access level, login history

---

## Backup Strategy

Both `streamlit_app_with_login.py` and `streamlit_app_simulator.py` are production-ready with login.

You can safely use either file - they are currently identical.

---

## Recommended Workflow

1. **Development**: Work in `streamlit_app_simulator.py`
2. **Testing**: Test changes thoroughly
3. **Production**: Deploy `streamlit_app_with_login.py`
4. **Backup**: Keep both files synced manually when making changes

---

Last Updated: December 12, 2025
