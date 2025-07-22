#!/usr/bin/env python3
"""
Check the download status for SPY options data
"""
import sys
import os
import psycopg2
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.theta_config import DB_CONFIG

def check_download_status():
    """Check download status from theta.download_status table"""
    
    print("🔍 Checking SPY Options Download Status")
    print("=" * 80)
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if download_status table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'theta' 
                AND table_name = 'download_status'
            )
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("\n📊 Download Status Summary:")
            cursor.execute("""
                SELECT 
                    symbol,
                    data_type,
                    status,
                    COUNT(*) as count,
                    SUM(records_downloaded) as total_records,
                    MIN(start_date) as earliest_date,
                    MAX(end_date) as latest_date
                FROM theta.download_status
                WHERE symbol = 'SPY'
                GROUP BY symbol, data_type, status
                ORDER BY data_type, status
            """)
            
            results = cursor.fetchall()
            
            if results:
                print(f"{'Data Type':<15} {'Status':<15} {'Count':<10} {'Total Records':<15} {'Date Range'}")
                print("-" * 80)
                for row in results:
                    records = f"{row[4]:,}" if row[4] else "N/A"
                    date_range = f"{row[5]} to {row[6]}" if row[5] and row[6] else "N/A"
                    print(f"{row[1]:<15} {row[2]:<15} {row[3]:<10} {records:<15} {date_range}")
            else:
                print("No download status records found for SPY")
        else:
            print("❌ Download status table does not exist")
            
        # Check checkpoint file if it exists
        checkpoint_file = '/home/info/fntx-ai-v1/download_checkpoint.json'
        if os.path.exists(checkpoint_file):
            print(f"\n📁 Found checkpoint file: {checkpoint_file}")
            import json
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            print(f"   Last checkpoint: {checkpoint.get('timestamp', 'Unknown')}")
            if 'progress' in checkpoint:
                print(f"   Current expiration: {checkpoint['progress'].get('current_expiration', 'Unknown')}")
                print(f"   Progress: {checkpoint['progress'].get('expiration_index', 0)}/{checkpoint['progress'].get('total_expirations', 0)}")
            if 'stats' in checkpoint:
                stats = checkpoint['stats']
                print(f"\n   Statistics from last run:")
                print(f"   - Contracts processed: {stats.get('contracts_processed', 0):,}")
                print(f"   - Contracts skipped: {stats.get('contracts_skipped', 0):,}")
                print(f"   - OHLC records: {stats.get('ohlc_records', 0):,}")
                print(f"   - Greeks records: {stats.get('greeks_records', 0):,}")
                print(f"   - IV records: {stats.get('iv_records', 0):,}")
        
        # Check last download activity
        print("\n📅 Recent Download Activity:")
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT contract_id) as contracts_updated,
                COUNT(*) as records_added,
                MAX(datetime) as last_data_point
            FROM theta.options_ohlc
            WHERE datetime >= CURRENT_DATE - INTERVAL '7 days'
        """)
        
        recent = cursor.fetchone()
        if recent[0]:
            print(f"   Contracts updated in last 7 days: {recent[0]}")
            print(f"   Records added in last 7 days: {recent[1]:,}")
            print(f"   Last data point: {recent[2]}")
        else:
            print("   No recent download activity")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_download_status()