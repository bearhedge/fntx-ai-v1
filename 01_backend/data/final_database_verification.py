#!/usr/bin/env python3
"""
Final database verification - ABSOLUTE confirmation of cleanliness
"""
import psycopg2
import sys
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def final_verification():
    """Provide ABSOLUTE confirmation that database is clean"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("🔍 FINAL ABSOLUTE DATABASE VERIFICATION")
    print("="*80)
    
    verification_results = {
        'database_clean': False,
        'schema_bulletproof': False,
        'ready_for_download': False,
        'issues_found': []
    }
    
    try:
        # 1. Check current data counts
        print("\n1. CURRENT DATABASE STATE")
        print("-" * 50)
        
        cursor.execute("""
        SELECT 'contracts' as table_name, COUNT(*) as count FROM theta.options_contracts
        UNION ALL
        SELECT 'ohlc', COUNT(*) FROM theta.options_ohlc
        UNION ALL  
        SELECT 'greeks', COUNT(*) FROM theta.options_greeks
        UNION ALL
        SELECT 'iv', COUNT(*) FROM theta.options_iv
        """)
        
        total_records = 0
        for table, count in cursor.fetchall():
            print(f"   {table:<12}: {count:,} records")
            total_records += count
        
        if total_records == 0:
            print("   ✅ Database is completely empty")
            verification_results['database_clean'] = True
        else:
            print(f"   ⚠️  Database contains {total_records:,} records")
            verification_results['issues_found'].append(f"Database not empty: {total_records} records")
        
        # 2. Contamination check using our bulletproof function
        print("\n2. CONTAMINATION DETECTION")
        print("-" * 50)
        
        cursor.execute("SELECT theta.quick_contamination_check()")
        contamination_status = cursor.fetchone()[0]
        print(f"   Status: {contamination_status}")
        
        if "CLEAN" in contamination_status:
            print("   ✅ No contamination detected")
        else:
            print("   ❌ Contamination found")
            verification_results['issues_found'].append("Contamination detected")
        
        # 3. Detailed 0DTE compliance check
        print("\n3. 0DTE COMPLIANCE VERIFICATION")
        print("-" * 50)
        
        cursor.execute("SELECT * FROM theta.validate_0dte_compliance()")
        results = cursor.fetchall()
        
        print(f"   {'Table':<20} {'Total':<10} {'Non-0DTE':<10} {'Compliance':<12}")
        print("   " + "-" * 55)
        
        all_compliant = True
        for table, total, non_0dte, compliance in results:
            print(f"   {table:<20} {total:<10} {non_0dte:<10} {compliance:<11.1f}%")
            if non_0dte > 0:
                all_compliant = False
                verification_results['issues_found'].append(f"{table} has {non_0dte} non-0DTE records")
        
        if all_compliant:
            print("   ✅ 100% 0DTE compliance across all tables")
        else:
            print("   ❌ Non-0DTE records found")
        
        # 4. Schema protection verification
        print("\n4. SCHEMA PROTECTION VERIFICATION")
        print("-" * 50)
        
        # Check triggers (count distinct names)
        cursor.execute("""
        SELECT COUNT(DISTINCT trigger_name) FROM information_schema.triggers 
        WHERE trigger_schema = 'theta' 
        AND trigger_name LIKE 'enforce_0dte%'
        """)
        
        trigger_count = cursor.fetchone()[0]
        if trigger_count == 3:  # Should have 3 triggers (ohlc, greeks, iv)
            print("   ✅ All 0DTE enforcement triggers active")
            verification_results['schema_bulletproof'] = True
        else:
            print(f"   ❌ Missing triggers: found {trigger_count}, expected 3")
            verification_results['issues_found'].append(f"Missing triggers: {trigger_count}/3")
        
        # Check constraints
        cursor.execute("""
        SELECT COUNT(*) FROM information_schema.table_constraints 
        WHERE table_schema = 'theta' 
        AND constraint_name = 'unique_contract'
        """)
        
        constraint_count = cursor.fetchone()[0]
        if constraint_count == 1:
            print("   ✅ Unique contract constraint active")
        else:
            print("   ❌ Unique contract constraint missing")
            verification_results['issues_found'].append("Missing unique constraint")
        
        # Check validation functions
        cursor.execute("""
        SELECT COUNT(*) FROM information_schema.routines 
        WHERE routine_schema = 'theta' 
        AND routine_name IN ('enforce_0dte', 'validate_0dte_compliance', 'quick_contamination_check')
        """)
        
        function_count = cursor.fetchone()[0]
        if function_count == 3:
            print("   ✅ All validation functions available")
        else:
            print(f"   ❌ Missing functions: found {function_count}, expected 3")
            verification_results['issues_found'].append(f"Missing functions: {function_count}/3")
        
        # 5. Test contamination rejection (if database is empty)
        if total_records == 0:
            print("\n5. TESTING CONTAMINATION REJECTION")
            print("-" * 50)
            
            try:
                # Try to insert contaminating data
                cursor.execute("""
                INSERT INTO theta.options_contracts 
                (contract_id, symbol, strike, expiration, option_type)
                VALUES (777777, 'SPY', 300, '2022-12-01', 'C')
                """)
                
                cursor.execute("""
                INSERT INTO theta.options_ohlc 
                (contract_id, datetime, open, high, low, close, volume)
                VALUES (777777, '2022-12-05 10:00:00', 1.0, 1.1, 0.9, 1.05, 100)
                """)
                
                print("   ❌ Contamination was NOT rejected")
                verification_results['issues_found'].append("Contamination rejection failed")
                
            except psycopg2.Error as e:
                if "NON-0DTE DATA REJECTED" in str(e):
                    print("   ✅ Contamination correctly rejected")
                else:
                    print(f"   ⚠️  Unexpected error: {e}")
                    verification_results['issues_found'].append(f"Unexpected rejection error: {e}")
            finally:
                conn.rollback()  # Clean up test
        
        # 6. Final assessment
        print("\n" + "="*80)
        print("📋 FINAL VERIFICATION ASSESSMENT")
        print("="*80)
        
        if not verification_results['issues_found']:
            verification_results['ready_for_download'] = True
            print("🎉 DATABASE IS ABSOLUTELY CLEAN AND READY")
            print("="*80)
            print("✅ Database is completely empty")
            print("✅ No contamination detected") 
            print("✅ 100% 0DTE compliance")
            print("✅ All schema protections active")
            print("✅ Contamination rejection working")
            print("\n🚀 READY FOR BULLETPROOF DECEMBER 2022 DOWNLOAD")
            
        else:
            print("❌ VERIFICATION FAILED - ISSUES FOUND")
            print("="*80)
            for issue in verification_results['issues_found']:
                print(f"❌ {issue}")
            print("\n🚫 NOT READY FOR DOWNLOAD - RESOLVE ISSUES FIRST")
        
        return verification_results
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        verification_results['issues_found'].append(f"Verification error: {e}")
        return verification_results
    finally:
        cursor.close()
        conn.close()

def show_database_summary():
    """Show a final summary of database readiness"""
    verification = final_verification()
    
    print("\n" + "🎯" * 27)
    if verification['ready_for_download']:
        print("DATABASE VERIFICATION: ✅ PASSED")
        print("CONTAMINATION PROTECTION: ✅ ACTIVE") 
        print("DOWNLOAD READINESS: ✅ READY")
        print("\n🔒 Database is BULLETPROOF and ready for clean download")
    else:
        print("DATABASE VERIFICATION: ❌ FAILED")
        print("CONTAMINATION PROTECTION: ⚠️  ISSUES FOUND")
        print("DOWNLOAD READINESS: ❌ NOT READY")
        print(f"\n🚫 {len(verification['issues_found'])} issues must be resolved")
    print("🎯" * 27)
    
    return verification['ready_for_download']

if __name__ == "__main__":
    show_database_summary()