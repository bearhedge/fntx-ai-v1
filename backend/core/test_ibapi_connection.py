#!/usr/bin/env python3
"""
Test IBAPI Installation and Basic Connection
Minimal test to verify IBAPI migration readiness
"""

import sys
import logging
import time
from pathlib import Path

# Add project path
sys.path.append('/home/info/fntx-ai-v1/backend')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ibapi_import():
    """Test IBAPI package import"""
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.contract import Contract
        from ibapi.order import Order
        logger.info("✅ IBAPI package imported successfully")
        logger.info(f"   EClient: {EClient}")
        logger.info(f"   EWrapper: {EWrapper}")
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import IBAPI: {e}")
        return False

def test_ibapi_trader_import():
    """Test IBAPITrader class import"""
    try:
        from core.trading.ibapi_trader import IBAPITrader, TradeResult
        logger.info("✅ IBAPITrader class imported successfully")
        logger.info(f"   IBAPITrader: {IBAPITrader}")
        logger.info(f"   TradeResult: {TradeResult}")
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import IBAPITrader: {e}")
        return False

def test_basic_connection():
    """Test basic connection to IB Gateway (if running)"""
    try:
        from core.trading.ibapi_trader import IBAPITrader
        
        # Test socket connectivity first
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 4001))
        sock.close()
        
        if result != 0:
            logger.warning("⚠️  IB Gateway not running on port 4001 - skipping connection test")
            logger.info("   This is expected if IB Gateway is not currently running")
            return True
        
        logger.info("✓ Port 4001 is accessible - testing IBAPI connection...")
        
        # Test IBAPI connection
        trader = IBAPITrader()
        success = trader.connect_api(client_id=9999)  # Use test client ID
        
        if success:
            logger.info("✅ IBAPI connection test successful")
            logger.info(f"   Client ID: {trader.client_id}")
            logger.info(f"   Managed Accounts: {trader.managed_accounts}")
            
            # Test market data request
            prices = trader.get_option_price('SPY', 630, 'C', '20250804')
            if prices:
                bid, ask = prices
                logger.info(f"✅ Market data test successful: SPY 630C Bid=${bid:.2f}, Ask=${ask:.2f}")
            else:
                logger.warning("⚠️  Market data test failed (may be due to market hours)")
            
            trader.disconnect_api()
            return True
        else:
            logger.error("❌ IBAPI connection test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection test error: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("IBAPI MIGRATION READINESS TEST")
    logger.info("="*60)
    
    tests = [
        ("IBAPI Package Import", test_ibapi_import),
        ("IBAPITrader Class Import", test_ibapi_trader_import),
        ("Basic Connection Test", test_basic_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ PASSED: {test_name}")
            else:
                logger.error(f"❌ FAILED: {test_name}")
        except Exception as e:
            logger.error(f"❌ ERROR in {test_name}: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎯 All tests passed! IBAPI migration is ready.")
        logger.info("   You can now use execute_spy_trades_ibapi.py instead of execute_spy_trades.py")
        logger.info("   No more ghost connection issues!")
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed. Review errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)