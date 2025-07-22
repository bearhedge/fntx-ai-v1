#!/usr/bin/env python3
"""
Strike-aware daily downloader for 0DTE SPY options
Supports two-tier strike strategy: core (±10) and extended (±11-20)
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
from typing import Dict, List, Tuple, Optional, Set
from psycopg2.extras import execute_batch
import argparse

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG
from smart_strike_selector import SmartStrikeSelector

class StrikeAwareDailyDownloader:
    def __init__(self, checkpoint_file: str = None, use_smart_selection: bool = True):
        self.base_url = "http://127.0.0.1:25510/v2/hist/option"
        self.delay = 0.3  # 300ms between requests
        self.interval = 300000  # 5 minutes in milliseconds
        self.batch_size = 10  # Contracts per database commit
        
        # Strike configuration
        self.core_strikes = 10  # ±10 strikes from ATM (high priority)
        self.extended_strikes = 20  # ±11-20 strikes from ATM (lower priority)
        
        # Smart strike selection
        self.use_smart_selection = use_smart_selection
        if use_smart_selection:
            self.smart_selector = SmartStrikeSelector(self.base_url)
        
        # Set checkpoint file based on date if not provided
        self.checkpoint_file = checkpoint_file
        
    def get_checkpoint_filename(self, date: datetime) -> str:
        """Generate checkpoint filename for a specific date"""
        if self.checkpoint_file:
            return self.checkpoint_file
        return f"checkpoint_{date.strftime('%Y%m%d')}.json"
        
    def load_checkpoint(self, date: datetime) -> Dict:
        """Load checkpoint file or create new one"""
        checkpoint_file = self.get_checkpoint_filename(date)
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "date": date.strftime('%Y-%m-%d'),
                "status": "initialized",
                "core_strikes": {"status": "pending", "contracts": 0, "last_strike": None},
                "extended_strikes": {"status": "pending", "contracts": 0, "last_strike": None},
                "smart_strikes": {"status": "pending", "contracts": 0, "strikes": [], "last_strike": None},
                "stats": {
                    "total_contracts": 0,
                    "total_ohlc_bars": 0,
                    "total_greeks_bars": 0,
                    "total_iv_bars": 0,
                    "spy_open": None,
                    "atm_strike": None,
                    "atm_iv": None,
                    "strike_selection_method": "smart" if self.use_smart_selection else "fixed"
                },
                "errors": []
            }
    
    def save_checkpoint(self, checkpoint: Dict, date: datetime):
        """Save checkpoint to file"""
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
    
    def discover_strikes(self, exp_str: str, spy_open: float) -> List[int]:
        """Discover available strikes around ATM"""
        strikes = []
        
        # Search range: ±$50 from SPY open (should cover extended strikes)
        min_strike = int(spy_open - 50)
        max_strike = int(spy_open + 50)
        
        for strike in range(min_strike, max_strike + 1):
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
    
    def categorize_strikes(self, spy_open: float, available_strikes: List[int]) -> Dict[str, List[int]]:
        """Categorize strikes into core and extended based on distance from ATM"""
        if not available_strikes:
            return {"core": [], "extended": []}
            
        # Find ATM strike
        atm_strike = min(available_strikes, key=lambda x: abs(x - spy_open))
        atm_index = available_strikes.index(atm_strike)
        
        core_strikes = []
        extended_strikes = []
        
        for i, strike in enumerate(available_strikes):
            distance = abs(i - atm_index)
            if distance <= self.core_strikes:
                core_strikes.append(strike)
            elif distance <= self.extended_strikes:
                extended_strikes.append(strike)
        
        return {
            "core": sorted(core_strikes),
            "extended": sorted(extended_strikes),
            "atm": atm_strike
        }
    
    def parse_timestamp(self, ms_of_day: int, date_int: int) -> datetime:
        """Parse timestamp from ms_of_day and date integer"""
        hours = ms_of_day // (1000 * 60 * 60)
        minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
        seconds = (ms_of_day % (1000 * 60)) // 1000
        
        year = date_int // 10000
        month = (date_int % 10000) // 100
        day = date_int % 100
        
        return datetime(year, month, day, hours, minutes, seconds)
    
    def download_contract_data(self, exp_str: str, strike: int, right: str, atm_strike: int = None) -> Dict:
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
    
    def download_strikes(self, trade_date: datetime, strikes: List[int], 
                        strike_type: str, checkpoint: Dict, conn, cursor) -> Dict:
        """Download data for a list of strikes"""
        exp_str = trade_date.strftime('%Y%m%d')
        
        # Get current progress
        progress = checkpoint[f"{strike_type}_strikes"]
        
        # Get ATM strike for OTM filtering
        atm_strike = checkpoint['stats']['atm_strike']
        
        # Resume from last strike if interrupted
        start_from = 0
        if progress['last_strike']:
            try:
                start_from = strikes.index(progress['last_strike']) + 1
                print(f"  Resuming {strike_type} from strike index {start_from}")
            except ValueError:
                start_from = 0
        
        # Process in batches
        batch_data = []
        stats = {'contracts': 0, 'ohlc': 0, 'greeks': 0, 'iv': 0}
        volume_skipped = 0
        min_volume_bars = 60  # Minimum OHLC bars for inclusion (60 * 5min = 5 hours)
        
        for i in range(start_from, len(strikes)):
            strike = strikes[i]
            
            for right in ['C', 'P']:
                # Download data first
                data = self.download_contract_data(exp_str, strike, right, atm_strike)
                
                # Volume-based filtering: only keep contracts with sufficient trading data
                if data['ohlc'] and len(data['ohlc']) >= min_volume_bars:
                    batch_data.append((trade_date, strike, right, data))
                elif data['ohlc']:
                    volume_skipped += 1
                    print(f"      Skipped ${strike}{right}: {len(data['ohlc'])} bars < {min_volume_bars}")
                else:
                    volume_skipped += 1
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
                    checkpoint['stats']['total_contracts'] += batch_stats['contracts']
                    checkpoint['stats']['total_ohlc_bars'] += batch_stats['ohlc']
                    checkpoint['stats']['total_greeks_bars'] += batch_stats['greeks']
                    checkpoint['stats']['total_iv_bars'] += batch_stats['iv']
                    
                    self.save_checkpoint(checkpoint, trade_date)
                    
                    print(f"    {strike_type}: ${strike} - {progress['contracts']} contracts")
                    
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
        
        # Mark as complete and add volume filtering stats
        progress['status'] = 'complete'
        stats['volume_skipped'] = volume_skipped
        self.save_checkpoint(checkpoint, trade_date)
        
        # Report volume filtering effectiveness
        total_tested = stats['contracts'] + volume_skipped
        if total_tested > 0:
            kept_percentage = (stats['contracts'] / total_tested) * 100
            print(f"    Volume filtering: {stats['contracts']}/{total_tested} contracts kept ({kept_percentage:.1f}%)")
            print(f"    Skipped {volume_skipped} contracts with <{min_volume_bars} bars")
        
        return stats
    
    def download_day(self, trade_date: datetime, 
                    core_only: bool = False,
                    extended_only: bool = False) -> Dict:
        """Download complete data for a single day"""
        date_str = trade_date.strftime('%Y-%m-%d')
        exp_str = trade_date.strftime('%Y%m%d')
        
        print(f"\n{'='*80}")
        print(f"Processing {date_str} ({trade_date.strftime('%A')})")
        print(f"{'='*80}")
        
        # Load checkpoint
        checkpoint = self.load_checkpoint(trade_date)
        
        # Check if already complete
        if checkpoint['status'] == 'complete':
            print(f"✓ Already complete: {checkpoint['stats']['total_contracts']} contracts")
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
        
        # Use smart selection or traditional method
        if self.use_smart_selection:
            print("\n🧠 Using Smart Strike Selection...")
            
            # Get strike recommendation from smart selector
            recommendation = self.smart_selector.get_strike_recommendation(trade_date, spy_open)
            
            if not recommendation['recommended_strikes']:
                print("✗ Smart selector found no relevant strikes")
                checkpoint['status'] = 'failed'
                checkpoint['errors'].append("No relevant strikes found by smart selector")
                self.save_checkpoint(checkpoint, trade_date)
                return checkpoint
            
            # Update checkpoint with smart selection info
            checkpoint['stats']['atm_strike'] = recommendation['atm_strike']
            checkpoint['stats']['atm_iv'] = recommendation['iv_data']['avg_iv'] if recommendation['iv_data'] else None
            checkpoint['smart_strikes']['strikes'] = recommendation['recommended_strikes']
            
            print(f"\n✓ Smart Selection Results:")
            print(f"  ATM: ${recommendation['atm_strike']}")
            print(f"  ATM IV: {recommendation['iv_data']['avg_iv']:.1%}" if recommendation['iv_data'] else "  ATM IV: N/A")
            print(f"  Selected strikes: {len(recommendation['recommended_strikes'])}")
            print(f"  Strike range: ${recommendation['min_strike']} - ${recommendation['max_strike']}")
            print(f"  Range as % of spot: {recommendation['range_percentage']:.1f}%")
            
            # For smart selection, we'll use all strikes as "core"
            strikes_dict = {
                'core': recommendation['recommended_strikes'],
                'extended': [],  # No extended strikes in smart mode
                'atm': recommendation['atm_strike']
            }
        else:
            # Traditional fixed strike selection
            print("Discovering available strikes...")
            all_strikes = self.discover_strikes(exp_str, spy_open)
            
            if not all_strikes:
                print("✗ No strikes available")
                checkpoint['status'] = 'failed'
                checkpoint['errors'].append("No strikes found")
                self.save_checkpoint(checkpoint, trade_date)
                return checkpoint
            
            strikes_dict = self.categorize_strikes(spy_open, all_strikes)
            checkpoint['stats']['atm_strike'] = strikes_dict['atm']
            
            print(f"Found {len(all_strikes)} total strikes")
            print(f"  ATM: ${strikes_dict['atm']}")
            print(f"  Core strikes (±{self.core_strikes}): {len(strikes_dict['core'])} strikes")
            print(f"  Extended strikes (±{self.extended_strikes}): {len(strikes_dict['extended'])} strikes")
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            checkpoint['status'] = 'in_progress'
            
            if self.use_smart_selection:
                # Download all smart-selected strikes as one batch
                if checkpoint['smart_strikes']['status'] != 'complete':
                    print(f"\n📍 Downloading {len(strikes_dict['core'])} smart-selected strikes...")
                    smart_stats = self.download_strikes(
                        trade_date, strikes_dict['core'], 'smart', checkpoint, conn, cursor
                    )
                    print(f"  ✓ Smart strikes complete: {smart_stats['contracts']} contracts, "
                          f"{smart_stats['ohlc']} OHLC bars")
            else:
                # Traditional core/extended download
                # Download core strikes (unless extended_only)
                if not extended_only and checkpoint['core_strikes']['status'] != 'complete':
                    print(f"\n📍 Downloading CORE strikes (±{self.core_strikes} from ATM)...")
                    core_stats = self.download_strikes(
                        trade_date, strikes_dict['core'], 'core', checkpoint, conn, cursor
                    )
                    print(f"  ✓ Core complete: {core_stats['contracts']} contracts, "
                          f"{core_stats['ohlc']} OHLC bars")
                
                # Download extended strikes (unless core_only)
                if not core_only and checkpoint['extended_strikes']['status'] != 'complete':
                    print(f"\n📍 Downloading EXTENDED strikes (±11-{self.extended_strikes} from ATM)...")
                    extended_stats = self.download_strikes(
                        trade_date, strikes_dict['extended'], 'extended', checkpoint, conn, cursor
                    )
                    print(f"  ✓ Extended complete: {extended_stats['contracts']} contracts, "
                          f"{extended_stats['ohlc']} OHLC bars")
            
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
    parser = argparse.ArgumentParser(description='Download 0DTE data with strike-aware strategy')
    parser.add_argument('--date', type=str, required=True,
                       help='Date to download (YYYY-MM-DD)')
    parser.add_argument('--core-only', action='store_true',
                       help='Download only core strikes (±10 from ATM)')
    parser.add_argument('--extended-only', action='store_true',
                       help='Download only extended strikes (±11-20 from ATM)')
    parser.add_argument('--checkpoint', type=str,
                       help='Custom checkpoint file path')
    
    args = parser.parse_args()
    
    # Parse date
    try:
        trade_date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"Invalid date format: {args.date}")
        return 1
    
    # Create downloader
    downloader = StrikeAwareDailyDownloader(checkpoint_file=args.checkpoint)
    
    # Download the day
    result = downloader.download_day(
        trade_date,
        core_only=args.core_only,
        extended_only=args.extended_only
    )
    
    if result.get('status') == 'complete':
        print("\n✓ Day download successful!")
        return 0
    else:
        print(f"\n✗ Day download failed: {result.get('errors', ['Unknown error'])}")
        return 1

if __name__ == "__main__":
    sys.exit(main())