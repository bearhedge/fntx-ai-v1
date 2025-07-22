#!/usr/bin/env python3
"""
Debug Greeks and IV data mapping
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def debug_mapping():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("DEBUGGING GREEKS AND IV DATA MAPPING")
    print("="*80)
    
    # 1. Find contracts that have OHLC data on Dec 15
    print("\n1. Contracts with OHLC data on Dec 15:")
    cursor.execute("""
    SELECT DISTINCT 
        oc.contract_id,
        oc.symbol,
        oc.expiration,
        oc.strike,
        oc.option_type
    FROM theta.options_ohlc o
    JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
    WHERE o.datetime::date = '2022-12-15'
      AND oc.expiration = '2022-12-15'
      AND oc.strike = 390
    ORDER BY oc.option_type
    """)
    
    ohlc_contracts = cursor.fetchall()
    print(f"Found {len(ohlc_contracts)} contracts with OHLC data")
    for contract in ohlc_contracts:
        print(f"  Contract ID {contract[0]}: {contract[1]} {contract[2]} ${contract[3]} {contract[4]}")
    
    # 2. Find contracts that have Greeks data on Dec 15
    print("\n2. Contracts with Greeks data on Dec 15:")
    cursor.execute("""
    SELECT DISTINCT 
        oc.contract_id,
        oc.symbol,
        oc.expiration,
        oc.strike,
        oc.option_type,
        COUNT(*) as records
    FROM theta.options_greeks g
    JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
    WHERE g.datetime::date = '2022-12-15'
      AND oc.strike = 390
    GROUP BY oc.contract_id, oc.symbol, oc.expiration, oc.strike, oc.option_type
    ORDER BY oc.expiration, oc.option_type
    """)
    
    greeks_contracts = cursor.fetchall()
    print(f"Found {len(greeks_contracts)} contracts with Greeks data")
    for contract in greeks_contracts:
        print(f"  Contract ID {contract[0]}: {contract[1]} {contract[2]} ${contract[3]} {contract[4]} ({contract[5]} records)")
    
    # 3. Check if contract IDs match
    print("\n3. Checking contract ID overlap:")
    ohlc_ids = {c[0] for c in ohlc_contracts}
    greeks_ids = {c[0] for c in greeks_contracts}
    
    overlap = ohlc_ids.intersection(greeks_ids)
    print(f"  OHLC contract IDs: {ohlc_ids}")
    print(f"  Greeks contract IDs: {list(greeks_ids)[:10]}... (showing first 10)")
    print(f"  Overlapping IDs: {overlap}")
    
    # 4. Sample Greeks data to see what we have
    print("\n4. Sample Greeks data (any Dec 15 0DTE):")
    cursor.execute("""
    SELECT 
        g.contract_id,
        g.datetime,
        g.delta,
        g.gamma,
        oc.expiration,
        oc.strike,
        oc.option_type
    FROM theta.options_greeks g
    JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
    WHERE g.datetime >= '2022-12-15 09:30:00'
      AND g.datetime < '2022-12-15 10:00:00'
      AND oc.expiration = '2022-12-15'
    ORDER BY oc.strike, oc.option_type
    LIMIT 5
    """)
    
    print(f"{'Contract':<10} {'DateTime':<20} {'Strike':<6} {'Type':<4} {'Delta':>8} {'Gamma':>10}")
    print("-"*60)
    
    for row in cursor.fetchall():
        cid, dt, delta, gamma, exp, strike, typ = row
        print(f"{cid:<10} {dt} ${strike:<4.0f} {typ:<4} {delta:>8.4f} {gamma:>10.6f}")
    
    # 5. Check date ranges
    print("\n5. Date ranges in Greeks table:")
    cursor.execute("""
    SELECT 
        MIN(g.datetime) as first_date,
        MAX(g.datetime) as last_date,
        COUNT(DISTINCT g.datetime::date) as days,
        COUNT(DISTINCT oc.expiration) as expirations
    FROM theta.options_greeks g
    JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
    WHERE g.datetime >= '2022-12-01' AND g.datetime < '2023-01-01'
    """)
    
    first, last, days, exps = cursor.fetchone()
    print(f"  First record: {first}")
    print(f"  Last record: {last}")
    print(f"  Days with data: {days}")
    print(f"  Unique expirations: {exps}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    debug_mapping()