#!/usr/bin/env python3
"""
ThetaTerminal Historical Data Downloader - ENHANCED VERSION
Downloads SPY and QQQ options data with comprehensive logging and data quality tracking

Key features:
1. Progress bars and ETA calculation
2. Data quality validation (missing OHLC/Greeks/IV detection)
3. Enhanced logging with contract details
4. Daily summaries with completeness statistics
"""
import requests
import psycopg2
import pandas as pd
from datetime import datetime, timedelta, date
import logging
import time
import sys
import os
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# Setup enhanced logging
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and symbols"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[0m',      # Default
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

# Configure logging
log_format = '%(asctime)s - %(levelname)s - %(message)s'
file_handler = logging.FileHandler('/home/info/fntx-ai-v1/backend/data/theta_download/download_improved.log')
file_handler.setFormatter(logging.Formatter(log_format))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColoredFormatter(log_format))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

class ThetaHistoricalDownloader:
    """Enhanced downloader with progress tracking and data validation"""
    
    def __init__(self):
        # Database config
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'options_data',
            'user': 'postgres',
            'password': 'theta_data_2024'
        }
        
        # ThetaTerminal REST API
        self.rest_base = "http://localhost:25510"
        
        # Symbols to download with their earliest data dates
        self.symbol_configs = {
            'SPY': {
                'earliest_date': date(2022, 12, 1),
                'strike_increment': 1.0
            },
            'QQQ': {
                'earliest_date': date(2022, 12, 1),
                'strike_increment': 1.0
            }
        }
        
        # Enhanced statistics tracking
        self.stats = {
            'contracts_checked': 0,
            'contracts_skipped_no_volume': 0,
            'contracts_downloaded': 0,
            'total_records': 0,
            'data_quality': {
                'complete_contracts': 0,
                'missing_greeks': 0,
                'missing_iv': 0,
                'sentinel_iv': 0,
                'iv_gaps': 0
            }
        }
        
        # Progress tracking
        self.start_time = None
        self.total_days = 0
        self.days_processed = 0
        
        # Data quality tracking
        self.contract_data_quality = defaultdict(lambda: {
            'ohlc_count': 0,
            'greeks_count': 0,
            'iv_count': 0,
            'sentinel_iv_count': 0,
            'iv_gaps': []
        })
        
        # Connect to database
        self.conn = None
        self._connect_db()
        
    def _connect_db(self):
        """Connect to PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to PostgreSQL successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def _calculate_total_trading_days(self, start_date: date, end_date: date) -> int:
        """Calculate total trading days between dates"""
        days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() not in [5, 6]:  # Not weekend
                days += 1
            current += timedelta(days=1)
        return days
    
    def _format_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Create a progress bar string"""
        if total == 0:
            return "[" + "?" * width + "]"
        
        progress = current / total
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        percentage = int(progress * 100)
        
        return f"[{bar}] {percentage}%"
    
    def _calculate_eta(self) -> str:
        """Calculate estimated time remaining"""
        if not self.start_time or self.days_processed == 0:
            return "calculating..."
        
        elapsed = time.time() - self.start_time
        days_remaining = self.total_days - self.days_processed
        
        if days_remaining == 0:
            return "completing..."
        
        avg_time_per_day = elapsed / self.days_processed
        eta_seconds = avg_time_per_day * days_remaining
        
        hours = int(eta_seconds // 3600)
        minutes = int((eta_seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m remaining"
        else:
            return f"{minutes}m remaining"
    
    def _log_progress(self, symbol: str, current_date: date, contracts_count: int, 
                     strike_min: float, strike_max: float, calls: int, puts: int):
        """Log enhanced progress information"""
        progress_bar = self._format_progress_bar(self.days_processed, self.total_days)
        eta = self._calculate_eta()
        
        # Calculate speed
        if self.start_time and self.stats['contracts_downloaded'] > 0:
            elapsed_hours = (time.time() - self.start_time) / 3600
            speed = int(self.stats['contracts_downloaded'] / elapsed_hours) if elapsed_hours > 0 else 0
        else:
            speed = 0
        
        logger.info("")
        logger.info(f"{'='*60}")
        logger.info(f"=== {symbol} Progress: {progress_bar} - Day {self.days_processed}/{self.total_days} ===")
        logger.info(f"Date: {current_date} | Contracts: {contracts_count} ({calls}C/{puts}P) | Strikes: ${strike_min:.0f}-${strike_max:.0f}")
        logger.info(f"Downloaded: {self.stats['contracts_downloaded']:,} | Skipped: {self.stats['contracts_skipped_no_volume']} | Speed: {speed} contracts/hr")
        logger.info(f"Total data points: {self.stats['total_records']:,} | Sentinel IVs: {self.stats['data_quality']['sentinel_iv']}")
        logger.info(f"ETA: {eta}")
        logger.info(f"{'='*60}")
    
    def _log_data_quality(self, contract: Dict, quality_info: Dict):
        """Log data quality information for a contract"""
        symbol = contract['symbol']
        strike = contract['strike']
        opt_type = contract['option_type']
        
        # Check for completeness
        ohlc = quality_info['ohlc_count']
        greeks = quality_info['greeks_count']
        iv = quality_info['iv_count']
        sentinel_iv = quality_info['sentinel_iv_count']
        
        if ohlc == 0:
            return  # No data at all, already handled
        
        status_parts = []
        
        # Check data completeness
        if greeks == 0:
            status_parts.append(f"Missing Greeks")
            self.stats['data_quality']['missing_greeks'] += 1
        elif greeks < ohlc:
            status_parts.append(f"Partial Greeks ({greeks}/{ohlc})")
        
        if iv == 0:
            status_parts.append(f"Missing IV")
            self.stats['data_quality']['missing_iv'] += 1
        elif iv < greeks:
            status_parts.append(f"IV gaps ({iv}/{greeks})")
            self.stats['data_quality']['iv_gaps'] += 1
        
        if sentinel_iv > 0:
            status_parts.append(f"Sentinel IVs: {sentinel_iv}")
            self.stats['data_quality']['sentinel_iv'] += sentinel_iv
        
        # Log based on completeness
        if not status_parts:
            logger.debug(f"Complete data: {symbol} ${strike:.0f}{opt_type} (OHLC:{ohlc}, Greeks:{greeks}, IV:{iv})")
            self.stats['data_quality']['complete_contracts'] += 1
        else:
            logger.warning(f"{symbol} ${strike:.0f}{opt_type}: {' | '.join(status_parts)}")
    
    def _log_daily_summary(self, symbol: str, date: date, daily_stats: Dict):
        """Log daily summary with data quality metrics"""
        total_contracts = daily_stats['downloaded'] + daily_stats['skipped']
        complete_pct = (self.stats['data_quality']['complete_contracts'] / daily_stats['downloaded'] * 100) if daily_stats['downloaded'] > 0 else 0
        
        logger.info("")
        logger.info(f"\nDaily Summary - {symbol} {date}:")
        logger.info(f"  Total contracts: {total_contracts}")
        logger.info(f"  Downloaded: {daily_stats['downloaded']}")
        logger.info(f"  Skipped (no volume): {daily_stats['skipped']}")
        logger.info(f"  Complete data: {self.stats['data_quality']['complete_contracts']} ({complete_pct:.1f}%)")
        
        if self.stats['data_quality']['missing_greeks'] > 0:
            logger.info(f"  Missing Greeks: {self.stats['data_quality']['missing_greeks']} contracts")
        if self.stats['data_quality']['missing_iv'] > 0:
            logger.info(f"  Missing IV: {self.stats['data_quality']['missing_iv']} contracts")
        if self.stats['data_quality']['iv_gaps'] > 0:
            logger.info(f"  IV gaps detected: {self.stats['data_quality']['iv_gaps']} contracts")
        if self.stats['data_quality']['sentinel_iv'] > 0:
            logger.info(f"  Sentinel IVs: {self.stats['data_quality']['sentinel_iv']} occurrences")
        
        logger.info("")
    
    def download_historical_data(self, symbol: str, start_date: date, end_date: date):
        """Download historical 1-minute data for a symbol with enhanced logging"""
        logger.info(f"Starting download for {symbol} from {start_date} to {end_date}")
        
        # Calculate total days for progress tracking
        self.total_days = self._calculate_total_trading_days(start_date, end_date)
        self.days_processed = 0
        self.start_time = time.time()
        
        # Reset stats for this symbol
        self.stats = {
            'contracts_checked': 0,
            'contracts_skipped_no_volume': 0,
            'contracts_downloaded': 0,
            'total_records': 0,
            'data_quality': {
                'complete_contracts': 0,
                'missing_greeks': 0,
                'missing_iv': 0,
                'sentinel_iv': 0,
                'iv_gaps': 0
            }
        }
        
        current_date = start_date
        
        while current_date <= end_date:
            try:
                # Skip weekends
                if current_date.weekday() in [5, 6]:
                    current_date += timedelta(days=1)
                    continue
                
                self.days_processed += 1
                
                # Get all contracts that were trading on this date
                contracts = self._get_contracts_for_trading_date(symbol, current_date)
                
                if not contracts:
                    logger.warning(f"No contracts found for {symbol} on {current_date}")
                    current_date += timedelta(days=1)
                    continue
                
                # Calculate contract details for logging
                strikes = [c['strike'] for c in contracts]
                strike_min = min(strikes) if strikes else 0
                strike_max = max(strikes) if strikes else 0
                calls = sum(1 for c in contracts if c['option_type'] == 'C')
                puts = sum(1 for c in contracts if c['option_type'] == 'P')
                
                # Log progress
                self._log_progress(symbol, current_date, len(contracts), strike_min, strike_max, calls, puts)
                
                # Track daily stats
                daily_stats = {
                    'downloaded': 0, 
                    'skipped': 0,
                    'records': 0,
                    'complete_start': self.stats['data_quality']['complete_contracts'],
                    'sentinel_start': self.stats['data_quality']['sentinel_iv'],
                    'gaps_start': self.stats['data_quality']['iv_gaps']
                }
                
                # Download data for each contract
                for contract in contracts:
                    self.stats['contracts_checked'] += 1
                    records, quality_info = self._download_contract_data(contract, current_date)
                    
                    if records > 0:
                        daily_stats['downloaded'] += 1
                        daily_stats['records'] += records
                        self.stats['contracts_downloaded'] += 1
                        self.stats['total_records'] += records
                        
                        # Log data quality
                        self._log_data_quality(contract, quality_info)
                    else:
                        daily_stats['skipped'] += 1
                        self.stats['contracts_skipped_no_volume'] += 1
                    
                    # Brief pause to avoid overwhelming the API
                    time.sleep(0.05)
                
                # Log daily summary
                self._log_daily_summary(symbol, current_date, daily_stats)
                
                # Move to next day
                current_date += timedelta(days=1)
                
            except Exception as e:
                logger.error(f"❌ Error processing {symbol} for {current_date}: {e}")
                # Continue with next day
                current_date += timedelta(days=1)
        
        # Log final statistics
        logger.info(f"\n{'='*60}")
        logger.info(f"\nDownload complete for {symbol}:")
        logger.info(f"  Total days processed: {self.days_processed}")
        logger.info(f"  Contracts checked: {self.stats['contracts_checked']:,}")
        logger.info(f"  Contracts downloaded: {self.stats['contracts_downloaded']:,}")
        logger.info(f"  Contracts skipped (no volume): {self.stats['contracts_skipped_no_volume']:,}")
        logger.info(f"  Total records: {self.stats['total_records']:,}")
        logger.info(f"\n  Data Quality Summary:")
        logger.info(f"  Complete contracts: {self.stats['data_quality']['complete_contracts']:,}")
        logger.info(f"  Missing Greeks: {self.stats['data_quality']['missing_greeks']:,}")
        logger.info(f"  Missing IV: {self.stats['data_quality']['missing_iv']:,}")
        logger.info(f"  IV gaps: {self.stats['data_quality']['iv_gaps']:,}")
        logger.info(f"  Sentinel IV occurrences: {self.stats['data_quality']['sentinel_iv']:,}")
        logger.info(f"{'='*60}\n")
        
        return self.stats['total_records']
    
    def _get_contracts_for_trading_date(self, symbol: str, trading_date: date) -> List[Dict]:
        """Get all option contracts that were trading on a specific date"""
        try:
            # Get symbol's price data for the trading date to determine strike range
            price_data = self._get_symbol_price_data(symbol, trading_date)
            if not price_data:
                logger.warning(f"No {symbol} price data for {trading_date}, skipping")
                return []
            
            # Get list of expirations
            url = f"{self.rest_base}/v2/list/expirations?root={symbol}"
            response = requests.get(url)
            
            if response.status_code != 200:
                logger.error(f"Failed to get expirations: {response.status_code}")
                return []
            
            data = response.json()
            if 'response' not in data:
                return []
            
            # Convert trading date to integer format
            trading_date_int = int(trading_date.strftime("%Y%m%d"))
            
            # For SPY and QQQ, focus on daily options (0DTE)
            valid_expirations = [exp for exp in data['response'] if exp == trading_date_int]
            
            if not valid_expirations:
                logger.debug(f"No valid expirations for {symbol} on {trading_date}")
                return []
            
            all_contracts = []
            
            # For each valid expiration, get contracts based on price range
            for exp in valid_expirations:
                exp_date = datetime.strptime(str(exp), "%Y%m%d").date()
                
                # Get contracts based on daily price range
                contracts = self._get_contracts_by_price_range(symbol, exp_date, trading_date, price_data)
                all_contracts.extend(contracts)
            
            return all_contracts
            
        except Exception as e:
            logger.error(f"Error getting contracts for trading date: {e}")
            return []
    
    def _get_symbol_price_data(self, symbol: str, trading_date: date) -> Optional[Dict[str, float]]:
        """Get non-adjusted price data for a symbol on a specific date"""
        try:
            # Check database for price data
            cursor = self.conn.cursor()
            # Use correct table names
            if symbol == 'SPY':
                table_name = 'spy_prices_raw'
            elif symbol == 'QQQ':
                table_name = 'qqq_prices_raw'
            else:
                table_name = f"{symbol.lower()}_price_data"
                
            cursor.execute(f"""
                SELECT open, high, low, close 
                FROM {table_name}
                WHERE date = %s
            """, (trading_date,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'open': float(result[0]),
                    'high': float(result[1]),
                    'low': float(result[2]),
                    'close': float(result[3])
                }
            return None
            
            # Response format: [ms_of_day, open, high, low, close, volume, count, date]
            eod_data = data['response'][0]
            if isinstance(eod_data, list) and len(eod_data) >= 5:
                return {
                    'open': float(eod_data[1]),
                    'high': float(eod_data[2]),
                    'low': float(eod_data[3]),
                    'close': float(eod_data[4])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting {symbol} price data: {e}")
            # Rollback on error to prevent transaction abort
            self.conn.rollback()
            return None
    
    def _get_spy_price_data(self, trading_date: date) -> Optional[Dict[str, float]]:
        """Get non-adjusted SPY price data for a specific date from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT open, high, low, close, volume
                FROM public.spy_prices_raw
                WHERE date = %s
            """, (trading_date,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'open': float(result[0]),
                    'high': float(result[1]),
                    'low': float(result[2]),
                    'close': float(result[3]),
                    'volume': int(result[4]) if result[4] else 0,
                    'atm_strike': float(result[3])
                }
            else:
                logger.warning(f"No non-adjusted SPY data for {trading_date}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting SPY price data: {e}")
            return None
    
    def _get_contracts_by_price_range(self, symbol: str, expiration: date, trading_date: date, price_data: Dict[str, float]) -> List[Dict]:
        """Get contracts based on the day's price range plus buffer"""
        contracts = []
        
        # Calculate the day's range for the symbol
        price_low = price_data['low']
        price_high = price_data['high']
        
        # Use the symbol's actual price range
        ref_low = price_low
        ref_high = price_high
        
        # Get strike increment for the symbol
        if symbol in self.symbol_configs:
            strike_increment = self.symbol_configs[symbol]['strike_increment']
        else:
            # Default to $1 strikes
            strike_increment = 1.0
            logger.warning(f"No strike increment configured for {symbol}, using default $1")
        
        # Use 1% buffer to capture more OTM options
        buffer_percent = 0.01
        
        # Calculate strike boundaries with buffer
        min_strike = int(ref_low * (1 - buffer_percent))
        max_strike = int(ref_high * (1 + buffer_percent)) + 1
        
        # Generate strikes
        current_strike = min_strike
        while current_strike <= max_strike:
            # Add call option
            contracts.append({
                'symbol': symbol,
                'expiration': expiration,
                'strike': float(current_strike),
                'option_type': 'C',
                'contract_id': None
            })
            
            # Add put option
            contracts.append({
                'symbol': symbol,
                'expiration': expiration,
                'strike': float(current_strike),
                'option_type': 'P',
                'contract_id': None
            })
            
            current_strike += strike_increment
        
        return contracts
    
    def _check_contract_has_volume(self, contract: Dict, date: date) -> bool:
        """Quick check if contract has any volume for the day"""
        try:
            # Use EOD endpoint for quick volume check
            exp_str = contract['expiration'].strftime("%Y%m%d")
            strike_int = int(contract['strike'] * 1000)
            date_str = date.strftime("%Y%m%d")
            
            url = (f"{self.rest_base}/hist/option/eod"
                   f"?root={contract['symbol']}"
                   f"&exp={exp_str}"
                   f"&strike={strike_int}"
                   f"&right={contract['option_type']}"
                   f"&start_date={date_str}"
                   f"&end_date={date_str}")
            
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                return True  # If we can't check, assume it has volume
            
            data = response.json()
            
            # Check for no data response
            if 'response' not in data or not data['response']:
                return False
            
            # Check if response is [0] (no data)
            if isinstance(data['response'], list) and len(data['response']) == 1 and data['response'][0] == 0:
                return False
            
            # Check if any EOD record has volume
            for eod_record in data['response']:
                if isinstance(eod_record, list) and len(eod_record) >= 7:
                    volume = eod_record[4] if len(eod_record) > 4 else 0
                    if volume and volume > 0:
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Volume check error, proceeding with download: {e}")
            return True
    
    def _download_contract_data(self, contract: Dict, date: date) -> Tuple[int, Dict]:
        """Download 1-minute data for a specific contract and return quality info"""
        quality_info = {
            'ohlc_count': 0,
            'greeks_count': 0,
            'iv_count': 0,
            'sentinel_iv_count': 0,
            'iv_gaps': []
        }
        
        try:
            # First do a quick volume check to see if contract traded
            has_volume = self._check_contract_has_volume(contract, date)
            if not has_volume:
                return 0, quality_info
            
            # Get or create contract ID
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT theta.get_or_create_contract(%s, %s, %s, %s)",
                (contract['symbol'], contract['expiration'], contract['strike'], contract['option_type'])
            )
            contract_id = cursor.fetchone()[0]
            self.conn.commit()
            
            # Download OHLC data
            ohlc_records = self._download_ohlc(contract, contract_id, date)
            quality_info['ohlc_count'] = ohlc_records
            
            # Only download Greeks/IV if we got OHLC data
            greeks_records = 0
            iv_records = 0
            
            if ohlc_records > 0:
                # Download Greeks (which includes IV)
                greeks_records, iv_count, sentinel_iv_count = self._download_greeks_with_iv(contract, contract_id, date)
                quality_info['greeks_count'] = greeks_records
                quality_info['iv_count'] = iv_count
                quality_info['sentinel_iv_count'] = sentinel_iv_count
            
            total_records = ohlc_records + greeks_records
            
            return total_records, quality_info
            
        except Exception as e:
            logger.error(f"Error downloading contract data: {e}")
            return 0, quality_info
    
    def _log_quality_issue(self, contract_id: int, datetime: datetime, issue_type: str, 
                          field_name: str, original_value: float, contract: Dict,
                          underlying_price: float = None):
        """Log data quality issue to database for later cleanup"""
        try:
            cursor = self.conn.cursor()
            
            # Calculate time to expiry
            expiry_date = contract['expiration']
            time_to_expiry = (expiry_date - datetime.date()).days
            
            # Calculate moneyness
            strike = contract['strike']
            if underlying_price and underlying_price > 0:
                if contract['option_type'] == 'C':
                    moneyness = underlying_price / strike
                else:  # Put
                    moneyness = strike / underlying_price
            else:
                moneyness = None
            
            cursor.execute("""
                INSERT INTO theta.data_quality_issues 
                (contract_id, datetime, issue_type, field_name, original_value,
                 symbol, strike, option_type, expiration, underlying_price,
                 time_to_expiry, moneyness)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                contract_id, datetime, issue_type, field_name, original_value,
                contract['symbol'], strike, contract['option_type'], 
                expiry_date, underlying_price, time_to_expiry, moneyness
            ))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error logging quality issue: {e}")
            self.conn.rollback()
    
    def _download_ohlc(self, contract: Dict, contract_id: int, date: date) -> int:
        """Download 1-minute OHLC data"""
        try:
            # Format request
            exp_str = contract['expiration'].strftime("%Y%m%d")
            strike_int = int(contract['strike'] * 1000)
            date_str = date.strftime("%Y%m%d")
            
            url = (f"{self.rest_base}/hist/option/ohlc"
                   f"?root={contract['symbol']}"
                   f"&exp={exp_str}"
                   f"&strike={strike_int}"
                   f"&right={contract['option_type']}"
                   f"&start_date={date_str}"
                   f"&end_date={date_str}"
                   f"&ivl=60000")  # 60000ms = 1 minute
            
            response = requests.get(url)
            
            if response.status_code != 200:
                logger.error(f"Failed to get OHLC data: {response.status_code}")
                return 0
            
            data = response.json()
            
            if 'response' not in data or not data['response']:
                return 0
            
            # Check if response is just [0] which means no data
            if isinstance(data['response'], list) and len(data['response']) == 1 and data['response'][0] == 0:
                return 0
            
            # Parse and insert data
            cursor = self.conn.cursor()
            records = 0
            
            for tick in data['response']:
                # Skip if tick is just an integer (error code)
                if isinstance(tick, int):
                    continue
                
                # Format: [ms_of_day, open, high, low, close, volume, count, date]
                if isinstance(tick, list) and len(tick) >= 8:
                    # Parse date as YYYYMMDD integer
                    date_int = int(tick[7])
                    year = date_int // 10000
                    month = (date_int % 10000) // 100
                    day = date_int % 100
                    
                    # Add time of day from ms_of_day
                    ms_of_day = tick[0]
                    hour = ms_of_day // 3600000
                    minute = (ms_of_day % 3600000) // 60000
                    second = (ms_of_day % 60000) // 1000
                    
                    timestamp = datetime(year, month, day, hour, minute, second)
                    
                    # Skip records with all zero prices (no trading activity)
                    if tick[1] == 0 and tick[2] == 0 and tick[3] == 0 and tick[4] == 0:
                        continue
                    
                    cursor.execute("""
                        INSERT INTO theta.options_ohlc 
                        (contract_id, datetime, open, high, low, close, volume, trade_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (contract_id, datetime) DO UPDATE
                        SET open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            trade_count = EXCLUDED.trade_count
                    """, (
                        contract_id, timestamp,
                        tick[1], tick[2], tick[3], tick[4],  # OHLC
                        tick[5], tick[6]  # Volume, trade count
                    ))
                    records += 1
            
            self.conn.commit()
            return records
            
        except Exception as e:
            logger.error(f"Error downloading OHLC: {e}")
            self.conn.rollback()
            return 0
    
    def _download_greeks_with_iv(self, contract: Dict, contract_id: int, date: date) -> Tuple[int, int, int]:
        """Download 1-minute Greeks data including IV, return (greeks_count, iv_count, sentinel_iv_count)"""
        try:
            exp_str = contract['expiration'].strftime("%Y%m%d")
            strike_int = int(contract['strike'] * 1000)
            date_str = date.strftime("%Y%m%d")
            
            url = (f"{self.rest_base}/hist/option/greeks"
                   f"?root={contract['symbol']}"
                   f"&exp={exp_str}"
                   f"&strike={strike_int}"
                   f"&right={contract['option_type']}"
                   f"&start_date={date_str}"
                   f"&end_date={date_str}"
                   f"&ivl=60000")
            
            response = requests.get(url)
            
            if response.status_code != 200:
                return 0, 0, 0
            
            data = response.json()
            
            if 'response' not in data or not data['response']:
                return 0, 0, 0
            
            # Check if response is just [0] which means no data
            if isinstance(data['response'], list) and len(data['response']) == 1 and data['response'][0] == 0:
                return 0, 0, 0
            
            cursor = self.conn.cursor()
            greeks_records = 0
            iv_records = 0
            sentinel_iv_count = 0
            
            for tick in data['response']:
                # Skip if tick is just an integer (error code)
                if isinstance(tick, int):
                    continue
                
                # Format: [ms_of_day, delta, theta, vega, rho, epsilon, lambda, implied_vol, underlying_price, date]
                if isinstance(tick, list) and len(tick) >= 10:
                    # Parse date
                    date_int = int(tick[9])
                    year = date_int // 10000
                    month = (date_int % 10000) // 100
                    day = date_int % 100
                    
                    # Add time of day from ms_of_day
                    ms_of_day = tick[0]
                    hour = ms_of_day // 3600000
                    minute = (ms_of_day % 3600000) // 60000
                    second = (ms_of_day % 60000) // 1000
                    
                    timestamp = datetime(year, month, day, hour, minute, second)
                    
                    # Extract values
                    delta = tick[1] if tick[1] is not None else None
                    gamma = None  # Not provided
                    theta = tick[2] if tick[2] is not None else None
                    vega = tick[3] if tick[3] is not None else None
                    rho = tick[4] if tick[4] is not None else None
                    implied_vol = tick[7] if len(tick) > 7 and tick[7] is not None else None
                    
                    # Round to reasonable precision
                    delta = round(delta, 4) if delta is not None else None
                    theta = round(theta, 4) if theta is not None else None
                    vega = round(vega, 4) if vega is not None else None
                    rho = round(rho, 4) if rho is not None else None
                    implied_vol = round(implied_vol, 4) if implied_vol is not None else None
                    
                    # Get underlying price for moneyness calculation
                    underlying_price = tick[8] if len(tick) > 8 else None
                    
                    # Check for sentinel IV values (negative values from ThetaData API)
                    if implied_vol is not None and implied_vol < 0:
                        sentinel_iv_count += 1
                        # Log to quality issues table
                        self._log_quality_issue(
                            contract_id, timestamp, 'sentinel_iv', 
                            'implied_volatility', implied_vol, contract,
                            underlying_price
                        )
                        # Don't store negative IV in database
                        implied_vol_to_store = None
                    else:
                        implied_vol_to_store = implied_vol
                    
                    # Insert Greeks
                    cursor.execute("""
                        INSERT INTO theta.options_greeks 
                        (contract_id, datetime, delta, gamma, theta, vega, rho)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (contract_id, datetime) DO UPDATE
                        SET delta = EXCLUDED.delta,
                            gamma = EXCLUDED.gamma,
                            theta = EXCLUDED.theta,
                            vega = EXCLUDED.vega,
                            rho = EXCLUDED.rho
                    """, (
                        contract_id, timestamp,
                        delta, gamma, theta, vega, rho
                    ))
                    greeks_records += 1
                    
                    # Insert IV if available (excluding sentinel values)
                    if implied_vol_to_store is not None:
                        cursor.execute("""
                            INSERT INTO theta.options_iv 
                            (contract_id, datetime, implied_volatility, is_interpolated)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (contract_id, datetime) DO UPDATE
                            SET implied_volatility = EXCLUDED.implied_volatility,
                                is_interpolated = EXCLUDED.is_interpolated
                        """, (
                            contract_id, timestamp,
                            implied_vol_to_store, False
                        ))
                        iv_records += 1
            
            self.conn.commit()
            return greeks_records, iv_records, sentinel_iv_count
            
        except Exception as e:
            logger.error(f"Error downloading Greeks: {e}")
            self.conn.rollback()
            return 0, 0, 0
    
    def run_test_download(self):
        """Run test download for one week of each symbol"""
        logger.info("Starting test download (1 week each)")
        
        # Test periods for each symbol
        test_configs = {
            'SPY': {
                'start': date(2022, 12, 5),
                'end': date(2022, 12, 9)
            },
            'QQQ': {
                'start': date(2023, 1, 9),
                'end': date(2023, 1, 13)
            }
        }
        
        for symbol, config in test_configs.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"Downloading {symbol} for test period: {config['start']} to {config['end']}")
            logger.info(f"{'='*50}")
            
            records = self.download_historical_data(symbol, config['start'], config['end'])
            
            # Show summary
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT contract_id) as contracts,
                       MIN(datetime) as earliest,
                       MAX(datetime) as latest
                FROM theta.options_ohlc
                WHERE contract_id IN (
                    SELECT contract_id FROM theta.options_contracts
                    WHERE symbol = %s AND expiration BETWEEN %s AND %s
                )
            """, (symbol, config['start'], config['end']))
            
            result = cursor.fetchone()
            logger.info(f"\nSummary for {symbol}:")
            logger.info(f"  Total records: {result[0]:,}")
            logger.info(f"  Unique contracts: {result[1]:,}")
            logger.info(f"  Date range: {result[2]} to {result[3]}")
    
    def run_full_download(self, symbol: str = None):
        """Run full historical download for specified symbol or all symbols"""
        logger.info("Starting full historical download")
        
        if symbol:
            symbols = [symbol] if symbol in self.symbol_configs else []
            if not symbols:
                logger.error(f"Unknown symbol: {symbol}")
                return
        else:
            symbols = list(self.symbol_configs.keys())
        
        # Process month by month
        from dateutil.relativedelta import relativedelta
        overall_start = datetime.now()
        
        # Start from Dec 2022
        current_month = date(2022, 12, 1)
        end_date = date.today()
        
        month_count = 0
        while current_month <= end_date:
            month_count += 1
            month_end = min(current_month + relativedelta(months=1) - timedelta(days=1), end_date)
            
            logger.info(f"\n{'='*80}")
            logger.info(f"PROCESSING MONTH {month_count}: {current_month.strftime('%B %Y')}")
            logger.info(f"{'='*80}")
            
            month_stats = {}
            
            # Download each symbol for this month
            for sym in symbols:
                logger.info(f"\nStarting {sym} for {current_month.strftime('%B %Y')}")
                logger.info(f"{'-'*60}")
                
                # Reset stats for this symbol/month
                self.stats = {
                    'contracts_checked': 0,
                    'contracts_downloaded': 0,
                    'contracts_skipped_no_volume': 0,
                    'total_records': 0,
                    'data_quality': {
                        'complete_contracts': 0,
                        'missing_greeks': 0,
                        'missing_iv': 0,
                        'sentinel_iv': 0,
                        'iv_gaps': 0
                    }
                }
                self.days_processed = 0
                
                records = self.download_historical_data(sym, current_month, month_end)
                
                # Store stats for summary
                month_stats[sym] = self.stats.copy()
                month_stats[sym]['days_processed'] = self.days_processed
                
                logger.info(f"\n{sym} completed for {current_month.strftime('%B %Y')}")
            
            # Print monthly summary
            logger.info(f"\n{'='*80}")
            logger.info(f"MONTHLY SUMMARY - {current_month.strftime('%B %Y')}")
            logger.info(f"{'='*80}")
            
            for sym in symbols:
                stats = month_stats.get(sym, {})
                logger.info(f"\n{sym} Summary:")
                logger.info(f"  Days processed: {stats.get('days_processed', 0)}")
                logger.info(f"  Contracts checked: {stats.get('contracts_checked', 0):,}")
                logger.info(f"  Contracts downloaded: {stats.get('contracts_downloaded', 0):,}")
                logger.info(f"  Contracts skipped (no volume): {stats.get('contracts_skipped_no_volume', 0):,}")
                logger.info(f"  Total records: {stats.get('total_records', 0):,}")
                
                dq = stats.get('data_quality', {})
                logger.info(f"  Data Quality:")
                logger.info(f"    Complete contracts: {dq.get('complete_contracts', 0):,}")
                logger.info(f"    Missing Greeks: {dq.get('missing_greeks', 0):,}")
                logger.info(f"    Missing IV: {dq.get('missing_iv', 0):,}")
                logger.info(f"    Sentinel IV occurrences: {dq.get('sentinel_iv', 0):,}")
                logger.info(f"    IV gaps: {dq.get('iv_gaps', 0):,}")
            
            # Move to next month
            current_month = current_month + relativedelta(months=1)
        
        # Overall summary
        elapsed = datetime.now() - overall_start
        logger.info(f"\n{'='*80}")
        logger.info(f"FULL DOWNLOAD COMPLETED")
        logger.info(f"Total time: {elapsed}")
        logger.info(f"Total months processed: {month_count}")
        logger.info(f"{'='*80}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--full':
            logger.info("Running FULL historical download for all symbols")
            downloader = ThetaHistoricalDownloader()
            try:
                downloader.run_full_download()
            finally:
                downloader.close()
        elif sys.argv[1] == '--spy':
            logger.info("Running FULL historical download for SPY only")
            downloader = ThetaHistoricalDownloader()
            try:
                downloader.run_full_download('SPY')
            finally:
                downloader.close()
        elif sys.argv[1] == '--qqq':
            logger.info("Running FULL historical download for QQQ only")
            downloader = ThetaHistoricalDownloader()
            try:
                downloader.run_full_download('QQQ')
            finally:
                downloader.close()
        else:
            print("Usage: python download_1min_data_enhanced.py [--full|--spy|--qqq]")
            print("  (no args)  Run test download (1 month each)")
            print("  --full     Run full historical download for all symbols")
            print("  --spy      Run full historical download for SPY only")
            print("  --qqq      Run full historical download for QQQ only")
    else:
        logger.info("Running TEST download (1 month each)")
        downloader = ThetaHistoricalDownloader()
        try:
            downloader.run_test_download()
        finally:
            downloader.close()


if __name__ == "__main__":
    main()