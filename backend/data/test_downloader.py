#!/usr/bin/env python3
"""
Test the ThetaTerminal downloader with a small date range
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from theta_downloader import ThetaDownloader
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_download():
    """Test download with one week of data"""
    downloader = ThetaDownloader()
    
    try:
        # Test with one week in June 2024
        print("Testing download for one week of SPY options data...")
        downloader.download_date_range('20240603', '20240607')
        
        # Check what was downloaded
        cursor = downloader.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as total_records,
                   COUNT(DISTINCT contract_id) as unique_contracts,
                   MIN(datetime) as earliest_data,
                   MAX(datetime) as latest_data
            FROM theta.options_ohlc
        """)
        
        result = cursor.fetchone()
        print(f"\nDatabase contents:")
        print(f"Total records: {result[0]:,}")
        print(f"Unique contracts: {result[1]:,}")
        print(f"Date range: {result[2]} to {result[3]}")
        
        cursor.close()
        
    finally:
        downloader.close()

if __name__ == "__main__":
    test_download()