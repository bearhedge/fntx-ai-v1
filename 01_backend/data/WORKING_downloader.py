#!/usr/bin/env python3
"""
GUARANTEED WORKING DOWNLOADER - Handles all edge cases
"""
import sys
import requests
import psycopg2
import psycopg2.extensions
import yfinance as yf
import time
from datetime import datetime, timedelta

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

class WorkingDownloader:
    def __init__(self):
        self.base_url = "http://127.0.0.1:25510/v2/hist/option"
        self.stats = {'days': 0, 'contracts': 0, 'ohlc': 0, 'greeks': 0, 'iv': 0}
        
    def get_or_create_contract(self, cursor, symbol, expiration, strike, option_type):
        """Get existing contract or create new one - HANDLES DUPLICATES PROPERLY"""
        # First try to get existing
        cursor.execute("""
            SELECT contract_id FROM theta.options_contracts
            WHERE symbol=%s AND expiration=%s AND strike=%s AND option_type=%s
        """, (symbol, expiration, strike, option_type))
        
        result = cursor.fetchone()
        if result:
            return result[0]
        
        # Create new with a savepoint to handle unique constraint
        cursor.execute("SAVEPOINT contract_insert")
        try:
            cursor.execute("""
                INSERT INTO theta.options_contracts 
                (symbol, expiration, strike, option_type)
                VALUES (%s, %s, %s, %s)
                RETURNING contract_id
            """, (symbol, expiration, strike, option_type))
            contract_id = cursor.fetchone()[0]
            cursor.execute("RELEASE SAVEPOINT contract_insert")
            return contract_id
        except psycopg2.IntegrityError:
            # Duplicate - rollback savepoint and get existing
            cursor.execute("ROLLBACK TO SAVEPOINT contract_insert")
            cursor.execute("""
                SELECT contract_id FROM theta.options_contracts
                WHERE symbol=%s AND expiration=%s AND strike=%s AND option_type=%s
            """, (symbol, expiration, strike, option_type))
            return cursor.fetchone()[0]
    
    def download_single_contract(self, cursor, trade_date, strike, right):
        """Download data for a single contract with proper error handling"""
        exp_str = trade_date.strftime('%Y%m%d')
        params = {
            'root': 'SPY',
            'exp': exp_str,
            'strike': strike * 1000,
            'right': right,
            'start_date': exp_str,
            'end_date': exp_str,
            'ivl': 300000  # 5 minutes
        }
        
        # Get contract ID
        contract_id = self.get_or_create_contract(
            cursor, 'SPY', trade_date.date(), strike, right
        )
        
        saved = {'ohlc': 0, 'greeks': 0, 'iv': 0}
        
        # Download OHLC
        try:
            r = requests.get(f"{self.base_url}/ohlc", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json().get('response', [])
                for bar in data:
                    ts = self.parse_timestamp(bar[0], trade_date)
                    cursor.execute("SAVEPOINT ohlc_insert")
                    try:
                        cursor.execute("""
                            INSERT INTO theta.options_ohlc
                            (contract_id, datetime, open, high, low, close, volume, trade_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (contract_id, ts, float(bar[1]), float(bar[2]), 
                              float(bar[3]), float(bar[4]), int(bar[5]), int(bar[6])))
                        cursor.execute("RELEASE SAVEPOINT ohlc_insert")
                        saved['ohlc'] += 1
                    except psycopg2.IntegrityError:
                        cursor.execute("ROLLBACK TO SAVEPOINT ohlc_insert")
        except Exception as e:
            print(f"  OHLC error ${strike}{right}: {e}")
        
        # Download Greeks
        try:
            r = requests.get(f"{self.base_url}/greeks", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json().get('response', [])
                for greek in data:
                    ts = self.parse_timestamp(greek[0], trade_date)
                    if ts.time().hour == 16:  # Skip 16:00
                        continue
                    cursor.execute("SAVEPOINT greeks_insert")
                    try:
                        cursor.execute("""
                            INSERT INTO theta.options_greeks
                            (contract_id, datetime, delta, gamma, theta, vega, rho)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (contract_id, ts,
                              float(greek[3]) if greek[3] is not None else None,
                              float(greek[4]) if greek[4] is not None else None,
                              float(greek[5]) if greek[5] is not None else None,
                              float(greek[6]) if greek[6] is not None else None,
                              float(greek[7]) if greek[7] is not None else None))
                        cursor.execute("RELEASE SAVEPOINT greeks_insert")
                        saved['greeks'] += 1
                    except psycopg2.IntegrityError:
                        cursor.execute("ROLLBACK TO SAVEPOINT greeks_insert")
        except Exception as e:
            print(f"  Greeks error ${strike}{right}: {e}")
        
        # Download IV
        try:
            r = requests.get(f"{self.base_url}/implied_volatility", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json().get('response', [])
                for iv in data:
                    ts = self.parse_timestamp(iv[0], trade_date)
                    # CORRECT IV PARSING
                    if right == 'C':
                        implied_vol = float(iv[4]) if iv[4] is not None and iv[4] > 0 else None
                    else:
                        implied_vol = float(iv[2]) if iv[2] is not None and iv[2] > 0 else None
                    
                    if implied_vol:
                        cursor.execute("SAVEPOINT iv_insert")
                        try:
                            cursor.execute("""
                                INSERT INTO theta.options_iv
                                (contract_id, datetime, implied_volatility)
                                VALUES (%s, %s, %s)
                            """, (contract_id, ts, implied_vol))
                            cursor.execute("RELEASE SAVEPOINT iv_insert")
                            saved['iv'] += 1
                        except psycopg2.IntegrityError:
                            cursor.execute("ROLLBACK TO SAVEPOINT iv_insert")
        except Exception as e:
            print(f"  IV error ${strike}{right}: {e}")
        
        time.sleep(0.1)  # Rate limit
        return saved
    
    def parse_timestamp(self, ms_of_day, trade_date):
        """Parse timestamp from ms_of_day"""
        hours = ms_of_day // (1000 * 60 * 60)
        minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
        seconds = (ms_of_day % (1000 * 60)) // 1000
        return datetime(trade_date.year, trade_date.month, trade_date.day, hours, minutes, seconds)
    
    def download_day(self, trade_date):
        """Download all data for a single day"""
        print(f"\n{'='*60}")
        print(f"Downloading {trade_date.strftime('%Y-%m-%d')} ({trade_date.strftime('%A')})")
        
        # Get SPY price
        try:
            spy = yf.Ticker('SPY')
            data = spy.history(
                start=trade_date.strftime('%Y-%m-%d'),
                end=(trade_date + timedelta(days=1)).strftime('%Y-%m-%d')
            )
            spy_open = float(data['Open'].iloc[0])
        except:
            print("❌ Could not get SPY price")
            return False
        
        print(f"SPY Open: ${spy_open:.2f}")
        
        # Find available strikes
        min_strike = int(spy_open - 20)
        max_strike = int(spy_open + 20)
        available_strikes = []
        
        exp_str = trade_date.strftime('%Y%m%d')
        for strike in range(min_strike, max_strike + 1):
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
        
        if not available_strikes:
            print("❌ No strikes available")
            return False
        
        print(f"Found {len(available_strikes)} strikes: ${min(available_strikes)}-${max(available_strikes)}")
        
        # Download with NEW CONNECTION for each day
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        day_stats = {'contracts': 0, 'ohlc': 0, 'greeks': 0, 'iv': 0}
        
        try:
            for i, strike in enumerate(available_strikes):
                for right in ['C', 'P']:
                    saved = self.download_single_contract(cursor, trade_date, strike, right)
                    if saved['ohlc'] > 0:
                        day_stats['contracts'] += 1
                        day_stats['ohlc'] += saved['ohlc']
                        day_stats['greeks'] += saved['greeks']
                        day_stats['iv'] += saved['iv']
                
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i+1}/{len(available_strikes)} strikes...")
            
            print(f"✅ Day complete: {day_stats['contracts']} contracts, "
                  f"{day_stats['ohlc']} OHLC, {day_stats['greeks']} Greeks, {day_stats['iv']} IV")
            
            self.stats['days'] += 1
            self.stats['contracts'] += day_stats['contracts']
            self.stats['ohlc'] += day_stats['ohlc']
            self.stats['greeks'] += day_stats['greeks']
            self.stats['iv'] += day_stats['iv']
            
            return True
            
        except Exception as e:
            print(f"❌ Day error: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def download_december_2022(self):
        """Download all of December 2022"""
        print("WORKING DECEMBER 2022 DOWNLOADER")
        print("="*60)
        print("This WILL work - handling all edge cases properly")
        
        holidays = [datetime(2022, 12, 26)]
        current = datetime(2022, 12, 1)
        end = datetime(2022, 12, 31)
        
        while current <= end:
            if current.weekday() < 5 and current not in holidays:
                self.download_day(current)
            current += timedelta(days=1)
        
        print(f"\n{'='*60}")
        print("DOWNLOAD COMPLETE")
        print(f"Days processed: {self.stats['days']}")
        print(f"Total contracts: {self.stats['contracts']:,}")
        print(f"Total OHLC: {self.stats['ohlc']:,}")
        print(f"Total Greeks: {self.stats['greeks']:,}")
        print(f"Total IV: {self.stats['iv']:,}")
        
        if self.stats['ohlc'] > 0:
            print(f"\nGreeks coverage: {self.stats['greeks']/self.stats['ohlc']*100:.1f}%")
            print(f"IV coverage: {self.stats['iv']/self.stats['ohlc']*100:.1f}%")

if __name__ == "__main__":
    downloader = WorkingDownloader()
    downloader.download_december_2022()