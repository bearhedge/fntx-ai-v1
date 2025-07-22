#!/usr/bin/env python3
"""
Execute SPY options trades with flexible side selection:
- Sell PUT, CALL, or BOTH with configurable strikes and stop loss
- Default: Sell both 630 Put and 632 Call with 3.5x stop loss
"""

import sys
import argparse
import logging
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from trading.options_trader import OptionsTrader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Execute SPY options trades with flexible side selection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute only PUT side
  python execute_spy_trades.py --side put
  
  # Execute only CALL side with custom strike
  python execute_spy_trades.py --side call --call-strike 630
  
  # Execute both sides with custom strikes
  python execute_spy_trades.py --side both --put-strike 626 --call-strike 629
        """
    )
    
    parse
    .add_argument(
        '--side', 
        choices=['put', 'call', 'both'], 
        default='both',
        help='Which side to trade: put, call, or both (default: both)'
    )
    
    parser.add_argument(
        '--put-strike', 
        type=float, 
        default=631.0,
        help='Strike price for PUT option (default: 625)'
    )
    
    parser.add_argument(
        '--call-strike', 
        type=float, 
        default=632.0,
        help='Strike price for CALL option (default: 629)'
    )
    
    parser.add_argument(
        '--stop-multiple', 
        type=float, 
        default=3.5,
        help='Stop loss multiple (default: 3.5)'
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
    logger.info(f"Stop Loss Multiple: {args.stop_multiple}x")
    logger.info("="*60)
    
    # Initialize trader
    trader = OptionsTrader(host='127.0.0.1', port=4001)
    
    # Connect to IB Gateway
    logger.info("Connecting to IB Gateway...")
    if not trader.connect():
        logger.error("Failed to connect to IB Gateway. Make sure it's running on port 4001.")
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
                    expiry=expiry_date
                )
                
                if result.success:
                    logger.info(f"✅ {result.message}")
                    logger.info(f"   Entry Price: ${result.entry_price:.2f}")
                    logger.info(f"   Stop Loss: ${result.stop_loss:.2f}")
                    logger.info(f"   Credit Received: ${result.credit:.2f}")
                    logger.info(f"   Max Risk: ${result.max_risk:.2f}")
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
                    expiry=expiry_date
                )
                
                if result.success:
                    logger.info(f"✅ {result.message}")
                    logger.info(f"   Entry Price: ${result.entry_price:.2f}")
                    logger.info(f"   Stop Loss: ${result.stop_loss:.2f}")
                    logger.info(f"   Credit Received: ${result.credit:.2f}")
                    logger.info(f"   Max Risk: ${result.max_risk:.2f}")
                else:
                    logger.error(f"❌ Failed to sell call: {result.message}")
            else:
                logger.error(f"Could not get SPY {args.call_strike} Call prices")
        
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

if __name__ == "__main__":
    main()