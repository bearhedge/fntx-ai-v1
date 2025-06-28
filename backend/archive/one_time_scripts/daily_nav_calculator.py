#!/usr/bin/env python3
"""
Daily NAV Calculator Service
Calculates daily NAV values from transaction history
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
from collections import defaultdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.database.trade_db import get_trade_db_connection

logger = logging.getLogger(__name__)

class DailyNAVCalculator:
    """Calculates daily NAV from transaction history"""
    
    def __init__(self):
        self.base_nav = Decimal('10791.86')  # Starting NAV from IBKR
        self.base_date = date(2025, 5, 28)    # Starting date
        
    def calculate_daily_nav(self, from_date: date, to_date: date) -> Dict[date, Dict[str, Decimal]]:
        """Calculate daily NAV values from transactions"""
        
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get all transactions in date range
                transactions = self._get_all_transactions(cursor, from_date, to_date)
                
                # Group transactions by date
                daily_transactions = defaultdict(list)
                for trans in transactions:
                    trans_date = trans['date']
                    daily_transactions[trans_date].append(trans)
                
                # Calculate daily NAV
                daily_nav = {}
                running_nav = self.base_nav
                
                # Start from base date or from_date, whichever is later
                current_date = max(self.base_date, from_date)
                
                while current_date <= to_date:
                    opening_nav = running_nav
                    
                    # Apply today's transactions
                    daily_change = Decimal('0')
                    daily_pnl = Decimal('0')
                    daily_commissions = Decimal('0')
                    daily_deposits = Decimal('0')
                    daily_withdrawals = Decimal('0')
                    
                    if current_date in daily_transactions:
                        for trans in daily_transactions[current_date]:
                            if trans['type'] == 'trade':
                                daily_pnl += trans['pnl'] or Decimal('0')
                                daily_commissions += trans['commission'] or Decimal('0')
                            elif trans['type'] == 'deposit':
                                daily_deposits += trans['amount']
                            elif trans['type'] == 'withdrawal':
                                daily_withdrawals += trans['amount']
                    
                    # Calculate net change
                    daily_change = daily_pnl - daily_commissions + daily_deposits - daily_withdrawals
                    closing_nav = opening_nav + daily_change
                    
                    # Store daily NAV data
                    daily_nav[current_date] = {
                        'opening_nav': opening_nav,
                        'closing_nav': closing_nav,
                        'trading_pnl': daily_pnl,
                        'commissions': daily_commissions,
                        'deposits': daily_deposits,
                        'withdrawals': daily_withdrawals,
                        'net_change': daily_change
                    }
                    
                    # Update running NAV for next day
                    running_nav = closing_nav
                    current_date += timedelta(days=1)
                
                return daily_nav
                
        finally:
            conn.close()
    
    def _get_all_transactions(self, cursor, from_date: date, to_date: date) -> List[Dict]:
        """Get all transactions (trades, deposits, withdrawals) in date range"""
        transactions = []
        
        # Get trades
        cursor.execute("""
            SELECT 
                DATE(entry_time) as trans_date,
                'trade' as trans_type,
                realized_pnl as pnl,
                (entry_commission + COALESCE(exit_commission, 0)) as commission,
                0 as amount
            FROM trading.trades
            WHERE DATE(entry_time) BETWEEN %s AND %s
            ORDER BY entry_time
        """, (from_date, to_date))
        
        for row in cursor.fetchall():
            transactions.append({
                'date': row[0],
                'type': row[1],
                'pnl': Decimal(str(row[2])) if row[2] else Decimal('0'),
                'commission': Decimal(str(row[3])) if row[3] else Decimal('0'),
                'amount': Decimal('0')
            })
        
        # Get cash movements
        cursor.execute("""
            SELECT 
                movement_date as trans_date,
                LOWER(movement_type) as trans_type,
                amount
            FROM portfolio.cash_movements
            WHERE movement_date BETWEEN %s AND %s
            ORDER BY movement_date
        """, (from_date, to_date))
        
        for row in cursor.fetchall():
            transactions.append({
                'date': row[0],
                'type': row[1],
                'pnl': Decimal('0'),
                'commission': Decimal('0'),
                'amount': Decimal(str(row[2]))
            })
        
        # Sort by date
        transactions.sort(key=lambda x: x['date'])
        return transactions
    
    def update_database_nav(self, daily_nav: Dict[date, Dict[str, Decimal]]):
        """Update database with calculated daily NAV values"""
        conn = get_trade_db_connection()
        try:
            with conn.cursor() as cursor:
                for nav_date, nav_data in daily_nav.items():
                    # Check if snapshot exists
                    cursor.execute("""
                        SELECT snapshot_id FROM portfolio.daily_nav_snapshots
                        WHERE snapshot_date = %s
                    """, (nav_date,))
                    
                    if cursor.fetchone():
                        # Update existing
                        cursor.execute("""
                            UPDATE portfolio.daily_nav_snapshots
                            SET opening_nav = %s,
                                closing_nav = %s,
                                opening_cash = %s,
                                closing_cash = %s,
                                trading_pnl = %s,
                                commissions_paid = %s,
                                source = 'calculated',
                                updated_at = NOW()
                            WHERE snapshot_date = %s
                        """, (
                            nav_data['opening_nav'],
                            nav_data['closing_nav'],
                            nav_data['opening_nav'],  # Using NAV as cash for now
                            nav_data['closing_nav'],  # Using NAV as cash for now
                            nav_data['trading_pnl'],
                            nav_data['commissions'],
                            nav_date
                        ))
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO portfolio.daily_nav_snapshots (
                                snapshot_date, opening_nav, closing_nav,
                                opening_cash, closing_cash,
                                trading_pnl, commissions_paid, source
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            nav_date,
                            nav_data['opening_nav'],
                            nav_data['closing_nav'],
                            nav_data['opening_nav'],  # Using NAV as cash for now
                            nav_data['closing_nav'],  # Using NAV as cash for now
                            nav_data['trading_pnl'],
                            nav_data['commissions'],
                            'calculated'
                        ))
                
                conn.commit()
                logger.info(f"Updated {len(daily_nav)} daily NAV snapshots")
                
        finally:
            conn.close()
    
    def validate_against_ibkr(self, end_date: date, expected_nav: Decimal) -> Tuple[bool, Decimal]:
        """Validate calculated NAV against IBKR reported NAV"""
        # Calculate NAV up to end date
        daily_nav = self.calculate_daily_nav(self.base_date, end_date)
        
        if end_date in daily_nav:
            calculated_nav = daily_nav[end_date]['closing_nav']
            difference = calculated_nav - expected_nav
            
            logger.info(f"NAV Validation for {end_date}:")
            logger.info(f"  Calculated: {calculated_nav:.2f}")
            logger.info(f"  Expected (IBKR): {expected_nav:.2f}")
            logger.info(f"  Difference: {difference:.2f}")
            
            # Consider valid if within 0.01 HKD
            is_valid = abs(difference) < Decimal('0.01')
            return is_valid, difference
        
        return False, Decimal('0')


# Convenience function for direct execution
def recalculate_all_nav():
    """Recalculate all NAV values from base date to today"""
    calculator = DailyNAVCalculator()
    
    # Calculate from base date to today
    daily_nav = calculator.calculate_daily_nav(
        date(2025, 5, 28),
        date.today()
    )
    
    # Update database
    calculator.update_database_nav(daily_nav)
    
    # Validate against IBKR ending NAV
    is_valid, diff = calculator.validate_against_ibkr(
        date(2025, 6, 26),
        Decimal('80905.79')
    )
    
    if is_valid:
        logger.info("NAV calculation validated successfully!")
    else:
        logger.warning(f"NAV calculation has discrepancy of {diff}")
    
    return daily_nav


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    nav_data = recalculate_all_nav()
    
    # Print summary
    print("\nDaily NAV Summary:")
    for nav_date in sorted(nav_data.keys())[-10:]:  # Last 10 days
        data = nav_data[nav_date]
        print(f"{nav_date}: {data['opening_nav']:.2f} → {data['closing_nav']:.2f} (Change: {data['net_change']:+.2f})")