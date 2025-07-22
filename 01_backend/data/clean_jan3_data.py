#!/usr/bin/env python3
"""
Clean up Jan 3, 2023 data for fresh smart selection test
"""
import sys
import psycopg2

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def clean_jan3_data():
    """Remove all Jan 3, 2023 data"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Get all contract IDs for Jan 3
        cursor.execute("""
            SELECT contract_id 
            FROM theta.options_contracts 
            WHERE symbol = 'SPY' 
            AND expiration = '2023-01-03'
        """)
        
        contract_ids = [row[0] for row in cursor.fetchall()]
        
        if contract_ids:
            print(f"Found {len(contract_ids)} contracts to clean")
            
            # Delete from all tables
            cursor.execute("""
                DELETE FROM theta.options_iv 
                WHERE contract_id = ANY(%s)
            """, (contract_ids,))
            print(f"  Deleted {cursor.rowcount} IV records")
            
            cursor.execute("""
                DELETE FROM theta.options_greeks 
                WHERE contract_id = ANY(%s)
            """, (contract_ids,))
            print(f"  Deleted {cursor.rowcount} Greeks records")
            
            cursor.execute("""
                DELETE FROM theta.options_ohlc 
                WHERE contract_id = ANY(%s)
            """, (contract_ids,))
            print(f"  Deleted {cursor.rowcount} OHLC records")
            
            cursor.execute("""
                DELETE FROM theta.options_contracts 
                WHERE symbol = 'SPY' 
                AND expiration = '2023-01-03'
            """)
            print(f"  Deleted {cursor.rowcount} contracts")
            
            conn.commit()
            print("\n✓ Jan 3, 2023 data cleaned successfully")
        else:
            print("No data found for Jan 3, 2023")
            
    except Exception as e:
        conn.rollback()
        print(f"Error cleaning data: {e}")
        return 1
        
    finally:
        cursor.close()
        conn.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(clean_jan3_data())