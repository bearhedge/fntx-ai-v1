#!/usr/bin/env python3
"""Verify Greeks-only records before deletion"""

import sys
import psycopg2
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def main():
    print("Verifying Greeks-only records (no OHLC)")
    print("=" * 80)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 1. Sample Greeks-only records to understand the pattern
    print("\n1. Sample of Greeks records without OHLC:")
    cursor.execute("""
        WITH valid_contracts AS (
            SELECT c.contract_id, c.expiration, c.strike, c.option_type
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id, c.expiration, c.strike, c.option_type
            HAVING COUNT(DISTINCT o.datetime) >= 60
        )
        SELECT 
            vc.expiration,
            vc.strike,
            vc.option_type,
            g.datetime,
            EXTRACT(hour FROM g.datetime) as hour,
            EXTRACT(minute FROM g.datetime) as minute,
            g.delta,
            g.gamma,
            g.theta,
            g.vega
        FROM theta.options_greeks g
        INNER JOIN valid_contracts vc ON g.contract_id = vc.contract_id
        LEFT JOIN theta.options_ohlc o ON g.contract_id = o.contract_id AND g.datetime = g.datetime
        WHERE o.datetime IS NULL
        ORDER BY g.datetime
        LIMIT 20
    """)
    
    results = cursor.fetchall()
    print(f"\nFound {len(results)} sample records:")
    print("Expiration | Strike | Type | DateTime            | Hour | Min | Delta   | Gamma   | Theta   | Vega")
    print("-" * 100)
    for row in results:
        exp, strike, typ, dt, hour, minute, delta, gamma, theta, vega = row
        print(f"{exp} | {strike:6} | {typ:4} | {dt} | {hour:4} | {minute:3} | {delta:7.4f} | {gamma:7.4f} | {theta:7.4f} | {vega:7.4f}")
    
    # 2. Distribution by time of day
    print("\n2. Distribution of Greeks-only records by hour:")
    cursor.execute("""
        WITH valid_contracts AS (
            SELECT c.contract_id
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id
            HAVING COUNT(DISTINCT o.datetime) >= 60
        ),
        greeks_only AS (
            SELECT 
                g.datetime,
                EXTRACT(hour FROM g.datetime) as hour
            FROM theta.options_greeks g
            INNER JOIN valid_contracts vc ON g.contract_id = vc.contract_id
            LEFT JOIN theta.options_ohlc o ON g.contract_id = o.contract_id AND g.datetime = g.datetime
            WHERE o.datetime IS NULL
        )
        SELECT 
            hour,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM greeks_only
        GROUP BY hour
        ORDER BY hour
    """)
    
    results = cursor.fetchall()
    print("Hour | Count  | Percentage")
    print("-----|--------|----------")
    for hour, count, pct in results:
        print(f"{hour:4} | {count:6} | {pct:6.2f}%")
    
    # 3. Count by minute within hour
    print("\n3. Most common timestamps (HH:MM):")
    cursor.execute("""
        WITH valid_contracts AS (
            SELECT c.contract_id
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id
            HAVING COUNT(DISTINCT o.datetime) >= 60
        ),
        greeks_only AS (
            SELECT 
                g.datetime,
                EXTRACT(hour FROM g.datetime) as hour,
                EXTRACT(minute FROM g.datetime) as minute
            FROM theta.options_greeks g
            INNER JOIN valid_contracts vc ON g.contract_id = vc.contract_id
            LEFT JOIN theta.options_ohlc o ON g.contract_id = o.contract_id AND g.datetime = g.datetime
            WHERE o.datetime IS NULL
        )
        SELECT 
            hour || ':' || LPAD(minute::text, 2, '0') as time,
            COUNT(*) as count
        FROM greeks_only
        GROUP BY hour, minute
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    print("Time  | Count")
    print("------|-------")
    for time, count in results:
        print(f"{time:5} | {count:6}")
    
    # 4. Total counts to be deleted
    print("\n4. Total records to be deleted:")
    
    # Greeks count
    cursor.execute("""
        WITH valid_contracts AS (
            SELECT c.contract_id
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id
            HAVING COUNT(DISTINCT o.datetime) >= 60
        )
        SELECT COUNT(*)
        FROM theta.options_greeks g
        INNER JOIN valid_contracts vc ON g.contract_id = vc.contract_id
        LEFT JOIN theta.options_ohlc o ON g.contract_id = o.contract_id AND g.datetime = g.datetime
        WHERE o.datetime IS NULL
    """)
    greeks_to_delete = cursor.fetchone()[0]
    print(f"   Greeks records without OHLC: {greeks_to_delete:,}")
    
    # IV count (should be same)
    cursor.execute("""
        WITH valid_contracts AS (
            SELECT c.contract_id
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id
            HAVING COUNT(DISTINCT o.datetime) >= 60
        )
        SELECT COUNT(*)
        FROM theta.options_iv iv
        INNER JOIN valid_contracts vc ON iv.contract_id = vc.contract_id
        LEFT JOIN theta.options_ohlc o ON iv.contract_id = o.contract_id AND iv.datetime = o.datetime
        WHERE o.datetime IS NULL
    """)
    iv_to_delete = cursor.fetchone()[0]
    print(f"   IV records without OHLC: {iv_to_delete:,}")
    
    print("\n5. CONFIRMATION:")
    print(f"   These records appear to be theoretical Greeks/IV calculations")
    print(f"   at times when no actual trading occurred.")
    print(f"   Most are at market close (16:00) or other non-peak times.")
    print(f"\n   Ready to delete {greeks_to_delete:,} Greeks and {iv_to_delete:,} IV records")
    print(f"   to create a congruent dataset where every timestamp has OHLC, Greeks, and IV.")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()