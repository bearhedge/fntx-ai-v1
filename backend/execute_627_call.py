#!/usr/bin/env python3
"""
Execute SPY 627 Call with 3x stop loss
"""

import sys
import logging
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from trading.options_trader import OptionsTrader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Initialize trader
    trader = OptionsTrader(host='127.0.0.1', port=4001)
    
    # Connect to IB Gateway
    logger.info("Connecting to IB Gateway...")
    if not trader.connect():
        logger.error("Failed to connect to IB Gateway. Make sure it's running on port 4001.")
        return
    
    logger.info("Successfully connected to IB Gateway")
    
    # Get today's expiration date
    today = datetime.now().strftime('%Y%m%d')
    logger.info(f"Using expiration date: {today}")
    
    try:
        # Sell SPY 627 Call with 3x stop loss
        logger.info("\n" + "="*60)
        logger.info("Selling SPY 627 Call with 3x Stop Loss")
        logger.info("="*60)
        
        # First check the call price
        call_prices = trader.get_option_price('SPY', 627.0, 'C', today)
        if call_prices:
            bid, ask = call_prices
            logger.info(f"SPY 627C - Bid: ${bid:.2f}, Ask: ${ask:.2f}")
            
            # Execute the sell
            result = trader.sell_option_with_stop(
                symbol='SPY',
                strike=627.0,
                right='C',
                stop_multiple=3.0,
                expiry=today
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
            logger.error("Could not get SPY 627 Call prices")
        
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