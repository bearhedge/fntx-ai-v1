#!/usr/bin/env python3
"""
Checkpoint-based daily downloader for December 2022 0DTE SPY options
Downloads a single day with progress tracking and recovery capability
"""
import sys
import os
import json
import requests
import psycopg2
import yfinance as yf
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from psycopg2.extras import execute_batch
import argparse

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

class DailyCheckpointDownloader:
    def __init__(self, checkpoint_file: str = "december_2022_progress.json"):
        self.base_url = "http://127.0.0.1:25510/v2/hist/option"
        self.delay = 0.3  # 300ms between requests
        self.interval = 300000  # 5 minutes in milliseconds
        self.checkpoint_file = checkpoint_file
        self.batch_size = 10  # Contracts per database commit
        
        # Load or create checkpoint
        self.checkpoint = self.load_checkpoint()
        
    def load_checkpoint(self) -> Dict:
        """Load checkpoint file or create new one"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "status": "initialized",
                "trading_days": {},
                "last_successful": None,
                "total_contracts": 0,
                "total_ohlc_bars": 0,
                "total_greeks_bars": 0,
                "total_iv_bars": 0
            }
    
    def save_checkpoint(self):
        """Save checkpoint to file"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2, default=str)
    
    def get_spy_open_price(self, date: datetime) -> Optional[float]:
        """Get SPY opening price for the given date"""
        try:
            spy = yf.Ticker('SPY')
            data = spy.history(start=date.strftime('%Y-%m-%d'), 
                              end=(date + timedelta(days=1)).strftime('%Y-%m-%d'))
            if not data.empty:
                return float(data['Open'].iloc[0])
        except Exception as e:
            print(f"Error getting SPY price: {e}")
        return None
    
    def discover_strikes(self, exp_str: str) -> List[int]:
        """Discover available strikes for the expiration date"""
        strikes = []
        
        # Test strike range (SPY typically 300-500 in Dec 2022)
        for strike in range(300, 500, 1):
            params = {
                'root': 'SPY',
                'exp': exp_str,
                'strike': strike * 1000,
                'right': 'C',
                'start_date': exp_str,
                'end_date': exp_str,
                'ivl': 3600000  # 1 hour for quick test
            }
            
            try:
                r = requests.get(f"{self.base_url}/ohlc", params=params, timeout=2)
                if r.status_code == 200 and r.json().get('response'):
                    strikes.append(strike)
            except:
                pass
            
            time.sleep(0.02)  # Small delay
            
        return sorted(strikes)
    
    def select_strikes(self, spy_open: float, available_strikes: List[int], 
                      strike_count: int = 40) -> List[int]:
        """Select strikes based on count from ATM"""
        if not available_strikes:
            return []
            
        # Find ATM strike
        atm_strike = min(available_strikes, key=lambda x: abs(x - spy_open))
        atm_index = available_strikes.index(atm_strike)
        
        # Select strikes
        start_idx = max(0, atm_index - strike_count)
        end_idx = min(len(available_strikes), atm_index + strike_count + 1)
        
        selected = available_strikes[start_idx:end_idx]
        
        print(f"   ATM: ${atm_strike} (SPY: ${spy_open:.2f})")
        print(f"   Selected: {len(selected)} strikes (${min(selected)}-${max(selected)})")
        
        return selected
    
    def parse_timestamp(self, ms_of_day: int, date_int: int) -> datetime:
        """Parse timestamp from ms_of_day and date integer"""
        hours = ms_of_day // (1000 * 60 * 60)
        minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
        seconds = (ms_of_day % (1000 * 60)) // 1000
        
        year = date_int // 10000
        month = (date_int % 10000) // 100
        day = date_int % 100
        
        return datetime(year, month, day, hours, minutes, seconds)
    
    def download_contract_data(self, exp_str: str, strike: int, right: str) -> Dict:
        """Download all data types for a contract with retries"""
        data = {'ohlc': [], 'greeks': [], 'iv': []}
        max_retries = 3
        
        for data_type, endpoint in [
            ('ohlc', 'ohlc'),
            ('greeks', 'greeks'),
            ('iv', 'implied_volatility')
        ]:
            url = f"{self.base_url}/{endpoint}"
            params = {
                'root': 'SPY',
                'exp': exp_str,
                'strike': strike * 1000,
                'right': right,
                'start_date': exp_str,
                'end_date': exp_str,
                'ivl': self.interval
            }
            
            for retry in range(max_retries):
                try:
                    r = requests.get(url, params=params, timeout=10)
                    if r.status_code == 200:
                        data[data_type] = r.json().get('response', [])
                        break
                except Exception as e:
                    if retry == max_retries - 1:
                        print(f"   Failed {data_type} for ${strike}{right}: {str(e)[:50]}")
                    else:
                        time.sleep(1)  # Wait before retry
                
            time.sleep(self.delay)
        
        return data
    
    def save_contract_batch(self, cursor, contracts_data: List[Tuple]) -> Dict:
        """Save a batch of contracts to database"""
        total_stats = {'contracts': 0, 'ohlc': 0, 'greeks': 0, 'iv': 0}
        
        for trade_date, strike, right, data in contracts_data:
            # Insert contract
            cursor.execute("""
                INSERT INTO theta.options_contracts 
                (symbol, expiration, strike, option_type)
                VALUES ('SPY', %s, %s, %s)
                ON CONFLICT (symbol, strike, expiration, option_type)
                DO NOTHING
                RETURNING contract_id
            """, (trade_date, strike, right))
            
            result = cursor.fetchone()
            if result:
                contract_id = result[0]
            else:
                cursor.execute("""
                    SELECT contract_id FROM theta.options_contracts
                    WHERE symbol='SPY' AND expiration=%s 
                    AND strike=%s AND option_type=%s
                """, (trade_date, strike, right))
                contract_id = cursor.fetchone()[0]
            
            total_stats['contracts'] += 1
            exp_int = int(trade_date.strftime('%Y%m%d'))
            
            # Save OHLC
            ohlc_batch = []
            for bar in data['ohlc']:
                ts = self.parse_timestamp(bar[0], exp_int)
                
                # Skip bars with 0 prices (invalid data)
                if float(bar[1]) == 0 or float(bar[2]) == 0 or float(bar[3]) == 0 or float(bar[4]) == 0:
                    continue
                    
                ohlc_batch.append((
                    contract_id, ts,
                    float(bar[1]), float(bar[2]),
                    float(bar[3]), float(bar[4]),
                    int(bar[5]), int(bar[6])
                ))
            
            if ohlc_batch:
                execute_batch(cursor, """
                    INSERT INTO theta.options_ohlc
                    (contract_id, datetime, open, high, low, close, volume, trade_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, ohlc_batch)
                total_stats['ohlc'] += len(ohlc_batch)
            
            # Save Greeks
            greeks_batch = []
            for greek in data['greeks']:
                ts = self.parse_timestamp(greek[0], exp_int)
                
                delta = float(greek[3]) if greek[3] is not None else None
                gamma = float(greek[4]) if greek[4] is not None else None
                theta = float(greek[5]) if greek[5] is not None else None
                vega = float(greek[6]) if greek[6] is not None else None
                rho = float(greek[7]) if greek[7] is not None else None
                
                greeks_batch.append((contract_id, ts, delta, gamma, theta, vega, rho))
            
            if greeks_batch:
                execute_batch(cursor, """
                    INSERT INTO theta.options_greeks
                    (contract_id, datetime, delta, gamma, theta, vega, rho)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, greeks_batch)
                total_stats['greeks'] += len(greeks_batch)
            
            # Save IV
            iv_batch = []
            for iv in data['iv']:
                ts = self.parse_timestamp(iv[0], exp_int)
                
                # IV is in different fields for calls vs puts
                if right == 'C':
                    implied_vol = float(iv[4]) if iv[4] is not None and iv[4] > 0 else None
                else:  # Put
                    implied_vol = float(iv[2]) if iv[2] is not None and iv[2] > 0 else None
                
                if implied_vol:
                    iv_batch.append((contract_id, ts, implied_vol))
            
            if iv_batch:
                execute_batch(cursor, """
                    INSERT INTO theta.options_iv
                    (contract_id, datetime, implied_volatility)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, iv_batch)
                total_stats['iv'] += len(iv_batch)
        
        return total_stats
    
    def download_day(self, trade_date: datetime, strike_count: int = 40) -> Dict:
        """Download complete data for a single day"""
        date_str = trade_date.strftime('%Y-%m-%d')
        exp_str = trade_date.strftime('%Y%m%d')
        
        print(f"\n{'='*80}")
        print(f"Processing {date_str} ({trade_date.strftime('%A')})")
        print(f"{'='*80}")
        
        # Check if already complete
        if date_str in self.checkpoint['trading_days']:
            day_data = self.checkpoint['trading_days'][date_str]
            if day_data.get('status') == 'complete':
                print(f"✓ Already complete: {day_data['contracts']} contracts, "
                      f"{day_data['coverage']:.1f}% coverage")
                return day_data
        
        # Get SPY open
        spy_open = self.get_spy_open_price(trade_date)
        if not spy_open:
            print("✗ Could not get SPY opening price")
            return {'success': False, 'reason': 'No SPY price'}
        
        print(f"SPY Open: ${spy_open:.2f}")
        
        # Discover strikes
        print("Discovering available strikes...")
        all_strikes = self.discover_strikes(exp_str)
        
        if not all_strikes:
            print("✗ No strikes available")
            return {'success': False, 'reason': 'No strikes'}
        
        print(f"Found {len(all_strikes)} strikes: ${min(all_strikes)}-${max(all_strikes)}")
        
        # Select strikes
        selected_strikes = self.select_strikes(spy_open, all_strikes, strike_count)
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Initialize day tracking
            if date_str not in self.checkpoint['trading_days']:
                self.checkpoint['trading_days'][date_str] = {
                    'status': 'in_progress',
                    'contracts': 0,
                    'ohlc_bars': 0,
                    'greeks_bars': 0,
                    'iv_bars': 0,
                    'last_strike': None,
                    'spy_open': spy_open,
                    'atm_strike': min(selected_strikes, key=lambda x: abs(x - spy_open))
                }
            
            day_info = self.checkpoint['trading_days'][date_str]
            
            # Resume from last strike if interrupted
            start_from = 0
            if day_info['last_strike']:
                try:
                    start_from = selected_strikes.index(day_info['last_strike']) + 1
                    print(f"Resuming from strike index {start_from}")
                except ValueError:
                    start_from = 0
            
            # Process in batches
            batch_data = []
            total_processed = day_info['contracts']
            
            for i in range(start_from, len(selected_strikes)):
                strike = selected_strikes[i]
                
                for right in ['C', 'P']:
                    # Download data
                    data = self.download_contract_data(exp_str, strike, right)
                    
                    if data['ohlc']:
                        batch_data.append((trade_date, strike, right, data))
                    
                    # Save batch
                    if len(batch_data) >= self.batch_size:
                        stats = self.save_contract_batch(cursor, batch_data)
                        conn.commit()
                        
                        # Update checkpoint
                        day_info['contracts'] += stats['contracts']
                        day_info['ohlc_bars'] += stats['ohlc']
                        day_info['greeks_bars'] += stats['greeks']
                        day_info['iv_bars'] += stats['iv']
                        day_info['last_strike'] = strike
                        
                        self.checkpoint['total_contracts'] += stats['contracts']
                        self.checkpoint['total_ohlc_bars'] += stats['ohlc']
                        self.checkpoint['total_greeks_bars'] += stats['greeks']
                        self.checkpoint['total_iv_bars'] += stats['iv']
                        
                        self.save_checkpoint()
                        
                        total_processed += stats['contracts']
                        print(f"  Progress: {total_processed} contracts, "
                              f"{day_info['ohlc_bars']} OHLC bars")
                        
                        batch_data = []
            
            # Save final batch
            if batch_data:
                stats = self.save_contract_batch(cursor, batch_data)
                conn.commit()
                
                day_info['contracts'] += stats['contracts']
                day_info['ohlc_bars'] += stats['ohlc']
                day_info['greeks_bars'] += stats['greeks']
                day_info['iv_bars'] += stats['iv']
                
                self.checkpoint['total_contracts'] += stats['contracts']
                self.checkpoint['total_ohlc_bars'] += stats['ohlc']
                self.checkpoint['total_greeks_bars'] += stats['greeks']
                self.checkpoint['total_iv_bars'] += stats['iv']
            
            # Calculate coverage
            expected_bars = 78  # 6.5 hours * 12 bars/hour
            expected_total = expected_bars * day_info['contracts']
            coverage = (day_info['ohlc_bars'] / expected_total * 100) if expected_total > 0 else 0
            
            # Mark complete
            day_info['status'] = 'complete'
            day_info['coverage'] = coverage
            day_info['strikes'] = len(selected_strikes)
            day_info['strike_range'] = f"${min(selected_strikes)}-${max(selected_strikes)}"
            
            self.checkpoint['last_successful'] = date_str
            self.checkpoint['status'] = 'in_progress'
            self.save_checkpoint()
            
            print(f"\n✓ Complete: {day_info['contracts']} contracts")
            print(f"  OHLC: {day_info['ohlc_bars']} bars ({coverage:.1f}% coverage)")
            print(f"  Greeks: {day_info['greeks_bars']} bars")
            print(f"  IV: {day_info['iv_bars']} bars")
            
            return {
                'success': True,
                **day_info
            }
            
        except Exception as e:
            conn.rollback()
            print(f"\n✗ Error: {str(e)}")
            
            # Save partial progress
            self.save_checkpoint()
            
            return {
                'success': False,
                'reason': str(e)[:100]
            }
            
        finally:
            cursor.close()
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Download December 2022 0DTE data for a single day')
    parser.add_argument('--date', type=str, required=True,
                       help='Date to download (YYYY-MM-DD)')
    parser.add_argument('--strikes', type=int, default=40,
                       help='Number of strikes above/below ATM (default: 40)')
    parser.add_argument('--checkpoint', type=str, default='december_2022_progress.json',
                       help='Checkpoint file path')
    
    args = parser.parse_args()
    
    # Parse date
    try:
        trade_date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"Invalid date format: {args.date}")
        return 1
    
    # Create downloader
    downloader = DailyCheckpointDownloader(checkpoint_file=args.checkpoint)
    
    # Download the day
    result = downloader.download_day(trade_date, strike_count=args.strikes)
    
    if result.get('success'):
        print("\n✓ Day download successful!")
        return 0
    else:
        print(f"\n✗ Day download failed: {result.get('reason', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())