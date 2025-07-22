#!/usr/bin/env python3
"""Fix December 2022 data by adding NULL IV records for OHLC without IV"""

import sys
import psycopg2
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def main():
    print("Fixing December 2022 IV data")
    print("=" * 80)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 1. Identify OHLC records without IV
    print("\n1. Finding OHLC records without IV:")
    cursor.execute("""
        SELECT 
            o.contract_id,
            o.datetime,
            c.expiration,
            c.strike,
            c.option_type
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_iv iv 
            WHERE iv.contract_id = o.contract_id 
            AND iv.datetime = o.datetime
        )
        ORDER BY o.datetime
    """)
    
    missing_iv_records = cursor.fetchall()
    print(f"   Found {len(missing_iv_records):,} OHLC records without IV")
    
    # 2. Check date range
    if missing_iv_records:
        first_date = missing_iv_records[0][2]
        last_date = missing_iv_records[-1][2]
        print(f"   Date range: {first_date} to {last_date}")
        
        # Verify they're all from December 2022
        dec_2022_count = sum(1 for r in missing_iv_records if r[2].year == 2022 and r[2].month == 12)
        print(f"   December 2022 records: {dec_2022_count:,}")
        
        if dec_2022_count != len(missing_iv_records):
            print(f"   WARNING: Not all missing IV records are from December 2022!")
            cursor.execute("""
                SELECT EXTRACT(YEAR FROM c.expiration) as year, 
                       EXTRACT(MONTH FROM c.expiration) as month,
                       COUNT(*) as count
                FROM theta.options_ohlc o
                JOIN theta.options_contracts c ON o.contract_id = c.contract_id
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM theta.options_iv iv 
                    WHERE iv.contract_id = o.contract_id 
                    AND iv.datetime = o.datetime
                )
                GROUP BY EXTRACT(YEAR FROM c.expiration), EXTRACT(MONTH FROM c.expiration)
                ORDER BY year, month
            """)
            results = cursor.fetchall()
            print("\n   Distribution by month:")
            for year, month, count in results:
                print(f"   {int(year)}-{int(month):02d}: {count:,} records")
    
    # 3. Insert NULL IV records
    print("\n2. Inserting NULL IV records for missing entries...")
    start_time = datetime.now()
    
    # Prepare batch insert
    iv_data = [(contract_id, dt, None) for contract_id, dt, _, _, _ in missing_iv_records]
    
    # Insert in batches
    batch_size = 1000
    total_inserted = 0
    
    for i in range(0, len(iv_data), batch_size):
        batch = iv_data[i:i + batch_size]
        cursor.executemany("""
            INSERT INTO theta.options_iv (contract_id, datetime, implied_volatility)
            VALUES (%s, %s, %s)
            ON CONFLICT (contract_id, datetime) DO NOTHING
        """, batch)
        total_inserted += cursor.rowcount
        if (i + batch_size) % 10000 == 0:
            conn.commit()
            print(f"   Inserted {i + batch_size:,} / {len(iv_data):,} records...")
    
    conn.commit()
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"   Inserted {total_inserted:,} IV records in {elapsed:.1f} seconds")
    
    # 4. Verify the fix
    print("\n3. Verifying the fix:")
    
    # Check current counts
    cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc")
    ohlc_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_greeks")
    greeks_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM theta.options_iv")
    iv_count = cursor.fetchone()[0]
    
    print(f"   OHLC records: {ohlc_count:,}")
    print(f"   Greeks records: {greeks_count:,}")
    print(f"   IV records: {iv_count:,}")
    
    if ohlc_count == greeks_count == iv_count:
        print(f"\n   ✓ SUCCESS! All three tables now have exactly {ohlc_count:,} records")
        print(f"   ✓ Dataset is perfectly congruent!")
    else:
        print(f"\n   Warning: Counts still don't match perfectly")
    
    # Check for any remaining OHLC without IV
    cursor.execute("""
        SELECT COUNT(*)
        FROM theta.options_ohlc o
        WHERE NOT EXISTS (
            SELECT 1 
            FROM theta.options_iv iv 
            WHERE iv.contract_id = o.contract_id 
            AND iv.datetime = o.datetime
        )
    """)
    remaining = cursor.fetchone()[0]
    print(f"\n   OHLC records without IV: {remaining}")
    
    # Count NULL IVs
    cursor.execute("SELECT COUNT(*) FROM theta.options_iv WHERE implied_volatility IS NULL")
    null_count = cursor.fetchone()[0]
    print(f"   Total NULL IV records: {null_count:,}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("December 2022 IV fix complete!")
    print("Dataset is now fully congruent across all months.")
    print("=" * 80)

if __name__ == "__main__":
    main()