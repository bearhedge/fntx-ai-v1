#!/usr/bin/env python3
"""
Consolidated data management tool for ThetaData operations.
Replaces multiple single-purpose scripts with a unified interface.
"""
import argparse
import logging
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.theta_downloader import ThetaDataDownloader
from database.postgres_client import PostgresClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataManager:
    """Unified data management for ThetaData operations"""
    
    def __init__(self):
        self.downloader = ThetaDataDownloader()
        self.db = PostgresClient()
    
    def download_data(self, data_type='all', start_date=None, end_date=None, symbol='SPY'):
        """Download data based on specified parameters"""
        if not start_date:
            start_date = datetime.now().date()
        if not end_date:
            end_date = start_date
            
        logger.info(f"Downloading {data_type} data for {symbol} from {start_date} to {end_date}")
        
        if data_type in ['all', 'ohlc']:
            self.downloader.download_date_range(start_date, end_date)
            
        if data_type in ['all', 'greeks', 'iv']:
            # Download Greeks/IV for existing contracts
            self._backfill_greeks_iv(start_date, end_date, symbol)
    
    def backfill_missing(self, data_type='greeks', symbol='SPY'):
        """Backfill missing data for existing contracts"""
        logger.info(f"Backfilling missing {data_type} data for {symbol}")
        
        if data_type == 'greeks':
            query = """
                SELECT DISTINCT root, exp, strike, right
                FROM spy_options_ohlc
                WHERE (delta IS NULL OR gamma IS NULL OR theta IS NULL OR vega IS NULL)
                AND root = %s
                ORDER BY exp, strike, right
            """
            contracts = self.db.fetch_all(query, (symbol,))
            
            for contract in contracts:
                try:
                    # Implement Greeks download logic here
                    logger.info(f"Backfilling Greeks for {contract}")
                    # Call appropriate downloader method
                except Exception as e:
                    logger.error(f"Error backfilling {contract}: {e}")
    
    def _backfill_greeks_iv(self, start_date, end_date, symbol):
        """Internal method to backfill Greeks and IV data"""
        # Implementation based on backfill_greeks_iv.py logic
        pass
    
    def monitor_status(self):
        """Monitor data download status"""
        query = """
            SELECT 
                COUNT(*) as total_contracts,
                COUNT(CASE WHEN delta IS NOT NULL THEN 1 END) as with_greeks,
                COUNT(CASE WHEN implied_volatility IS NOT NULL THEN 1 END) as with_iv,
                MIN(quote_date) as earliest_date,
                MAX(quote_date) as latest_date
            FROM spy_options_ohlc
        """
        result = self.db.fetch_one(query)
        
        logger.info("Data Status:")
        logger.info(f"  Total contracts: {result[0]}")
        logger.info(f"  With Greeks: {result[1]} ({result[1]/result[0]*100:.1f}%)")
        logger.info(f"  With IV: {result[2]} ({result[2]/result[0]*100:.1f}%)")
        logger.info(f"  Date range: {result[3]} to {result[4]}")
        
        return result


def main():
    parser = argparse.ArgumentParser(description='ThetaData Management Tool')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download data')
    download_parser.add_argument('--type', choices=['all', 'ohlc', 'greeks', 'iv'], 
                                default='all', help='Type of data to download')
    download_parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    download_parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    download_parser.add_argument('--symbol', default='SPY', help='Symbol to download')
    
    # Backfill command
    backfill_parser = subparsers.add_parser('backfill', help='Backfill missing data')
    backfill_parser.add_argument('--type', choices=['greeks', 'iv'], 
                                default='greeks', help='Type of data to backfill')
    backfill_parser.add_argument('--symbol', default='SPY', help='Symbol to backfill')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show data status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = DataManager()
    
    if args.command == 'download':
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date() if args.start_date else None
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date() if args.end_date else None
        manager.download_data(args.type, start_date, end_date, args.symbol)
        
    elif args.command == 'backfill':
        manager.backfill_missing(args.type, args.symbol)
        
    elif args.command == 'status':
        manager.monitor_status()


if __name__ == '__main__':
    main()