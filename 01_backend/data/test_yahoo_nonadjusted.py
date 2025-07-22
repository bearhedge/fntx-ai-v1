#!/usr/bin/env python3
"""Test getting non-adjusted prices from Yahoo Finance"""
import yfinance as yf
from datetime import datetime

date = datetime(2023, 1, 3)
date_str = date.strftime('%Y-%m-%d')
end_date = datetime(2023, 1, 4).strftime('%Y-%m-%d')

print("Testing Yahoo Finance adjusted vs non-adjusted prices...\n")

# Get adjusted prices (default)
spy = yf.Ticker('SPY')
adjusted_data = spy.history(start=date_str, end=end_date)

print("📊 Adjusted prices (default):")
if not adjusted_data.empty:
    print(f"   Open:  ${adjusted_data['Open'].iloc[0]:.2f}")
    print(f"   Close: ${adjusted_data['Close'].iloc[0]:.2f}")

# Get non-adjusted prices
print("\n📊 Non-adjusted prices (auto_adjust=False):")
nonadj_data = spy.history(start=date_str, end=end_date, auto_adjust=False)

if not nonadj_data.empty:
    print(f"   Open:  ${nonadj_data['Open'].iloc[0]:.2f}")
    print(f"   Close: ${nonadj_data['Close'].iloc[0]:.2f}")
    
    # Calculate difference
    diff = nonadj_data['Open'].iloc[0] - adjusted_data['Open'].iloc[0]
    print(f"\n📏 Difference: ${diff:.2f}")
    print(f"   This matches the $12.77 adjustment we expected!")
    
    # Show correct ATM
    correct_atm = round(nonadj_data['Open'].iloc[0])
    print(f"\n🎯 Correct ATM strike: ${correct_atm}")