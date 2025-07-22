#!/usr/bin/env python3
"""
Test script to examine raw IV data from ThetaData API
Diagnose why IV has gaps for liquid ITM options
"""
import requests
import json
from datetime import datetime

def test_iv_raw_response():
    """Get raw IV data for specific contract and examine structure"""
    base_url = "http://127.0.0.1:25510/v2/hist/option/implied_volatility"
    
    # Test with the problematic $385 put from Jan 3, 2023
    params = {
        'root': 'SPY',
        'exp': '20230103',
        'strike': 385000,  # $385 * 1000
        'right': 'P',
        'start_date': '20230103',
        'end_date': '20230103',
        'ivl': 300000  # 5 minutes
    }
    
    print("Testing IV data for SPY Jan 3 2023 $385 Put")
    print("=" * 60)
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Print raw response structure
            print(f"\nRaw response keys: {data.keys()}")
            
            if 'response' in data:
                iv_data = data['response']
                print(f"\nTotal IV data points: {len(iv_data)}")
                
                # Examine first few and problematic timeframes
                print("\nFirst 5 data points:")
                for i, point in enumerate(iv_data[:5]):
                    print(f"  {i}: {point}")
                
                # Find data around 11:10 AM (last good IV)
                print("\nData around 11:10-11:20 AM:")
                for point in iv_data:
                    # Convert ms_of_day to time
                    ms_of_day = point[0]
                    hours = ms_of_day // (1000 * 60 * 60)
                    minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
                    
                    if 11 <= hours < 12 and 0 <= minutes <= 30:
                        time_str = f"{hours:02d}:{minutes:02d}"
                        # For puts, IV is in field [2]
                        iv_value = point[2] if len(point) > 2 else None
                        print(f"  {time_str}: Raw IV = {iv_value}, Full point: {point}")
                
                # Check for None, 0, or negative values
                print("\nAnalyzing IV values:")
                none_count = 0
                zero_count = 0
                negative_count = 0
                valid_count = 0
                
                for point in iv_data:
                    iv_value = point[2] if len(point) > 2 else None
                    
                    if iv_value is None:
                        none_count += 1
                    elif iv_value == 0:
                        zero_count += 1
                    elif iv_value < 0:
                        negative_count += 1
                    else:
                        valid_count += 1
                
                print(f"  Valid IV values: {valid_count}")
                print(f"  None values: {none_count}")
                print(f"  Zero values: {zero_count}")
                print(f"  Negative values: {negative_count}")
                
        else:
            print(f"Error: API returned status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error testing IV data: {e}")

def test_multiple_strikes():
    """Test IV availability across multiple strikes"""
    base_url = "http://127.0.0.1:25510/v2/hist/option/implied_volatility"
    
    strikes = [380, 382, 384, 385, 386, 388, 390]
    
    print("\n\nIV Availability Across Strikes")
    print("=" * 60)
    
    for strike in strikes:
        for right in ['C', 'P']:
            params = {
                'root': 'SPY',
                'exp': '20230103',
                'strike': strike * 1000,
                'right': right,
                'start_date': '20230103',
                'end_date': '20230103',
                'ivl': 300000
            }
            
            try:
                response = requests.get(base_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    iv_points = data.get('response', [])
                    
                    # Count valid IVs
                    valid_ivs = 0
                    for point in iv_points:
                        iv_idx = 4 if right == 'C' else 2
                        if len(point) > iv_idx and point[iv_idx] and point[iv_idx] > 0:
                            valid_ivs += 1
                    
                    coverage = (valid_ivs / len(iv_points) * 100) if iv_points else 0
                    print(f"${strike}{right}: {valid_ivs}/{len(iv_points)} valid IVs ({coverage:.1f}% coverage)")
                    
            except Exception as e:
                print(f"${strike}{right}: Error - {e}")

if __name__ == "__main__":
    test_iv_raw_response()
    test_multiple_strikes()