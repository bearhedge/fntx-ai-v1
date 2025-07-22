#!/usr/bin/env python3
"""Quick check of Greeks vs OHLC discrepancy"""

import sys
import psycopg2

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def main():
    print("Quick Greeks vs OHLC Check")
    print("=" * 80)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 1. Get exact counts
    print("\n1. Row counts:")
    cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc")
    ohlc_count = cursor.fetchone()[0]
    print(f"   OHLC rows: {ohlc_count:,}")
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_greeks")
    greeks_count = cursor.fetchone()[0]
    print(f"   Greeks rows: {greeks_count:,}")
    
    diff = greeks_count - ohlc_count
    pct = (diff / ohlc_count) * 100
    print(f"   Difference: {diff:,} ({pct:.1f}%)")
    
    # 2. Check a specific contract to understand the pattern
    print("\n2. Checking Jan 3, 2023 $385 Put:")
    cursor.execute("""
        SELECT contract_id 
        FROM theta.options_contracts 
        WHERE expiration = '2023-01-03' 
        AND strike = 385 
        AND option_type = 'P'
    """)
    contract_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc WHERE contract_id = %s", (contract_id,))
    ohlc_bars = cursor.fetchone()[0]
    print(f"   OHLC bars: {ohlc_bars}")
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_greeks WHERE contract_id = %s", (contract_id,))
    greeks_bars = cursor.fetchone()[0]
    print(f"   Greeks bars: {greeks_bars}")
    
    # 3. Find timestamps with Greeks but no OHLC for this contract
    print("\n3. Finding timestamps with Greeks but no OHLC:")
    cursor.execute("""
        SELECT g.datetime, g.delta, g.gamma, g.theta, g.vega
        FROM theta.options_greeks g
        LEFT JOIN theta.options_ohlc o ON g.contract_id = o.contract_id AND g.datetime = o.datetime
        WHERE g.contract_id = %s 
        AND o.datetime IS NULL
        ORDER BY g.datetime
        LIMIT 10
    """, (contract_id,))
    
    results = cursor.fetchall()
    if results:
        print(f"   Found {len(results)} timestamps with Greeks but no OHLC. First 10:")
        for ts, delta, gamma, theta, vega in results:
            print(f"   {ts}: delta={delta:.4f}, gamma={gamma:.4f}, theta={theta:.4f}, vega={gamma:.4f}")
    
    # 4. Check the theory: ThetaData provides Greeks even during non-trading hours
    print("\n4. Checking time distribution of Greeks without OHLC:")
    cursor.execute("""
        WITH greeks_no_ohlc AS (
            SELECT 
                g.datetime,
                EXTRACT(hour FROM g.datetime) as hour,
                EXTRACT(minute FROM g.datetime) as minute
            FROM theta.options_greeks g
            LEFT JOIN theta.options_ohlc o ON g.contract_id = o.contract_id AND g.datetime = o.datetime
            WHERE g.contract_id = %s 
            AND o.datetime IS NULL
        )
        SELECT 
            hour,
            COUNT(*) as count
        FROM greeks_no_ohlc
        GROUP BY hour
        ORDER BY hour
    """, (contract_id,))
    
    results = cursor.fetchall()
    print("   Hour | Count")
    print("   -----|------")
    for hour, count in results:
        print(f"   {hour:4} | {count}")
    
    # 5. Summary check across all contracts
    print("\n5. How many contracts have more Greeks bars than OHLC bars?")
    cursor.execute("""
        WITH bar_counts AS (
            SELECT 
                c.contract_id,
                COUNT(DISTINCT o.datetime) as ohlc_count,
                COUNT(DISTINCT g.datetime) as greeks_count
            FROM theta.options_contracts c
            LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id
            HAVING COUNT(DISTINCT g.datetime) > 0  -- Has Greeks data
        )
        SELECT 
            COUNT(*) as total_contracts,
            SUM(CASE WHEN greeks_count > ohlc_count THEN 1 ELSE 0 END) as contracts_with_more_greeks,
            SUM(greeks_count - ohlc_count) as total_extra_greeks_bars
        FROM bar_counts
        WHERE ohlc_count >= 60  -- Only contracts that passed the filter
    """)
    
    result = cursor.fetchone()
    print(f"   Total contracts (with 60+ OHLC bars): {result[0]:,}")
    print(f"   Contracts with more Greeks than OHLC: {result[1]:,}")
    print(f"   Total extra Greeks bars: {result[2]:,}")
    
    print("\n6. Key Insight:")
    print("   ThetaData appears to provide Greeks calculations at timestamps")
    print("   where no actual trading occurred (no OHLC data). This could be:")
    print("   - Pre-market/after-hours theoretical values")
    print("   - Greeks calculated at regular intervals even without trades")
    print("   - Model-based Greeks that don't require actual trade data")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()