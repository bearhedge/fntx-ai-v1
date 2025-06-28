#!/usr/bin/env python3
"""
Get PROPER SPY option chain - multiple expirations and strikes
"""
import requests
from datetime import datetime, timedelta

HTTP_API = "http://localhost:25510"

def get_expirations(symbol):
    """Get all available expiration dates"""
    url = f"{HTTP_API}/v2/list/expirations"
    params = {"root": symbol}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'response' in data:
                return data['response']
    except Exception as e:
        print(f"Error getting expirations: {e}")
    return []

def get_strikes(symbol, exp):
    """Get all strikes for an expiration"""
    url = f"{HTTP_API}/v2/list/strikes"
    params = {
        "root": symbol,
        "exp": exp
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'response' in data:
                return [s/1000 for s in data['response']]  # Convert from 605000 to 605
    except Exception as e:
        print(f"Error getting strikes: {e}")
    return []

def get_option_quote(symbol, exp, strike, right):
    """Get option quote"""
    url = f"{HTTP_API}/v2/snapshot/option/quote"
    params = {
        "root": symbol,
        "exp": exp,
        "strike": int(strike * 1000),
        "right": right
    }
    
    try:
        response = requests.get(url, params=params, timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data and 'response' in data and len(data['response']) > 0:
                quote = data['response'][0]
                return {
                    'bid': quote[3],
                    'ask': quote[7],
                    'bid_size': quote[1],
                    'ask_size': quote[5]
                }
    except:
        pass
    return {'bid': 0, 'ask': 0, 'bid_size': 0, 'ask_size': 0}

def main():
    print("\nSPY OPTION CHAIN - MULTIPLE EXPIRATIONS")
    print("=" * 150)
    
    # Get expirations
    expirations = get_expirations("SPY")
    if not expirations:
        print("Could not get expirations")
        return
    
    # Get next 5 expirations
    exps_to_show = expirations[:5]
    
    # For each expiration, show strikes around current price (600-610)
    for exp in exps_to_show:
        exp_date = datetime.strptime(str(exp), '%Y%m%d').strftime('%b %d, %Y')
        days_to_exp = (datetime.strptime(str(exp), '%Y%m%d') - datetime.now()).days
        
        print(f"\nEXPIRATION: {exp_date} ({days_to_exp} days)")
        print("-" * 150)
        print(f"{'Strike':^8} | {'PUT':^50} | {'CALL':^50} | {'Straddle':^10}")
        print(f"{'':^8} | {'Bid':>10} {'Ask':>10} {'Mid':>10} {'Size':>18} | {'Bid':>10} {'Ask':>10} {'Mid':>10} {'Size':>18} | {'Mid':>10}")
        print("-" * 150)
        
        # Get strikes for this expiration
        all_strikes = get_strikes("SPY", exp)
        
        # Filter to 600-610 range
        strikes = [s for s in all_strikes if 600 <= s <= 610]
        
        for strike in strikes:
            # Get quotes
            put = get_option_quote("SPY", exp, strike, "P")
            call = get_option_quote("SPY", exp, strike, "C")
            
            put_mid = (put['bid'] + put['ask']) / 2 if put['ask'] > 0 else 0
            call_mid = (call['bid'] + call['ask']) / 2 if call['ask'] > 0 else 0
            straddle_mid = put_mid + call_mid
            
            # Mark today's positions
            marker = ""
            if exp == int(datetime.now().strftime('%Y%m%d')):
                if strike == 603:
                    marker = " <- YOUR PUT"
                elif strike == 608:
                    marker = " <- YOUR CALL"
            
            print(f"{strike:^8} | {put['bid']:>10.2f} {put['ask']:>10.2f} {put_mid:>10.2f} "
                  f"{put['bid_size']:>8}x{put['ask_size']:<8} | "
                  f"{call['bid']:>10.2f} {call['ask']:>10.2f} {call_mid:>10.2f} "
                  f"{call['bid_size']:>8}x{call['ask_size']:<8} | "
                  f"{straddle_mid:>10.2f}{marker}")
    
    print("\n" + "=" * 150)
    print("Data source: ThetaTerminal Live Feed")

if __name__ == "__main__":
    main()