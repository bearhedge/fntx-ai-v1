#!/usr/bin/env python3
"""Investigate Greeks vs OHLC discrepancy"""

import os
import sys
import psycopg2
from psycopg2 import sql

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def main():
    print("Investigating Greeks vs OHLC Discrepancy")
    print("=" * 80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Get exact counts
    print("\n1. Exact counts from each table:")
    cursor.execute("""
        WITH counts AS (
            SELECT 
                'OHLC' as data_type,
                COUNT(*) as row_count
            FROM theta.options_ohlc
            
            UNION ALL
            
            SELECT 
                'Greeks' as data_type,
                COUNT(*) as row_count
            FROM theta.options_greeks
            
            UNION ALL
            
            SELECT 
                'IV' as data_type,
                COUNT(*) as row_count
            FROM theta.options_iv
        )
        SELECT * FROM counts
    """)
    
    results = cursor.fetchall()
    print("\nData Type | Row Count")
    print("-" * 30)
    for row in results:
        print(f"{row[0]:9} | {row[1]:,}")
    
    # Calculate percentage difference
    ohlc_count = next(r[1] for r in results if r[0] == 'OHLC')
    greeks_count = next(r[1] for r in results if r[0] == 'Greeks')
    diff_pct = ((greeks_count - ohlc_count) / ohlc_count) * 100
    print(f"\nGreeks has {diff_pct:.1f}% more rows than OHLC")
    
    # 2. Find contracts with Greeks but no OHLC
    print("\n2. Contracts with Greeks but no OHLC data:")
    cursor.execute("""
        WITH contract_counts AS (
            SELECT 
                c.contract_id,
                c.symbol,
                c.expiration,
                c.strike,
                c.option_type,
                COUNT(DISTINCT o.datetime) as ohlc_count,
                COUNT(DISTINCT g.datetime) as greeks_count,
                COUNT(DISTINCT iv.datetime) as iv_count
            FROM theta.options_contracts c
            LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
            LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id, c.symbol, c.expiration, c.strike, c.option_type
        )
        SELECT 
            COUNT(*) as contracts_with_greeks_no_ohlc,
            COALESCE(SUM(greeks_count), 0) as total_greeks_bars_without_ohlc
        FROM contract_counts
        WHERE greeks_count > 0 AND ohlc_count = 0
    """)
    
    result = cursor.fetchone()
    print(f"  Contracts with Greeks but no OHLC: {result[0]}")
    print(f"  Total Greeks bars without OHLC: {result[1]:,}")
    print(f"  This explains {result[1]:,} of the {greeks_count - ohlc_count:,} extra Greeks bars")
    
    # 3. Sample contracts with Greeks but no OHLC
    print("\n3. Sample contracts with Greeks but no OHLC:")
    cursor.execute("""
        WITH contract_counts AS (
            SELECT 
                c.contract_id,
                c.symbol,
                c.expiration,
                c.strike,
                c.option_type,
                COUNT(DISTINCT o.datetime) as ohlc_count,
                COUNT(DISTINCT g.datetime) as greeks_count
            FROM theta.options_contracts c
            LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id, c.symbol, c.expiration, c.strike, c.option_type
        )
        SELECT 
            expiration,
            strike,
            option_type,
            ohlc_count,
            greeks_count
        FROM contract_counts
        WHERE greeks_count > 0 AND ohlc_count = 0
        ORDER BY expiration, strike
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    if results:
        print("\nExpiration  | Strike | Type | OHLC | Greeks")
        print("-" * 50)
        for row in results:
            print(f"{row[0]} | {row[1]:6} | {row[2]:4} | {row[3]:4} | {row[4]:6}")
    
    # 4. Check for duplicate Greeks entries
    print("\n4. Checking for duplicate Greeks entries per timestamp:")
    cursor.execute("""
        WITH duplicate_greeks AS (
            SELECT 
                contract_id,
                datetime,
                COUNT(*) as dup_count
            FROM theta.options_greeks
            GROUP BY contract_id, datetime
            HAVING COUNT(*) > 1
        )
        SELECT COUNT(*) as contracts_with_duplicate_greeks
        FROM duplicate_greeks
    """)
    
    result = cursor.fetchone()
    print(f"  Contracts with duplicate Greeks entries: {result[0]}")
    
    # 5. Distribution of bar counts
    print("\n5. Distribution of bar counts per contract:")
    cursor.execute("""
        WITH contract_bar_counts AS (
            SELECT 
                c.contract_id,
                c.expiration,
                COUNT(DISTINCT o.datetime) as ohlc_bars,
                COUNT(DISTINCT g.datetime) as greeks_bars
            FROM theta.options_contracts c
            LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
            WHERE c.expiration >= '2023-01-01'
            GROUP BY c.contract_id, c.expiration
        )
        SELECT 
            CASE 
                WHEN ohlc_bars = 0 THEN '0 OHLC bars'
                WHEN ohlc_bars < 60 THEN '1-59 OHLC bars'
                WHEN ohlc_bars >= 60 THEN '60+ OHLC bars'
            END as ohlc_category,
            COUNT(*) as contract_count,
            SUM(greeks_bars) as total_greeks_bars
        FROM contract_bar_counts
        GROUP BY 
            CASE 
                WHEN ohlc_bars = 0 THEN '0 OHLC bars'
                WHEN ohlc_bars < 60 THEN '1-59 OHLC bars'
                WHEN ohlc_bars >= 60 THEN '60+ OHLC bars'
            END
        ORDER BY ohlc_category
    """)
    
    results = cursor.fetchall()
    print("\nOHLC Category    | Contracts | Total Greeks Bars")
    print("-" * 50)
    for row in results:
        print(f"{row[0]:15} | {row[1]:9} | {row[2]:,}")
    
    # 6. Analyze download logic
    print("\n6. Key Finding:")
    print("   The 60-bar filter is applied to OHLC data, but the download process")
    print("   downloads ALL data (OHLC, Greeks, IV) for a contract first, THEN")
    print("   applies the filter only to decide whether to SAVE the data.")
    print("\n   However, if Greeks data exists but OHLC has < 60 bars, the contract")
    print("   is skipped entirely. This suggests the extra Greeks bars come from")
    print("   contracts that PASSED the 60-bar filter but have more Greeks bars")
    print("   than OHLC bars for the same time period.")
    
    # 7. Check timestamps that have Greeks but no OHLC for valid contracts
    print("\n7. Checking for timestamps with Greeks but no OHLC (for contracts with 60+ OHLC bars):")
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
                g.contract_id,
                g.datetime,
                CASE WHEN o.datetime IS NOT NULL THEN 1 ELSE 0 END as has_ohlc,
                1 as has_greeks
            FROM theta.options_greeks g
            INNER JOIN valid_contracts vc ON g.contract_id = vc.contract_id
            LEFT JOIN theta.options_ohlc o ON g.contract_id = o.contract_id AND g.datetime = o.datetime
        )
        SELECT 
            COUNT(*) as total_greeks_timestamps,
            SUM(CASE WHEN has_ohlc = 0 THEN 1 ELSE 0 END) as greeks_without_ohlc,
            (SUM(CASE WHEN has_ohlc = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as pct_without_ohlc
        FROM timestamp_comparison
    """)
    
    result = cursor.fetchone()
    print(f"  Total Greeks timestamps (for valid contracts): {result[0]:,}")
    print(f"  Greeks timestamps without matching OHLC: {result[1]:,}")
    print(f"  Percentage without OHLC: {result[2]:.1f}%")
    print(f"\n  This accounts for the {result[1]:,} extra Greeks bars!")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()