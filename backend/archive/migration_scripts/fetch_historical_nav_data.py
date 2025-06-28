#!/usr/bin/env python3
"""
Fetch historical NAV data and cash movements from IBKR
Specifically targeting June 25-26 data with T+1 settlement
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ibkr_flex_query_enhanced import flex_query_enhanced
from backend.services.ibkr_flex_query import flex_query_service
from backend.database.trade_db import get_trade_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_historical_trades():
    """Import June 25-26 trades which should now be settled"""
    logger.info("Fetching historical trades from IBKR...")
    
    # Get trades for the past 7 days to ensure we capture June 25-26
    trades = flex_query_service.get_complete_trade_history(days_back=7)
    
    if not trades:
        logger.warning("No trades found")
        return
    
    logger.info(f"Found {len(trades)} completed trades")
    
    conn = get_trade_db_connection()
    imported = 0
    
    try:
        with conn.cursor() as cursor:
            for trade in trades:
                # Check if it's June 25 or 26
                open_date = trade.get('open_datetime')
                if open_date and open_date.date() >= datetime(2025, 6, 25).date():
                    logger.info(f"Processing trade from {open_date.date()}: {trade['strike']} {trade['option_type']}")
                    
                    # Insert into trade_lifecycles table
                    cursor.execute("""
                        INSERT INTO trading.trade_lifecycles (
                            symbol,
                            strategy_type,
                            trade_direction,
                            open_date,
                            open_time,
                            open_strike,
                            open_option_type,
                            open_expiration,
                            open_quantity,
                            open_price,
                            open_commission,
                            open_exec_id,
                            open_order_id,
                            close_date,
                            close_time,
                            close_price,
                            close_commission,
                            close_reason,
                            close_exec_id,
                            close_order_id
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (open_exec_id) DO UPDATE SET
                            close_date = EXCLUDED.close_date,
                            close_time = EXCLUDED.close_time,
                            close_price = EXCLUDED.close_price,
                            close_commission = EXCLUDED.close_commission,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING lifecycle_id
                    """, (
                        trade['symbol'],
                        'naked_option',
                        'credit',
                        trade['open_datetime'].date(),
                        trade['open_datetime'],
                        trade['strike'],
                        trade['option_type'],
                        datetime.strptime(trade['expiry'], '%Y%m%d').date(),
                        trade['open_quantity'],
                        trade['open_price'],
                        trade['open_commission'],
                        trade['open_exec_id'],
                        trade['open_order_id'],
                        trade['close_datetime'].date() if trade.get('close_datetime') else None,
                        trade['close_datetime'],
                        trade['close_price'],
                        trade['close_commission'],
                        'expired' if trade.get('close_datetime') else None,
                        trade['close_exec_id'],
                        trade['close_order_id']
                    ))
                    
                    result = cursor.fetchone()
                    if result:
                        imported += 1
                        logger.info(f"Imported trade: {trade['strike']} {trade['option_type']}")
        
        # Update daily summaries
        cursor.execute("""
            INSERT INTO trading.daily_summaries (trade_date, trades_opened, trades_closed, 
                                               winning_trades, losing_trades, gross_pnl, net_pnl)
            SELECT 
                open_date,
                COUNT(*) FILTER (WHERE open_date = DATE '2025-06-25' OR open_date = DATE '2025-06-26'),
                COUNT(*) FILTER (WHERE close_date = DATE '2025-06-25' OR close_date = DATE '2025-06-26'),
                COUNT(*) FILTER (WHERE status = 'closed' AND net_pnl > 0),
                COUNT(*) FILTER (WHERE status = 'closed' AND net_pnl <= 0),
                COALESCE(SUM(gross_pnl) FILTER (WHERE status = 'closed'), 0),
                COALESCE(SUM(net_pnl) FILTER (WHERE status = 'closed'), 0)
            FROM trading.trade_lifecycles
            WHERE open_date IN (DATE '2025-06-25', DATE '2025-06-26')
            GROUP BY open_date
            ON CONFLICT (trade_date) DO UPDATE SET
                trades_opened = EXCLUDED.trades_opened,
                trades_closed = EXCLUDED.trades_closed,
                winning_trades = EXCLUDED.winning_trades,
                losing_trades = EXCLUDED.losing_trades,
                gross_pnl = EXCLUDED.gross_pnl,
                net_pnl = EXCLUDED.net_pnl,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        conn.commit()
        logger.info(f"Successfully imported {imported} historical trades")
        
    except Exception as e:
        logger.error(f"Error importing trades: {e}")
        conn.rollback()
    finally:
        conn.close()

def fetch_nav_and_cash_data():
    """Fetch NAV snapshots and cash movements"""
    logger.info("Fetching NAV and cash movement data...")
    
    # This will fetch the last 7 days of data including June 25-26
    success = flex_query_enhanced.fetch_and_save_account_data(days_back=7)
    
    if success:
        logger.info("Successfully fetched and saved NAV/cash data")
        
        # Run reconciliation for June 25-26
        run_reconciliation(datetime(2025, 6, 25).date())
        run_reconciliation(datetime(2025, 6, 26).date())
    else:
        logger.error("Failed to fetch NAV/cash data")

def run_reconciliation(reconcile_date):
    """Run reconciliation for a specific date"""
    conn = get_trade_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # Get NAV data
            cursor.execute("""
                SELECT opening_nav, closing_nav, trading_pnl
                FROM portfolio.daily_nav_snapshots
                WHERE snapshot_date = %s
            """, (reconcile_date,))
            
            nav_data = cursor.fetchone()
            if not nav_data:
                logger.warning(f"No NAV data found for {reconcile_date}")
                return
            
            opening_nav, closing_nav, trading_pnl = nav_data
            
            # Get cash movements
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount) FILTER (WHERE movement_type = 'DEPOSIT'), 0) as deposits,
                    COALESCE(SUM(ABS(amount)) FILTER (WHERE movement_type = 'WITHDRAWAL'), 0) as withdrawals
                FROM portfolio.cash_movements
                WHERE movement_date = %s AND status = 'COMPLETED'
            """, (reconcile_date,))
            
            cash_data = cursor.fetchone()
            deposits = cash_data[0] if cash_data else 0
            withdrawals = cash_data[1] if cash_data else 0
            
            # Create reconciliation record
            cursor.execute("""
                INSERT INTO portfolio.nav_reconciliation (
                    reconciliation_date,
                    opening_nav,
                    actual_closing_nav,
                    trading_pnl,
                    deposits,
                    withdrawals,
                    reconciled_by,
                    reconciled_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reconciliation_date) DO UPDATE SET
                    actual_closing_nav = EXCLUDED.actual_closing_nav,
                    trading_pnl = EXCLUDED.trading_pnl,
                    deposits = EXCLUDED.deposits,
                    withdrawals = EXCLUDED.withdrawals,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                reconcile_date,
                opening_nav,
                closing_nav,
                trading_pnl or 0,
                deposits,
                withdrawals,
                'IBKR_Import',
                datetime.now()
            ))
            
            # Check if balanced
            cursor.execute("""
                SELECT is_balanced, discrepancy
                FROM portfolio.nav_reconciliation
                WHERE reconciliation_date = %s
            """, (reconcile_date,))
            
            result = cursor.fetchone()
            if result:
                is_balanced, discrepancy = result
                if is_balanced:
                    logger.info(f"✅ {reconcile_date} reconciliation balanced!")
                else:
                    logger.warning(f"⚠️ {reconcile_date} reconciliation discrepancy: ${discrepancy}")
            
            conn.commit()
            
    except Exception as e:
        logger.error(f"Error running reconciliation: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Main execution"""
    logger.info("Starting historical data import...")
    
    # Set environment variables if not set
    if not os.getenv("IBKR_FLEX_TOKEN"):
        logger.error("Please set IBKR_FLEX_TOKEN environment variable")
        return
    
    if not os.getenv("IBKR_FLEX_QUERY_ID"):
        logger.error("Please set IBKR_FLEX_QUERY_ID environment variable")
        return
    
    # Import trades
    import_historical_trades()
    
    # Fetch NAV and cash data
    fetch_nav_and_cash_data()
    
    # Display reconciliation summary
    conn = get_trade_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    reconciliation_date,
                    opening_nav,
                    actual_closing_nav,
                    trading_pnl,
                    deposits,
                    withdrawals,
                    is_balanced,
                    discrepancy
                FROM portfolio.nav_reconciliation
                WHERE reconciliation_date >= '2025-06-25'
                ORDER BY reconciliation_date
            """)
            
            print("\n📊 NAV Reconciliation Summary:")
            print("=" * 100)
            print(f"{'Date':<12} {'Opening NAV':>12} {'Closing NAV':>12} {'P&L':>10} {'Deposits':>10} {'Withdrawals':>12} {'Status':>10} {'Discrepancy':>12}")
            print("-" * 100)
            
            for row in cursor.fetchall():
                status = "✅ Balanced" if row[6] else "⚠️ Check"
                print(f"{row[0]!s:<12} ${row[1]:>11,.2f} ${row[2]:>11,.2f} ${row[3]:>9,.2f} ${row[4]:>9,.2f} ${row[5]:>11,.2f} {status:>10} ${row[7] or 0:>11,.2f}")
    
    finally:
        conn.close()
    
    logger.info("Historical data import complete!")

if __name__ == "__main__":
    main()