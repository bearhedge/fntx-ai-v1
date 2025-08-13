#!/usr/bin/env python3
"""
Close SPY options positions
Separate script for closing positions to avoid IB Gateway connection conflicts
"""

import sys
import argparse
import logging
from datetime import datetime
import os
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.append('/home/info/fntx-ai-v1/backend')
from trading.options_trader import OptionsTrader
from ib_insync import util, Option, MarketOrder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_trade_in_database(symbol, strike, right, expiry_date, exit_price, status='closed'):
    """Update trade record in database after closing"""
    try:
        # Database connection parameters - same as execute_spy_trades.py
        db_config = {
            'host': 'localhost',
            'database': 'options_data',
            'user': 'postgres',
            'password': 'theta_data_2024'
        }
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Update the trade record
        update_query = """
            UPDATE trading.trades 
            SET exit_time = %s,
                exit_price = %s,
                status = %s,
                pnl = (entry_price - %s) * quantity * 100  -- For short options
            WHERE symbol = %s 
              AND strike_price = %s 
              AND option_type = %s
              AND expiration = %s
              AND status = 'open'
            RETURNING trade_id, quantity, entry_price, pnl;
        """
        
        # Convert expiry string to date
        expiry = datetime.strptime(expiry_date, '%Y%m%d').date()
        
        cursor.execute(update_query, (
            datetime.now(),  # exit_time
            exit_price,
            status,
            exit_price,  # For PNL calculation
            symbol,
            strike,
            'CALL' if right == 'C' else 'PUT',
            expiry
        ))
        
        result = cursor.fetchone()
        if result:
            trade_id, quantity, entry_price, pnl = result
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Trade {trade_id} closed in database")
            logger.info(f"   Entry: ${entry_price:.2f}, Exit: ${exit_price:.2f}")
            logger.info(f"   P&L: ${pnl:.2f}")
            return trade_id
        else:
            logger.warning("No open trade found to update")
            conn.rollback()
            cursor.close()
            conn.close()
            return None
            
    except Exception as e:
        logger.error(f"❌ Failed to update trade in database: {e}")
        return None

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Close SPY options positions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Close a specific put position
  python close_spy_trades.py --strike 635 --right P
  
  # Close a specific call position
  python close_spy_trades.py --strike 640 --right C
  
  # Close with specific quantity
  python close_spy_trades.py --strike 635 --right P --quantity 3
        """
    )
    
    parser.add_argument(
        '--strike', 
        type=float, 
        required=True,
        help='Strike price of option to close'
    )
    
    parser.add_argument(
        '--right', 
        choices=['P', 'C'], 
        required=True,
        help='Option type: P for Put, C for Call'
    )
    
    parser.add_argument(
        '--quantity', 
        type=int, 
        default=None,
        help='Number of contracts to close (default: close all)'
    )
    
    parser.add_argument(
        '--expiry', 
        type=str, 
        default=None,
        help='Expiry date (YYYYMMDD format, default: today)'
    )
    
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Get expiry date (default to today for 0DTE)
    if args.expiry:
        expiry_date = args.expiry
    else:
        expiry_date = datetime.now().strftime('%Y%m%d')
    
    # Log closing configuration
    logger.info("="*60)
    logger.info("CLOSING SPY OPTIONS POSITION")
    logger.info("="*60)
    logger.info(f"Strike: {args.strike}")
    logger.info(f"Type: {'PUT' if args.right == 'P' else 'CALL'}")
    logger.info(f"Expiry: {expiry_date}")
    if args.quantity:
        logger.info(f"Quantity: {args.quantity} contracts")
    else:
        logger.info(f"Quantity: Close all")
    logger.info("="*60)
    
    # Initialize trader
    trader = OptionsTrader(host='127.0.0.1', port=4001)
    
    # Connect to IB Gateway
    logger.info("Connecting to IB Gateway...")
    if not trader.connect():
        logger.error("Failed to connect to IB Gateway. Make sure it's running on port 4001.")
        return
    
    logger.info("Successfully connected to IB Gateway")
    
    try:
        # Get current positions to find quantity if not specified
        if not args.quantity:
            logger.info("Checking current positions...")
            positions = trader.ib.positions()
            
            # Find matching position
            for pos in positions:
                contract = pos.contract
                if (contract.symbol == 'SPY' and 
                    contract.secType == 'OPT' and
                    contract.strike == args.strike and
                    contract.right == args.right and
                    contract.lastTradeDateOrContractMonth == expiry_date):
                    
                    args.quantity = abs(pos.position)
                    logger.info(f"Found position: {args.quantity} contracts")
                    break
            
            if not args.quantity:
                logger.error(f"No position found for SPY {args.strike}{args.right}")
                return
        
        # Create the option contract
        option = Option('SPY', expiry_date, args.strike, args.right, 'SMART')
        trader.ib.qualifyContracts(option)
        
        # Get current price
        ticker = trader.ib.reqMktData(option, '', False, False)
        trader.ib.sleep(2)  # Wait for data
        
        if ticker.bid and ticker.ask:
            logger.info(f"Current market: Bid ${ticker.bid:.2f}, Ask ${ticker.ask:.2f}")
        
        # Create market order to close (BUY to close short position)
        order = MarketOrder('BUY', args.quantity)
        
        logger.info(f"Placing order to close {args.quantity} contracts...")
        
        # Place the order
        trade = trader.ib.placeOrder(option, order)
        
        # Wait for fill
        trader.ib.sleep(1)
        
        # Check order status
        fill_price = None
        for i in range(10):  # Wait up to 10 seconds
            if trade.orderStatus.status in ['Filled', 'PartiallyFilled']:
                # Get average fill price
                if trade.fills:
                    fill_price = sum(fill.execution.avgPrice for fill in trade.fills) / len(trade.fills)
                    logger.info(f"✅ Position closed at ${fill_price:.2f}")
                    
                    # Update database
                    update_trade_in_database(
                        symbol='SPY',
                        strike=args.strike,
                        right=args.right,
                        expiry_date=expiry_date,
                        exit_price=fill_price
                    )
                    break
            trader.ib.sleep(1)
        
        if not fill_price:
            logger.error("❌ Failed to close position - order not filled")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("CLOSE SUMMARY")
        logger.info("="*60)
        logger.info(f"Position: SPY {args.strike}{args.right}")
        logger.info(f"Quantity: {args.quantity} contracts")
        if fill_price:
            logger.info(f"Exit Price: ${fill_price:.2f}")
            logger.info(f"Total Cost: ${fill_price * args.quantity * 100:.2f}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Error during closing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect
        logger.info("\nDisconnecting from IB Gateway...")
        trader.disconnect()
        logger.info("Done.")

if __name__ == "__main__":
    # Start the event loop for ib_insync
    util.startLoop()
    main()