#!/usr/bin/env python3
"""
ThetaTerminal Historical Data Downloader
Downloads 4 years of SPY options data with intelligent resumption
"""
import os
import sys
import time
import json
import logging
import requests
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd
from tqdm import tqdm

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.theta_config import *

# Setup logging
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class ThetaDownloader:
    """Downloads historical options data from ThetaTerminal"""
    
    def __init__(self):
        self.conn = self._connect_db()
        self.session = requests.Session()
        self.stats = {
            'contracts_processed': 0,
            'records_downloaded': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    def _connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            logger.info("Connected to database successfully")
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def get_spy_expirations(self, start_date: str, end_date: str) -> List[str]:
        """Get all SPY expiration dates in range"""
        expirations = []
        
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        current = start
        
        while current <= end:
            # SPY has expirations on Mon, Wed, Fri
            if current.weekday() in [0, 2, 4]:  # Monday, Wednesday, Friday
                expirations.append(current.strftime("%Y%m%d"))
            
            # Monthly options (3rd Friday)
            if current.weekday() == 4 and 15 <= current.day <= 21:
                exp_str = current.strftime("%Y%m%d")
                if exp_str not in expirations:
                    expirations.append(exp_str)
            
            current += timedelta(days=1)
        
        return sorted(expirations)
    
    def get_strikes_for_date(self, expiration: str) -> List[int]:
        """Get relevant strikes for an expiration date"""
        # Estimate ATM based on year
        year = int(expiration[:4])
        atm = SPY_CONFIG['atm_estimates'].get(year, 500)
        
        # Get strikes within range
        strike_range = SPY_CONFIG['strike_range']
        strikes = list(range(atm - strike_range, atm + strike_range + 1))
        
        return strikes
    
    def check_download_status(self, symbol: str, start_date: str, end_date: str, data_type: str) -> bool:
        """Check if data has already been downloaded"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT status FROM theta.download_status
            WHERE symbol = %s AND start_date = %s AND end_date = %s 
            AND data_type = %s AND status = 'completed'
        """, (symbol, start_date, end_date, data_type))
        
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    
    def mark_download_status(self, symbol: str, start_date: str, end_date: str, 
                           data_type: str, status: str, records: int = 0, error: str = None):
        """Update download status in database"""
        cursor = self.conn.cursor()
        
        if status == 'in_progress':
            cursor.execute("""
                INSERT INTO theta.download_status 
                (symbol, start_date, end_date, data_type, status, started_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (symbol, start_date, end_date, data_type) 
                DO UPDATE SET status = EXCLUDED.status, started_at = NOW()
            """, (symbol, start_date, end_date, data_type, status))
        
        elif status == 'completed':
            cursor.execute("""
                UPDATE theta.download_status 
                SET status = %s, records_downloaded = %s, completed_at = NOW()
                WHERE symbol = %s AND start_date = %s AND end_date = %s AND data_type = %s
            """, (status, records, symbol, start_date, end_date, data_type))
        
        elif status == 'failed':
            cursor.execute("""
                UPDATE theta.download_status 
                SET status = %s, error_message = %s
                WHERE symbol = %s AND start_date = %s AND end_date = %s AND data_type = %s
            """, (status, error, symbol, start_date, end_date, data_type))
        
        self.conn.commit()
        cursor.close()
    
    def download_ohlc_data(self, expiration: str, strike: int, option_type: str,
                          start_date: str, end_date: str) -> int:
        """Download OHLC data for a single contract"""
        url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
        params = {
            'root': SPY_CONFIG['symbol'],
            'exp': expiration,
            'strike': strike * 1000,  # Strike in thousandths
            'right': option_type,
            'start_date': start_date,
            'end_date': end_date,
            'ivl': DOWNLOAD_CONFIG['interval_ms']
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                if "No data" in response.text:
                    return 0  # No data for this contract
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    return -1
            
            data = response.json()
            if not data.get('response'):
                return 0
            
            # Get or create contract ID
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT theta.get_or_create_contract(%s, %s, %s, %s)
            """, (SPY_CONFIG['symbol'], 
                  datetime.strptime(expiration, "%Y%m%d").date(), 
                  strike, 
                  option_type))
            
            contract_id = cursor.fetchone()[0]
            
            # Prepare data for bulk insert
            records = []
            for row in data['response']:
                # Format: [ms_of_day, open, high, low, close, volume, count, date]
                date_str = str(row[7])
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                
                # Convert ms_of_day to full timestamp
                ms_of_day = row[0]
                timestamp = date_obj + timedelta(milliseconds=ms_of_day)
                
                records.append((
                    contract_id,
                    timestamp,
                    row[1],  # open
                    row[2],  # high
                    row[3],  # low
                    row[4],  # close
                    row[5],  # volume
                    row[6]   # count
                ))
            
            # Bulk insert
            if records:
                execute_batch(cursor, """
                    INSERT INTO theta.options_ohlc 
                    (contract_id, datetime, open, high, low, close, volume, trade_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, records, page_size=1000)
                
                self.conn.commit()
            
            cursor.close()
            return len(records)
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {expiration} {strike}{option_type}: {e}")
            return -1
        except Exception as e:
            logger.error(f"Error processing {expiration} {strike}{option_type}: {e}")
            self.conn.rollback()
            return -1
    
    def download_date_range(self, start_date: str, end_date: str):
        """Download all options data for a date range"""
        logger.info(f"Downloading SPY options from {start_date} to {end_date}")
        
        # Check if already downloaded
        if self.check_download_status(SPY_CONFIG['symbol'], start_date, end_date, 'ohlc'):
            logger.info(f"Data for {start_date} to {end_date} already downloaded")
            return
        
        # Mark as in progress
        self.mark_download_status(SPY_CONFIG['symbol'], start_date, end_date, 'ohlc', 'in_progress')
        
        # Get all expirations in range
        expirations = self.get_spy_expirations(start_date, end_date)
        logger.info(f"Found {len(expirations)} expiration dates")
        
        total_records = 0
        
        # Process each expiration
        for exp_idx, expiration in enumerate(tqdm(expirations, desc="Expirations")):
            strikes = self.get_strikes_for_date(expiration)
            
            for strike in tqdm(strikes, desc=f"Exp {expiration}", leave=False):
                for option_type in ['C', 'P']:
                    # Rate limiting
                    time.sleep(DOWNLOAD_CONFIG['rate_limit_delay'])
                    
                    # Download with retries
                    for attempt in range(DOWNLOAD_CONFIG['max_retries']):
                        records = self.download_ohlc_data(
                            expiration, strike, option_type, start_date, end_date
                        )
                        
                        if records >= 0:
                            total_records += records
                            self.stats['contracts_processed'] += 1
                            self.stats['records_downloaded'] += records
                            break
                        else:
                            if attempt < DOWNLOAD_CONFIG['max_retries'] - 1:
                                time.sleep(DOWNLOAD_CONFIG['retry_delay'])
                            else:
                                self.stats['errors'] += 1
            
            # Log progress
            if (exp_idx + 1) % 10 == 0:
                logger.info(f"Progress: {exp_idx + 1}/{len(expirations)} expirations, "
                          f"{total_records:,} records downloaded")
        
        # Mark as completed
        self.mark_download_status(SPY_CONFIG['symbol'], start_date, end_date, 'ohlc', 
                                'completed', total_records)
        
        logger.info(f"Completed {start_date} to {end_date}: {total_records:,} records")
    
    def download_all_data(self):
        """Download all historical data in batches"""
        start = datetime.strptime(DOWNLOAD_CONFIG['start_date'], "%Y%m%d")
        end = datetime.strptime(DOWNLOAD_CONFIG['end_date'], "%Y%m%d")
        
        logger.info(f"Starting full download from {start.date()} to {end.date()}")
        
        # Process in monthly batches
        current = start
        while current < end:
            batch_end = min(current + timedelta(days=DOWNLOAD_CONFIG['batch_size_days']), end)
            
            batch_start_str = current.strftime("%Y%m%d")
            batch_end_str = batch_end.strftime("%Y%m%d")
            
            try:
                self.download_date_range(batch_start_str, batch_end_str)
            except Exception as e:
                logger.error(f"Batch {batch_start_str} to {batch_end_str} failed: {e}")
                self.mark_download_status(SPY_CONFIG['symbol'], batch_start_str, 
                                        batch_end_str, 'ohlc', 'failed', error=str(e))
            
            current = batch_end + timedelta(days=1)
        
        # Print final statistics
        duration = datetime.now() - self.stats['start_time']
        logger.info(f"""
        Download Complete!
        ==================
        Duration: {duration}
        Contracts processed: {self.stats['contracts_processed']:,}
        Records downloaded: {self.stats['records_downloaded']:,}
        Errors: {self.stats['errors']:,}
        """)
    
    def close(self):
        """Clean up resources"""
        if self.conn:
            self.conn.close()
        self.session.close()


def main():
    """Main entry point"""
    logger.info("ThetaTerminal Data Downloader Starting...")
    
    downloader = ThetaDownloader()
    
    try:
        # For testing, download just one week
        # downloader.download_date_range('20240601', '20240607')
        
        # For production, download all data
        downloader.download_all_data()
        
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        downloader.close()


if __name__ == "__main__":
    main()