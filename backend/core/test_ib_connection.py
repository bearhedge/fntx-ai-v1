#!/usr/bin/env python3
"""
Simple IB Gateway connection test script
Based on troubleshooting document
"""
from ib_insync import IB, util
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    util.startLoop()
    ib = IB()
    try:
        print("Testing IB Gateway connection on port 4001...")
        ib.connect('127.0.0.1', 4001, clientId=9999, timeout=10)
        print(f"✅ Connected: {ib.isConnected()}")
        if ib.isConnected():
            print(f"Server version: {ib.serverVersion()}")
            print("Connection test successful!")
        ib.disconnect()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("IB Gateway is not accepting API connections on port 4001")