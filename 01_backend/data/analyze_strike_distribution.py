#!/usr/bin/env python3
"""
Analyze strike distribution to understand far OTM data issues
"""
import sys
import psycopg2
import pandas as pd
import numpy as np

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def analyze_strike_distribution(date: str = "2023-01-03"):
    """Analyze strike distribution and identify relevant vs irrelevant strikes"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Get SPY price data for the day
    spy_query = """
        SELECT MIN(datetime) as open_time, MAX(datetime) as close_time
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
        WHERE c.expiration = %s AND c.symbol = 'SPY'
    """
    times = pd.read_sql(spy_query, conn, params=[date])
    print(f"\nAnalyzing strikes for {date}")
    print(f"Trading from {times.iloc[0]['open_time']} to {times.iloc[0]['close_time']}")
    
    # Analyze all strikes
    query = """
        WITH strike_stats AS (
            SELECT 
                c.strike,
                c.option_type,
                COUNT(o.datetime) as price_bars,
                SUM(o.volume) as total_volume,
                AVG(o.close) as avg_price,
                MIN(o.close) as min_price,
                MAX(o.close) as max_price,
                AVG(i.implied_volatility) as avg_iv,
                COUNT(DISTINCT o.datetime) as trading_periods,
                COUNT(DISTINCT CASE WHEN o.volume > 0 THEN o.datetime END) as active_periods
            FROM theta.options_contracts c
            LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            LEFT JOIN theta.options_iv i ON c.contract_id = i.contract_id AND o.datetime = i.datetime
            WHERE c.expiration = %s AND c.symbol = 'SPY'
            GROUP BY c.strike, c.option_type
        )
        SELECT 
            strike,
            option_type,
            price_bars,
            total_volume,
            avg_price,
            avg_iv,
            trading_periods,
            active_periods,
            CASE 
                WHEN total_volume IS NULL OR total_volume = 0 THEN 'No Trading'
                WHEN avg_price < 0.10 THEN 'Penny Options'
                WHEN active_periods < 5 THEN 'Barely Traded'
                WHEN avg_iv IS NULL THEN 'No IV Data'
                WHEN avg_iv > 2.0 THEN 'Extreme IV'
                ELSE 'Normal'
            END as data_quality
        FROM strike_stats
        ORDER BY strike
    """
    
    df = pd.read_sql(query, conn, params=[date])
    
    # SPY price estimate (using ATM options as proxy)
    atm_query = """
        SELECT c.strike, SUM(o.volume) as volume
        FROM theta.options_contracts c
        JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        WHERE c.expiration = %s AND c.symbol = 'SPY'
        GROUP BY c.strike
        ORDER BY volume DESC
        LIMIT 1
    """
    atm_result = pd.read_sql(atm_query, conn, params=[date])
    atm_strike = atm_result.iloc[0]['strike'] if not atm_result.empty else 380
    
    print(f"\nEstimated ATM strike: ${atm_strike}")
    
    # Categorize strikes
    print("\n" + "="*100)
    print("STRIKE DISTRIBUTION ANALYSIS")
    print("="*100)
    
    # Group by strike ranges
    for distance in [5, 10, 15, 20, 25, 30]:
        min_strike = atm_strike - distance
        max_strike = atm_strike + distance
        
        range_df = df[(df['strike'] >= min_strike) & (df['strike'] <= max_strike)]
        
        total_volume = range_df['total_volume'].sum()
        normal_contracts = len(range_df[range_df['data_quality'] == 'Normal'])
        problem_contracts = len(range_df[range_df['data_quality'] != 'Normal'])
        
        print(f"\n±${distance} from ATM (${min_strike}-${max_strike}):")
        print(f"  Contracts: {len(range_df)}")
        print(f"  Total Volume: {total_volume:,.0f}")
        print(f"  Normal Data: {normal_contracts}")
        print(f"  Problem Data: {problem_contracts}")
        
        # Show distribution of problems
        problems = range_df[range_df['data_quality'] != 'Normal']['data_quality'].value_counts()
        if not problems.empty:
            print("  Issues:")
            for issue, count in problems.items():
                print(f"    - {issue}: {count}")
    
    # Detailed view of far OTM strikes
    print("\n" + "="*100)
    print("FAR OTM STRIKE ANALYSIS (>$20 from ATM)")
    print("="*100)
    
    far_otm = df[(df['strike'] < atm_strike - 20) | (df['strike'] > atm_strike + 20)]
    
    print(f"\nTotal far OTM contracts: {len(far_otm)}")
    print("\nData quality breakdown:")
    print(far_otm['data_quality'].value_counts())
    
    # Show examples of problematic strikes
    print("\nExample problematic strikes:")
    problematic = far_otm[far_otm['data_quality'] != 'Normal'].head(10)
    
    print(f"\n{'Strike':>6} {'Type':>4} {'Avg Price':>10} {'Volume':>10} {'Avg IV':>8} {'Issue':>15}")
    print("-" * 70)
    
    for _, row in problematic.iterrows():
        avg_price = f"${row['avg_price']:.2f}" if pd.notna(row['avg_price']) else "N/A"
        volume = f"{row['total_volume']:.0f}" if pd.notna(row['total_volume']) else "0"
        avg_iv = f"{row['avg_iv']:.1%}" if pd.notna(row['avg_iv']) else "N/A"
        
        print(f"${row['strike']:>5} {row['option_type']:>4} {avg_price:>10} {volume:>10} {avg_iv:>8} {row['data_quality']:>15}")
    
    conn.close()
    
    return df, atm_strike

if __name__ == "__main__":
    df, atm = analyze_strike_distribution()
    
    print("\n" + "="*100)
    print("RECOMMENDATION")
    print("="*100)
    print("\nBased on this analysis, we should implement dynamic strike selection that:")
    print("1. Calculates expected price range using IV")
    print("2. Filters out strikes with minimal trading activity")
    print("3. Avoids penny options and extreme IV strikes")
    print("4. Adjusts range based on market volatility")