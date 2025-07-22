#!/usr/bin/env python3
"""Check if there are OHLC bars without corresponding Greeks"""

import sys
import psycopg2

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def main():
    print("Checking for OHLC bars WITHOUT corresponding Greeks")
    print("=" * 80)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 1. Check if any OHLC bars lack Greeks
    print("\n1. Looking for OHLC timestamps without Greeks (for contracts with 60+ OHLC bars):")
    cursor.execute("""
        WITH valid_contracts AS (
            -- Contracts that passed the 60-bar filter
            SELECT c.contract_id
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id
            HAVING COUNT(DISTINCT o.datetime) >= 60
        )
        SELECT 
            COUNT(*) as ohlc_without_greeks
        FROM theta.options_ohlc o
        INNER JOIN valid_contracts vc ON o.contract_id = vc.contract_id
        LEFT JOIN theta.options_greeks g ON o.contract_id = g.contract_id AND o.datetime = g.datetime
        WHERE g.datetime IS NULL
    """)
    
    result = cursor.fetchone()[0]
    print(f"   OHLC bars without matching Greeks: {result:,}")
    
    if result > 0:
        print("\n   THIS IS THE PROBLEM! There should NEVER be OHLC without Greeks.")
        print("   Every traded interval should have Greeks calculated.")
        
        # 2. Get examples
        print("\n2. Examples of OHLC without Greeks:")
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
                o.datetime,
                o.open,
                o.high,
                o.low,
                o.close,
                o.volume
            FROM theta.options_ohlc o
            INNER JOIN valid_contracts vc ON o.contract_id = vc.contract_id
            LEFT JOIN theta.options_greeks g ON o.contract_id = g.contract_id AND o.datetime = g.datetime
            WHERE g.datetime IS NULL
            ORDER BY vc.expiration, o.datetime
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        print("   Exp Date   | Strike | Type | Timestamp           | O     | H     | L     | C     | Vol")
        print("   -----------|--------|------|---------------------|-------|-------|-------|-------|-----")
        for row in results:
            exp, strike, typ, ts, o, h, l, c, vol = row
            print(f"   {exp} | {strike:6} | {typ:4} | {ts} | {o:5.2f} | {h:5.2f} | {l:5.2f} | {c:5.2f} | {vol:4}")
    
    # 3. Check the opposite - total picture
    print("\n3. Complete picture:")
    cursor.execute("""
        WITH valid_contracts AS (
            SELECT c.contract_id
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id
            HAVING COUNT(DISTINCT o.datetime) >= 60
        ),
        timestamp_comparison AS (
            SELECT 
                COALESCE(o.contract_id, g.contract_id) as contract_id,
                COALESCE(o.datetime, g.datetime) as datetime,
                CASE WHEN o.datetime IS NOT NULL THEN 1 ELSE 0 END as has_ohlc,
                CASE WHEN g.datetime IS NOT NULL THEN 1 ELSE 0 END as has_greeks
            FROM theta.options_ohlc o
            FULL OUTER JOIN theta.options_greeks g 
                ON o.contract_id = g.contract_id AND o.datetime = g.datetime
            WHERE COALESCE(o.contract_id, g.contract_id) IN (SELECT contract_id FROM valid_contracts)
        )
        SELECT 
            SUM(CASE WHEN has_ohlc = 1 AND has_greeks = 1 THEN 1 ELSE 0 END) as both,
            SUM(CASE WHEN has_ohlc = 1 AND has_greeks = 0 THEN 1 ELSE 0 END) as ohlc_only,
            SUM(CASE WHEN has_ohlc = 0 AND has_greeks = 1 THEN 1 ELSE 0 END) as greeks_only
        FROM timestamp_comparison
    """)
    
    both, ohlc_only, greeks_only = cursor.fetchone()
    print(f"   Timestamps with both OHLC and Greeks: {both:,}")
    print(f"   Timestamps with OHLC only (NO Greeks): {ohlc_only:,}")
    print(f"   Timestamps with Greeks only (NO OHLC): {greeks_only:,}")
    
    total_ohlc = both + ohlc_only
    total_greeks = both + greeks_only
    print(f"\n   Total OHLC timestamps: {total_ohlc:,}")
    print(f"   Total Greeks timestamps: {total_greeks:,}")
    print(f"   Difference: {total_greeks - total_ohlc:,}")
    
    # 4. The real discrepancy
    print("\n4. THE REAL ISSUE:")
    if ohlc_only > 0:
        print(f"   There are {ohlc_only:,} OHLC bars WITHOUT Greeks!")
        print("   This explains why the total counts don't match.")
        print("   Every OHLC bar should have Greeks, but some are missing.")
    
    print(f"\n   Additionally, there are {greeks_only:,} Greeks bars without OHLC")
    print("   (which is normal - Greeks can be calculated without trades)")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()