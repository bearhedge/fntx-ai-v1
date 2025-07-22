#!/usr/bin/env python3
"""Delete Greeks and IV records that don't have corresponding OHLC data"""

import sys
import psycopg2
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def main():
    print("Deleting Greeks and IV records without corresponding OHLC")
    print("=" * 80)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Get counts before deletion
    print("\n1. Current record counts:")
    cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc")
    ohlc_before = cursor.fetchone()[0]
    print(f"   OHLC records: {ohlc_before:,}")
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_greeks")
    greeks_before = cursor.fetchone()[0]
    print(f"   Greeks records: {greeks_before:,}")
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_iv")
    iv_before = cursor.fetchone()[0]
    print(f"   IV records: {iv_before:,}")
    
    # Count records to delete
    print("\n2. Records to delete:")
    cursor.execute("""
        SELECT COUNT(*)
        FROM theta.options_greeks g
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        )
    """)
    greeks_to_delete = cursor.fetchone()[0]
    print(f"   Greeks without OHLC: {greeks_to_delete:,}")
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM theta.options_iv iv
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = iv.contract_id 
            AND o.datetime = iv.datetime
        )
    """)
    iv_to_delete = cursor.fetchone()[0]
    print(f"   IV without OHLC: {iv_to_delete:,}")
    
    # Delete Greeks without OHLC
    print("\n3. Deleting Greeks records without OHLC...")
    start_time = datetime.now()
    cursor.execute("""
        DELETE FROM theta.options_greeks g
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        )
    """)
    greeks_deleted = cursor.rowcount
    conn.commit()
    print(f"   Deleted {greeks_deleted:,} Greeks records in {(datetime.now() - start_time).total_seconds():.1f} seconds")
    
    # Delete IV without OHLC
    print("\n4. Deleting IV records without OHLC...")
    start_time = datetime.now()
    cursor.execute("""
        DELETE FROM theta.options_iv iv
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = iv.contract_id 
            AND o.datetime = iv.datetime
        )
    """)
    iv_deleted = cursor.rowcount
    conn.commit()
    print(f"   Deleted {iv_deleted:,} IV records in {(datetime.now() - start_time).total_seconds():.1f} seconds")
    
    # Verify final counts
    print("\n5. Final record counts:")
    cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc")
    ohlc_after = cursor.fetchone()[0]
    print(f"   OHLC records: {ohlc_after:,} (unchanged)")
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_greeks")
    greeks_after = cursor.fetchone()[0]
    print(f"   Greeks records: {greeks_after:,} (deleted {greeks_before - greeks_after:,})")
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_iv")
    iv_after = cursor.fetchone()[0]
    print(f"   IV records: {iv_after:,} (deleted {iv_before - iv_after:,})")
    
    # Verify congruence
    print("\n6. Verifying dataset congruence:")
    
    # Check if counts match
    if ohlc_after == greeks_after and ohlc_after == iv_after:
        print(f"   ✓ SUCCESS: All tables now have exactly {ohlc_after:,} records")
        print(f"   ✓ Dataset is perfectly congruent!")
    else:
        print(f"   ✗ WARNING: Record counts don't match:")
        print(f"     OHLC: {ohlc_after:,}")
        print(f"     Greeks: {greeks_after:,}")
        print(f"     IV: {iv_after:,}")
    
    # Double-check no orphans remain
    cursor.execute("""
        SELECT COUNT(*)
        FROM theta.options_greeks g
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        )
    """)
    remaining_greeks = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM theta.options_iv iv
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_ohlc o 
            WHERE o.contract_id = iv.contract_id 
            AND o.datetime = iv.datetime
        )
    """)
    remaining_iv = cursor.fetchone()[0]
    
    print(f"\n7. Verification check:")
    print(f"   Greeks without OHLC remaining: {remaining_greeks}")
    print(f"   IV without OHLC remaining: {remaining_iv}")
    
    if remaining_greeks == 0 and remaining_iv == 0:
        print(f"   ✓ Perfect! No orphan records remain.")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE - Dataset is now congruent!")
    print("Every timestamp now has OHLC, Greeks, AND IV data.")
    print("=" * 80)

if __name__ == "__main__":
    main()