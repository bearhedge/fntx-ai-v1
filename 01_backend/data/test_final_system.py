#!/usr/bin/env python3
"""Test the final system with non-adjusted prices and volume filtering"""
from download_day_strikes import StrikeAwareDailyDownloader
from datetime import datetime

# Create downloader with smart selection
downloader = StrikeAwareDailyDownloader(use_smart_selection=True)

# For testing, reduce the smart selector parameters to download fewer strikes
downloader.smart_selector.sigma_multiplier = 1.5  # Reduce from 2.5
downloader.smart_selector.min_range_pct = 0.01    # Reduce from 0.015

# Test date
test_date = datetime(2023, 1, 3)

print("🧪 Testing final system configuration:")
print("   - Non-adjusted prices from Yahoo Finance")
print("   - 60-bar volume filtering (5 hours)")
print("   - Smart strike selection around correct ATM")
print("\nStarting limited test download...\n")

# Get SPY price first
spy_price = downloader.get_spy_open_price(test_date)
if spy_price:
    print(f"✅ Got non-adjusted price: ${spy_price:.2f}")
    atm = round(spy_price)
    print(f"   ATM strike: ${atm}")
else:
    print("❌ Failed to get SPY price")
    exit(1)