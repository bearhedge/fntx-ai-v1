#!/usr/bin/env python3
"""
Find when continuous SPY options data actually starts
Testing month by month to find consistent data availability
"""
import sys
import requests
from datetime import datetime
import yfinance as yf

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import THETA_HTTP_API

def test_month(year: int, month: int) -> dict:
    """Test data availability for a specific month"""
    session = requests.Session()
    spy = yf.Ticker("SPY")
    
    # Get SPY price for mid-month
    test_date = datetime(year, month, 15)
    if test_date.weekday() >= 5:  # Weekend
        test_date = datetime(year, month, 14 if test_date.weekday() == 6 else 13)
    
    # Get SPY price
    date_str = test_date.strftime('%Y-%m-%d')
    next_day = (test_date + timedelta(days=1)).strftime('%Y-%m-%d') 
    
    try:
        hist = spy.history(start=date_str, end=next_day)
        if hist.empty:
            return {'has_data': False, 'reason': 'No SPY price'}
        spy_price = float(hist['Close'].iloc[0])
    except:
        return {'has_data': False, 'reason': 'SPY price error'}
    
    # Calculate ATM strike
    atm_strike = int(round(spy_price))
    
    # Test with monthly expiration (3rd Friday)
    # Find 3rd Friday
    first_day = datetime(year, month, 1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
    third_friday = first_friday + timedelta(days=14)
    
    exp_date = third_friday.strftime('%Y%m%d')
    trade_date = test_date.strftime('%Y%m%d')
    
    # Test if data exists
    url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
    params = {
        'root': 'SPY',
        'exp': exp_date,
        'strike': atm_strike * 1000,
        'right': 'C',
        'start_date': trade_date,
        'end_date': trade_date,
        'ivl': 60000
    }
    
    try:
        response = session.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('response'):
                return {
                    'has_data': True,
                    'spy_price': spy_price,
                    'atm_strike': atm_strike,
                    'bars': len(data['response']),
                    'exp_date': exp_date
                }
    except:
        pass
    
    return {'has_data': False, 'reason': 'No options data'}

def main():
    print("Finding start of continuous SPY options data...")
    print("="*80)
    
    # Test months from 2016 onwards
    print(f"{'Year-Month':<12} {'SPY Price':<10} {'ATM Strike':<12} {'Has Data':<10} {'Details'}")
    print("-" * 60)
    
    first_continuous = None
    
    for year in [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]:
        for month in range(1, 13):
            # Skip future months
            if datetime(year, month, 1) > datetime.now():
                break
            
            result = test_month(year, month)
            
            month_str = f"{year}-{month:02d}"
            
            if result['has_data']:
                spy_str = f"${result['spy_price']:.2f}"
                strike_str = f"${result['atm_strike']}"
                status = f"✅ {result['bars']} bars"
                
                if not first_continuous:
                    first_continuous = (year, month)
                
                print(f"{month_str:<12} {spy_str:<10} {strike_str:<12} {status:<10}")
            else:
                # Only print failures near boundaries
                if first_continuous and (year, month) < first_continuous:
                    print(f"{month_str:<12} {'N/A':<10} {'N/A':<12} ❌ {result.get('reason', 'No data')}")
            
            # If we found continuous data, check if it stays continuous
            if first_continuous and result['has_data']:
                # Test next 3 months to verify continuity
                continuous = True
                for i in range(1, 4):
                    test_month_num = month + i
                    test_year = year
                    if test_month_num > 12:
                        test_month_num -= 12
                        test_year += 1
                    
                    if datetime(test_year, test_month_num, 1) > datetime.now():
                        break
                    
                    next_result = test_month(test_year, test_month_num)
                    if not next_result['has_data']:
                        continuous = False
                        break
                
                if continuous:
                    print(f"\n✅ Found start of continuous data: {month_str}")
                    print(f"   SPY was trading at ${result['spy_price']:.2f}")
                    print(f"   Monthly expiration: {result['exp_date']}")
                    return
    
    print("\n❌ No continuous data found!")

if __name__ == "__main__":
    from datetime import timedelta
    main()