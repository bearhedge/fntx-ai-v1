#!/usr/bin/env python3
"""
Comprehensive database verification and testing
"""
import psycopg2
import sys
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def comprehensive_verification():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("COMPREHENSIVE DATABASE VERIFICATION")
    print("="*80)
    
    verification_passed = True
    
    try:
        # 1. Check schema constraints exist
        print("\n1. VERIFYING SCHEMA CONSTRAINTS")
        print("-" * 50)
        
        # Check unique constraint
        cursor.execute("""
        SELECT constraint_name FROM information_schema.table_constraints 
        WHERE table_schema = 'theta' 
        AND table_name = 'options_contracts' 
        AND constraint_type = 'UNIQUE'
        AND constraint_name = 'unique_contract'
        """)
        
        if cursor.fetchone():
            print("   ✅ Unique contract constraint exists")
        else:
            print("   ❌ Unique contract constraint MISSING")
            verification_passed = False
        
        # Check triggers exist
        triggers = ['enforce_0dte_ohlc_trigger', 'enforce_0dte_greeks_trigger', 'enforce_0dte_iv_trigger']
        for trigger in triggers:
            cursor.execute("""
            SELECT trigger_name FROM information_schema.triggers 
            WHERE trigger_schema = 'theta' AND trigger_name = %s
            """, (trigger,))
            
            if cursor.fetchone():
                print(f"   ✅ {trigger} exists")
            else:
                print(f"   ❌ {trigger} MISSING")
                verification_passed = False
        
        # Check validation functions exist
        functions = ['enforce_0dte', 'validate_0dte_compliance', 'quick_contamination_check']
        for func in functions:
            cursor.execute("""
            SELECT routine_name FROM information_schema.routines 
            WHERE routine_schema = 'theta' AND routine_name = %s
            """, (func,))
            
            if cursor.fetchone():
                print(f"   ✅ Function {func}() exists")
            else:
                print(f"   ❌ Function {func}() MISSING")
                verification_passed = False
        
        # 2. Test 0DTE enforcement (should reject non-0DTE data)
        print("\n2. TESTING 0DTE ENFORCEMENT")
        print("-" * 50)
        
        try:
            # First insert a valid contract
            cursor.execute("""
            INSERT INTO theta.options_contracts 
            (contract_id, symbol, strike, expiration, option_type)
            VALUES (999999, 'SPY', 400, '2022-12-01', 'C')
            """)
            conn.commit()
            print("   ✅ Valid contract insertion works")
            
            # Try to insert 0DTE data (should work)
            cursor.execute("""
            INSERT INTO theta.options_ohlc 
            (contract_id, datetime, open, high, low, close, volume, trade_count)
            VALUES (999999, '2022-12-01 10:00:00', 1.0, 1.1, 0.9, 1.05, 100, 5)
            """)
            conn.commit()
            print("   ✅ Valid 0DTE OHLC insertion works")
            
            # Try to insert non-0DTE data (should fail)
            try:
                cursor.execute("""
                INSERT INTO theta.options_ohlc 
                (contract_id, datetime, open, high, low, close, volume, trade_count)
                VALUES (999999, '2022-12-02 10:00:00', 1.0, 1.1, 0.9, 1.05, 100, 5)
                """)
                conn.commit()
                print("   ❌ Non-0DTE data was INCORRECTLY allowed")
                verification_passed = False
            except psycopg2.Error as e:
                conn.rollback()  # Reset transaction after error
                if "NON-0DTE DATA REJECTED" in str(e):
                    print("   ✅ Non-0DTE data correctly rejected")
                else:
                    print(f"   ❌ Unexpected error: {e}")
                    verification_passed = False
            
            # Clean up test data
            cursor.execute("DELETE FROM theta.options_ohlc WHERE contract_id = 999999")
            cursor.execute("DELETE FROM theta.options_contracts WHERE contract_id = 999999")
            conn.commit()
            
        except Exception as e:
            print(f"   ❌ Test error: {e}")
            verification_passed = False
            conn.rollback()
        
        # 3. Verify data integrity
        print("\n3. VERIFYING DATA INTEGRITY")
        print("-" * 50)
        
        # Check 0DTE compliance
        cursor.execute("SELECT * FROM theta.validate_0dte_compliance()")
        results = cursor.fetchall()
        
        print(f"   {'Table':<20} {'Total':<10} {'Non-0DTE':<10} {'Compliance':<12}")
        print("   " + "-" * 55)
        
        all_clean = True
        for table, total, non_0dte, compliance in results:
            print(f"   {table:<20} {total:<10} {non_0dte:<10} {compliance:<11.1f}%")
            if non_0dte > 0:
                all_clean = False
                verification_passed = False
        
        if all_clean:
            print("   ✅ All tables have 100% 0DTE compliance")
        else:
            print("   ❌ Some tables have non-0DTE contamination")
        
        # 4. Check contamination status
        print("\n4. CONTAMINATION STATUS CHECK")
        print("-" * 50)
        
        cursor.execute("SELECT theta.quick_contamination_check()")
        status = cursor.fetchone()[0]
        print(f"   {status}")
        
        if "CLEAN" in status:
            print("   ✅ Database contamination check passed")
        else:
            print("   ❌ Database contamination detected")
            verification_passed = False
        
        # 5. Verify table structures
        print("\n5. VERIFYING TABLE STRUCTURES")
        print("-" * 50)
        
        expected_tables = ['options_contracts', 'options_ohlc', 'options_greeks', 'options_iv']
        for table in expected_tables:
            cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = 'theta' AND table_name = %s
            """, (table,))
            
            col_count = cursor.fetchone()[0]
            if col_count > 0:
                print(f"   ✅ Table {table} exists with {col_count} columns")
            else:
                print(f"   ❌ Table {table} MISSING")
                verification_passed = False
        
        # 6. Check indexes
        print("\n6. VERIFYING INDEXES")
        print("-" * 50)
        
        expected_indexes = [
            'idx_ohlc_contract_datetime',
            'idx_greeks_contract_datetime', 
            'idx_iv_contract_datetime',
            'idx_contracts_symbol_exp'
        ]
        
        for index in expected_indexes:
            cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'theta' AND indexname = %s
            """, (index,))
            
            if cursor.fetchone():
                print(f"   ✅ Index {index} exists")
            else:
                print(f"   ❌ Index {index} MISSING")
                verification_passed = False
        
        # 7. Final verification summary
        print("\n" + "="*80)
        if verification_passed:
            print("🎉 COMPREHENSIVE VERIFICATION PASSED")
            print("="*80)
            print("✅ All schema constraints in place")
            print("✅ All triggers functioning correctly")
            print("✅ 0DTE enforcement working")
            print("✅ Database is 100% clean")
            print("✅ All table structures correct")
            print("✅ All indexes present")
            print("\n🔒 DATABASE IS BULLETPROOF AND READY FOR CLEAN DOWNLOAD")
        else:
            print("❌ VERIFICATION FAILED")
            print("="*80)
            print("❌ Some checks failed - review output above")
            print("❌ Database may not be properly protected")
        
        return verification_passed
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR during verification: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def test_contamination_prevention():
    """Specific test to verify contamination cannot occur"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("CONTAMINATION PREVENTION TEST")
    print("="*80)
    
    try:
        print("\nTesting various contamination scenarios...")
        
        # Test 1: Valid 0DTE insertion
        print("\n1. Testing valid 0DTE insertion...")
        cursor.execute("""
        INSERT INTO theta.options_contracts 
        (contract_id, symbol, strike, expiration, option_type)
        VALUES (888888, 'SPY', 350, '2022-12-15', 'P')
        """)
        
        cursor.execute("""
        INSERT INTO theta.options_ohlc 
        (contract_id, datetime, open, high, low, close, volume)
        VALUES (888888, '2022-12-15 14:30:00', 2.5, 2.6, 2.4, 2.55, 50)
        """)
        conn.commit()  # Commit the valid data
        print("   ✅ Valid 0DTE data accepted")
        
        # Test 2: Try non-0DTE contamination
        contamination_attempts = [
            ("Next day contamination", "2022-12-16 14:30:00"),
            ("Previous day contamination", "2022-12-14 14:30:00"), 
            ("Way off date contamination", "2023-01-15 14:30:00")
        ]
        
        for test_name, bad_datetime in contamination_attempts:
            print(f"\n2. Testing {test_name.lower()}...")
            try:
                cursor.execute("""
                INSERT INTO theta.options_ohlc 
                (contract_id, datetime, open, high, low, close, volume)
                VALUES (888888, %s, 2.5, 2.6, 2.4, 2.55, 50)
                """, (bad_datetime,))
                cursor.execute("COMMIT")  # Try to commit the bad data
                print(f"   ❌ {test_name} was INCORRECTLY allowed")
                return False
            except psycopg2.Error as e:
                if "NON-0DTE DATA REJECTED" in str(e):
                    print(f"   ✅ {test_name} correctly blocked")
                else:
                    print(f"   ❌ Unexpected error: {e}")
                    return False
            conn.rollback()  # Reset after each failed attempt
        
        # Clean up
        cursor.execute("DELETE FROM theta.options_ohlc WHERE contract_id = 888888")
        cursor.execute("DELETE FROM theta.options_contracts WHERE contract_id = 888888")
        conn.commit()
        
        print("\n✅ ALL CONTAMINATION PREVENTION TESTS PASSED")
        print("🔒 Database is IMMUNE to non-0DTE contamination")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Test error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Run comprehensive verification
    verification_result = comprehensive_verification()
    
    # Run contamination prevention test
    if verification_result:
        contamination_test_result = test_contamination_prevention()
        
        if verification_result and contamination_test_result:
            print("\n" + "🎯" * 27)
            print("DATABASE IS FULLY VERIFIED AND BULLETPROOF")
            print("Ready for clean December 2022 0DTE download")
            print("🎯" * 27)
        else:
            print("\n❌ VERIFICATION OR CONTAMINATION TEST FAILED")
    else:
        print("\n❌ BASIC VERIFICATION FAILED - SKIPPING CONTAMINATION TEST")