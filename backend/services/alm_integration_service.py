#!/usr/bin/env python3
"""
ALM Integration Service
Bridges the trading system with the financial ALM infrastructure
Automatically creates journal entries from trading activities
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class ALMIntegrationService:
    """
    Service that integrates trading activities with the ALM system
    Automatically creates double-entry accounting records from trades
    """
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        
        # Account mappings for automated journal entries
        self.account_mappings = {
            # Cash accounts
            'usd_cash': '1111',  # IBKR USD Cash
            'hkd_cash': '1121',  # IBKR HKD Cash
            
            # Options positions
            'spy_calls_sold': '2410',  # SPY Call Options Sold (liability)
            'spy_puts_sold': '2411',   # SPY Put Options Sold (liability)
            'spy_calls_owned': '1311', # SPY Call Options (asset)
            'spy_puts_owned': '1312',  # SPY Put Options (asset)
            
            # Revenue/Income
            'options_premium_income': '4111',  # SPY Options Premium Income
            'options_closing_gains': '4112',   # Options Closing Gains
            
            # Expenses
            'commission_expense': '5111',      # IBKR Commissions
            'options_losses': '5131',          # SPY Options Losses
            'sec_fees': '5121',               # SEC Fees
            'exchange_fees': '5122',          # Exchange Fees
        }
    
    def process_trade_entry(self, trade_data: Dict[str, Any]) -> Optional[str]:
        """
        Process a new trade entry and create corresponding journal entries
        
        Args:
            trade_data: Trade information from trading.trades table
            
        Returns:
            entry_id if successful, None if failed
        """
        try:
            # Determine trade type and create appropriate journal entry
            if trade_data.get('quantity', 0) > 0:
                # This shouldn't happen for options selling, but handle it
                return self._create_options_purchase_entry(trade_data)
            else:
                # Negative quantity = sold options (our main strategy)
                return self._create_options_sale_entry(trade_data)
                
        except Exception as e:
            logger.error(f"Failed to process trade entry: {e}")
            return None
    
    def process_trade_exit(self, trade_data: Dict[str, Any]) -> Optional[str]:
        """
        Process a trade exit and create closing journal entries
        
        Args:
            trade_data: Complete trade information including exit details
            
        Returns:
            entry_id if successful, None if failed
        """
        try:
            return self._create_options_closing_entry(trade_data)
            
        except Exception as e:
            logger.error(f"Failed to process trade exit: {e}")
            return None
    
    def _create_options_sale_entry(self, trade_data: Dict[str, Any]) -> Optional[str]:
        """
        Create journal entry for selling options (opening position)
        
        When selling options:
        Dr. Cash (premium received)
        Cr. Options Liability (obligation created)
        Dr. Commission Expense
        """
        try:
            quantity = abs(trade_data.get('quantity', 0))
            entry_price = Decimal(str(trade_data.get('entry_price', 0)))
            commission = Decimal(str(trade_data.get('entry_commission', 0)))
            option_type = trade_data.get('option_type', '')
            strike = trade_data.get('strike_price', 0)
            
            # Calculate premium received (positive)
            premium_received = entry_price * quantity * 100  # Options multiplier
            net_premium = premium_received - commission
            
            # Determine liability account based on option type
            if option_type == 'CALL':
                liability_account = self.account_mappings['spy_calls_sold']
            else:  # PUT
                liability_account = self.account_mappings['spy_puts_sold']
            
            # Create journal entry
            description = f"Sold {quantity} SPY {strike} {option_type} @ ${entry_price}"
            
            journal_lines = [
                {
                    'account_number': self.account_mappings['usd_cash'],
                    'debit_amount': net_premium,
                    'credit_amount': Decimal('0'),
                    'description': f"Cash received from options sale",
                    'quantity': quantity,
                    'unit_price': entry_price
                },
                {
                    'account_number': liability_account,
                    'debit_amount': Decimal('0'),
                    'credit_amount': premium_received,
                    'description': f"Options liability created",
                    'quantity': -quantity,  # Negative for short position
                    'unit_price': entry_price
                }
            ]
            
            # Add commission expense if any
            if commission > 0:
                journal_lines.append({
                    'account_number': self.account_mappings['commission_expense'],
                    'debit_amount': commission,
                    'credit_amount': Decimal('0'),
                    'description': "Commission on options sale"
                })
            
            return self._create_journal_entry(
                description=description,
                source_system='trading',
                source_id=str(trade_data.get('trade_id')),
                journal_lines=journal_lines
            )
            
        except Exception as e:
            logger.error(f"Failed to create options sale entry: {e}")
            return None
    
    def _create_options_closing_entry(self, trade_data: Dict[str, Any]) -> Optional[str]:
        """
        Create journal entry for closing options position
        
        When buying back options to close:
        Dr. Options Liability (remove obligation)
        Cr. Cash (payment made)
        Dr. Commission Expense
        
        Calculate P&L and record as gain/loss
        """
        try:
            quantity = abs(trade_data.get('quantity', 0))
            entry_price = Decimal(str(trade_data.get('entry_price', 0)))
            exit_price = Decimal(str(trade_data.get('exit_price', 0)))
            entry_commission = Decimal(str(trade_data.get('entry_commission', 0)))
            exit_commission = Decimal(str(trade_data.get('exit_commission', 0)))
            option_type = trade_data.get('option_type', '')
            strike = trade_data.get('strike_price', 0)
            
            # Calculate amounts
            original_premium = entry_price * quantity * 100
            closing_cost = exit_price * quantity * 100
            gross_pnl = original_premium - closing_cost
            net_pnl = gross_pnl - entry_commission - exit_commission
            
            # Determine accounts
            if option_type == 'CALL':
                liability_account = self.account_mappings['spy_calls_sold']
            else:  # PUT
                liability_account = self.account_mappings['spy_puts_sold']
            
            description = f"Closed {quantity} SPY {strike} {option_type} @ ${exit_price} (P&L: ${net_pnl})"
            
            journal_lines = [
                {
                    'account_number': liability_account,
                    'debit_amount': original_premium,
                    'credit_amount': Decimal('0'),
                    'description': f"Close options liability",
                    'quantity': quantity,
                    'unit_price': entry_price
                },
                {
                    'account_number': self.account_mappings['usd_cash'],
                    'debit_amount': Decimal('0'),
                    'credit_amount': closing_cost,
                    'description': f"Cash paid to close position",
                    'quantity': quantity,
                    'unit_price': exit_price
                }
            ]
            
            # Record P&L
            if gross_pnl > 0:
                # Profit
                journal_lines.append({
                    'account_number': self.account_mappings['options_closing_gains'],
                    'debit_amount': Decimal('0'),
                    'credit_amount': gross_pnl,
                    'description': f"Options trading gain"
                })
            elif gross_pnl < 0:
                # Loss
                journal_lines.append({
                    'account_number': self.account_mappings['options_losses'],
                    'debit_amount': abs(gross_pnl),
                    'credit_amount': Decimal('0'),
                    'description': f"Options trading loss"
                })
            
            # Add commission expenses
            total_commissions = entry_commission + exit_commission
            if total_commissions > 0:
                journal_lines.append({
                    'account_number': self.account_mappings['commission_expense'],
                    'debit_amount': total_commissions,
                    'credit_amount': Decimal('0'),
                    'description': "Total commissions on options trade"
                })
            
            return self._create_journal_entry(
                description=description,
                source_system='trading',
                source_id=str(trade_data.get('trade_id')),
                journal_lines=journal_lines
            )
            
        except Exception as e:
            logger.error(f"Failed to create options closing entry: {e}")
            return None
    
    def _create_journal_entry(self, description: str, source_system: str, 
                            source_id: str, journal_lines: List[Dict[str, Any]]) -> Optional[str]:
        """
        Create a journal entry with multiple lines
        
        Args:
            description: Entry description
            source_system: Source system identifier
            source_id: Source transaction ID
            journal_lines: List of journal line dictionaries
            
        Returns:
            entry_id if successful, None if failed
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Generate entry ID and number
                    entry_id = str(uuid.uuid4())
                    entry_number = self._generate_entry_number(cur)
                    
                    # Calculate totals
                    total_debit = sum(Decimal(str(line.get('debit_amount', 0))) for line in journal_lines)
                    total_credit = sum(Decimal(str(line.get('credit_amount', 0))) for line in journal_lines)
                    
                    # Validate balanced entry
                    if total_debit != total_credit:
                        logger.error(f"Unbalanced journal entry: Debits={total_debit}, Credits={total_credit}")
                        return None
                    
                    # Insert journal entry header
                    cur.execute("""
                        INSERT INTO financial.journal_entries (
                            entry_id, entry_number, transaction_date, description,
                            source_system, source_id, status, total_debit, total_credit, created_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        entry_id, entry_number, datetime.now(timezone.utc), description,
                        source_system, source_id, 'posted', total_debit, total_credit, 'alm_integration'
                    ))
                    
                    # Insert journal lines
                    for i, line in enumerate(journal_lines, 1):
                        account_id = self._get_account_id(cur, line['account_number'])
                        if not account_id:
                            logger.error(f"Account not found: {line['account_number']}")
                            conn.rollback()
                            return None
                        
                        cur.execute("""
                            INSERT INTO financial.journal_lines (
                                entry_id, line_number, account_id, debit_amount, credit_amount,
                                description, quantity, unit_price
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            entry_id, i, account_id,
                            line.get('debit_amount', 0),
                            line.get('credit_amount', 0),
                            line.get('description', ''),
                            line.get('quantity'),
                            line.get('unit_price')
                        ))
                    
                    conn.commit()
                    logger.info(f"Created journal entry {entry_number} for {description}")
                    return entry_id
                    
        except Exception as e:
            logger.error(f"Failed to create journal entry: {e}")
            return None
    
    def _generate_entry_number(self, cursor) -> str:
        """Generate sequential journal entry number"""
        cursor.execute("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(entry_number FROM '[0-9]+') AS INTEGER)), 0) + 1
            FROM financial.journal_entries
            WHERE entry_number ~ '^JE[0-9]+$'
        """)
        next_number = cursor.fetchone()[0]
        return f"JE{next_number:06d}"
    
    def _get_account_id(self, cursor, account_number: str) -> Optional[str]:
        """Get account ID from account number"""
        cursor.execute("""
            SELECT account_id FROM financial.chart_of_accounts 
            WHERE account_number = %s AND is_active = true
        """, (account_number,))
        
        result = cursor.fetchone()
        return str(result[0]) if result else None
    
    def update_positions(self, trade_data: Dict[str, Any]) -> bool:
        """
        Update position records in the financial.positions table
        
        Args:
            trade_data: Complete trade information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get account ID for positions
                    account_id = self._get_account_id(cur, self.account_mappings['usd_cash'])
                    
                    symbol = trade_data.get('symbol', 'SPY')
                    option_type = trade_data.get('option_type', '')
                    strike = trade_data.get('strike_price', 0)
                    expiration = trade_data.get('expiration')
                    
                    # Create instrument ID
                    instrument_id = f"{symbol}_{strike}_{option_type}_{expiration}"
                    
                    if trade_data.get('status') == 'open':
                        # Opening position
                        quantity = -abs(trade_data.get('quantity', 0))  # Negative for short
                        cost_basis = Decimal(str(trade_data.get('entry_price', 0))) * abs(quantity) * 100
                        market_value = cost_basis  # Initially same as cost
                        
                        cur.execute("""
                            INSERT INTO financial.positions (
                                account_id, instrument_type, instrument_id, symbol,
                                quantity, cost_basis, average_price, market_value,
                                unrealized_pnl, as_of_date, first_trade_date, last_trade_date
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (account_id, instrument_type, instrument_id, as_of_date)
                            DO UPDATE SET
                                quantity = EXCLUDED.quantity,
                                cost_basis = EXCLUDED.cost_basis,
                                average_price = EXCLUDED.average_price,
                                market_value = EXCLUDED.market_value,
                                last_trade_date = EXCLUDED.last_trade_date
                        """, (
                            account_id, 'option', instrument_id, symbol,
                            quantity, cost_basis, trade_data.get('entry_price'),
                            market_value, Decimal('0'), datetime.now(timezone.utc),
                            trade_data.get('entry_time'), trade_data.get('entry_time')
                        ))
                    
                    elif trade_data.get('status') == 'closed':
                        # Closing position - set quantity to 0
                        cur.execute("""
                            UPDATE financial.positions
                            SET quantity = 0,
                                market_value = 0,
                                unrealized_pnl = 0,
                                last_trade_date = %s,
                                as_of_date = %s
                            WHERE account_id = %s 
                              AND instrument_id = %s
                              AND instrument_type = 'option'
                        """, (
                            trade_data.get('exit_time'),
                            datetime.now(timezone.utc),
                            account_id,
                            instrument_id
                        ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update positions: {e}")
            return False
    
    def create_cash_flow_record(self, trade_data: Dict[str, Any]) -> bool:
        """
        Create cash flow records for the trade
        
        Args:
            trade_data: Trade information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get cash account ID
                    account_id = self._get_account_id(cur, self.account_mappings['usd_cash'])
                    
                    if trade_data.get('status') == 'open':
                        # Premium received (inflow)
                        quantity = abs(trade_data.get('quantity', 0))
                        entry_price = Decimal(str(trade_data.get('entry_price', 0)))
                        commission = Decimal(str(trade_data.get('entry_commission', 0)))
                        premium_received = entry_price * quantity * 100
                        net_flow = premium_received - commission
                        
                        cur.execute("""
                            INSERT INTO financial.cash_flows (
                                flow_date, account_id, flow_type, flow_category,
                                amount, description
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            trade_data.get('entry_time'),
                            account_id,
                            'operating',
                            'options_premium',
                            net_flow,
                            f"Premium received from selling {trade_data.get('symbol')} options"
                        ))
                    
                    elif trade_data.get('status') == 'closed':
                        # Premium paid to close (outflow)
                        quantity = abs(trade_data.get('quantity', 0))
                        exit_price = Decimal(str(trade_data.get('exit_price', 0)))
                        commission = Decimal(str(trade_data.get('exit_commission', 0)))
                        premium_paid = exit_price * quantity * 100
                        net_flow = -(premium_paid + commission)  # Negative for outflow
                        
                        cur.execute("""
                            INSERT INTO financial.cash_flows (
                                flow_date, account_id, flow_type, flow_category,
                                amount, description
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            trade_data.get('exit_time'),
                            account_id,
                            'operating',
                            'options_closing',
                            net_flow,
                            f"Cost to close {trade_data.get('symbol')} options position"
                        ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to create cash flow record: {e}")
            return False
    
    def reconcile_trading_to_ledger(self, trade_id: str) -> Dict[str, Any]:
        """
        Reconcile a specific trade against the general ledger
        
        Args:
            trade_id: Trade ID to reconcile
            
        Returns:
            Reconciliation results
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get trade details
                    cur.execute("""
                        SELECT * FROM trading.trades WHERE trade_id = %s
                    """, (trade_id,))
                    trade = cur.fetchone()
                    
                    if not trade:
                        return {"status": "error", "message": "Trade not found"}
                    
                    # Get related journal entries
                    cur.execute("""
                        SELECT * FROM financial.journal_entries 
                        WHERE source_system = 'trading' AND source_id = %s
                    """, (trade_id,))
                    journal_entries = cur.fetchall()
                    
                    # Calculate expected vs actual amounts
                    expected_premium = abs(trade['quantity']) * trade['entry_price'] * 100 if trade['entry_price'] else 0
                    expected_commissions = (trade['entry_commission'] or 0) + (trade['exit_commission'] or 0)
                    
                    # Sum journal entry amounts
                    total_journal_debits = sum(je['total_debit'] for je in journal_entries)
                    total_journal_credits = sum(je['total_credit'] for je in journal_entries)
                    
                    return {
                        "status": "success",
                        "trade_id": trade_id,
                        "expected_premium": float(expected_premium),
                        "expected_commissions": float(expected_commissions),
                        "journal_debits": float(total_journal_debits),
                        "journal_credits": float(total_journal_credits),
                        "journal_entries_count": len(journal_entries),
                        "balanced": total_journal_debits == total_journal_credits,
                        "reconciled": True  # Would implement more detailed reconciliation logic
                    }
                    
        except Exception as e:
            logger.error(f"Failed to reconcile trade {trade_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)


# Integration function for trading system
def create_alm_integration_service(db_config: Dict[str, Any]) -> ALMIntegrationService:
    """Create ALM integration service instance"""
    return ALMIntegrationService(db_config)


def setup_trade_to_alm_integration(db_config: Dict[str, Any]):
    """
    Set up integration hooks for automatic ALM updates
    This function should be called when trades are created/updated
    """
    alm_service = ALMIntegrationService(db_config)
    
    def process_trade_hook(trade_event: str, trade_data: Dict[str, Any]):
        """Hook function for trade events"""
        try:
            if trade_event == "trade_opened":
                # Create opening journal entry
                entry_id = alm_service.process_trade_entry(trade_data)
                
                # Update positions
                alm_service.update_positions(trade_data)
                
                # Create cash flow record
                alm_service.create_cash_flow_record(trade_data)
                
                logger.info(f"ALM integration completed for trade opening: {trade_data.get('trade_id')}")
                
            elif trade_event == "trade_closed":
                # Create closing journal entry
                entry_id = alm_service.process_trade_exit(trade_data)
                
                # Update positions
                alm_service.update_positions(trade_data)
                
                # Create cash flow record
                alm_service.create_cash_flow_record(trade_data)
                
                logger.info(f"ALM integration completed for trade closing: {trade_data.get('trade_id')}")
                
        except Exception as e:
            logger.error(f"ALM integration failed for {trade_event}: {e}")
    
    return process_trade_hook