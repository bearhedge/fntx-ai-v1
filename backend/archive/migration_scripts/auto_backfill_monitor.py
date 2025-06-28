#!/usr/bin/env python3
"""
Monitor main download and automatically start Greeks/IV backfill when complete
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/auto_backfill_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_main_download_status():
    """Check if main download is complete"""
    checkpoint_file = '/home/info/fntx-ai-v1/download_checkpoint.json'
    
    try:
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        progress = data['progress']
        current = progress['expiration_index']
        total = progress['total_expirations']
        
        return current, total, current >= total
    except:
        return 0, 0, False

def estimate_backfill_time():
    """Estimate backfill time based on contract count"""
    import psycopg2
    from backend.config.theta_config import DB_CONFIG
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT oc.contract_id)
        FROM theta.options_contracts oc
        INNER JOIN theta.options_ohlc ohlc ON oc.contract_id = ohlc.contract_id
        LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id
        WHERE g.contract_id IS NULL
        AND oc.symbol = 'SPY'
    """)
    
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    # Estimate: 0.5 seconds per contract with 10 workers
    time_hours = (count * 0.5) / 10 / 3600
    
    return count, time_hours

def main():
    logger.info("Starting automatic backfill monitor...")
    
    while True:
        current, total, is_complete = check_main_download_status()
        
        if total > 0:
            progress_pct = (current / total) * 100
            logger.info(f"Main download progress: {current}/{total} ({progress_pct:.1f}%)")
        
        if is_complete:
            logger.info("Main download complete! Starting Greeks/IV backfill...")
            
            # Estimate backfill time
            contract_count, hours = estimate_backfill_time()
            logger.info(f"Found {contract_count:,} contracts needing Greeks/IV")
            logger.info(f"Estimated backfill time: {hours:.1f} hours")
            
            # Start backfill with reduced workers to avoid overloading
            cmd = [
                'python3', '/home/info/fntx-ai-v1/backfill_greeks_iv.py'
            ]
            
            subprocess.run(cmd)
            logger.info("Backfill process completed!")
            break
        
        # Wait 5 minutes before checking again
        time.sleep(300)

if __name__ == "__main__":
    # Add project path
    sys.path.append('/home/info/fntx-ai-v1')
    main()