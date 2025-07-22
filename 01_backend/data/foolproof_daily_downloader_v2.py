#!/usr/bin/env python3
"""
Foolproof Daily Options Downloader V2
Enhanced with automatic strike interval detection for historical data
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
from typing import List, Dict, Tuple, Optional, Set
import threading
from pathlib import Path
from psycopg2.extras import execute_batch

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import THETA_HTTP_API, DB_CONFIG

# Setup logging to use 08_logs directory
def setup_logging():
    log_dir = Path('/home/info/fntx-ai-v1/08_logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'foolproof_daily_downloader_v2_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class StrikeIntervalDetector:
    """Detects the appropriate strike interval for a given date"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache = {}  # Cache detected intervals by date
    
    def detect_interval(self, date: datetime, spy_price: float) -> int:
        """Detect strike interval for a given date"""
        # Check cache first
        date_key = date.strftime('%Y-%m-%d')
        if date_key in self.cache:
            return self.cache[date_key]
        
        # Test different intervals
        session = requests.Session()
        
        # Find next expiration
        exp_date = date
        while exp_date.weekday() > 4:  # Skip to weekday
            exp_date += timedelta(days=1)
        exp_date += timedelta(days=1)  # Next day expiration
        exp_str = exp_date.strftime('%Y%m%d')
        
        # Test strikes around SPY price
        base_strike = int(spy_price)
        intervals_to_test = [1, 5, 10]  # Common intervals
        
        for interval in intervals_to_test:
            test_strikes = [
                base_strike - interval,
                base_strike,
                base_strike + interval
            ]
            
            success_count = 0
            
            for strike in test_strikes:
                url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
                params = {
                    'root': 'SPY',
                    'exp': exp_str,
                    'strike': strike * 1000,
                    'right': 'C',
                    'start_date': date.strftime('%Y%m%d'),
                    'end_date': date.strftime('%Y%m%d'),
                    'ivl': 60000
                }
                
                try:
                    response = session.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('response'):
                            success_count += 1
                except:
                    pass
            
            # If we get data for multiple strikes at this interval, it's likely correct
            if success_count >= 2:
                self.logger.info(f"✅ Detected strike interval for {date_key}: ${interval}")
                self.cache[date_key] = interval
                return interval
        
        # Default to $5 for older data
        self.logger.warning(f"⚠️ Could not detect interval for {date_key}, defaulting to $5")
        self.cache[date_key] = 5
        return 5

class StrikeRangeCalculator:
    """Calculates comprehensive strike ranges using open-close union method"""
    
    def __init__(self, buffer_percent: float = 0.05):
        self.buffer = buffer_percent  # 5% default
        self.logger = logging.getLogger(__name__)
        self.interval_detector = StrikeIntervalDetector()
    
    def calculate_daily_strikes(self, spy_data: Dict, expiration: datetime) -> Set[int]:
        """
        Calculate all relevant strikes for a day using union of ranges
        """
        date = spy_data['date']
        dte = (expiration - date).days
        
        # Detect appropriate strike interval
        interval = self.interval_detector.detect_interval(date, spy_data['close'])
        
        # Adjust buffer based on DTE
        if dte == 0:
            buffer = 0.05  # ±5% for 0DTE
        elif dte <= 7:
            buffer = 0.07  # ±7% for weekly
        else:
            buffer = 0.10  # ±10% for monthly
        
        all_strikes = set()
        
        # 1. Strikes from opening price
        open_strikes = self._get_strikes_from_price(spy_data['open'], buffer, interval)
        all_strikes.update(open_strikes)
        self.logger.debug(f"Open strikes ({spy_data['open']:.2f} ± {buffer*100}%): "
                         f"${min(open_strikes)}-${max(open_strikes)}")
        
        # 2. Strikes from closing price
        close_strikes = self._get_strikes_from_price(spy_data['close'], buffer, interval)
        all_strikes.update(close_strikes)
        self.logger.debug(f"Close strikes ({spy_data['close']:.2f} ± {buffer*100}%): "
                         f"${min(close_strikes)}-${max(close_strikes)}")
        
        # 3. Strikes from high
        high_strikes = self._get_strikes_from_price(spy_data['high'], buffer, interval)
        all_strikes.update(high_strikes)
        
        # 4. Strikes from low  
        low_strikes = self._get_strikes_from_price(spy_data['low'], buffer, interval)
        all_strikes.update(low_strikes)
        
        # 5. For 0DTE, add strikes around VWAP (approximate as (H+L+C)/3)
        if dte == 0:
            vwap = (spy_data['high'] + spy_data['low'] + spy_data['close']) / 3
            vwap_strikes = self._get_strikes_from_price(vwap, buffer * 0.5, interval)  # Tighter range
            all_strikes.update(vwap_strikes)
        
        self.logger.info(f"Total unique strikes for DTE={dte}: {len(all_strikes)} "
                        f"(${min(all_strikes)}-${max(all_strikes)}) interval=${interval}")
        
        return all_strikes
    
    def _get_strikes_from_price(self, price: float, buffer: float, interval: int) -> Set[int]:
        """Get all strikes within buffer of price at the specified interval"""
        min_price = price * (1 - buffer)
        max_price = price * (1 + buffer)
        
        # Round to nearest interval
        min_strike = int(min_price / interval) * interval
        max_strike = int(max_price / interval + 1) * interval
        
        # Ensure reasonable bounds
        min_strike = max(min_strike, 50)
        max_strike = min(max_strike, 1000)
        
        # Generate strikes at interval
        strikes = set()
        strike = min_strike
        while strike <= max_strike:
            strikes.add(strike)
            strike += interval
        
        return strikes

class FoolproofDailyDownloader:
    """Downloads options data using foolproof open-close union methodology"""
    
    def __init__(self, max_workers: int = 10):
        self.session = requests.Session()
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'start_time': datetime.now(),
            'dates_processed': 0,
            'spy_data_collected': 0,
            'contracts_downloaded': 0,
            'total_records': 0,
            'unique_strikes': 0,
            'errors': 0,
            'validation_failures': 0
        }
        self.db_lock = threading.Lock()
        self.strike_calculator = StrikeRangeCalculator(buffer_percent=0.05)
        self.checkpoint_file = Path('/home/info/fntx-ai-v1/08_logs/foolproof_checkpoint.json')
    
    def get_spy_data(self, date: datetime) -> Optional[Dict]:
        """Get SPY OHLC data for a specific date"""
        # Try ThetaData first
        spy_data = self._fetch_from_theta(date)
        
        # Fallback to Yahoo if needed
        if not spy_data:
            self.logger.warning(f"ThetaData unavailable for {date}, trying Yahoo Finance...")
            spy_data = self._fetch_from_yahoo(date)
        
        if spy_data and self._validate_spy_data(spy_data):
            self.stats['spy_data_collected'] += 1
            return spy_data
        
        return None
    
    def _fetch_from_theta(self, date: datetime) -> Optional[Dict]:
        """Get SPY data from ThetaData"""
        try:
            url = f"{THETA_HTTP_API}/v2/hist/stock/ohlc"
            params = {
                'root': 'SPY',
                'start_date': date.strftime('%Y%m%d'),
                'end_date': date.strftime('%Y%m%d'),
                'ivl': 1440 * 60000  # Daily bars
            }
            
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    ohlc = data['response'][0]  # First bar
                    return {
                        'date': date,
                        'open': float(ohlc[1]),
                        'high': float(ohlc[2]),
                        'low': float(ohlc[3]),
                        'close': float(ohlc[4]),
                        'volume': int(ohlc[5])
                    }
        except Exception as e:
            self.logger.error(f"ThetaData error: {e}")
        
        return None
    
    def _fetch_from_yahoo(self, date: datetime) -> Optional[Dict]:
        """Fallback: Get SPY data from Yahoo Finance"""
        try:
            # Import yfinance only if needed
            import yfinance as yf
            
            spy = yf.Ticker("SPY")
            date_str = date.strftime('%Y-%m-%d')
            next_day = (date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            hist = spy.history(start=date_str, end=next_day)
            if not hist.empty:
                return {
                    'date': date,
                    'open': float(hist['Open'].iloc[0]),
                    'high': float(hist['High'].iloc[0]),
                    'low': float(hist['Low'].iloc[0]),
                    'close': float(hist['Close'].iloc[0]),
                    'volume': int(hist['Volume'].iloc[0])
                }
        except Exception as e:
            self.logger.error(f"Yahoo Finance error: {e}")
        
        return None
    
    def _validate_spy_data(self, data: Dict) -> bool:
        """Validate SPY data is reasonable"""
        if not all(k in data for k in ['open', 'high', 'low', 'close']):
            return False
        
        # Basic sanity checks
        if data['low'] > data['high']:
            return False
        if data['open'] < 50 or data['open'] > 1000:
            return False
        if data['close'] < 50 or data['close'] > 1000:
            return False
        
        return True
    
    def _get_expirations_for_date(self, date: datetime) -> List[str]:
        """Get all expirations traded on a specific date"""
        try:
            # For 0-2 DTE focus, we need expirations within next few days
            expirations = []
            
            # Check next 10 days for potential expirations
            for days_ahead in range(10):
                exp_date = date + timedelta(days=days_ahead)
                
                # Skip if DTE > 2 for this project
                if days_ahead > 2:
                    break
                
                # SPY has Mon/Wed/Fri expirations
                if exp_date.weekday() in [0, 2, 4]:  # Monday, Wednesday, Friday
                    expirations.append(exp_date.strftime('%Y%m%d'))
            
            return expirations
            
        except Exception as e:
            self.logger.error(f"Error getting expirations: {e}")
            return []
    
    def _download_single_contract(self, contract_params: Dict) -> Optional[Tuple[int, List]]:
        """Download a single options contract"""
        try:
            url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
            response = self.session.get(url, params=contract_params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    return len(data['response']), data['response']
            elif response.status_code == 472:
                # No data for this contract
                return None, None
                
        except Exception as e:
            self.logger.error(f"Error downloading contract: {e}")
            self.stats['errors'] += 1
        
        return None, None
    
    def _save_contract_data(self, contract_info: Dict, ohlc_data: List):
        """Save contract and OHLC data to database"""
        try:
            with self.db_lock:
                conn = psycopg2.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                # Insert or get contract
                cursor.execute("""
                    INSERT INTO theta.options_contracts 
                    (symbol, expiration, strike, option_type, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (symbol, expiration, strike, option_type) 
                    DO UPDATE SET updated_at = NOW()
                    RETURNING contract_id
                """, (
                    contract_info['symbol'],
                    contract_info['expiration'],
                    contract_info['strike'],
                    contract_info['option_type']
                ))
                
                contract_id = cursor.fetchone()[0]
                
                # Prepare OHLC records
                ohlc_records = []
                for bar in ohlc_data:
                    timestamp = datetime.fromtimestamp(bar[0] / 1000)
                    ohlc_records.append((
                        contract_id,
                        timestamp,
                        float(bar[1]),  # open
                        float(bar[2]),  # high
                        float(bar[3]),  # low
                        float(bar[4]),  # close
                        int(bar[5]),    # volume
                        int(bar[6]) if len(bar) > 6 else 0  # open_interest
                    ))
                
                # Bulk insert OHLC data
                execute_batch(cursor, """
                    INSERT INTO theta.options_ohlc 
                    (contract_id, datetime, open, high, low, close, volume, open_interest)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, ohlc_records, page_size=1000)
                
                conn.commit()
                cursor.close()
                conn.close()
                
                self.stats['total_records'] += len(ohlc_records)
                
        except Exception as e:
            self.logger.error(f"Database error: {e}")
            self.stats['errors'] += 1
    
    def _download_strikes_for_expiration(self, trade_date: datetime, exp_str: str, 
                                       strikes: Set[int], spy_data: Dict) -> int:
        """Download all strikes for a specific expiration"""
        exp_date = datetime.strptime(exp_str, '%Y%m%d')
        dte = (exp_date - trade_date).days
        
        # Prepare download tasks
        tasks = []
        for strike in strikes:
            for right in ['C', 'P']:
                contract_params = {
                    'root': 'SPY',
                    'exp': exp_str,
                    'strike': strike * 1000,
                    'right': right,
                    'start_date': trade_date.strftime('%Y%m%d'),
                    'end_date': trade_date.strftime('%Y%m%d'),
                    'ivl': 60000  # 1-minute bars
                }
                
                contract_info = {
                    'symbol': 'SPY',
                    'expiration': exp_date,
                    'strike': strike,
                    'option_type': right,
                    'dte': dte,
                    'spy_price': spy_data['close']
                }
                
                tasks.append((contract_params, contract_info))
        
        # Download in parallel
        downloaded = 0
        unique_strikes = set()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(self._download_single_contract, params): (params, info)
                for params, info in tasks
            }
            
            for future in as_completed(future_to_task):
                params, info = future_to_task[future]
                try:
                    bar_count, data = future.result()
                    if data:
                        self._save_contract_data(info, data)
                        downloaded += 1
                        unique_strikes.add(info['strike'])
                        
                        if downloaded % 10 == 0:
                            self.logger.info(f"Progress: {downloaded}/{len(tasks)} contracts")
                            
                except Exception as e:
                    self.logger.error(f"Error processing {info['strike']}{info['option_type']}: {e}")
        
        self.stats['contracts_downloaded'] += downloaded
        self.stats['unique_strikes'] += len(unique_strikes)
        
        self.logger.info(f"Downloaded {downloaded}/{len(tasks)} contracts for {exp_str}")
        return downloaded
    
    def process_trading_day(self, date: datetime) -> bool:
        """Process all options for a single trading day"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"📅 Processing: {date.strftime('%Y-%m-%d (%A)')}")
        
        # Step 1: Get SPY OHLC data
        spy_data = self.get_spy_data(date)
        if not spy_data:
            self.logger.error(f"❌ Could not get SPY data for {date}")
            return False
        
        self.logger.info(f"📊 SPY: Open=${spy_data['open']:.2f}, "
                        f"High=${spy_data['high']:.2f}, "
                        f"Low=${spy_data['low']:.2f}, "
                        f"Close=${spy_data['close']:.2f}")
        
        # Calculate daily range
        daily_range = spy_data['high'] - spy_data['low']
        daily_move_pct = (daily_range / spy_data['open']) * 100
        self.logger.info(f"📈 Daily Range: ${daily_range:.2f} ({daily_move_pct:.2f}%)")
        
        # Step 2: Get all expirations for this date
        expirations = self._get_expirations_for_date(date)
        if not expirations:
            self.logger.warning(f"⚠️ No expirations found for {date}")
            return True
        
        # Step 3: Process each expiration
        total_contracts_for_day = 0
        
        for exp_str in expirations:
            exp_date = datetime.strptime(exp_str, '%Y%m%d')
            dte = (exp_date - date).days
            
            # Skip far-dated options for now (focus on near-term)
            if dte > 30:
                continue
            
            # Calculate comprehensive strike list
            strikes = self.strike_calculator.calculate_daily_strikes(spy_data, exp_date)
            
            self.logger.info(f"\n🎯 Expiration: {exp_str} (DTE: {dte})")
            self.logger.info(f"📊 Strikes to download: {len(strikes)} "
                           f"(${min(strikes)}-${max(strikes)})")
            
            # Download strikes for this expiration
            downloaded = self._download_strikes_for_expiration(
                date, exp_str, strikes, spy_data
            )
            total_contracts_for_day += downloaded
        
        # Step 4: Validate the day's downloads
        if self._validate_daily_downloads(date, spy_data):
            self.logger.info(f"✅ Validation passed for {date}")
        else:
            self.logger.warning(f"⚠️ Validation issues for {date}")
            self.stats['validation_failures'] += 1
        
        self.stats['dates_processed'] += 1
        self.logger.info(f"\n📊 Daily Summary: {total_contracts_for_day} contracts downloaded")
        
        # Save checkpoint
        self._save_checkpoint(date)
        
        return True
    
    def _validate_daily_downloads(self, date: datetime, spy_data: Dict) -> bool:
        """Validate downloads for completeness"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Check we have strikes near open
            open_price = spy_data['open']
            cursor.execute("""
                SELECT COUNT(DISTINCT oc.strike)
                FROM theta.options_contracts oc
                JOIN theta.options_ohlc ohlc ON oc.contract_id = ohlc.contract_id
                WHERE oc.symbol = 'SPY'
                AND ohlc.datetime::date = %s
                AND oc.strike BETWEEN %s AND %s
            """, (date, int(open_price * 0.99), int(open_price * 1.01)))
            
            strikes_near_open = cursor.fetchone()[0]
            
            # Check we have strikes near close
            close_price = spy_data['close']
            cursor.execute("""
                SELECT COUNT(DISTINCT oc.strike)
                FROM theta.options_contracts oc
                JOIN theta.options_ohlc ohlc ON oc.contract_id = ohlc.contract_id
                WHERE oc.symbol = 'SPY'
                AND ohlc.datetime::date = %s
                AND oc.strike BETWEEN %s AND %s
            """, (date, int(close_price * 0.99), int(close_price * 1.01)))
            
            strikes_near_close = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            # Validation criteria (adjusted for $5 intervals)
            if strikes_near_open < 1:  # At least 1 strike near open
                self.logger.warning(f"Only {strikes_near_open} strikes near open")
                return False
            
            if strikes_near_close < 1:  # At least 1 strike near close
                self.logger.warning(f"Only {strikes_near_close} strikes near close")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
    
    def _save_checkpoint(self, last_date: datetime):
        """Save progress checkpoint"""
        checkpoint = {
            'last_processed_date': last_date.strftime('%Y-%m-%d'),
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2, default=str)
    
    def _load_checkpoint(self) -> Optional[datetime]:
        """Load checkpoint if exists"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                return datetime.strptime(checkpoint['last_processed_date'], '%Y-%m-%d')
            except Exception as e:
                self.logger.error(f"Error loading checkpoint: {e}")
        return None
    
    def run_date_range(self, start_date: datetime, end_date: datetime):
        """Process a range of dates"""
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🚀 FOOLPROOF DAILY OPTIONS DOWNLOAD V2")
        self.logger.info(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to "
                        f"{end_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"📊 Strategy: Open-Close Union with ±5% buffer")
        self.logger.info(f"🔧 Feature: Automatic strike interval detection")
        self.logger.info(f"{'='*80}")
        
        # Check for checkpoint
        last_processed = self._load_checkpoint()
        if last_processed:
            self.logger.info(f"📂 Resuming from checkpoint: {last_processed.strftime('%Y-%m-%d')}")
            current_date = last_processed + timedelta(days=1)
        else:
            current_date = start_date
        
        # Process each trading day
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                success = self.process_trading_day(current_date)
                if not success:
                    self.logger.warning(f"Failed to process {current_date}, continuing...")
            
            current_date += timedelta(days=1)
        
        # Final statistics
        self._print_final_statistics()
    
    def _print_final_statistics(self):
        """Print comprehensive statistics"""
        duration = datetime.now() - self.stats['start_time']
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"✅ DOWNLOAD COMPLETE")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"⏰ Duration: {duration}")
        self.logger.info(f"📅 Trading days processed: {self.stats['dates_processed']}")
        self.logger.info(f"📊 SPY data collected: {self.stats['spy_data_collected']}")
        self.logger.info(f"📈 Contracts downloaded: {self.stats['contracts_downloaded']:,}")
        self.logger.info(f"🎯 Unique strikes: {self.stats['unique_strikes']:,}")
        self.logger.info(f"💾 Total records: {self.stats['total_records']:,}")
        self.logger.info(f"⚠️ Validation failures: {self.stats['validation_failures']}")
        self.logger.info(f"❌ Errors: {self.stats['errors']}")
        
        if self.stats['dates_processed'] > 0:
            avg_contracts = self.stats['contracts_downloaded'] / self.stats['dates_processed']
            avg_strikes = self.stats['unique_strikes'] / self.stats['dates_processed']
            self.logger.info(f"\n📊 Averages per day:")
            self.logger.info(f"   Contracts: {avg_contracts:.1f}")
            self.logger.info(f"   Unique strikes: {avg_strikes:.1f}")


def main():
    """Run January 2020 download"""
    # Setup logging
    setup_logging()
    
    # January 2020
    start_date = datetime(2020, 1, 2)   # Thursday (Jan 1 was holiday)
    end_date = datetime(2020, 1, 31)    # Friday
    
    # Use small batch size to avoid timeouts
    downloader = FoolproofDailyDownloader(max_workers=2)
    downloader.run_date_range(start_date, end_date)


if __name__ == "__main__":
    # Check if yfinance is installed for Yahoo fallback
    try:
        import yfinance
    except ImportError:
        print("Warning: yfinance not installed. Yahoo Finance fallback will not work.")
        print("Install with: pip install yfinance")
    
    main()