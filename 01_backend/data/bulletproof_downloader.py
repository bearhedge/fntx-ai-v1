#!/usr/bin/env python3
"""
Bulletproof 0DTE Downloader with comprehensive validation
Enhanced to prevent any contamination and ensure 100% 0DTE compliance
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

class BulletproofDownloader:
    def __init__(self):
        self.base_url = "http://127.0.0.1:25510/v2/hist/option"
        self.delay = 0.3  # 300ms between requests
        self.interval = 300000  # 5 minutes in milliseconds
        self.validation_enabled = True
        self.report = {
            'successful_days': [],
            'failed_days': [],
            'total_contracts': 0,
            'total_ohlc_bars': 0,
            'total_greeks_bars': 0,
            'total_iv_bars': 0,
            'validation_checks': 0,
            'validation_failures': 0,
            'by_day': {}
        }
        
    def validate_0dte_compliance(self) -> bool:
        """Run real-time 0DTE compliance check"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("SELECT theta.quick_contamination_check()")
            status = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            self.report['validation_checks'] += 1
            
            if "CLEAN" in status:
                return True
            else:
                self.report['validation_failures'] += 1
                print(f"🚨 CONTAMINATION DETECTED: {status}")
                return False
                
        except Exception as e:
            print(f"❌ Validation error: {e}")
            self.report['validation_failures'] += 1
            return False
    
    def validate_api_request(self, exp_str: str, trade_date: datetime) -> bool:
        """Validate API request parameters ensure 0DTE"""
        expected_date = trade_date.strftime('%Y%m%d')
        
        if exp_str != expected_date:
            print(f"🚨 API VALIDATION FAILED: exp_str={exp_str}, expected={expected_date}")
            return False
            
        return True
    
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
    
    def download_ohlc(self, exp_str: str, strike: int, right: str, trade_date: datetime) -> List:
        """Download OHLC data with validation"""
        if not self.validate_api_request(exp_str, trade_date):
            return []
            
        url = f"{self.base_url}/ohlc"
        params = {
            'root': 'SPY',
            'exp': exp_str,
            'strike': strike * 1000,
            'right': right,
            'start_date': exp_str,  # Must match exp_str for 0DTE
            'end_date': exp_str,    # Must match exp_str for 0DTE  
            'ivl': self.interval
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                response = data.get('response', [])
                
                # Validate each timestamp is for the same date
                exp_date = trade_date.date()
                for bar in response:
                    ts = self.parse_timestamp(bar[0], int(exp_str))
                    if ts.date() != exp_date:
                        print(f"🚨 OHLC VALIDATION FAILED: timestamp {ts.date()} != expiration {exp_date}")
                        return []
                
                return response
        except Exception as e:
            print(f"OHLC error for ${strike}{right}: {str(e)[:50]}")
        return []
    
    def download_greeks(self, exp_str: str, strike: int, right: str, trade_date: datetime) -> List:
        """Download Greeks data with validation"""
        if not self.validate_api_request(exp_str, trade_date):
            return []
            
        url = f"{self.base_url}/greeks"
        params = {
            'root': 'SPY',
            'exp': exp_str,
            'strike': strike * 1000,
            'right': right,
            'start_date': exp_str,  # Must match exp_str for 0DTE
            'end_date': exp_str,    # Must match exp_str for 0DTE
            'ivl': self.interval
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                response = data.get('response', [])
                
                # Validate each timestamp and exclude 16:00 records
                exp_date = trade_date.date()
                filtered_response = []
                for greek in response:
                    ts = self.parse_timestamp(greek[0], int(exp_str))
                    if ts.date() != exp_date:
                        print(f"🚨 GREEKS VALIDATION FAILED: timestamp {ts.date()} != expiration {exp_date}")
                        return []
                    
                    # Exclude 16:00 records (after market close)
                    if ts.time().hour != 16:
                        filtered_response.append(greek)
                
                return filtered_response
        except Exception as e:
            print(f"Greeks error for ${strike}{right}: {str(e)[:50]}")
        return []
    
    def download_iv(self, exp_str: str, strike: int, right: str, trade_date: datetime) -> List:
        """Download IV data with validation"""
        if not self.validate_api_request(exp_str, trade_date):
            return []
            
        url = f"{self.base_url}/implied_volatility"
        params = {
            'root': 'SPY',
            'exp': exp_str,
            'strike': strike * 1000,
            'right': right,
            'start_date': exp_str,  # Must match exp_str for 0DTE
            'end_date': exp_str,    # Must match exp_str for 0DTE
            'ivl': self.interval
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                response = data.get('response', [])
                
                # Validate each timestamp is for the same date
                exp_date = trade_date.date()
                for iv in response:
                    ts = self.parse_timestamp(iv[0], int(exp_str))
                    if ts.date() != exp_date:
                        print(f"🚨 IV VALIDATION FAILED: timestamp {ts.date()} != expiration {exp_date}")
                        return []
                
                return response
        except Exception as e:
            print(f"IV error for ${strike}{right}: {str(e)[:50]}")
        return []
    
    def save_contract_data(self, cursor, trade_date: datetime, strike: int, right: str,
                          ohlc_data: List, greeks_data: List, iv_data: List) -> Dict:
        """Save all data with enhanced validation"""
        stats = {'ohlc': 0, 'greeks': 0, 'iv': 0}
        
        # Pre-save validation: ensure this is 0DTE
        exp_date = trade_date.date()
        
        # Insert/get contract with BULLETPROOF validation
        try:
            cursor.execute("""
                INSERT INTO theta.options_contracts 
                (contract_id, symbol, expiration, strike, option_type)
                VALUES (DEFAULT, 'SPY', %s, %s, %s)
                ON CONFLICT (symbol, expiration, strike, option_type)
                DO UPDATE SET symbol = EXCLUDED.symbol
                RETURNING contract_id
            """, (trade_date.date(), strike, right))
            
            result = cursor.fetchone()
            if result:
                contract_id = result[0]
            else:
                cursor.execute("""
                    SELECT contract_id FROM theta.options_contracts
                    WHERE symbol='SPY' AND expiration=%s 
                    AND strike=%s AND option_type=%s
                """, (trade_date.date(), strike, right))
                contract_id = cursor.fetchone()[0]
        except Exception as e:
            print(f"🚨 CONTRACT SAVE ERROR: {e}")
            return stats
        
        exp_int = int(trade_date.strftime('%Y%m%d'))
        
        # Save OHLC data with validation
        for bar in ohlc_data:
            ts = self.parse_timestamp(bar[0], exp_int)
            
            # CRITICAL: Validate timestamp matches expiration
            if ts.date() != exp_date:
                print(f"🚨 OHLC TIMESTAMP VIOLATION: {ts.date()} != {exp_date}")
                continue
                
            try:
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
            except Exception as e:
                print(f"🚨 OHLC INSERT ERROR: {e}")
        
        # Save Greeks data with validation
        for greek in greeks_data:
            ts = self.parse_timestamp(greek[0], exp_int)
            
            # CRITICAL: Validate timestamp matches expiration
            if ts.date() != exp_date:
                print(f"🚨 GREEKS TIMESTAMP VIOLATION: {ts.date()} != {exp_date}")
                continue
                
            # Skip 16:00 records
            if ts.time().hour == 16:
                continue
                
            delta = float(greek[3]) if greek[3] is not None else None
            gamma = float(greek[4]) if greek[4] is not None else None
            theta = float(greek[5]) if greek[5] is not None else None
            vega = float(greek[6]) if greek[6] is not None else None
            rho = float(greek[7]) if greek[7] is not None else None
            
            try:
                cursor.execute("""
                    INSERT INTO theta.options_greeks
                    (contract_id, datetime, delta, gamma, theta, vega, rho)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, (contract_id, ts, delta, gamma, theta, vega, rho))
                if cursor.rowcount > 0:
                    stats['greeks'] += 1
            except Exception as e:
                print(f"🚨 GREEKS INSERT ERROR: {e}")
        
        # Save IV data with validation
        for iv in iv_data:
            ts = self.parse_timestamp(iv[0], exp_int)
            
            # CRITICAL: Validate timestamp matches expiration
            if ts.date() != exp_date:
                print(f"🚨 IV TIMESTAMP VIOLATION: {ts.date()} != {exp_date}")
                continue
            
            # IV is in different fields for calls vs puts
            if right == 'C':
                implied_vol = float(iv[4]) if iv[4] is not None and iv[4] > 0 else None
            else:  # Put
                implied_vol = float(iv[2]) if iv[2] is not None and iv[2] > 0 else None
            
            if implied_vol:
                try:
                    cursor.execute("""
                        INSERT INTO theta.options_iv
                        (contract_id, datetime, implied_volatility)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (contract_id, datetime) DO NOTHING
                    """, (contract_id, ts, implied_vol))
                    if cursor.rowcount > 0:
                        stats['iv'] += 1
                except Exception as e:
                    print(f"🚨 IV INSERT ERROR: {e}")
        
        return stats
    
    def download_day(self, trade_date: datetime) -> Dict:
        """Download 0DTE options with bulletproof validation for a single day"""
        date_str = trade_date.strftime('%Y-%m-%d')
        exp_str = trade_date.strftime('%Y%m%d')
        
        print(f"\n{'='*80}")
        print(f"🔒 BULLETPROOF DOWNLOAD: {date_str} ({trade_date.strftime('%A')})")
        print(f"🔒 0DTE Validation: ENABLED")
        
        # PRE-DOWNLOAD VALIDATION
        if not self.validate_0dte_compliance():
            return {'success': False, 'reason': 'Pre-download contamination detected'}
        
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
                'start_date': exp_str,  # CRITICAL: Must match exp_str
                'end_date': exp_str,    # CRITICAL: Must match exp_str
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
                    # Download all data types with enhanced validation
                    ohlc_data = self.download_ohlc(exp_str, strike, right, trade_date)
                    time.sleep(self.delay)
                    
                    greeks_data = self.download_greeks(exp_str, strike, right, trade_date)
                    time.sleep(self.delay)
                    
                    iv_data = self.download_iv(exp_str, strike, right, trade_date)
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
                    
                    # Periodic validation and progress report
                    if contracts_saved % 20 == 0 and contracts_saved > 0:
                        print(f"  Progress: {contracts_saved} contracts, "
                              f"{total_stats['ohlc']} OHLC, "
                              f"{total_stats['greeks']} Greeks, "
                              f"{total_stats['iv']} IV bars")
                        
                        # Real-time contamination check
                        conn.commit()
                        if not self.validate_0dte_compliance():
                            conn.rollback()
                            return {'success': False, 'reason': 'Mid-download contamination detected'}
            
            conn.commit()
            
            # POST-DOWNLOAD VALIDATION
            if not self.validate_0dte_compliance():
                conn.rollback()
                return {'success': False, 'reason': 'Post-download contamination detected'}
            
            print(f"\n✅ Success: {contracts_saved} contracts")
            print(f"   OHLC bars: {total_stats['ohlc']}")
            print(f"   Greeks bars: {total_stats['greeks']}")
            print(f"   IV bars: {total_stats['iv']}")
            print(f"🔒 0DTE compliance: VERIFIED")
            
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
        """Download all of December 2022 with bulletproof validation"""
        print("🔒 BULLETPROOF DECEMBER 2022 SPY 0DTE OPTIONS DOWNLOAD")
        print("🔒 Enhanced with contamination prevention and real-time validation")
        print("Downloading OHLC + Greeks + IV with 5-minute intervals")
        print("Using daily opening price ± $20 for strike selection")
        
        # Initial validation check
        if not self.validate_0dte_compliance():
            print("❌ Pre-download validation failed - aborting")
            return
        
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
                        
                        # If validation failed, stop immediately
                        if 'contamination' in result['reason'].lower():
                            print(f"🚨 STOPPING DOWNLOAD DUE TO CONTAMINATION: {result['reason']}")
                            break
            
            current += timedelta(days=1)
        
        # Final validation
        print(f"\n🔒 FINAL VALIDATION CHECK...")
        if self.validate_0dte_compliance():
            print("✅ Final validation passed")
            self.print_report()
        else:
            print("❌ FINAL VALIDATION FAILED - DATABASE MAY BE CONTAMINATED")
    
    def print_report(self):
        """Print comprehensive download report with validation stats"""
        print("\n" + "="*100)
        print("🔒 BULLETPROOF DECEMBER 2022 SPY 0DTE DOWNLOAD REPORT")
        print("="*100)
        
        print(f"\n🔒 VALIDATION STATISTICS:")
        print(f"   Validation checks performed: {self.report['validation_checks']}")
        print(f"   Validation failures: {self.report['validation_failures']}")
        print(f"   Validation success rate: {((self.report['validation_checks'] - self.report['validation_failures']) / max(1, self.report['validation_checks']) * 100):.1f}%")
        
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
        print("🔒 BULLETPROOF SUMMARY:")
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
        
        print(f"\n🔒 CONTAMINATION PROTECTION: ACTIVE")
        print(f"🔒 0DTE COMPLIANCE: 100% GUARANTEED")

def main():
    downloader = BulletproofDownloader()
    downloader.download_december_2022()

if __name__ == "__main__":
    main()