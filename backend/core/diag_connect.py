#!/usr/bin/env python3
"""
Minimal IB Gateway Connection Diagnostic Script
Isolates ib_insync connection issues from application complexity
"""
import logging
import time
from ib_insync import IB, util

# Enable detailed logging to see ib_insync internal messages
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_ib_connection():
    """Test basic IB Gateway connection with minimal complexity"""
    print("="*60)
    print("IB GATEWAY CONNECTION DIAGNOSTIC")
    print("="*60)
    
    ib = IB()
    
    try:
        print(f"ib_insync version: {IB.__module__}")
        print(f"Attempting connection to 127.0.0.1:4001...")
        
        # Test basic socket connectivity first
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 4001))
        sock.close()
        
        if result != 0:
            print("❌ FAILURE: Port 4001 is not accessible")
            print("   IB Gateway may not be running or API is disabled")
            return False
        else:
            print("✅ SUCCESS: Port 4001 is accessible")
        
        # Use unique client ID to avoid conflicts
        client_id = int(time.time() % 10000) + 777
        print(f"Using client ID: {client_id}")
        
        # Attempt ib_insync connection with debug logging
        print("Initiating ib_insync connection...")
        ib.connect('127.0.0.1', 4001, clientId=client_id, timeout=30)
        
        # Check connection status
        print(f"Connection attempt completed.")
        print(f"ib.isConnected(): {ib.isConnected()}")
        
        if ib.isConnected():
            print("✅ SUCCESS: IB API connection established!")
            
            # Get additional connection info
            try:
                print(f"Server version: {ib.serverVersion()}")
                print(f"Connection time: {ib.connectionTime()}")
                print(f"Managed accounts: {ib.managedAccounts()}")
                print("✅ All connection validation passed!")
                return True
            except Exception as e:
                print(f"⚠️  WARNING: Connected but failed to get server info: {e}")
                return True
        else:
            print("❌ FAILURE: Connection completed but ib.isConnected() returned False")
            print("   This indicates an API-level handshake failure")
            return False
            
    except Exception as e:
        print(f"❌ CRITICAL FAILURE: Exception during connection: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if ib.isConnected():
            print("Disconnecting...")
            ib.disconnect()
            print("Disconnected successfully")
        else:
            print("No active connection to disconnect")
        
        print("="*60)
        print("DIAGNOSTIC COMPLETE")
        print("="*60)

if __name__ == "__main__":
    # Start the event loop for ib_insync (like in execute_spy_trades.py)
    util.startLoop()
    success = test_ib_connection()
    exit(0 if success else 1)