#!/usr/bin/env python3
"""
Execute SPY options trades with flexible side selection:
- Sell PUT, CALL, or BOTH with configurable strikes and stop loss
- Default: Sell both 627 Put and 631 Call with 3.5x stop loss
- Fixed quantity: 3 contracts on each side
"""

import sys
import argparse
import logging
from datetime import datetime
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from config/.env
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.options_trader import OptionsTrader
from ib_insync import util

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def record_trade_to_database(symbol, strike, right, quantity, entry_price, stop_loss, expiry_date, order_id=None):
    """Record executed trade to database for position tracking"""
    try:
        # Database connection parameters from environment
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'options_data'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'theta_data_2024'),
            'port': int(os.getenv('DB_PORT', 5432))
        }
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Insert trade record
        insert_query = """
            INSERT INTO trading.trades (
                ibkr_order_id,
                symbol,
                strike_price,
                option_type,
                expiration,
                quantity,
                entry_time,
                entry_price,
                stop_loss_price,
                status,
                market_snapshot
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING trade_id;
        """
        
        # Convert expiry string to date
        expiry = datetime.strptime(expiry_date, '%Y%m%d').date()
        
        cursor.execute(insert_query, (
            order_id or 0,  # Use 0 if no order_id provided
            symbol,
            strike,
            right,  # 'P' or 'C' will be converted to 'PUT' or 'CALL' in database
            expiry,
            quantity,
            datetime.now(),  # entry_time
            entry_price,
            stop_loss,
            'open',
            '{}'  # Empty JSON for market_snapshot
        ))
        
        trade_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Trade recorded in database with ID: {trade_id}")
        return trade_id
        
    except Exception as e:
        logger.error(f"❌ Failed to record trade in database: {e}")
        return None

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Execute SPY options trades with flexible side selection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute only PUT side with 3 contracts
  python execute_spy_trades.py --side put
  
  # Execute only CALL side with custom strike
  python execute_spy_trades.py --side call --call-strike 640
  
  # Execute both sides with custom strikes
  python execute_spy_trades.py --side both --put-strike 636 --call-strike 639
        """
    )
    
    parser.add_argument(
        '--side', 
        choices=['put', 'call', 'both'], 
        default='both',
        help='Which side to trade: put, call, or both (default: both)'
    )
    
    parser.add_argument(
        '--put-strike', 
        type=float, 
        default=629.0,
        help='Strike price for PUT option (default: 636)'
    )
    
    parser.add_argument(
        '--call-strike', 
        type=float, 
        default=631.0,
        help='Strike price for CALL option (default: 639)'
    )
    
    parser.add_argument(
        '--stop-multiple', 
        type=float, 
        default=5.0,
        help='Stop loss multiple (default: 3.5)'
    )
    
    parser.add_argument(
        '--quantity', 
        type=int, 
        default=3,
        help='Number of contracts to trade (default: 3)'
    )
    
    parser.add_argument(
        '--start-cleanup', 
        action='store_true',
        help='Start cleanup manager after placing trades'
    )
    
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    
    # Log trading configuration
    logger.info("="*60)
    logger.info("SPY OPTIONS TRADING CONFIGURATION")
    logger.info("="*60)
    logger.info(f"Trading Side: {args.side.upper()}")
    if args.side in ['put', 'both']:
        logger.info(f"PUT Strike: {args.put_strike}")
    if args.side in ['call', 'both']:
        logger.info(f"CALL Strike: {args.call_strike}")
    logger.info(f"Quantity: {args.quantity} contracts")
    logger.info(f"Stop Loss Multiple: {args.stop_multiple}x")
    logger.info("="*60)
    
    # Initialize trader
    trader = OptionsTrader(host='127.0.0.1', port=4001)
    
    # Connect to IB Gateway with diagnostics
    logger.info("Connecting to IB Gateway...")
    logger.info(f"Client ID: {trader.client_id}")
    
    # Test basic connectivity first
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 4001))
        sock.close()
        if result != 0:
            logger.error("❌ IB Gateway is not listening on port 4001")
            logger.error("   Please check that IB Gateway is running and API is enabled")
            return
        else:
            logger.info("✓ Port 4001 is accepting connections")
    except Exception as e:
        logger.error(f"❌ Network test failed: {e}")
        return
    
    # Now try IB API connection
    if not trader.connect():
        logger.error("❌ Failed to connect to IB Gateway API")
        logger.error("   IB Gateway is running but API connection failed")
        logger.error("   This usually means:")
        logger.error("   1. Another process is already connected to IB Gateway")
        logger.error("   2. IB Gateway needs to be restarted to accept API connections")
        logger.error("   3. API settings in IB Gateway need verification")
        return
    
    logger.info("Successfully connected to IB Gateway")
    
    # Get today's expiration date for 0DTE
    today = datetime.now()
    expiry_date = today.strftime('%Y%m%d')
    logger.info(f"Using expiration date: {expiry_date}")
    
    try:
        # Execute PUT trade if requested
        if args.side in ['put', 'both']:
            logger.info("\n" + "="*60)
            logger.info(f"TRADE 1: Selling SPY {args.put_strike} Put")
            logger.info("="*60)
            
            # First check the put price
            put_prices = trader.get_option_price('SPY', args.put_strike, 'P', expiry_date)
            if put_prices:
                bid, ask = put_prices
                logger.info(f"SPY {args.put_strike}P - Bid: ${bid:.2f}, Ask: ${ask:.2f}")
                
                # Execute the sell
                result = trader.sell_option_with_stop(
                    symbol='SPY',
                    strike=args.put_strike,
                    right='P',
                    stop_multiple=args.stop_multiple,
                    quantity=args.quantity,
                    expiry=expiry_date
                )
                
                if result.success:
                    logger.info(f"✅ {result.message}")
                    logger.info(f"   Entry Price: ${result.entry_price:.2f}")
                    logger.info(f"   Stop Loss: ${result.stop_loss:.2f}")
                    logger.info(f"   Credit Received: ${result.credit:.2f}")
                    logger.info(f"   Max Risk: ${result.max_risk:.2f}")
                    
                    # Record trade to database
                    if args.quantity > 0:  # Only record if actual quantity traded
                        record_trade_to_database(
                            symbol='SPY',
                            strike=args.put_strike,
                            right='PUT',
                            quantity=args.quantity,
                            entry_price=result.entry_price,
                            stop_loss=result.stop_loss,
                            expiry_date=expiry_date,
                            order_id=getattr(result, 'order_id', None)
                        )
                else:
                    logger.error(f"❌ Failed to sell put: {result.message}")
            else:
                logger.error(f"Could not get SPY {args.put_strike} Put prices")
        
        # Execute CALL trade if requested
        if args.side in ['call', 'both']:
            logger.info("\n" + "="*60)
            logger.info(f"TRADE 2: Selling SPY {args.call_strike} Call")
            logger.info("="*60)
            
            # First check the call price
            call_prices = trader.get_option_price('SPY', args.call_strike, 'C', expiry_date)
            if call_prices:
                bid, ask = call_prices
                logger.info(f"SPY {args.call_strike}C - Bid: ${bid:.2f}, Ask: ${ask:.2f}")
                
                # Execute the sell
                result = trader.sell_option_with_stop(
                    symbol='SPY',
                    strike=args.call_strike,
                    right='C',
                    stop_multiple=args.stop_multiple,
                    quantity=args.quantity,
                    expiry=expiry_date
                )
                
                if result.success:
                    logger.info(f"✅ {result.message}")
                    logger.info(f"   Entry Price: ${result.entry_price:.2f}")
                    logger.info(f"   Stop Loss: ${result.stop_loss:.2f}")
                    logger.info(f"   Credit Received: ${result.credit:.2f}")
                    logger.info(f"   Max Risk: ${result.max_risk:.2f}")
                    
                    # Record trade to database
                    if args.quantity > 0:  # Only record if actual quantity traded
                        record_trade_to_database(
                            symbol='SPY',
                            strike=args.call_strike,
                            right='CALL',
                            quantity=args.quantity,
                            entry_price=result.entry_price,
                            stop_loss=result.stop_loss,
                            expiry_date=expiry_date,
                            order_id=getattr(result, 'order_id', None)
                        )
                else:
                    logger.error(f"❌ Failed to sell call: {result.message}")
            else:
                logger.error(f"Could not get SPY {args.call_strike} Call prices")
        
        # Verify stop losses were placed
        logger.info("\n" + "="*60)
        logger.info("VERIFYING STOP LOSSES")
        logger.info("="*60)
        
        # Check all open orders for stop losses
        open_trades = trader.ib.openTrades()
        stop_trades = [t for t in open_trades if t.order.orderType == 'STP']
        
        logger.info(f"Found {len(stop_trades)} stop orders:")
        for trade in stop_trades:
            if hasattr(trade.contract, 'symbol') and trade.contract.symbol == 'SPY':
                logger.info(f"✅ Stop Order: {trade.contract.strike} {trade.contract.right} - "
                           f"BUY {trade.order.totalQuantity} @ ${trade.order.auxPrice:.2f}")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("TRADE SUMMARY")
        logger.info("="*60)
        
        # Get current SPY price for reference
        from ib_insync import Stock
        spy = Stock('SPY', 'SMART', 'USD')
        trader.ib.qualifyContracts(spy)
        trader.ib.reqMktData(spy, '', False, False)
        trader.ib.sleep(2)
        spy_ticker = trader.ib.ticker(spy)
        
        if spy_ticker.last:
            logger.info(f"SPY Current Price: ${spy_ticker.last:.2f}")
            if args.side in ['put', 'both']:
                put_distance = spy_ticker.last - args.put_strike
                logger.info(f"{args.put_strike} Put is ${abs(put_distance):.2f} {'OTM' if put_distance > 0 else 'ITM'}")
            if args.side in ['call', 'both']:
                call_distance = args.call_strike - spy_ticker.last
                logger.info(f"{args.call_strike} Call is ${abs(call_distance):.2f} {'OTM' if call_distance > 0 else 'ITM'}")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect
        logger.info("\nDisconnecting from IB Gateway...")
        trader.disconnect()
        logger.info("Done.")
        
        # Start cleanup manager if requested
        if args.start_cleanup and (args.side in ['put', 'call', 'both']):
            logger.info("\nStarting cleanup manager...")
            # Note: Cleanup manager has been archived. Use systemctl to manage cleanup services instead.
            logger.info("⚠️  Cleanup manager script not available. Use systemctl to manage cleanup services:")
            logger.info("   sudo systemctl start cleanup-manager.timer")
            logger.info("   sudo systemctl status cleanup-manager")

if __name__ == "__main__":
    # Start the event loop for ib_insync
    util.startLoop()
    main()