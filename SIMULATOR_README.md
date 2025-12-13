# DCA Navigator Simulator

## Files
- `streamlit_app.py` - Original DCA Navigator app (preserved as working version)
- `streamlit_app_simulator.py` - NEW Simulator version with backtesting capabilities

## How to Run the Simulator
```bash
streamlit run streamlit_app_simulator.py
```

## New Features in Simulator

### 1. **Asset Type Detection**
- Automatically identifies if the asset is a Stock (🏦) or Cryptocurrency (₿)
- Prevents errors from attempting to get dividend data on crypto assets

### 2. **Dividend Information** (Stocks Only)
- Displays dividend yield, annual rate, and payout ratio
- Includes dividend income in simulation results
- Calculates quarterly dividends for long-term holders

### 3. **DCA Simulator Inputs**
- **Total Investment Budget**: Amount you plan to invest ($100 - $1,000,000)
- **Investment Period**: Time horizon in years (1 - 30 years)
- Automatically calculates:
  - Daily DCA amount = Budget ÷ (365 × Years)
  - Aggressive buy amount = Daily DCA × 5

### 4. **Entry & Exit Signals**

#### Entry Signal (5X Aggressive Buy)
- **Yesterday**: Price touched/crossed buy zone (HIGH > zone AND LOW ≤ zone)
- **Today**: Price bounced and stayed above zone (LOW > zone AND HIGH > zone)
- **Action**: Buy 5X the daily DCA amount

#### Exit Signal (Full Position Sale)
- **Yesterday**: Price touched/crossed TP zone (LOW < zone AND HIGH ≥ zone)
- **Today**: Price stayed below zone (HIGH < zone AND LOW < zone)
- **Action**: Sell 100% of position at TP level

### 5. **Simulation Results**
- Total invested amount
- Current portfolio value
- Total return (profit/loss)
- ROI percentage
- Number of buy/sell signals
- Current shares held
- Dividend income (for stocks)
- Cash from sales

### 6. **Trade History**
- Complete log of all buy and sell transactions
- Date, type, level, price, amount, shares
- Exportable to analyze strategy performance

### 7. **Beginner-Friendly Interface**
- Clear explanations of all metrics
- Color-coded profit/loss indicators
- Simple tips for understanding results
- No complex jargon

## Strategy Overview

### Conservative Approach (Base)
- Equal 25% allocation at each of 4 buy zones
- Balanced risk distribution
- Good for steady accumulation

### Aggressive Approach (Implemented)
- Base allocation: Daily DCA amount
- 5X multiplier when signal triggers
- Maximizes gains on price bounces
- Takes full profits at TP zones

## Best Practices

1. **Polynomial Degree Settings**:
   - Degree 2-5: Long-term trends, fewer signals
   - Degree 10-20: Medium-term swings
   - Degree 25-40: Short-term action, more signals

2. **Budget Planning**:
   - Only invest what you can afford to lose
   - Spread investments over longer periods for stability
   - Test different time horizons in simulator

3. **Asset Selection**:
   - Stocks: Consider dividend yield for extra income
   - Crypto: Higher volatility = more signals
   - Blue chips: More stable, fewer signals

## Tips for New Investors

✅ **Green ROI** = Your strategy made money!  
❌ **Red ROI** = Strategy lost money, try adjusting settings

- Start with lower polynomial degrees (2-5) for simplicity
- Test multiple time periods (3, 5, 10 years)
- Review trade history to understand buy/sell patterns
- Adjust strategy based on your risk tolerance
- Remember: Past performance doesn't guarantee future results

## Technical Notes

- Simulation runs on historical data only
- 24-hour cache for zone stability
- Dividend calculations are approximate (quarterly)
- Signal detection uses daily candles (OHLC data)
- All percentages and metrics update in real-time
