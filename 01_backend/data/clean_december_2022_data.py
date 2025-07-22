#!/usr/bin/env python3
"""
Clean December 2022 data from database
Ensures clean state before new download
"""
import sys
import psycopg2
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def clean_december_2022():
    """Remove all December 2022 SPY 0DTE data"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("CLEANING DECEMBER 2022 SPY 0DTE DATA")
        print("="*60)
        
        # First, get count of affected records
        cursor.execute("""
            SELECT COUNT(*) FROM theta.options_contracts 
            WHERE symbol = 'SPY' 
            AND expiration >= '2022-12-01' 
            AND expiration <= '2022-12-31'
        """)
        contract_count = cursor.fetchone()[0]
        
        if contract_count == 0:
            print("✅ No December 2022 data found - database is already clean")
            return
        
        print(f"Found {contract_count} December 2022 contracts to remove")
        
        # Get contract IDs
        cursor.execute("""
            SELECT contract_id FROM theta.options_contracts 
            WHERE symbol = 'SPY' 
            AND expiration >= '2022-12-01' 
            AND expiration <= '2022-12-31'
        """)
        contract_ids = [row[0] for row in cursor.fetchall()]
        
        # Count data in each table
        counts = {}
        for table in ['options_ohlc', 'options_greeks', 'options_iv']:
            cursor.execute(f"""
                SELECT COUNT(*) FROM theta.{table}
                WHERE contract_id = ANY(%s)
            """, (contract_ids,))
            counts[table] = cursor.fetchone()[0]
            print(f"  - {table}: {counts[table]:,} records")
        
        # Confirm deletion
        print("\n⚠️  This will permanently delete all December 2022 data!")
        response = input("Continue with deletion? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Deletion cancelled")
            return
        
        # Delete data
        print("\nDeleting data...")
        
        # Delete from data tables first (foreign key constraints)
        for table in ['options_ohlc', 'options_greeks', 'options_iv', 'options_oi']:
            cursor.execute(f"""
                DELETE FROM theta.{table}
                WHERE contract_id = ANY(%s)
            """, (contract_ids,))
            print(f"  ✓ Deleted from {table}")
        
        # Delete contracts
        cursor.execute("""
            DELETE FROM theta.options_contracts 
            WHERE symbol = 'SPY' 
            AND expiration >= '2022-12-01' 
            AND expiration <= '2022-12-31'
        """)
        print(f"  ✓ Deleted {contract_count} contracts")
        
        # Update download status if exists
        cursor.execute("""
            DELETE FROM theta.download_status
            WHERE symbol = 'SPY'
            AND start_date >= '2022-12-01'
            AND end_date <= '2022-12-31'
        """)
        
        conn.commit()
        print("\n✅ December 2022 data successfully cleaned")
        
        # Verify cleanup
        cursor.execute("""
            SELECT COUNT(*) FROM theta.options_contracts 
            WHERE symbol = 'SPY' 
            AND expiration >= '2022-12-01' 
            AND expiration <= '2022-12-31'
        """)
        remaining = cursor.fetchone()[0]
        
        if remaining == 0:
            print("✅ Verification passed - no December 2022 data remaining")
        else:
            print(f"⚠️  Warning: {remaining} contracts still remain")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during cleanup: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    clean_december_2022()