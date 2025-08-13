#!/usr/bin/env python3
"""
Test Exercise Detection and Disposal System
This script tests the complete flow from detection to disposal
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '01_backend'))

from backend.data.database.trade_db import get_trade_db_connection


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")


def check_database_connection():
    """Test database connectivity"""
    print_section("Testing Database Connection")
    try:
        conn = get_trade_db_connection()
        if conn:
            print("✅ Database connection successful")
            
            # Check exercise table exists
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'portfolio' 
                        AND table_name = 'option_exercises'
                    )
                """)
                exists = cursor.fetchone()[0]
                if exists:
                    print("✅ Exercise tracking table exists")
                else:
                    print("❌ Exercise tracking table missing")
                    print("   Run: psql -d fntx_trading -f /home/info/fntx-ai-v1/03_database/portfolio/003_exercise_tracking.sql")
            conn.close()
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def check_ibkr_credentials():
    """Check IBKR FlexQuery credentials"""
    print_section("Checking IBKR Credentials")
    
    token = os.getenv("IBKR_FLEX_TOKEN")
    query_id = os.getenv("IBKR_FLEX_QUERY_ID")
    
    if token and query_id:
        print("✅ IBKR_FLEX_TOKEN is set")
        print("✅ IBKR_FLEX_QUERY_ID is set")
        return True
    else:
        if not token:
            print("❌ IBKR_FLEX_TOKEN not set in environment")
        if not query_id:
            print("❌ IBKR_FLEX_QUERY_ID not set in environment")
        print("   Check .env file at /home/info/fntx-ai-v1/.env")
        return False


def check_ib_gateway():
    """Check IB Gateway connectivity"""
    print_section("Checking IB Gateway Connection")
    
    try:
        from ib_insync import IB
        ib = IB()
        ib.connect('127.0.0.1', 4001, clientId=99)
        print("✅ IB Gateway connection successful")
        ib.disconnect()
        return True
    except Exception as e:
        print(f"⚠️  IB Gateway not connected: {e}")
        print("   This is required for order placement")
        print("   Start IB Gateway and ensure it's running on port 4001")
        return False


def test_exercise_detection():
    """Test exercise detection script"""
    print_section("Testing Exercise Detection")
    
    try:
        # Import and test
        from scripts.exercise_detector import ExerciseDetector
        
        detector = ExerciseDetector()
        print("✅ Exercise detector imported successfully")
        
        # Check if we can request a report
        from services.ibkr_flex_query_enhanced import flex_query_enhanced
        reference_code = flex_query_enhanced.request_flex_report()
        
        if reference_code:
            print("✅ FlexQuery report requested successfully")
            print(f"   Reference code: {reference_code}")
            return True
        else:
            print("❌ Failed to request FlexQuery report")
            return False
            
    except Exception as e:
        print(f"❌ Exercise detection error: {e}")
        return False


def check_existing_exercises():
    """Check for any existing exercises in database"""
    print_section("Checking Existing Exercises")
    
    conn = get_trade_db_connection()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            # Get recent exercises
            cursor.execute("""
                SELECT exercise_date, option_symbol, strike_price, 
                       option_type, contracts, shares_received, 
                       disposal_status, disposal_time
                FROM portfolio.option_exercises
                ORDER BY exercise_date DESC
                LIMIT 5
            """)
            
            exercises = cursor.fetchall()
            
            if exercises:
                print(f"Found {len(exercises)} recent exercise(s):")
                for ex in exercises:
                    date, symbol, strike, opt_type, contracts, shares, status, disposal = ex
                    print(f"\n  Date: {date}")
                    print(f"  Option: {symbol}")
                    print(f"  Type: {opt_type} ${strike}")
                    print(f"  Contracts: {contracts} ({shares} shares)")
                    print(f"  Status: {status}")
                    if disposal:
                        print(f"  Disposal: {disposal}")
                        
                # Check for pending disposals
                cursor.execute("""
                    SELECT COUNT(*) FROM portfolio.option_exercises
                    WHERE disposal_status = 'PENDING'
                """)
                pending_count = cursor.fetchone()[0]
                
                if pending_count > 0:
                    print(f"\n⚠️  {pending_count} exercise(s) pending disposal")
            else:
                print("No exercises found in database")
                
    except Exception as e:
        print(f"Error checking exercises: {e}")
    finally:
        conn.close()


def simulate_exercise():
    """Add a simulated exercise for testing"""
    print_section("Simulating Exercise (Optional)")
    
    response = input("\nAdd a test exercise to database? (y/n): ")
    if response.lower() != 'y':
        print("Skipping simulation")
        return
        
    conn = get_trade_db_connection()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            # Insert test exercise
            test_date = datetime.now().date()
            cursor.execute("""
                INSERT INTO portfolio.option_exercises (
                    exercise_date, option_symbol, strike_price, 
                    option_type, contracts, shares_received,
                    detection_time, disposal_status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING exercise_id
            """, (
                test_date,
                'SPY   250715P00622000',  # Example symbol
                622.00,
                'PUT',
                1,
                100,
                datetime.now(),
                'PENDING',
                'TEST EXERCISE - Remove after testing'
            ))
            
            exercise_id = cursor.fetchone()[0]
            conn.commit()
            
            print(f"✅ Test exercise created (ID: {exercise_id})")
            print("   Run exercise_disposal_asap.py to test disposal")
            
    except Exception as e:
        print(f"Error creating test exercise: {e}")
        conn.rollback()
    finally:
        conn.close()


def run_full_test():
    """Run complete system test"""
    print_section("Exercise Detection & Disposal System Test")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} HKT")
    
    # Run all checks
    results = {
        'database': check_database_connection(),
        'ibkr_creds': check_ibkr_credentials(),
        'ib_gateway': check_ib_gateway(),
        'detection': test_exercise_detection()
    }
    
    # Check existing exercises
    check_existing_exercises()
    
    # Offer to simulate
    simulate_exercise()
    
    # Summary
    print_section("Test Summary")
    
    all_passed = all(results.values())
    critical_passed = results['database'] and results['ibkr_creds']
    
    print("\nComponent Status:")
    print(f"  Database: {'✅' if results['database'] else '❌'}")
    print(f"  IBKR Credentials: {'✅' if results['ibkr_creds'] else '❌'}")
    print(f"  IB Gateway: {'✅' if results['ib_gateway'] else '⚠️  (Required for trading)'}")
    print(f"  Exercise Detection: {'✅' if results['detection'] else '❌'}")
    
    if all_passed:
        print("\n✅ All systems operational!")
        print("\nNext steps:")
        print("  1. Run daily tasks: ./scripts/run_daily_tasks.sh")
        print("  2. Set up scheduling (see SCHEDULING_SETUP.md)")
        print("  3. Monitor logs in /home/info/fntx-ai-v1/logs/")
    elif critical_passed:
        print("\n⚠️  System partially operational")
        print("  - Exercise detection will work")
        print("  - IB Gateway needed for automated disposal")
    else:
        print("\n❌ Critical components missing")
        print("  - Fix database and IBKR credentials first")


if __name__ == "__main__":
    run_full_test()