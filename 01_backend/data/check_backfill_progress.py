#!/usr/bin/env python3
"""
Check progress of the final minutes backfill
"""
import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'options_data',
    'user': 'info'
}

def check_progress():
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Check how many days have 3:59 PM data
    query = """
    WITH days_with_359pm AS (
        SELECT DATE(datetime) as trading_date,
               COUNT(DISTINCT contract_id) as contracts_with_359pm
        FROM theta.options_ohlc
        WHERE datetime::time = '15:59:00'
        GROUP BY DATE(datetime)
    ),
    total_days AS (
        SELECT COUNT(DISTINCT DATE(datetime)) as total
        FROM theta.options_ohlc
    )
    SELECT 
        (SELECT COUNT(*) FROM days_with_359pm) as days_completed,
        (SELECT total FROM total_days) as total_days,
        (SELECT MAX(trading_date) FROM days_with_359pm) as last_completed_date
    """
    
    with conn.cursor() as cur:
        cur.execute(query)
        result = cur.fetchone()
        
        days_completed = result[0] or 0
        total_days = result[1] or 0
        last_date = result[2]
        
        print(f"Backfill Progress Report")
        print(f"========================")
        print(f"Days completed: {days_completed}/{total_days} ({days_completed/total_days*100:.1f}%)")
        print(f"Last completed date: {last_date}")
        
        # Check records added
        cur.execute("""
            SELECT COUNT(*) 
            FROM theta.options_ohlc 
            WHERE datetime::time = '15:59:00'
        """)
        new_records = cur.fetchone()[0]
        
        print(f"New 3:59 PM records: {new_records:,}")
        
        # Estimate time remaining
        if days_completed > 0:
            # Get runtime from log
            try:
                with open('/home/info/fntx-ai-v1/08_logs/backfill_final_minutes.log', 'r') as f:
                    first_line = f.readline()
                    if 'Starting' in first_line:
                        start_time = datetime.strptime(first_line[:19], '%Y-%m-%d %H:%M:%S')
                        elapsed = datetime.now() - start_time
                        rate = days_completed / elapsed.total_seconds() * 3600  # days per hour
                        remaining_hours = (total_days - days_completed) / rate
                        print(f"Estimated time remaining: {remaining_hours:.1f} hours")
            except:
                pass
    
    conn.close()

if __name__ == "__main__":
    check_progress()