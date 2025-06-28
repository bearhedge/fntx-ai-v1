#!/usr/bin/env python3
"""
Quick database cleanup to remove far OTM contracts
"""
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.append('/home/info/fntx-ai-v1')
from backend.config.theta_config import DB_CONFIG

def run_cleanup():
    """Execute the cleanup to remove far OTM contracts"""
    
    print("🧹 Starting database cleanup...")
    print("=" * 50)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check current count
    cursor.execute("SELECT COUNT(*) as count FROM theta.options_ohlc")
    initial_count = cursor.fetchone()['count']
    print(f"📊 Initial OHLC records: {initial_count:,}")
    
    # Delete worthless OHLC records
    print("🗑️ Removing far OTM contracts...")
    
    cleanup_sql = """
    DELETE FROM theta.options_ohlc 
    WHERE contract_id IN (
        SELECT c.contract_id 
        FROM theta.options_contracts c
        WHERE c.symbol = 'SPY'
        AND (
            -- 2021: Keep strikes 395-445 (ATM 420 ±25)
            (EXTRACT(YEAR FROM c.expiration) = 2021 AND (c.strike < 395 OR c.strike > 445))
            OR
            -- 2022: Keep strikes 425-475 (ATM 450 ±25)  
            (EXTRACT(YEAR FROM c.expiration) = 2022 AND (c.strike < 425 OR c.strike > 475))
            OR
            -- 2023: Keep strikes 375-425 (ATM 400 ±25)
            (EXTRACT(YEAR FROM c.expiration) = 2023 AND (c.strike < 375 OR c.strike > 425))
            OR
            -- 2024: Keep strikes 475-525 (ATM 500 ±25)
            (EXTRACT(YEAR FROM c.expiration) = 2024 AND (c.strike < 475 OR c.strike > 525))
            OR
            -- 2025: Keep strikes 575-625 (ATM 600 ±25)
            (EXTRACT(YEAR FROM c.expiration) = 2025 AND (c.strike < 575 OR c.strike > 625))
        )
    )
    """
    
    cursor.execute(cleanup_sql)
    deleted_ohlc = cursor.rowcount
    print(f"🗑️ Deleted {deleted_ohlc:,} far OTM OHLC records")
    
    # Delete orphaned contracts
    print("🧹 Removing orphaned contracts...")
    cursor.execute("""
        DELETE FROM theta.options_contracts 
        WHERE contract_id NOT IN (
            SELECT DISTINCT contract_id FROM theta.options_ohlc
        )
    """)
    deleted_contracts = cursor.rowcount
    print(f"🗑️ Deleted {deleted_contracts:,} orphaned contracts")
    
    # Commit changes
    conn.commit()
    
    # Check final count
    cursor.execute("SELECT COUNT(*) as count FROM theta.options_ohlc")
    final_count = cursor.fetchone()['count']
    
    # Update statistics
    cursor.execute("ANALYZE theta.options_ohlc")
    cursor.execute("ANALYZE theta.options_contracts")
    
    cursor.close()
    conn.close()
    
    # Summary
    print("\n✅ Cleanup Complete!")
    print("=" * 50)
    print(f"📊 Before: {initial_count:,} records")
    print(f"📊 After:  {final_count:,} records")
    print(f"🗑️ Removed: {initial_count - final_count:,} records ({100*(initial_count-final_count)/initial_count:.1f}%)")
    print(f"💾 Space freed: ~{(initial_count - final_count) * 0.5 / 1024:.1f} MB")
    print("🚀 Database is now optimized for enhanced download!")

if __name__ == "__main__":
    run_cleanup()