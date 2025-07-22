#!/usr/bin/env python3
"""
Daily IBKR Flex Query Import Script
Runs automatically via cron to import previous day's trades
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from 01_backend.services.ibkr_flex_query_enhanced import flex_query_enhanced as flex_query_service
from 01_backend.database.trade_db import get_trade_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/daily_flex_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def import_matched_trades(matched_pairs):
    """Import matched trade pairs to database"""
    imported_count = 0
    
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                for pair in matched_pairs:
                    # Check if trade already exists
                    cur.execute("""
                        SELECT trade_id FROM trading.trades 
                        WHERE entry_time = %s AND symbol = %s AND strike_price = %s
                    """, (pair['entry_time'], pair['symbol'], pair['strike']))
                    
                    if cur.fetchone():
                        logger.info(f"Trade already exists: {pair['symbol']} {pair['strike']} @ {pair['entry_time']}")
                        continue
                    
                    # Insert new trade
                    cur.execute("""
                        INSERT INTO trading.trades (
                            symbol, strike_price, option_type, expiration,
                            quantity, entry_time, entry_price, entry_commission,
                            exit_time, exit_price, exit_commission, exit_reason,
                            realized_pnl, status
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        pair['symbol'],
                        pair['strike'],
                        pair['option_type'],
                        pair['expiration'],
                        pair['quantity'],
                        pair['entry_time'],
                        pair['entry_price'],
                        pair['entry_commission'],
                        pair['exit_time'],
                        pair['exit_price'],
                        pair['exit_commission'],
                        'EXPIRED' if pair['exit_price'] == 0 else 'CLOSED',
                        pair['net_pnl'],
                        'CLOSED'
                    ))
                    imported_count += 1
                    
                conn.commit()
                
    except Exception as e:
        logger.error(f"Error importing trades: {e}")
        raise
        
    return imported_count

def run_daily_import():
    """Main function to run daily Flex Query import"""
    logger.info("Starting daily Flex Query import")
    
    try:
        # Check if credentials are configured
        if not flex_query_service.token or not flex_query_service.query_id:
            logger.error("Flex Query credentials not configured")
            return False
            
        # Create import record
        import_id = None
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trading.flex_query_imports (
                        query_id, period_start, period_end, status
                    ) VALUES (%s, %s, %s, 'pending')
                    RETURNING import_id
                """, (
                    flex_query_service.query_id,
                    datetime.now() - timedelta(days=1),
                    datetime.now(),
                ))
                import_id = str(cur.fetchone()[0])
                conn.commit()
        
        # Get yesterday's trades (most recent completed trading day)
        matched_pairs = flex_query_service.get_complete_trade_history(days_back=1)
        
        if not matched_pairs:
            logger.info("No trades found for import")
            # Update import record
            with get_trade_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE trading.flex_query_imports
                        SET status = 'completed', trades_imported = 0, trades_skipped = 0
                        WHERE import_id = %s
                    """, (import_id,))
                    conn.commit()
            return True
        
        logger.info(f"Found {len(matched_pairs)} matched trade pairs")
        
        # Import trades
        imported_count = import_matched_trades(matched_pairs)
        
        # Calculate total P&L
        total_pnl = sum(float(pair['net_pnl']) for pair in matched_pairs)
        
        # Update import record
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trading.flex_query_imports
                    SET status = 'completed', 
                        trades_imported = %s,
                        trades_skipped = %s,
                        total_pnl = %s
                    WHERE import_id = %s
                """, (
                    imported_count,
                    len(matched_pairs) - imported_count,
                    total_pnl,
                    import_id
                ))
                conn.commit()
        
        logger.info(f"Import completed: {imported_count} trades imported, Total P&L: ${total_pnl:.2f}")
        
        # Send notification if trades were imported
        if imported_count > 0:
            send_notification(f"IBKR Daily Import: {imported_count} trades, P&L: ${total_pnl:.2f}")
            
        return True
        
    except Exception as e:
        logger.error(f"Daily import failed: {e}")
        
        # Update import record with error
        if import_id:
            with get_trade_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE trading.flex_query_imports
                        SET status = 'failed', error_message = %s
                        WHERE import_id = %s
                    """, (str(e), import_id))
                    conn.commit()
        
        # Send error notification
        send_notification(f"IBKR Daily Import Failed: {str(e)}")
        return False

def send_notification(message):
    """Send notification (placeholder for email/webhook)"""
    logger.info(f"NOTIFICATION: {message}")
    # TODO: Implement actual notification (email, Discord, etc.)

if __name__ == "__main__":
    success = run_daily_import()
    sys.exit(0 if success else 1)