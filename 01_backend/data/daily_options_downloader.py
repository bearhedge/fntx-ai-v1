#!/usr/bin/env python3
"""
Daily-Focused Options Downloader with Dynamic Strike Ranging
Downloads options data based on actual daily SPY prices, focusing on same-day expiring options
"""
import sys
import os
import requests
import psycopg2
import time
import logging
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional
import threading
from pathlib import Path

sys.path.append('/home/info/fntx-ai-v1')
from backend_01.config.theta_config import THETA_HTTP_API, DB_CONFIG

# Setup logging
def setup_logging():
    log_dir = Path('/home/info/fntx-ai-v1/logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'daily_options_downloader_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

class DailyOptionsDownloader:
    """Downloads options data using daily-aware dynamic strike selection"""
    
    def __init__(self, max_workers: int = 10):
        self.logger = setup_logging()
        self.session = requests.Session()
        self.max_workers = max_workers
        self.checkpoint_file = '/home/info/fntx-ai-v1/daily_download_checkpoint.json'
        
        # Statistics
        self.stats = {
            'dates_processed': 0,
            'contracts_downloaded': 0,
            'contracts_skipped': 0,
            'strikes_with_volume': 0,
            'total_records': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        self.logger.info("🚀 Daily Options Downloader initialized")
        self.logger.info(f"📊 Strategy: Dynamic strike ranging based on daily SPY prices")
    
    def get_spy_ohlc(self, date: datetime) -> Optional[Dict]:
        """Get SPY OHLC for a specific date"""
        try:
            date_str = date.strftime('%Y%m%d')
            url = f"{THETA_HTTP_API}/v2/hist/stock/ohlc"
            params = {
                'root': 'SPY',
                'start_date': date_str,
                'end_date': date_str,
                'ivl': 86400000  # Daily interval
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('response') and len(data['response']) > 0:
                    ohlc = data['response'][0]
                    return {
                        'date': date,
                        'open': float(ohlc[1]),
                        'high': float(ohlc[2]),
                        'low': float(ohlc[3]),
                        'close': float(ohlc[4]),
                        'volume': int(ohlc[5])
                    }
            else:
                self.logger.error(f"Failed to get SPY OHLC for {date_str}: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error getting SPY OHLC for {date}: {e}")
        
        return None
    
    def calculate_strike_range(self, spy_price: float, days_to_expiry: int, 
                              volatility_factor: float = 0.02) -> Tuple[int, int]:
        """
        Calculate dynamic strike range based on:
        1. Current SPY price
        2. Days to expiry
        3. Expected volatility
        """
        # Base expected move on time to expiry
        if days_to_expiry == 0:  # Same-day expiry
            # Tight range for 0DTE: ±3%
            move_percent = 0.03
        elif days_to_expiry <= 2:  # 1-2 days
            # Slightly wider: ±4%
            move_percent = 0.04
        elif days_to_expiry <= 7:  # Weekly
            # Weekly range: ±5%
            move_percent = 0.05
        elif days_to_expiry <= 30:  # Monthly
            # Monthly range: ±8%
            move_percent = 0.08
        else:  # Longer term
            # Wider range: ±10%
            move_percent = 0.10
        
        # Calculate strikes
        min_strike = int(spy_price * (1 - move_percent))
        max_strike = int(spy_price * (1 + move_percent))
        
        # Ensure reasonable bounds
        min_strike = max(min_strike, 50)  # SPY unlikely below $50
        max_strike = min(max_strike, 1000)  # SPY unlikely above $1000
        
        return min_strike, max_strike
    
    def get_expiring_options(self, date: datetime) -> List[str]:
        """Get all options expiring on or shortly after the given date"""
        try:
            # Get list of all expirations
            url = f"{THETA_HTTP_API}/v2/list/expirations"
            params = {'root': 'SPY'}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                all_expirations = data.get('response', [])
                
                # Filter for expirations within next 30 days from date
                relevant_expirations = []
                date_str = date.strftime('%Y%m%d')
                date_plus_30 = (date + timedelta(days=30)).strftime('%Y%m%d')
                
                for exp in all_expirations:
                    exp_str = str(exp)
                    if date_str <= exp_str <= date_plus_30:
                        relevant_expirations.append(exp_str)
                
                return relevant_expirations
        except Exception as e:
            self.logger.error(f"Error getting expirations: {e}")
        
        return []
    
    def download_option_data(self, date: datetime, expiration: str, strike: int, 
                           option_type: str, spy_ohlc: Dict) -> Dict:
        """Download data for a specific option contract"""
        try:
            # Get or create contract
            conn = psycopg2.connect(**DB_CONFIG)
            contract_id = self.get_or_create_contract(conn, 'SPY', expiration, strike, option_type)
            
            if not contract_id:
                return {'status': 'error', 'reason': 'contract_creation_failed'}
            
            # Download parameters
            params = {
                'root': 'SPY',
                'exp': expiration,
                'strike': strike * 1000,  # API expects strike * 1000
                'right': option_type,
                'start_date': date.strftime('%Y%m%d'),
                'end_date': date.strftime('%Y%m%d'),
                'ivl': 60000  # 1-minute intervals
            }
            
            # Download OHLC data
            ohlc_url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
            ohlc_response = self.session.get(ohlc_url, params=params, timeout=30)
            
            records_downloaded = 0
            if ohlc_response.status_code == 200:
                data = ohlc_response.json()
                if data.get('response'):
                    records_downloaded = self.store_ohlc_data(contract_id, data['response'])
                    
                    # Track if this strike had volume
                    if records_downloaded > 0:
                        self.stats['strikes_with_volume'] += 1
            
            # Download Greeks data
            greeks_url = f"{THETA_HTTP_API}/v2/hist/option/greeks"
            greeks_response = self.session.get(greeks_url, params=params, timeout=30)
            
            if greeks_response.status_code == 200:
                data = greeks_response.json()
                if data.get('response'):
                    self.store_greeks_data(contract_id, data['response'])
            
            conn.close()
            
            self.stats['contracts_downloaded'] += 1
            self.stats['total_records'] += records_downloaded
            
            return {
                'status': 'success',
                'contract_id': contract_id,
                'records': records_downloaded
            }
            
        except Exception as e:
            self.logger.error(f"Error downloading {expiration} {strike}{option_type}: {e}")
            self.stats['errors'] += 1
            return {'status': 'error', 'reason': str(e)}
    
    def process_date(self, date: datetime):
        """Process all relevant options for a specific date"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"📅 Processing date: {date.strftime('%Y-%m-%d')}")
        
        # Get SPY OHLC for the date
        spy_ohlc = self.get_spy_ohlc(date)
        if not spy_ohlc:
            self.logger.warning(f"⚠️ No SPY data for {date}, skipping")
            return
        
        self.logger.info(f"📊 SPY: Open=${spy_ohlc['open']:.2f}, High=${spy_ohlc['high']:.2f}, "
                        f"Low=${spy_ohlc['low']:.2f}, Close=${spy_ohlc['close']:.2f}")
        
        # Get relevant expirations
        expirations = self.get_expiring_options(date)
        if not expirations:
            self.logger.warning(f"⚠️ No expirations found for {date}")
            return
        
        # Process each expiration
        for expiration in expirations:
            exp_date = datetime.strptime(expiration, '%Y%m%d')
            days_to_expiry = (exp_date - date).days
            
            # Use opening price for strike calculation
            base_price = spy_ohlc['open']
            min_strike, max_strike = self.calculate_strike_range(base_price, days_to_expiry)
            
            self.logger.info(f"\n🎯 Expiration: {expiration} (DTE: {days_to_expiry})")
            self.logger.info(f"📊 Strike range: ${min_strike} - ${max_strike} "
                           f"(based on SPY open ${base_price:.2f})")
            
            # Build list of contracts to download
            contracts = []
            for strike in range(min_strike, max_strike + 1):
                for option_type in ['C', 'P']:
                    contracts.append((date, expiration, strike, option_type, spy_ohlc))
            
            # Download in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for contract in contracts:
                    future = executor.submit(
                        self.download_option_data, 
                        contract[0], contract[1], contract[2], contract[3], contract[4]
                    )
                    futures.append(future)
                
                # Wait for completion
                for future in as_completed(futures):
                    result = future.result()
                    # Progress update every 20 contracts
                    if len(futures) > 0 and len(futures) % 20 == 0:
                        self.logger.info(f"Progress: {self.stats['contracts_downloaded']} downloaded, "
                                       f"{self.stats['strikes_with_volume']} with volume")
        
        self.stats['dates_processed'] += 1
        self.save_checkpoint(date)
    
    def save_checkpoint(self, last_processed_date: datetime):
        """Save progress checkpoint"""
        checkpoint = {
            'last_processed_date': last_processed_date.strftime('%Y-%m-%d'),
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2, default=str)
    
    def load_checkpoint(self) -> Optional[datetime]:
        """Load last processed date from checkpoint"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                return datetime.strptime(checkpoint['last_processed_date'], '%Y-%m-%d')
            except Exception as e:
                self.logger.error(f"Error loading checkpoint: {e}")
        return None
    
    def get_or_create_contract(self, conn, symbol: str, expiration: str, 
                              strike: float, option_type: str) -> Optional[int]:
        """Get or create contract in database"""
        cursor = conn.cursor()
        try:
            exp_date = datetime.strptime(expiration, '%Y%m%d').date()
            
            # Check if exists
            cursor.execute("""
                SELECT contract_id FROM theta.options_contracts
                WHERE symbol = %s AND expiration = %s AND strike = %s AND option_type = %s
            """, (symbol, exp_date, strike, option_type))
            
            result = cursor.fetchone()
            if result:
                cursor.close()
                return result[0]
            
            # Create new
            cursor.execute("""
                INSERT INTO theta.options_contracts (symbol, expiration, strike, option_type)
                VALUES (%s, %s, %s, %s)
                RETURNING contract_id
            """, (symbol, exp_date, strike, option_type))
            
            contract_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return contract_id
            
        except Exception as e:
            self.logger.error(f"Contract creation error: {e}")
            cursor.close()
            return None
    
    def store_ohlc_data(self, contract_id: int, data: List) -> int:
        """Store OHLC data"""
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            cursor = conn.cursor()
            records = []
            
            for row in data:
                date_str = str(row[7])
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                ms_of_day = row[0]
                timestamp = date_obj + timedelta(milliseconds=ms_of_day)
                
                records.append((
                    contract_id, timestamp, 
                    row[1], row[2], row[3], row[4],  # open, high, low, close
                    row[5], row[6]  # volume, trade_count
                ))
            
            if records:
                from psycopg2.extras import execute_batch
                execute_batch(cursor, """
                    INSERT INTO theta.options_ohlc 
                    (contract_id, datetime, open, high, low, close, volume, trade_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, records, page_size=1000)
                
                conn.commit()
            
            cursor.close()
            return len(records)
            
        except Exception as e:
            self.logger.error(f"OHLC storage error: {e}")
            return 0
        finally:
            conn.close()
    
    def store_greeks_data(self, contract_id: int, data: List) -> int:
        """Store Greeks and IV data"""
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            cursor = conn.cursor()
            records = []
            
            for row in data:
                try:
                    if len(row) < 14:
                        continue
                    
                    date_str = str(row[13])
                    if '.' in date_str or len(date_str) != 8:
                        continue
                    
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    ms_of_day = row[0]
                    timestamp = date_obj + timedelta(milliseconds=ms_of_day)
                    
                    # Extract Greeks
                    delta = float(row[3]) if row[3] else 0.0
                    theta = float(row[4]) if row[4] else 0.0
                    vega = float(row[5]) if row[5] else 0.0
                    rho = float(row[6]) if row[6] else 0.0
                    implied_vol = float(row[9]) if row[9] else 0.0
                    
                    records.append((
                        contract_id, timestamp,
                        delta, 0.0, theta, vega, rho  # gamma not provided
                    ))
                    
                    # Also store IV
                    if implied_vol > 0:
                        cursor.execute("""
                            INSERT INTO theta.options_iv 
                            (contract_id, datetime, implied_volatility)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (contract_id, datetime) DO NOTHING
                        """, (contract_id, timestamp, implied_vol))
                        
                except (ValueError, IndexError):
                    continue
            
            if records:
                from psycopg2.extras import execute_batch
                execute_batch(cursor, """
                    INSERT INTO theta.options_greeks 
                    (contract_id, datetime, delta, gamma, theta, vega, rho)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, records, page_size=1000)
                
                conn.commit()
            
            cursor.close()
            return len(records)
            
        except Exception as e:
            self.logger.error(f"Greeks storage error: {e}")
            return 0
        finally:
            conn.close()
    
    def run_test_period(self, start_date: datetime, end_date: datetime):
        """Run downloader for a test period"""
        self.logger.info(f"\n🚀 Starting Daily Options Download Test")
        self.logger.info(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Check for checkpoint
        last_processed = self.load_checkpoint()
        if last_processed:
            self.logger.info(f"📂 Resuming from checkpoint: {last_processed.strftime('%Y-%m-%d')}")
            current_date = last_processed + timedelta(days=1)
        else:
            current_date = start_date
        
        # Process each trading day
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                self.process_date(current_date)
            
            current_date += timedelta(days=1)
        
        # Final summary
        duration = datetime.now() - self.stats['start_time']
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"✅ Download Test Complete!")
        self.logger.info(f"⏰ Duration: {duration}")
        self.logger.info(f"📅 Dates processed: {self.stats['dates_processed']}")
        self.logger.info(f"📊 Contracts downloaded: {self.stats['contracts_downloaded']:,}")
        self.logger.info(f"📈 Strikes with volume: {self.stats['strikes_with_volume']:,}")
        self.logger.info(f"💾 Total records: {self.stats['total_records']:,}")
        self.logger.info(f"❌ Errors: {self.stats['errors']}")


def main():
    """Test with 2017 H1 data"""
    # Test period: January to June 2017
    start_date = datetime(2017, 1, 3)  # First trading day of 2017
    end_date = datetime(2017, 6, 30)   # End of H1 2017
    
    downloader = DailyOptionsDownloader(max_workers=10)
    downloader.run_test_period(start_date, end_date)


if __name__ == "__main__":
    main()