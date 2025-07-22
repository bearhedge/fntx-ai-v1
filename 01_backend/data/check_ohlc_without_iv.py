#!/usr/bin/env python3
"""Check for OHLC records without IV"""

import sys
import psycopg2

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("Checking for OHLC without IV:")
    cursor.execute("""
        SELECT COUNT(*)
        FROM theta.options_ohlc o
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_iv iv 
            WHERE iv.contract_id = o.contract_id 
            AND iv.datetime = o.datetime
        )
    """)
    ohlc_without_iv = cursor.fetchone()[0]
    print(f"OHLC records without IV: {ohlc_without_iv:,}")
    
    if ohlc_without_iv > 0:
        print("\nSample of OHLC without IV:")
        cursor.execute("""
            SELECT 
                c.expiration,
                c.strike,
                c.option_type,
                o.datetime,
                o.close,
                o.volume
            FROM theta.options_ohlc o
            JOIN theta.options_contracts c ON o.contract_id = c.contract_id
            WHERE NOT EXISTS (
                SELECT 1 
                FROM theta.options_iv iv 
                WHERE iv.contract_id = o.contract_id 
                AND iv.datetime = o.datetime
            )
            ORDER BY o.datetime
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        for row in results:
            print(f"  {row[0]} ${row[1]} {row[2]} at {row[3]}: close=${row[4]:.2f}, vol={row[5]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()