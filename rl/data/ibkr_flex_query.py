"""
IBKR Flex Query API Integration
Fetches account data from Interactive Brokers
"""
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import logging
from datetime import datetime
import psycopg2
import os

class IBKRFlexQuery:
    """Fetch account data from IBKR Flex Query Service"""
    
    def __init__(self, token: str, query_id: str):
        self.token = token
        self.query_id = query_id
        self.base_url = "https://gdcdyn.interactivebrokers.com/Universal/servlet"
        self.logger = logging.getLogger(__name__)
        
    def fetch_account_summary(self) -> Optional[Dict]:
        """
        Fetch account summary from IBKR Flex Query
        
        Returns:
            Dict with account data or None if error
        """
        try:
            # Step 1: Request the report
            request_url = f"{self.base_url}/FlexStatementService.SendRequest"
            params = {
                "t": self.token,
                "q": self.query_id,
                "v": "3"
            }
            
            response = requests.get(request_url, params=params)
            if response.status_code != 200:
                self.logger.error(f"Failed to request report: {response.status_code}")
                return None
                
            # Parse response to get reference code
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text if root.find(".//Status") is not None else None
            
            if status != "Success":
                error_msg = root.find(".//ErrorMessage").text if root.find(".//ErrorMessage") is not None else "Unknown error"
                self.logger.error(f"Flex Query request failed: {error_msg}")
                return None
                
            reference_code = root.find(".//ReferenceCode").text
            if not reference_code:
                self.logger.error("No reference code received")
                return None
                
            # Step 2: Retrieve the report (may need to retry)
            retrieve_url = f"{self.base_url}/FlexStatementService.GetStatement"
            params = {
                "q": reference_code,
                "t": self.token,
                "v": "3"
            }
            
            # Try a few times as report generation may take time
            for attempt in range(5):
                response = requests.get(retrieve_url, params=params)
                if response.status_code == 200 and "<FlexQueryResponse" in response.text:
                    break
                import time
                time.sleep(2)  # Wait 2 seconds between attempts
            else:
                self.logger.error("Failed to retrieve report after multiple attempts")
                return None
                
            # Parse account data
            root = ET.fromstring(response.text)
            
            # Extract account summary
            account_data = {}
            
            # Find account information
            account_info = root.find(".//AccountInformation")
            if account_info is not None:
                account_data['account_id'] = account_info.get('accountId', '')
                account_data['currency'] = account_info.get('currency', 'USD')
                # Log all attributes for debugging
                self.logger.info(f"AccountInformation attributes: {account_info.attrib}")
                
            # Find cash report
            cash_report = root.find(".//CashReport")
            if cash_report is not None:
                # Get ending cash balance
                ending_cash = cash_report.get('endingCash', '0')
                account_data['cash_balance'] = float(ending_cash)
                self.logger.info(f"Cash Report - endingCash: {ending_cash}")
                
            # Find summary data - try multiple locations
            # First try ChangeInNAV which is what the ALM system uses
            nav_summary = root.find(".//ChangeInNAV")
            if nav_summary is not None:
                ending_value = nav_summary.get('endingValue', '0')
                starting_value = nav_summary.get('startingValue', '0')
                nav_currency = nav_summary.get('currency', 'HKD')
                
                # Use ending value as total, with fallback to starting value
                total_val = float(ending_value) if ending_value and ending_value != '0' else float(starting_value)
                account_data['total_value'] = total_val
                account_data['currency'] = nav_currency  # Override with NAV currency
                
                self.logger.info(f"ChangeInNAV found - startingValue: {starting_value}, endingValue: {ending_value}, currency: {nav_currency}")
                self.logger.info(f"ChangeInNAV all attributes: {nav_summary.attrib}")
                
                # Also capture other NAV components for debugging
                account_data['nav_details'] = {
                    'starting_value': float(starting_value) if starting_value else 0,
                    'ending_value': float(ending_value) if ending_value else 0,
                    'mtm': float(nav_summary.get('mtm', '0')),
                    'realized': float(nav_summary.get('realized', '0')),
                    'deposits_withdrawals': float(nav_summary.get('depositsWithdrawals', '0')),
                    'interest': float(nav_summary.get('interest', '0')),
                    'commissions': float(nav_summary.get('commissions', '0'))
                }
            else:
                # Fallback to other summary types
                summary = root.find(".//EquitySummaryByReportDateInBase")
                if summary is not None:
                    total = summary.get('total', '0')
                    account_data['total_value'] = float(total)
                    self.logger.info(f"EquitySummaryByReportDateInBase - total: {total}")
                    self.logger.info(f"EquitySummaryByReportDateInBase attributes: {summary.attrib}")
                else:
                    # Try EquitySummaryInBase
                    summary_in_base = root.find(".//EquitySummaryInBase")
                    if summary_in_base is not None:
                        total = summary_in_base.get('total', '0')
                        account_data['total_value'] = float(total)
                        self.logger.info(f"EquitySummaryInBase - total: {total}")
                        self.logger.info(f"EquitySummaryInBase attributes: {summary_in_base.attrib}")
                    else:
                        # Fallback to cash balance if no equity summary
                        account_data['total_value'] = account_data.get('cash_balance', 0)
                        self.logger.info("No equity summary found, using cash balance")
                
            # Add timestamp
            account_data['timestamp'] = datetime.now().isoformat()
            
            # Store the XML root for later parsing (trades, exercises, etc)
            account_data['_xml_root'] = root
            
            self.logger.info(f"Successfully fetched account data: ${account_data.get('total_value', 0):,.2f} {account_data.get('currency', 'USD')}")
            
            # If we got 0 value, try database fallback
            if account_data.get('total_value', 0) == 0:
                self.logger.warning("IBKR returned $0 value, attempting database fallback")
                db_data = self.fetch_nav_from_database()
                if db_data and db_data.get('total_value', 0) > 0:
                    # Merge database data with IBKR structure
                    account_data['total_value'] = db_data['total_value']
                    account_data['currency'] = db_data['currency']
                    account_data['source'] = 'database_fallback'
                    self.logger.info(f"Using database NAV: ${db_data['total_value']:,.2f} {db_data['currency']}")
            
            return account_data
            
        except Exception as e:
            self.logger.error(f"Error fetching IBKR data: {e}")
            # Try database as last resort
            return self.fetch_nav_from_database()
            
    def fetch_nav_from_database(self) -> Optional[Dict]:
        """
        Fetch NAV from ALM database as fallback
        
        Returns:
            Dict with account data from backend.data.database or None if error
        """
        try:
            # Database connection parameters
            db_params = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'options_data'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'theta_data_2024')
            }
            
            conn = psycopg2.connect(**db_params)
            cursor = conn.cursor()
            
            # Query latest NAV from ALM daily summary
            cursor.execute("""
                SELECT 
                    summary_date,
                    closing_nav_hkd,
                    opening_nav_hkd,
                    cash_balance_hkd,
                    currency
                FROM alm_reporting.daily_summary
                WHERE closing_nav_hkd IS NOT NULL
                ORDER BY summary_date DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                self.logger.info(f"Found NAV in database for date {result[0]}: HKD {result[1]:,.2f}")
                return {
                    'total_value': float(result[1]),  # closing_nav_hkd
                    'opening_value': float(result[2]) if result[2] else 0,
                    'cash_balance': float(result[3]) if result[3] else 0,
                    'currency': result[4] or 'HKD',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'database',
                    'date': str(result[0])
                }
            else:
                self.logger.warning("No NAV data found in database")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching NAV from backend.data.database: {e}")
            return None
    
    def get_buying_power(self) -> float:
        """Get available buying power from account data"""
        account_data = self.fetch_account_summary()
        
        # If IBKR returns 0 or None, try database fallback
        if not account_data or account_data.get('total_value', 0) == 0:
            self.logger.info("IBKR returned no data or $0, trying database fallback")
            account_data = self.fetch_nav_from_database()
        
        if account_data:
            # For now, use total value as buying power
            # In practice, this should consider margin requirements
            return account_data.get('total_value', 0)
        return 0