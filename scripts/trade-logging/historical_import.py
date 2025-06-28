#!/usr/bin/env python3
"""
Historical Trade Import Script
Imports all IBKR trades since a specified date using Flex Query API
"""

import os
import sys
import logging
import argparse
import hashlib
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.services.ibkr_flex_query_enhanced import flex_query_enhanced
from backend.database.trade_db import get_trade_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/scripts/trade-logging/logs/historical_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HistoricalTradeImporter:
    """Import historical trades from IBKR Flex Query"""
    
    def __init__(self, start_date: date, end_date: Optional[date] = None):
        self.start_date = start_date
        self.end_date = end_date or date.today()
        self.flex_service = flex_query_enhanced
        self.import_id = str(uuid.uuid4())
        self.stats = {
            'total_trades': 0,
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'matched_pairs': 0
        }
    
    def run_import(self) -> bool:
        """Run the complete historical import process"""
        try:
            logger.info(f"Starting historical import from {self.start_date} to {self.end_date}")
            
            # 1. Create import log entry
            if not self._create_import_log():
                return False
            
            # 2. Fetch data from IBKR
            xml_data = self._fetch_flex_query_data()
            if not xml_data:
                self._update_import_status('FAILED', 'Failed to fetch Flex Query data')
                return False
            
            # 3. Parse and stage trades
            trades = self._parse_trades(xml_data)
            if not trades:
                self._update_import_status('COMPLETED', 'No trades found in period')
                return True
            
            self.stats['total_trades'] = len(trades)
            logger.info(f"Found {len(trades)} trades to process")
            
            # 4. Stage trades for validation
            if not self._stage_trades(trades):
                self._update_import_status('FAILED', 'Failed to stage trades')
                return False
            
            # 5. Run validation
            validation_results = self._validate_staged_trades()
            if validation_results.get('errors', 0) > 0:
                logger.warning(f"Validation found {validation_results['errors']} errors")
            
            # 6. Process staged trades to production
            if not self._process_staged_trades():
                self._update_import_status('FAILED', 'Failed to process staged trades')
                return False
            
            # 7. Match opening and closing trades
            self._match_trades()
            
            # 8. Update import status
            self._update_import_status('COMPLETED', 
                f"Imported {self.stats['imported']} trades, "
                f"matched {self.stats['matched_pairs']} pairs")
            
            logger.info(f"Import completed successfully: {self.stats}")
            return True
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            self._update_import_status('FAILED', str(e))
            return False
    
    def _create_import_log(self) -> bool:
        """Create import log entry"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trading.import_log (
                        import_id, source_type, source_id,
                        period_start, period_end, import_hash,
                        status, started_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.import_id,
                    'FLEX_QUERY',
                    f'historical_{self.start_date}_{self.end_date}',
                    self.start_date,
                    self.end_date,
                    hashlib.sha256(f"{self.start_date}{self.end_date}".encode()).hexdigest(),
                    'PROCESSING',
                    datetime.now()
                ))
                conn.commit()
                return True
        except psycopg2.IntegrityError:
            logger.error("Import already exists for this period")
            return False
        except Exception as e:
            logger.error(f"Failed to create import log: {e}")
            return False
        finally:
            conn.close()
    
    def _fetch_flex_query_data(self) -> Optional[str]:
        """Fetch Flex Query data from IBKR"""
        try:
            logger.info("Requesting Flex Query report...")
            
            # Request report
            reference_code = self.flex_service.request_flex_report()
            if not reference_code:
                logger.error("Failed to request Flex Query report")
                return None
            
            logger.info(f"Report requested, reference code: {reference_code}")
            logger.info("Waiting for report generation...")
            
            # Wait and retrieve
            import time
            time.sleep(30)  # Wait 30 seconds for report generation
            
            xml_data = self.flex_service.get_flex_report(reference_code, max_retries=30)
            if not xml_data:
                logger.error("Failed to retrieve Flex Query report")
                return None
            
            logger.info(f"Retrieved report, size: {len(xml_data)} bytes")
            return xml_data
            
        except Exception as e:
            logger.error(f"Error fetching Flex Query data: {e}")
            return None
    
    def _parse_trades(self, xml_data: str) -> List[Dict]:
        """Parse trades from Flex Query XML"""
        trades = []
        
        try:
            root = ET.fromstring(xml_data)
            
            # Find all Trade elements
            for trade_elem in root.findall(".//Trade"):
                trade_date_str = trade_elem.get("tradeDate", "")
                if not trade_date_str:
                    continue
                
                # Parse trade date
                trade_date = datetime.strptime(trade_date_str, "%Y%m%d").date()
                
                # Filter by date range
                if trade_date < self.start_date or trade_date > self.end_date:
                    continue
                
                # Parse trade time
                trade_time_str = trade_elem.get("tradeTime", "")
                if trade_time_str and ";" in trade_time_str:
                    trade_time = datetime.strptime(trade_time_str.split(";")[1], "%H%M%S").time()
                else:
                    trade_time = None
                
                trade_data = {
                    'ibkr_trade_id': trade_elem.get('tradeID'),
                    'ibkr_order_id': trade_elem.get('orderID'),
                    'ibkr_exec_id': trade_elem.get('execID'),
                    'ibkr_perm_id': trade_elem.get('permID'),
                    'account_id': trade_elem.get('accountId'),
                    'symbol': trade_elem.get('symbol'),
                    'underlying': trade_elem.get('underlyingSymbol'),
                    'asset_category': trade_elem.get('assetCategory'),
                    'sub_category': trade_elem.get('subCategory'),
                    'trade_date': trade_date,
                    'trade_time': trade_time,
                    'settle_date': self._parse_date(trade_elem.get('settleDateTarget')),
                    'quantity': self._parse_int(trade_elem.get('quantity')),
                    'price': self._parse_decimal(trade_elem.get('tradePrice')),
                    'proceeds': self._parse_decimal(trade_elem.get('proceeds')),
                    'commission': abs(self._parse_decimal(trade_elem.get('ibCommission', '0'))),
                    'fees': self._parse_decimal(trade_elem.get('taxes', '0')),
                    'realized_pnl': self._parse_decimal(trade_elem.get('fifoPnlRealized')),
                    'fx_rate': self._parse_decimal(trade_elem.get('fxRateToBase')),
                    # Options specific
                    'strike': self._parse_decimal(trade_elem.get('strike')),
                    'expiry': self._parse_date(trade_elem.get('expiry')),
                    'put_call': trade_elem.get('putCall'),
                    # Raw XML for reference
                    'raw_xml': ET.tostring(trade_elem, encoding='unicode')
                }
                
                trades.append(trade_data)
            
            logger.info(f"Parsed {len(trades)} trades from XML")
            return trades
            
        except Exception as e:
            logger.error(f"Error parsing trades: {e}")
            return []
    
    def _stage_trades(self, trades: List[Dict]) -> bool:
        """Stage trades for validation"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cur:
                for trade in trades:
                    # Create raw data JSON
                    raw_data = {k: str(v) if v is not None else None 
                               for k, v in trade.items() 
                               if k != 'raw_xml'}
                    
                    cur.execute("""
                        INSERT INTO staging.flex_trades (
                            import_id, ibkr_trade_id, ibkr_order_id, ibkr_exec_id,
                            ibkr_perm_id, account_id, symbol, underlying,
                            asset_category, sub_category, trade_date, trade_time,
                            settle_date, quantity, price, proceeds, commission,
                            fees, realized_pnl, fx_rate, strike, expiry, put_call,
                            raw_data
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        self.import_id,
                        trade['ibkr_trade_id'],
                        trade['ibkr_order_id'],
                        trade['ibkr_exec_id'],
                        trade['ibkr_perm_id'],
                        trade['account_id'],
                        trade['symbol'],
                        trade['underlying'],
                        trade['asset_category'],
                        trade['sub_category'],
                        trade['trade_date'],
                        trade['trade_time'],
                        trade['settle_date'],
                        trade['quantity'],
                        trade['price'],
                        trade['proceeds'],
                        trade['commission'],
                        trade['fees'],
                        trade['realized_pnl'],
                        trade['fx_rate'],
                        trade['strike'],
                        trade['expiry'],
                        trade['put_call'],
                        Json(raw_data)
                    ))
                
                conn.commit()
                logger.info(f"Staged {len(trades)} trades")
                return True
                
        except Exception as e:
            logger.error(f"Failed to stage trades: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _validate_staged_trades(self) -> Dict:
        """Run validation on staged trades"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Run validation function
                cur.execute("SELECT * FROM staging.validate_import(%s)", (self.import_id,))
                results = cur.fetchall()
                
                # Count errors and warnings
                summary = {
                    'errors': 0,
                    'warnings': 0,
                    'info': 0
                }
                
                for result in results:
                    logger.info(f"Validation {result['rule_name']}: "
                              f"{result['error_count']} {result['severity']}")
                    
                    if result['severity'] == 'ERROR':
                        summary['errors'] += result['error_count']
                    elif result['severity'] == 'WARNING':
                        summary['warnings'] += result['error_count']
                    else:
                        summary['info'] += result['error_count']
                
                return summary
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {'errors': -1}
        finally:
            conn.close()
    
    def _process_staged_trades(self) -> bool:
        """Process validated trades from staging to production"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get all staged trades that passed validation
                cur.execute("""
                    SELECT * FROM staging.flex_trades
                    WHERE import_id = %s
                    AND validation_status IN ('PASSED', 'WARNING')
                    AND NOT processed
                    ORDER BY trade_date, trade_time
                """, (self.import_id,))
                
                staged_trades = cur.fetchall()
                
                for staged in staged_trades:
                    action = self._process_single_trade(cur, staged)
                    
                    # Record mapping
                    if action['trade_id']:
                        cur.execute("""
                            INSERT INTO staging.import_mappings (
                                import_id, staging_id, trade_id, action_taken, reason
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            self.import_id,
                            staged['staging_id'],
                            action['trade_id'],
                            action['action'],
                            action['reason']
                        ))
                    
                    # Mark as processed
                    cur.execute("""
                        UPDATE staging.flex_trades
                        SET processed = TRUE, processed_at = NOW()
                        WHERE staging_id = %s
                    """, (staged['staging_id'],))
                    
                    # Update stats
                    if action['action'] == 'INSERTED':
                        self.stats['imported'] += 1
                    elif action['action'] == 'UPDATED':
                        self.stats['updated'] += 1
                    elif action['action'] == 'SKIPPED':
                        self.stats['skipped'] += 1
                    else:
                        self.stats['errors'] += 1
                
                conn.commit()
                logger.info(f"Processed {len(staged_trades)} trades")
                return True
                
        except Exception as e:
            logger.error(f"Failed to process trades: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _process_single_trade(self, cur, staged: Dict) -> Dict:
        """Process a single staged trade"""
        try:
            # Check if trade already exists
            cur.execute("""
                SELECT trade_id FROM trading.trades
                WHERE ibkr_order_id = %s
                AND DATE(entry_time) = %s
            """, (int(staged['ibkr_order_id']), staged['trade_date']))
            
            existing = cur.fetchone()
            
            if existing:
                # Log to audit table
                cur.execute("""
                    SELECT trading.audit_trade_change(
                        %s, 'UPDATE', NULL, %s, NULL, 'Historical import duplicate check'
                    )
                """, (existing['trade_id'], Json(staged)))
                
                return {
                    'trade_id': existing['trade_id'],
                    'action': 'SKIPPED',
                    'reason': 'Trade already exists'
                }
            
            # Determine trade direction and prepare data
            quantity = staged['quantity']
            is_opening = quantity < 0  # Selling options = opening trade
            
            # Create new trade
            trade_id = str(uuid.uuid4())
            
            # Combine date and time
            if staged['trade_time']:
                entry_time = datetime.combine(staged['trade_date'], staged['trade_time'])
            else:
                entry_time = datetime.combine(staged['trade_date'], datetime.min.time())
            
            # For closed trades (buy to close), we need exit time
            exit_time = None
            exit_price = None
            status = 'open'
            
            if not is_opening:  # This is a closing trade
                exit_time = entry_time
                exit_price = staged['price']
                status = 'closed'
            
            cur.execute("""
                INSERT INTO trading.trades (
                    trade_id, ibkr_order_id, ibkr_exec_id, ibkr_perm_id,
                    symbol, strike_price, option_type, expiration,
                    quantity, entry_time, entry_price, entry_commission,
                    exit_time, exit_price, exit_commission, status,
                    realized_pnl, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                trade_id,
                int(staged['ibkr_order_id']) if staged['ibkr_order_id'] else None,
                staged['ibkr_exec_id'],
                int(staged['ibkr_perm_id']) if staged['ibkr_perm_id'] else None,
                staged['symbol'],
                staged['strike'],
                'PUT' if staged['put_call'] in ('P', 'PUT') else 'CALL',
                staged['expiry'],
                quantity,
                entry_time,
                staged['price'],
                staged['commission'],
                exit_time,
                exit_price,
                staged['commission'] if exit_time else None,
                status,
                staged['realized_pnl'],
                datetime.now()
            ))
            
            # Log to audit
            cur.execute("""
                SELECT trading.audit_trade_change(
                    %s, 'INSERT', NULL, %s, NULL, 'Historical import'
                )
            """, (trade_id, Json(staged)))
            
            return {
                'trade_id': trade_id,
                'action': 'INSERTED',
                'reason': 'New trade imported'
            }
            
        except Exception as e:
            logger.error(f"Failed to process trade {staged['staging_id']}: {e}")
            return {
                'trade_id': None,
                'action': 'ERROR',
                'reason': str(e)
            }
    
    def _match_trades(self) -> int:
        """Match opening and closing trades"""
        conn = get_trade_db_connection()
        matched_count = 0
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get unmatched closed trades
                cur.execute("""
                    SELECT * FROM trading.unmatched_trades
                    WHERE is_unmatched = TRUE
                    AND status = 'closed'
                    ORDER BY entry_time
                """)
                
                unmatched = cur.fetchall()
                logger.info(f"Found {len(unmatched)} unmatched trades to process")
                
                for trade in unmatched:
                    # Skip if this is an opening trade
                    if trade['quantity'] < 0:
                        continue
                    
                    # Find matching opening trade (FIFO)
                    cur.execute("""
                        SELECT trade_id, entry_price, entry_commission
                        FROM trading.trades t
                        WHERE t.symbol = %s
                        AND t.strike_price = %s
                        AND t.option_type = %s
                        AND t.expiration = %s
                        AND t.quantity < 0  -- Opening trades are negative
                        AND t.entry_time < %s  -- Must be opened before closing
                        AND NOT EXISTS (
                            SELECT 1 FROM trading.matched_trades mt
                            WHERE mt.opening_trade_id = t.trade_id
                        )
                        ORDER BY t.entry_time
                        LIMIT 1
                    """, (
                        trade['symbol'],
                        trade['strike_price'],
                        trade['option_type'],
                        trade['expiration'],
                        trade['exit_time']
                    ))
                    
                    opening_trade = cur.fetchone()
                    
                    if opening_trade:
                        # Create match
                        match_quantity = abs(trade['quantity'])
                        opening_price = opening_trade['entry_price']
                        closing_price = trade['exit_price']
                        
                        # Calculate P&L
                        pnl = (opening_price - closing_price) * match_quantity * 100
                        commissions = opening_trade['entry_commission'] + (trade['exit_commission'] or 0)
                        
                        cur.execute("""
                            INSERT INTO trading.matched_trades (
                                opening_trade_id, closing_trade_id, match_method,
                                quantity_matched, opening_price, closing_price,
                                realized_pnl, commissions_total, notes
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            opening_trade['trade_id'],
                            trade['trade_id'],
                            'FIFO',
                            match_quantity,
                            opening_price,
                            closing_price,
                            pnl - commissions,
                            commissions,
                            'Historical import auto-match'
                        ))
                        
                        matched_count += 1
                
                conn.commit()
                self.stats['matched_pairs'] = matched_count
                logger.info(f"Matched {matched_count} trade pairs")
                
        except Exception as e:
            logger.error(f"Failed to match trades: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return matched_count
    
    def _update_import_status(self, status: str, message: str = None):
        """Update import log status"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trading.import_log
                    SET status = %s,
                        error_message = %s,
                        completed_at = %s,
                        trades_imported = %s,
                        trades_updated = %s,
                        trades_skipped = %s,
                        record_count = %s
                    WHERE import_id = %s
                """, (
                    status,
                    message,
                    datetime.now() if status in ('COMPLETED', 'FAILED') else None,
                    self.stats['imported'],
                    self.stats['updated'],
                    self.stats['skipped'],
                    self.stats['total_trades'],
                    self.import_id
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update import status: {e}")
        finally:
            conn.close()
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse IBKR date format"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except:
            return None
    
    def _parse_decimal(self, value: Optional[str]) -> Optional[Decimal]:
        """Parse decimal value"""
        if not value:
            return None
        try:
            return Decimal(value)
        except:
            return None
    
    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse integer value"""
        if not value:
            return None
        try:
            return int(value)
        except:
            return None


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Import historical IBKR trades')
    parser.add_argument('--start-date', type=str, default='2025-06-20',
                        help='Start date for import (YYYY-MM-DD), defaults to June 20, 2025')
    parser.add_argument('--end-date', type=str, default=None,
                        help='End date for import (YYYY-MM-DD), defaults to today')
    parser.add_argument('--force', action='store_true',
                        help='Force import even if data exists')
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date() if args.end_date else date.today()
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    # Validate date range
    if start_date > end_date:
        logger.error("Start date must be before end date")
        sys.exit(1)
    
    if start_date > date.today():
        logger.error("Start date cannot be in the future")
        sys.exit(1)
    
    # Check for existing import
    if not args.force:
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM trading.import_log
                    WHERE source_type = 'FLEX_QUERY'
                    AND period_start <= %s
                    AND period_end >= %s
                    AND status = 'COMPLETED'
                """, (start_date, end_date))
                
                if cur.fetchone()[0] > 0:
                    logger.error("Import already exists for this period. Use --force to override")
                    sys.exit(1)
        finally:
            conn.close()
    
    # Run import
    importer = HistoricalTradeImporter(start_date, end_date)
    success = importer.run_import()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()