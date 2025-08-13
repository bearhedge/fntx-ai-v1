#!/usr/bin/env python3
"""
Delete mock positions from the database
"""
import psycopg2
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))
from config import DB_CONFIG

def delete_mock_positions():
    """Delete the mock positions (635P, 640C) from the database"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        
        with conn.cursor() as cur:
            # Delete 635 PUT positions
            cur.execute("""
                DELETE FROM trading.trades
                WHERE symbol = 'SPY' 
                AND strike_price = 635 
                AND option_type = 'PUT'
                AND status = 'open'
            """)
            deleted_635p = cur.rowcount
            
            # Delete 640 CALL positions
            cur.execute("""
                DELETE FROM trading.trades
                WHERE symbol = 'SPY' 
                AND strike_price = 640 
                AND option_type = 'CALL'
                AND status = 'open'
            """)
            deleted_640c = cur.rowcount
            
            # Also delete any duplicate 635 PUT entries
            cur.execute("""
                DELETE FROM trading.trades
                WHERE symbol = 'SPY' 
                AND strike_price = 635 
                AND option_type = 'PUT'
                AND entry_price IN (0.50, 1.10)
                AND status = 'open'
            """)
            deleted_dupe_635p = cur.rowcount
            
            conn.commit()
            
            print(f"Deleted mock positions:")
            print(f"  - 635 PUT: {deleted_635p} positions")
            print(f"  - 640 CALL: {deleted_640c} positions")
            print(f"  - Duplicate 635 PUT: {deleted_dupe_635p} positions")
            print(f"Total deleted: {deleted_635p + deleted_640c + deleted_dupe_635p}")
            
        conn.close()
        
    except Exception as e:
        print(f"Error deleting mock positions: {e}")
        sys.exit(1)

if __name__ == "__main__":
    delete_mock_positions()