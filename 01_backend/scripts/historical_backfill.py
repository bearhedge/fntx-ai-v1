#!/usr/bin/env python3
"""
Historical Data Backfill Script
Fetches historical NAV data from IBKR FlexQuery for the past 30 days
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from decimal import Decimal

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '01_backend'))

from services.ibkr_flex_query_enhanced import flex_query_enhanced
from database.trade_db import get_trade_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/historical_backfill.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HistoricalBackfill:
    """Backfill historical NAV data from IBKR"""
    
    def __init__(self, days_back=30):
        self.days_back = days_back
        self.nav_data = []
        
    def run_backfill(self):
        """Main backfill process"""
        logger.info(f"Starting historical backfill for {self.days_back} days...")
        
        # Request FlexQuery report with historical data
        reference_code = flex_query_enhanced.request_flex_report()
        if not reference_code:
            logger.error("Failed to request FlexQuery report")
            return False
            
        # Wait for report generation
        import time
        time.sleep(5)
        
        # Get report XML
        xml_data = flex_query_enhanced.get_flex_report(reference_code)
        if not xml_data:
            logger.error("Failed to retrieve FlexQuery report")
            return False
            
        # Parse historical NAV data
        self._parse_historical_nav(xml_data)
        
        # Save to database
        if self.nav_data:
            self._save_historical_data()
            return True
        else:
            logger.warning("No historical data found")
            return False
            
    def _parse_historical_nav(self, xml_data: str):
        """Parse historical NAV from XML"""
        try:
            root = ET.fromstring(xml_data)
            
            # Look for historical equity summaries
            for equity_elem in root.findall(".//EquitySummaryByReportDateInBase"):
                # Get HKD entries
                if equity_elem.get('currency') == 'HKD':
                    report_date = equity_elem.get('reportDate')
                    total_nav = float(equity_elem.get('total', '0'))
                    
                    if report_date and total_nav > 0:
                        # Convert date format
                        date_obj = datetime.strptime(report_date, '%Y%m%d').date()
                        
                        # Check if within our backfill range
                        cutoff_date = (datetime.now() - timedelta(days=self.days_back)).date()
                        if date_obj >= cutoff_date:
                            self.nav_data.append({
                                'date': date_obj,
                                'nav': total_nav,
                                'currency': 'HKD'
                            })
                            
            # Sort by date
            self.nav_data.sort(key=lambda x: x['date'])
            
            logger.info(f"Found {len(self.nav_data)} days of historical NAV data")
            
            # Show date range
            if self.nav_data:
                start_date = self.nav_data[0]['date']
                end_date = self.nav_data[-1]['date']
                logger.info(f"Date range: {start_date} to {end_date}")
                
        except Exception as e:
            logger.error(f"Error parsing historical NAV: {e}")
            
    def _save_historical_data(self):
        """Save historical data to database"""
        conn = get_trade_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return
            
        try:
            with conn.cursor() as cursor:
                inserted = 0
                updated = 0
                
                for nav_entry in self.nav_data:
                    # Check if entry exists
                    cursor.execute("""
                        SELECT snapshot_id FROM portfolio.daily_nav_snapshots
                        WHERE snapshot_date = %s
                    """, (nav_entry['date'],))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing entry
                        cursor.execute("""
                            UPDATE portfolio.daily_nav_snapshots
                            SET closing_nav = %s,
                                source = 'IBKR_HISTORICAL',
                                updated_at = CURRENT_TIMESTAMP
                            WHERE snapshot_date = %s
                        """, (nav_entry['nav'], nav_entry['date']))
                        updated += 1
                    else:
                        # Insert new entry
                        cursor.execute("""
                            INSERT INTO portfolio.daily_nav_snapshots 
                            (snapshot_date, closing_nav, source)
                            VALUES (%s, %s, %s)
                        """, (nav_entry['date'], nav_entry['nav'], 'IBKR_HISTORICAL'))
                        inserted += 1
                        
                conn.commit()
                
                logger.info(f"✅ Historical backfill complete:")
                logger.info(f"   - Inserted: {inserted} new records")
                logger.info(f"   - Updated: {updated} existing records")
                
                # Show sample of data
                if self.nav_data:
                    latest = self.nav_data[-1]
                    logger.info(f"   - Latest NAV: {latest['nav']:,.2f} {latest['currency']} ({latest['date']})")
                    
        except Exception as e:
            logger.error(f"Error saving historical data: {e}")
            conn.rollback()
        finally:
            conn.close()
            
    def get_missing_dates(self):
        """Check for missing dates in the database"""
        conn = get_trade_db_connection()
        if not conn:
            return []
            
        try:
            with conn.cursor() as cursor:
                # Get date range
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=self.days_back)
                
                # Get existing dates
                cursor.execute("""
                    SELECT DISTINCT snapshot_date 
                    FROM portfolio.daily_nav_snapshots
                    WHERE snapshot_date >= %s AND snapshot_date <= %s
                    ORDER BY snapshot_date
                """, (start_date, end_date))
                
                existing_dates = {row[0] for row in cursor.fetchall()}
                
                # Generate all dates in range (weekdays only)
                all_dates = []
                current = start_date
                while current <= end_date:
                    # Skip weekends
                    if current.weekday() < 5:  # Monday = 0, Friday = 4
                        all_dates.append(current)
                    current += timedelta(days=1)
                    
                # Find missing dates
                missing_dates = [d for d in all_dates if d not in existing_dates]
                
                if missing_dates:
                    logger.info(f"Found {len(missing_dates)} missing dates")
                    for date in missing_dates[:5]:  # Show first 5
                        logger.info(f"  - {date}")
                    if len(missing_dates) > 5:
                        logger.info(f"  ... and {len(missing_dates) - 5} more")
                        
                return missing_dates
                
        except Exception as e:
            logger.error(f"Error checking missing dates: {e}")
            return []
        finally:
            conn.close()


def main():
    """Main entry point"""
    backfill = HistoricalBackfill(days_back=30)
    
    # Check for missing dates first
    print("\n" + "="*60)
    print("Historical NAV Backfill")
    print("="*60)
    
    missing_dates = backfill.get_missing_dates()
    if missing_dates:
        print(f"Missing {len(missing_dates)} dates in the last 30 days")
    else:
        print("✅ No missing dates in the last 30 days")
        
    # Run backfill
    print("\nFetching historical data from IBKR...")
    if backfill.run_backfill():
        print("\n✅ Historical backfill completed successfully")
    else:
        print("\n❌ Historical backfill failed")
        
    print("="*60 + "\n")


if __name__ == "__main__":
    main()