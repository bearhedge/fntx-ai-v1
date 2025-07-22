#!/usr/bin/env python3
"""
Complete 0DTE Options Downloader with OHLC, Greeks, and IV
Downloads 5-minute interval data for same-day expiration options
"""
import sys
import requests
import psycopg2
import yfinance as yf
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from psycopg2.extras import execute_batch

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

class Complete0DTEDownloader:
    def __init__(self):
        self.base_url = "http://127.0.0.1:25510/v2/hist/option"
        self.delay = 0.3  # 300ms between requests
        self.interval = 300000  # 5 minutes in milliseconds
        self.report = {
            'successful_days': [],
            'failed_days': [],
            'total_contracts': 0,
            'total_ohlc_bars': 0,
            'total_greeks_bars': 0,
            'total_iv_bars': 0,
            'by_day': {}
        }
        
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
    
    def parse_timestamp(self, ms_of_day: int, date_int: int) -> datetime:
        """Parse timestamp from ms_of_day and date integer"""
        hours = ms_of_day // (1000 * 60 * 60)
        minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
        seconds = (ms_of_day % (1000 * 60)) // 1000
        
        year = date_int // 10000
        month = (date_int % 10000) // 100
        day = date_int % 100
        
        return datetime(year, month, day, hours, minutes, seconds)
    
    def download_ohlc(self, exp_str: str, strike: int, right: str) -> List:
        """Download OHLC data for a contract"""
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
                data = r.json()
                return data.get('response', [])
        except Exception as e:
            print(f"OHLC error for ${strike}{right}: {str(e)[:50]}")
        return []
    
    def download_greeks(self, exp_str: str, strike: int, right: str) -> List:
        """Download Greeks data for a contract"""
        url = f"{self.base_url}/greeks"
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
                data = r.json()
                return data.get('response', [])
        except Exception as e:
            print(f"Greeks error for ${strike}{right}: {str(e)[:50]}")
        return []
    
    def download_iv(self, exp_str: str, strike: int, right: str) -> List:
        """Download IV data for a contract"""
        url = f"{self.base_url}/implied_volatility"
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
                data = r.json()
                return data.get('response', [])
        except Exception as e:
            print(f"IV error for ${strike}{right}: {str(e)[:50]}")
        return []
    
    def save_contract_data(self, cursor, trade_date: datetime, strike: int, right: str,
                          ohlc_data: List, greeks_data: List, iv_data: List) -> Dict:
        """Save all data for a contract"""
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
        for bar in ohlc_data:
            ts = self.parse_timestamp(bar[0], exp_int)
            cursor.execute("""
                INSERT INTO theta.options_ohlc
                (contract_id, datetime, open, high, low, close, volume, trade_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (contract_id, datetime) DO NOTHING
            """, (
                contract_id, ts,
                float(bar[1]), float(bar[2]),
                float(bar[3]), float(bar[4]),
                int(bar[5]), int(bar[6])
            ))
            if cursor.rowcount > 0:
                stats['ohlc'] += 1
        
        # Save Greeks data
        # Format: [ms_of_day, bid?, ask?, delta, gamma, theta, vega, rho, phi?, iv?, ?, ms_of_day, underlying, date]
        for greek in greeks_data:
            ts = self.parse_timestamp(greek[0], exp_int)
            
            # Extract Greeks values (positions based on analysis)
            delta = float(greek[3]) if greek[3] is not None else None
            gamma = float(greek[4]) if greek[4] is not None else None
            theta = float(greek[5]) if greek[5] is not None else None
            vega = float(greek[6]) if greek[6] is not None else None
            rho = float(greek[7]) if greek[7] is not None else None
            
            cursor.execute("""
                INSERT INTO theta.options_greeks
                (contract_id, datetime, delta, gamma, theta, vega, rho)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (contract_id, datetime) DO NOTHING
            """, (contract_id, ts, delta, gamma, theta, vega, rho))
            if cursor.rowcount > 0:
                stats['greeks'] += 1
        
        # Save IV data
        # Format: [ms_of_day, bid_price, iv_field2_puts, bid_price2, iv_field4_calls, ..., ms_of_day, underlying, date]
        for iv in iv_data:
            ts = self.parse_timestamp(iv[0], exp_int)
            
            # IV is in different fields for calls vs puts
            # Calls: field [4], Puts: field [2]
            if right == 'C':
                implied_vol = float(iv[4]) if iv[4] is not None and iv[4] > 0 else None
            else:  # Put
                implied_vol = float(iv[2]) if iv[2] is not None and iv[2] > 0 else None
            
            if implied_vol:
                cursor.execute("""
                    INSERT INTO theta.options_iv
                    (contract_id, datetime, implied_volatility)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, (contract_id, ts, implied_vol))
                if cursor.rowcount > 0:
                    stats['iv'] += 1
        
        return stats
    
    def download_day(self, trade_date: datetime) -> Dict:
        """Download 0DTE options with complete data for a single day"""
        date_str = trade_date.strftime('%Y-%m-%d')
        exp_str = trade_date.strftime('%Y%m%d')
        
        print(f"\n{'='*80}")
        print(f"Processing {date_str} ({trade_date.strftime('%A')})")
        
        # Get SPY opening price
        spy_open = self.get_spy_open_price(trade_date)
        if not spy_open:
            reason = "Could not get SPY opening price"
            print(f"❌ {reason}")
            return {'success': False, 'reason': reason}
        
        print(f"SPY Open: ${spy_open:.2f}")
        
        # Calculate strike range (open ± $20)
        min_strike = int(spy_open - 20)
        max_strike = int(spy_open + 20)
        print(f"Strike range: ${min_strike} to ${max_strike}")
        
        # Test strikes to find available ones
        available_strikes = []
        test_strikes = list(range(min_strike, max_strike + 1))
        
        print("Finding available strikes...", end='', flush=True)
        for strike in test_strikes:
            params = {
                'root': 'SPY',
                'exp': exp_str,
                'strike': strike * 1000,
                'right': 'C',
                'start_date': exp_str,
                'end_date': exp_str,
                'ivl': 3600000
            }
            
            try:
                r = requests.get(f"{self.base_url}/ohlc", params=params, timeout=3)
                if r.status_code == 200 and r.json().get('response'):
                    available_strikes.append(strike)
            except:
                pass
            
            time.sleep(0.05)
        
        print(f" Found {len(available_strikes)} strikes")
        
        if not available_strikes:
            reason = "No strikes with data in ATM ±20 range"
            print(f"❌ {reason}")
            return {'success': False, 'reason': reason}
        
        print(f"Available strikes: ${min(available_strikes)} to ${max(available_strikes)}")
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        contracts_saved = 0
        total_stats = {'ohlc': 0, 'greeks': 0, 'iv': 0}
        
        try:
            for i, strike in enumerate(available_strikes):
                for right in ['C', 'P']:
                    # Download all data types
                    ohlc_data = self.download_ohlc(exp_str, strike, right)
                    time.sleep(self.delay)
                    
                    greeks_data = self.download_greeks(exp_str, strike, right)
                    time.sleep(self.delay)
                    
                    iv_data = self.download_iv(exp_str, strike, right)
                    time.sleep(self.delay)
                    
                    # Save if we have data
                    if ohlc_data:
                        stats = self.save_contract_data(
                            cursor, trade_date, strike, right,
                            ohlc_data, greeks_data, iv_data
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
            
            print(f"\n✅ Success: {contracts_saved} contracts")
            print(f"   OHLC bars: {total_stats['ohlc']}")
            print(f"   Greeks bars: {total_stats['greeks']}")
            print(f"   IV bars: {total_stats['iv']}")
            
            return {
                'success': True,
                'contracts': contracts_saved,
                'ohlc_bars': total_stats['ohlc'],
                'greeks_bars': total_stats['greeks'],
                'iv_bars': total_stats['iv'],
                'strikes': len(available_strikes),
                'strike_range': f"${min(available_strikes)}-${max(available_strikes)}",
                'spy_open': spy_open
            }
            
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
        print("DECEMBER 2022 SPY 0DTE OPTIONS - COMPLETE DATA DOWNLOAD")
        print("Downloading OHLC + Greeks + IV with 5-minute intervals")
        print("Using daily opening price ± $20 for strike selection")
        
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
                            'contracts': result['contracts'],
                            'ohlc_bars': result['ohlc_bars'],
                            'greeks_bars': result['greeks_bars'],
                            'iv_bars': result['iv_bars'],
                            'strikes': result['strikes'],
                            'strike_range': result['strike_range'],
                            'spy_open': result['spy_open']
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
        
        self.print_report()
    
    def print_report(self):
        """Print comprehensive download report"""
        print("\n" + "="*100)
        print("DECEMBER 2022 SPY 0DTE COMPLETE DATA DOWNLOAD REPORT")
        print("="*100)
        
        print(f"\n✅ SUCCESSFUL DAYS ({len(self.report['successful_days'])} days):")
        print("-" * 100)
        
        for day in self.report['successful_days']:
            print(f"✅ {day['date']} ({day['day'][0:3]}): "
                  f"{day['strikes']} strikes {day['strike_range']}, "
                  f"{day['contracts']} contracts")
            print(f"   Data: {day['ohlc_bars']} OHLC | "
                  f"{day['greeks_bars']} Greeks | "
                  f"{day['iv_bars']} IV bars "
                  f"(SPY open: ${day['spy_open']:.2f})")
        
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
            greeks_coverage = self.report['total_greeks_bars'] / self.report['total_ohlc_bars'] * 100
            iv_coverage = self.report['total_iv_bars'] / self.report['total_ohlc_bars'] * 100
            print(f"\nData coverage:")
            print(f"Greeks coverage:             {greeks_coverage:.1f}%")
            print(f"IV coverage:                 {iv_coverage:.1f}%")

def main():
    downloader = Complete0DTEDownloader()
    downloader.download_december_2022()

if __name__ == "__main__":
    main()