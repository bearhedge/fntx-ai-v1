#!/usr/bin/env python3
"""
Simple connection test without ghost cleanup logic
Sometimes the cleanup logic itself causes issues
"""
import logging
import random
import time
from ib_insync import IB, util

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def simple_connection_test():
    """Test connection without any ghost cleanup logic"""
    print("🔌 Testing simple connection without cleanup...")
    
    # Start event loop
    util.startLoop()
    
    ib = IB()
    
    try:
        # Use completely random client ID
        client_id = random.randint(5000, 9999)
        print(f"Using client ID: {client_id}")
        
        # Simple connection with longer timeout
        print("Attempting connection...")
        ib.connect('127.0.0.1', 4001, clientId=client_id, timeout=45)
        
        if ib.isConnected():
            print("✅ SUCCESS: Simple connection worked!")
            print(f"Server version: {ib.serverVersion()}")
            print(f"Connection time: {ib.connectionTime()}")
            return True
        else:
            print("❌ Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False
    finally:
        if ib and ib.isConnected():
            ib.disconnect()
            print("Disconnected")

if __name__ == "__main__":
    success = simple_connection_test()
    if success:
        print("\n🎯 The issue was with the ghost cleanup logic!")
        print("Consider using this simpler approach in your trading script.")
    else:
        print("\n💡 The ghost connections are likely the real issue.")
        print("You may need to restart IB Gateway completely.")