"""
IBKR Flex Query API Integration
Fetches account data from Interactive Brokers
"""
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import logging
from datetime import datetime

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
                
            # Find cash report
            cash_report = root.find(".//CashReport")
            if cash_report is not None:
                # Get ending cash balance
                ending_cash = cash_report.get('endingCash', '0')
                account_data['cash_balance'] = float(ending_cash)
                
            # Find summary data
            summary = root.find(".//EquitySummaryByReportDateInBase")
            if summary is not None:
                total = summary.get('total', '0')
                account_data['total_value'] = float(total)
            else:
                # Fallback to cash balance if no equity summary
                account_data['total_value'] = account_data.get('cash_balance', 0)
                
            # Add timestamp
            account_data['timestamp'] = datetime.now().isoformat()
            
            self.logger.info(f"Successfully fetched account data: ${account_data.get('total_value', 0):,.2f}")
            return account_data
            
        except Exception as e:
            self.logger.error(f"Error fetching IBKR data: {e}")
            return None
            
    def get_buying_power(self) -> float:
        """Get available buying power from account data"""
        account_data = self.fetch_account_summary()
        if account_data:
            # For now, use total value as buying power
            # In practice, this should consider margin requirements
            return account_data.get('total_value', 0)
        return 0