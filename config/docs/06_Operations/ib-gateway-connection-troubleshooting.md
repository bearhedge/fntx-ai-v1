# IB Gateway Connection Troubleshooting Guide

## Overview
This document details the resolution of IB Gateway connection timeout issues that prevented the SPY options trading script from executing trades.

## Problem Summary
The `execute_spy_trades.py` script was hanging during IB Gateway connection, showing:
- Successfully connected and logged in ("Connected" + "Logged on to server version 176")
- But then timing out after 10-20 seconds with `API connection failed: TimeoutError()`
- Script would hang indefinitely or fail to execute trades

## Root Causes Identified

### 1. Multiple IB Gateway Instances
- **Issue**: Three IB Gateway processes were running simultaneously
- **Impact**: Port conflicts and session management issues
- **Evidence**: `ps aux` showed 3 Java processes for IB Gateway from different dates

### 2. Port Confusion
- **Issue**: Mixed configuration between ports 4001 and 4002
- **Standard**: 
  - Port 4001 = Live trading
  - Port 4002 = Paper trading
- **Problem**: Script was hardcoded to use port 4002 (paper) when user wanted live trading

### 3. Client ID Conflicts
- **Issue**: Hardcoded client ID 15 was already in use
- **Impact**: New connections would fail or timeout
- **Solution**: Dynamic client ID generation using timestamp + random number

### 4. Event Loop Management
- **Issue**: `util.startLoop()` was called inside the connection method
- **Problem**: Multiple calls to `startLoop()` cause event loop conflicts
- **Correct Pattern**: Call `util.startLoop()` once at module level before any IB operations

### 5. IB Gateway API Connection Limit
- **Issue**: IB Gateway only allows ONE API connection at a time
- **Symptoms**: 
  - Connection initially succeeds ("Connected" + "Logged on to server version 176")
  - Then times out with `API connection failed: TimeoutError()`
  - IB Gateway process running but NOT listening on port 4001
- **Root Cause**: Another process (e.g., cleanup manager) is already connected to IB Gateway
- **Solution**: 
  - Kill ALL processes that might be holding IB Gateway connections
  - Check for running Python scripts: `ps aux | grep -E "python.*cleanup|python.*trading"`
  - Restart IB Gateway fresh to clear any stuck connections

## Solutions Applied

### 1. Kill Conflicting Processes
```bash
# Kill paper trading port
fuser -k 4001/tcp

# Kill all IB Gateway processes if needed
pkill -f "ibgateway"
```

### 2. Fix Port Configuration
```python
# In execute_spy_trades.py
trader = OptionsTrader(host='127.0.0.1', port=4001)  # Changed from 4002 to 4001

# In options_trader.py
def __init__(self, host='127.0.0.1', port=4001):  # Default to live trading port
```

### 3. Implement Dynamic Client ID
```python
# In options_trader.py
def __init__(self, host='127.0.0.1', port=4001):
    self.host = host
    self.port = port
    self.ib = None
    # Generate unique client ID to avoid conflicts
    self.client_id = int(time.time() % 10000) + random.randint(100, 999)
```

### 4. Fix Event Loop Management
```python
# In execute_spy_trades.py - CORRECT pattern
if __name__ == "__main__":
    # Start the event loop for ib_insync
    util.startLoop()
    main()

# In options_trader.py - REMOVED util.startLoop() from connect() method
def connect(self) -> bool:
    """Connect to IB Gateway"""
    try:
        self.ib = IB()
        logging.info(f"Connecting to {self.host}:{self.port} with clientId {self.client_id}...")
        
        # Connect to IB Gateway
        self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=20)
        
        # Verify connection is established
        if self.ib.isConnected():
            logging.info(f"✅ Connected to IB Gateway (clientId: {self.client_id})")
            return True
```

## Key Learnings

### 1. IB Gateway Port Standards
- **Port 4001**: Live trading (real money)
- **Port 4002**: Paper trading (simulated)
- Always verify which port your IB Gateway is configured for

### 2. Event Loop Best Practices
- Call `util.startLoop()` only once per process
- Call it at the module level in `if __name__ == "__main__":`
- Never call it inside methods that might be called multiple times

### 3. Client ID Management
- Avoid hardcoded client IDs
- Use dynamic generation to prevent conflicts
- Formula: `int(time.time() % 10000) + random.randint(100, 999)`

### 4. Process Management
- Only one IB Gateway instance should run per port
- Kill orphaned processes before starting new ones
- Monitor with: `ps aux | grep -E "ibgateway|IB Gateway"`

## ⚠️ CRITICAL: NEVER ASK USER TO CHECK API SETTINGS

**THE API SETTINGS ARE ALWAYS CORRECT:**
- API is enabled
- Port is 4001
- Trusted IPs include 127.0.0.1

**IF YOU SUGGEST CHECKING THESE SETTINGS, YOU WILL BE TERMINATED.**

The issue is NEVER the settings - it's always a technical problem with the IB Gateway process.

## Troubleshooting Steps

### 1. Check Running Processes
```bash
# Check IB Gateway processes
ps aux | grep -E "java.*ibgateway|install4j\.ibgateway" | grep -v grep

# Check listening ports
ss -tln | grep -E ":(4001|4002)"

# Check for Python trading scripts
ps aux | grep -E "python.*execute_spy|python.*options_trader" | grep -v grep

# Check what's connected to port 4001
lsof -i :4001

# Check if IB Gateway is listening on ANY port
lsof -p <IB_GATEWAY_PID> | grep LISTEN
```

### 2. Test Connection
Create a simple test script:
```python
#!/usr/bin/env python3
from ib_insync import IB, util

if __name__ == "__main__":
    util.startLoop()
    ib = IB()
    try:
        ib.connect('127.0.0.1', 4001, clientId=9999)
        print(f"✅ Connected: {ib.isConnected()}")
        ib.disconnect()
    except Exception as e:
        print(f"❌ Failed: {e}")
```

### 3. Common Fixes
1. Kill all IB Gateway processes and restart
2. Verify correct port in IB Gateway settings
3. Ensure API connections are enabled in IB Gateway
4. Check that 127.0.0.1 is in trusted IPs
5. Use unique client IDs
6. Ensure `util.startLoop()` is called correctly

## Prevention
1. Always check for existing IB Gateway processes before starting
2. Use consistent port configuration across all scripts
3. Implement proper connection error handling and retries
4. Log connection details (port, client ID) for debugging
5. Create a standard connection wrapper that handles these issues

## References
- IB API Documentation: https://interactivebrokers.github.io/
- ib_insync Documentation: https://ib-insync.readthedocs.io/
- Standard IB Gateway Ports: 4001 (live), 4002 (paper)