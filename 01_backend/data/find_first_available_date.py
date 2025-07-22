#!/usr/bin/env python3
"""
Find the first available date with options data in Theta Data
"""
import sys
import requests
from datetime import datetime, timedelta

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import THETA_HTTP_API

def test_options_data(test_date: datetime, expiration: str) -> bool:
    """Test if options data is available for a specific date"""
    session = requests.Session()
    
    # Test with a reasonable strike for the time period
    # SPY was around $200-250 in 2016-2017
    test_strike = 220000  # $220 in 1/10th cent
    
    url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
    params = {
        'root': 'SPY',
        'exp': expiration,
        'strike': test_strike,
        'right': 'C',
        'start_date': test_date.strftime('%Y%m%d'),
        'end_date': test_date.strftime('%Y%m%d'),
        'ivl': 60000  # 1-minute
    }
    
    try:
        response = session.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return bool(data.get('response'))
        elif response.status_code == 471:
            # "End date cannot earlier than the your first access date"
            return False
    except:
        pass
    
    return False

def find_first_available_date():
    """Binary search to find the first available date"""
    print("Finding first available date for options data...")
    print("=" * 60)
    
    # Get list of all expirations
    session = requests.Session()
    url = f"{THETA_HTTP_API}/v2/list/expirations"
    params = {'root': 'SPY'}
    
    response = session.get(url, params=params)
    if response.status_code != 200:
        print("Failed to get expirations list")
        return
    
    data = response.json()
    expirations = sorted([str(exp) for exp in data.get('response', [])])
    
    print(f"Found {len(expirations)} expirations")
    print(f"Range: {expirations[0]} to {expirations[-1]}")
    
    # Test different years
    test_points = [
        ('2016-01-04', '20160115'),  # 9 years ago
        ('2017-01-03', '20170120'),  # 8 years ago
        ('2017-07-03', '20170707'),  # 7.5 years ago
        ('2018-01-02', '20180119'),  # 7 years ago
        ('2019-01-02', '20190118'),  # 6 years ago
        ('2020-01-02', '20200117'),  # 5 years ago
        ('2021-01-04', '20210115'),  # 4 years ago
        ('2022-01-03', '20220121'),  # 3 years ago
        ('2023-01-03', '20230120'),  # 2 years ago
        ('2024-01-02', '20240119'),  # 1 year ago
    ]
    
    print("\nTesting availability by year:")
    first_available = None
    
    for date_str, exp_str in test_points:
        test_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Find a valid expiration near this date
        exp_date = datetime.strptime(exp_str, '%Y%m%d')
        
        # Check if this expiration exists
        if exp_str not in expirations:
            # Find nearest expiration
            for exp in expirations:
                if exp >= exp_str:
                    exp_str = exp
                    break
        
        has_data = test_options_data(test_date, exp_str)
        
        if has_data:
            print(f"  ✅ {date_str}: Data available (exp: {exp_str})")
            if not first_available:
                first_available = test_date
        else:
            print(f"  ❌ {date_str}: No data")
    
    if first_available:
        print(f"\nFirst available date: {first_available.strftime('%Y-%m-%d')}")
        
        # Find exact boundary with binary search
        print("\nRefining exact start date...")
        
        # We know data exists at first_available
        # Check 6 months before
        earlier = first_available - timedelta(days=180)
        
        while (first_available - earlier).days > 1:
            mid = earlier + (first_available - earlier) / 2
            
            # Find nearest expiration
            mid_str = mid.strftime('%Y%m%d')
            exp_to_test = None
            for exp in expirations:
                if exp >= mid_str:
                    exp_to_test = exp
                    break
            
            if exp_to_test and test_options_data(mid, exp_to_test):
                first_available = mid
                print(f"  Data found at {mid.strftime('%Y-%m-%d')}")
            else:
                earlier = mid
                print(f"  No data at {mid.strftime('%Y-%m-%d')}")
        
        print(f"\nExact first available date: {first_available.strftime('%Y-%m-%d')}")
        
        # Show what options are available for the first month
        print(f"\nExpirations in first month:")
        first_month_end = first_available + timedelta(days=30)
        count = 0
        for exp in expirations:
            exp_date = datetime.strptime(exp, '%Y%m%d')
            if first_available <= exp_date <= first_month_end:
                print(f"  {exp} ({exp_date.strftime('%a, %b %d, %Y')})")
                count += 1
        print(f"Total: {count} expirations in first month")
        
        return first_available
    else:
        print("\nNo available data found!")
        return None

if __name__ == "__main__":
    first_date = find_first_available_date()