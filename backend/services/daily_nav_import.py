#!/usr/bin/env python3
"""
Daily NAV Import Service
Fetches daily NAV data from IBKR using the "Last Business Day" Flex Query
"""

import os
import sys
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
import xml.etree.ElementTree as ET

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.ibkr_flex_query import IBKRFlexQueryService
from backend.database.trade_db import get_trade_db_connection

logger = logging.getLogger(__name__)

class DailyNAVImport:
    """Import daily NAV snapshots from IBKR"""
    
    def __init__(self):
        self.service = IBKRFlexQueryService()
        
    def import_daily_nav(self):
        """Import yesterday's NAV data from IBKR"""
        
        logger.info("Starting daily NAV import...")
        
        # Request the report
        reference_code = self.service.request_flex_report()
        if not reference_code:
            logger.error("Failed to request NAV report")
            return False
            
        # Get the report
        import time
        time.sleep(5)  # Wait for report generation
        
        # Fetch directly since service may not handle this format
        import requests
        url = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement"
        params = {
            "t": os.getenv('IBKR_FLEX_TOKEN'),
            "q": reference_code,
            "v": "3"
        }
        
        response = requests.get(url, params=params)
        xml_data = response.text
        
        if not xml_data or "FlexStatement" not in xml_data:
            logger.error("Failed to retrieve NAV report")
            return False
            
        # Parse the XML
        try:
            root = ET.fromstring(xml_data)
            
            # Find the ChangeInNAV element
            nav_data = None
            for nav_elem in root.findall(".//ChangeInNAV"):
                nav_data = {
                    'account_id': nav_elem.get('accountId'),
                    'currency': nav_elem.get('currency'),
                    'from_date': nav_elem.get('fromDate'),
                    'to_date': nav_elem.get('toDate'),
                    'starting_value': Decimal(nav_elem.get('startingValue', '0')),
                    'ending_value': Decimal(nav_elem.get('endingValue', '0')),
                    'mtm': Decimal(nav_elem.get('mtm', '0')),
                    'realized': Decimal(nav_elem.get('realized', '0')),
                    'deposits_withdrawals': Decimal(nav_elem.get('depositsWithdrawals', '0')),
                    'interest': Decimal(nav_elem.get('interest', '0')),
                    'commissions': Decimal(nav_elem.get('commissions', '0')),
                    'other_fees': Decimal(nav_elem.get('otherFees', '0')),
                    'fx_translation': Decimal(nav_elem.get('fxTranslation', '0'))
                }
                break
                
            if not nav_data:
                logger.error("No NAV data found in report")
                return False
                
            # Find the NAV in Base element for detailed NAV breakdown
            nav_base_data = None
            for nav_base in root.findall(".//NetAssetValueInBase"):
                nav_base_data = {
                    'report_date': nav_base.get('reportDate'),
                    'cash': Decimal(nav_base.get('cash', '0')),
                    'stock': Decimal(nav_base.get('stock', '0')),
                    'options': Decimal(nav_base.get('options', '0')),
                    'total': Decimal(nav_base.get('total', '0'))
                }
                break
                
            # Get cash report data
            cash_data = None
            for cash_elem in root.findall(".//CashReportCurrency[@currency='BASE_SUMMARY']"):
                cash_data = {
                    'starting_cash': Decimal(cash_elem.get('startingCash', '0')),
                    'ending_cash': Decimal(cash_elem.get('endingCash', '0')),
                    'ending_settled_cash': Decimal(cash_elem.get('endingSettledCash', '0'))
                }
                break
                
            # Save to database
            return self._save_nav_snapshot(nav_data, nav_base_data, cash_data)
            
        except Exception as e:
            logger.error(f"Failed to parse NAV report: {e}")
            return False
    
    def _save_nav_snapshot(self, nav_data: dict, nav_base_data: dict, cash_data: dict) -> bool:
        """Save NAV snapshot to database"""
        
        try:
            # Determine the date (to_date from ChangeInNAV)
            snapshot_date = datetime.strptime(nav_data['to_date'], '%Y%m%d').date()
            
            logger.info(f"Saving NAV snapshot for {snapshot_date}")
            logger.info(f"  Starting NAV: {nav_data['starting_value']}")
            logger.info(f"  Ending NAV: {nav_data['ending_value']}")
            logger.info(f"  Cash: {cash_data['ending_cash'] if cash_data else 'N/A'}")
            
            conn = get_trade_db_connection()
            try:
                with conn.cursor() as cursor:
                    # Check if snapshot exists
                    cursor.execute("""
                        SELECT snapshot_id FROM portfolio.daily_nav_snapshots
                        WHERE snapshot_date = %s
                    """, (snapshot_date,))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing snapshot
                        cursor.execute("""
                            UPDATE portfolio.daily_nav_snapshots
                            SET opening_nav = %s,
                                closing_nav = %s,
                                opening_cash = %s,
                                closing_cash = %s,
                                opening_positions_value = %s,
                                closing_positions_value = %s,
                                trading_pnl = %s,
                                commissions_paid = %s,
                                interest_earned = %s,
                                fees_charged = %s,
                                source = 'ibkr_daily',
                                is_reconciled = true,
                                updated_at = NOW(),
                                last_fetched_at = NOW()
                            WHERE snapshot_date = %s
                        """, (
                            nav_data['starting_value'],
                            nav_data['ending_value'],
                            cash_data['starting_cash'] if cash_data else nav_data['starting_value'],
                            cash_data['ending_cash'] if cash_data else nav_data['ending_value'],
                            nav_data['starting_value'] - (cash_data['starting_cash'] if cash_data else 0),
                            nav_data['ending_value'] - (cash_data['ending_cash'] if cash_data else 0),
                            nav_data['realized'] + nav_data['mtm'],
                            nav_data['commissions'],
                            nav_data['interest'],
                            nav_data['other_fees'],
                            snapshot_date
                        ))
                        logger.info(f"Updated NAV snapshot for {snapshot_date}")
                    else:
                        # Insert new snapshot
                        cursor.execute("""
                            INSERT INTO portfolio.daily_nav_snapshots (
                                snapshot_date, opening_nav, closing_nav,
                                opening_cash, closing_cash,
                                opening_positions_value, closing_positions_value,
                                trading_pnl, commissions_paid,
                                interest_earned, fees_charged,
                                source, is_reconciled, last_fetched_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            snapshot_date,
                            nav_data['starting_value'],
                            nav_data['ending_value'],
                            cash_data['starting_cash'] if cash_data else nav_data['starting_value'],
                            cash_data['ending_cash'] if cash_data else nav_data['ending_value'],
                            nav_data['starting_value'] - (cash_data['starting_cash'] if cash_data else 0),
                            nav_data['ending_value'] - (cash_data['ending_cash'] if cash_data else 0),
                            nav_data['realized'] + nav_data['mtm'],
                            nav_data['commissions'],
                            nav_data['interest'],
                            nav_data['other_fees'],
                            'ibkr_daily',
                            True,
                            datetime.now()
                        ))
                        logger.info(f"Created NAV snapshot for {snapshot_date}")
                    
                    conn.commit()
                    return True
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Failed to save NAV snapshot: {e}")
            return False
    
    def import_historical_nav(self, days_back: int = 30):
        """Import historical NAV data by switching to period query temporarily"""
        # This would require switching query IDs or using a different approach
        # For now, this is a placeholder
        logger.info(f"Historical import for {days_back} days not yet implemented")
        logger.info("Use the daily import for ongoing NAV tracking")


def main():
    """Run daily NAV import"""
    logging.basicConfig(level=logging.INFO)
    
    importer = DailyNAVImport()
    success = importer.import_daily_nav()
    
    if success:
        logger.info("Daily NAV import completed successfully")
    else:
        logger.error("Daily NAV import failed")
        sys.exit(1)


if __name__ == "__main__":
    main()