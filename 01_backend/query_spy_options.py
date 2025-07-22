#!/usr/bin/env python3
"""
Query SPY 615 Put and 620 Call prices
"""

import sys
import logging
from datetime import datetime
from ib_insync import IB, Option, Stock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Initialize IB connection
    ib = IB()
    
    try:
        # Connect to IB Gateway
        logger.info("Connecting to IB Gateway on port 4001...")
        ib.connect('127.0.0.1', 4001, clientId=20)  # Use different client ID
        logger.info("Successfully connected!")
        
        # Get today's expiration
        today = datetime.now().strftime('%Y%m%d')
        logger.info(f"Querying options expiring today: {today}")
        
        # Get SPY current price first
        spy = Stock('SPY', 'SMART', 'USD')
        ib.qualifyContracts(spy)
        ib.reqMktData(spy, '', False, False)
        ib.sleep(2)
        spy_ticker = ib.ticker(spy)
        logger.info(f"\nSPY Current Price: ${spy_ticker.last:.2f}")
        
        # Query 615 Put
        logger.info("\n" + "-"*40)
        logger.info("SPY 615 PUT:")
        put_contract = Option('SPY', today, 615.0, 'P', 'SMART', currency='USD')
        try:
            ib.qualifyContracts(put_contract)
            put_ticker = ib.reqMktData(put_contract, '', False, False)
            ib.sleep(2)
            
            if put_ticker.bid is not None and put_ticker.ask is not None:
                logger.info(f"  Bid: ${put_ticker.bid:.2f}")
                logger.info(f"  Ask: ${put_ticker.ask:.2f}")
                logger.info(f"  Last: ${put_ticker.last:.2f}" if put_ticker.last else "  Last: N/A")
                logger.info(f"  Volume: {put_ticker.volume}" if put_ticker.volume else "  Volume: N/A")
                
                # Calculate stop loss levels
                logger.info(f"\n  If sold at bid ${put_ticker.bid:.2f}:")
                logger.info(f"  3.5x stop loss would be at: ${put_ticker.bid * 3.5:.2f}")
                logger.info(f"  Max risk: ${(put_ticker.bid * 3.5 - put_ticker.bid) * 100:.2f}")
            else:
                logger.warning("  No bid/ask data available")
            
            ib.cancelMktData(put_contract)
        except Exception as e:
            logger.error(f"  Error getting put data: {e}")
        
        # Query 620 Call
        logger.info("\n" + "-"*40)
        logger.info("SPY 620 CALL:")
        call_contract = Option('SPY', today, 620.0, 'C', 'SMART', currency='USD')
        try:
            ib.qualifyContracts(call_contract)
            call_ticker = ib.reqMktData(call_contract, '', False, False)
            ib.sleep(2)
            
            if call_ticker.bid is not None and call_ticker.ask is not None:
                logger.info(f"  Bid: ${call_ticker.bid:.2f}")
                logger.info(f"  Ask: ${call_ticker.ask:.2f}")
                logger.info(f"  Last: ${call_ticker.last:.2f}" if call_ticker.last else "  Last: N/A")
                logger.info(f"  Volume: {call_ticker.volume}" if call_ticker.volume else "  Volume: N/A")
                
                # Check if > $20
                if call_ticker.bid > 20:
                    logger.info(f"\n  ⚠️  Call bid ${call_ticker.bid:.2f} is > $20")
                    logger.info(f"  If sold at bid ${call_ticker.bid:.2f}:")
                    logger.info(f"  4x stop loss would be at: ${call_ticker.bid * 4:.2f}")
                    logger.info(f"  Max risk: ${(call_ticker.bid * 4 - call_ticker.bid) * 100:.2f}")
                else:
                    logger.info(f"\n  ℹ️  Call bid ${call_ticker.bid:.2f} is < $20 (no action needed)")
            else:
                logger.warning("  No bid/ask data available")
                
            ib.cancelMktData(call_contract)
        except Exception as e:
            logger.error(f"  Error getting call data: {e}")
        
        logger.info("\n" + "-"*40)
        
    except Exception as e:
        logger.error(f"Connection error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if ib.isConnected():
            logger.info("\nDisconnecting...")
            ib.disconnect()

if __name__ == "__main__":
    main()