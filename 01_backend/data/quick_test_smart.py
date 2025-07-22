#!/usr/bin/env python3
"""
Quick test of smart strike selection with limited strikes
"""
from download_day_strikes import StrikeAwareDailyDownloader
from datetime import datetime

def quick_test():
    """Test smart selection with just a couple strikes"""
    # Create downloader with smart selection
    downloader = StrikeAwareDailyDownloader(use_smart_selection=True)
    
    # Temporarily reduce the liquidity cascade to test faster
    downloader.smart_selector.dead_zone_strikes = 1  # Stop after 1 illiquid strike
    
    # Test date
    test_date = datetime(2023, 1, 3)
    
    print("Quick test of smart strike selection...")
    print("(Limited strikes for fast testing)")
    print()
    
    # Run download
    result = downloader.download_day(test_date)
    
    if result['status'] == 'complete':
        print("\n✓ Test successful!")
        print(f"Downloaded {result['stats']['total_contracts']} contracts")
        print(f"Coverage: {result['stats'].get('coverage', 0):.1f}%")
    else:
        print("\n✗ Test failed!")
        print(f"Status: {result['status']}")
        if result.get('errors'):
            print(f"Errors: {result['errors']}")

if __name__ == "__main__":
    quick_test()