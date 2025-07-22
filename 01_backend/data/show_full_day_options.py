#!/usr/bin/env python3
"""
Show full day of options data with gaps highlighted
"""
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

# Get options data from database
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# First, get SPY open price for context
cursor.execute("""
    SELECT open_price 
    FROM extract_spy_data 
    WHERE date = '2022-12-07'
""")
spy_open = cursor.fetchone()[0]

cursor.execute("""
    SELECT 
        o.datetime,
        o.open as opt_open,
        o.high as opt_high,
        o.low as opt_low,
        o.close as opt_close,
        o.volume as opt_volume,
        o.trade_count,
        g.delta,
        g.gamma,
        g.theta,
        g.vega,
        g.rho,
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
    'opt_volume', 'trade_count', 'delta', 'gamma', 'theta', 'vega', 'rho', 'iv'
])
options_df['datetime'] = pd.to_datetime(options_df['datetime'])
options_df.set_index('datetime', inplace=True)

# Create complete 5-minute time series for the day
start_time = datetime(2022, 12, 7, 9, 30)
end_time = datetime(2022, 12, 7, 16, 0)
full_index = pd.date_range(start=start_time, end=end_time, freq='5min')

print("="*130)
print(f"DECEMBER 7, 2022 - COMPLETE DAY DATA FOR $380 CALL OPTION")
print(f"SPY Opening Price: ${spy_open:.2f} | Strike: $380 | Moneyness: ${spy_open - 380:.2f} below strike")
print("="*130)
print("\n📊 SHOWING ALL 78 POSSIBLE 5-MINUTE INTERVALS (9:30 AM - 4:00 PM)")
print("-"*130)

# Header
print(f"{'Time':<8} | {'Open':>7} | {'High':>7} | {'Low':>7} | {'Close':>7} | {'Volume':>6} | {'Trades':>6} | {'Delta':>6} | {'Gamma':>7} | {'Theta':>7} | {'IV':>5} | Status")
print("-"*130)

traded_count = 0
gap_start = None
gaps = []

for time_slot in full_index:
    time_str = time_slot.strftime('%H:%M')
    
    if time_slot in options_df.index:
        row = options_df.loc[time_slot]
        traded_count += 1
        
        # If we were in a gap, record it
        if gap_start:
            gap_duration = (time_slot - gap_start).seconds // 60
            gaps.append((gap_start, time_slot, gap_duration))
            gap_start = None
        
        # Format values
        open_str = f"${row['opt_open']:.2f}" if pd.notna(row['opt_open']) else "---"
        high_str = f"${row['opt_high']:.2f}" if pd.notna(row['opt_high']) else "---"
        low_str = f"${row['opt_low']:.2f}" if pd.notna(row['opt_low']) else "---"
        close_str = f"${row['opt_close']:.2f}" if pd.notna(row['opt_close']) else "---"
        vol_str = f"{int(row['opt_volume'])}" if pd.notna(row['opt_volume']) else "0"
        trades_str = f"{int(row['trade_count'])}" if pd.notna(row['trade_count']) else "0"
        delta_str = f"{row['delta']:.3f}" if pd.notna(row['delta']) else "---"
        gamma_str = f"{row['gamma']:.4f}" if pd.notna(row['gamma']) else "---"
        theta_str = f"{row['theta']:.3f}" if pd.notna(row['theta']) else "---"
        iv_str = f"{row['iv']:.1%}" if pd.notna(row['iv']) else "---"
        
        print(f"{time_str:<8} | {open_str:>7} | {high_str:>7} | {low_str:>7} | {close_str:>7} | {vol_str:>6} | {trades_str:>6} | {delta_str:>6} | {gamma_str:>7} | {theta_str:>7} | {iv_str:>5} | ✓ TRADED")
    else:
        # Mark gap start
        if gap_start is None:
            gap_start = time_slot
        
        print(f"{time_str:<8} | {'---':>7} | {'---':>7} | {'---':>7} | {'---':>7} | {'---':>6} | {'---':>6} | {'---':>6} | {'---':>7} | {'---':>7} | {'---':>5} | ⚪ No trades")

# Handle final gap if exists
if gap_start:
    gap_duration = (end_time - gap_start).seconds // 60
    gaps.append((gap_start, end_time, gap_duration))

print("\n" + "="*130)
print("DATA COVERAGE ANALYSIS")
print("="*130)

print(f"\n📈 Trading Activity:")
print(f"   - Total 5-minute periods: 78")
print(f"   - Periods with trades: {traded_count} ({traded_count/78*100:.1f}%)")
print(f"   - Periods without trades: {78-traded_count} ({(78-traded_count)/78*100:.1f}%)")

print(f"\n⏱️  Longest Gaps Without Trading:")
if gaps:
    sorted_gaps = sorted(gaps, key=lambda x: x[2], reverse=True)
    for i, (start, end, duration) in enumerate(sorted_gaps[:5]):
        print(f"   {i+1}. {start.strftime('%H:%M')} - {end.strftime('%H:%M')}: {duration} minutes")

# Show trading concentration by hour
print(f"\n📊 Trading Concentration by Hour:")
hourly_trades = {}
for time_slot in full_index:
    hour = time_slot.hour
    if hour not in hourly_trades:
        hourly_trades[hour] = {'total': 0, 'traded': 0}
    hourly_trades[hour]['total'] += 1
    if time_slot in options_df.index:
        hourly_trades[hour]['traded'] += 1

for hour in sorted(hourly_trades.keys()):
    data = hourly_trades[hour]
    pct = data['traded'] / data['total'] * 100 if data['total'] > 0 else 0
    bar = '█' * int(pct / 10)
    print(f"   {hour:02d}:00 - {hour:02d}:59: {bar:<10} {data['traded']}/{data['total']} periods ({pct:.0f}%)")

# Price movement summary
print(f"\n💰 Price Movement Summary:")
print(f"   - Opening price: ${options_df['opt_open'].iloc[0]:.2f}")
print(f"   - Closing price: ${options_df['opt_close'].iloc[-1]:.2f}")
print(f"   - Day's range: ${options_df['opt_low'].min():.2f} - ${options_df['opt_high'].max():.2f}")
print(f"   - Total volume: {options_df['opt_volume'].sum():,} contracts")
print(f"   - Average trade size: {options_df['opt_volume'].sum() / options_df['trade_count'].sum():.1f} contracts")

# Greeks summary
print(f"\n🔢 Greeks Summary:")
print(f"   - Delta range: {options_df['delta'].min():.3f} to {options_df['delta'].max():.3f}")
print(f"   - Average IV: {options_df['iv'].mean():.1%}")
print(f"   - IV range: {options_df['iv'].min():.1%} to {options_df['iv'].max():.1%}")