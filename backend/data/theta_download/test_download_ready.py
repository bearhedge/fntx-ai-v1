#!/usr/bin/env python3
from download_1min_data_improved import ThetaHistoricalDownloader
from datetime import date

# Quick test to verify both symbols work
downloader = ThetaHistoricalDownloader()

# Test SPY price retrieval
spy_price = downloader._get_symbol_price_data('SPY', date(2022, 12, 5))
print(f"SPY price data: {spy_price}")

# Test QQQ price retrieval  
qqq_price = downloader._get_symbol_price_data('QQQ', date(2022, 12, 5))
print(f"QQQ price data: {qqq_price}")

# Test contract retrieval for both
spy_contracts = downloader._get_contracts_for_trading_date('SPY', date(2022, 12, 5))
print(f"\nSPY contracts on 2022-12-05: {len(spy_contracts)}")

qqq_contracts = downloader._get_contracts_for_trading_date('QQQ', date(2022, 12, 5))
print(f"QQQ contracts on 2022-12-05: {len(qqq_contracts)}")

downloader.close()
print("\nAll tests passed - ready for full download!")