#!/usr/bin/env python3
"""
Execute SPY options trades using IB REST API
Replacement for ib_insync/IBAPI-based execute_spy_trades.py

Features:
- Sell PUT, CALL, or BOTH with configurable strikes and stop loss
- Default: Sell both 629 Put and 631 Call with 5.0x stop loss
- Fixed quantity: 3 contracts on each side
- No ghost connection issues (stateless REST API)
- Headless authentication for institutional accounts
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
from core.trading.ib_rest_client import IBRestClient

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
            order_id or '0',  # Use '0' if no order_id provided
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
        description='Execute SPY options trades using IB REST API (no ghost connections)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute only PUT side with 3 contracts
  python execute_spy_trades_rest.py --side put
  
  # Execute only CALL side with custom strike
  python execute_spy_trades_rest.py --side call --call-strike 640
  
  # Execute both sides with custom strikes
  python execute_spy_trades_rest.py --side both --put-strike 636 --call-strike 639
  
  # Use specific quantity (overrides default)
  python execute_spy_trades_rest.py --side both --quantity 5
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
    
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Log trading configuration
    logger.info("="*60)
    logger.info("SPY OPTIONS TRADING - IB REST API")
    logger.info("="*60)
    logger.info(f"Trading Side: {args.side.upper()}")
    if args.side in ['put', 'both']:
        logger.info(f"PUT Strike: {args.put_strike}")
    if args.side in ['call', 'both']:
        logger.info(f"CALL Strike: {args.call_strike}")
    logger.info(f"Quantity: {args.quantity} contracts")
    logger.info(f"Stop Loss Multiple: {args.stop_multiple}x")
    logger.info("Authentication: Headless REST API")
    logger.info("="*60)
    
    # Initialize REST API client
    client = IBRestClient()
    
    # Connect to IB REST API
    logger.info("Connecting to IB REST API...")
    
    if not client.connect():
        logger.error("❌ Failed to connect to IB REST API")
        logger.error("   Possible causes:")
        logger.error("   1. Missing or invalid authentication credentials")
        logger.error("   2. Keys not properly configured in environment")
        logger.error("   3. Network connectivity issues")
        logger.error("   4. API endpoint unavailable")
        return
    
    logger.info("✅ Successfully connected to IB REST API")
    logger.info(f"   Primary Account: {client.account_id}")
    
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
            
            # Execute the sell
            result = client.sell_option_with_stop(
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
        
        # Execute CALL trade if requested
        if args.side in ['call', 'both']:
            logger.info("\n" + "="*60)
            logger.info(f"TRADE 2: Selling SPY {args.call_strike} Call")
            logger.info("="*60)
            
            # Execute the sell
            result = client.sell_option_with_stop(
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
        
        # Verify orders were placed
        logger.info("\n" + "="*60)
        logger.info("VERIFYING ORDERS")
        logger.info("="*60)
        
        # Get open orders
        orders = client.get_orders()
        if orders:
            logger.info(f"Found {len(orders)} orders:")
            for order in orders[:10]:  # Show first 10 orders
                logger.info(f"  Order {order.get('orderId')}: {order.get('side')} "
                           f"{order.get('quantity')} @ {order.get('orderType')}")
        else:
            logger.warning("Could not retrieve orders list")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("TRADE SUMMARY")
        logger.info("="*60)
        
        # Display current positions
        positions = client.get_positions()
        if positions:
            spy_positions = [p for p in positions if p.get('ticker', '').startswith('SPY')]
            
            if spy_positions:
                logger.info(f"Current SPY Positions: {len(spy_positions)}")
                for pos in spy_positions:
                    logger.info(f"  {pos.get('ticker')} - "
                               f"Qty: {pos.get('position')}, "
                               f"Avg Cost: ${pos.get('avgCost', 0):.2f}")
        else:
            logger.info("No position data available")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        logger.info("\n✅ IB REST API trading completed successfully!")
        logger.info("🎯 No ghost connections, no manual login required!")

if __name__ == "__main__":
    main()