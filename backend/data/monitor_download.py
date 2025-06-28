#!/usr/bin/env python3
"""
Monitor ThetaData Download Progress
Real-time monitoring of Greeks, IV, and historical data downloads
"""
import sys
import time
import psycopg2
from datetime import datetime
import os

sys.path.append('/home/info/fntx-ai-v1')
from backend.config.theta_config import DB_CONFIG

def monitor_downloads():
    """Monitor download progress in real-time"""
    
    print("📊 ThetaData Download Monitor")
    print("=" * 50)
    print("🔄 Refreshing every 30 seconds...")
    print("Press Ctrl+C to stop monitoring")
    print()
    
    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Clear screen (works on most terminals)
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(f"📊 ThetaData Download Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
            
            # Overall summary by data type
            cursor.execute("""
                SELECT data_type,
                       COUNT(*) as total_batches,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                       SUM(COALESCE(records_downloaded, 0)) as total_records
                FROM theta.download_status
                WHERE symbol = 'SPY'
                GROUP BY data_type
                ORDER BY data_type
            """)
            
            print("📈 Summary by Data Type:")
            print("Type     | Batches | Done | Progress | Failed | Records")
            print("-" * 60)
            
            for row in cursor.fetchall():
                data_type, total, completed, in_progress, failed, records = row
                print(f"{data_type:8} | {total:7} | {completed:4} | {in_progress:8} | {failed:6} | {records:,}")
            
            print()
            
            # Recent activity
            cursor.execute("""
                SELECT data_type, status, start_date, end_date, 
                       records_downloaded, started_at, completed_at
                FROM theta.download_status
                WHERE symbol = 'SPY' 
                AND (status = 'in_progress' OR completed_at > NOW() - INTERVAL '1 hour')
                ORDER BY started_at DESC
                LIMIT 10
            """)
            
            print("🔄 Recent Activity (Last Hour + In Progress):")
            print("Type     | Status     | Period         | Records   | Started")
            print("-" * 70)
            
            recent_results = cursor.fetchall()
            if recent_results:
                for row in recent_results:
                    data_type, status, start_date, end_date, records, started_at, completed_at = row
                    records_str = f"{records:,}" if records else "0"
                    started_str = started_at.strftime('%H:%M') if started_at else "N/A"
                    print(f"{data_type:8} | {status:10} | {start_date}-{end_date} | {records_str:8} | {started_str}")
            else:
                print("No recent activity")
            
            print()
            
            # Progress by year
            cursor.execute("""
                SELECT EXTRACT(YEAR FROM start_date) as year,
                       data_type,
                       COUNT(*) as batches,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                       SUM(COALESCE(records_downloaded, 0)) as records
                FROM theta.download_status
                WHERE symbol = 'SPY'
                GROUP BY EXTRACT(YEAR FROM start_date), data_type
                ORDER BY year DESC, data_type
            """)
            
            print("📅 Progress by Year:")
            print("Year | Type     | Batches | Done | Records")
            print("-" * 45)
            
            for row in cursor.fetchall():
                year, data_type, batches, completed, records = row
                year_int = int(year) if year else 0
                print(f"{year_int} | {data_type:8} | {batches:7} | {completed:4} | {records:,}")
            
            cursor.close()
            conn.close()
            
            print()
            print("🔄 Auto-refreshing in 30 seconds... (Ctrl+C to stop)")
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    monitor_downloads()