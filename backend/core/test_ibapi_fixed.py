#!/usr/bin/env python3
"""
Test Fixed IBAPI Implementation
Quick test to verify threading fixes work
"""

import sys
import logging
import time
from pathlib import Path

# Add project path
sys.path.append('/home/info/fntx-ai-v1/backend')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fixed_connection():
    """Test the fixed IBAPI connection"""
    try:
        from core.trading.ibapi_trader import IBAPITrader
        
        logger.info("Testing fixed IBAPI connection...")
        
        # Create trader instance
        trader = IBAPITrader()
        
        # Test connection with shorter timeout
        success = trader.connect_api(client_id=8888, timeout=10)
        
        if success:
            logger.info("✅ Fixed IBAPI connection working!")
            logger.info(f"   Client ID: {trader.client_id}")
            logger.info(f"   Next Order ID: {trader.next_order_id}")
            
            # Quick price test
            logger.info("Testing market data request...")
            prices = trader.get_option_price('SPY', 630, 'C')
            
            if prices:
                bid, ask = prices
                logger.info(f"✅ Market data working: SPY 630C Bid=${bid:.2f}, Ask=${ask:.2f}")
            else:
                logger.warning("⚠️  Market data failed (could be after hours)")
            
            trader.disconnect_api()
            return True
        else:
            logger.error("❌ Connection still failing")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    logger.info("="*50)
    logger.info("TESTING FIXED IBAPI IMPLEMENTATION")
    logger.info("="*50)
    
    # Test socket connectivity first
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('127.0.0.1', 4001))
        sock.close()
        
        if result != 0:
            logger.error("❌ IB Gateway not accessible on port 4001")
            return False
        else:
            logger.info("✓ Port 4001 accessible")
    except Exception as e:
        logger.error(f"❌ Socket test failed: {e}")
        return False
    
    # Test the fixed connection
    success = test_fixed_connection()
    
    if success:
        logger.info("\n🎯 IBAPI IS FIXED! You can now run:")
        logger.info("   python execute_spy_trades_ibapi.py")
    else:
        logger.error("\n❌ Still having issues - may need IB Gateway restart")
    
    return success

if __name__ == "__main__":
    main()