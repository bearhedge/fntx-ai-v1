#!/usr/bin/env python3
"""
Investigate why we have non-0DTE data in our December 2022 dataset
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def investigate():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("INVESTIGATING DATA CONSISTENCY ISSUE")
    print("="*80)
    
    # 1. Check what expirations we have for December 2022 data
    print("\n1. Expirations in Greeks table for Dec 2022:")
    cursor.execute("""
    SELECT DISTINCT 
        oc.expiration,
        g.datetime::date as trade_date,
        oc.expiration = g.datetime::date as is_0dte,
        COUNT(DISTINCT oc.contract_id) as contracts
    FROM theta.options_greeks g
    JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
    WHERE g.datetime >= '2022-12-01' 
      AND g.datetime < '2023-01-01'
      AND oc.symbol = 'SPY'
    GROUP BY oc.expiration, g.datetime::date
    ORDER BY g.datetime::date, oc.expiration
    LIMIT 20
    """)
    
    print(f"{'Trade Date':<12} {'Expiration':<12} {'Is 0DTE?':<10} {'Contracts':<10}")
    print("-"*50)
    for exp, trade_date, is_0dte, contracts in cursor.fetchall():
        print(f"{trade_date} {exp} {str(is_0dte):<10} {contracts:<10}")
    
    # 2. Count 0DTE vs non-0DTE
    print("\n2. 0DTE vs Non-0DTE breakdown:")
    cursor.execute("""
    SELECT 
        CASE 
            WHEN oc.expiration = g.datetime::date THEN '0DTE'
            ELSE 'Non-0DTE'
        END as type,
        COUNT(DISTINCT oc.contract_id) as contracts,
        COUNT(*) as records
    FROM theta.options_greeks g
    JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
    WHERE g.datetime >= '2022-12-01' 
      AND g.datetime < '2023-01-01'
      AND oc.symbol = 'SPY'
    GROUP BY CASE WHEN oc.expiration = g.datetime::date THEN '0DTE' ELSE 'Non-0DTE' END
    """)
    
    for typ, contracts, records in cursor.fetchall():
        print(f"  {typ}: {contracts} contracts, {records:,} records")
    
    # 3. Check OHLC consistency
    print("\n3. OHLC Data Check:")
    cursor.execute("""
    SELECT 
        CASE 
            WHEN oc.expiration = o.datetime::date THEN '0DTE'
            ELSE 'Non-0DTE'
        END as type,
        COUNT(DISTINCT oc.contract_id) as contracts,
        COUNT(*) as records
    FROM theta.options_ohlc o
    JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
    WHERE o.datetime >= '2022-12-01' 
      AND o.datetime < '2023-01-01'
      AND oc.symbol = 'SPY'
    GROUP BY CASE WHEN oc.expiration = o.datetime::date THEN '0DTE' ELSE 'Non-0DTE' END
    """)
    
    for typ, contracts, records in cursor.fetchall():
        print(f"  {typ}: {contracts} contracts, {records:,} records")
    
    # 4. Sample non-0DTE data
    print("\n4. Sample of Non-0DTE data (should not exist!):")
    cursor.execute("""
    SELECT 
        g.datetime::date as trade_date,
        oc.expiration,
        oc.strike,
        oc.option_type,
        COUNT(*) as records
    FROM theta.options_greeks g
    JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
    WHERE g.datetime >= '2022-12-01' 
      AND g.datetime < '2023-01-01'
      AND oc.symbol = 'SPY'
      AND oc.expiration != g.datetime::date  -- Non-0DTE
    GROUP BY g.datetime::date, oc.expiration, oc.strike, oc.option_type
    ORDER BY g.datetime::date, oc.expiration
    LIMIT 10
    """)
    
    print(f"{'Trade Date':<12} {'Expiration':<12} {'Strike':<8} {'Type':<5} {'Records':<10}")
    print("-"*55)
    for trade_date, exp, strike, opt_type, records in cursor.fetchall():
        print(f"{trade_date} {exp} ${strike:<6.0f} {opt_type:<5} {records:<10}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    investigate()