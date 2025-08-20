#!/usr/bin/env python3
"""
Get ARM 143 Call option quote for Aug 22 2025
Using IB Gateway (the working method from execute_spy_trades.py)
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.options_trader import OptionsTrader
from ib_insync import util, Option

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_arm_option_quote():
    """Get ARM 143 call option expiring Aug 22 2025"""
    
    print("\n" + "="*60)
    print("ARM $143 CALL - AUGUST 22, 2025")
    print("="*60)
    
    # Initialize trader (same as execute_spy_trades.py)
    trader = OptionsTrader(host='127.0.0.1', port=4001)
    
    # Connect to IB Gateway
    logger.info("Connecting to IB Gateway...")
    
    if not trader.connect():
        logger.error("❌ Failed to connect to IB Gateway")
        logger.error("   Please ensure IB Gateway is running on port 4001")
        return
    
    logger.info("✓ Connected to IB Gateway")
    
    try:
        # Create ARM option contract
        # ARM Aug 22 2025 143 Call
        arm_option = Option(
            symbol='ARM',
            lastTradeDateOrContractMonth='20250822',  # August 22, 2025
            strike=143.0,
            right='C',  # Call
            exchange='SMART',
            currency='USD'
        )
        
        # Qualify the contract (get full details from IBKR)
        logger.info("Qualifying ARM option contract...")
        contracts = trader.ib.qualifyContracts(arm_option)
        
        if not contracts:
            logger.error("❌ Could not find ARM Aug 22 2025 143 Call")
            logger.error("   The contract may not exist yet or have different specifications")
            return
        
        arm_option = contracts[0]
        logger.info(f"✓ Found contract: {arm_option}")
        
        # Request market data
        logger.info("Requesting market data...")
        ticker = trader.ib.reqMktData(arm_option, '', False, False)
        
        # Wait for data to populate
        trader.ib.sleep(3)
        
        # Display the quote
        print("\n" + "="*60)
        print("ARM $143 CALL - AUGUST 22, 2025 - QUOTE")
        print("="*60)
        
        if ticker.bid is not None and ticker.ask is not None:
            print(f"Bid: ${ticker.bid:.2f}")
            print(f"Ask: ${ticker.ask:.2f}")
            print(f"Mid: ${(ticker.bid + ticker.ask) / 2:.2f}")
            
            if ticker.last is not None:
                print(f"Last: ${ticker.last:.2f}")
            if ticker.volume is not None:
                print(f"Volume: {ticker.volume}")
            if ticker.high is not None:
                print(f"High: ${ticker.high:.2f}")
            if ticker.low is not None:
                print(f"Low: ${ticker.low:.2f}")
            if ticker.close is not None:
                print(f"Previous Close: ${ticker.close:.2f}")
                
            # Calculate implied volatility if available
            if ticker.modelGreeks:
                print(f"\nGreeks:")
                print(f"IV: {ticker.modelGreeks.impliedVol:.2%}")
                print(f"Delta: {ticker.modelGreeks.delta:.4f}")
                print(f"Gamma: {ticker.modelGreeks.gamma:.4f}")
                print(f"Theta: {ticker.modelGreeks.theta:.4f}")
                print(f"Vega: {ticker.modelGreeks.vega:.4f}")
        else:
            print("❌ No market data available")
            print("   This could mean:")
            print("   1. The option doesn't exist yet (too far out)")
            print("   2. No market data subscription")
            print("   3. Market is closed")
            
            # Try to at least show contract details
            if arm_option.conId:
                print(f"\nContract Details:")
                print(f"Contract ID: {arm_option.conId}")
                print(f"Symbol: {arm_option.symbol}")
                print(f"Strike: ${arm_option.strike}")
                print(f"Expiry: {arm_option.lastTradeDateOrContractMonth}")
                print(f"Right: {'Call' if arm_option.right == 'C' else 'Put'}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
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
    get_arm_option_quote()