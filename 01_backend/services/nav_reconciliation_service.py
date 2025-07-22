#!/usr/bin/env python3
"""
NAV Reconciliation Service
Ensures daily NAV changes are fully explained by trading P&L and cash movements
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor

from 01_backend.database.trade_db import get_trade_db_connection

logger = logging.getLogger(__name__)

class NAVReconciliationService:
    """Service for reconciling daily NAV changes"""
    
    def __init__(self):
        self.tolerance = Decimal("0.01")  # $0.01 tolerance for rounding
    
    def reconcile_date(self, reconcile_date: date) -> Dict[str, any]:
        """Reconcile NAV for a specific date"""
        conn = get_trade_db_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get NAV snapshot
                nav_data = self._get_nav_data(cursor, reconcile_date)
                if not nav_data:
                    return {"status": "error", "message": f"No NAV data for {reconcile_date}"}
                
                # Get trading P&L
                trading_pnl = self._get_trading_pnl(cursor, reconcile_date)
                
                # Get cash movements
                cash_movements = self._get_cash_movements(cursor, reconcile_date)
                
                # Get fees and interest
                fees_interest = self._get_fees_interest(cursor, reconcile_date)
                
                # Create or update reconciliation record
                reconciliation = self._create_reconciliation(
                    cursor, reconcile_date, nav_data, trading_pnl, 
                    cash_movements, fees_interest
                )
                
                conn.commit()
                
                # Check if balanced
                if reconciliation['is_balanced']:
                    logger.info(f"✅ {reconcile_date} reconciliation balanced")
                    return {
                        "status": "balanced",
                        "date": reconcile_date,
                        "discrepancy": float(reconciliation['discrepancy'])
                    }
                else:
                    logger.warning(f"⚠️ {reconcile_date} reconciliation discrepancy: ${reconciliation['discrepancy']}")
                    return {
                        "status": "discrepancy",
                        "date": reconcile_date,
                        "discrepancy": float(reconciliation['discrepancy']),
                        "details": reconciliation
                    }
                    
        except Exception as e:
            logger.error(f"Error reconciling {reconcile_date}: {e}")
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()
    
    def _get_nav_data(self, cursor, reconcile_date: date) -> Optional[Dict]:
        """Get NAV snapshot data"""
        cursor.execute("""
            SELECT 
                opening_nav,
                closing_nav,
                opening_cash,
                closing_cash,
                opening_positions_value,
                closing_positions_value,
                trading_pnl,
                commissions_paid,
                interest_earned,
                fees_charged
            FROM portfolio.daily_nav_snapshots
            WHERE snapshot_date = %s
        """, (reconcile_date,))
        
        return cursor.fetchone()
    
    def _get_trading_pnl(self, cursor, reconcile_date: date) -> Decimal:
        """Get total trading P&L for the day"""
        # From trade lifecycles
        cursor.execute("""
            SELECT COALESCE(SUM(net_pnl), 0) as daily_pnl
            FROM trading.trade_lifecycles
            WHERE close_date = %s
        """, (reconcile_date,))
        
        result = cursor.fetchone()
        lifecycle_pnl = result['daily_pnl'] if result else Decimal("0")
        
        # From daily summaries (if different)
        cursor.execute("""
            SELECT net_pnl
            FROM trading.daily_summaries
            WHERE trade_date = %s
        """, (reconcile_date,))
        
        result = cursor.fetchone()
        summary_pnl = result['net_pnl'] if result else Decimal("0")
        
        # Use the more detailed source or reconcile if different
        if lifecycle_pnl != summary_pnl and summary_pnl != 0:
            logger.warning(f"P&L mismatch for {reconcile_date}: lifecycles=${lifecycle_pnl}, summary=${summary_pnl}")
        
        return lifecycle_pnl or summary_pnl
    
    def _get_cash_movements(self, cursor, reconcile_date: date) -> Dict[str, Decimal]:
        """Get cash movements for the day"""
        cursor.execute("""
            SELECT 
                movement_type,
                SUM(amount) as total_amount
            FROM portfolio.cash_movements
            WHERE movement_date = %s 
                AND status = 'COMPLETED'
            GROUP BY movement_type
        """, (reconcile_date,))
        
        movements = {"deposits": Decimal("0"), "withdrawals": Decimal("0")}
        
        for row in cursor.fetchall():
            if row['movement_type'] == 'DEPOSIT':
                movements['deposits'] = row['total_amount']
            elif row['movement_type'] == 'WITHDRAWAL':
                movements['withdrawals'] = abs(row['total_amount'])
        
        return movements
    
    def _get_fees_interest(self, cursor, reconcile_date: date) -> Dict[str, Decimal]:
        """Get fees and interest for the day"""
        cursor.execute("""
            SELECT 
                SUM(amount) FILTER (WHERE movement_type = 'FEE') as fees,
                SUM(amount) FILTER (WHERE movement_type = 'INTEREST') as interest
            FROM portfolio.cash_movements
            WHERE movement_date = %s 
                AND status = 'COMPLETED'
                AND movement_type IN ('FEE', 'INTEREST')
        """, (reconcile_date,))
        
        result = cursor.fetchone()
        return {
            "fees": abs(result['fees'] or Decimal("0")),
            "interest": result['interest'] or Decimal("0")
        }
    
    def _create_reconciliation(self, cursor, reconcile_date: date, nav_data: Dict,
                             trading_pnl: Decimal, cash_movements: Dict, 
                             fees_interest: Dict) -> Dict:
        """Create or update reconciliation record"""
        
        # Use NAV data or fetch from cash movements
        opening_nav = nav_data['opening_nav']
        closing_nav = nav_data['closing_nav']
        
        # Combine all fees
        total_fees = (nav_data.get('commissions_paid', 0) + 
                     nav_data.get('fees_charged', 0) + 
                     fees_interest['fees'])
        
        # Create reconciliation
        cursor.execute("""
            INSERT INTO portfolio.nav_reconciliation (
                reconciliation_date,
                opening_nav,
                actual_closing_nav,
                trading_pnl,
                deposits,
                withdrawals,
                fees,
                interest,
                reconciled_by,
                reconciled_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (reconciliation_date) DO UPDATE SET
                actual_closing_nav = EXCLUDED.actual_closing_nav,
                trading_pnl = EXCLUDED.trading_pnl,
                deposits = EXCLUDED.deposits,
                withdrawals = EXCLUDED.withdrawals,
                fees = EXCLUDED.fees,
                interest = EXCLUDED.interest,
                reconciled_by = EXCLUDED.reconciled_by,
                reconciled_at = EXCLUDED.reconciled_at,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """, (
            reconcile_date,
            opening_nav,
            closing_nav,
            trading_pnl,
            cash_movements['deposits'],
            cash_movements['withdrawals'],
            total_fees,
            fees_interest['interest'] + nav_data.get('interest_earned', 0),
            'Automated',
            datetime.now()
        ))
        
        return cursor.fetchone()
    
    def reconcile_range(self, start_date: date, end_date: date) -> List[Dict]:
        """Reconcile a range of dates"""
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            result = self.reconcile_date(current_date)
            results.append(result)
            current_date += timedelta(days=1)
        
        return results
    
    def get_reconciliation_summary(self, days_back: int = 30) -> Dict:
        """Get summary of recent reconciliations"""
        conn = get_trade_db_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_days,
                        COUNT(*) FILTER (WHERE is_balanced) as balanced_days,
                        COUNT(*) FILTER (WHERE NOT is_balanced) as unbalanced_days,
                        SUM(ABS(discrepancy)) as total_discrepancy,
                        MAX(ABS(discrepancy)) as max_discrepancy,
                        AVG(ABS(discrepancy)) as avg_discrepancy
                    FROM portfolio.nav_reconciliation
                    WHERE reconciliation_date >= CURRENT_DATE - INTERVAL '%s days'
                """, (days_back,))
                
                summary = cursor.fetchone()
                
                # Get details of unbalanced days
                cursor.execute("""
                    SELECT 
                        reconciliation_date,
                        opening_nav,
                        actual_closing_nav,
                        calculated_closing_nav,
                        discrepancy,
                        trading_pnl,
                        deposits,
                        withdrawals
                    FROM portfolio.nav_reconciliation
                    WHERE reconciliation_date >= CURRENT_DATE - INTERVAL '%s days'
                        AND NOT is_balanced
                    ORDER BY ABS(discrepancy) DESC
                """, (days_back,))
                
                unbalanced_days = cursor.fetchall()
                
                return {
                    "summary": summary,
                    "unbalanced_days": unbalanced_days,
                    "status": "healthy" if summary['unbalanced_days'] == 0 else "needs_review"
                }
                
        finally:
            conn.close()
    
    def auto_reconcile_missing_days(self) -> List[Dict]:
        """Find and reconcile any missing days"""
        conn = get_trade_db_connection()
        results = []
        
        try:
            with conn.cursor() as cursor:
                # Find days with NAV data but no reconciliation
                cursor.execute("""
                    SELECT DISTINCT n.snapshot_date
                    FROM portfolio.daily_nav_snapshots n
                    LEFT JOIN portfolio.nav_reconciliation r 
                        ON n.snapshot_date = r.reconciliation_date
                    WHERE r.reconciliation_date IS NULL
                        AND n.closing_nav IS NOT NULL
                    ORDER BY n.snapshot_date
                """)
                
                missing_days = [row[0] for row in cursor.fetchall()]
                
                if missing_days:
                    logger.info(f"Found {len(missing_days)} days needing reconciliation")
                    
                    for day in missing_days:
                        result = self.reconcile_date(day)
                        results.append(result)
                else:
                    logger.info("All days are reconciled")
                    
        finally:
            conn.close()
        
        return results

# Singleton instance
nav_reconciliation_service = NAVReconciliationService()