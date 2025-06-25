#!/usr/bin/env python3
"""
Command Line Interface for Options Trading
"""
import argparse
import sys
from options_trader import OptionsTrader

def main():
    parser = argparse.ArgumentParser(description='Options Trading CLI')
    parser.add_argument('action', choices=['sell', 'strangle', 'positions', 'price'])
    parser.add_argument('--symbol', default='SPY', help='Symbol to trade')
    parser.add_argument('--strike', type=float, help='Strike price')
    parser.add_argument('--right', choices=['C', 'P'], help='Call or Put')
    parser.add_argument('--put-strike', type=float, help='Put strike for strangle')
    parser.add_argument('--call-strike', type=float, help='Call strike for strangle')
    parser.add_argument('--stop', type=float, default=3.0, help='Stop loss multiple (default 3x)')
    parser.add_argument('--expiry', help='Expiration date (YYYYMMDD, default today)')
    
    args = parser.parse_args()
    
    trader = OptionsTrader()
    
    if not trader.connect():
        print("❌ Failed to connect to IB Gateway")
        return 1
    
    try:
        if args.action == 'sell':
            if not args.strike or not args.right:
                print("❌ --strike and --right required for sell")
                return 1
                
            result = trader.sell_option_with_stop(
                args.symbol, args.strike, args.right, args.stop, args.expiry
            )
            
            if result.success:
                print(f"✅ {result.message}")
                print(f"Credit: ${result.credit:.2f}")
                print(f"Stop: ${result.stop_loss:.2f}")
                print(f"Max Risk: ${result.max_risk:.2f}")
            else:
                print(f"❌ {result.message}")
                
        elif args.action == 'strangle':
            if not args.put_strike or not args.call_strike:
                print("❌ --put-strike and --call-strike required for strangle")
                return 1
                
            results = trader.sell_strangle(
                args.symbol, args.put_strike, args.call_strike, args.stop, args.expiry
            )
            
            total_credit = sum(r.credit for r in results if r.success)
            total_risk = sum(r.max_risk for r in results if r.success)
            
            for result in results:
                status = "✅" if result.success else "❌"
                print(f"{status} {result.symbol} {result.strike}{result.right}: {result.message}")
                
            print(f"\nTotal Credit: ${total_credit:.2f}")
            print(f"Total Max Risk: ${total_risk:.2f}")
            
        elif args.action == 'positions':
            positions = trader.get_positions()
            if positions:
                print("Current Positions:")
                for pos in positions:
                    print(f"{pos['symbol']} {pos.get('strike', 'N/A')}{pos.get('right', '')} "
                          f"Qty: {pos['position']} Value: ${pos['marketValue']:.2f}")
            else:
                print("No positions found")
                
        elif args.action == 'price':
            if not args.strike or not args.right:
                print("❌ --strike and --right required for price")
                return 1
                
            prices = trader.get_option_price(args.symbol, args.strike, args.right, args.expiry)
            if prices:
                bid, ask = prices
                print(f"{args.symbol} {args.strike}{args.right}: Bid ${bid:.2f}, Ask ${ask:.2f}")
            else:
                print("❌ Could not get price data")
                
    finally:
        trader.disconnect()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())