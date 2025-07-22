#!/usr/bin/env python3
"""
Compare SPY 5-minute data with options data for December 7, 2022
"""
import yfinance as yf
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

# Get SPY 5-minute data
print("Fetching SPY 5-minute data for December 7, 2022...")
spy = yf.Ticker('SPY')

# Need to fetch from Dec 6 4pm to Dec 7 4pm to get all intraday data
spy_data = spy.history(
    start='2022-12-06', 
    end='2022-12-08',
    interval='5m'
)

# Filter for December 7th trading hours only
spy_dec7 = spy_data[
    (spy_data.index.date == datetime(2022, 12, 7).date()) & 
    (spy_data.index.time >= datetime.strptime('09:30', '%H:%M').time()) &
    (spy_data.index.time <= datetime.strptime('16:00', '%H:%M').time())
]

print(f"\nSPY data points found: {len(spy_dec7)}")

# Get options data from database
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        o.datetime,
        o.open as opt_open,
        o.high as opt_high,
        o.low as opt_low,
        o.close as opt_close,
        o.volume as opt_volume,
        g.delta,
        g.gamma,
        g.theta,
        i.implied_volatility
    FROM theta.options_ohlc o
    JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
    LEFT JOIN theta.options_greeks g ON o.contract_id = g.contract_id AND o.datetime = g.datetime
    LEFT JOIN theta.options_iv i ON o.contract_id = i.contract_id AND o.datetime = i.datetime
    WHERE oc.expiration = '2022-12-07'
    AND oc.strike = 380
    AND oc.option_type = 'C'
    ORDER BY o.datetime
""")

options_data = cursor.fetchall()
cursor.close()
conn.close()

# Create DataFrame for options
options_df = pd.DataFrame(options_data, columns=[
    'datetime', 'opt_open', 'opt_high', 'opt_low', 'opt_close', 
    'opt_volume', 'delta', 'gamma', 'theta', 'iv'
])
options_df['datetime'] = pd.to_datetime(options_df['datetime'])
options_df.set_index('datetime', inplace=True)

# Create complete 5-minute time series for the day
start_time = datetime(2022, 12, 7, 9, 30)
end_time = datetime(2022, 12, 7, 16, 0)
full_index = pd.date_range(start=start_time, end=end_time, freq='5min')

# Create comparison DataFrame
comparison = pd.DataFrame(index=full_index)
comparison.index.name = 'Time'

# Add SPY data
for idx in comparison.index:
    # Find closest SPY data point
    if len(spy_dec7) > 0:
        time_diffs = abs(spy_dec7.index - idx)
        if min(time_diffs) <= timedelta(minutes=2.5):  # Within 2.5 minutes
            closest_idx = time_diffs.argmin()
            comparison.loc[idx, 'SPY_Open'] = spy_dec7.iloc[closest_idx]['Open']
            comparison.loc[idx, 'SPY_High'] = spy_dec7.iloc[closest_idx]['High']
            comparison.loc[idx, 'SPY_Low'] = spy_dec7.iloc[closest_idx]['Low']
            comparison.loc[idx, 'SPY_Close'] = spy_dec7.iloc[closest_idx]['Close']
            comparison.loc[idx, 'SPY_Volume'] = spy_dec7.iloc[closest_idx]['Volume']

# Add options data
for idx in comparison.index:
    if idx in options_df.index:
        comparison.loc[idx, 'Opt_Open'] = options_df.loc[idx, 'opt_open']
        comparison.loc[idx, 'Opt_Close'] = options_df.loc[idx, 'opt_close']
        comparison.loc[idx, 'Opt_Volume'] = options_df.loc[idx, 'opt_volume']
        comparison.loc[idx, 'Delta'] = options_df.loc[idx, 'delta']
        comparison.loc[idx, 'IV'] = options_df.loc[idx, 'iv']

# Calculate intrinsic value
comparison['Intrinsic'] = comparison['SPY_Close'] - 380
comparison['Intrinsic'] = comparison['Intrinsic'].apply(lambda x: max(0, x) if pd.notna(x) else None)

# Format for display
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)

print("\n" + "="*120)
print("DECEMBER 7, 2022 - SPY vs $380 CALL OPTION (5-minute bars)")
print("="*120)
print("\nNote: Empty option fields indicate no trades during that 5-minute period")
print("-"*120)

# Print header
print(f"{'Time':<11} | {'SPY Close':>9} | {'Opt Open':>8} | {'Opt Close':>9} | {'Opt Vol':>7} | {'Delta':>6} | {'IV':>6} | {'Intrinsic':>9} | {'Status'}")
print("-"*120)

# Print each row
for idx, row in comparison.iterrows():
    time_str = idx.strftime('%H:%M')
    spy_close = f"{row['SPY_Close']:.2f}" if pd.notna(row['SPY_Close']) else "---"
    opt_open = f"{row['Opt_Open']:.2f}" if pd.notna(row['Opt_Open']) else ""
    opt_close = f"{row['Opt_Close']:.2f}" if pd.notna(row['Opt_Close']) else ""
    opt_vol = f"{int(row['Opt_Volume'])}" if pd.notna(row['Opt_Volume']) else ""
    delta = f"{row['Delta']:.3f}" if pd.notna(row['Delta']) else ""
    iv = f"{row['IV']:.2f}" if pd.notna(row['IV']) else ""
    intrinsic = f"{row['Intrinsic']:.2f}" if pd.notna(row['Intrinsic']) else ""
    
    # Status
    if pd.notna(row['Opt_Close']):
        status = "TRADED"
    elif pd.notna(row['SPY_Close']):
        status = "No option trades"
    else:
        status = "Missing data"
    
    print(f"{time_str:<11} | {spy_close:>9} | {opt_open:>8} | {opt_close:>9} | {opt_vol:>7} | {delta:>6} | {iv:>6} | {intrinsic:>9} | {status}")

# Summary statistics
print("\n" + "="*120)
print("SUMMARY STATISTICS")
print("="*120)

total_periods = len(comparison)
spy_periods = comparison['SPY_Close'].notna().sum()
option_periods = comparison['Opt_Close'].notna().sum()

print(f"Total 5-minute periods: {total_periods}")
print(f"Periods with SPY data: {spy_periods} ({spy_periods/total_periods*100:.1f}%)")
print(f"Periods with option trades: {option_periods} ({option_periods/total_periods*100:.1f}%)")
print(f"\nSPY range: ${comparison['SPY_Low'].min():.2f} - ${comparison['SPY_High'].max():.2f}")
print(f"Option price range: ${options_df['opt_low'].min():.2f} - ${options_df['opt_high'].max():.2f}")
print(f"Total option volume: {options_df['opt_volume'].sum():,}")
print(f"Average IV: {options_df['iv'].mean():.2%}" if options_df['iv'].notna().any() else "Average IV: N/A")