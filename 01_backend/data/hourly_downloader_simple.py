#!/usr/bin/env python3
"""
Simplified Hourly Options Downloader
Downloads with smaller batches to avoid timeouts
"""
import sys
import requests
import psycopg2
import logging
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
    
    log_file = log_dir / f'hourly_simple_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class SimpleHourlyDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'contracts': 0,
            'records': 0,
            'errors': 0
        }
    
    def get_spy_price(self, date: datetime) -> float:
        """Get SPY closing price for a date"""
        try:
            import yfinance as yf
            spy = yf.Ticker("SPY")
            date_str = date.strftime('%Y-%m-%d')
            next_day = (date + timedelta(days=1)).strftime('%Y-%m-%d')
            hist = spy.history(start=date_str, end=next_day)
            if not hist.empty:
                return float(hist['Close'].iloc[0])
        except:
            pass
        return 300.0  # Default for Jan 2020
    
    def get_strikes_for_date(self, spy_price: float, interval: int = 5) -> Set[int]:
        """Get limited strike range based on SPY price"""
        # Only get strikes within ±3% of SPY price for testing
        min_strike = int(spy_price * 0.97 / interval) * interval
        max_strike = int(spy_price * 1.03 / interval + 1) * interval
        
        strikes = set()
        strike = min_strike
        while strike <= max_strike:
            strikes.add(strike)
            strike += interval
        
        return strikes
    
    def download_contract(self, date: datetime, exp_str: str, strike: int, right: str) -> bool:
        """Download single contract with hourly bars"""
        try:
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
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    bars = data['response']
                    if bars:
                        self.save_to_db(date, exp_str, strike, right, bars)
                        return True
            elif response.status_code == 472:
                self.logger.debug(f"No data for ${strike}{right}")
                
        except Exception as e:
            self.logger.error(f"Error downloading ${strike}{right}: {e}")
            self.stats['errors'] += 1
        
        return False
    
    def save_to_db(self, date: datetime, exp_str: str, strike: int, right: str, bars):
        """Save contract data to database"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
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
                    float(bar[1]),  # open
                    float(bar[2]),  # high
                    float(bar[3]),  # low
                    float(bar[4]),  # close
                    int(bar[5]),    # volume
                    int(bar[6]) if len(bar) > 6 else 0  # open_interest
                ))
            
            # Bulk insert
            execute_batch(cursor, """
                INSERT INTO theta.options_ohlc 
                (contract_id, datetime, open, high, low, close, volume, open_interest)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (contract_id, datetime) DO NOTHING
            """, records, page_size=100)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.stats['contracts'] += 1
            self.stats['records'] += len(records)
            
        except Exception as e:
            self.logger.error(f"Database error: {e}")
    
    def download_day(self, date: datetime):
        """Download options for a single day"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Processing {date.strftime('%Y-%m-%d')}")
        
        # Get SPY price
        spy_price = self.get_spy_price(date)
        self.logger.info(f"SPY price: ${spy_price:.2f}")
        
        # Get next trading day expiration
        exp_date = date + timedelta(days=1)
        while exp_date.weekday() > 4:
            exp_date += timedelta(days=1)
        exp_str = exp_date.strftime('%Y%m%d')
        
        # Get limited strikes
        strikes = self.get_strikes_for_date(spy_price, interval=5)
        self.logger.info(f"Testing {len(strikes)} strikes: ${min(strikes)}-${max(strikes)}")
        
        # Download each contract
        downloaded = 0
        for strike in sorted(strikes):
            for right in ['C', 'P']:
                if self.download_contract(date, exp_str, strike, right):
                    downloaded += 1
                    if downloaded % 5 == 0:
                        self.logger.info(f"Progress: {downloaded} contracts")
        
        self.logger.info(f"Downloaded {downloaded} contracts with {self.stats['records']} hourly records")
    
    def run(self, start_date: datetime, end_date: datetime):
        """Run downloader for date range"""
        self.logger.info("SIMPLIFIED HOURLY DOWNLOADER")
        self.logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        self.logger.info("Using 6 hourly bars per day instead of 390 minute bars")
        
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Weekday
                self.download_day(current)
            current += timedelta(days=1)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"COMPLETE: {self.stats['contracts']} contracts, {self.stats['records']} records")
        self.logger.info(f"Errors: {self.stats['errors']}")

def main():
    setup_logging()
    
    # Test with just 2 days
    start = datetime(2020, 1, 2)
    end = datetime(2020, 1, 3)
    
    downloader = SimpleHourlyDownloader()
    downloader.run(start, end)

if __name__ == "__main__":
    main()