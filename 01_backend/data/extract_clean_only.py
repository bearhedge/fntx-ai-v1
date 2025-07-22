#!/usr/bin/env python3
"""
Extract only clean data into new tables, then replace original tables
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def extract_clean():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("EXTRACTING CLEAN DATA TO NEW TABLES")
    print("="*80)
    
    try:
        # Create clean OHLC table
        print("\n1. Creating clean OHLC table...")
        cursor.execute("DROP TABLE IF EXISTS theta.options_ohlc_clean")
        cursor.execute("""
        CREATE TABLE theta.options_ohlc_clean AS
        SELECT o.*
        FROM theta.options_ohlc o
        JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
        WHERE oc.contract_id BETWEEN 117799 AND 119374
          AND oc.symbol = 'SPY'
          AND o.datetime >= '2022-12-01' 
          AND o.datetime < '2023-01-01'
          AND oc.expiration = o.datetime::date
        """)
        print(f"   Created clean OHLC with {cursor.rowcount:,} records")
        conn.commit()
        
        # Create clean Greeks table
        print("\n2. Creating clean Greeks table...")
        cursor.execute("DROP TABLE IF EXISTS theta.options_greeks_clean") 
        cursor.execute("""
        CREATE TABLE theta.options_greeks_clean AS
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
        print(f"   Created clean Greeks with {cursor.rowcount:,} records")
        conn.commit()
        
        # Create clean IV table
        print("\n3. Creating clean IV table...")
        cursor.execute("DROP TABLE IF EXISTS theta.options_iv_clean")
        cursor.execute("""
        CREATE TABLE theta.options_iv_clean AS
        SELECT i.*
        FROM theta.options_iv i
        JOIN theta.options_contracts oc ON i.contract_id = oc.contract_id
        WHERE oc.contract_id BETWEEN 117799 AND 119374
          AND oc.symbol = 'SPY'
          AND i.datetime >= '2022-12-01' 
          AND i.datetime < '2023-01-01'
          AND oc.expiration = i.datetime::date
        """)
        print(f"   Created clean IV with {cursor.rowcount:,} records")
        conn.commit()
        
        # Create clean contracts table
        print("\n4. Creating clean contracts table...")
        cursor.execute("DROP TABLE IF EXISTS theta.options_contracts_clean")
        cursor.execute("""
        CREATE TABLE theta.options_contracts_clean AS
        SELECT DISTINCT oc.*
        FROM theta.options_contracts oc
        WHERE oc.contract_id BETWEEN 117799 AND 119374
          AND oc.symbol = 'SPY'
        """)
        print(f"   Created clean contracts with {cursor.rowcount:,} records")
        conn.commit()
        
        # Verify clean data
        print("\n5. Verifying clean dataset...")
        cursor.execute("""
        SELECT 
            COUNT(DISTINCT c.contract_id) as contracts,
            COUNT(DISTINCT o.id) as ohlc,
            COUNT(DISTINCT g.id) as greeks,
            COUNT(DISTINCT i.id) as iv
        FROM theta.options_contracts_clean c
        LEFT JOIN theta.options_ohlc_clean o ON c.contract_id = o.contract_id
        LEFT JOIN theta.options_greeks_clean g ON c.contract_id = g.contract_id
        LEFT JOIN theta.options_iv_clean i ON c.contract_id = i.contract_id
        """)
        
        contracts, ohlc, greeks, iv = cursor.fetchone()
        print(f"Clean dataset:")
        print(f"  Contracts: {contracts:,}")
        print(f"  OHLC: {ohlc:,}")
        print(f"  Greeks: {greeks:,}")
        print(f"  IV: {iv:,}")
        
        expected = 1576 * 78
        print(f"\nExpected: {expected:,}")
        print(f"OHLC completeness: {ohlc/expected*100:.1f}%")
        print(f"Greeks completeness: {greeks/expected*100:.1f}%")
        print(f"IV completeness: {iv/expected*100:.1f}%")
        
        if input("\nReplace original tables with clean data? (y/N): ").lower() == 'y':
            print("\n6. Replacing original tables...")
            
            # Replace tables
            cursor.execute("DROP TABLE theta.options_ohlc")
            cursor.execute("ALTER TABLE theta.options_ohlc_clean RENAME TO options_ohlc")
            
            cursor.execute("DROP TABLE theta.options_greeks")
            cursor.execute("ALTER TABLE theta.options_greeks_clean RENAME TO options_greeks")
            
            cursor.execute("DROP TABLE theta.options_iv")
            cursor.execute("ALTER TABLE theta.options_iv_clean RENAME TO options_iv")
            
            cursor.execute("DROP TABLE theta.options_contracts")
            cursor.execute("ALTER TABLE theta.options_contracts_clean RENAME TO options_contracts")
            
            conn.commit()
            print("✓ Replaced original tables with clean data")
        else:
            print("Keeping clean tables as *_clean versions")
            
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    extract_clean()