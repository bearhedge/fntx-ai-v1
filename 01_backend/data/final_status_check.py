#!/usr/bin/env python3
"""
Final status check after IV backfill
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def final_check():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("FINAL DATASET STATUS - DECEMBER 2022")
    print("="*80)
    
    # Overall counts
    cursor.execute("""
    SELECT 
        COUNT(DISTINCT oc.contract_id) as contracts,
        SUM(CASE WHEN oc.option_type = 'C' THEN 1 ELSE 0 END) as calls,
        SUM(CASE WHEN oc.option_type = 'P' THEN 1 ELSE 0 END) as puts
    FROM theta.options_contracts oc
    WHERE oc.symbol = 'SPY'
      AND oc.expiration >= '2022-12-01'
      AND oc.expiration <= '2022-12-31'
    """)
    
    contracts, calls, puts = cursor.fetchone()
    print(f"Total contracts: {contracts:,} ({calls:,} calls, {puts:,} puts)")
    
    # Data completeness
    cursor.execute("""
    SELECT 
        COUNT(DISTINCT o.id) as ohlc_records,
        COUNT(DISTINCT g.id) as greeks_records,
        COUNT(DISTINCT i.id) as iv_records,
        COUNT(DISTINCT CASE WHEN g.datetime::time = '16:00:00' THEN g.id END) as extra_greeks
    FROM theta.options_ohlc o
    FULL OUTER JOIN theta.options_greeks g ON o.contract_id = g.contract_id AND o.datetime = g.datetime
    FULL OUTER JOIN theta.options_iv i ON o.contract_id = i.contract_id AND o.datetime = i.datetime
    WHERE EXISTS (
        SELECT 1 FROM theta.options_contracts oc 
        WHERE (o.contract_id = oc.contract_id OR g.contract_id = oc.contract_id OR i.contract_id = oc.contract_id)
        AND oc.symbol = 'SPY'
        AND oc.expiration >= '2022-12-01'
        AND oc.expiration <= '2022-12-31'
    )
    """)
    
    ohlc, greeks, iv, extra = cursor.fetchone()
    
    print(f"\nData records:")
    print(f"  OHLC: {ohlc:,}")
    print(f"  Greeks: {greeks:,} (includes {extra:,} extra 16:00 records)")
    print(f"  IV: {iv:,}")
    
    # Check IV by option type
    cursor.execute("""
    SELECT 
        oc.option_type,
        COUNT(DISTINCT oc.contract_id) as contracts,
        COUNT(DISTINCT CASE WHEN i.id IS NOT NULL THEN oc.contract_id END) as with_iv,
        COUNT(i.id) as iv_records
    FROM theta.options_contracts oc
    LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id
    WHERE oc.symbol = 'SPY'
      AND oc.expiration >= '2022-12-01'
      AND oc.expiration <= '2022-12-31'
    GROUP BY oc.option_type
    ORDER BY oc.option_type
    """)
    
    print(f"\nIV coverage by type:")
    for opt_type, total, with_iv, records in cursor.fetchall():
        coverage = with_iv / total * 100 if total > 0 else 0
        print(f"  {opt_type}: {with_iv}/{total} contracts ({coverage:.1f}%), {records:,} IV records")
    
    # Expected vs actual
    expected_0dte_contracts = 1536  # From the download log
    expected_records = expected_0dte_contracts * 78
    
    print(f"\nExpected for 0DTE contracts:")
    print(f"  Contracts: {expected_0dte_contracts:,}")
    print(f"  Records per type: {expected_records:,}")
    
    print(f"\nCompleteness (0DTE only):")
    print(f"  OHLC: {ohlc/expected_records*100:.1f}%")
    print(f"  Greeks: {(greeks-extra)/expected_records*100:.1f}% (after removing extras)")
    print(f"  IV: {iv/expected_records*100:.1f}%")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    final_check()