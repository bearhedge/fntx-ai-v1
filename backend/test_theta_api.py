#!/usr/bin/env python3
"""
Test script to demonstrate ThetaTerminal API capabilities
and show actual data fields available
"""
import requests
import json
from datetime import datetime

THETA_HTTP_API = "http://localhost:25510"

def test_option_data():
    """Test all available option data endpoints"""
    
    # Test parameters
    root = "SPY"
    exp = "20250625"  # Today's date
    strike = "605000"
    right = "C"
    
    print("=" * 80)
    print("THETATERMINAL API TEST - SPY OPTIONS DATA")
    print("=" * 80)
    print(f"Testing for: {root} {exp} {int(strike)/1000:.0f} {right}")
    print()
    
    # 1. Option Quote (bid/ask)
    print("1. OPTION QUOTE DATA:")
    print("-" * 40)
    quote_url = f"{THETA_HTTP_API}/v2/snapshot/option/quote?root={root}&exp={exp}&strike={strike}&right={right}"
    quote_resp = requests.get(quote_url)
    if quote_resp.status_code == 200:
        data = quote_resp.json()
        print(f"Format: {data['header']['format']}")
        if data['response']:
            quote = data['response'][0]
            print(f"Raw data: {quote}")
            print(f"Bid: ${quote[3]:.2f} (Size: {quote[1]})")
            print(f"Ask: ${quote[7]:.2f} (Size: {quote[5]})")
            print(f"Mid: ${(quote[3] + quote[7])/2:.2f}")
            print(f"Date: {quote[9]}")
    print()
    
    # 2. Option OHLC (includes volume)
    print("2. OPTION OHLC DATA (includes VOLUME):")
    print("-" * 40)
    ohlc_url = f"{THETA_HTTP_API}/v2/snapshot/option/ohlc?root={root}&exp={exp}&strike={strike}&right={right}"
    ohlc_resp = requests.get(ohlc_url)
    if ohlc_resp.status_code == 200:
        data = ohlc_resp.json()
        print(f"Format: {data['header']['format']}")
        if data['response']:
            ohlc = data['response'][0]
            print(f"Raw data: {ohlc}")
            print(f"Open: ${ohlc[1]:.2f}")
            print(f"High: ${ohlc[2]:.2f}")
            print(f"Low: ${ohlc[3]:.2f}")
            print(f"Close: ${ohlc[4]:.2f}")
            print(f"Volume: {ohlc[5]:,}")  # This is the volume!
            print(f"Count: {ohlc[6]:,}")
            print(f"Date: {ohlc[7]}")
    print()
    
    # 3. Option Open Interest
    print("3. OPTION OPEN INTEREST DATA:")
    print("-" * 40)
    oi_url = f"{THETA_HTTP_API}/v2/snapshot/option/open_interest?root={root}&exp={exp}&strike={strike}&right={right}"
    oi_resp = requests.get(oi_url)
    if oi_resp.status_code == 200:
        data = oi_resp.json()
        print(f"Format: {data['header']['format']}")
        if data['response']:
            oi = data['response'][0]
            print(f"Raw data: {oi}")
            print(f"Open Interest: {oi[1]:,}")  # This is the open interest!
            print(f"Date: {oi[2]}")
    print()
    
    # 4. Check for Greeks/IV (not available)
    print("4. IMPLIED VOLATILITY / GREEKS:")
    print("-" * 40)
    greeks_url = f"{THETA_HTTP_API}/v2/snapshot/option/greeks?root={root}&exp={exp}&strike={strike}&right={right}"
    greeks_resp = requests.get(greeks_url)
    print(f"Greeks endpoint response: {greeks_resp.text}")
    
    iv_url = f"{THETA_HTTP_API}/v2/snapshot/option/implied_volatility?root={root}&exp={exp}&strike={strike}&right={right}"
    iv_resp = requests.get(iv_url)
    print(f"IV endpoint response: {iv_resp.text}")
    print("\nNOTE: Implied Volatility and Greeks are NOT available via ThetaTerminal HTTP API")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY OF AVAILABLE DATA:")
    print("=" * 80)
    print("✓ Bid/Ask prices and sizes - via /v2/snapshot/option/quote")
    print("✓ Volume - via /v2/snapshot/option/ohlc")
    print("✓ Open Interest - via /v2/snapshot/option/open_interest")
    print("✗ Implied Volatility - NOT AVAILABLE")
    print("✗ Greeks (Delta, Gamma, etc.) - NOT AVAILABLE")
    print()
    print("RECOMMENDATION: Update the code to fetch volume and open interest from")
    print("the appropriate endpoints instead of hardcoding to 0.")

if __name__ == "__main__":
    test_option_data()