#!/usr/bin/env python3
"""
Find the actual start date of available options data
Test year by year to find when data really begins
"""
import sys
import requests
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import THETA_HTTP_API

def test_year(year: int) -> bool:
    """Test if data is available for a specific year"""
    session = requests.Session()
    
    # Test with first Friday of the year
    test_dates = {
        2017: ('20170106', '20170103', 180),  # Jan 6 exp, Jan 3 trade, $180 strike
        2018: ('20180105', '20180102', 200),  
        2019: ('20180104', '20190102', 220),
        2020: ('20200103', '20200102', 250),
        2021: ('20210108', '20210104', 300),
        2022: ('20220107', '20220103', 350),
        2023: ('20230106', '20230103', 380),
        2024: ('20240105', '20240102', 400),
    }
    
    if year not in test_dates:
        return False
    
    exp_date, trade_date, strike = test_dates[year]
    
    url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
    params = {
        'root': 'SPY',
        'exp': exp_date,
        'strike': strike * 1000,
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
                return True
    except:
        pass
    
    return False

def find_actual_start():
    print("Finding actual start date of options data...")
    print("="*60)
    
    # Test each year
    for year in range(2017, 2025):
        has_data = test_year(year)
        print(f"{year}: {'✅ Data available' if has_data else '❌ No data'}")
    
    # Now test months of 2017 more carefully
    print("\nTesting 2017 months...")
    session = requests.Session()
    url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
    
    # Get a 2017 expiration that likely exists
    test_exp = '20170721'  # July 21, 2017 (Friday)
    
    for month in range(1, 13):
        # Test first trading day of each month
        test_date = f"2017{month:02d}03"  # 3rd of month (usually after weekend)
        
        params = {
            'root': 'SPY',
            'exp': test_exp,
            'strike': 240000,  # $240
            'right': 'C', 
            'start_date': test_date,
            'end_date': test_date,
            'ivl': 60000
        }
        
        try:
            response = session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    print(f"  {datetime.strptime(test_date, '%Y%m%d').strftime('%B %Y')}: ✅ Data found")
                else:
                    print(f"  {datetime.strptime(test_date, '%Y%m%d').strftime('%B %Y')}: ❌ No data")
            else:
                print(f"  {datetime.strptime(test_date, '%Y%m%d').strftime('%B %Y')}: ❌ Error {response.status_code}")
        except Exception as e:
            print(f"  {datetime.strptime(test_date, '%Y%m%d').strftime('%B %Y')}: ❌ {str(e)[:50]}")
    
    # Test specific dates in June/July 2017
    print("\nTesting June/July 2017 transition...")
    
    test_dates = [
        '20170615',  # June 15
        '20170620',  # June 20
        '20170625',  # June 25
        '20170630',  # June 30
        '20170701',  # July 1
        '20170705',  # July 5
        '20170710',  # July 10
    ]
    
    for date_str in test_dates:
        params['start_date'] = date_str
        params['end_date'] = date_str
        
        try:
            response = session.get(url, params=params, timeout=5)
            has_data = response.status_code == 200 and bool(response.json().get('response'))
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            print(f"  {date_obj.strftime('%Y-%m-%d')}: {'✅' if has_data else '❌'}")
        except:
            print(f"  {date_str}: ❌ Error")

if __name__ == "__main__":
    find_actual_start()