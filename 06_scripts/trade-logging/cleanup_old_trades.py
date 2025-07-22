#!/usr/bin/env python3
"""
Cleanup trades before June 20, 2025
Remove trades that shouldn't be in the system
"""

import sys
import os
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from 01_backend.database.trade_db import get_trade_db_connection

def cleanup_old_trades():
    """Remove trades before June 20, 2025"""
    cutoff_date = date(2025, 6, 20)
    
    conn = get_trade_db_connection()
    try:
        with conn.cursor() as cur:
            # First, show what we're about to delete
            print("=== Trades to be removed (before June 20, 2025) ===")
            cur.execute("""
                SELECT DATE(entry_time) as trade_date, 
                       COUNT(*) as count,
                       STRING_AGG(trade_id::TEXT, ', ') as trade_ids
                FROM trading.trades
                WHERE DATE(entry_time) < %s
                GROUP BY DATE(entry_time)
                ORDER BY trade_date
            """, (cutoff_date,))
            
            trades_to_delete = cur.fetchall()
            total_to_delete = 0
            
            for row in trades_to_delete:
                print(f"  {row[0]}: {row[1]} trades")
                total_to_delete += row[1]
            
            if total_to_delete == 0:
                print("No trades to delete.")
                return
            
            print(f"\nTotal trades to delete: {total_to_delete}")
            
            # Ask for confirmation
            response = input("\nProceed with deletion? (yes/no): ")
            if response.lower() != 'yes':
                print("Deletion cancelled.")
                return
            
            # Log trades to audit table before deletion
            cur.execute("""
                INSERT INTO trading.trades_audit (
                    trade_id, action, old_values, change_reason
                )
                SELECT 
                    trade_id, 
                    'DELETE',
                    row_to_json(t.*),
                    'Cleanup: removing trades before June 20, 2025'
                FROM trading.trades t
                WHERE DATE(entry_time) < %s
            """, (cutoff_date,))
            
            # Delete the trades
            cur.execute("""
                DELETE FROM trading.trades
                WHERE DATE(entry_time) < %s
            """, (cutoff_date,))
            
            deleted_count = cur.rowcount
            
            # Also check for any cash movements before June 12
            deposit_date = date(2025, 6, 12)
            cur.execute("""
                SELECT COUNT(*) FROM portfolio.cash_movements
                WHERE movement_date < %s
            """, (deposit_date,))
            
            old_cash_movements = cur.fetchone()[0]
            if old_cash_movements > 0:
                print(f"\nFound {old_cash_movements} cash movements before June 12, 2025")
                response = input("Delete these as well? (yes/no): ")
                if response.lower() == 'yes':
                    cur.execute("""
                        DELETE FROM portfolio.cash_movements
                        WHERE movement_date < %s
                    """, (deposit_date,))
            
            conn.commit()
            print(f"\n✅ Successfully deleted {deleted_count} trades")
            
            # Show remaining trades
            print("\n=== Remaining trades (June 20, 2025 onwards) ===")
            cur.execute("""
                SELECT DATE(entry_time) as trade_date, 
                       COUNT(*) as count,
                       SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open,
                       SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed
                FROM trading.trades
                GROUP BY DATE(entry_time)
                ORDER BY trade_date
            """)
            
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]} trades ({row[2]} open, {row[3]} closed)")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_initial_deposit():
    """Add the initial deposit on June 12, 2025"""
    deposit_date = date(2025, 6, 12)
    
    conn = get_trade_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if deposit already exists
            cur.execute("""
                SELECT COUNT(*) FROM portfolio.cash_movements
                WHERE movement_date = %s
                AND movement_type = 'DEPOSIT'
            """, (deposit_date,))
            
            if cur.fetchone()[0] > 0:
                print("Initial deposit already exists.")
                return
            
            amount = input("\nEnter initial deposit amount (USD): ")
            try:
                amount = float(amount)
            except ValueError:
                print("Invalid amount")
                return
            
            # Add deposit
            cur.execute("""
                INSERT INTO portfolio.cash_movements (
                    movement_date,
                    movement_time,
                    movement_type,
                    amount,
                    currency,
                    status,
                    description,
                    is_reconciled
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                deposit_date,
                datetime.combine(deposit_date, datetime.min.time()),
                'DEPOSIT',
                amount,
                'USD',
                'COMPLETED',
                'Initial deposit to IBKR account',
                True
            ))
            
            conn.commit()
            print(f"✅ Added initial deposit of ${amount:,.2f} on June 12, 2025")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("FNTX AI Trade Data Cleanup")
    print("=" * 50)
    
    # Clean up old trades
    cleanup_old_trades()
    
    # Ask about initial deposit
    print("\n" + "=" * 50)
    response = input("\nWould you like to add the initial deposit from June 12, 2025? (yes/no): ")
    if response.lower() == 'yes':
        add_initial_deposit()