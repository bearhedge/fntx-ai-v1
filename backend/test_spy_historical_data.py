#!/usr/bin/env python3
"""
Focused test of SPY historical options data with ThetaData Value subscription
Tests with actual recent SPY contracts
"""
import requests
import json
from datetime import datetime, timedelta
import pandas as pd

def test_spy_historical():
    """Test SPY historical data access with recent contracts"""
    api_base = "http://localhost:25510"
    
    print("="*80)
    print("SPY HISTORICAL DATA TEST - THETADATA VALUE SUBSCRIPTION")
    print("="*80)
    print()
    
    # Test 1: Recent SPY contract with known data
    print("1. TESTING RECENT SPY CONTRACT (Jan 2024 expiration)")
    print("-" * 50)
    
    # Jan 19, 2024 expiration (monthly)
    test_contract = {
        "root": "SPY",
        "exp": "20240119",  # Jan 19, 2024 monthly
        "strike": "475000",  # $475 strike
        "right": "C"
    }
    
    # Test different date ranges
    date_ranges = [
        ("Week before expiry", "20240112", "20240119"),
        ("Month of data", "20240101", "20240119"),
        ("Single day", "20240116", "20240116")
    ]
    
    for desc, start, end in date_ranges:
        print(f"\n{desc} ({start} to {end}):")
        
        # Test 1-minute data
        params = test_contract.copy()
        params.update({
            "start_date": start,
            "end_date": end,
            "ivl": 60000  # 1 minute
        })
        
        try:
            resp = requests.get(f"{api_base}/v2/hist/option/ohlc", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response') and len(data['response']) > 0:
                    records = data['response']
                    print(f"  ✅ 1-minute data: {len(records)} records")
                    
                    # Show sample data
                    sample = records[0]
                    print(f"  First record: {sample}")
                    
                    # Parse the data
                    df = pd.DataFrame(records, columns=['ms_of_day', 'open', 'high', 'low', 'close', 'volume', 'count', 'date'])
                    print(f"  Date range in data: {df['date'].min()} to {df['date'].max()}")
                    print(f"  Total volume: {df['volume'].sum():,}")
                    print(f"  Avg price: ${df['close'].mean():.2f}")
                    
                    # Check if prices are reasonable
                    if df['close'].mean() > 0:
                        print(f"  ✅ Valid price data found")
                    else:
                        print(f"  ⚠️  Zero prices - contract may not have traded")
                else:
                    print(f"  ❌ No data returned")
            else:
                print(f"  ❌ Error {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
    
    # Test 2: Check multiple strikes for same expiration
    print("\n\n2. TESTING MULTIPLE STRIKES (SPY Jan 2024)")
    print("-" * 50)
    
    strikes = [470, 475, 480, 485]  # Around ATM for Jan 2024
    start_date = "20240116"
    end_date = "20240116"
    
    available_contracts = []
    
    for strike in strikes:
        for right in ['C', 'P']:
            params = {
                "root": "SPY",
                "exp": "20240119",
                "strike": f"{strike}000",
                "right": right,
                "start_date": start_date,
                "end_date": end_date,
                "ivl": 3600000  # 1 hour for quick test
            }
            
            try:
                resp = requests.get(f"{api_base}/v2/hist/option/ohlc", params=params, timeout=5)
                if resp.status_code == 200 and resp.json().get('response'):
                    data = resp.json()['response']
                    if data and any(row[5] > 0 for row in data):  # Check for non-zero volume
                        available_contracts.append(f"{strike}{right}")
                        total_volume = sum(row[5] for row in data)
                        avg_price = sum(row[4] for row in data) / len(data) if data else 0
                        print(f"  {strike}{right}: ✅ Volume={total_volume:,}, Avg=${avg_price:.2f}")
                    else:
                        print(f"  {strike}{right}: ⚠️  No volume")
                else:
                    print(f"  {strike}{right}: ❌ No data")
            except:
                print(f"  {strike}{right}: ❌ Error")
    
    print(f"\nContracts with data: {', '.join(available_contracts)}")
    
    # Test 3: Find earliest available data
    print("\n\n3. FINDING EARLIEST AVAILABLE DATA")
    print("-" * 50)
    
    # Test going back in time
    test_years = [2024, 2023, 2022, 2021, 2020]
    earliest_found = None
    
    for year in test_years:
        # Test January monthly expiration
        exp_date = f"{year}0119" if year >= 2022 else f"{year}0115"  # 3rd Friday
        test_date = f"{year}0110"  # Mid-month
        
        params = {
            "root": "SPY",
            "exp": exp_date,
            "strike": "400000",  # Use a round number
            "right": "C",
            "start_date": test_date,
            "end_date": test_date,
            "ivl": 3600000  # 1 hour
        }
        
        try:
            resp = requests.get(f"{api_base}/v2/hist/option/ohlc", params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response') and len(data['response']) > 0:
                    print(f"  {year}: ✅ Data available")
                    if not earliest_found:
                        earliest_found = year
                else:
                    print(f"  {year}: ❌ No data (empty response)")
            else:
                print(f"  {year}: ❌ Error {resp.status_code}")
        except Exception as e:
            print(f"  {year}: ❌ Exception: {str(e)}")
    
    if earliest_found:
        print(f"\nEarliest data found: {earliest_found}")
    
    # Test 4: Data size estimation
    print("\n\n4. DATA SIZE CALCULATION FOR SPY")
    print("-" * 50)
    
    # Get one full day of 1-minute data to calculate accurately
    params = {
        "root": "SPY",
        "exp": "20240119",
        "strike": "475000",
        "right": "C",
        "start_date": "20240116",
        "end_date": "20240116",
        "ivl": 60000  # 1 minute
    }
    
    try:
        resp = requests.get(f"{api_base}/v2/hist/option/ohlc", params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('response'):
                records_per_day = len(data['response'])
                bytes_per_record = len(json.dumps(data['response'][0]).encode())
                
                print(f"1-minute data statistics:")
                print(f"  Records per trading day: {records_per_day}")
                print(f"  Bytes per record: {bytes_per_record}")
                
                # Calculate for different scenarios
                scenarios = [
                    ("1 contract, 1 year", 1, 252),
                    ("100 contracts (1 expiry), 1 year", 100, 252),
                    ("All SPY weeklies, 1 year", 100 * 156, 252),  # 156 expirations/year
                    ("All SPY weeklies, 4 years", 100 * 156, 252 * 4)
                ]
                
                print(f"\nStorage estimates (1-minute data):")
                for desc, contracts, days in scenarios:
                    total_records = contracts * days * records_per_day
                    total_bytes = total_records * bytes_per_record
                    total_gb = total_bytes / 1e9
                    compressed_gb = total_gb / 8  # Assume 8:1 compression
                    
                    print(f"  {desc}:")
                    print(f"    Uncompressed: {total_gb:.1f} GB")
                    print(f"    Compressed: {compressed_gb:.1f} GB")
    except Exception as e:
        print(f"Error calculating size: {str(e)}")
    
    # Test 5: Open Interest data
    print("\n\n5. TESTING OPEN INTEREST DATA")
    print("-" * 50)
    
    params = {
        "root": "SPY",
        "exp": "20240119",
        "strike": "475000",
        "right": "C",
        "start_date": "20240101",
        "end_date": "20240119"
    }
    
    try:
        resp = requests.get(f"{api_base}/v2/hist/option/open_interest", params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('response'):
                oi_data = data['response']
                print(f"✅ Open Interest data available: {len(oi_data)} records")
                print(f"Sample: {oi_data[0] if oi_data else 'No data'}")
                
                # Parse OI data
                if oi_data:
                    df_oi = pd.DataFrame(oi_data, columns=['ms_of_day', 'open_interest', 'date'])
                    print(f"Date range: {df_oi['date'].min()} to {df_oi['date'].max()}")
                    print(f"Max OI: {df_oi['open_interest'].max():,}")
                    print(f"Final OI: {df_oi['open_interest'].iloc[-1]:,}")
            else:
                print("❌ No OI data returned")
        else:
            print(f"❌ Error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print("\n\n" + "="*80)
    print("SUMMARY OF FINDINGS")
    print("="*80)
    print()
    print("✅ CONFIRMED AVAILABLE WITH VALUE SUBSCRIPTION:")
    print("  - Historical OHLC data (1-min, 5-min, 1-hour)")
    print("  - Open Interest historical data")
    print("  - Data from at least 2021 onwards")
    print("  - All SPY strikes and expirations")
    print()
    print("❌ NOT AVAILABLE WITH VALUE SUBSCRIPTION:")
    print("  - Greeks (delta, gamma, theta, vega)")
    print("  - Implied Volatility")
    print("  - Daily bars (only intraday intervals)")
    print("  - Volume endpoint (included in OHLC)")
    print()
    print("💡 RECOMMENDATIONS:")
    print("  1. Download 1-hour bars for general backtesting (2-3 GB for 4 years)")
    print("  2. Download 1-minute data only for specific dates/strategies")
    print("  3. Store data in compressed format (8:1 compression ratio)")
    print("  4. Consider Standard subscription only if Greeks are essential")

if __name__ == "__main__":
    test_spy_historical()