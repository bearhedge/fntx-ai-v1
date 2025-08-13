#!/usr/bin/env python3
"""
ALM Automation System
Orchestrates the complete ALM reporting workflow:
1. Downloads reports from IBKR FlexQuery API
2. Manages files (keeps 3 most recent)
3. Parses and appends data to database
4. Runs calculation engine for daily narratives
"""

import os
import sys
import logging
import json
import shutil
from datetime import datetime, timedelta, date
from pathlib import Path
import xml.etree.ElementTree as ET
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ibkr_flex_query_enhanced import IBKRFlexQueryEnhanced
from calculation_engine_v1 import generate_daily_narrative
from spy_price_fetcher import get_spy_closing_price
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

DATA_BASE_DIR = "/home/info/fntx-ai-v1/database/ibkr/data"
ARCHIVE_DIR = "/home/info/fntx-ai-v1/database/ibkr/data/archive"
MAX_FILES_TO_KEEP = 3
DATABASE_URL = "postgresql://postgres:theta_data_2024@localhost:5432/options_data"

# FlexQuery configurations for different report types
FLEX_CONFIGS = {
    "NAV": {
        "query_id": "1244257",
        "file_pattern": "NAV_({query_id})_{period}.xml"
    },
    "Cash_Transactions": {
        "query_id": "1257703", 
        "file_pattern": "Cash_Transactions_({query_id})_{period}.xml"
    },
    "Trades": {
        "query_id": "1257686",
        "file_pattern": "Trades_({query_id})_{period}.xml"
    },
    "Exercises_and_Expiries": {
        "query_id": "1257675",
        "file_pattern": "Exercises_and_Expiries_({query_id})_{period}.xml"
    },
    "Interest_Accruals": {
        "query_id": "1257707",
        "file_pattern": "Interest_Accruals_({query_id})_{period}.xml"
    }
}

class ALMAutomation:
    """Main automation class for ALM reporting workflow"""
    
    def __init__(self):
        self.flex_service = IBKRFlexQueryEnhanced()
        self.ensure_directories()
        
    def ensure_directories(self):
        """Ensure required directories exist"""
        Path(DATA_BASE_DIR).mkdir(parents=True, exist_ok=True)
        Path(ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)
        
    def get_last_processed_date(self) -> date:
        """Get the last successfully processed date from backend.data.database"""
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(summary_date) 
                    FROM alm_reporting.daily_summary
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
                return date(2025, 7, 18)  # Default to last manual update
        finally:
            conn.close()
            
    def download_flex_reports(self, report_date: date, period: str = "MTD") -> dict:
        """Download all required FlexQuery reports for a given date"""
        downloaded_files = {}
        
        # Create month-specific directory
        month_dir = report_date.strftime("%B%Y")  # e.g., "July2025"
        data_dir = os.path.join(DATA_BASE_DIR, month_dir)
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        
        for report_type, config in FLEX_CONFIGS.items():
            logger.info(f"Downloading {report_type} report for {report_date}")
            
            # Set the appropriate query ID
            self.flex_service.query_id = config["query_id"]
            
            # Request the report
            reference_code = self.flex_service.request_flex_report()
            if not reference_code:
                logger.error(f"Failed to request {report_type} report")
                continue
                
            # Wait for report generation
            time.sleep(10)
            
            # Retrieve the report
            xml_data = self.flex_service.get_flex_report(reference_code)
            if not xml_data:
                logger.error(f"Failed to retrieve {report_type} report")
                continue
                
            # Save to file
            filename = config["file_pattern"].format(
                query_id=config["query_id"],
                period=period
            )
            file_path = os.path.join(data_dir, filename)
            
            # Save to temporary file first
            temp_path = file_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(xml_data)
                
            # Validate XML
            try:
                ET.parse(temp_path)
                shutil.move(temp_path, file_path)
                downloaded_files[report_type] = file_path
                logger.info(f"Successfully saved {report_type} report to {file_path}")
            except ET.ParseError as e:
                logger.error(f"Invalid XML for {report_type}: {e}")
                os.remove(temp_path)
                continue
                
        return downloaded_files
        
    def manage_file_rotation(self):
        """Keep only the most recent files, delete older ones"""
        # Get all month directories
        month_dirs = [d for d in os.listdir(DATA_BASE_DIR) 
                     if os.path.isdir(os.path.join(DATA_BASE_DIR, d)) 
                     and d not in ['archive', 'processed', 'raw', 'checkpoints']]
        
        for report_type, config in FLEX_CONFIGS.items():
            # Find all files matching this report type across all month directories
            pattern_prefix = config["file_pattern"].split("{")[0]
            matching_files = []
            
            for month_dir in month_dirs:
                dir_path = os.path.join(DATA_BASE_DIR, month_dir)
                for filename in os.listdir(dir_path):
                    if filename.startswith(pattern_prefix) and filename.endswith(".xml"):
                        file_path = os.path.join(dir_path, filename)
                        matching_files.append({
                            'path': file_path,
                            'mtime': os.path.getmtime(file_path),
                            'name': filename
                        })
                    
            # Sort by modification time (newest first)
            matching_files.sort(key=lambda x: x['mtime'], reverse=True)
            
            # Keep only the most recent files
            for i, file_info in enumerate(matching_files):
                if i < MAX_FILES_TO_KEEP:
                    logger.info(f"Keeping {file_info['name']}")
                else:
                    # Archive before deletion (optional)
                    archive_path = os.path.join(ARCHIVE_DIR, file_info['name'])
                    shutil.move(file_info['path'], archive_path)
                    logger.info(f"Archived {file_info['name']} to {archive_path}")
                    
    def prefetch_spy_price(self, target_date: date):
        """Pre-fetch SPY closing price for the target date"""
        try:
            spy_price = get_spy_closing_price(datetime.combine(target_date, datetime.min.time()))
            if spy_price:
                logger.info(f"Pre-fetched SPY closing price for {target_date}: ${spy_price:.2f}")
            else:
                logger.warning(f"Could not fetch SPY price for {target_date}")
        except Exception as e:
            logger.error(f"Error pre-fetching SPY price: {e}")

    def process_date_range(self, start_date: date, end_date: date):
        """Process a range of dates, skipping Sundays only"""
        current_date = start_date
        
        while current_date <= end_date:
            # Skip Sundays only (Monday=0, Sunday=6)
            if current_date.weekday() == 6:  # Sunday = 6
                logger.info(f"Skipping Sunday: {current_date}")
                current_date += timedelta(days=1)
                continue
                
            logger.info(f"Processing date: {current_date}")
            
            # Pre-fetch SPY price for ITM assumption logic
            self.prefetch_spy_price(current_date)
            
            try:
                # Download reports for this date
                downloaded_files = self.download_flex_reports(current_date)
                
                if len(downloaded_files) == len(FLEX_CONFIGS):
                    # Get the data directory for this date
                    month_dir = current_date.strftime("%B%Y")
                    data_dir = os.path.join(DATA_BASE_DIR, month_dir)
                    
                    # Run the ALM data builder in append mode
                    self.run_alm_data_builder(append_mode=True, data_dir=data_dir)
                    
                    # Mark this date as processed
                    self.mark_date_processed(current_date)
                    
                    # Run calculation engine for this date
                    conn = psycopg2.connect(DATABASE_URL)
                    try:
                        with conn.cursor() as cursor:
                            # Generate daily narrative
                            generate_daily_narrative(cursor, current_date)
                            logger.info(f"Generated daily narrative for {current_date}")
                    finally:
                        conn.close()
                else:
                    logger.warning(f"Not all reports downloaded for {current_date}")
                    
            except Exception as e:
                logger.error(f"Error processing {current_date}: {e}")
                
            current_date += timedelta(days=1)
            
    def run_alm_data_builder(self, append_mode: bool = True, data_dir: str = None):
        """Run the ALM data builder script"""
        import subprocess
        
        # Prepare the command
        script_path = "/home/info/fntx-ai-v1/backend/alm/build_alm_data_append.py"
        cmd = [sys.executable, script_path]
        
        if append_mode:
            cmd.append("--append")
            
        if data_dir:
            cmd.extend(["--data-dir", data_dir])
            
        logger.info(f"Running ALM data builder: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ALM data builder failed: {result.stderr}")
            raise RuntimeError("ALM data builder failed")
        else:
            logger.info("ALM data builder completed successfully")
            
    def mark_date_processed(self, process_date: date):
        """Mark a date as successfully processed in the database"""
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO alm_reporting.import_history 
                    (import_date, status, completed_at)
                    VALUES (%s, 'SUCCESS', %s)
                    ON CONFLICT (import_date) 
                    DO UPDATE SET 
                        status = 'SUCCESS',
                        completed_at = EXCLUDED.completed_at
                """, (process_date, datetime.now()))
                conn.commit()
        finally:
            conn.close()
            
    def run_daily_update(self):
        """Run daily update - main entry point for scheduled job"""
        logger.info("Starting ALM daily update")
        
        # Get last processed date
        last_date = self.get_last_processed_date()
        logger.info(f"Last processed date: {last_date}")
        
        # Process from next day to yesterday (today's data not available yet)
        start_date = last_date + timedelta(days=1)
        end_date = date.today() - timedelta(days=1)
        
        if start_date > end_date:
            logger.info("Already up to date")
            return
            
        # Process the date range
        self.process_date_range(start_date, end_date)
        
        # Clean up old files
        self.manage_file_rotation()
        
        logger.info("ALM daily update completed")
        
    def run_historical_backfill(self, start_date: date, end_date: date):
        """Run historical backfill for a specific date range"""
        logger.info(f"Running historical backfill from {start_date} to {end_date}")
        
        # For historical data, we might need to use MTD reports
        # This is a simplified version - enhance as needed
        self.process_date_range(start_date, end_date)
        
        logger.info("Historical backfill completed")

def create_tracking_tables():
    """Create database tables for tracking imports"""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alm_reporting.import_history (
                    import_date DATE PRIMARY KEY,
                    status VARCHAR(20),
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_import_history_status 
                ON alm_reporting.import_history(status);
            """)
            conn.commit()
            logger.info("Created tracking tables")
    finally:
        conn.close()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ALM Automation System')
    parser.add_argument('--backfill', action='store_true', 
                       help='Run historical backfill')
    parser.add_argument('--start-date', type=str, 
                       help='Start date for backfill (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='End date for backfill (YYYY-MM-DD)')
    parser.add_argument('--setup', action='store_true',
                       help='Create tracking tables')
    
    args = parser.parse_args()
    
    automation = ALMAutomation()
    
    if args.setup:
        create_tracking_tables()
        
    elif args.backfill:
        if not args.start_date or not args.end_date:
            logger.error("--start-date and --end-date required for backfill")
            sys.exit(1)
            
        start = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        automation.run_historical_backfill(start, end)
        
    else:
        # Default: run daily update
        automation.run_daily_update()

if __name__ == "__main__":
    main()