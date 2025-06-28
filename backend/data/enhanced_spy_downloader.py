#!/usr/bin/env python3
"""
Enhanced SPY Options Downloader with Dynamic Strike Range
Designed to run in background without active sessions
"""
import sys
import os
import requests
import psycopg2
import time
import logging
import json
import signal
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional
import threading
from pathlib import Path

sys.path.append('/home/info/fntx-ai-v1')
from backend.config.theta_config import THETA_HTTP_API, DB_CONFIG

# Setup comprehensive logging
def setup_logging():
    log_dir = Path('/home/info/fntx-ai-v1/logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'enhanced_spy_downloader_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

class EnhancedSPYDownloader:
    """Background-safe SPY downloader with dynamic strike filtering"""
    
    def __init__(self, max_workers: int = 15):
        self.logger = setup_logging()
        self.session = requests.Session()
        self.max_workers = max_workers
        self.stop_event = threading.Event()
        self.checkpoint_file = '/home/info/fntx-ai-v1/download_checkpoint.json'
        
        # Statistics with thread safety
        self.stats = {
            'contracts_processed': 0,
            'contracts_skipped': 0,
            'ohlc_records': 0,
            'greeks_records': 0,
            'iv_records': 0,
            'errors': 0,
            'start_time': datetime.now(),
            'last_checkpoint': None
        }
        self.lock = threading.Lock()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("🚀 Enhanced SPY Downloader initialized")
        self.logger.info(f"📊 Max workers: {self.max_workers}")
        self.logger.info(f"📁 Log file: {logging.getLogger().handlers[0].baseFilename}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.stop_event.set()
    
    def save_checkpoint(self, progress_data: Dict):
        """Save progress to resume later"""
        try:
            checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats.copy(),
                'progress': progress_data
            }
            
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2, default=str)
            
            self.logger.info(f"💾 Checkpoint saved: {progress_data.get('current_expiration', 'unknown')}")
        except Exception as e:
            self.logger.error(f"❌ Failed to save checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """Load previous progress"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                self.logger.info(f"📂 Checkpoint loaded from {checkpoint['timestamp']}")
                return checkpoint
        except Exception as e:
            self.logger.error(f"❌ Failed to load checkpoint: {e}")
        return None
    
    def get_spy_daily_ohlc(self, date_str: str) -> Optional[Dict]:
        """Get SPY OHLC for a specific date to calculate dynamic strike range"""
        try:
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
                    ohlc = data['response'][0]  # [ms_of_day, open, high, low, close, volume, trade_count, date]
                    return {
                        'open': ohlc[1],
                        'high': ohlc[2], 
                        'low': ohlc[3],
                        'close': ohlc[4],
                        'date': date_str
                    }
        except Exception as e:
            self.logger.error(f"❌ Failed to get SPY OHLC for {date_str}: {e}")
        
        return None
    
    def calculate_dynamic_strike_range(self, spy_ohlc: Dict, buffer: int = 20) -> Tuple[int, int]:
        """Calculate dynamic strike range based on SPY OHLC + buffer"""
        if not spy_ohlc:
            # Fallback to reasonable range
            return (400, 600)
        
        low = spy_ohlc['low']
        high = spy_ohlc['high']
        
        min_strike = max(1, int(low - buffer))  # Don't go below $1
        max_strike = int(high + buffer)
        
        return (min_strike, max_strike)
    
    def should_download_contract(self, expiration: str, strike: int, option_type: str, spy_ohlc: Dict = None) -> bool:
        """Smart filtering with dynamic strike range"""
        
        # 1. Expiration date filtering
        try:
            exp_date = datetime.strptime(expiration, '%Y%m%d')
            
            # Skip very old or far future expirations
            if exp_date.year < 2017 or exp_date > datetime.now() + timedelta(days=730):
                return False
        except:
            return False
        
        # 2. Dynamic strike range filtering
        if spy_ohlc:
            min_strike, max_strike = self.calculate_dynamic_strike_range(spy_ohlc)
            if strike < min_strike or strike > max_strike:
                return False
        else:
            # Fallback: Conservative ATM range if no OHLC data
            year = exp_date.year
            atm_estimates = {
                2017: 250, 2018: 280, 2019: 320, 2020: 350,
                2021: 420, 2022: 450, 2023: 400, 2024: 500, 2025: 600
            }
            estimated_atm = atm_estimates.get(year, 500)
            if abs(strike - estimated_atm) > 25:  # ±25 fallback
                return False
        
        # 3. Sanity checks
        if strike <= 0 or strike > 1000:
            return False
        
        return True
    
    def check_if_data_exists(self, conn, contract_id: int, data_type: str) -> bool:
        """Check if we already have data for this contract"""
        cursor = conn.cursor()
        
        try:
            if data_type == 'ohlc':
                cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc WHERE contract_id = %s", (contract_id,))
            elif data_type == 'greeks':
                cursor.execute("SELECT COUNT(*) FROM theta.options_greeks WHERE contract_id = %s", (contract_id,))
            elif data_type == 'iv':
                cursor.execute("SELECT COUNT(*) FROM theta.options_iv WHERE contract_id = %s", (contract_id,))
            else:
                return False
            
            count = cursor.fetchone()[0]
            cursor.close()
            return count > 0
            
        except Exception as e:
            self.logger.error(f"❌ Error checking existing data: {e}")
            cursor.close()
            return False
    
    def has_volume(self, expiration: str, strike: int, option_type: str) -> bool:
        """Always return True - removed zero-volume filtering per user request"""
        return True
    
    def download_contract_data(self, expiration: str, strike: int, option_type: str, spy_ohlc: Dict = None) -> Dict:
        """Download comprehensive data for one contract"""
        
        # Quick filtering
        if not self.should_download_contract(expiration, strike, option_type, spy_ohlc):
            with self.lock:
                self.stats['contracts_skipped'] += 1
            return {'status': 'skipped', 'reason': 'filtered_out'}
        
        # Note: Zero-volume filtering removed per user request
        # All contracts passing strike filtering will be downloaded
        
        conn = psycopg2.connect(**DB_CONFIG)
        
        try:
            # Get or create contract
            contract_id = self.get_or_create_contract(conn, 'SPY', expiration, strike, option_type)
            if not contract_id:
                return {'status': 'error', 'reason': 'contract_creation_failed'}
            
            results = {'status': 'success', 'contract_id': contract_id}
            
            # Check what data we need
            need_ohlc = not self.check_if_data_exists(conn, contract_id, 'ohlc')
            need_greeks = not self.check_if_data_exists(conn, contract_id, 'greeks')
            need_iv = not self.check_if_data_exists(conn, contract_id, 'iv')
            
            # Skip if we already have everything
            if not (need_ohlc or need_greeks or need_iv):
                with self.lock:
                    self.stats['contracts_skipped'] += 1
                return {'status': 'skipped', 'reason': 'data_exists'}
            
            # Download parameters
            base_params = {
                'root': 'SPY',
                'exp': expiration,
                'strike': strike * 1000,
                'right': option_type,
                'start_date': '20170101',
                'end_date': datetime.now().strftime('%Y%m%d'),
                'ivl': 60000  # 1-minute intervals
            }
            
            # Download each data type
            if need_ohlc:
                ohlc_count = self.download_ohlc_for_contract(contract_id, base_params)
                results['ohlc_records'] = ohlc_count
                with self.lock:
                    self.stats['ohlc_records'] += ohlc_count
            
            # Greeks and IV are downloaded together from the same endpoint
            if need_greeks or need_iv:
                greeks_count = self.download_greeks_for_contract(contract_id, base_params)
                results['greeks_records'] = greeks_count
                with self.lock:
                    self.stats['greeks_records'] += greeks_count
            
            with self.lock:
                self.stats['contracts_processed'] += 1
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Contract download error {expiration} {strike}{option_type}: {e}")
            with self.lock:
                self.stats['errors'] += 1
            return {'status': 'error', 'reason': str(e)}
        finally:
            conn.close()
    
    def download_ohlc_for_contract(self, contract_id: int, params: Dict) -> int:
        """Download OHLC data"""
        url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    return self.store_ohlc_data(contract_id, data['response'])
            return 0
        except Exception as e:
            self.logger.error(f"❌ OHLC download error: {e}")
            return 0
    
    def download_greeks_for_contract(self, contract_id: int, params: Dict) -> int:
        """Download Greeks data"""
        url = f"{THETA_HTTP_API}/v2/hist/option/greeks"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    # Store both Greeks and IV data from the same response
                    greeks_count = self.store_greeks_data(contract_id, data['response'])
                    # IV data is embedded in Greeks response, update stats separately
                    if greeks_count > 0:
                        with self.lock:
                            self.stats['iv_records'] += greeks_count
                    return greeks_count
            return 0
        except Exception as e:
            self.logger.error(f"❌ Greeks download error: {e}")
            return 0
    
    def download_iv_for_contract(self, contract_id: int, params: Dict) -> int:
        """Download IV data - Note: IV is included in Greeks endpoint"""
        # IV data is included in the Greeks endpoint response
        # No separate IV endpoint exists, so we return 0
        # The actual IV storage happens in store_greeks_data
        return 0
    
    def store_ohlc_data(self, contract_id: int, data: List) -> int:
        """Store OHLC data efficiently"""
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
                    contract_id, timestamp, row[1], row[2], row[3], row[4], row[5], row[6]
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
            self.logger.error(f"❌ OHLC storage error: {e}")
            return 0
        finally:
            conn.close()
    
    def store_greeks_data(self, contract_id: int, data: List) -> int:
        """Store Greeks data efficiently with improved error handling"""
        conn = psycopg2.connect(**DB_CONFIG)
        
        try:
            cursor = conn.cursor()
            records = []
            
            for row in data:
                try:
                    # ThetaData Greeks format: [ms_of_day, bid, ask, delta, theta, vega, rho, epsilon, lambda, implied_vol, iv_error, ms_of_day2, underlying_price, date]
                    if len(row) < 14:
                        continue
                    
                    date_str = str(row[13])  # Date is at position 13
                    # Skip if date field contains Greek values instead of date
                    if '.' in date_str or len(date_str) != 8:
                        continue
                        
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    ms_of_day = row[0]
                    timestamp = date_obj + timedelta(milliseconds=ms_of_day)
                    
                    # Extract Greeks: delta, theta, vega, rho (no gamma in this API)
                    # Set gamma to 0 as it's not provided by this endpoint
                    delta = float(row[3]) if row[3] else 0.0
                    theta = float(row[4]) if row[4] else 0.0
                    vega = float(row[5]) if row[5] else 0.0
                    rho = float(row[6]) if row[6] else 0.0
                    implied_vol = float(row[9]) if row[9] else 0.0
                    
                    # Store Greeks
                    records.append((
                        contract_id, timestamp, 
                        delta,      # delta
                        0.0,        # gamma (not provided)
                        theta,      # theta  
                        vega,       # vega
                        rho         # rho
                    ))
                    
                    # Also store IV data if valid
                    if implied_vol > 0:
                        cursor.execute("""
                            INSERT INTO theta.options_iv 
                            (contract_id, datetime, implied_volatility)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (contract_id, datetime) DO NOTHING
                        """, (contract_id, timestamp, implied_vol))
                except (ValueError, IndexError) as e:
                    # Skip malformed rows
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
            self.logger.error(f"❌ Greeks storage error: {e}")
            return 0
        finally:
            conn.close()
    
    def store_iv_data(self, contract_id: int, data: List) -> int:
        """Store IV data efficiently"""
        conn = psycopg2.connect(**DB_CONFIG)
        
        try:
            cursor = conn.cursor()
            records = []
            
            for row in data:
                try:
                    # IV data is included in Greeks endpoint at position 9
                    # Format: [ms_of_day, bid, ask, delta, theta, vega, rho, epsilon, lambda, implied_vol, iv_error, ms_of_day2, underlying_price, date]
                    if len(row) < 14:
                        continue
                        
                    date_str = str(row[13])  # Date is at position 13
                    if '.' in date_str or len(date_str) != 8:
                        continue
                        
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    ms_of_day = row[0]
                    timestamp = date_obj + timedelta(milliseconds=ms_of_day)
                    
                    # Extract implied volatility from position 9
                    implied_vol = float(row[9])
                    if implied_vol > 0:  # Only store valid IV values
                        records.append((contract_id, timestamp, implied_vol))
                except (ValueError, IndexError) as e:
                    continue
            
            if records:
                from psycopg2.extras import execute_batch
                execute_batch(cursor, """
                    INSERT INTO theta.options_iv 
                    (contract_id, datetime, implied_volatility)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, records, page_size=1000)
                
                conn.commit()
            
            cursor.close()
            return len(records)
        except Exception as e:
            self.logger.error(f"❌ IV storage error: {e}")
            return 0
        finally:
            conn.close()
    
    def get_or_create_contract(self, conn, symbol: str, expiration: str, strike: float, option_type: str):
        """Get or create contract efficiently"""
        cursor = conn.cursor()
        
        try:
            exp_date = datetime.strptime(expiration, '%Y%m%d').date()
            
            cursor.execute("""
                SELECT contract_id FROM theta.options_contracts
                WHERE symbol = %s AND expiration = %s AND strike = %s AND option_type = %s
            """, (symbol, exp_date, strike, option_type))
            
            result = cursor.fetchone()
            if result:
                cursor.close()
                return result[0]
            
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
            self.logger.error(f"❌ Contract creation error: {e}")
            cursor.close()
            return None
    
    def get_liquid_expirations(self) -> List[str]:
        """Get liquid, tradeable expirations"""
        url = f"{THETA_HTTP_API}/v2/list/expirations?root=SPY"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                expirations = data.get('response', [])
                
                # Filter to recent, liquid expirations
                filtered = []
                for exp in expirations:
                    exp_str = str(exp)
                    exp_date = datetime.strptime(exp_str, '%Y%m%d')
                    
                    # Only 2017+ and within 2 years
                    if (exp_date.year >= 2017 and 
                        exp_date <= datetime.now() + timedelta(days=730)):
                        filtered.append(exp_str)
                
                return sorted(filtered)
        except Exception as e:
            self.logger.error(f"❌ Error getting expirations: {e}")
        
        return []
    
    def run_enhanced_download(self):
        """Main download loop with dynamic strike filtering"""
        
        self.logger.info("🎯 Starting Enhanced SPY Download with Dynamic Strike Filtering")
        self.logger.info(f"📊 Workers: {self.max_workers}")
        self.logger.info(f"🎲 Strategy: SPY OHLC ±20 strikes only (zero-volume filter removed)")
        
        # Load checkpoint if exists
        checkpoint = self.load_checkpoint()
        start_from_expiration = None
        if checkpoint:
            start_from_expiration = checkpoint.get('progress', {}).get('current_expiration')
            self.logger.info(f"📂 Resuming from expiration: {start_from_expiration}")
        
        # Get all liquid expirations
        expirations = self.get_liquid_expirations()
        if not expirations:
            self.logger.error("❌ No expirations found")
            return
        
        # Resume from checkpoint if available
        if start_from_expiration and start_from_expiration in expirations:
            start_idx = expirations.index(start_from_expiration)
            expirations = expirations[start_idx:]
        
        self.logger.info(f"📅 Processing {len(expirations)} expirations")
        
        total_contracts_evaluated = 0
        
        for i, expiration in enumerate(expirations):
            if self.stop_event.is_set():
                self.logger.info("⏹️ Graceful shutdown requested")
                break
            
            exp_date_str = expiration[:4] + expiration[4:6] + expiration[6:8]  # Format for SPY OHLC lookup
            
            # Get SPY OHLC for this expiration to calculate dynamic strike range
            spy_ohlc = self.get_spy_daily_ohlc(exp_date_str)
            
            if spy_ohlc:
                min_strike, max_strike = self.calculate_dynamic_strike_range(spy_ohlc)
                self.logger.info(f"📊 {expiration}: SPY OHLC L:{spy_ohlc['low']:.2f} H:{spy_ohlc['high']:.2f} → Strikes: ${min_strike}-${max_strike}")
            else:
                # Fallback range
                min_strike, max_strike = 400, 600
                self.logger.warning(f"⚠️ {expiration}: No SPY OHLC data, using fallback range ${min_strike}-${max_strike}")
            
            # Generate contracts for this expiration
            contracts_for_expiration = []
            for strike in range(min_strike, max_strike + 1):
                for option_type in ['C', 'P']:
                    contracts_for_expiration.append((expiration, strike, option_type))
            
            total_contracts_evaluated += len(contracts_for_expiration)
            self.logger.info(f"🎯 {expiration}: Evaluating {len(contracts_for_expiration)} contracts")
            
            # Process contracts in parallel
            completed_this_exp = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all jobs for this expiration
                future_to_contract = {
                    executor.submit(self.download_contract_data, exp, strike, opt_type, spy_ohlc): (exp, strike, opt_type)
                    for exp, strike, opt_type in contracts_for_expiration
                }
                
                # Process results
                for future in as_completed(future_to_contract):
                    if self.stop_event.is_set():
                        break
                    
                    completed_this_exp += 1
                    
                    # Progress logging every 50 contracts
                    if completed_this_exp % 50 == 0:
                        with self.lock:
                            self.logger.info(f"📈 {expiration} Progress: {completed_this_exp}/{len(contracts_for_expiration)} "
                                            f"| Processed: {self.stats['contracts_processed']:,} "
                                            f"| Skipped: {self.stats['contracts_skipped']:,} "
                                            f"| OHLC: {self.stats['ohlc_records']:,}")
            
            # Save checkpoint after each expiration
            progress_data = {
                'current_expiration': expiration,
                'expiration_index': i,
                'total_expirations': len(expirations),
                'total_contracts_evaluated': total_contracts_evaluated
            }
            self.save_checkpoint(progress_data)
            
            # Expiration summary
            self.logger.info(f"✅ {expiration} Complete: {completed_this_exp} contracts evaluated")
        
        # Final statistics
        duration = datetime.now() - self.stats['start_time']
        total_records = self.stats['ohlc_records'] + self.stats['greeks_records'] + self.stats['iv_records']
        
        self.logger.info("\n🎉 Enhanced SPY Download Complete!")
        self.logger.info("=" * 60)
        self.logger.info(f"⏰ Duration: {duration}")
        self.logger.info(f"📊 Contracts processed: {self.stats['contracts_processed']:,}")
        self.logger.info(f"⏭️ Contracts skipped: {self.stats['contracts_skipped']:,}")
        self.logger.info(f"📈 OHLC records: {self.stats['ohlc_records']:,}")
        self.logger.info(f"🧮 Greeks records: {self.stats['greeks_records']:,}")
        self.logger.info(f"📐 IV records: {self.stats['iv_records']:,}")
        self.logger.info(f"📊 Total records: {total_records:,}")
        self.logger.info(f"❌ Errors: {self.stats['errors']:,}")
        
        if duration.total_seconds() > 0:
            rate = total_records / duration.total_seconds()
            self.logger.info(f"💨 Average rate: {rate:.1f} records/second")
        
        self.logger.info("🏁 Download process completed successfully")


def main():
    """Main entry point for background execution"""
    print("🚀 Starting Enhanced SPY Options Downloader")
    print("This process is designed to run in the background")
    print("Use Ctrl+C or send SIGTERM to stop gracefully")
    print("-" * 60)
    
    try:
        downloader = EnhancedSPYDownloader(max_workers=15)
        downloader.run_enhanced_download()
    except KeyboardInterrupt:
        print("\n🛑 Download stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()