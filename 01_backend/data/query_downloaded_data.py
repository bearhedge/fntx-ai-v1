#!/usr/bin/env python3
"""
Query and display downloaded 0DTE data for testing
"""
import sys
import psycopg2
import pandas as pd
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def query_downloaded_data(date: str = "2023-01-03"):
    """Query and display downloaded data for a specific date"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    print(f"="*80)
    print(f"DOWNLOADED DATA SUMMARY FOR {date}")
    print(f"="*80)
    
    # 1. Contract Summary
    query = """
        SELECT 
            COUNT(*) as total_contracts,
            COUNT(CASE WHEN option_type = 'C' THEN 1 END) as calls,
            COUNT(CASE WHEN option_type = 'P' THEN 1 END) as puts,
            MIN(strike) as min_strike,
            MAX(strike) as max_strike
        FROM theta.options_contracts 
        WHERE expiration = %s AND symbol = 'SPY'
    """
    
    df = pd.read_sql(query, conn, params=[date])
    print(f"\n📊 CONTRACT SUMMARY:")
    print(f"   Total contracts: {df.iloc[0]['total_contracts']}")
    print(f"   Calls: {df.iloc[0]['calls']}")  
    print(f"   Puts: {df.iloc[0]['puts']}")
    print(f"   Strike range: ${df.iloc[0]['min_strike']} - ${df.iloc[0]['max_strike']}")
    
    # 2. Data Volume by Type
    query = """
        SELECT 
            'OHLC' as data_type,
            COUNT(*) as total_bars,
            COUNT(DISTINCT o.contract_id) as contracts_with_data,
            MIN(o.datetime) as first_bar,
            MAX(o.datetime) as last_bar
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
        WHERE c.expiration = %s AND c.symbol = 'SPY'
        
        UNION ALL
        
        SELECT 
            'Greeks' as data_type,
            COUNT(*) as total_bars,
            COUNT(DISTINCT g.contract_id) as contracts_with_data,
            MIN(g.datetime) as first_bar,
            MAX(g.datetime) as last_bar
        FROM theta.options_greeks g
        JOIN theta.options_contracts c ON g.contract_id = c.contract_id
        WHERE c.expiration = %s AND c.symbol = 'SPY'
        
        UNION ALL
        
        SELECT 
            'IV' as data_type,
            COUNT(*) as total_bars,
            COUNT(DISTINCT i.contract_id) as contracts_with_data,
            MIN(i.datetime) as first_bar,
            MAX(i.datetime) as last_bar
        FROM theta.options_iv i
        JOIN theta.options_contracts c ON i.contract_id = c.contract_id
        WHERE c.expiration = %s AND c.symbol = 'SPY'
    """
    
    df = pd.read_sql(query, conn, params=[date, date, date])
    print(f"\n📈 DATA VOLUME:")
    for _, row in df.iterrows():
        print(f"   {row['data_type']:<8}: {row['total_bars']:,} bars across {row['contracts_with_data']} contracts")
        print(f"             Time range: {row['first_bar']} to {row['last_bar']}")
    
    # 3. Sample Option Data (ATM Call)
    query = """
        SELECT 
            o.datetime,
            o.open, o.high, o.low, o.close, o.volume,
            g.delta, g.gamma, g.theta, g.vega,
            i.implied_volatility
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
        LEFT JOIN theta.options_greeks g ON o.contract_id = g.contract_id AND o.datetime = g.datetime
        LEFT JOIN theta.options_iv i ON o.contract_id = i.contract_id AND o.datetime = i.datetime
        WHERE c.expiration = %s AND c.symbol = 'SPY' AND c.strike = 372 AND c.option_type = 'C'
        ORDER BY o.datetime
        LIMIT 10
    """
    
    df = pd.read_sql(query, conn, params=[date])
    if not df.empty:
        print(f"\n💰 SAMPLE DATA ($372 Call - First 10 bars):")
        print(f"{'Time':<8} {'Open':<7} {'High':<7} {'Low':<7} {'Close':<7} {'Vol':<5} {'Delta':<6} {'IV':<6}")
        print("-" * 65)
        for _, row in df.iterrows():
            time_str = row['datetime'].strftime('%H:%M')
            delta_str = f"{row['delta']:.3f}" if pd.notna(row['delta']) else "---"
            iv_str = f"{row['implied_volatility']:.1%}" if pd.notna(row['implied_volatility']) else "---"
            print(f"{time_str:<8} ${row['open']:<6.2f} ${row['high']:<6.2f} ${row['low']:<6.2f} ${row['close']:<6.2f} {row['volume']:<5.0f} {delta_str:<6} {iv_str:<6}")
    
    # 4. Strike Distribution
    query = """
        SELECT 
            c.strike,
            c.option_type,
            COUNT(o.datetime) as ohlc_bars,
            MIN(o.open) as min_price,
            MAX(o.high) as max_price,
            SUM(o.volume) as total_volume
        FROM theta.options_contracts c
        LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        WHERE c.expiration = %s AND c.symbol = 'SPY'
        GROUP BY c.strike, c.option_type
        ORDER BY c.strike, c.option_type
    """
    
    df = pd.read_sql(query, conn, params=[date])
    
    # Separate calls and puts
    calls = df[df['option_type'] == 'C'].copy()
    puts = df[df['option_type'] == 'P'].copy()
    
    print(f"\n📋 STRIKE DISTRIBUTION:")
    print(f"{'Strike':<8} {'Calls':<8} {'Puts':<8} {'C-Volume':<10} {'P-Volume':<10}")
    print("-" * 50)
    
    for strike in sorted(df['strike'].unique()):
        call_data = calls[calls['strike'] == strike]
        put_data = puts[puts['strike'] == strike]
        
        call_bars = call_data['ohlc_bars'].iloc[0] if not call_data.empty else 0
        put_bars = put_data['ohlc_bars'].iloc[0] if not put_data.empty else 0
        call_vol = call_data['total_volume'].iloc[0] if not call_data.empty else 0
        put_vol = put_data['total_volume'].iloc[0] if not put_data.empty else 0
        
        print(f"${strike:<7} {call_bars:<8} {put_bars:<8} {call_vol:<10.0f} {put_vol:<10.0f}")
    
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default='2023-01-03', help='Date to query (YYYY-MM-DD)')
    args = parser.parse_args()
    
    query_downloaded_data(args.date)