#!/usr/bin/env python3
"""
Enhanced IBKR Flex Query API Integration
Retrieves trade history, NAV snapshots, and cash movements
"""

import os
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import time
import psycopg2
from psycopg2.extras import RealDictCursor

from database.trade_db import get_trade_db_connection

logger = logging.getLogger(__name__)

class IBKRFlexQueryEnhanced:
    """Enhanced service for retrieving complete account data via IBKR Flex Query API"""
    
    def __init__(self):
        # Flex Query configuration
        self.base_url = "https://gdcdyn.interactivebrokers.com/Universal/servlet"
        self.token = os.getenv("IBKR_FLEX_TOKEN")
        self.query_id = os.getenv("IBKR_FLEX_QUERY_ID")
        
        if not self.token or not self.query_id:
            logger.warning("IBKR Flex Query credentials not configured. Please set IBKR_FLEX_TOKEN and IBKR_FLEX_QUERY_ID")
    
    def request_flex_report(self) -> Optional[str]:
        """Request a Flex Query report and return the reference code"""
        if not self.token or not self.query_id:
            raise ValueError("Flex Query credentials not configured")
        
        url = f"{self.base_url}/FlexStatementService.SendRequest"
        params = {
            "t": self.token,
            "q": self.query_id,
            "v": "3"  # API version
        }
        
        try:
            logger.info(f"Requesting Flex Query report with query ID: {self.query_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            
            if root.tag == "FlexStatementResponse":
                status = root.find("Status")
                if status is not None and status.text == "Success":
                    reference_code = root.find("ReferenceCode")
                    if reference_code is not None:
                        logger.info(f"Flex Query request successful. Reference code: {reference_code.text}")
                        return reference_code.text
                else:
                    error_code = root.find("ErrorCode")
                    error_msg = root.find("ErrorMessage")
                    logger.error(f"Flex Query request failed: {error_code.text if error_code is not None else 'Unknown'} - "
                               f"{error_msg.text if error_msg is not None else 'Unknown error'}")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to request Flex Query report: {e}")
            return None
    
    def get_flex_report(self, reference_code: str, max_retries: int = 20) -> Optional[str]:
        """Retrieve the Flex Query report using the reference code"""
        url = f"{self.base_url}/FlexStatementService.GetStatement"
        
        for attempt in range(max_retries):
            params = {
                "q": reference_code,
                "t": self.token,
                "v": "3"
            }
            
            try:
                logger.info(f"Retrieving Flex Query report (attempt {attempt + 1}/{max_retries})")
                response = requests.get(url, params=params, timeout=60)
                
                # Check if report is ready
                if response.status_code == 200:
                    # Check if it's XML (report ready) or error message
                    if (response.text.startswith("<?xml") or "FlexQueryResponse" in response.text) and "Statement generation in progress" not in response.text:
                        logger.info("Flex Query report retrieved successfully")
                        return response.text
                    elif "not yet available" in response.text.lower() or "generation in progress" in response.text.lower():
                        logger.info(f"Report not ready yet, waiting... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(10)  # Wait 10 seconds before retry
                        continue
                else:
                    logger.error(f"HTTP error {response.status_code}: {response.text}")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to retrieve Flex Query report: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                return None
        
        logger.error("Max retries reached, report not available")
        return None
    
    def parse_account_information(self, xml_data: str) -> Dict[str, Any]:
        """Parse account information including NAV from Flex Query XML"""
        account_info = {}
        
        try:
            root = ET.fromstring(xml_data)
            
            # Find ChangeInNAV element (this contains the NAV data)
            for nav_elem in root.findall(".//ChangeInNAV"):
                account_info = {
                    "account_id": nav_elem.get("accountId"),
                    "currency": nav_elem.get("currency", "HKD"),
                    "starting_nav": self._parse_decimal(nav_elem.get("startingValue")),
                    "ending_nav": self._parse_decimal(nav_elem.get("endingValue")),
                    "mtm": self._parse_decimal(nav_elem.get("mtm")),
                    "realized": self._parse_decimal(nav_elem.get("realized")),
                    "deposits_withdrawals": self._parse_decimal(nav_elem.get("depositsWithdrawals")),
                    "commissions": self._parse_decimal(nav_elem.get("commissions")),
                    "interest": self._parse_decimal(nav_elem.get("interest")),
                    "other_fees": self._parse_decimal(nav_elem.get("otherFees")),
                    "from_date": nav_elem.get("fromDate"),
                    "to_date": nav_elem.get("toDate")
                }
                break  # Usually only one account
            
            # Also get cash balances from CashReportCurrency
            for cash_elem in root.findall(".//CashReportCurrency[@currency='BASE_SUMMARY']"):
                if account_info:
                    account_info.update({
                        "starting_cash": self._parse_decimal(cash_elem.get("startingCash")),
                        "ending_cash": self._parse_decimal(cash_elem.get("endingCash")),
                        "ending_settled_cash": self._parse_decimal(cash_elem.get("endingSettledCash"))
                    })
                break
            
            nav_value = account_info.get('ending_nav', account_info.get('starting_nav', 0))
            logger.info(f"Parsed account info - NAV: ${nav_value:,.2f} {account_info.get('currency', 'HKD')}")
            return account_info
            
        except Exception as e:
            logger.error(f"Failed to parse account information: {e}")
            return {}
    
    def parse_cash_transactions(self, xml_data: str) -> List[Dict[str, Any]]:
        """Parse cash transactions from dedicated Cash Transactions FlexQuery XML"""
        transactions = []
        
        try:
            root = ET.fromstring(xml_data)
            
            # Parse CashTransaction elements from Cash Transactions FlexQuery
            for cash_elem in root.findall(".//CashTransaction"):
                trans_type = cash_elem.get("type", "")
                description = cash_elem.get("description", "")
                amount = self._parse_decimal(cash_elem.get("amount"))
                
                # Determine transaction category
                category = None
                if trans_type in ["Deposits/Withdrawals", "Deposits", "Withdrawals"]:
                    category = "DEPOSIT" if amount and amount > 0 else "WITHDRAWAL"
                elif trans_type == "Broker Interest Paid":
                    category = "INTEREST_PAID"
                elif trans_type == "Broker Interest Received":
                    category = "INTEREST_RECEIVED"
                elif trans_type in ["Other Fees", "Broker Fees"]:
                    category = "FEE"
                elif trans_type == "Commission Adjustments":
                    category = "COMMISSION_ADJ"
                elif trans_type == "Price Adjustments":
                    category = "PRICE_ADJ"
                elif trans_type == "Other Income":
                    category = "OTHER_INCOME"
                
                if category:
                    transaction = {
                        "date": cash_elem.get("dateTime", "").split(";")[0],
                        "datetime": cash_elem.get("dateTime", ""),
                        "type": trans_type,
                        "category": category,
                        "amount": amount,
                        "currency": cash_elem.get("currency", "USD"),
                        "currency_primary": cash_elem.get("currencyPrimary", "HKD"),
                        "description": description,
                        "transaction_id": cash_elem.get("transactionID"),
                        "settle_date": cash_elem.get("settleDate"),
                        "account_id": cash_elem.get("accountId")
                    }
                    transactions.append(transaction)
            
            logger.info(f"Parsed {len(transactions)} cash transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to parse cash transactions: {e}")
            return []
    
    def parse_interest_accruals(self, xml_data: str) -> Dict[str, Any]:
        """Parse interest accruals from Interest Accruals FlexQuery XML"""
        result = {
            "accruals": {},
            "tier_details": []
        }
        
        try:
            root = ET.fromstring(xml_data)
            
            # Parse InterestAccruals summary
            for accrual in root.findall(".//InterestAccrual"):
                currency = accrual.get("currencyPrimary", "HKD")
                result["accruals"][currency] = {
                    "from_date": accrual.get("fromDate"),
                    "to_date": accrual.get("toDate"),
                    "starting_balance": self._parse_decimal(accrual.get("startingAccrualBalance")),
                    "interest_accrued": self._parse_decimal(accrual.get("interestAccrued")),
                    "accrual_reversal": self._parse_decimal(accrual.get("accrualReversal")),
                    "fx_translation": self._parse_decimal(accrual.get("fxTranslation")),
                    "ending_balance": self._parse_decimal(accrual.get("endingAccrualBalance")),
                    "account_id": accrual.get("accountId")
                }
            
            # Parse InterestDetail tier information
            for detail in root.findall(".//InterestDetail"):
                tier_info = {
                    "report_date": detail.get("reportDate"),
                    "value_date": detail.get("valueDate"),
                    "currency": detail.get("currencyPrimary", "HKD"),
                    "interest_type": detail.get("interestType"),
                    "tier_break": self._parse_decimal(detail.get("tierBreak")),
                    "balance_threshold": self._parse_decimal(detail.get("balanceThreshold")),
                    "total_principal": self._parse_decimal(detail.get("totalPrincipal")),
                    "margin_balance": self._parse_decimal(detail.get("marginBalance")),
                    "rate": self._parse_decimal(detail.get("rate")),
                    "total_interest": self._parse_decimal(detail.get("totalInterest")),
                    "code": detail.get("code"),
                    "from_acct": detail.get("fromAcct"),
                    "to_acct": detail.get("toAcct")
                }
                result["tier_details"].append(tier_info)
            
            logger.info(f"Parsed interest accruals for {len(result['accruals'])} currencies with {len(result['tier_details'])} tier details")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse interest accruals: {e}")
            return {"accruals": {}, "tier_details": []}
    
    def parse_daily_pnl(self, xml_data: str) -> Dict[str, Decimal]:
        """Parse daily P&L from trades"""
        daily_pnl = {}
        
        try:
            root = ET.fromstring(xml_data)
            
            # Parse trades for P&L
            for trade in root.findall(".//Trade"):
                trade_date = trade.get("tradeDate")
                if trade_date:
                    pnl = self._parse_decimal(trade.get("fifoPnlRealized", "0"))
                    if trade_date not in daily_pnl:
                        daily_pnl[trade_date] = Decimal("0")
                    daily_pnl[trade_date] += pnl
            
            return daily_pnl
            
        except Exception as e:
            logger.error(f"Failed to parse daily P&L: {e}")
            return {}
    
    def save_nav_snapshot(self, date: date, account_info: Dict[str, Any], daily_pnl: Decimal = None):
        """Save NAV snapshot to database"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portfolio.daily_nav_snapshots (
                        snapshot_date,
                        opening_nav,
                        closing_nav,
                        opening_cash,
                        closing_cash,
                        opening_positions_value,
                        closing_positions_value,
                        trading_pnl,
                        source,
                        last_fetched_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (snapshot_date) DO UPDATE SET
                        closing_nav = EXCLUDED.closing_nav,
                        closing_cash = EXCLUDED.closing_cash,
                        closing_positions_value = EXCLUDED.closing_positions_value,
                        trading_pnl = COALESCE(EXCLUDED.trading_pnl, portfolio.daily_nav_snapshots.trading_pnl),
                        last_fetched_at = EXCLUDED.last_fetched_at,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    date,
                    account_info.get('starting_nav', account_info.get('ending_nav', 0)),  # Use starting NAV as opening
                    account_info.get('ending_nav', 0),
                    account_info.get('starting_cash', 0),
                    account_info.get('ending_cash', 0),
                    0,  # Will calculate from positions
                    0,  # Will calculate from positions  
                    daily_pnl or 0,
                    'IBKR',
                    datetime.now()
                ))
                conn.commit()
                logger.info(f"Saved NAV snapshot for {date}")
        except Exception as e:
            logger.error(f"Failed to save NAV snapshot: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_period_nav_snapshot(self, from_date: date, to_date: date, account_info: Dict[str, Any], daily_pnl: Dict[str, Decimal]):
        """Save NAV snapshots for opening and closing of period"""
        # Save opening NAV (from_date)
        opening_nav_data = {
            'starting_nav': account_info.get('starting_nav'),
            'ending_nav': account_info.get('starting_nav'),  # Same as starting for opening
            'starting_cash': account_info.get('starting_cash'),
            'ending_cash': account_info.get('starting_cash'),  # Same as starting for opening
        }
        self.save_nav_snapshot(from_date, opening_nav_data)
        
        # Save closing NAV (to_date)
        closing_nav_data = {
            'starting_nav': account_info.get('starting_nav'),
            'ending_nav': account_info.get('ending_nav'),
            'starting_cash': account_info.get('starting_cash'),
            'ending_cash': account_info.get('ending_cash'),
        }
        
        # Calculate total P&L for the period
        total_pnl = sum(daily_pnl.values()) if daily_pnl else Decimal('0')
        self.save_nav_snapshot(to_date, closing_nav_data, total_pnl)
        
        # Also save individual daily P&L snapshots if we have trade data
        for date_str, pnl in daily_pnl.items():
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            if from_date <= trade_date <= to_date:
                # Create snapshot for trade day with daily P&L
                daily_nav_data = {
                    'starting_nav': account_info.get('starting_nav'),
                    'ending_nav': account_info.get('ending_nav'),
                    'starting_cash': account_info.get('starting_cash'), 
                    'ending_cash': account_info.get('ending_cash'),
                }
                self.save_nav_snapshot(trade_date, daily_nav_data, pnl)
    
    def save_cash_transactions(self, transactions: List[Dict[str, Any]]):
        """Save cash transactions to database"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cursor:
                for trans in transactions:
                    # Parse datetime properly
                    move_datetime = self._parse_datetime(trans['datetime'])
                    move_date = move_datetime.date() if move_datetime else datetime.now().date()
                    
                    cursor.execute("""
                        INSERT INTO portfolio.cash_transactions (
                            transaction_date,
                            transaction_time,
                            transaction_type,
                            category,
                            amount,
                            currency,
                            currency_primary,
                            description,
                            ibkr_transaction_id,
                            settlement_date,
                            account_id,
                            created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (ibkr_transaction_id) DO UPDATE SET
                            amount = EXCLUDED.amount,
                            description = EXCLUDED.description,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        move_date,
                        move_datetime,
                        trans['type'],
                        trans['category'],
                        trans['amount'],
                        trans['currency'],
                        trans['currency_primary'],
                        trans['description'],
                        trans['transaction_id'],
                        trans.get('settle_date'),
                        trans['account_id'],
                        datetime.now()
                    ))
                conn.commit()
                logger.info(f"Saved {len(transactions)} cash transactions")
        except Exception as e:
            logger.error(f"Failed to save cash transactions: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_interest_accruals(self, interest_data: Dict[str, Any]):
        """Save interest accruals and tier details to database"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cursor:
                # Save accruals summary
                for currency, accrual in interest_data['accruals'].items():
                    cursor.execute("""
                        INSERT INTO portfolio.interest_accruals (
                            from_date,
                            to_date,
                            currency,
                            starting_balance,
                            interest_accrued,
                            accrual_reversal,
                            fx_translation,
                            ending_balance,
                            account_id,
                            created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (from_date, to_date, currency) DO UPDATE SET
                            ending_balance = EXCLUDED.ending_balance,
                            interest_accrued = EXCLUDED.interest_accrued,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        datetime.strptime(accrual['from_date'], '%Y%m%d').date() if accrual['from_date'] else None,
                        datetime.strptime(accrual['to_date'], '%Y%m%d').date() if accrual['to_date'] else None,
                        currency,
                        accrual['starting_balance'],
                        accrual['interest_accrued'],
                        accrual['accrual_reversal'],
                        accrual['fx_translation'],
                        accrual['ending_balance'],
                        accrual['account_id'],
                        datetime.now()
                    ))
                
                # Save tier details
                for detail in interest_data['tier_details']:
                    cursor.execute("""
                        INSERT INTO portfolio.interest_tier_details (
                            report_date,
                            value_date,
                            currency,
                            interest_type,
                            tier_break,
                            balance_threshold,
                            total_principal,
                            margin_balance,
                            rate,
                            total_interest,
                            code,
                            from_acct,
                            to_acct
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (report_date, currency, interest_type, tier_break) DO UPDATE SET
                            total_interest = EXCLUDED.total_interest,
                            rate = EXCLUDED.rate
                    """, (
                        datetime.strptime(detail['report_date'], '%Y%m%d').date() if detail['report_date'] else None,
                        datetime.strptime(detail['value_date'], '%Y%m%d').date() if detail['value_date'] else None,
                        detail['currency'],
                        detail['interest_type'],
                        detail['tier_break'],
                        detail['balance_threshold'],
                        detail['total_principal'],
                        detail['margin_balance'],
                        detail['rate'],
                        detail['total_interest'],
                        detail['code'],
                        detail['from_acct'],
                        detail['to_acct']
                    ))
                
                conn.commit()
                logger.info(f"Saved interest accruals for {len(interest_data['accruals'])} currencies")
        except Exception as e:
            logger.error(f"Failed to save interest accruals: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_cash_movements(self, transactions: List[Dict[str, Any]]):
        """DEPRECATED: Use save_cash_transactions instead"""
        logger.warning("save_cash_movements is deprecated. Use save_cash_transactions")
        self.save_cash_transactions(transactions)
    
    def fetch_and_save_account_data(self, days_back: int = 7) -> bool:
        """Fetch complete account data and save to database"""
        try:
            # Request report
            reference_code = self.request_flex_report()
            if not reference_code:
                logger.error("Failed to request Flex Query report")
                return False
            
            # Wait longer for report generation (30 seconds)
            logger.info("Waiting 30 seconds for report generation...")
            time.sleep(30)
            
            # Retrieve report with longer wait
            xml_data = self.get_flex_report(reference_code, max_retries=30)
            if not xml_data:
                logger.error("Failed to retrieve Flex Query report")
                return False
            
            # Parse and save data
            account_info = self.parse_account_information(xml_data)
            cash_transactions = self.parse_cash_transactions(xml_data)
            daily_pnl = self.parse_daily_pnl(xml_data)
            
            # Save to database
            if account_info:
                # Extract from/to dates from the account info
                from_date_str = account_info.get('from_date')
                to_date_str = account_info.get('to_date')
                
                if from_date_str and to_date_str:
                    from_date = datetime.strptime(from_date_str, '%Y%m%d').date()
                    to_date = datetime.strptime(to_date_str, '%Y%m%d').date()
                    
                    # Save period NAV data as opening/closing for the period
                    self.save_period_nav_snapshot(from_date, to_date, account_info, daily_pnl)
                else:
                    # Fallback: save current day NAV
                    self.save_nav_snapshot(date.today(), account_info)
            
            if cash_transactions:
                self.save_cash_movements(cash_transactions)
            
            # Store raw XML for reference
            self._store_raw_statement(xml_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fetch and save account data: {e}")
            return False
    
    def _store_raw_statement(self, xml_data: str):
        """Store raw XML statement for audit purposes"""
        conn = get_trade_db_connection()
        try:
            # Extract statement date from XML
            root = ET.fromstring(xml_data)
            statement_date = root.get("toDate", date.today().strftime('%Y%m%d'))
            account_id = ""
            
            for account in root.findall(".//AccountInformation"):
                account_id = account.get("accountId", "")
                break
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portfolio.account_statements (
                        statement_date,
                        account_id,
                        flex_query_xml,
                        is_processed,
                        processed_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (statement_date, account_id) DO UPDATE SET
                        flex_query_xml = EXCLUDED.flex_query_xml,
                        is_processed = EXCLUDED.is_processed,
                        processed_at = EXCLUDED.processed_at
                """, (
                    datetime.strptime(statement_date, '%Y%m%d').date(),
                    account_id,
                    xml_data,
                    True,
                    datetime.now()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store raw statement: {e}")
        finally:
            conn.close()
    
    def _parse_decimal(self, value: Optional[str]) -> Optional[Decimal]:
        """Safely parse decimal values"""
        if value is None or value == "":
            return None
        try:
            return Decimal(value)
        except:
            return None
    
    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse IBKR datetime format"""
        if not value:
            return None
        
        # IBKR format: "YYYYMMDD;HHMMSS"
        try:
            if ";" in value:
                date_part, time_part = value.split(";")
                dt_str = f"{date_part} {time_part}"
                return datetime.strptime(dt_str, "%Y%m%d %H%M%S")
            else:
                # Just date
                return datetime.strptime(value, "%Y%m%d")
        except Exception as e:
            logger.error(f"Failed to parse datetime '{value}': {e}")
            return None

# Singleton instance
flex_query_enhanced = IBKRFlexQueryEnhanced()