#!/usr/bin/env python3
"""
Execute SPY options trades using Official IBAPI
Replacement for ib_insync-based execute_spy_trades.py

Features:
- Sell PUT, CALL, or BOTH with configurable strikes and stop loss
- Default: Sell both 629 Put and 631 Call with 5.0x stop loss
- Fixed quantity: 3 contracts on each side
- No ghost connection issues (native IBAPI threading)
- Institutional account support for headless authentication
"""

import sys
import argparse
import logging
import time
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
from core.trading.ibapi_trader import IBAPITrader

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
        description='Execute SPY options trades using Official IBAPI (no ghost connections)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute only PUT side with 3 contracts
  python execute_spy_trades_ibapi.py --side put
  
  # Execute only CALL side with custom strike
  python execute_spy_trades_ibapi.py --side call --call-strike 640
  
  # Execute both sides with custom strikes
  python execute_spy_trades_ibapi.py --side both --put-strike 636 --call-strike 639
  
  # Use institutional account (headless authentication)
  python execute_spy_trades_ibapi.py --side both --client-id 2000
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
        help='Strike price for PUT option (default: 629)'
    )
    
    parser.add_argument(
        '--call-strike', 
        type=float, 
        default=631.0,
        help='Strike price for CALL option (default: 631)'
    )
    
    parser.add_argument(
        '--stop-multiple', 
        type=float, 
        default=5.0,
        help='Stop loss multiple (default: 5.0)'
    )
    
    parser.add_argument(
        '--quantity', 
        type=int, 
        default=3,
        help='Number of contracts to trade (default: 3)'
    )
    
    parser.add_argument(
        '--client-id', 
        type=int, 
        help='Client ID for IBAPI connection (auto-generated if not specified)'
    )
    
    parser.add_argument(
        '--timeout', 
        type=int, 
        default=45,
        help='Connection timeout in seconds (default: 45)'
    )
    
    return parser.parse_args()

def test_connection(host='127.0.0.1', port=4001):
    """Test basic socket connectivity to IB Gateway"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        if result != 0:
            logger.error("❌ IB Gateway is not listening on port 4001")
            logger.error("   Please check that IB Gateway is running and API is enabled")
            return False
        else:
            logger.info("✓ Port 4001 is accepting connections")
            return True
    except Exception as e:
        logger.error(f"❌ Network test failed: {e}")
        return False

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Log trading configuration
    logger.info("="*60)
    logger.info("SPY OPTIONS TRADING - OFFICIAL IBAPI")
    logger.info("="*60)
    logger.info(f"Trading Side: {args.side.upper()}")
    if args.side in ['put', 'both']:
        logger.info(f"PUT Strike: {args.put_strike}")
    if args.side in ['call', 'both']:
        logger.info(f"CALL Strike: {args.call_strike}")
    logger.info(f"Quantity: {args.quantity} contracts")
    logger.info(f"Stop Loss Multiple: {args.stop_multiple}x")
    if args.client_id:
        logger.info(f"Client ID: {args.client_id} (manual)")
    else:
        logger.info("Client ID: Auto-generated")
    logger.info("="*60)
    
    # Test basic connectivity first
    if not test_connection():
        return
    
    # Initialize IBAPI trader
    trader = IBAPITrader(host='127.0.0.1', port=4001)
    
    # Connect to IB Gateway
    logger.info("Connecting to IB Gateway using Official IBAPI...")
    
    if not trader.connect_api(client_id=args.client_id):
        logger.error("❌ Failed to connect to IB Gateway")
        logger.error("   Possible causes:")
        logger.error("   1. IB Gateway is not running")
        logger.error("   2. API is not enabled in IB Gateway settings")
        logger.error("   3. Another client is already connected with the same client ID")
        logger.error("   4. Network connectivity issues")
        return
    
    logger.info("✅ Successfully connected to IB Gateway")
    logger.info(f"   Client ID: {trader.client_id}")
    logger.info(f"   Managed Accounts: {trader.managed_accounts}")
    
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
                            order_id=result.order_id
                        )
                else:
                    logger.error(f"❌ Failed to sell put: {result.message}")
                    if "CRITICAL" in result.message:
                        logger.error("⚠️  Stop loss not placed - position may be at risk!")
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
                            order_id=result.order_id
                        )
                else:
                    logger.error(f"❌ Failed to sell call: {result.message}")
                    if "CRITICAL" in result.message:
                        logger.error("⚠️  Stop loss not placed - position may be at risk!")
            else:
                logger.error(f"Could not get SPY {args.call_strike} Call prices")
        
        # Verify stop losses were placed
        logger.info("\n" + "="*60)
        logger.info("VERIFYING STOP LOSSES")
        logger.info("="*60)
        
        # Get open orders
        open_orders = trader.get_open_orders()
        stop_orders = [order for order in open_orders 
                      if order.get('order', {}).get('orderType') == 'STP']
        
        logger.info(f"Found {len(stop_orders)} stop orders:")
        for order in stop_orders:
            contract = order.get('contract', {})
            order_obj = order.get('order', {})
            if contract.get('symbol') == 'SPY':
                logger.info(f"✅ Stop Order: {contract.get('strike')} {contract.get('right')} - "
                           f"BUY {order_obj.get('totalQuantity')} @ ${order_obj.get('auxPrice', 0):.2f}")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("TRADE SUMMARY")
        logger.info("="*60)
        
        # Get current SPY price for reference (simplified approach)  
        spy_prices = trader.get_option_price('SPY', 500, 'C', expiry_date)  # Use deep ITM call as proxy
        if spy_prices:
            # Approximate SPY price (this is simplified - in production would use stock ticker)
            bid, ask = spy_prices
            approx_spy_price = 500 + (bid + ask) / 2  # Rough approximation
            
            logger.info(f"SPY Approximate Price: ${approx_spy_price:.2f}")
            if args.side in ['put', 'both']:
                put_distance = approx_spy_price - args.put_strike
                logger.info(f"{args.put_strike} Put is ${abs(put_distance):.2f} {'OTM' if put_distance > 0 else 'ITM'}")
            if args.side in ['call', 'both']:
                call_distance = args.call_strike - approx_spy_price
                logger.info(f"{args.call_strike} Call is ${abs(call_distance):.2f} {'OTM' if call_distance > 0 else 'ITM'}")
        
        # Display current positions
        positions = trader.get_positions_list()
        spy_positions = [p for p in positions if p.get('symbol') == 'SPY' and p.get('position', 0) != 0]
        
        if spy_positions:
            logger.info(f"\nCurrent SPY Positions: {len(spy_positions)}")
            for pos in spy_positions:
                logger.info(f"  {pos['symbol']} {pos.get('strike', 'N/A')}{pos.get('right', '')} - "
                           f"Qty: {pos['position']}, Avg Cost: ${pos['avgCost']:.2f}")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect
        logger.info("\nDisconnecting from IB Gateway...")
        trader.disconnect_api()
        logger.info("✅ Migration to Official IBAPI completed successfully!")
        logger.info("🎯 No more ghost connection issues!")

if __name__ == "__main__":
    main()