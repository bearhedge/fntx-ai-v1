#!/usr/bin/env python3
"""
Check current SPY options positions and add stop losses if needed
"""

import os
import sys
import time
from ib_insync import IB, Stock, Option, StopOrder
from datetime import datetime

# Configuration
IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4001
CLIENT_ID = 2

def check_positions_and_add_stops():
    """Check positions and add stop loss orders"""
    ib = IB()
    
    try:
        print(f"Connecting to IB Gateway...")
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=CLIENT_ID)
        print("✅ Connected")
        
        # Get all positions
        positions = ib.positions()
        print(f"\n📊 Current Positions:")
        print("=" * 60)
        
        spy_positions = []
        for pos in positions:
            if pos.contract.symbol == 'SPY' and pos.contract.secType == 'OPT':
                spy_positions.append(pos)
                print(f"Contract: SPY {pos.contract.strike} {pos.contract.right}")
                print(f"Position: {pos.position} contracts")
                print(f"Avg Cost: ${pos.avgCost:.2f}")
                print(f"Market Value: ${pos.marketValue:.2f}")
                print(f"Unrealized P&L: ${pos.unrealizedPnL:.2f}")
                print("-" * 40)
        
        # Get open orders
        open_orders = ib.openOrders()
        print(f"\n📋 Open Orders:")
        for order in open_orders:
            if hasattr(order.contract, 'symbol') and order.contract.symbol == 'SPY':
                print(f"{order.contract.strike} {order.contract.right}: {order.orderType} {order.action} {order.totalQuantity} @ ${order.auxPrice if hasattr(order, 'auxPrice') else 'MKT'}")
        
        # Check if we need to add stop losses
        for pos in spy_positions:
            if pos.position < 0:  # Short position
                avg_price = abs(pos.avgCost / 100)  # Convert to per-contract price
                stop_price = avg_price * 4  # 4x stop loss
                
                # Check if stop already exists
                has_stop = False
                for order in open_orders:
                    if (order.contract.conId == pos.contract.conId and 
                        order.orderType == 'STP' and 
                        order.action == 'BUY'):
                        has_stop = True
                        break
                
                if not has_stop:
                    print(f"\n🛡️ Adding stop loss for {pos.contract.strike} {pos.contract.right}")
                    print(f"   Avg price: ${avg_price:.2f}")
                    print(f"   Stop at: ${stop_price:.2f}")
                    
                    stop_order = StopOrder('BUY', abs(pos.position), stop_price)
                    stop_trade = ib.placeOrder(pos.contract, stop_order)
                    print(f"   ✅ Stop order placed: ID {stop_trade.order.orderId}")
        
        # Account summary
        account = ib.accountSummary()
        for item in account:
            if item.tag in ['NetLiquidation', 'UnrealizedPnL', 'RealizedPnL']:
                print(f"\n{item.tag}: ${float(item.value):,.2f}")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\n🔌 Disconnected")

if __name__ == "__main__":
    check_positions_and_add_stops()