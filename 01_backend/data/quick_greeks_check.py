#!/usr/bin/env python3
"""
Quick check for Greeks and IV data
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def quick_check():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("QUICK CHECK FOR GREEKS AND IV DATA")
    print("="*60)
    
    # Check Greeks
    print("\n1. Greeks table:")
    cursor.execute("""
    SELECT COUNT(*) 
    FROM theta.options_greeks 
    WHERE datetime >= '2022-12-01' 
      AND datetime < '2022-12-02'
    LIMIT 1
    """)
    
    count = cursor.fetchone()[0]
    print(f"   Records for Dec 1, 2022: {count:,}")
    
    if count > 0:
        # Get one sample
        cursor.execute("""
        SELECT g.*, oc.strike, oc.option_type
        FROM theta.options_greeks g
        JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
        WHERE g.datetime >= '2022-12-15 09:30:00' 
          AND g.datetime < '2022-12-15 09:31:00'
          AND oc.strike = 390
        LIMIT 2
        """)
        
        print("\n   Sample data (Dec 15, 9:30 AM, $390):")
        for row in cursor.fetchall():
            print(f"   {row}")
    
    # Check IV
    print("\n2. IV table:")
    cursor.execute("""
    SELECT COUNT(*) 
    FROM theta.options_iv 
    WHERE datetime >= '2022-12-01' 
      AND datetime < '2022-12-02'
    LIMIT 1
    """)
    
    count = cursor.fetchone()[0]
    print(f"   Records for Dec 1, 2022: {count:,}")
    
    if count > 0:
        # Get one sample
        cursor.execute("""
        SELECT i.*, oc.strike, oc.option_type
        FROM theta.options_iv i
        JOIN theta.options_contracts oc ON i.contract_id = oc.contract_id
        WHERE i.datetime >= '2022-12-15 09:30:00' 
          AND i.datetime < '2022-12-15 09:31:00'
          AND oc.strike = 390
        LIMIT 2
        """)
        
        print("\n   Sample data (Dec 15, 9:30 AM, $390):")
        for row in cursor.fetchall():
            print(f"   {row}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    quick_check()