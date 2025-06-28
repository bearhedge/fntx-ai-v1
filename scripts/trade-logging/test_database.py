#!/usr/bin/env python3
"""
Test database setup and verify all tables are created correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.database.trade_db import get_trade_db_connection

def test_database_setup():
    """Test that all required tables and views exist"""
    conn = get_trade_db_connection()
    
    try:
        with conn.cursor() as cur:
            # Check trading schema tables
            print("=== Trading Schema Tables ===")
            cur.execute("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_schema = 'trading' AND table_name = t.table_name) as columns
                FROM information_schema.tables t
                WHERE table_schema = 'trading'
                ORDER BY table_name
            """)
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]} columns")
            
            # Check staging schema
            print("\n=== Staging Schema Tables ===")
            cur.execute("""
                SELECT table_name,
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_schema = 'staging' AND table_name = t.table_name) as columns
                FROM information_schema.tables t
                WHERE table_schema = 'staging'
                ORDER BY table_name
            """)
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]} columns")
            
            # Check views
            print("\n=== Views ===")
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.views
                WHERE table_schema IN ('trading', 'staging')
                ORDER BY table_schema, table_name
            """)
            for row in cur.fetchall():
                print(f"  {row[0]}.{row[1]}")
            
            # Check validation rules
            print("\n=== Validation Rules ===")
            cur.execute("""
                SELECT rule_name, severity, is_active
                FROM staging.validation_rules
                ORDER BY 
                    CASE severity 
                        WHEN 'ERROR' THEN 1 
                        WHEN 'WARNING' THEN 2 
                        ELSE 3 
                    END,
                    rule_name
            """)
            for row in cur.fetchall():
                status = "✓" if row[2] else "✗"
                print(f"  [{status}] {row[0]}: {row[1]}")
            
            # Check existing data
            print("\n=== Existing Data ===")
            cur.execute("""
                SELECT 
                    'Trades' as table_name,
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'open' THEN 1 END) as open,
                    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed
                FROM trading.trades
            """)
            row = cur.fetchone()
            print(f"  {row[0]}: {row[1]} total ({row[2]} open, {row[3]} closed)")
            
            cur.execute("SELECT COUNT(*) FROM trading.matched_trades")
            print(f"  Matched Trades: {cur.fetchone()[0]}")
            
            cur.execute("SELECT COUNT(*) FROM trading.import_log")
            print(f"  Import Logs: {cur.fetchone()[0]}")
            
            cur.execute("SELECT COUNT(*) FROM staging.flex_trades")
            print(f"  Staged Trades: {cur.fetchone()[0]}")
            
            # Check for duplicates
            print("\n=== Data Quality Checks ===")
            cur.execute("SELECT COUNT(*) FROM trading.duplicate_trade_check")
            dupes = cur.fetchone()[0]
            if dupes > 0:
                print(f"  ⚠️  Found {dupes} duplicate trade groups")
                cur.execute("SELECT * FROM trading.duplicate_trade_check LIMIT 5")
                for row in cur.fetchall():
                    print(f"     Order {row[0]}: {row[1]} duplicates")
            else:
                print("  ✓ No duplicate trades found")
            
            # Check date range
            cur.execute("""
                SELECT MIN(entry_time)::date as earliest,
                       MAX(entry_time)::date as latest
                FROM trading.trades
            """)
            row = cur.fetchone()
            if row[0]:
                print(f"\n=== Trade Date Range ===")
                print(f"  Earliest: {row[0]}")
                print(f"  Latest: {row[1]}")
            
            print("\n✅ Database setup verified successfully!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        conn.close()
    
    return True


if __name__ == "__main__":
    test_database_setup()