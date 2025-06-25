#!/usr/bin/env python3
"""
Monitor ThetaTerminal download progress
"""
import psycopg2
import time
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.theta_config import DB_CONFIG

def monitor_progress():
    """Monitor download progress in real-time"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("ThetaTerminal Download Monitor")
    print("=" * 60)
    
    while True:
        cursor = conn.cursor()
        
        # Get overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT contract_id) as unique_contracts,
                MIN(datetime) as earliest_data,
                MAX(datetime) as latest_data,
                pg_size_pretty(pg_database_size('options_data')) as db_size
            FROM theta.options_ohlc
        """)
        
        stats = cursor.fetchone()
        
        # Get recent download status
        cursor.execute("""
            SELECT symbol, start_date, end_date, status, records_downloaded
            FROM theta.download_status
            WHERE status IN ('in_progress', 'completed')
            ORDER BY start_date DESC
            LIMIT 5
        """)
        
        recent = cursor.fetchall()
        
        # Clear screen and display
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print(f"Total Records: {stats[0]:,}")
        print(f"Unique Contracts: {stats[1]:,}")
        print(f"Date Range: {stats[2]} to {stats[3]}")
        print(f"Database Size: {stats[4]}")
        print()
        print("Recent Downloads:")
        print("-" * 60)
        print(f"{'Symbol':<6} {'Start Date':<12} {'End Date':<12} {'Status':<12} {'Records':<10}")
        print("-" * 60)
        
        for row in recent:
            print(f"{row[0]:<6} {row[1]} {row[2]} {row[3]:<12} {row[4] or 0:>10,}")
        
        print()
        print("Press Ctrl+C to exit")
        
        cursor.close()
        time.sleep(10)  # Update every 10 seconds

if __name__ == "__main__":
    try:
        monitor_progress()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")