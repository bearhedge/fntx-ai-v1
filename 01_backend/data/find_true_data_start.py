#!/usr/bin/env python3
"""
Find the true start of continuous SPY options data
Test every month from 2019 onwards more carefully
"""
import sys
import requests
from datetime import datetime, timedelta
import yfinance as yf

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import THETA_HTTP_API

def test_trading_days(year: int, month: int) -> dict:
    """Test multiple trading days in a month for consistency"""
    session = requests.Session()
    spy = yf.Ticker("SPY")
    
    # Test 5 different trading days in the month
    test_days = [5, 10, 15, 20, 25]
    successful_tests = 0
    
    for day in test_days:
        try:
            test_date = datetime(year, month, day)
            # Skip if beyond month end
            if test_date.month != month:
                continue
            # Skip weekends
            if test_date.weekday() >= 5:
                test_date = test_date - timedelta(days=test_date.weekday() - 4)
            
            # Get SPY price
            date_str = test_date.strftime('%Y-%m-%d')
            next_day = (test_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            hist = spy.history(start=date_str, end=next_day)
            if hist.empty:
                continue
                
            spy_price = float(hist['Close'].iloc[0])
            atm_strike = int(round(spy_price))
            
            # Find nearest Friday expiration
            days_to_friday = (4 - test_date.weekday()) % 7
            if days_to_friday == 0:
                days_to_friday = 7  # Next Friday
            exp_date = test_date + timedelta(days=days_to_friday)
            
            # Test data availability
            url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
            params = {
                'root': 'SPY',
                'exp': exp_date.strftime('%Y%m%d'),
                'strike': atm_strike * 1000,
                'right': 'C',
                'start_date': test_date.strftime('%Y%m%d'),
                'end_date': test_date.strftime('%Y%m%d'),
                'ivl': 60000
            }
            
            response = session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('response') and len(data['response']) > 300:  # At least 300 bars
                    successful_tests += 1
                    
        except Exception as e:
            continue
    
    # Consider month has good data if at least 3 out of 5 days work
    return {
        'has_good_data': successful_tests >= 3,
        'successful_days': successful_tests,
        'total_days': len(test_days)
    }

def main():
    print("Finding true start of continuous SPY options data...")
    print("Testing multiple days per month for consistency")
    print("="*80)
    
    print(f"{'Year-Month':<12} {'Test Results':<20} {'Status'}")
    print("-" * 45)
    
    # Start from 2019 since earlier data is sporadic
    first_good_month = None
    consecutive_good = 0
    
    for year in range(2019, 2025):
        for month in range(1, 13):
            # Skip future
            if datetime(year, month, 1) > datetime.now():
                break
            
            result = test_trading_days(year, month)
            month_str = f"{year}-{month:02d}"
            
            if result['has_good_data']:
                status = f"✅ Good data"
                test_str = f"{result['successful_days']}/{result['total_days']} days work"
                consecutive_good += 1
                
                if not first_good_month and consecutive_good >= 3:
                    # Found 3 consecutive months with good data
                    first_good_month = (year, month - 2)  # Go back to start
                    print(f"{month_str:<12} {test_str:<20} {status}")
                    print(f"\n🎯 Found start of reliable continuous data!")
                    print(f"   Start from: {first_good_month[0]}-{first_good_month[1]:02d}")
                    print(f"   {consecutive_good} consecutive months verified")
                    
                    # Show recommendation
                    start_date = datetime(first_good_month[0], first_good_month[1], 1)
                    print(f"\n📊 Recommendation:")
                    print(f"   Begin downloading from: {start_date.strftime('%B %Y')}")
                    print(f"   This gives you {(datetime.now() - start_date).days // 365} years of continuous data")
                    return
                else:
                    print(f"{month_str:<12} {test_str:<20} {status}")
            else:
                status = "❌ Sporadic"
                test_str = f"{result['successful_days']}/{result['total_days']} days work"
                print(f"{month_str:<12} {test_str:<20} {status}")
                consecutive_good = 0

if __name__ == "__main__":
    main()