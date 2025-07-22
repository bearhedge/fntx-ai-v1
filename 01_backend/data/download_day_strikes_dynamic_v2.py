#!/usr/bin/env python3
"""
Dynamic Strike-aware daily downloader for 0DTE SPY options - V2
- Uses implied volatility to determine optimal strike selection
- PRESERVES NULL IV values instead of filtering them out
"""
import sys
import os
import json
import requests
import psycopg2
import yfinance as yf
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
from psycopg2.extras import execute_batch
import argparse

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG
from dynamic_strike_selector import DynamicStrikeSelector
from smart_strike_selector import SmartStrikeSelector

class DynamicStrikeDownloaderV2:
    def __init__(self, checkpoint_file: str = None, use_dynamic_selection: bool = True):
        self.base_url = "http://127.0.0.1:25510/v2/hist/option"
        self.delay = 0.3  # 300ms between requests
        self.interval = 300000  # 5 minutes in milliseconds
        self.batch_size = 10  # Contracts per database commit
        
        # Dynamic strike selection
        self.use_dynamic_selection = use_dynamic_selection
        if use_dynamic_selection:
            self.dynamic_selector = DynamicStrikeSelector(self.base_url)
        else:
            # Fallback to smart selector
            self.smart_selector = SmartStrikeSelector(self.base_url)
        
        # Volume filtering
        self.min_volume_bars = 60  # 5 hours of trading data
        
        # Set checkpoint file based on date if not provided
        self.checkpoint_file = checkpoint_file
        
        # IV diagnostic tracking
        self.iv_stats = {
            'total_points': 0,
            'valid_ivs': 0,
            'zero_ivs': 0,
            'null_stored': 0
        }
        
    def get_checkpoint_filename(self, date: datetime) -> str:
        """Generate checkpoint filename for a specific date"""
        if self.checkpoint_file:
            return self.checkpoint_file
        return f"checkpoint_{date.strftime('%Y%m%d')}_dynamic_v2.json"
        
    def load_checkpoint(self, date: datetime) -> Dict:
        """Load checkpoint file or create new one"""
        checkpoint_file = self.get_checkpoint_filename(date)
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                # Restore IV stats if available
                if 'iv_stats' in checkpoint:
                    self.iv_stats = checkpoint['iv_stats']
                return checkpoint
        else:
            return {
                "date": date.strftime('%Y-%m-%d'),
                "status": "initialized",
                "dynamic_strikes": {
                    "status": "pending", 
                    "contracts": 0, 
                    "strikes": [], 
                    "last_strike": None,
                    "volume_filtered": 0
                },
                "stats": {
                    "total_contracts": 0,
                    "total_ohlc_bars": 0,
                    "total_greeks_bars": 0,
                    "total_iv_bars": 0,
                    "total_iv_nulls": 0,
                    "spy_open": None,
                    "atm_strike": None,
                    "atm_iv": None,
                    "strike_selection_method": "dynamic" if self.use_dynamic_selection else "smart",
                    "strikes_per_side": None,
                    "volume_filtered_count": 0
                },
                "iv_stats": self.iv_stats,
                "errors": []
            }
    
    def save_checkpoint(self, checkpoint: Dict, date: datetime):
        """Save checkpoint to file"""
        checkpoint['iv_stats'] = self.iv_stats
        checkpoint_file = self.get_checkpoint_filename(date)
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2, default=str)
    
    def get_spy_open_price(self, date: datetime) -> Optional[float]:
        """Get non-adjusted SPY opening price for the given date"""
        try:
            spy = yf.Ticker('SPY')
            # Get non-adjusted prices by setting auto_adjust=False
            data = spy.history(start=date.strftime('%Y-%m-%d'), 
                              end=(date + timedelta(days=1)).strftime('%Y-%m-%d'),
                              auto_adjust=False)
            
            if not data.empty:
                open_price = float(data['Open'].iloc[0])
                print(f"   SPY non-adjusted open: ${open_price:.2f}")
                return open_price
        except Exception as e:
            print(f"Error getting SPY price: {e}")
        return None
    
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
        """Save a batch of contracts to database - V2 with NULL IV preservation"""
        total_stats = {'contracts': 0, 'ohlc': 0, 'greeks': 0, 'iv': 0, 'iv_nulls': 0}
        
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
            
            # Save IV - V2: Store NULL for zero values
            iv_batch = []
            iv_null_count = 0
            
            for iv in data['iv']:
                ts = self.parse_timestamp(iv[0], exp_int)
                
                # IV is in different fields for calls vs puts
                if right == 'C':
                    raw_iv = float(iv[4]) if iv[4] is not None else 0.0
                else:  # Put
                    raw_iv = float(iv[2]) if iv[2] is not None else 0.0
                
                # Track statistics
                self.iv_stats['total_points'] += 1
                
                # Store NULL for zero or invalid IV values
                if raw_iv > 0:
                    implied_vol = raw_iv
                    self.iv_stats['valid_ivs'] += 1
                else:
                    implied_vol = None  # Store as NULL
                    self.iv_stats['zero_ivs'] += 1
                    self.iv_stats['null_stored'] += 1
                    iv_null_count += 1
                
                iv_batch.append((contract_id, ts, implied_vol))
            
            if iv_batch:
                execute_batch(cursor, """
                    INSERT INTO theta.options_iv
                    (contract_id, datetime, implied_volatility)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, iv_batch)
                total_stats['iv'] += len(iv_batch)
                total_stats['iv_nulls'] += iv_null_count
        
        return total_stats
    
    def download_strikes(self, trade_date: datetime, strikes: List[int], 
                        checkpoint: Dict, conn, cursor) -> Dict:
        """Download data for a list of strikes with volume filtering"""
        exp_str = trade_date.strftime('%Y%m%d')
        
        # Get current progress
        progress = checkpoint['dynamic_strikes']
        
        # Resume from last strike if interrupted
        start_from = 0
        if progress['last_strike']:
            try:
                start_from = strikes.index(progress['last_strike']) + 1
                print(f"  Resuming from strike index {start_from}")
            except ValueError:
                start_from = 0
        
        # Process in batches
        batch_data = []
        stats = {'contracts': 0, 'ohlc': 0, 'greeks': 0, 'iv': 0, 'iv_nulls': 0}
        volume_filtered = 0
        
        for i in range(start_from, len(strikes)):
            strike = strikes[i]
            
            for right in ['C', 'P']:
                # Download data first
                data = self.download_contract_data(exp_str, strike, right)
                
                # Volume-based filtering: only keep contracts with sufficient trading data
                if data['ohlc'] and len(data['ohlc']) >= self.min_volume_bars:
                    batch_data.append((trade_date, strike, right, data))
                elif data['ohlc']:
                    volume_filtered += 1
                    print(f"      Skipped ${strike}{right}: {len(data['ohlc'])} bars < {self.min_volume_bars}")
                else:
                    volume_filtered += 1
                    print(f"      Skipped ${strike}{right}: No OHLC data")
                
                # Save batch
                if len(batch_data) >= self.batch_size:
                    batch_stats = self.save_contract_batch(cursor, batch_data)
                    conn.commit()
                    
                    # Update stats
                    for key in stats:
                        stats[key] += batch_stats[key]
                    
                    # Update checkpoint
                    progress['contracts'] += batch_stats['contracts']
                    progress['last_strike'] = strike
                    progress['volume_filtered'] = volume_filtered
                    checkpoint['stats']['total_contracts'] += batch_stats['contracts']
                    checkpoint['stats']['total_ohlc_bars'] += batch_stats['ohlc']
                    checkpoint['stats']['total_greeks_bars'] += batch_stats['greeks']
                    checkpoint['stats']['total_iv_bars'] += batch_stats['iv']
                    checkpoint['stats']['total_iv_nulls'] += batch_stats['iv_nulls']
                    checkpoint['stats']['volume_filtered_count'] = volume_filtered
                    
                    self.save_checkpoint(checkpoint, trade_date)
                    
                    print(f"    ${strike} - {progress['contracts']} contracts kept, {volume_filtered} filtered")
                    
                    batch_data = []
        
        # Save final batch
        if batch_data:
            batch_stats = self.save_contract_batch(cursor, batch_data)
            conn.commit()
            
            for key in stats:
                stats[key] += batch_stats[key]
            
            progress['contracts'] += batch_stats['contracts']
            checkpoint['stats']['total_contracts'] += batch_stats['contracts']
            checkpoint['stats']['total_ohlc_bars'] += batch_stats['ohlc']
            checkpoint['stats']['total_greeks_bars'] += batch_stats['greeks']
            checkpoint['stats']['total_iv_bars'] += batch_stats['iv']
            checkpoint['stats']['total_iv_nulls'] += batch_stats['iv_nulls']
            checkpoint['stats']['volume_filtered_count'] = volume_filtered
        
        # Mark as complete and add filtering stats
        progress['status'] = 'complete'
        stats['volume_filtered'] = volume_filtered
        self.save_checkpoint(checkpoint, trade_date)
        
        # Report volume filtering effectiveness
        total_tested = stats['contracts'] + volume_filtered
        if total_tested > 0:
            kept_percentage = (stats['contracts'] / total_tested) * 100
            print(f"    Volume filtering: {stats['contracts']}/{total_tested} contracts kept ({kept_percentage:.1f}%)")
            print(f"    Filtered {volume_filtered} contracts with <{self.min_volume_bars} bars")
        
        # Report IV statistics
        print(f"    IV Statistics:")
        print(f"      Total IV points: {self.iv_stats['total_points']}")
        print(f"      Valid IVs: {self.iv_stats['valid_ivs']} ({self.iv_stats['valid_ivs']/self.iv_stats['total_points']*100:.1f}%)")
        print(f"      NULLs stored: {self.iv_stats['null_stored']}")
        
        return stats
    
    def download_day(self, trade_date: datetime) -> Dict:
        """Download complete data for a single day using dynamic selection"""
        date_str = trade_date.strftime('%Y-%m-%d')
        exp_str = trade_date.strftime('%Y%m%d')
        
        print(f"\n{'='*80}")
        print(f"Processing {date_str} ({trade_date.strftime('%A')}) - V2 with NULL IV preservation")
        print(f"{'='*80}")
        
        # Load checkpoint
        checkpoint = self.load_checkpoint(trade_date)
        
        # Check if already complete
        if checkpoint['status'] == 'complete':
            print(f"✓ Already complete: {checkpoint['stats']['total_contracts']} contracts")
            print(f"  IV NULLs preserved: {checkpoint['stats']['total_iv_nulls']}")
            return checkpoint
        
        # Get SPY open
        if checkpoint['stats']['spy_open'] is None:
            spy_open = self.get_spy_open_price(trade_date)
            if not spy_open:
                print("✗ Could not get SPY opening price")
                checkpoint['status'] = 'failed'
                checkpoint['errors'].append("No SPY price available")
                self.save_checkpoint(checkpoint, trade_date)
                return checkpoint
            
            checkpoint['stats']['spy_open'] = spy_open
            self.save_checkpoint(checkpoint, trade_date)
        else:
            spy_open = checkpoint['stats']['spy_open']
        
        print(f"SPY Open: ${spy_open:.2f}")
        
        # Use dynamic selection
        if self.use_dynamic_selection:
            print("\n🎯 Using Dynamic Strike Selection based on Volatility...")
            
            # Get strike recommendation from dynamic selector
            strike_result = self.dynamic_selector.get_strike_range(spy_open, trade_date)
            
            if not strike_result['all_strikes']:
                print("✗ Dynamic selector found no strikes")
                checkpoint['status'] = 'failed'
                checkpoint['errors'].append("No strikes found by dynamic selector")
                self.save_checkpoint(checkpoint, trade_date)
                return checkpoint
            
            # Update checkpoint with dynamic selection info
            checkpoint['stats']['atm_strike'] = strike_result['atm_strike']
            checkpoint['stats']['atm_iv'] = strike_result['iv']
            checkpoint['stats']['strikes_per_side'] = strike_result['strikes_per_side']
            checkpoint['dynamic_strikes']['strikes'] = strike_result['all_strikes']
            
            print(f"\n✓ Dynamic Selection Results:")
            print(f"  ATM: ${strike_result['atm_strike']}")
            if strike_result['iv']:
                print(f"  ATM IV: {strike_result['iv']:.1%}")
            print(f"  Method: {strike_result['method']}")
            print(f"  Strikes per side: {strike_result['strikes_per_side']}")
            print(f"  Strike range: ${strike_result['min_strike']} - ${strike_result['max_strike']}")
            print(f"  Total strikes: {strike_result['total_strikes']}")
            
            strikes_to_download = strike_result['all_strikes']
        else:
            # Use smart selection as fallback
            print("\n🧠 Using Smart Strike Selection...")
            recommendation = self.smart_selector.get_strike_recommendation(trade_date, spy_open)
            strikes_to_download = recommendation['recommended_strikes']
            checkpoint['stats']['atm_strike'] = recommendation['atm_strike']
            checkpoint['stats']['atm_iv'] = recommendation['iv_data']['avg_iv'] if recommendation['iv_data'] else None
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            checkpoint['status'] = 'in_progress'
            
            # Download strikes
            print(f"\n📍 Downloading {len(strikes_to_download)} strikes with volume filtering...")
            download_stats = self.download_strikes(
                trade_date, strikes_to_download, checkpoint, conn, cursor
            )
            
            print(f"  ✓ Download complete:")
            print(f"     Contracts kept: {download_stats['contracts']}")
            print(f"     Contracts filtered: {download_stats['volume_filtered']}")
            print(f"     OHLC bars: {download_stats['ohlc']}")
            print(f"     IV NULL values: {download_stats['iv_nulls']}")
            
            # Calculate coverage
            expected_bars = 78  # 6.5 hours * 12 bars/hour
            expected_total = expected_bars * checkpoint['stats']['total_contracts']
            coverage = (checkpoint['stats']['total_ohlc_bars'] / expected_total * 100) if expected_total > 0 else 0
            
            # Mark complete
            checkpoint['status'] = 'complete'
            checkpoint['stats']['coverage'] = coverage
            self.save_checkpoint(checkpoint, trade_date)
            
            print(f"\n✓ Day Complete!")
            print(f"  Total contracts: {checkpoint['stats']['total_contracts']}")
            print(f"  Total OHLC bars: {checkpoint['stats']['total_ohlc_bars']} ({coverage:.1f}% coverage)")
            print(f"  Total Greeks bars: {checkpoint['stats']['total_greeks_bars']}")
            print(f"  Total IV bars: {checkpoint['stats']['total_iv_bars']}")
            print(f"  Total IV NULLs: {checkpoint['stats']['total_iv_nulls']}")
            print(f"  Volume filtered: {checkpoint['stats']['volume_filtered_count']} contracts")
            
            return checkpoint
            
        except Exception as e:
            conn.rollback()
            print(f"\n✗ Error: {str(e)}")
            
            checkpoint['errors'].append(str(e)[:200])
            self.save_checkpoint(checkpoint, trade_date)
            
            return checkpoint
            
        finally:
            cursor.close()
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Download 0DTE data with dynamic volatility-based strike selection - V2')
    parser.add_argument('--date', type=str, required=True,
                       help='Date to download (YYYY-MM-DD)')
    parser.add_argument('--checkpoint', type=str,
                       help='Custom checkpoint file path')
    parser.add_argument('--use-smart', action='store_true',
                       help='Use smart selection instead of dynamic')
    
    args = parser.parse_args()
    
    # Parse date
    try:
        trade_date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"Invalid date format: {args.date}")
        return 1
    
    # Create downloader
    downloader = DynamicStrikeDownloaderV2(
        checkpoint_file=args.checkpoint,
        use_dynamic_selection=not args.use_smart
    )
    
    # Download the day
    result = downloader.download_day(trade_date)
    
    if result.get('status') == 'complete':
        print("\n✓ Day download successful!")
        return 0
    else:
        print(f"\n✗ Day download failed: {result.get('errors', ['Unknown error'])}")
        return 1

if __name__ == "__main__":
    sys.exit(main())