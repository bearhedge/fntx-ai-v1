#!/usr/bin/env python3
"""
Sequential Hourly Downloader - One contract at a time with delays
"""
import sys
import requests
import psycopg2
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from pathlib import Path
from psycopg2.extras import execute_batch

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import THETA_HTTP_API, DB_CONFIG

# Setup logging
def setup_logging():
    log_dir = Path('/home/info/fntx-ai-v1/08_logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'hourly_sequential_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class SequentialHourlyDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        self.delay_between_requests = 0.5  # 500ms delay between API calls
    
    def download_single_contract(self, date: datetime, exp_str: str, strike: int, right: str):
        """Download one contract and save to database"""
        try:
            # API request
            url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
            params = {
                'root': 'SPY',
                'exp': exp_str,
                'strike': strike * 1000,
                'right': right,
                'start_date': date.strftime('%Y%m%d'),
                'end_date': date.strftime('%Y%m%d'),
                'ivl': 3600000  # Hourly bars
            }
            
            self.logger.info(f"Downloading ${strike}{right} exp {exp_str}...")
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    bars = data['response']
                    if bars:
                        # Save to database
                        self.save_to_database(date, exp_str, strike, right, bars)
                        self.logger.info(f"  ✅ Saved {len(bars)} hourly bars")
                    else:
                        self.logger.info(f"  ⚪ Empty data")
                else:
                    self.logger.info(f"  ⚪ No data")
            elif response.status_code == 472:
                self.logger.info(f"  ⚪ No data available")
            else:
                self.logger.warning(f"  ❌ Error {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"  ❌ Exception: {str(e)[:50]}")
        
        # IMPORTANT: Delay between requests
        time.sleep(self.delay_between_requests)
    
    def save_to_database(self, date: datetime, exp_str: str, strike: int, right: str, bars):
        """Save contract and hourly bars to database"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Insert contract
            exp_date = datetime.strptime(exp_str, '%Y%m%d')
            cursor.execute("""
                INSERT INTO theta.options_contracts 
                (symbol, expiration, strike, option_type, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (symbol, expiration, strike, option_type) 
                DO UPDATE SET updated_at = NOW()
                RETURNING contract_id
            """, ('SPY', exp_date, strike, right))
            
            contract_id = cursor.fetchone()[0]
            
            # Prepare hourly records
            records = []
            for bar in bars:
                timestamp = datetime.fromtimestamp(bar[0] / 1000)
                records.append((
                    contract_id,
                    timestamp,
                    float(bar[1]),
                    float(bar[2]),
                    float(bar[3]),
                    float(bar[4]),
                    int(bar[5]),
                    int(bar[6]) if len(bar) > 6 else 0
                ))
            
            # Insert hourly bars
            execute_batch(cursor, """
                INSERT INTO theta.options_ohlc 
                (contract_id, datetime, open, high, low, close, volume, open_interest)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (contract_id, datetime) DO NOTHING
            """, records)
            
            conn.commit()
            
        finally:
            cursor.close()
            conn.close()
    
    def download_day(self, date: datetime):
        """Download options for a single day"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"📅 Processing {date.strftime('%Y-%m-%d')}")
        
        # Get next expiration (1DTE)
        exp_date = date + timedelta(days=1)
        while exp_date.weekday() > 4:
            exp_date += timedelta(days=1)
        exp_str = exp_date.strftime('%Y%m%d')
        
        # For January 2020, use $5 intervals around $300
        strikes = [290, 295, 300, 305, 310]  # Limited strikes for testing
        
        self.logger.info(f"Expiration: {exp_str}")
        self.logger.info(f"Strikes: {strikes}")
        self.logger.info(f"Delay between requests: {self.delay_between_requests}s")
        
        # Download each contract sequentially
        contract_count = 0
        for strike in strikes:
            for right in ['C', 'P']:
                self.download_single_contract(date, exp_str, strike, right)
                contract_count += 1
        
        self.logger.info(f"✅ Processed {contract_count} contracts")
    
    def run(self, start_date: datetime, end_date: datetime):
        """Run downloader for date range"""
        self.logger.info("SEQUENTIAL HOURLY DOWNLOADER")
        self.logger.info("Downloading one contract at a time with delays")
        self.logger.info(f"Period: {start_date} to {end_date}")
        
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                self.download_day(current)
            current += timedelta(days=1)
        
        self.logger.info("\n✅ DOWNLOAD COMPLETE")

def main():
    setup_logging()
    
    # Test with Jan 2-3, 2020
    start = datetime(2020, 1, 2)
    end = datetime(2020, 1, 3)
    
    downloader = SequentialHourlyDownloader()
    downloader.run(start, end)

if __name__ == "__main__":
    main()