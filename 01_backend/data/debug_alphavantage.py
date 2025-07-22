#!/usr/bin/env python3
"""Debug AlphaVantage API call"""
import requests
import json

url = "https://www.alphavantage.co/query"
params = {
    "function": "TIME_SERIES_DAILY",
    "symbol": "SPY",
    "apikey": "1YWMUOJEEH1ILDFU",
    "outputsize": "compact"
}

print("Making AlphaVantage API call...")
print(f"URL: {url}")
print(f"Params: {params}")

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"\nStatus code: {response.status_code}")
    
    data = response.json()
    
    # Check for errors
    if "Error Message" in data:
        print(f"❌ API Error: {data['Error Message']}")
    elif "Note" in data:
        print(f"⚠️  API Note: {data['Note']}")
        print("   (This usually means rate limit)")
    elif "Information" in data:
        print(f"ℹ️  API Info: {data['Information']}")
    elif "Time Series (Daily)" in data:
        print("✅ Success! Got time series data")
        
        ts = data["Time Series (Daily)"]
        dates = sorted(ts.keys())
        print(f"\nAvailable dates: {len(dates)} days")
        print(f"  First: {dates[0]}")
        print(f"  Last: {dates[-1]}")
        
        # Check if our date exists
        if "2023-01-03" in ts:
            day_data = ts["2023-01-03"]
            print(f"\n✅ Jan 3, 2023 data:")
            print(f"  Open: ${float(day_data['1. open']):.2f}")
            print(f"  High: ${float(day_data['2. high']):.2f}")
            print(f"  Low: ${float(day_data['3. low']):.2f}")
            print(f"  Close: ${float(day_data['4. close']):.2f}")
        else:
            print("\n❌ Jan 3, 2023 not found in data")
            print("   'compact' only returns last 100 days")
            print("   Need 'full' outputsize for historical data")
    else:
        print("❌ Unexpected response format")
        print(json.dumps(data, indent=2)[:500])
        
except Exception as e:
    print(f"❌ Exception: {type(e).__name__}: {e}")