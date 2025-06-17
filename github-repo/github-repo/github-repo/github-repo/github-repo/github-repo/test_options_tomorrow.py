#!/usr/bin/env python3
"""
Test options chain with tomorrow's expiration
"""
import sys
import os
from datetime import datetime, timedelta, date

# Add backend to path
sys.path.append('/Users/jimmyhou/CascadeProjects/fntx-ai-v10/backend')

from services.ibkr_singleton_service import ibkr_singleton

def test_tomorrow_options():
    """Test getting options chain for tomorrow's expiration"""
    print("Testing SPY options chain for tomorrow's expiration...")
    
    # Calculate tomorrow's date
    tomorrow = date.today() + timedelta(days=1)
    expiration = tomorrow.strftime('%Y%m%d')
    
    print(f"Using expiration date: {expiration}")
    
    # Get options chain
    options = ibkr_singleton.get_spy_options_chain(expiration=expiration, max_strikes=6)
    
    print(f"\nFound {len(options)} option contracts:")
    
    for option in options[:10]:  # Show first 10
        print(f"  {option['strike']}{option['right']}: bid=${option['bid']:.2f} ask=${option['ask']:.2f} last=${option['last']:.2f}")
    
    # Show summary
    non_zero_prices = [opt for opt in options if opt['bid'] > 0 or opt['ask'] > 0 or opt['last'] > 0]
    print(f"\nContracts with non-zero prices: {len(non_zero_prices)}/{len(options)}")
    
    return options

if __name__ == "__main__":
    try:
        options = test_tomorrow_options()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()