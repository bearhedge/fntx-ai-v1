#!/usr/bin/env python3
"""
Minimal working downloader - focus on getting data downloaded
"""
import sys
import requests
import psycopg2
import yfinance as yf
import time
from datetime import datetime, timedelta

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def download_single_day(trade_date):
    """Download data for a single day"""
    date_str = trade_date.strftime('%Y-%m-%d')
    exp_str = trade_date.strftime('%Y%m%d')
    
    print(f"\nDownloading {date_str}...")
    
    # Get SPY price
    try:
        spy = yf.Ticker('SPY')
        data = spy.history(start=date_str, end=(trade_date + timedelta(days=1)).strftime('%Y-%m-%d'))
        spy_open = float(data['Open'].iloc[0])
    except:
        print(f"❌ Could not get SPY price for {date_str}")
        return 0
    
    print(f"SPY Open: ${spy_open:.2f}")
    
    # Strike range
    min_strike = int(spy_open - 20)
    max_strike = int(spy_open + 20)
    
    # Find available strikes
    available_strikes = []
    base_url = "http://127.0.0.1:25510/v2/hist/option/ohlc"
    
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
            r = requests.get(base_url, params=params, timeout=3)
            if r.status_code == 200 and r.json().get('response'):
                available_strikes.append(strike)
        except:
            pass
        time.sleep(0.05)
    
    print(f"Found {len(available_strikes)} strikes: ${min(available_strikes)} to ${max(available_strikes)}")
    
    if not available_strikes:
        print("❌ No strikes found")
        return 0
    
    # Download data
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    total_contracts = 0
    
    try:
        for strike in available_strikes:
            for right in ['C', 'P']:
                # Download OHLC
                params = {
                    'root': 'SPY', 'exp': exp_str, 'strike': strike * 1000, 'right': right,
                    'start_date': exp_str, 'end_date': exp_str, 'ivl': 300000
                }
                
                ohlc_data = []
                try:
                    r = requests.get("http://127.0.0.1:25510/v2/hist/option/ohlc", params=params, timeout=10)
                    if r.status_code == 200:
                        ohlc_data = r.json().get('response', [])
                except:
                    pass
                
                if not ohlc_data:
                    continue
                
                # Create contract
                try:
                    cursor.execute("""
                        INSERT INTO theta.options_contracts 
                        (symbol, expiration, strike, option_type)
                        VALUES ('SPY', %s, %s, %s)
                        RETURNING contract_id
                    """, (trade_date.date(), strike, right))
                    contract_id = cursor.fetchone()[0]
                except psycopg2.IntegrityError:
                    # Contract exists
                    cursor.execute("""
                        SELECT contract_id FROM theta.options_contracts
                        WHERE symbol='SPY' AND expiration=%s AND strike=%s AND option_type=%s
                    """, (trade_date.date(), strike, right))
                    contract_id = cursor.fetchone()[0]
                
                # Save OHLC
                for bar in ohlc_data:
                    ms_of_day = bar[0]
                    hours = ms_of_day // (1000 * 60 * 60)
                    minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
                    seconds = (ms_of_day % (1000 * 60)) // 1000
                    ts = datetime(trade_date.year, trade_date.month, trade_date.day, hours, minutes, seconds)
                    
                    try:
                        cursor.execute("""
                            INSERT INTO theta.options_ohlc
                            (contract_id, datetime, open, high, low, close, volume, trade_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (contract_id, ts, float(bar[1]), float(bar[2]), float(bar[3]), 
                              float(bar[4]), int(bar[5]), int(bar[6])))
                    except psycopg2.IntegrityError:
                        pass
                
                # Download and save Greeks
                try:
                    r = requests.get("http://127.0.0.1:25510/v2/hist/option/greeks", params=params, timeout=10)
                    if r.status_code == 200:
                        greeks_data = r.json().get('response', [])
                        for greek in greeks_data:
                            ms_of_day = greek[0]
                            hours = ms_of_day // (1000 * 60 * 60)
                            minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
                            seconds = (ms_of_day % (1000 * 60)) // 1000
                            ts = datetime(trade_date.year, trade_date.month, trade_date.day, hours, minutes, seconds)
                            
                            # Skip 16:00 records
                            if ts.time().hour == 16:
                                continue
                            
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
                            except psycopg2.IntegrityError:
                                pass
                except:
                    pass
                
                # Download and save IV
                try:
                    r = requests.get("http://127.0.0.1:25510/v2/hist/option/implied_volatility", params=params, timeout=10)
                    if r.status_code == 200:
                        iv_data = r.json().get('response', [])
                        for iv in iv_data:
                            ms_of_day = iv[0]
                            hours = ms_of_day // (1000 * 60 * 60)
                            minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
                            seconds = (ms_of_day % (1000 * 60)) // 1000
                            ts = datetime(trade_date.year, trade_date.month, trade_date.day, hours, minutes, seconds)
                            
                            # CORRECT IV parsing
                            if right == 'C':
                                implied_vol = float(iv[4]) if iv[4] is not None and iv[4] > 0 else None
                            else:
                                implied_vol = float(iv[2]) if iv[2] is not None and iv[2] > 0 else None
                            
                            if implied_vol:
                                try:
                                    cursor.execute("""
                                        INSERT INTO theta.options_iv
                                        (contract_id, datetime, implied_volatility)
                                        VALUES (%s, %s, %s)
                                    """, (contract_id, ts, implied_vol))
                                except psycopg2.IntegrityError:
                                    pass
                except:
                    pass
                
                total_contracts += 1
                time.sleep(0.1)
        
        conn.commit()
        print(f"✅ {total_contracts} contracts downloaded")
        return total_contracts
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

def main():
    print("MINIMAL DECEMBER 2022 DOWNLOADER")
    print("="*50)
    
    # Download December 2022
    start_date = datetime(2022, 12, 1)
    end_date = datetime(2022, 12, 31)
    holidays = [datetime(2022, 12, 26)]
    
    total_contracts = 0
    successful_days = 0
    
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in holidays:  # Weekday, not holiday
            contracts = download_single_day(current)
            total_contracts += contracts
            if contracts > 0:
                successful_days += 1
        
        current += timedelta(days=1)
    
    print(f"\n" + "="*50)
    print(f"DOWNLOAD COMPLETE")
    print(f"Successful days: {successful_days}")
    print(f"Total contracts: {total_contracts:,}")

if __name__ == "__main__":
    main()