#!/usr/bin/env python3
"""
Enhanced December 2022 0DTE SPY Options Downloader
- 5-minute bars for OHLC, Greeks, and IV
- Strike selection by count (± N strikes from ATM)
- TimescaleDB optimization support
- Comprehensive validation and coverage reporting
"""
import sys
import requests
import psycopg2
import yfinance as yf
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from psycopg2.extras import execute_batch
import json

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

class December2022Enhanced0DTEDownloader:
    def __init__(self, strike_count: int = 40):
        """
        Initialize downloader with configurable strike count
        
        Args:
            strike_count: Number of strikes above/below ATM (default 40 for ±40 strikes)
        """
        self.base_url = "http://127.0.0.1:25510/v2/hist/option"
        self.delay = 0.3  # 300ms between requests
        self.interval = 300000  # 5 minutes in milliseconds
        self.strike_count = strike_count  # Number of strikes above/below ATM
        
        self.report = {
            'successful_days': [],
            'failed_days': [],
            'total_contracts': 0,
            'total_ohlc_bars': 0,
            'total_greeks_bars': 0,
            'total_iv_bars': 0,
            'coverage_stats': {},
            'by_day': {}
        }
        
    def verify_clean_database(self) -> bool:
        """Verify database is clean before starting download"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Check if any December 2022 data exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM theta.options_contracts 
                WHERE symbol = 'SPY' 
                AND expiration >= '2022-12-01' 
                AND expiration <= '2022-12-31'
            """)
            
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"⚠️  WARNING: Found {count} existing December 2022 contracts in database")
                print("   Run cleanup script first or use --force flag to continue")
                return False
            
            print("✅ Database is clean - no December 2022 data found")
            return True
            
        finally:
            cursor.close()
            conn.close()
    
    def setup_timescaledb(self):
        """Setup TimescaleDB hypertables if available"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Check if TimescaleDB is available
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
            if cursor.fetchone():
                print("🔧 Setting up TimescaleDB hypertables...")
                
                # Convert tables to hypertables if not already done
                for table, time_col in [
                    ('options_ohlc', 'datetime'),
                    ('options_greeks', 'datetime'),
                    ('options_iv', 'datetime')
                ]:
                    try:
                        cursor.execute(f"""
                            SELECT create_hypertable('theta.{table}', '{time_col}', 
                                                    if_not_exists => TRUE)
                        """)
                        print(f"   ✓ {table} configured as hypertable")
                    except Exception as e:
                        print(f"   - {table}: {str(e)[:50]}")
                
                conn.commit()
                print("✅ TimescaleDB setup complete")
            else:
                print("ℹ️  TimescaleDB not installed - using standard PostgreSQL")
                
        except Exception as e:
            print(f"TimescaleDB setup error: {e}")
        finally:
            cursor.close()
            conn.close()
    
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
    
    def get_available_strikes_for_day(self, exp_str: str) -> List[int]:
        """Get all available strikes for a given expiration date"""
        strikes = []
        
        # Test a wide range to find all available strikes
        for strike in range(300, 500):  # SPY typically trades 300-500 in this period
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
            
            time.sleep(0.02)  # Small delay to avoid overwhelming API
        
        return sorted(strikes)
    
    def select_strikes_by_count(self, spy_open: float, available_strikes: List[int]) -> List[int]:
        """
        Select strikes based on count from ATM
        
        Args:
            spy_open: SPY opening price
            available_strikes: List of all available strikes
            
        Returns:
            List of selected strikes (± strike_count from ATM)
        """
        # Find closest strike to opening price (ATM)
        atm_strike = min(available_strikes, key=lambda x: abs(x - spy_open))
        atm_index = available_strikes.index(atm_strike)
        
        # Select ± strike_count strikes from ATM
        start_idx = max(0, atm_index - self.strike_count)
        end_idx = min(len(available_strikes), atm_index + self.strike_count + 1)
        
        selected = available_strikes[start_idx:end_idx]
        
        print(f"   ATM strike: ${atm_strike} (SPY open: ${spy_open:.2f})")
        print(f"   Selected {len(selected)} strikes: ${min(selected)} to ${max(selected)}")
        print(f"   Strike range: {selected[0] - atm_strike} to +{selected[-1] - atm_strike} from ATM")
        
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
        """Download all data types for a contract"""
        data = {
            'ohlc': [],
            'greeks': [],
            'iv': []
        }
        
        # Download OHLC
        url = f"{self.base_url}/ohlc"
        params = {
            'root': 'SPY',
            'exp': exp_str,
            'strike': strike * 1000,
            'right': right,
            'start_date': exp_str,
            'end_date': exp_str,
            'ivl': self.interval  # 5 minutes
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data['ohlc'] = r.json().get('response', [])
        except Exception as e:
            print(f"OHLC error for ${strike}{right}: {str(e)[:50]}")
        
        time.sleep(self.delay)
        
        # Download Greeks
        url = f"{self.base_url}/greeks"
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data['greeks'] = r.json().get('response', [])
        except Exception as e:
            print(f"Greeks error for ${strike}{right}: {str(e)[:50]}")
        
        time.sleep(self.delay)
        
        # Download IV
        url = f"{self.base_url}/implied_volatility"
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data['iv'] = r.json().get('response', [])
        except Exception as e:
            print(f"IV error for ${strike}{right}: {str(e)[:50]}")
        
        time.sleep(self.delay)
        
        return data
    
    def save_contract_data(self, cursor, trade_date: datetime, strike: int, right: str,
                          data: Dict) -> Dict:
        """Save all data for a contract with proper error handling"""
        stats = {'ohlc': 0, 'greeks': 0, 'iv': 0}
        
        # Insert/get contract
        cursor.execute("""
            INSERT INTO theta.options_contracts 
            (symbol, expiration, strike, option_type)
            VALUES ('SPY', %s, %s, %s)
            ON CONFLICT (symbol, expiration, strike, option_type)
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
        
        exp_int = int(trade_date.strftime('%Y%m%d'))
        
        # Save OHLC data
        ohlc_batch = []
        for bar in data['ohlc']:
            ts = self.parse_timestamp(bar[0], exp_int)
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
            stats['ohlc'] = len(ohlc_batch)
        
        # Save Greeks data
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
            stats['greeks'] = len(greeks_batch)
        
        # Save IV data
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
            stats['iv'] = len(iv_batch)
        
        return stats
    
    def calculate_coverage_stats(self, day_stats: Dict) -> Dict:
        """Calculate data coverage statistics"""
        coverage = {}
        
        if day_stats['ohlc_bars'] > 0:
            # Expected bars: 6.5 hours * 12 bars/hour = 78 bars per contract
            expected_bars_per_contract = 78
            expected_total_bars = expected_bars_per_contract * day_stats['contracts']
            
            coverage['ohlc_coverage'] = (day_stats['ohlc_bars'] / expected_total_bars) * 100
            coverage['greeks_coverage'] = (day_stats['greeks_bars'] / day_stats['ohlc_bars']) * 100
            coverage['iv_coverage'] = (day_stats['iv_bars'] / day_stats['ohlc_bars']) * 100
            coverage['avg_bars_per_contract'] = day_stats['ohlc_bars'] / day_stats['contracts']
        else:
            coverage = {
                'ohlc_coverage': 0,
                'greeks_coverage': 0,
                'iv_coverage': 0,
                'avg_bars_per_contract': 0
            }
        
        return coverage
    
    def download_day(self, trade_date: datetime) -> Dict:
        """Download 0DTE options with complete data for a single day"""
        date_str = trade_date.strftime('%Y-%m-%d')
        exp_str = trade_date.strftime('%Y%m%d')
        
        print(f"\n{'='*100}")
        print(f"Processing {date_str} ({trade_date.strftime('%A')})")
        
        # Get SPY opening price
        spy_open = self.get_spy_open_price(trade_date)
        if not spy_open:
            reason = "Could not get SPY opening price"
            print(f"❌ {reason}")
            return {'success': False, 'reason': reason}
        
        print(f"SPY Open: ${spy_open:.2f}")
        
        # Get all available strikes for the day
        print("Scanning for available strikes...")
        all_strikes = self.get_available_strikes_for_day(exp_str)
        
        if not all_strikes:
            reason = "No strikes available for this expiration"
            print(f"❌ {reason}")
            return {'success': False, 'reason': reason}
        
        print(f"Found {len(all_strikes)} total available strikes: ${min(all_strikes)} to ${max(all_strikes)}")
        
        # Select strikes based on count from ATM
        selected_strikes = self.select_strikes_by_count(spy_open, all_strikes)
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        contracts_saved = 0
        total_stats = {'ohlc': 0, 'greeks': 0, 'iv': 0}
        
        try:
            for i, strike in enumerate(selected_strikes):
                for right in ['C', 'P']:
                    # Download all data types
                    data = self.download_contract_data(exp_str, strike, right)
                    
                    # Save if we have data
                    if data['ohlc']:
                        stats = self.save_contract_data(
                            cursor, trade_date, strike, right, data
                        )
                        
                        total_stats['ohlc'] += stats['ohlc']
                        total_stats['greeks'] += stats['greeks']
                        total_stats['iv'] += stats['iv']
                        
                        if stats['ohlc'] > 0:
                            contracts_saved += 1
                    
                    if contracts_saved % 20 == 0 and contracts_saved > 0:
                        print(f"  Progress: {contracts_saved} contracts, "
                              f"{total_stats['ohlc']} OHLC, "
                              f"{total_stats['greeks']} Greeks, "
                              f"{total_stats['iv']} IV bars")
                        conn.commit()
            
            conn.commit()
            
            # Calculate coverage statistics
            day_result = {
                'success': True,
                'contracts': contracts_saved,
                'ohlc_bars': total_stats['ohlc'],
                'greeks_bars': total_stats['greeks'],
                'iv_bars': total_stats['iv'],
                'strikes': len(selected_strikes),
                'strike_range': f"${min(selected_strikes)}-${max(selected_strikes)}",
                'spy_open': spy_open,
                'atm_strike': min(selected_strikes, key=lambda x: abs(x - spy_open))
            }
            
            coverage = self.calculate_coverage_stats(day_result)
            day_result.update(coverage)
            
            print(f"\n✅ Success: {contracts_saved} contracts")
            print(f"   OHLC bars: {total_stats['ohlc']} ({coverage['ohlc_coverage']:.1f}% coverage)")
            print(f"   Greeks bars: {total_stats['greeks']} ({coverage['greeks_coverage']:.1f}% of OHLC)")
            print(f"   IV bars: {total_stats['iv']} ({coverage['iv_coverage']:.1f}% of OHLC)")
            print(f"   Avg bars/contract: {coverage['avg_bars_per_contract']:.1f}")
            
            return day_result
            
        except Exception as e:
            conn.rollback()
            reason = f"Error: {str(e)[:100]}"
            print(f"❌ {reason}")
            return {'success': False, 'reason': reason}
            
        finally:
            cursor.close()
            conn.close()
    
    def download_december_2022(self):
        """Download all of December 2022 with complete data"""
        print("DECEMBER 2022 SPY 0DTE OPTIONS - ENHANCED DATA DOWNLOAD")
        print(f"Downloading OHLC + Greeks + IV with 5-minute intervals")
        print(f"Using ±{self.strike_count} strikes from ATM selection")
        print("="*100)
        
        # Verify clean database
        if not self.verify_clean_database():
            print("\n❌ Aborting download - database not clean")
            return
        
        # Setup TimescaleDB if available
        self.setup_timescaledb()
        
        # All potential trading days in December 2022
        start_date = datetime(2022, 12, 1)
        end_date = datetime(2022, 12, 31)
        
        # Market holidays in December 2022
        holidays = [
            datetime(2022, 12, 26)  # Christmas observed
        ]
        
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Weekday
                if current in holidays:
                    self.report['failed_days'].append({
                        'date': current.strftime('%Y-%m-%d'),
                        'day': current.strftime('%A'),
                        'reason': 'Market holiday'
                    })
                else:
                    # Download this day
                    result = self.download_day(current)
                    
                    if result['success']:
                        self.report['successful_days'].append({
                            'date': current.strftime('%Y-%m-%d'),
                            'day': current.strftime('%A'),
                            **result
                        })
                        self.report['total_contracts'] += result['contracts']
                        self.report['total_ohlc_bars'] += result['ohlc_bars']
                        self.report['total_greeks_bars'] += result['greeks_bars']
                        self.report['total_iv_bars'] += result['iv_bars']
                    else:
                        self.report['failed_days'].append({
                            'date': current.strftime('%Y-%m-%d'),
                            'day': current.strftime('%A'),
                            'reason': result['reason']
                        })
            
            current += timedelta(days=1)
        
        self.print_comprehensive_report()
    
    def print_comprehensive_report(self):
        """Print comprehensive download report with coverage analysis"""
        print("\n" + "="*100)
        print("DECEMBER 2022 SPY 0DTE ENHANCED DOWNLOAD REPORT")
        print("="*100)
        
        print(f"\n✅ SUCCESSFUL DAYS ({len(self.report['successful_days'])} days):")
        print("-" * 100)
        
        for day in self.report['successful_days']:
            print(f"✅ {day['date']} ({day['day'][0:3]}): "
                  f"{day['strikes']} strikes {day['strike_range']}, "
                  f"{day['contracts']} contracts")
            print(f"   Data: {day['ohlc_bars']} OHLC | "
                  f"{day['greeks_bars']} Greeks | "
                  f"{day['iv_bars']} IV bars")
            print(f"   Coverage: OHLC {day.get('ohlc_coverage', 0):.1f}% | "
                  f"Greeks {day.get('greeks_coverage', 0):.1f}% | "
                  f"IV {day.get('iv_coverage', 0):.1f}%")
            print(f"   SPY open: ${day['spy_open']:.2f}, ATM: ${day.get('atm_strike', 0)}")
        
        if self.report['failed_days']:
            print(f"\n❌ FAILED/MISSING DAYS ({len(self.report['failed_days'])} days):")
            print("-" * 100)
            
            for day in self.report['failed_days']:
                print(f"❌ {day['date']} ({day['day'][0:3]}): {day['reason']}")
        
        print("\n" + "="*100)
        print("SUMMARY:")
        print("-" * 100)
        print(f"Trading days in December:     22")
        print(f"Days with successful data:    {len(self.report['successful_days'])}")
        print(f"Days failed/missing:          {len(self.report['failed_days'])}")
        print(f"Total contracts downloaded:   {self.report['total_contracts']:,}")
        print(f"Total OHLC bars:             {self.report['total_ohlc_bars']:,}")
        print(f"Total Greeks bars:           {self.report['total_greeks_bars']:,}")
        print(f"Total IV bars:               {self.report['total_iv_bars']:,}")
        
        if self.report['successful_days']:
            # Calculate overall coverage
            avg_ohlc_coverage = sum(d.get('ohlc_coverage', 0) for d in self.report['successful_days']) / len(self.report['successful_days'])
            avg_greeks_coverage = sum(d.get('greeks_coverage', 0) for d in self.report['successful_days']) / len(self.report['successful_days'])
            avg_iv_coverage = sum(d.get('iv_coverage', 0) for d in self.report['successful_days']) / len(self.report['successful_days'])
            
            print(f"\nAverage Coverage:")
            print(f"OHLC coverage:               {avg_ohlc_coverage:.1f}%")
            print(f"Greeks coverage:             {avg_greeks_coverage:.1f}%")
            print(f"IV coverage:                 {avg_iv_coverage:.1f}%")
        
        # Save detailed report to file
        report_file = f"/home/info/fntx-ai-v1/08_logs/december_2022_download_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.report, f, indent=2, default=str)
        print(f"\n📄 Detailed report saved to: {report_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced December 2022 0DTE SPY Options Downloader')
    parser.add_argument('--strikes', type=int, default=40, 
                       help='Number of strikes above/below ATM (default: 40)')
    parser.add_argument('--force', action='store_true',
                       help='Force download even if data exists')
    
    args = parser.parse_args()
    
    downloader = December2022Enhanced0DTEDownloader(strike_count=args.strikes)
    downloader.download_december_2022()

if __name__ == "__main__":
    main()