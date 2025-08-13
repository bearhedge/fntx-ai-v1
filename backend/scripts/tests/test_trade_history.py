#!/usr/bin/env python3
"""
Test script to verify trade history functionality
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "fntx_trading",
    "user": "info"
}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def test_trade_history():
    """Test fetching trade history from backend.data.database"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get trades from last 30 days
                query = """
                SELECT 
                    trade_id,
                    symbol,
                    strike_price,
                    option_type,
                    expiration,
                    quantity,
                    entry_time,
                    entry_price,
                    entry_commission,
                    exit_time,
                    exit_price,
                    exit_commission,
                    exit_reason,
                    realized_pnl,
                    status
                FROM trading.trades
                WHERE entry_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                ORDER BY entry_time DESC
                LIMIT 10
                """
                
                cur.execute(query)
                trades = cur.fetchall()
                
                print(f"Found {len(trades)} trades in the last 30 days")
                print("-" * 80)
                
                for trade in trades:
                    print(f"Trade ID: {trade['trade_id']}")
                    print(f"Symbol: {trade['symbol']} {trade['strike_price']} {trade['option_type']}")
                    print(f"Entry: {trade['entry_time']} @ ${trade['entry_price']}")
                    print(f"Exit: {trade['exit_time']} @ ${trade['exit_price']}")
                    print(f"P&L: ${trade['realized_pnl']}")
                    print(f"Status: {trade['status']}")
                    print("-" * 80)
                    
                return trades
                
    except Exception as e:
        print(f"Error fetching trade history: {e}")
        return []

def test_import_functionality():
    """Test if trades can be imported"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check flex query imports table
                cur.execute("""
                    SELECT * FROM trading.flex_query_imports
                    ORDER BY import_date DESC
                    LIMIT 5
                """)
                
                imports = cur.fetchall()
                
                print("\nRecent import history:")
                print("-" * 80)
                
                for imp in imports:
                    print(f"Import ID: {imp['import_id']}")
                    print(f"Date: {imp['import_date']}")
                    print(f"Status: {imp['status']}")
                    print(f"Trades Imported: {imp.get('trades_imported', 0)}")
                    print("-" * 80)
                    
    except Exception as e:
        print(f"Error checking imports: {e}")

if __name__ == "__main__":
    print("Testing Trade History System")
    print("=" * 80)
    
    # Test fetching trade history
    trades = test_trade_history()
    
    # Test import functionality
    test_import_functionality()
    
    print(f"\nTotal trades found: {len(trades)}")
    print("Test complete!")