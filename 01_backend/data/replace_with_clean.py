#!/usr/bin/env python3
"""
Replace contaminated tables with clean data only
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def replace_with_clean():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("REPLACING TABLES WITH CLEAN DATA ONLY")
    print("="*80)
    
    try:
        # 1. Create clean temp tables
        print("\n1. Creating clean temp tables...")
        
        # Clean contracts
        cursor.execute("DROP TABLE IF EXISTS theta.temp_contracts")
        cursor.execute("""
        CREATE TABLE theta.temp_contracts AS
        SELECT DISTINCT oc.*
        FROM theta.options_contracts oc
        WHERE oc.contract_id BETWEEN 117799 AND 119374
          AND oc.symbol = 'SPY'
        """)
        contracts_count = cursor.rowcount
        print(f"   Clean contracts: {contracts_count:,}")
        
        # Clean OHLC
        cursor.execute("DROP TABLE IF EXISTS theta.temp_ohlc")
        cursor.execute("""
        CREATE TABLE theta.temp_ohlc AS
        SELECT o.*
        FROM theta.options_ohlc o
        JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
        WHERE oc.contract_id BETWEEN 117799 AND 119374
          AND oc.symbol = 'SPY'
          AND o.datetime >= '2022-12-01' 
          AND o.datetime < '2023-01-01'
          AND oc.expiration = o.datetime::date
        """)
        ohlc_count = cursor.rowcount
        print(f"   Clean OHLC: {ohlc_count:,}")
        
        # Clean Greeks
        cursor.execute("DROP TABLE IF EXISTS theta.temp_greeks")
        cursor.execute("""
        CREATE TABLE theta.temp_greeks AS
        SELECT g.*
        FROM theta.options_greeks g
        JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
        WHERE oc.contract_id BETWEEN 117799 AND 119374
          AND oc.symbol = 'SPY'
          AND g.datetime >= '2022-12-01' 
          AND g.datetime < '2023-01-01'
          AND g.datetime::time != '16:00:00'
          AND oc.expiration = g.datetime::date
        """)
        greeks_count = cursor.rowcount
        print(f"   Clean Greeks: {greeks_count:,}")
        
        # Clean IV
        cursor.execute("DROP TABLE IF EXISTS theta.temp_iv")
        cursor.execute("""
        CREATE TABLE theta.temp_iv AS
        SELECT i.*
        FROM theta.options_iv i
        JOIN theta.options_contracts oc ON i.contract_id = oc.contract_id
        WHERE oc.contract_id BETWEEN 117799 AND 119374
          AND oc.symbol = 'SPY'
          AND i.datetime >= '2022-12-01' 
          AND i.datetime < '2023-01-01'
          AND oc.expiration = i.datetime::date
        """)
        iv_count = cursor.rowcount
        print(f"   Clean IV: {iv_count:,}")
        
        # 2. Replace original tables
        print("\n2. Replacing original tables...")
        
        cursor.execute("DROP TABLE theta.options_contracts")
        cursor.execute("ALTER TABLE theta.temp_contracts RENAME TO options_contracts")
        
        cursor.execute("DROP TABLE theta.options_ohlc")
        cursor.execute("ALTER TABLE theta.temp_ohlc RENAME TO options_ohlc")
        
        cursor.execute("DROP TABLE theta.options_greeks")
        cursor.execute("ALTER TABLE theta.temp_greeks RENAME TO options_greeks")
        
        cursor.execute("DROP TABLE theta.options_iv")
        cursor.execute("ALTER TABLE theta.temp_iv RENAME TO options_iv")
        
        print("   Replaced all tables with clean data")
        
        contracts_inserted = contracts_count
        ohlc_inserted = ohlc_count
        greeks_inserted = greeks_count
        iv_inserted = iv_count
        
        conn.commit()
        
        print("\n" + "="*80)
        print("CLEAN DATABASE COMPLETE!")
        print("="*80)
        print(f"Contracts: {contracts_inserted:,}")
        print(f"OHLC: {ohlc_inserted:,}")
        print(f"Greeks: {greeks_inserted:,}")
        print(f"IV: {iv_inserted:,}")
        
        expected = 1576 * 78
        print(f"\nExpected: {expected:,}")
        print(f"OHLC: {ohlc_inserted/expected*100:.1f}%")
        print(f"Greeks: {greeks_inserted/expected*100:.1f}%")
        print(f"IV: {iv_inserted/expected*100:.1f}%")
        
        print("\n✓ Database now contains ONLY clean December 2022 0DTE data")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    replace_with_clean()