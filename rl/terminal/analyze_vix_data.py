#!/usr/bin/env python3
"""Analyze VIX data to understand chart requirements"""

import yfinance as yf
from datetime import datetime
import numpy as np

# Get VIX data
vix = yf.Ticker("^VIX")
hist = vix.history(period="3d", interval="15m")

print("=== VIX DATA ANALYSIS ===")
print(f"Total data points: {len(hist)}")
print(f"Date range: {hist.index[0]} to {hist.index[-1]}")
print()

# Show data density
print("=== DATA DENSITY FOR CHART ===")
chart_width = 23  # Available columns for dots
print(f"Chart width: {chart_width} columns")
print(f"Data points: {len(hist)}")
print(f"Points per column: {len(hist) / chart_width:.1f}")
print()

# Analyze the data range
vix_values = hist['Close'].values
print("=== VIX VALUE RANGE ===")
print(f"Minimum: {vix_values.min():.2f}")
print(f"Maximum: {vix_values.max():.2f}")
print(f"Current: {vix_values[-1]:.2f}")
print()

# Show how data would be compressed into chart
print("=== CHART COMPRESSION EXAMPLE ===")
print("Compressing data into 23 columns:")
compression_ratio = len(vix_values) / chart_width

for col in range(5):  # Show first 5 columns as example
    start_idx = int(col * compression_ratio)
    end_idx = int((col + 1) * compression_ratio)
    col_values = vix_values[start_idx:end_idx]
    avg_val = np.mean(col_values)
    print(f"Column {col}: {len(col_values)} points, avg={avg_val:.2f}, range={col_values.min():.2f}-{col_values.max():.2f}")

print("...")
print()

# Show recent trend
print("=== RECENT VIX TREND (Last 24 hours) ===")
recent_data = hist.tail(96)  # ~24 hours of 15-min data
print("Time (ET)        | VIX")
print("-----------------|------")
for i in range(0, len(recent_data), 4):  # Show every hour
    timestamp = recent_data.index[i]
    et_time = timestamp.tz_convert('US/Eastern')
    vix_val = recent_data.iloc[i]['Close']
    print(f"{et_time.strftime('%m-%d %H:%M')} | {vix_val:.2f}")

print()
print("CONCLUSION: With 156 data points compressed into 23 columns,")
print("each column represents ~6-7 data points. Using dots will")
print("create a continuous line showing the VIX trend clearly!")