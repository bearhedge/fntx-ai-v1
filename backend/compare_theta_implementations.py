#!/usr/bin/env python3
"""
Compare original vs improved ThetaTerminal implementations
Shows the difference in data quality
"""
import requests
import json
from datetime import datetime

def compare_implementations():
    """Compare the original hardcoded values vs real data"""
    
    print("=" * 80)
    print("COMPARISON: Original vs Improved ThetaTerminal Implementation")
    print("=" * 80)
    print()
    
    # Test parameters
    strike = 605
    
    # 1. Call the original endpoint
    print("1. ORIGINAL IMPLEMENTATION (hardcoded values):")
    print("-" * 50)
    try:
        orig_resp = requests.get(f"http://localhost:8000/api/options/spy-atm?num_strikes=1")
        if orig_resp.status_code == 200:
            orig_data = orig_resp.json()
            if orig_data.get('contracts'):
                for contract in orig_data['contracts']:
                    if contract['strike'] == strike:
                        print(f"Contract: {contract['symbol']}")
                        print(f"  Volume: {contract['volume']} (HARDCODED TO 0)")
                        print(f"  Open Interest: {contract['open_interest']} (HARDCODED TO 0)")
                        print(f"  Implied Volatility: {contract['implied_volatility']} (HARDCODED TO 0.20)")
                        print()
    except Exception as e:
        print(f"Error calling original endpoint: {e}")
    
    # 2. Show what the improved implementation would return
    print("2. IMPROVED IMPLEMENTATION (real data from ThetaTerminal):")
    print("-" * 50)
    
    # Simulate improved endpoint results by calling ThetaTerminal directly
    exp = datetime.now().strftime('%Y%m%d')
    
    # Get CALL data
    print(f"SPY {exp} {strike} CALL:")
    
    # Get volume from OHLC
    ohlc_url = f"http://localhost:25510/v2/snapshot/option/ohlc?root=SPY&exp={exp}&strike={strike}000&right=C"
    ohlc_resp = requests.get(ohlc_url)
    if ohlc_resp.status_code == 200:
        data = ohlc_resp.json()
        if data.get('response'):
            ohlc = data['response'][0]
            volume = ohlc[5]
            print(f"  Volume: {volume:,} (REAL DATA FROM OHLC ENDPOINT)")
    
    # Get open interest
    oi_url = f"http://localhost:25510/v2/snapshot/option/open_interest?root=SPY&exp={exp}&strike={strike}000&right=C"
    oi_resp = requests.get(oi_url)
    if oi_resp.status_code == 200:
        data = oi_resp.json()
        if data.get('response'):
            oi = data['response'][0]
            open_interest = oi[1]
            print(f"  Open Interest: {open_interest:,} (REAL DATA FROM OI ENDPOINT)")
    
    print(f"  Implied Volatility: None (NOT AVAILABLE FROM THETATERMINAL)")
    print()
    
    # 3. Summary
    print("=" * 80)
    print("SUMMARY OF FINDINGS:")
    print("=" * 80)
    print()
    print("ISSUE #1: Volume is always 0")
    print("  - CAUSE: Code tries to access quote[10] which doesn't exist")
    print("  - SOLUTION: Use /v2/snapshot/option/ohlc endpoint, field index 5")
    print()
    print("ISSUE #2: Open Interest is always 0")
    print("  - CAUSE: Hardcoded to 0 in the code")
    print("  - SOLUTION: Use /v2/snapshot/option/open_interest endpoint, field index 1")
    print()
    print("ISSUE #3: Implied Volatility is hardcoded to 0.20 (20%)")
    print("  - CAUSE: ThetaTerminal HTTP API doesn't provide IV or Greeks")
    print("  - SOLUTION: Either calculate IV using Black-Scholes or clearly indicate 'N/A'")
    print()
    print("RECOMMENDATION:")
    print("Replace theta_options_endpoint.py with the improved version that properly")
    print("fetches volume and open interest from the correct endpoints.")

if __name__ == "__main__":
    compare_implementations()