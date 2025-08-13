#!/usr/bin/env python3
from download_1min_data_improved import ThetaHistoricalDownloader
from datetime import date
import logging

# Quick QQQ test - 2 days only
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

downloader = ThetaHistoricalDownloader()
try:
    # Just download 2 days of QQQ data from December 2022
    start = date(2022, 12, 5)
    end = date(2022, 12, 6)
    logger.info(f"Quick QQQ test: {start} to {end}")
    downloader.download_historical_data('QQQ', start, end)
finally:
    downloader.close()