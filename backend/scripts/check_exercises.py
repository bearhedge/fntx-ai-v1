#!/usr/bin/env python3
"""
Quick script to check exercise status in database
"""
import os
import sys
from datetime import datetime, timedelta

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '01_backend'))

from backend.data.database.trade_db import get_trade_db_connection


def check_exercises():
    """Check current exercise status"""
    conn = get_trade_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return
        
    try:
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'portfolio' 
                    AND table_name = 'option_exercises'
                )
            """)
            
            if not cursor.fetchone()[0]:
                print("❌ Exercise table doesn't exist!")
                print("Run: psql -d fntx_trading -f database/portfolio/003_exercise_tracking.sql")
                return
                
            # Get all exercises
            cursor.execute("""
                SELECT exercise_id, exercise_date, option_symbol, 
                       strike_price, option_type, contracts, 
                       shares_received, disposal_status,
                       disposal_order_id, disposal_price,
                       detection_time, disposal_time
                FROM portfolio.option_exercises
                ORDER BY exercise_date DESC, exercise_id DESC
            """)
            
            exercises = cursor.fetchall()
            
            if not exercises:
                print("No exercises found in database")
                print("\nThis is normal if:")
                print("  - No options have been exercised recently")
                print("  - Exercise detection hasn't run yet")
                print("\nTo test the system:")
                print("  1. Wait for an actual exercise, or")
                print("  2. Run: python3 scripts/test_exercise_system.py")
            else:
                print(f"Found {len(exercises)} exercise(s):\n")
                
                for ex in exercises:
                    (ex_id, ex_date, symbol, strike, opt_type, contracts, 
                     shares, status, order_id, disposal_price, 
                     detect_time, disposal_time) = ex
                     
                    print(f"Exercise #{ex_id}")
                    print(f"  Date: {ex_date}")
                    print(f"  Option: {symbol}")
                    print(f"  Type: {opt_type} ${strike}")
                    print(f"  Contracts: {contracts} ({shares} shares)")
                    print(f"  Status: {status}")
                    print(f"  Detected: {detect_time}")
                    
                    if order_id:
                        print(f"  Disposal Order: {order_id}")
                        print(f"  Disposal Price: ${disposal_price}")
                        print(f"  Order Time: {disposal_time}")
                    print()
                    
            # Check for pending disposals
            cursor.execute("""
                SELECT COUNT(*) FROM portfolio.option_exercises
                WHERE disposal_status = 'PENDING'
            """)
            pending = cursor.fetchone()[0]
            
            if pending > 0:
                print(f"\n⚠️  {pending} exercise(s) pending disposal")
                print("Run: python3 01_backend/scripts/exercise_disposal_asap.py")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


def check_recent_nav():
    """Check recent NAV snapshots"""
    print("\n" + "="*50)
    print("Recent NAV Snapshots")
    print("="*50)
    
    conn = get_trade_db_connection()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT snapshot_date, closing_nav, source, created_at
                FROM portfolio.daily_nav_snapshots
                ORDER BY snapshot_date DESC
                LIMIT 5
            """)
            
            snapshots = cursor.fetchall()
            
            if snapshots:
                for snap in snapshots:
                    date, nav, source, created = snap
                    print(f"{date}: ${nav:,.2f} ({source}) - Added {created}")
            else:
                print("No NAV snapshots found")
                print("Run: python3 01_backend/scripts/daily_flex_import.py")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("="*50)
    print("Exercise Management System Status")
    print("="*50)
    print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} HKT\n")
    
    check_exercises()
    check_recent_nav()