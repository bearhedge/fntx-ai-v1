#!/usr/bin/env python3
"""Test price fetching from AlphaVantage vs Yahoo"""
from datetime import datetime
from download_day_strikes import StrikeAwareDailyDownloader

# Create downloader instance
downloader = StrikeAwareDailyDownloader()

# Test date
test_date = datetime(2023, 1, 3)

print("Testing get_spy_open_price method...")
price = downloader.get_spy_open_price(test_date)

if price:
    print(f"\nResult: ${price:.2f}")
    
    # Check if it's non-adjusted
    if price > 380:
        print("✅ This appears to be non-adjusted (correct)")
    else:
        print("❌ This appears to be adjusted (incorrect)")
else:
    print("❌ Failed to get price")