#!/usr/bin/env python3
"""
Execute single SPY options trades
Sell 1x 605 PUT and 1x 610 CALL with 4x stop loss
"""

import os
import sys
import time
from ib_insync import IB, Stock, Option, MarketOrder, StopOrder, Trade
from datetime import datetime

# Configuration
IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4001
CLIENT_ID = 3  # Use different client ID

def execute_single_spy_trades():
    """Execute single contract SPY options trades"""
    ib = IB()
    
    try:
        # Connect to IB Gateway
        print(f"Connecting to IB Gateway at {IBKR_HOST}:{IBKR_PORT}...")
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=CLIENT_ID)
        print("✅ Connected to IB Gateway")
        
        # Get today's date for expiration
        today = datetime.now().strftime("%Y%m%d")
        print(f"Trading 0DTE options expiring: {today}")
        
        # Define the option contracts
        spy_605_put = Option('SPY', today, 605, 'P', 'SMART')
        spy_610_call = Option('SPY', today, 610, 'C', 'SMART')
        
        # Qualify the contracts
        print("\nQualifying contracts...")
        qualified = ib.qualifyContracts(spy_605_put, spy_610_call)
        print(f"✅ Qualified {len(qualified)} contracts")
        
        # Get current prices
        print("\nGetting current market data...")
        put_ticker = ib.reqTickers(spy_605_put)[0]
        call_ticker = ib.reqTickers(spy_610_call)[0]
        
        time.sleep(1)  # Give time for market data
        
        put_mid = (put_ticker.bid + put_ticker.ask) / 2 if put_ticker.bid and put_ticker.ask else 0.30
        call_mid = (call_ticker.bid + call_ticker.ask) / 2 if call_ticker.bid and call_ticker.ask else 0.15
        
        print(f"\n📊 Current Prices:")
        print(f"SPY 605 PUT: Bid ${put_ticker.bid:.2f}, Ask ${put_ticker.ask:.2f}, Mid ${put_mid:.2f}")
        print(f"SPY 610 CALL: Bid ${call_ticker.bid:.2f}, Ask ${call_ticker.ask:.2f}, Mid ${call_mid:.2f}")
        
        # Place sell orders one at a time
        trades = []
        
        # Sell 1 SPY 605 PUT
        print(f"\n📉 Selling 1x SPY 605 PUT...")
        put_order = MarketOrder('SELL', 1)
        put_trade = ib.placeOrder(spy_605_put, put_order)
        trades.append(put_trade)
        print(f"   Order placed: ID {put_trade.order.orderId}")
        
        # Wait for fill
        time.sleep(3)
        
        # Sell 1 SPY 610 CALL
        print(f"📈 Selling 1x SPY 610 CALL...")
        call_order = MarketOrder('SELL', 1)
        call_trade = ib.placeOrder(spy_610_call, call_order)
        trades.append(call_trade)
        print(f"   Order placed: ID {call_trade.order.orderId}")
        
        # Wait for fills
        print("\n⏳ Waiting for fills...")
        time.sleep(5)
        
        # Check fills and place stop loss orders
        print("\n🛡️ Setting up stop losses...")
        for trade in trades:
            # Refresh trade status
            ib.sleep(0.1)
            
            contract_desc = f"SPY {trade.contract.strike} {trade.contract.right}"
            print(f"\nChecking {contract_desc}:")
            print(f"   Status: {trade.orderStatus.status}")
            
            if trade.orderStatus.status == 'Filled' and trade.orderStatus.avgFillPrice:
                avg_price = trade.orderStatus.avgFillPrice
                stop_price = avg_price * 4  # 4x stop loss
                
                print(f"   ✅ FILLED at ${avg_price:.2f}")
                print(f"   Setting stop loss at ${stop_price:.2f}")
                
                stop_order = StopOrder('BUY', 1, stop_price)
                stop_trade = ib.placeOrder(trade.contract, stop_order)
                print(f"   🛡️ Stop loss placed: ID {stop_trade.order.orderId}")
            else:
                print(f"   ⏳ Not filled yet or no fill price")
        
        # Final summary
        print("\n" + "="*60)
        print("✅ TRADE EXECUTION SUMMARY")
        print("="*60)
        
        total_premium = 0
        for trade in trades:
            if trade.orderStatus.status == 'Filled' and trade.orderStatus.avgFillPrice:
                contract_desc = f"SPY {trade.contract.strike} {trade.contract.right}"
                avg_price = trade.orderStatus.avgFillPrice
                premium = avg_price * 100  # 1 contract
                total_premium += premium
                
                print(f"{contract_desc}:")
                print(f"  SOLD 1 contract @ ${avg_price:.2f} = ${premium:.2f} premium")
                print(f"  Stop Loss: ${avg_price * 4:.2f} (4x premium)")
                print()
        
        print(f"Total Premium Received: ${total_premium:.2f}")
        print(f"Account Value: $80,515 + ${total_premium:.2f} = ${80515 + total_premium:.2f}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\n🔌 Disconnected from IB Gateway")

if __name__ == "__main__":
    execute_single_spy_trades()