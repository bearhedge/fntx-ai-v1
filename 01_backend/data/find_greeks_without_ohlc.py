#!/usr/bin/env python3
"""Find and analyze Greeks records without OHLC"""

import sys
import psycopg2

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def main():
    print("Finding Greeks records without corresponding OHLC")
    print("=" * 80)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # First, let's understand the overall picture
    print("\n1. Overall data counts:")
    cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc")
    ohlc_total = cursor.fetchone()[0]
    print(f"   Total OHLC records: {ohlc_total:,}")
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_greeks")
    greeks_total = cursor.fetchone()[0]
    print(f"   Total Greeks records: {greeks_total:,}")
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_iv")
    iv_total = cursor.fetchone()[0]
    print(f"   Total IV records: {iv_total:,}")
    
    # Find Greeks without OHLC - corrected query
    print("\n2. Finding Greeks without OHLC (ALL contracts):")
    cursor.execute("""
        SELECT COUNT(*)
        FROM theta.options_greeks g
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        )
    """)
    greeks_without_ohlc = cursor.fetchone()[0]
    print(f"   Greeks records without OHLC: {greeks_without_ohlc:,}")
    
    # Find IV without OHLC
    print("\n3. Finding IV without OHLC (ALL contracts):")
    cursor.execute("""
        SELECT COUNT(*)
        FROM theta.options_iv iv
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = iv.contract_id 
            AND o.datetime = iv.datetime
        )
    """)
    iv_without_ohlc = cursor.fetchone()[0]
    print(f"   IV records without OHLC: {iv_without_ohlc:,}")
    
    # Sample some of these records
    print("\n4. Sample of Greeks without OHLC:")
    cursor.execute("""
        SELECT 
            c.expiration,
            c.strike,
            c.option_type,
            g.datetime,
            g.delta,
            g.gamma,
            g.theta,
            g.vega
        FROM theta.options_greeks g
        JOIN theta.options_contracts c ON g.contract_id = c.contract_id
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        )
        ORDER BY g.datetime
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    if results:
        print("   Expiration | Strike | Type | DateTime            | Delta  | Gamma  | Theta  | Vega")
        print("   " + "-" * 85)
        for row in results:
            exp, strike, typ, dt, delta, gamma, theta, vega = row
            print(f"   {exp} | {strike:6} | {typ:4} | {dt} | {delta:6.3f} | {gamma:6.3f} | {theta:6.3f} | {vega:6.3f}")
    
    # Time distribution
    print("\n5. Time distribution of Greeks without OHLC:")
    cursor.execute("""
        SELECT 
            EXTRACT(hour FROM g.datetime) as hour,
            COUNT(*) as count
        FROM theta.options_greeks g
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        )
        GROUP BY EXTRACT(hour FROM g.datetime)
        ORDER BY hour
    """)
    
    results = cursor.fetchall()
    if results:
        print("   Hour | Count")
        print("   -----|-------")
        total = sum(r[1] for r in results)
        for hour, count in results:
            pct = (count / total) * 100
            print(f"   {hour:4} | {count:6} ({pct:5.1f}%)")
    
    # Most common exact timestamps
    print("\n6. Most common exact timestamps without OHLC:")
    cursor.execute("""
        SELECT 
            TO_CHAR(g.datetime, 'HH24:MI') as time,
            COUNT(*) as count
        FROM theta.options_greeks g
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        )
        GROUP BY TO_CHAR(g.datetime, 'HH24:MI')
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    if results:
        print("   Time  | Count")
        print("   ------|-------")
        for time, count in results:
            print(f"   {time} | {count:6}")
    
    print(f"\n7. SUMMARY:")
    print(f"   Greeks without OHLC: {greeks_without_ohlc:,}")
    print(f"   IV without OHLC: {iv_without_ohlc:,}")
    print(f"   These represent theoretical calculations when no trading occurred.")
    print(f"   Deleting these will create a perfectly aligned dataset.")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()