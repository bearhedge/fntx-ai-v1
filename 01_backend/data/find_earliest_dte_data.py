#!/usr/bin/env python3
"""
Find earliest available data for 0-2 DTE SPY options
Using a holistic approach that works across all years
"""
import sys
import requests
from datetime import datetime, timedelta
import yfinance as yf

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import THETA_HTTP_API

class DTEDataFinder:
    def __init__(self):
        self.session = requests.Session()
        self.spy = yf.Ticker("SPY")
        
    def get_spy_price(self, date: datetime) -> float:
        """Get SPY closing price for a given date"""
        date_str = date.strftime('%Y-%m-%d')
        next_day = (date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        try:
            hist = self.spy.history(start=date_str, end=next_day)
            if not hist.empty:
                return float(hist['Close'].iloc[0])
        except:
            pass
        return None
    
    def find_nearby_expirations(self, trade_date: datetime, max_dte: int = 2) -> list:
        """Find option expirations within max_dte days"""
        expirations = []
        
        # Check next several days for expirations
        for dte in range(max_dte + 1):
            exp_date = trade_date + timedelta(days=dte)
            
            # Skip weekends
            if exp_date.weekday() >= 5:
                continue
                
            expirations.append({
                'date': exp_date,
                'dte': dte,
                'date_str': exp_date.strftime('%Y%m%d')
            })
        
        return expirations
    
    def test_options_data(self, trade_date: datetime, exp_date_str: str, strike: int) -> bool:
        """Test if options data exists for a specific contract"""
        url = f"{THETA_HTTP_API}/v2/hist/option/ohlc"
        
        params = {
            'root': 'SPY',
            'exp': exp_date_str,
            'strike': strike * 1000,  # Convert to 1/10th cent
            'right': 'C',
            'start_date': trade_date.strftime('%Y%m%d'),
            'end_date': trade_date.strftime('%Y%m%d'),
            'ivl': 60000  # 1-minute bars
        }
        
        try:
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    return len(data['response']) > 0
        except:
            pass
        
        return False
    
    def test_date(self, test_date: datetime) -> dict:
        """Test if we have 0-2 DTE options data for a given date"""
        # Get SPY price
        spy_price = self.get_spy_price(test_date)
        if not spy_price:
            return {'date': test_date, 'has_data': False, 'reason': 'No SPY price'}
        
        # Calculate ATM strike
        atm_strike = int(round(spy_price))
        
        # Find nearby expirations
        expirations = self.find_nearby_expirations(test_date)
        
        # Test each expiration
        results = []
        for exp in expirations:
            has_data = self.test_options_data(test_date, exp['date_str'], atm_strike)
            results.append({
                'dte': exp['dte'],
                'exp_date': exp['date_str'],
                'has_data': has_data
            })
        
        # Consider successful if we have any DTE data
        any_data = any(r['has_data'] for r in results)
        
        return {
            'date': test_date,
            'spy_price': spy_price,
            'atm_strike': atm_strike,
            'has_data': any_data,
            'details': results
        }
    
    def find_earliest_date(self):
        """Find the earliest date with 0-2 DTE options data"""
        print("Finding earliest available 0-2 DTE options data...")
        print("=" * 80)
        
        # Test dates going backwards
        test_points = [
            datetime(2024, 6, 30),   # Recent (we know this works)
            datetime(2023, 6, 30),   # 1 year ago
            datetime(2022, 6, 30),   # 2 years ago
            datetime(2021, 6, 30),   # 3 years ago
            datetime(2020, 6, 30),   # 4 years ago
            datetime(2019, 6, 28),   # 5 years ago (Friday)
            datetime(2018, 6, 29),   # 6 years ago (Friday)
            datetime(2017, 6, 30),   # 7 years ago (Friday)
            datetime(2016, 6, 30),   # 8 years ago
        ]
        
        print("\nTesting availability by year:")
        print(f"{'Date':<12} {'SPY Price':<10} {'ATM Strike':<12} {'Has Data':<10} {'Details'}")
        print("-" * 80)
        
        earliest_with_data = None
        
        for test_date in test_points:
            result = self.test_date(test_date)
            
            date_str = test_date.strftime('%Y-%m-%d')
            spy_str = f"${result.get('spy_price', 0):.2f}" if result.get('spy_price') else "N/A"
            strike_str = f"${result.get('atm_strike', 0)}" if result.get('atm_strike') else "N/A"
            has_data = "✅ Yes" if result['has_data'] else "❌ No"
            
            details = ""
            if result.get('details'):
                dte_results = [f"{d['dte']}DTE:{'✓' if d['has_data'] else '✗'}" 
                              for d in result['details']]
                details = " ".join(dte_results)
            
            print(f"{date_str:<12} {spy_str:<10} {strike_str:<12} {has_data:<10} {details}")
            
            if result['has_data'] and (not earliest_with_data or test_date < earliest_with_data):
                earliest_with_data = test_date
        
        if earliest_with_data:
            print(f"\n✅ Earliest date with data: {earliest_with_data.strftime('%Y-%m-%d')}")
            
            # Now refine to find exact boundary
            print("\nRefining to find exact start date...")
            current = earliest_with_data
            
            # Go back 3 months at a time
            while True:
                test = current - timedelta(days=90)
                result = self.test_date(test)
                
                if result['has_data']:
                    print(f"  ✅ Data found at {test.strftime('%Y-%m-%d')}")
                    current = test
                    earliest_with_data = test
                else:
                    print(f"  ❌ No data at {test.strftime('%Y-%m-%d')}")
                    # Binary search between test and current
                    while (current - test).days > 7:
                        mid = test + (current - test) / 2
                        mid_result = self.test_date(mid)
                        
                        if mid_result['has_data']:
                            current = mid
                            earliest_with_data = mid
                            print(f"    ✅ Data at {mid.strftime('%Y-%m-%d')}")
                        else:
                            test = mid
                            print(f"    ❌ No data at {mid.strftime('%Y-%m-%d')}")
                    break
            
            print(f"\n🎯 Exact earliest date with 0-2 DTE data: {earliest_with_data.strftime('%Y-%m-%d')}")
            return earliest_with_data
        else:
            print("\n❌ No data found in any test dates!")
            return None

def main():
    finder = DTEDataFinder()
    earliest = finder.find_earliest_date()
    
    if earliest:
        print(f"\nRecommendation: Start downloading from {earliest.strftime('%B %Y')}")

if __name__ == "__main__":
    main()