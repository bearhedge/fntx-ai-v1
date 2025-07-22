#!/usr/bin/env python3
"""
Import Historical IBKR FlexQuery Data
Import all locally downloaded XML files to establish baseline track record
"""
import os
import sys
import logging
from datetime import datetime
import glob
import psycopg2
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flexquery_parser import FlexQueryParser
from db_importer import FlexQueryDBImporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_import_type_from_filename(filename: str) -> str:
    """Determine import type from filename"""
    mapping = {
        'NAV_(1244257)_MTD.xml': 'NAV_MTD',
        'NAV_(1257542)_LBD.xml': 'NAV_LBD',
        'Trades_(1257686)_MTD.xml': 'TRADES_MTD',
        'Trades_(1257690)_LBD.xml': 'TRADES_LBD',
        'Exercises_and_Expiries_(1257675)_MTD.xml': 'EXERCISES_EXPIRIES_MTD',
        'Exercises_and_Expiries_(1257679)_LBD.xml': 'EXERCISES_EXPIRIES_LBD',
        'Open_Positions_(1257695)_LBD.xml': 'OPEN_POSITIONS_LBD',
        'Cash_Transactions_(1257703)_MTD.xml': 'CASH_TRANSACTIONS_MTD',
        'Cash_Transactions_(1257704)_LBD.xml': 'CASH_TRANSACTIONS_LBD',
        'Interest_Accruals_(1257707)_MTD.xml': 'INTEREST_ACCRUALS_MTD',
        'Interest_Accruals_(1257708)_LBD.xml': 'INTEREST_ACCRUALS_LBD'
    }
    return mapping.get(filename, 'UNKNOWN')


def import_historical_files(data_dir: str, connection_string: str) -> Dict[str, List[Dict]]:
    """Import all XML files from data directory"""
    logger.info("="*60)
    logger.info("Starting Historical Data Import")
    logger.info("="*60)
    
    # Initialize importer
    importer = FlexQueryDBImporter(connection_string)
    
    # Find all XML files
    xml_files = sorted(glob.glob(os.path.join(data_dir, "*.xml")))
    logger.info(f"Found {len(xml_files)} XML files to import")
    
    results = {
        'successful': [],
        'failed': [],
        'skipped': []
    }
    
    # Process each file
    for xml_path in xml_files:
        filename = os.path.basename(xml_path)
        import_type = get_import_type_from_filename(filename)
        
        if import_type == 'UNKNOWN':
            logger.warning(f"Skipping unknown file: {filename}")
            results['skipped'].append({
                'file': filename,
                'reason': 'Unknown import type'
            })
            continue
        
        logger.info(f"\nImporting {filename} as {import_type}...")
        
        try:
            # Import the file
            import_result = importer.import_flexquery_file(xml_path, import_type)
            
            if import_result['status'] == 'COMPLETED':
                logger.info(f"✓ Successfully imported {filename}")
                logger.info(f"  Records: {import_result.get('results', {})}")
                results['successful'].append({
                    'file': filename,
                    'import_type': import_type,
                    'records': import_result.get('results', {})
                })
            else:
                logger.error(f"✗ Failed to import {filename}: {import_result.get('error')}")
                results['failed'].append({
                    'file': filename,
                    'import_type': import_type,
                    'error': import_result.get('error')
                })
                
        except Exception as e:
            logger.error(f"✗ Exception importing {filename}: {str(e)}")
            results['failed'].append({
                'file': filename,
                'import_type': import_type,
                'error': str(e)
            })
    
    return results


def verify_import_data(connection_string: str):
    """Verify imported data in database"""
    logger.info("\n" + "-"*60)
    logger.info("Verifying Imported Data")
    logger.info("-"*60)
    
    try:
        conn = psycopg2.connect(connection_string)
        
        with conn.cursor() as cursor:
            # Check NAV snapshots
            cursor.execute("""
                SELECT COUNT(*), MIN(snapshot_date), MAX(snapshot_date)
                FROM portfolio.nav_snapshots
            """)
            nav_count, min_date, max_date = cursor.fetchone()
            logger.info(f"\nNAV Snapshots:")
            logger.info(f"  Count: {nav_count}")
            logger.info(f"  Date range: {min_date} to {max_date}")
            
            # Check trades
            cursor.execute("""
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date)
                FROM trading.trades
            """)
            trade_count, min_trade_date, max_trade_date = cursor.fetchone()
            logger.info(f"\nTrades:")
            logger.info(f"  Count: {trade_count}")
            logger.info(f"  Date range: {min_trade_date} to {max_trade_date}")
            
            # Check positions
            cursor.execute("""
                SELECT COUNT(*), COUNT(DISTINCT symbol), COUNT(DISTINCT snapshot_date)
                FROM portfolio.open_positions
            """)
            pos_count, symbol_count, date_count = cursor.fetchone()
            logger.info(f"\nOpen Positions:")
            logger.info(f"  Total records: {pos_count}")
            logger.info(f"  Unique symbols: {symbol_count}")
            logger.info(f"  Snapshot dates: {date_count}")
            
            # Check cash transactions
            cursor.execute("""
                SELECT COUNT(*), SUM(amount) as total_amount
                FROM portfolio.cash_transactions
            """)
            cash_count, total_amount = cursor.fetchone()
            logger.info(f"\nCash Transactions:")
            logger.info(f"  Count: {cash_count}")
            logger.info(f"  Total amount: ${total_amount:,.2f}" if total_amount else "  Total amount: $0.00")
            
            # Check exercises and expiries
            cursor.execute("""
                SELECT COUNT(*), COUNT(DISTINCT symbol)
                FROM portfolio.exercises_and_expiries
            """)
            ex_count, ex_symbols = cursor.fetchone()
            logger.info(f"\nExercises & Expiries:")
            logger.info(f"  Count: {ex_count}")
            logger.info(f"  Unique symbols: {ex_symbols}")
            
        conn.close()
        
    except Exception as e:
        logger.error(f"Error verifying data: {e}")


def print_summary(results: Dict[str, List[Dict]]):
    """Print import summary"""
    logger.info("\n" + "="*60)
    logger.info("Import Summary")
    logger.info("="*60)
    
    logger.info(f"\n✓ Successful imports: {len(results['successful'])}")
    for item in results['successful']:
        logger.info(f"   - {item['file']}: {item['records']}")
    
    if results['failed']:
        logger.info(f"\n✗ Failed imports: {len(results['failed'])}")
        for item in results['failed']:
            logger.info(f"   - {item['file']}: {item['error']}")
    
    if results['skipped']:
        logger.info(f"\n⚠️  Skipped files: {len(results['skipped'])}")
        for item in results['skipped']:
            logger.info(f"   - {item['file']}: {item['reason']}")


def main():
    """Main entry point"""
    # Configuration
    data_dir = "/home/info/fntx-ai-v1/04_data"
    
    # Get database connection from environment or use default
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "options_data")
    db_user = os.getenv("DB_USER", "info")
    db_password = os.getenv("DB_PASSWORD", "")
    
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Database: {db_name} on {db_host}:{db_port}")
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Import historical files
    results = import_historical_files(data_dir, connection_string)
    
    # Verify imported data
    verify_import_data(connection_string)
    
    # Print summary
    print_summary(results)
    
    logger.info(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("\nNext steps:")
    logger.info("1. Review any failed imports")
    logger.info("2. Run ALM reconciliation calculations")
    logger.info("3. Set up automated daily imports")


if __name__ == "__main__":
    main()