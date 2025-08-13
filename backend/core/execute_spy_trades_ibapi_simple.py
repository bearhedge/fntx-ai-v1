#!/usr/bin/env python3
"""
Quick IBAPI Implementation for SPY Options Trading
Simplified version to avoid threading complexity
"""

import sys
import argparse
import logging
import time
from datetime import datetime
import os
import threading
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from config/.env
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

# IBAPI imports
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleIBAPI(EWrapper, EClient):
    """Simplified IBAPI implementation for quick testing"""
    
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id = None
        self.connected = False
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode == 2104 or errorCode == 2106:
            logger.debug(f"Market data: {errorString}")
        elif errorCode >= 2100 and errorCode <= 2200:
            logger.info(f"Info ({errorCode}): {errorString}")
        else:
            logger.error(f"Error {errorCode}: {errorString}")
    
    def nextValidId(self, orderId):
        self.next_order_id = orderId
        self.connected = True
        logger.info(f"Connected! Next order ID: {orderId}")
    
    def connectAck(self):
        logger.info("Connection acknowledged")

def test_connection():
    """Quick connection test"""
    logger.info("Testing IBAPI connection...")
    
    app = SimpleIBAPI()
    
    # Generate unique client ID
    client_id = int(time.time() % 10000) + 1000
    
    try:
        app.connect("127.0.0.1", 4001, client_id)
        
        # Start API thread
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        
        # Wait for connection
        timeout = 10
        start_time = time.time()
        
        while not app.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if app.connected:
            logger.info(f"✅ IBAPI connection successful (Client ID: {client_id})")
            app.disconnect()
            return True
        else:
            logger.error("❌ Connection timeout")
            app.disconnect()
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False

def main():
    """Quick test main function"""
    logger.info("="*60)
    logger.info("QUICK IBAPI CONNECTION TEST")
    logger.info("="*60)
    
    # Test socket connectivity
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 4001))
        sock.close()
        
        if result != 0:
            logger.error("❌ IB Gateway not running on port 4001")
            return False
        else:
            logger.info("✓ Port 4001 accessible")
    except Exception as e:
        logger.error(f"❌ Socket test failed: {e}")
        return False
    
    # Test IBAPI connection
    if test_connection():
        logger.info("\n🎯 IBAPI is working! You can now proceed with full migration.")
        logger.info("   The complex IBAPITrader class needs threading fixes.")
        logger.info("   For now, use the original execute_spy_trades.py")
        return True
    else:
        logger.error("\n❌ IBAPI connection failed")
        logger.error("   Check IB Gateway settings and try again")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)