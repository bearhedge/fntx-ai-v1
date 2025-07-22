#!/usr/bin/env python3
"""
Get non-adjusted SPY price using AlphaVantage API
This gives us the actual trading price, not dividend-adjusted
"""
import requests
import json
from datetime import datetime

def get_nonadjusted_spy_price(date: str, api_key: str = "1YWMUOJEEH1ILDFU"):
    """
    Get non-adjusted SPY price for a specific date
    
    Args:
        date: Date in YYYY-MM-DD format
        api_key: AlphaVantage API key
    
    Returns:
        dict with open, high, low, close prices
    """
    # AlphaVantage daily endpoint (non-adjusted)
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "SPY",
        "apikey": api_key,
        "outputsize": "full"  # Get more historical data
    }
    
    try:
        print(f"Fetching non-adjusted SPY data from AlphaVantage...")
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "Error Message" in data:
            print(f"API Error: {data['Error Message']}")
            return None
            
        if "Note" in data:
            print(f"API Note: {data['Note']}")
            return None
            
        # Get the time series data
        time_series = data.get("Time Series (Daily)", {})
        
        # Get data for specific date
        if date in time_series:
            day_data = time_series[date]
            result = {
                "date": date,
                "open": float(day_data["1. open"]),
                "high": float(day_data["2. high"]),
                "low": float(day_data["3. low"]),
                "close": float(day_data["4. close"]),
                "volume": int(day_data["5. volume"])
            }
            return result
        else:
            print(f"No data found for {date}")
            return None
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def compare_adjusted_vs_nonadjusted(date: str = "2023-01-03"):
    """Compare adjusted vs non-adjusted prices"""
    # Get non-adjusted from AlphaVantage
    nonadj = get_nonadjusted_spy_price(date)
    
    if nonadj:
        print(f"\n📊 SPY Prices for {date}:")
        print(f"\n🔴 Non-Adjusted (AlphaVantage - actual trading prices):")
        print(f"   Open:  ${nonadj['open']:.2f}")
        print(f"   High:  ${nonadj['high']:.2f}")
        print(f"   Low:   ${nonadj['low']:.2f}")
        print(f"   Close: ${nonadj['close']:.2f}")
        
        # Compare with Yahoo (adjusted)
        import yfinance as yf
        spy = yf.Ticker('SPY')
        yahoo_data = spy.history(start=date, end="2023-01-04")
        
        if not yahoo_data.empty:
            print(f"\n🔵 Adjusted (Yahoo Finance - dividend adjusted):")
            print(f"   Open:  ${yahoo_data['Open'].iloc[0]:.2f}")
            print(f"   High:  ${yahoo_data['High'].iloc[0]:.2f}")
            print(f"   Low:   ${yahoo_data['Low'].iloc[0]:.2f}")
            print(f"   Close: ${yahoo_data['Close'].iloc[0]:.2f}")
            
            # Calculate difference
            diff = nonadj['open'] - yahoo_data['Open'].iloc[0]
            print(f"\n📏 Difference: ${diff:.2f} ({diff/nonadj['open']*100:.1f}%)")
            print(f"\n💡 This explains why ATM strike calculations differ!")
            
            # Show correct ATM
            print(f"\n🎯 Correct ATM strike calculation:")
            print(f"   Non-adjusted open: ${nonadj['open']:.2f}")
            print(f"   Nearest strike: ${round(nonadj['open'])}")
            
        return nonadj
    
    return None

if __name__ == "__main__":
    # Test with Jan 3, 2023
    result = compare_adjusted_vs_nonadjusted("2023-01-03")
    
    if result:
        print(f"\n✅ Non-adjusted data retrieved successfully")
        print(f"   Use ${result['open']:.2f} for ATM calculations")
    else:
        print("\n❌ Failed to retrieve non-adjusted data")